"""
AWS Lambda Serverless Claims Ingestion Handler.
Component: infrastructure/serverless/handler.py
Triggered by: S3 ObjectCreated event on s3://<landing-bucket>/raw-claims/
"""

import json
import logging
import os
import urllib.parse
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("insurance_claims_lambda")
logger.setLevel(logging.INFO)

# Optional boto3 import with graceful fallback for offline/local execution
try:
    import boto3
except ImportError:
    boto3 = None


def validate_claim_record(record: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate a single raw claim record."""
    if not isinstance(record, dict):
        return False, "Record must be a JSON object"

    claim_id = str(record.get("claim_id", "")).strip()
    if not claim_id:
        return False, "Missing mandatory field 'claim_id'"

    policy_id = str(record.get("policy_id", "")).strip()
    if not policy_id:
        return False, "Missing mandatory field 'policy_id'"

    try:
        amount = float(record.get("claim_amount", 0.0))
        if amount <= 0.0:
            return False, f"Invalid claim_amount: {amount} (must be > 0.0)"
    except (ValueError, TypeError):
        return False, "Non-numeric claim_amount"

    return True, None


def process_claims_batch(
    raw_content: str | list[Any] | dict[str, Any], filename: str
) -> dict[str, Any]:
    """Parse and validate incoming claims batch content (JSON string or object)."""
    clean_records: list[dict[str, Any]] = []
    quarantined_records: list[dict[str, Any]] = []
    total_amount = 0.0

    if isinstance(raw_content, (list, dict)):
        data = raw_content
        items = data if isinstance(data, list) else data.get("claims", [data])
    else:
        try:
            data = json.loads(raw_content)
            items = data if isinstance(data, list) else data.get("claims", [data])
        except Exception as e:
            logger.error("Failed to parse JSON content from %s: %s", filename, e)
            return {
                "status": "CORRUPTED_BATCH",
                "error": str(e),
                "filename": filename,
                "total_records": 0,
                "clean_count": 0,
                "quarantine_count": 0,
                "total_amount": 0.0,
                "clean_records": [],
                "quarantined_records": [
                    {"raw_content": str(raw_content)[:500], "reason": "Malformed JSON"}
                ],
            }

    for item in items:
        is_valid, reason = validate_claim_record(item)
        if is_valid:
            clean_records.append(item)
            total_amount += float(item.get("claim_amount", 0.0))
        else:
            quarantined_records.append({"record": item, "rejection_reason": reason})

    return {
        "status": "PROCESSED",
        "filename": filename,
        "total_records": len(items),
        "clean_count": len(clean_records),
        "quarantine_count": len(quarantined_records),
        "total_amount": round(total_amount, 2),
        "clean_records": clean_records,
        "quarantined_records": quarantined_records,
    }


def lambda_handler(
    event: dict[str, Any],
    context: Any = None,
    s3_client: Any = None,
) -> dict[str, Any]:
    """AWS Lambda Entrypoint invoked by S3 ObjectCreated events.

    Args:
        event: AWS S3 Event Notification dictionary.
        context: AWS Lambda runtime context object.
        s3_client: Optional injected boto3 S3 client (used for mocking in tests).

    Returns:
        Standard Lambda API response dictionary.
    """
    start_time = datetime.now(UTC)
    records = event.get("Records", [])

    if not records:
        logger.warning("Lambda invoked with empty Records array")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "No S3 event records provided"}),
        }

    processed_batches = []

    # Initialize S3 client if not injected
    if s3_client is None and boto3 is not None:
        s3_client = boto3.client("s3")

    for rec in records:
        s3_info = rec.get("s3", {})
        bucket_name = s3_info.get("bucket", {}).get("name", "")
        raw_key = s3_info.get("object", {}).get("key", "")
        object_key = urllib.parse.unquote_plus(raw_key)

        logger.info("Processing S3 object s3://%s/%s", bucket_name, object_key)

        # Retrieve file content from S3 (or mock client)
        file_content = ""
        if s3_client is not None:
            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                file_content = response["Body"].read().decode("utf-8")
            except Exception as e:
                logger.error(
                    "Failed to read s3://%s/%s: %s", bucket_name, object_key, e
                )
                processed_batches.append(
                    {
                        "bucket": bucket_name,
                        "key": object_key,
                        "status": "S3_READ_ERROR",
                        "error": str(e),
                    }
                )
                continue
        else:
            file_content = rec.get("simulated_content", "[]")

        # Process and validate the batch
        batch_summary = process_claims_batch(file_content, object_key)
        batch_summary["bucket"] = bucket_name
        batch_summary["key"] = object_key

        # If quarantined records exist, route to quarantine/ prefix in S3
        if batch_summary["quarantine_count"] > 0 and s3_client is not None:
            quarantine_key = f"quarantine/{os.path.basename(object_key)}"
            try:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=quarantine_key,
                    Body=json.dumps(batch_summary["quarantined_records"], indent=2),
                    ContentType="application/json",
                )
                logger.info(
                    "Routed %d quarantined records to s3://%s/%s",
                    batch_summary["quarantine_count"],
                    bucket_name,
                    quarantine_key,
                )
            except Exception as e:
                logger.warning("Failed to store quarantine object: %s", e)

        processed_batches.append(batch_summary)

    duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000.0

    response_payload = {
        "statusCode": 200,
        "execution_time_ms": round(duration_ms, 2),
        "batches_processed": len(processed_batches),
        "results": processed_batches,
    }

    logger.info(
        "Lambda execution complete in %.2fms. Batches: %d",
        duration_ms,
        len(processed_batches),
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_payload),
    }
