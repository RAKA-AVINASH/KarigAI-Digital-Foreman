# KarigAI Backend Startup Script
Write-Host "Starting KarigAI Backend..." -ForegroundColor Green

# Navigate to backend
Set-Location karigai_backend

# Create venv if needed
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -q -r requirements-local.txt

# Create .env if needed
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    @"
DATABASE_URL=sqlite:///./karigai.db
ENVIRONMENT=development
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,*
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:*
OPENAI_API_KEY=
ELEVENLABS_API_KEY=
"@ | Out-File -FilePath ".env" -Encoding UTF8
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Health: http://localhost:8000/health" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start server
python main.py
