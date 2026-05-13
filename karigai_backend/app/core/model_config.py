"""
Model Configuration for KarigAI Backend

This module provides configuration for switching between API-based services
and locally trained models, with fallback mechanisms.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from pydantic import Field


class ModelMode(str, Enum):
    """Model inference mode."""
    API = "api"  # Use paid API services (OpenAI, ElevenLabs, etc.)
    LOCAL = "local"  # Use locally trained models
    HYBRID = "hybrid"  # Use local models with API fallback


class ModelConfig(BaseSettings):
    """Configuration for model services."""
    
    # Model mode
    model_mode: ModelMode = Field(
        default=ModelMode.HYBRID,
        env="MODEL_MODE",
        description="Model inference mode (api, local, or hybrid)"
    )
    
    # Model directory
    model_dir: str = Field(
        default="ml_models/models/exports",
        env="MODEL_DIR",
        description="Directory containing exported models"
    )
    
    # Fallback settings
    enable_fallback: bool = Field(
        default=True,
        env="ENABLE_MODEL_FALLBACK",
        description="Enable fallback to API when local models fail"
    )
    
    fallback_timeout: float = Field(
        default=5.0,
        env="MODEL_FALLBACK_TIMEOUT",
        description="Timeout for model inference before fallback (seconds)"
    )
    
    # Cache settings
    enable_model_cache: bool = Field(
        default=True,
        env="ENABLE_MODEL_CACHE",
        description="Enable caching of loaded models"
    )
    
    enable_result_cache: bool = Field(
        default=True,
        env="ENABLE_RESULT_CACHE",
        description="Enable caching of inference results"
    )
    
    result_cache_ttl: int = Field(
        default=3600,
        env="RESULT_CACHE_TTL",
        description="TTL for result cache in seconds"
    )
    
    # Performance settings
    warm_up_models: bool = Field(
        default=True,
        env="WARM_UP_MODELS",
        description="Pre-load models at startup"
    )
    
    max_batch_size: int = Field(
        default=8,
        env="MAX_BATCH_SIZE",
        description="Maximum batch size for model inference"
    )
    
    # Service-specific model modes
    speech_recognition_mode: Optional[ModelMode] = Field(
        default=None,
        env="SPEECH_RECOGNITION_MODE",
        description="Override mode for speech recognition"
    )
    
    text_to_speech_mode: Optional[ModelMode] = Field(
        default=None,
        env="TEXT_TO_SPEECH_MODE",
        description="Override mode for text-to-speech"
    )
    
    vision_mode: Optional[ModelMode] = Field(
        default=None,
        env="VISION_MODE",
        description="Override mode for vision services"
    )
    
    nlp_mode: Optional[ModelMode] = Field(
        default=None,
        env="NLP_MODE",
        description="Override mode for NLP services"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
    
    def get_mode_for_service(self, service_name: str) -> ModelMode:
        """
        Get the model mode for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Model mode for the service
        """
        service_mode_map = {
            "speech_recognition": self.speech_recognition_mode,
            "text_to_speech": self.text_to_speech_mode,
            "equipment_identification": self.vision_mode,
            "ocr": self.vision_mode,
            "pattern_analysis": self.vision_mode,
            "quality_assessment": self.vision_mode,
            "crop_disease": self.vision_mode,
            "circuit_analysis": self.vision_mode,
            "intent_recognition": self.nlp_mode,
            "translation": self.nlp_mode,
            "knowledge_retrieval": self.nlp_mode,
            "scheme_matching": self.nlp_mode,
            "learning_recommendation": self.nlp_mode,
            "trend_analysis": self.nlp_mode,
        }
        
        # Return service-specific mode if set, otherwise use global mode
        return service_mode_map.get(service_name) or self.model_mode
    
    def should_use_local_model(self, service_name: str) -> bool:
        """
        Check if local model should be used for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if local model should be used
        """
        mode = self.get_mode_for_service(service_name)
        return mode in (ModelMode.LOCAL, ModelMode.HYBRID)
    
    def should_use_api(self, service_name: str) -> bool:
        """
        Check if API should be used for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if API should be used
        """
        mode = self.get_mode_for_service(service_name)
        return mode == ModelMode.API
    
    def can_fallback_to_api(self, service_name: str) -> bool:
        """
        Check if fallback to API is allowed for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if fallback is allowed
        """
        mode = self.get_mode_for_service(service_name)
        return self.enable_fallback and mode == ModelMode.HYBRID


# Global configuration instance
_config = None


def get_model_config() -> ModelConfig:
    """Get or create the global model configuration instance."""
    global _config
    if _config is None:
        _config = ModelConfig()
    return _config
