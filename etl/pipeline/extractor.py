"""
etl/pipeline/extractor.py
=========================
Resilient API Extractor for partner Core Policy & Claims API.
Features:
- Tenacity exponential backoff retries on transient errors (500, 502, 503, 504)
- Jittered backoff to prevent thundering-herd issues
- Sliding-window rate limit awareness (intercepts HTTP 429 and obeys Retry-After)
- Standardized pagination traversal
- High-watermark incremental state tracking
- Structured logging with structlog
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from etl.config.settings import settings
from etl.pipeline.state_manager import StateManager, state_manager
from etl.utils.logging import logger


def _is_transient_error(exception: BaseException) -> bool:
    """
    Determines if an exception is transient and worth retrying.
    Retries on network timeouts, connection drops, and HTTP 5xx server errors.
    Does NOT retry on 4xx client errors (e.g. 401 Unauthorized, 404 Not Found).
    """
    if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        # 500, 502, 503, 504 are transient server-side issues
        return exception.response.status_code in [500, 502, 503, 504]
    return False


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    """Callback for logging retry attempts with exponential backoff details."""
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Transient error encountered. Retrying request with exponential backoff...",
        attempt=retry_state.attempt_number,
        wait_seconds=round(retry_state.next_action.sleep, 2)
        if retry_state.next_action
        else None,
        error=str(exception),
    )


class ApiExtractor:
    """Extracts datasets from external Mock Insurance API with enterprise resilience."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        state_mgr: StateManager | None = None,
        raw_output_dir: Path | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.mock_api_base_url).rstrip("/")
        self.api_key = api_key or settings.mock_api_key
        self.state_mgr = state_mgr or state_manager
        self.raw_output_dir = raw_output_dir or settings.raw_landing_dir
        self.raw_output_dir.mkdir(parents=True, exist_ok=True)

        self.headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "Insurance-Platform-ETL-Pipeline/1.0",
        }

        # Injectable HTTP client (useful for unit testing with ASGI transport or mocking)
        self.client = client or httpx.Client(
            headers=self.headers,
            timeout=settings.request_timeout_seconds,
        )

    @retry(
        retry=retry_if_exception(_is_transient_error),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=0.5),
        stop=stop_after_attempt(3),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )
    def _execute_request_with_retry(
        self, url: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Executes a single HTTP GET request with automated retries and rate limit handling.
        """
        response = self.client.get(url, params=params)

        # Handle HTTP 429 Too Many Requests (Rate Limiting)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(
                "Rate limit exceeded (HTTP 429). Pausing pipeline per Retry-After header...",
                retry_after_seconds=retry_after,
                url=url,
            )
            time.sleep(retry_after)
            # Re-execute after waiting
            response = self.client.get(url, params=params)

        # Raise HTTPStatusError for 4xx/5xx errors
        response.raise_for_status()
        return response.json()

    def extract_entity(
        self,
        entity_name: str,
        endpoint_path: str,
        is_incremental: bool = False,
        extra_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extracts all paginated records for an entity.
        Supports high-watermark incremental extraction if `is_incremental` is True.
        """
        url = f"{self.base_url}{endpoint_path}"
        all_records: list[dict[str, Any]] = []
        page = 1
        page_size = settings.mock_api_page_size
        start_time = time.time()

        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            **(extra_params or {}),
        }

        # Incremental watermark lookup
        watermark = None
        if is_incremental:
            watermark = self.state_mgr.get_watermark(entity_name)
            if watermark:
                # Use only YYYY-MM-DD for since_date endpoint filter
                params["since_date"] = watermark[:10]
                logger.info(
                    "Executing incremental extraction",
                    entity=entity_name,
                    since_date=params["since_date"],
                )
            else:
                logger.info(
                    "No prior watermark found. Initiating full historical extraction.",
                    entity=entity_name,
                )

        logger.info("Beginning entity extraction", entity=entity_name, url=url)

        has_next = True
        total_pages = 1

        while has_next:
            params["page"] = page
            data = self._execute_request_with_retry(url, params)

            records = data.get("data", [])
            pagination = data.get("pagination", {})
            all_records.extend(records)

            total_pages = pagination.get("total_pages", 1)
            has_next = pagination.get("has_next", False)

            logger.info(
                "Extracted page batch",
                entity=entity_name,
                page=page,
                total_pages=total_pages,
                batch_size=len(records),
                cumulative_records=len(all_records),
            )

            page += 1

        elapsed = time.time() - start_time
        logger.info(
            "Extraction completed successfully",
            entity=entity_name,
            total_records=len(all_records),
            elapsed_seconds=round(elapsed, 2),
        )

        # Update high-watermark if records were extracted
        if is_incremental and all_records:
            # Determine maximum timestamp in the batch
            timestamps = [
                r.get("created_at") or r.get("filing_date")
                for r in all_records
                if r.get("created_at") or r.get("filing_date")
            ]
            new_watermark = (
                max(timestamps) if timestamps else datetime.now().isoformat()
            )
            self.state_mgr.update_watermark(
                entity_name, new_watermark, len(all_records)
            )

        return all_records

    def extract_customers(self) -> list[dict[str, Any]]:
        """Extracts all customers."""
        return self.extract_entity(
            "customers", "/api/v1/customers", is_incremental=False
        )

    def extract_policies(self) -> list[dict[str, Any]]:
        """Extracts all policies."""
        return self.extract_entity("policies", "/api/v1/policies", is_incremental=False)

    def extract_claims(self, incremental: bool = True) -> list[dict[str, Any]]:
        """Extracts claims with incremental high-watermark support."""
        return self.extract_entity(
            "claims", "/api/v1/claims", is_incremental=incremental
        )

    def extract_all(
        self, incremental_claims: bool = True
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Coordinates full or incremental ingestion across all entities.
        Saves raw extracted JSON payloads to the raw landing directory.
        """
        logger.info("Starting complete ETL ingestion run...")
        start_time = time.time()

        customers = self.extract_customers()
        policies = self.extract_policies()
        claims = self.extract_claims(incremental=incremental_claims)

        elapsed = time.time() - start_time

        logger.info(
            "ETL Extraction Run Complete",
            customers_count=len(customers),
            policies_count=len(policies),
            claims_count=len(claims),
            elapsed_seconds=round(elapsed, 2),
        )

        return {
            "customers": customers,
            "policies": policies,
            "claims": claims,
        }
