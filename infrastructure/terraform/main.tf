# ==============================================================================
# main.tf — Root Terraform Module Orchestration
# Project: Insurance Claims Intelligence Platform (ICIP)
# ==============================================================================
# Architecture Standards:
#   1. AWS Free Tier Compliance (₹0 spend guarantee): t2.micro + S3 Standard + 20GB EBS.
#   2. Least-Privilege IAM Scoping: EC2 instances can only access the landing bucket.
#   3. Automated Cloud-Init Bootstrapping: Auto-installs Docker and runtime dependencies.
#   4. FinOps & Operational Observability: CloudWatch alarms + $1 Budget tripwire.
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

# ------------------------------------------------------------------------------
# 4. Serverless Event-Driven Claims Ingestion Module (AWS Lambda)
# ------------------------------------------------------------------------------
module "lambda_ingestion" {
  source = "./modules/lambda"

  project_name  = var.project_name
  environment   = var.environment
  s3_bucket_arn = module.s3_storage.bucket_arn
  s3_bucket_id  = module.s3_storage.bucket_id
}

# ------------------------------------------------------------------------------
# 5. Operational Observability & CloudWatch Alarms Module
# ------------------------------------------------------------------------------
module "cloudwatch_monitoring" {
  source = "./modules/cloudwatch"

  project_name         = var.project_name
  environment          = var.environment
  ec2_instance_id      = module.ec2_compute.instance_id
  lambda_function_name = module.lambda_ingestion.lambda_function_name
}

# ------------------------------------------------------------------------------
# 6. FinOps Cost Protection Guardrail (Zero-Cost / $1 Tripwire AWS Budget)
# ------------------------------------------------------------------------------
resource "aws_budgets_budget" "zero_spend_guardrail" {
  name              = "${var.project_name}-finops-guardrail-${var.environment}"
  budget_type       = "COST"
  limit_amount      = tostring(var.monthly_budget_limit)
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2026-01-01_00:00"

  # Warning Alert: Triggers when forecasted monthly spend exceeds 80% of $1.00
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }

  # Critical Alert: Triggers when actual monthly spend exceeds 100% of $1.00
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
