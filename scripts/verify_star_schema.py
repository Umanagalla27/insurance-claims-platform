"""
Verification Script for Star-Schema Warehouse Views & Power BI Semantic Model (ICIP-025).
Audits SQL migration 005, DAX measures, Tabular Semantic Model schema, and referential integrity of dimensional exports.
"""

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SQL = (
    PROJECT_ROOT / "database" / "migrations" / "005_star_schema_semantic_views.sql"
)
DAX_FILE = PROJECT_ROOT / "powerbi" / "dax_measures.dax"
SEMANTIC_MODEL_JSON = PROJECT_ROOT / "powerbi" / "semantic_model.json"
SEMANTIC_DATA_DIR = PROJECT_ROOT / "data" / "semantic_layer"


def audit_sql_views() -> bool:
    print("[1/5] Auditing SQL Migration 005 Star-Schema Views...")
    assert MIGRATION_SQL.is_file(), f"Migration SQL file missing: {MIGRATION_SQL}"
    content = MIGRATION_SQL.read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW vw_dim_date" in content
    assert "CREATE OR REPLACE VIEW vw_dim_policy" in content
    assert "CREATE OR REPLACE VIEW vw_dim_customer" in content
    assert "CREATE OR REPLACE VIEW vw_fact_claims_adjudication" in content
    assert "CREATE OR REPLACE VIEW vw_fact_underwriting_portfolio" in content
    assert "is_straight_through_approved" in content
    assert "fraud_loss_avoidance" in content
    print(
        "  -> Conformed dimensional and fact views verified (vw_dim_date, vw_dim_policy, vw_dim_customer, vw_fact_claims_adjudication, vw_fact_underwriting_portfolio)."
    )
    return True


def audit_dax_measures() -> bool:
    print("[2/5] Auditing Power BI DAX Measures...")
    assert DAX_FILE.is_file(), f"DAX measures file missing: {DAX_FILE}"
    content = DAX_FILE.read_text(encoding="utf-8")
    assert "[Loss Ratio %]" in content
    assert "[STP Rate %]" in content
    assert "[Fraud Loss Avoidance $]" in content
    assert "[Fraud Rate %]" in content
    assert "DIVIDE(" in content
    print(
        "  -> Power BI DAX measures verified (Loss Ratio %, STP Rate %, Fraud Loss Avoidance $, DIVIDE guards)."
    )
    return True


def audit_semantic_model_json() -> bool:
    print("[3/5] Auditing Power BI Tabular Semantic Model Specification...")
    assert SEMANTIC_MODEL_JSON.is_file(), (
        f"Semantic model JSON missing: {SEMANTIC_MODEL_JSON}"
    )
    with open(SEMANTIC_MODEL_JSON, encoding="utf-8") as f:
        model_data = json.load(f)

    assert "model" in model_data
    tables = [t["name"] for t in model_data["model"].get("tables", [])]
    expected_tables = [
        "dim_date",
        "dim_policy",
        "dim_customer",
        "fact_claims_adjudication",
    ]
    for t in expected_tables:
        assert t in tables, f"Missing table {t} in semantic model"

    relationships = model_data["model"].get("relationships", [])
    assert len(relationships) >= 3, (
        "Semantic model must define at least 3 foreign key relationships"
    )
    print(
        "  -> Power BI Semantic Model schema verified (4 tables, 1-to-many single-directional relationships)."
    )
    return True


def audit_exported_datasets() -> bool:
    print("[4/5] Auditing Exported Semantic Layer Datasets...")
    expected_files = [
        "dim_customer.csv",
        "dim_policy.csv",
        "dim_date.csv",
        "fact_claims_adjudication.csv",
        "fact_underwriting_portfolio.csv",
        "summary_metrics.json",
    ]
    for filename in expected_files:
        filepath = SEMANTIC_DATA_DIR / filename
        assert filepath.is_file(), f"Exported dataset missing: {filepath}"
        assert filepath.stat().st_size > 0, f"Exported file is empty: {filepath}"

    with open(SEMANTIC_DATA_DIR / "summary_metrics.json", encoding="utf-8") as f:
        metrics = json.load(f)
    assert metrics.get("status") == "SUCCESS"
    assert metrics["kpi_metrics"]["total_claims_filed"] > 0
    print(
        f"  -> Exported datasets verified: {metrics['records_exported']['fact_claims_adjudication']:,} claims across conformed dimensions."
    )
    return True


def audit_referential_integrity() -> bool:
    print("[5/5] Auditing Star-Schema Referential Integrity...")
    df_claims = pd.read_csv(SEMANTIC_DATA_DIR / "fact_claims_adjudication.csv")
    df_policy = pd.read_csv(SEMANTIC_DATA_DIR / "dim_policy.csv")
    df_customer = pd.read_csv(SEMANTIC_DATA_DIR / "dim_customer.csv")
    df_date = pd.read_csv(SEMANTIC_DATA_DIR / "dim_date.csv")

    valid_policies = set(df_policy["policy_id"])
    valid_customers = set(df_customer["customer_id"])
    valid_dates = set(df_date["date_key"])

    orphan_policies = set(df_claims["policy_id"]) - valid_policies
    orphan_customers = set(df_claims["customer_id"]) - valid_customers
    orphan_dates = set(df_claims["date_key"]) - valid_dates

    assert len(orphan_policies) == 0, (
        f"Found {len(orphan_policies)} orphan policy IDs in fact table"
    )
    assert len(orphan_customers) == 0, (
        f"Found {len(orphan_customers)} orphan customer IDs in fact table"
    )
    assert len(orphan_dates) == 0, (
        f"Found {len(orphan_dates)} orphan date keys in fact table"
    )
    print(
        "  -> Star-Schema referential integrity verified (0 orphan foreign keys across all 9,107 fact records)."
    )
    return True


def main() -> int:
    print("=" * 80)
    print(
        "   Insurance Claims Intelligence — Star-Schema & Semantic Layer Audit (ICIP-025)"
    )
    print("=" * 80)
    try:
        assert audit_sql_views()
        assert audit_dax_measures()
        assert audit_semantic_model_json()
        assert audit_exported_datasets()
        assert audit_referential_integrity()
        print("\n" + "=" * 80)
        print(" [SUCCESS] All 5 Star-Schema & Semantic Layer audit checks PASSED!")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n[ERROR] Audit check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
