"""
Verification and Audit Script for Serverless Lambda Ingestion (ICIP-023).
Tests S3 event parsing, validation rules, quarantine routing, and Terraform module definitions.
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAMBDA_SRC = PROJECT_ROOT / "infrastructure" / "serverless" / "handler.py"
ETL_ALIAS = PROJECT_ROOT / "etl" / "lambda_handler.py"
TF_LAMBDA_DIR = PROJECT_ROOT / "infrastructure" / "terraform" / "modules" / "lambda"
TF_ROOT_MAIN = PROJECT_ROOT / "infrastructure" / "terraform" / "main.tf"

# Import handler directly from source file
sys.path.insert(0, str(PROJECT_ROOT))
from infrastructure.serverless.handler import lambda_handler, process_claims_batch, validate_claim_record


class MockS3Client:
    """Mock boto3 S3 client simulating cloud S3 API in tests and CI."""

    def __init__(self, objects: dict[str, str]):
        self.objects = objects
        self.stored_quarantine: dict[str, str] = {}

    def get_object(self, Bucket: str, Key: str):
        full_key = f"{Bucket}/{Key}"
        if full_key not in self.objects:
            raise KeyError(f"NoSuchKey: {Key} in {Bucket}")
        content = self.objects[full_key]

        class MockBody:
            def __init__(self, data: str):
                self.data = data.encode("utf-8")

            def read(self):
                return self.data

        return {"Body": MockBody(content)}

    def put_object(self, Bucket: str, Key: str, Body: str, ContentType: str = "application/json"):
        self.stored_quarantine[f"{Bucket}/{Key}"] = Body
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


def test_validation_logic():
    print("[1/5] Testing single claim validation rules...")
    # Valid
    ok, err = validate_claim_record({"claim_id": "CLM-001", "policy_id": "POL-1", "claim_amount": 1500.0})
    assert ok is True and err is None

    # Missing claim_id
    ok, err = validate_claim_record({"policy_id": "POL-1", "claim_amount": 1500.0})
    assert ok is False and "claim_id" in err

    # Negative amount
    ok, err = validate_claim_record({"claim_id": "CLM-002", "policy_id": "POL-1", "claim_amount": -50.0})
    assert ok is False and "claim_amount" in err

    # Missing policy_id
    ok, err = validate_claim_record({"claim_id": "CLM-003", "claim_amount": 500.0})
    assert ok is False and "policy_id" in err
    print("  -> Validation rules (positive amount, non-empty IDs) verified.")


def test_batch_processing_and_quarantine():
    print("[2/5] Testing batch processing and quarantine segmentation...")
    sample_batch = [
        {"claim_id": "CLM-101", "policy_id": "POL-AUTO-1", "claim_amount": 1200.00},
        {"claim_id": "CLM-102", "policy_id": "POL-AUTO-2", "claim_amount": -300.00}, # Invalid
        {"claim_id": "", "policy_id": "POL-AUTO-3", "claim_amount": 800.00},         # Invalid
        {"claim_id": "CLM-104", "policy_id": "POL-AUTO-4", "claim_amount": 2500.50}, # Valid
    ]
    raw_json = json.dumps(sample_batch)

    res = process_claims_batch(raw_json, "batch_001.json")
    assert res["status"] == "PROCESSED"
    assert res["total_records"] == 4
    assert res["clean_count"] == 2
    assert res["quarantine_count"] == 2
    assert res["total_amount"] == 3700.50
    print("  -> Batch segmentation (2 clean vs 2 quarantined, sum $3,700.50) verified.")


def test_lambda_handler_s3_event_flow():
    print("[3/5] Simulating full S3 Event Notification trigger flow...")
    test_bucket = "insurance-landing-test-bucket"
    test_key = "raw-claims/batch_2026_01.json"

    batch_payload = json.dumps([
        {"claim_id": "CLM-901", "policy_id": "POL-HOME-1", "claim_amount": 4500.00},
        {"claim_id": "CLM-902", "policy_id": "POL-HOME-2", "claim_amount": 0.00}, # Invalid
    ])

    mock_s3 = MockS3Client({
        f"{test_bucket}/{test_key}": batch_payload
    })

    simulated_event = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": test_bucket},
                    "object": {"key": test_key},
                },
            }
        ]
    }

    resp = lambda_handler(event=simulated_event, s3_client=mock_s3)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["batches_processed"] == 1
    batch_res = body["results"][0]
    assert batch_res["clean_count"] == 1
    assert batch_res["quarantine_count"] == 1

    # Verify quarantine routing occurred
    quarantine_key = f"{test_bucket}/quarantine/batch_2026_01.json"
    assert quarantine_key in mock_s3.stored_quarantine
    print("  -> Full S3 event trigger, ingestion, and S3 quarantine put_object verified.")


def test_terraform_lambda_module():
    print("[4/5] Auditing Terraform Serverless Lambda Module...")
    assert (TF_LAMBDA_DIR / "main.tf").is_file()
    assert (TF_LAMBDA_DIR / "variables.tf").is_file()
    assert (TF_LAMBDA_DIR / "outputs.tf").is_file()

    content = (TF_LAMBDA_DIR / "main.tf").read_text(encoding="utf-8")
    assert "archive_file" in content, "Must use archive_file to package zip"
    assert "aws_lambda_function" in content, "Missing aws_lambda_function"
    assert 'runtime          = "python3.12"' in content, "Runtime must be Python 3.12"
    assert "memory_size      = var.lambda_memory_size" in content, "Must configure memory size"
    assert "aws_lambda_permission" in content, "Missing S3 invocation permission"
    assert "aws_s3_bucket_notification" in content, "Missing S3 bucket notification trigger"
    assert "raw-claims/" in content, "Trigger must filter prefix raw-claims/"
    print("  -> Terraform Lambda module verified: Python 3.12, S3 permission, and S3 event notification.")


def test_root_terraform_wiring():
    print("[5/5] Auditing root Terraform orchestration wiring...")
    main_tf = TF_ROOT_MAIN.read_text(encoding="utf-8")
    assert 'module "lambda_ingestion"' in main_tf, "Root main.tf must call module lambda_ingestion"
    assert "outputs.tf" in [f.name for f in TF_ROOT_MAIN.parent.iterdir()]
    out_tf = (TF_ROOT_MAIN.parent / "outputs.tf").read_text(encoding="utf-8")
    assert "lambda_function_arn" in out_tf, "outputs.tf must export lambda_function_arn"
    print("  -> Root Terraform orchestration wiring and outputs confirmed.")


def main():
    print("================================================================================")
    print("    Insurance Claims Intelligence Platform — Serverless Lambda Audit (ICIP-023)")
    print("================================================================================")
    try:
        test_validation_logic()
        test_batch_processing_and_quarantine()
        test_lambda_handler_s3_event_flow()
        test_terraform_lambda_module()
        test_root_terraform_wiring()
        print("\n================================================================================")
        print(" [SUCCESS] All 5 Serverless Lambda Ingestion audit checks PASSED!              ")
        print("================================================================================")
    except AssertionError as e:
        print(f"\n[FAIL] Audit failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
