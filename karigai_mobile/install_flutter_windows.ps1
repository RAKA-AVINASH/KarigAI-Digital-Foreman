# Flutter Development Environment Setup Script for Windows
# Run this script as Administrator in PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Flutter Development Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Function to check if a command exists
function Test-CommandExists {
    param($command)
    $null = Get-Command $command -ErrorAction SilentlyContinue
    return $?
}

# Function to add to PATH
function Add-ToPath {
    param($path)
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$path*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$path", "User")
        Write-Host "Added to PATH: $path" -ForegroundColor Green
    } else {
        Write-Host "Already in PATH: $path" -ForegroundColor Yellow
    }
}

Write-Host "Step 1: Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Check Git
if (Test-CommandExists git) {
    $gitVersion = git --version
    Write-Host "✓ Git is installed: $gitVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Git is not installed" -ForegroundColor Red
    Write-Host "Installing Git..." -ForegroundColor Yellow
    
    # Download and install Git
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"
    $gitInstaller = "$env:TEMP\git-installer.exe"
    
    Write-Host "Downloading Git..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller
    
    Write-Host "Installing Git (this may take a few minutes)..." -ForegroundColor Yellow
    Start-Process -FilePath $gitInstaller -Args "/VERYSILENT /NORESTART" -Wait
    
    Remove-Item $gitInstaller
    Write-Host "✓ Git installed successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Installing Chocolatey (package manager)..." -ForegroundColor Cyan
Write-Host ""

# Check if Chocolatey is installed
if (Test-CommandExists choco) {
    Write-Host "✓ Chocolatey is already installed" -ForegroundColor Green
} else {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "✓ Chocolatey installed successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 3: Installing Flutter SDK..." -ForegroundColor Cyan
Write-Host ""

# Check if Flutter is installed
if (Test-CommandExists flutter) {
    $flutterVersion = flutter --version | Select-Object -First 1
    Write-Host "✓ Flutter is already installed: $flutterVersion" -ForegroundColor Green
} else {
    Write-Host "Installing Flutter SDK (this may take several minutes)..." -ForegroundColor Yellow
    choco install flutter -y
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "✓ Flutter SDK installed successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 4: Checking Android Studio..." -ForegroundColor Cyan
Write-Host ""

# Check if Android Studio is installed
$androidStudioPath = "C:\Program Files\Android\Android Studio\bin\studio64.exe"
if (Test-Path $androidStudioPath) {
    Write-Host "✓ Android Studio is installed" -ForegroundColor Green
} else {
    Write-Host "✗ Android Studio is not installed" -ForegroundColor Red
    Write-Host "Please download and install Android Studio manually from:" -ForegroundColor Yellow
    Write-Host "https://developer.android.com/studio" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installation:" -ForegroundColor Yellow
    Write-Host "1. Open Android Studio" -ForegroundColor Yellow
    Write-Host "2. Go to SDK Manager" -ForegroundColor Yellow
    Write-Host "3. Install Android SDK Platform (API 33+)" -ForegroundColor Yellow
    Write-Host "4. Install Android SDK Build-Tools" -ForegroundColor Yellow
    Write-Host "5. Install Android Emulator" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 5: Installing Chrome (for web development)..." -ForegroundColor Cyan
Write-Host ""

# Check if Chrome is installed
if (Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe") {
    Write-Host "✓ Chrome is already installed" -ForegroundColor Green
} else {
    Write-Host "Installing Chrome..." -ForegroundColor Yellow
    choco install googlechrome -y
    Write-Host "✓ Chrome installed successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 6: Installing Visual Studio Code (optional)..." -ForegroundColor Cyan
Write-Host ""

# Check if VS Code is installed
if (Test-CommandExists code) {
    Write-Host "✓ VS Code is already installed" -ForegroundColor Green
} else {
    Write-Host "Installing VS Code..." -ForegroundColor Yellow
    choco install vscode -y
    Write-Host "✓ VS Code installed successfully" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 7: Configuring Flutter..." -ForegroundColor Cyan
Write-Host ""

# Enable Flutter platforms
Write-Host "Enabling Flutter platforms..." -ForegroundColor Yellow
flutter config --enable-web
flutter config --enable-windows-desktop

Write-Host ""
Write-Host "Step 8: Running Flutter Doctor..." -ForegroundColor Cyan
Write-Host ""

# Run flutter doctor
flutter doctor -v

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Close and reopen PowerShell to refresh environment variables" -ForegroundColor White
Write-Host "2. If Android Studio was just installed, open it and complete setup" -ForegroundColor White
Write-Host "3. Run: flutter doctor --android-licenses (accept all licenses)" -ForegroundColor White
Write-Host "4. Navigate to project: cd karigai_mobile" -ForegroundColor White
Write-Host "5. Install dependencies: flutter pub get" -ForegroundColor White
Write-Host "6. Run the app: flutter run" -ForegroundColor White
Write-Host ""

Write-Host "For VS Code Flutter development:" -ForegroundColor Yellow
Write-Host "1. Open VS Code" -ForegroundColor White
Write-Host "2. Install Flutter extension (Ctrl+Shift+X)" -ForegroundColor White
Write-Host "3. Install Dart extension" -ForegroundColor White
Write-Host ""

Write-Host "Troubleshooting:" -ForegroundColor Yellow
Write-Host "- If 'flutter' command not found, restart PowerShell" -ForegroundColor White
Write-Host "- Run 'flutter doctor' to check for any issues" -ForegroundColor White
Write-Host "- See INSTALLATION_GUIDE.md for detailed instructions" -ForegroundColor White
Write-Host ""

Write-Host "Press any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
