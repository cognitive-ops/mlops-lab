resource "aws_security_group" "gpu_instance_sg" {
  name        = "${var.project}-ml-instance-sg"
  description = "Allow SSH and HTTPS"
  vpc_id      = var.vpc_id

  ingress {
    description      = "SSH"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  ingress {
    description      = "HTTPS"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  egress {
    description      = "Allow all outbound traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project}-ml-instance-sg"
    Project = var.project
    Owner = var.owner
  }
}

resource "tls_private_key" "gpu_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "gpu_key" {
  key_name   = "${var.project}-gpu-ec2-key"
  public_key = tls_private_key.gpu_key.public_key_openssh
}

resource "local_file" "private_key_pem" {
      filename        = pathexpand("~/.ssh/${aws_key_pair.gpu_key.key_name}.pem")
      content         = tls_private_key.gpu_key.private_key_pem
      file_permission = "0600" # Restrict access to the owner only
}

resource "aws_instance" "gpu_instance" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = aws_key_pair.gpu_key.key_name  
  subnet_id     = var.subnet_id
  security_groups = [aws_security_group.gpu_instance_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ssm_role.name

  # Root volume configuration
  root_block_device {
    volume_size = 100
    volume_type = "standard"
    encrypted   = true
    delete_on_termination = true   
   
  }

  tags = {
    Name = "${var.project}-ml-ec2"
    Project = var.project
    Owner = var.owner
  }
  user_data = <<-EOF
  #!/bin/bash
  echo "Starting setup..."
  sudo add-apt-repository ppa:graphics-drivers/ppa
  sudo apt update
  sudo apt install -y nvidia-driver-535
  EOF
}

# EBS Volume for additional storage
resource "aws_ebs_volume" "ml_data_volume" {
  availability_zone = aws_instance.gpu_instance.availability_zone
  size              = 200
  type              = "gp3"
  encrypted         = true
  
  tags = {
    Name = "${var.project}-ml-data-volume"
    Project = var.project
    Owner = var.owner
  }
}

# Attach EBS volume to EC2 instance
resource "aws_volume_attachment" "ml_data_attachment" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.ml_data_volume.id
  instance_id = aws_instance.gpu_instance.id
}

resource "aws_iam_role" "ssm_role" {
  name = "${var.project}-ssm_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Effect    = "Allow"
        Sid       = ""
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.ssm_role.name
}

resource "aws_iam_instance_profile" "ssm_role" {
  name = "ssm_instance_profile"
  role = aws_iam_role.ssm_role.name
}