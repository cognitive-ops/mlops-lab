output "mlflow_db_host" {
  description = "RDS endpoint for MLflow database"
  value       = aws_db_instance.mlflow_db.endpoint
}