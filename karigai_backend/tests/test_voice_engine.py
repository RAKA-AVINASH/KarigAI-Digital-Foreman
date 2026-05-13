"""
Unit tests for Voice Engine components.

Tests the VoiceEngine abstract interface, AudioData model,
and audio preprocessing utilities.
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from app.core.voice_engine import (
    VoiceEngine, AudioData, VoiceProcessingSession, VoiceProcessingError
)
from app.core.audio_preprocessing import AudioPreprocessor


class TestAudioData:
    """Test AudioData model functionality."""
    
    def test_audio_data_creation(self):
        """Test AudioData object creation with required fields."""
        audio_bytes = b"fake_audio_data"
        audio_data = AudioData(
            audio_bytes=audio_bytes,
            sample_rate=16000,
            channels=1,
            duration=2.0,
            format="wav",
            bit_depth=16
        )
        
        assert audio_data.audio_bytes == audio_bytes
        assert audio_data.sample_rate == 16000
        assert audio_data.channels == 1
        assert audio_data.duration == 2.0
        assert audio_data.format == "wav"
        assert audio_data.bit_depth == 16
        assert audio_data.preprocessed is False
        assert audio_data.noise_level == 0.0
    
    def test_audio_data_from_numpy(self):
        """Test creating AudioData from numpy array."""
        # Create test audio array (1 second of 440Hz sine wave)
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_array = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        
        audio_data = AudioData.from_numpy(
            audio_array, sample_rate, channels=1, format="wav"
        )
        
        assert audio_data.sample_rate == sample_rate
        assert audio_data.channels == 1
        assert audio_data.format == "wav"
        assert abs(audio_data.duration - duration) < 0.1
        assert len(audio_data.audio_bytes) > 0
    
    def test_audio_data_to_numpy(self):
        """Test converting AudioData to numpy array."""
        # Create simple audio data
        sample_rate = 8000
        samples = 1000
        audio_array = np.random.randint(-32768, 32767, samples, dtype=np.int16)
        
        audio_data = AudioData.from_numpy(audio_array, sample_rate)
        converted_array = audio_data.to_numpy()
        
        assert converted_array.dtype == np.int16
        assert len(converted_array) == samples
        np.testing.assert_array_equal(audio_array, converted_array)


class TestVoiceProcessingSession:
    """Test VoiceProcessingSession model functionality."""
    
    def test_voice_session_creation(self):
        """Test VoiceProcessingSession object creation."""
        audio_data = AudioData(
            audio_bytes=b"test",
            sample_rate=16000,
            channels=1,
            duration=1.0,
            format="wav"
        )
        
        session = VoiceProcessingSession(
            session_id="test-session",
            user_id="test-user",
            input_audio=audio_data
        )
        
        assert session.session_id == "test-session"
        assert session.user_id == "test-user"
        assert session.input_audio == audio_data
        assert session.processed_audio is None
        assert session.transcribed_text is None
        assert session.detected_language is None
        assert session.confidence_score is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.metadata, dict)
    
    def test_voice_session_with_results(self):
        """Test VoiceProcessingSession with processing results."""
        audio_data = AudioData(
            audio_bytes=b"test",
            sample_rate=16000,
            channels=1,
            duration=1.0,
            format="wav"
        )
        
        session = VoiceProcessingSession(
            session_id="test-session",
            user_id="test-user",
            input_audio=audio_data,
            transcribed_text="Hello world",
            detected_language="en-US",
            confidence_score=0.95
        )
        
        assert session.transcribed_text == "Hello world"
        assert session.detected_language == "en-US"
        assert session.confidence_score == 0.95


class MockVoiceEngine(VoiceEngine):
    """Mock implementation of VoiceEngine for testing."""
    
    async def speech_to_text(self, audio, language_code=None):
        return "Mock transcription"
    
    async def text_to_speech(self, text, language_code, voice_settings=None):
        # Return simple audio data
        return AudioData(
            audio_bytes=b"mock_audio",
            sample_rate=22050,
            channels=1,
            duration=1.0,
            format="wav"
        )
    
    async def detect_language(self, audio):
        return "en-US"
    
    async def is_language_supported(self, language_code):
        return language_code in ["en-US", "hi-IN"]
    
    async def get_supported_languages(self):
        return ["en-US", "hi-IN"]
    
    async def preprocess_audio(self, audio, noise_reduction=True, normalize=True):
        processed = AudioData(
            audio_bytes=audio.audio_bytes,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            duration=audio.duration,
            format=audio.format,
            preprocessed=True
        )
        return processed


class TestVoiceEngine:
    """Test VoiceEngine abstract interface."""
    
    @pytest.fixture
    def voice_engine(self):
        """Create mock voice engine for testing."""
        return MockVoiceEngine()
    
    @pytest.fixture
    def sample_audio(self):
        """Create sample audio data for testing."""
        return AudioData(
            audio_bytes=b"sample_audio_data",
            sample_rate=16000,
            channels=1,
            duration=2.0,
            format="wav"
        )
    
    @pytest.mark.asyncio
    async def test_speech_to_text(self, voice_engine, sample_audio):
        """Test speech-to-text functionality."""
        result = await voice_engine.speech_to_text(sample_audio, "en-US")
        assert result == "Mock transcription"
    
    @pytest.mark.asyncio
    async def test_text_to_speech(self, voice_engine):
        """Test text-to-speech functionality."""
        result = await voice_engine.text_to_speech("Hello world", "en-US")
        assert isinstance(result, AudioData)
        assert result.sample_rate == 22050
        assert result.duration == 1.0
    
    @pytest.mark.asyncio
    async def test_detect_language(self, voice_engine, sample_audio):
        """Test language detection."""
        result = await voice_engine.detect_language(sample_audio)
        assert result == "en-US"
    
    @pytest.mark.asyncio
    async def test_is_language_supported(self, voice_engine):
        """Test language support checking."""
        assert await voice_engine.is_language_supported("en-US") is True
        assert await voice_engine.is_language_supported("hi-IN") is True
        assert await voice_engine.is_language_supported("fr-FR") is False
    
    @pytest.mark.asyncio
    async def test_get_supported_languages(self, voice_engine):
        """Test getting supported languages."""
        languages = await voice_engine.get_supported_languages()
        assert "en-US" in languages
        assert "hi-IN" in languages
        assert len(languages) == 2
    
    @pytest.mark.asyncio
    async def test_preprocess_audio(self, voice_engine, sample_audio):
        """Test audio preprocessing."""
        result = await voice_engine.preprocess_audio(sample_audio)
        assert isinstance(result, AudioData)
        assert result.preprocessed is True
    
    @pytest.mark.asyncio
    async def test_create_session(self, voice_engine, sample_audio):
        """Test voice session creation."""
        session = await voice_engine.create_session("test-user", sample_audio)
        assert isinstance(session, VoiceProcessingSession)
        assert session.user_id == "test-user"
        assert session.input_audio == sample_audio
        assert session.session_id is not None
    
    @pytest.mark.asyncio
    async def test_process_voice_session(self, voice_engine, sample_audio):
        """Test complete voice session processing."""
        session = await voice_engine.create_session("test-user", sample_audio)
        processed_session = await voice_engine.process_voice_session(session, "en-US")
        
        assert processed_session.transcribed_text == "Mock transcription"
        assert processed_session.detected_language == "en-US"
        assert processed_session.confidence_score is not None
        assert processed_session.processing_time is not None
        assert processed_session.processed_audio is not None


class TestAudioPreprocessor:
    """Test AudioPreprocessor functionality."""
    
    @pytest.fixture
    def preprocessor(self):
        """Create AudioPreprocessor instance."""
        return AudioPreprocessor()
    
    @pytest.fixture
    def sample_audio_with_noise(self):
        """Create sample audio with simulated noise."""
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)
        
        # Create signal + noise
        t = np.linspace(0, duration, samples)
        signal = np.sin(2 * np.pi * 440 * t)  # 440Hz tone
        noise = np.random.normal(0, 0.1, samples)  # Add noise
        audio_array = (signal + noise) * 16384  # Scale to 16-bit range
        audio_array = audio_array.astype(np.int16)
        
        return AudioData.from_numpy(audio_array, sample_rate)
    
    def test_reduce_noise(self, preprocessor, sample_audio_with_noise):
        """Test noise reduction functionality."""
        original_audio = sample_audio_with_noise
        processed_audio = preprocessor.reduce_noise(original_audio, 0.5)
        
        assert isinstance(processed_audio, AudioData)
        assert processed_audio.preprocessed is True
        assert processed_audio.sample_rate == original_audio.sample_rate
        assert processed_audio.channels == original_audio.channels
        assert processed_audio.noise_level <= original_audio.noise_level
    
    def test_normalize_audio(self, preprocessor, sample_audio_with_noise):
        """Test audio normalization."""
        processed_audio = preprocessor.normalize_audio(sample_audio_with_noise, 0.8)
        
        assert isinstance(processed_audio, AudioData)
        assert processed_audio.sample_rate == sample_audio_with_noise.sample_rate
        
        # Check that audio is normalized (max value should be close to target)
        audio_array = processed_audio.to_numpy().astype(np.float32)
        max_val = np.max(np.abs(audio_array)) / 32767.0  # Normalize to 0-1 range
        assert max_val <= 1.0  # Should not clip
    
    def test_apply_bandpass_filter(self, preprocessor, sample_audio_with_noise):
        """Test bandpass filtering."""
        processed_audio = preprocessor.apply_bandpass_filter(
            sample_audio_with_noise, 300.0, 3400.0
        )
        
        assert isinstance(processed_audio, AudioData)
        assert processed_audio.preprocessed is True
        assert processed_audio.sample_rate == sample_audio_with_noise.sample_rate
    
    def test_assess_audio_quality(self, preprocessor, sample_audio_with_noise):
        """Test audio quality assessment."""
        quality_metrics = preprocessor.assess_audio_quality(sample_audio_with_noise)
        
        assert isinstance(quality_metrics, dict)
        assert 'rms_level' in quality_metrics
        assert 'snr_estimate' in quality_metrics
        assert 'zero_crossing_rate' in quality_metrics
        assert 'spectral_centroid' in quality_metrics
        assert 'quality_score' in quality_metrics
        assert 'recommendations' in quality_metrics
        
        # Quality score should be between 0 and 1
        assert 0.0 <= quality_metrics['quality_score'] <= 1.0
        
        # Recommendations should be a list
        assert isinstance(quality_metrics['recommendations'], list)
        assert len(quality_metrics['recommendations']) > 0


class TestVoiceProcessingError:
    """Test VoiceProcessingError exception."""
    
    def test_voice_processing_error_creation(self):
        """Test creating VoiceProcessingError."""
        error = VoiceProcessingError(
            "Test error message",
            error_code="TEST_ERROR",
            original_error=ValueError("Original error")
        )
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "TEST_ERROR"
        assert isinstance(error.original_error, ValueError)
    
    def test_voice_processing_error_minimal(self):
        """Test creating VoiceProcessingError with minimal parameters."""
        error = VoiceProcessingError("Simple error")
        
        assert str(error) == "Simple error"
        assert error.message == "Simple error"
        assert error.error_code is None
        assert error.original_error is None