"""
Lightning AI Studio for Translation Model Training

This script provides a Lightning AI compatible training environment for the
translation and language transformation model.
"""

import lightning as L
from lightning.app.components import TracerPythonScript


class TranslationStudio(L.LightningFlow):
    """Lightning AI Studio for Translation Training"""
    
    def __init__(self):
        super().__init__()
        self.training_script = TracerPythonScript(
            script_path="training/train_translation.py",
            script_args=[
                "--model_name", "facebook/mbart-large-50-many-to-many-mmt",
                "--data_dir", "data/processed/nlp/translation",
                "--output_dir", "models/checkpoints/translation",
                "--batch_size", "16",
                "--learning_rate", "3e-5",
                "--num_epochs", "20",
                "--max_length", "128"
            ],
            cloud_compute=L.CloudCompute("gpu", disk_size=50),
            env={
                "TRANSFORMERS_CACHE": "/teamspace/studios/this_studio/.cache/huggingface",
                "HF_HOME": "/teamspace/studios/this_studio/.cache/huggingface"
            }
        )
    
    def run(self):
        """Run the training workflow"""
        print("=" * 80)
        print("Translation Model Training - Lightning AI Studio")
        print("=" * 80)
        print("\nModel: mBART-50 Many-to-Many")
        print("Task: Multilingual Translation + Register Transformation")
        print("Target BLEU: >30")
        print("Languages: Hindi, English, Malayalam, Dogri, Punjabi, Bengali, Tamil, Telugu")
        print("\n" + "=" * 80)
        
        # Run training
        self.training_script.run()
        
        if self.training_script.has_succeeded:
            print("\n✓ Training completed successfully!")
            print("Model saved to: models/checkpoints/translation/")
        elif self.training_script.has_failed:
            print("\n✗ Training failed!")
            print(f"Error: {self.training_script.error}")


# Lightning AI App
app = L.LightningApp(TranslationStudio())


# Instructions for running on Lightning AI
"""
# Translation Model Training on Lightning AI

## Setup Instructions

1. Create a new Lightning AI Studio
2. Upload this file and the training script
3. Install dependencies:
   ```bash
   pip install torch transformers sacrebleu tqdm
   ```

4. Prepare datasets:
   ```bash
   python utils/nlp_dataset_preparation.py --task translation --num_examples 50000
   ```

5. Run training:
   ```bash
   lightning run app lightning_ai/translation_studio.py
   ```

## Expected Results

- Training time: ~2-3 hours on T4 GPU
- Target BLEU: >30
- Model size: ~2.4GB
- Inference latency: <200ms per request

## Model Capabilities

- Multilingual translation (8 Indian languages)
- Register transformation (colloquial to formal)
- Technical term preservation
- Bidirectional translation
- Code-mixed language support

## Next Steps

1. Test model on validation set
2. Export to ONNX format for deployment
3. Integrate with KarigAI translation service
4. Deploy to production API

## Troubleshooting

- If GPU memory error: Reduce batch_size to 8
- If BLEU < 30: Increase num_epochs to 30-40
- If training too slow: Use smaller model (mbart-large-50)
"""
