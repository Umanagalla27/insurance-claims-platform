"""
Unit and Integration Tests for Anomaly & Fraud Detection Engine
Component: ml/tests/test_anomaly_detector.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.anomaly_detection.features import (
    FEATURE_NAMES,
    AnomalyFeatureExtractor,
    CategoryStats,
)
from ml.anomaly_detection.predict import AnomalyResult, ClaimAnomalyDetector
from ml.anomaly_detection.train import train_anomaly_model


@pytest.fixture(scope="module")
def shared_detector() -> ClaimAnomalyDetector:
    return ClaimAnomalyDetector()


@pytest.mark.unit
class TestFeatureExtraction:
    """Unit tests verifying feature engineering logic and dimension contracts."""

    def test_feature_names_constant(self) -> None:
        assert len(FEATURE_NAMES) == 10
        expected = [
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
        assert expected == FEATURE_NAMES

    def test_single_record_extraction_shape(self) -> None:
        extractor = AnomalyFeatureExtractor()
        df = extractor.extract_single_record(
            claim_amount=5000.0,
            claim_category="Auto",
            incident_date="2026-05-10",
            filing_date="2026-05-15",
            policy_start_date="2025-01-01",
            coverage_limit=50000.0,
            credit_score=720.0,
        )
        assert len(df) == 1
        assert list(df.columns) == FEATURE_NAMES
        assert df["claim_to_coverage_ratio"].iloc[0] == pytest.approx(0.10)
        assert df["early_filing_flag"].iloc[0] == 0.0
        assert df["exceeds_coverage_flag"].iloc[0] == 0.0

    def test_category_stats_serialization(self) -> None:
        stats = CategoryStats(means={"Auto": 5000.0}, stds={"Auto": 1200.0})
        data = stats.to_dict()
        restored = CategoryStats.from_dict(data)
        assert restored.means == stats.means
        assert restored.stds == stats.stds


@pytest.mark.integration
class TestAnomalyInference:
    """Integration tests verifying trained Isolation Forest inference and risk flags."""

    def test_model_artifact_loaded_correctly(self, shared_detector: ClaimAnomalyDetector) -> None:
        assert len(shared_detector.feature_names) == 10
        assert "score_min" in shared_detector.calibration
        assert "score_max" in shared_detector.calibration

    def test_routine_claim_receives_low_risk(self, shared_detector: ClaimAnomalyDetector) -> None:
        result = shared_detector.evaluate_claim(
            claim_amount=3200.0,
            claim_category="Auto",
            incident_date="2026-06-10",
            filing_date="2026-06-14",
            policy_start_date="2025-01-01",
            coverage_limit=50000.0,
            credit_score=750.0,
        )
        assert isinstance(result, AnomalyResult)
        assert result.is_anomaly is False
        assert result.risk_tier == "LOW"
        assert result.risk_score < 45.0
        assert len(result.risk_factors) == 0

    def test_exceeds_coverage_and_early_filing_triggers_critical(
        self, shared_detector: ClaimAnomalyDetector
    ) -> None:
        result = shared_detector.evaluate_claim(
            claim_amount=120000.0,
            claim_category="Auto",
            incident_date="2026-01-02",
            filing_date="2026-01-03",
            policy_start_date="2026-01-01",  # 1 day after inception
            coverage_limit=50000.0,  # 2.4x coverage
            credit_score=520.0,
        )
        assert result.is_anomaly is True
        assert result.risk_tier in ["HIGH", "CRITICAL"]
        assert result.risk_score >= 65.0
        assert any("exceeds policy coverage" in f.lower() for f in result.risk_factors)
        assert any("early filing" in f.lower() for f in result.risk_factors)

    def test_round_number_high_value_flag(self, shared_detector: ClaimAnomalyDetector) -> None:
        result = shared_detector.evaluate_claim(
            claim_amount=50000.0,  # Suspiciously round
            claim_category="Property",
            incident_date="2026-03-10",
            filing_date="2026-03-12",
            policy_start_date="2025-06-01",
            coverage_limit=75000.0,
            credit_score=680.0,
        )
        assert any("round claim amount" in f.lower() for f in result.risk_factors)

    def test_training_pipeline_end_to_end(self, tmp_path: Path) -> None:
        _, metrics = train_anomaly_model(artifact_dir=tmp_path, n_estimators=50)
        assert "roc_auc" in metrics["metrics"]
        assert metrics["metrics"]["roc_auc"] > 0.70
        assert (tmp_path / "isolation_forest_anomaly.joblib").exists()
        assert (tmp_path / "anomaly_metrics.json").exists()

        with open(tmp_path / "anomaly_metrics.json", encoding="utf-8") as f:
            data = json.load(f)
            assert data["total_samples"] == 9107
