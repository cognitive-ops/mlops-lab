variable "ec2_instance_id" {
  description = "EC2 instance ID for MLflow server"
  type        = string
  default     = "i-051eae3ec45b80705"
}

variable "rds_instance_id" {
  description = "RDS instance ID for MLflow database"
  type        = string
  default     = "mlflow-db"
}

variable "api_key" {
  description = "API key for Lambda function authentication"
  type        = string
  sensitive   = true
}
