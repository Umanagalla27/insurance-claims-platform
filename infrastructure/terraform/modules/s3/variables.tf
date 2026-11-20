# ==============================================================================
# modules/s3/variables.tf
# ==============================================================================

variable "bucket_prefix" {
  description = "Prefix for S3 bucket name"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}
