# Running KarigAI in Mobile Emulator View

## Option 1: Chrome with Mobile Device Emulation (Recommended - Works Now!)

This is the easiest way to see your app in a mobile view without installing Android Studio.

### Steps:

1. **Run the app in Chrome:**
   ```powershell
   cd karigai_mobile
   flutter run -d chrome
   ```

2. **Open Chrome DevTools:**
   - Press `F12` or `Ctrl+Shift+I` in Chrome
   - Or right-click and select "Inspect"

3. **Toggle Device Toolbar:**
   - Press `Ctrl+Shift+M`
   - Or click the device icon in DevTools toolbar (looks like a phone/tablet)

4. **Select a Mobile Device:**
   - Choose from preset devices:
     - iPhone 12 Pro
     - iPhone SE
     - Pixel 5
     - Samsung Galaxy S20
     - iPad Air
   - Or create custom dimensions

5. **Features Available:**
   - ✅ Responsive design testing
   - ✅ Touch simulation
   - ✅ Device rotation
   - ✅ Network throttling
   - ✅ Different screen sizes
   - ✅ Hot reload (press 'r' in terminal)

### Quick Command:
```powershell
# Navigate to project
cd karigai_mobile

# Run in Chrome
flutter run -d chrome

# Then press F12 and Ctrl+Shift+M in Chrome
```

---

## Option 2: Flutter Web with Custom Window Size

Run Flutter with a specific mobile window size:

```powershell
cd karigai_mobile
flutter run -d chrome --web-browser-flag="--window-size=375,812"
```

Common mobile sizes:
- iPhone 12 Pro: `--window-size=390,844`
- iPhone SE: `--window-size=375,667`
- Pixel 5: `--window-size=393,851`
- Samsung Galaxy S20: `--window-size=360,800`

---

## Option 3: Android Emulator (Requires Android Studio)

For a true Android emulator experience:

### Prerequisites:
1. Install Android Studio from: https://developer.android.com/studio
2. Install Android SDK components
3. Create an Android Virtual Device (AVD)

### Steps:

1. **Open Android Studio**
2. **Go to Device Manager:**
   - Tools → Device Manager
   - Or click the device icon in toolbar

3. **Create Virtual Device:**
   - Click "Create Device"
   - Select device (e.g., Pixel 5)
   - Download system image (API 33 recommended)
   - Click "Finish"

4. **Start Emulator:**
   - Click the play button next to your device
   - Wait for emulator to boot

5. **Run Flutter App:**
   ```powershell
   cd karigai_mobile
   flutter devices  # Should show your emulator
   flutter run      # Will automatically use emulator
   ```

### Advantages:
- ✅ True Android environment
- ✅ Test Android-specific features
- ✅ Camera simulation
- ✅ GPS simulation
- ✅ Sensors simulation
- ✅ Google Play Services

### Disadvantages:
- ❌ Requires ~10GB disk space
- ❌ Slower than web
- ❌ Requires Android Studio installation

---

## Option 4: Windows Desktop with Mobile Layout

Run as Windows app with mobile-sized window:

```powershell
cd karigai_mobile
flutter run -d windows
```

Then resize the window to mobile dimensions (375x812 pixels).

---

## Option 5: Browser Extensions (Alternative)

Install browser extensions for mobile testing:

### Responsive Viewer (Chrome Extension)
- Install from Chrome Web Store
- Shows multiple device views simultaneously
- Free and easy to use

### Mobile Simulator (Chrome Extension)
- Simulates various mobile devices
- Includes touch gestures
- Network throttling

---

## Recommended Workflow

### For Development (Best Experience):

1. **Start with Chrome DevTools:**
   ```powershell
   cd karigai_mobile
   flutter run -d chrome
   ```
   - Press `F12` → `Ctrl+Shift+M`
   - Select "iPhone 12 Pro" or "Pixel 5"
   - Develop and test with hot reload

2. **Test on Android Emulator (Optional):**
   - Once Android Studio is installed
   - Test Android-specific features
   - Verify performance

3. **Test on Real Device (Best):**
   - Connect Android phone via USB
   - Enable USB debugging
   - Run: `flutter run`

---

## Quick Start Guide

### Immediate Testing (No Additional Setup):

```powershell
# 1. Navigate to project
cd karigai_mobile

# 2. Run in Chrome
flutter run -d chrome

# 3. In Chrome:
#    - Press F12 (open DevTools)
#    - Press Ctrl+Shift+M (toggle device toolbar)
#    - Select "iPhone 12 Pro" from dropdown
#    - Enjoy mobile view!
```

### What You'll See:
- ✅ Home screen with feature cards
- ✅ Navigation drawer (hamburger menu)
- ✅ Bottom navigation bar
- ✅ Voice, Camera, Documents, Learning, Profile screens
- ✅ Responsive layout adapting to mobile size
- ✅ Touch-friendly UI elements

### Hot Reload:
- Make code changes
- Press 'r' in terminal
- See changes instantly!

---

## Comparison Table

| Method | Setup Time | Realism | Performance | Best For |
|--------|------------|---------|-------------|----------|
| Chrome DevTools | 0 min | Good | Excellent | Daily development |
| Custom Window Size | 0 min | Fair | Excellent | Quick testing |
| Android Emulator | 30-60 min | Excellent | Good | Android testing |
| Windows Desktop | 0 min | Fair | Excellent | Desktop testing |
| Real Device | 5 min | Perfect | Excellent | Final testing |

---

## Troubleshooting

### Chrome DevTools not showing mobile view:
- Make sure you pressed `Ctrl+Shift+M`
- Click the device icon in DevTools toolbar
- Refresh the page

### App not responsive in mobile view:
- Check if responsive widgets are used
- Verify MediaQuery is working
- Test different device sizes

### Emulator not showing in flutter devices:
- Make sure emulator is running
- Run: `flutter devices`
- Restart emulator if needed

---

## Next Steps

1. **Try it now:**
   ```powershell
   cd karigai_mobile
   flutter run -d chrome
   ```
   Then press `F12` and `Ctrl+Shift+M`

2. **Explore the app:**
   - Navigate between screens
   - Test responsive design
   - Try different device sizes

3. **Make changes:**
   - Edit any screen file
   - Press 'r' for hot reload
   - See changes instantly

4. **Optional: Install Android Studio**
   - For true Android emulator
   - Follow INSTALLATION_GUIDE.md

---

## Screenshots Guide

To take screenshots of your mobile view:

1. **In Chrome DevTools:**
   - Open DevTools (`F12`)
   - Toggle device toolbar (`Ctrl+Shift+M`)
   - Click the three dots menu
   - Select "Capture screenshot"

2. **Or use Windows Snipping Tool:**
   - Press `Win+Shift+S`
   - Select area to capture

---

**Recommendation:** Start with Chrome DevTools mobile emulation. It's instant, works great, and supports hot reload!
