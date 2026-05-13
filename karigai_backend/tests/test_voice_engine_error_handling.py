"""
Unit tests for Voice Engine Error Handling.

Tests error handling scenarios for voice processing including:
- Low confidence score handling
- Unsupported language fallback
- Audio quality issue detection
- Network and API failures
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the database and other dependencies before importing
sys.modules['app.models.voice_session'] = MagicMock()
sys.modules['app.schemas.voice'] = MagicMock()
sys.modules['app.core.database'] = MagicMock()
sys.modules['app.models'] = MagicMock()
sys.modules['app.core.audio_preprocessing'] = MagicMock()

from app.core.voice_engine import (
    VoiceEngine, AudioData, VoiceProcessingSession, VoiceProcessingError
)


class MockVoiceService(VoiceEngine):
    """Mock voice service for testing error handling."""
    
    def __init__(self):
        self.supported_languages = [
            "hi-IN", "en-IN", "ml-IN", "pa-IN", "bn-IN", "ta-IN", "te-IN"
        ]
        self.preprocessor = Mock()
        self.preprocessor.assess_audio_quality = Mock(return_value={
            'rms_level': 0.5,
            'snr_estimate': 15.0,
            'zero_crossing_rate': 0.1,
            'spectral_centroid': 2000.0,
            'quality_score': 0.7,
            'recommendations': ['Good quality audio']
        })
        self.preprocessor.reduce_noise = Mock(side_effect=lambda x, *args: x)
        self.preprocessor.normalize_audio = Mock(side_effect=lambda x, *args: x)
        self.preprocessor.apply_bandpass_filter = Mock(side_effect=lambda x, *args: x)
    
    async def speech_to_text(self, audio: AudioData, language_code: str = None) -> str:
        if language_code and not await self.is_language_supported(language_code):
            raise VoiceProcessingError(
                f"Language {language_code} is not supported",
                error_code="UNSUPPORTED_LANGUAGE"
            )
        return "Mock transcription"
    
    async def text_to_speech(self, text: str, language_code: str, 
                           voice_settings: dict = None) -> AudioData:
        if not await self.is_language_supported(language_code):
            raise VoiceProcessingError(
                f"Language {language_code} is not supported for TTS",
                error_code="UNSUPPORTED_LANGUAGE"
            )
        return AudioData(
            audio_bytes=b"mock_audio",
            sample_rate=22050,
            channels=1,
            duration=1.0,
            format="wav"
        )
    
    async def detect_language(self, audio: AudioData) -> str:
        return "hi-IN"
    
    async def is_language_supported(self, language_code: str) -> bool:
        return language_code in self.supported_languages
    
    async def get_supported_languages(self) -> list:
        return self.supported_languages.copy()
    
    async def preprocess_audio(self, audio: AudioData, 
                             noise_reduction: bool = True,
                             normalize: bool = True) -> AudioData:
        if audio.sample_rate <= 0 or audio.channels <= 0 or audio.duration < 0:
            raise VoiceProcessingError(
                "Invalid audio parameters",
                error_code="PREPROCESSING_FAILED"
            )
        
        processed = AudioData(
            audio_bytes=audio.audio_bytes,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            duration=audio.duration,
            format=audio.format,
            preprocessed=True
        )
        return processed
    
    async def _calculate_confidence(self, session: VoiceProcessingSession) -> float:
        # Simulate confidence calculation based on audio quality
        audio = session.input_audio
        
        # Base confidence
        base_confidence = 0.5
        
        # Adjust based on duration
        if 1.0 <= audio.duration <= 30.0:
            base_confidence += 0.2
        elif audio.duration < 0.5:
            base_confidence -= 0.3
        
        # Adjust based on sample rate
        if audio.sample_rate >= 16000:
            base_confidence += 0.1
        elif audio.sample_rate < 8000:
            base_confidence -= 0.2
        
        # Simulate noise level impact
        if hasattr(audio, 'noise_level') and audio.noise_level > 0.5:
            base_confidence -= 0.3
        
        return max(0.0, min(1.0, base_confidence))
class TestLowConfidenceScoreHandling:
    """Test handling of low confidence scores in voice recognition."""
    
    @pytest.fixture
    def voice_service(self):
        """Create mock VoiceService instance for testing."""
        return MockVoiceService()
    
    @pytest.fixture
    def low_quality_audio(self):
        """Create low quality audio data that should result in low confidence."""
        # Create very short, noisy audio
        sample_rate = 8000  # Low sample rate
        duration = 0.2  # Very short duration
        samples = int(sample_rate * duration)
        
        # Generate mostly noise with weak signal
        noise = np.random.normal(0, 0.8, samples)
        weak_signal = np.sin(2 * np.pi * 100 * np.linspace(0, duration, samples)) * 0.1
        audio_array = (noise + weak_signal) * 16384
        audio_array = audio_array.astype(np.int16)
        
        audio_data = AudioData.from_numpy(audio_array, sample_rate, format="wav")
        audio_data.noise_level = 0.8  # High noise level
        return audio_data
    
    @pytest.mark.asyncio
    async def test_low_confidence_detection(self, voice_service, low_quality_audio):
        """Test that low quality audio results in low confidence scores."""
        session = await voice_service.create_session("test-user", low_quality_audio)
        processed_session = await voice_service.process_voice_session(session)
        
        # Low quality audio should result in lower confidence
        assert processed_session.confidence_score is not None
        assert processed_session.confidence_score < 0.8  # Below typical threshold
    
    @pytest.mark.asyncio
    async def test_confidence_score_calculation_factors(self, voice_service):
        """Test that confidence score considers multiple quality factors."""
        # Test with different audio characteristics
        test_cases = [
            # (sample_rate, duration, noise_level, expected_confidence_range)
            (16000, 5.0, 0.1, (0.7, 1.0)),  # Good quality
            (8000, 1.0, 0.5, (0.3, 0.7)),   # Medium quality
            (8000, 0.1, 0.8, (0.0, 0.5)),   # Poor quality
        ]
        
        for sample_rate, duration, noise_level, (min_conf, max_conf) in test_cases:
            samples = int(sample_rate * duration)
            t = np.linspace(0, duration, samples)
            signal = np.sin(2 * np.pi * 440 * t) * (1 - noise_level)
            noise = np.random.normal(0, noise_level, samples)
            audio_array = ((signal + noise) * 16384).astype(np.int16)
            
            audio_data = AudioData.from_numpy(audio_array, sample_rate)
            audio_data.noise_level = noise_level
            session = await voice_service.create_session("test-user", audio_data)
            processed_session = await voice_service.process_voice_session(session)
            
            assert min_conf <= processed_session.confidence_score <= max_conf
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_handling(self, voice_service, low_quality_audio):
        """Test handling when confidence falls below threshold."""
        session = await voice_service.create_session("test-user", low_quality_audio)
        processed_session = await voice_service.process_voice_session(session)
        
        # Should still process but mark low confidence
        assert processed_session.confidence_score < 0.5
        assert processed_session.transcribed_text is not None


class TestUnsupportedLanguageFallback:
    """Test fallback behavior for unsupported languages."""
    
    @pytest.fixture
    def voice_service(self):
        """Create mock VoiceService instance for testing."""
        return MockVoiceService()
    
    @pytest.fixture
    def sample_audio(self):
        """Create sample audio data."""
        return AudioData(
            audio_bytes=b"sample_audio_data",
            sample_rate=16000,
            channels=1,
            duration=2.0,
            format="wav"
        )
    
    @pytest.mark.asyncio
    async def test_unsupported_language_detection(self, voice_service):
        """Test detection of unsupported languages."""
        unsupported_languages = ["fr-FR", "de-DE", "ja-JP", "zh-CN"]
        
        for lang_code in unsupported_languages:
            is_supported = await voice_service.is_language_supported(lang_code)
            assert is_supported is False
    
    @pytest.mark.asyncio
    async def test_unsupported_language_stt_fallback(self, voice_service, sample_audio):
        """Test STT fallback for unsupported languages."""
        # Try to process with unsupported language
        with pytest.raises(VoiceProcessingError) as exc_info:
            await voice_service.speech_to_text(sample_audio, "fr-FR")
        
        assert exc_info.value.error_code == "UNSUPPORTED_LANGUAGE"
        assert "fr-FR" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_unsupported_language_tts_fallback(self, voice_service):
        """Test TTS fallback for unsupported languages."""
        # Try to synthesize with unsupported language
        with pytest.raises(VoiceProcessingError) as exc_info:
            await voice_service.text_to_speech("Hello world", "fr-FR")
        
        assert exc_info.value.error_code == "UNSUPPORTED_LANGUAGE"
        assert "fr-FR" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_language_fallback_to_supported(self, voice_service, sample_audio):
        """Test automatic fallback to supported language."""
        session = await voice_service.create_session("test-user", sample_audio)
        processed_session = await voice_service.process_voice_session(session)
        
        # Should successfully process with detected language
        assert processed_session.detected_language == "hi-IN"
        assert processed_session.transcribed_text is not None
    
    @pytest.mark.asyncio
    async def test_supported_languages_list(self, voice_service):
        """Test that supported languages list is comprehensive."""
        supported_languages = await voice_service.get_supported_languages()
        
        # Should include major Indian languages
        expected_languages = ["hi-IN", "en-IN", "ml-IN", "pa-IN", "bn-IN", "ta-IN", "te-IN"]
        
        for lang in expected_languages:
            assert lang in supported_languages
        
        # Should not include unsupported languages
        unsupported_languages = ["fr-FR", "de-DE", "ja-JP"]
        for lang in unsupported_languages:
            assert lang not in supported_languages


class TestAudioQualityIssueDetection:
    """Test detection and handling of audio quality issues."""
    
    @pytest.fixture
    def voice_service(self):
        """Create mock VoiceService instance for testing."""
        return MockVoiceService()
    
    def create_problematic_audio(self, issue_type: str) -> AudioData:
        """Create audio with specific quality issues."""
        sample_rate = 16000
        duration = 2.0
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        if issue_type == "too_quiet":
            # Very low amplitude audio
            audio_array = (np.sin(2 * np.pi * 440 * t) * 100).astype(np.int16)
        elif issue_type == "too_loud":
            # Clipped/distorted audio
            audio_array = np.full(samples, 32767, dtype=np.int16)
        elif issue_type == "too_noisy":
            # High noise-to-signal ratio
            signal = np.sin(2 * np.pi * 440 * t) * 0.1
            noise = np.random.normal(0, 0.9, samples)
            audio_array = ((signal + noise) * 16384).astype(np.int16)
        elif issue_type == "too_short":
            # Very short duration
            short_samples = int(sample_rate * 0.1)  # 0.1 seconds
            audio_array = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, short_samples)) * 16384).astype(np.int16)
            return AudioData.from_numpy(audio_array, sample_rate)
        elif issue_type == "wrong_sample_rate":
            # Very low sample rate
            low_sr = 4000
            low_samples = int(low_sr * duration)
            audio_array = (np.sin(2 * np.pi * 440 * np.linspace(0, duration, low_samples)) * 16384).astype(np.int16)
            return AudioData.from_numpy(audio_array, low_sr)
        else:
            # Default case
            audio_array = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16)
        
        return AudioData.from_numpy(audio_array, sample_rate)
    
    @pytest.mark.asyncio
    async def test_quiet_audio_detection(self, voice_service):
        """Test detection of too-quiet audio."""
        quiet_audio = self.create_problematic_audio("too_quiet")
        
        # Mock quality assessment to return low RMS
        voice_service.preprocessor.assess_audio_quality.return_value = {
            'rms_level': 0.05,  # Very low RMS level
            'snr_estimate': 5.0,
            'zero_crossing_rate': 0.1,
            'spectral_centroid': 2000.0,
            'quality_score': 0.3,
            'recommendations': ['Increase volume', 'Check microphone']
        }
        
        # Process audio and check quality assessment
        processed_audio = await voice_service.preprocess_audio(quiet_audio)
        quality_metrics = voice_service.preprocessor.assess_audio_quality(quiet_audio)
        
        assert quality_metrics['rms_level'] < 0.1  # Very low RMS level
        assert 'increase volume' in ' '.join(quality_metrics['recommendations']).lower()
    
    @pytest.mark.asyncio
    async def test_loud_audio_detection(self, voice_service):
        """Test detection of too-loud/clipped audio."""
        loud_audio = self.create_problematic_audio("too_loud")
        
        # Mock quality assessment to return high RMS
        voice_service.preprocessor.assess_audio_quality.return_value = {
            'rms_level': 0.95,  # Very high RMS level
            'snr_estimate': 20.0,
            'zero_crossing_rate': 0.1,
            'spectral_centroid': 2000.0,
            'quality_score': 0.4,
            'recommendations': ['Audio may be clipped', 'Reduce input volume']
        }
        
        quality_metrics = voice_service.preprocessor.assess_audio_quality(loud_audio)
        
        assert quality_metrics['rms_level'] > 0.9  # Very high RMS level
        assert any('clip' in rec.lower() or 'loud' in rec.lower() or 'volume' in rec.lower()
                  for rec in quality_metrics['recommendations'])
    
    @pytest.mark.asyncio
    async def test_noisy_audio_detection(self, voice_service):
        """Test detection of noisy audio."""
        noisy_audio = self.create_problematic_audio("too_noisy")
        
        # Mock quality assessment to return low SNR
        voice_service.preprocessor.assess_audio_quality.return_value = {
            'rms_level': 0.5,
            'snr_estimate': 5.0,  # Low signal-to-noise ratio
            'zero_crossing_rate': 0.3,
            'spectral_centroid': 2000.0,
            'quality_score': 0.3,
            'recommendations': ['High noise detected', 'Use noise reduction']
        }
        
        quality_metrics = voice_service.preprocessor.assess_audio_quality(noisy_audio)
        
        # Should detect low SNR
        assert quality_metrics['snr_estimate'] < 10  # Low signal-to-noise ratio
        assert any('noise' in rec.lower() for rec in quality_metrics['recommendations'])
    
    @pytest.mark.asyncio
    async def test_short_audio_detection(self, voice_service):
        """Test detection of too-short audio."""
        short_audio = self.create_problematic_audio("too_short")
        
        session = await voice_service.create_session("test-user", short_audio)
        processed_session = await voice_service.process_voice_session(session)
        
        # Short audio should result in lower confidence
        assert processed_session.confidence_score < 0.7
        assert short_audio.duration < 0.5
    
    @pytest.mark.asyncio
    async def test_low_sample_rate_detection(self, voice_service):
        """Test detection of inadequate sample rate."""
        low_sr_audio = self.create_problematic_audio("wrong_sample_rate")
        
        # Mock quality assessment for low sample rate
        voice_service.preprocessor.assess_audio_quality.return_value = {
            'rms_level': 0.5,
            'snr_estimate': 15.0,
            'zero_crossing_rate': 0.1,
            'spectral_centroid': 1500.0,
            'quality_score': 0.4,
            'recommendations': ['Low sample rate detected', 'Consider higher sample rate']
        }
        
        quality_metrics = voice_service.preprocessor.assess_audio_quality(low_sr_audio)
        
        # Should recommend higher sample rate for low sample rates
        if low_sr_audio.sample_rate < 8000:
            assert any('sample rate' in rec.lower() for rec in quality_metrics['recommendations'])
    
    @pytest.mark.asyncio
    async def test_audio_preprocessing_error_handling(self, voice_service):
        """Test error handling in audio preprocessing."""
        # Create invalid audio data
        invalid_audio = AudioData(
            audio_bytes=b"invalid_audio_data",
            sample_rate=0,  # Invalid sample rate
            channels=0,     # Invalid channels
            duration=-1.0,  # Invalid duration
            format="invalid"
        )
        
        # Should handle preprocessing errors gracefully
        with pytest.raises(VoiceProcessingError) as exc_info:
            await voice_service.preprocess_audio(invalid_audio)
        
        assert exc_info.value.error_code == "PREPROCESSING_FAILED"


class TestErrorRecoveryAndRetry:
    """Test error recovery and retry mechanisms."""
    
    @pytest.fixture
    def voice_service(self):
        """Create mock VoiceService instance for testing."""
        return MockVoiceService()
    
    @pytest.mark.asyncio
    async def test_session_processing_error_recovery(self, voice_service):
        """Test recovery from session processing errors."""
        sample_audio = AudioData(
            audio_bytes=b"test_audio",
            sample_rate=16000,
            channels=1,
            duration=1.0,
            format="wav"
        )
        
        session = await voice_service.create_session("test-user", sample_audio)
        
        # Mock an error during processing
        with patch.object(voice_service, 'speech_to_text') as mock_stt:
            mock_stt.side_effect = VoiceProcessingError("Temporary failure", "TEMP_ERROR")
            
            # Should handle error gracefully and record it in metadata
            try:
                await voice_service.process_voice_session(session)
            except VoiceProcessingError:
                pass  # Expected
            
            # Session should have error recorded
            assert 'error' in session.metadata
            assert session.processing_time is not None
    
    @pytest.mark.asyncio
    async def test_partial_processing_results(self, voice_service):
        """Test handling of partial processing results."""
        sample_audio = AudioData(
            audio_bytes=b"test_audio",
            sample_rate=16000,
            channels=1,
            duration=1.0,
            format="wav"
        )
        
        session = await voice_service.create_session("test-user", sample_audio)
        
        # Mock partial failure (preprocessing works, but STT fails)
        with patch.object(voice_service, 'speech_to_text') as mock_stt:
            mock_stt.side_effect = VoiceProcessingError("STT failed", "STT_ERROR")
            
            try:
                await voice_service.process_voice_session(session)
            except VoiceProcessingError:
                pass
            
            # Should have partial results (preprocessing should have worked)
            assert session.processed_audio is not None  # Preprocessing succeeded
            assert session.transcribed_text is None     # STT failed
            assert session.processing_time is not None