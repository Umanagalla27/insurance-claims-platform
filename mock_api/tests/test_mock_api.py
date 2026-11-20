"""
mock_api/tests/test_mock_api.py
===============================
Comprehensive test suite for the Mock Policy & Claims API.
Validates authentication, pagination, filtering, chaos injection, and rate limiting.
"""

from starlette.testclient import TestClient

from mock_api.app.config import settings
from mock_api.app.data_store import store
from mock_api.app.main import app

# Ensure store data is loaded for test suite
store.load_data()
client = TestClient(app)

VALID_HEADERS = {"X-API-Key": settings.mock_api_key}


def test_health_check():
    """Verify public health endpoint returns 200 and data volume metrics."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["records_loaded"]["claims"] >= 10000
    assert data["records_loaded"]["policies"] >= 800
    assert data["records_loaded"]["customers"] >= 500


def test_auth_missing_api_key():
    """Secured endpoints must reject unauthenticated requests with 401."""
    response = client.get("/api/v1/customers")
    assert response.status_code == 401
    assert "Missing required authentication header" in response.json()["detail"]


def test_auth_invalid_api_key():
    """Secured endpoints must reject invalid keys with 401."""
    response = client.get("/api/v1/customers", headers={"X-API-Key": "bogus-key"})
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]


def test_get_customers_paginated():
    """Verify customers endpoint returns correct page envelope."""
    response = client.get(
        "/api/v1/customers?page=1&page_size=25", headers=VALID_HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 25
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 25
    assert body["pagination"]["total_records"] >= 500
    assert body["pagination"]["has_next"] is True


def test_get_customer_by_id():
    """Verify fetching single customer by ID."""
    sample_id = store.customers[0]["customer_id"]
    response = client.get(f"/api/v1/customers/{sample_id}", headers=VALID_HEADERS)
    assert response.status_code == 200
    assert response.json()["customer_id"] == sample_id


def test_get_customer_not_found():
    """Non-existent customer must return 404."""
    response = client.get("/api/v1/customers/CUST-99999", headers=VALID_HEADERS)
    assert response.status_code == 404


def test_get_policies_filtered_by_status():
    """Verify filtering policies by status."""
    response = client.get(
        "/api/v1/policies?status=Active&page_size=20", headers=VALID_HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert item["status"] == "Active"


def test_get_claims_filtered_by_category():
    """Verify filtering claims by category."""
    response = client.get(
        "/api/v1/claims?category=Auto&page_size=20", headers=VALID_HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) > 0
    for item in body["data"]:
        assert item["claim_category"] == "Auto"


def test_get_claims_incremental_since_date():
    """Verify incremental extraction filter by since_date."""
    response = client.get(
        "/api/v1/claims?since_date=2025-01-01&page_size=10", headers=VALID_HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) > 0
    for item in body["data"]:
        claim_date = item.get("created_at") or item.get("filing_date")
        assert claim_date >= "2025-01-01"


def test_create_new_claim_success():
    """Verify submitting a valid claim returns 201 Created and persists."""
    sample_policy = store.policies[0]
    payload = {
        "policy_id": sample_policy["policy_id"],
        "customer_id": sample_policy["customer_id"],
        "claim_category": "Auto",
        "claim_priority": "High",
        "claim_amount": 3250.75,
        "incident_date": "2026-04-15",
        "state": "CA",
        "description": "Front collision with stationary pole during heavy rain.",
    }
    response = client.post("/api/v1/claims", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 201
    created = response.json()
    assert created["claim_id"].startswith("CLM-")
    assert created["claim_amount"] == 3250.75
    assert created["status"] == "Pending"

    # Verify lookup of newly created claim
    fetch_resp = client.get(
        f"/api/v1/claims/{created['claim_id']}", headers=VALID_HEADERS
    )
    assert fetch_resp.status_code == 200


def test_create_claim_invalid_policy():
    """Submitting a claim against non-existent policy must fail with 400."""
    payload = {
        "policy_id": "POL-99999",
        "customer_id": "CUST-0001",
        "claim_category": "Auto",
        "claim_amount": 1000.0,
        "incident_date": "2026-04-15",
        "state": "CA",
        "description": "Minor scratch on front fender.",
    }
    response = client.post("/api/v1/claims", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_chaos_middleware_forced_error():
    """Verify forced error injection works for upstream retry testing."""
    response = client.get(
        "/api/v1/claims", headers={**VALID_HEADERS, "X-Force-Error": "503"}
    )
    assert response.status_code == 503
    assert response.json()["error"] == "SimulatedFailure"


def test_rate_limiter_exceeded():
    """Verify rate limiter middleware triggers HTTP 429 when limit is exceeded."""
    from fastapi import FastAPI

    from mock_api.app.middleware.rate_limiter import RateLimitMiddleware

    tiny_app = FastAPI()
    tiny_app.add_middleware(RateLimitMiddleware, requests_per_minute=3)

    @tiny_app.get("/test")
    def dummy_route():
        return {"msg": "ok"}

    tiny_client = TestClient(tiny_app)
    headers = {"X-API-Key": "test-key"}

    # First 3 should succeed
    for _ in range(3):
        res = tiny_client.get("/test", headers=headers)
        assert res.status_code == 200

    # 4th request must trigger 429
    res = tiny_client.get("/test", headers=headers)
    assert res.status_code == 429
    assert "Rate limit exceeded" in res.json()["detail"]
    assert "Retry-After" in res.headers
