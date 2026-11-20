"""
mock_api/app/routers/customers.py
=================================
Customer query endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from mock_api.app.data_store import store
from mock_api.app.middleware.auth import verify_api_key
from mock_api.app.models.schemas import CustomerListResponse, CustomerSchema

router = APIRouter(
    prefix="/api/v1/customers",
    tags=["Customers"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    state: Annotated[
        str | None, Query(description="Filter by 2-letter US State", max_length=2)
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=200, description="Page size (max 200)")
    ] = 50,
) -> CustomerListResponse:
    """Retrieves paginated list of customers with optional geographic filtering."""
    items, meta = store.get_customers(state=state, page=page, page_size=page_size)
    return CustomerListResponse(
        data=[CustomerSchema(**item) for item in items], pagination=meta
    )


@router.get("/{customer_id}", response_model=CustomerSchema)
async def get_customer(customer_id: str) -> CustomerSchema:
    """Retrieves single customer profile by customer ID."""
    customer = store.customers_by_id.get(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found",
        )
    return CustomerSchema(**customer)
