"""
mock_api/app/middleware/rate_limiter.py
=======================================
Sliding window rate limiting middleware.
Guards external mock API against excessive load and simulates production rate limits.
"""

import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from mock_api.app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Tracks request timestamps per client within a 60-second sliding window.
    Emits HTTP 429 when quota is exceeded.
    """

    def __init__(self, app, requests_per_minute: int | None = None) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute or settings.rate_limit_per_minute
        # client_id -> list of float epoch timestamps
        self.history: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude documentation and health check from rate limits
        path = request.url.path
        if path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Identify client by API Key or client host IP
        client_key = request.headers.get("X-API-Key") or (
            request.client.host if request.client else "unknown"
        )
        now = time.time()
        window_start = now - 60.0

        # Purge timestamps older than 60 seconds
        timestamps = [t for t in self.history[client_key] if t > window_start]
        self.history[client_key] = timestamps

        if len(timestamps) >= self.rpm:
            retry_after = int(60 - (now - timestamps[0])) if timestamps else 60
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded: maximum {self.rpm} requests per minute.",
                    "retry_after_seconds": max(1, retry_after),
                },
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(self.rpm),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self.history[client_key].append(now)

        response = await call_next(request)
        remaining = max(0, self.rpm - len(self.history[client_key]))
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
