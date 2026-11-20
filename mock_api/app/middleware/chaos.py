"""
mock_api/app/middleware/chaos.py
================================
Chaos Engineering and transient failure injection middleware.
Simulates real-world legacy system downtime (500s, 503s) and network latency
to ensure our downstream ETL pipelines (Sprint 2) build resilient retry mechanisms.
"""

import asyncio
import random

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from mock_api.app.config import settings


class ChaosMiddleware(BaseHTTPMiddleware):
    """
    Simulates transient network/server failures and network latency.
    Can be activated via config flag or triggered explicitly via test headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # 1. Header-forced error simulation (useful for deterministic integration tests)
        forced_status = request.headers.get("X-Force-Error")
        if forced_status:
            code = int(forced_status)
            return JSONResponse(
                status_code=code,
                content={
                    "error": "SimulatedFailure",
                    "detail": f"Forced error simulation with HTTP {code}",
                },
            )

        # 2. Probabilistic failure injection if enabled in settings
        if settings.simulate_errors and random.random() < settings.error_rate:
            error_code = random.choice([500, 502, 503])
            return JSONResponse(
                status_code=error_code,
                content={
                    "error": "TransientSystemFailure",
                    "detail": f"Legacy core claims system temporarily unavailable (HTTP {error_code})",
                },
            )

        # 3. Simulate minor network latency (10ms - 40ms)
        await asyncio.sleep(random.uniform(0.01, 0.04))

        return await call_next(request)
