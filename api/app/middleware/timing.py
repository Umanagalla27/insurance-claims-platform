"""High-performance pure ASGI Request Timing and Correlation ID middleware.

Avoids BaseHTTPMiddleware task-group deadlock and latency overhead,
providing sub-microsecond header injection and correlation tracing.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable


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
        updated.append((b"x-process-time", f"{process_time:.6f}s".encode("utf-8")))
        updated.append((b"x-request-id", request_id.encode("utf-8")))
        return updated

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

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                process_time = time.perf_counter() - start_time
                orig_headers = message.get("headers", [])
                message["headers"] = self.attach_timing_headers(orig_headers, process_time, request_id)
            await send(message)

        await self.app(scope, receive, send_wrapper)
