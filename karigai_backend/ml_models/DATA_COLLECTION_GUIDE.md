# Speech Dataset Collection Guide for KarigAI

This guide provides detailed instructions for collecting and preparing Indian language speech datasets for training custom speech recognition models.

## Target Languages

KarigAI supports the following Indian languages:
- Hindi (hi)
- Malayalam (ml)
- Punjabi (pa)
- Bengali (bn)
- Tamil (ta)
- Telugu (te)
- English - Indian accent (en-IN)

## Dataset Sources

### 1. Mozilla Common Voice

**URL:** https://commonvoice.mozilla.org/

**Available Languages:** Hindi, Punjabi, Bengali, Tamil, Telugu

**How to Download:**
1. Visit the Common Voice website
2. Navigate to the Datasets page
3. Select your target language
4. Download the validated dataset (recommended)
5. Extract to: `ml_models/data/raw/common_voice_<lang>/`

**Dataset Structure:**
```
common_voice_hi/
├── clips/           # Audio files (.mp3)
├── validated.tsv    # Validated transcripts
├── train.tsv
├── dev.tsv
└── test.tsv
```

**Pros:**
- High quality, validated by community
- Good coverage of common phrases
- Free and open source

**Cons:**
- May not include trade-specific vocabulary
- Accent diversity varies by language

### 2. OpenSLR (Open Speech and Language Resources)

**URL:** https://www.openslr.org/

**Available Languages:** Hindi, Malayalam, Tamil, Telugu, Bengali

**How to Download:**
1. Browse the OpenSLR resources page
2. Look for Indian language datasets (e.g., SLR 63-66 for Indian languages)
3. Download using provided links
4. Extract to: `ml_models/data/raw/openslr_<lang>/`

**Notable Datasets:**
- SLR 63: Hindi (Crowdsourced high-quality)
- SLR 64: Tamil
- SLR 65: Telugu
- SLR 66: Gujarati

**Pros:**
- High quality recordings
- Good for ASR training
- Free and open source

**Cons:**
- Smaller dataset sizes
- Limited dialect coverage

### 3. IIT Madras Indic TTS Database

**URL:** https://www.iitm.ac.in/donlab/tts/

**Available Languages:** Hindi, Tamil, Telugu, Malayalam

**How to Download:**
1. Visit the IIT Madras TTS database page
2. Request access (may require registration)
3. Download datasets for required languages
4. Extract to: `ml_models/data/raw/indic_tts_<lang>/`

**Pros:**
- High quality studio recordings
- Good for TTS training
- Indian accent coverage

**Cons:**
- May require registration
- Primarily designed for TTS (but usable for ASR)

### 4. AI4Bharat IndicSpeech

**URL:** https://indicnlp.ai4bharat.org/

**Available Languages:** Multiple Indian languages

**How to Download:**
1. Visit AI4Bharat website
2. Navigate to IndicSpeech datasets
3. Follow download instructions
4. Extract to: `ml_models/data/raw/indicspeech_<lang>/`

**Pros:**
- Large-scale datasets
- Good language coverage
- Research-quality

**Cons:**
- May require academic access
- Large download sizes

## Trade-Specific Vocabulary Collection

For KarigAI to work effectively, we need trade-specific terminology in local dialects.

### Creating Custom Recordings

**Equipment Needed:**
- Smartphone with good microphone
- Quiet recording environment
- Recording app (e.g., Voice Recorder, Easy Voice Recorder)

**Recording Guidelines:**
1. **Environment:**
   - Find a quiet room with minimal background noise
   - Avoid echo (use soft furnishings to dampen sound)
   - Consistent recording environment for all samples

2. **Recording Settings:**
   - Format: WAV or high-quality MP3 (320 kbps)
   - Sample rate: 16 kHz or 44.1 kHz
   - Mono channel (not stereo)

3. **Speaking Guidelines:**
   - Speak clearly and naturally
   - Maintain consistent distance from microphone (15-20 cm)
   - Avoid breathing directly into microphone
   - Pause briefly between sentences

4. **Content:**
   - Record common trade phrases
   - Include numbers, measurements, and units
   - Record tool names and materials
   - Include customer interaction phrases

### Trade Vocabulary Template

Use the provided CSV template to organize trade-specific terms:

```csv
trade,term_english,term_hindi,term_local,pronunciation,context
plumber,pipe,पाइप,<local_term>,paip,water supply
electrician,wire,तार,<local_term>,taar,electrical work
carpenter,wood,लकड़ी,<local_term>,lakdi,furniture
```

**How to Fill:**
1. Run the notebook to generate template
2. Fill in local dialect translations
3. Add pronunciation guide (using Latin script)
4. Provide context for each term

### Recording Trade Vocabulary

**Process:**
1. Create a list of 100-200 common trade terms
2. Record each term 5-10 times with slight variations
3. Record full sentences using the terms
4. Include questions and responses
5. Record numbers and measurements

**Example Phrases to Record:**
- "मुझे एक पाइप चाहिए" (I need a pipe)
- "यह कितने का है?" (How much does this cost?)
- "काम कब पूरा होगा?" (When will the work be complete?)
- "बिजली का तार कहाँ है?" (Where is the electrical wire?)

## Data Augmentation

To increase dataset size and robustness, we apply augmentation:

### Augmentation Techniques

1. **Noise Injection:**
   - Add background noise (traffic, construction, etc.)
   - Noise factor: 0.005-0.01

2. **Speed Perturbation:**
   - Speed factors: 0.9x, 1.0x, 1.1x
   - Simulates different speaking rates

3. **Pitch Shifting:**
   - Shift by ±2 semitones
   - Simulates different voice pitches

