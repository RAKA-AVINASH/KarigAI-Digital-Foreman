"""
Lightning AI Studio for Intent Recognition Model Training

This script provides a Lightning AI compatible training environment for the
intent recognition and NLU model.
"""

import lightning as L
from lightning.app.components import TracerPythonScript


class IntentRecognitionStudio(L.LightningFlow):
    """Lightning AI Studio for Intent Recognition Training"""
    
    def __init__(self):
        super().__init__()
        self.training_script = TracerPythonScript(
            script_path="training/train_intent_recognition.py",
            script_args=[
                "--model_name", "distilbert-base-multilingual-cased",
                "--data_dir", "data/processed/nlp/intent",
                "--output_dir", "models/checkpoints/intent_recognition",
                "--batch_size", "32",
                "--learning_rate", "2e-5",
                "--num_epochs", "10",
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
        print("Intent Recognition Model Training - Lightning AI Studio")
        print("=" * 80)
        print("\nModel: DistilBERT Multilingual")
        print("Task: Intent Classification + Entity Extraction")
        print("Target Accuracy: >90%")
        print("Languages: Hindi, English, Malayalam, Dogri, Punjabi, Bengali, Tamil, Telugu")
        print("\n" + "=" * 80)
        
        # Run training
        self.training_script.run()
        
        if self.training_script.has_succeeded:
            print("\n✓ Training completed successfully!")
            print("Model saved to: models/checkpoints/intent_recognition/")
        elif self.training_script.has_failed:
            print("\n✗ Training failed!")
            print(f"Error: {self.training_script.error}")


# Lightning AI App
app = L.LightningApp(IntentRecognitionStudio())


# Instructions for running on Lightning AI
"""
# Intent Recognition Model Training on Lightning AI

## Setup Instructions

1. Create a new Lightning AI Studio
2. Upload this file and the training script
3. Install dependencies:
   ```bash
   pip install torch transformers scikit-learn tqdm
   ```

4. Prepare datasets:
   ```bash
   python utils/nlp_dataset_preparation.py --task intent --num_examples 10000
   ```

5. Run training:
   ```bash
   lightning run app lightning_ai/intent_recognition_studio.py
   ```

## Expected Results

- Training time: ~30-45 minutes on T4 GPU
- Target accuracy: >90%
- Model size: ~250MB
- Inference latency: <50ms per request

## Model Outputs

- Checkpoint: models/checkpoints/intent_recognition/best_model.pt
- Intent classes: 9 classes (invoice, repair, equipment, quality, learning, document, query, complaint, feedback)
- Entity types: 7 types (amount, date, item, equipment, location, person_name, phone_number)

## Next Steps

1. Test model on validation set
2. Export to ONNX format for deployment
3. Integrate with KarigAI backend services
4. Deploy to production API

## Troubleshooting

- If GPU memory error: Reduce batch_size to 16
- If accuracy < 90%: Increase num_epochs to 15-20
- If training too slow: Use smaller model (distilbert-base-uncased)
"""
