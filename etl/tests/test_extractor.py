"""
etl/tests/test_extractor.py
===========================
Unit tests for the resilient ETL API Extractor and State Manager.
Validates pagination, tenacity exponential backoff retries, rate-limiting (429),
and incremental watermarking.
"""

import json
from pathlib import Path

import httpx

from etl.pipeline.extractor import ApiExtractor
from etl.pipeline.state_manager import StateManager


class MockTransport(httpx.BaseTransport):
    """Custom transport to simulate network responses, retries, and errors."""

    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if not self.responses:
            raise RuntimeError("No more mocked responses available")
        return self.responses.pop(0)


def test_state_manager_atomic_updates(tmp_path: Path):
    """Verify state manager reads, updates, and persists watermarks atomically."""
    state_file = tmp_path / "test_state.json"
    mgr = StateManager(state_file_path=state_file)

    # Initial state should be None
    assert mgr.get_watermark("claims") is None

    # Update state
    mgr.update_watermark("claims", "2026-11-19T10:00:00", records_processed=500)
    assert mgr.get_watermark("claims") == "2026-11-19T10:00:00"

    # Verify underlying file contents
    assert state_file.exists()
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data["claims"]["records_processed"] == 500


def test_extractor_pagination_traversal(tmp_path: Path):
    """Verify extractor iterates through multiple pages based on has_next."""
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file_path=state_file)

    # Prepare two paginated responses
    page1_body = {
        "data": [{"id": 1, "name": "Claim 1"}, {"id": 2, "name": "Claim 2"}],
        "pagination": {
            "page": 1,
            "page_size": 2,
            "total_records": 4,
            "total_pages": 2,
            "has_next": True,
            "has_prev": False,
        },
    }
    page2_body = {
        "data": [{"id": 3, "name": "Claim 3"}, {"id": 4, "name": "Claim 4"}],
        "pagination": {
            "page": 2,
            "page_size": 2,
            "total_records": 4,
            "total_pages": 2,
            "has_next": False,
            "has_prev": True,
        },
    }

    mock_transport = MockTransport(
        [
            httpx.Response(200, json=page1_body),
            httpx.Response(200, json=page2_body),
        ]
    )
    client = httpx.Client(transport=mock_transport)

    extractor = ApiExtractor(
        base_url="http://mock-service",
        api_key="test-key",
        state_mgr=mgr,
        raw_output_dir=tmp_path,
        client=client,
    )

    records = extractor.extract_entity(
        "customers", "/api/v1/customers", is_incremental=False
    )
    assert len(records) == 4
    assert [r["id"] for r in records] == [1, 2, 3, 4]
    assert len(mock_transport.calls) == 2


def test_extractor_retry_on_503_transient_error(tmp_path: Path):
    """Verify tenacity retries on 503 Service Unavailable and succeeds on subsequent attempt."""
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file_path=state_file)

    success_body = {
        "data": [{"claim_id": "CLM-0001", "created_at": "2026-11-19T08:00:00"}],
        "pagination": {
            "page": 1,
            "page_size": 1,
            "total_records": 1,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        },
    }

    # First attempt: 503 Server Error, Second attempt: 200 OK
    mock_transport = MockTransport(
        [
            httpx.Response(503, json={"error": "Service Unavailable"}),
            httpx.Response(200, json=success_body),
        ]
    )
    client = httpx.Client(transport=mock_transport)

    extractor = ApiExtractor(
        base_url="http://mock-service",
        api_key="test-key",
        state_mgr=mgr,
        raw_output_dir=tmp_path,
        client=client,
    )

    records = extractor.extract_entity("claims", "/api/v1/claims", is_incremental=False)
    assert len(records) == 1
    assert records[0]["claim_id"] == "CLM-0001"
    # Proves retry occurred: 2 requests made
    assert len(mock_transport.calls) == 2


def test_extractor_rate_limit_429_handling(tmp_path: Path):
    """Verify extractor intercepts HTTP 429, pauses for Retry-After, and retries."""
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file_path=state_file)

    success_body = {
        "data": [{"claim_id": "CLM-0002", "created_at": "2026-11-19T09:00:00"}],
        "pagination": {
            "page": 1,
            "page_size": 1,
            "total_records": 1,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        },
    }

    # First attempt: 429 Too Many Requests (Retry-After: 0 seconds for fast unit test)
    # Second attempt: 200 OK
    mock_transport = MockTransport(
        [
            httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"detail": "Rate limit exceeded"},
            ),
            httpx.Response(200, json=success_body),
        ]
    )
    client = httpx.Client(transport=mock_transport)

    extractor = ApiExtractor(
        base_url="http://mock-service",
        api_key="test-key",
        state_mgr=mgr,
        raw_output_dir=tmp_path,
        client=client,
    )

    records = extractor.extract_entity("claims", "/api/v1/claims", is_incremental=False)
    assert len(records) == 1
    assert records[0]["claim_id"] == "CLM-0002"
    assert len(mock_transport.calls) == 2


def test_extractor_incremental_watermark_update(tmp_path: Path):
    """Verify incremental extraction updates watermark with maximum timestamp in batch."""
    state_file = tmp_path / "state.json"
    mgr = StateManager(state_file_path=state_file)

    claims_body = {
        "data": [
            {"claim_id": "CLM-001", "created_at": "2026-11-18T10:00:00"},
            {"claim_id": "CLM-002", "created_at": "2026-11-19T14:30:00"},
            {"claim_id": "CLM-003", "created_at": "2026-11-19T09:15:00"},
        ],
        "pagination": {
            "page": 1,
            "page_size": 3,
            "total_records": 3,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        },
    }

    mock_transport = MockTransport([httpx.Response(200, json=claims_body)])
    client = httpx.Client(transport=mock_transport)

    extractor = ApiExtractor(
        base_url="http://mock-service",
        api_key="test-key",
        state_mgr=mgr,
        raw_output_dir=tmp_path,
        client=client,
    )

    records = extractor.extract_claims(incremental=True)
    assert len(records) == 3

    # Watermark must be the maximum created_at timestamp
    saved_watermark = mgr.get_watermark("claims")
    assert saved_watermark == "2026-11-19T14:30:00"
