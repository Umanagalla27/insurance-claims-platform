"""
data_generator/verify_data.py
=============================
Quality gate and verification script for the synthetic insurance dataset.
Validates row counts, schemas, messiness, fraud rates, and relational integrity.

Usage:
    python data_generator/verify_data.py
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check(name: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}")
    if details:
        print(f"         {details}")
    return condition


def verify_dataset() -> bool:
    print("\n" + "=" * 65)
    print("  Insurance Claims Intelligence Platform — Data Quality Verification")
    print("=" * 65 + "\n")

    raw_dir = PROJECT_ROOT / "data" / "raw"
    cust_file = raw_dir / "customers.csv"
    pol_file = raw_dir / "policies.csv"
    claim_file = raw_dir / "claims.csv"

    results = []

    # 1. File existence
    print("1. File Existence & Loading:")
    for f in [cust_file, pol_file, claim_file]:
        r = check(f"File exists: {f.name}", f.exists())
        results.append(r)

    if not all(results):
        print("\n  ❌ Missing files! Run 'python data_generator/run_all.py' first.")
        return False

    df_cust = pd.read_csv(cust_file)
    df_pol = pd.read_csv(pol_file)
    df_claim = pd.read_csv(claim_file)

    # 2. Volume checks
    print("\n2. Dataset Scale & Volume:")
    r1 = check(f"Customers count ({len(df_cust)} >= 500)", len(df_cust) >= 500)
    r2 = check(f"Policies count ({len(df_pol)} >= 800)", len(df_pol) >= 800)
    r3 = check(f"Claims count ({len(df_claim)} >= 10,000)", len(df_claim) >= 10000)
    results.extend([r1, r2, r3])

    # 3. Intentional Messiness Verification
    print("\n3. Realistic Messiness Injections:")
    # Check for missing values in claims
    missing_desc = df_claim["description"].isna().sum()
    missing_state = df_claim["state"].isna().sum()
    r_missing = check(
        f"Missing values present (desc: {missing_desc}, state: {missing_state})",
        missing_desc > 0 and missing_state > 0,
        f"Missing rate in description: {missing_desc / len(df_claim):.2%}",
    )
    results.append(r_missing)

    # Check for duplicate claims
    dup_claims = df_claim.duplicated(subset=["claim_id"]).sum()
    r_dup = check(
        f"Duplicate claims present ({dup_claims} duplicates)",
        dup_claims > 100,
        f"Duplicate rate: {dup_claims / len(df_claim):.2%}",
    )
    results.append(r_dup)

    # Check for negative / zero amounts
    invalid_amts = (df_claim["claim_amount"] <= 0).sum()
    r_amts = check(
        f"Negative/zero amounts present ({invalid_amts} erroneous rows)",
        invalid_amts > 20,
        f"Invalid amount rate: {invalid_amts / len(df_claim):.2%}",
    )
    results.append(r_amts)

    # Check for non-standard date formats (e.g. contains '/')
    slash_dates = df_claim["incident_date"].str.contains("/", na=False).sum()
    r_dates = check(
        f"Non-ISO date formats present ({slash_dates} rows with MM/DD/YYYY)",
        slash_dates > 50,
        f"Non-ISO date rate: {slash_dates / len(df_claim):.2%}",
    )
    results.append(r_dates)

    # 4. Fraud and Anomaly Injection
    print("\n4. Fraud & Anomaly Indicators:")
    fraud_count = (df_claim["is_fraud"] == 1).sum()
    fraud_pct = fraud_count / len(df_claim)
    r_fraud = check(
        f"Fraudulent claims flagged ({fraud_count} claims, {fraud_pct:.1%})",
        0.03 <= fraud_pct <= 0.08,
        f"Target range: 3% - 8% (Actual: {fraud_pct:.2%})",
    )
    results.append(r_fraud)

    # 5. Relational Integrity
    print("\n5. Relational Integrity:")
    valid_cust_ids = set(df_cust["customer_id"].dropna())
    valid_pol_ids = set(df_pol["policy_id"].dropna())

    orphaned_policies = (~df_pol["customer_id"].isin(valid_cust_ids)).sum()
    r_pol_fk = check(
        f"All policies map to valid customers ({orphaned_policies} orphaned)",
        orphaned_policies == 0,
    )
    results.append(r_pol_fk)

    orphaned_claims = (~df_claim["policy_id"].isin(valid_pol_ids)).sum()
    r_claim_fk = check(
        f"All claims map to valid policies ({orphaned_claims} orphaned)",
        orphaned_claims == 0,
    )
    results.append(r_claim_fk)

    # 6. NLP / Description Text Quality
    print("\n6. Text Narrative Quality (for ML Sprint 4):")
    valid_descs = df_claim["description"].dropna()
    word_counts = valid_descs.apply(lambda x: len(str(x).split()))
    avg_words = word_counts.mean()
    r_nlp = check(
        f"Rich text narrative (avg {avg_words:.1f} words per claim)",
        avg_words >= 25,
        f"Min: {word_counts.min()} words | Max: {word_counts.max()} words",
    )
    results.append(r_nlp)

    num_categories = df_claim["claim_category"].nunique()
    r_cat = check(
        f"All 7 claim categories represented ({num_categories}/7)",
        num_categories == 7,
    )
    results.append(r_cat)

    passed_count = sum(results)
    total_count = len(results)

    print("\n" + "=" * 65)
    print(f"  Summary: {passed_count}/{total_count} assertions PASSED")
    print("=" * 65)

    if passed_count == total_count:
        print("\n  🎉 Data Quality Verification: PASSED!")
        print("  Dataset is ready for Mock API (Step 3) and ETL Pipeline (Sprint 2).\n")
        return True
    else:
        print(f"\n  ❌ {total_count - passed_count} check(s) FAILED.")
        return False


if __name__ == "__main__":
    success = verify_dataset()
    sys.exit(0 if success else 1)
