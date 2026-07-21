variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Instance type for MLflow EC2"
  type        = string
  default     = "t3.medium"
}

variable "mlflow_s3_bucket" {
  description = "S3 bucket for MLflow artifacts"
  type        = string
  default     = "mlflow-dev-s3-bucket"
}

variable "mlflow_db_user" {
  description = "Username for MLflow PostgreSQL database"
  type        = string
  default     = "mlflowuser"
}

variable "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  type        = string
  default     = "mlflow-dev-terraform-state-bucket"

}

variable "terraform_lock_table" {
  description = "DynamoDB table for Terraform state lock"
  type        = string
  default     = "mlflow-dev-terraform-state-lock"

}

variable "mlflow_admin_username" {
  description = "MLflow admin username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "mlflow_admin_password" {
  description = "MLflow admin password"
  type        = string
  sensitive   = true
}

variable "mlflow_flask_secret_key" {
  description = "Flask secret key for CSRF protection"
  type        = string
  sensitive   = true
}