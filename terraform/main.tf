provider "aws" {
  region = var.region
}

# VPC (minimal)
resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
  tags = { Name = "invoicing-vpc" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, 1)
  availability_zone = data.aws_availability_zones.available.names[0]
}

# RDS Postgres
resource "aws_db_instance" "postgres" {
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "15"
  instance_class       = "db.t4g.small"
  name                 = var.db_name
  username             = var.db_user
  password             = var.db_password
  skip_final_snapshot  = true
  publicly_accessible  = false
  vpc_security_group_ids = [aws_security_group.db.id]
}

# ECR repo for API image
resource "aws_ecr_repository" "api" {
  name = "mijn_api"
}

# S3 for PDFs
resource "aws_s3_bucket" "pdfs" {
  bucket = var.pdf_bucket
  acl    = "private"
}

# ECS cluster and task/service are left as a skeleton — fill with modules or ECS task def
resource "aws_ecs_cluster" "cluster" {
  name = "invoicing-cluster"
}

# Security groups
resource "aws_security_group" "alb" {
  name   = "alb-sg"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 80; to_port = 80; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "db" {
  name   = "db-sg"
  vpc_id = aws_vpc.main.id
  ingress { from_port = 5432; to_port = 5432; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
  egress  { from_port = 0; to_port = 0; protocol = "-1"; cidr_blocks = ["0.0.0.0/0"] }
}

# Outputs
output "ecr_repo_url" {
  value = aws_ecr_repository.api.repository_url
}
