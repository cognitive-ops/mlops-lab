# Deployment Checklist & Troubleshooting Guide

## Pre-Deployment Checklist

### AWS Account Setup
- [ ] AWS account created and verified
- [ ] AWS CLI installed: `aws --version`
- [ ] AWS credentials configured: `aws sts get-caller-identity`
- [ ] IAM permissions for EC2, ELB, S3, VPC, IAM, CloudWatch
- [ ] Appropriate AWS region selected: `aws configure get region`

### Terraform Setup
- [ ] Terraform installed (v1.0+): `terraform version`
- [ ] Terraform working directory: `d:\Work\scopic\ai\backbone-mlops\iac\llm-selfhost`
- [ ] Git initialized (optional but recommended): `git init`

### Configuration
- [ ] `terraform.tfvars` updated with:
  - [ ] Correct AMI ID for your region
  - [ ] Instance type decided (g4dn.xlarge recommended)
  - [ ] Model repository selected
  - [ ] Security settings (CIDR blocks, SSH access)
  - [ ] Region set to desired AWS region

### Pre-Deployment Validation
- [ ] Terraform syntax valid: `terraform validate`
- [ ] No resource conflicts: `terraform plan` shows expected resources
- [ ] Cost estimate reviewed (especially for p3 instances)
- [ ] Security groups reviewed
- [ ] SSH key generation won't overwrite existing: `ls ~/.ssh/llm-server-key.pem` (should not exist)

---

## Deployment Steps Checklist

### Step 1: Infrastructure Creation
- [ ] `terraform init` completed successfully
- [ ] `terraform plan -out=tfplan` ran without errors
- [ ] Resource count matches expectations (~15-20 resources)
- [ ] Cost estimate reviewed
- [ ] `terraform apply tfplan` started

### Step 2: Wait for Deployment
Time: 5-10 minutes

- [ ] All Terraform resources created (watch for completion)
- [ ] Outputs displayed (instance IP, load balancer DNS, etc.)
- [ ] Note the following outputs:
  - [ ] Instance Public IP: _______________
  - [ ] Load Balancer DNS: _______________
  - [ ] SSH command: _______________
  - [ ] API endpoint: _______________
  - [ ] S3 bucket name: _______________

### Step 3: Instance Initialization
Time: 3-5 minutes (after instance launch)

- [ ] Instance is running: `aws ec2 describe-instances --instance-ids <id> --query 'Reservations[0].Instances[0].State.Name'`
- [ ] Elastic IP assigned
- [ ] Instance accepting SSH connections (may take 1-2 minutes)

### Step 4: Verify Instance Setup
- [ ] SSH connection successful: `ssh -i ~/.ssh/llm-server-key.pem ubuntu@<ip>`
- [ ] Setup script running: `sudo systemctl status vllm`
- [ ] Check logs: `sudo journalctl -u vllm -n 100`
- [ ] NVIDIA drivers installed: `nvidia-smi` (see GPU info)
- [ ] vLLM installed: `python3 -c "import vllm; print(vllm.__version__)"`

---

## Post-Deployment Verification

### Health Checks
- [ ] Instance status: Running
- [ ] Load balancer target: Healthy (may take 2-3 minutes)
- [ ] vLLM service: Active
- [ ] GPU recognized: `nvidia-smi` shows GPU(s)
- [ ] Model download started: Check `/mnt/models` size growth (`du -sh /mnt/models`)

```bash
# Run these checks on the instance
sudo systemctl status vllm           # Service status
sudo journalctl -u vllm -f          # Live logs
nvidia-smi                          # GPU status
df -h /mnt/models                   # Storage usage
curl http://localhost:8000/v1/models  # API response
```

### API Testing from Local Machine
```bash
# Setup variables
ENDPOINT="http://<load_balancer_dns>"

# Test 1: Check models endpoint
[ ] curl $ENDPOINT/v1/models | jq .

# Test 2: Template completion request
[ ] curl -X POST $ENDPOINT/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "prompt": "What is AI?",
    "max_tokens": 50
  }' | jq .

# Test 3: Chat completion (OpenAI compatible)
[ ] curl -X POST $ENDPOINT/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-7b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7
  }' | jq .
```

---

## Common Issues & Troubleshooting

### Issue 1: "terraform init" fails
**Error**: `Error: Failed to download module`

**Solutions**:
```bash
# Check internet connectivity
ping registry.terraform.io

# Clear Terraform cache
rm -rf .terraform
terraform init

# Check Terraform version
terraform version  # Should be >= 1.0
```

---

### Issue 2: AMI ID not found
**Error**: `InvalidAMIID.NotFound`

