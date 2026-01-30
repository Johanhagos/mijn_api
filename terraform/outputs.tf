output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "s3_bucket" {
  value = aws_s3_bucket.pdfs.bucket
}
