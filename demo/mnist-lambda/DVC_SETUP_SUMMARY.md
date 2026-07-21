# DVC Pipeline Setup Summary

## ✅ Created Files

### Core DVC Files
1. **dvc.yaml** - Pipeline definition with 4 stages:
   - `download_data`: Downloads MNIST dataset
   - `train`: Trains the CNN model
   - `evaluate`: Evaluates model performance
   - `export_model`: Exports traced model for Lambda

2. **params.yaml** - Hyperparameters configuration:
   - Training parameters (epochs, batch_size, learning_rate, wandb settings)
   - Model architecture (conv layers, dropout rates)
   - Data settings (normalization values, data directory)
   - Evaluation settings
   - Lambda deployment settings

3. **.dvcignore** - Files to ignore in DVC tracking

### Updated Files
4. **train_model.py** - Enhanced with:
   - JSON and YAML imports
   - Automatic parameter loading from `params.yaml`
   - Metrics export to `metrics/training_metrics.json`
   - DVC-compatible outputs

5. **requirements.txt** - Added:
   - `dvc>=3.0.0`
   - `pyyaml>=6.0`

### New Scripts
6. **evaluate_model.py** - Complete evaluation script:
   - Loads trained model
   - Evaluates on test dataset
   - Generates detailed metrics (accuracy, loss, per-class accuracy)
   - Creates confusion matrix CSV for DVC plots
   - Optionally saves predictions

### Documentation
7. **DVC_README.md** - Comprehensive guide covering:
   - Pipeline overview and DAG
   - Installation and setup
   - Running the pipeline
   - Experiment tracking (DVC + W&B)
   - Parameter tuning
   - Metrics and plots
   - Team collaboration
   - Troubleshooting
   - CI/CD integration
   - Best practices

8. **README.md** - Updated to include:
   - DVC pipeline as recommended approach
   - Links to DVC documentation
   - Quick start options (DVC vs manual)

### Automation
9. **Makefile** - Convenient commands for:
   - `make install` - Install dependencies
   - `make init` - Initialize DVC
   - `make repro` - Run full pipeline
   - `make train` - Train only
   - `make evaluate` - Evaluate only
   - `make metrics` - Show metrics
   - `make plots` - Show confusion matrix
   - `make exp-run` - Run experiments
   - Plus many more shortcuts

10. **quickstart.sh** - Bash script for Linux/Mac
11. **quickstart.ps1** - PowerShell script for Windows

## 🎯 Pipeline Stages

```
download_data → train → evaluate → export_model
```

### Stage Details

| Stage | Command | Inputs | Outputs | Metrics |
|-------|---------|--------|---------|---------|
| download_data | Downloads MNIST | - | data/MNIST/raw/ | - |
| train | `python train_model.py` | train_model.py, data, params | models/*.pth | training_metrics.json |
| evaluate | `python evaluate_model.py` | evaluate_model.py, models, data, params | - | evaluation_metrics.json, confusion_matrix.csv |
| export_model | Model already traced | models/mnist_model_traced.pt | models/mnist_model_traced.pt | - |

## 📊 Tracked Metrics

### Training Metrics (training_metrics.json)
- `final_validation_accuracy`
- `num_epochs`
- `batch_size`
- `learning_rate`
- `device`
- `total_parameters`

### Evaluation Metrics (evaluation_metrics.json)
- `test_accuracy`
- `test_loss`
- `average_confidence`
- `total_samples`
- `correct_predictions`
- `class_0_accuracy` through `class_9_accuracy`

### Plots
- Confusion matrix (metrics/confusion_matrix.csv)

## 🚀 How to Use

### Quick Start (Windows)
```powershell
# Run the setup script
.\quickstart.ps1

# Or manually
pip install -r requirements.txt
dvc init
dvc repro
```

### Quick Start (Linux/Mac)
```bash
# Run the setup script
chmod +x quickstart.sh
./quickstart.sh

# Or manually
pip install -r requirements.txt
dvc init
dvc repro
```

### Using Make (if available)
```bash
make install
make init
make repro
make metrics
```

## 🔧 Configuration

Edit `params.yaml` to change hyperparameters:

```yaml
training:
  num_epochs: 10        # Change from 5 to 10
  batch_size: 128       # Change from 64
  learning_rate: 0.0005 # Change learning rate
```

Then run:
```bash
dvc repro  # Automatically detects changes
```

## 📈 Experiment Tracking

### With DVC Experiments
```bash
# Run experiment with different parameters
dvc exp run -S training.num_epochs=10 -S training.learning_rate=0.0005

# List experiments
dvc exp show

# Compare experiments
dvc exp diff
```

### With Weights & Biases
```bash
# Login
wandb login

# Run pipeline (W&B enabled by default)
dvc repro

# View at https://wandb.ai/
```

## 📦 Output Structure

After running the pipeline:

```
mnist-lambda/
├── data/
│   └── MNIST/raw/              # MNIST dataset (tracked by DVC)
├── models/
│   ├── mnist_model.pth         # Model weights (tracked by DVC)
│   └── mnist_model_traced.pt   # JIT traced model (tracked by DVC)
├── metrics/
│   ├── training_metrics.json   # Training results
│   ├── evaluation_metrics.json # Test results
│   ├── confusion_matrix.csv    # For DVC plots
│   └── predictions.json        # Optional detailed predictions
└── wandb/                      # W&B logs (ignored by DVC)
```

## 🔄 Workflow

### 1. Development
```bash
# Make changes to code or params
vim params.yaml
vim train_model.py

# Run pipeline
dvc repro

# Check metrics
dvc metrics show
```

### 2. Experimentation
```bash
# Try different hyperparameters
dvc exp run -S training.num_epochs=10
dvc exp run -S training.batch_size=128

# Compare results
dvc exp show

# Apply best experiment
dvc exp apply <exp-name>
```

### 3. Collaboration
```bash
# Share your work
git add dvc.yaml dvc.lock params.yaml
git commit -m "Improved model accuracy"
git push

# Team members reproduce
git pull
dvc pull
dvc repro
```

## 🎓 Key Benefits

1. **Reproducibility**: Every experiment is fully reproducible
2. **Version Control**: Track code, data, models, and metrics together
3. **Experiment Tracking**: Compare different hyperparameters easily
4. **Collaboration**: Share experiments with team seamlessly
5. **Automation**: Single command runs entire pipeline
6. **Efficiency**: DVC caches outputs, only re-runs changed stages
7. **Integration**: Works with Git, W&B, CI/CD pipelines

## 📚 Next Steps

1. **Run the pipeline**: `dvc repro`
2. **View metrics**: `dvc metrics show`
3. **Experiment**: Try different parameters in `params.yaml`
4. **Deploy**: Use trained model with `cdk deploy`
5. **Read docs**: See `DVC_README.md` for advanced features

## 🆘 Support

- DVC Documentation: https://dvc.org/doc
- Project README: `README.md`
- Pipeline Guide: `DVC_README.md`
- W&B Docs: https://docs.wandb.ai/

---

**Happy Experimenting! 🚀**
