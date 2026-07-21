# MLflow Control Lambda - How to Use

This Lambda function allows you to start and stop MLflow EC2 and RDS instances via REST API.

## Deployment

### 1. Navigate to the directory:
```bash
cd iac/mlflow-server/mlflow-control
```

### 2. Initialize Terraform:
```bash
terraform init
```

### 3. Deploy with variables:

**Option A: Using command-line flags**
```bash
terraform apply \
  -var="ec2_instance_id=i-0f5ea2f0e601a7f77" \
  -var="rds_instance_id=mlflow-db" \
  -var="api_key=your-super-secret-key"
```

**Option B: Using terraform.tfvars file**

Create `terraform.tfvars`:
```hcl
ec2_instance_id = "i-0f5ea2f0e601a7f77"
rds_instance_id = "mlflow-db"
api_key         = "your-super-secret-key"
```

Then run:
```bash
terraform apply
```

### 4. Get the Lambda Function URL:
```bash
terraform output lambda_function_url
```

Example output:
```
https://abc123xyz.lambda-url.us-east-1.on.aws/
```

---

## Using the Endpoint

### Authentication

All requests require a Bearer token in the `Authorization` header:
```
Authorization: Bearer your-super-secret-key
```

### Request Format

**Method:** `POST`
**Content-Type:** `application/json`

**Body:**
```json
{
  "action": "start|stop",
  "resources": ["ec2", "rds"]
}
```

### Parameters

- **action** (required): `"start"` or `"stop"`
- **resources** (required): Array of resources to control
  - `["ec2"]` - Control EC2 only
  - `["rds"]` - Control RDS only
  - `["ec2", "rds"]` - Control both

---

## Examples

### Check Status (GET):
```bash
curl -X GET https://rlby2nulxkyxzxklcd2bbjtswy0bcgxw.lambda-url.us-east-1.on.aws/ \
  -H "Authorization: Bearer your-super-secret-key"
```

**Response:**
```json
{
  "message": "Status retrieved successfully",
  "status": {
    "ec2": {
      "instance_id": "i-0f5ea2f0e601a7f77",
      "status": "running"
    },
    "rds": {
      "instance_id": "mlflow-db",
      "status": "available"
    }
  }
}
```

**Possible EC2 Status Values:**
- `pending` - Instance is starting
- `running` - Instance is running
- `stopping` - Instance is stopping
- `stopped` - Instance is stopped
- `shutting-down` - Instance is terminating
- `terminated` - Instance is terminated

**Possible RDS Status Values:**
- `available` - Database is running
- `starting` - Database is starting
- `stopping` - Database is stopping
- `stopped` - Database is stopped
- `backing-up` - Database is being backed up

---

### Stop Both EC2 and RDS:
```bash
curl -X POST https://rlby2nulxkyxzxklcd2bbjtswy0bcgxw.lambda-url.us-east-1.on.aws/ \
  -H "Authorization: Bearer your-super-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"action": "stop", "resources": ["ec2", "rds"]}'
```

**Response:**
```json
{
  "message": "Command executed successfully",
  "results": {
    "ec2": "Stopping EC2 instance i-0f5ea2f0e601a7f77",
    "rds": "Stopping RDS instance mlflow-db"
  }
}
```

---

### Start Both EC2 and RDS:
```bash
curl -X POST https://rlby2nulxkyxzxklcd2bbjtswy0bcgxw.lambda-url.us-east-1.on.aws/ \
  -H "Authorization: Bearer your-super-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"action": "start", "resources": ["ec2", "rds"]}'
```

---

### Stop EC2 Only:
```bash
curl -X POST https://rlby2nulxkyxzxklcd2bbjtswy0bcgxw.lambda-url.us-east-1.on.aws/ \
  -H "Authorization: Bearer your-super-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"action": "stop", "resources": ["ec2"]}'
```

---

### Start RDS Only:
```bash
curl -X POST https://rlby2nulxkyxzxklcd2bbjtswy0bcgxw.lambda-url.us-east-1.on.aws/ \
  -H "Authorization: Bearer your-super-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"action": "start", "resources": ["rds"]}'
```

---

## Troubleshooting

### Check Lambda Logs:
```bash
aws logs tail /aws/lambda/mlflow-control --follow
```

### Check Instance Status:
```bash
# EC2 status
aws ec2 describe-instances --instance-ids i-0f5ea2f0e601a7f77

# RDS status
aws rds describe-db-instances --db-instance-identifier mlflow-db
```

### Update API Key:
```bash
terraform apply -var="api_key=new-secret-key"
```

---

## Security Best Practices

1. **Keep API key secret** - Don't commit it to Git
2. **Rotate API key regularly**
3. **Use environment variables** in scripts:
   ```bash
   export MLFLOW_CONTROL_API_KEY="your-secret-key"
   curl -H "Authorization: Bearer $MLFLOW_CONTROL_API_KEY" ...
   ```
4. **Consider AWS IAM authentication** for production use
