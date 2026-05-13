# KarigAI Mobile App Architecture

## Overview

The KarigAI mobile app follows a clean architecture pattern with clear separation of concerns across three main layers: Core, Data, and Presentation.

## Architecture Layers

### 1. Core Layer (`lib/core/`)

The core layer contains fundamental app configuration, utilities, and services that are used throughout the application.

#### Components:

**app_config.dart**
- Application-wide configuration
- API endpoints and timeouts
- Supported languages and locales
- Performance thresholds

**constants/app_constants.dart**
- Static constants and enums
- Route names
- Asset paths
- Trade types and language codes

**database/app_database.dart**
- SQLite database initialization
- Schema definitions for:
  - Users
  - Voice sessions
  - Documents
  - Learning progress
  - Equipment cache
  - Offline queue

**localization/app_localizations.dart**
- Internationalization support
- Localized strings for UI
- Support for 7+ Indian languages
- Fallback to English for missing translations

**services/service_locator.dart**
- Dependency injection
- Service initialization
- Singleton pattern for services
- Lifecycle management

**theme/app_theme.dart**
- Material Design 3 theming
- Light and dark themes
- Color schemes
- Typography and component styles

### 2. Data Layer (`lib/data/`)

The data layer handles all data operations including API calls, local storage, and data transformations.

#### Services:

**api_service.dart**
- HTTP client wrapper
- Request/response interceptors
- Error handling
- Authentication

**voice_service.dart**
- Voice recording management
- Speech-to-text integration
- Audio preprocessing
- Language detection

**vision_service.dart**
- Image capture and processing
- Equipment identification
- Pattern analysis
- OCR functionality

**document_service.dart**
- PDF generation
- Document storage
- WhatsApp integration
- Document sharing

**offline_service.dart**
- Offline data management
- Sync queue management
- Cache management
- Conflict resolution

### 3. Presentation Layer (`lib/presentation/`)

The presentation layer contains all UI components, screens, and navigation logic.

#### Routes (`routes/`)

**app_router.dart**
- Declarative routing with go_router
- Route definitions
- Error handling
- Deep linking support
- Navigation helpers

#### Screens (`screens/`)

**home/home_screen.dart**
- Main dashboard
- Feature cards for quick access
- Navigation to all main features
- User greeting and status

**voice/voice_input_screen.dart**
- Voice recording interface
- Real-time audio visualization
- Transcription display
- Language selection

**camera/camera_screen.dart**
- Camera interface
- Image capture and preview
- Gallery selection
- Analysis results display

**documents/document_list_screen.dart**
- Document listing
- Document preview
- Sharing options
- Document management (view, share, delete)

**learning/learning_screen.dart**
- Learning module listing
- Progress tracking
- Course recommendations
- Category filtering

**profile/profile_screen.dart**
- User profile information
- Settings and preferences
- Language selection
- Trade type configuration
- Logout functionality

#### Widgets (`widgets/`)

**responsive_layout.dart**
- Responsive design utilities
- Screen size detection
- Adaptive layouts for mobile/tablet/desktop
- Responsive padding and grids

**accessibility_wrapper.dart**
- Accessibility enhancements
- Semantic labels
- Screen reader support
- High contrast mode support
- Minimum touch target sizes

**app_drawer.dart**
- Navigation drawer
- User profile header
- Menu items
- About dialog

**bottom_nav_bar.dart**
- Bottom navigation bar
- Active route detection
- Navigation helpers

**loading_widget.dart**
- Loading indicators
- Shimmer effects
- Overlay loading
- Progress messages

**error_widget.dart**
- Error display
- Empty states
- Network error handling
- Offline mode indicator
- Retry functionality

## Design Patterns

### 1. Service Locator Pattern
- Centralized service management
- Lazy initialization
- Singleton services
- Easy testing and mocking

### 2. Repository Pattern
- Data abstraction
- Multiple data sources (API, local DB, cache)
- Consistent data access interface

### 3. Provider Pattern (Riverpod)
- Reactive state management
- Dependency injection
- Testable architecture
- Compile-time safety

### 4. Factory Pattern
- Service creation
- Configuration-based instantiation
- Flexible service switching

## Navigation Flow

```
Home Screen
├── Voice Input Screen
│   └── Voice Recording → Transcription → Invoice Generation
├── Camera Screen
│   └── Image Capture → Analysis → Results
├── Documents Screen
│   └── Document List → Document View → Share
├── Learning Screen
│   └── Course List → Course Detail → Progress Tracking
└── Profile Screen
    └── Settings → Language → Trade Type → Logout
```

## Data Flow

### Voice-to-Invoice Flow
1. User taps record button
2. VoiceService captures audio
3. Audio sent to backend API
4. Transcription received
5. Invoice data extracted
6. DocumentService generates PDF
7. Document saved locally
8. Share options presented

### Image Analysis Flow
1. User captures/selects image
2. VisionService processes image
3. Image sent to backend API
4. Analysis results received
5. Results displayed with confidence scores
6. Troubleshooting steps provided
7. Results cached for offline access

### Offline Sync Flow
1. User performs action offline
2. Action queued in offline_queue table
3. Connectivity restored
4. OfflineService processes queue
5. Actions synced to backend
6. Local data updated
7. Queue cleared

## State Management

### Local State
- Widget-level state using StatefulWidget
- Form state management
- UI interaction state

### App State (Riverpod)
- User authentication state
- Language preferences
- Offline mode status
- Network connectivity

### Persistent State
- SharedPreferences for simple key-value pairs
- Hive for complex objects
- SQLite for structured data

## Error Handling

### Network Errors
- Automatic retry with exponential backoff
- Offline mode fallback
- User-friendly error messages
- Connectivity monitoring

### Validation Errors
- Input validation
- Form validation
- Data integrity checks
- User feedback

### System Errors
- Crash reporting
- Error logging
- Graceful degradation
- Recovery mechanisms

## Performance Optimization

### Image Optimization
- Automatic compression
- Lazy loading
- Caching with expiry
- Thumbnail generation

### Network Optimization
- Request batching
- Response caching
- Compression
- Connection pooling

### UI Optimization
- Widget recycling
- Lazy rendering
- Debouncing user input
- Efficient rebuilds

## Accessibility Features

### Screen Reader Support
- Semantic labels on all interactive elements
- Proper focus management
- Announcement of state changes

### Visual Accessibility
- High contrast mode support
- Scalable text (respects system settings)
- Color-blind friendly palette
- Clear visual hierarchy

### Motor Accessibility
- Large touch targets (minimum 48x48 dp)
- Gesture alternatives
- Voice control support
- Keyboard navigation (desktop)

## Testing Strategy

### Unit Tests
- Service logic
- Data transformations
- Utility functions
- Validation logic

### Widget Tests
- UI components
- User interactions
- State changes
- Navigation

### Integration Tests
- End-to-end workflows
- API integration
- Database operations
- Offline functionality

## Security Considerations

### Data Protection
- Encrypted local storage
- Secure API communication (HTTPS)
- Token-based authentication
- Sensitive data masking

### Privacy
- User consent management
- Data anonymization
- GDPR compliance
- Data deletion support

## Future Enhancements

### Planned Features
1. Biometric authentication
2. Voice commands for navigation
3. AR-based equipment identification
4. Collaborative features
5. Advanced analytics dashboard

### Technical Improvements
1. GraphQL API integration
2. Background sync optimization
3. Advanced caching strategies
4. Performance monitoring
5. A/B testing framework
