# KarigAI Mobile App

The Vernacular Digital Foreman - A voice-first, multimodal mobile application for India's informal workforce.

## Project Structure

```
lib/
├── core/                           # Core functionality and configuration
│   ├── constants/                  # App-wide constants
│   │   └── app_constants.dart
│   ├── database/                   # Local database management
│   │   └── app_database.dart
│   ├── localization/               # Internationalization
│   │   └── app_localizations.dart
│   ├── services/                   # Core services
│   │   └── service_locator.dart
│   ├── theme/                      # App theming
│   │   └── app_theme.dart
│   └── app_config.dart             # App configuration
│
├── data/                           # Data layer
│   └── services/                   # API and data services
│       ├── api_service.dart
│       ├── document_service.dart
│       ├── offline_service.dart
│       ├── vision_service.dart
│       └── voice_service.dart
│
├── presentation/                   # UI layer
│   ├── routes/                     # Navigation and routing
│   │   └── app_router.dart
│   ├── screens/                    # App screens
│   │   ├── camera/
│   │   │   └── camera_screen.dart
│   │   ├── documents/
│   │   │   └── document_list_screen.dart
│   │   ├── home/
│   │   │   └── home_screen.dart
│   │   ├── learning/
│   │   │   └── learning_screen.dart
│   │   ├── profile/
│   │   │   └── profile_screen.dart
│   │   └── voice/
│   │       └── voice_input_screen.dart
│   └── widgets/                    # Reusable widgets
│       ├── accessibility_wrapper.dart
│       ├── app_drawer.dart
│       ├── bottom_nav_bar.dart
│       ├── error_widget.dart
│       ├── loading_widget.dart
│       └── responsive_layout.dart
│
└── main.dart                       # App entry point
```

## Features

### Core Features
- **Voice Input**: Voice-to-invoice system with local dialect support
- **Visual Analysis**: Equipment identification and pattern recognition
- **Document Management**: Professional invoice and document generation
- **Learning Modules**: Micro-courses and skill development
- **Profile Management**: User preferences and settings

### Technical Features
- **Responsive Design**: Adapts to different screen sizes (mobile, tablet, desktop)
- **Accessibility**: Enhanced accessibility features for diverse users
- **Offline Support**: Core features work without internet connectivity
- **Multilingual**: Support for 7+ Indian languages
- **Material Design 3**: Modern UI with Material You theming

## Architecture

### Navigation
- **go_router**: Declarative routing with deep linking support
- **Bottom Navigation**: Quick access to main features
- **Drawer Navigation**: Complete app navigation menu

### State Management
- **Riverpod**: Reactive state management
- **Provider**: Dependency injection

### Local Storage
- **Hive**: Fast key-value storage
- **SQLite**: Structured data storage
- **SharedPreferences**: Simple key-value pairs

### Networking
- **Dio**: HTTP client with interceptors
- **WebSocket**: Real-time communication

## Accessibility Features

1. **Screen Reader Support**: Semantic labels for all interactive elements
2. **High Contrast Mode**: Automatic detection and adaptation
3. **Text Scaling**: Support for system text size preferences
4. **Touch Targets**: Minimum 48x48 dp touch targets
5. **Voice Feedback**: Audio confirmation for actions

## Responsive Design

The app adapts to three screen size categories:
- **Mobile**: < 600dp width
- **Tablet**: 600-1200dp width
- **Desktop**: > 1200dp width

## Getting Started

### Prerequisites
- Flutter SDK 3.10.0 or higher
- Dart SDK 3.0.0 or higher
- Android Studio / VS Code with Flutter extensions

### Installation

1. Install dependencies:
```bash
flutter pub get
```

2. Run the app:
```bash
flutter run
```

3. Build for production:
```bash
# Android
flutter build apk --release

# iOS
flutter build ios --release
```

## Configuration

### API Endpoint
Update the API base URL in `lib/core/app_config.dart`:
```dart
static const String baseUrl = 'YOUR_API_URL';
```

### Supported Languages
Configure supported locales in `lib/core/app_config.dart`:
```dart
static const List<Locale> supportedLocales = [
  Locale('en', 'US'),
  Locale('hi', 'IN'),
  // Add more locales
];
```

## Testing

Run tests:
```bash
flutter test
```

Run integration tests:
```bash
flutter test integration_test
```

## Performance Optimization

- **Image Caching**: Automatic caching of network images
- **Lazy Loading**: Deferred loading of heavy components
- **Code Splitting**: Route-based code splitting
- **Asset Optimization**: Compressed images and assets

## Offline Functionality

The app provides offline support for:
- Voice recognition (basic)
- Document generation
- Previously downloaded learning modules
- Cached equipment information

Data syncs automatically when connectivity is restored.

## Contributing

1. Follow the existing code structure
2. Use meaningful variable and function names
3. Add comments for complex logic
4. Write tests for new features
5. Follow Flutter style guide

## License

Copyright © 2024 KarigAI. All rights reserved.
