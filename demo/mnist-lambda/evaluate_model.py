"""
MNIST Model Evaluation
Evaluate the trained model on test dataset and generate metrics
"""
import torch
import torch.nn as nn
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import json
import yaml
import os
import numpy as np
from train_model import MNISTNet

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def evaluate_model(model_path='models/mnist_model.pth', params_file='params.yaml'):
    """
    Evaluate the trained MNIST model
    
    Args:
        model_path: Path to the trained model
        params_file: Path to parameters file
        
    Returns:
        Dictionary with evaluation metrics
    """
    # Load parameters
    try:
        with open(params_file, 'r') as f:
            params = yaml.safe_load(f)
        eval_params = params.get('evaluation', {})
        data_params = params.get('data', {})
    except FileNotFoundError:
        eval_params = {'test_batch_size': 1000, 'save_predictions': False}
        data_params = {'data_dir': './data', 'normalize_mean': 0.1307, 'normalize_std': 0.3081}
    
    # Data preprocessing
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            (data_params.get('normalize_mean', 0.1307),), 
            (data_params.get('normalize_std', 0.3081),)
        )
    ])
    
    # Load test dataset
    print("Loading MNIST test dataset...")
    test_dataset = datasets.MNIST(
        root=data_params.get('data_dir', './data'),
        train=False,
        download=False,
        transform=transform
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=eval_params.get('test_batch_size', 1000),
        shuffle=False,
        num_workers=2
    )
    
    # Load model
    print(f"Loading model from {model_path}...")
    model = MNISTNet().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # Evaluation
    print("Evaluating model...")
    correct = 0
    total = 0
    all_predictions = []
    all_labels = []
    all_confidences = []
    
    # Confusion matrix data
    confusion_matrix = np.zeros((10, 10), dtype=int)
    
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item()
            
            # Get predictions
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # Store for detailed metrics
            all_predictions.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_confidences.extend(confidence.cpu().numpy())
            
            # Update confusion matrix
            for t, p in zip(labels.cpu().numpy(), predicted.cpu().numpy()):
                confusion_matrix[t][p] += 1
    
    # Calculate metrics
    accuracy = 100 * correct / total
    avg_loss = total_loss / len(test_loader)
    avg_confidence = float(np.mean(all_confidences))
    
    # Per-class accuracy
    per_class_accuracy = {}
    for i in range(10):
        class_correct = confusion_matrix[i][i]
        class_total = confusion_matrix[i].sum()
        per_class_accuracy[f'class_{i}_accuracy'] = float(class_correct / class_total if class_total > 0 else 0)
    
    # Compile metrics
    metrics = {
        'test_accuracy': float(accuracy),
        'test_loss': float(avg_loss),
        'average_confidence': avg_confidence,
        'total_samples': int(total),
        'correct_predictions': int(correct),
        **per_class_accuracy
    }
    
    # Save metrics
    os.makedirs('metrics', exist_ok=True)
    
    with open('metrics/evaluation_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\nEvaluation Results:")
    print(f"Test Accuracy: {accuracy:.2f}%")
    print(f"Test Loss: {avg_loss:.4f}")
    print(f"Average Confidence: {avg_confidence:.4f}")
    print(f"\nMetrics saved to metrics/evaluation_metrics.json")
    
    # Save confusion matrix for DVC plots
    with open('metrics/confusion_matrix.csv', 'w') as f:
        f.write('actual,predicted,count\n')
        for i in range(10):
            for j in range(10):
                if confusion_matrix[i][j] > 0:
                    f.write(f'{i},{j},{confusion_matrix[i][j]}\n')
    
    print(f"Confusion matrix saved to metrics/confusion_matrix.csv")
    
    # Optionally save predictions
    if eval_params.get('save_predictions', False):
        predictions_data = {
            'predictions': [int(p) for p in all_predictions],
            'labels': [int(l) for l in all_labels],
            'confidences': [float(c) for c in all_confidences]
        }
        
        with open('metrics/predictions.json', 'w') as f:
            json.dump(predictions_data, f, indent=2)
        
        print(f"Predictions saved to metrics/predictions.json")
    
    return metrics


if __name__ == "__main__":
    evaluate_model()
