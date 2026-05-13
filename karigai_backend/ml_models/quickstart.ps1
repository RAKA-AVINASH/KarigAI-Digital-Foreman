# Quick start script for KarigAI ML development (Windows PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "KarigAI ML Development Quick Start" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed. Please install Python 3.8 or later." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check if pip is installed
try {
    $pipVersion = pip --version 2>&1
    Write-Host "✅ pip found" -ForegroundColor Green
} catch {
    Write-Host "❌ pip is not installed. Please install pip." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Run setup script
Write-Host "Running setup script..." -ForegroundColor Yellow
python setup_ml_env.py

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start developing:" -ForegroundColor Yellow
Write-Host "  1. cd ml_models"
Write-Host "  2. jupyter lab"
Write-Host ""
Write-Host "To start MLflow UI:" -ForegroundColor Yellow
Write-Host "  1. cd ml_models"
Write-Host "  2. mlflow ui"
Write-Host ""
