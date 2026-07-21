# =====================================================
# Lambda Function to Control MLflow EC2 and RDS
# =====================================================

# Lambda execution role
resource "aws_iam_role" "lambda_execution_role" {
  name_prefix = "mlflow-lambda-control-role-"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

# Lambda policy for EC2 and RDS control
resource "aws_iam_policy" "lambda_control_policy" {
  name_prefix = "mlflow-lambda-control-policy-"
  description = "Allows Lambda to start/stop EC2 and RDS instances"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowLogGroup",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "*"
      ]
    },
    {
      "Sid": "AllowEC2Control",
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowRDSControl",
      "Effect": "Allow",
      "Action": [
        "rds:StartDBInstance",
        "rds:StopDBInstance",
        "rds:DescribeDBInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowXRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

# Attach the control policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_control_policy_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_control_policy.arn
}

# Archive the Lambda function code
data "archive_file" "mlflow_control_archive" {
  type        = "zip"
  source_file = "${path.module}/lambda/mlflow_control.py"
  output_path = "${path.module}/lambda/mlflow_control.zip"
}

# Lambda function
resource "aws_lambda_function" "mlflow_control" {
  description      = "Lambda function to control MLflow EC2 and RDS instances"
  runtime          = "python3.12"
  handler          = "mlflow_control.lambda_handler"
  memory_size      = 128
  timeout          = 60
  function_name    = "mlflow-control"
  role             = aws_iam_role.lambda_execution_role.arn
  filename         = data.archive_file.mlflow_control_archive.output_path
  source_code_hash = data.archive_file.mlflow_control_archive.output_base64sha256

  environment {
    variables = {
      EC2_INSTANCE_ID = var.ec2_instance_id
      RDS_INSTANCE_ID = var.rds_instance_id
      API_KEY         = var.api_key
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "MLflow-Control-Lambda"
  }
}

# Lambda Function URL
resource "aws_lambda_function_url" "mlflow_control_url" {
  function_name      = aws_lambda_function.mlflow_control.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST"]
  }
}

# CloudWatch Log Group for the Lambda function
resource "aws_cloudwatch_log_group" "mlflow_control_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.mlflow_control.function_name}"
  retention_in_days = 14
}

# Output Lambda Function URL
output "lambda_function_url" {
  description = "Lambda Function URL for MLflow control"
  value       = aws_lambda_function_url.mlflow_control_url.function_url
}
