# KarigAI Local Development Startup Script
# This script starts all services needed for local development

Write-Host "🚀 Starting KarigAI Local Development Environment..." -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
$dockerRunning = docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Create .env file if it doesn't exist
if (-not (Test-Path "karigai_backend\.env")) {
    Write-Host "Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item "karigai_backend\.env.example" "karigai_backend\.env"
    Write-Host "✅ Created .env file. Please update it with your API keys if needed." -ForegroundColor Green
    Write-Host ""
}

# Start Docker services
Write-Host "Starting Docker services (PostgreSQL, Redis, Backend)..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Docker services" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker services started" -ForegroundColor Green
Write-Host ""

# Wait for services to be ready
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check backend health
Write-Host "Checking backend health..." -ForegroundColor Yellow
$maxRetries = 10
$retryCount = 0
$backendReady = $false

while ($retryCount -lt $maxRetries -and -not $backendReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Write-Host "✅ Backend is ready!" -ForegroundColor Green
        }
    } catch {
        $retryCount++
        Write-Host "Waiting for backend... ($retryCount/$maxRetries)" -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
}

if (-not $backendReady) {
    Write-Host "⚠️  Backend health check failed, but services are running." -ForegroundColor Yellow
    Write-Host "   Check logs with: docker-compose logs -f backend" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🎉 KarigAI Backend Services are Running!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Service URLs:" -ForegroundColor Cyan
Write-Host "   Backend API:        http://localhost:8000" -ForegroundColor White
Write-Host "   API Documentation:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Health Check:       http://localhost:8000/health" -ForegroundColor White
Write-Host "   PostgreSQL:         localhost:5432" -ForegroundColor White
Write-Host "   Redis:              localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "📱 To start the Flutter mobile app:" -ForegroundColor Cyan
Write-Host "   cd karigai_mobile" -ForegroundColor White
Write-Host "   flutter pub get" -ForegroundColor White
Write-Host "   flutter run -d chrome" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Useful Commands:" -ForegroundColor Cyan
Write-Host "   View logs:          docker-compose logs -f backend" -ForegroundColor White
Write-Host "   Stop services:      docker-compose down" -ForegroundColor White
Write-Host "   Restart backend:    docker-compose restart backend" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   Local Setup:        LOCAL_SETUP.md" -ForegroundColor White
Write-Host "   Deployment:         karigai_backend/DEPLOYMENT.md" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Ask if user wants to open browser
$openBrowser = Read-Host "Would you like to open the API documentation in your browser? (Y/n)"
if ($openBrowser -eq "" -or $openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "http://localhost:8000/docs"
}

Write-Host ""
Write-Host "Press any key to view backend logs (Ctrl+C to exit)..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Show logs
docker-compose logs -f backend
