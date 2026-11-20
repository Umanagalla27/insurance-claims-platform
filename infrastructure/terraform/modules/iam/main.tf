# ==============================================================================
# modules/iam/main.tf — Least-Privilege IAM Roles & EC2 Instance Profile
# ==============================================================================

# 1. EC2 Assume Role Trust Policy
resource "aws_iam_role" "ec2_app_role" {
  name = "${var.project_name}-ec2-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ec2-role"
  }
}

# 2. Scoped S3 Access Policy (No wildcard resources; constrained to project bucket)
resource "aws_iam_policy" "s3_access_policy" {
  name        = "${var.project_name}-s3-policy-${var.environment}"
  description = "Allows EC2 instances to read/write claims data and model artifacts"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListBucketContents"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = var.s3_bucket_arn
      },
      {
        Sid    = "ReadWriteClaimsObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${var.s3_bucket_arn}/*"
      }
    ]
  })
}

# 3. Policy Attachment
resource "aws_iam_role_policy_attachment" "attach_s3" {
  role       = aws_iam_role.ec2_app_role.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}

# 4. EC2 Instance Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile-${var.environment}"
  role = aws_iam_role.ec2_app_role.name
}
