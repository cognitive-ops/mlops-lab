#!/bin/bash
# SGLang Setup Script for AWS EC2 GPU Instance
# Runs SGLang via Docker (lmsysorg/sglang image) — avoids building flashinfer/sgl-kernel
# CUDA extensions from source, which is the fragile part of a bare pip install.

set -e

# Configuration Parameters (passed from Terraform)
MODEL_NAME="${model_name}"
MODEL_REPO="${model_repo}"
HF_TOKEN="${hf_token}"
SGLANG_PORT="${sglang_port}"
SGLANG_CONTEXT_LENGTH="${sglang_context_length}"
SGLANG_MEM_FRACTION_STATIC="${sglang_mem_fraction_static}"
SGLANG_TOOL_CALL_PARSER="${sglang_tool_call_parser}"
AWS_REGION="${aws_region}"
S3_BUCKET="${s3_bucket_name}"
LOG_GROUP="${log_group_name}"

# Logging
exec > >(tee /var/log/sglang-setup.log)
exec 2>&1

echo "=== SGLang Setup Started at $(date) ==="
echo "Model: $MODEL_NAME"
echo "Model Repo: $MODEL_REPO"
echo "SGLang Port: $SGLANG_PORT"
echo "Region: $AWS_REGION"

# Update system
echo "=== Updating system packages ==="
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y \
  build-essential \
  git \
  curl \
  wget \
  jq \
  htop \
  nvtop \
  tmux \
  awscli \
  ca-certificates \
  gnupg

# Install NVIDIA drivers
echo "=== Installing NVIDIA drivers ==="
sudo apt-get install -y \
  nvidia-driver-535 \
  nvidia-utils-535

# Install Docker
echo "=== Installing Docker ==="
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu

# Install NVIDIA Container Toolkit (lets Docker containers see the GPU)
echo "=== Installing NVIDIA Container Toolkit ==="
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Create model storage directory
echo "=== Setting up model storage ==="
sudo mkdir -p /mnt/models
sudo chown ubuntu:ubuntu /mnt/models
chmod 755 /mnt/models

# Format and mount additional EBS volume (if attached)
if [ -e /dev/nvme1n1 ]; then
  echo "Formatting /dev/nvme1n1 for model storage..."
  sudo mkfs.ext4 -F /dev/nvme1n1
  sudo mount /dev/nvme1n1 /mnt/models
  echo "/dev/nvme1n1 /mnt/models ext4 defaults,nofail 0 0" | sudo tee -a /etc/fstab
fi

# Install CloudWatch agent
if [ -n "$LOG_GROUP" ]; then
  echo "=== Installing CloudWatch Logs agent ==="
  wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
  sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
  rm amazon-cloudwatch-agent.deb
fi

# Environment file for the container (HF token, model config)
cat > /home/ubuntu/.sglang_env <<EOF
MODEL_NAME=$MODEL_NAME
MODEL_REPO=$MODEL_REPO
HF_TOKEN=$HF_TOKEN
SGLANG_PORT=$SGLANG_PORT
AWS_REGION=$AWS_REGION
S3_BUCKET=$S3_BUCKET
EOF
chmod 600 /home/ubuntu/.sglang_env

# Pre-pull the SGLang image
echo "=== Pulling SGLang image ==="
sudo docker pull lmsysorg/sglang:latest

# Create systemd service for SGLang (runs the official Docker image)
echo "=== Creating SGLang systemd service ==="
sudo tee /etc/systemd/system/sglang.service > /dev/null <<EOF
[Unit]
Description=SGLang Inference Server
After=network.target docker.service
Requires=docker.service
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
EnvironmentFile=-/home/ubuntu/.sglang_env

ExecStartPre=-/usr/bin/docker rm -f sglang-server
ExecStart=/usr/bin/docker run --rm --name sglang-server \
    --gpus all \
    --shm-size 16g \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    -p $SGLANG_PORT:$SGLANG_PORT \
    -v /mnt/models:/root/.cache/huggingface \
    -e HF_TOKEN=$HF_TOKEN \
    lmsysorg/sglang:latest \
    python3 -m sglang.launch_server \
      --model-path $MODEL_REPO \
      --host 0.0.0.0 \
      --port $SGLANG_PORT \
      --context-length $SGLANG_CONTEXT_LENGTH \
      --mem-fraction-static $SGLANG_MEM_FRACTION_STATIC \
      --tool-call-parser $SGLANG_TOOL_CALL_PARSER
ExecStop=/usr/bin/docker stop sglang-server

Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sglang

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sglang
# Not started here — the NVIDIA kernel module isn't loaded until after the
# reboot at the end of this script. `enable` makes systemd start it on boot.

# Health check script
sudo tee /usr/local/bin/check_sglang_health.sh > /dev/null <<'HEALTH_EOF'
#!/bin/bash
SGLANG_PORT=${SGLANG_PORT:-30000}
RETRY_COUNT=0
MAX_RETRIES=60

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if curl -s http://localhost:$SGLANG_PORT/health > /dev/null 2>&1; then
    echo "SGLang is healthy"
    exit 0
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "Waiting for SGLang to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 10
done

echo "SGLang health check failed"
exit 1
HEALTH_EOF

sudo chmod +x /usr/local/bin/check_sglang_health.sh

# CloudWatch Logs configuration
if [ -n "$LOG_GROUP" ]; then
  echo "=== Configuring CloudWatch Logs ==="
  sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json > /dev/null <<EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/sglang-setup.log",
            "log_group_name": "$LOG_GROUP",
            "log_stream_name": "setup"
          },
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "$LOG_GROUP",
            "log_stream_name": "syslog"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "SGLang",
    "metrics_collected": {
      "mem": {
        "measurement": [{"name": "mem_used_percent", "rename": "MemoryUtilization"}],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [{"name": "used_percent", "rename": "DiskUtilization"}],
        "metrics_collection_interval": 60,
        "resources": ["/mnt/models"]
      }
    }
  }
}
EOF

  sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s
fi

# Create helpful scripts
echo "=== Creating utility scripts ==="
cat > /home/ubuntu/test_api.sh <<'TEST_EOF'
#!/bin/bash
HOST=${1:-"http://localhost:30000"}
echo "Testing SGLang API at: $HOST"
echo ""
echo "=== Available Models ==="
curl -s "$HOST/v1/models" | jq '.'
echo ""
echo "=== Test Chat Completion Request ==="
curl -s -X POST "$HOST/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "What is artificial intelligence?"}],
    "max_tokens": 100,
    "temperature": 0.7
  }' | jq '.'
TEST_EOF

chmod +x /home/ubuntu/test_api.sh

# Setup log rotation
sudo tee /etc/logrotate.d/sglang > /dev/null <<'LOGROTATE_EOF'
/var/log/sglang-setup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
LOGROTATE_EOF

# Final messages
echo "=== SGLang Setup Complete ==="
echo "Service Status: sudo systemctl status sglang"
echo "View Logs: sudo journalctl -u sglang -f"
echo "Test API: /home/ubuntu/test_api.sh"

# Reboot to load the NVIDIA kernel module — sglang.service is enabled and will
# start automatically once the instance comes back up.
echo "=== Rebooting to load NVIDIA drivers ==="
sudo reboot
