# Text-to-Speech Model Training Guide for KarigAI

This guide provides instructions for building a custom text-to-speech (TTS) model for Indian languages.

## Overview

We'll build a TTS system that can generate natural-sounding speech in multiple Indian languages. The system consists of two main components:

1. **Acoustic Model** (Tacotron2/FastSpeech2): Converts text to mel spectrograms
2. **Vocoder** (HiFi-GAN/WaveGlow): Converts mel spectrograms to audio waveforms

## Architecture Options

### Option 1: Tacotron2 + HiFi-GAN (Recommended)

**Tacotron2:**
- Sequence-to-sequence model with attention
- Generates mel spectrograms from text
- Good quality, moderate training time

**HiFi-GAN:**
- Neural vocoder
- Fast inference
- High quality audio generation

### Option 2: FastSpeech2 + HiFi-GAN

**FastSpeech2:**
- Non-autoregressive model
- Faster inference than Tacotron2
- Requires duration predictor

### Option 3: VITS (End-to-End)

**VITS:**
- Single model for text-to-audio
- No separate vocoder needed
- State-of-the-art quality

## Prerequisites

### Hardware Requirements

**Minimum:**
- GPU: 8 GB VRAM
- RAM: 16 GB
- Storage: 50 GB

**Recommended:**
- GPU: 16 GB VRAM (RTX 4080 or A4000)
- RAM: 32 GB
- Storage: 100 GB

**Training Time:**
- Tacotron2: 3-5 days on RTX 3090 (100 hours of data)
- HiFi-GAN: 1-2 days on RTX 3090

### Software Requirements

```bash
pip install torch torchaudio librosa soundfile
pip install phonemizer  # For text preprocessing
```

## Data Preparation

### Dataset Requirements

**Quality Criteria:**
- High-quality studio recordings
- Single speaker per model (or multi-speaker with speaker embeddings)
- Clear pronunciation
- Minimal background noise
- Consistent recording environment

**Quantity:**
- Minimum: 5 hours per language
- Recommended: 20+ hours per language
- Professional: 50+ hours per language

### Data Sources

1. **IIT Madras Indic TTS Database**
   - High-quality recordings
   - Multiple Indian languages
   - Professional voice actors

2. **Custom Recordings**
   - Record using professional microphone
   - Quiet studio environment
   - Consistent speaking style

### Recording Guidelines

**Equipment:**
- Professional USB microphone (e.g., Blue Yeti, Audio-Technica AT2020)
- Pop filter
- Acoustic treatment (foam panels)

**Settings:**
- Sample rate: 22050 Hz or 44100 Hz
- Bit depth: 16-bit or 24-bit
- Format: WAV (uncompressed)
- Mono channel

**Speaking Guidelines:**
- Consistent pace and volume
- Clear pronunciation
- Natural intonation
- Avoid breathing sounds
- Pause between sentences

## Training Process

### Step 1: Prepare TTS Dataset

```python
from ml_models.utils.dataset_preparation import DatasetManager

manager = DatasetManager()

# Register TTS dataset
manager.register_dataset(
    name="indic_tts",
    language="hi",
    audio_dir=Path("data/raw/indic_tts_hi/audio"),
    transcript_file=Path("data/raw/indic_tts_hi/transcripts.txt")
)

# Split dataset
manager.split_dataset("indic_tts_hi", train_ratio=0.9, val_ratio=0.05, test_ratio=0.05)
```

### Step 2: Text Preprocessing

```python
from phonemizer import phonemize

def preprocess_text(text, language='hi'):
    """Convert text to phonemes."""
    # Normalize text
    text = text.lower().strip()
    
    # Convert to phonemes
    phonemes = phonemize(
        text,
        language=language,
        backend='espeak',
        strip=True
    )
    
    return phonemes

# Example
text = "नमस्ते, आप कैसे हैं?"
phonemes = preprocess_text(text, language='hi')
print(phonemes)
```

