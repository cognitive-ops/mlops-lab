# LLM Self-Hosting Infrastructure on AWS

This Terraform configuration deploys a self-hosted LLM inference server on AWS using EC2 GPU instances and vLLM for optimized inference.

## Architecture

- **EC2 GPU Instance**: Runs the LLM model using vLLM for high-performance inference
- **Elastic IP**: Static public IP for consistent access
- **Application Load Balancer**: Distributes traffic and provides health checks
- **S3 Bucket**: Stores model artifacts and logs
- **CloudWatch**: Monitoring and logging
- **IAM Roles**: Secure access to AWS resources

## Supported Models

- Llama 2 (7B, 13B, 70B)
- Mistral (7B, 8x7B)
- Other open-source LLMs compatible with vLLM

## Prerequisites

1. **Terraform** >= 1.0
2. **AWS CLI** configured with appropriate credentials
3. **AWS Account** with appropriate permissions for EC2, S3, ELB, CloudWatch
4. **SSH Key Pair** for accessing the instance (generated automatically)

## Setup Instructions

### 1. Initialize Terraform

```bash
cd d:\Work\acme\ai\backbone-mlops\iac\llm-selfhost
terraform init
```

### 2. Review and Update Variables

Edit `terraform.tfvars` or set environment variables:

```hcl
# Core Configuration
aws_region              = "us-east-1"
project_name            = "llm-server"
environment             = "dev"
owner                   = "your-name"

# Instance Configuration
instance_type           = "g4dn.xlarge"        # GPU instance (1x NVIDIA T4)
ami_id                  = "ami-0c55b159cbfafe1f0"  # Ubuntu 22.04 LTS (update per region)

# Model Configuration
model_name              = "mistral-7b"         # or "llama2-7b", "llama2-13b", etc.
model_size_gb           = 14                   # Adjust based on your model

# Networking
vpc_cidr                = "10.0.0.0/16"
subnet_cidr             = "10.0.1.0/24"

# API Configuration
enable_api_gateway      = true
api_health_check_path   = "/v1/models"
allow_public_access     = true
allowed_cidr_blocks     = ["0.0.0.0/0"]       # Restrict for production!
```

### 3. Plan the Infrastructure

```bash
terraform plan -out=tfplan
```

### 4. Apply the Configuration

```bash
terraform apply tfplan
```

## Outputs

After successful deployment, you'll receive:

- **Load Balancer DNS**: Use this to access your LLM API
- **EC2 Instance ID**: For direct SSH access
- **Elastic IP**: Static public IP address
- **S3 Bucket**: For model artifacts and logs
- **SSH Key Location**: Path to private key for SSH access

Example output:
```
load_balancer_dns = "llm-server-alb-123456.us-east-1.elb.amazonaws.com"
instance_public_ip = "54.123.45.67"
s3_bucket_name = "llm-server-artifacts-dev-123456"
```

## Accessing the LLM API

Once deployed, the vLLM server will be available at:

```bash
# Via Load Balancer
curl http://<load_balancer_dns>:8000/v1/models

# Via Direct IP
curl http://<instance_public_ip>:8000/v1/models

# Check health
curl http://<load_balancer_dns>/health
```

## Cost Estimation

| Component | Instance | Cost/Month |
|-----------|----------|-----------|
| EC2 (g4dn.xlarge) | 1 | ~$300-400 |
| EBS Storage (200GB) | 200 GB | ~$20 |
| Load Balancer | 1 | ~$16 |
| Data Transfer | Variable | ~$0-50 |
| **Total (estimated)** | | **~$350-500** |

*Prices vary by region. Use AWS pricing calculator for your region.*

## Model Management

### Download and Upload a Model

```bash
# SSH into the instance
ssh -i ~/.ssh/<key-name>.pem ubuntu@<instance-public-ip>

# Download a model from HuggingFace
cd /opt/models
huggingface-cli download mistralai/Mistral-7B-v0.1

# Or upload pre-downloaded model
aws s3 cp /path/to/model s3://<bucket-name>/models/ --recursive
```

### Starting the vLLM Server

```bash
# SSH into instance
ssh -i ~/.ssh/<key-name>.pem ubuntu@<instance-public-ip>

# The server should start automatically via systemd
# Check status:
sudo systemctl status vllm

# View logs:
sudo journalctl -u vllm -f
```

## Testing the Inference API

```bash
# Test model list
curl -s http://<load_balancer_dns>:8000/v1/models | jq

# Test completion (requires vLLM running)
curl -X POST http://<load_balancer_dns>:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "prompt": "Explain quantum computing in simple terms.",
    "max_tokens": 100,
    "temperature": 0.7
  }'

# Test chat completion
curl -X POST http://<load_balancer_dns>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "messages": [{"role": "user", "content": "What is AI?"}],
    "temperature": 0.7
  }'
```

## Scaling Up

To use a larger instance with more GPUs:

1. Update `instance_type` in `terraform.tfvars`:
   - `g4dn.2xlarge` (2x NVIDIA T4, ~$600/month)
   - `g4dn.12xlarge` (4x NVIDIA T4, ~$2000/month)  
   - `p3.2xlarge` (8x NVIDIA V100, ~$3000/month)

2. Re-run:
   ```bash
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

## Cleanup

To destroy all resources and avoid costs:

```bash
terraform destroy
```

⚠️ **Warning**: This will terminate the EC2 instance, delete the load balancer, and remove all associated resources.

## Troubleshooting

### Instance Not Starting
- Check security group rules allow SSH and vLLM ports
- Verify IAM role has S3 access
- Check CloudWatch logs for startup errors

### vLLM Service Not Running
```bash
ssh -i ~/.ssh/<key-name>.pem ubuntu@<instance-public-ip>
sudo journalctl -u vllm -n 50
```

### Load Balancer Health Check Failing
- Ensure vLLM is running and responding on port 8000
- Check security group allows ALB → instance traffic
- Verify health check path is correct

## Next Steps

1. **Auto-scaling**: Add Auto Scaling Groups for multiple instances
2. **Multiple GPUs**: Use instances with multiple GPUs
3. **Model Updates**: Implement automated model versioning
4. **API Authentication**: Add API keys and authentication
5. **Monitoring**: Set up CloudWatch dashboards and alarms
6. **Backup**: Enable EBS snapshots for model persistence

## Support

For issues or questions, refer to:
- [vLLM Documentation](https://docs.vllm.ai/)
- [AWS EC2 GPU Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using_gpus.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
