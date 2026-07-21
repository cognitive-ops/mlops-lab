# LLM Self-Hosting Infrastructure - Project Summary

## 📋 Project Overview

Complete AWS infrastructure-as-code (IaC) solution for self-hosting Large Language Models (LLMs) using Terraform. Deploy a production-ready LLM inference server with vLLM on AWS in 15 minutes.

**Created**: 2024  
**Location**: `d:\Work\scopic\ai\backbone-mlops\iac\llm-selfhost\`  
**Infrastructure**: AWS EC2 + ELB + S3 + CloudWatch  
**Framework**: vLLM (OpenAI-compatible API)  
**Supported Models**: Mistral, Llama 2, and other open-source LLMs  

---

## 📁 File Structure

```
llm-selfhost/
├── README.md                    # Main documentation
├── QUICKSTART.md               # 15-minute setup guide
├── ADVANCED.md                 # Advanced configs (multi-GPU, scaling)
├── TROUBLESHOOTING.md          # Common issues & solutions
├── API.md                      # API reference & usage examples
│
├── Terraform Configuration Files:
├── provider.tf                 # AWS provider setup
├── variables.tf               # All input variables
├── terraform.tfvars           # Default/example values
├── network.tf                 # VPC, subnets, security groups
├── iam.tf                     # IAM roles & permissions
├── ec2.tf                     # EC2 instance & storage
├── alb.tf                     # Load balancer setup
├── s3.tf                      # S3 bucket for artifacts
├── monitoring.tf              # CloudWatch alarms & dashboard
├── outputs.tf                 # Output values
│
├── user_data.sh               # EC2 initialization script
├── .gitignore                 # Git ignore patterns
└── .git/                      # (Optional) Git repository
```

---

## ✨ Key Features

### Infrastructure
✅ **Auto-scaling Load Balancer** - Distributes traffic across instances  
✅ **GPU Compute** - g4dn (T4) or p3 (V100) instances  
✅ **Model Storage** - Dedicated 200GB EBS volume  
✅ **S3 Integration** - Backup and model artifact storage  
✅ **CloudWatch Monitoring** - Logs, metrics, alarms, dashboard  

### Networking
✅ **VPC Isolation** - Custom VPC with public/private subnets  
✅ **Security Groups** - Fine-grained access control  
✅ **Elastic IP** - Static public IP address  
✅ **ALB Health Checks** - Automatic health monitoring  

### Software
✅ **vLLM Framework** - GPU-optimized inference server  
✅ **OpenAI Compatible** - Drop-in replacement for GPT APIs  
✅ **Systemd Service** - Auto-restart and recovery  
✅ **NVIDIA Drivers** - Automatic GPU driver setup  

### Operations
✅ **Infrastructure as Code** - Fully reproducible with Terraform  
✅ **One-Click Deploy** - `terraform apply` and done  
✅ **Cost Monitoring** - CloudWatch budgets and alerts  
✅ **Rollback Capability** - State management for easy rollback  

---

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Check you have these
terraform --version                # >= 1.0
aws --version                      # AWS CLI v2
aws sts get-caller-identity        # AWS credentials configured
```

### 2. Get AMI ID for Your Region
```bash
REGION="us-east-1"
aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
  --region $REGION \
  --query 'Images | sort_by(@, &CreationDate) | [-1].[ImageId]' \
  --output text
```

### 3. Update Configuration
```bash
# Edit terraform.tfvars
# - Update ami_id with value from step 2
# - Choose instance_type (g4dn.xlarge recommended)
# - Set security restrictions (allowed_cidr_blocks)
```

### 4. Deploy
```bash
cd d:\Work\scopic\ai\backbone-mlops\iac\llm-selfhost
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 5. Test API
```bash
# Get endpoint from outputs
ENDPOINT=$(terraform output -raw load_balancer_dns)

# List models
curl http://$ENDPOINT/v1/models

