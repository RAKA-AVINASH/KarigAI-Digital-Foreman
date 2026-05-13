# Building Multilingual Speech Recognition Model for KarigAI

This guide provides step-by-step instructions for building a custom multilingual speech recognition model fine-tuned for Indian languages.

## Overview

We'll use OpenAI's Whisper model as a base and fine-tune it on Indian language datasets. Whisper is a state-of-the-art speech recognition model that already supports multiple languages, making it an excellent starting point.

## Architecture Choice

### Option 1: Whisper (Recommended)

**Pros:**
- Pre-trained on 680,000 hours of multilingual data
- Already supports Hindi, Tamil, Telugu (partial support for others)
- Excellent transfer learning capabilities
- Robust to accents and noise

**Model Sizes:**
- `whisper-tiny`: 39M parameters, fastest inference
- `whisper-base`: 74M parameters, good balance
- `whisper-small`: 244M parameters, better accuracy (recommended)
- `whisper-medium`: 769M parameters, high accuracy
- `whisper-large`: 1550M parameters, best accuracy (requires significant compute)

### Option 2: Wav2Vec2

**Pros:**
- Self-supervised pre-training
- Good for low-resource languages
- Efficient fine-tuning

**Cons:**
- Requires more data for good performance
- Less robust to noise than Whisper

## Prerequisites

### Hardware Requirements

**Minimum (for whisper-small):**
- GPU: 8 GB VRAM (RTX 3060 Ti or better)
- RAM: 16 GB
- Storage: 100 GB

**Recommended (for whisper-medium):**
- GPU: 16 GB VRAM (RTX 4080 or A4000)
- RAM: 32 GB
- Storage: 200 GB

**Training Time Estimates:**
- whisper-small on 100 hours: 2-3 days on RTX 3090
- whisper-medium on 100 hours: 4-5 days on RTX 3090

### Software Requirements

```bash
pip install transformers datasets evaluate jiwer librosa soundfile
```

## Step-by-Step Training Process

### Step 1: Prepare Datasets

Ensure you've completed Task 16.2 and have:
- ✅ Downloaded Indian language datasets
- ✅ Created train/val/test splits
- ✅ Generated manifest files

Verify datasets:
```python
from ml_models.utils.dataset_preparation import DatasetManager

manager = DatasetManager()
datasets = manager.list_datasets()
for ds in datasets:
    print(f"{ds['id']}: {ds['splits']}")
```

### Step 2: Configure Training

Edit `ml_models/configs/training_config.yaml`:

```yaml
speech_recognition:
  model_name: "openai/whisper-small"
  batch_size: 8  # Adjust based on GPU memory
  learning_rate: 1e-5
  num_epochs: 20
  warmup_steps: 500
  gradient_accumulation_steps: 4  # Effective batch size = 8 * 4 = 32
  freeze_encoder: false  # Set to true for faster training with less data
  gradient_checkpointing: true  # Saves memory
```

### Step 3: Start Training

```bash
cd karigai_backend/ml_models
python training/train_speech_recognition.py
```

Or use the training script with custom config:

```python
from training.train_speech_recognition import SpeechRecognitionTrainer, SpeechRecognitionConfig

config = SpeechRecognitionConfig(
    model_name="openai/whisper-small",
    languages=['hi', 'ml', 'pa'],  # Start with fewer languages
    batch_size=8,
    num_epochs=20,
    learning_rate=1e-5
)

trainer = SpeechRecognitionTrainer(config)
trainer.train()
```

### Step 4: Monitor Training

**MLflow UI:**
```bash
cd ml_models
mlflow ui
```

Open http://localhost:5000 to view:
- Training loss curves
- Validation WER (Word Error Rate)
- Learning rate schedule
- GPU utilization

**Key Metrics to Watch:**
- **Training Loss:** Should decrease steadily
- **Validation WER:** Should decrease (lower is better)
  - Target: <15% WER for good performance
  - Acceptable: <25% WER for initial models
- **Overfitting:** If val WER increases while train loss decreases

### Step 5: Evaluate Model

After training, evaluate on test set:

```python
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import torch
import librosa

# Load model
model_path = "./ml_models/models/speech_recognition"
processor = WhisperProcessor.from_pretrained(model_path)
model = WhisperForConditionalGeneration.from_pretrained(model_path)
model.eval()

# Test on audio file
audio_path = "test_audio.wav"
audio, sr = librosa.load(audio_path, sr=16000)

# Generate transcription
input_features = processor(audio, sampling_rate=16000, return_tensors="pt").input_features
predicted_ids = model.generate(input_features)
transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

print(f"Transcription: {transcription}")
```

