# Variables
variable "ssh_cidr" {
  type        = string
  description = "Your home IP in CIDR notation"
}

variable "ssh_key_name" {
  type        = string
  description = "Name of your existing AWS key pair"
}

# Provider
provider "aws" {
  region = "us-east-1"
}

# EC2 Instance with User Data to install Git and Docker
resource "aws_instance" "demo-instance" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t2.micro"
  iam_instance_profile   = "LabInstanceProfile"
  vpc_security_group_ids = [aws_security_group.web.id]
  key_name               = var.ssh_key_name

  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y git docker
              systemctl start docker
              systemctl enable docker
              usermod -aG docker ec2-user
              
              # Clone and Run App
              git clone https://github.com/justin-aj/go-hw.git /home/ec2-user/app
              cd /home/ec2-user/app/HW-1/web-service-gin
              docker build -t web-service-gin .
              docker run -d -p 8080:8080 web-service-gin
              EOF

  tags = {
    Name = "go-docker-instance"
  }
}

# Security Group - Allow SSH (22) and App (8080)
resource "aws_security_group" "web" {
  name        = "allow_ssh_and_web"
  description = "Allow SSH and port 8080"

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }

  # App access on port 8080
  ingress {
    description = "Web App"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Latest Amazon Linux 2023 AMI
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64-ebs"]
  }
}

# Outputs
output "ec2_public_dns" {
  value = aws_instance.demo-instance.public_dns
}

output "ec2_public_ip" {
  value = aws_instance.demo-instance.public_ip
}