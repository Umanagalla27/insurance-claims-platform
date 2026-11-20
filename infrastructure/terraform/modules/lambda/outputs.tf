# ==============================================================================
# modules/lambda/outputs.tf
# ==============================================================================

output "lambda_arn" {
  description = "The ARN of the provisioned Lambda Function"
  value       = aws_lambda_function.claims_ingestion_trigger.arn
}

output "lambda_function_name" {
  description = "The Name of the provisioned Lambda Function"
  value       = aws_lambda_function.claims_ingestion_trigger.function_name
}

output "lambda_role_arn" {
  description = "The ARN of the IAM Execution Role assigned to Lambda"
  value       = aws_iam_role.lambda_exec_role.arn
}
