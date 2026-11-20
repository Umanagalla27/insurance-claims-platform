"""
Automated Pytest Suite for BI Snapshots, Columnar Parquet Exports & Executive Briefings (ICIP-027).
Validates Apache Parquet conversion, Snappy compression savings, cryptographic SHA-256 manifests,
and executive briefing metrics consistency.
"""

import json
from pathlib import Path

import pandas as pd

from powerbi.snapshot_pipeline import compute_file_sha256

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LATEST_SNAPSHOT = PROJECT_ROOT / "data" / "snapshots" / "latest"
MANIFEST_FILE = LATEST_SNAPSHOT / "manifest.json"
BRIEFING_MD = LATEST_SNAPSHOT / "executive_briefing.md"
BRIEFING_JSON = LATEST_SNAPSHOT / "executive_briefing.json"


class TestParquetColumnarStorage:
    """Validates Apache Parquet datasets and columnar schema typing."""

    def test_parquet_files_exist(self):
        expected_tables = [
            "dim_customer",
            "dim_policy",
            "dim_date",
            "fact_claims_adjudication",
            "fact_underwriting_portfolio",
        ]
        for tbl in expected_tables:
            pq_file = LATEST_SNAPSHOT / f"{tbl}.parquet"
            assert pq_file.is_file()
            assert pq_file.stat().st_size > 0

    def test_parquet_exact_row_count_parity(self):
        df_claims = pd.read_parquet(
            LATEST_SNAPSHOT / "fact_claims_adjudication.parquet"
        )
        df_customer = pd.read_parquet(LATEST_SNAPSHOT / "dim_customer.parquet")
        df_policy = pd.read_parquet(LATEST_SNAPSHOT / "dim_policy.parquet")

        assert len(df_claims) == 9107
        assert len(df_customer) == 515
        assert len(df_policy) == 800

    def test_parquet_columnar_types(self):
        df_claims = pd.read_parquet(
            LATEST_SNAPSHOT / "fact_claims_adjudication.parquet"
        )
        assert pd.api.types.is_float_dtype(df_claims["claim_amount"])
        assert pd.api.types.is_float_dtype(df_claims["approved_amount"])
        assert pd.api.types.is_integer_dtype(df_claims["is_fraud"])
        assert pd.api.types.is_integer_dtype(df_claims["is_straight_through_approved"])
        assert pd.api.types.is_string_dtype(df_claims["claim_id"])


class TestCompressionAndPerformance:
    """Validates Snappy compression ratio and columnar query pushdown."""

    def test_snappy_compression_ratio(self):
        fact_csv = LATEST_SNAPSHOT / "fact_claims_adjudication.csv"
        fact_pq = LATEST_SNAPSHOT / "fact_claims_adjudication.parquet"

        csv_sz = fact_csv.stat().st_size
        pq_sz = fact_pq.stat().st_size
        savings_pct = (1.0 - (pq_sz / csv_sz)) * 100.0

        # Snappy compression must reduce size by at least 50%
        assert savings_pct > 50.0

    def test_columnar_projection_and_filtering(self):
        pq_path = LATEST_SNAPSHOT / "fact_claims_adjudication.parquet"
        df = pd.read_parquet(
            pq_path, columns=["claim_category", "is_straight_through_approved"]
        )
        assert list(df.columns) == ["claim_category", "is_straight_through_approved"]
        assert len(df) == 9107

        stp_count = df["is_straight_through_approved"].sum()
        assert stp_count > 400


class TestCryptographicManifest:
    """Validates snapshot manifest metadata and SHA-256 hashes."""

    def test_manifest_schema_and_metadata(self):
        assert MANIFEST_FILE.is_file()
        with open(MANIFEST_FILE, encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest.get("status") == "COMPLETED"
        assert manifest.get("tables_count") == 5
        assert manifest.get("total_files") == 10
        assert "kpi_metrics" in manifest

    def test_sha256_checksum_verification(self):
        with open(MANIFEST_FILE, encoding="utf-8") as f:
            manifest = json.load(f)

        for fname, meta in manifest["files"].items():
            fpath = LATEST_SNAPSHOT / fname
            assert fpath.is_file()
            actual_sha = compute_file_sha256(fpath)
            assert actual_sha == meta["sha256"]


class TestExecutiveBriefing:
    """Validates analytical executive briefing content and KPI metrics."""

    def test_briefing_files_exist(self):
        assert BRIEFING_MD.is_file()
        assert BRIEFING_JSON.is_file()

    def test_briefing_content_and_kpis(self):
        md_text = BRIEFING_MD.read_text(encoding="utf-8")
        assert "Executive Analytics Briefing" in md_text
        assert "Total Incurred Claims Liability" in md_text
        assert "Fraud Mitigation & Capital Loss Avoidance" in md_text

        with open(BRIEFING_JSON, encoding="utf-8") as f:
            bj = json.load(f)

        kpi = bj["kpi_metrics"]
        assert kpi["total_claims_filed"] == 9107
        assert kpi["fraud_incidents_detected"] == 436
        assert kpi["fraud_loss_avoidance_usd"] > 60000000.0
        assert kpi["straight_through_processing_count"] >= 400
        assert kpi["average_settlement_lag_days"] > 15.0
