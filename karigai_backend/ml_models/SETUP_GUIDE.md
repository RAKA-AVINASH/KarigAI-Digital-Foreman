# KarigAI ML Development Environment Setup Guide

This guide walks you through setting up the complete ML development environment for building custom AI models from scratch.

## Prerequisites

### Hardware Requirements

**Minimum:**
- CPU: 4+ cores
- RAM: 16 GB
- Storage: 100 GB free space
- GPU: Not required but highly recommended

**Recommended:**
- CPU: 8+ cores
- RAM: 32 GB
- Storage: 500 GB SSD
- GPU: NVIDIA GPU with 8+ GB VRAM (RTX 3060 or better)
- CUDA: 11.8 or later

### Software Requirements

- Python 3.8 or later
- pip (Python package manager)
- Git
- (Optional) NVIDIA CUDA Toolkit and cuDNN for GPU acceleration

## Installation Steps

### 1. Clone the Repository

```bash
cd karigai_backend
```

### 2. Run the Setup Script

```bash
python ml_models/setup_ml_env.py
```

This script will:
- Check system requirements
- Create necessary directories
- Optionally install dependencies
- Configure MLflow tracking

### 3. Install Dependencies Manually (if not done by setup script)

```bash
pip install -r requirements-ml.txt
```

**Note:** This will install:
- PyTorch (with CUDA support if available)
- TensorFlow
- Transformers (Hugging Face)
- MLflow for experiment tracking
- DVC for data versioning
- Jupyter for interactive development
- And many other ML libraries

### 4. Verify Installation

Run the environment setup notebook:

```bash
cd ml_models
jupyter lab
```

Open `notebooks/00_environment_setup.ipynb` and run all cells to verify the installation.

## GPU Setup (Optional but Recommended)

### For NVIDIA GPUs:

1. **Install NVIDIA Drivers**
   - Download from: https://www.nvidia.com/Download/index.aspx
   - Verify: `nvidia-smi`

2. **Install CUDA Toolkit**
   - Download from: https://developer.nvidia.com/cuda-downloads
   - Recommended version: 11.8 or 12.1
   - Verify: `nvcc --version`

3. **Install cuDNN**
   - Download from: https://developer.nvidia.com/cudnn
   - Follow installation instructions for your platform

4. **Verify PyTorch GPU Support**
   ```python
   import torch
   print(torch.cuda.is_available())  # Should return True
   print(torch.cuda.get_device_name(0))  # Should show your GPU
   ```

### For Apple Silicon (M1/M2/M3):

PyTorch supports Metal Performance Shaders (MPS):

```python
import torch
print(torch.backends.mps.is_available())  # Should return True
device = torch.device("mps")
```

## Directory Structure

After setup, you'll have:

```
ml_models/
├── README.md                 # Overview
├── SETUP_GUIDE.md           # This file
├── setup_ml_env.py          # Setup script
├── configs/                 # Configuration files
│   ├── mlflow_config.yaml
│   ├── data_config.yaml
│   └── training_config.yaml
├── data/                    # Datasets
│   ├── raw/                # Raw data
│   ├── processed/          # Preprocessed data
│   └── cache/              # Cached data
├── models/                  # Trained models
│   ├── checkpoints/        # Training checkpoints
│   └── exports/            # Exported models (ONNX, etc.)
├── notebooks/               # Jupyter notebooks
│   └── 00_environment_setup.ipynb
├── training/                # Training scripts
│   └── train_pipeline.py
├── inference/               # Inference scripts
├── utils/                   # Utility functions
│   └── setup_environment.py
├── mlruns/                  # MLflow tracking data
└── mlartifacts/            # MLflow artifacts
```

## MLflow Setup

MLflow is used for experiment tracking and model versioning.

### Start MLflow UI

```bash
cd ml_models
mlflow ui
```

Then open http://localhost:5000 in your browser.

### Using MLflow in Code

```python
import mlflow

# Set experiment
mlflow.set_experiment("karigai_models")

# Start a run
with mlflow.start_run(run_name="my_experiment"):
    # Log parameters
    mlflow.log_param("learning_rate", 0.001)
    
    # Log metrics
    mlflow.log_metric("accuracy", 0.95)
    
    # Log model
    mlflow.pytorch.log_model(model, "model")
```

## DVC Setup (Data Version Control)

DVC helps version control large datasets and models.

### Initialize DVC

```bash
cd ml_models
dvc init
```

### Track a Dataset

```bash
dvc add data/raw/speech_dataset.zip
git add data/raw/speech_dataset.zip.dvc .gitignore
git commit -m "Add speech dataset"
```

### Configure Remote Storage (Optional)

```bash
# For cloud storage (S3, GCS, Azure)
dvc remote add -d myremote s3://mybucket/path

# For local storage
dvc remote add -d myremote /path/to/storage
```

## Jupyter Lab Setup

### Start Jupyter Lab

```bash
cd ml_models
jupyter lab
```

### Recommended Extensions

Install useful Jupyter extensions:

```bash
pip install jupyterlab-git
pip install jupyterlab-lsp
pip install python-lsp-server
```

## Configuration Files

### MLflow Configuration (`configs/mlflow_config.yaml`)

Configure experiment tracking, model registry, and autologging.

### Data Configuration (`configs/data_config.yaml`)

Configure dataset paths, splits, and augmentation parameters.

### Training Configuration (`configs/training_config.yaml`)

Configure training hyperparameters for different model types.

## Common Issues and Solutions

### Issue: CUDA Out of Memory

**Solution:**
- Reduce batch size in training config
- Enable gradient accumulation
- Use mixed precision training
- Clear GPU cache: `torch.cuda.empty_cache()`

### Issue: Slow Training on CPU

**Solution:**
- Use smaller models for prototyping
- Reduce dataset size for initial experiments
- Consider using cloud GPU instances (Google Colab, AWS, etc.)

### Issue: MLflow UI Not Starting

**Solution:**
- Check if port 5000 is available
- Use a different port: `mlflow ui --port 5001`
- Check MLflow tracking URI in config

### Issue: Import Errors

**Solution:**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements-ml.txt`
- Check Python version: `python --version` (should be 3.8+)

## Next Steps

1. **Data Collection**: Start with task 16.2 - Collect and prepare speech datasets
2. **Model Development**: Use Jupyter notebooks for experimentation
3. **Training**: Use the training pipeline for model training
4. **Evaluation**: Validate models on test sets
5. **Deployment**: Export models for production use

## Resources

### Documentation
- PyTorch: https://pytorch.org/docs/
- TensorFlow: https://www.tensorflow.org/api_docs
- Transformers: https://huggingface.co/docs/transformers
- MLflow: https://mlflow.org/docs/latest/index.html
- DVC: https://dvc.org/doc

### Tutorials
- PyTorch Tutorials: https://pytorch.org/tutorials/
- Hugging Face Course: https://huggingface.co/course
- Fast.ai: https://www.fast.ai/

### Datasets
- Common Voice: https://commonvoice.mozilla.org/
- OpenSLR: https://www.openslr.org/
- Hugging Face Datasets: https://huggingface.co/datasets

## Support

For issues or questions:
1. Check this guide and README.md
2. Review error messages and logs
3. Consult official documentation
4. Search for similar issues online

## License

This ML infrastructure is part of the KarigAI project.