**Solution**:
```bash
# Get correct AMI for your region
REGION=$(aws configure get region)
aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
  --region $REGION \
  --query 'Images | sort_by(@, &CreationDate) | [-1].[ImageId]' \
  --output text

# Update terraform.tfvars with the new AMI ID
```

---

### Issue 3: Instance takes too long to initialize
**Expected**: 3-5 minutes for instance to be fully setup

**If longer than 10 minutes**:
```bash
# SSH in and check logs
ssh -i ~/.ssh/llm-server-key.pem ubuntu@<ip>
cat /var/log/vllm-setup.log

# Check if system is rebooting (after NVIDIA driver install)
uptime

# Watch cloud-init progress
cloud-init status --wait
```

---

### Issue 4: Cannot SSH into instance
**Error**: `Connection refused` or `Permission denied`

**Solutions**:
```bash
# Check security group allows SSH
aws ec2 describe-security-groups \
  --group-ids <sg-id> \
  --query 'SecurityGroups[0].IpPermissions'

# Check SSH key permissions
ls -la ~/.ssh/llm-server-key.pem
chmod 600 ~/.ssh/llm-server-key.pem

# Verify instance has elastic IP
aws ec2 describe-addresses --query 'Addresses[*].[PublicIp,InstanceId]'

# Try again with verbose output
ssh -vv -i ~/.ssh/llm-server-key.pem ubuntu@<ip>
```

---

### Issue 5: Load balancer shows "unhealthy" target
**Status**: Target group shows "Unhealthy"

**Causes & Solutions**:

**Cause A**: vLLM still downloading model
- **Solution**: Wait 2-5 minutes for model download to complete
- **Check**: `ssh ... du -sh /mnt/models` - size should increase

**Cause B**: Health check path incorrect
- **Fix**: Update `health_check_path` in terraform.tfvars
- Current: `/v1/models` (correct for vLLM)

**Cause C**: Security group doesn't allow ALB → instance traffic
- **Check**: Instance security group has rule for port 8000 from ALB SG
- **Fix**:
  ```bash
  aws ec2 authorize-security-group-ingress \
    --group-id <instance-sg-id> \
    --protocol tcp \
    --port 8000 \
    --source-group <alb-sg-id>
  ```

**Cause D**: vLLM not running
- **Check**: `sudo systemctl status vllm`
- **Fix**: `sudo systemctl restart vllm`
- **Debug**: `sudo journalctl -u vllm -n 50`

---

### Issue 6: vLLM service fails to start
**Error**: `sudo systemctl status vllm` shows "failed"

**Solutions**:
```bash
# View error details
sudo journalctl -u vllm -n 50

# Common causes and fixes:

# 1. NVIDIA drivers not loaded
nvidia-smi  # Should show GPU info
# Fix: systemctl reboot (drivers load on boot)

# 2. vLLM not installed
python3 -m pip list | grep vllm
# Fix: python3 -m pip install vllm==0.3.3

# 3. Out of GPU memory
nvidia-smi  # Check memory usage
# Fix: Reduce vllm_gpu_memory_utilization to 0.7

# 4. Port 8000 already in use
lsof -i :8000
# Fix: Change VLLM_PORT in /home/ubuntu/.vllm_env
```

---

### Issue 7: API returns 504 Gateway Timeout
**Error**: `<html><body>504 Gateway Time-out</body></html>`

**Causes**:

1. **Model inference taking too long**
   - Reduce `max_tokens` in request
   - Increase ALB timeout:
     ```hcl
     # Add to alb.tf (requires reapply)
     deregistration_delay = 120
     ```

2. **vLLM not responding**
   - Check vLLM is running
   - Check it's listening on port 8000: `lsof -i :8000`

3. **ALB can't reach instance**
   - Check instance security group
   - Check instance is in correct subnet

---

### Issue 8: "Out of memory" errors
**Error**: `CUDA out of memory` / `RuntimeError: CUDA out of memory`

**Solutions** (in order):

1. **Reduce GPU utilization**
   ```hcl
   # In terraform.tfvars
   vllm_gpu_memory_utilization = 0.7  # From 0.9
   # Reapply: terraform apply
   ```

2. **Reduce max sequence length**
   ```hcl
   vllm_max_model_len = 2048  # From 4096
   ```

3. **Use quantized model**
   ```hcl
   model_repo = "TheBloke/Mistral-7B-v0.1-GGUF"  # 4GB vs 14GB
   ```

4. **Upgrade instance**
   ```hcl
   instance_type = "g4dn.2xlarge"  # 2x GPU
   ```

---

### Issue 9: EC2 instance launched in wrong AZ
**Problem**: Instance in different AZ than Load Balancer

