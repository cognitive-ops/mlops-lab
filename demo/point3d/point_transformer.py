"""
Point Transformer Implementation in PyTorch

This implements the Point Transformer architecture for point cloud processing.
Based on the paper: "Point Transformer" by Zhao et al. (2021)

The Point Transformer uses self-attention mechanisms to capture local and global
geometric features from point clouds.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class PointTransformerLayer(nn.Module):
    """
    Single Point Transformer layer with self-attention.
    
    This layer computes attention weights between points and aggregates features
    based on geometric relationships.
    """
    
    def __init__(self, in_channels, out_channels, k=16):
        """
        Args:
            in_channels: number of input feature channels
            out_channels: number of output feature channels
            k: number of nearest neighbors for local attention
        """
        super(PointTransformerLayer, self).__init__()
        self.k = k
        self.in_channels = in_channels
        self.out_channels = out_channels
        
        # Linear transformations for Query, Key, Value
        self.fc_q = nn.Linear(in_channels, out_channels)
        self.fc_k = nn.Linear(in_channels, out_channels)
        self.fc_v = nn.Linear(in_channels, out_channels)
        
        # Position encoding
        self.fc_delta = nn.Sequential(
            nn.Linear(3, out_channels),
            nn.ReLU(),
            nn.Linear(out_channels, out_channels)
        )
        
        # Attention weight generation
        self.fc_gamma = nn.Sequential(
            nn.Linear(out_channels, out_channels),
            nn.ReLU(),
            nn.Linear(out_channels, out_channels)
        )
        
        # Output projection
        self.fc_out = nn.Linear(out_channels, out_channels)
        
    def forward(self, xyz, features):
        """
        Args:
            xyz: point coordinates (B, N, 3)
            features: point features (B, N, C)
            
        Returns:
            transformed features (B, N, C_out)
        """
        B, N, C = features.shape
        
        # Get k-nearest neighbors
        knn_idx = self.knn(xyz, self.k)  # (B, N, k)
        
        # Gather neighbor features and positions
        neighbor_xyz = self.gather_neighbors(xyz, knn_idx)  # (B, N, k, 3)
        neighbor_features = self.gather_neighbors(features, knn_idx)  # (B, N, k, C)
        
        # Compute Query, Key, Value
        q = self.fc_q(features)  # (B, N, C_out)
        k = self.fc_k(neighbor_features)  # (B, N, k, C_out)
        v = self.fc_v(neighbor_features)  # (B, N, k, C_out)
        
        # Position encoding
        pos_enc = neighbor_xyz - xyz.unsqueeze(2)  # (B, N, k, 3)
        pos_enc = self.fc_delta(pos_enc)  # (B, N, k, C_out)
        
        # Attention scores
        attn = q.unsqueeze(2) - k + pos_enc  # (B, N, k, C_out)
        attn = self.fc_gamma(attn)  # (B, N, k, C_out)
        attn = F.softmax(attn, dim=2)  # (B, N, k, C_out)
        
        # Aggregate features
        out = torch.sum(attn * (v + pos_enc), dim=2)  # (B, N, C_out)
        out = self.fc_out(out)
        
        return out
    
    @staticmethod
    def knn(xyz, k):
        """
        Find k-nearest neighbors for each point.
        
        Args:
            xyz: (B, N, 3)
            k: number of neighbors
            
        Returns:
            indices of k-nearest neighbors (B, N, k)
        """
        B, N, _ = xyz.shape
        
        # Compute pairwise distances
        dist = torch.cdist(xyz, xyz)  # (B, N, N)
        
        # Get k nearest neighbors (including self)
        _, idx = torch.topk(dist, k, dim=2, largest=False)  # (B, N, k)
        
        return idx
    
    @staticmethod
    def gather_neighbors(features, idx):
        """
        Gather features of neighboring points.
        
        Args:
            features: (B, N, C)
            idx: (B, N, k)
            
        Returns:
            neighbor features (B, N, k, C)
        """
        B, N, C = features.shape
        k = idx.shape[2]
        
        # Expand features for gathering
        idx_expanded = idx.unsqueeze(-1).expand(-1, -1, -1, C)  # (B, N, k, C)
        features_expanded = features.unsqueeze(2).expand(-1, -1, k, -1)  # (B, N, k, C)
        
        # Gather
        neighbor_features = torch.gather(features_expanded, 1, 
                                        idx_expanded.transpose(1, 2)).transpose(1, 2)
        
        return neighbor_features


class TransitionDown(nn.Module):
    """Downsampling layer with max pooling."""
    
    def __init__(self, in_channels, out_channels, k=16, stride=4):
        super(TransitionDown, self).__init__()
        self.k = k
        self.stride = stride
        
        self.mlp = nn.Sequential(
            nn.Linear(in_channels, out_channels),
            nn.BatchNorm1d(out_channels),
            nn.ReLU()
        )
        
    def forward(self, xyz, features):
        """
        Args:
            xyz: (B, N, 3)
            features: (B, N, C)
            
        Returns:
            downsampled xyz and features
        """
        B, N, C = features.shape
        
        # Farthest point sampling
        fps_idx = self.farthest_point_sample(xyz, N // self.stride)
        
        # Subsample points
        xyz_sub = torch.gather(xyz, 1, fps_idx.unsqueeze(-1).expand(-1, -1, 3))
        
        # Get k-nearest neighbors in original cloud
        knn_idx = PointTransformerLayer.knn(xyz_sub, self.k)
        neighbor_features = PointTransformerLayer.gather_neighbors(features, knn_idx)
        
        # Max pooling
        features_sub = torch.max(neighbor_features, dim=2)[0]  # (B, N/stride, C)
        
        # MLP
        features_sub = self.mlp(features_sub.transpose(1, 2)).transpose(1, 2)
        
        return xyz_sub, features_sub
    
    @staticmethod
    def farthest_point_sample(xyz, npoint):
        """
        Farthest point sampling.
        
        Args:
            xyz: (B, N, 3)
            npoint: number of points to sample
            
        Returns:
            sampled point indices (B, npoint)
        """
        B, N, _ = xyz.shape
        device = xyz.device
        
        centroids = torch.zeros(B, npoint, dtype=torch.long).to(device)
        distance = torch.ones(B, N).to(device) * 1e10
        farthest = torch.randint(0, N, (B,), dtype=torch.long).to(device)
        batch_indices = torch.arange(B, dtype=torch.long).to(device)
        
        for i in range(npoint):
            centroids[:, i] = farthest
            centroid = xyz[batch_indices, farthest, :].view(B, 1, 3)
            dist = torch.sum((xyz - centroid) ** 2, -1)
            mask = dist < distance
            distance[mask] = dist[mask]
            farthest = torch.max(distance, -1)[1]
        
        return centroids


class TransitionUp(nn.Module):
    """Upsampling layer with interpolation."""
    
    def __init__(self, in_channels, out_channels):
        super(TransitionUp, self).__init__()
        
        self.mlp = nn.Sequential(
            nn.Linear(in_channels, out_channels),
            nn.BatchNorm1d(out_channels),
            nn.ReLU()
        )
        
    def forward(self, xyz1, xyz2, features1, features2):
        """
        Args:
            xyz1: (B, N1, 3) - low resolution
            xyz2: (B, N2, 3) - high resolution
            features1: (B, N1, C1) - low resolution features
            features2: (B, N2, C2) - high resolution features
            
        Returns:
            interpolated features (B, N2, C_out)
        """
        # Interpolate features from low to high resolution
        features1_interp = self.interpolate(xyz1, xyz2, features1)
        
        # Concatenate with high-res features
        features = torch.cat([features1_interp, features2], dim=-1)
        
        # MLP
        features = self.mlp(features.transpose(1, 2)).transpose(1, 2)
        
        return features
    
    @staticmethod
    def interpolate(xyz1, xyz2, features1, k=3):
        """
        Interpolate features using k-nearest neighbors.
        
        Args:
            xyz1: (B, N1, 3) - source points
            xyz2: (B, N2, 3) - target points
            features1: (B, N1, C) - source features
            k: number of neighbors
            
        Returns:
            interpolated features (B, N2, C)
        """
        B, N1, C = features1.shape
        N2 = xyz2.shape[1]
        
        # Find k-nearest neighbors
        dist = torch.cdist(xyz2, xyz1)  # (B, N2, N1)
        dist, idx = torch.topk(dist, k, dim=2, largest=False)  # (B, N2, k)
        
        # Inverse distance weighting
        dist = torch.clamp(dist, min=1e-10)
        weights = 1.0 / dist
        weights = weights / torch.sum(weights, dim=2, keepdim=True)  # (B, N2, k)
        
        # Gather neighbor features
        idx_expanded = idx.unsqueeze(-1).expand(-1, -1, -1, C)
        neighbor_features = torch.gather(
            features1.unsqueeze(1).expand(-1, N2, -1, -1),
            2, idx_expanded
        )  # (B, N2, k, C)
        
        # Weighted sum
        features2 = torch.sum(weights.unsqueeze(-1) * neighbor_features, dim=2)
        
        return features2


class PointTransformerCls(nn.Module):
    """
    Point Transformer for classification tasks.
    """
    
    def __init__(self, num_classes=10, num_points=1024, in_channels=3):
        super(PointTransformerCls, self).__init__()
        
        # Input embedding
        self.input_embed = nn.Sequential(
            nn.Linear(in_channels, 32),
            nn.BatchNorm1d(32),
            nn.ReLU()
        )
        
        # Encoder
        self.pt1 = PointTransformerLayer(32, 64, k=16)
        self.down1 = TransitionDown(64, 128, k=16, stride=4)
        
        self.pt2 = PointTransformerLayer(128, 256, k=16)
        self.down2 = TransitionDown(256, 512, k=16, stride=4)
        
        self.pt3 = PointTransformerLayer(512, 512, k=16)
        
        # Global pooling
        self.global_pool = nn.AdaptiveMaxPool1d(1)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, xyz, features=None):
        """
        Args:
            xyz: point coordinates (B, N, 3)
            features: optional point features (B, N, C)
            
        Returns:
            class logits (B, num_classes)
        """
        B, N, _ = xyz.shape
        
        # Use xyz as features if not provided
        if features is None:
            features = xyz
        
        # Input embedding
        features = self.input_embed(features.transpose(1, 2)).transpose(1, 2)
        
        # Encoder
        features = self.pt1(xyz, features)
        xyz, features = self.down1(xyz, features)
        
        features = self.pt2(xyz, features)
        xyz, features = self.down2(xyz, features)
        
        features = self.pt3(xyz, features)
        
        # Global pooling
        features = self.global_pool(features.transpose(1, 2))  # (B, C, 1)
        features = features.squeeze(-1)  # (B, C)
        
        # Classification
        logits = self.classifier(features)
        
        return logits


def test_point_transformer():
    """Test the Point Transformer implementation."""
    
    print("=" * 60)
    print("Point Transformer Test")
    print("=" * 60)
    
    # Create sample data
    batch_size = 4
    num_points = 1024
    num_classes = 10
    
    # Random point cloud (B, N, 3)
    xyz = torch.randn(batch_size, num_points, 3)
    
    print(f"\nInput point cloud shape: {xyz.shape}")
    
    # Create model
    model = PointTransformerCls(num_classes=num_classes, num_points=num_points)
    
    # Count parameters
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model parameters: {num_params:,}")
    
    # Forward pass
    print("\nRunning forward pass...")
    with torch.no_grad():
        logits = model(xyz)
    
    print(f"Output logits shape: {logits.shape}")
    print(f"Predicted classes: {torch.argmax(logits, dim=1)}")
    
    # Test with features
    print("\nTesting with additional features...")
    features = torch.randn(batch_size, num_points, 6)  # xyz + rgb
    with torch.no_grad():
        logits = model(xyz, features)
    print(f"Output shape: {logits.shape}")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    
    return model


if __name__ == "__main__":
    # Test the implementation
    model = test_point_transformer()
    
    # Print model architecture
    print("\nModel Architecture:")
    print(model)
