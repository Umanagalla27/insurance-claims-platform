"""Automated Pytest Suite for Production Telemetry, Prometheus Metrics, and CloudWatch Dashboards (ICIP-028).

Validates:
1. Kubernetes/ALB Liveness and Readiness probes (/health, /health/live, /ready, /health/ready).
2. Prometheus text exposition format (version 0.0.4) at /metrics.
3. Domain counters (claims adjudication, fraud detection, STP approvals, RAG queries).
4. System telemetry gauges (uptime, memory RSS, threads, subsystem readiness flags).
5. Prometheus alert rules configuration syntax and threshold integrity.
6. CloudWatch operational dashboard Terraform specifications.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from starlette.requests import Request
from starlette.responses import Response

from api.app.main import create_app
from api.app.routers.health import (
    health_check,
    prometheus_metrics,
    readiness_check,
)
from api.app.services.container import ServiceContainer, container
from api.app.services.metrics import MetricsCollector

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def initialized_container():
    """Module-level initialized services container."""
    container.initialize()
    return container


@pytest.fixture
def fresh_metrics():
    """Provide a clean metrics collector registry for isolated test runs."""
    collector = MetricsCollector()
    return collector


@pytest.fixture
def mock_request(initialized_container):
    """Mock HTTP request with pre-warmed service state."""
    req = MagicMock(spec=Request)
    req.app = MagicMock()
    req.app.state.services = initialized_container
    req.state.request_id = "test-monitoring-uuid-001"
    req.headers = {"accept": "text/plain; version=0.0.4"}
    return req


# ==============================================================================
# 1. Health & Readiness Probe Tests
# ==============================================================================


def test_liveness_probes():
    """Verify /health and /health/live return 200 OK with healthy status."""
    result = health_check()
    assert result.success is True
    assert result.data.status == "healthy"
    assert "Insurance Claims" in result.data.service
    assert result.data.version == "1.0.0"


def test_readiness_probe_all_systems_ready(mock_request):
    """Verify readiness returns 200 and all subsystems are marked ready."""
    response = Response()
    result = readiness_check(mock_request, response)
    assert result.success is True
    assert result.data.status == "ready"
    assert response.status_code == 200

    components = {c.component: c for c in result.data.components}
    assert components["nlp_text_classifier"].status == "ready"
    assert components["isolation_forest_anomaly"].status == "ready"
    assert components["policy_vector_store"].status == "ready"


def test_readiness_probe_degraded_returns_503():
    """Verify readiness returns 503 when a subsystem is unavailable."""
    req = MagicMock(spec=Request)
    req.app = MagicMock()
    degraded = ServiceContainer()
    degraded.status_flags = {
        "classifier": False,
        "anomaly_detector": True,
        "retrieval_service": True,
    }
    req.app.state.services = degraded
    response = Response()

    result = readiness_check(req, response)
    assert result.success is False
    assert result.data.status == "degraded"
    assert response.status_code == 503


# ==============================================================================
# 2. Prometheus Metrics Telemetry Tests
# ==============================================================================


def test_metrics_collector_domain_counters(fresh_metrics):
    """Verify claim adjudication, fraud, and STP metric increments."""
    fresh_metrics.record_claim_adjudication(category="AUTO", outcome="APPROVE")
    fresh_metrics.record_claim_adjudication(category="AUTO", outcome="FAST_TRACK")
    fresh_metrics.record_claim_adjudication(category="PROPERTY", outcome="REJECT")
    fresh_metrics.record_fraud_detected(category="PROPERTY")
    fresh_metrics.record_stp_approval()
    fresh_metrics.record_stp_approval()

    output = fresh_metrics.export_prometheus_text()

    assert 'claims_adjudicated_total{category="AUTO",outcome="APPROVE"} 1.0' in output
    assert (
        'claims_adjudicated_total{category="AUTO",outcome="FAST_TRACK"} 1.0' in output
    )
    assert (
        'claims_adjudicated_total{category="PROPERTY",outcome="REJECT"} 1.0' in output
    )
    assert 'claims_fraud_detected_total{category="PROPERTY"} 1.0' in output
    assert "claims_stp_approved_total 2.0" in output


def test_metrics_collector_rag_queries(fresh_metrics):
    """Verify RAG query metric counters with cache hit labels."""
    fresh_metrics.record_rag_query(status="success", cache_hit=True)
    fresh_metrics.record_rag_query(status="success", cache_hit=False)
    fresh_metrics.record_rag_query(status="error", cache_hit=False)

    output = fresh_metrics.export_prometheus_text()

    assert 'rag_queries_total{cache_hit="true",status="success"} 1.0' in output
    assert 'rag_queries_total{cache_hit="false",status="success"} 1.0' in output
    assert 'rag_queries_total{cache_hit="false",status="error"} 1.0' in output


def test_metrics_collector_http_request_histogram(fresh_metrics):
    """Verify HTTP ingress requests and latency histogram observation."""
    fresh_metrics.record_http_request(
        method="POST",
        endpoint="/api/v1/claims/analyze",
        status_code=200,
        duration_seconds=0.035,
    )

    output = fresh_metrics.export_prometheus_text()

    assert (
        'http_requests_total{endpoint="/api/v1/claims/analyze",method="POST",status_code="200"} 1.0'
        in output
    )
    assert (
        'http_request_duration_seconds_bucket{endpoint="/api/v1/claims/analyze",le="0.05",method="POST"} 1.0'
        in output
    )


def test_metrics_collector_system_gauges(fresh_metrics):
    """Verify system telemetry gauges update correctly."""
    fresh_metrics.update_system_metrics(
        uptime_seconds=3600.5,
        memory_rss_bytes=104857600.0,
        active_threads=8,
        model_flags={
            "classifier": True,
            "anomaly_detector": True,
            "retrieval_service": False,
        },
    )

    output = fresh_metrics.export_prometheus_text()

    assert "app_uptime_seconds 3600.5" in output
    assert "process_memory_rss_bytes" in output
    assert "process_active_threads 8.0" in output
    assert 'subsystem_readiness_status{subsystem="classifier"} 1.0' in output
    assert 'subsystem_readiness_status{subsystem="anomaly_detector"} 1.0' in output
    assert 'subsystem_readiness_status{subsystem="retrieval_service"} 0.0' in output


def test_prometheus_metrics_endpoint_exposition(mock_request):
    """Verify GET /metrics returns valid Prometheus exposition text/plain."""
    response = Response()
    starlette_resp = prometheus_metrics(mock_request, response)

    assert "text/plain; version=0.0.4" in starlette_resp.media_type
    body = starlette_resp.body.decode("utf-8")

    assert "# HELP http_requests_total" in body
    assert "# TYPE http_requests_total counter" in body
    assert "# HELP claims_adjudicated_total" in body
    assert "# HELP app_uptime_seconds" in body
    assert "# HELP process_memory_rss_bytes" in body


def test_prometheus_metrics_json_content_negotiation(mock_request):
    """Verify GET /metrics returns JSON when client explicitly requests application/json."""
    mock_request.headers = {"accept": "application/json"}
    response = Response()
    starlette_resp = prometheus_metrics(mock_request, response)

    body = json.loads(starlette_resp.body.decode("utf-8"))
    assert body["success"] is True
    assert "uptime_seconds" in body["data"]
    assert "threads_active" in body["data"]


def test_routes_mounted_in_fastapi_app():
    """Verify /health/live, /health/ready, /metrics, /metrics/json are registered in OpenAPI schema."""
    app = create_app()
    paths = set(app.openapi()["paths"].keys())

    assert "/api/v1/health" in paths
    assert "/api/v1/health/live" in paths
    assert "/api/v1/ready" in paths
    assert "/api/v1/health/ready" in paths
    assert "/api/v1/metrics" in paths
    assert "/api/v1/metrics/json" in paths


# ==============================================================================
# 3. Prometheus Alert Rules Validation
# ==============================================================================


def test_prometheus_alert_rules_yaml_syntax():
    """Verify monitoring/alerts/prometheus_alerts.yml conforms to Prometheus Alertmanager spec."""
    alerts_path = PROJECT_ROOT / "monitoring" / "alerts" / "prometheus_alerts.yml"
    assert alerts_path.is_file(), f"Missing alert rules file at {alerts_path}"

    with open(alerts_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "groups" in data
    group = data["groups"][0]
    assert group["name"] == "icip_platform_alerts"
    assert len(group["rules"]) >= 5

    rule_names = {r["alert"] for r in group["rules"]}
    expected_rules = {
        "HighRequestLatency",
        "HighErrorRateSpike",
        "MLSubsystemDown",
        "LowStraightThroughProcessingRate",
        "HighMemoryUtilization",
    }
    assert expected_rules.issubset(rule_names)

    for rule in group["rules"]:
        assert "expr" in rule
        assert "for" in rule
        assert "labels" in rule
        assert "severity" in rule["labels"]
        assert "annotations" in rule
        assert "summary" in rule["annotations"]
        assert "runbook_url" in rule["annotations"]


# ==============================================================================
# 4. Terraform CloudWatch Dashboard Validation
# ==============================================================================


def test_terraform_cloudwatch_dashboard_resource():
    """Verify Terraform CloudWatch module configures the executive & operational dashboard."""
    cw_main = (
        PROJECT_ROOT
        / "infrastructure"
        / "terraform"
        / "modules"
        / "cloudwatch"
        / "main.tf"
    )
    cw_outputs = (
        PROJECT_ROOT
        / "infrastructure"
        / "terraform"
        / "modules"
        / "cloudwatch"
        / "outputs.tf"
    )
    root_outputs = PROJECT_ROOT / "infrastructure" / "terraform" / "outputs.tf"

    main_text = cw_main.read_text(encoding="utf-8")
    assert "aws_cloudwatch_dashboard" in main_text
    assert "platform_overview" in main_text
    assert "EC2 API Gateway Node Performance" in main_text
    assert "Serverless Claims Ingestion Lambda" in main_text

    cw_out_text = cw_outputs.read_text(encoding="utf-8")
    assert "output \"dashboard_name\"" in cw_out_text
    assert "output \"dashboard_arn\"" in cw_out_text

    root_out_text = root_outputs.read_text(encoding="utf-8")
    assert "output \"cloudwatch_dashboard_name\"" in root_out_text
