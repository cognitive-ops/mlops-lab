

resource "aws_iam_role" "sagemaker_execution" {
  name = "sagemaker_execution_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sagemaker.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_policy_attachment" "sagemaker_full_access" {
  name       = "sagemaker_full_access"
  roles      = [aws_iam_role.sagemaker_execution.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_sagemaker_notebook_instance" "this" {
  name          = var.notebook_name
  instance_type = var.notebook_type # Change as needed
  role_arn      = aws_iam_role.sagemaker_execution.arn
  lifecycle_config_name = aws_sagemaker_notebook_instance_lifecycle_configuration.setup.name
}
resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "setup" {
  name = "my-lifecycle-config"

  on_start = <<EOF
#bin/bash
echo "Installing ffmpeg..."
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz
cd ffmpeg-7.0.2-amd64-static
sudo mv ffmpeg /usr/local/bin/
sudo mv ffprobe /usr/local/bin
sudo yum update -y
sudo yum groupinstall "Development Tools" -y
sudo yum install -y gcc-c++ python3 python3-devel ffmpeg ffmpeg-devel libsndfile
python3 -m pip install --upgrade pip setuptools wheel
pip3 install torch datasets librosa
EOF
}
