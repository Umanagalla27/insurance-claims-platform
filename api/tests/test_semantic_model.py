"""
Automated Pytest Suite for Star-Schema Warehouse Views & Power BI Semantic Layer (ICIP-025).
Validates SQL DDL views, DAX calculations, Tabular Semantic Model definitions,
and referential integrity across conformed dimensional tables.
"""

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATION_SQL = (
    PROJECT_ROOT / "database" / "migrations" / "005_star_schema_semantic_views.sql"
)
DAX_FILE = PROJECT_ROOT / "powerbi" / "dax_measures.dax"
SEMANTIC_MODEL_JSON = PROJECT_ROOT / "powerbi" / "semantic_model.json"
SEMANTIC_DATA_DIR = PROJECT_ROOT / "data" / "semantic_layer"


class TestSQLStarSchemaViews:
    """Validates Kimball Star-Schema SQL DDL view declarations."""

    def test_sql_migration_file_exists(self):
        assert MIGRATION_SQL.is_file()

    def test_sql_dimensional_views_declared(self):
        content = MIGRATION_SQL.read_text(encoding="utf-8")
        assert "CREATE OR REPLACE VIEW vw_dim_date" in content
        assert "CREATE OR REPLACE VIEW vw_dim_policy" in content
        assert "CREATE OR REPLACE VIEW vw_dim_customer" in content
        assert "coverage_tier" in content
        assert "premium_band" in content
        assert "credit_tier" in content
        assert "us_region" in content

    def test_sql_fact_views_declared(self):
        content = MIGRATION_SQL.read_text(encoding="utf-8")
        assert "CREATE OR REPLACE VIEW vw_fact_claims_adjudication" in content
        assert "CREATE OR REPLACE VIEW vw_fact_underwriting_portfolio" in content
        assert "is_straight_through_approved" in content
        assert "fraud_loss_avoidance" in content
        assert "loss_ratio_pct" in content


class TestDAXMeasures:
    """Validates Power BI DAX formula syntax and financial safety patterns."""

    def test_dax_file_exists(self):
        assert DAX_FILE.is_file()

    def test_essential_insurance_kpis_defined(self):
        content = DAX_FILE.read_text(encoding="utf-8")
        assert "[Total Claims Filed]" in content
        assert "[Total Incurred Claims]" in content
        assert "[Total Approved Payout]" in content
        assert "[Total Earned Premium]" in content
        assert "[Loss Ratio %]" in content
        assert "[STP Rate %]" in content
        assert "[Fraud Rate %]" in content
        assert "[Fraud Loss Avoidance $]" in content
        assert "[Average Filing Lag Days]" in content

    def test_dax_division_by_zero_guards(self):
        content = DAX_FILE.read_text(encoding="utf-8")
        # Ensure DIVIDE is used rather than raw '/' operator for ratios
        assert "DIVIDE(" in content
        assert "/" not in [
            line.strip()
            for line in content.splitlines()
            if line.strip().startswith("[Loss Ratio %]")
        ]


class TestTabularSemanticModel:
    """Validates Microsoft Power BI Analysis Services Tabular Model schema."""

    def test_semantic_model_json_structure(self):
        assert SEMANTIC_MODEL_JSON.is_file()
        with open(SEMANTIC_MODEL_JSON, encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("compatibilityLevel") == 1567
        assert "model" in data
        assert "tables" in data["model"]
        assert "relationships" in data["model"]

    def test_model_tables_and_columns(self):
        with open(SEMANTIC_MODEL_JSON, encoding="utf-8") as f:
            data = json.load(f)
        tables = {t["name"]: t for t in data["model"]["tables"]}
        assert "dim_date" in tables
        assert "dim_policy" in tables
        assert "dim_customer" in tables
        assert "fact_claims_adjudication" in tables

        fact_cols = [c["name"] for c in tables["fact_claims_adjudication"]["columns"]]
        assert "claim_id" in fact_cols
        assert "policy_id" in fact_cols
        assert "customer_id" in fact_cols
        assert "date_key" in fact_cols
        assert "is_straight_through_approved" in fact_cols
        assert "fraud_loss_avoidance" in fact_cols

    def test_model_relationships_cardinality(self):
        with open(SEMANTIC_MODEL_JSON, encoding="utf-8") as f:
            data = json.load(f)
        relationships = data["model"]["relationships"]
        assert len(relationships) >= 3
        for rel in relationships:
            assert rel["toTable"].startswith("dim_")
            assert rel["fromTable"] == "fact_claims_adjudication"
            assert rel["cardinality"] == "manyToOne"
            assert rel["crossFilteringBehavior"] == "singleDirection"


class TestSemanticDataExportsAndIntegrity:
    """Validates generated CSV extracts and star-schema referential integrity."""

    def test_exported_csv_files_exist(self):
        for name in [
            "dim_customer.csv",
            "dim_policy.csv",
            "dim_date.csv",
            "fact_claims_adjudication.csv",
        ]:
            p = SEMANTIC_DATA_DIR / name
            assert p.is_file()
            assert p.stat().st_size > 0

    def test_referential_integrity_foreign_keys(self):
        df_claims = pd.read_csv(SEMANTIC_DATA_DIR / "fact_claims_adjudication.csv")
        df_policy = pd.read_csv(SEMANTIC_DATA_DIR / "dim_policy.csv")
        df_customer = pd.read_csv(SEMANTIC_DATA_DIR / "dim_customer.csv")
        df_date = pd.read_csv(SEMANTIC_DATA_DIR / "dim_date.csv")

        # Zero orphan foreign keys
        assert len(set(df_claims["policy_id"]) - set(df_policy["policy_id"])) == 0
        assert len(set(df_claims["customer_id"]) - set(df_customer["customer_id"])) == 0
        assert len(set(df_claims["date_key"]) - set(df_date["date_key"])) == 0

    def test_summary_metrics_values(self):
        with open(SEMANTIC_DATA_DIR / "summary_metrics.json", encoding="utf-8") as f:
            metrics = json.load(f)
        kpi = metrics["kpi_metrics"]
        assert kpi["total_claims_filed"] >= 8000
        assert kpi["fraud_incidents_detected"] > 0
        assert 1.0 <= kpi["fraud_rate_pct"] <= 10.0
        assert kpi["fraud_loss_avoidance_usd"] > 1000000.0
        assert kpi["average_settlement_lag_days"] > 0
