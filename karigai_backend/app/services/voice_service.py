from sqlalchemy.orm import Session
from fastapi import UploadFile
from typing import Optional, List
import uuid
import time
import io

from app.models.voice_session import VoiceSession
from app.schemas.voice import VoiceProcessResponse
from app.core.voice_engine import VoiceEngine, AudioData, VoiceProcessingError, VoiceProcessingSession
from app.core.audio_preprocessing import AudioPreprocessor


class VoiceService(VoiceEngine):
    """
    Concrete implementation of VoiceEngine for KarigAI system.
    
    This service provides voice processing capabilities including speech-to-text,
    text-to-speech, language detection, and audio preprocessing.
    """
    
    def __init__(self, db: Session):
        super().__init__()
        self.db = db
        self.preprocessor = AudioPreprocessor()
        
        # Supported languages for KarigAI
        self.supported_languages = [
            "hi-IN",  # Hindi (India)
            "en-IN",  # English (India)
            "ml-IN",  # Malayalam (India)
            "pa-IN",  # Punjabi (India)
            "bn-IN",  # Bengali (India)
            "ta-IN",  # Tamil (India)
            "te-IN",  # Telugu (India)
            "gu-IN",  # Gujarati (India)
            "kn-IN",  # Kannada (India)
            "mr-IN",  # Marathi (India)
        ]
    
    async def speech_to_text(self, audio: AudioData, language_code: Optional[str] = None) -> str:
        """
        Convert speech to text using the configured STT engine.
        
        Args:
            audio: AudioData object containing speech
            language_code: Optional language code hint
            
        Returns:
            Transcribed text string
            
        Raises:
            VoiceProcessingError: If transcription fails
        """
        try:
            # Placeholder implementation - in production this would use
            # OpenAI Whisper API or similar service
            
            # Validate language support
            if language_code and not await self.is_language_supported(language_code):
                raise VoiceProcessingError(
                    f"Language {language_code} is not supported",
                    error_code="UNSUPPORTED_LANGUAGE"
                )
            
            # Simulate processing time based on audio duration
            processing_time = min(audio.duration * 0.1, 3.0)  # Max 3 seconds
            await self._simulate_processing(processing_time)
            
            # Mock transcription result
            if language_code and language_code.startswith("hi"):
                transcribed_text = "नमस्ते, मैं आपकी सहायता कैसे कर सकता हूं?"
            else:
                transcribed_text = "Hello, how can I help you today?"
            
            return transcribed_text
            
        except Exception as e:
            raise VoiceProcessingError(
                f"Speech-to-text conversion failed: {str(e)}",
                error_code="STT_FAILED",
                original_error=e
            )
    
    async def text_to_speech(self, text: str, language_code: str, 
                           voice_settings: Optional[dict] = None) -> AudioData:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert to speech
            language_code: Language code for synthesis
            voice_settings: Optional voice configuration
            
        Returns:
            AudioData containing synthesized speech
            
        Raises:
            VoiceProcessingError: If synthesis fails
        """
        try:
            # Validate language support
            if not await self.is_language_supported(language_code):
                raise VoiceProcessingError(
                    f"Language {language_code} is not supported for TTS",
                    error_code="UNSUPPORTED_LANGUAGE"
                )
            
            # Placeholder implementation - in production this would use
            # ElevenLabs API or similar service
            
            # Simulate processing
            await self._simulate_processing(1.0)
            
            # Create mock audio data (silence for now)
            sample_rate = 22050
            duration = max(1.0, len(text) * 0.1)  # Estimate duration
            samples = int(sample_rate * duration)
            
            # Generate simple sine wave as placeholder
            import numpy as np
            t = np.linspace(0, duration, samples)
            frequency = 440  # A4 note
            audio_array = (np.sin(2 * np.pi * frequency * t) * 0.1).astype(np.float32)
            
            # Convert to 16-bit PCM
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            return AudioData.from_numpy(
                audio_int16,
                sample_rate=sample_rate,
                channels=1,
                format="wav",
                bit_depth=16
            )
            
        except Exception as e:
            raise VoiceProcessingError(
                f"Text-to-speech conversion failed: {str(e)}",
                error_code="TTS_FAILED",
                original_error=e
            )
    
    async def detect_language(self, audio: AudioData) -> str:
        """
        Detect language from audio.
        
        Args:
            audio: AudioData containing speech
            
        Returns:
            Detected language code
            
        Raises:
            VoiceProcessingError: If detection fails
        """
        try:
            # Placeholder implementation - in production this would use
            # language detection models
            
            await self._simulate_processing(0.5)
            
            # Mock detection - default to Hindi for Indian context
            return "hi-IN"
            
        except Exception as e:
            raise VoiceProcessingError(
                f"Language detection failed: {str(e)}",
                error_code="LANGUAGE_DETECTION_FAILED",
                original_error=e
            )
    
    async def is_language_supported(self, language_code: str) -> bool:
        """Check if language is supported."""
        return language_code in self.supported_languages
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self.supported_languages.copy()
    
    async def preprocess_audio(self, audio: AudioData, 
                             noise_reduction: bool = True,
                             normalize: bool = True) -> AudioData:
        """
        Preprocess audio for better recognition quality.
        
        Args:
            audio: Input AudioData
            noise_reduction: Apply noise reduction
            normalize: Normalize audio levels
            
        Returns:
            Preprocessed AudioData
        """
        try:
            processed_audio = audio
            
            # Apply noise reduction
            if noise_reduction:
                processed_audio = self.preprocessor.reduce_noise(processed_audio)
            
            # Apply normalization
            if normalize:
                processed_audio = self.preprocessor.normalize_audio(processed_audio)
            
            # Apply bandpass filter for speech frequencies
            processed_audio = self.preprocessor.apply_bandpass_filter(processed_audio)
            
            return processed_audio
            
        except Exception as e:
            raise VoiceProcessingError(
                f"Audio preprocessing failed: {str(e)}",
                error_code="PREPROCESSING_FAILED",
                original_error=e
            )
    
    async def _calculate_confidence(self, session) -> float:
        """Calculate confidence score based on audio quality and processing results."""
        try:
            # Assess audio quality
            quality_metrics = self.preprocessor.assess_audio_quality(session.input_audio)
            
            # Base confidence on quality score
            base_confidence = quality_metrics.get('quality_score', 0.5)
            
            # Adjust based on language detection confidence
            if session.detected_language in self.supported_languages:
                language_bonus = 0.2
            else:
                language_bonus = 0.0
            
            # Adjust based on audio duration (too short or too long reduces confidence)
            duration = session.input_audio.duration
            if 1.0 <= duration <= 30.0:
                duration_bonus = 0.1
            else:
                duration_bonus = 0.0
            
            final_confidence = min(1.0, base_confidence + language_bonus + duration_bonus)
            return final_confidence
            
        except Exception:
            return 0.5  # Default confidence if calculation fails
    
    async def _simulate_processing(self, duration: float):
        """Simulate processing delay for development/testing."""
        import asyncio
        await asyncio.sleep(duration)
    
    # Legacy methods for backward compatibility with existing API
    async def speech_to_text_legacy(
        self, 
        audio_file: UploadFile, 
        user_id: Optional[str] = None,
        language_code: str = "hi-IN"
    ) -> VoiceProcessResponse:
        """Legacy method for backward compatibility with existing API."""
        start_time = time.time()
        
        try:
            # Read audio file and convert to AudioData
            audio_bytes = await audio_file.read()
            
            # Create AudioData object (simplified - in production would parse file format)
            audio_data = AudioData(
                audio_bytes=audio_bytes,
                sample_rate=16000,  # Assume 16kHz
                channels=1,  # Assume mono
                duration=len(audio_bytes) / (16000 * 2),  # Rough estimate
                format=audio_file.filename.split('.')[-1] if audio_file.filename else "wav",
                bit_depth=16,
                file_path=audio_file.filename
            )
            
            # Create and process voice session
            session = await self.create_session(user_id, audio_data)
            processed_session = await self.process_voice_session(session, language_code)
            
            # Save to database
            db_session = VoiceSession(
                session_id=processed_session.session_id,
                user_id=user_id,
                audio_file_path=f"uploads/{audio_file.filename}",
                transcribed_text=processed_session.transcribed_text,
                language_detected=processed_session.detected_language,
                confidence_score=processed_session.confidence_score
            )
            
            self.db.add(db_session)
            self.db.commit()
            self.db.refresh(db_session)
            
            processing_time = time.time() - start_time
            
            return VoiceProcessResponse(
                session_id=processed_session.session_id,
                transcribed_text=processed_session.transcribed_text,
                language_detected=processed_session.detected_language,
                confidence_score=processed_session.confidence_score,
                processing_time=processing_time,
                created_at=db_session.created_at
            )
            
        except Exception as e:
            raise VoiceProcessingError(
                f"Legacy speech-to-text processing failed: {str(e)}",
                error_code="LEGACY_STT_FAILED",
                original_error=e
            )
    
    async def text_to_speech_legacy(self, text: str, language_code: str = "hi-IN") -> str:
        """Legacy method for backward compatibility."""
        try:
            audio_data = await self.text_to_speech(text, language_code)
            
            # Save audio file and return path
            audio_filename = f"tts_{uuid.uuid4()}.wav"
            audio_path = f"uploads/audio/{audio_filename}"
            
            # In production, would save audio_data.audio_bytes to file
            return audio_path
            
        except Exception as e:
            raise VoiceProcessingError(
                f"Legacy text-to-speech processing failed: {str(e)}",
                error_code="LEGACY_TTS_FAILED",
                original_error=e
            )
    
    async def detect_language_legacy(self, audio_file: UploadFile) -> str:
        """Legacy method for backward compatibility."""
        try:
            # Read audio file and convert to AudioData
            audio_bytes = await audio_file.read()
            
            audio_data = AudioData(
                audio_bytes=audio_bytes,
                sample_rate=16000,
                channels=1,
                duration=len(audio_bytes) / (16000 * 2),
                format=audio_file.filename.split('.')[-1] if audio_file.filename else "wav",
                bit_depth=16,
                file_path=audio_file.filename
            )
            
            return await self.detect_language(audio_data)
            
        except Exception as e:
            raise VoiceProcessingError(
                f"Legacy language detection failed: {str(e)}",
                error_code="LEGACY_DETECTION_FAILED",
                original_error=e
            )