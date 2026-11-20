# ==============================================================================
# modules/ec2/main.tf — Free-Tier EC2 t2.micro & Security Group Provisioner
# ==============================================================================

# 1. Fetch Latest Amazon Linux 2023 Minimal AMI (Free-Tier Eligible)
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 2. Strict Security Group
resource "aws_security_group" "api_sg" {
  name        = "${var.project_name}-sg-${var.environment}"
  description = "Controls ingress and egress for Insurance Claims Platform API"

  # Port 8000: FastAPI Core REST Gateway Ingress
  ingress {
    description = "FastAPI Application Port"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_http_cidr]
  }

  # Port 22: SSH Administration
  ingress {
    description = "SSH Remote Access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Outbound Egress: Allow outbound internet access for packages and Docker images
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

# 3. EC2 Instance (Strictly t2.micro — Free Tier 750 hours/month)
resource "aws_instance" "api_server" {
  ami                  = data.aws_ami.amazon_linux_2023.id
  instance_type        = var.instance_type
  iam_instance_profile = var.iam_instance_profile_name
  key_name             = var.ssh_key_name

  vpc_security_group_ids = [aws_security_group.api_sg.id]

  # Root EBS Volume (20 GB gp3 — Free Tier provides up to 30 GB total)
  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  # Cloud-Init User Data: Automates Docker installation and platform bootstrapping
  user_data = <<-EOF
              #!/bin/bash
              set -ex

              # 1. System Updates
              dnf update -y

              # 2. Install Docker & Git
              dnf install -y docker git
              systemctl enable --now docker
              usermod -aG docker ec2-user

              # 3. Install Docker Compose CLI Plugin
              DOCKER_CONFIG=/usr/local/lib/docker
              mkdir -p $DOCKER_CONFIG/cli-plugins
              curl -SL https://github.com/docker/compose/releases/download/v2.29.1/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
              chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

              echo "Insurance Claims Platform EC2 Node successfully initialized."
              EOF

  tags = {
    Name = "${var.project_name}-api-server"
    Tier = "AppServer"
  }
}
