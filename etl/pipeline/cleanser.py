"""
etl/pipeline/cleanser.py
========================
Data cleansing and normalization functions.
Standardizes messy dates, trims whitespace, fixes text casing, and formats numbers
before records reach strict schema validation.
"""

import contextlib
import re
from datetime import datetime
from typing import Any


class DataCleanser:
    """Performs pre-validation standardization on raw incoming records."""

    @staticmethod
    def normalize_date(date_str: Any) -> str | None:
        """
        Standardizes various date formats into ISO 8601 YYYY-MM-DD.
        Handles:
        - MM/DD/YYYY (e.g., '05/14/2025' -> '2025-05-14')
        - YYYY-MM-DD (already standard)
        - Datetime objects or timestamps
        """
        if not date_str:
            return None

        clean_str = str(date_str).strip()

        # Already ISO YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", clean_str):
            return clean_str

        # MM/DD/YYYY or M/D/YYYY
        if "/" in clean_str:
            try:
                dt = datetime.strptime(clean_str, "%m/%d/%Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Try general ISO datetime parsing (e.g. '2025-05-14T10:30:00')
        if "T" in clean_str:
            return clean_str[:10]

        # Return original if unparseable so schema validator raises descriptive error
        return clean_str

    @staticmethod
    def cleanse_string(value: Any) -> str | None:
        """Strips leading/trailing whitespace and normalizes empty strings to None."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @classmethod
    def cleanse_claim_record(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Applies data cleansing rules to a single raw claim payload.
        Mutates a shallow copy to preserve idempotency and avoid altering source data.
        """
        clean = dict(raw)

        # 1. Cleanse dates
        if "incident_date" in clean:
            clean["incident_date"] = cls.normalize_date(clean["incident_date"])
        if "filing_date" in clean:
            clean["filing_date"] = cls.normalize_date(clean["filing_date"])

        # 2. String cleansing
        if "state" in clean and clean["state"]:
            clean["state"] = str(clean["state"]).strip().upper()

        if "description" in clean:
            desc = cls.cleanse_string(clean["description"])
            clean["description"] = (
                desc if desc else "[NO DESCRIPTION PROVIDED - PENDING REVIEW]"
            )

        # 3. Numeric conversions
        if "claim_amount" in clean and clean["claim_amount"] is not None:
            with contextlib.suppress(ValueError, TypeError):
                clean["claim_amount"] = float(clean["claim_amount"])

        if "approved_amount" in clean and clean["approved_amount"] is not None:
            with contextlib.suppress(ValueError, TypeError):
                clean["approved_amount"] = float(clean["approved_amount"])

        return clean
