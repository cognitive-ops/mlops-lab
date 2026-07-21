resource "aws_iam_role" "mlflow_role" {
  name = "mlflow_role"
  assume_role_policy = jsonencode({
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_instance_profile" "mlflow_profile" {
  name = "mlflow-profile"
  role = aws_iam_role.mlflow_role.name
}

resource "aws_iam_policy" "s3_policy" {
  name = "mlflow_s3_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::mlflow-dev-s3-bucket",
          "arn:aws:s3:::mlflow-dev-s3-bucket/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_s3_policy" {
  role       = aws_iam_role.mlflow_role.name
  policy_arn = aws_iam_policy.s3_policy.arn
}

resource "aws_iam_policy" "mlflow_secrets_policy" {
  name        = "mlflow-secrets-policy"
  description = "Allows EC2 to retrieve RDS credentials from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.rds_secret.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_secrets_policy" {
  role       = aws_iam_role.mlflow_role.name
  policy_arn = aws_iam_policy.mlflow_secrets_policy.arn
}