"""Global error handling middleware and exception handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on FastAPI application instance."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        details = []
        for error in exc.errors():
            loc = " -> ".join(str(p) for p in error.get("loc", []))
            details.append(
                ErrorDetail(
                    field=loc,
                    message=error.get("msg", "Validation error"),
                    code=error.get("type", "value_error"),
                )
            )

        error_body = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Request body or query parameter failed validation schema checks.",
            details=details,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_body.model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        error_body = ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            details=[],
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "Unhandled server exception processing request %s: %s", request_id, exc
        )

        error_body = ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred while processing your request.",
            details=[ErrorDetail(message=str(exc))] if app.debug else [],
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body.model_dump(),
        )
