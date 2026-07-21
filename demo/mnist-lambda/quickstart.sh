#!/bin/bash
# Quick start script for MNIST DVC Pipeline

set -e

echo "🚀 MNIST DVC Pipeline - Quick Start"
echo "===================================="
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8+ first."
    exit 1
fi

echo "✓ Python found: $(python --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✓ Dependencies installed"
echo ""

# Initialize DVC
if [ ! -d ".dvc" ]; then
    echo "🔧 Initializing DVC..."
    dvc init --subdir
    echo "✓ DVC initialized"
else
    echo "✓ DVC already initialized"
fi

echo ""

# Optional: Setup W&B
read -p "Do you want to setup Weights & Biases? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔑 Setting up Weights & Biases..."
    wandb login
    echo "✓ W&B configured"
else
    echo "⚠️  Skipping W&B setup. Training will run without experiment tracking."
    # Disable wandb in params
    sed -i 's/use_wandb: true/use_wandb: false/' params.yaml 2>/dev/null || \
    sed -i '' 's/use_wandb: true/use_wandb: false/' params.yaml 2>/dev/null || true
fi

echo ""
echo "🎯 Ready to run the pipeline!"
echo ""
echo "Quick commands:"
echo "  make repro       - Run full pipeline"
echo "  make train       - Train model only"
echo "  make evaluate    - Evaluate model only"
echo "  make metrics     - Show metrics"
echo "  make help        - Show all commands"
echo ""
echo "Or run manually:"
echo "  dvc repro        - Run full pipeline"
echo "  dvc metrics show - Show metrics"
echo ""

read -p "Do you want to run the pipeline now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏃 Running pipeline..."
    dvc repro
    echo ""
    echo "📊 Training Results:"
    cat metrics/training_metrics.json
    echo ""
    echo "📊 Evaluation Results:"
    cat metrics/evaluation_metrics.json
    echo ""
    echo "✅ Pipeline completed successfully!"
else
    echo "👍 Skipping pipeline run. Run 'dvc repro' when ready."
fi

echo ""
echo "📚 For more information, see DVC_README.md"
