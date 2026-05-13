# Flutter Development Environment Setup for Windows

## Overview
This guide will help you install Flutter and all required tools to complete the remaining KarigAI mobile app tasks on Windows.

## Required Software

### 1. Flutter SDK
- **Version Required**: 3.10.0 or higher
- **Download**: https://docs.flutter.dev/get-started/install/windows

### 2. Git for Windows
- **Required for**: Flutter SDK management and version control
- **Download**: https://git-scm.com/download/win

### 3. Android Studio
- **Required for**: Android development, SDK tools, and emulator
- **Download**: https://developer.android.com/studio

### 4. Visual Studio Code (Optional but Recommended)
- **Required for**: Lightweight IDE with Flutter support
- **Download**: https://code.visualstudio.com/

## Installation Steps

### Step 1: Install Git for Windows

1. Download Git from: https://git-scm.com/download/win
2. Run the installer
3. Use default settings (recommended)
4. Verify installation:
   ```powershell
   git --version
   ```

### Step 2: Install Flutter SDK

#### Option A: Using Chocolatey (Recommended)

1. Install Chocolatey (if not already installed):
   ```powershell
   # Run PowerShell as Administrator
   Set-ExecutionPolicy Bypass -Scope Process -Force
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

2. Install Flutter:
   ```powershell
   choco install flutter
   ```

#### Option B: Manual Installation

1. Download Flutter SDK from: https://docs.flutter.dev/get-started/install/windows
2. Extract the zip file to a location (e.g., `C:\src\flutter`)
3. Add Flutter to PATH:
   - Open "Edit the system environment variables"
   - Click "Environment Variables"
   - Under "User variables", find "Path"
   - Click "Edit" → "New"
   - Add: `C:\src\flutter\bin` (or your installation path)
   - Click "OK" on all dialogs

4. Verify installation:
   ```powershell
   flutter --version
   flutter doctor
   ```

### Step 3: Install Android Studio

1. Download Android Studio from: https://developer.android.com/studio
2. Run the installer
3. During installation, ensure these components are selected:
   - Android SDK
   - Android SDK Platform
   - Android Virtual Device (AVD)

4. After installation, open Android Studio:
   - Go to "More Actions" → "SDK Manager"
   - Install the following:
     - Android SDK Platform (API 33 or higher)
     - Android SDK Build-Tools
     - Android SDK Command-line Tools
     - Android Emulator
     - Android SDK Platform-Tools

5. Accept Android licenses:
   ```powershell
   flutter doctor --android-licenses
   ```
   Type 'y' to accept all licenses.

### Step 4: Install Flutter and Dart Plugins

#### For Android Studio:
1. Open Android Studio
2. Go to File → Settings → Plugins
3. Search for "Flutter" and install
4. Search for "Dart" and install
5. Restart Android Studio

#### For VS Code:
1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Flutter" and install
4. Search for "Dart" and install
5. Restart VS Code

### Step 5: Create Android Virtual Device (AVD)

1. Open Android Studio
2. Go to "More Actions" → "Virtual Device Manager"
3. Click "Create Device"
4. Select a device (e.g., Pixel 5)
5. Select a system image (e.g., API 33 - Android 13)
6. Click "Finish"

### Step 6: Verify Installation

Run Flutter Doctor to check your setup:
```powershell
flutter doctor -v
```

Expected output should show:
- ✓ Flutter (Channel stable, version 3.x.x)
- ✓ Android toolchain
- ✓ Android Studio
- ✓ VS Code (if installed)
- ✓ Connected device (if emulator is running)

## Additional Tools for KarigAI Development

### 1. Chrome (for Web Development)
- Download: https://www.google.com/chrome/
- Required for Flutter web development and debugging

### 2. Windows PowerShell 7+ (Optional)
- Download: https://github.com/PowerShell/PowerShell/releases
- Better terminal experience

## Project Setup

### 1. Navigate to Project Directory
```powershell
cd "E:\Projects\Kiro Projects\karigai_mobile"
```

### 2. Install Dependencies
```powershell
flutter pub get
```

### 3. Run Flutter Doctor
```powershell
flutter doctor
```

### 4. Check for Issues
```powershell
flutter analyze
```

### 5. Run Tests
```powershell
flutter test
```

## Running the App

### On Android Emulator:
1. Start the emulator from Android Studio or:
   ```powershell
   flutter emulators
   flutter emulators --launch <emulator_id>
   ```

2. Run the app:
   ```powershell
   flutter run
   ```

### On Physical Device:
1. Enable Developer Options on your Android device
2. Enable USB Debugging
3. Connect device via USB
4. Run:
   ```powershell
   flutter devices
   flutter run
   ```

### On Chrome (Web):
```powershell
flutter run -d chrome
```

## Troubleshooting

### Issue: Flutter command not found
**Solution**: Add Flutter to PATH (see Step 2)

### Issue: Android licenses not accepted
**Solution**: 
```powershell
flutter doctor --android-licenses
```

### Issue: No devices available
**Solution**: 
- Start an emulator from Android Studio
- Or connect a physical device with USB debugging enabled

### Issue: Gradle build failed
**Solution**:
```powershell
cd android
.\gradlew clean
cd ..
flutter clean
flutter pub get
```

### Issue: SDK location not found
**Solution**: Create `android/local.properties` with:
```properties
sdk.dir=C:\\Users\\<YourUsername>\\AppData\\Local\\Android\\Sdk
```

## Environment Variables to Set

Add these to your system PATH:
1. Flutter bin directory: `C:\src\flutter\bin`
2. Android SDK platform-tools: `C:\Users\<YourUsername>\AppData\Local\Android\Sdk\platform-tools`
3. Android SDK tools: `C:\Users\<YourUsername>\AppData\Local\Android\Sdk\tools`

## Recommended VS Code Extensions

1. **Flutter** - Flutter support and debugger
2. **Dart** - Dart language support
3. **Flutter Widget Snippets** - Code snippets
4. **Error Lens** - Inline error display
5. **Bracket Pair Colorizer** - Better bracket visibility
6. **GitLens** - Git integration
7. **Material Icon Theme** - Better file icons

## Recommended Android Studio Plugins

1. **Flutter** - Flutter framework support
2. **Dart** - Dart language support
3. **Flutter Enhancement Suite** - Additional Flutter tools
4. **Rainbow Brackets** - Better bracket visibility
5. **Key Promoter X** - Learn keyboard shortcuts

## Performance Optimization

### Enable Flutter Performance Mode:
```powershell
flutter config --enable-web
flutter config --enable-windows-desktop
flutter config --enable-macos-desktop
flutter config --enable-linux-desktop
```

### Clear Flutter Cache (if needed):
```powershell
flutter clean
flutter pub cache repair
```

## Next Steps After Installation

1. Verify all tools are installed:
   ```powershell
   flutter doctor -v
   ```

2. Navigate to project:
   ```powershell
   cd karigai_mobile
   ```

3. Get dependencies:
   ```powershell
   flutter pub get
   ```

4. Run the app:
   ```powershell
   flutter run
   ```

5. Start developing the remaining tasks!

## Useful Commands Reference

```powershell
# Check Flutter version
flutter --version

