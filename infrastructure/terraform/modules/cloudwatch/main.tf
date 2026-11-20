# ==============================================================================
# modules/cloudwatch/main.tf — Operational Observability & Metric Alarms
# ==============================================================================

# 1. CloudWatch Log Group for Lambda with FinOps Retention Limit (14 Days)
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-lambda-log-group"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# 2. CloudWatch Metric Alarm: High EC2 CPU Utilization (> 80%)
resource "aws_cloudwatch_metric_alarm" "ec2_high_cpu" {
  alarm_name          = "${var.project_name}-ec2-high-cpu-${var.environment}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80.0
  alarm_description   = "Triggers when EC2 instance CPU utilization breaches 80% for 2 consecutive 5-minute periods"

  dimensions = {
    InstanceId = var.ec2_instance_id
  }

  alarm_actions = var.notification_topic_arn != "" ? [var.notification_topic_arn] : []
  ok_actions    = var.notification_topic_arn != "" ? [var.notification_topic_arn] : []

  tags = {
    Name        = "${var.project_name}-ec2-cpu-alarm"
    Environment = var.environment
  }
}

# 3. CloudWatch Metric Alarm: Serverless Lambda Execution Errors (Errors >= 1)
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1.0
  alarm_description   = "Triggers immediately when Lambda claims ingestion handler experiences 1 or more runtime errors"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = var.notification_topic_arn != "" ? [var.notification_topic_arn] : []

  tags = {
    Name        = "${var.project_name}-lambda-error-alarm"
    Environment = var.environment
  }
}
