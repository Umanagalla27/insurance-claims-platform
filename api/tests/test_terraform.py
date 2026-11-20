"""
Automated Pytest Suite for Terraform Infrastructure as Code (ICIP-022).
Asserts that Terraform modules, Free-Tier constraints, security policies, and resource configurations conform to production standards.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TF_ROOT = PROJECT_ROOT / "infrastructure" / "terraform"


class TestTerraformArchitecture:
    """Test suite validating Terraform Infrastructure as Code definitions."""

    def test_root_terraform_files_exist(self):
        assert (TF_ROOT / "versions.tf").is_file()
        assert (TF_ROOT / "variables.tf").is_file()
        assert (TF_ROOT / "main.tf").is_file()
        assert (TF_ROOT / "outputs.tf").is_file()
        assert (TF_ROOT / "terraform.tfvars.example").is_file()

    def test_free_tier_instance_type_variable_validation(self):
        content = (TF_ROOT / "variables.tf").read_text(encoding="utf-8")
        assert 'default     = "t2.micro"' in content
        assert 'contains(["t2.micro", "t3.micro"], var.ec2_instance_type)' in content

    def test_s3_storage_security_and_encryption(self):
        content = (TF_ROOT / "modules" / "s3" / "main.tf").read_text(encoding="utf-8")
        assert "aws_s3_bucket" in content
        assert "aws_s3_bucket_versioning" in content
        assert "sse_algorithm = \"AES256\"" in content
        assert "block_public_acls       = true" in content
        assert "block_public_policy     = true" in content

    def test_iam_least_privilege_policy(self):
        content = (TF_ROOT / "modules" / "iam" / "main.tf").read_text(encoding="utf-8")
        assert "aws_iam_role" in content
        assert "ec2.amazonaws.com" in content
        assert "s3:GetObject" in content
        assert "s3:PutObject" in content
        assert "aws_iam_instance_profile" in content

    def test_ec2_compute_and_bootstrap_script(self):
        content = (TF_ROOT / "modules" / "ec2" / "main.tf").read_text(encoding="utf-8")
        assert "aws_security_group" in content
        assert "from_port   = 8000" in content
        assert "from_port   = 22" in content
        assert "aws_instance" in content
        assert "volume_size           = 20" in content
        assert "user_data" in content
        assert "dnf install -y docker" in content
