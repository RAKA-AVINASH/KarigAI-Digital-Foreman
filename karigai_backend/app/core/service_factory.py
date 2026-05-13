"""
Service Factory for KarigAI Backend

This module provides a factory for creating service instances that can
switch between API-based and local model implementations.
"""

import logging
from typing import Any, Dict, Optional
from app.core.model_config import get_model_config, ModelMode

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory for creating service instances with mode switching.
    """
    
    def __init__(self):
        """Initialize the service factory."""
        self.config = get_model_config()
        self._service_cache = {}
        logger.info(f"ServiceFactory initialized with mode: {self.config.model_mode}")
    
    def get_speech_recognition_service(self):
        """
        Get speech recognition service based on configuration.
        
        Returns:
            Speech recognition service instance
        """
        service_name = "speech_recognition"
        
        if service_name in self._service_cache:
            return self._service_cache[service_name]
        
        if self.config.should_use_api(service_name):
            from app.services.whisper_stt_service import WhisperSTTService
            service = WhisperSTTService()
            logger.info("Using API-based speech recognition (Whisper)")
        else:
            # Use local model with optional API fallback
            from app.services.local_speech_service import LocalSpeechRecognitionService
            service = LocalSpeechRecognitionService(
                fallback_enabled=self.config.can_fallback_to_api(service_name)
            )
            logger.info("Using local speech recognition model")
        
        self._service_cache[service_name] = service
        return service
    
    def get_text_to_speech_service(self):
        """
        Get text-to-speech service based on configuration.
        
        Returns:
            TTS service instance
        """
        service_name = "text_to_speech"
        
        if service_name in self._service_cache:
            return self._service_cache[service_name]
        
        if self.config.should_use_api(service_name):
            from app.services.elevenlabs_tts_service import ElevenLabsTTSService
            service = ElevenLabsTTSService()
            logger.info("Using API-based TTS (ElevenLabs)")
        else:
            from app.services.local_tts_service import LocalTTSService
            service = LocalTTSService(
                fallback_enabled=self.config.can_fallback_to_api(service_name)
            )
            logger.info("Using local TTS model")
        
        self._service_cache[service_name] = service
        return service
    
    def get_equipment_vision_service(self):
        """
        Get equipment vision service based on configuration.
        
        Returns:
            Equipment vision service instance
        """
        service_name = "equipment_identification"
        
        if service_name in self._service_cache:
            return self._service_cache[service_name]
        
        if self.config.should_use_api(service_name):
            from app.services.equipment_vision_service import EquipmentVisionService
            service = EquipmentVisionService()
            logger.info("Using API-based equipment vision")
        else:
            from app.services.local_equipment_service import LocalEquipmentService
            service = LocalEquipmentService(
                fallback_enabled=self.config.can_fallback_to_api(service_name)
            )
            logger.info("Using local equipment vision model")
        
        self._service_cache[service_name] = service
        return service
    
    def get_translation_service(self):
        """
        Get translation service based on configuration.
        
        Returns:
            Translation service instance
        """
        service_name = "translation"
        
        if service_name in self._service_cache:
            return self._service_cache[service_name]
        
        if self.config.should_use_api(service_name):
            from app.services.translation_service import TranslationService
            service = TranslationService()
            logger.info("Using API-based translation")
        else:
            from app.services.local_translation_service import LocalTranslationService
            service = LocalTranslationService(
                fallback_enabled=self.config.can_fallback_to_api(service_name)
            )
            logger.info("Using local translation model")
        
        self._service_cache[service_name] = service
        return service
    
    def clear_cache(self):
        """Clear the service cache."""
        self._service_cache.clear()
        logger.info("Service cache cleared")
    
    def reload_config(self):
        """Reload configuration and clear cache."""
        self.config = get_model_config()
        self.clear_cache()
        logger.info(f"Configuration reloaded, mode: {self.config.model_mode}")


# Global factory instance
_factory = None


def get_service_factory() -> ServiceFactory:
    """Get or create the global service factory instance."""
    global _factory
    if _factory is None:
        _factory = ServiceFactory()
    return _factory
