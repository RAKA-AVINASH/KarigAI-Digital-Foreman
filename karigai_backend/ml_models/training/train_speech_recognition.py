"""
Training script for multilingual speech recognition model.
Based on Whisper architecture with fine-tuning for Indian languages.
"""

import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer
)
from datasets import load_dataset, Audio
import evaluate
import mlflow
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class SpeechRecognitionConfig:
    """Configuration for speech recognition training."""
    model_name: str = "openai/whisper-small"  # or whisper-base, whisper-medium
    languages: List[str] = None  # ['hi', 'ml', 'pa', 'bn', 'ta', 'te', 'en']
    sample_rate: int = 16000
    max_duration_seconds: float = 30.0
    
    # Training hyperparameters
    batch_size: int = 8
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-5
    num_epochs: int = 20
    warmup_steps: int = 500
    weight_decay: float = 0.01
    
    # Model-specific
    freeze_encoder: bool = False
    gradient_checkpointing: bool = True
    
    # Paths
    data_dir: str = "./ml_models/data/processed"
    output_dir: str = "./ml_models/models/speech_recognition"
    cache_dir: str = "./ml_models/data/cache"
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ['hi', 'ml', 'pa', 'bn', 'ta', 'te', 'en']


class SpeechDataset(Dataset):
    """Custom dataset for speech recognition."""
    
    def __init__(
        self,
        manifest_file: str,
        processor: WhisperProcessor,
        sample_rate: int = 16000,
        max_duration: float = 30.0
    ):
        self.processor = processor
        self.sample_rate = sample_rate
        self.max_duration = max_duration
        
        # Load manifest
        self.samples = []
        with open(manifest_file, 'r', encoding='utf-8') as f:
            for line in f:
                self.samples.append(json.loads(line))
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load audio
        import librosa
        audio, sr = librosa.load(sample['audio_filepath'], sr=self.sample_rate)
        
        # Truncate if too long
        max_samples = int(self.max_duration * self.sample_rate)
        if len(audio) > max_samples:
            audio = audio[:max_samples]
        
        # Process audio
        input_features = self.processor(
            audio,
            sampling_rate=self.sample_rate,
            return_tensors="pt"
        ).input_features[0]
        
        # Process text
        labels = self.processor.tokenizer(
            sample['text'],
            return_tensors="pt"
        ).input_ids[0]
        
        return {
            'input_features': input_features,
            'labels': labels
        }


class SpeechRecognitionTrainer:
    """Trainer for multilingual speech recognition model."""
    
    def __init__(self, config: SpeechRecognitionConfig):
        self.config = config
        
        # Initialize processor and model
        self.processor = WhisperProcessor.from_pretrained(config.model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(config.model_name)
        
        # Configure model
        if config.freeze_encoder:
            for param in self.model.model.encoder.parameters():
                param.requires_grad = False
        
        if config.gradient_checkpointing:
            self.model.config.use_cache = False
            self.model.gradient_checkpointing_enable()
        
        # Add language tokens if needed
        self._setup_language_tokens()
        
        # Initialize metrics
        self.wer_metric = evaluate.load("wer")
        
        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _setup_language_tokens(self):
        """Setup language-specific tokens."""
        # Whisper already has language tokens, but we can add custom ones if needed
        pass
    
    def load_datasets(self) -> Dict[str, Dataset]:
        """Load train, validation, and test datasets."""
        datasets = {}
        
        for split in ['train', 'val', 'test']:
            manifest_files = []
            
            # Collect manifest files for all languages
            for lang in self.config.languages:
                manifest_path = Path(self.config.data_dir) / f"*_{lang}" / f"{split}_manifest.json"
                manifest_files.extend(list(Path(self.config.data_dir).glob(str(manifest_path))))
            
            if manifest_files:
                # For simplicity, use the first manifest file
                # In production, you'd want to combine all manifests
                datasets[split] = SpeechDataset(
                    manifest_file=str(manifest_files[0]),
                    processor=self.processor,
                    sample_rate=self.config.sample_rate,
                    max_duration=self.config.max_duration_seconds
                )
        
        return datasets
    
    def compute_metrics(self, pred):
        """Compute WER metric."""
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        
        # Replace -100 with pad token id
        label_ids[label_ids == -100] = self.processor.tokenizer.pad_token_id
        
        # Decode predictions and labels
        pred_str = self.processor.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = self.processor.batch_decode(label_ids, skip_special_tokens=True)
        
        # Compute WER
        wer = self.wer_metric.compute(predictions=pred_str, references=label_str)
        
        return {"wer": wer}
    
    def train(self):
        """Train the speech recognition model."""
        print("Loading datasets...")
        datasets = self.load_datasets()
        
        if 'train' not in datasets:
            raise ValueError("No training dataset found. Please prepare datasets first.")
        
        print(f"Train samples: {len(datasets['train'])}")
        if 'val' in datasets:
            print(f"Validation samples: {len(datasets['val'])}")
        
        # Training arguments
        training_args = Seq2SeqTrainingArguments(
            output_dir=self.config.output_dir,
            per_device_train_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            warmup_steps=self.config.warmup_steps,
            num_train_epochs=self.config.num_epochs,
            weight_decay=self.config.weight_decay,
            evaluation_strategy="steps" if 'val' in datasets else "no",
            eval_steps=500 if 'val' in datasets else None,
            save_strategy="steps",
            save_steps=500,
            save_total_limit=3,
            logging_steps=50,
            report_to=["mlflow"],
            load_best_model_at_end=True if 'val' in datasets else False,
            metric_for_best_model="wer" if 'val' in datasets else None,
            greater_is_better=False,
            push_to_hub=False,
            predict_with_generate=True,
            generation_max_length=225,
            fp16=torch.cuda.is_available(),
        )
        
        # Initialize trainer
        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=datasets['train'],
            eval_dataset=datasets.get('val'),
            tokenizer=self.processor.feature_extractor,
            compute_metrics=self.compute_metrics if 'val' in datasets else None,
        )
        
        # Start MLflow run
        with mlflow.start_run(run_name="whisper_indian_languages"):
            # Log config
            mlflow.log_params({
                "model_name": self.config.model_name,
                "languages": ",".join(self.config.languages),
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "num_epochs": self.config.num_epochs
            })
            
            # Train
            print("Starting training...")
            trainer.train()
            
            # Evaluate on test set if available
            if 'test' in datasets:
                print("Evaluating on test set...")
                test_results = trainer.evaluate(datasets['test'])
                print(f"Test WER: {test_results['eval_wer']:.4f}")
                mlflow.log_metric("test_wer", test_results['eval_wer'])
            
            # Save final model
            print("Saving model...")
            trainer.save_model(self.config.output_dir)
            self.processor.save_pretrained(self.config.output_dir)
            
            # Log model to MLflow
            mlflow.transformers.log_model(
                transformers_model={
                    "model": self.model,
                    "processor": self.processor
                },
                artifact_path="model"
            )
        
        print("Training complete!")
        return trainer


def main():
    """Main training function."""
    # Configuration
    config = SpeechRecognitionConfig(
        model_name="openai/whisper-small",
        languages=['hi', 'ml', 'pa', 'bn', 'ta', 'te', 'en'],
        batch_size=8,
        num_epochs=20,
        learning_rate=1e-5
    )
    
    # Initialize trainer
    trainer = SpeechRecognitionTrainer(config)
    
    # Train model
    trainer.train()


if __name__ == "__main__":
    main()
