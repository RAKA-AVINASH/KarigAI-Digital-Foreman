# KarigAI ML Models

This directory contains the machine learning infrastructure for building custom AI models from scratch.

## Directory Structure

```
ml_models/
├── notebooks/          # Jupyter notebooks for model development
├── data/              # Training datasets and preprocessed data
├── models/            # Trained model checkpoints
├── configs/           # Model configuration files
├── training/          # Training scripts and pipelines
├── inference/         # Inference and deployment scripts
└── utils/             # Utility functions for data processing
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements-ml.txt
```

### 2. GPU Setup (Optional but Recommended)

For CUDA support:
- Install NVIDIA drivers
- Install CUDA Toolkit 11.8+
- Install cuDNN

### 3. Data Storage Configuration

Configure data storage paths in `configs/data_config.yaml`

### 4. Model Versioning

We use MLflow for model versioning and experiment tracking:

```bash
mlflow ui
```

## Model Development Workflow

1. **Data Collection**: Gather and prepare datasets in `data/`
2. **Preprocessing**: Use notebooks in `notebooks/` for exploration
3. **Training**: Run training scripts from `training/`
4. **Evaluation**: Validate models on test sets
5. **Deployment**: Export models using `inference/` scripts

## Supported Models

- Speech Recognition (Wav2Vec2/Whisper-based)
- Text-to-Speech (Tacotron2/FastSpeech2)
- Computer Vision (ResNet/EfficientNet)
- NLP (BERT/Transformer-based)

## Resources

- PyTorch Documentation: https://pytorch.org/docs/
- Hugging Face Transformers: https://huggingface.co/docs/transformers
- MLflow Documentation: https://mlflow.org/docs/latest/index.html
