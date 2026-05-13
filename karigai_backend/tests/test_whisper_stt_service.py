"""
Unit tests for WhisperSTTService

Tests the OpenAI Whisper-based speech-to-text service implementation,
including language support, confidence scoring, and fallback handling.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import tempfile
import os
from typing import Dict, Any

from app.services.whisper_stt_service import WhisperSTTService
from app.core.voice_engine import AudioData, VoiceProcessingError


class TestWhisperSTTService:
    """Test WhisperSTTService functionality."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create mock OpenAI client."""
        mock_client = AsyncMock()
        mock_transcription = Mock()
        mock_transcription.text = "Hello world"
        mock_transcription.language = "en"
        
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
        return mock_client
    
    @pytest.fixture
    def whisper_service(self, mock_openai_client):
        """Create WhisperSTTService with mocked OpenAI client."""
        with patch('app.services.whisper_stt_service.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            service = WhisperSTTService(api_key="test-api-key")
            service.client = mock_openai_client
            return service
    
    @pytest.fixture
    def sample_audio(self):
        """Create sample audio data for testing."""
        # Generate 1 second of 440Hz sine wave
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_array = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16)
        
        return AudioData.from_numpy(
            audio_array, sample_rate, channels=1, format="wav"
        )
    
    def test_whisper_service_initialization(self):
        """Test WhisperSTTService initialization."""
        with patch('app.services.whisper_stt_service.AsyncOpenAI'):
            service = WhisperSTTService(api_key="test-key")
            assert service.api_key == "test-key"
            assert service.model == "whisper-1"
            assert service.temperature == 0.0
            assert service.max_retries == 3
    
    def test_whisper_service_initialization_no_api_key(self):
        """Test WhisperSTTService initialization without API key."""
        with patch('app.services.whisper_stt_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                WhisperSTTService()
    
    @pytest.mark.asyncio
    async def test_speech_to_text_success(self, whisper_service, sample_audio, mock_openai_client):
        """Test successful speech-to-text conversion."""
        # Mock the transcription response
        mock_transcription = Mock()
        mock_transcription.text = "Test transcription"
        mock_openai_client.audio.transcriptions.create.return_value = mock_transcription
        
        # Mock preprocessing
        with patch.object(whisper_service, 'preprocess_audio', return_value=sample_audio):
            result = await whisper_service.speech_to_text(sample_audio, "hi-IN")
        
        assert result == "Test transcription"
        mock_openai_client.audio.transcriptions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_speech_to_text_with_language_code(self, whisper_service, sample_audio, mock_openai_client):
        """Test speech-to-text with specific language code."""
        mock_transcription = Mock()
        mock_transcription.text = "Hindi transcription"
        mock_openai_client.audio.transcriptions.create.return_value = mock_transcription
        
        with patch.object(whisper_service, 'preprocess_audio', return_value=sample_audio):
            result = await whisper_service.speech_to_text(sample_audio, "hi-IN")
        
        assert result == "Hindi transcription"
        
        # Check that the correct language was passed to Whisper
        call_args = mock_openai_client.audio.transcriptions.create.call_args
        assert call_args[1]["language"] == "hi"  # Whisper language code for Hindi
    
    @pytest.mark.asyncio
    async def test_speech_to_text_api_error(self, whisper_service, sample_audio, mock_openai_client):
        """Test speech-to-text with API error."""
        import openai
        mock_openai_client.audio.transcriptions.create.side_effect = openai.APIError("API Error")
        
        with patch.object(whisper_service, 'preprocess_audio', return_value=sample_audio):
            with pytest.raises(VoiceProcessingError, match="Failed to convert speech to text"):
                await whisper_service.speech_to_text(sample_audio, "en-US")
    
    @pytest.mark.asyncio
    async def test_detect_language_success(self, whisper_service, sample_audio, mock_openai_client):
        """Test successful language detection."""
        # Mock verbose response with language detection
        mock_response = {
            "text": "Hello world",
            "language": "en"
        }
        mock_openai_client.audio.transcriptions.create.return_value = mock_response
        
        with patch.object(whisper_service, 'preprocess_audio', return_value=sample_audio):
            with patch.object(whisper_service, '_transcribe_with_whisper', return_value=mock_response):
                result = await whisper_service.detect_language(sample_audio)
        
        assert result == "en-US"  # Should convert to internal language code
    
    @pytest.mark.asyncio
    async def test_detect_language_fallback(self, whisper_service, sample_audio):
        """Test language detection fallback to English."""
        with patch.object(whisper_service, 'preprocess_audio', return_value=sample_audio):
            with patch.object(whisper_service, '_transcribe_with_whisper', side_effect=Exception("Error")):
                result = await whisper_service.detect_language(sample_audio)
        
        assert result == "en-US"  # Should fallback to English
    
    @pytest.mark.asyncio
    async def test_is_language_supported(self, whisper_service):
        """Test language support checking."""
        # Test supported languages
        assert await whisper_service.is_language_supported("hi-IN") is True
        assert await whisper_service.is_language_supported("en-US") is True
        assert await whisper_service.is_language_supported("ml-IN") is True
        
        # Test unsupported language
        assert await whisper_service.is_language_supported("fr-FR") is False
        assert await whisper_service.is_language_supported("invalid") is False
    
    @pytest.mark.asyncio
    async def test_get_supported_languages(self, whisper_service):
        """Test getting supported languages."""
        languages = await whisper_service.get_supported_languages()
        
        assert isinstance(languages, list)
        assert "hi-IN" in languages
        assert "en-US" in languages
        assert "ml-IN" in languages
        assert "ta-IN" in languages
        assert len(languages) > 5  # Should have multiple Indian languages
    
    @pytest.mark.asyncio
    async def test_preprocess_audio(self, whisper_service, sample_audio):
        """Test audio preprocessing."""
        # Mock the preprocessor methods
        with patch.object(whisper_service.preprocessor, 'reduce_noise', return_value=sample_audio) as mock_reduce:
            with patch.object(whisper_service.preprocessor, 'normalize_audio', return_value=sample_audio) as mock_normalize:
                with patch.object(whisper_service.preprocessor, 'apply_bandpass_filter', return_value=sample_audio) as mock_filter:
                    result = await whisper_service.preprocess_audio(sample_audio)
        
        assert isinstance(result, AudioData)
        assert result.preprocessed is True
        
        # Check that preprocessing methods were called
        mock_normalize.assert_called_once()
        mock_filter.assert_called_once_with(sample_audio, low_freq=300.0, high_freq=3400.0)
    
    @pytest.mark.asyncio
    async def test_preprocess_audio_with_noise_reduction(self, whisper_service, sample_audio):
        """Test audio preprocessing with noise reduction."""
        # Set high noise level to trigger noise reduction
        sample_audio.noise_level = 0.5
        
        with patch.object(whisper_service.preprocessor, 'reduce_noise', return_value=sample_audio) as mock_reduce:
            with patch.object(whisper_service.preprocessor, 'normalize_audio', return_value=sample_audio):
                with patch.object(whisper_service.preprocessor, 'apply_bandpass_filter', return_value=sample_audio):
                    await whisper_service.preprocess_audio(sample_audio, noise_reduction=True)
        
        mock_reduce.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_preprocess_audio_error_handling(self, whisper_service, sample_audio):
        """Test audio preprocessing error handling."""
        with patch.object(whisper_service.preprocessor, 'normalize_audio', side_effect=Exception("Processing error")):
            with pytest.raises(VoiceProcessingError, match="Failed to preprocess audio"):
                await whisper_service.preprocess_audio(sample_audio)
    
    @pytest.mark.asyncio
    async def test_get_confidence_score(self, whisper_service, sample_audio):
        """Test confidence score calculation."""
        transcription = "This is a clear transcription"
        
        # Mock quality assessment
        quality_metrics = {"quality_score": 0.8}
        with patch.object(whisper_service.preprocessor, 'assess_audio_quality', return_value=quality_metrics):
            confidence = await whisper_service.get_confidence_score(sample_audio, transcription)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high for good transcription
    
    @pytest.mark.asyncio
    async def test_get_confidence_score_with_artifacts(self, whisper_service, sample_audio):
        """Test confidence score with transcription artifacts."""
        transcription = "This is [inaudible] transcription with [unclear] parts..."
        
        quality_metrics = {"quality_score": 0.8}
        with patch.object(whisper_service.preprocessor, 'assess_audio_quality', return_value=quality_metrics):
            confidence = await whisper_service.get_confidence_score(sample_audio, transcription)
        
        assert confidence < 0.8  # Should be lower due to artifacts
    
    def test_get_whisper_language_code(self, whisper_service):
        """Test conversion from internal to Whisper language codes."""
        assert whisper_service._get_whisper_language_code("hi-IN") == "hi"
        assert whisper_service._get_whisper_language_code("en-US") == "en"
        assert whisper_service._get_whisper_language_code("ml-IN") == "ml"
        assert whisper_service._get_whisper_language_code("invalid") is None
    
    @pytest.mark.asyncio
    async def test_transcribe_with_fallback_success(self, whisper_service, sample_audio):
        """Test transcription with fallback - success on first try."""
        with patch.object(whisper_service, '_transcribe_with_whisper', return_value="Success transcription"):
            with patch.object(whisper_service, 'get_confidence_score', return_value=0.9):
                text, lang, confidence = await whisper_service.transcribe_with_fallback(sample_audio, "hi-IN")
        
        assert text == "Success transcription"
        assert lang == "hi-IN"
        assert confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_transcribe_with_fallback_uses_fallback(self, whisper_service, sample_audio):
        """Test transcription with fallback - uses fallback language."""
        # First call fails, second succeeds
        with patch.object(whisper_service, '_transcribe_with_whisper', side_effect=[
            Exception("First attempt failed"),
            "Fallback transcription"
        ]):
            with patch.object(whisper_service, 'get_confidence_score', return_value=0.8):
                text, lang, confidence = await whisper_service.transcribe_with_fallback(sample_audio, "hi-IN")
        
        assert text == "Fallback transcription"
        assert lang == "hi-IN"  # Should map back to supported language
        assert confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_transcribe_with_fallback_all_fail(self, whisper_service, sample_audio):
        """Test transcription with fallback - all attempts fail."""
        with patch.object(whisper_service, '_transcribe_with_whisper', side_effect=Exception("All failed")):
            with pytest.raises(VoiceProcessingError, match="Transcription failed for all languages"):
                await whisper_service.transcribe_with_fallback(sample_audio, "hi-IN")
    
    @pytest.mark.asyncio
    async def test_text_to_speech_not_supported(self, whisper_service):
        """Test that text-to-speech raises appropriate error."""
        with pytest.raises(VoiceProcessingError, match="Text-to-speech is not supported"):
            await whisper_service.text_to_speech("Hello", "en-US")
    
    @pytest.mark.asyncio
    async def test_transcribe_with_whisper_rate_limit_retry(self, whisper_service, sample_audio, mock_openai_client):
        """Test retry logic for rate limit errors."""
        import openai
        
        # First call fails with rate limit, second succeeds
        mock_openai_client.audio.transcriptions.create.side_effect = [
            openai.RateLimitError("Rate limit exceeded"),
            Mock(text="Success after retry")
        ]
        
        with patch('aiofiles.open', create=True) as mock_aiofiles:
            mock_file = AsyncMock()
            mock_file.read.return_value = b"fake_audio_data"
            mock_aiofiles.return_value.__aenter__.return_value = mock_file
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "test.wav"
                mock_temp.return_value.__enter__.return_value.write = Mock()
                
                with patch('os.unlink'):  # Mock file cleanup
                    result = await whisper_service._transcribe_with_whisper(sample_audio, "en")
        
        assert result == "Success after retry"
        assert mock_openai_client.audio.transcriptions.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_transcribe_with_whisper_max_retries_exceeded(self, whisper_service, sample_audio, mock_openai_client):
        """Test max retries exceeded scenario."""
        import openai
        
        # All calls fail
        mock_openai_client.audio.transcriptions.create.side_effect = openai.APIError("Persistent error")
        
        with patch('aiofiles.open', create=True) as mock_aiofiles:
            mock_file = AsyncMock()
            mock_file.read.return_value = b"fake_audio_data"
            mock_aiofiles.return_value.__aenter__.return_value = mock_file
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "test.wav"
                mock_temp.return_value.__enter__.return_value.write = Mock()
                
                with patch('os.unlink'):
                    with pytest.raises(VoiceProcessingError, match="Transcription failed after 3 attempts"):
                        await whisper_service._transcribe_with_whisper(sample_audio, "en")
        
        assert mock_openai_client.audio.transcriptions.create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_with_session(self, whisper_service):
        """Test confidence calculation for voice processing session."""
        from app.core.voice_engine import VoiceProcessingSession
        
        # Create mock session
        sample_audio = AudioData(
            audio_bytes=b"test", sample_rate=16000, channels=1, duration=1.0, format="wav"
        )
        
        session = VoiceProcessingSession(
            session_id="test",
            user_id="user",
            input_audio=sample_audio,
            transcribed_text="Test transcription"
        )
        
        with patch.object(whisper_service, 'get_confidence_score', return_value=0.85):
            confidence = await whisper_service._calculate_confidence(session)
        
        assert confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_no_transcription(self, whisper_service):
        """Test confidence calculation with no transcription."""
        from app.core.voice_engine import VoiceProcessingSession
        
        sample_audio = AudioData(
            audio_bytes=b"test", sample_rate=16000, channels=1, duration=1.0, format="wav"
        )
        
        session = VoiceProcessingSession(
            session_id="test",
            user_id="user",
            input_audio=sample_audio,
            transcribed_text=None  # No transcription
        )
        
        confidence = await whisper_service._calculate_confidence(session)
        assert confidence == 0.0


class TestWhisperSTTServiceIntegration:
    """Integration tests for WhisperSTTService with real audio processing."""
    
    @pytest.fixture
    def whisper_service_real(self):
        """Create WhisperSTTService with real preprocessor but mocked OpenAI."""
        with patch('app.services.whisper_stt_service.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_transcription = Mock()
            mock_transcription.text = "Integration test transcription"
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
            mock_openai.return_value = mock_client
            
            service = WhisperSTTService(api_key="test-key")
            service.client = mock_client
            return service
    
    @pytest.fixture
    def noisy_audio(self):
        """Create audio with noise for preprocessing tests."""
        sample_rate = 16000
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create signal with noise
        signal = np.sin(2 * np.pi * 440 * t)  # 440Hz tone
        noise = np.random.normal(0, 0.2, len(signal))  # Add noise
        audio_array = ((signal + noise) * 16384).astype(np.int16)
        
        audio_data = AudioData.from_numpy(audio_array, sample_rate)
        audio_data.noise_level = 0.4  # Set noise level
        return audio_data
    
    @pytest.mark.asyncio
    async def test_end_to_end_speech_processing(self, whisper_service_real, noisy_audio):
        """Test end-to-end speech processing with real preprocessing."""
        result = await whisper_service_real.speech_to_text(noisy_audio, "en-US")
        
        assert result == "Integration test transcription"
        
        # Verify that preprocessing was applied
        # (This is tested indirectly through the successful completion)
    
    @pytest.mark.asyncio
    async def test_language_detection_integration(self, whisper_service_real, noisy_audio):
        """Test language detection with real preprocessing."""
        # Mock the transcribe method to return language info
        mock_response = {"text": "Test", "language": "hi"}
        with patch.object(whisper_service_real, '_transcribe_with_whisper', return_value=mock_response):
            detected_lang = await whisper_service_real.detect_language(noisy_audio)
        
        assert detected_lang == "hi-IN"
    
    @pytest.mark.asyncio
    async def test_quality_assessment_integration(self, whisper_service_real, noisy_audio):
        """Test quality assessment integration."""
        confidence = await whisper_service_real.get_confidence_score(
            noisy_audio, "Test transcription"
        )
        
        assert 0.0 <= confidence <= 1.0
        # Should be lower confidence due to noise
        assert confidence < 0.9