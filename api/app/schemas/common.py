"""Common response and error schemas for API Gateway."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse[T](BaseModel):
    """Standardized API response envelope for all successful endpoints."""

    success: bool = Field(
        default=True, description="Indicates whether the request was successful"
    )
    data: T | None = Field(default=None, description="Response payload")
    message: str = Field(default="Success", description="Human-readable status message")
    request_id: str | None = Field(
        default=None, description="Unique trace identifier for debugging"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of response generation",
    )


class ErrorDetail(BaseModel):
    """Granular error detail item (field validation, business logic rule)."""

    field: str | None = Field(
        default=None, description="Form or JSON field name that caused the error"
    )
    message: str = Field(..., description="Specific error explanation")
    code: str | None = Field(default=None, description="Machine-readable error code")


class ErrorResponse(BaseModel):
    """Standardized error envelope for HTTP 4xx and 5xx responses."""

    success: bool = Field(default=False, description="Always false for error responses")
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="High-level description of what went wrong")
    details: list[ErrorDetail] = Field(
        default_factory=list, description="Sub-errors or validation issues"
    )
    request_id: str | None = Field(
        default=None, description="Unique trace identifier for troubleshooting"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of error occurrence",
    )
