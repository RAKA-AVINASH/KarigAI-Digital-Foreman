"""
Voice Service Factory

This module provides a factory for creating voice service instances
with different TTS and STT providers based on configuration.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.voice_engine import VoiceEngine, AudioData, VoiceProcessingError
from app.core.config_ai_services import AIServicesConfig, AIServiceMode
from app.services.voice_service import VoiceService
from app.services.elevenlabs_tts_service import ElevenLabsTTSService, VoiceSettings
from app.services.whisper_stt_service import WhisperSTTService


class EnhancedVoiceService(VoiceService):
    """
    Enhanced voice service that integrates multiple TTS and STT providers.
    
    This service combines the base VoiceService with specialized providers
    like ElevenLabs for TTS and Whisper for STT.
    """
    
    def __init__(self, db: Session, config: AIServicesConfig):
        super().__init__(db)
        self.config = config
        
        # Initialize TTS service
        if config.elevenlabs_api_key:
            self.tts_service = ElevenLabsTTSService(config)
        else:
            self.tts_service = None
        
        # Initialize STT service
        if config.openai_api_key:
            self.stt_service = WhisperSTTService(config)
        else:
            self.stt_service = None
    
    async def text_to_speech(self, text: str, language_code: str, 
                           voice_settings: Optional[dict] = None) -> AudioData:
        """
        Convert text to speech using ElevenLabs or fallback to base implementation.
        
        Args:
            text: Text to convert to speech
            language_code: Language code for synthesis
            voice_settings: Optional voice configuration
            
        Returns:
            AudioData containing synthesized speech
        """
        if self.tts_service:
            try:
                # Convert dict to VoiceSettings if provided
                if voice_settings:
                    settings = VoiceSettings(
                        stability=voice_settings.get('stability', 0.75),
                        similarity_boost=voice_settings.get('similarity_boost', 0.75),
                        style=voice_settings.get('style', 0.0),
                        use_speaker_boost=voice_settings.get('use_speaker_boost', True)
                    )
                else:
                    settings = None
                
                return await self.tts_service.text_to_speech(text, language_code, settings)
            
            except VoiceProcessingError as e:
                # Log error and fallback to base implementation
                print(f"ElevenLabs TTS failed, falling back to base implementation: {e}")
                return await super().text_to_speech(text, language_code, voice_settings)
        else:
            # Use base implementation if ElevenLabs not available
            return await super().text_to_speech(text, language_code, voice_settings)
    
    async def speech_to_text(self, audio: AudioData, language_code: Optional[str] = None) -> str:
        """
        Convert speech to text using Whisper or fallback to base implementation.
        
        Args:
            audio: AudioData containing speech
            language_code: Optional language code hint
            
        Returns:
            Transcribed text string
        """
        if self.stt_service:
            try:
                return await self.stt_service.speech_to_text(audio, language_code)
            except VoiceProcessingError as e:
                # Log error and fallback to base implementation
                print(f"Whisper STT failed, falling back to base implementation: {e}")
                return await super().speech_to_text(audio, language_code)
        else:
            # Use base implementation if Whisper not available
            return await super().speech_to_text(audio, language_code)
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """Get available voices from TTS service."""
        if self.tts_service:
            try:
                voices = await self.tts_service.get_available_voices()
                return {
                    "provider": "elevenlabs",
                    "voices": voices,
                    "supported_languages": self.tts_service.get_supported_languages()
                }
            except Exception as e:
                print(f"Failed to get ElevenLabs voices: {e}")
        
        return {
            "provider": "base",
            "voices": [],
            "supported_languages": self.supported_languages
        }
    
    async def clone_voice(self, name: str, audio_files: list, 
                         description: Optional[str] = None) -> Optional[str]:
        """Clone a voice using TTS service."""
        if self.tts_service:
            try:
                return await self.tts_service.clone_voice(name, audio_files, description)
            except Exception as e:
                print(f"Voice cloning failed: {e}")
                return None
        return None
    
    async def get_tts_cache_stats(self) -> Dict[str, Any]:
        """Get TTS cache statistics."""
        if self.tts_service:
            try:
                return await self.tts_service.get_cache_stats()
            except Exception as e:
                print(f"Failed to get cache stats: {e}")
        
        return {"error": "TTS service not available"}
    
    async def preload_common_phrases(self, phrases: list):
        """Preload common phrases for faster TTS response."""
        if self.tts_service:
            try:
                await self.tts_service.preload_common_phrases(phrases)
            except Exception as e:
                print(f"Failed to preload phrases: {e}")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all voice services."""
        health_status = {}
        
        # Check TTS service
        if self.tts_service:
            health_status["tts_elevenlabs"] = await self.tts_service.health_check()
        else:
            health_status["tts_elevenlabs"] = False
        
        # Check STT service
        if self.stt_service:
            health_status["stt_whisper"] = await self.stt_service.health_check()
        else:
            health_status["stt_whisper"] = False
        
        # Check base service
        health_status["base_service"] = True  # Base service is always available
        
        return health_status


class VoiceServiceFactory:
    """Factory for creating voice service instances."""
    
    @staticmethod
    def create_voice_service(db: Session, config: Optional[AIServicesConfig] = None) -> VoiceEngine:
        """
        Create a voice service instance based on configuration.
        
        Args:
            db: Database session
            config: AI services configuration
            
        Returns:
            VoiceEngine instance
        """
        if config is None:
            from app.core.config_ai_services import ai_config
            config = ai_config
        
        if config.ai_service_mode == AIServiceMode.PAID_APIS:
            return EnhancedVoiceService(db, config)
        elif config.ai_service_mode == AIServiceMode.COLAB_MODELS:
            # TODO: Implement Colab voice service
            return VoiceService(db)
        elif config.ai_service_mode == AIServiceMode.HYBRID:
            # Use enhanced service with fallback capabilities
            return EnhancedVoiceService(db, config)
        else:
            # Offline or basic mode
            return VoiceService(db)
    
    @staticmethod
    def create_tts_service(config: Optional[AIServicesConfig] = None) -> Optional[ElevenLabsTTSService]:
        """
        Create a standalone TTS service instance.
        
        Args:
            config: AI services configuration
            
        Returns:
            ElevenLabsTTSService instance or None
        """
        if config is None:
            from app.core.config_ai_services import ai_config
            config = ai_config
        
        if config.elevenlabs_api_key:
            return ElevenLabsTTSService(config)
        return None
    
    @staticmethod
    def create_stt_service(config: Optional[AIServicesConfig] = None) -> Optional[WhisperSTTService]:
        """
        Create a standalone STT service instance.
        
        Args:
            config: AI services configuration
            
        Returns:
            WhisperSTTService instance or None
        """
        if config is None:
            from app.core.config_ai_services import ai_config
            config = ai_config
        
        if config.openai_api_key:
            return WhisperSTTService(config)
        return None


# Convenience functions for common use cases
def get_voice_service(db: Session) -> VoiceEngine:
    """Get the default voice service instance."""
    return VoiceServiceFactory.create_voice_service(db)


def get_tts_service() -> Optional[ElevenLabsTTSService]:
    """Get the default TTS service instance."""
    return VoiceServiceFactory.create_tts_service()


def get_stt_service() -> Optional[WhisperSTTService]:
    """Get the default STT service instance."""
    return VoiceServiceFactory.create_stt_service()