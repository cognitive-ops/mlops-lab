resource "random_password" "mlflow_rds_password" {
  length           = 16
  special          = true
  override_special = "_#$*-=+"
}
resource "aws_secretsmanager_secret" "rds_secret" {
  name = "mlflow-db-password"
}

resource "aws_secretsmanager_secret_version" "rds_secret_version" {
  secret_id     = aws_secretsmanager_secret.rds_secret.id
  secret_string = random_password.mlflow_rds_password.result
}

resource "aws_db_instance" "mlflow_db" {
  identifier             = "mlflow-db"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = "db.t3.micro"
  db_name                = "mlflowdb"
  username               = var.mlflow_db_user
  password               = random_password.mlflow_rds_password.result
  vpc_security_group_ids = [aws_security_group.mlflow_db_sg.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
}

resource "aws_security_group" "mlflow_db_sg" {
  name        = "mlflow-db-sg"
  description = "Security group for MLflow PostgreSQL DB"

  vpc_id = data.aws_vpc.default.id

  # Allow PostgreSQL connection from MLflow EC2
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.mlflow_sg.id] # Allows only MLflow EC2 to access
  }

  # Allow all outgoing traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}