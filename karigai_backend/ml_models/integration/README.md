# Model Integration Guide

This directory contains the integration layer for connecting trained ML models with the KarigAI backend services.

## Overview

The integration system provides:

1. **Mode Switching**: Switch between API-based services and locally trained models
2. **Fallback Mechanisms**: Automatic fallback to API when local models fail
3. **Model Caching**: Efficient model loading and caching strategies
4. **Warm-up**: Pre-load models at startup for faster inference
5. **Service Factory**: Unified interface for creating service instances

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Service Factory                          │
│  (Decides which implementation to use based on config)       │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌───────▼────────┐
│  API Services  │       │ Local Services │
│  (OpenAI, etc) │       │ (Trained Models)│
└────────────────┘       └───────┬────────┘
                                 │
                         ┌───────▼────────┐
                         │ Model Integrator│
                         │ (Load & Cache)  │
                         └────────────────┘
```

## Configuration

Set the model mode using environment variables:

```bash
# Use API services only
MODEL_MODE=api

# Use local models only
MODEL_MODE=local

# Use local models with API fallback (recommended)
MODEL_MODE=hybrid

# Enable/disable fallback
ENABLE_MODEL_FALLBACK=true

# Model directory
MODEL_DIR=ml_models/models/exports
```

### Service-Specific Configuration

Override mode for specific services:

```bash
# Use API for speech, local for vision
SPEECH_RECOGNITION_MODE=api
VISION_MODE=local
NLP_MODE=hybrid
```

## Usage

### In Application Code

```python
from app.core.service_factory import get_service_factory

# Get service factory
factory = get_service_factory()

# Get speech recognition service (automatically uses correct implementation)
speech_service = factory.get_speech_recognition_service()

# Use the service (same interface regardless of implementation)
result = await speech_service.speech_to_text(audio_data, language="hi")
```

### Model Warm-up at Startup

```python
from ml_models.integration.service_integration import initialize_models

# Warm up models at application startup
model_names = [
    "speech_recognition",
    "text_to_speech",
    "equipment_identification",
    "ocr_model",
    # ... other models
]

initialize_models(model_names)
```

## Implementing Local Services

To create a local service implementation:

1. **Create service class** that inherits from the appropriate base class
2. **Load model** in `__init__` using the model integrator
3. **Implement inference** methods
4. **Add fallback** logic if hybrid mode is enabled

Example:

```python
from app.core.voice_engine import VoiceEngine
from ml_models.integration.service_integration import get_integrator

class LocalSpeechService(VoiceEngine):
    def __init__(self, fallback_enabled=True):
        self.fallback_enabled = fallback_enabled
        self.integrator = get_integrator()
        self.model = self.integrator.load_model("speech_recognition")
    
    async def speech_to_text(self, audio_data, language=None):
        try:
            # Run local model inference
            result = self._run_inference(audio_data, language)
            return result
        except Exception as e:
            if self.fallback_enabled:
                return await self._fallback_to_api(audio_data, language)
            raise
```

## Model Export Format

Models should be exported in ONNX format for optimal inference:

```python
# Export PyTorch model to ONNX
import torch

model = YourModel()
model.load_state_dict(torch.load("model.pt"))
model.eval()

dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    model,
    dummy_input,
    "model.onnx",
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
)
```

## Testing Integration

Test the integration with:

```bash
# Test model loading
python ml_models/integration/service_integration.py

# Test service factory
python -c "from app.core.service_factory import get_service_factory; factory = get_service_factory(); print(factory.config.model_mode)"

# Run integration tests
pytest karigai_backend/tests/test_model_integration.py
```

## Performance Optimization

### Model Caching

Models are cached after first load:

```python
# First call loads model
model1 = integrator.load_model("speech_recognition")

# Second call uses cached model
model2 = integrator.load_model("speech_recognition")  # Fast!
```

### Result Caching

Enable result caching for repeated queries:

```bash
ENABLE_RESULT_CACHE=true
RESULT_CACHE_TTL=3600  # 1 hour
```

### Batch Processing

Process multiple requests in batches:

```bash
MAX_BATCH_SIZE=8
```

## Monitoring

Monitor model performance:

- **Inference latency**: Time taken for model inference
- **Fallback rate**: How often fallback to API occurs
- **Cache hit rate**: Percentage of cached results used
- **Memory usage**: Model memory footprint

## Troubleshooting

### Model Not Found

```
FileNotFoundError: Model not found: ml_models/models/exports/speech_recognition.onnx
```

**Solution**: Export trained models to ONNX format and place in `MODEL_DIR`

### Fallback Always Triggered

```
WARNING: Falling back to API service for: speech_recognition
```

**Solution**: Check model loading errors, ensure models are properly exported

### High Memory Usage

**Solution**: 
- Reduce `MAX_BATCH_SIZE`
- Disable model caching: `ENABLE_MODEL_CACHE=false`
- Use quantized models (INT8/FP16)

## Next Steps

1. **Train models**: Complete model training (tasks 16-19)
2. **Export models**: Convert to ONNX format
3. **Implement local services**: Create local service classes for each model
4. **Test integration**: Run end-to-end tests
5. **Deploy**: Configure production environment

## Related Files

- `service_integration.py`: Core integration logic
- `app/core/model_config.py`: Configuration management
- `app/core/service_factory.py`: Service factory
- `app/services/local_*_service.py`: Local service implementations
