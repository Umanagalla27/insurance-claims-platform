"""
mock_api/app/models/schemas.py
==============================
Pydantic schemas for request validation and response serialization.
"""

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Metadata describing a paginated response slice."""

    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_records: int = Field(..., description="Total items matching filter criteria")
    total_pages: int = Field(..., description="Total available pages")
    has_next: bool = Field(..., description="True if subsequent page exists")
    has_prev: bool = Field(..., description="True if prior page exists")


class CustomerSchema(BaseModel):
    """Customer profile entity."""

    customer_id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    address: str
    city: str
    state: str
    postal_code: str
    date_of_birth: str
    credit_score: int
    created_at: str


class CustomerListResponse(BaseModel):
    """Paginated list of customers."""

    data: list[CustomerSchema]
    pagination: PaginationMeta


class PolicySchema(BaseModel):
    """Insurance policy entity."""

    policy_id: str
    customer_id: str
    policy_type: str
    coverage_limit: float
    deductible: float
    annual_premium: float
    start_date: str
    end_date: str
    status: str
    created_at: str


class PolicyListResponse(BaseModel):
    """Paginated list of policies."""

    data: list[PolicySchema]
    pagination: PaginationMeta


class ClaimSchema(BaseModel):
    """Insurance claim record."""

    claim_id: str
    policy_id: str
    customer_id: str
    claim_category: str
    claim_priority: str
    claim_amount: float
    approved_amount: float | None = None
    incident_date: str
    filing_date: str
    status: str
    state: str | None = None
    description: str | None = None
    is_fraud: int = 0
    fraud_reason: str | None = None
    created_at: str


class ClaimCreate(BaseModel):
    """Payload to file a new insurance claim."""

    policy_id: str = Field(..., examples=["POL-00001"])
    customer_id: str = Field(..., examples=["CUST-0001"])
    claim_category: str = Field(..., examples=["Auto"])
    claim_priority: str = Field(default="Medium", examples=["Medium"])
    claim_amount: float = Field(..., gt=0, examples=[4500.0])
    incident_date: str = Field(..., examples=["2026-05-10"])
    state: str = Field(..., examples=["CA"])
    description: str = Field(
        ..., min_length=10, examples=["Vehicle rear-ended at intersection."]
    )


class ClaimListResponse(BaseModel):
    """Paginated list of claims."""

    data: list[ClaimSchema]
    pagination: PaginationMeta


class HealthResponse(BaseModel):
    """API health status representation."""

    status: str
    service: str
    version: str
    records_loaded: dict[str, int]
    timestamp: str
