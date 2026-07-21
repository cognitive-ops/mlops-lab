# Quick start script for MNIST DVC Pipeline (Windows PowerShell)

Write-Host "🚀 MNIST DVC Pipeline - Quick Start" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Initialize DVC
if (-not (Test-Path ".dvc")) {
    Write-Host "🔧 Initializing DVC..." -ForegroundColor Yellow
    dvc init
    Write-Host "✓ DVC initialized" -ForegroundColor Green
} else {
    Write-Host "✓ DVC already initialized" -ForegroundColor Green
}

Write-Host ""

# Optional: Setup W&B
$setupWandb = Read-Host "Do you want to setup Weights & Biases? (y/n)"
if ($setupWandb -eq "y" -or $setupWandb -eq "Y") {
    Write-Host "🔑 Setting up Weights & Biases..." -ForegroundColor Yellow
    wandb login
    Write-Host "✓ W&B configured" -ForegroundColor Green
} else {
    Write-Host "⚠️  Skipping W&B setup. Training will run without experiment tracking." -ForegroundColor Yellow
    # Disable wandb in params
    (Get-Content params.yaml) -replace 'use_wandb: true', 'use_wandb: false' | Set-Content params.yaml
}

Write-Host ""
Write-Host "🎯 Ready to run the pipeline!" -ForegroundColor Green
Write-Host ""
Write-Host "Quick commands:" -ForegroundColor Cyan
Write-Host "  dvc repro         - Run full pipeline"
Write-Host "  dvc repro train   - Train model only"
Write-Host "  dvc metrics show  - Show metrics"
Write-Host "  dvc dag           - Show pipeline graph"
Write-Host ""

$runPipeline = Read-Host "Do you want to run the pipeline now? (y/n)"
if ($runPipeline -eq "y" -or $runPipeline -eq "Y") {
    Write-Host ""
    Write-Host "🏃 Running pipeline..." -ForegroundColor Yellow
    dvc repro
    
    Write-Host ""
    Write-Host "📊 Training Results:" -ForegroundColor Cyan
    Get-Content metrics/training_metrics.json
    
    Write-Host ""
    Write-Host "📊 Evaluation Results:" -ForegroundColor Cyan
    Get-Content metrics/evaluation_metrics.json
    
    Write-Host ""
    Write-Host "✅ Pipeline completed successfully!" -ForegroundColor Green
} else {
    Write-Host "👍 Skipping pipeline run. Run 'dvc repro' when ready." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📚 For more information, see DVC_README.md" -ForegroundColor Cyan
