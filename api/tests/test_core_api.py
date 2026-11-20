"""Unit and Integration Tests for FastAPI Core Architecture (ICIP-016).

Tests health, readiness, telemetry metrics, ASGI middleware, and service container
dependency injection using direct synchronous invocation over async coroutines.
"""

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from api.app.main import create_app
from api.app.middleware.timing import TimingMiddleware
from api.app.routers.health import health_check, readiness_check, runtime_metrics
from api.app.services.container import (
    ServiceContainer,
    container,
    get_anomaly_detector,
    get_classifier,
    get_retrieval_service,
)


@pytest.fixture(scope="module")
def initialized_container():
    """Module-level pre-warmed service container."""
    container.initialize()
    return container


@pytest.fixture
def mock_request(initialized_container):
    """Create a mock Request with pre-warmed services state."""
    req = MagicMock(spec=Request)
    req.app = MagicMock()
    req.app.state.services = initialized_container
    req.state.request_id = "test-req-uuid-12345"
    return req


def test_health_liveness_probe():
    result = health_check()
    assert result.success is True
    assert result.data.status == "healthy"
    assert "Insurance Claims" in result.data.service
    assert result.data.version == "1.0.0"


def test_readiness_all_subsystems_healthy(mock_request):
    mock_response = Response()
    result = readiness_check(mock_request, mock_response)

    assert result.success is True
    assert result.data.status == "ready"
    assert mock_response.status_code == 200

    comp_dict = {c.component: c for c in result.data.components}
    assert "nlp_text_classifier" in comp_dict
    assert "isolation_forest_anomaly" in comp_dict
    assert "policy_vector_store" in comp_dict

    assert comp_dict["nlp_text_classifier"].status == "ready"
    assert comp_dict["isolation_forest_anomaly"].status == "ready"
    assert comp_dict["policy_vector_store"].status == "ready"


def test_readiness_degraded_when_model_offline(initialized_container):
    mock_req = MagicMock(spec=Request)
    mock_req.app = MagicMock()
    # Create copy container with classifier intentionally disabled
    degraded_container = ServiceContainer()
    degraded_container.anomaly_detector = initialized_container.anomaly_detector
    degraded_container.retrieval_service = initialized_container.retrieval_service
    degraded_container.status_flags = {
        "classifier": False,
        "anomaly_detector": True,
        "retrieval_service": True,
    }
    mock_req.app.state.services = degraded_container
    mock_response = Response()

    result = readiness_check(mock_req, mock_response)
    assert result.success is False
    assert result.data.status == "degraded"
    assert mock_response.status_code == 503


def test_runtime_metrics_telemetry(mock_request):
    result = runtime_metrics(mock_request)
    assert result.success is True
    data = result.data
    assert data.uptime_seconds >= 0.0
    assert data.threads_active > 0
    assert data.models_loaded["classifier"] is True
    assert data.models_loaded["anomaly_detector"] is True
    assert data.models_loaded["retrieval_service"] is True


def test_timing_middleware_header_injection():
    # 1. Custom request ID extraction
    incoming_headers = [
        (b"content-type", b"application/json"),
        (b"x-request-id", b"custom-trace-uuid-888"),
    ]
    req_id = TimingMiddleware.extract_or_generate_request_id(incoming_headers)
    assert req_id == "custom-trace-uuid-888"

    # 2. Fresh UUID generation when absent
    fresh_id = TimingMiddleware.extract_or_generate_request_id(
        [(b"host", b"localhost")]
    )
    assert fresh_id is not None
    assert len(fresh_id) >= 32

    # 3. Header attachment logic
    base_headers = [(b"content-length", b"42")]
    updated = TimingMiddleware.attach_timing_headers(
        base_headers, process_time=0.001234, request_id="req-123"
    )
    header_dict = {k.decode("utf-8"): v.decode("utf-8") for k, v in updated}

    assert "x-process-time" in header_dict
    assert header_dict["x-process-time"] == "0.001234s"
    assert header_dict["x-request-id"] == "req-123"
    assert header_dict["content-length"] == "42"


def test_get_classifier_success(mock_request):
    classifier = get_classifier(mock_request)
    assert classifier is not None
    assert len(classifier.classes) == 7


def test_get_anomaly_detector_success(mock_request):
    detector = get_anomaly_detector(mock_request)
    assert detector is not None
    assert len(detector.feature_names) == 10


def test_get_retrieval_service_success(mock_request):
    service = get_retrieval_service(mock_request)
    assert service is not None


def test_get_classifier_raises_503_when_unavailable():
    req = MagicMock(spec=Request)
    req.app = MagicMock()
    mock_container = MagicMock(spec=ServiceContainer)
    mock_container.classifier = None
    mock_container.status_flags = {"classifier": False}
    req.app.state.services = mock_container

    with pytest.raises(HTTPException) as exc_info:
        get_classifier(req)
    assert exc_info.value.status_code == 503


def test_app_routes_registered():
    app = create_app()
    assert app.title == "Insurance Claims Intelligence Platform - API Gateway"

    openapi_paths = list(app.openapi()["paths"].keys())
    assert "/api/v1/health" in openapi_paths
    assert "/api/v1/ready" in openapi_paths
    assert "/api/v1/metrics" in openapi_paths
    assert "/health" in openapi_paths

    # Root web portal route check
    route_paths = [getattr(r, "path", "") for r in app.routes]
    assert "/" in route_paths
