#!/usr/bin/env python3
"""
Setup script for KarigAI ML development environment.
Run this script to initialize the ML infrastructure.
"""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml_models.utils.setup_environment import (
    check_gpu_availability,
    check_system_requirements,
    setup_directories,
    setup_mlflow,
    print_environment_summary,
    install_dependencies
)


def main():
    """Main setup function."""
    print("="*60)
    print("KarigAI ML Development Environment Setup")
    print("="*60)
    print()
    
    # Step 1: Check system requirements
    print("Step 1: Checking system requirements...")
    system_info = check_system_requirements()
    gpu_info = check_gpu_availability()
    print("✅ System check complete\n")
    
    # Step 2: Setup directories
    print("Step 2: Creating directory structure...")
    directories = setup_directories()
    print("✅ Directories created\n")
    
    # Step 3: Install dependencies (optional)
    print("Step 3: Install ML dependencies?")
    print("This will install PyTorch, TensorFlow, Transformers, and other ML libraries.")
    response = input("Install dependencies now? (y/n): ").strip().lower()
    
    if response == 'y':
        requirements_file = Path(__file__).parent.parent / "requirements-ml.txt"
        if install_dependencies(str(requirements_file)):
            print("✅ Dependencies installed\n")
        else:
            print("⚠️  Dependency installation failed. You can install manually later.\n")
    else:
        print("⏭️  Skipping dependency installation")
        print(f"   To install later: pip install -r requirements-ml.txt\n")
    
    # Step 4: Setup MLflow
    print("Step 4: Setting up MLflow...")
    if setup_mlflow():
        print("✅ MLflow configured\n")
    else:
        print("⚠️  MLflow setup skipped\n")
    
    # Step 5: Print summary
    print_environment_summary(gpu_info, system_info)
    
    # Final instructions
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\n📚 Next Steps:\n")
    print("1. Start Jupyter Lab:")
    print("   cd karigai_backend/ml_models")
    print("   jupyter lab\n")
    print("2. Open the environment setup notebook:")
    print("   notebooks/00_environment_setup.ipynb\n")
    print("3. Start MLflow UI (in a separate terminal):")
    print("   cd karigai_backend/ml_models")
    print("   mlflow ui\n")
    print("4. Begin data collection and model development\n")
    print("="*60)


if __name__ == "__main__":
    main()