# Generate text
curl -X POST http://$ENDPOINT/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "prompt": "Hello, world!",
    "max_tokens": 50
  }'
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      AWS Region                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Application Load Balancer           │   │
│  │  (Health Checks • Horizontal Scaling)           │   │
│  └──────────────┬──────────────────────────────────┘   │
│                 │                                        │
│        ┌────────▼─────────┐                             │
│        │   Target Group   │                             │
│        │   (Port 8000)    │                             │
│        └────────┬─────────┘                             │
│                 │                                        │
│    ┌────────────▼─────────────┐                         │
│    │  EC2 GPU Instance        │                         │
│    │  ┌──────────────────┐    │                         │
│    │  │   vLLM Server    │    │                         │
│    │  │  (Port 8000)     │    │                         │
│    │  │  OpenAI API      │    │                         │
│    │  └──────────────────┘    │                         │
│    │                          │                         │
│    │  GPU: g4dn.xlarge        │                         │
│    │  (NVIDIA T4 16GB)        │                         │
│    │                          │                         │
│    │  Storage:                │                         │
│    │  ├─ /mnt/models (200GB)  │                         │
│    │  └─ Root Volume (100GB)  │                         │
│    └──────────────────────────┘                         │
│                 │                                        │
│    ┌────────────▼──────────┐                            │
│    │  S3 Bucket (Artifacts)│  ┌──────────────────┐   │
│    │                       │  │ CloudWatch       │   │
│    │ • Model downloads     ├─►│ • Logs           │   │
│    │ • Logs storage        │  │ • Metrics        │   │
│    │ • Backups            │  │ • Alarms         │   │
│    │                       │  │ • Dashboard      │   │
│    └───────────────────────┘  └──────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 💰 Cost Estimation

| Component | Instance | Monthly Cost | Annual Cost |
|-----------|----------|--------------|-------------|
| EC2 g4dn.xlarge | On-demand | ~$300 | ~$3,600 |
| EC2 g4dn.xlarge | 1-yr reserved | ~$200 | ~$2,400 |
| EBS storage (200GB) | gp3 | ~$20 | ~$240 |
| Load Balancer | ALB | ~$16 | ~$192 |
| Data transfer | Variable | ~$10 | ~$120 |
| S3 storage | <1GB | ~$5 | ~$60 |
| **Total (On-Demand)** | | **~$351/mo** | **~$4,212/yr** |
| **Total (Reserved)** | | **~$251/mo** | **~$3,012/yr** |

**To reduce costs:**
- Use spot instances (70-90% discount, interruptions possible)
- Stop instance when not in use
- Use g4dn.xlarge for 7B models (vs p3 for large models)
- Use quantized models (4-5GB vs 14GB)

---

## 📚 Documentation Guide

| Document | Best For |
|----------|----------|
| **README.md** | Understanding the project |
| **QUICKSTART.md** | Getting started (first-time users) |
| **API.md** | Integrating with your applications |
| **ADVANCED.md** | Production setup, scaling, optimization |
| **TROUBLESHOOTING.md** | Diagnosing issues, debugging |

---

## 🔧 Terraform Modules Breakdown

### network.tf (250 lines)
- VPC with configurable CIDR
- Internet Gateway
- Public subnet with auto-assign public IPs
- RouteTable with internet access
- Security groups for EC2 and ALB with fine-grained rules

### ec2.tf (150 lines)
- AWS Key Pair management (automatic SSH key generation)
- EC2 instance configuration with GPU support
- EBS volume for model storage
- CloudWatch log group for vLLM output
- User data script execution (fully automated setup)

### iam.tf (100 lines)
- IAM roles and instance profiles
- S3 access policy (read/write models)
- CloudWatch logs permission
- Secrets Manager access (for HF tokens)
- SSM Session Manager for secure access

### alb.tf (100 lines)
- Application Load Balancer
- Target group with health checks
- HTTP listener with forward routing
- CloudWatch alarms for ALB health and response time

### s3.tf (80 lines)
- S3 bucket with auto-generated name
- Versioning for model artifacts
- Server-side encryption
- Lifecycle policies (auto-cleanup old logs)
- Public access blocked by default

### monitoring.tf (60 lines)
- CloudWatch CPU utilization alarm
- Custom metrics for GPU monitoring
- Dashboard for visualization
- Log group for structured logging

---

## 🎯 Typical Workflows

### Development Setup
```bash
terraform apply \
  -var="instance_type=g4dn.xlarge" \
  -var="environment=dev" \
  -var="enable_cloudwatch_monitoring=true"
```

### Production Deployment
```bash
terraform apply \
  -var="instance_type=g4dn.2xlarge" \
  -var="instance_count=2" \
  -var="environment=prod" \
  -var="enable_alb=true" \
  -var="enable_cloudwatch_monitoring=true" \
  -var="allowed_cidr_blocks=[\"10.0.0.0/8\"]"
```

### Cost-Optimized (Dev/Test)
```bash
terraform apply \
  -var="instance_type=g4dn.xlarge" \
  -var="model_repo=TheBloke/Mistral-7B-v0.1-GGUF" \
  -var="enable_alb=false" \
  -var="enable_cloudwatch_monitoring=false"
```

---

## 📋 Variables Reference

**Key variables you must configure:**

