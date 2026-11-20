"""
etl/tests/test_validator_and_cleanser.py
========================================
Unit tests for data cleansing, Pydantic validation, and dead-letter quarantine.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from etl.pipeline.cleanser import DataCleanser
from etl.pipeline.transformer import ClaimsTransformer
from etl.pipeline.validator import CleanClaimModel


def test_date_normalization():
    """Verify cleanser standardizes non-ISO date formats to YYYY-MM-DD."""
    assert DataCleanser.normalize_date("05/14/2025") == "2025-05-14"
    assert DataCleanser.normalize_date("12/01/2024") == "2024-12-01"
    assert DataCleanser.normalize_date("2026-03-20") == "2026-03-20"
    assert DataCleanser.normalize_date("2026-03-20T14:30:00") == "2026-03-20"
    assert DataCleanser.normalize_date(None) is None


def test_clean_claim_model_valid():
    """Verify valid claim payload passes Pydantic schema validation."""
    valid_payload = {
        "claim_id": "CLM-00001",
        "policy_id": "POL-00001",
        "customer_id": "CUST-0001",
        "claim_category": "Auto",
        "claim_priority": "High",
        "claim_amount": 4500.0,
        "approved_amount": 4000.0,
        "incident_date": "2026-01-10",
        "filing_date": "2026-01-15",
        "status": "Approved",
        "state": "CA",
        "description": "Rear-end collision at intersection.",
        "is_fraud": 0,
        "fraud_reason": None,
        "created_at": "2026-01-15T09:00:00",
    }
    model = CleanClaimModel(**valid_payload)
    assert model.claim_id == "CLM-00001"
    assert model.claim_amount == 4500.0


def test_invalid_negative_amount_fails():
    """Verify negative and zero amounts are rejected."""
    bad_payload = {
        "claim_id": "CLM-00002",
        "policy_id": "POL-00001",
        "customer_id": "CUST-0001",
        "claim_category": "Auto",
        "claim_priority": "Medium",
        "claim_amount": -1500.0,  # Negative amount!
        "incident_date": "2026-01-10",
        "filing_date": "2026-01-15",
        "status": "Pending",
        "state": "TX",
        "description": "Minor fender bender.",
        "created_at": "2026-01-15T09:00:00",
    }
    with pytest.raises(ValidationError) as exc:
        CleanClaimModel(**bad_payload)
    assert "claim_amount" in str(exc.value)


def test_cross_field_date_logic_fails():
    """Verify filing_date earlier than incident_date is rejected."""
    bad_dates_payload = {
        "claim_id": "CLM-00003",
        "policy_id": "POL-00001",
        "customer_id": "CUST-0001",
        "claim_category": "Auto",
        "claim_priority": "Medium",
        "claim_amount": 2500.0,
        "incident_date": "2026-02-20",
        "filing_date": "2026-02-10",  # 10 days before incident!
        "status": "Pending",
        "state": "FL",
        "description": "Vehicle hail damage.",
        "created_at": "2026-02-10T09:00:00",
    }
    with pytest.raises(ValidationError) as exc:
        CleanClaimModel(**bad_dates_payload)
    assert "cannot be earlier than incident date" in str(exc.value)


def test_transformer_segregates_clean_and_quarantine(tmp_path: Path):
    """Verify ClaimsTransformer splits clean from corrupt records and records reasons."""
    transformer = ClaimsTransformer(
        processed_dir=tmp_path / "processed", quarantine_dir=tmp_path / "quarantine"
    )

    records = [
        # Record 1: Clean
        {
            "claim_id": "CLM-00010",
            "policy_id": "POL-00001",
            "customer_id": "CUST-0001",
            "claim_category": "Auto",
            "claim_priority": "Medium",
            "claim_amount": 3000.0,
            "incident_date": "2026-01-10",
            "filing_date": "2026-01-12",
            "status": "Pending",
            "state": "NY",
            "description": "Valid claim description.",
            "created_at": "2026-01-12T00:00:00",
        },
        # Record 2: Non-ISO date (cleanser will fix this)
        {
            "claim_id": "CLM-00011",
            "policy_id": "POL-00001",
            "customer_id": "CUST-0001",
            "claim_category": "Medical",
            "claim_priority": "High",
            "claim_amount": 5500.0,
            "incident_date": "03/15/2026",  # Slash format
            "filing_date": "03/18/2026",
            "status": "Pending",
            "state": "ca",  # Lowercase state
            "description": "Emergency clinic visit.",
            "created_at": "2026-03-18T00:00:00",
        },
        # Record 3: Duplicate of CLM-00010 (must be quarantined)
        {
            "claim_id": "CLM-00010",
            "policy_id": "POL-00001",
            "customer_id": "CUST-0001",
            "claim_category": "Auto",
            "claim_priority": "Medium",
            "claim_amount": 3000.0,
            "incident_date": "2026-01-10",
            "filing_date": "2026-01-12",
            "status": "Pending",
            "state": "NY",
            "description": "Duplicate submission.",
            "created_at": "2026-01-12T00:00:00",
        },
        # Record 4: Negative amount (must be quarantined)
        {
            "claim_id": "CLM-00012",
            "policy_id": "POL-00001",
            "customer_id": "CUST-0001",
            "claim_category": "Auto",
            "claim_priority": "Low",
            "claim_amount": -500.0,
            "incident_date": "2026-01-10",
            "filing_date": "2026-01-12",
            "status": "Pending",
            "state": "IL",
            "description": "Negative amount claim.",
            "created_at": "2026-01-12T00:00:00",
        },
    ]

    result = transformer.process_claims(records, persist_to_disk=True)

    assert len(result["clean_records"]) == 2  # Records 1 & 2
    assert len(result["rejected_records"]) == 2  # Records 3 & 4

    # Verify clean record 2 was cleansed
    clean_rec_2 = result["clean_records"][1]
    assert clean_rec_2["incident_date"] == "2026-03-15"
    assert clean_rec_2["state"] == "CA"

    # Verify rejection reasons
    reasons = [r["rejection_reason"] for r in result["rejected_records"]]
    assert any("DUPLICATE_RECORD" in r for r in reasons)
    assert any("claim_amount" in r for r in reasons)

    # Verify disk files created
    assert (tmp_path / "processed" / "claims_clean.json").exists()
    assert (tmp_path / "quarantine" / "claims_rejected.json").exists()
