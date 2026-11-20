"""Verification Script for Step 10.2 (ICIP-029).

Audits:
1. Two-sample Kolmogorov-Smirnov (KS) test & continuous Population Stability Index (PSI).
2. Categorical Chi-Square contingency & categorical PSI.
3. Model Governance Registry (artifacts, lineage, metrics, lifecycle stages).
4. Automated Retraining Decision Engine & Candidate Staging.
5. Markdown & JSON drift report generation.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure immediate line-buffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ml.drift_detector import DriftDetector, DriftSeverity  # noqa: E402
from ml.model_registry.registry import ModelStage, model_registry  # noqa: E402
from ml.retraining_trigger import RetrainingPolicyEngine  # noqa: E402


def print_banner(text: str) -> None:
    line = "=" * 80
    print(f"\n{line}\n  {text}\n{line}", flush=True)


def main() -> int:
    print_banner(
        "AUDIT: ICIP-029 MLOps Model Governance, Drift Detection & Retraining Triggers"
    )

    # 1. Audit Statistical Drift Calculations
    print(">>> 1. Auditing Statistical Drift Functions (KS & PSI)...", flush=True)
    detector = DriftDetector()
    np.random.seed(42)

    # Test identical continuous distributions
    base_num = np.random.normal(loc=100.0, scale=15.0, size=2000)
    curr_num_stable = np.random.normal(loc=100.0, scale=15.0, size=2000)
    psi_stable, _ = detector.calculate_continuous_psi(base_num, curr_num_stable)
    assert (
        psi_stable < 0.05
    ), f"Expected stable PSI < 0.05, got {psi_stable:.4f}"
    print(
        f"    [PASS] Stable continuous distribution PSI: {psi_stable:.4f} (Threshold: < 0.10)",
        flush=True,
    )

    # Test severe continuous drift
    curr_num_drifted = np.random.normal(loc=150.0, scale=35.0, size=2000)
    res_num = detector.test_continuous_feature(
        "claim_amount", base_num, curr_num_drifted
    )
    assert res_num.severity == DriftSeverity.CRITICAL
    assert res_num.psi_score >= 0.25
    print(
        f"    [PASS] Drifted continuous distribution PSI: {res_num.psi_score:.4f} | p-Value: {res_num.p_value:.2e} (Severity: {res_num.severity.value})",
        flush=True,
    )

    # Test categorical drift
    base_cat = ["Auto"] * 600 + ["Property"] * 300 + ["Life"] * 100
    curr_cat = ["Auto"] * 200 + ["Property"] * 700 + ["Life"] * 100
    res_cat = detector.test_categorical_feature("claim_category", base_cat, curr_cat)
    assert res_cat.severity in (DriftSeverity.MODERATE, DriftSeverity.CRITICAL)
    print(
        f"    [PASS] Shifted categorical distribution PSI: {res_cat.psi_score:.4f} | Chi2: {res_cat.test_statistic:.2f} (Severity: {res_cat.severity.value})",
        flush=True,
    )

    # 2. Audit Model Registry Governance
    print("\n>>> 2. Auditing Model Governance & Lineage Registry...", flush=True)
    models = model_registry.list_models()
    print(f"    Loaded {len(models)} models from {model_registry.registry_path.name}:", flush=True)

    clf_model = model_registry.get_model("NLP Claim Domain Classifier")
    assert clf_model is not None, "Missing NLP Classifier in registry"
    assert clf_model.stage == ModelStage.PRODUCTION
    print(
        f"      - {clf_model.name} (v{clf_model.version}) | Stage: {clf_model.stage.value} | Accuracy: {clf_model.metrics.get('accuracy')}",
        flush=True,
    )

    anom_model = model_registry.get_model("Isolation Forest Fraud Anomaly Detector")
    assert anom_model is not None, "Missing Isolation Forest in registry"
    assert anom_model.stage == ModelStage.PRODUCTION
    print(
        f"      - {anom_model.name} (v{anom_model.version}) | Stage: {anom_model.stage.value} | ROC-AUC: {anom_model.metrics.get('roc_auc')}",
        flush=True,
    )
    print("    [PASS] Production model governance records verified.", flush=True)

    # 3. Audit Batch Drift Evaluation on Real Platform Data
    print(
        "\n>>> 3. Executing Batch Drift Audit on Platform Baseline vs Shifted Inference...",
        flush=True,
    )
    data_path = PROJECT_ROOT / "data" / "processed" / "claims_clean.csv"
    assert data_path.is_file(), f"Missing {data_path}"
    df_clean = pd.read_csv(data_path)

    # Create synthetic post-production inference batch with 40% inflation
    df_inference = df_clean.sample(n=1500, random_state=42).copy()
    df_inference["claim_amount"] = (df_inference["claim_amount"] * 1.45 + 500.0).round(2)
    # Severe Property catastrophe shift
    prop_indices = df_inference.sample(frac=0.40, random_state=77).index
    df_inference.loc[prop_indices, "claim_category"] = "Property"

    audit_report = detector.audit_batch_drift(
        baseline_df=df_clean,
        current_df=df_inference,
        continuous_features=["claim_amount", "approved_amount"],
        categorical_features=["claim_category", "claim_priority", "status"],
        baseline_id="clean_claims_baseline",
        current_id="simulated_q4_inference_batch",
    )

    print(
        f"    Total Evaluated: {audit_report.total_features_evaluated} features | Drifted: {audit_report.drifted_features_count} ({audit_report.critical_drift_count} critical)",
        flush=True,
    )
    assert audit_report.retraining_recommended is True
    print(
        f"    [PASS] Retraining trigger policy tripped as expected (Critical Count: {audit_report.critical_drift_count})",
        flush=True,
    )

    # 4. Audit Retraining Policy Engine & Candidate Staging
    print(
        "\n>>> 4. Auditing Retraining Decision Engine & Candidate Staging...",
        flush=True,
    )
    policy_engine = RetrainingPolicyEngine()
    outcome = policy_engine.evaluate_and_trigger(
        audit_report=audit_report,
        target_model_name="NLP Claim Domain Classifier",
    )

    assert outcome["retraining_triggered"] is True
    assert Path(outcome["json_report_path"]).is_file()
    assert Path(outcome["md_report_path"]).is_file()
    print(
        f"    [PASS] JSON Report Generated: {Path(outcome['json_report_path']).name}",
        flush=True,
    )
    print(
        f"    [PASS] Markdown Report Generated: {Path(outcome['md_report_path']).name}",
        flush=True,
    )

    staged_ver = outcome["staged_candidate_version"]
    assert staged_ver is not None
    staged_model = model_registry.get_model("NLP Claim Domain Classifier", staged_ver)
    assert staged_model is not None
    assert staged_model.stage == ModelStage.STAGING
    print(
        f"    [PASS] Successfully staged retrained candidate: {staged_model.name}@{staged_model.version} (Stage: {staged_model.stage.value})",
        flush=True,
    )

    print_banner("ALL AUDIT CHECKS PASSED: STEP 10.2 MLOPS GOVERNANCE FULLY PRODUCTION-READY!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
