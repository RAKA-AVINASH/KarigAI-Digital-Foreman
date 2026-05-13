# Quick Start Guide - Flutter Installation

## For Windows Users

### Option 1: Automated Installation (Recommended)

1. **Open PowerShell as Administrator**
   - Press `Win + X`
   - Select "Windows PowerShell (Admin)" or "Terminal (Admin)"

2. **Navigate to the project directory**
   ```powershell
   cd "E:\Projects\Kiro Projects\karigai_mobile"
   ```

3. **Run the installation script**
   ```powershell
   .\install_flutter_windows.ps1
   ```

4. **Follow the on-screen instructions**
   - The script will install Git, Chocolatey, Flutter, Chrome, and VS Code
   - Android Studio must be installed manually (link provided)

5. **Restart PowerShell** to refresh environment variables

6. **Verify installation**
   ```powershell
   .\verify_setup.ps1
   ```

### Option 2: Manual Installation

Follow the detailed steps in [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)

## After Installation

### 1. Accept Android Licenses
```powershell
flutter doctor --android-licenses
```
Type 'y' to accept all licenses.

### 2. Install Project Dependencies
```powershell
cd karigai_mobile
flutter pub get
```

### 3. Verify Setup
```powershell
flutter doctor -v
```

All checks should pass (✓) except iOS (not needed on Windows).

### 4. Run the App

**On Android Emulator:**
```powershell
# Start emulator from Android Studio, then:
flutter run
```

**On Chrome (Web):**
```powershell
flutter run -d chrome
```

**On Windows Desktop:**
```powershell
flutter run -d windows
```

## Troubleshooting

### Issue: "flutter: command not found"
**Solution:** 
1. Restart PowerShell
2. Check if Flutter is in PATH:
   ```powershell
   $env:Path
   ```
3. If not, add manually or re-run installation script

### Issue: "Android licenses not accepted"
**Solution:**
```powershell
flutter doctor --android-licenses
```

### Issue: "No devices available"
**Solution:**
1. Start Android emulator from Android Studio
2. Or run on Chrome: `flutter run -d chrome`
3. Or run on Windows: `flutter run -d windows`

### Issue: "Unable to locate Android SDK"
**Solution:**
1. Open Android Studio
2. Go to File → Settings → Appearance & Behavior → System Settings → Android SDK
3. Note the SDK location
4. Create `android/local.properties` with:
   ```properties
   sdk.dir=C:\\Users\\YourUsername\\AppData\\Local\\Android\\Sdk
   ```

## IDE Setup

### Visual Studio Code (Recommended for Flutter)

1. **Install Extensions:**
   - Open VS Code
   - Press `Ctrl+Shift+X`
   - Search and install:
     - Flutter
     - Dart
     - Flutter Widget Snippets
     - Error Lens

2. **Open Project:**
   ```powershell
   code .
   ```

3. **Run App:**
   - Press `F5` or
   - View → Command Palette → "Flutter: Launch Emulator"
   - Then press `F5` again

### Android Studio

1. **Install Plugins:**
   - File → Settings → Plugins
   - Search and install:
     - Flutter
     - Dart

2. **Open Project:**
   - File → Open → Select `karigai_mobile` folder

3. **Run App:**
   - Click the green play button in toolbar
   - Or press `Shift+F10`

## Development Workflow

### Hot Reload (Fast Development)
1. Run the app: `flutter run`
2. Make code changes
3. Press `r` in terminal for hot reload
4. Press `R` for hot restart
5. Press `q` to quit

### Useful Commands

```powershell
# Check Flutter version
flutter --version

# List available devices
flutter devices

# Run on specific device
flutter run -d <device-id>

# Run tests
flutter test

# Analyze code
flutter analyze

# Format code
flutter format .

# Clean build
flutter clean

# Build APK
flutter build apk

# Open DevTools
flutter pub global activate devtools
flutter pub global run devtools
```

## Project Structure Overview

```
karigai_mobile/
├── lib/
│   ├── core/           # Configuration, theme, localization
│   ├── data/           # Models, services, API
│   └── presentation/   # UI screens and widgets
├── test/               # Unit and widget tests
├── android/            # Android-specific code
├── ios/                # iOS-specific code (if needed)
├── web/                # Web-specific code
└── pubspec.yaml        # Dependencies
```

## Next Steps

Once your environment is set up:

1. ✅ **Task 11.1 Complete** - App structure and navigation
2. 🔜 **Task 11.2** - Voice interaction UI components
3. 🔜 **Task 11.3** - Camera and image capture UI
4. 🔜 **Task 11.4** - Document viewing and sharing UI
5. 🔜 **Task 11.5** - Learning module UI components

## Getting Help

- **Flutter Documentation**: https://docs.flutter.dev/
- **Flutter YouTube**: https://www.youtube.com/c/flutterdev
- **Stack Overflow**: https://stackoverflow.com/questions/tagged/flutter
- **Project Documentation**: See [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md)

## Estimated Time

- **Installation**: 1-1.5 hours
- **Setup & Verification**: 15-30 minutes
- **First Run**: 5-10 minutes
- **Total**: ~2 hours

## System Requirements

- Windows 10 or later (64-bit)
- 20 GB free disk space
- 8 GB RAM (16 GB recommended)
- Intel i5 or equivalent processor

## Ready to Code!

Once `flutter doctor` shows all green checkmarks (except iOS on Windows), you're ready to start developing the remaining Flutter tasks!

Happy coding! 🚀
