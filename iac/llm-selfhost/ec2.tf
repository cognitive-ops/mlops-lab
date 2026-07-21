# EC2 Key Pair
resource "tls_private_key" "main" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-key"
  public_key = tls_private_key.main.public_key_openssh

  tags = {
    Name = "${var.project_name}-key"
  }
}

# Store private key locally
resource "local_file" "private_key" {
  filename        = pathexpand("~/.ssh/${aws_key_pair.main.key_name}.pem")
  content         = tls_private_key.main.private_key_pem
  file_permission = "0600"
}

# Additional EBS Volume for Models
resource "aws_ebs_volume" "model_storage" {
  availability_zone = data.aws_availability_zones.available.names[0]
  size              = var.model_volume_size
  type              = "gp3"
  iops              = 3000
  throughput        = 125

  tags = {
    Name = "${var.project_name}-model-volume"
  }
}

# User Data Script
locals {
  user_data_script = base64encode(templatefile("${path.module}/user_data.sh", {
    model_name                  = var.model_name
    model_repo                  = var.model_repo
    vllm_port                   = var.vllm_port
    vllm_max_model_len          = var.vllm_max_model_len
    vllm_gpu_memory_utilization = var.vllm_gpu_memory_utilization
    vllm_version                = var.vllm_version
    nvidia_driver_version       = var.nvidia_driver_version
    hf_token                    = var.hf_token
    aws_region                  = var.aws_region
    s3_bucket_name              = var.enable_s3_bucket ? aws_s3_bucket.artifacts[0].id : ""
    log_group_name              = var.enable_cloudwatch_monitoring ? aws_cloudwatch_log_group.vllm[0].name : ""
  }))
}

# EC2 Instance
resource "aws_instance" "llm" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.main.key_name
  iam_instance_profile   = aws_iam_instance_profile.llm_instance_profile.name
  
  # Network configuration
  network_interface {
    network_interface_id = aws_network_interface.main.id
    device_index         = 0
  }

  # Root volume
  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }

  # User data for setup
  user_data = local.user_data_script

  # CloudWatch monitoring
  monitoring = var.enable_cloudwatch_monitoring

  # Enable EBS optimization
  ebs_optimized = true

  tags = {
    Name = "${var.project_name}-instance"
  }

  depends_on = [
    aws_internet_gateway.main
  ]
}

# Attach Model Storage Volume
resource "aws_volume_attachment" "model_storage" {
  device_name             = "/dev/sdf"
  volume_id               = aws_ebs_volume.model_storage.id
  instance_id             = aws_instance.llm.id
  force_detach            = false
  skip_destroy            = false
}

# Elastic IP
resource "aws_eip" "llm" {
  instance = aws_instance.llm.id
  domain   = "vpc"

  depends_on = [aws_internet_gateway.main]

  tags = {
    Name = "${var.project_name}-eip"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "vllm" {
  count             = var.enable_cloudwatch_monitoring ? 1 : 0
  name              = "/aws/ec2/${var.project_name}/vllm"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-logs"
  }
}
