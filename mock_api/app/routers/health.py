"""
mock_api/app/routers/health.py
==============================
Health check endpoint for container probes and load balancers.
"""

from datetime import datetime

from fastapi import APIRouter

from mock_api.app.data_store import store
from mock_api.app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns service health status and loaded dataset metrics."""
    return HealthResponse(
        status="healthy" if store.is_loaded else "initializing",
        service="mock-insurance-core-api",
        version="1.0.0",
        records_loaded={
            "customers": len(store.customers),
            "policies": len(store.policies),
            "claims": len(store.claims),
        },
        timestamp=datetime.now().isoformat(),
    )
