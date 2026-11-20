"""Prometheus Observability & Metrics Instrumentation Engine.

Provides enterprise telemetry for FastAPI gateway, ML inference pipelines,
underwriting rules engine, and policy RAG hybrid search.
"""

from __future__ import annotations

import logging
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Enterprise Prometheus metrics collector and registry manager."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self._init_metrics()

    def _init_metrics(self) -> None:
        """Initialize all platform counters, histograms, and gauges."""
        # 1. HTTP Gateway Ingress & Latency Metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP ingress requests processed by the API gateway",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request processing latency in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        # 2. ML Inference & Underwriting Decision Metrics
        self.claims_adjudicated_total = Counter(
            "claims_adjudicated_total",
            "Total claims adjudicated by the multi-model intelligence pipeline",
            ["category", "outcome"],
            registry=self.registry,
        )

        self.claims_fraud_detected_total = Counter(
            "claims_fraud_detected_total",
            "Total claims flagged as fraudulent or anomalous",
            ["category"],
            registry=self.registry,
        )

        self.claims_stp_approved_total = Counter(
            "claims_stp_approved_total",
            "Total touchless straight-through-processing (STP) claims approved automatically",
            registry=self.registry,
        )

        # 3. Policy RAG Chatbot & Semantic Search Metrics
        self.rag_queries_total = Counter(
            "rag_queries_total",
            "Total policy RAG hybrid search queries executed",
            ["status", "cache_hit"],
            registry=self.registry,
        )

        # 4. System Runtime & Health Telemetry Gauges
        self.app_uptime_seconds = Gauge(
            "app_uptime_seconds",
            "Platform gateway uptime in elapsed seconds",
            registry=self.registry,
        )

        self.process_memory_rss_bytes = Gauge(
            "process_memory_rss_bytes",
            "Resident Set Size (RSS) memory consumption of the Python process in bytes",
            registry=self.registry,
        )

        self.process_active_threads = Gauge(
            "process_active_threads",
            "Count of active Python OS worker threads",
            registry=self.registry,
        )

        self.subsystem_readiness_status = Gauge(
            "subsystem_readiness_status",
            "Subsystem operational readiness flag (1.0 = ready, 0.0 = offline)",
            ["subsystem"],
            registry=self.registry,
        )

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record HTTP ingress request completion and latency."""
        norm_method = method.upper()
        norm_endpoint = endpoint if endpoint else "/"
        self.http_requests_total.labels(
            method=norm_method,
            endpoint=norm_endpoint,
            status_code=str(status_code),
        ).inc()
        self.http_request_duration_seconds.labels(
            method=norm_method,
            endpoint=norm_endpoint,
        ).observe(duration_seconds)

    def record_claim_adjudication(self, category: str, outcome: str) -> None:
        """Record a completed claim adjudication event."""
        self.claims_adjudicated_total.labels(
            category=category or "UNKNOWN",
            outcome=outcome or "UNKNOWN",
        ).inc()

    def record_fraud_detected(self, category: str) -> None:
        """Increment count of detected fraudulent claims."""
        self.claims_fraud_detected_total.labels(
            category=category or "UNKNOWN"
        ).inc()

    def record_stp_approval(self) -> None:
        """Increment count of touchless straight-through-processing approvals."""
        self.claims_stp_approved_total.inc()

    def record_rag_query(self, status: str, cache_hit: bool) -> None:
        """Record policy RAG query execution."""
        self.rag_queries_total.labels(
            status=status,
            cache_hit="true" if cache_hit else "false",
        ).inc()

    def update_system_metrics(
        self,
        uptime_seconds: float,
        memory_rss_bytes: float,
        active_threads: int,
        model_flags: dict[str, Any],
    ) -> None:
        """Update runtime gauges before Prometheus scrapers harvest data."""
        self.app_uptime_seconds.set(max(0.0, float(uptime_seconds)))
        self.process_memory_rss_bytes.set(max(0.0, float(memory_rss_bytes)))
        self.process_active_threads.set(max(1, int(active_threads)))

        for subsystem, is_ready in model_flags.items():
            val = 1.0 if bool(is_ready) else 0.0
            self.subsystem_readiness_status.labels(subsystem=subsystem).set(val)

    def export_prometheus_text(self) -> str:
        """Generate Prometheus exposition text format (version 0.0.4)."""
        return generate_latest(self.registry).decode("utf-8")

    def reset(self) -> None:
        """Reset all metrics by creating a clean registry (used in test fixtures)."""
        self.registry = CollectorRegistry(auto_describe=True)
        self._init_metrics()


# Global Singleton Instance for Platform Telemetry
metrics_collector = MetricsCollector()
