"""Pydantic v2 Schemas for Claims Analysis and Adjudication API."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel, Field, field_validator


class ClaimAnalysisRequest(BaseModel):
    """Payload for submitting an insurance claim for real-time ML analysis and adjudication."""

    claim_id: str | None = Field(
        default=None, description="External claim reference or identifier"
    )
    claim_text: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Free-form claim incident description, claimant narrative, or adjuster notes",
        examples=[
            "Rear bumper dented and taillight shattered during parking lot collision."
        ],
    )
    claim_amount: float = Field(
        ...,
        ge=0.0,
        description="Total monetary claim amount requested in USD",
        examples=[1850.00],
    )
    coverage_limit: float = Field(
        ...,
        gt=0.0,
        description="Applicable maximum policy coverage limit in USD",
        examples=[50000.00],
    )
    incident_date: str | None = Field(
        default=None,
        description="Incident occurrence date in YYYY-MM-DD format (defaults to 5 days prior to filing)",
    )
    filing_date: str | None = Field(
        default=None,
        description="Claim submission date in YYYY-MM-DD format (defaults to current date)",
    )
    policy_start_date: str | None = Field(
        default=None,
        description="Policy effective start date in YYYY-MM-DD format (defaults to 180 days prior)",
    )
    credit_score: float = Field(
        default=700.0,
        ge=300.0,
        le=850.0,
        description="Claimant FICO/credit score (300 to 850)",
    )

    @field_validator("claim_amount", "coverage_limit")
    @classmethod
    def round_amounts(cls, v: float) -> float:
        return round(float(v), 2)

    def resolve_dates(self) -> tuple[str, str, str]:
        """Resolve default dates if omitted by client."""
        today = date.today()
        filing = self.filing_date or today.isoformat()
        incident = self.incident_date or (today - timedelta(days=5)).isoformat()
        pol_start = self.policy_start_date or (today - timedelta(days=180)).isoformat()
        return str(incident), str(filing), str(pol_start)


class ClassificationDetail(BaseModel):
    """NLP text classification output breakdown."""

    predicted_category: str = Field(
        ..., description="Top predicted claim domain category"
    )
    confidence: float = Field(
        ...,
        description="Softmax confidence probability for predicted category [0.0 - 1.0]",
    )
    all_probabilities: dict[str, float] = Field(
        ..., description="Probabilities across all claim classes"
    )
    cleaned_text: str = Field(
        ..., description="Sanitized and normalized text analyzed by TF-IDF model"
    )
    is_fallback: bool = Field(
        default=False,
        description="True if input text lacked signal and triggered fallback",
    )


class AnomalyDetail(BaseModel):
    """Unsupervised Isolation Forest anomaly & fraud assessment."""

    risk_score: float = Field(
        ...,
        description="Calibrated risk index between 0.0 (safest) and 100.0 (highest risk)",
    )
    risk_tier: str = Field(..., description="Risk tier: LOW, MEDIUM, HIGH, or CRITICAL")
    is_anomaly: bool = Field(
        ..., description="Statistical anomaly detection boolean flag"
    )
    raw_anomaly_score: float = Field(
        ..., description="Raw Isolation Forest decision function score"
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Specific risk drivers triggering fraud alerts",
    )
    feature_values: dict[str, float] = Field(
        default_factory=dict, description="Numerical features fed into model"
    )


class AdjudicationDecision(BaseModel):
    """Automated underwriting & adjudication recommendation."""

    action: str = Field(
        ...,
        description="Recommended action: AUTO_APPROVE, FAST_TRACK_REVIEW, MANUAL_AUDIT, FRAUD_INVESTIGATION_FLAG",
    )
    confidence_score: float = Field(
        ..., description="Composite decision confidence [0.0 - 1.0]"
    )
    reasons: list[str] = Field(
        ..., description="Detailed business logic adjudication reasoning"
    )
    requires_supervisor_approval: bool = Field(
        default=False,
        description="True if claim exceeds auto-adjudication thresholds or triggers compliance flags",
    )


class ClaimAnalysisResponse(BaseModel):
    """Unified response containing multi-model inference and automated adjudication."""

    claim_id: str | None = Field(default=None, description="External claim reference")
    classification: ClassificationDetail = Field(
        ..., description="NLP classification model output"
    )
    anomaly_assessment: AnomalyDetail = Field(
        ..., description="Fraud risk and anomaly scoring"
    )
    adjudication: AdjudicationDecision = Field(
        ..., description="Actionable adjudication decision"
    )
    latency_ms: float = Field(
        ..., description="Total pipeline execution latency in milliseconds"
    )
    processed_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of analysis completion",
    )


class BatchClaimAnalysisRequest(BaseModel):
    """Batch analysis request containing up to 50 claims."""

    claims: list[ClaimAnalysisRequest] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of insurance claims to evaluate concurrently",
    )


class BatchClaimAnalysisResponse(BaseModel):
    """Batch adjudication summary and individual results."""

    total_claims: int = Field(..., description="Total claims processed in batch")
    results: list[ClaimAnalysisResponse] = Field(
        ..., description="Individual claim evaluation results"
    )
    action_summary: dict[str, int] = Field(
        ..., description="Counts of claims categorized by adjudication action"
    )
    average_risk_score: float = Field(
        ..., description="Mean fraud risk score across batch"
    )
    total_latency_ms: float = Field(
        ..., description="Total batch execution time in milliseconds"
    )
