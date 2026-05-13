"""
Tests for Model Integration

Tests the integration of trained ML models with backend services,
including mode switching, fallback mechanisms, and caching.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

try:
    from app.core.model_config import ModelConfig, ModelMode, get_model_config
    from app.core.service_factory import ServiceFactory, get_service_factory
    from ml_models.integration.service_integration import ModelServiceIntegrator, get_integrator
except ImportError as e:
    pytest.skip(f"Skipping tests due to import error: {e}", allow_module_level=True)


class TestModelConfig:
    """Test model configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ModelConfig()
        assert config.model_mode == ModelMode.HYBRID
        assert config.enable_fallback is True
        assert config.enable_model_cache is True
    
    def test_get_mode_for_service(self):
        """Test getting mode for specific service."""
        config = ModelConfig(
            model_mode=ModelMode.HYBRID,
            speech_recognition_mode=ModelMode.API
        )
        
        # Service-specific mode
        assert config.get_mode_for_service("speech_recognition") == ModelMode.API
        
        # Global mode for other services
        assert config.get_mode_for_service("translation") == ModelMode.HYBRID
    
    def test_should_use_local_model(self):
        """Test local model usage decision."""
        config = ModelConfig(model_mode=ModelMode.LOCAL)
        assert config.should_use_local_model("speech_recognition") is True
        
        config = ModelConfig(model_mode=ModelMode.API)
        assert config.should_use_local_model("speech_recognition") is False
        
        config = ModelConfig(model_mode=ModelMode.HYBRID)
        assert config.should_use_local_model("speech_recognition") is True
    
    def test_can_fallback_to_api(self):
        """Test fallback decision."""
        config = ModelConfig(
            model_mode=ModelMode.HYBRID,
            enable_fallback=True
        )
        assert config.can_fallback_to_api("speech_recognition") is True
        
        config = ModelConfig(
            model_mode=ModelMode.LOCAL,
            enable_fallback=True
        )
        assert config.can_fallback_to_api("speech_recognition") is False


class TestModelServiceIntegrator:
    """Test model service integrator."""
    
    def test_initialization(self):
        """Test integrator initialization."""
        integrator = ModelServiceIntegrator()
        assert integrator.model_dir.name == "exports"
        assert integrator.fallback_enabled is True
        assert len(integrator.models) == 0
    
    def test_model_caching(self):
        """Test model caching mechanism."""
        integrator = ModelServiceIntegrator()
        
        # Mock model loading
        with patch.object(integrator, 'load_model') as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model
            
            # First call should load
            model1 = integrator.load_model("test_model")
            assert mock_load.call_count == 1
            
            # Second call should use cache
            model2 = integrator.load_model("test_model")
            assert mock_load.call_count == 1  # Not called again
            assert model1 is model2
    
    def test_get_inference_function(self):
        """Test getting inference functions."""
        integrator = ModelServiceIntegrator()
        
        # Test valid service
        func = integrator.get_inference_function("speech_recognition")
        assert func is not None
        assert callable(func)
        
        # Test invalid service
        func = integrator.get_inference_function("invalid_service")
        assert func is None
    
    def test_inference_with_fallback(self):
        """Test inference with fallback mechanism."""
        integrator = ModelServiceIntegrator()
        integrator.fallback_enabled = True
        
        # Mock model loading to fail
        with patch.object(integrator, 'load_model') as mock_load:
            mock_load.side_effect = FileNotFoundError("Model not found")
            
            # Should fallback without raising exception
            result = integrator._speech_recognition_inference(b"audio_data", "hi")
            assert result is not None
            assert "fallback" in result or "text" in result


class TestServiceFactory:
    """Test service factory."""
    
    def test_initialization(self):
        """Test factory initialization."""
        factory = ServiceFactory()
        assert factory.config is not None
        assert len(factory._service_cache) == 0
    
    def test_service_caching(self):
        """Test service instance caching."""
        factory = ServiceFactory()
        
        # Mock service creation
        with patch('app.services.whisper_stt_service.WhisperSTTService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # First call should create service
            service1 = factory.get_speech_recognition_service()
            
            # Second call should use cached service
            service2 = factory.get_speech_recognition_service()
            assert service1 is service2
    
    def test_clear_cache(self):
        """Test cache clearing."""
        factory = ServiceFactory()
        
        # Add something to cache
        factory._service_cache["test"] = Mock()
        assert len(factory._service_cache) == 1
        
        # Clear cache
        factory.clear_cache()
        assert len(factory._service_cache) == 0
    
    def test_reload_config(self):
        """Test configuration reload."""
        factory = ServiceFactory()
        
        # Add something to cache
        factory._service_cache["test"] = Mock()
        
        # Reload config
        factory.reload_config()
        
        # Cache should be cleared
        assert len(factory._service_cache) == 0


class TestLocalServiceIntegration:
    """Test local service integration."""
    
    @pytest.mark.asyncio
    async def test_local_speech_service_fallback(self):
        """Test local speech service with fallback."""
        from app.services.local_speech_service import LocalSpeechRecognitionService
        from app.core.voice_engine import AudioData
        
        service = LocalSpeechRecognitionService(fallback_enabled=True)
        
        # Create test audio data
        audio_data = AudioData(
            data=b"test_audio_data",
            sample_rate=16000,
            channels=1,
            duration=1.0
        )
        
        # Mock the fallback method
        with patch.object(service, '_fallback_to_api') as mock_fallback:
            mock_fallback.return_value = {
                "text": "fallback transcription",
                "confidence": 0.95,
                "language": "hi",
                "model": "api_fallback"
            }
            
            # Should use fallback since model is not loaded
            result = await service.speech_to_text(audio_data, "hi")
            
            # Verify result
            assert result is not None
            assert "text" in result


class TestEndToEndIntegration:
    """Test end-to-end integration scenarios."""
    
    def test_api_mode_integration(self):
        """Test integration in API mode."""
        # Set API mode
        config = ModelConfig(model_mode=ModelMode.API)
        factory = ServiceFactory()
        factory.config = config
        
        # Should use API services
        assert config.should_use_api("speech_recognition") is True
        assert config.should_use_local_model("speech_recognition") is False
    
    def test_local_mode_integration(self):
        """Test integration in local mode."""
        # Set local mode
        config = ModelConfig(model_mode=ModelMode.LOCAL)
        factory = ServiceFactory()
        factory.config = config
        
        # Should use local models
        assert config.should_use_local_model("speech_recognition") is True
        assert config.should_use_api("speech_recognition") is False
    
    def test_hybrid_mode_integration(self):
        """Test integration in hybrid mode."""
        # Set hybrid mode
        config = ModelConfig(
            model_mode=ModelMode.HYBRID,
            enable_fallback=True
        )
        factory = ServiceFactory()
        factory.config = config
        
        # Should use local models with fallback
        assert config.should_use_local_model("speech_recognition") is True
        assert config.can_fallback_to_api("speech_recognition") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
