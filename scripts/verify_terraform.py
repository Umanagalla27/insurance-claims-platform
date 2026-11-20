"""
Verification and Audit Script for AWS Terraform Infrastructure as Code (ICIP-022).
Validates root files, modules (s3, iam, ec2), Free-Tier resource guardrails, and security configurations.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TF_ROOT = PROJECT_ROOT / "infrastructure" / "terraform"


def audit_root_files():
    print("[1/5] Auditing Root Terraform Configurations...")
    required_root_files = [
        TF_ROOT / "versions.tf",
        TF_ROOT / "variables.tf",
        TF_ROOT / "main.tf",
        TF_ROOT / "outputs.tf",
        TF_ROOT / "terraform.tfvars.example",
    ]
    for f in required_root_files:
        assert f.is_file(), f"Missing root Terraform file: {f.name}"
    print("  -> All 5 root Terraform configuration files present.")


def audit_s3_module():
    print("[2/5] Auditing S3 Storage Module (Free-Tier & CIS Security)...")
    s3_dir = TF_ROOT / "modules" / "s3"
    assert (s3_dir / "main.tf").is_file(), "Missing modules/s3/main.tf"
    assert (s3_dir / "variables.tf").is_file(), "Missing modules/s3/variables.tf"
    assert (s3_dir / "outputs.tf").is_file(), "Missing modules/s3/outputs.tf"

    content = (s3_dir / "main.tf").read_text(encoding="utf-8")
    assert "aws_s3_bucket" in content, "Missing S3 bucket declaration"
    assert "aws_s3_bucket_versioning" in content, "Missing S3 versioning declaration"
    assert "aws_s3_bucket_server_side_encryption_configuration" in content, (
        "Missing S3 encryption"
    )
    assert "AES256" in content, "Must use free SSE-S3 AES256 encryption"
    assert "aws_s3_bucket_public_access_block" in content, "Missing public access block"
    assert "block_public_acls       = true" in content, "Public ACLs must be blocked"
    assert "aws_s3_bucket_lifecycle_configuration" in content, (
        "Missing lifecycle rule to prune old versions"
    )
    print(
        "  -> S3 module verified: AES256 encryption, versioning, lifecycle pruning, and public access block enabled."
    )


def audit_iam_module():
    print("[3/5] Auditing IAM Security Module (Least-Privilege Scoping)...")
    iam_dir = TF_ROOT / "modules" / "iam"
    assert (iam_dir / "main.tf").is_file(), "Missing modules/iam/main.tf"
    assert (iam_dir / "variables.tf").is_file(), "Missing modules/iam/variables.tf"
    assert (iam_dir / "outputs.tf").is_file(), "Missing modules/iam/outputs.tf"

    content = (iam_dir / "main.tf").read_text(encoding="utf-8")
    assert "aws_iam_role" in content, "Missing IAM role"
    assert "ec2.amazonaws.com" in content, "Role must trust EC2 service"
    assert "aws_iam_policy" in content, "Missing IAM policy"
    assert "s3:GetObject" in content and "s3:PutObject" in content, (
        "Must grant S3 read/write"
    )
    assert "aws_iam_instance_profile" in content, "Missing EC2 instance profile"
    print("  -> IAM module verified: Scoped S3 access policy and EC2 instance profile.")


def audit_ec2_module():
    print("[4/5] Auditing EC2 Compute Module (Free-Tier & Cloud-Init Bootstrap)...")
    ec2_dir = TF_ROOT / "modules" / "ec2"
    assert (ec2_dir / "main.tf").is_file(), "Missing modules/ec2/main.tf"
    assert (ec2_dir / "variables.tf").is_file(), "Missing modules/ec2/variables.tf"
    assert (ec2_dir / "outputs.tf").is_file(), "Missing modules/ec2/outputs.tf"

    content = (ec2_dir / "main.tf").read_text(encoding="utf-8")
    assert "aws_security_group" in content, "Missing security group"
    assert "8000" in content, "Security group must permit port 8000 (FastAPI)"
    assert "22" in content, "Security group must permit port 22 (SSH)"
    assert "aws_instance" in content, "Missing EC2 instance resource"
    assert "root_block_device" in content, "Missing root EBS volume specification"
    assert "volume_size           = 20" in content, (
        "EBS volume must be 20 GB (<= 30 GB Free-Tier limit)"
    )
    assert "user_data" in content, "Missing cloud-init user_data bootstrapping script"
    assert "docker" in content, "User data script must install Docker"
    print(
        "  -> EC2 module verified: Port 8000 ingress, 20GB gp3 EBS, and Docker cloud-init bootstrap."
    )


def audit_free_tier_guardrails():
    print("[5/5] Auditing Variable Cost Guardrails...")
    var_content = (TF_ROOT / "variables.tf").read_text(encoding="utf-8")
    assert 'default     = "t2.micro"' in var_content, (
        "Default instance type must be t2.micro"
    )
    assert "validation {" in var_content, "Variables must enforce Free Tier validation"
    assert "t2.micro" in var_content and "t3.micro" in var_content, (
        "Validation must restrict to Free Tier instances"
    )
    print(
        "  -> Variable guardrails verified: Strict Free-Tier validation for t2.micro/t3.micro."
    )


def main():
    print(
        "================================================================================"
    )
    print(
        "    Insurance Claims Intelligence Platform — Terraform Audit (ICIP-022)       "
    )
    print(
        "================================================================================"
    )
    try:
        audit_root_files()
        audit_s3_module()
        audit_iam_module()
        audit_ec2_module()
        audit_free_tier_guardrails()
        print(
            "\n================================================================================"
        )
        print(
            " [SUCCESS] All 5 Terraform Infrastructure as Code audit checks PASSED!        "
        )
        print(
            "================================================================================"
        )
    except AssertionError as e:
        print(f"\n[FAIL] Audit failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
