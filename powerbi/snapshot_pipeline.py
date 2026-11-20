"""
Automated BI Snapshot Pipeline & Columnar Parquet Exporter (ICIP-027).
Converts Kimball star-schema datasets into Snappy-compressed Apache Parquet format,
computes cryptographic SHA-256 integrity checksums, and compiles executive analytical briefings.
"""

import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("snapshot_pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEMANTIC_DIR = PROJECT_ROOT / "data" / "semantic_layer"
SNAPSHOTS_ROOT = PROJECT_ROOT / "data" / "snapshots"


def compute_file_sha256(filepath: Path) -> str:
    """Compute deterministic SHA-256 cryptographic digest of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_executive_briefing_md(
    kpi: dict, manifest_files: dict, snapshot_id: str
) -> str:
    """Render executive analytical briefing markdown report."""
    now_str = datetime.now(UTC).strftime("%B %d, %Y at %H:%M UTC")

    return f"""# Executive Analytics Briefing & Portfolio Loss Intelligence
**Snapshot Reference**: `{snapshot_id}`
**Published**: {now_str}
**Classification**: Enterprise Confidential — Executive & Actuarial Leadership
**Platform**: Insurance Claims Intelligence Platform (ICIP)

---

## 1. Executive Summary & Financial Highlights

During this reporting period, the platform ingested and processed **{kpi["total_claims_filed"]:,}** claims across conformed personal and commercial lines.

| Core Strategic Metric | Current Platform Metric | Industry Target / Benchmark | Strategic Evaluation |
|---|---|---|---|
| **Total Incurred Claims Liability** | **${kpi["total_incurred_claims_usd"]:,.2f}** | — | Gross portfolio loss exposure |
| **Approved Settlement Payouts** | **${kpi["total_approved_payout_usd"]:,.2f}** | — | Total realized claims disbursements |
| **Total Written / Earned Premium** | **${kpi["total_earned_premium_usd"]:,.2f}** | — | Premium capital base across 800 accounts |
| **Underwriting Loss Ratio %** | **{kpi["overall_loss_ratio_pct"]:.2f}%** | **60.0% - 75.0%** | Key underwriting health indicator |
| **Touchless STP Settlement Rate** | **{kpi["straight_through_processing_rate_pct"]:.2f}%** ({kpi["straight_through_processing_count"]} claims) | **> 15.0%** | Automated adjudication without human touch |
| **Fraud Mitigation Savings** | **${kpi["fraud_loss_avoidance_usd"]:,.2f}** | Maximum capital | Direct capital saved by denying fraud |
| **Portfolio Fraud Incidence Rate** | **{kpi["fraud_rate_pct"]:.2f}%** ({kpi["fraud_incidents_detected"]} claims) | **< 5.0%** | Anomaly screening efficacy |
| **Mean Settlement Lag** | **{kpi["average_settlement_lag_days"]:.1f} Days** | **< 15.0 Days** | Turnaround from incident to filing |

---

## 2. Fraud Mitigation & Capital Loss Avoidance

Our multi-layered fraud defense (combining isolation forest anomaly detection and underwriting constraint validation) successfully intercepted **{kpi["fraud_incidents_detected"]}** fraudulent or highly anomalous claims.

- **Capital Loss Avoidance**: Denying or quarantining these claims protected **${kpi["fraud_loss_avoidance_usd"]:,.2f}** in enterprise capital.
- **Top Fraud Risk Indicators**:
  1. *Exceeds Policy Coverage*: Claims filed above stated aggregate policy limits.
  2. *Round-Number High-Value Anomalies*: Claims with clean round values ($10,000, $25,000) lacking itemized hospital/repair bills.
  3. *Early Inception Filings*: Claims submitted within 14 days of policy inception.
  4. *Narrative Sentiment Mismatch*: Claims whose descriptions conflict with medical/police damage documentation.

---

## 3. Operational Touchless Claims Velocity (STP)

- **Automated Approvals**: **{kpi["straight_through_processing_count"]}** routine claims satisfied all adjudication criteria and settled within 5 business days without requiring adjustor touch.
- **Current STP Rate**: **{kpi["straight_through_processing_rate_pct"]:.2f}%**.
- **Average Customer Settlement Lag**: **{kpi["average_settlement_lag_days"]:.1f} days**.

---

## 4. Downstream Data Catalog & Columnar Parquet Manifest

All snapshot datasets have been converted to high-performance, Snappy-compressed Apache Parquet format for DirectLake consumption in Power BI, Snowflake, and AWS Athena.

```text
{json.dumps(manifest_files, indent=2)}
```
"""


def create_bi_snapshot(
    source_dir: Path = SEMANTIC_DIR,
    snapshots_root: Path = SNAPSHOTS_ROOT,
    snapshot_tag: str | None = None,
) -> dict:
    """Create a complete columnar Parquet and CSV snapshot with cryptographic manifest."""
    if not source_dir.is_dir():
        raise FileNotFoundError(
            f"Source semantic layer directory not found: {source_dir}"
        )

    timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    snapshot_id = snapshot_tag or f"SNP_{timestamp_str}"
    snapshot_dir = snapshots_root / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Initiating snapshot '%s' into: %s", snapshot_id, snapshot_dir)

    # Required tables in star schema
    tables = [
        "dim_customer",
        "dim_policy",
        "dim_date",
        "fact_claims_adjudication",
        "fact_underwriting_portfolio",
    ]

    manifest_files = {}

    for table_name in tables:
        csv_source = source_dir / f"{table_name}.csv"
        if not csv_source.is_file():
            raise FileNotFoundError(f"Source CSV missing: {csv_source}")

        logger.info("Processing table: %s", table_name)
        df = pd.read_csv(csv_source)

        # 1. Export as Snappy-compressed Parquet
        parquet_target = snapshot_dir / f"{table_name}.parquet"
        df.to_parquet(
            parquet_target, engine="pyarrow", compression="snappy", index=False
        )
        parquet_size = parquet_target.stat().st_size
        parquet_sha = compute_file_sha256(parquet_target)

        # 2. Export companion clean CSV
        csv_target = snapshot_dir / f"{table_name}.csv"
        df.to_csv(csv_target, index=False)
        csv_size = csv_target.stat().st_size
        csv_sha = compute_file_sha256(csv_target)

        compression_ratio = (
            round((1.0 - (parquet_size / csv_size)) * 100.0, 1) if csv_size > 0 else 0.0
        )

        manifest_files[f"{table_name}.parquet"] = {
            "format": "parquet",
            "compression": "snappy",
            "row_count": len(df),
            "size_bytes": parquet_size,
            "sha256": parquet_sha,
            "compression_savings_pct": compression_ratio,
        }
        manifest_files[f"{table_name}.csv"] = {
            "format": "csv",
            "row_count": len(df),
            "size_bytes": csv_size,
            "sha256": csv_sha,
        }

        logger.info(
            "  -> %s: %d rows | CSV: %.1f KB | Parquet: %.1f KB (%s%% savings)",
            table_name,
            len(df),
            csv_size / 1024,
            parquet_size / 1024,
            compression_ratio,
        )

    # 3. Load or inherit summary metrics
    metrics_file = source_dir / "summary_metrics.json"
    if metrics_file.is_file():
        with open(metrics_file, encoding="utf-8") as f:
            metrics_data = json.load(f)
        kpi = metrics_data.get("kpi_metrics", {})
    else:
        kpi = {}

    # 4. Generate Executive Briefing Markdown & JSON
    briefing_md = generate_executive_briefing_md(kpi, manifest_files, snapshot_id)
    briefing_path = snapshot_dir / "executive_briefing.md"
    briefing_path.write_text(briefing_md, encoding="utf-8")

    briefing_json_path = snapshot_dir / "executive_briefing.json"
    briefing_json_payload = {
        "snapshot_id": snapshot_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "kpi_metrics": kpi,
        "files": manifest_files,
    }
    briefing_json_path.write_text(
        json.dumps(briefing_json_payload, indent=2), encoding="utf-8"
    )

    # 5. Compile and write manifest.json
    manifest_payload = {
        "snapshot_id": snapshot_id,
        "status": "COMPLETED",
        "generated_at": datetime.now(UTC).isoformat(),
        "storage_format": "Parquet (Snappy) + CSV",
        "tables_count": len(tables),
        "total_files": len(manifest_files),
        "files": manifest_files,
        "kpi_metrics": kpi,
    }
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    # Also symlink / copy to "latest" directory for downstream pipelines
    latest_dir = snapshots_root / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    for fpath in snapshot_dir.glob("*"):
        target_f = latest_dir / fpath.name
        target_f.write_bytes(fpath.read_bytes())

    logger.info(
        "Snapshot completed successfully. Artifacts available in: %s and %s",
        snapshot_dir,
        latest_dir,
    )

    return manifest_payload


def main() -> int:
    try:
        manifest = create_bi_snapshot()
        print("\n" + "=" * 80)
        print("   Insurance Claims Platform — BI Snapshot Pipeline Completed")
        print("=" * 80)
        print(f"   * Snapshot ID   : {manifest['snapshot_id']}")
        print(f"   * Storage Format: {manifest['storage_format']}")
        print(
            f"   * Tables Exported: {manifest['tables_count']} conformed dimensions & facts"
        )
        print("-" * 80)
        print(" Generated Parquet Assets:")
        for fname, meta in manifest["files"].items():
            if meta.get("format") == "parquet":
                print(
                    f"   [x] {fname:<34} | {meta['row_count']:>6,} rows | {meta['size_bytes'] / 1024:>6.1f} KB (Saved {meta['compression_savings_pct']}%)"
                )
        print("-" * 80)
        print(
            f"   [x] Manifest   : data/snapshots/{manifest['snapshot_id']}/manifest.json"
        )
        print(
            f"   [x] Briefing   : data/snapshots/{manifest['snapshot_id']}/executive_briefing.md"
        )
        print("=" * 80 + "\n")
        return 0
    except Exception as e:
        logger.error("Snapshot generation failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
