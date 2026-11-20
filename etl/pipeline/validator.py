"""
etl/pipeline/validator.py
=========================
Pydantic V2 schemas and business validation rules for insurance entities.
Enforces data integrity, value ranges, category enums, and logical date consistency.
Invalid records trigger ValidationError with clear, auditable error reasons.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from data_generator.config import (
    CLAIM_CATEGORIES,
    CLAIM_PRIORITIES,
    CLAIM_STATUSES,
)


class CleanClaimModel(BaseModel):
    """
    Validated and cleansed claim entity ready for warehouse loading.
    Strictly typed with zero tolerance for corrupted values.
    """

    claim_id: str = Field(..., pattern=r"^CLM-\d{5}$")
    policy_id: str = Field(..., pattern=r"^POL-\d{5}$")
    customer_id: str = Field(..., pattern=r"^CUST-\d{4}$")
    claim_category: str
    claim_priority: str
    claim_amount: float = Field(
        ..., gt=0.0, description="Claim amount must be strictly greater than 0"
    )
    approved_amount: float | None = None
    incident_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    filing_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str
    state: str = Field(..., min_length=2, max_length=2)
    description: str
    is_fraud: int = Field(default=0, ge=0, le=1)
    fraud_reason: str | None = None
    created_at: str

    @field_validator("claim_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in CLAIM_CATEGORIES:
            raise ValueError(
                f"Invalid claim category '{v}'. Allowed: {CLAIM_CATEGORIES}"
            )
        return v

    @field_validator("claim_priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in CLAIM_PRIORITIES:
            raise ValueError(
                f"Invalid claim priority '{v}'. Allowed: {CLAIM_PRIORITIES}"
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in CLAIM_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Allowed: {CLAIM_STATUSES}")
        return v

    @field_validator("approved_amount")
    @classmethod
    def validate_approved_amount(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError(f"Approved amount cannot be negative: {v}")
        return v

    @model_validator(mode="after")
    def validate_dates_and_logic(self) -> "CleanClaimModel":
        """
        Cross-field date logic:
        1. incident_date cannot be in the future.
        2. filing_date cannot be before incident_date.
        """
        try:
            inc_dt = date.fromisoformat(self.incident_date)
            file_dt = date.fromisoformat(self.filing_date)
        except ValueError as e:
            raise ValueError(f"Malformed date string: {e}") from e

        today = date.today()
        if inc_dt > today:
            raise ValueError(
                f"Incident date '{self.incident_date}' is in the future (today is {today})"
            )

        if file_dt < inc_dt:
            raise ValueError(
                f"Filing date '{self.filing_date}' cannot be earlier than incident date '{self.incident_date}'"
            )

        return self


class CleanCustomerModel(BaseModel):
    """Validated customer profile entity."""

    customer_id: str = Field(..., pattern=r"^CUST-\d{4}$")
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    address: str
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    postal_code: str
    date_of_birth: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    credit_score: int = Field(..., ge=300, le=850)
    created_at: str


class CleanPolicyModel(BaseModel):
    """Validated insurance policy entity."""

    policy_id: str = Field(..., pattern=r"^POL-\d{5}$")
    customer_id: str = Field(..., pattern=r"^CUST-\d{4}$")
    policy_type: str
    coverage_limit: float = Field(..., gt=0.0)
    deductible: float = Field(..., ge=0.0)
    annual_premium: float = Field(..., gt=0.0)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str
    created_at: str


class RejectionRecord(BaseModel):
    """Dead-letter quarantine record capturing bad data and root cause."""

    record_id: str | None = None
    entity_name: str
    rejected_at: str
    rejection_reason: str
    raw_payload: dict[str, Any]