### Step 3: Train Tacotron2

```bash
cd ml_models
python training/train_tts.py
```

Or with custom config:

```python
from training.train_tts import TTSTrainer, TTSConfig, TTSDataset

config = TTSConfig(
    model_type="tacotron2",
    languages=['hi'],
    batch_size=16,
    learning_rate=1e-4,
    num_epochs=100
)

# Load dataset
train_dataset = TTSDataset(
    manifest_file="data/processed/tts_hi/train_manifest.json",
    sample_rate=22050
)

# Train
trainer = TTSTrainer(config)
trainer.train(train_dataset)
```

### Step 4: Train Vocoder (HiFi-GAN)

```python
# Use pre-trained HiFi-GAN or train from scratch
# Pre-trained models available at: https://github.com/jik876/hifi-gan

from hifigan import HiFiGAN

vocoder = HiFiGAN.from_pretrained("hifigan-universal-v1")
```

### Step 5: Inference

```python
import torch
from training.train_tts import Tacotron2Model, TTSConfig

# Load model
checkpoint = torch.load("models/tts/tts_model.pt")
config = checkpoint['config']
char_to_idx = checkpoint['char_to_idx']

model = Tacotron2Model(config, len(char_to_idx))
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

# Generate speech
text = "नमस्ते"
text_sequence = torch.LongTensor([char_to_idx.get(c, 0) for c in text]).unsqueeze(0)

with torch.no_grad():
    mel_output = model.inference(model.encode(text_sequence))

# Convert mel to audio using vocoder
audio = vocoder(mel_output)

# Save audio
import soundfile as sf
sf.write("output.wav", audio.cpu().numpy(), 22050)
```

## Multi-Speaker TTS

### Adding Speaker Embeddings

```python
class MultiSpeakerTacotron2(nn.Module):
    def __init__(self, config, vocab_size, num_speakers):
        super().__init__()
        self.speaker_embedding = nn.Embedding(num_speakers, config.encoder_embedding_dim)
        # ... rest of model
    
    def forward(self, text_inputs, speaker_ids, mel_targets=None):
        # Get speaker embedding
        speaker_emb = self.speaker_embedding(speaker_ids)
        
        # Add to encoder output
        encoder_outputs = self.encode(text_inputs)
        encoder_outputs = encoder_outputs + speaker_emb.unsqueeze(1)
        
        # ... rest of forward pass
```

### Training Multi-Speaker Model

```python
config = TTSConfig(
    model_type="tacotron2",
    num_speakers=5,  # Number of different speakers
    batch_size=16
)

# Dataset should include speaker IDs
# manifest format: {"audio_filepath": "...", "text": "...", "speaker_id": 0}
```

## Voice Cloning

### Few-Shot Voice Cloning

```python
# Use speaker encoder to extract voice characteristics
from resemblyzer import VoiceEncoder

encoder = VoiceEncoder()

# Extract speaker embedding from reference audio
reference_audio, sr = librosa.load("reference_voice.wav", sr=16000)
speaker_embedding = encoder.embed_utterance(reference_audio)

# Use embedding for synthesis
mel_output = model.inference(text_sequence, speaker_embedding=speaker_embedding)
```

## Optimization

### Model Quantization

```python
# Quantize to INT8
quantized_model = torch.quantization.quantize_dynamic(
    model,
    {nn.Linear, nn.LSTM},
    dtype=torch.qint8
)

# Save quantized model
torch.save(quantized_model.state_dict(), "tts_quantized.pt")
```

### ONNX Export

```python
# Export Tacotron2 to ONNX
dummy_input = torch.randint(0, vocab_size, (1, 50))
torch.onnx.export(
    model,
    dummy_input,
    "tts_model.onnx",
    input_names=['text'],
    output_names=['mel_spectrogram'],
    dynamic_axes={'text': {1: 'sequence_length'}}
)
```

## Evaluation Metrics

### Mean Opinion Score (MOS)

