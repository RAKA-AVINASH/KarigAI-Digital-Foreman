# KarigAI Backend Local Startup (Without Docker)
# This script starts the backend API directly with Python

Write-Host "Starting KarigAI Backend (Local Mode)..." -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "OK $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Navigate to backend directory
Set-Location karigai_backend

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "OK Virtual environment created" -ForegroundColor Green
    Write-Host ""
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Check if requirements are installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$requirementsInstalled = Test-Path "venv\Lib\site-packages\fastapi"
if (-not $requirementsInstalled) {
    Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host "OK Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "OK Dependencies already installed" -ForegroundColor Green
}
Write-Host ""

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    
    # Update .env for local development without Docker
    $envContent = Get-Content ".env"
    $envContent = $envContent -replace "DATABASE_URL=.*", "DATABASE_URL=sqlite:///./karigai.db"
    $envContent = $envContent -replace "REDIS_URL=.*", "# REDIS_URL=redis://localhost:6379/0  # Optional for local dev"
    $envContent | Set-Content ".env"
    
    Write-Host "OK Created .env file (configured for SQLite)" -ForegroundColor Green
    Write-Host ""
}

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Starting KarigAI Backend API..." -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The API will be available at:" -ForegroundColor Cyan
Write-Host "   Backend API:        http://localhost:8000" -ForegroundColor White
Write-Host "   API Documentation:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Health Check:       http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Start the server
python main.py
