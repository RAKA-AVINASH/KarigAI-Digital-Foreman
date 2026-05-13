"""
Lightning AI Studio for Government Scheme Matching Model Training

This script provides a Lightning AI compatible training environment for the
government scheme matching model.
"""

import lightning as L
from lightning.app.components import TracerPythonScript


class SchemeMatchingStudio(L.LightningFlow):
    """Lightning AI Studio for Scheme Matching Training"""
    
    def __init__(self):
        super().__init__()
        self.training_script = TracerPythonScript(
            script_path="training/train_scheme_matching.py",
            script_args=[
                "--model_name", "distilbert-base-multilingual-cased",
                "--data_dir", "data/processed/nlp/schemes",
                "--output_dir", "models/checkpoints/scheme_matching",
                "--batch_size", "32",
                "--learning_rate", "2e-5",
                "--num_epochs", "10",
                "--max_length", "256"
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
        print("Government Scheme Matching Model Training - Lightning AI Studio")
        print("=" * 80)
        print("\nModel: DistilBERT Multilingual + Classification Head")
        print("Task: User-Scheme Eligibility Matching")
        print("Target Accuracy: >85%")
        print("Use Case: Government scheme recommendation and auto-filling")
        print("\n" + "=" * 80)
        
        # Run training
        self.training_script.run()
        
        if self.training_script.has_succeeded:
            print("\n✓ Training completed successfully!")
            print("Model saved to: models/checkpoints/scheme_matching/")
        elif self.training_script.has_failed:
            print("\n✗ Training failed!")
            print(f"Error: {self.training_script.error}")


# Lightning AI App
app = L.LightningApp(SchemeMatchingStudio())


# Instructions for running on Lightning AI
"""
# Government Scheme Matching Model Training on Lightning AI

## Setup Instructions

1. Create a new Lightning AI Studio
2. Upload this file and the training script
3. Install dependencies:
   ```bash
   pip install torch transformers scikit-learn tqdm
   ```

4. Prepare datasets:
   ```bash
   python utils/nlp_dataset_preparation.py --task schemes --num_examples 5000
   ```

5. Run training:
   ```bash
   lightning run app lightning_ai/scheme_matching_studio.py
   ```

## Expected Results

- Training time: ~30-40 minutes on T4 GPU
- Target accuracy: >85%
- Model size: ~250MB
- Inference latency: <50ms per request

## Model Capabilities

- Eligibility assessment
- Rule-based complex logic
- Form field extraction
- Scheme recommendation ranking
- Multi-criteria matching

## Next Steps

1. Test model on validation set
2. Export to ONNX format for deployment
3. Create new scheme matching service
4. Deploy to production API

## Troubleshooting

- If GPU memory error: Reduce batch_size to 16
- If accuracy < 85%: Increase num_epochs to 15-20
- If training too slow: Use smaller model (distilbert-base-uncased)
"""
