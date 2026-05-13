# KarigAI Application Refinement Tasks

## Status: Ready for Implementation
**Created**: 2026-02-10  
**Purpose**: Fix functionality issues in mobile app features

---

## 1. Voice Input / Speech-to-Text Refinement

### Issue
Voice input returns pre-saved/mock text instead of actual transcription from user speech.

### Root Cause
Voice input screen uses placeholder implementation instead of connecting to backend API.

### Tasks
- [x] 1.1 Connect voice input to backend `/api/v1/voice/transcribe` endpoint
- [x] 1.2 Implement actual microphone access using `record` package
- [x] 1.3 Remove mock/placeholder transcription text
- [x] 1.4 Add proper error handling for microphone permissions
- [x] 1.5 Test with real audio input and verify backend connection
- [x] 1.6 Add loading states during transcription
- [x] 1.7 Handle web platform microphone permissions

### Files to Modify
- `karigai_mobile/lib/presentation/screens/voice/voice_input_screen.dart`
- `karigai_mobile/lib/data/services/voice_api_service.dart`
- `karigai_mobile/lib/presentation/widgets/voice_input_widget.dart`

### Acceptance Criteria
- User can record audio using microphone
- Audio is sent to backend for transcription
- Real transcription is displayed (not mock text)
- Proper error messages for permission denials
- Works on web platform (Chrome)

---

## 2. Camera / Vision Recognition Refinement

### Issue
Camera fails to start with torch-related errors. Vision recognition not functional.

### Root Cause
Camera implementation has initialization issues and torch control problems. Not connected to backend.

### Tasks
- [ ] 2.1 Fix camera initialization in `camera_screen.dart`
- [ ] 2.2 Remove or fix torch/flashlight control (not essential for web)
- [ ] 2.3 Implement proper camera permissions handling
- [ ] 2.4 Connect camera capture to backend `/api/v1/vision/analyze` endpoint
- [ ] 2.5 Add fallback for web (file upload instead of camera)
- [ ] 2.6 Test image capture and backend analysis
- [ ] 2.7 Display analysis results properly
- [ ] 2.8 Add loading states during analysis

### Files to Modify
- `karigai_mobile/lib/presentation/screens/camera/camera_screen.dart`
- `karigai_mobile/lib/presentation/widgets/camera_widget.dart`
- `karigai_mobile/lib/data/services/vision_api_service.dart`

### Acceptance Criteria
- Camera initializes without errors
- User can capture images (or upload on web)
- Images are sent to backend for analysis
- Analysis results are displayed
- Proper error handling for permissions
- Web fallback works (file picker)

---

## 3. Document Access Refinement

### Issue
Documents are shown in list but not accessible/viewable. Shows mock data.

### Root Cause
Document list shows placeholder data, not connected to backend. Document viewer not implemented.

### Tasks
- [ ] 3.1 Connect document list to backend `/api/v1/documents` endpoint
- [ ] 3.2 Implement document download/viewing functionality
- [ ] 3.3 Add proper document URL handling
- [ ] 3.4 Fix document viewer widget to display PDFs
- [ ] 3.5 Add error handling for missing/inaccessible documents
- [ ] 3.6 Implement document refresh functionality
- [ ] 3.7 Add empty state when no documents exist
- [ ] 3.8 Add loading states during document fetch

### Files to Modify
- `karigai_mobile/lib/presentation/screens/documents/document_list_screen.dart`
- `karigai_mobile/lib/presentation/widgets/document_viewer_widget.dart`
- `karigai_mobile/lib/data/services/document_api_service.dart`

### Acceptance Criteria
- Document list loads from backend
- Documents can be opened and viewed
- PDF viewer displays content correctly
- Download/share functionality works
- Empty state handled properly
- Error messages for inaccessible documents

---

## 4. Learning / Courses Module Refinement

### Issue
Courses screen doesn't open or load. Module appears broken.

### Root Cause
Learning screen has initialization errors or data loading issues. Not connected to backend.

### Tasks
- [ ] 4.1 Debug learning screen initialization errors
- [ ] 4.2 Connect to backend `/api/v1/learning/courses` endpoint
- [ ] 4.3 Implement course list loading and display
- [ ] 4.4 Add proper loading states and error handling
- [ ] 4.5 Test course navigation and content display
- [ ] 4.6 Implement course progress tracking
- [ ] 4.7 Add empty state for no courses
- [ ] 4.8 Fix micro-SOP widget display

### Files to Modify
- `karigai_mobile/lib/presentation/screens/learning/learning_screen.dart`
- `karigai_mobile/lib/data/services/learning_api_service.dart`
- `karigai_mobile/lib/presentation/widgets/micro_sop_widget.dart`
- `karigai_mobile/lib/presentation/widgets/course_recommendation_widget.dart`

### Acceptance Criteria
- Learning screen opens without errors
- Course list loads from backend
- Courses can be opened and viewed
- Course content displays properly
- Progress tracking works
- Navigation between modules works

---

## Implementation Priority