4. **Time Stretching:**
   - Stretch factors: 0.9x, 1.0x, 1.1x
   - Changes tempo without affecting pitch

### Applying Augmentation

Use the `AudioAugmentor` class:

```python
from ml_models.utils.audio_preprocessing import AudioAugmentor

augmentor = AudioAugmentor(sample_rate=16000)

# Apply augmentation
augmented = augmentor.augment(waveform, {
    'noise_injection': True,
    'speed_perturbation': [0.9, 1.0, 1.1],
    'pitch_shift': [-2, 0, 2]
})
```

## Dataset Organization

### Directory Structure

```
ml_models/data/
├── raw/                          # Raw downloaded datasets
│   ├── common_voice_hi/
│   ├── common_voice_ml/
│   ├── openslr_hi/
│   └── trade_recordings/         # Custom trade recordings
├── processed/                    # Processed and split datasets
│   ├── common_voice_hi/
│   │   ├── train_files.txt
│   │   ├── val_files.txt
│   │   ├── test_files.txt
│   │   ├── train_manifest.json
│   │   ├── val_manifest.json
│   │   └── test_manifest.json
│   └── ...
├── cache/                        # Preprocessed features cache
└── dataset_registry.json         # Dataset metadata
```

### Manifest File Format

Each manifest file contains one JSON object per line:

```json
{"audio_filepath": "/path/to/audio.wav", "text": "transcript text", "duration": 3.5, "language": "hi"}
{"audio_filepath": "/path/to/audio2.wav", "text": "another transcript", "duration": 2.8, "language": "hi"}
```

## Dataset Preparation Workflow

### Step-by-Step Process

1. **Download Datasets:**
   ```bash
   # Download from sources listed above
   # Extract to ml_models/data/raw/
   ```

2. **Register Datasets:**
   ```python
   from ml_models.utils.dataset_preparation import DatasetManager
   
   manager = DatasetManager()
   manager.register_dataset(
       name="common_voice",
       language="hi",
       audio_dir=Path("data/raw/common_voice_hi/clips"),
       transcript_file=Path("data/raw/common_voice_hi/validated.tsv")
   )
   ```

3. **Split Datasets:**
   ```python
   splits = manager.split_dataset(
       dataset_id="common_voice_hi",
       train_ratio=0.8,
       val_ratio=0.1,
       test_ratio=0.1
   )
   ```

4. **Create Manifests:**
   ```python
   # Parse transcript file to create mapping
   transcript_mapping = {...}  # audio_path -> transcript
   
   manager.create_manifest(
       dataset_id="common_voice_hi",
       split="train",
       transcript_mapping=transcript_mapping
   )
   ```

5. **Verify Data:**
   ```python
   stats = manager.get_dataset_statistics("common_voice_hi")
   print(stats)
   ```

## Quality Checks

### Audio Quality Criteria

- **Sample Rate:** 16 kHz minimum
- **Duration:** 1-30 seconds per clip
- **Format:** WAV or high-quality MP3
- **Noise Level:** Minimal background noise
- **Clipping:** No audio clipping or distortion

### Transcript Quality Criteria

- **Accuracy:** Exact transcription of spoken words
- **Formatting:** Consistent punctuation and capitalization
- **Language:** Correct language tagging
- **Special Characters:** Proper handling of numbers, symbols

### Validation Script

```python
from ml_models.utils.audio_preprocessing import AudioPreprocessor

preprocessor = AudioPreprocessor()

def validate_audio(audio_path):
    try:
        result = preprocessor.preprocess(audio_path)
        if result['duration'] < 1.0:
            print(f"⚠️  Too short: {audio_path}")
        elif result['duration'] > 30.0:
            print(f"⚠️  Too long: {audio_path}")
        else:
            print(f"✅ Valid: {audio_path}")
        return True
    except Exception as e:
        print(f"❌ Invalid: {audio_path} - {e}")
        return False
```

## Dataset Size Recommendations

### Minimum Requirements

- **Per Language:** 10-20 hours of audio
- **Training Set:** 8-16 hours
- **Validation Set:** 1-2 hours
- **Test Set:** 1-2 hours

### Recommended for Production

- **Per Language:** 100+ hours of audio
- **Training Set:** 80+ hours
- **Validation Set:** 10+ hours
- **Test Set:** 10+ hours

### Trade-Specific Vocabulary

- **Per Trade:** 500-1000 unique terms
- **Recordings per Term:** 5-10 variations
- **Total:** 2500-10000 recordings per trade

## Next Steps

After collecting and preparing datasets:

1. ✅ Verify all datasets are registered
2. ✅ Check dataset statistics
3. ✅ Validate audio quality
4. ✅ Create manifest files
5. ➡️  Proceed to model training (Task 16.3)

## Troubleshooting

### Common Issues

**Issue:** Audio files not loading
- **Solution:** Check file format and codec compatibility
- **Solution:** Convert to WAV using: `ffmpeg -i input.mp3 -ar 16000 output.wav`

**Issue:** Transcripts not matching audio
- **Solution:** Verify file paths in manifest
- **Solution:** Check character encoding (use UTF-8)

**Issue:** Dataset too large for storage
- **Solution:** Use DVC for version control
- **Solution:** Store on external drive or cloud storage

## Resources

- **Audio Editing:** Audacity (https://www.audacityteam.org/)
- **Format Conversion:** FFmpeg (https://ffmpeg.org/)
- **Dataset Management:** DVC (https://dvc.org/)
- **Annotation Tools:** Praat (https://www.fon.hum.uva.nl/praat/)

## License Considerations

- **Common Voice:** CC0 (Public Domain)
- **OpenSLR:** Various open licenses (check individual datasets)
- **Custom Recordings:** Ensure you have rights to use and distribute

Always check and comply with dataset licenses before use.
