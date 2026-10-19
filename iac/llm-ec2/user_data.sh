#!/bin/bash
# vLLM Setup Script for AWS EC2 GPU Instance
#
# cloud-init runs this file exactly once, on first boot. Loading the NVIDIA
# driver requires a reboot, and cloud-init user-data does NOT re-run after
# that reboot -- so everything that must happen post-driver-load (installing
# vLLM, starting the API server) lives in a separate systemd oneshot unit
# (vllm-bootstrap.service) that this script installs and enables. That unit
# is itself idempotent (guarded by a marker file) so it's safe if the
# instance reboots again later for unrelated reasons (e.g. a kernel update).
#
# NOTE ON TERRAFORM INTERPOLATION: this file is rendered by templatefile(),
# which does its own dollar-brace substitution over the raw text before bash
# ever sees it, regardless of bash quoting. Bash variables below are always
# referenced as plain $VAR without braces to avoid colliding with that. The
# few places bash genuinely needs brace-with-default parameter expansion,
# the opening dollar-brace is doubled up so templatefile emits it as a
# literal for bash to parse (see MODEL_REPO_ARG and HOST below).

set -euo pipefail

MODEL_NAME="${model_name}"
MODEL_REPO="${model_repo}"
VLLM_PORT="${vllm_port}"
VLLM_MAX_MODEL_LEN="${vllm_max_model_len}"
GPU_MEMORY_UTILIZATION="${vllm_gpu_memory_utilization}"
VLLM_VERSION="${vllm_version}"
NVIDIA_DRIVER_VERSION="${nvidia_driver_version}"
HF_TOKEN="${hf_token}"
AWS_REGION="${aws_region}"
S3_BUCKET="${s3_bucket_name}"
LOG_GROUP="${log_group_name}"

MARKER=/var/lib/vllm-bootstrap-done

exec > >(tee -a /var/log/vllm-setup.log)
exec 2>&1

echo "=== vLLM Setup (phase 1: base packages + GPU driver) started at $(date) ==="

if [ -f "$MARKER" ]; then
  echo "Bootstrap already completed on a previous boot -- nothing to do."
  exit 0
fi

echo "=== Updating system packages ==="
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo apt-get install -y \
  build-essential \
  python3.10 \
  python3.10-venv \
  python3-pip \
  python3-dev \
  git \
  curl \
  wget \
  jq \
  htop \
  nvtop \
  tmux \
  awscli \
  ubuntu-drivers-common

echo "=== Setting up model storage ==="
sudo mkdir -p /mnt/models

if [ -e /dev/nvme1n1 ] && ! mountpoint -q /mnt/models; then
  if ! blkid /dev/nvme1n1 > /dev/null 2>&1; then
    echo "Formatting /dev/nvme1n1 for model storage..."
    sudo mkfs.ext4 -F /dev/nvme1n1
  fi
  if ! grep -q /dev/nvme1n1 /etc/fstab; then
    echo "/dev/nvme1n1 /mnt/models ext4 defaults,nofail 0 0" | sudo tee -a /etc/fstab
  fi
  sudo mount /mnt/models
fi
sudo chown ubuntu:ubuntu /mnt/models
chmod 755 /mnt/models

echo "=== Installing NVIDIA driver ==="
if [ -n "$NVIDIA_DRIVER_VERSION" ]; then
  sudo apt-get install -y "nvidia-driver-$NVIDIA_DRIVER_VERSION"
else
  sudo ubuntu-drivers install --gpgpu
fi

echo "=== Writing vLLM config for post-reboot bootstrap ==="
sudo mkdir -p /etc/vllm
sudo tee /etc/vllm/vllm.env > /dev/null <<EOF
MODEL_NAME=$MODEL_NAME
MODEL_REPO=$MODEL_REPO
VLLM_PORT=$VLLM_PORT
VLLM_MAX_MODEL_LEN=$VLLM_MAX_MODEL_LEN
GPU_MEMORY_UTILIZATION=$GPU_MEMORY_UTILIZATION
VLLM_VERSION=$VLLM_VERSION
HF_TOKEN=$HF_TOKEN
AWS_REGION=$AWS_REGION
S3_BUCKET=$S3_BUCKET
LOG_GROUP=$LOG_GROUP
EOF
sudo chmod 600 /etc/vllm/vllm.env

echo "=== Installing post-reboot bootstrap script ==="
sudo tee /usr/local/bin/vllm-bootstrap.sh > /dev/null <<'BOOT_EOF'
#!/bin/bash
set -euo pipefail
exec > >(tee -a /var/log/vllm-setup.log)
exec 2>&1

MARKER=/var/lib/vllm-bootstrap-done
if [ -f "$MARKER" ]; then
  echo "vllm-bootstrap: marker present, skipping."
  exit 0
fi

# shellcheck disable=SC1091
source /etc/vllm/vllm.env

echo "=== vLLM Setup (phase 2: post-reboot) started at $(date) ==="

echo "=== Verifying GPU is visible ==="
for i in $(seq 1 12); do
  if nvidia-smi > /dev/null 2>&1; then
    nvidia-smi
    break
  fi
  echo "Waiting for NVIDIA driver to come up ($i/12)..."
  sleep 10
done
nvidia-smi || { echo "nvidia-smi still failing -- driver did not load, aborting bootstrap"; exit 1; }

