"""
mock_api/app/routers/policies.py
================================
Policy query endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from mock_api.app.data_store import store
from mock_api.app.middleware.auth import verify_api_key
from mock_api.app.models.schemas import PolicyListResponse, PolicySchema

router = APIRouter(
    prefix="/api/v1/policies",
    tags=["Policies"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=PolicyListResponse)
async def list_policies(
    customer_id: Annotated[
        str | None, Query(description="Filter by Customer ID")
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by status (Active, Expired, etc.)"),
    ] = None,
    policy_type: Annotated[
        str | None, Query(description="Filter by policy type")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=200, description="Page size (max 200)")
    ] = 50,
) -> PolicyListResponse:
    """Retrieves paginated list of policies with multi-criteria filtering."""
    items, meta = store.get_policies(
        customer_id=customer_id,
        status=status_filter,
        policy_type=policy_type,
        page=page,
        page_size=page_size,
    )
    return PolicyListResponse(
        data=[PolicySchema(**item) for item in items], pagination=meta
    )


@router.get("/{policy_id}", response_model=PolicySchema)
async def get_policy(policy_id: str) -> PolicySchema:
    """Retrieves single policy details by policy ID."""
    policy = store.policies_by_id.get(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID '{policy_id}' not found",
        )
    return PolicySchema(**policy)
