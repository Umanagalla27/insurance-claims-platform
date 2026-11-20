"""Insurance Claims Intelligence Platform — Core API Gateway Application."""

from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.config import settings
from api.app.middleware.errors import setup_exception_handlers
from api.app.middleware.timing import TimingMiddleware
from api.app.routers.claims import router as claims_router
from api.app.routers.health import router as health_router
from api.app.services.container import lifespan

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api.app.main")


def create_app() -> FastAPI:
    """Application factory initializing FastAPI gateway with production middleware and routing."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "Enterprise Insurance Claims Intelligence Platform Core REST API Gateway. "
            "Exposes multi-model ML inference (NLP classification, fraud anomaly detection) "
            "and multi-stage RAG hybrid policy retrieval."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Register Custom Timing & Correlation Middleware
    app.add_middleware(TimingMiddleware)

    # 2. Register CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Register Global Exception Handlers
    setup_exception_handlers(app)

    # 4. Mount Routers
    # Standard health router mounted under /api/v1
    app.include_router(health_router, prefix=settings.API_V1_PREFIX)
    # Claims analysis and ML adjudication router
    app.include_router(claims_router, prefix=settings.API_V1_PREFIX)
    # Convenience liveness alias at root /health for Kubernetes / AWS Target Groups
    app.include_router(health_router, prefix="")

    logger.info("FastAPI application created with API prefix: %s", settings.API_V1_PREFIX)
    return app


app = create_app()