### Step 6: Calculate WER on Test Set

```python
import evaluate
from tqdm import tqdm

wer_metric = evaluate.load("wer")

predictions = []
references = []

# Load test manifest
with open("data/processed/common_voice_hi/test_manifest.json", 'r') as f:
    for line in tqdm(f):
        sample = json.loads(line)
        
        # Load and transcribe audio
        audio, sr = librosa.load(sample['audio_filepath'], sr=16000)
        input_features = processor(audio, sampling_rate=16000, return_tensors="pt").input_features
        
        with torch.no_grad():
            predicted_ids = model.generate(input_features)
        
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        
        predictions.append(transcription)
        references.append(sample['text'])

# Calculate WER
wer = wer_metric.compute(predictions=predictions, references=references)
print(f"Test WER: {wer:.2%}")
```

## Fine-Tuning Strategies

### Strategy 1: Freeze Encoder (Faster, Less Data)

```python
config = SpeechRecognitionConfig(
    freeze_encoder=True,  # Only train decoder
    num_epochs=10,
    learning_rate=1e-4  # Higher LR for decoder-only training
)
```

**When to use:**
- Limited training data (<50 hours)
- Limited compute resources
- Quick prototyping

### Strategy 2: Full Fine-Tuning (Better Performance)

```python
config = SpeechRecognitionConfig(
    freeze_encoder=False,  # Train entire model
    num_epochs=20,
    learning_rate=1e-5  # Lower LR for full model
)
```

**When to use:**
- Sufficient training data (>100 hours)
- Good compute resources
- Production deployment

### Strategy 3: Progressive Unfreezing

```python
# Phase 1: Train decoder only (5 epochs)
config1 = SpeechRecognitionConfig(freeze_encoder=True, num_epochs=5)
trainer1 = SpeechRecognitionTrainer(config1)
trainer1.train()

# Phase 2: Unfreeze and train full model (15 epochs)
config2 = SpeechRecognitionConfig(
    freeze_encoder=False,
    num_epochs=15,
    learning_rate=5e-6  # Lower LR for fine-tuning
)
trainer2 = SpeechRecognitionTrainer(config2)
trainer2.train()
```

## Language-Specific Fine-Tuning

### Adding Language Identification

Whisper can automatically detect languages, but you can force a specific language:

```python
# Force Hindi transcription
forced_decoder_ids = processor.get_decoder_prompt_ids(language="hindi", task="transcribe")
predicted_ids = model.generate(input_features, forced_decoder_ids=forced_decoder_ids)
```

### Multi-Task Learning

Train on multiple tasks simultaneously:
- Transcription (speech-to-text)
- Translation (speech-to-English)
- Language identification

```python
# Configure for multi-task
model.config.forced_decoder_ids = None  # Allow model to choose task
```

## Optimization Techniques

### 1. Mixed Precision Training

Automatically enabled in training script:
```python
training_args = Seq2SeqTrainingArguments(
    fp16=torch.cuda.is_available(),  # Use FP16 on GPU
    ...
)
```

**Benefits:**
- 2x faster training
- 50% less memory usage
- Minimal accuracy loss

### 2. Gradient Accumulation

Simulate larger batch sizes:
```python
config = SpeechRecognitionConfig(
    batch_size=4,  # Actual batch size per GPU
    gradient_accumulation_steps=8,  # Effective batch size = 32
)
```

### 3. Gradient Checkpointing

Trade compute for memory:
```python
config = SpeechRecognitionConfig(
    gradient_checkpointing=True,  # Saves ~30% memory
)
```

## Handling Trade-Specific Vocabulary

### Option 1: Add Custom Tokens

```python
# Add trade-specific tokens to tokenizer
new_tokens = ["पाइप", "तार", "लकड़ी", "इंजन"]
processor.tokenizer.add_tokens(new_tokens)
model.resize_token_embeddings(len(processor.tokenizer))
```

### Option 2: Post-Processing Correction

```python
# Create trade vocabulary dictionary
trade_vocab = {
    "pipe": "पाइप",
    "wire": "तार",
    "wood": "लकड़ी"
}

def correct_transcription(text, vocab_dict):
    for eng, hindi in vocab_dict.items():
        text = text.replace(eng, hindi)
    return text

transcription = correct_transcription(transcription, trade_vocab)
```

