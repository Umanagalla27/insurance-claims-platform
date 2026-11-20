"""
ETL Lambda Handler Module Alias.
Points to infrastructure/serverless/handler.py for serverless S3 ingestion.
"""

from infrastructure.serverless.handler import (
    lambda_handler,
    process_claims_batch,
    validate_claim_record,
)

__all__ = ["lambda_handler", "process_claims_batch", "validate_claim_record"]
