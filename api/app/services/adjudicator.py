"""Automated Claims Adjudication Decision Engine.

Evaluates combined signals from NLP text classification, Isolation Forest fraud
anomaly detection, and policy coverage parameters to synthesize a binding,
transparent adjudication recommendation (AUTO_APPROVE, FAST_TRACK, MANUAL_AUDIT, FRAUD_FLAG).
"""

from __future__ import annotations

from api.app.schemas.claims import AdjudicationDecision, ClaimAnalysisRequest
from ml.anomaly_detection.predict import AnomalyResult
from ml.classification.predict import PredictionResult


class ClaimsAdjudicator:
    """Enterprise policy rules engine for claims adjudication."""

    AUTO_APPROVE_MAX_AMOUNT: float = 5000.00
    AUTO_APPROVE_MAX_RISK: float = 25.0
    AUTO_APPROVE_MIN_CONFIDENCE: float = 0.50
    AUTO_APPROVE_MAX_COVERAGE_RATIO: float = 0.80

    MANUAL_AUDIT_RISK_THRESHOLD: float = 45.0
    FRAUD_INVESTIGATION_RISK_THRESHOLD: float = 70.0

    @classmethod
    def evaluate(
        cls,
        request: ClaimAnalysisRequest,
        classification: PredictionResult,
        anomaly: AnomalyResult,
    ) -> AdjudicationDecision:
        """Synthesize multi-model outputs into a single actionable decision."""
        reasons: list[str] = []
        action: str
        requires_supervisor: bool = False

        ratio = request.claim_amount / max(request.coverage_limit, 1.0)
        risk_score = anomaly.risk_score
        confidence = classification.confidence

        # Rule 1: Hard policy violation or critical fraud risk
        if ratio > 1.0:
            action = "FRAUD_INVESTIGATION_FLAG"
            requires_supervisor = True
            reasons.append(
                f"Requested claim amount (${request.claim_amount:,.2f}) strictly exceeds policy coverage limit (${request.coverage_limit:,.2f})."
            )
        elif (
            anomaly.risk_tier == "CRITICAL"
            or risk_score >= cls.FRAUD_INVESTIGATION_RISK_THRESHOLD
        ):
            action = "FRAUD_INVESTIGATION_FLAG"
            requires_supervisor = True
            reasons.append(
                f"Critical statistical anomaly detected (Risk Score: {risk_score:.1f}/100, Tier: {anomaly.risk_tier})."
            )
            for rf in anomaly.risk_factors:
                reasons.append(f"Flagged Factor: {rf}")

        # Rule 2: Multiple risk indicators or high risk
        elif (
            len(anomaly.risk_factors) >= 2
            or risk_score >= cls.MANUAL_AUDIT_RISK_THRESHOLD
        ):
            action = "MANUAL_AUDIT"
            reasons.append(
                f"Moderate-to-high risk profile (Risk Score: {risk_score:.1f}/100) necessitates full human adjuster audit."
            )
            for rf in anomaly.risk_factors:
                reasons.append(f"Contributing Risk Factor: {rf}")

        # Rule 3: Text classification ambiguity
        elif confidence < 0.50 or classification.is_fallback:
            action = "MANUAL_AUDIT"
            reasons.append(
                f"Claim incident description exhibits low model confidence ({confidence:.1%}) or ambiguous language."
            )

        # Rule 4: Straight-Through Processing (STP) Auto-Approval
        elif (
            risk_score < cls.AUTO_APPROVE_MAX_RISK
            and confidence >= cls.AUTO_APPROVE_MIN_CONFIDENCE
            and request.claim_amount <= cls.AUTO_APPROVE_MAX_AMOUNT
            and ratio <= cls.AUTO_APPROVE_MAX_COVERAGE_RATIO
        ):
            action = "AUTO_APPROVE"
            reasons.append(
                f"Clean risk profile (Risk Score: {risk_score:.1f}/100, Tier: {anomaly.risk_tier}) "
                f"with high classification certainty ({confidence:.1%} in category '{classification.predicted_category}')."
            )
            reasons.append(
                f"Claim amount (${request.claim_amount:,.2f}) is within automated straight-through settlement limit (${cls.AUTO_APPROVE_MAX_AMOUNT:,.2f})."
            )

        # Rule 5: Low-to-moderate standard claims eligible for accelerated review
        else:
            action = "FAST_TRACK_REVIEW"
            reasons.append(
                f"Claim satisfies standard underwriting guidelines (Risk: {risk_score:.1f}/100, Coverage Ratio: {ratio:.1%})."
            )
            reasons.append("Eligible for Fast-Track Adjuster sign-off.")

        # Composite decision confidence calculation
        comp_confidence = round(
            (confidence * 0.45) + ((1.0 - (risk_score / 100.0)) * 0.55),
            4,
        )

        return AdjudicationDecision(
            action=action,
            confidence_score=comp_confidence,
            reasons=reasons,
            requires_supervisor_approval=requires_supervisor,
        )
