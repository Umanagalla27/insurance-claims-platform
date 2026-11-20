# ==============================================================================
# modules/iam/variables.tf
# ==============================================================================

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 landing bucket for least-privilege scoping"
  type        = string
}
