# SAM Deployment Guide for MNIST Lambda

## 📦 Prerequisites

```bash
# Install AWS SAM CLI
# Windows (PowerShell as Administrator)
# Download from: https://github.com/aws/aws-sam-cli/releases/latest/download/AWS_SAM_CLI_64_PY3.msi

# Linux/WSL
pip install aws-sam-cli

# Verify installation
sam --version
```

## 🚀 Deployment Steps

### 1. Build the SAM Application

```bash
cd /mnt/d/work/acme/backbone-mlops/demo/mnist-lambda

# Build the application (packages dependencies)
sam build
```

### 2. Deploy to AWS

#### First Time Deployment (Guided):
```bash
sam deploy --guided
```

You'll be prompted for:
- **Stack Name**: `mnist-lambda-stack` (or your choice)
- **AWS Region**: `us-east-1` (or your preferred region)
- **Confirm changes**: Y
- **Allow SAM CLI IAM role creation**: Y
- **Disable rollback**: N
- **Save arguments to samconfig.toml**: Y

#### Subsequent Deployments:
```bash
sam deploy
```

### 3. Upload Model to S3

After deployment, upload your trained model:

```bash
# Get the bucket name from outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name mnist-lambda-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`ModelBucketName`].OutputValue' \
  --output text)

# Upload model
aws s3 cp models/mnist_model_traced.pt s3://$BUCKET_NAME/models/mnist_model_traced.pt
```

## 🧪 Testing

### Local Testing

```bash
# Start local API
sam local start-api

# In another terminal, test the endpoint
curl -X POST http://localhost:3000/predict \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_encoded_image_here"}'

# Test with Python
python test_api.py
```

### Test Deployed API

```bash
# Get API endpoint
sam list endpoints --stack-name mnist-lambda-stack

# Test with curl
API_URL=$(aws cloudformation describe-stacks \
  --stack-name mnist-lambda-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`PredictEndpoint`].OutputValue' \
  --output text)

curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

## 📊 Monitoring

```bash
# View logs
sam logs -n MNISTInferenceFunction --stack-name mnist-lambda-stack --tail

# View CloudWatch logs
sam logs -n MNISTInferenceFunction --stack-name mnist-lambda-stack --start-time '10min ago'
```

## 🔄 Update Deployment

```bash
# After making changes to code
sam build
sam deploy
```

## 🗑️ Cleanup

```bash
# Delete the stack
sam delete --stack-name mnist-lambda-stack

# Or use CloudFormation
aws cloudformation delete-stack --stack-name mnist-lambda-stack
```

## 📁 Required Files Structure

```
mnist-lambda/
├── template.yaml              # SAM template (this file)
├── lambda_function.py         # Lambda handler
├── lambda_requirements.txt    # Lambda dependencies
├── models/
│   └── mnist_model_traced.pt # Trained model
├── samconfig.toml            # SAM configuration (auto-generated)
└── .aws-sam/                 # Build artifacts (auto-generated)
```

## 🔧 SAM Commands Reference

```bash
# Validate template
sam validate

# Build application
sam build

# Deploy application
sam deploy

# Start local API
sam local start-api

# Invoke function locally
sam local invoke MNISTInferenceFunction -e events/event.json

# View logs
sam logs -n MNISTInferenceFunction --tail

# List endpoints
sam list endpoints

# List stack resources
sam list stack-outputs

# Delete stack
sam delete
```

## ⚙️ Configuration File (samconfig.toml)

After running `sam deploy --guided`, a `samconfig.toml` file is created:

```toml
version = 0.1
[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "mnist-lambda-stack"
s3_bucket = "aws-sam-cli-managed-default-samclisourcebucket-xxx"
s3_prefix = "mnist-lambda-stack"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
parameter_overrides = ""
image_repositories = []
```

## 🎯 Benefits of SAM over CDK

1. **Simpler syntax** - YAML-based, easier to understand
2. **Built-in local testing** - `sam local` commands
3. **Faster deployments** - Optimized for serverless
4. **Better logging** - Integrated CloudWatch access
5. **Native AWS support** - Part of AWS toolkit
6. **Auto-packaging** - Handles dependencies automatically

## 🔗 Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [SAM CLI Reference](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-command-reference.html)
- [SAM Examples](https://github.com/aws/serverless-application-model/tree/master/examples)
