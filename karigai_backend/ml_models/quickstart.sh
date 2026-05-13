#!/bin/bash
# Quick start script for KarigAI ML development

echo "=========================================="
echo "KarigAI ML Development Quick Start"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or later."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip is not installed. Please install pip."
    exit 1
fi

echo "✅ pip found"
echo ""

# Run setup script
echo "Running setup script..."
python3 setup_ml_env.py

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To start developing:"
echo "  1. cd ml_models"
echo "  2. jupyter lab"
echo ""
echo "To start MLflow UI:"
echo "  1. cd ml_models"
echo "  2. mlflow ui"
echo ""