| Variable | Default | Notes |
|----------|---------|-------|
| `aws_region` | us-east-1 | Change per region |
| `ami_id` | "" | MUST UPDATE - get from AWS |
| `instance_type` | g4dn.xlarge | GPU required |
| `model_repo` | mistralai/Mistral-7B-v0.1 | HuggingFace model ID |
| `allowed_cidr_blocks` | 0.0.0.0/0 | RESTRICT for production |
| `vllm_gpu_memory_utilization` | 0.9 | Reduce if OOM errors |

---

## 🔐 Security Best Practices

✅ **Implement:**
1. Restrict `allowed_cidr_blocks` to your IP/VPN
2. Enable VPC private subnets for production
3. Use AWS Secrets Manager for API keys
4. Enable encryption (S3, EBS, ALB→HTTPS)
5. Set up IAM roles (not access keys)
6. Enable CloudWatch alarms

❌ **Avoid:**
1. Don't leave `allowed_cidr_blocks = ["0.0.0.0/0"]` in production
2. Don't store credentials in terraform.tfvars
3. Don't commit SSH keys to git
4. Don't use root AWS account
5. Don't skip security group rules

See [ADVANCED.md](ADVANCED.md#advanced-security) for implementation.

---

## 📈 Scaling Options

### Vertical Scaling (Bigger Instances)
```bash
# Upgrade to more GPUs
instance_type = "g4dn.2xlarge"  # 2x T4
instance_type = "p3.2xlarge"    # 8x V100
```

### Horizontal Scaling (More Instances)
See [ADVANCED.md](ADVANCED.md#auto-scaling) for:
- Auto Scaling Groups
- CloudWatch scaling policies
- Load balancer target groups

### Model Scaling (Larger Models)
```bash
# 70B parameter model
model_repo = "meta-llama/Llama-2-70b-hf"
instance_type = "p3.8xlarge"  # 32x V100
vllm_tensor_parallel_size = 4
```

---

## 🚨 Important Notes

### Before Production
- [ ] Test with dev setup first
- [ ] Review security group rules
- [ ] Set up CloudWatch alarms
- [ ] Test failover and recovery
- [ ] Document your infrastructure
- [ ] Set up cost monitoring

### During Operation
- [ ] Monitor GPU utilization regularly
- [ ] Keep vLLM updated (`pip install --upgrade vllm`)
- [ ] Backup model artifacts to S3
- [ ] Review CloudWatch dashboards weekly
- [ ] Check AWS Trusted Advisor for optimizations

### Cost Management
- [ ] Use reserved instances for production (25% savings)
- [ ] Destroy dev/test environments when not in use
- [ ] Use CloudWatch budgets and alarms
- [ ] Monitor S3 costs (data transfer)
- [ ] Consider spot instances for non-critical workloads

---

## 🔄 Terraform Workflow

```bash
# 1. Initialize (first time only)
terraform init

# 2. Validate syntax
terraform validate

# 3. Check what will change
terraform plan -out=tfplan

# 4. Apply changes
terraform apply tfplan

# 5. View outputs
terraform output

# 6. Get specific value
terraform output -raw load_balancer_dns

# 7. When done, destroy
terraform destroy
```

---

## 📞 Support & Resources

| Resource | Link |
|----------|------|
| vLLM Documentation | https://docs.vllm.ai/ |
| AWS EC2 GPU Docs | https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using_gpus.html |
| Terraform AWS | https://registry.terraform.io/providers/hashicorp/aws/latest |
| HuggingFace Models | https://huggingface.co/models?pipeline_tag=text-generation |
| OpenAI API Docs | https://platform.openai.com/docs/api-reference |

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024 | Initial release with vLLM support |

---

## 📄 License

This infrastructure code is provided as-is. Use at your own risk.

---

## 🎓 Learning Resources

### Getting Started with vLLM
```python
# Minimal example
from openai import OpenAI
client = OpenAI(base_url="http://your-endpoint")
response = client.chat.completions.create(
    model="mistral-7b",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### Monitoring Your Deployment
```bash
# SSH into instance
ssh -i ~/.ssh/llm-server-key.pem ubuntu@<ip>

# Watch GPU usage
watch nvidia-smi

# View vLLM logs
sudo journalctl -u vllm -f
```

### Next Steps
1. Deploy with [QUICKSTART.md](QUICKSTART.md)
2. Test APIs with [API.md](API.md)
3. Learn advanced configs in [ADVANCED.md](ADVANCED.md)
4. Troubleshoot with [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Happy LLM serving! 🚀**

For questions or issues, check the troubleshooting guide or refer to vLLM/AWS documentation.
