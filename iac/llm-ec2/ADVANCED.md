# Advanced Configuration Guide

This guide covers advanced scenarios and configurations for production deployments.

## Table of Contents
1. [Multi-GPU Setup](#multi-gpu-setup)
2. [Multiple Models](#multiple-models)
3. [Auto-Scaling](#auto-scaling)
4. [HTTPS/TLS Setup](#httpstls-setup)
5. [Advanced Security](#advanced-security)
6. [Performance Tuning](#performance-tuning)
7. [Model Quantization](#model-quantization)
8. [Cost Optimization](#cost-optimization)

## Multi-GPU Setup

For instances with multiple GPUs (g4dn.2xlarge, g4dn.12xlarge, p3.2xlarge):

### Enable Tensor Parallelism

Edit `user_data.sh` and modify the vLLM service definition:

```bash
# In /etc/systemd/system/vllm.service, change:
ExecStart=/usr/local/bin/python3 -m vllm.entrypoints.openai.api_server \
    --model $MODEL_REPO \
    --tensor-parallel-size 2 \    # Use 2 GPUs
    --port $VLLM_PORT \
    --max-model-len $VLLM_MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --download-dir /mnt/models
```

### Tensor Parallel Size Reference
- g4dn.xlarge (1 GPU): `--tensor-parallel-size 1`
- g4dn.2xlarge (2 GPUs): `--tensor-parallel-size 2`
- g4dn.12xlarge (4 GPUs): `--tensor-parallel-size 4`
- p3.2xlarge (8 GPUs): `--tensor-parallel-size 4` or `8`

### Performance Impact
- **Throughput**: ~1.8x improvement with 2 GPUs
- **Latency**: Slightly higher (network overhead)
- **Memory**: Better distribution (2 x 16GB vs 1 x 32GB)

## Multiple Models

To serve multiple models using vLLM's multi-model serving:

### Option 1: Sequential Loading (Simple)

```bash
# Create model list file
cat > /home/ubuntu/models_list.txt <<EOF
mistralai/Mistral-7B-v0.1
NousResearch/Nous-Hermes-2-7b
EOF

# Modify vLLM service for multi-model
ExecStart=/usr/local/bin/python3 -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-v0.1 \
    --enable-lora \
    --port 8000
```

**Note**: vLLM loads one model at a time. Use separate instances for true concurrent serving.

### Option 2: Separate Instances (Recommended for Production)

Deploy multiple instances, each serving a different model:

```bash
# Deploy mlflow-server instance for same models
# Apply infrastructure twice with different model_name
terraform apply -var="model_repo=mistralai/Mistral-7B-v0.1" \
                -var="project_name=llm-mistral"

terraform apply -var="model_repo=meta-llama/Llama-2-7b-hf" \
                -var="project_name=llm-llama"

# Use API gateway to route requests by model name
```

## Auto-Scaling

Add autoscaling for dynamic workloads:

### Create Auto Scaling Group

Add to `ec2.tf`:

```hcl
# Launch Template
resource "aws_launch_template" "llm" {
  name_prefix   = "${var.project_name}-"
  image_id      = var.ami_id
  instance_type = var.instance_type
  
  iam_instance_profile {
    name = aws_iam_instance_profile.llm_instance_profile.name
  }

  user_data = base64encode(local.user_data_script)

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project_name}-instance"
    }
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "llm" {
  name                = "${var.project_name}-asg"
  vpc_zone_identifier = [aws_subnet.public.id]
  target_group_arns   = [aws_lb_target_group.vllm[0].arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = 1
  max_size         = 3
  desired_capacity = 2

  launch_template {
    id      = aws_launch_template.llm.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-asg"
    propagate_at_launch = true
  }
}

# Scaling Policy: Scale Up
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "${var.project_name}-scale-up"
  autoscaling_group_name = aws_autoscaling_group.llm.name
  adjustment_type        = "ChangeInCapacity"
  scaling_adjustment     = 1
  cooldown               = 300
}

# Scaling Policy: Scale Down
resource "aws_autoscaling_policy" "scale_down" {
  name                   = "${var.project_name}-scale-down"
  autoscaling_group_name = aws_autoscaling_group.llm.name
  adjustment_type        = "ChangeInCapacity"
  scaling_adjustment     = -1
  cooldown               = 300
}

# CloudWatch Alarm: Scale Up when CPU high
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 70
  alarm_actions       = [aws_autoscaling_policy.scale_up.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.llm.name
  }
}

# CloudWatch Alarm: Scale Down when CPU low
resource "aws_cloudwatch_metric_alarm" "cpu_low" {
  alarm_name          = "${var.project_name}-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 5
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 20
  alarm_actions       = [aws_autoscaling_policy.scale_down.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.llm.name
  }
}
```

## HTTPS/TLS Setup

### Option 1: Use AWS Certificate Manager

```hcl
# In alb.tf, add:

# Create certificate (requires domain validation)
resource "aws_acm_certificate" "llm" {
  domain_name       = "llm.yourdomain.com"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# Add HTTPS listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main[0].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.llm.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.vllm[0].arn
  }
}

# Redirect HTTP to HTTPS
resource "aws_lb_listener_rule" "redirect_http" {
  listener_arn = aws_lb_listener.http[0].arn

  action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }
}
```

### Option 2: Self-Signed Certificate (Testing Only)

```bash
# SSH into instance
ssh -i ~/.ssh/llm-server-key.pem ubuntu@<instance-ip>

# Generate self-signed cert
sudo openssl req -x509 -newkey rsa:4096 -keyout /etc/ssl/private/vllm.key \
  -out /etc/ssl/certs/vllm.crt -days 365 -nodes

# Update nginx/reverse proxy to use HTTPS
sudo apt install -y nginx
sudo systemctl enable nginx
```

## Advanced Security

### 1. API Key Authentication

Create wrapper script in `user_data.sh`:

```bash
cat > /home/ubuntu/api_gateway.py <<'EOF'
from fastapi import FastAPI, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthCredential
import httpx
import os

app = FastAPI()
security = HTTPBearer()

VALID_KEYS = os.getenv("API_KEYS", "").split(",")
VLLM_URL = "http://localhost:8000"

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request, credentials: HTTPAuthCredential = Security(security)):
    if credentials.credentials not in VALID_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=f"{VLLM_URL}/{path}",
            content=await request.body(),
            headers=request.headers
        )
    return response
EOF

# Install and run with uvicorn
pip install fastapi uvicorn httpx
```

### 2. VPC Security

```hcl
# Add private subnet
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
}

# NAT Gateway for private subnet
resource "aws_nat_gateway" "main" {
  depends_on = [aws_internet_gateway.main]
  subnet_id  = aws_subnet.public.id
}

# Move instances to private subnet, ALB in public
```

### 3. Network ACLs

```hcl
# Restrict network access at NACLs level
resource "aws_network_acl_rule" "ingress_vllm" {
  network_acl_id = aws_network_acl.default.id
  rule_number    = 100
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.allowed_cidr_blocks[0]
  from_port      = var.vllm_port
  to_port        = var.vllm_port
}
```

## Performance Tuning

### vLLM Optimization

Modify `user_data.sh` ExecStart parameters:

```bash
ExecStart=/usr/local/bin/python3 -m vllm.entrypoints.openai.api_server \
    --model $MODEL_REPO \
    --tensor-parallel-size 2 \
    --pipeline-parallel-size 1 \
    --max-num-seqs 256 \                    # Increase batch size
    --gpu-memory-utilization 0.95 \         # Higher utilization
    --max-context-len-to-capture 16384 \    # KV cache optimization
    --disable-log-requests \                # Reduce I/O overhead
    --disable-log-stats
```

### Kernel Tuning

Add to `user_data.sh`:

```bash
# Optimize network settings
sudo sysctl -w net.core.somaxconn=512
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=2048
sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535"

# Persist changes
echo "net.core.somaxconn=512" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog=2048" | sudo tee -a /etc/sysctl.conf
```

## Model Quantization

### Using GPTQ Quantized Models

```bash
# In terraform.tfvars
model_repo = "TheBloke/Mistral-7B-v0.1-GGUF"  # Quantized, 4-5GB instead of 14GB

# Reduce memory utilization
vllm_gpu_memory_utilization = 0.5  # More headroom for larger batch
```

Benefits:
- **Size**: 50-80% reduction (14GB → 4GB)
- **Speed**: 1.2-1.5x faster
- **Quality**: <1% difference in most tasks
- **Cost**: Use g4dn.xlarge for larger models

## Cost Optimization

### 1. Use Reserved Instances

```bash
# Buy 1-year reserved for 25% savings
aws ec2 purchase-reserved-instances-offering \
  --reserved-instances-offering-id "xxxxx" \
  --instance-count 1
```

### 2. Spot Instances (Dev/Test Only)

```hcl
# In launch template, add:
spot_price = "0.15"  # Up to 90% cheaper
instance_interruption_behavior = "terminate"
```

### 3. Minimize Data Transfer

- Keep API clients in same region
- Use VPC endpoint for S3 to avoid NAT charges
- Cache responses client-side

### 4. Monitor Costs

```hcl
# Add budget alert
resource "aws_budgets_budget" "llm" {
  name              = "${var.project_name}-budget"
  budget_type       = "COST"
  limit_unit        = "USD"
  limit_value       = "500"
  time_period_end   = "2099-12-31"
  time_period_start = "2024-01-01"

  cost_filters = {
    Service = "Amazon Elastic Compute Cloud - Compute"
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = ["your-email@example.com"]
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
  }
}
```

## Monitoring Dashboard

### CloudWatch Custom Metrics

Add to `user_data.sh`:

```bash
# Custom script to push metrics
cat > /usr/local/bin/push_metrics.sh <<'METRICS_EOF'
#!/bin/bash
while true; do
  GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | awk '{s+=$1} END {print s/NR}')
  GPU_MEM=$(nvidia-smi --query-gpu=utilization.memory --format=csv,noheader,nounits | awk '{s+=$1} END {print s/NR}')
  
  aws cloudwatch put-metric-data \
    --metric-name GPUUtilization \
    --value $GPU_UTIL \
    --namespace vLLM
  
  aws cloudwatch put-metric-data \
    --metric-name GPUMemoryUtilization \
    --value $GPU_MEM \
    --namespace vLLM
  
  sleep 60
done
METRICS_EOF

sudo chmod +x /usr/local/bin/push_metrics.sh
```

---

For production deployments, test thoroughly in a dev environment first!
