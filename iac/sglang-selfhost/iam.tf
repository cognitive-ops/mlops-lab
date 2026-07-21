# IAM Role for EC2 Instance
resource "aws_iam_role" "llm_instance_role" {
  name        = "${var.project_name}-instance-role"
  description = "IAM role for SGLang instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-instance-role"
  }
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "llm_instance_profile" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.llm_instance_role.name
}

# IAM Policy for S3 Access
resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-s3-access"
  role = aws_iam_role.llm_instance_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:ListBucketVersions"
        ]
        Resource = [
          var.enable_s3_bucket ? aws_s3_bucket.artifacts[0].arn : "*",
          var.enable_s3_bucket ? "${aws_s3_bucket.artifacts[0].arn}/*" : "*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Policy for CloudWatch Logs
resource "aws_iam_role_policy" "cloudwatch_logs" {
  count = var.enable_cloudwatch_monitoring ? 1 : 0
  name  = "${var.project_name}-cloudwatch-logs"
  role  = aws_iam_role.llm_instance_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# IAM Policy for HuggingFace Token / Secrets Access
resource "aws_iam_role_policy" "secrets_access" {
  name = "${var.project_name}-secrets-access"
  role = aws_iam_role.llm_instance_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:${var.project_name}-*"
      }
    ]
  })
}

# IAM Policy for CloudWatch Monitoring
resource "aws_iam_role_policy" "cloudwatch_metrics" {
  count = var.enable_cloudwatch_monitoring ? 1 : 0
  name  = "${var.project_name}-cloudwatch-metrics"
  role  = aws_iam_role.llm_instance_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Policy for Systems Manager Session Manager (optional, for secure access)
resource "aws_iam_role_policy_attachment" "ssm_access" {
  role       = aws_iam_role.llm_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
