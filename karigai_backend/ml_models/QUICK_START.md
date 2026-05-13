# Quick Start Guide - KarigAI ML Models

## ✅ Completed Steps

1. **GitHub Push**: All ML infrastructure code has been pushed to GitHub
2. **Basic Dependencies**: psutil and pyyaml installed

## 📋 Next Steps (Manual Execution Required)

### Step 1: Run Environment Setup

```powershell
python karigai_backend/ml_models/setup_ml_env.py
```

This will:
- Check system requirements (CPU, RAM, GPU)
- Create directory structure
- Optionally install ML dependencies
- Configure MLflow tracking

### Step 2: Install ML Dependencies (Large Download ~5GB)

```powershell
pip install -r karigai_backend/requirements-ml.txt
```

**Note**: This will take 15-30 minutes depending on your internet speed.

### Step 3: Download Datasets

Follow the guide in `karigai_backend/ml_models/DATA_COLLECTION_GUIDE.md`

**Dataset Sources**:
- Mozilla Common Voice: https://commonvoice.mozilla.org/
- OpenSLR: https://www.openslr.org/
- IIT Madras Indic TTS: https://www.iitm.ac.in/donlab/tts/

**Estimated Download**: 50-100 GB per language

### Step 4: Prepare Datasets

```powershell
# Start Jupyter Lab
cd karigai_backend/ml_models
jupyter lab

# Open: notebooks/01_speech_dataset_collection.ipynb
```

### Step 5: Train Speech Recognition Model

```powershell
cd karigai_backend/ml_models
python training/train_speech_recognition.py
```

**Requirements**:
- GPU with 8+ GB VRAM (RTX 3060 or better)
- Training time: 3-7 days
- Dataset: 100+ hours of audio

### Step 6: Train Text-to-Speech Model

```powershell
python training/train_tts.py
```

**Requirements**:
- GPU with 8+ GB VRAM
- Training time: 3-5 days
- Dataset: 20+ hours of audio

### Step 7: Deploy Models

```powershell
# Start inference API
python inference/speech_inference_api.py

# Or use Docker
docker build -t karigai-speech-api .
docker run -p 8000:8000 karigai-speech-api
```

## 📚 Documentation

All comprehensive guides are available in `karigai_backend/ml_models/`:

- `SETUP_GUIDE.md` - Environment setup (50+ pages)
- `DATA_COLLECTION_GUIDE.md` - Dataset collection (40+ pages)
- `SPEECH_RECOGNITION_GUIDE.md` - STT training (50+ pages)
- `TTS_GUIDE.md` - TTS training (30+ pages)
- `DEPLOYMENT_GUIDE.md` - Production deployment (40+ pages)
- `IMPLEMENTATION_SUMMARY.md` - Complete overview

## ⚠️ Important Notes

### Resource Requirements

**Minimum**:
- CPU: 4+ cores
- RAM: 16 GB
- GPU: 8 GB VRAM
- Storage: 100 GB
- Internet: For dataset downloads

**Recommended**:
- CPU: 8+ cores
- RAM: 32 GB
- GPU: 16 GB VRAM (RTX 4080)
- Storage: 500 GB SSD
- Internet: High-speed for downloads

### Time Estimates

- Environment setup: 1-2 hours
- Dataset download: 1-2 days
- Dataset preparation: 1-2 days
- Model training: 1-2 weeks (per model)
- Deployment: 1 day

### Cost Considerations

**Option 1: Local Training**
- One-time GPU purchase: $500-$1500
- Electricity: ~$50-100 for training period

**Option 2: Cloud Training (AWS/GCP)**
- GPU instance (g4dn.xlarge): ~$0.50/hour
- Training cost: ~$200-400 per model
- Storage: ~$10-20/month

**Option 3: Use Pre-trained Models (Recommended for MVP)**
- OpenAI Whisper API: $0.006/minute
- ElevenLabs TTS: $0.30/1000 characters
- Much faster to deploy
- No training required

## 🚀 Recommended Approach

For initial development and MVP:

1. **Use existing paid APIs** (OpenAI Whisper, ElevenLabs)
   - Already implemented in the backend
   - Fast to deploy
   - Good quality
   - Pay as you go

2. **Build custom models later** when:
   - You have significant user base
   - Cost justifies investment
   - You need specific customizations
   - You have collected user data

## 📞 Support

- Review documentation in `ml_models/` directory
- Check Jupyter notebooks for interactive guides
- Consult official documentation:
  - PyTorch: https://pytorch.org/docs/
  - Transformers: https://huggingface.co/docs/transformers
  - MLflow: https://mlflow.org/docs/

## ✅ What's Ready

The complete ML infrastructure is ready:
- ✅ Environment setup scripts
- ✅ Dataset management tools
- ✅ Training pipelines
- ✅ Inference API
- ✅ Deployment configurations
- ✅ Comprehensive documentation

You can start whenever you have the required resources (GPU, datasets, time).