# Update Flutter
flutter upgrade

# List available devices
flutter devices

# List available emulators
flutter emulators

# Launch emulator
flutter emulators --launch <emulator_id>

# Run app
flutter run

# Run app in release mode
flutter run --release

# Run app on specific device
flutter run -d <device_id>

# Hot reload (press 'r' in terminal while app is running)
# Hot restart (press 'R' in terminal while app is running)

# Build APK
flutter build apk

# Build App Bundle
flutter build appbundle

# Run tests
flutter test

# Analyze code
flutter analyze

# Format code
flutter format .

# Clean build files
flutter clean

# Get dependencies
flutter pub get

# Update dependencies
flutter pub upgrade

# Check for outdated packages
flutter pub outdated

# Generate code (for build_runner)
flutter pub run build_runner build --delete-conflicting-outputs

# Open DevTools
flutter pub global activate devtools
flutter pub global run devtools
```

## Support Resources

- **Flutter Documentation**: https://docs.flutter.dev/
- **Flutter YouTube Channel**: https://www.youtube.com/c/flutterdev
- **Flutter Community**: https://flutter.dev/community
- **Stack Overflow**: https://stackoverflow.com/questions/tagged/flutter
- **Flutter Discord**: https://discord.gg/flutter

## Estimated Installation Time

- Git: 5 minutes
- Flutter SDK: 10-15 minutes
- Android Studio: 20-30 minutes
- Android SDK components: 15-20 minutes
- IDE plugins: 5 minutes
- Total: ~1-1.5 hours

## Disk Space Requirements

- Flutter SDK: ~2 GB
- Android Studio: ~3 GB
- Android SDK: ~5-10 GB
- Emulator images: ~2-4 GB each
- Total: ~15-20 GB recommended

## System Requirements

- **OS**: Windows 10 or later (64-bit)
- **Disk Space**: 20 GB free
- **RAM**: 8 GB minimum (16 GB recommended)
- **Processor**: Intel i5 or equivalent (i7 recommended)

## Ready to Start?

Once all installations are complete and `flutter doctor` shows no issues, you're ready to continue with the remaining Flutter tasks:
- Task 11.2: Voice interaction UI components
- Task 11.3: Camera and image capture UI
- Task 11.4: Document viewing and sharing UI
- Task 11.5: Learning module UI components

Good luck with your development!
