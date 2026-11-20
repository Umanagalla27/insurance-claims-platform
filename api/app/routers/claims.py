"""Claims Analysis and Automated Adjudication Endpoints."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from api.app.schemas.claims import (
    AnomalyDetail,
    BatchClaimAnalysisRequest,
    BatchClaimAnalysisResponse,
    ClaimAnalysisRequest,
    ClaimAnalysisResponse,
    ClassificationDetail,
)
from api.app.schemas.common import ApiResponse
from api.app.services.adjudicator import ClaimsAdjudicator
from api.app.services.container import get_anomaly_detector, get_classifier
from api.app.services.metrics import metrics_collector
from ml.anomaly_detection.predict import ClaimAnomalyDetector
from ml.classification.predict import ClaimClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["Claims Intelligence & Adjudication"])


@router.post(
    "/analyze",
    response_model=ApiResponse[ClaimAnalysisResponse],
    summary="Analyze Single Claim",
    description=(
        "Executes end-to-end multi-model inference on a single insurance claim. "
        "Runs TF-IDF NLP text classification, Isolation Forest unsupervised fraud scoring, "
        "and policy underwriting rules to return a binding adjudication decision."
    ),
)
def analyze_claim(
    request: ClaimAnalysisRequest,
    classifier: ClaimClassifier = Depends(get_classifier),
    anomaly_detector: ClaimAnomalyDetector = Depends(get_anomaly_detector),
) -> ApiResponse[ClaimAnalysisResponse]:
    """Execute real-time multi-model claim evaluation."""
    start_time = time.perf_counter()

    # 1. NLP Text Classification
    clf_res = classifier.predict(request.claim_text)

    # 2. Resolve Dates and Run Unsupervised Anomaly Scoring
    inc_dt, fil_dt, pol_dt = request.resolve_dates()
    anom_res = anomaly_detector.evaluate_claim(
        claim_amount=request.claim_amount,
        claim_category=clf_res.predicted_category,
        incident_date=inc_dt,
        filing_date=fil_dt,
        policy_start_date=pol_dt,
        coverage_limit=request.coverage_limit,
        credit_score=request.credit_score,
    )

    # 3. Adjudication Rules Engine
    adjudication = ClaimsAdjudicator.evaluate(
        request=request,
        classification=clf_res,
        anomaly=anom_res,
    )

    # 4. Record Prometheus Domain Metrics
    try:
        metrics_collector.record_claim_adjudication(
            category=clf_res.predicted_category,
            outcome=adjudication.action,
        )
        if anom_res.is_anomaly or adjudication.action == "FRAUD_INVESTIGATION_FLAG":
            metrics_collector.record_fraud_detected(category=clf_res.predicted_category)

        if adjudication.action == "AUTO_APPROVE" and not adjudication.requires_supervisor_approval:
            metrics_collector.record_stp_approval()
    except Exception as exc:
        logger.warning("Failed to record Prometheus metrics for claim: %s", exc)

    total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    response_payload = ClaimAnalysisResponse(
        claim_id=request.claim_id,
        classification=ClassificationDetail(
            predicted_category=clf_res.predicted_category,
            confidence=round(clf_res.confidence, 4),
            all_probabilities={
                k: round(v, 4) for k, v in clf_res.all_probabilities.items()
            },
            cleaned_text=clf_res.cleaned_text,
            is_fallback=clf_res.is_fallback,
        ),
        anomaly_assessment=AnomalyDetail(
            risk_score=round(anom_res.risk_score, 2),
            risk_tier=anom_res.risk_tier,
            is_anomaly=anom_res.is_anomaly,
            raw_anomaly_score=round(anom_res.raw_anomaly_score, 4),
            risk_factors=anom_res.risk_factors,
            feature_values={k: round(v, 4) for k, v in anom_res.feature_values.items()},
        ),
        adjudication=adjudication,
        latency_ms=total_latency_ms,
        processed_at=datetime.now(UTC).isoformat(),
    )

    return ApiResponse(
        success=True,
        data=response_payload,
        message=f"Claim evaluated successfully in {total_latency_ms}ms: {adjudication.action}",
    )


@router.post(
    "/batch-analyze",
    response_model=ApiResponse[BatchClaimAnalysisResponse],
    summary="Batch Analyze Claims",
    description="Processes up to 50 claims sequentially, returning summary distributions and individual adjudication decisions.",
)
def batch_analyze_claims(
    batch: BatchClaimAnalysisRequest,
    classifier: ClaimClassifier = Depends(get_classifier),
    anomaly_detector: ClaimAnomalyDetector = Depends(get_anomaly_detector),
) -> ApiResponse[BatchClaimAnalysisResponse]:
    """Execute batch multi-model claim evaluation."""
    start_time = time.perf_counter()

    results: list[ClaimAnalysisResponse] = []
    action_counts: dict[str, int] = {}
    total_risk: float = 0.0

    for req in batch.claims:
        single_res = analyze_claim(
            request=req,
            classifier=classifier,
            anomaly_detector=anomaly_detector,
        )
        data = single_res.data
        results.append(data)
        action_counts[data.adjudication.action] = (
            action_counts.get(data.adjudication.action, 0) + 1
        )
        total_risk += data.anomaly_assessment.risk_score

    batch_latency = round((time.perf_counter() - start_time) * 1000.0, 2)
    avg_risk = round(total_risk / len(results), 2) if results else 0.0

    batch_payload = BatchClaimAnalysisResponse(
        total_claims=len(results),
        results=results,
        action_summary=action_counts,
        average_risk_score=avg_risk,
        total_latency_ms=batch_latency,
    )

    return ApiResponse(
        success=True,
        data=batch_payload,
        message=f"Batch processed {len(results)} claims in {batch_latency}ms",
    )
