# KarigAI Mobile App - Setup Guide

## Prerequisites

### Required Software

1. **Flutter SDK** (3.10.0 or higher)
   - Download from: https://flutter.dev/docs/get-started/install
   - Add Flutter to your PATH

2. **Dart SDK** (3.0.0 or higher)
   - Included with Flutter SDK

3. **IDE** (Choose one)
   - Android Studio (recommended)
   - VS Code with Flutter extension
   - IntelliJ IDEA

4. **Platform-Specific Tools**

   **For Android Development:**
   - Android Studio
   - Android SDK (API level 21 or higher)
   - Android Emulator or physical device

   **For iOS Development (macOS only):**
   - Xcode 14.0 or higher
   - CocoaPods
   - iOS Simulator or physical device

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd karigai_mobile
```

### 2. Install Flutter Dependencies

```bash
flutter pub get
```

### 3. Verify Flutter Installation

```bash
flutter doctor
```

Fix any issues reported by `flutter doctor` before proceeding.

### 4. Configure Backend API

Edit `lib/core/app_config.dart` and update the API base URL:

```dart
static const String baseUrl = 'YOUR_BACKEND_URL';
```

For local development:
```dart
static const String baseUrl = 'http://localhost:8000';
```

For Android emulator accessing local backend:
```dart
static const String baseUrl = 'http://10.0.2.2:8000';
```

### 5. Set Up Assets

Create the following directories if they don't exist:

```bash
mkdir -p assets/images
mkdir -p assets/icons
mkdir -p assets/animations
mkdir -p assets/audio
mkdir -p assets/fonts
```

Add placeholder assets or your actual assets to these directories.

### 6. Generate Code (if needed)

If you're using code generation for models:

```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

## Running the App

### Development Mode

**Android:**
```bash
flutter run
```

**iOS:**
```bash
flutter run
```

**Specific Device:**
```bash
# List available devices
flutter devices

# Run on specific device
flutter run -d <device-id>
```

### Debug Mode with Hot Reload

1. Start the app in debug mode
2. Make code changes
3. Press `r` in terminal for hot reload
4. Press `R` for hot restart
5. Press `q` to quit

## Building for Production

### Android APK

```bash
# Build APK
flutter build apk --release

# Build App Bundle (recommended for Play Store)
flutter build appbundle --release
```

Output location: `build/app/outputs/flutter-apk/app-release.apk`

### iOS IPA

```bash
# Build for iOS
flutter build ios --release

# Create IPA (requires Xcode)
# Open ios/Runner.xcworkspace in Xcode
# Product > Archive > Distribute App
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
API_BASE_URL=https://api.karigai.com
API_VERSION=v1
ENABLE_ANALYTICS=true
LOG_LEVEL=info
```

### Firebase Configuration (Optional)

If using Firebase:

1. Create a Firebase project
2. Download `google-services.json` (Android) and `GoogleService-Info.plist` (iOS)
3. Place files in appropriate directories:
   - Android: `android/app/google-services.json`
   - iOS: `ios/Runner/GoogleService-Info.plist`

### API Keys

For services requiring API keys, add them to:

**Android:** `android/local.properties`
```properties
MAPS_API_KEY=your_maps_api_key
```

**iOS:** `ios/Flutter/Release.xcconfig` and `ios/Flutter/Debug.xcconfig`
```
MAPS_API_KEY=your_maps_api_key
```

## Development Workflow

### 1. Code Style

Follow Flutter style guide:
```bash
# Format code
flutter format .

# Analyze code
flutter analyze
```

### 2. Linting

The project uses strict linting rules defined in `analysis_options.yaml`.

Fix linting issues:
```bash
dart fix --apply
```

### 3. Testing

Run all tests:
```bash
flutter test
```

Run specific test:
```bash
flutter test test/widget_test.dart
```

Run with coverage:
```bash
flutter test --coverage
```

### 4. Integration Testing

```bash
flutter test integration_test
```

## Troubleshooting

### Common Issues

**1. Gradle Build Failed (Android)**
```bash
cd android
./gradlew clean
cd ..
flutter clean
flutter pub get
```

**2. CocoaPods Issues (iOS)**
```bash
cd ios
pod deintegrate
pod install
cd ..
flutter clean
flutter pub get
```

**3. Version Conflicts**
```bash
flutter clean
flutter pub cache repair
flutter pub get
```

**4. Hot Reload Not Working**
- Restart the app with `R`
- Check for syntax errors
- Ensure you're not modifying main() or initState()

**5. Device Not Detected**
```bash
# Android
adb devices
adb kill-server
adb start-server

# iOS
xcrun simctl list devices
```

## IDE Setup

### VS Code

Install extensions:
1. Flutter
2. Dart
3. Flutter Widget Snippets
4. Error Lens

Recommended settings (`.vscode/settings.json`):
```json
{
  "dart.flutterSdkPath": "/path/to/flutter",
  "editor.formatOnSave": true,
  "editor.rulers": [80],
  "dart.lineLength": 80
}
```

### Android Studio

1. Install Flutter plugin
2. Install Dart plugin
3. Configure Flutter SDK path
4. Enable Dart Analysis

## Performance Profiling

### Profile Mode

```bash
flutter run --profile
```

### Performance Overlay

In debug mode, press `P` to toggle performance overlay.

### DevTools

```bash
flutter pub global activate devtools
flutter pub global run devtools
```

## Debugging

### Debug Console

Use `print()` or `debugPrint()` for logging:
```dart
debugPrint('Debug message: $variable');
```

### Flutter Inspector

In VS Code: View > Command Palette > "Flutter: Open DevTools"

### Network Debugging

Use Charles Proxy or similar tools to inspect network traffic.

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/flutter.yml`:

```yaml
name: Flutter CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.10.0'
      - run: flutter pub get
      - run: flutter analyze
      - run: flutter test
      - run: flutter build apk
```

## Additional Resources

- [Flutter Documentation](https://flutter.dev/docs)
- [Dart Language Tour](https://dart.dev/guides/language/language-tour)
- [Material Design Guidelines](https://material.io/design)
- [Flutter Cookbook](https://flutter.dev/docs/cookbook)
- [Effective Dart](https://dart.dev/guides/language/effective-dart)

## Support

For issues and questions:
- Check existing GitHub issues
- Create a new issue with detailed description
- Include Flutter doctor output
- Provide error logs and stack traces

## Next Steps

After setup:
1. Review the [Architecture Documentation](ARCHITECTURE.md)
2. Explore the codebase structure
3. Run the app and test features
4. Read the [Contributing Guidelines](CONTRIBUTING.md)
5. Start developing!
