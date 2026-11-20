"""
Insurance Claims Intelligence Platform — Real-Time Anomaly & Fraud Inference Engine
Component: ml/anomaly_detection/predict.py

Provides production inference wrapper for evaluating insurance claims against
the trained Isolation Forest anomaly detection pipeline with explainable risk factors.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from pydantic import BaseModel, Field

from ml.anomaly_detection.features import CategoryStats

logger = logging.getLogger("ml.anomaly_detection.predict")

DEFAULT_MODEL_PATH = Path("ml/artifacts/isolation_forest_anomaly.joblib")


class AnomalyResult(BaseModel):
    """Pydantic model representing an anomaly risk assessment."""

    is_anomaly: bool = Field(..., description="True if claim is identified as a statistical anomaly")
    risk_score: float = Field(..., description="Calibrated risk score between 0.0 (safest) and 100.0 (highest risk)")
    risk_tier: str = Field(..., description="Risk tier classification: LOW, MEDIUM, HIGH, or CRITICAL")
    raw_anomaly_score: float = Field(..., description="Raw decision function score from Isolation Forest")
    risk_factors: list[str] = Field(default_factory=list, description="Rule-based explainability factors driving risk")
    feature_values: dict[str, float] = Field(default_factory=dict, description="Engineered features used by model")


class ClaimAnomalyDetector:
    """Production inference engine for unsupervised insurance claim fraud and anomaly detection."""

    def __init__(self, model_path: Path | str = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Anomaly model artifact not found at {self.model_path}")

        payload = joblib.load(self.model_path)
        self.pipeline = payload["pipeline"]
        self.feature_names: list[str] = payload["feature_names"]
        self.category_stats = CategoryStats.from_dict(payload["category_stats"])
        self.calibration = payload.get("score_calibration", {"score_min": -0.15, "score_max": 0.20})
        self.metadata: dict[str, Any] = payload.get("metadata", {})

        logger.info("ClaimAnomalyDetector initialized from %s", self.model_path)

    def evaluate_claim(
        self,
        claim_amount: float,
        claim_category: str,
        incident_date: str,
        filing_date: str,
        policy_start_date: str,
        coverage_limit: float,
        credit_score: float = 700.0,
    ) -> AnomalyResult:
        """Evaluate a single claim against the trained anomaly model."""
        import pandas as pd

        # Extract features
        inc_dt = pd.to_datetime(incident_date)
        fil_dt = pd.to_datetime(filing_date)
        pol_dt = pd.to_datetime(policy_start_date)

        filing_lag = max(0, (fil_dt - inc_dt).days)
        days_since_start = max(0, (inc_dt - pol_dt).days)
        early_filing = 1.0 if days_since_start <= 7 else 0.0

        cov_limit = max(coverage_limit, 1.0)
        ratio = claim_amount / cov_limit
        exceeds_cov = 1.0 if ratio > 1.0 else 0.0

        is_round = 1.0 if (claim_amount % 1000 == 0 and claim_amount >= 10000) else 0.0

        cat_mean = self.category_stats.means.get(claim_category, claim_amount)
        cat_std = self.category_stats.stds.get(claim_category, 1.0)
        zscore = (claim_amount - cat_mean) / cat_std

        features_dict = {
            "claim_amount": float(claim_amount),
            "coverage_limit": float(coverage_limit),
            "claim_to_coverage_ratio": float(ratio),
            "exceeds_coverage_flag": float(exceeds_cov),
            "days_since_policy_start": float(days_since_start),
            "early_filing_flag": float(early_filing),
            "filing_lag_days": float(filing_lag),
            "is_round_amount": float(is_round),
            "category_amount_zscore": float(zscore),
            "credit_score": float(credit_score),
        }

        X = pd.DataFrame([features_dict])[self.feature_names]

        # Scaler + Decision function
        scaled_X = self.pipeline.named_steps["scaler"].transform(X)
        model = self.pipeline.named_steps["model"]
        raw_score = float(-model.decision_function(scaled_X)[0])
        pred_label = int(model.predict(scaled_X)[0])  # -1 for anomaly, 1 for normal

        # Calibrate raw score to 0-100 scale
        s_min = self.calibration["score_min"]
        s_max = self.calibration["score_max"]
        denom = s_max - s_min if s_max != s_min else 1.0
        norm_score = float(np.clip(((raw_score - s_min) / denom) * 100.0, 0.0, 100.0))

        # Risk tier assignment
        if norm_score >= 80.0:
            risk_tier = "CRITICAL"
        elif norm_score >= 65.0:
            risk_tier = "HIGH"
        elif norm_score >= 45.0:
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        is_anomaly = (pred_label == -1) or (norm_score >= 65.0)

        # Rule-based explainability factors
        factors: list[str] = []
        if exceeds_cov:
            factors.append(f"Claim exceeds policy coverage limit (Ratio: {ratio:.2f}x)")
        if early_filing:
            factors.append(f"Early filing: Claim incident occurred {days_since_start} days after policy inception")
        if is_round:
            factors.append(f"Suspiciously round claim amount (${claim_amount:,.2f})")
        if zscore >= 2.0:
            factors.append(f"Statistical category outlier (Z-Score: +{zscore:.2f} vs {claim_category} baseline)")
        if credit_score < 600:
            factors.append(f"Adverse credit profile ({int(credit_score)}) combined with high claim ratio")

        return AnomalyResult(
            is_anomaly=is_anomaly,
            risk_score=round(norm_score, 2),
            risk_tier=risk_tier,
            raw_anomaly_score=round(raw_score, 4),
            risk_factors=factors,
            feature_values={k: round(v, 4) for k, v in features_dict.items()},
        )
