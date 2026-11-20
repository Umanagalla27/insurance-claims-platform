# ==============================================================================
# variables.tf — Root Terraform Variables with Free-Tier Constraints
# ==============================================================================

variable "aws_region" {
  description = "AWS region for infrastructure provisioning (us-east-1 recommended for Free Tier)"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (development, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name prefix used for resource naming and tagging"
  type        = string
  default     = "insurance-claims-platform"
}

variable "s3_bucket_prefix" {
  description = "Prefix for the globally unique S3 claims document landing bucket"
  type        = string
  default     = "insurance-claims-landing"
}

variable "ec2_instance_type" {
  description = "EC2 instance size strictly constrained to Free Tier eligible types"
  type        = string
  default     = "t2.micro"

  validation {
    condition     = contains(["t2.micro", "t3.micro"], var.ec2_instance_type)
    error_message = "Cost Protection Guardrail: Only t2.micro or t3.micro are permitted under the AWS Free-Tier budget."
  }
}

variable "ssh_key_name" {
  description = "Optional EC2 Key Pair name for SSH remote administration"
  type        = string
  default     = null
}

variable "allowed_ssh_cidr" {
  description = "CIDR block permitted to initiate SSH connections (port 22)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_http_cidr" {
  description = "CIDR block permitted to query FastAPI HTTP API (port 8000)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "monthly_budget_limit" {
  description = "Monthly AWS spend limit in USD (FinOps ₹0 Free-Tier tripwire)"
  type        = number
  default     = 1.0
}

variable "alert_email" {
  description = "Email destination for FinOps budget breaches and CloudWatch alarms"
  type        = string
  default     = "devops-alerts@insurance-intel.internal"
}
