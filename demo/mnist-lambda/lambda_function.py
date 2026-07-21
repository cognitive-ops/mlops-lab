"""
AWS Lambda Handler for MNIST Digit Recognition
Handles inference requests for handwritten digit recognition
"""
import json
import base64
import io
import torch
import numpy as np
from PIL import Image


# Global model variable (loaded once during cold start)
model = None


def load_model():
    """Load the traced PyTorch model"""
    global model
    if model is None:
        print("Loading model...")
        model = torch.jit.load('models/mnist_model_traced.pt')
        model.eval()
        print("Model loaded successfully")
    return model


def preprocess_image(image_data):
    """
    Preprocess image for MNIST model
    
    Args:
        image_data: Base64 encoded image or raw bytes
        
    Returns:
        torch.Tensor: Preprocessed image tensor
    """
    # Decode base64 if necessary
    if isinstance(image_data, str):
        image_bytes = base64.b64decode(image_data)
    else:
        image_bytes = image_data
    
    # Open image
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert to grayscale
    image = image.convert('L')
    
    # Resize to 28x28
    image = image.resize((28, 28), Image.LANCZOS)
    
    # Convert to numpy array
    img_array = np.array(image, dtype=np.float32)
    
    # Normalize (MNIST preprocessing)
    img_array = img_array / 255.0  # Scale to [0, 1]
    img_array = (img_array - 0.1307) / 0.3081  # MNIST normalization
    
    # Convert to tensor and add batch + channel dimensions
    img_tensor = torch.from_numpy(img_array).unsqueeze(0).unsqueeze(0)
    
    return img_tensor


def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Expected event format:
    {
        "image": "base64_encoded_image_string",
        "return_probabilities": false  // optional
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "predicted_digit": 7,
            "confidence": 0.9876,
            "probabilities": [0.01, 0.02, ...] // if requested
        }
    }
    """
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        image_data = body.get('image')
        return_probabilities = body.get('return_probabilities', False)
        
        if not image_data:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing "image" field in request body'
                })
            }
        
        # Load model
        model = load_model()
        
        # Preprocess image
        img_tensor = preprocess_image(image_data)
        
        # Run inference
        with torch.no_grad():
            outputs = model(img_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
        
        # Prepare response
        response_body = {
            'predicted_digit': int(predicted.item()),
            'confidence': float(confidence.item())
        }
        
        if return_probabilities:
            response_body['probabilities'] = probabilities[0].tolist()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }


# For local testing
if __name__ == "__main__":
    # Test with a sample image
    from torchvision import datasets, transforms
    
    # Load a sample MNIST image
    test_dataset = datasets.MNIST(
        root='./data',
        train=False,
        download=True,
        transform=transforms.ToTensor()
    )
    
    # Get first image
    img, label = test_dataset[0]
    
    # Convert to PIL Image and save
    from torchvision.transforms import ToPILImage
    pil_img = ToPILImage()(img)
    
    # Convert to base64
    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Test the handler
    test_event = {
        'image': img_str,
        'return_probabilities': True
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
    print(f"Actual label: {label}")
