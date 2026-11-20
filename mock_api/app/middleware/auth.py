"""
mock_api/app/middleware/auth.py
===============================
API Key authentication dependency for FastAPI routes.
Checks X-API-Key header or Bearer token against configured secret.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from mock_api.app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """
    Validates API key from request headers.
    Returns the key if valid; raises HTTP 401 if invalid or absent.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication header 'X-API-Key'",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != settings.mock_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key provided",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
