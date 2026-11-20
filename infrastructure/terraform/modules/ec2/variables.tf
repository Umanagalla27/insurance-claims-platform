# ==============================================================================
# modules/ec2/variables.tf
# ==============================================================================

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance size"
  type        = string
  default     = "t2.micro"
}

variable "iam_instance_profile_name" {
  description = "IAM instance profile name attached to the EC2 host"
  type        = string
}

variable "ssh_key_name" {
  description = "Key pair name for SSH access"
  type        = string
  default     = null
}

variable "allowed_ssh_cidr" {
  description = "Permitted CIDR block for SSH"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_http_cidr" {
  description = "Permitted CIDR block for FastAPI HTTP ingress"
  type        = string
  default     = "0.0.0.0/0"
}
