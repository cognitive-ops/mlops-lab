# SGLang Self-Hosting Infrastructure on AWS

Terraform config that deploys a self-hosted LLM inference server on AWS using an EC2 GPU instance and [SGLang](https://github.com/sgl-project/sglang) for inference. Mirrors [iac/llm-selfhost](../llm-selfhost) (vLLM) — swap between the two by pointing traffic at whichever ALB you deploy. For a local Docker-only version, see [demo/sglang](../../demo/sglang).

## Architecture

- **EC2 GPU Instance**: Runs SGLang's OpenAI-compatible server via Docker (official `lmsysorg/sglang` image)
- **Elastic IP**: Static public IP for consistent access
- **Application Load Balancer**: Distributes traffic and provides health checks
- **S3 Bucket**: Stores model artifacts and logs
- **CloudWatch**: Monitoring and logging
- **IAM Roles**: Secure access to AWS resources

## Why SGLang over vLLM

Both serve an OpenAI-compatible API. SGLang's RadixAttention automatically reuses KV cache across requests sharing a prefix (system prompts, few-shot examples, multi-turn chat, agent loops), which wins on those workloads. For pure single-turn throughput the two engines are close — pick based on workload shape, not this module in isolation.

## Prerequisites

1. **Terraform** >= 1.0
2. **AWS CLI** configured with appropriate credentials
3. **AWS Account** with permissions for EC2, S3, ELB, CloudWatch
4. **HuggingFace token** if serving a gated repo (e.g. `meta-llama/*`)

## Setup

### 1. Initialize Terraform

```bash
cd iac/sglang-selfhost
terraform init
```

### 2. Configure variables

Create `terraform.tfvars`:

```hcl
aws_region     = "us-east-1"
project_name   = "sglang-server"
environment    = "dev"
owner          = "your-name"

instance_type  = "g5.xlarge"                          # 1x A10G (24GB) — fits an 8B model
ami_id         = "ami-xxxxxxxx"                        # Ubuntu 22.04 LTS, region-specific

model_name     = "llama-3.1-8b-instruct"
model_repo     = "meta-llama/Llama-3.1-8B-Instruct"
model_size_gb  = 16

allow_public_access = true
allowed_cidr_blocks = ["0.0.0.0/0"]                    # Restrict for production!
```

Pass the HuggingFace token via env var rather than committing it to `.tfvars`:

```bash
export TF_VAR_hf_token="hf_xxxxxxxxxxxx"
```

### 3. Plan and apply

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

First boot installs NVIDIA drivers, Docker, and the NVIDIA Container Toolkit, then reboots; SGLang starts automatically after reboot and downloads the model on first request (or you can preload it — see below). Expect 10-20 minutes before the API responds.

## Accessing the API

```bash
curl http://<load_balancer_dns>/v1/models

curl -X POST http://<load_balancer_dns>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "What is AI?"}],
    "temperature": 0.7
  }'
```

## Operations

```bash
# SSH in
ssh -i ~/.ssh/<project_name>-key.pem ubuntu@<instance_public_ip>

# Service status / logs
sudo systemctl status sglang
sudo journalctl -u sglang -f

# Preload model weights ahead of first request
sudo docker exec sglang-server huggingface-cli download <model_repo>

# Smoke test
/home/ubuntu/test_api.sh
```

## Cost Estimation

| Component | Instance | Cost/Month |
|-----------|----------|-----------|
| EC2 (g5.xlarge) | 1 | ~$700-900 |
| EBS Storage (300GB) | 300 GB | ~$30 |
| Load Balancer | 1 | ~$16 |
| Data Transfer | Variable | ~$0-50 |
| **Total (estimated)** | | **~$750-1000** |

Swap `instance_type` to `g4dn.xlarge` (~$300-400/mo, T4 16GB) for smaller models if A10G headroom isn't needed.

## Scaling Up

Larger models or higher throughput: bump `instance_type` (`g5.2xlarge`, `g5.12xlarge` for multi-GPU, `p4d.24xlarge`), raise `sglang_context_length`, and re-run `terraform apply`. Multi-GPU tensor parallelism requires adding `--tp <n>` to the launch command in [user_data.sh](user_data.sh).

## Cleanup

```bash
terraform destroy
```

⚠️ Terminates the EC2 instance, deletes the load balancer, and removes all associated resources.

## Troubleshooting

- **Instance unreachable after apply**: driver/Docker install + reboot takes several minutes — wait, then check `/var/log/sglang-setup.log` via SSM or SSH.
- **`sglang` service failing**: `sudo journalctl -u sglang -n 100` — most common cause is a gated HF repo without `HF_TOKEN` set, or GPU VRAM too small for `sglang_context_length`.
- **ALB health check failing**: confirm SGLang is listening on `sglang_port` and the security group allows ALB → instance traffic on that port.
