resource "aws_s3_bucket" "terraform_state" {
  bucket        = var.terraform_state_bucket
  force_destroy = false
}

# Enable Versioning to track state history
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Block Public Access for security
resource "aws_s3_bucket_public_access_block" "s3_public_block" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "mlflow_bucket" {
  bucket = var.mlflow_s3_bucket

}