"""
OpenAI Whisper Speech-to-Text Service

This module implements the WhisperSTTService class that provides speech-to-text
functionality using OpenAI's Whisper API. It supports multiple Indian languages
and includes confidence scoring, language detection, and fallback handling.
"""

import asyncio
import io
import logging
import tempfile
import time
from typing import Dict, List, Optional, Tuple
import aiofiles
import httpx
import openai
from openai import AsyncOpenAI

from app.core.voice_engine import VoiceEngine, AudioData, VoiceProcessingError
from app.core.audio_preprocessing import AudioPreprocessor
from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperSTTService(VoiceEngine):
    """
    OpenAI Whisper-based Speech-to-Text service implementation.
    
    Provides speech recognition for multiple Indian languages with confidence
    scoring, language detection, and fallback handling for unsupported dialects.
    """
    
    # Supported languages mapping (Whisper language codes to our internal codes)
    SUPPORTED_LANGUAGES = {
        "hi": "hi-IN",      # Hindi
        "en": "en-US",      # English
        "ml": "ml-IN",      # Malayalam
        "pa": "pa-IN",      # Punjabi (Panjabi)
        "bn": "bn-IN",      # Bengali
        "ta": "ta-IN",      # Tamil
        "te": "te-IN",      # Telugu
        "gu": "gu-IN",      # Gujarati
        "kn": "kn-IN",      # Kannada
        "mr": "mr-IN",      # Marathi
        "or": "or-IN",      # Odia
        "as": "as-IN",      # Assamese
        "ur": "ur-IN",      # Urdu
    }
    
    # Reverse mapping for language detection
    LANGUAGE_CODE_MAPPING = {v: k for k, v in SUPPORTED_LANGUAGES.items()}
    
    # Fallback languages for unsupported dialects
    FALLBACK_LANGUAGES = {
        "hi-IN": ["hi", "en"],  # Hindi fallback to Hindi then English
        "en-US": ["en", "hi"],  # English fallback to English then Hindi
        "ml-IN": ["ml", "hi", "en"],  # Malayalam fallback chain
        "pa-IN": ["pa", "hi", "en"],  # Punjabi fallback chain
        "bn-IN": ["bn", "hi", "en"],  # Bengali fallback chain
        "ta-IN": ["ta", "hi", "en"],  # Tamil fallback chain
        "te-IN": ["te", "hi", "en"],  # Telugu fallback chain
        "gu-IN": ["gu", "hi", "en"],  # Gujarati fallback chain
        "kn-IN": ["kn", "hi", "en"],  # Kannada fallback chain
        "mr-IN": ["mr", "hi", "en"],  # Marathi fallback chain
        "or-IN": ["or", "hi", "en"],  # Odia fallback chain
        "as-IN": ["as", "hi", "en"],  # Assamese fallback chain
        "ur-IN": ["ur", "hi", "en"],  # Urdu fallback chain
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize WhisperSTTService.
        
        Args:
            api_key: OpenAI API key. If None, uses settings.OPENAI_API_KEY
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required for WhisperSTTService")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.preprocessor = AudioPreprocessor()
        
        # Configuration
        self.model = "whisper-1"
        self.temperature = 0.0  # Deterministic output
        self.max_retries = 3
        self.timeout = 30.0
        
        # Confidence scoring thresholds
        self.high_confidence_threshold = 0.9
        self.medium_confidence_threshold = 0.7
        self.low_confidence_threshold = 0.5
        
        logger.info("WhisperSTTService initialized with OpenAI Whisper API")
    
    async def speech_to_text(self, audio: AudioData, language_code: Optional[str] = None) -> str:
        """
        Convert speech audio to text using OpenAI Whisper.
        
        Args:
            audio: AudioData object containing the speech audio
            language_code: Optional language code hint (e.g., 'hi-IN', 'en-US')
            
        Returns:
            Transcribed text string
            
        Raises:
            VoiceProcessingError: If speech-to-text conversion fails
        """
        try:
            start_time = time.time()
            
            # Preprocess audio for better recognition
            processed_audio = await self.preprocess_audio(audio)
            
            # Determine language for Whisper API
            whisper_language = None
            if language_code:
                whisper_language = self._get_whisper_language_code(language_code)
            
            # Convert audio to temporary file for Whisper API
            transcription = await self._transcribe_with_whisper(
                processed_audio, whisper_language
            )
            
            processing_time = time.time() - start_time
            logger.info(
                f"Speech-to-text completed in {processing_time:.2f}s, "
                f"language: {language_code}, text length: {len(transcription)}"
            )
            
            return transcription
            
        except Exception as e:
            logger.error(f"Speech-to-text failed: {str(e)}")
            raise VoiceProcessingError(
                f"Failed to convert speech to text: {str(e)}",
                error_code="STT_FAILED",
                original_error=e
            )
    
    async def text_to_speech(self, text: str, language_code: str, 
                           voice_settings: Optional[dict] = None) -> AudioData:
        """
        Convert text to speech audio.
        
        Note: This is a placeholder implementation. OpenAI Whisper is STT-only.
        For TTS, use ElevenLabs or other TTS services.
        
        Args:
            text: Text to convert to speech
            language_code: Language code for speech synthesis
            voice_settings: Optional voice configuration
            
        Returns:
            AudioData object containing synthesized speech
            
        Raises:
            VoiceProcessingError: Always raises as TTS is not supported
        """
        raise VoiceProcessingError(
            "Text-to-speech is not supported by WhisperSTTService. Use ElevenLabsTTSService instead.",
            error_code="TTS_NOT_SUPPORTED"
        )
    
    async def detect_language(self, audio: AudioData) -> str:
        """
        Detect the language of speech in audio using Whisper.
        
        Args:
            audio: AudioData object containing speech
            
        Returns:
            Detected language code (e.g., 'hi-IN', 'en-US')
            
        Raises:
            VoiceProcessingError: If language detection fails
        """
        try:
            # Use Whisper's language detection capability
            processed_audio = await self.preprocess_audio(audio)
            
            # Transcribe without language hint to get language detection
            result = await self._transcribe_with_whisper(
                processed_audio, language=None, detect_language=True
            )
            
            # Extract detected language from result
            detected_language = result.get("language", "en")
            
            # Convert to our internal language code format
            internal_language_code = self.SUPPORTED_LANGUAGES.get(
                detected_language, "en-US"
            )
            
            logger.info(f"Detected language: {detected_language} -> {internal_language_code}")
            return internal_language_code
            
        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            # Fallback to English if detection fails
            return "en-US"
    
    async def is_language_supported(self, language_code: str) -> bool:
        """
        Check if a language is supported by Whisper.
        
        Args:
            language_code: Language code to check
            
        Returns:
            True if language is supported, False otherwise
        """
        return language_code in self.SUPPORTED_LANGUAGES.values()
    
    async def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.
        
        Returns:
            List of supported language codes
        """
        return list(self.SUPPORTED_LANGUAGES.values())
    
    async def preprocess_audio(self, audio: AudioData, 
                             noise_reduction: bool = True,
                             normalize: bool = True) -> AudioData:
        """
        Preprocess audio for better recognition quality.
        
        Args:
            audio: Input AudioData object
            noise_reduction: Whether to apply noise reduction
            normalize: Whether to normalize audio levels
            
        Returns:
            Preprocessed AudioData object
            
        Raises:
            VoiceProcessingError: If preprocessing fails
        """
        try:
            processed_audio = audio
            
            # Apply noise reduction if requested
            if noise_reduction and audio.noise_level > 0.3:
                processed_audio = self.preprocessor.reduce_noise(processed_audio)
            
            # Normalize audio levels if requested
            if normalize:
                processed_audio = self.preprocessor.normalize_audio(processed_audio)
            
            # Apply bandpass filter for speech frequencies (300-3400 Hz)
            processed_audio = self.preprocessor.apply_bandpass_filter(
                processed_audio, low_freq=300.0, high_freq=3400.0
            )
            
            # Mark as preprocessed
            processed_audio.preprocessed = True
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {str(e)}")
            raise VoiceProcessingError(
                f"Failed to preprocess audio: {str(e)}",
                error_code="PREPROCESSING_FAILED",
                original_error=e
            )
    
    async def get_confidence_score(self, audio: AudioData, transcription: str) -> float:
        """
        Calculate confidence score for transcription.
        
        Args:
            audio: Original audio data
            transcription: Transcribed text
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Assess audio quality
            quality_metrics = self.preprocessor.assess_audio_quality(audio)
            audio_quality_score = quality_metrics.get("quality_score", 0.5)
            
            # Calculate transcription quality indicators
            text_length_score = min(1.0, len(transcription.strip()) / 50.0)  # Normalize by expected length
            
            # Check for common transcription artifacts that indicate low confidence
            artifacts = ["[inaudible]", "[unclear]", "...", "???"]
            artifact_penalty = sum(0.1 for artifact in artifacts if artifact in transcription.lower())
            
            # Combine factors for overall confidence
            base_confidence = (audio_quality_score * 0.6 + text_length_score * 0.4)
            final_confidence = max(0.0, min(1.0, base_confidence - artifact_penalty))
            
            return final_confidence
            
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {str(e)}")
            return 0.5  # Default medium confidence
    
    async def _transcribe_with_whisper(self, audio: AudioData, 
                                     language: Optional[str] = None,
                                     detect_language: bool = False) -> str:
        """
        Perform transcription using OpenAI Whisper API.
        
        Args:
            audio: Preprocessed audio data
            language: Optional language code for Whisper
            detect_language: Whether to return language detection info
            
        Returns:
            Transcribed text or dict with transcription and language info
        """
        # Create temporary file for audio
        with tempfile.NamedTemporaryFile(suffix=f".{audio.format}", delete=False) as temp_file:
            temp_file.write(audio.audio_bytes)
            temp_file_path = temp_file.name
        
        try:
            # Prepare transcription parameters
            transcription_params = {
                "model": self.model,
                "temperature": self.temperature,
                "response_format": "verbose_json" if detect_language else "text"
            }
            
            if language:
                transcription_params["language"] = language
            
            # Perform transcription with retries
            for attempt in range(self.max_retries):
                try:
                    async with aiofiles.open(temp_file_path, 'rb') as audio_file:
                        audio_content = await audio_file.read()
                    
                    # Create file-like object for OpenAI API
                    audio_buffer = io.BytesIO(audio_content)
                    audio_buffer.name = f"audio.{audio.format}"
                    
                    # Call Whisper API
                    result = await self.client.audio.transcriptions.create(
                        file=audio_buffer,
                        **transcription_params
                    )
                    
                    if detect_language and hasattr(result, 'language'):
                        return {
                            "text": result.text,
                            "language": result.language
                        }
                    else:
                        return result.text if hasattr(result, 'text') else str(result)
                    
                except openai.RateLimitError as e:
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise VoiceProcessingError(
                        "OpenAI API rate limit exceeded",
                        error_code="RATE_LIMIT_EXCEEDED",
                        original_error=e
                    )
                
                except openai.APIError as e:
                    if attempt < self.max_retries - 1:
                        wait_time = 1 + attempt
                        logger.warning(f"API error, retrying in {wait_time}s: {str(e)}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise VoiceProcessingError(
                        f"OpenAI API error: {str(e)}",
                        error_code="API_ERROR",
                        original_error=e
                    )
                
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        wait_time = 1 + attempt
                        logger.warning(f"Transcription attempt {attempt + 1} failed, retrying: {str(e)}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise
            
            raise VoiceProcessingError(
                f"Transcription failed after {self.max_retries} attempts",
                error_code="MAX_RETRIES_EXCEEDED"
            )
            
        finally:
            # Clean up temporary file
            try:
                import os
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {str(e)}")
    
    def _get_whisper_language_code(self, internal_language_code: str) -> Optional[str]:
        """
        Convert internal language code to Whisper language code.
        
        Args:
            internal_language_code: Our internal language code (e.g., 'hi-IN')
            
        Returns:
            Whisper language code (e.g., 'hi') or None if not supported
        """
        return self.LANGUAGE_CODE_MAPPING.get(internal_language_code)
    
    async def transcribe_with_fallback(self, audio: AudioData, 
                                     preferred_language: str) -> Tuple[str, str, float]:
        """
        Transcribe audio with fallback language handling.
        
        Args:
            audio: Audio data to transcribe
            preferred_language: Preferred language code
            
        Returns:
            Tuple of (transcribed_text, detected_language, confidence_score)
        """
        fallback_languages = self.FALLBACK_LANGUAGES.get(
            preferred_language, ["en", "hi"]
        )
        
        last_error = None
        
        # Try preferred language first
        try:
            whisper_lang = self._get_whisper_language_code(preferred_language)
            if whisper_lang:
                transcription = await self._transcribe_with_whisper(audio, whisper_lang)
                confidence = await self.get_confidence_score(audio, transcription)
                
                if confidence >= self.low_confidence_threshold:
                    return transcription, preferred_language, confidence
        except Exception as e:
            last_error = e
            logger.warning(f"Transcription failed for {preferred_language}: {str(e)}")
        
        # Try fallback languages
        for fallback_lang in fallback_languages:
            try:
                transcription = await self._transcribe_with_whisper(audio, fallback_lang)
                confidence = await self.get_confidence_score(audio, transcription)
                
                # Convert back to internal language code
                internal_lang = self.SUPPORTED_LANGUAGES.get(fallback_lang, "en-US")
                
                if confidence >= self.low_confidence_threshold:
                    logger.info(f"Fallback successful with {fallback_lang}")
                    return transcription, internal_lang, confidence
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Fallback transcription failed for {fallback_lang}: {str(e)}")
                continue
        
        # If all fallbacks fail, raise the last error
        if last_error:
            raise VoiceProcessingError(
                f"Transcription failed for all languages including fallbacks",
                error_code="ALL_FALLBACKS_FAILED",
                original_error=last_error
            )
        
        # Return empty result if no error but no success
        return "", "en-US", 0.0
    
    async def _calculate_confidence(self, session) -> float:
        """
        Calculate confidence score for a voice processing session.
        
        Args:
            session: VoiceProcessingSession object
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not session.transcribed_text:
            return 0.0
        
        return await self.get_confidence_score(
            session.processed_audio or session.input_audio,
            session.transcribed_text
        )