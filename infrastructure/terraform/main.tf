# ==============================================================================
# main.tf — Root Terraform Module Orchestration
# Project: Insurance Claims Intelligence Platform (ICIP)
# ==============================================================================
# Architecture Standards:
#   1. AWS Free Tier Compliance (₹0 spend guarantee): t2.micro + S3 Standard + 20GB EBS.
#   2. Least-Privilege IAM Scoping: EC2 instances can only access the landing bucket.
#   3. Automated Cloud-Init Bootstrapping: Auto-installs Docker and runtime dependencies.
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. S3 Claims Landing & Artifact Storage Module
# ------------------------------------------------------------------------------
module "s3_storage" {
  source = "./modules/s3"

  bucket_prefix = var.s3_bucket_prefix
  environment   = var.environment
}

# ------------------------------------------------------------------------------
# 2. Least-Privilege IAM Roles & Profiles Module
# ------------------------------------------------------------------------------
module "iam_security" {
  source = "./modules/iam"

  project_name  = var.project_name
  environment   = var.environment
  s3_bucket_arn = module.s3_storage.bucket_arn
}

# ------------------------------------------------------------------------------
# 3. EC2 Compute & Network Security Module
# ------------------------------------------------------------------------------
module "ec2_compute" {
  source = "./modules/ec2"

  project_name              = var.project_name
  environment               = var.environment
  instance_type             = var.ec2_instance_type
  iam_instance_profile_name = module.iam_security.instance_profile_name
  ssh_key_name              = var.ssh_key_name
  allowed_ssh_cidr          = var.allowed_ssh_cidr
  allowed_http_cidr         = var.allowed_http_cidr
}
