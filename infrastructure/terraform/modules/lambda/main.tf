# ==============================================================================
# modules/lambda/main.tf — Serverless Claims Ingestion Function & S3 Event Trigger
# ==============================================================================

# 1. Package Python Lambda Source into Deployment ZIP
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../serverless/handler.py"
  output_path = "${path.module}/dist/claims_ingestion_lambda.zip"
}

# 2. IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-lambda-role"
  }
}

# 3. Scoped Least-Privilege Policy (CloudWatch Logs + S3 Read/Write)
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-lambda-policy-${var.environment}"
  description = "Allows Lambda to write CloudWatch logs and access S3 landing/quarantine prefixes"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogging"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "S3LandingAndQuarantineAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${var.s3_bucket_arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# 4. AWS Lambda Function (Free Tier: 128 MB RAM, 60s timeout)
resource "aws_lambda_function" "claims_ingestion_trigger" {
  function_name    = "${var.project_name}-claims-ingestion-${var.environment}"
  description      = "Validates and parses raw insurance claims dropped into S3 landing bucket"
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  role             = aws_iam_role.lambda_exec_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout

  environment {
    variables = {
      ENV         = var.environment
      S3_BUCKET   = var.s3_bucket_id
      LOG_LEVEL   = "INFO"
    }
  }

  tags = {
    Name = "${var.project_name}-lambda-ingestion"
    Tier = "ServerlessETL"
  }
}

# 5. Permission allowing S3 Bucket to invoke this Lambda Function
resource "aws_lambda_permission" "allow_s3_invocation" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.claims_ingestion_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_bucket_arn
}

# 6. S3 Event Notification triggering Lambda on file upload to raw-claims/
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = var.s3_bucket_id

  lambda_function {
    lambda_function_arn = aws_lambda_function.claims_ingestion_trigger.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw-claims/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3_invocation]
}