echo "=== Creating vLLM virtualenv ==="
sudo -u ubuntu python3.10 -m venv /opt/vllm/venv
sudo -u ubuntu /opt/vllm/venv/bin/pip install --upgrade pip setuptools wheel

VLLM_PKG="vllm"
if [ -n "$VLLM_VERSION" ]; then
  VLLM_PKG="vllm==$VLLM_VERSION"
fi
sudo -u ubuntu /opt/vllm/venv/bin/pip install "$VLLM_PKG" "huggingface-hub>=0.26.0" "python-dotenv>=1.0.0"

if [ -n "$HF_TOKEN" ]; then
  echo "=== Logging in to Hugging Face Hub (gated model access) ==="
  sudo -u ubuntu /opt/vllm/venv/bin/huggingface-cli login --token "$HF_TOKEN" --add-to-git-credential
fi

echo "=== Creating vLLM systemd service ==="
sudo tee /etc/systemd/system/vllm.service > /dev/null <<SERVICE_EOF
[Unit]
Description=vLLM Inference Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="HF_HOME=/mnt/models/.huggingface"
Environment="CUDA_DEVICE_ORDER=PCI_BUS_ID"
Environment="VLLM_LOGGING_LEVEL=INFO"
EnvironmentFile=/etc/vllm/vllm.env

ExecStart=/opt/vllm/venv/bin/vllm serve \$MODEL_REPO \\
    --served-model-name \$MODEL_NAME \\
    --tensor-parallel-size 1 \\
    --port \$VLLM_PORT \\
    --max-model-len \$VLLM_MAX_MODEL_LEN \\
    --gpu-memory-utilization \$GPU_MEMORY_UTILIZATION \\
    --download-dir /mnt/models \\
    --dtype auto

Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vllm

MemoryLimit=90%
CPUQuota=90%

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
sudo systemctl enable vllm
sudo systemctl start vllm

echo "=== Creating utility scripts ==="
cat > /home/ubuntu/download_model.sh <<'DOWNLOAD_EOF'
#!/bin/bash
source /etc/vllm/vllm.env
MODEL_REPO_ARG=$${1:-$MODEL_REPO}
echo "Downloading model: $MODEL_REPO_ARG"
/opt/vllm/venv/bin/huggingface-cli download "$MODEL_REPO_ARG" --cache-dir /mnt/models/.huggingface/hub
DOWNLOAD_EOF
chmod +x /home/ubuntu/download_model.sh
chown ubuntu:ubuntu /home/ubuntu/download_model.sh

cat > /home/ubuntu/test_api.sh <<'TEST_EOF'
#!/bin/bash
source /etc/vllm/vllm.env
HOST=$${1:-"http://localhost:$VLLM_PORT"}
echo "Testing vLLM API at: $HOST"
echo ""
echo "=== Available Models ==="
curl -s "$HOST/v1/models" | jq '.'
echo ""
echo "=== Test Completion Request ==="
curl -s -X POST "$HOST/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL_NAME\", \"prompt\": \"What is artificial intelligence?\", \"max_tokens\": 100, \"temperature\": 0.7, \"top_p\": 0.9}" | jq '.'
TEST_EOF
chmod +x /home/ubuntu/test_api.sh
chown ubuntu:ubuntu /home/ubuntu/test_api.sh

sudo tee /usr/local/bin/check_vllm_health.sh > /dev/null <<'HEALTH_EOF'
#!/bin/bash
source /etc/vllm/vllm.env
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if curl -s "http://localhost:$VLLM_PORT/v1/models" > /dev/null 2>&1; then
    echo "vLLM is healthy"
    exit 0
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "Waiting for vLLM to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 10
done

echo "vLLM health check failed"
exit 1
HEALTH_EOF
sudo chmod +x /usr/local/bin/check_vllm_health.sh

sudo tee /etc/logrotate.d/vllm > /dev/null <<'LOGROTATE_EOF'
/var/log/vllm-setup.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
LOGROTATE_EOF

if [ -n "$LOG_GROUP" ]; then
  echo "=== Configuring CloudWatch Logs ==="
  sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json > /dev/null <<CW_EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/vllm-setup.log",
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
    "namespace": "vLLM",
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
CW_EOF
  sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s
fi

sudo touch "$MARKER"
echo "=== vLLM bootstrap complete at $(date) ==="
echo "Service Status: sudo systemctl status vllm"
echo "View Logs: sudo journalctl -u vllm -f"
echo "Test API: /home/ubuntu/test_api.sh"
BOOT_EOF

sudo chmod +x /usr/local/bin/vllm-bootstrap.sh

echo "=== Installing CloudWatch Logs agent ==="
if [ -n "$LOG_GROUP" ]; then
  wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
  sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
  rm amazon-cloudwatch-agent.deb
fi

echo "=== Registering vllm-bootstrap as a one-shot boot service ==="
sudo tee /etc/systemd/system/vllm-bootstrap.service > /dev/null <<'UNIT_EOF'
[Unit]
Description=vLLM post-reboot bootstrap (installs and starts the vLLM API server)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/vllm-bootstrap.sh

[Install]
WantedBy=multi-user.target
UNIT_EOF

sudo systemctl daemon-reload
sudo systemctl enable vllm-bootstrap

echo "=== Rebooting to load the NVIDIA driver; vllm-bootstrap.service takes over from here ==="
sudo reboot
