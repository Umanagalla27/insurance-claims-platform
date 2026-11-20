"""Health, readiness, and observability endpoints."""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status
from starlette.responses import JSONResponse
from starlette.responses import Response as StarletteResponse

from api.app.config import settings
from api.app.schemas.common import ApiResponse
from api.app.schemas.health import (
    ComponentReadiness,
    HealthStatus,
    ReadinessReport,
    SystemMetrics,
)
from api.app.services.container import ServiceContainer
from api.app.services.metrics import metrics_collector

router = APIRouter(tags=["Health & Diagnostics"])


@router.get(
    "/health", response_model=ApiResponse[HealthStatus], summary="Liveness Probe"
)
@router.get(
    "/health/live",
    response_model=ApiResponse[HealthStatus],
    summary="Liveness Probe (Kubernetes / ALB)",
)
def health_check() -> ApiResponse[HealthStatus]:
    """Lightweight Kubernetes / ALB liveness probe.

    Returns 200 OK if the ASGI process is actively responding to HTTP requests.
    """
    payload = HealthStatus(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(UTC).isoformat(),
    )
    return ApiResponse(
        success=True,
        data=payload,
        message="Service is alive",
    )


@router.get(
    "/ready", response_model=ApiResponse[ReadinessReport], summary="Readiness Probe"
)
@router.get(
    "/health/ready",
    response_model=ApiResponse[ReadinessReport],
    summary="Readiness Probe (Kubernetes / ALB)",
)
def readiness_check(
    request: Request, response: Response
) -> ApiResponse[ReadinessReport]:
    """Deep readiness probe checking ML models, vector database, and platform dependencies.

    Returns 200 OK if all subsystems are loaded and ready to serve traffic.
    Returns 503 Service Unavailable if any critical subsystem is offline.
    """
    services: ServiceContainer = getattr(request.app.state, "services", None)
    components: list[ComponentReadiness] = []
    overall_healthy = True

    # 1. Text Classification Model Probe
    t0 = time.perf_counter()
    if services and services.classifier and services.status_flags.get("classifier"):
        c_lat = (time.perf_counter() - t0) * 1000.0
        components.append(
            ComponentReadiness(
                component="nlp_text_classifier",
                status="ready",
                latency_ms=round(c_lat, 2),
                details=f"Classes: {', '.join(services.classifier.classes)}",
            )
        )
    else:
        overall_healthy = False
        components.append(
            ComponentReadiness(
                component="nlp_text_classifier",
                status="unavailable",
                details="Model artifact missing or initialization failed",
            )
        )

    # 2. Anomaly Detection Model Probe
    t0 = time.perf_counter()
    if (
        services
        and services.anomaly_detector
        and services.status_flags.get("anomaly_detector")
    ):
        a_lat = (time.perf_counter() - t0) * 1000.0
        components.append(
            ComponentReadiness(
                component="isolation_forest_anomaly",
                status="ready",
                latency_ms=round(a_lat, 2),
                details=f"Features: {len(services.anomaly_detector.feature_names)} features configured",
            )
        )
    else:
        overall_healthy = False
        components.append(
            ComponentReadiness(
                component="isolation_forest_anomaly",
                status="unavailable",
                details="Anomaly detector artifact missing or failed to initialize",
            )
        )

    # 3. Vector Store & RAG Engine Probe
    t0 = time.perf_counter()
    if (
        services
        and services.retrieval_service
        and services.status_flags.get("retrieval_service")
    ):
        r_lat = (time.perf_counter() - t0) * 1000.0
        total_vectors = getattr(
            services.retrieval_service.retriever.vector_store, "total_vectors", 0
        )
        components.append(
            ComponentReadiness(
                component="policy_vector_store",
                status="ready",
                latency_ms=round(r_lat, 2),
                details=f"Total Indexed Clauses: {total_vectors}",
            )
        )
    else:
        overall_healthy = False
        components.append(
            ComponentReadiness(
                component="policy_vector_store",
                status="unavailable",
                details="Vector store index binary or metadata manifest missing",
            )
        )

    report = ReadinessReport(
        status="ready" if overall_healthy else "degraded",
        components=components,
        timestamp=datetime.now(UTC).isoformat(),
    )

    if not overall_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ApiResponse(
        success=overall_healthy,
        data=report,
        message="All systems operational"
        if overall_healthy
        else "Subsystems degraded or offline",
    )


@router.get(
    "/metrics/json",
    response_model=ApiResponse[SystemMetrics],
    summary="Runtime Metrics (JSON)",
)
def runtime_metrics(request: Request) -> ApiResponse[SystemMetrics]:
    """Runtime telemetry reporting memory, active threads, and active model flags."""
    services: ServiceContainer = getattr(request.app.state, "services", None)
    uptime = (
        (time.time() - services.startup_time)
        if (services and services.startup_time > 0)
        else 0.0
    )

    # Calculate approximate process memory consumption
    memory_mb = 0.0
    try:
        import psutil

        process = psutil.Process(os.getpid())
        memory_mb = round(process.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        memory_mb = 0.0

    models_loaded = services.status_flags if services else {}

    metrics = SystemMetrics(
        uptime_seconds=round(uptime, 2),
        memory_rss_mb=memory_mb,
        python_version=sys.version.split()[0],
        models_loaded=models_loaded,
        threads_active=threading.active_count(),
    )

    return ApiResponse(
        success=True,
        data=metrics,
        message="Metrics collected successfully",
    )


@router.get(
    "/metrics",
    summary="Prometheus Metrics Exposition",
    response_class=StarletteResponse,
)
def prometheus_metrics(request: Request, response: Response) -> StarletteResponse:
    """Standard Prometheus exposition endpoint (/metrics).

    Scraped by Prometheus and OpenTelemetry agents using text/plain (version 0.0.4).
    If an explicit application/json Accept header is supplied, delegates to runtime_metrics.
    """
    accept = request.headers.get("accept", "")
    if (
        "application/json" in accept
        and "text/plain" not in accept
        and "version=0.0.4" not in accept
    ):
        json_data = runtime_metrics(request)
        return JSONResponse(content=json_data.model_dump())

    services: ServiceContainer = getattr(request.app.state, "services", None)
    uptime = (
        (time.time() - services.startup_time)
        if (services and services.startup_time > 0)
        else 0.0
    )

    memory_bytes = 0.0
    try:
        import psutil

        process = psutil.Process(os.getpid())
        memory_bytes = float(process.memory_info().rss)
    except Exception:
        memory_bytes = 0.0

    models_loaded = services.status_flags if services else {}
    threads = threading.active_count()

    metrics_collector.update_system_metrics(
        uptime_seconds=uptime,
        memory_rss_bytes=memory_bytes,
        active_threads=threads,
        model_flags=models_loaded,
    )

    prom_content = metrics_collector.export_prometheus_text()
    return StarletteResponse(
        content=prom_content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
