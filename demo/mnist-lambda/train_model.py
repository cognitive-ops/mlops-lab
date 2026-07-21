"""
MNIST Handwriting Detection - Model Training
Train a neural network to recognize handwritten digits (0-9)
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import os
import wandb
import json
import yaml

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")


# Define the Neural Network
class MNISTNet(nn.Module):
    """Convolutional Neural Network for MNIST digit classification"""
    
    def __init__(self):
        super(MNISTNet, self).__init__()
        
        # Convolutional layers
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout1 = nn.Dropout(0.25)
        
        # Fully connected layers
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.dropout2 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(128, 10)
        
        self.relu = nn.ReLU()
    
    def forward(self, x):
        # Conv block 1
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        
        # Conv block 2
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        x = self.dropout1(x)
        
        # Flatten
        x = x.view(-1, 64 * 7 * 7)
        
        # Fully connected layers
        x = self.relu(self.fc1(x))
        x = self.dropout2(x)
        x = self.fc2(x)
        
        return x


def train_model(num_epochs=5, batch_size=64, learning_rate=0.001, use_wandb=True, project_name="mnist-digit-recognition"):
    """Train the MNIST model with W&B logging"""
    
    # Initialize Weights & Biases
    if use_wandb:
        wandb.init(
            project=project_name,
            config={
                "architecture": "CNN",
                "dataset": "MNIST",
                "epochs": num_epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "optimizer": "Adam",
                "device": str(device),
            }
        )
    
    # Data preprocessing
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))  # MNIST mean and std
    ])
    
    # Load MNIST dataset
    print("Loading MNIST dataset...")
    train_dataset = datasets.MNIST(
        root='./data',
        train=True,
        download=True,
        transform=transform
    )
    
    test_dataset = datasets.MNIST(
        root='./data',
        train=False,
        download=True,
        transform=transform
    )
    
    # Data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=2
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=1000,
        shuffle=False,
        num_workers=2
    )
    
    # Initialize model, loss, and optimizer
    model = MNISTNet().to(device)
    
    # Watch model with wandb
    if use_wandb:
        wandb.watch(model, log="all", log_freq=100)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    print(f"\nModel Architecture:")
    print(model)
    print(f"\nTotal parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Training loop
    print(f"\nStarting training for {num_epochs} epochs...")
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for i, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            
            # Forward pass
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            # Backward pass and optimization
            loss.backward()
            optimizer.step()
            
            # Statistics
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # Print progress and log to wandb
            if (i + 1) % 100 == 0:
                batch_loss = running_loss / (i + 1)
                batch_acc = 100 * correct / total
                
                print(f'Epoch [{epoch+1}/{num_epochs}], '
                      f'Step [{i+1}/{len(train_loader)}], '
                      f'Loss: {batch_loss:.4f}, '
                      f'Accuracy: {batch_acc:.2f}%')
                
                if use_wandb:
                    wandb.log({
                        "train/batch_loss": batch_loss,
                        "train/batch_accuracy": batch_acc,
                        "train/step": epoch * len(train_loader) + i,
                        "epoch": epoch + 1
                    })
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        val_loss = 0.0
        
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_accuracy = 100 * val_correct / val_total
        avg_val_loss = val_loss / len(test_loader)
        
        print(f'\nEpoch [{epoch+1}/{num_epochs}] Validation - Loss: {avg_val_loss:.4f}, Accuracy: {val_accuracy:.2f}%\n')
        
        # Log validation metrics to wandb
        if use_wandb:
            wandb.log({
                "val/loss": avg_val_loss,
                "val/accuracy": val_accuracy,
                "epoch": epoch + 1
            })
    
    # Save the model
    os.makedirs('models', exist_ok=True)
    
    # Save full model
    torch.save(model.state_dict(), 'models/mnist_model.pth')
    print(f"Model saved to models/mnist_model.pth")
    
    # Save model artifact to wandb
    if use_wandb:
        wandb.save('models/mnist_model.pth')
    
    # Save traced model for Lambda (CPU version)
    model.cpu()
    model.eval()
    example_input = torch.randn(1, 1, 28, 28)
    traced_model = torch.jit.trace(model, example_input)
    traced_model.save('models/mnist_model_traced.pt')
    print(f"Traced model saved to models/mnist_model_traced.pt")
    
    # Save traced model artifact to wandb
    if use_wandb:
        wandb.save('models/mnist_model_traced.pt')
        wandb.finish()
    
    # Save training metrics for DVC
    os.makedirs('metrics', exist_ok=True)
    metrics = {
        'final_validation_accuracy': float(val_accuracy),
        'num_epochs': num_epochs,
        'batch_size': batch_size,
        'learning_rate': learning_rate,
        'device': str(device),
        'total_parameters': sum(p.numel() for p in model.parameters())
    }
    
    with open('metrics/training_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\nTraining metrics saved to metrics/training_metrics.json")
    
    return model, val_accuracy


def load_params():
    """Load parameters from params.yaml if it exists"""
    try:
        with open('params.yaml', 'r') as f:
            params = yaml.safe_load(f)
            return params
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    # Load parameters from params.yaml if available
    params = load_params()
    
    if params and 'training' in params:
        train_params = params['training']
        model, accuracy = train_model(
            num_epochs=train_params.get('num_epochs', 5),
            batch_size=train_params.get('batch_size', 64),
            learning_rate=train_params.get('learning_rate', 0.001),
            use_wandb=train_params.get('use_wandb', True),
            project_name=train_params.get('project_name', 'mnist-digit-recognition')
        )
    else:
        model, accuracy = train_model(num_epochs=5)
    print(f"\n✓ Training completed! Final accuracy: {accuracy:.2f}%")
