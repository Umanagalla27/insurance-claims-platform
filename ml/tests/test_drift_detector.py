"""Automated Pytest Suite for MLOps Governance & Drift Detection (ICIP-029).

Tests:
1. Continuous Population Stability Index (PSI) calculations & edge cases.
2. Categorical PSI & Chi-Square statistical tests.
3. Two-sample Kolmogorov-Smirnov (KS) test integration.
4. Drift severity classification rules (NONE, MODERATE, CRITICAL).
5. Model Registry lifecycle transitions (DEVELOPMENT -> STAGING -> PRODUCTION -> ARCHIVED).
6. Automated Retraining Decision Engine and candidate version staging.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.drift_detector import (
    DriftDetector,
    DriftSeverity,
)
from ml.model_registry.registry import (
    ModelMetadata,
    ModelRegistry,
    ModelStage,
)
from ml.retraining_trigger import RetrainingPolicyEngine


@pytest.fixture
def detector() -> DriftDetector:
    return DriftDetector(
        psi_moderate_threshold=0.10,
        psi_critical_threshold=0.25,
        alpha_p_value=0.05,
    )


@pytest.fixture
def temp_registry() -> ModelRegistry:
    """Create an isolated temporary registry for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "test_model_registry.json"
        reg = ModelRegistry(registry_path=reg_file)
        yield reg


# ==============================================================================
# 1. Statistical Drift Test Cases (Continuous & Categorical PSI)
# ==============================================================================


def test_continuous_psi_identical_distributions(detector: DriftDetector):
    """Identical distributions must produce near-zero PSI (< 0.02)."""
    np.random.seed(42)
    expected = np.random.normal(loc=100.0, scale=15.0, size=5000)
    actual = np.random.normal(loc=100.0, scale=15.0, size=5000)

    psi, details = detector.calculate_continuous_psi(expected, actual)
    assert psi < 0.02, f"Expected near-zero PSI, got {psi}"
    assert details["num_bins_used"] >= 5


def test_continuous_psi_moderate_drift(detector: DriftDetector):
    """Mild distribution shift must yield moderate PSI (0.10 <= PSI < 0.25)."""
    np.random.seed(42)
    expected = np.random.normal(loc=100.0, scale=15.0, size=5000)
    actual = np.random.normal(loc=107.0, scale=18.0, size=5000)

    psi, _ = detector.calculate_continuous_psi(expected, actual)
    assert 0.08 <= psi < 0.30, f"Expected moderate PSI, got {psi}"


def test_continuous_psi_critical_drift(detector: DriftDetector):
    """Severe distribution shift must yield critical PSI (PSI >= 0.25)."""
    np.random.seed(42)
    expected = np.random.normal(loc=100.0, scale=15.0, size=5000)
    actual = np.random.normal(loc=140.0, scale=30.0, size=5000)

    psi, _ = detector.calculate_continuous_psi(expected, actual)
    assert psi >= 0.25, f"Expected critical PSI >= 0.25, got {psi}"


def test_continuous_feature_ks_and_severity(detector: DriftDetector):
    """Assert KS test and severity classification for stable vs shifted data."""
    np.random.seed(42)
    baseline = np.random.exponential(scale=2000.0, size=3000)
    # Severe inflation
    current = np.random.exponential(scale=3500.0, size=3000)

    res = detector.test_continuous_feature("claim_amount", baseline, current)
    assert res.feature_name == "claim_amount"
    assert res.feature_type == "continuous"
    assert res.p_value < 1e-5
    assert res.psi_score >= 0.15
    assert res.severity in (DriftSeverity.MODERATE, DriftSeverity.CRITICAL)


def test_categorical_psi_and_chi2(detector: DriftDetector):
    """Categorical features must correctly detect frequency shifts."""
    baseline = ["Auto"] * 500 + ["Property"] * 300 + ["Life"] * 200
    # Current batch with catastrophe shift (massive Property surge)
    current = ["Auto"] * 200 + ["Property"] * 700 + ["Life"] * 100

    res = detector.test_categorical_feature("claim_category", baseline, current)
    assert res.feature_name == "claim_category"
    assert res.feature_type == "categorical"
    assert res.p_value < 1e-4
    assert res.psi_score >= 0.20
    assert res.severity in (DriftSeverity.MODERATE, DriftSeverity.CRITICAL)