**Fix**:
```bash
# Update terraform.tfvars to specify AZ
aws_az = "us-east-1a"  # Match your setup

# Or destroy and reapply
terraform destroy -auto-approve
terraform apply
```

---

### Issue 10: Model download stuck/very slow
**Problem**: Model download taking >15 minutes

**Solutions**:
```bash
# Check internet connectivity
curl https://huggingface.co/mistralai/Mistral-7B-v0.1

# Check disk space
df -h /mnt/models

# Check process
ps aux | grep huggingface

# Use CDN-enabled region
# Or manually download and upload:
# 1. Download locally: huggingface-cli download mistralai/Mistral-7B-v0.1
# 2. Upload to S3: aws s3 cp . s3://bucket/models/ --recursive
# 3. Download on instance: aws s3 cp s3://bucket/models/ /mnt/models/ --recursive
```

---

### Issue 11: High AWS costs
**Problem**: Unexpected AWS charges

**Investigation**:
```bash
# Check running instances
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"

# Check if resources still exist
terraform show

# Common issues:
# - Instance still running (stop with: terraform destroy)
# - Multiple instances from repeated applies
# - s3 bucket with large data transfer
```

**Fix**:
```bash
# Stop charges immediately
terraform destroy

# Review and destroy any orphaned resources
aws ec2 describe-instances --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name}'
```

---

### Issue 12: Need to change instance type
**Problem**: Current instance too slow/expensive

**Steps**:

1. Stop instance:
   ```bash
   aws ec2 stop-instances --instance-ids <instance-id>
   ```

2. Update terraform.tfvars:
   ```hcl
   instance_type = "g4dn.2xlarge"  # Upgrade
   ```

3. Reapply (in-place update):
   ```bash
   terraform plan
   terraform apply
   ```

4. Restart:
   ```bash
   aws ec2 start-instances --instance-ids <instance-id>
   ```

**Note**: Some instance type changes require instance replacement (full recreation).

---

## Recovery Procedures

### Backup Current State
```bash
# Save Terraform state
cp terraform.tfstate terraform.tfstate.backup
git add terraform.tfstate.backup

# Save instance data
ssh ... ubuntu@<ip>
tar -czf /tmp/models.tar.gz /mnt/models
```

### Restore from Backup
```bash
# Restore Terraform state
cp terraform.tfstate.backup terraform.tfstate
terraform refresh

# Recreate infrastructure
terraform apply
```

### Emergency Cleanup
```bash
# Force destroy all resources
terraform destroy -auto-approve -force

# Or manually:
aws ec2 terminate-instances --instance-ids <instance-id>
aws ec2 release-address --allocation-id <alloc-id>
aws elb delete-load-balancer --load-balancer-name <name>
aws s3 rb s3://<bucket-name> --force
```

---

## Performance Optimization

### Monitor GPU Utilization
```bash
# SSH into instance
watch -n 1 nvidia-smi

# Check vLLM throughput
curl http://localhost:8000/metrics  # Prometheus metrics
```

### Identify Bottlenecks
```bash
# CPU bottleneck?
top -n 1

# Memory bottleneck?
free -h

# Disk I/O bottleneck?
iostat -x 1

# Network bottleneck?
iftop
nethogs
```

### Tune for Throughput vs Latency
```bash
# For throughput (batch processing):
# Increase max_num_seqs in user_data.sh
--max-num-seqs 256

# For latency (real-time):
# Decrease max_num_seqs
--max-num-seqs 32
```

---

## Support Links

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **vLLM Documentation**: https://docs.vllm.ai/
- **HuggingFace Models**: https://huggingface.co/models
- **AWS Support**: https://console.aws.amazon.com/support/

---

## Quick Command Reference

```bash
# Terraform operations
terraform validate              # Validate syntax
terraform plan                  # Preview changes
terraform apply                 # Deploy changes
terraform destroy               # Remove all resources
terraform output                # View outputs
terraform refresh               # Sync state

# AWS CLI operations
aws ec2 describe-instances      # List instances
aws ec2 start-instances         # Start instance
aws ec2 stop-instances          # Stop instance
aws ec2 terminate-instances     # Kill instance
aws ec2 describe-security-groups # List security groups
aws elb describe-load-balancers  # List load balancers

# Instance operations
ssh -i KEY ubuntu@IP            # SSH into instance
scp -i KEY FILE ubuntu@IP:/tmp  # Copy file to instance
sudo systemctl status vllm      # Check service status
sudo journalctl -u vllm -f      # View live logs
nvidia-smi                      # GPU status
curl http://localhost:8000/v1/models  # Test API

# Cleanup
terraform destroy -auto-approve # Destroy without prompt
```

---

Last Updated: 2024
For latest updates, check the README.md and QUICKSTART.md files.
