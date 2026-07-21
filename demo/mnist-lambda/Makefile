.PHONY: help install init train evaluate repro clean metrics plots status push pull

help:
	@echo "MNIST DVC Pipeline - Available Commands"
	@echo "========================================"
	@echo "make install      - Install all dependencies"
	@echo "make init         - Initialize DVC (first time only)"
	@echo "make train        - Run training stage only"
	@echo "make evaluate     - Run evaluation stage only"
	@echo "make repro        - Run full DVC pipeline"
	@echo "make repro-force  - Force re-run entire pipeline"
	@echo "make metrics      - Show all metrics"
	@echo "make plots        - Show confusion matrix plot"
	@echo "make status       - Show DVC pipeline status"
	@echo "make clean        - Clean generated files"
	@echo "make push         - Push data/models to DVC remote"
	@echo "make pull         - Pull data/models from DVC remote"
	@echo "make dag          - Show pipeline dependency graph"
	@echo "make exp-run      - Run experiment with custom params"
	@echo "make exp-show     - Show all experiments"

install:
	pip install -r requirements.txt

init:
	dvc init
	@echo "DVC initialized! Configure remote with:"
	@echo "  dvc remote add -d myremote s3://bucket/path"

train:
	dvc repro train

evaluate:
	dvc repro evaluate

repro:
	dvc repro

repro-force:
	dvc repro --force

metrics:
	@echo "=== Training Metrics ==="
	@cat metrics/training_metrics.json 2>/dev/null || echo "No training metrics found. Run 'make train' first."
	@echo ""
	@echo "=== Evaluation Metrics ==="
	@cat metrics/evaluation_metrics.json 2>/dev/null || echo "No evaluation metrics found. Run 'make evaluate' first."
	@echo ""
	@dvc metrics show

plots:
	dvc plots show metrics/confusion_matrix.csv

status:
	dvc status

dag:
	dvc dag

push:
	dvc push

pull:
	dvc pull

clean:
	rm -rf models/*.pth models/*.pt
	rm -rf metrics/*.json metrics/*.csv
	rm -rf wandb/
	rm -rf data/MNIST/processed/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

exp-run:
	@echo "Example: dvc exp run -S training.num_epochs=10 -S training.learning_rate=0.0005"
	@echo "Run with custom parameters:"
	@read -p "Enter parameters (e.g., training.num_epochs=10): " params; \
	dvc exp run -S $$params

exp-show:
	dvc exp show

exp-diff:
	dvc exp diff

# Quick experiment shortcuts
exp-10epochs:
	dvc exp run -S training.num_epochs=10

exp-20epochs:
	dvc exp run -S training.num_epochs=20

exp-batch128:
	dvc exp run -S training.batch_size=128

exp-lr-low:
	dvc exp run -S training.learning_rate=0.0001

exp-lr-high:
	dvc exp run -S training.learning_rate=0.01

# Wandb integration
wandb-login:
	wandb login

wandb-off:
	dvc exp run -S training.use_wandb=false

# Model deployment
deploy:
	@echo "Deploying model to AWS Lambda..."
	cdk deploy

test-api:
	python test_api.py

# Development
lint:
	flake8 train_model.py evaluate_model.py lambda_function.py --max-line-length=120

format:
	black train_model.py evaluate_model.py lambda_function.py

# Full workflow
all: install init repro metrics

# CI/CD simulation
ci: repro metrics
	@echo "Pipeline completed successfully!"
	@echo "Training accuracy: $$(cat metrics/training_metrics.json | grep final_validation_accuracy | cut -d':' -f2 | tr -d ', ')"
	@echo "Test accuracy: $$(cat metrics/evaluation_metrics.json | grep test_accuracy | cut -d':' -f2 | tr -d ', ')"
