# NLP Models Guide for KarigAI

## Overview

This guide covers the Natural Language Processing (NLP) models for KarigAI, including intent recognition, translation, knowledge retrieval, and government scheme matching. These models enable the system to understand user queries, translate between languages, retrieve relevant information, and match users with government schemes.

## Models Overview

### 1. Intent Recognition and NLU Model
- **Architecture**: BERT/DistilBERT for intent classification
- **Purpose**: Classify user intents (invoice, repair, query, etc.) and extract entities
- **Target Accuracy**: >90% intent accuracy
- **Requirements**: 1.1, 7.5

### 2. Translation and Language Transformation Model
- **Architecture**: mBART/mT5 Transformer
- **Purpose**: Translate between Indian languages and transform language register
- **Target Performance**: >30 BLEU score
- **Requirements**: 7.2, 7.3, 18.2

### 3. Knowledge Retrieval and QA Model
- **Architecture**: Dense Passage Retrieval (DPR) or ColBERT
- **Purpose**: Retrieve relevant troubleshooting information and answer questions
- **Target Accuracy**: >75% answer accuracy
- **Requirements**: 2.2, 2.5, 20.1, 20.2

### 4. Government Scheme Matching Model
- **Architecture**: Classification model with rule-based system
- **Purpose**: Match users with eligible government schemes
- **Target Accuracy**: >85% matching accuracy
- **Requirements**: 19.1, 19.2, 19.3

## Dataset Requirements

### Intent Recognition Dataset
- **Size**: Minimum 10,000 labeled examples
- **Languages**: Hindi, English, Malayalam, Dogri, Punjabi, Bengali, Tamil, Telugu
- **Intent Classes**:
  - invoice_generation
  - repair_query
  - equipment_identification
  - quality_assessment
  - learning_request
  - document_request
  - general_query
  - complaint
  - feedback

### Translation Dataset
- **Size**: Minimum 50,000 parallel sentence pairs per language pair
- **Language Pairs**:
  - Hindi ↔ English
  - Malayalam ↔ English
  - Dogri ↔ English
  - Punjabi ↔ English
  - Bengali ↔ English
  - Tamil ↔ English
  - Telugu ↔ English
- **Register Types**: Colloquial, Formal, Technical

### Knowledge Base Dataset
- **Size**: Minimum 5,000 troubleshooting documents
- **Categories**:
  - Appliance repair manuals
  - Equipment troubleshooting guides
  - Trade-specific procedures
  - Safety guidelines
  - Material specifications
- **Format**: Question-answer pairs with context passages

### Government Scheme Dataset
- **Size**: All active government schemes (500+ schemes)
- **Information**:
  - Scheme name and description
  - Eligibility criteria
  - Application process
  - Required documents
  - Benefits and subsidies
- **Sources**: Government portals, official documents

## Data Collection Strategy

### 1. Customer Service Conversations
```python
# Collect from:
# - Simulated conversations
# - User feedback and queries
# - Trade-specific terminology databases
# - Code-mixed language examples
```

### 2. Translation Pairs
```python
# Sources:
# - Public parallel corpora (OPUS, PMIndia)
# - Government documents (bilingual)
# - News articles (multilingual)
# - Trade-specific glossaries
```

### 3. Knowledge Base
```python
# Sources:
# - Equipment manufacturer manuals
# - Online repair forums
# - YouTube tutorial transcripts
# - Trade association documents
```

### 4. Government Schemes
```python
# Sources:
# - Official government portals
# - Scheme documents (PDF extraction)
# - Eligibility calculators
# - Application forms
```

## Data Preparation Pipeline

### Step 1: Data Collection
```bash
# Run data collection notebook
jupyter notebook notebooks/03_nlp_dataset_collection.ipynb
```

### Step 2: Data Cleaning
```python
# Clean and normalize text
python utils/nlp_dataset_preparation.py --task clean --input raw/ --output processed/
```

### Step 3: Data Augmentation
```python
# Augment training data
python utils/nlp_dataset_preparation.py --task augment --input processed/ --output augmented/
```

### Step 4: Train/Val/Test Split
```python
# Split datasets (80/10/10)
python utils/nlp_dataset_preparation.py --task split --input augmented/ --output final/
```

## Model Training

### Intent Recognition Model
```bash
# Train intent recognition model
python training/train_intent_recognition.py \
  --data_dir data/processed/intent/ \
  --model_name distilbert-base-multilingual-cased \
  --epochs 10 \
  --batch_size 32 \
  --learning_rate 2e-5
```

### Translation Model
```bash
# Train translation model
python training/train_translation.py \
  --data_dir data/processed/translation/ \
  --model_name facebook/mbart-large-50 \
  --epochs 20 \
  --batch_size 16 \
  --learning_rate 3e-5
```

### Knowledge Retrieval Model
```bash
# Train knowledge retrieval model
python training/train_knowledge_retrieval.py \
  --data_dir data/processed/knowledge/ \
  --model_name facebook/dpr-ctx_encoder-multiset-base \
  --epochs 15 \
  --batch_size 32 \
  --learning_rate 1e-5
```

### Government Scheme Matching Model
```bash
# Train scheme matching model
python training/train_scheme_matching.py \
  --data_dir data/processed/schemes/ \
  --model_name distilbert-base-multilingual-cased \
  --epochs 10 \
  --batch_size 32 \
  --learning_rate 2e-5
```

## Model Evaluation

### Intent Recognition Metrics
- Accuracy
- Precision, Recall, F1 per intent class
- Confusion matrix
- Slot filling accuracy

