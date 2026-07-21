"""
Test script for MNIST Lambda API
"""
import requests
import base64
import json
from torchvision import datasets, transforms
from torchvision.transforms import ToPILImage
import io


def test_local_lambda():
    """Test the Lambda function locally"""
    print("Testing Lambda function locally...")
    
    from lambda_function import lambda_handler
    from PIL import Image
    
    # Load test image from file
    try:
        pil_img = Image.open('test_digit_7.png').convert('L')  # Convert to grayscale
        print(f"Loaded test image: test_digit_7.png")
        actual_label = 7  # We know it's a 7
    except FileNotFoundError:
        print("Error: test_digit_7.png not found. Creating a sample image...")
        # Fallback to dataset if file doesn't exist
        from torchvision import datasets, transforms
        from torchvision.transforms import ToPILImage
        
        test_dataset = datasets.MNIST(
            root='./data',
            train=False,
            download=True,
            transform=transforms.ToTensor()
        )
        
        img, actual_label = test_dataset[1]
        pil_img = ToPILImage()(img)
    
    # Convert to base64
    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Test event
    event = {
        'image': img_str,
        'return_probabilities': True
    }
    
    result = lambda_handler(event, None)
    response_body = json.loads(result['body'])
    
    print(f"Predicted digit: {response_body['predicted_digit']}")
    print(f"Confidence: {response_body['confidence']:.4f}")
    print(f"Actual label: {actual_label}")
    print(f"Correct: {response_body['predicted_digit'] == actual_label}")


def test_api_endpoint(api_url, num_samples=1):
    """
    Test deployed API endpoint
    
    Args:
        api_url: API Gateway URL (e.g., https://xxx.execute-api.us-east-1.amazonaws.com/prod/predict)
        num_samples: Number of test samples to run (default 1 for single image test)
    """
    print(f"\nTesting API endpoint: {api_url}")
    
    from PIL import Image
    
    # Load test image from file
    try:
        pil_img = Image.open('test_digit_7.png').convert('L')
        print("Loaded test image: test_digit_7.png")
        actual_label = 7
        
        # Convert to base64
        buffered = io.BytesIO()
        pil_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Make API request
        payload = {
            'image': img_str,
            'return_probabilities': True
        }
        
        response = requests.post(
            api_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            predicted = result['predicted_digit']
            confidence = result['confidence']
            
            is_correct = predicted == actual_label
            
            print(f"Predicted: {predicted}, Actual: {actual_label}, "
                  f"Confidence: {confidence:.4f}, Correct: {is_correct}")
        else:
            print(f"API Error - {response.status_code}: {response.text}")
            
    except FileNotFoundError:
        print("Error: test_digit_7.png not found. Falling back to dataset...")
        # Fallback to dataset
        test_dataset = datasets.MNIST(
            root='./data',
            train=False,
            download=True,
            transform=transforms.ToTensor()
        )
        
        correct = 0
        total = num_samples
        
        for i in range(num_samples):
            img, label = test_dataset[i]
            pil_img = ToPILImage()(img)
            
            # Convert to base64
            buffered = io.BytesIO()
            pil_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Make API request
            payload = {
                'image': img_str,
                'return_probabilities': False
            }
            
            response = requests.post(
                api_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                predicted = result['predicted_digit']
                confidence = result['confidence']
                
                is_correct = predicted == label
                correct += is_correct
                
                print(f"Sample {i+1}: Predicted={predicted}, Actual={label}, "
                      f"Confidence={confidence:.4f}, Correct={is_correct}")
            else:
                print(f"Sample {i+1}: API Error - {response.status_code}")
        
        accuracy = (correct / total) * 100
        print(f"\nAccuracy: {accuracy:.2f}% ({correct}/{total})")


if __name__ == "__main__":
    # Test locally first
    test_local_lambda()
    
    # Uncomment to test deployed API
    # Replace with your actual API endpoint
    # api_url = "https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/predict"
    # test_api_endpoint(api_url, num_samples=10)
