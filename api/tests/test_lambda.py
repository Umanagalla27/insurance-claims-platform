"""
Automated Pytest Suite for Serverless Claims Ingestion Lambda & S3 Notifications (ICIP-023).
Tests validation logic, batch segmentation, mock S3 event execution, and Terraform Lambda module definitions.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from etl.lambda_handler import (
    lambda_handler,
    process_claims_batch,
    validate_claim_record,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TF_ROOT = PROJECT_ROOT / "infrastructure" / "terraform"
LAMBDA_MODULE = TF_ROOT / "modules" / "lambda"


class TestLambdaValidationLogic:
    """Tests claim data validation and quarantine criteria."""

    def test_valid_claim_record(self):
        valid_claim = {
            "claim_id": "CLM-2026-9901",
            "policy_id": "POL-1001",
            "claim_amount": 1250.75,
            "incident_date": "2026-05-10",
        }
        is_valid, reason = validate_claim_record(valid_claim)
        assert is_valid is True
        assert reason is None

    def test_invalid_claim_missing_required_keys(self):
        invalid_claim = {
            "claim_id": "CLM-2026-9902",
            "claim_amount": 500.00,
        }
        is_valid, reason = validate_claim_record(invalid_claim)
        assert is_valid is False
        assert "Missing mandatory field 'policy_id'" in reason

    def test_invalid_claim_negative_or_zero_amount(self):
        negative_claim = {
            "claim_id": "CLM-2026-9903",
            "policy_id": "POL-1002",
            "claim_amount": -100.00,
            "incident_date": "2026-05-11",
        }
        is_valid, reason = validate_claim_record(negative_claim)
        assert is_valid is False
        assert "must be > 0.0" in reason

        zero_claim = {
            "claim_id": "CLM-2026-9904",
            "policy_id": "POL-1002",
            "claim_amount": 0,
            "incident_date": "2026-05-11",
        }
        is_valid, reason = validate_claim_record(zero_claim)
        assert is_valid is False
        assert "must be > 0.0" in reason

    def test_invalid_claim_empty_string_identifiers(self):
        empty_id_claim = {
            "claim_id": "   ",
            "policy_id": "POL-1003",
            "claim_amount": 750.00,
            "incident_date": "2026-05-12",
        }
        is_valid, reason = validate_claim_record(empty_id_claim)
        assert is_valid is False
        assert "Missing mandatory field 'claim_id'" in reason


class TestLambdaBatchProcessing:
    """Tests batch processing and segregation into clean and quarantine collections."""

    def test_process_claims_batch_segmentation(self):
        records = [
            {
                "claim_id": "CLM-001",
                "policy_id": "POL-001",
                "claim_amount": 1000.0,
                "incident_date": "2026-01-01",
            },
            {
                "claim_id": "CLM-002",
                "policy_id": "POL-002",
                "claim_amount": -50.0,
                "incident_date": "2026-01-02",
            },
            {
                "claim_id": "CLM-003",
                "policy_id": "",
                "claim_amount": 2500.0,
                "incident_date": "2026-01-03",
            },
            {
                "claim_id": "CLM-004",
                "policy_id": "POL-004",
                "claim_amount": 350.5,
                "incident_date": "2026-01-04",
            },
        ]
        result = process_claims_batch(records, "test_batch.json")
        assert result["total_records"] == 4
        assert result["clean_count"] == 2
        assert result["quarantine_count"] == 2
        assert result["total_amount"] == 1350.5
        assert len(result["clean_records"]) == 2
        assert len(result["quarantined_records"]) == 2
        assert "rejection_reason" in result["quarantined_records"][0]


class TestLambdaS3ExecutionFlow:
    """Tests Lambda handler invocation with simulated S3 event notifications."""

    def test_lambda_handler_s3_event_flow(self):
        mock_claims = [
            {
                "claim_id": "CLM-101",
                "policy_id": "POL-101",
                "claim_amount": 800.0,
                "incident_date": "2026-02-01",
            },
            {
                "claim_id": "CLM-102",
                "policy_id": "POL-102",
                "claim_amount": -20.0,
                "incident_date": "2026-02-02",
            },
        ]
        raw_body = json.dumps(mock_claims).encode("utf-8")

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: raw_body)}

        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-landing-bucket"},
                        "object": {"key": "raw-claims/batch_20260515.json"},
                    }
                }
            ]
        }

        response = lambda_handler(event, None, s3_client=mock_s3)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["statusCode"] == 200
        assert body["batches_processed"] == 1
        results = body["results"]
        assert len(results) == 1
        assert results[0]["clean_count"] == 1
        assert results[0]["quarantine_count"] == 1

        # Verify S3 quarantine put_object was called
        mock_s3.put_object.assert_called_once()
        put_kwargs = mock_s3.put_object.call_args[1]
        assert put_kwargs["Bucket"] == "test-landing-bucket"
        assert put_kwargs["Key"] == "quarantine/batch_20260515.json"
        quarantined_payload = json.loads(put_kwargs["Body"])
        assert len(quarantined_payload) == 1
        assert quarantined_payload[0]["record"]["claim_id"] == "CLM-102"


class TestTerraformLambdaModule:
    """Validates Terraform Lambda module and S3 event trigger configurations."""

    def test_lambda_module_files_exist(self):
        assert (LAMBDA_MODULE / "main.tf").is_file()
        assert (LAMBDA_MODULE / "variables.tf").is_file()
        assert (LAMBDA_MODULE / "outputs.tf").is_file()

    def test_lambda_terraform_resources(self):
        content = (LAMBDA_MODULE / "main.tf").read_text(encoding="utf-8")
        assert 'resource "aws_lambda_function" "claims_ingestion_trigger"' in content
        assert 'runtime          = "python3.12"' in content
        assert 'handler          = "handler.lambda_handler"' in content
        assert 'resource "aws_lambda_permission" "allow_s3_invocation"' in content
        assert 'resource "aws_s3_bucket_notification" "bucket_notification"' in content
        assert 'filter_prefix       = "raw-claims/"' in content

    def test_root_terraform_wiring(self):
        root_main = (TF_ROOT / "main.tf").read_text(encoding="utf-8")
        assert 'module "lambda_ingestion"' in root_main
        assert 'source = "./modules/lambda"' in root_main

        root_outputs = (TF_ROOT / "outputs.tf").read_text(encoding="utf-8")
        assert "lambda_function_arn" in root_outputs
        assert "lambda_function_name" in root_outputs
