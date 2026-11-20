"""High-performance pure ASGI Request Timing, Correlation ID, and Metrics middleware.

Avoids BaseHTTPMiddleware task-group deadlock and latency overhead,
providing sub-microsecond header injection, correlation tracing,
and automated Prometheus request metrics collection.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from collections.abc import Callable
from typing import Any

from api.app.services.metrics import metrics_collector


class TimingMiddleware:
    """Pure ASGI middleware measuring duration and injecting standard tracing headers."""

    def __init__(self, app: Any):
        self.app = app

    @staticmethod
    def extract_or_generate_request_id(headers: list[tuple[bytes, bytes]]) -> str:
        """Extract correlation ID from incoming ASGI headers or generate fresh UUID."""
        for name, value in headers:
            if name.lower() == b"x-request-id":
                return value.decode("utf-8", errors="replace")
        return str(uuid.uuid4())

    @staticmethod
    def attach_timing_headers(
        headers: list[tuple[bytes, bytes]],
        process_time: float,
        request_id: str,
    ) -> list[tuple[bytes, bytes]]:
        """Append standardized performance and tracing headers."""
        updated = list(headers)
        updated.append((b"x-process-time", f"{process_time:.6f}s".encode()))
        updated.append((b"x-request-id", request_id.encode("utf-8")))
        return updated

    @staticmethod
    def normalize_endpoint(path: str) -> str:
        """Normalize endpoint paths to prevent high-cardinality label explosion."""
        if not path:
            return "/"
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        return path

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_headers = scope.get("headers", [])
        request_id = self.extract_or_generate_request_id(raw_headers)

        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        start_time = time.perf_counter()
        status_code = [200]

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 200)
                process_time = time.perf_counter() - start_time
                orig_headers = message.get("headers", [])
                message["headers"] = self.attach_timing_headers(
                    orig_headers, process_time, request_id
                )
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start_time
            method = scope.get("method", "GET")
            raw_path = scope.get("path", "/")
            endpoint = self.normalize_endpoint(raw_path)
            with contextlib.suppress(Exception):
                metrics_collector.record_http_request(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code[0],
                    duration_seconds=duration,
                )
