"""
Environment setup utilities for ML development.
Checks for GPU availability, installs dependencies, and configures paths.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Tuple


def check_gpu_availability() -> Dict[str, any]:
    """
    Check if GPU is available and return GPU information.
    
    Returns:
        Dictionary with GPU availability and details
    """
    gpu_info = {
        "available": False,
        "device_count": 0,
        "devices": [],
        "cuda_version": None,
        "cudnn_version": None
    }
    
    try:
        import torch
        
        if torch.cuda.is_available():
            gpu_info["available"] = True
            gpu_info["device_count"] = torch.cuda.device_count()
            gpu_info["cuda_version"] = torch.version.cuda
            
            for i in range(torch.cuda.device_count()):
                device_props = torch.cuda.get_device_properties(i)
                gpu_info["devices"].append({
                    "id": i,
                    "name": device_props.name,
                    "memory_total_gb": device_props.total_memory / (1024**3),
                    "compute_capability": f"{device_props.major}.{device_props.minor}"
                })
            
            if torch.backends.cudnn.is_available():
                gpu_info["cudnn_version"] = torch.backends.cudnn.version()
                
    except ImportError:
        print("PyTorch not installed. GPU check skipped.")
    except Exception as e:
        print(f"Error checking GPU: {e}")
    
    return gpu_info


def check_tensorflow_gpu() -> bool:
    """Check if TensorFlow can access GPU."""
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        return len(gpus) > 0
    except ImportError:
        return False
    except Exception:
        return False


def install_dependencies(requirements_file: str = "requirements-ml.txt") -> bool:
    """
    Install ML dependencies from requirements file.
    
    Args:
        requirements_file: Path to requirements file
        
    Returns:
        True if installation successful
    """
    try:
        print(f"Installing dependencies from {requirements_file}...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ])
        print("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False


def setup_directories() -> Dict[str, Path]:
    """
    Create necessary directories for ML development.
    
    Returns:
        Dictionary of created directory paths
    """
    base_path = Path(__file__).parent.parent
    
    directories = {
        "data": base_path / "data",
        "raw_data": base_path / "data" / "raw",
        "processed_data": base_path / "data" / "processed",
        "cache": base_path / "data" / "cache",
        "models": base_path / "models",
        "checkpoints": base_path / "models" / "checkpoints",
        "exports": base_path / "models" / "exports",
        "notebooks": base_path / "notebooks",
        "training": base_path / "training",
        "inference": base_path / "inference",
        "mlruns": base_path / "mlruns",
        "mlartifacts": base_path / "mlartifacts"
    }
    
    for name, path in directories.items():
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {path}")
    
    return directories


def check_system_requirements() -> Dict[str, any]:
    """
    Check system requirements for ML development.
    
    Returns:
        Dictionary with system information
    """
    import psutil
    
    system_info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "cpu_count": os.cpu_count(),
        "memory_total_gb": psutil.virtual_memory().total / (1024**3),
        "memory_available_gb": psutil.virtual_memory().available / (1024**3),
        "disk_total_gb": psutil.disk_usage('/').total / (1024**3),
        "disk_free_gb": psutil.disk_usage('/').free / (1024**3)
    }
    
    return system_info


def setup_mlflow() -> bool:
    """
    Initialize MLflow tracking server.
    
    Returns:
        True if setup successful
    """
    try:
        import mlflow
        
        # Set tracking URI
        tracking_uri = Path(__file__).parent.parent / "mlruns"
        mlflow.set_tracking_uri(f"file://{tracking_uri}")
        
        # Create default experiment
        experiment_name = "karigai_models"
        try:
            mlflow.create_experiment(experiment_name)
        except Exception:
            pass  # Experiment already exists
        
        mlflow.set_experiment(experiment_name)
        
        print(f"MLflow tracking URI: {mlflow.get_tracking_uri()}")
        print(f"MLflow experiment: {experiment_name}")
        
        return True
    except ImportError:
        print("MLflow not installed. Skipping MLflow setup.")
        return False
    except Exception as e:
        print(f"Error setting up MLflow: {e}")
        return False


def print_environment_summary(gpu_info: Dict, system_info: Dict):
    """Print a summary of the environment setup."""
    print("\n" + "="*60)
    print("ML ENVIRONMENT SETUP SUMMARY")
    print("="*60)
    
    print("\n📊 System Information:")
    print(f"  Platform: {system_info['platform']} {system_info['architecture']}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  CPUs: {system_info['cpu_count']}")
    print(f"  RAM: {system_info['memory_total_gb']:.1f} GB (Available: {system_info['memory_available_gb']:.1f} GB)")
    print(f"  Disk: {system_info['disk_free_gb']:.1f} GB free of {system_info['disk_total_gb']:.1f} GB")
    
    print("\n🎮 GPU Information:")
    if gpu_info["available"]:
        print(f"  ✅ GPU Available: {gpu_info['device_count']} device(s)")
        print(f"  CUDA Version: {gpu_info['cuda_version']}")
        if gpu_info['cudnn_version']:
            print(f"  cuDNN Version: {gpu_info['cudnn_version']}")
        for device in gpu_info["devices"]:
            print(f"  - {device['name']}: {device['memory_total_gb']:.1f} GB")
    else:
        print("  ⚠️  No GPU detected. Training will use CPU (slower).")
    
    print("\n📦 Framework Status:")
    try:
        import torch
        print(f"  ✅ PyTorch: {torch.__version__}")
    except ImportError:
        print("  ❌ PyTorch: Not installed")
    
    try:
        import tensorflow as tf
        print(f"  ✅ TensorFlow: {tf.__version__}")
    except ImportError:
        print("  ❌ TensorFlow: Not installed")
    
    try:
        import transformers
        print(f"  ✅ Transformers: {transformers.__version__}")
    except ImportError:
        print("  ❌ Transformers: Not installed")
    
    try:
        import mlflow
        print(f"  ✅ MLflow: {mlflow.__version__}")
    except ImportError:
        print("  ❌ MLflow: Not installed")
    
    print("\n" + "="*60)


def main():
    """Main setup function."""
    print("🚀 Setting up KarigAI ML Development Environment...\n")
    
    # Check system requirements
    print("Checking system requirements...")
    system_info = check_system_requirements()
    
    # Check GPU availability
    print("Checking GPU availability...")
    gpu_info = check_gpu_availability()
    
    # Setup directories
    print("\nCreating directory structure...")
    directories = setup_directories()
    
    # Setup MLflow
    print("\nSetting up MLflow...")
    setup_mlflow()
    
    # Print summary
    print_environment_summary(gpu_info, system_info)
    
    print("\n✅ Environment setup complete!")
    print("\nNext steps:")
    print("  1. Install dependencies: pip install -r requirements-ml.txt")
    print("  2. Start Jupyter: jupyter lab")
    print("  3. Start MLflow UI: mlflow ui")
    print("  4. Begin model development in notebooks/")


if __name__ == "__main__":
    main()