Subjective quality evaluation (1-5 scale):
- 5: Excellent
- 4: Good
- 3: Fair
- 2: Poor
- 1: Bad

**Target:** MOS > 4.0 for production

### Mel Cepstral Distortion (MCD)

Objective quality metric:
```python
from scipy.spatial.distance import euclidean

def calculate_mcd(mel_pred, mel_target):
    """Calculate Mel Cepstral Distortion."""
    return (10 / np.log(10)) * np.mean(euclidean(mel_pred, mel_target))

# Target: MCD < 5.0 for good quality
```

### Real-Time Factor (RTF)

```python
import time

start = time.time()
audio = synthesize(text)
end = time.time()

audio_duration = len(audio) / sample_rate
synthesis_time = end - start
rtf = synthesis_time / audio_duration

print(f"RTF: {rtf:.2f}x")
# Target: RTF < 0.5 for real-time synthesis
```

## Troubleshooting

### Issue: Robotic/Unnatural Voice

**Solutions:**
1. Increase training data (20+ hours)
2. Improve data quality (studio recordings)
3. Train for more epochs
4. Use better vocoder (HiFi-GAN instead of WaveGlow)
5. Add prosody modeling

### Issue: Mispronunciation

**Solutions:**
1. Use phoneme-based input instead of characters
2. Add pronunciation dictionary
3. Improve text preprocessing
4. Add more training examples with correct pronunciation

### Issue: Slow Inference

**Solutions:**
1. Use FastSpeech2 instead of Tacotron2
2. Quantize model to INT8
3. Use ONNX Runtime
4. Batch processing
5. GPU inference

### Issue: Inconsistent Quality

**Solutions:**
1. Ensure consistent recording environment
2. Use single speaker
3. Normalize audio levels
4. Remove outliers from dataset
5. Add data augmentation

## Performance Benchmarks

### Expected Quality (MOS)

| Model | Data Size | MOS Score |
|-------|-----------|-----------|
| Tacotron2 + WaveGlow | 5 hours | 3.5-3.8 |
| Tacotron2 + HiFi-GAN | 5 hours | 3.8-4.1 |
| Tacotron2 + HiFi-GAN | 20 hours | 4.1-4.3 |
| FastSpeech2 + HiFi-GAN | 20 hours | 4.2-4.4 |
| VITS | 20 hours | 4.3-4.5 |

### Inference Speed

| Model | GPU | RTF |
|-------|-----|-----|
| Tacotron2 | RTX 3060 | 0.3x |
| FastSpeech2 | RTX 3060 | 0.1x |
| VITS | RTX 3060 | 0.2x |

## Integration with KarigAI

### API Endpoint

```python
from fastapi import FastAPI
import torch

app = FastAPI()

# Load model
model = load_tts_model()
vocoder = load_vocoder()

@app.post("/tts/synthesize")
async def synthesize_speech(text: str, language: str = "hi"):
    # Generate mel spectrogram
    mel = model.synthesize(text, language)
    
    # Generate audio
    audio = vocoder(mel)
    
    return {"audio": audio.tolist(), "sample_rate": 22050}
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def synthesize_cached(text, language):
    """Cache frequently used phrases."""
    return synthesize_speech(text, language)
```

## Next Steps

After training TTS model:

1. ✅ Evaluate MOS score (target: >4.0)
2. ✅ Measure inference speed (target: RTF <0.5)
3. ✅ Export to ONNX for production
4. ✅ Integrate with backend API
5. ➡️  Proceed to Task 16.5 (Model deployment)

## Resources

- **Tacotron2 Paper:** https://arxiv.org/abs/1712.05884
- **HiFi-GAN Paper:** https://arxiv.org/abs/2010.05646
- **FastSpeech2 Paper:** https://arxiv.org/abs/2006.04558
- **VITS Paper:** https://arxiv.org/abs/2106.06103
- **Coqui TTS:** https://github.com/coqui-ai/TTS
