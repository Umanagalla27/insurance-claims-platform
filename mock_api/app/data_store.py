"""
mock_api/app/data_store.py
==========================
In-memory dataset storage and query engine for Mock API.
Loads synthetic JSON datasets into memory for fast, filtered, paginated access.
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from mock_api.app.models.schemas import PaginationMeta

# Path to mock data files
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class DataStore:
    """Manages synthetic records in memory with indexed lookups and filtering."""

    def __init__(self) -> None:
        self.customers: list[dict[str, Any]] = []
        self.policies: list[dict[str, Any]] = []
        self.claims: list[dict[str, Any]] = []

        self.customers_by_id: dict[str, dict[str, Any]] = {}
        self.policies_by_id: dict[str, dict[str, Any]] = {}
        self.claims_by_id: dict[str, dict[str, Any]] = {}

        self.is_loaded: bool = False

    def load_data(self) -> None:
        """Loads JSON files from disk into memory."""
        cust_path = DATA_DIR / "customers.json"
        pol_path = DATA_DIR / "policies.json"
        claim_path = DATA_DIR / "claims.json"

        if not (cust_path.exists() and pol_path.exists() and claim_path.exists()):
            raise FileNotFoundError(
                f"Mock data files not found in {DATA_DIR}. "
                "Run 'python data_generator/run_all.py' to generate seed data."
            )

        with open(cust_path, encoding="utf-8") as f:
            self.customers = json.load(f)
            self.customers_by_id = {c["customer_id"]: c for c in self.customers}

        with open(pol_path, encoding="utf-8") as f:
            self.policies = json.load(f)
            self.policies_by_id = {p["policy_id"]: p for p in self.policies}

        with open(claim_path, encoding="utf-8") as f:
            self.claims = json.load(f)
            self.claims_by_id = {c["claim_id"]: c for c in self.claims}

        self.is_loaded = True

    @staticmethod
    def paginate(
        items: list[Any], page: int, page_size: int
    ) -> tuple[list[Any], PaginationMeta]:
        """Calculates page slices and pagination metadata."""
        total_records = len(items)
        total_pages = max(1, math.ceil(total_records / page_size))
        page = max(1, min(page, total_pages)) if total_records > 0 else 1

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        sliced_items = items[start_idx:end_idx]

        meta = PaginationMeta(
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )
        return sliced_items, meta

    def get_customers(
        self,
        state: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], PaginationMeta]:
        """Filters and paginates customers."""
        results = self.customers
        if state:
            results = [
                c for c in results if c.get("state", "").upper() == state.upper()
            ]
        return self.paginate(results, page, page_size)

    def get_policies(
        self,
        customer_id: str | None = None,
        status: str | None = None,
        policy_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], PaginationMeta]:
        """Filters and paginates policies."""
        results = self.policies
        if customer_id:
            results = [p for p in results if p.get("customer_id") == customer_id]
        if status:
            results = [
                p for p in results if p.get("status", "").lower() == status.lower()
            ]
        if policy_type:
            results = [
                p
                for p in results
                if p.get("policy_type", "").lower() == policy_type.lower()
            ]
        return self.paginate(results, page, page_size)

    def get_claims(
        self,
        status: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        since_date: str | None = None,
        state: str | None = None,
        policy_id: str | None = None,
        customer_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], PaginationMeta]:
        """
        Filters and paginates claims.
        Crucial for Sprint 2: `since_date` enables incremental ETL loads!
        """
        results = self.claims

        if status:
            results = [
                c for c in results if c.get("status", "").lower() == status.lower()
            ]
        if category:
            results = [
                c
                for c in results
                if c.get("claim_category", "").lower() == category.lower()
            ]
        if priority:
            results = [
                c
                for c in results
                if c.get("claim_priority", "").lower() == priority.lower()
            ]
        if state:
            results = [
                c for c in results if (c.get("state") or "").upper() == state.upper()
            ]
        if policy_id:
            results = [c for c in results if c.get("policy_id") == policy_id]
        if customer_id:
            results = [c for c in results if c.get("customer_id") == customer_id]
        if since_date:
            # Filter claims created or filed on or after since_date (ISO format YYYY-MM-DD)
            results = [
                c
                for c in results
                if (c.get("created_at") or c.get("filing_date", "")) >= since_date
            ]

        return self.paginate(results, page, page_size)

    def add_claim(self, claim_data: dict[str, Any]) -> dict[str, Any]:
        """Appends a new claim into the in-memory store."""
        new_id = f"CLM-{len(self.claims) + 1:05d}"
        now_iso = datetime.now().isoformat()

        record = {
            "claim_id": new_id,
            "policy_id": claim_data["policy_id"],
            "customer_id": claim_data["customer_id"],
            "claim_category": claim_data["claim_category"],
            "claim_priority": claim_data.get("claim_priority", "Medium"),
            "claim_amount": claim_data["claim_amount"],
            "approved_amount": None,
            "incident_date": claim_data["incident_date"],
            "filing_date": now_iso[:10],
            "status": "Pending",
            "state": claim_data.get("state"),
            "description": claim_data.get("description"),
            "is_fraud": 0,
            "fraud_reason": None,
            "created_at": now_iso,
        }

        self.claims.insert(0, record)
        self.claims_by_id[new_id] = record
        return record


# Global singleton instance
store = DataStore()
