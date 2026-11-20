# ==============================================================================
# modules/cloudwatch/variables.tf
# ==============================================================================

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "ec2_instance_id" {
  description = "Target EC2 Instance ID to monitor for CPU utilization"
  type        = string
}

variable "lambda_function_name" {
  description = "Target Lambda function name to monitor for execution errors"
  type        = string
}

variable "notification_topic_arn" {
  description = "Optional SNS topic ARN for alarm notification routing"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "Retention period for CloudWatch logs in days (FinOps Free Tier optimization)"
  type        = number
  default     = 14
}
