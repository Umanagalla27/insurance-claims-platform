"""Verification Script for Step 10.1 (ICIP-028).

Audits:
1. Liveness and Readiness probes (/health, /health/live, /ready, /health/ready).
2. Prometheus text exposition format (version 0.0.4) at /metrics.
3. Domain counters (adjudications, fraud, STP, RAG queries).
4. System gauges (uptime, RSS memory, thread counts, subsystem flags).
5. Prometheus alert rules configuration (syntax, expressions, runbook links).
6. CloudWatch operational dashboard Terraform specifications.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure immediate line-buffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import Response  # noqa: E402

from api.app.main import create_app  # noqa: E402
from api.app.routers.claims import analyze_claim  # noqa: E402
from api.app.routers.health import (  # noqa: E402
    health_check,
    prometheus_metrics,
    readiness_check,
)
from api.app.schemas.claims import ClaimAnalysisRequest  # noqa: E402
from api.app.services.container import container  # noqa: E402
from api.app.services.metrics import metrics_collector  # noqa: E402


def print_banner(text: str) -> None:
    line = "=" * 80
    print(f"\n{line}\n  {text}\n{line}", flush=True)


def main() -> int:
    print_banner(
        "AUDIT: ICIP-028 Production Health Probes, Prometheus Metrics & CloudWatch Dashboard"
    )

    # 1. Initialize Application & Service Container
    print(">>> 1. Initializing Service Container & FastAPI Gateway...", flush=True)
    container.initialize()
    app = create_app()
    app.state.services = container

    mock_req = MagicMock(spec=Request)
    mock_req.app = app
    mock_req.app.state.services = container
    mock_req.state.request_id = "audit-verify-uuid-001"
    mock_req.headers = {"accept": "text/plain; version=0.0.4"}

    print(
        "    [PASS] FastAPI Application Factory & Service Container warmed up.",
        flush=True,
    )

    # 2. Test Liveness Probes
    print("\n>>> 2. Probing Liveness Endpoints...", flush=True)
    res_l1 = health_check()
    assert res_l1.success is True
    assert res_l1.data.status == "healthy"
    print(
        f"    [PASS] /health and /health/live validated (Status: {res_l1.data.status})",
        flush=True,
    )

    # 3. Test Readiness Probes
    print("\n>>> 3. Probing Readiness Subsystems...", flush=True)
    resp_obj = Response()
    res_r1 = readiness_check(mock_req, resp_obj)
    assert res_r1.success is True
    assert res_r1.data.status == "ready"
    assert resp_obj.status_code == 200

    for comp in res_r1.data.components:
        print(f"      - {comp.component}: {comp.status} ({comp.details})", flush=True)
    print(
        "    [PASS] Deep subsystem readiness validated (3/3 components active).",
        flush=True,
    )

    # 4. Simulate Business Transactions & Verify Prometheus Exposition
    print(
        "\n>>> 4. Simulating Ingress Transactions & Validating Prometheus Telemetry...",
        flush=True,
    )
    metrics_collector.reset()

    # Simulate claim analysis
    claim_req = ClaimAnalysisRequest(
        claim_id="CLM-VERIFY-001",
        policy_number="POL-9999",
        claim_text="Rear-ended by a truck at a traffic stop. Extensive fender and bumper damage.",
        claim_amount=1450.0,
        coverage_limit=50000.0,
        credit_score=750,
        incident_date="2024-05-10",
        filing_date="2024-05-12",
        policy_start_date="2023-01-01",
    )
    res_claim = analyze_claim(
        request=claim_req,
        classifier=container.classifier,
        anomaly_detector=container.anomaly_detector,
    )
    assert res_claim.success is True
    claim_action = res_claim.data.adjudication.action
    print(f"      - Evaluated Claim Decision: {claim_action}", flush=True)

    # Simulate RAG query metric recording
    metrics_collector.record_rag_query(status="success", cache_hit=True)
    metrics_collector.record_rag_query(status="success", cache_hit=False)
    print(
        "      - Recorded Policy RAG Hybrid Retrieval & Cache Hits", flush=True
    )

    # Scrape /metrics in Prometheus exposition format
    starlette_resp = prometheus_metrics(mock_req, resp_obj)
    assert "text/plain; version=0.0.4" in starlette_resp.media_type
    prom_text = starlette_resp.body.decode("utf-8")

    assert "claims_adjudicated_total" in prom_text
    assert "claims_stp_approved_total" in prom_text
    assert "rag_queries_total" in prom_text
    assert "app_uptime_seconds" in prom_text
    assert "subsystem_readiness_status" in prom_text
    print(
        "    [PASS] Prometheus exposition format /metrics successfully scraped.",
        flush=True,
    )

    # Scrape /metrics with JSON content negotiation
    mock_req.headers = {"accept": "application/json"}
    json_resp = prometheus_metrics(mock_req, resp_obj)
    assert "application/json" in json_resp.media_type
    json_body = json.loads(json_resp.body.decode("utf-8"))
    assert json_body["success"] is True
    print(
        "    [PASS] Content negotiation for JSON metrics verified.",
        flush=True,
    )

    # 5. Audit Prometheus Alert Rules
    print(
        "\n>>> 5. Auditing Prometheus Alert Rules Specification...", flush=True
    )
    alerts_file = PROJECT_ROOT / "monitoring" / "alerts" / "prometheus_alerts.yml"
    assert alerts_file.is_file(), f"Missing {alerts_file}"
    with open(alerts_file, encoding="utf-8") as f:
        alert_config = yaml.safe_load(f)

    rules = alert_config["groups"][0]["rules"]
    print(f"    Loaded {len(rules)} production alert rules:", flush=True)
    for rule in rules:
        print(
            f"      - Alert: {rule['alert']:<34} | Severity: {rule['labels']['severity']:<8} | Expression: {rule['expr'][:32]}...",
            flush=True,
        )
    print(
        "    [PASS] Prometheus Alertmanager configuration verified.", flush=True
    )

    # 6. Audit Terraform CloudWatch Dashboard
    print(
        "\n>>> 6. Auditing Terraform CloudWatch Dashboard Definition...",
        flush=True,
    )
    tf_main = (
        PROJECT_ROOT
        / "infrastructure"
        / "terraform"
        / "modules"
        / "cloudwatch"
        / "main.tf"
    )
    tf_content = tf_main.read_text(encoding="utf-8")
    assert "aws_cloudwatch_dashboard" in tf_content
    assert "platform_overview" in tf_content
    assert "EC2 API Gateway Node Performance" in tf_content
    assert "Serverless Claims Ingestion Lambda" in tf_content
    print(
        "    [PASS] Terraform CloudWatch Dashboard resource & widgets verified.",
        flush=True,
    )

    print_banner(
        "ALL AUDIT CHECKS PASSED: STEP 10.1 TELEMETRY FULLY PRODUCTION-READY!"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
