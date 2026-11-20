# ==============================================================================
# modules/cloudwatch/outputs.tf
# ==============================================================================

output "ec2_cpu_alarm_arn" {
  description = "ARN of the EC2 High CPU Utilization CloudWatch Alarm"
  value       = aws_cloudwatch_metric_alarm.ec2_high_cpu.arn
}

output "lambda_error_alarm_arn" {
  description = "ARN of the Lambda Ingestion Error CloudWatch Alarm"
  value       = aws_cloudwatch_metric_alarm.lambda_errors.arn
}

output "lambda_log_group_arn" {
  description = "ARN of the Lambda CloudWatch Log Group"
  value       = aws_cloudwatch_log_group.lambda_log_group.arn
}

output "dashboard_name" {
  description = "Name of the provisioned CloudWatch Executive Dashboard"
  value       = aws_cloudwatch_dashboard.platform_overview.dashboard_name
}

output "dashboard_arn" {
  description = "ARN of the provisioned CloudWatch Executive Dashboard"
  value       = aws_cloudwatch_dashboard.platform_overview.dashboard_arn
}
