# ==============================================================================
# modules/ec2/outputs.tf
# ==============================================================================

output "instance_id" {
  description = "The ID of the EC2 instance"
  value       = aws_instance.api_server.id
}

output "public_ip" {
  description = "Public IPv4 address assigned to the EC2 instance"
  value       = aws_instance.api_server.public_ip
}

output "public_dns" {
  description = "Public DNS name assigned to the EC2 instance"
  value       = aws_instance.api_server.public_dns
}

output "security_group_id" {
  description = "ID of the associated Security Group"
  value       = aws_security_group.api_sg.id
}
