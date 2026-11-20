"""CLI Runner for MLOps Data & Prediction Drift Audits (ICIP-029).

Executes statistical drift detection (KS test, PSI, Chi-Square) across production features,
generates executive markdown and JSON drift reports, and triggers candidate model staging.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from ml.drift_detector import DriftDetector, DriftSeverity  # noqa: E402
from ml.retraining_trigger import RetrainingPolicyEngine  # noqa: E402


def print_banner(text: str) -> None:
    line = "=" * 80
    print(f"\n{line}\n  {text}\n{line}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MLOps Drift Audit and Retraining Decision Engine"
    )
    parser.add_argument(
        "--simulate-drift",
        action="store_true",
        help="Simulate severe covariate shift (e.g., inflation surge and category shift)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="NLP Claim Domain Classifier",
        help="Target model name to evaluate in registry",
    )
    args = parser.parse_args()

    print_banner("MLOPS GOVERNANCE: DATA & PREDICTION DRIFT AUDIT")

    # 1. Load Baseline Production Dataset
    data_path = PROJECT_ROOT / "data" / "processed" / "claims_clean.csv"
    if not data_path.is_file():
        print(f"[ERROR] Baseline dataset not found at {data_path}")
        return 1

    df_baseline = pd.read_csv(data_path)
    print(
        f">>> 1. Loaded Baseline Dataset: {len(df_baseline):,} records from {data_path.name}"
    )

    # 2. Prepare Current Production Batch
    if args.simulate_drift:
        print(
            ">>> 2. Simulating Covariate Shift & Fraud Surge in Current Batch..."
        )
        df_current = df_baseline.sample(
            n=2000, random_state=42, replace=False
        ).copy()
        # Covariate shift: 40% inflation spike in claim amounts + 25% shift towards Property/Auto
        df_current["claim_amount"] = (
            df_current["claim_amount"] * 1.45 + 500.0
        ).round(2)
        df_current["approved_amount"] = (
            df_current["approved_amount"] * 1.30
        ).round(2)
        # Category distribution drift: Catastrophe surge in Property
        surge_indices = df_current.sample(frac=0.35, random_state=99).index
        df_current.loc[surge_indices, "claim_category"] = "Property"
        df_current.loc[surge_indices, "claim_priority"] = "HIGH"
        batch_id = "simulated_inflation_catastrophe_batch"
    else:
        print(">>> 2. Splitting Baseline for Natural Variance Audit...")
        df_current = df_baseline.sample(
            n=2000, random_state=123, replace=False
        ).copy()
        batch_id = "production_inference_sample"

    print(
        f"    Target Current Batch Size: {len(df_current):,} records (Batch ID: {batch_id})"
    )

    # 3. Execute Statistical Drift Detection
    print("\n>>> 3. Executing Two-Sample Statistical Drift Tests...")
    detector = DriftDetector()
    continuous_features = ["claim_amount", "approved_amount"]
    categorical_features = ["claim_category", "claim_priority", "status"]

    audit_report = detector.audit_batch_drift(
        baseline_df=df_baseline,
        current_df=df_current,
        continuous_features=continuous_features,
        categorical_features=categorical_features,
        baseline_id="claims_clean_baseline",
        current_id=batch_id,
    )

    # 4. Print Summary Table
    print("\n" + "-" * 85)
    print(
        f"{'Feature Name':<20} | {'Type':<12} | {'PSI':<8} | {'p-Value':<10} | {'Statistic':<10} | {'Severity':<10}"
    )
    print("-" * 85)
    for fname, res in sorted(audit_report.feature_results.items()):
        sev_color = (
            "[CRITICAL]"
            if res.severity == DriftSeverity.CRITICAL
            else (
                "[MODERATE]"
                if res.severity == DriftSeverity.MODERATE
                else "[NONE]"
            )
        )
        print(
            f"{fname:<20} | {res.feature_type:<12} | {res.psi_score:<8.4f} | {res.p_value:<10.3e} | {res.test_statistic:<10.4f} | {sev_color:<10}"
        )
    print("-" * 85)

    print(f"\nTotal Features Audited: {audit_report.total_features_evaluated}")
    print(f"Drifted Features Count: {audit_report.drifted_features_count}")
    print(f"Critical Drift Count:   {audit_report.critical_drift_count}")
    print(f"Moderate Drift Count:   {audit_report.moderate_drift_count}")
    print(
        f"Retraining Needed?:     {'YES (TRIGGERED)' if audit_report.retraining_recommended else 'NO (STABLE)'}"
    )

    # 5. Execute Retraining Policy & Candidate Staging
    print("\n>>> 4. Evaluating Retraining Policy & Staging Candidates...")
    engine = RetrainingPolicyEngine()
    eval_outcome = engine.evaluate_and_trigger(
        audit_report=audit_report, target_model_name=args.model_name
    )

    print(f"    Report JSON Generated: {eval_outcome['json_report_path']}")
    print(f"    Report Markdown:       {eval_outcome['md_report_path']}")

    if eval_outcome["retraining_triggered"]:
        print(
            f"    [STAGED] Staged Candidate Model Version: {eval_outcome['staged_candidate_version']} in Model Registry!"
        )
    else:
        print(
            "    [STABLE] All monitored feature distributions within acceptable tolerances."
        )

    print_banner("DRIFT AUDIT COMPLETE — GOVERNANCE AUDIT LOGGED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
