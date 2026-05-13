# Flutter Setup Verification Script
# Run this script to verify your Flutter development environment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Flutter Setup Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Function to check if a command exists
function Test-CommandExists {
    param($command)
    $null = Get-Command $command -ErrorAction SilentlyContinue
    return $?
}

# Function to print check result
function Print-Check {
    param($name, $result, $details = "")
    if ($result) {
        Write-Host "✓ $name" -ForegroundColor Green
        if ($details) {
            Write-Host "  $details" -ForegroundColor Gray
        }
    } else {
        Write-Host "✗ $name" -ForegroundColor Red
        if ($details) {
            Write-Host "  $details" -ForegroundColor Yellow
        }
        $script:allGood = $false
    }
}

Write-Host "Checking required tools..." -ForegroundColor Cyan
Write-Host ""

# Check Git
$gitInstalled = Test-CommandExists git
if ($gitInstalled) {
    $gitVersion = git --version
    Print-Check "Git" $true $gitVersion
} else {
    Print-Check "Git" $false "Not installed. Download from: https://git-scm.com/download/win"
}

# Check Flutter
$flutterInstalled = Test-CommandExists flutter
if ($flutterInstalled) {
    $flutterVersion = flutter --version | Select-Object -First 1
    Print-Check "Flutter SDK" $true $flutterVersion
} else {
    Print-Check "Flutter SDK" $false "Not installed. Run install_flutter_windows.ps1"
}

# Check Dart (comes with Flutter)
$dartInstalled = Test-CommandExists dart
if ($dartInstalled) {
    $dartVersion = dart --version 2>&1 | Select-Object -First 1
    Print-Check "Dart SDK" $true $dartVersion
} else {
    Print-Check "Dart SDK" $false "Should come with Flutter"
}

# Check Chrome
$chromeInstalled = Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe"
Print-Check "Chrome" $chromeInstalled $(if ($chromeInstalled) { "Installed" } else { "Not found. Install for web development" })

# Check VS Code
$vscodeInstalled = Test-CommandExists code
Print-Check "VS Code" $vscodeInstalled $(if ($vscodeInstalled) { "Installed" } else { "Optional but recommended" })

# Check Android Studio
$androidStudioInstalled = Test-Path "C:\Program Files\Android\Android Studio\bin\studio64.exe"
Print-Check "Android Studio" $androidStudioInstalled $(if ($androidStudioInstalled) { "Installed" } else { "Required for Android development" })

Write-Host ""
Write-Host "Checking Flutter configuration..." -ForegroundColor Cyan
Write-Host ""

if ($flutterInstalled) {
    # Check Flutter doctor
    Write-Host "Running Flutter Doctor..." -ForegroundColor Yellow
    Write-Host ""
    flutter doctor
    
    Write-Host ""
    Write-Host "Checking project dependencies..." -ForegroundColor Cyan
    Write-Host ""
    
    # Check if we're in the project directory
    if (Test-Path "pubspec.yaml") {
        Write-Host "✓ Found pubspec.yaml" -ForegroundColor Green
        
        # Check if dependencies are installed
        if (Test-Path ".dart_tool") {
            Write-Host "✓ Dependencies are installed" -ForegroundColor Green
        } else {
            Write-Host "✗ Dependencies not installed" -ForegroundColor Red
            Write-Host "  Run: flutter pub get" -ForegroundColor Yellow
            $allGood = $false
        }
    } else {
        Write-Host "⚠ Not in Flutter project directory" -ForegroundColor Yellow
        Write-Host "  Navigate to: cd karigai_mobile" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host "Setup Status: READY ✓" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Your Flutter development environment is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Navigate to project: cd karigai_mobile" -ForegroundColor White
    Write-Host "2. Get dependencies: flutter pub get" -ForegroundColor White
    Write-Host "3. Run the app: flutter run" -ForegroundColor White
} else {
    Write-Host "Setup Status: INCOMPLETE ✗" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Please fix the issues above before continuing." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "- Run install_flutter_windows.ps1 as Administrator" -ForegroundColor White
    Write-Host "- Restart PowerShell after installation" -ForegroundColor White
    Write-Host "- Run: flutter doctor --android-licenses" -ForegroundColor White
    Write-Host "- See INSTALLATION_GUIDE.md for detailed help" -ForegroundColor White
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
