# Quick Start Guide for LLM Self-Hosting Infrastructure

This guide will get you up and running with a self-hosted LLM on AWS in 15-20 minutes.

## Prerequisites

- AWS Account with appropriate permissions
- Terraform installed (v1.0+)
- AWS CLI configured with credentials
- Bash/terminal access
- ~30 minutes of time

## Step 1: Get the Correct AMI ID for Your Region

The infrastructure uses Ubuntu 22.04 LTS. You need the correct AMI ID for your region.

```bash
# Set your region (change as needed)
REGION="us-east-1"

# Get the latest Ubuntu 22.04 LTS AMI
aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
  --region $REGION \
  --query 'Images | sort_by(@, &CreationDate) | [-1].[ImageId]' \
  --output text
```

This will output something like: `ami-0c55b159cbfafe1f0`

## Step 2: Update Configuration

Edit [terraform.tfvars](terraform.tfvars):

```bash
# 1. Update the AMI ID from Step 1
ami_id = "ami-XXXXXXXX"

# 2. Choose your instance type:
#    - g4dn.xlarge (1x T4, good for 7B models) ✅ Recommended for starting
#    - g4dn.2xlarge (2x T4, good for 13B models)
#    - p3.2xlarge (8x V100, high performance)
instance_type = "g4dn.xlarge"

# 3. Choose your model:
#    - mistralai/Mistral-7B-v0.1 (recommended, free, high quality)
#    - meta-llama/Llama-2-7b-hf (Meta's Llama, requires HF token)
model_repo = "mistralai/Mistral-7B-v0.1"

# 4. (Optional but recommended) Restrict access by changing:
allowed_cidr_blocks = ["YOUR_IP/32"]        # Your IP only
allowed_ssh_cidr_blocks = ["YOUR_IP/32"]    # Your IP only
```

Find your IP:
```bash
curl https://api.ipify.org
```

## Step 3: Initialize Terraform

```bash
cd d:\Work\scopic\ai\backbone-mlops\iac\llm-selfhost
terraform init
```

## Step 4: Review the Plan

```bash
terraform plan -out=tfplan
```

Review the output to understand what will be created:
- 1x EC2 GPU Instance
- 1x Elastic IP
- 1x Application Load Balancer
- 1x S3 Bucket (for models)
- Security groups, VPC, subnets, IAM roles, etc.

## Step 5: Deploy

```bash
terraform apply tfplan
```

This will take 5-10 minutes. Grab a coffee! ☕

## Step 6: Get Connection Information

Once deployment completes, note the following outputs:

```bash
# Get all outputs
terraform output

# Or specific values:
terraform output -raw instance_public_ip
terraform output -raw load_balancer_dns
terraform output -raw api_endpoint
```

## Step 7: Connect to Your Instance

Wait 2-3 minutes for the instance to boot and install/compile everything.

```bash
# SSH into the instance
ssh -i ~/.ssh/llm-server-key.pem ubuntu@<instance_public_ip>

# Check vLLM status
sudo systemctl status vllm

# View setup logs
sudo journalctl -u vllm -f

# View setup script output
cat /var/log/vllm-setup.log
```

## Step 8: Test the API

Once vLLM is running (you'll see "Active (running)" in the status):

```bash
# From your local machine:

# Check available models
curl http://<load_balancer_dns>/v1/models

# Or test completion
curl -X POST http://<load_balancer_dns>/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "prompt": "The meaning of life is",
    "max_tokens": 50,
    "temperature": 0.7
  }' | jq

# Or test chat completion (OpenAI compatible)
curl -X POST http://<load_balancer_dns>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "messages": [
      {"role": "user", "content": "What is Python?"}
    ],
    "temperature": 0.7
  }' | jq
```

## Estimated Costs

| Instance | Monthly Cost |
|----------|-------------|
| g4dn.xlarge (1x T4) | ~$300 |
| g4dn.2xlarge (2x T4) | ~$600 |
| EBS storage (200GB) | ~$20 |
| Load Balancer | ~$16 |
| S3 (baseline) | ~$5 |
| **Total** | ~**$341-641** |

## Troubleshooting

### Instance still initializing
- Wait 3-5 minutes after creation
- Check: `ssh ... sudo journalctl -u vllm -n 50`

### vLLM not responding
- Check instance is running: `aws ec2 describe-instances --instance-ids <instance-id>`
- View logs: `sudo journalctl -u vllm -f`
- Check port: `netstat -tulpn | grep 8000`
- Restart: `sudo systemctl restart vllm`

### Load Balancer shows unhealthy target
- vLLM takes time to download and load the model (2-5 minutes for 7B)
- Check instance logs
- Verify security group allows traffic on port 8000

### Model download fails
- Check internet connectivity on instance
- Verify HuggingFace hub access: `huggingface-cli login` (if using auth-required models)
- Check disk space: `df -h /mnt/models`

### Out of GPU memory
- Reduce `vllm_gpu_memory_utilization` in terraform.tfvars (default 0.9)
- Use a quantized model instead
- Upgrade to a larger instance

## Next Steps

1. **Use the API**: Integrate with your applications
2. **Add Authentication**: Use an API gateway with keys
3. **Enable HTTPS**: Add SSL certificate to load balancer
4. **Scale**: Deploy multiple instances with auto-scaling
5. **Monitor**: Set up CloudWatch dashboards and alarms
6. **Backup**: Enable EBS snapshots for disaster recovery

## Cleanup (Important!)

To avoid ongoing charges, destroy resources when done:

```bash
terraform destroy
```

Type `yes` when prompted.

## Common Use Cases

### Development/Testing
```bash
instance_type = "g4dn.xlarge"
model_repo = "mistralai/Mistral-7B-v0.1"  # Fastest to load
```

### Production Small Models
```bash
instance_type = "g4dn.xlarge"
enable_alb = true
enable_cloudwatch_monitoring = true
```

### Production Large Models
```bash
instance_type = "g4dn.12xlarge"  # Or p3.2xlarge
model_repo = "meta-llama/Llama-2-70b-hf"
vllm_tensor_parallel_size = 4  # Add to user_data.sh
```

## Support & Documentation

- **vLLM Docs**: https://docs.vllm.ai/
- **AWS EC2 GPU**: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using_gpus.html
- **Terraform AWS**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **HuggingFace Models**: https://huggingface.co/models?pipeline_tag=text-generation&sort=trending

## Tips for Success

✅ **Do:**
- Start with g4dn.xlarge for testing
- Use Mistral-7B for fastest setup
- Monitor costs with CloudWatch
- Keep instance security groups restrictive
- Use the load balancer for reliability

❌ **Don't:**
- Leave `allowed_cidr_blocks = ["0.0.0.0/0"]` in production
- Forget to run `terraform destroy` when done
- Use p3 instances unless you need 100+ req/sec
- Ignore CloudWatch logs
- Leave instances running longer than needed

Happy LLM serving! 🚀
