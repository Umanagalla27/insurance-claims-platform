"""
Insurance Claims Intelligence Platform — Anomaly Feature Extraction Pipeline
Component: ml/anomaly_detection/features.py

Extracts multidimensional temporal, financial, and behavioral risk features
from joined claims, policy, and customer records for unsupervised anomaly detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger("ml.anomaly_detection.features")

FEATURE_NAMES: list[str] = [
    "claim_amount",
    "coverage_limit",
    "claim_to_coverage_ratio",
    "exceeds_coverage_flag",
    "days_since_policy_start",
    "early_filing_flag",
    "filing_lag_days",
    "is_round_amount",
    "category_amount_zscore",
    "credit_score",
]


@dataclass
class CategoryStats:
    """Historical mean and standard deviation per claim category for Z-score calculation."""

    means: dict[str, float] = field(default_factory=dict)
    stds: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"means": self.means, "stds": self.stds}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CategoryStats:
        return cls(means=data.get("means", {}), stds=data.get("stds", {}))


class AnomalyFeatureExtractor:
    """Extracts standardized anomaly features for training and inference."""

    def __init__(self, category_stats: CategoryStats | None = None) -> None:
        self.category_stats = category_stats or CategoryStats()

    def fit_category_stats(self, claims_df: pd.DataFrame) -> CategoryStats:
        """Calculate historical baseline mean and std for each claim category."""
        means = {}
        stds = {}
        for cat, group in claims_df.groupby("claim_category"):
            means[str(cat)] = float(group["claim_amount"].mean())
            std_val = float(group["claim_amount"].std())
            stds[str(cat)] = std_val if std_val > 0 else 1.0

        self.category_stats = CategoryStats(means=means, stds=stds)
        logger.info("Fitted category stats for %d categories", len(means))
        return self.category_stats

    def extract_training_features(
        self,
        claims_path: Path = Path("data/staging/stg_claims.csv"),
        policies_path: Path = Path("data/staging/stg_policies.csv"),
        customers_path: Path = Path("data/staging/stg_customers.csv"),
    ) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """Join staging datasets, compute category statistics, and engineer feature matrix."""
        claims = pd.read_csv(claims_path)
        policies = pd.read_csv(policies_path).drop_duplicates(subset=["policy_id"])
        customers = pd.read_csv(customers_path).drop_duplicates(
            subset=["customer_id"], keep="last"
        )

        logger.info(
            "Loaded staging data: %d claims, %d policies, %d customers",
            len(claims),
            len(policies),
            len(customers),
        )

        # 1:1 Left joins
        merged = claims.merge(
            policies[["policy_id", "start_date", "coverage_limit", "deductible"]],
            on="policy_id",
            how="left",
        )
        merged = merged.merge(
            customers[["customer_id", "credit_score"]],
            on="customer_id",
            how="left",
        )

        # Fit category stats
        self.fit_category_stats(merged)

        # Feature transformations
        X = self._compute_feature_dataframe(merged)
        y = merged["is_fraud"].astype(int)

        return X, y, merged

    def extract_single_record(
        self,
        claim_amount: float,
        claim_category: str,
        incident_date: str,
        filing_date: str,
        policy_start_date: str,
        coverage_limit: float,
        credit_score: float = 700.0,
    ) -> pd.DataFrame:
        """Extract feature row for a single incoming claim in real-time inference."""
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

        data = {
            "claim_amount": [float(claim_amount)],
            "coverage_limit": [float(coverage_limit)],
            "claim_to_coverage_ratio": [float(ratio)],
            "exceeds_coverage_flag": [float(exceeds_cov)],
            "days_since_policy_start": [float(days_since_start)],
            "early_filing_flag": [float(early_filing)],
            "filing_lag_days": [float(filing_lag)],
            "is_round_amount": [float(is_round)],
            "category_amount_zscore": [float(zscore)],
            "credit_score": [float(credit_score)],
        }
        return pd.DataFrame(data)[FEATURE_NAMES]

    def _compute_feature_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute vectorized feature matrix across all records."""
        inc_dt = pd.to_datetime(df["incident_date"])
        fil_dt = pd.to_datetime(df["filing_date"])
        pol_dt = pd.to_datetime(df["start_date"])

        filing_lag = (fil_dt - inc_dt).dt.days.clip(lower=0)
        days_since_start = (inc_dt - pol_dt).dt.days.clip(lower=0)
        early_filing = (days_since_start <= 7).astype(float)

        cov_limit = df["coverage_limit"].clip(lower=1.0)
        ratio = df["claim_amount"] / cov_limit
        exceeds_cov = (ratio > 1.0).astype(float)

        is_round = (
            (df["claim_amount"] % 1000 == 0) & (df["claim_amount"] >= 10000)
        ).astype(float)

        cat_means = (
            df["claim_category"]
            .map(self.category_stats.means)
            .fillna(df["claim_amount"])
        )
        cat_stds = (
            df["claim_category"]
            .map(self.category_stats.stds)
            .fillna(1.0)
            .replace(0, 1.0)
        )
        zscores = (df["claim_amount"] - cat_means) / cat_stds

        features_dict = {
            "claim_amount": df["claim_amount"].astype(float),
            "coverage_limit": df["coverage_limit"].astype(float),
            "claim_to_coverage_ratio": ratio.astype(float),
            "exceeds_coverage_flag": exceeds_cov,
            "days_since_policy_start": days_since_start.astype(float),
            "early_filing_flag": early_filing,
            "filing_lag_days": filing_lag.astype(float),
            "is_round_amount": is_round,
            "category_amount_zscore": zscores.astype(float),
            "credit_score": df["credit_score"].fillna(700.0).astype(float),
        }

        X = pd.DataFrame(features_dict)[FEATURE_NAMES]
        return X.fillna(0.0)
