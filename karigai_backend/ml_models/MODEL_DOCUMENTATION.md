# KarigAI ML Models Documentation

## Overview

This document provides comprehensive documentation for all machine learning models used in the KarigAI system, including architectures, training procedures, performance metrics, and deployment instructions.

## Table of Contents

1. [Speech Recognition Models](#speech-recognition-models)
2. [Text-to-Speech Models](#text-to-speech-models)
3. [Computer Vision Models](#computer-vision-models)
4. [NLP Models](#nlp-models)
5. [Recommendation Models](#recommendation-models)
6. [Model Cards](#model-cards)
7. [API Reference](#api-reference)
8. [Deployment Guide](#deployment-guide)

---

## Speech Recognition Models

### Multilingual Speech Recognition

**Model Name**: `speech_recognition_v1`

**Architecture**: Wav2Vec2-based transformer model fine-tuned for Indian languages

**Supported Languages**:
- Hindi (hi)
- Malayalam (ml)
- Punjabi (pa)
- Bengali (bn)
- Tamil (ta)
- Telugu (te)
- Gujarati (gu)
- Kannada (kn)
- Marathi (mr)
- English (en)

**Training Details**:
- Base Model: facebook/wav2vec2-large-xlsr-53
- Training Data: 500+ hours of Indian language speech
- Fine-tuning: 50 epochs with learning rate 1e-4
- Optimizer: AdamW with weight decay 0.01
- Loss Function: CTC Loss

**Performance Metrics**:
- Word Error Rate (WER): <15% average across languages
- Character Error Rate (CER): <8% average
- Inference Latency: <500ms for 10-second audio
- Model Size: 1.2GB (FP32), 300MB (INT8 quantized)

**Input Format**:
- Audio: 16kHz mono WAV
- Max Duration: 30 seconds
- Preprocessing: Noise reduction, normalization

**Output Format**:
```json
{
  "text": "transcribed text",
  "confidence": 0.95,
  "language": "hi",
  "word_timestamps": [...]
}
```

---

## Text-to-Speech Models

### Multilingual TTS

**Model Name**: `text_to_speech_v1`

**Architecture**: FastSpeech2 + HiFi-GAN vocoder

**Supported Languages**: Same as speech recognition

**Training Details**:
- Base Model: Custom FastSpeech2 architecture
- Training Data: 200+ hours of high-quality speech
- Training: 100 epochs with learning rate 1e-3
- Vocoder: HiFi-GAN V1
- Loss Function: MSE + Duration Loss

**Performance Metrics**:
- Mean Opinion Score (MOS): 4.2/5.0
- Real-time Factor: 0.3 (faster than real-time)
- Inference Latency: <200ms for 10-word sentence
- Model Size: 800MB (FP32), 200MB (FP16)

**Input Format**:
```json
{
  "text": "text to synthesize",
  "language": "hi",
  "speaker_id": "default"
}
```

**Output Format**:
- Audio: 22kHz mono WAV
- Format: PCM 16-bit

---

## Computer Vision Models

### Equipment Identification

**Model Name**: `equipment_identification_v1`

**Architecture**: EfficientNet-B3 with multi-label classification head

**Categories**:
- Appliances (refrigerators, washing machines, ACs)
- Power tools (drills, saws, grinders)
- Electronics (TVs, computers, phones)
- Machinery (generators, pumps, motors)

**Training Details**:
- Base Model: EfficientNet-B3 pretrained on ImageNet
- Training Data: 50,000+ equipment images
- Fine-tuning: 50 epochs with learning rate 1e-4
- Augmentation: Rotation, brightness, contrast, occlusion
- Loss Function: Focal Loss for imbalanced classes

**Performance Metrics**:
- Top-1 Accuracy: 88%
- Top-5 Accuracy: 96%
- mAP: 0.91
- Inference Latency: <100ms per image
- Model Size: 45MB (ONNX)

**Input Format**:
- Image: RGB, 300x300 pixels
- Format: JPEG/PNG

**Output Format**:
```json
{
  "equipment_type": "washing_machine",
  "brand": "LG",
  "model": "T7288NDDLG",
  "confidence": 0.92,
  "bounding_box": [x, y, w, h]
}
```

### OCR Model

**Model Name**: `ocr_model_v1`

**Architecture**: CRNN (CNN + BiLSTM + CTC)

**Capabilities**:
- Error code recognition
- Product label reading
- Multilingual text extraction

**Training Details**:
- Architecture: ResNet34 + BiLSTM (256 hidden units)
- Training Data: 100,000+ text images (synthetic + real)
- Training: 80 epochs with learning rate 1e-3
- Augmentation: Perspective, blur, noise
- Loss Function: CTC Loss

**Performance Metrics**:
- Character Accuracy: 96%
- Word Accuracy: 92%
- Inference Latency: <50ms per text region
- Model Size: 25MB (ONNX)

### Pattern Analysis

**Model Name**: `pattern_analysis_v1`

**Architecture**: Mask R-CNN for motif detection + StyleGAN for generation

**Capabilities**:
- Traditional pattern recognition
- Motif extraction
- Design element classification
- Modern variation generation

**Training Details**:
- Detection: Mask R-CNN with ResNet50 backbone
- Training Data: 10,000+ traditional design images
- Training: 60 epochs with learning rate 1e-4
- Loss Function: Mask Loss + Box Loss + Class Loss

**Performance Metrics**:
- Motif Detection mAP: 0.87
- Segmentation IoU: 0.82
- Inference Latency: <200ms per image
- Model Size: 180MB (ONNX)

### Quality Assessment

**Model Name**: `quality_assessment_v1`

**Architecture**: Multi-task CNN (ResNet50 + regression heads)

**Product Types**:
- Saffron
- Walnuts
- Textiles
- Agricultural products

**Training Details**:
- Base Model: ResNet50 pretrained on ImageNet
- Training Data: 20,000+ product images with quality labels
- Training: 50 epochs with learning rate 1e-4
- Loss Function: MSE (quality score) + Cross-Entropy (grade)

**Performance Metrics**:
- Grading Accuracy: 90%
- Quality Score MAE: 0.08
- Inference Latency: <80ms per image
- Model Size: 95MB (ONNX)

### Crop Disease Detection

**Model Name**: `crop_disease_v1`

**Architecture**: DenseNet121 for disease classification

**Supported Crops**:
- Tomato, Potato, Wheat, Rice, Cotton, etc.

**Disease Categories**: 38 disease classes

**Training Details**:
- Base Model: DenseNet121 pretrained on ImageNet
- Training Data: PlantVillage + custom Indian crop dataset (50,000+ images)
- Training: 70 epochs with learning rate 1e-4
- Augmentation: Rotation, flip, color jitter
- Loss Function: Cross-Entropy with class weights

**Performance Metrics**:
- Classification Accuracy: 94%
- F1-Score: 0.93
- Inference Latency: <100ms per image
- Model Size: 32MB (ONNX)

### Circuit Analysis

**Model Name**: `circuit_analysis_v1`

**Architecture**: Faster R-CNN for component detection

**Capabilities**:
- Component identification (resistors, capacitors, ICs)
- Damage detection (burn marks, corrosion)
- Hotspot localization

**Training Details**:
- Architecture: Faster R-CNN with ResNet50 backbone
- Training Data: 15,000+ circuit board images
- Training: 60 epochs with learning rate 1e-4
- Loss Function: RPN Loss + Detection Loss

**Performance Metrics**:
- Component Detection mAP: 0.87
- Damage Classification Accuracy: 85%
- Inference Latency: <150ms per image
- Model Size: 160MB (ONNX)

---

## NLP Models

### Intent Recognition

**Model Name**: `intent_recognition_v1`

**Architecture**: DistilBERT fine-tuned for intent classification

**Intent Categories**:
- Invoice generation
- Repair query
- Learning request
- Equipment identification
- Translation request
- etc. (20+ intents)

**Training Details**:
- Base Model: distilbert-base-multilingual-cased
- Training Data: 50,000+ customer conversations
- Training: 30 epochs with learning rate 2e-5
- Loss Function: Cross-Entropy

**Performance Metrics**:
- Intent Accuracy: 92%
- F1-Score: 0.91
- Inference Latency: <50ms per query
- Model Size: 250MB (ONNX)

### Translation

**Model Name**: `translation_v1`

**Architecture**: mBART-based sequence-to-sequence model

**Language Pairs**: All combinations of supported languages

**Training Details**:
- Base Model: facebook/mbart-large-50-many-to-many-mmt
- Training Data: 1M+ parallel sentences
- Fine-tuning: 20 epochs with learning rate 3e-5
- Loss Function: Cross-Entropy

**Performance Metrics**:
- BLEU Score: 35+ average
- Translation Accuracy: 88%
- Inference Latency: <200ms per sentence
- Model Size: 600MB (ONNX)

### Knowledge Retrieval

**Model Name**: `knowledge_retrieval_v1`

**Architecture**: Dense Passage Retrieval (DPR) + Extractive QA

**Capabilities**:
- Semantic search over knowledge base
- Extractive question answering
- Troubleshooting guidance retrieval

**Training Details**:
- Retriever: DPR with BERT encoders
- Reader: RoBERTa for extractive QA
- Training Data: 100,000+ QA pairs from manuals
- Training: 40 epochs with learning rate 1e-5

**Performance Metrics**:
- Retrieval Recall@10: 0.82
- Answer Accuracy: 78%
- Inference Latency: <300ms per query
- Model Size: 450MB (ONNX)

### Scheme Matching

**Model Name**: `scheme_matching_v1`

**Architecture**: BERT-based classification + rule-based system

**Capabilities**:
- Eligibility assessment
- Scheme recommendation
- Form field extraction

**Training Details**:
- Base Model: bert-base-multilingual-cased
- Training Data: Government scheme documents + synthetic profiles
- Training: 25 epochs with learning rate 2e-5
- Loss Function: Binary Cross-Entropy (multi-label)

**Performance Metrics**:
- Matching Accuracy: 87%
- Precision: 0.89
- Recall: 0.85
- Inference Latency: <100ms per profile
- Model Size: 420MB (ONNX)

---

## Recommendation Models

### Learning Recommendation

**Model Name**: `learning_recommendation_v1`

**Architecture**: Hybrid collaborative + content-based filtering

**Components**:
- Matrix Factorization (user-course interactions)
- Content Embeddings (course metadata)
- Sequential Recommendation (learning paths)

**Training Details**:
- Algorithm: Neural Collaborative Filtering
- Training Data: 100,000+ user interactions
- Training: 50 epochs with learning rate 1e-3
- Loss Function: BPR Loss

**Performance Metrics**:
- NDCG@10: 0.78
- Hit Rate@10: 0.85
- Inference Latency: <50ms per user
- Model Size: 80MB (ONNX)

### Trend Analysis

**Model Name**: `trend_analysis_v1`

**Architecture**: LSTM-based time series forecasting

**Capabilities**:
- Market trend prediction
- Seasonal pattern detection
- Price forecasting

**Training Details**:
- Architecture: 3-layer LSTM (256 hidden units)
- Training Data: 2 years of market data
- Training: 100 epochs with learning rate 1e-3
- Loss Function: MSE

**Performance Metrics**:
- Trend Prediction Accuracy: 82%
- RMSE: 0.15
- Inference Latency: <30ms per prediction
- Model Size: 45MB (ONNX)

---

## Model Cards

### Model Card Template

Each model includes a model card with:

1. **Model Details**
   - Model name and version
   - Architecture description
   - Training date and framework

2. **Intended Use**
   - Primary use cases
   - Out-of-scope uses
   - Limitations

3. **Training Data**
   - Dataset description
   - Data sources
   - Preprocessing steps

4. **Performance**
   - Evaluation metrics
   - Test set results
   - Known biases

5. **Ethical Considerations**
   - Potential biases
   - Fairness considerations
   - Privacy implications

6. **Maintenance**
   - Update schedule
   - Monitoring plan
   - Contact information

---

## API Reference

### Model Inference API

All models expose a unified inference API:

```python
from ml_models.integration.service_integration import get_integrator

integrator = get_integrator()

# Load model
model = integrator.load_model("model_name")

# Run inference
result = integrator.get_inference_function("service_name")(input_data)
```

### REST API Endpoints

```
POST /api/v1/models/speech-recognition
POST /api/v1/models/text-to-speech
POST /api/v1/models/equipment-identification
POST /api/v1/models/ocr
POST /api/v1/models/pattern-analysis
POST /api/v1/models/quality-assessment
POST /api/v1/models/crop-disease
POST /api/v1/models/circuit-analysis
POST /api/v1/models/intent-recognition
POST /api/v1/models/translation
POST /api/v1/models/knowledge-retrieval
POST /api/v1/models/scheme-matching
POST /api/v1/models/learning-recommendation
POST /api/v1/models/trend-analysis
```

### Request/Response Formats

See individual model sections for specific formats.

---

## Deployment Guide

### Prerequisites

- Python 3.8+
- PyTorch 2.0+ or ONNX Runtime
- CUDA 11.8+ (for GPU inference)
- 16GB RAM minimum
- 50GB disk space for all models

### Installation

```bash
# Install dependencies
pip install -r requirements-ml.txt

# Download models
python ml_models/download_models.py

# Verify installation
python ml_models/verify_models.py
```

### Configuration

Set environment variables:

```bash
# Model mode
export MODEL_MODE=hybrid  # api, local, or hybrid

# Model directory
export MODEL_DIR=ml_models/models/exports

# Enable fallback
export ENABLE_MODEL_FALLBACK=true

# Cache settings
export ENABLE_MODEL_CACHE=true
export ENABLE_RESULT_CACHE=true
```

### Starting the Service

```bash
# Start backend with models
python main.py

# Or with Docker
docker-compose up
```

### Model Warm-up

Pre-load models at startup:

```python
from ml_models.integration.service_integration import initialize_models

model_names = [
    "speech_recognition",
    "text_to_speech",
    "equipment_identification",
    # ... other models
]

initialize_models(model_names)
```

### Performance Optimization

1. **Use ONNX Runtime** for faster inference
2. **Enable quantization** (INT8) to reduce model size
3. **Batch requests** when possible
4. **Use GPU** for vision and NLP models
5. **Enable caching** for repeated queries

### Monitoring

Monitor model performance:

```python
from ml_models.serving.model_server import get_metrics

metrics = get_metrics()
print(f"Inference latency: {metrics['latency_p95']}ms")
print(f"Throughput: {metrics['requests_per_second']}")
print(f"Cache hit rate: {metrics['cache_hit_rate']}")
```

### Troubleshooting

See [Integration README](integration/README.md) for common issues and solutions.

---

## Version History

- **v1.0.0** (2024-02-13): Initial release
  - All 14 models trained and deployed
  - ONNX export for all models
  - Hybrid mode with API fallback

---

## Contact

For questions or issues:
- GitHub Issues: [karigai/issues](https://github.com/karigai/issues)
- Email: support@karigai.com
- Documentation: [docs.karigai.com](https://docs.karigai.com)
