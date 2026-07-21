# MNIST Handwriting Detection with AWS Lambda

Complete end-to-end solution for training and deploying a neural network to recognize handwritten digits (0-9) using PyTorch and AWS Lambda.

## 🎯 Project Overview

This project demonstrates:
- Training a convolutional neural network (CNN) for MNIST digit recognition
- Achieving >98% accuracy on test data
- Deploying the model as a serverless API using AWS Lambda
- Infrastructure as Code using AWS CDK
- RESTful API with API Gateway

## 📁 Project Structure

```
mnist-lambda/
├── train_model.py           # Model training script
├── evaluate_model.py        # Model evaluation script
├── lambda_function.py       # AWS Lambda handler
├── deploy_cdk.py            # AWS CDK deployment stack
├── test_api.py              # API testing utilities
├── dvc.yaml                 # DVC pipeline configuration
├── params.yaml              # Training hyperparameters
├── requirements.txt         # Training dependencies
├── lambda_requirements.txt  # Lambda-specific dependencies
├── environment.yml          # Conda environment configuration
├── Makefile                 # Convenient commands
├── README.md                # This file
└── DVC_README.md            # DVC pipeline documentation
```

## 🚀 Quick Start

### Prerequisites

Choose one of the following environment setups:

#### Option 1: Using Conda (Recommended)

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate mnist-lambda

# Verify installation
conda list
```

#### Option 2: Using pip

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Training and Evaluation

#### Option A: Using DVC Pipeline (Recommended)

```bash
# If using conda environment
conda activate mnist-lambda

# Initialize DVC (first time only)
dvc init

# Run the complete pipeline
dvc repro

# Or use Make commands
make install
make repro
make metrics
```

This will:
- Download MNIST dataset
- Train the model with parameters from `params.yaml`
- Evaluate on test set
- Generate metrics and confusion matrix
- Track everything with DVC

**See [DVC_README.md](DVC_README.md) for detailed pipeline documentation.**

#### Option B: Manual Training

```bash
# If using conda environment
conda activate mnist-lambda

# Train with W&B logging (default)
python train_model.py

# Or train without W&B logging
python -c "from train_model import train_model; train_model(use_wandb=False)"
```

This will:
- Download the MNIST dataset
- Train a CNN for 5 epochs
- Save the model to `models/mnist_model.pth`
- Create a traced model for Lambda at `models/mnist_model_traced.pt`
- Achieve ~98-99% accuracy
- Log metrics to W&B dashboard (if enabled)

### Additional Setup Steps

#### Step 1: Setup Weights & Biases (Optional)

```bash
# Login to W&B (get API key from https://wandb.ai/authorize)
wandb login
```

### Step 2: Evaluate Model

```bash
# Evaluate on test set
python evaluate_model.py

# Or use DVC
dvc repro evaluate
```

### Step 3: Test Locally

```bash
# Test the Lambda function locally
python test_api.py
```

### Step 4: Deploy to AWS

```bash
# Install AWS CDK dependencies
pip install aws-cdk-lib constructs

# Prepare Lambda package
mkdir -p lambda_package
cp lambda_function.py lambda_package/
cp lambda_requirements.txt lambda_package/requirements.txt
cp -r models lambda_package/

# Deploy using CDK
cdk bootstrap  # First time only
cdk deploy
```

The deployment will output your API endpoint URL.

### Step 5: Test the Deployed API

```python
import requests
import base64

# Read your image file
with open("digit_image.png", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# Make prediction request
response = requests.post(
    "https://YOUR-API-ID.execute-api.REGION.amazonaws.com/prod/predict",
    json={"image": img_base64, "return_probabilities": True}
)

print(response.json())
# Output: {"predicted_digit": 7, "confidence": 0.9876, "probabilities": [...]}
```

## 🧠 Model Architecture

```
MNISTNet (
  Conv2D(1→32, 3×3) + ReLU + MaxPool(2×2)
  Conv2D(32→64, 3×3) + ReLU + MaxPool(2×2)
  Dropout(0.25)
  Flatten
  Linear(3136→128) + ReLU
  Dropout(0.5)
  Linear(128→10)
)
Total Parameters: ~1.2M
```

## 📊 Performance

- **Training Accuracy**: ~99%
- **Validation Accuracy**: ~98.5%
- **Inference Time (Lambda)**: ~50-100ms (cold start: ~2-3s)
- **Model Size**: ~4.7 MB

## 🔧 API Specification

### Endpoint: POST /predict

**Request:**
```json
{
  "image": "base64_encoded_image_string",
  "return_probabilities": false
}
```

**Response (Success):**
```json
{
  "predicted_digit": 7,
  "confidence": 0.9876,
  "probabilities": [0.001, 0.002, ..., 0.987, ...]
}
```

**Response (Error):**
```json
{
  "error": "Error message description"
}
```

### Endpoint: GET /health

Returns service health status.

## 💰 AWS Costs

Estimated costs (us-east-1):
- Lambda: ~$0.20 per 1M requests
- API Gateway: ~$3.50 per 1M requests
- S3 storage: ~$0.023/GB/month
- **Total**: < $5/month for typical usage

## 🎨 Frontend Integration Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>MNIST Digit Recognition</title>
</head>
<body>
    <h1>Draw a Digit</h1>
    <canvas id="canvas" width="280" height="280"></canvas>
    <button onclick="predict()">Predict</button>
    <div id="result"></div>

    <script>
        const API_URL = 'https://YOUR-API-URL/predict';
        
        async function predict() {
            const canvas = document.getElementById('canvas');
            const base64Image = canvas.toDataURL('image/png').split(',')[1];
            
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    image: base64Image,
                    return_probabilities: true
                })
            });
            
            const result = await response.json();
            document.getElementById('result').innerHTML = 
                `Predicted: ${result.predicted_digit} 
                 (Confidence: ${(result.confidence * 100).toFixed(2)}%)`;
        }
    </script>
</body>
</html>
```

## 🔍 Troubleshooting

### Weights & Biases Issues

**Not logged in:**
```bash
wandb login  # Enter API key from https://wandb.ai/authorize
```

**Run training without W&B:**
```python
from train_model import train_model
train_model(use_wandb=False)
```

**View your experiments:**
- Visit https://wandb.ai/
- Navigate to your project "mnist-digit-recognition"
- Explore training metrics, model artifacts, and run comparisons

### Model not loading in Lambda

- Ensure model file is included in deployment package
- Check Lambda memory allocation (minimum 512 MB recommended)

### Poor accuracy
- Verify image preprocessing matches training
- Ensure grayscale conversion and normalization are correct

### Cold start too slow
- Use provisioned concurrency
- Optimize model size
- Consider using ONNX format

## 📚 Further Improvements

1. **Model Optimization**
   - Quantize model for faster inference
   - Convert to ONNX format
   - Use model pruning

2. **Infrastructure**
   - Add CloudWatch logging and metrics
   - Implement API key authentication
   - Add rate limiting
   - Set up CI/CD pipeline

3. **Features**
   - Batch prediction support
   - Model versioning
   - A/B testing capabilities
   - Confidence threshold tuning

## 📄 License

MIT License - feel free to use for learning and commercial projects.

## 👤 Author

Created by v.anh - Acme ML Studio

## 🙏 Acknowledgments

- MNIST dataset: Yann LeCun et al.
- PyTorch framework
- AWS Lambda & CDK teams
