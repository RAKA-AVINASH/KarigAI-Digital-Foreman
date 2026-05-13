"""
AI Services Configuration

This module provides configuration management for switching between
paid APIs and Google Colab models, enabling cost-effective deployment
options for different scenarios.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field
from dataclasses import dataclass


class AIServiceMode(str, Enum):
    """AI service deployment modes."""
    PAID_APIS = "paid_apis"
    COLAB_MODELS = "colab_models"
    HYBRID = "hybrid"  # Use paid APIs with Colab fallback
    OFFLINE_ONLY = "offline_only"  # Use only cached/on-device models


@dataclass
class ServiceEndpoint:
    """Configuration for a service endpoint."""
    url: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    health_check_url: Optional[str] = None


class AIServicesConfig(BaseSettings):
    """Configuration for AI services."""
    
    # Service mode selection
    ai_service_mode: AIServiceMode = Field(
        default=AIServiceMode.PAID_APIS,
        env="AI_SERVICE_MODE",
        description="AI service deployment mode"
    )
    
    # Paid API configurations
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    google_cloud_api_key: Optional[str] = Field(default=None, env="GOOGLE_CLOUD_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(default=None, env="ELEVENLABS_API_KEY")
    
    # Colab model endpoints
    colab_voice_endpoint: Optional[str] = Field(
        default=None, 
        env="COLAB_VOICE_ENDPOINT",
        description="Colab voice processing endpoint URL"
    )
    colab_vision_endpoint: Optional[str] = Field(
        default=None,
        env="COLAB_VISION_ENDPOINT", 
        description="Colab vision processing endpoint URL"
    )
    colab_nlp_endpoint: Optional[str] = Field(
        default=None,
        env="COLAB_NLP_ENDPOINT",
        description="Colab NLP processing endpoint URL"
    )
    
    # Service-specific configurations
    voice_service_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "paid_apis": {
                "speech_to_text": {
                    "provider": "openai_whisper",
                    "model": "whisper-1",
                    "language_support": ["hi", "en", "ml", "pa", "bn", "ta", "te"]
                },
                "text_to_speech": {
                    "provider": "elevenlabs",
                    "voice_id": "default",
                    "stability": 0.75,
                    "similarity_boost": 0.75
                }
            },
            "colab_models": {
                "speech_to_text": {
                    "model_path": "/models/whisper_indian_languages",
                    "language_support": ["hi", "en", "ml", "pa", "bn", "ta", "te", "hi-en-mixed"]
                },
                "text_to_speech": {
                    "model_path": "/models/coqui_tts_multilingual",
                    "voice_cloning": True
                }
            }
        }
    )
    
    vision_service_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "paid_apis": {
                "equipment_recognition": {
                    "provider": "google_vision",
                    "model": "vision-api-v1"
                },
                "ocr": {
                    "provider": "google_vision",
                    "languages": ["hi", "en"]
                }
            },
            "colab_models": {
                "equipment_recognition": {
                    "model_path": "/models/equipment_classifier",
                    "confidence_threshold": 0.8
                },
                "ocr": {
                    "model_path": "/models/multilingual_ocr",
                    "languages": ["hi", "en", "ml", "pa", "bn", "ta", "te"]
                }
            }
        }
    )
    
    # Fallback and caching configuration
    enable_fallback: bool = Field(
        default=True,
        env="ENABLE_AI_FALLBACK",
        description="Enable fallback between service modes"
    )
    
    cache_results: bool = Field(
        default=True,
        env="CACHE_AI_RESULTS",
        description="Enable caching of AI service results"
    )
    
    cache_ttl_seconds: int = Field(
        default=3600,
        env="CACHE_TTL_SECONDS",
        description="Cache time-to-live in seconds"
    )
    
    # Cost optimization settings
    max_daily_api_cost: float = Field(
        default=10.0,
        env="MAX_DAILY_API_COST",
        description="Maximum daily cost for paid APIs in USD"
    )
    
    cost_tracking_enabled: bool = Field(
        default=True,
        env="COST_TRACKING_ENABLED",
        description="Enable API cost tracking"
    )
    
    # Performance settings
    request_timeout: int = Field(
        default=30,
        env="AI_REQUEST_TIMEOUT",
        description="Request timeout for AI services in seconds"
    )
    
    max_concurrent_requests: int = Field(
        default=10,
        env="MAX_CONCURRENT_AI_REQUESTS",
        description="Maximum concurrent AI service requests"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class AIServiceFactory:
    """Factory for creating AI service instances based on configuration."""
    
    def __init__(self, config: AIServicesConfig):
        self.config = config
        self._service_cache = {}
    
    def get_voice_service(self):
        """Get voice service instance based on current configuration."""
        if "voice" not in self._service_cache:
            if self.config.ai_service_mode == AIServiceMode.PAID_APIS:
                from app.services.voice_service_paid import PaidVoiceService
                self._service_cache["voice"] = PaidVoiceService(self.config)
            elif self.config.ai_service_mode == AIServiceMode.COLAB_MODELS:
                from app.services.voice_service_colab import ColabVoiceService
                self._service_cache["voice"] = ColabVoiceService(self.config)
            elif self.config.ai_service_mode == AIServiceMode.HYBRID:
                from app.services.voice_service_hybrid import HybridVoiceService
                self._service_cache["voice"] = HybridVoiceService(self.config)
            else:
                from app.services.voice_service_offline import OfflineVoiceService
                self._service_cache["voice"] = OfflineVoiceService(self.config)
        
        return self._service_cache["voice"]
    
    def get_vision_service(self):
        """Get vision service instance based on current configuration."""
        if "vision" not in self._service_cache:
            if self.config.ai_service_mode == AIServiceMode.PAID_APIS:
                from app.services.vision_service_paid import PaidVisionService
                self._service_cache["vision"] = PaidVisionService(self.config)
            elif self.config.ai_service_mode == AIServiceMode.COLAB_MODELS:
                from app.services.vision_service_colab import ColabVisionService
                self._service_cache["vision"] = ColabVisionService(self.config)
            elif self.config.ai_service_mode == AIServiceMode.HYBRID:
                from app.services.vision_service_hybrid import HybridVisionService
                self._service_cache["vision"] = HybridVisionService(self.config)
            else:
                from app.services.vision_service_offline import OfflineVisionService
                self._service_cache["vision"] = OfflineVisionService(self.config)
        
        return self._service_cache["vision"]
    
    def get_nlp_service(self):
        """Get NLP service instance based on current configuration."""
        if "nlp" not in self._service_cache:
            if self.config.ai_service_mode == AIServiceMode.PAID_APIS:
                from app.services.nlp_service_paid import PaidNLPService
                self._service_cache["nlp"] = PaidNLPService(self.config)
            elif self.config.ai_service_mode == AIServiceMode.COLAB_MODELS:
                from app.services.nlp_service_colab import ColabNLPService
                self._service_cache["nlp"] = ColabNLPService(self.config)
            elif self.config.ai_service_mode == AIServiceMode.HYBRID:
                from app.services.nlp_service_hybrid import HybridNLPService
                self._service_cache["nlp"] = HybridNLPService(self.config)
            else:
                from app.services.nlp_service_offline import OfflineNLPService
                self._service_cache["nlp"] = OfflineNLPService(self.config)
        
        return self._service_cache["nlp"]
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all configured AI services."""
        health_status = {}
        
        try:
            voice_service = self.get_voice_service()
            health_status["voice"] = voice_service.health_check()
        except Exception as e:
            health_status["voice"] = False
            health_status["voice_error"] = str(e)
        
        try:
            vision_service = self.get_vision_service()
            health_status["vision"] = vision_service.health_check()
        except Exception as e:
            health_status["vision"] = False
            health_status["vision_error"] = str(e)
        
        try:
            nlp_service = self.get_nlp_service()
            health_status["nlp"] = nlp_service.health_check()
        except Exception as e:
            health_status["nlp"] = False
            health_status["nlp_error"] = str(e)
        
        return health_status
    
    def switch_mode(self, new_mode: AIServiceMode):
        """Switch AI service mode and clear cache."""
        self.config.ai_service_mode = new_mode
        self._service_cache.clear()
    
    def get_cost_summary(self) -> Dict[str, float]:
        """Get cost summary for paid API usage."""
        # Implementation would track API usage costs
        return {
            "daily_cost": 0.0,
            "monthly_cost": 0.0,
            "remaining_budget": self.config.max_daily_api_cost
        }


