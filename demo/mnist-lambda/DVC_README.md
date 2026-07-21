# DVC Pipeline for MNIST Training

This directory contains a complete DVC (Data Version Control) pipeline for training and evaluating the MNIST digit recognition model.

## 🎯 Pipeline Overview

The DVC pipeline consists of 4 stages:

1. **download_data**: Download MNIST dataset
2. **train**: Train the CNN model
3. **evaluate**: Evaluate model on test set
4. **export_model**: Export traced model for Lambda deployment

## 📋 Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize DVC (first time only)
dvc init

# Optional: Configure remote storage (S3, GCS, Azure, etc.)
# dvc remote add -d myremote s3://my-bucket/dvc-storage
```

## 🚀 Running the Pipeline

### Run the entire pipeline:

```bash
dvc repro
```

This will execute all stages in order, skipping stages that haven't changed.

### Run a specific stage:

```bash
# Download data only
dvc repro download_data

# Train model only
dvc repro train

# Evaluate model only
dvc repro evaluate
```

### Force re-run (ignore cache):

```bash
dvc repro --force
```

## 📊 Viewing Metrics

DVC automatically tracks metrics defined in `dvc.yaml`:

```bash
# Show all metrics
dvc metrics show

# Compare metrics across experiments
dvc metrics diff

# Show plots (confusion matrix)
dvc plots show metrics/confusion_matrix.csv
```

## 🔧 Modifying Hyperparameters

Edit `params.yaml` to change training hyperparameters:

```yaml
training:
  num_epochs: 10          # Change from 5 to 10
  batch_size: 128         # Change from 64 to 128
  learning_rate: 0.0005   # Change from 0.001
  use_wandb: true
```

Then run:

```bash
dvc repro
```

DVC will automatically detect parameter changes and re-run affected stages.

## 📈 Experiment Tracking

### With DVC Experiments:

```bash
# Run experiment with different parameters
dvc exp run -S training.num_epochs=10 -S training.learning_rate=0.0005

# List all experiments
dvc exp show

# Compare experiments
dvc exp diff

# Apply the best experiment
dvc exp apply exp-12345
```

### With Weights & Biases:

The pipeline integrates with W&B for real-time tracking:

```bash
# Login to W&B
wandb login

# Run pipeline (W&B enabled by default in params.yaml)
dvc repro
```

View experiments at: https://wandb.ai/

## 📦 Managing Data and Models

### Track data files:

```bash
# Add data to DVC tracking
dvc add data/MNIST

# Push to remote storage
dvc push
```

### Pull data from remote:

```bash
# Pull all tracked data
dvc pull

# Pull specific stage outputs
dvc pull download_data.dvc
```

## 🔄 Pipeline DAG (Directed Acyclic Graph)

Visualize pipeline dependencies:

```bash
# View pipeline DAG
dvc dag

# Generate DAG visualization
dvc dag --md > pipeline-dag.md
```

```
    ┌──────────────┐
    │download_data │
    └──────┬───────┘
           │
           ▼
       ┌───────┐
       │ train │
       └───┬───┘
           │
           ▼
      ┌─────────┐
      │evaluate │
      └────┬────┘
           │
           ▼
    ┌─────────────┐
    │export_model │
    └─────────────┘
```

## 📁 Output Files

After running the pipeline:

```
mnist-lambda/
├── data/
│   └── MNIST/raw/           # Downloaded dataset (tracked by DVC)
├── models/
│   ├── mnist_model.pth      # Trained model weights (tracked by DVC)
│   └── mnist_model_traced.pt # JIT traced model for Lambda (tracked by DVC)
├── metrics/
│   ├── training_metrics.json      # Training metrics
│   ├── evaluation_metrics.json    # Evaluation metrics
│   ├── confusion_matrix.csv       # Confusion matrix for plots
│   └── predictions.json           # Optional: detailed predictions
└── wandb/                         # W&B run data (ignored by DVC)
```

## 🎛️ Parameters Reference

### Training Parameters (`params.yaml`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `training.num_epochs` | 5 | Number of training epochs |
| `training.batch_size` | 64 | Batch size for training |
| `training.learning_rate` | 0.001 | Learning rate for Adam optimizer |
| `training.use_wandb` | true | Enable Weights & Biases logging |
| `training.project_name` | mnist-digit-recognition | W&B project name |

### Model Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model.conv1_out` | 32 | First conv layer output channels |
| `model.conv2_out` | 64 | Second conv layer output channels |
| `model.dropout1` | 0.25 | First dropout rate |
| `model.dropout2` | 0.5 | Second dropout rate |

### Evaluation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `evaluation.test_batch_size` | 1000 | Batch size for evaluation |
| `evaluation.save_predictions` | false | Save detailed predictions |

## 🔍 Troubleshooting

### DVC cache issues:

```bash
# Clear DVC cache
dvc cache dir .dvc/cache

# Check DVC status
dvc status
```

### Pipeline not detecting changes:

```bash
# Force re-run all stages
dvc repro --force

# Check what changed
dvc status
```

### Metrics not updating:

```bash
# Remove metrics cache
dvc remove metrics/training_metrics.json.dvc --force
dvc remove metrics/evaluation_metrics.json.dvc --force

# Re-run pipeline
dvc repro
```

## 🚀 CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: DVC Pipeline

on: [push, pull_request]

jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: iterative/setup-dvc@v1
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run DVC pipeline
        run: dvc repro
      - name: Show metrics
        run: dvc metrics show
```

## 📚 Additional Resources

- [DVC Documentation](https://dvc.org/doc)
- [DVC Experiments](https://dvc.org/doc/command-reference/exp)
- [DVC Metrics](https://dvc.org/doc/command-reference/metrics)
- [DVC Plots](https://dvc.org/doc/command-reference/plots)
- [Weights & Biases](https://docs.wandb.ai/)

## 🎓 Best Practices

1. **Version Control**: Commit `dvc.yaml`, `params.yaml`, and `.dvc` files to git
2. **Remote Storage**: Configure DVC remote for team collaboration
3. **Experiment Tracking**: Use `dvc exp run` for systematic experimentation
4. **Reproducibility**: Always use `params.yaml` for hyperparameters
5. **Documentation**: Update this README when adding new stages
6. **Metrics**: Track all important metrics in JSON format
7. **Plots**: Use DVC plots for visualization

## 🤝 Team Collaboration

```bash
# Pull latest code and data
git pull
dvc pull

# Make changes and run experiments
dvc exp run -S training.num_epochs=10

# Share results
git add dvc.yaml dvc.lock params.yaml
git commit -m "Experiment: 10 epochs"
git push
dvc push
```

Team members can reproduce your results with:

```bash
git pull
dvc pull
dvc repro
```
