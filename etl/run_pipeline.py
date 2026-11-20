"""
etl/run_pipeline.py
===================
CLI Pipeline Orchestrator for the Insurance Claims Platform.
Coordinates extraction, cleansing, validation, quarantine segregation,
and warehouse staging file generation.

Usage:
    python etl/run_pipeline.py --mode full --source local
    python etl/run_pipeline.py --mode incremental --source api
"""

import argparse
import contextlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.config.settings import settings  # noqa: E402
from etl.pipeline.extractor import ApiExtractor  # noqa: E402
from etl.pipeline.state_manager import state_manager  # noqa: E402
from etl.pipeline.transformer import claims_transformer  # noqa: E402
from etl.pipeline.validator import CleanCustomerModel, CleanPolicyModel  # noqa: E402
from etl.utils.logging import logger  # noqa: E402


class PipelineRunner:
    """Orchestrates end-to-end data pipeline execution from raw sources to warehouse staging."""

    def __init__(self, mode: str = "incremental", source: str = "local") -> None:
        self.mode = mode
        self.source = source
        self.staging_dir = settings.staging_dir
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def load_local_data(self) -> dict[str, list[dict[str, Any]]]:
        """Loads raw data from disk for offline or local pipeline execution."""
        mock_dir = PROJECT_ROOT / "mock_api" / "data"
        raw_dir = PROJECT_ROOT / "data" / "raw"

        # Check mock_api/data first, fallback to data/raw
        source_dir = mock_dir if (mock_dir / "claims.json").exists() else raw_dir

        logger.info("Loading local source data", source_dir=str(source_dir))

        def read_file(name: str) -> list[dict[str, Any]]:
            json_file = source_dir / f"{name}.json"
            csv_file = source_dir / f"{name}.csv"
            if json_file.exists():
                with open(json_file, encoding="utf-8") as f:
                    return json.load(f)
            elif csv_file.exists():
                df = pd.read_csv(csv_file)
                return df.to_dict(orient="records")
            else:
                raise FileNotFoundError(f"Source file {name} not found in {source_dir}")

        return {
            "customers": read_file("customers"),
            "policies": read_file("policies"),
            "claims": read_file("claims"),
        }

    def run_pipeline(self) -> dict[str, Any]:
        """Executes all ETL phases and generates staging datasets."""
        start_time = time.time()
        logger.info(
            "=== Starting Insurance Platform Ingestion Pipeline ===",
            mode=self.mode,
            source=self.source,
        )

        # ── Phase 1: Ingestion / Extraction ─────────────────────────
        if self.source == "api":
            logger.info("Phase 1: Extracting data from live Mock Core API...")
            extractor = ApiExtractor()
            is_incremental = self.mode == "incremental"
            raw_data = extractor.extract_all(incremental_claims=is_incremental)
        else:
            logger.info("Phase 1: Loading raw data from local storage...")
            raw_data = self.load_local_data()

        raw_customers = raw_data["customers"]
        raw_policies = raw_data["policies"]
        raw_claims = raw_data["claims"]

        # ── Phase 2: Cleansing, Validation & Segregation ────────────
        logger.info("Phase 2: Cleansing, validating, and segregating claims...")
        claim_results = claims_transformer.process_claims(
            raw_claims, persist_to_disk=True
        )
        clean_claims = claim_results["clean_records"]
        rejected_claims = claim_results["rejected_records"]
        claim_metrics = claim_results["metrics"]

        # Validate customers (drop corrupt, preserve valid)
        clean_customers: list[dict[str, Any]] = []
        for c in raw_customers:
            with contextlib.suppress(Exception):
                clean_customers.append(CleanCustomerModel(**c).model_dump())

        # Validate policies
        clean_policies: list[dict[str, Any]] = []
        for p in raw_policies:
            with contextlib.suppress(Exception):
                clean_policies.append(CleanPolicyModel(**p).model_dump())

        # ── Phase 3: Staging Layer Generation ───────────────────────
        logger.info(
            "Phase 3: Generating warehouse staging datasets in data/staging/..."
        )
        stg_claims_path = self.staging_dir / "stg_claims.csv"
        stg_rejected_path = self.staging_dir / "stg_claims_rejected.csv"
        stg_customers_path = self.staging_dir / "stg_customers.csv"
        stg_policies_path = self.staging_dir / "stg_policies.csv"

        if clean_claims:
            pd.DataFrame(clean_claims).to_csv(stg_claims_path, index=False)
        if rejected_claims:
            pd.DataFrame(rejected_claims).to_csv(stg_rejected_path, index=False)
        if clean_customers:
            pd.DataFrame(clean_customers).to_csv(stg_customers_path, index=False)
        if clean_policies:
            pd.DataFrame(clean_policies).to_csv(stg_policies_path, index=False)

        # ── Phase 4: State & High-Watermark Updates ──────────────────
        if clean_claims and self.mode == "incremental":
            latest_watermark = max(
                c.get("created_at") or c.get("filing_date") for c in clean_claims
            )
            state_manager.update_watermark(
                "claims", latest_watermark, len(clean_claims)
            )

        total_elapsed = round(time.time() - start_time, 2)

        summary = {
            "execution_status": "SUCCESS",
            "mode": self.mode,
            "source": self.source,
            "elapsed_seconds": total_elapsed,
            "raw_counts": {
                "customers": len(raw_customers),
                "policies": len(raw_policies),
                "claims": len(raw_claims),
            },
            "staging_counts": {
                "stg_customers": len(clean_customers),
                "stg_policies": len(clean_policies),
                "stg_claims": len(clean_claims),
                "stg_claims_rejected": len(rejected_claims),
            },
            "claims_metrics": claim_metrics,
        }

        self.print_reconciliation_report(summary)
        return summary

    @staticmethod
    def print_reconciliation_report(summary: dict[str, Any]) -> None:
        """Prints a human-readable executive data reconciliation summary."""
        raw = summary["raw_counts"]
        stg = summary["staging_counts"]
        metrics = summary["claims_metrics"]

        print("\n" + "=" * 70)
        print("  INSURANCE CLAIMS PLATFORM — DATA RECONCILIATION AUDIT REPORT")
        print("=" * 70)
        print(f"  Execution Status:      {summary['execution_status']}")
        print(f"  Pipeline Mode:         {summary['mode'].upper()}")
        print(f"  Source Mode:           {summary['source'].upper()}")
        print(f"  Processing Time:       {summary['elapsed_seconds']} seconds")
        print("-" * 70)
        print("  ENTITY RECONCILIATION:")
        print(
            f"    Customers Ingested:  {raw['customers']:>6}  -->  Staged: {stg['stg_customers']:>6}"
        )
        print(
            f"    Policies Ingested:   {raw['policies']:>6}  -->  Staged: {stg['stg_policies']:>6}"
        )
        print(
            f"    Claims Ingested:     {raw['claims']:>6}  -->  Staged: {stg['stg_claims']:>6}"
        )
        print("-" * 70)
        print("  CLAIMS QUALITY GATE BREAKDOWN:")
        print(f"    Total Raw Claims:    {metrics['total_records']:>6}")
        print(
            f"    Clean Claims:        {metrics['clean_records']:>6}  ({metrics['clean_rate_pct']}%)"
        )
        print(
            f"    Quarantined Claims:  {metrics['rejected_records']:>6}  ({round(100 - metrics['clean_rate_pct'], 2)}%)"
        )
        print("-" * 70)
        print("  DEAD-LETTER REJECTION ROOT CAUSES:")
        for reason, count in metrics["rejection_breakdown"].items():
            display_reason = reason if reason else "CROSS_FIELD_LOGIC_ERROR"
            print(f"    - {display_reason:<32} : {count:>5} records")
        print("-" * 70)
        print(f"  Staging Output Directory: {settings.staging_dir}")
        print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Insurance Claims Platform ETL Orchestrator"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="Extraction mode (default: incremental)",
    )
    parser.add_argument(
        "--source",
        choices=["local", "api"],
        default="local",
        help="Data source mode: 'local' (offline files) or 'api' (live Mock API)",
    )

    args = parser.parse_args()
    runner = PipelineRunner(mode=args.mode, source=args.source)
    runner.run_pipeline()


if __name__ == "__main__":
    main()
