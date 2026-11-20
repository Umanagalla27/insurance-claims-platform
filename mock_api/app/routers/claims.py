"""
mock_api/app/routers/claims.py
==============================
Claims query and ingestion endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from mock_api.app.data_store import store
from mock_api.app.middleware.auth import verify_api_key
from mock_api.app.models.schemas import ClaimCreate, ClaimListResponse, ClaimSchema

router = APIRouter(
    prefix="/api/v1/claims",
    tags=["Claims"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=ClaimListResponse)
async def list_claims(
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by claim status")
    ] = None,
    category: Annotated[
        str | None, Query(description="Filter by claim category")
    ] = None,
    priority: Annotated[
        str | None, Query(description="Filter by claim priority")
    ] = None,
    state: Annotated[str | None, Query(description="Filter by US State")] = None,
    policy_id: Annotated[str | None, Query(description="Filter by Policy ID")] = None,
    customer_id: Annotated[
        str | None, Query(description="Filter by Customer ID")
    ] = None,
    since_date: Annotated[
        str | None,
        Query(
            description="Incremental extraction filter (ISO format YYYY-MM-DD). Returns claims filed on or after date.",
            pattern=r"^\d{4}-\d{2}-\d{2}",
        ),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=200, description="Page size (max 200)")
    ] = 50,
) -> ClaimListResponse:
    """
    Retrieves paginated insurance claims.
    Supports incremental ETL date querying via `since_date`.
    """
    items, meta = store.get_claims(
        status=status_filter,
        category=category,
        priority=priority,
        state=state,
        policy_id=policy_id,
        customer_id=customer_id,
        since_date=since_date,
        page=page,
        page_size=page_size,
    )
    return ClaimListResponse(
        data=[ClaimSchema(**item) for item in items], pagination=meta
    )


@router.get("/{claim_id}", response_model=ClaimSchema)
async def get_claim(claim_id: str) -> ClaimSchema:
    """Retrieves single claim record by claim ID."""
    claim = store.claims_by_id.get(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim with ID '{claim_id}' not found",
        )
    return ClaimSchema(**claim)


@router.post("", response_model=ClaimSchema, status_code=status.HTTP_201_CREATED)
async def create_claim(payload: ClaimCreate) -> ClaimSchema:
    """
    Submits a new insurance claim into the core system.
    Validates that the referenced policy exists before accepting.
    """
    if payload.policy_id not in store.policies_by_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Referenced policy '{payload.policy_id}' does not exist in core registry.",
        )

    new_claim = store.add_claim(payload.model_dump())
    return ClaimSchema(**new_claim)
