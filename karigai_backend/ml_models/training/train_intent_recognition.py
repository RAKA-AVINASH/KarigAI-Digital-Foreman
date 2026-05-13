"""
Intent Recognition and NLU Model Training for KarigAI

This script trains a BERT/DistilBERT model for intent classification and entity extraction.
Supports multilingual Indian languages and code-mixed speech.
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AdamW,
    get_linear_schedule_with_warmup
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentDataset(Dataset):
    """Dataset for intent classification"""
    
    def __init__(self, data_path: str, tokenizer, max_length: int = 128):
        with open(data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Create intent label mapping
        self.intent_labels = sorted(list(set(item['intent'] for item in self.data)))
        self.intent2id = {label: idx for idx, label in enumerate(self.intent_labels)}
        self.id2intent = {idx: label for label, idx in self.intent2id.items()}
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item['text']
        intent = item['intent']
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(self.intent2id[intent], dtype=torch.long)
        }


class IntentRecognitionModel(nn.Module):
    """Intent recognition model with BERT/DistilBERT backbone"""
    
    def __init__(self, model_name: str, num_intents: int):
        super().__init__()
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_intents
        )
    
    def forward(self, input_ids, attention_mask, labels=None):
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )
        return outputs


class IntentRecognitionTrainer:
    """Trainer for intent recognition model"""
    
    def __init__(
        self,
        model_name: str = 'distilbert-base-multilingual-cased',
        data_dir: str = 'data/processed/nlp/intent',
        output_dir: str = 'models/checkpoints/intent_recognition',
        batch_size: int = 32,
        learning_rate: float = 2e-5,
        num_epochs: int = 10,
        max_length: int = 128,
        device: str = None
    ):
        self.model_name = model_name
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.num_epochs = num_epochs
        self.max_length = max_length
        
        # Device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Load datasets
        self.train_dataset = IntentDataset(
            self.data_dir / 'intent_train.json',
            self.tokenizer,
            max_length
        )
        self.val_dataset = IntentDataset(
            self.data_dir / 'intent_val.json',
            self.tokenizer,
            max_length
        )
        self.test_dataset = IntentDataset(
            self.data_dir / 'intent_test.json',
            self.tokenizer,
            max_length
        )
        
        # Create data loaders
        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=batch_size,
            shuffle=True
        )
        self.val_loader = DataLoader(
            self.val_dataset,
            batch_size=batch_size
        )
        self.test_loader = DataLoader(
            self.test_dataset,
            batch_size=batch_size
        )
        
        # Initialize model
        num_intents = len(self.train_dataset.intent_labels)
        self.model = IntentRecognitionModel(model_name, num_intents)
        self.model.to(self.device)
        
        # Optimizer and scheduler
        self.optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        total_steps = len(self.train_loader) * num_epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=total_steps // 10,
            num_training_steps=total_steps
        )
        
        logger.info(f"Model initialized with {num_intents} intent classes")
        logger.info(f"Training samples: {len(self.train_dataset)}")
        logger.info(f"Validation samples: {len(self.val_dataset)}")
        logger.info(f"Test samples: {len(self.test_dataset)}")
    
    def train_epoch(self) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        
        progress_bar = tqdm(self.train_loader, desc='Training')
        for batch in progress_bar:
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)
            
            self.optimizer.zero_grad()
            
            outputs = self.model(input_ids, attention_mask, labels)
            loss = outputs.loss
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            self.scheduler.step()
            
            total_loss += loss.item()
            progress_bar.set_postfix({'loss': loss.item()})
        
        return total_loss / len(self.train_loader)
    
    def evaluate(self, data_loader: DataLoader) -> Dict:
        """Evaluate model"""
        self.model.eval()
        all_preds = []
        all_labels = []
        total_loss = 0
        
        with torch.no_grad():
            for batch in tqdm(data_loader, desc='Evaluating'):
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.model(input_ids, attention_mask, labels)
                loss = outputs.loss
                logits = outputs.logits
                
                total_loss += loss.item()
                
                preds = torch.argmax(logits, dim=-1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        # Calculate metrics
        accuracy = accuracy_score(all_labels, all_preds)
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_preds, average='weighted'
        )
        
        return {
            'loss': total_loss / len(data_loader),
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
    
    def train(self):
        """Train the model"""
        logger.info("Starting training...")
        
        best_val_accuracy = 0
        
        for epoch in range(self.num_epochs):
            logger.info(f"\nEpoch {epoch + 1}/{self.num_epochs}")
            
            # Train
            train_loss = self.train_epoch()
            logger.info(f"Train loss: {train_loss:.4f}")
            
            # Validate
            val_metrics = self.evaluate(self.val_loader)
            logger.info(f"Val loss: {val_metrics['loss']:.4f}")
            logger.info(f"Val accuracy: {val_metrics['accuracy']:.4f}")
            logger.info(f"Val F1: {val_metrics['f1']:.4f}")
            
            # Save best model
            if val_metrics['accuracy'] > best_val_accuracy:
                best_val_accuracy = val_metrics['accuracy']
                self.save_model('best_model.pt')
                logger.info(f"Saved best model with accuracy: {best_val_accuracy:.4f}")
        
        logger.info("\nTraining complete!")
        logger.info(f"Best validation accuracy: {best_val_accuracy:.4f}")
    
    def test(self):
        """Test the model"""
        logger.info("\nTesting model...")
        
        # Load best model
        self.load_model('best_model.pt')
        
        # Test
        test_metrics = self.evaluate(self.test_loader)
        logger.info(f"Test loss: {test_metrics['loss']:.4f}")
        logger.info(f"Test accuracy: {test_metrics['accuracy']:.4f}")
        logger.info(f"Test precision: {test_metrics['precision']:.4f}")
        logger.info(f"Test recall: {test_metrics['recall']:.4f}")
        logger.info(f"Test F1: {test_metrics['f1']:.4f}")
        
        # Detailed classification report
        self.model.eval()
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch in self.test_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.model(input_ids, attention_mask)
                logits = outputs.logits
                preds = torch.argmax(logits, dim=-1)
                
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        # Print classification report
        intent_names = self.train_dataset.intent_labels
        report = classification_report(all_labels, all_preds, target_names=intent_names)
        logger.info("\nClassification Report:")
        logger.info(f"\n{report}")
        
        return test_metrics
    
    def save_model(self, filename: str):
        """Save model checkpoint"""
        checkpoint_path = self.output_dir / filename
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'intent_labels': self.train_dataset.intent_labels,
            'intent2id': self.train_dataset.intent2id,
            'id2intent': self.train_dataset.id2intent
        }, checkpoint_path)
        logger.info(f"Model saved to {checkpoint_path}")
    
    def load_model(self, filename: str):
        """Load model checkpoint"""
        checkpoint_path = self.output_dir / filename
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Model loaded from {checkpoint_path}")
    
    def export_to_onnx(self, output_path: str):
        """Export model to ONNX format"""
        self.model.eval()
        
        # Dummy input
        dummy_input_ids = torch.randint(0, 1000, (1, self.max_length)).to(self.device)
        dummy_attention_mask = torch.ones((1, self.max_length)).to(self.device)
        
        # Export
        torch.onnx.export(
            self.model.model,
            (dummy_input_ids, dummy_attention_mask),
            output_path,
            input_names=['input_ids', 'attention_mask'],
            output_names=['logits'],
            dynamic_axes={
                'input_ids': {0: 'batch_size'},
                'attention_mask': {0: 'batch_size'},
                'logits': {0: 'batch_size'}
            },
            opset_version=14
        )
        logger.info(f"Model exported to ONNX: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Train intent recognition model')
    parser.add_argument('--model_name', type=str, default='distilbert-base-multilingual-cased',
                       help='Pretrained model name')
    parser.add_argument('--data_dir', type=str, default='data/processed/nlp/intent',
                       help='Data directory')
    parser.add_argument('--output_dir', type=str, default='models/checkpoints/intent_recognition',
                       help='Output directory')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=2e-5,
                       help='Learning rate')
    parser.add_argument('--num_epochs', type=int, default=10,
                       help='Number of epochs')
    parser.add_argument('--max_length', type=int, default=128,
                       help='Maximum sequence length')
    parser.add_argument('--export_onnx', type=str, default=None,
                       help='Export model to ONNX format')
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = IntentRecognitionTrainer(
        model_name=args.model_name,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        num_epochs=args.num_epochs,
        max_length=args.max_length
    )
    
    # Train
    trainer.train()
    
    # Test
    test_metrics = trainer.test()
    
    # Check if target accuracy is met
    if test_metrics['accuracy'] >= 0.90:
        logger.info(f"✓ Target accuracy achieved: {test_metrics['accuracy']:.4f} >= 0.90")
    else:
        logger.warning(f"✗ Target accuracy not met: {test_metrics['accuracy']:.4f} < 0.90")
    
    # Export to ONNX if requested
    if args.export_onnx:
        trainer.export_to_onnx(args.export_onnx)


if __name__ == '__main__':
    main()
