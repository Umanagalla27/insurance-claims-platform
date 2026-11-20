# ==============================================================================
# modules/lambda/variables.tf
# ==============================================================================

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 landing bucket triggering ingestion"
  type        = string
}

variable "s3_bucket_id" {
  description = "Name/ID of the S3 landing bucket"
  type        = string
}

variable "lambda_memory_size" {
  description = "Allocated RAM (MB) — 128 MB is optimal for Free Tier execution"
  type        = number
  default     = 128
}

variable "lambda_timeout" {
  description = "Maximum execution timeout in seconds"
  type        = number
  default     = 60
}
