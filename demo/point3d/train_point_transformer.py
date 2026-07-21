"""
Point Transformer Training Example

This script demonstrates how to train a Point Transformer on 3D point cloud data.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import numpy as np
from point_transformer import PointTransformerCls


class SimplePointCloudDataset(Dataset):
    """
    Simple synthetic point cloud dataset for demonstration.
    Generates random point clouds with different shapes.
    """
    
    def __init__(self, num_samples=1000, num_points=1024, num_classes=10):
        self.num_samples = num_samples
        self.num_points = num_points
        self.num_classes = num_classes
        
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        # Generate random shape based on class
        label = idx % self.num_classes
        
        if label == 0:  # Sphere
            points = self._generate_sphere(self.num_points)
        elif label == 1:  # Cube
            points = self._generate_cube(self.num_points)
        elif label == 2:  # Cylinder
            points = self._generate_cylinder(self.num_points)
        else:  # Random
            points = np.random.randn(self.num_points, 3)
        
        # Normalize
        points = points - np.mean(points, axis=0)
        points = points / np.max(np.abs(points))
        
        return torch.FloatTensor(points), label
    
    @staticmethod
    def _generate_sphere(n):
        """Generate points on a sphere."""
        phi = np.random.uniform(0, 2*np.pi, n)
        theta = np.random.uniform(0, np.pi, n)
        r = np.random.uniform(0.8, 1.0, n)
        
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        
        return np.stack([x, y, z], axis=1)
    
    @staticmethod
    def _generate_cube(n):
        """Generate points in a cube."""
        return np.random.uniform(-1, 1, (n, 3))
    
    @staticmethod
    def _generate_cylinder(n):
        """Generate points in a cylinder."""
        theta = np.random.uniform(0, 2*np.pi, n)
        r = np.random.uniform(0, 1, n)
        z = np.random.uniform(-1, 1, n)
        
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        
        return np.stack([x, y, z], axis=1)


def train_one_epoch(model, dataloader, optimizer, criterion, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0
    
    for batch_idx, (points, labels) in enumerate(dataloader):
        points = points.to(device)  # (B, N, 3)
        labels = labels.to(device)
        
        # Forward pass
        optimizer.zero_grad()
        logits = model(points)
        loss = criterion(logits, labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        # Statistics
        total_loss += loss.item()
        _, predicted = torch.max(logits, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
        
        if (batch_idx + 1) % 10 == 0:
            print(f"  Batch [{batch_idx+1}/{len(dataloader)}], "
                  f"Loss: {loss.item():.4f}, "
                  f"Acc: {100.0*correct/total:.2f}%")
    
    avg_loss = total_loss / len(dataloader)
    accuracy = 100.0 * correct / total
    
    return avg_loss, accuracy


def validate(model, dataloader, criterion, device):
    """Validate the model."""
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for points, labels in dataloader:
            points = points.to(device)
            labels = labels.to(device)
            
            logits = model(points)
            loss = criterion(logits, labels)
            
            total_loss += loss.item()
            _, predicted = torch.max(logits, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    avg_loss = total_loss / len(dataloader)
    accuracy = 100.0 * correct / total
    
    return avg_loss, accuracy


def main():
    """Main training function."""
    
    print("=" * 70)
    print("Point Transformer Training Demo")
    print("=" * 70)
    
    # Hyperparameters
    num_classes = 10
    num_points = 1024
    batch_size = 8
    num_epochs = 20
    learning_rate = 0.001
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nUsing device: {device}")
    
    # Create datasets
    print("\nCreating datasets...")
    train_dataset = SimplePointCloudDataset(num_samples=800, 
                                           num_points=num_points,
                                           num_classes=num_classes)
    val_dataset = SimplePointCloudDataset(num_samples=200,
                                         num_points=num_points,
                                         num_classes=num_classes)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, 
                             shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size,
                           shuffle=False, num_workers=0)
    
    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")
    
    # Create model
    print("\nInitializing model...")
    model = PointTransformerCls(num_classes=num_classes, 
                                num_points=num_points,
                                in_channels=3)
    model = model.to(device)
    
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model parameters: {num_params:,}")
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    
    # Training loop
    print("\n" + "=" * 70)
    print("Starting Training")
    print("=" * 70)
    
    best_val_acc = 0.0
    
    for epoch in range(num_epochs):
        print(f"\nEpoch [{epoch+1}/{num_epochs}]")
        print("-" * 70)
        
        # Train
        train_loss, train_acc = train_one_epoch(model, train_loader, 
                                                optimizer, criterion, device)
        
        # Validate
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        
        # Update learning rate
        scheduler.step()
        
        # Print epoch results
        print(f"\nEpoch Summary:")
        print(f"  Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"  Val Loss:   {val_loss:.4f}, Val Acc:   {val_acc:.2f}%")
        print(f"  LR: {optimizer.param_groups[0]['lr']:.6f}")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), 'best_point_transformer.pth')
            print(f"  ✓ Best model saved! (Val Acc: {val_acc:.2f}%)")
    
    print("\n" + "=" * 70)
    print("Training Complete!")
    print(f"Best Validation Accuracy: {best_val_acc:.2f}%")
    print("=" * 70)


def test_inference():
    """Test inference on a single point cloud."""
    
    print("\n" + "=" * 70)
    print("Testing Inference")
    print("=" * 70)
    
    # Load model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = PointTransformerCls(num_classes=10, num_points=1024, in_channels=3)
    model.load_state_dict(torch.load('best_point_transformer.pth'))
    model = model.to(device)
    model.eval()
    
    # Generate test point cloud
    dataset = SimplePointCloudDataset(num_samples=1, num_points=1024, num_classes=10)
    points, label = dataset[0]
    points = points.unsqueeze(0).to(device)  # Add batch dimension
    
    # Inference
    with torch.no_grad():
        logits = model(points)
        probabilities = torch.softmax(logits, dim=1)
        predicted = torch.argmax(logits, dim=1)
    
    print(f"\nTrue Label: {label}")
    print(f"Predicted: {predicted.item()}")
    print(f"Confidence: {probabilities[0, predicted].item():.2%}")
    print(f"\nAll class probabilities:")
    for i, prob in enumerate(probabilities[0]):
        print(f"  Class {i}: {prob.item():.2%}")


if __name__ == "__main__":
    # Train the model
    main()
    
    # Test inference
    try:
        test_inference()
    except FileNotFoundError:
        print("\nSkipping inference test (no saved model found)")