### Phase 1: Core Connectivity (Week 1)
**Priority**: Critical
- Fix service initialization
- Ensure all screens can communicate with backend
- Add proper error handling and loading states
- Test basic API connectivity

### Phase 2: Voice & Documents (Week 2)
**Priority**: High
- Voice input with real microphone access
- Document viewing and access
- These have no hardware dependencies on web

### Phase 3: Camera & Learning (Week 3)
**Priority**: High
- Camera/vision with proper initialization
- Learning module loading
- More complex due to platform differences

### Phase 4: Polish & Testing (Week 4)
**Priority**: Medium
- Improve error messages
- Add user feedback for permissions
- Test all features end-to-end
- Performance optimization

---

## Technical Requirements

### Backend Connection
- **Base URL**: `http://localhost:8000`
- **API Version**: `v1`
- **Authentication**: None (add if needed later)
- **Timeout**: 30 seconds for API calls

### Required Packages
Already installed:
- `camera`: For camera access
- `record`: For audio recording
- `permission_handler`: For permissions
- `dio`: For HTTP requests

May need to add:
- `flutter_pdfview` or `syncfusion_flutter_pdfviewer`: For PDF viewing
- `file_picker`: For web file uploads

### Web Platform Limitations
- Camera access works differently (use file picker as fallback)
- Microphone requires HTTPS in production (localhost OK for dev)
- Some native features need web-specific implementations
- Torch/flashlight not available on web

---

## Testing Checklist

### Voice Input Testing
- [ ] Microphone permission requested
- [ ] Audio recording works
- [ ] Audio sent to backend successfully
- [ ] Transcription received and displayed
- [ ] Error handling works (permission denied, network error)
- [ ] Loading states display correctly
- [ ] Works on Chrome web browser

### Camera/Vision Testing
- [ ] Camera permission requested
- [ ] Camera preview displays (or file picker on web)
- [ ] Image capture works
- [ ] Image sent to backend successfully
- [ ] Analysis results received and displayed
- [ ] Web fallback (file upload) works
- [ ] Error handling works
- [ ] Loading states display correctly

### Document Testing
- [ ] Document list loads from backend
- [ ] Documents display in list
- [ ] Documents can be opened
- [ ] PDF viewer displays content
- [ ] Download/share functionality works
- [ ] Empty state handled properly
- [ ] Error handling works
- [ ] Loading states display correctly

### Learning Testing
- [ ] Learning screen opens without errors
- [ ] Course list loads from backend
- [ ] Courses display in list
- [ ] Courses can be opened
- [ ] Course content displays
- [ ] Progress tracking works
- [ ] Navigation between modules works
- [ ] Error handling works
- [ ] Loading states display correctly

---

## Known Issues & Limitations

### Current Status
- ✅ App loads and displays UI
- ✅ Backend running at localhost:8000
- ✅ Basic navigation works
- ✅ Service locator initialized
- ❌ Core features use mock data
- ❌ Backend integration incomplete
- ❌ Permissions not properly handled
- ❌ Error states not implemented

### Platform Limitations
1. **Web Platform**: Camera and microphone have browser limitations
2. **Mock Data**: Most screens show placeholder data
3. **Error Handling**: Minimal error handling implemented
4. **Permissions**: Permission requests not properly implemented
5. **Loading States**: Many screens lack loading indicators

### Recommendations
1. **Start Simple**: Begin with voice input (easiest to fix)
2. **Then Documents**: No hardware dependencies
3. **Then Learning**: Similar to documents
4. **Finally Camera**: Most complex due to web limitations
5. **Test Incrementally**: Test each feature as you fix it

---

## Success Criteria

Refinement is complete when:

1. ✅ **Voice Input**: Captures real audio and returns actual transcription
2. ✅ **Camera**: Can capture images (or upload files on web) and get analysis
3. ✅ **Documents**: Load from backend and can be viewed properly
4. ✅ **Learning**: Loads courses and displays content correctly
5. ✅ **Error Handling**: All features have proper error handling
6. ✅ **User Feedback**: Clear feedback for permissions and errors
7. ✅ **Loading States**: All async operations show loading indicators
8. ✅ **Web Compatibility**: All features work on Chrome web browser

---

## Notes

### Development Environment
- **Backend**: Docker at http://localhost:8000
- **Frontend**: Flutter web at http://localhost:8081
- **Browser**: Chrome (recommended for testing)
- **Platform**: Windows with PowerShell

### API Endpoints Available
- `/api/v1/voice/transcribe` - Voice transcription
- `/api/v1/vision/analyze` - Image analysis
- `/api/v1/documents` - Document management
- `/api/v1/learning/courses` - Course management
- `/health` - Health check

### Next Steps
1. Review this document
2. Start with Phase 1 (Core Connectivity)
3. Work through tasks sequentially
4. Test each feature as you complete it
5. Update task checkboxes as you progress

---

**Last Updated**: 2026-02-10  
**Status**: Ready for Implementation  
**Estimated Effort**: 4 weeks (1 week per phase)
