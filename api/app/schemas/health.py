"""Schemas for health, readiness, and metrics endpoints."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Basic liveness status schema."""

    status: str = Field(default="healthy", description="Status string: healthy, degraded, unhealthy")
    service: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Application semantic version")
    timestamp: str = Field(..., description="Current UTC timestamp")


class ComponentReadiness(BaseModel):
    """Status details for an individual platform dependency or model subsystem."""

    component: str = Field(..., description="Component name: classifier, anomaly_detector, vector_store, database")
    status: str = Field(..., description="Status: ready, degraded, unavailable")
    latency_ms: Optional[float] = Field(default=None, description="Probe latency in milliseconds")
    details: Optional[str] = Field(default=None, description="Diagnostic information or error summary")


class ReadinessReport(BaseModel):
    """Deep readiness report covering all critical models and data stores."""

    status: str = Field(..., description="Overall readiness: ready, degraded, unavailable")
    components: List[ComponentReadiness] = Field(..., description="Subsystem readiness statuses")
    timestamp: str = Field(..., description="Report generation timestamp")


class SystemMetrics(BaseModel):
    """Runtime telemetry and performance indicators."""

    uptime_seconds: float = Field(..., description="Seconds elapsed since process startup")
    memory_rss_mb: float = Field(..., description="Resident Set Size (physical memory) consumed by process in MB")
    python_version: str = Field(..., description="Host Python interpreter version")
    models_loaded: Dict[str, bool] = Field(..., description="Map of ML models and vector indexes active in memory")
    threads_active: int = Field(..., description="Active thread count in current process")
