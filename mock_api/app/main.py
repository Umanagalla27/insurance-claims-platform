"""
mock_api/app/main.py
====================
Entry point for Mock External Policy & Claims API service.
Simulates a partner legacy core insurance system (e.g. Guidewire / Duck Creek).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mock_api.app.config import settings
from mock_api.app.data_store import store
from mock_api.app.middleware.chaos import ChaosMiddleware
from mock_api.app.middleware.rate_limiter import RateLimitMiddleware
from mock_api.app.routers import claims, customers, health, policies


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan event handler: load dataset into memory upon startup."""
    print("Initializing Mock Insurance Core API...")
    store.load_data()
    print(
        f"Mock API Ready: Loaded {len(store.customers)} customers, "
        f"{len(store.policies)} policies, and {len(store.claims)} claims."
    )
    yield
    print("Shutting down Mock Insurance Core API.")


app = FastAPI(
    title="Mock Insurance Core Policy & Claims API",
    description=(
        "Simulates a partner enterprise core policy administration and claims processing system. "
        "Provides API-Key authentication, sliding-window rate limiting, paginated endpoints, "
        "and transient error simulation for resilient ETL pipeline development."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for local frontend/dashboard accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middlewares
app.add_middleware(ChaosMiddleware)
app.add_middleware(RateLimitMiddleware)

# Mount Routers
app.include_router(health.router)
app.include_router(customers.router)
app.include_router(policies.router)
app.include_router(claims.router)


if __name__ == "__main__":
    uvicorn.run(
        "mock_api.app.main:app",
        host=settings.mock_api_host,
        port=settings.mock_api_port,
        reload=False,
    )
