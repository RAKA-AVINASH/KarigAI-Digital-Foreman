#!/usr/bin/env python3
"""
Test imports for voice engine components.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test importing all voice engine components."""
    try:
        print("Testing core voice engine imports...")
        from app.core.voice_engine import (
            VoiceEngine, AudioData, VoiceProcessingSession, VoiceProcessingError
        )
        print("✓ Voice engine core imports successful")
        
        print("Testing audio preprocessing imports...")
        from app.core.audio_preprocessing import AudioPreprocessor
        print("✓ Audio preprocessing imports successful")
        
        print("Testing voice service imports...")
        # Note: This will fail without database setup, but we can test the import
        try:
            from app.services.voice_service import VoiceService
            print("✓ Voice service imports successful")
        except ImportError as e:
            if "sqlalchemy" in str(e).lower() or "database" in str(e).lower():
                print("⚠ Voice service import requires database dependencies (expected)")
            else:
                raise
        
        print("\n✓ All critical imports successful!")
        return True
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)