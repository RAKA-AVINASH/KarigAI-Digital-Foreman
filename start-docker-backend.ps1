# KarigAI Backend Docker Startup Script
# This script starts the backend services using Docker Compose

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KarigAI Backend Docker Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
Write-Host "Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if Docker Compose is available
Write-Host "Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker compose version
    Write-Host "✓ Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose is not available" -ForegroundColor Red
    exit 1
}

# Check if Docker daemon is running
Write-Host "Checking Docker daemon..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✓ Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker daemon is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Backend Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
docker compose down

Write-Host ""
Write-Host "Building and starting services..." -ForegroundColor Yellow
Write-Host "This may take a few minutes on first run..." -ForegroundColor Gray
Write-Host ""

# Build and start services
docker compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Backend Services Started Successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services running:" -ForegroundColor Cyan
    Write-Host "  • PostgreSQL Database: localhost:5432" -ForegroundColor White
    Write-Host "  • Redis Cache: localhost:6379" -ForegroundColor White
    Write-Host "  • FastAPI Backend: http://localhost:8000" -ForegroundColor White
    Write-Host "  • Nginx Proxy: http://localhost:80" -ForegroundColor White
    Write-Host ""
    Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Yellow
    Write-Host "Health Check: http://localhost:8000/health" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To view logs: docker compose logs -f" -ForegroundColor Gray
    Write-Host "To stop services: docker compose down" -ForegroundColor Gray
    Write-Host ""
    
    # Wait a moment for services to initialize
    Write-Host "Waiting for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Check backend health
    Write-Host "Checking backend health..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Backend is healthy and responding" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠ Backend may still be initializing. Check logs with: docker compose logs backend" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Press any key to view live logs (Ctrl+C to exit logs)..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    docker compose logs -f
    
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  Failed to Start Backend Services" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
    Write-Host "You can view detailed logs with: docker compose logs" -ForegroundColor Gray
    exit 1
}
