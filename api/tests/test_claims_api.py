"""Unit and Integration Tests for Claims Analysis and Adjudication API (ICIP-017)."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from api.app.routers.claims import analyze_claim, batch_analyze_claims
from api.app.schemas.claims import BatchClaimAnalysisRequest, ClaimAnalysisRequest
from api.app.services.container import container


@pytest.fixture(scope="module")
def initialized_services():
    """Ensure ML models are initialized in singleton container."""
    container.initialize()
    return container


class TestClaimsAnalysisAPI:
    """Test suite for /api/v1/claims/analyze and batch endpoints."""

    def test_routine_auto_claim_straight_through_approval(self, initialized_services):
        today = date.today()
        req = ClaimAnalysisRequest(
            claim_id="CLM-TEST-001",
            claim_text="Rear passenger bumper scratched and taillight cracked during parking maneuver at grocery store.",
            claim_amount=1450.00,
            coverage_limit=50000.00,
            incident_date=(today - timedelta(days=3)).isoformat(),
            filing_date=today.isoformat(),
            policy_start_date=(today - timedelta(days=250)).isoformat(),
            credit_score=750.0,
        )

        res = analyze_claim(
            request=req,
            classifier=container.classifier,
            anomaly_detector=container.anomaly_detector,
        )

        assert res.success is True
        data = res.data
        assert data.claim_id == "CLM-TEST-001"
        assert data.classification.predicted_category == "Auto"
        assert data.classification.confidence >= 0.50
        assert data.anomaly_assessment.risk_tier == "LOW"
        assert data.adjudication.action == "AUTO_APPROVE"
        assert data.adjudication.requires_supervisor_approval is False
        assert data.latency_ms > 0.0

    def test_claim_exceeding_coverage_triggers_fraud_flag(self, initialized_services):
        today = date.today()
        req = ClaimAnalysisRequest(
            claim_id="CLM-EXCEED-002",
            claim_text="Vehicle completely submerged in flash flood water, complete total loss.",
            claim_amount=65000.00,
            coverage_limit=25000.00,  # Claim exceeds limit by 2.6x
            incident_date=(today - timedelta(days=2)).isoformat(),
            filing_date=today.isoformat(),
            policy_start_date=(today - timedelta(days=120)).isoformat(),
        )

        res = analyze_claim(
            request=req,
            classifier=container.classifier,
            anomaly_detector=container.anomaly_detector,
        )

        assert res.success is True
        data = res.data
        assert data.adjudication.action == "FRAUD_INVESTIGATION_FLAG"
        assert data.adjudication.requires_supervisor_approval is True
        reasons_text = " ".join(data.adjudication.reasons)
        assert (
            "exceeds policy coverage limit" in reasons_text.lower()
            or "limit" in reasons_text.lower()
        )

    def test_early_filing_round_number_anomaly_flag(self, initialized_services):
        today = date.today()
        pol_start = today - timedelta(days=3)  # Policy only 3 days old!
        inc_date = today - timedelta(days=1)  # Incident within 2 days!

        req = ClaimAnalysisRequest(
            claim_id="CLM-EARLY-003",
            claim_text="Water damage completely ruined living room hardwood floors and structural drywall.",
            claim_amount=40000.00,  # Round high number
            coverage_limit=50000.00,
            incident_date=inc_date.isoformat(),
            filing_date=today.isoformat(),
            policy_start_date=pol_start.isoformat(),
            credit_score=520.0,  # Low credit
        )

        res = analyze_claim(
            request=req,
            classifier=container.classifier,
            anomaly_detector=container.anomaly_detector,
        )

        assert res.success is True
        data = res.data
        assert data.anomaly_assessment.risk_score >= 60.0
        assert data.adjudication.action in ("FRAUD_INVESTIGATION_FLAG", "MANUAL_AUDIT")

    def test_ambiguous_narrative_triggers_manual_audit(self, initialized_services):
        today = date.today()
        req = ClaimAnalysisRequest(
            claim_id="CLM-AMBIG-004",
            claim_text="General issue happened at premises and things were broken.",
            claim_amount=3200.00,
            coverage_limit=50000.00,
            incident_date=(today - timedelta(days=5)).isoformat(),
            filing_date=today.isoformat(),
            policy_start_date=(today - timedelta(days=200)).isoformat(),
        )

        res = analyze_claim(
            request=req,
            classifier=container.classifier,
            anomaly_detector=container.anomaly_detector,
        )

        assert res.success is True
        data = res.data
        assert data.adjudication.action in ("MANUAL_AUDIT", "FAST_TRACK_REVIEW")

    def test_batch_claim_analysis_aggregation(self, initialized_services):
        date.today()
        batch_req = BatchClaimAnalysisRequest(
            claims=[
                ClaimAnalysisRequest(
                    claim_id="BATCH-001",
                    claim_text="Windshield chipped by road debris on interstate highway.",
                    claim_amount=450.00,
                    coverage_limit=50000.00,
                ),
                ClaimAnalysisRequest(
                    claim_id="BATCH-002",
                    claim_text="Roof tiles blown off during severe windstorm.",
                    claim_amount=3200.00,
                    coverage_limit=100000.00,
                ),
                ClaimAnalysisRequest(
                    claim_id="BATCH-003",
                    claim_text="Stolen sports car reported stolen immediately after policy binding.",
                    claim_amount=95000.00,
                    coverage_limit=50000.00,
                ),
            ]
        )

        batch_res = batch_analyze_claims(
            batch=batch_req,
            classifier=container.classifier,
            anomaly_detector=container.anomaly_detector,
        )

        assert batch_res.success is True
        bdata = batch_res.data
        assert bdata.total_claims == 3
        assert len(bdata.results) == 3
        assert bdata.average_risk_score > 0.0
        assert "FRAUD_INVESTIGATION_FLAG" in bdata.action_summary
        assert bdata.total_latency_ms > 0.0

    def test_request_validation_enforces_positive_amounts(self):
        with pytest.raises(ValidationError):
            ClaimAnalysisRequest(
                claim_text="Short",  # Min length is 5
                claim_amount=-500.00,  # Negative amount rejected
                coverage_limit=10000.00,
            )
