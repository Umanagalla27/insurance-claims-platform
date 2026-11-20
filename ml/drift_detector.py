"""Statistical Data & Prediction Drift Detection Engine (ICIP-029).

Implements enterprise-grade statistical tests for continuous and categorical features:
1. Kolmogorov-Smirnov (KS) 2-Sample Test: Non-parametric ECDF divergence.
2. Population Stability Index (PSI): Industry-standard risk bucket shift metric.
3. Chi-Square Test & Categorical Divergence: Frequency distribution comparison.
4. Drift Severity Classification: Categorization into NONE, MODERATE, or CRITICAL.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class DriftSeverity(StrEnum):
    """Classification of distribution drift severity."""

    NONE = "NONE"
    MODERATE = "MODERATE"
    CRITICAL = "CRITICAL"


@dataclass
class FeatureDriftResult:
    """Detailed drift audit result for a single feature or target prediction."""

    feature_name: str
    feature_type: str  # "continuous" or "categorical"
    psi_score: float
    p_value: float
    test_statistic: float
    test_name: str
    severity: DriftSeverity
    baseline_sample_count: int
    current_sample_count: int
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class DriftAuditReport:
    """Consolidated drift report across all monitored features and predictions."""

    audit_timestamp: str
    baseline_dataset_id: str
    current_dataset_id: str
    total_features_evaluated: int
    drifted_features_count: int
    critical_drift_count: int
    moderate_drift_count: int
    retraining_recommended: bool
    feature_results: dict[str, FeatureDriftResult] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_timestamp": self.audit_timestamp,
            "baseline_dataset_id": self.baseline_dataset_id,
            "current_dataset_id": self.current_dataset_id,
            "total_features_evaluated": self.total_features_evaluated,
            "drifted_features_count": self.drifted_features_count,
            "critical_drift_count": self.critical_drift_count,
            "moderate_drift_count": self.moderate_drift_count,
            "retraining_recommended": self.retraining_recommended,
            "feature_results": {
                k: v.to_dict() for k, v in self.feature_results.items()
            },
        }


class DriftDetector:
    """Statistical distribution drift detector for production ML models."""

    def __init__(
        self,
        psi_moderate_threshold: float = 0.10,
        psi_critical_threshold: float = 0.25,
        alpha_p_value: float = 0.05,
        num_continuous_bins: int = 10,
    ) -> None:
        self.psi_moderate_threshold = psi_moderate_threshold
        self.psi_critical_threshold = psi_critical_threshold
        self.alpha_p_value = alpha_p_value
        self.num_continuous_bins = num_continuous_bins

    def calculate_continuous_psi(
        self,
        expected: np.ndarray | pd.Series,
        actual: np.ndarray | pd.Series,
        num_bins: int | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Compute Population Stability Index (PSI) for continuous numerical data."""
        bins = num_bins or self.num_continuous_bins
        exp_arr = np.asarray(expected, dtype=float)
        act_arr = np.asarray(actual, dtype=float)

        # Drop NaNs
        exp_arr = exp_arr[~np.isnan(exp_arr)]
        act_arr = act_arr[~np.isnan(act_arr)]

        if len(exp_arr) == 0 or len(act_arr) == 0:
            return 0.0, {"error": "Empty dataset"}

        # Define quantile bin boundaries based on expected (baseline) distribution
        quantiles = np.linspace(0, 100, bins + 1)
        bin_edges = np.percentile(exp_arr, quantiles)
        # Ensure strictly ascending edges by adding tiny jitter if duplicated
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            return 0.0, {"warning": "Insufficient distinct values for binning"}

        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf

        # Calculate counts per bin
        exp_counts, _ = np.histogram(exp_arr, bins=bin_edges)
        act_counts, _ = np.histogram(act_arr, bins=bin_edges)

        # Laplace smoothing (add small epsilon to avoid division by zero or log(0))
        eps = 1e-4
        exp_pct = (exp_counts + eps) / (len(exp_arr) + eps * len(exp_counts))
        act_pct = (act_counts + eps) / (len(act_arr) + eps * len(act_counts))

        # PSI formula: sum((Actual - Expected) * ln(Actual / Expected))
        psi_components = (act_pct - exp_pct) * np.log(act_pct / exp_pct)
        psi_total = float(np.sum(psi_components))

        details = {
            "num_bins_used": len(exp_counts),
            "expected_counts": exp_counts.tolist(),
            "actual_counts": act_counts.tolist(),
            "psi_components": [round(float(x), 5) for x in psi_components],
        }
        return max(0.0, round(psi_total, 5)), details

    def calculate_categorical_psi(
        self,
        expected: list[Any] | pd.Series,
        actual: list[Any] | pd.Series,
    ) -> tuple[float, dict[str, Any]]:
        """Compute Population Stability Index (PSI) for discrete categorical features."""
        exp_series = pd.Series(expected).dropna().astype(str)
        act_series = pd.Series(actual).dropna().astype(str)

        all_categories = sorted(
            set(exp_series.unique()).union(set(act_series.unique()))
        )
        if not all_categories:
            return 0.0, {"error": "No valid categories"}

        exp_counts = exp_series.value_counts()
        act_counts = act_series.value_counts()

        total_exp = len(exp_series)
        total_act = len(act_series)

        eps = 1e-4
        psi_total = 0.0
        details_breakdown = {}

        for cat in all_categories:
            c_exp = exp_counts.get(cat, 0)
            c_act = act_counts.get(cat, 0)

            pct_exp = (c_exp + eps) / (total_exp + eps * len(all_categories))
            pct_act = (c_act + eps) / (total_act + eps * len(all_categories))

            comp = (pct_act - pct_exp) * np.log(pct_act / pct_exp)
            psi_total += comp
            details_breakdown[cat] = {
                "expected_pct": round(float(pct_exp), 4),
                "actual_pct": round(float(pct_act), 4),
                "psi_component": round(float(comp), 5),
            }

        return max(0.0, round(float(psi_total), 5)), details_breakdown

    def test_continuous_feature(
        self,
        feature_name: str,
        baseline: np.ndarray | pd.Series,
        current: np.ndarray | pd.Series,
    ) -> FeatureDriftResult:
        """Run KS test and PSI on a continuous numerical feature."""
        b_clean = np.asarray(baseline, dtype=float)
        c_clean = np.asarray(current, dtype=float)
        b_clean = b_clean[~np.isnan(b_clean)]
        c_clean = c_clean[~np.isnan(c_clean)]

        # 1. Kolmogorov-Smirnov 2-sample test
        ks_res = stats.ks_2samp(b_clean, c_clean)
        ks_stat = float(ks_res.statistic)
        p_val = float(ks_res.pvalue)

        # 2. Population Stability Index (PSI)
        psi_score, details = self.calculate_continuous_psi(b_clean, c_clean)
        details["ks_statistic"] = round(ks_stat, 5)
        details["p_value"] = round(p_val, 6)

        # 3. Severity classification
        severity = self._classify_severity(psi_score, p_val)

        return FeatureDriftResult(
            feature_name=feature_name,
            feature_type="continuous",
            psi_score=psi_score,
            p_value=p_val,
            test_statistic=ks_stat,
            test_name="Kolmogorov-Smirnov + PSI",
            severity=severity,
            baseline_sample_count=len(b_clean),
            current_sample_count=len(c_clean),
            details=details,
        )

    def test_categorical_feature(
        self,
        feature_name: str,
        baseline: list[Any] | pd.Series,
        current: list[Any] | pd.Series,
    ) -> FeatureDriftResult:
        """Run Chi-Square and Categorical PSI on discrete or prediction features."""
        b_series = pd.Series(baseline).dropna().astype(str)
        c_series = pd.Series(current).dropna().astype(str)

        # Categorical PSI
        psi_score, details = self.calculate_categorical_psi(b_series, c_series)

        # Chi-Square contingency table
        all_cats = sorted(
            set(b_series.unique()).union(set(c_series.unique()))
        )
        b_counts = [b_series.value_counts().get(c, 0) for c in all_cats]
        c_counts = [c_series.value_counts().get(c, 0) for c in all_cats]

        # Use 2xK contingency table for independent samples
        contingency = np.array([b_counts, c_counts])
        # Add 1 smoothing if zeros present
        if np.any(contingency == 0):
            contingency = contingency + 1

        try:
            chi2_res = stats.chi2_contingency(contingency)
            chi2_stat = float(chi2_res.statistic)
            p_val = float(chi2_res.pvalue)
        except Exception:
            chi2_stat = 0.0
            p_val = 1.0

        details["chi2_statistic"] = round(chi2_stat, 4)
        details["p_value"] = round(p_val, 6)

        severity = self._classify_severity(psi_score, p_val)

        return FeatureDriftResult(
            feature_name=feature_name,
            feature_type="categorical",
            psi_score=psi_score,
            p_value=p_val,
            test_statistic=chi2_stat,
            test_name="Chi-Square Contingency + Categorical PSI",
            severity=severity,
            baseline_sample_count=len(b_series),
            current_sample_count=len(c_series),
            details=details,
        )

    def _classify_severity(self, psi: float, p_val: float) -> DriftSeverity:
        """Rule-based drift severity classification matrix."""
        if psi >= self.psi_critical_threshold:
            return DriftSeverity.CRITICAL
        elif psi >= self.psi_moderate_threshold or (p_val < 0.01 and psi >= 0.08):
            return DriftSeverity.MODERATE
        return DriftSeverity.NONE

    def audit_batch_drift(
        self,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        continuous_features: list[str],
        categorical_features: list[str],
        baseline_id: str = "baseline_v1",
        current_id: str = "inference_batch",
    ) -> DriftAuditReport:
        """Run complete multi-feature drift audit across baseline and production batches."""
        from datetime import UTC, datetime

        results: dict[str, FeatureDriftResult] = {}
        crit_count = 0
        mod_count = 0

        # Continuous Numerical Audit
        for col in continuous_features:
            if col in baseline_df.columns and col in current_df.columns:
                res = self.test_continuous_feature(
                    feature_name=col,
                    baseline=baseline_df[col],
                    current=current_df[col],
                )
                results[col] = res
                if res.severity == DriftSeverity.CRITICAL:
                    crit_count += 1
                elif res.severity == DriftSeverity.MODERATE:
                    mod_count += 1

        # Categorical Feature & Prediction Audit
        for col in categorical_features:
            if col in baseline_df.columns and col in current_df.columns:
                res = self.test_categorical_feature(
                    feature_name=col,
                    baseline=baseline_df[col],
                    current=current_df[col],
                )
                results[col] = res
                if res.severity == DriftSeverity.CRITICAL:
                    crit_count += 1
                elif res.severity == DriftSeverity.MODERATE:
                    mod_count += 1

        # Retraining decision policy:
        # Trigger if >= 1 critical feature drifted, or >= 2 moderate features drifted
        retrain_needed = (crit_count >= 1) or (mod_count >= 2)

        return DriftAuditReport(
            audit_timestamp=datetime.now(UTC).isoformat(),
            baseline_dataset_id=baseline_id,
            current_dataset_id=current_id,
            total_features_evaluated=len(results),
            drifted_features_count=crit_count + mod_count,
            critical_drift_count=crit_count,
            moderate_drift_count=mod_count,
            retraining_recommended=retrain_needed,
            feature_results=results,
        )