### Translation Metrics
- BLEU score
- METEOR score
- chrF score
- Human evaluation (fluency, adequacy)

### Knowledge Retrieval Metrics
- Mean Reciprocal Rank (MRR)
- Recall@k (k=1,5,10)
- Answer accuracy
- Retrieval latency

### Scheme Matching Metrics
- Matching accuracy
- Precision, Recall, F1
- False positive rate
- Coverage (% of eligible users matched)

## Deployment

### Model Export
```bash
# Convert to ONNX format
python utils/export_to_onnx.py \
  --model_path models/checkpoints/intent_recognition.pt \
  --output_path models/exports/intent_recognition.onnx
```

### API Deployment
```bash
# Start NLP inference API
python inference/nlp_inference_api.py \
  --host 0.0.0.0 \
  --port 8001 \
  --models_dir models/exports/
```

## Integration with KarigAI Backend

The trained NLP models integrate with existing services:

1. **Intent Recognition** → `voice_service.py`, `translation_service.py`
2. **Translation** → `translation_service.py`, `multilingual_content_service.py`
3. **Knowledge Retrieval** → `equipment_vision_service.py`, `learning_service.py`
4. **Scheme Matching** → New service: `scheme_matching_service.py`

## Performance Optimization

### Model Quantization
```python
# Quantize models to INT8
python utils/quantize_model.py \
  --model_path models/exports/intent_recognition.onnx \
  --output_path models/exports/intent_recognition_int8.onnx \
  --quantization_type int8
```

### Model Pruning
```python
# Prune models to reduce size
python utils/prune_model.py \
  --model_path models/checkpoints/translation.pt \
  --pruning_ratio 0.3 \
  --output_path models/checkpoints/translation_pruned.pt
```

### Caching Strategy
- Cache frequent queries and responses
- Use Redis for distributed caching
- Implement LRU eviction policy

## Troubleshooting

### Low Accuracy
- Increase training data size
- Try different model architectures
- Adjust hyperparameters
- Add data augmentation

### Slow Inference
- Use model quantization
- Implement batch processing
- Use GPU acceleration
- Cache frequent queries

### Memory Issues
- Use smaller model variants (DistilBERT instead of BERT)
- Implement model pruning
- Use gradient checkpointing during training
- Reduce batch size

## Next Steps

1. Collect and prepare datasets (Task 18.1)
2. Train intent recognition model (Task 18.2)
3. Train translation model (Task 18.3)
4. Train knowledge retrieval model (Task 18.4)
5. Train scheme matching model (Task 18.5)
6. Deploy models and create API (Task 18.6)

## Resources

- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [OPUS Parallel Corpora](https://opus.nlpl.eu/)
- [PMIndia Corpus](https://github.com/AI4Bharat/indicnlp_corpus)
- [DPR Documentation](https://github.com/facebookresearch/DPR)
- [mBART Documentation](https://huggingface.co/docs/transformers/model_doc/mbart)


## API Deployment Guide

### Starting the NLP Inference API

The NLP inference API provides REST endpoints for all NLP models:

```bash
# Start the API server
python inference/nlp_inference_api.py \
  --host 0.0.0.0 \
  --port 8001 \
  --models_dir models/checkpoints/
```

### API Endpoints

1. **Intent Recognition**: `POST /intent`
   - Recognizes user intent and extracts entities
   - Request: `{"text": "मुझे एक बिल बनाना है", "language": "hi"}`
   - Response: `{"intent": "invoice_generation", "confidence": 0.95, "entities": []}`

2. **Translation**: `POST /translate`
   - Translates between Indian languages
   - Request: `{"text": "मुझे मदद चाहिए", "source_lang": "hi", "target_lang": "en"}`
   - Response: `{"translated_text": "I need help", "source_lang": "hi", "target_lang": "en"}`

3. **Knowledge Retrieval**: `POST /knowledge`
   - Retrieves troubleshooting information
   - Request: `{"question": "How to fix AC error E01?", "top_k": 5}`
   - Response: `{"answers": [...], "confidence_scores": [...]}`

4. **Scheme Matching**: `POST /schemes`
   - Matches users with eligible government schemes
   - Request: `{"user_profile": {"age": 35, "income": 200000, ...}, "top_k": 5}`
   - Response: `{"schemes": [...], "eligibility_scores": [...]}`

### Docker Deployment

Create a Docker container for the NLP API:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements-ml.txt .
RUN pip install -r requirements-ml.txt

COPY ml_models/ .
EXPOSE 8001

CMD ["python", "inference/nlp_inference_api.py"]
```

Build and run:
```bash
docker build -t karigai-nlp-api .
docker run -p 8001:8001 karigai-nlp-api
```

### Testing the API

```bash
# Health check
curl http://localhost:8001/health

# Test intent recognition
curl -X POST http://localhost:8001/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "मुझे एक बिल बनाना है", "language": "hi"}'
```

### Integration with KarigAI Backend

The NLP models integrate with existing KarigAI services:

1. **Intent Recognition** → `voice_service.py`, `translation_service.py`
2. **Translation** → `translation_service.py`, `multilingual_content_service.py`
3. **Knowledge Retrieval** → `equipment_vision_service.py`, `learning_service.py`
4. **Scheme Matching** → New service: `scheme_matching_service.py`

### Performance Monitoring

Monitor API performance:
- Request latency
- Model inference time
- Cache hit rate
- Error rate

Use Prometheus and Grafana for monitoring dashboards.
