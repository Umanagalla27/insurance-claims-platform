# ==============================================================================
# modules/s3/outputs.tf
# ==============================================================================

output "bucket_id" {
  description = "The name of the provisioned S3 bucket"
  value       = aws_s3_bucket.claims_landing.id
}

output "bucket_arn" {
  description = "The ARN of the provisioned S3 bucket"
  value       = aws_s3_bucket.claims_landing.arn
}

output "bucket_domain_name" {
  description = "The FQDN of the provisioned S3 bucket"
  value       = aws_s3_bucket.claims_landing.bucket_regional_domain_name
}
