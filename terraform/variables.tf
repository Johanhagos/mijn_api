variable "region" { default = "eu-west-1" }
variable "vpc_cidr" { default = "10.0.0.0/16" }
variable "db_name" { default = "invoicing" }
variable "db_user" {}
variable "db_password" {}
variable "pdf_bucket" { default = "mijn-invoices-pdfs" }
