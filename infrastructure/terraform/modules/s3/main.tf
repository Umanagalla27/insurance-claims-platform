# ==============================================================================
# modules/s3/main.tf — Encrypted, Versioned, Public-Blocked S3 Landing Bucket
# ==============================================================================

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# 1. Primary S3 Storage Bucket
resource "aws_s3_bucket" "claims_landing" {
  bucket        = "${var.bucket_prefix}-${var.environment}-${random_id.bucket_suffix.hex}"
  force_destroy = true # Enables clean automated terraform destroy

  tags = {
    Name        = "${var.bucket_prefix}-${var.environment}"
    Purpose     = "Claims Raw Ingestion & ML Model Artifacts"
  }
}

# 2. Versioning for Regulatory Audit Trail
resource "aws_s3_bucket_versioning" "claims_versioning" {
  bucket = aws_s3_bucket.claims_landing.id

  versioning_configuration {
    status = "Enabled"
  }
}

# 3. Server-Side Encryption (SSE-S3 AES256 — Free, Zero KMS Overhead)
resource "aws_s3_bucket_server_side_encryption_configuration" "claims_sse" {
  bucket = aws_s3_bucket.claims_landing.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 4. Strict Public Access Block (CIS AWS Benchmark 2.1.5)
resource "aws_s3_bucket_public_access_block" "block_public" {
  bucket = aws_s3_bucket.claims_landing.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 5. Lifecycle Rule (Prunes stale versions to maintain Free-Tier 5 GB storage limit)
resource "aws_s3_bucket_lifecycle_configuration" "lifecycle" {
  bucket     = aws_s3_bucket.claims_landing.id
  depends_on = [aws_s3_bucket_versioning.claims_versioning]

  rule {
    id     = "prune-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
