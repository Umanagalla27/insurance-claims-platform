# ==============================================================================
# outputs.tf — Root Terraform Stack Outputs
# ==============================================================================

output "s3_bucket_name" {
  description = "Name of the provisioned S3 landing bucket"
  value       = module.s3_storage.bucket_id
}

output "s3_bucket_arn" {
  description = "ARN of the provisioned S3 landing bucket"
  value       = module.s3_storage.bucket_arn
}

output "ec2_public_ip" {
  description = "Public IP address of the deployed EC2 API Gateway node"
  value       = module.ec2_compute.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the deployed EC2 API Gateway node"
  value       = module.ec2_compute.public_dns
}

output "ec2_security_group_id" {
  description = "Security Group ID governing ingress/egress"
  value       = module.ec2_compute.security_group_id
}

output "iam_role_arn" {
  description = "ARN of the IAM role attached to the EC2 host"
  value       = module.iam_security.role_arn
}

output "api_endpoint_url" {
  description = "Public URL for accessing the FastAPI documentation and health probe"
  value       = "http://${module.ec2_compute.public_ip}:8000/docs"
}

output "lambda_function_arn" {
  description = "ARN of the serverless claims ingestion trigger Lambda"
  value       = module.lambda_ingestion.lambda_arn
}

output "lambda_function_name" {
  description = "Name of the serverless claims ingestion trigger Lambda"
  value       = module.lambda_ingestion.lambda_function_name
}

output "ec2_cpu_alarm_arn" {
  description = "ARN of the EC2 High CPU CloudWatch Alarm"
  value       = module.cloudwatch_monitoring.ec2_cpu_alarm_arn
}

output "lambda_error_alarm_arn" {
  description = "ARN of the Lambda Error CloudWatch Alarm"
  value       = module.cloudwatch_monitoring.lambda_error_alarm_arn
}

output "cloudwatch_dashboard_name" {
  description = "Name of the provisioned CloudWatch Executive Dashboard"
  value       = module.cloudwatch_monitoring.dashboard_name
}

output "finops_budget_name" {
  description = "Name of the AWS FinOps zero-spend budget tripwire"
  value       = aws_budgets_budget.zero_spend_guardrail.name
}
