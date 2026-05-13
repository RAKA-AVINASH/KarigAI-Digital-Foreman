"""
Voice Engine Abstract Interface

This module defines the abstract interface for voice processing engines,
providing a contract for speech-to-text, text-to-speech, and language
detection capabilities.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import numpy as np


@dataclass
class AudioData:
    """
    Represents audio data with metadata for voice processing.
    
    Attributes:
        audio_bytes: Raw audio data as bytes
        sample_rate: Audio sample rate in Hz
        channels: Number of audio channels (1 for mono, 2 for stereo)
        duration: Duration of audio in seconds
        format: Audio format (e.g., 'wav', 'mp3', 'flac')
        bit_depth: Audio bit depth (e.g., 16, 24, 32)
        file_path: Optional path to the audio file
        preprocessed: Whether audio has been preprocessed for noise reduction
        noise_level: Estimated noise level (0.0 to 1.0)
    """
    audio_bytes: bytes
    sample_rate: int
    channels: int
    duration: float
    format: str
    bit_depth: int = 16
    file_path: Optional[str] = None
    preprocessed: bool = False
    noise_level: float = 0.0
    
    def to_numpy(self) -> np.ndarray:
        """Convert audio bytes to numpy array for processing."""
        # Convert bytes to numpy array based on bit depth
        if self.bit_depth == 16:
            dtype = np.int16
        elif self.bit_depth == 24:
            dtype = np.int32  # 24-bit stored in 32-bit container
        elif self.bit_depth == 32:
            dtype = np.int32
        else:
            dtype = np.int16  # Default fallback
            
        audio_array = np.frombuffer(self.audio_bytes, dtype=dtype)
        
        # Reshape for multi-channel audio
        if self.channels > 1:
            audio_array = audio_array.reshape(-1, self.channels)
            
        return audio_array
    
    @classmethod
    def from_numpy(cls, audio_array: np.ndarray, sample_rate: int, 
                   channels: int = 1, format: str = "wav", 
                   bit_depth: int = 16) -> 'AudioData':
        """Create AudioData from numpy array."""
        # Convert numpy array to bytes
        if bit_depth == 16:
            audio_array = audio_array.astype(np.int16)
        elif bit_depth == 24:
            audio_array = audio_array.astype(np.int32)
        elif bit_depth == 32:
            audio_array = audio_array.astype(np.int32)
        else:
            audio_array = audio_array.astype(np.int16)
            
        audio_bytes = audio_array.tobytes()
        duration = len(audio_array) / sample_rate
        
        return cls(
            audio_bytes=audio_bytes,
            sample_rate=sample_rate,
            channels=channels,
            duration=duration,
            format=format,
            bit_depth=bit_depth
        )


@dataclass
class VoiceProcessingSession:
    """
    Represents a voice processing session with metadata and results.
    
    Attributes:
        session_id: Unique identifier for the session
        user_id: ID of the user who initiated the session
        input_audio: Original audio input
        processed_audio: Audio after preprocessing (if applicable)
        transcribed_text: Text result from speech-to-text
        detected_language: Detected language code
        confidence_score: Confidence score for recognition (0.0 to 1.0)
        processing_time: Time taken for processing in seconds
        created_at: Timestamp when session was created
        metadata: Additional session metadata
    """
    session_id: str
    user_id: Optional[str]
    input_audio: AudioData
    processed_audio: Optional[AudioData] = None
    transcribed_text: Optional[str] = None
    detected_language: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    created_at: datetime = None
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class VoiceEngine(ABC):
    """
    Abstract base class for voice processing engines.
    
    This interface defines the contract for implementing voice processing
    capabilities including speech-to-text, text-to-speech, language detection,
    and audio preprocessing.
    """
    
    @abstractmethod
    async def speech_to_text(self, audio: AudioData, language_code: Optional[str] = None) -> str:
        """
        Convert speech audio to text.
        
        Args:
            audio: AudioData object containing the speech audio
            language_code: Optional language code hint (e.g., 'hi-IN', 'en-US')
            
        Returns:
            Transcribed text string
            
        Raises:
            VoiceProcessingError: If speech-to-text conversion fails
        """
        pass
    
    @abstractmethod
    async def text_to_speech(self, text: str, language_code: str, 
                           voice_settings: Optional[dict] = None) -> AudioData:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert to speech
            language_code: Language code for speech synthesis
            voice_settings: Optional voice configuration (speed, pitch, etc.)
            
        Returns:
            AudioData object containing the synthesized speech
            
        Raises:
            VoiceProcessingError: If text-to-speech conversion fails
        """
        pass
    
    @abstractmethod
    async def detect_language(self, audio: AudioData) -> str:
        """
        Detect the language of speech in audio.
        
        Args:
            audio: AudioData object containing speech
            
        Returns:
            Detected language code (e.g., 'hi-IN', 'en-US')
            
        Raises:
            VoiceProcessingError: If language detection fails
        """
        pass
    
    @abstractmethod
    async def is_language_supported(self, language_code: str) -> bool:
        """
        Check if a language is supported by the engine.
        
        Args:
            language_code: Language code to check
            
        Returns:
            True if language is supported, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.
        
        Returns:
            List of supported language codes
        """
        pass
    
    @abstractmethod
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
        pass
    
    async def create_session(self, user_id: Optional[str], 
                           audio: AudioData) -> VoiceProcessingSession:
        """
        Create a new voice processing session.
        
        Args:
            user_id: Optional user identifier
            audio: Input audio data
            
        Returns:
            VoiceProcessingSession object
        """
        import uuid
        
        session_id = str(uuid.uuid4())
        return VoiceProcessingSession(
            session_id=session_id,
            user_id=user_id,
            input_audio=audio
        )
    
    async def process_voice_session(self, session: VoiceProcessingSession, 
                                  language_code: Optional[str] = None,
                                  preprocess: bool = True) -> VoiceProcessingSession:
        """
        Process a complete voice session with preprocessing and transcription.
        
        Args:
            session: VoiceProcessingSession to process
            language_code: Optional language code hint
            preprocess: Whether to preprocess audio
            
        Returns:
            Updated VoiceProcessingSession with results
        """
        import time
        
        start_time = time.time()
        
        try:
            # Preprocess audio if requested
            if preprocess:
                session.processed_audio = await self.preprocess_audio(session.input_audio)
                audio_to_process = session.processed_audio
            else:
                audio_to_process = session.input_audio
            
            # Detect language if not provided
            if language_code is None:
                session.detected_language = await self.detect_language(audio_to_process)
                language_code = session.detected_language
            else:
                session.detected_language = language_code
            
            # Convert speech to text
            session.transcribed_text = await self.speech_to_text(audio_to_process, language_code)
            
            # Set confidence score (implementation-specific)
            session.confidence_score = await self._calculate_confidence(session)
            
        except Exception as e:
            session.metadata['error'] = str(e)
            raise
        finally:
            session.processing_time = time.time() - start_time
        
        return session
    
    async def _calculate_confidence(self, session: VoiceProcessingSession) -> float:
        """
        Calculate confidence score for the session.
        Default implementation returns 0.8, should be overridden by implementations.
        """
        return 0.8


class VoiceProcessingError(Exception):
    """Exception raised for voice processing errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 original_error: Optional[Exception] = None):
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)