# Global configuration instance
ai_config = AIServicesConfig()
ai_service_factory = AIServiceFactory(ai_config)


def get_ai_service_factory() -> AIServiceFactory:
    """Get the global AI service factory instance."""
    return ai_service_factory


def configure_ai_services(
    mode: AIServiceMode = None,
    colab_endpoints: Dict[str, str] = None,
    api_keys: Dict[str, str] = None
) -> AIServiceFactory:
    """Configure AI services with custom settings."""
    global ai_config, ai_service_factory
    
    if mode:
        ai_config.ai_service_mode = mode
    
    if colab_endpoints:
        if "voice" in colab_endpoints:
            ai_config.colab_voice_endpoint = colab_endpoints["voice"]
        if "vision" in colab_endpoints:
            ai_config.colab_vision_endpoint = colab_endpoints["vision"]
        if "nlp" in colab_endpoints:
            ai_config.colab_nlp_endpoint = colab_endpoints["nlp"]
    
    if api_keys:
        if "openai" in api_keys:
            ai_config.openai_api_key = api_keys["openai"]
        if "google_cloud" in api_keys:
            ai_config.google_cloud_api_key = api_keys["google_cloud"]
        if "elevenlabs" in api_keys:
            ai_config.elevenlabs_api_key = api_keys["elevenlabs"]
    
    # Recreate factory with new configuration
    ai_service_factory = AIServiceFactory(ai_config)
    return ai_service_factory