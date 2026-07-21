terraform {
  backend "s3" {
    bucket         = "mlflow-dev-terraform-state-bucket"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "mlflow-dev-terraform-state-lock"
    encrypt        = true
  }
}