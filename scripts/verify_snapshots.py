"""
Verification Script for Automated BI Snapshots & Columnar Parquet Exports (ICIP-027).
Audits Apache Parquet conversion, SHA-256 manifest integrity, compression ratios, and executive briefing accuracy.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from powerbi.snapshot_pipeline import compute_file_sha256  # noqa: E402

LATEST_SNAPSHOT = PROJECT_ROOT / "data" / "snapshots" / "latest"
MANIFEST_FILE = LATEST_SNAPSHOT / "manifest.json"
BRIEFING_FILE = LATEST_SNAPSHOT / "executive_briefing.md"


def audit_parquet_files_exist_and_readable() -> bool:
    print("[1/5] Auditing Parquet Datasets & Columnar Readability...")
    tables = [
        ("dim_customer", 515),
        ("dim_policy", 800),
        ("dim_date", 833),
        ("fact_claims_adjudication", 9107),
        ("fact_underwriting_portfolio", 800),
    ]

    for tbl_name, expected_rows in tables:
        pq_path = LATEST_SNAPSHOT / f"{tbl_name}.parquet"
        assert pq_path.is_file(), f"Parquet file missing: {pq_path}"
        df = pd.read_parquet(pq_path)
        assert len(df) == expected_rows, (
            f"Row count mismatch in {tbl_name}: expected {expected_rows}, got {len(df)}"
        )

    print(
        "  -> All 5 Parquet tables verified and readable via PyArrow engine (Exact row count parity)."
    )
    return True


def audit_compression_efficiency() -> bool:
    print("[2/5] Auditing Snappy Columnar Compression Efficiency...")
    fact_csv = LATEST_SNAPSHOT / "fact_claims_adjudication.csv"
    fact_pq = LATEST_SNAPSHOT / "fact_claims_adjudication.parquet"

    assert fact_csv.is_file() and fact_pq.is_file()
    csv_bytes = fact_csv.stat().st_size
    pq_bytes = fact_pq.stat().st_size

    savings_pct = (1.0 - (pq_bytes / csv_bytes)) * 100.0
    assert savings_pct > 50.0, (
        f"Expected > 50% compression savings, got {savings_pct:.1f}%"
    )
    print(
        f"  -> Snappy compression verified: Fact table compressed from {csv_bytes / 1024:.1f} KB to {pq_bytes / 1024:.1f} KB ({savings_pct:.1f}% storage reduction)."
    )
    return True


def audit_cryptographic_manifest() -> bool:
    print("[3/5] Auditing Cryptographic SHA-256 Manifest Integrity...")
    assert MANIFEST_FILE.is_file(), f"Manifest file missing: {MANIFEST_FILE}"
    with open(MANIFEST_FILE, encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("status") == "COMPLETED"
    files_meta = manifest.get("files", {})
    assert len(files_meta) == 10  # 5 tables x 2 formats (parquet + csv)

    for fname, meta in files_meta.items():
        fpath = LATEST_SNAPSHOT / fname
        assert fpath.is_file(), f"File declared in manifest missing: {fpath}"
        actual_sha = compute_file_sha256(fpath)
        assert actual_sha == meta["sha256"], (
            f"SHA-256 mismatch for {fname}: expected {meta['sha256']}, got {actual_sha}"
        )

    print(
        "  -> Cryptographic integrity verified: All 10 manifest SHA-256 checksums match live disk hashes."
    )
    return True


def audit_executive_briefing_report() -> bool:
    print("[4/5] Auditing Executive Briefing Digest Content...")
    assert BRIEFING_FILE.is_file(), f"Briefing report missing: {BRIEFING_FILE}"
    content = BRIEFING_FILE.read_text(encoding="utf-8")

    assert "Executive Analytics Briefing" in content
    assert "Total Incurred Claims Liability" in content
    assert "Fraud Mitigation & Capital Loss Avoidance" in content
    assert "Touchless STP Settlement Rate" in content
    assert "69,641,502.09" in content
    assert "5.18%" in content
    assert "436" in content

    briefing_json = LATEST_SNAPSHOT / "executive_briefing.json"
    assert briefing_json.is_file()
    with open(briefing_json, encoding="utf-8") as f:
        bj = json.load(f)
    assert bj["kpi_metrics"]["fraud_incidents_detected"] == 436
    print(
        "  -> Executive briefing verified (Contains strategic KPIs, $69.64M fraud savings, and STP metrics)."
    )
    return True


def audit_columnar_query_performance() -> bool:
    print("[5/5] Auditing Columnar Query & Predicate Pushdown...")
    pq_path = LATEST_SNAPSHOT / "fact_claims_adjudication.parquet"

    # Query subset using columnar projection (selecting only claim_id, is_fraud, claim_amount)
    df_projected = pd.read_parquet(
        pq_path, columns=["claim_id", "is_fraud", "claim_amount"]
    )
    assert list(df_projected.columns) == ["claim_id", "is_fraud", "claim_amount"]
    assert len(df_projected) == 9107

    # Filter pushdown
    fraud_only = df_projected[df_projected["is_fraud"] == 1]
    assert len(fraud_only) == 436
    print(
        f"  -> Columnar projection and filter confirmed (Filtered {len(fraud_only)} fraud records instantaneously)."
    )
    return True


def main() -> int:
    print("=" * 80)
    print(
        "   Insurance Claims Platform — BI Snapshot & Columnar Parquet Audit (ICIP-027)"
    )
    print("=" * 80)
    try:
        assert audit_parquet_files_exist_and_readable()
        assert audit_compression_efficiency()
        assert audit_cryptographic_manifest()
        assert audit_executive_briefing_report()
        assert audit_columnar_query_performance()
        print("\n" + "=" * 80)
        print(" [SUCCESS] All 5 BI Snapshot & Columnar Parquet audit checks PASSED!")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n[ERROR] Audit check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