## Confidence Scoring

Implement confidence scoring for predictions:

```python
def transcribe_with_confidence(audio, model, processor):
    input_features = processor(audio, sampling_rate=16000, return_tensors="pt").input_features
    
    # Generate with output scores
    outputs = model.generate(
        input_features,
        return_dict_in_generate=True,
        output_scores=True
    )
    
    # Calculate confidence from scores
    scores = outputs.scores
    confidence = torch.exp(torch.stack(scores).mean())
    
    transcription = processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0]
    
    return transcription, confidence.item()
```

## Model Export

### Export to ONNX

```python
from optimum.onnxruntime import ORTModelForSpeechSeq2Seq

# Convert to ONNX
ort_model = ORTModelForSpeechSeq2Seq.from_pretrained(
    model_path,
    export=True
)

# Save ONNX model
ort_model.save_pretrained("./ml_models/models/exports/whisper_onnx")
```

**Benefits:**
- Faster inference (1.5-2x speedup)
- Smaller model size
- Cross-platform compatibility

### Quantization

```python
from optimum.onnxruntime import ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig

# Quantize to INT8
quantizer = ORTQuantizer.from_pretrained(ort_model)
qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False)
quantizer.quantize(save_dir="./ml_models/models/exports/whisper_quantized", quantization_config=qconfig)
```

**Benefits:**
- 4x smaller model size
- 2-3x faster inference
- Minimal accuracy loss (<2% WER increase)

## Troubleshooting

### Issue: Out of Memory (OOM)

**Solutions:**
1. Reduce batch size: `batch_size=4` or `batch_size=2`
2. Increase gradient accumulation: `gradient_accumulation_steps=8`
3. Enable gradient checkpointing: `gradient_checkpointing=True`
4. Use smaller model: `whisper-base` instead of `whisper-small`
5. Reduce max audio duration: `max_duration_seconds=20`

### Issue: High WER (>30%)

**Solutions:**
1. Train for more epochs
2. Increase dataset size
3. Improve data quality (check transcripts)
4. Use larger model (whisper-medium)
5. Adjust learning rate (try 5e-6 or 2e-5)
6. Add more data augmentation

### Issue: Overfitting

**Solutions:**
1. Add dropout: `model.config.dropout = 0.1`
2. Increase weight decay: `weight_decay=0.1`
3. Use early stopping
4. Add more training data
5. Use data augmentation

### Issue: Slow Training

**Solutions:**
1. Use mixed precision: `fp16=True`
2. Increase batch size (if memory allows)
3. Use gradient accumulation
4. Enable gradient checkpointing
5. Use faster GPU or multiple GPUs

## Performance Benchmarks

### Expected WER by Language (after fine-tuning)

| Language | Dataset Size | whisper-small WER | whisper-medium WER |
|----------|--------------|-------------------|---------------------|
| Hindi    | 100 hours    | 12-15%           | 8-10%              |
| Malayalam| 50 hours     | 18-22%           | 12-15%             |
| Tamil    | 80 hours     | 15-18%           | 10-12%             |
| Telugu   | 80 hours     | 15-18%           | 10-12%             |
| Bengali  | 60 hours     | 16-20%           | 11-14%             |
| Punjabi  | 40 hours     | 20-25%           | 15-18%             |

### Inference Speed

| Model          | GPU          | Real-time Factor |
|----------------|--------------|------------------|
| whisper-tiny   | RTX 3060     | 0.05x           |
| whisper-base   | RTX 3060     | 0.08x           |
| whisper-small  | RTX 3060     | 0.15x           |
| whisper-medium | RTX 3090     | 0.25x           |

*Real-time factor: 0.1x means 10 seconds of audio processed in 1 second*

## Next Steps

After training the speech recognition model:

1. ✅ Evaluate on test set (target: <15% WER)
2. ✅ Export to ONNX for production
3. ✅ Integrate with backend API
4. ➡️  Proceed to Task 16.4 (Text-to-Speech model)

## Resources

- **Whisper Paper:** https://arxiv.org/abs/2212.04356
- **Hugging Face Whisper:** https://huggingface.co/docs/transformers/model_doc/whisper
- **Fine-tuning Guide:** https://huggingface.co/blog/fine-tune-whisper
- **WER Metric:** https://huggingface.co/spaces/evaluate-metric/wer
