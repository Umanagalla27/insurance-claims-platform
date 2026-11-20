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

# 4. CloudWatch Operational & Executive Telemetry Dashboard
resource "aws_cloudwatch_dashboard" "platform_overview" {
  dashboard_name = "${var.project_name}-operational-overview-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", var.ec2_instance_id, { stat = "Average", period = 300, color = "#ff7f0e" }],
            [".", "NetworkIn", ".", ".", { stat = "Sum", period = 300, yAxis = "right", color = "#1f77b4" }],
            [".", "NetworkOut", ".", ".", { stat = "Sum", period = 300, yAxis = "right", color = "#2ca02c" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "EC2 API Gateway Node Performance (CPU & Network I/O)"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_name, { stat = "Sum", period = 300, color = "#2ca02c" }],
            [".", "Errors", ".", ".", { stat = "Sum", period = 300, color = "#d62728" }],
            [".", "Throttles", ".", ".", { stat = "Sum", period = 300, color = "#9467bd" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Serverless Claims Ingestion Lambda (Invocations vs Runtime Errors)"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", var.lambda_function_name, { stat = "Average", period = 300, color = "#1f77b4" }],
            [".", "Duration", ".", ".", { stat = "p95", period = 300, color = "#e377c2" }],
            [".", "Duration", ".", ".", { stat = "Maximum", period = 300, color = "#d62728" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Lambda Execution Latency Profile (Avg, p95, Max)"
          period  = 300
        }
      },
      {
        type   = "text"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          markdown = "## Insurance Claims Intelligence Platform (ICIP)\n**FinOps Free-Tier SLA Guardrail:**\n- Max monthly spend: **$1.00 USD**\n- EC2 Target: `t2.micro` (750 hrs free)\n- S3 Storage: `Standard-IA` lifecycle after 30 days\n- Alerts: Amazon SNS + CloudWatch Alarms active"
        }
      }
    ]
  })
}
