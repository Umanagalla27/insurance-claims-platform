"""
etl/pipeline/transformer.py
===========================
Data Transformation, Validation, and Quarantine Engine.
Separates clean records from dirty/corrupted records without dropping data.
Routes rejected records to a dead-letter quarantine store with exact diagnostic reasons.
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from etl.config.settings import settings
from etl.pipeline.cleanser import DataCleanser
from etl.pipeline.validator import CleanClaimModel, RejectionRecord
from etl.utils.logging import logger


class ClaimsTransformer:
    """Transforms, cleanses, and validates claims data into clean and quarantine streams."""

    def __init__(
        self,
        processed_dir: Path | None = None,
        quarantine_dir: Path | None = None,
    ) -> None:
        self.processed_dir = processed_dir or settings.processed_dir
        self.quarantine_dir = quarantine_dir or settings.quarantine_dir

        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def process_claims(
        self,
        raw_claims: list[dict[str, Any]],
        persist_to_disk: bool = True,
    ) -> dict[str, Any]:
        """
        Executes end-to-end processing:
        1. De-duplication check
        2. Date & text normalization
        3. Pydantic schema validation
        4. Segregation into clean vs quarantine
        5. File persistence & metric generation
        """
        clean_records: list[dict[str, Any]] = []
        rejected_records: list[dict[str, Any]] = []
        rejection_reasons: list[str] = []

        seen_claim_ids: set[str] = set()
        now_iso = datetime.now().isoformat()

        logger.info(
            "Beginning claims transformation and validation", raw_count=len(raw_claims)
        )

        for raw in raw_claims:
            claim_id = raw.get("claim_id")

            # 1. De-duplication Gate
            if claim_id in seen_claim_ids:
                reason = "DUPLICATE_RECORD: Claim ID already processed in this batch"
                rejection = RejectionRecord(
                    record_id=claim_id,
                    entity_name="claims",
                    rejected_at=now_iso,
                    rejection_reason=reason,
                    raw_payload=raw,
                )
                rejected_records.append(rejection.model_dump())
                rejection_reasons.append("DUPLICATE_RECORD")
                continue

            seen_claim_ids.add(claim_id)

            # 2. Cleansing & Normalization
            cleansed = DataCleanser.cleanse_claim_record(raw)

            # 3. Strict Schema Validation
            try:
                validated = CleanClaimModel(**cleansed)
                clean_records.append(validated.model_dump())
            except ValidationError as ve:
                # Format descriptive error list
                err_messages = []
                for err in ve.errors():
                    field = ".".join(str(loc) for loc in err["loc"])
                    msg = err["msg"]
                    err_messages.append(f"[{field}] {msg}")

                full_reason = "; ".join(err_messages)
                primary_reason = err_messages[0].split("]")[0].strip("[")

                rejection = RejectionRecord(
                    record_id=claim_id,
                    entity_name="claims",
                    rejected_at=now_iso,
                    rejection_reason=full_reason,
                    raw_payload=raw,
                )
                rejected_records.append(rejection.model_dump())
                rejection_reasons.append(primary_reason)

        # 4. Optional Persistence to Disk
        if persist_to_disk:
            self._persist_datasets(clean_records, rejected_records)

        # 5. Calculate Metrics
        total = len(raw_claims)
        clean_count = len(clean_records)
        rejected_count = len(rejected_records)
        clean_rate = (clean_count / total * 100) if total > 0 else 0.0

        reasons_breakdown = dict(Counter(rejection_reasons))

        metrics = {
            "total_records": total,
            "clean_records": clean_count,
            "rejected_records": rejected_count,
            "clean_rate_pct": round(clean_rate, 2),
            "rejection_breakdown": reasons_breakdown,
        }

        logger.info(
            "Transformation & validation complete",
            total_records=total,
            clean_records=clean_count,
            quarantined_records=rejected_count,
            clean_rate_pct=metrics["clean_rate_pct"],
        )

        return {
            "clean_records": clean_records,
            "rejected_records": rejected_records,
            "metrics": metrics,
        }

    def _persist_datasets(
        self,
        clean_records: list[dict[str, Any]],
        rejected_records: list[dict[str, Any]],
    ) -> None:
        """Saves clean data and dead-letter quarantine datasets to CSV and JSON."""
        # Clean paths
        clean_json = self.processed_dir / "claims_clean.json"
        clean_csv = self.processed_dir / "claims_clean.csv"

        # Quarantine paths
        quarantine_json = self.quarantine_dir / "claims_rejected.json"
        quarantine_csv = self.quarantine_dir / "claims_rejected.csv"

        # 1. Write clean records
        with open(clean_json, "w", encoding="utf-8") as f:
            json.dump(clean_records, f, indent=2)
        if clean_records:
            pd.DataFrame(clean_records).to_csv(clean_csv, index=False)

        # 2. Write quarantined records
        with open(quarantine_json, "w", encoding="utf-8") as f:
            json.dump(rejected_records, f, indent=2)
        if rejected_records:
            pd.DataFrame(rejected_records).to_csv(quarantine_csv, index=False)

        logger.info(
            "Persisted clean and quarantine datasets",
            clean_json=str(clean_json),
            quarantine_json=str(quarantine_json),
        )


# Global instance
claims_transformer = ClaimsTransformer()