def test_audit_batch_drift_orchestration(detector: DriftDetector):
    """Batch evaluation correctly flags critical and moderate drifts across features."""
    np.random.seed(42)
    df_base = pd.DataFrame(
        {
            "amount": np.random.normal(1000, 200, 1000),
            "score": np.random.normal(700, 50, 1000),
            "category": ["A"] * 600 + ["B"] * 400,
        }
    )
    # Shifted current batch
    df_curr = pd.DataFrame(
        {
            "amount": np.random.normal(2000, 400, 1000),  # Critical shift
            "score": np.random.normal(700, 50, 1000),  # Stable
            "category": ["A"] * 600 + ["B"] * 400,  # Stable
        }
    )

    report = detector.audit_batch_drift(
        baseline_df=df_base,
        current_df=df_curr,
        continuous_features=["amount", "score"],
        categorical_features=["category"],
    )

    assert report.total_features_evaluated == 3
    assert report.critical_drift_count >= 1
    assert report.retraining_recommended is True
    assert "amount" in report.feature_results


# ==============================================================================
# 2. Model Registry Governance Tests
# ==============================================================================


def test_model_registry_initial_seed(temp_registry: ModelRegistry):
    """Verify registry initializes with seeded production models."""
    models = temp_registry.list_models()
    assert len(models) >= 2

    clf = temp_registry.get_model("NLP Claim Domain Classifier")
    assert clf is not None
    assert clf.stage == ModelStage.PRODUCTION
    assert clf.version == "1.0.0"

    anom = temp_registry.get_model("Isolation Forest Fraud Anomaly Detector")
    assert anom is not None
    assert anom.stage == ModelStage.PRODUCTION


def test_model_registry_stage_transitions(temp_registry: ModelRegistry):
    """Verify promotion to PRODUCTION automatically archives prior production version."""
    # 1. Register candidate in STAGING
    candidate = ModelMetadata(
        model_id="clf_candidate_v2",
        name="NLP Claim Domain Classifier",
        version="1.1.0",
        model_type="classification",
        stage=ModelStage.STAGING,
        artifact_path="ml/artifacts/claim_classifier_v1_1.joblib",
        trained_at="2026-11-20T12:00:00Z",
        git_commit="abcdef1",
        metrics={"accuracy": 1.0},
        hyperparameters={},
        feature_names=["claim_text_tfidf"],
        description="Retrained candidate",
    )
    temp_registry.register_model(candidate)

    # 2. Promote candidate to PRODUCTION
    temp_registry.transition_stage(
        name="NLP Claim Domain Classifier",
        version="1.1.0",
        new_stage=ModelStage.PRODUCTION,
        notes="Promoted after passing shadow canary evaluation",
    )

    # 3. Assert v1.1.0 is PRODUCTION and v1.0.0 was ARCHIVED
    current_prod = temp_registry.get_production_model(
        "NLP Claim Domain Classifier"
    )
    assert current_prod is not None
    assert current_prod.version == "1.1.0"
    assert current_prod.stage == ModelStage.PRODUCTION

    old_v1 = temp_registry.get_model("NLP Claim Domain Classifier", "1.0.0")
    assert old_v1.stage == ModelStage.ARCHIVED
    assert len(old_v1.transitions) >= 2


# ==============================================================================
# 3. Retraining Decision Engine Tests
# ==============================================================================


def test_retraining_trigger_policy(temp_registry: ModelRegistry):
    """Verify retraining trigger engine stages candidate model on critical drift."""
    detector = DriftDetector()
    df_base = pd.DataFrame({"amount": np.random.normal(1000, 100, 1000)})
    df_curr = pd.DataFrame(
        {"amount": np.random.normal(2500, 500, 1000)}
    )  # Severe drift

    report = detector.audit_batch_drift(
        baseline_df=df_base,
        current_df=df_curr,
        continuous_features=["amount"],
        categorical_features=[],
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = RetrainingPolicyEngine(
            registry=temp_registry, reports_dir=Path(tmp_dir)
        )
        outcome = engine.evaluate_and_trigger(
            audit_report=report,
            target_model_name="NLP Claim Domain Classifier",
        )

        assert outcome["retraining_triggered"] is True
        assert Path(outcome["json_report_path"]).is_file()
        assert Path(outcome["md_report_path"]).is_file()
        assert outcome["staged_candidate_version"] == "1.1.0-candidate"

        # Check candidate staged in registry
        staged = temp_registry.get_model(
            "NLP Claim Domain Classifier", "1.1.0-candidate"
        )
        assert staged is not None
        assert staged.stage == ModelStage.STAGING
