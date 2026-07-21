# MLflow Authentication Secrets
# Store admin credentials in AWS Secrets Manager

resource "aws_secretsmanager_secret" "mlflow_auth_secret" {
  name        = "mlflow-auth-credentials"
  description = "MLflow authentication credentials (username, password, Flask secret)"
}

resource "aws_secretsmanager_secret_version" "mlflow_auth_secret_version" {
  secret_id = aws_secretsmanager_secret.mlflow_auth_secret.id
  secret_string = jsonencode({
    username          = var.mlflow_admin_username
    password          = var.mlflow_admin_password
    flask_secret_key  = var.mlflow_flask_secret_key
  })
}
