"""
Government Scheme Matching Model Training for KarigAI

This script trains a classification model for matching users with eligible
government schemes based on their profile.
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModel,
    AdamW,
    get_linear_schedule_with_warmup
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemeMatchingDataset(Dataset):
    """Dataset for scheme matching"""
    
    def __init__(self, profiles_path: str, schemes_path: str, tokenizer, max_length: int = 256):
        # Load user profiles
        with open(profiles_path, 'r', encoding='utf-8') as f:
            self.profiles = json.load(f)
        
        # Load schemes
        with open(schemes_path, 'r', encoding='utf-8') as f:
            self.schemes = json.load(f)
        
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Create training examples (user-scheme pairs with eligibility labels)
        self.examples = self._create_examples()
    
    def _check_eligibility(self, profile: Dict, scheme: Dict) -> bool:
        """Check if user is eligible for scheme"""
        eligibility = scheme['eligibility']
        
        # Check age
        if 'age_min' in eligibility and profile['age'] < eligibility['age_min']:
            return False
        if 'age_max' in eligibility and profile['age'] > eligibility['age_max']:
            return False
        
        # Check income
        if 'income_max' in eligibility and profile['income'] > eligibility['income_max']:
            return False
        
        # Check trade
        if 'trade' in eligibility and profile['trade'] != eligibility['trade']:
            return False
        
        # Check state
        if 'state' in eligibility and profile['state'] != eligibility['state']:
            return False
        
        return True
    
    def _create_examples(self) -> List[Dict]:
        """Create user-scheme pairs with eligibility labels"""
        examples = []
        
        for profile in self.profiles:
            # Create profile text
            profile_text = f"Age: {profile['age']}, Income: {profile['income']}, Trade: {profile['trade']}, State: {profile['state']}, Education: {profile['education']}"
            
            # Sample positive and negative schemes
            eligible_schemes = [s for s in self.schemes if self._check_eligibility(profile, s)]
            ineligible_schemes = [s for s in self.schemes if not self._check_eligibility(profile, s)]
            
            # Add positive examples
            for scheme in eligible_schemes[:3]:  # Limit to 3 per user
                scheme_text = f"{scheme['name']}. {scheme['description']}. Benefits: {scheme['benefits']}"
                examples.append({
                    'profile_text': profile_text,
                    'scheme_text': scheme_text,
                    'label': 1
                })
            
            # Add negative examples (balanced)
            for scheme in np.random.choice(ineligible_schemes, min(3, len(ineligible_schemes)), replace=False):
                scheme_text = f"{scheme['name']}. {scheme['description']}. Benefits: {scheme['benefits']}"
                examples.append({
                    'profile_text': profile_text,
                    'scheme_text': scheme_text,
                    'label': 0
                })
        
        return examples
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        example = self.examples[idx]
        
        # Combine profile and scheme text
        combined_text = f"[PROFILE] {example['profile_text']} [SCHEME] {example['scheme_text']}"
        
        # Tokenize
        encoding = self.tokenizer(
            combined_text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(example['label'], dtype=torch.long)
        }


class SchemeMatchingModel(nn.Module):
    """Scheme matching model with BERT backbone"""
    
    def __init__(self, model_name: str):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        self.classifier = nn.Linear(self.bert.config.hidden_size, 2)  # Binary classification
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, input_ids, attention_mask, labels=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        # Use [CLS] token embedding
        pooled_output = outputs.last_hidden_state[:, 0, :]
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        
        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits, labels)
        
        return {'loss': loss, 'logits': logits}


class SchemeMatchingTrainer:
    """Trainer for scheme matching model"""
    
    def __init__(
        self,
        model_name: str = 'distilbert-base-multilingual-cased',
        data_dir: str = 'data/processed/nlp/schemes',
        output_dir: str = 'models/checkpoints/scheme_matching',
        batch_size: int = 32,
        learning_rate: float = 2e-5,
        num_epochs: int = 10,
        max_length: int = 256,
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
        schemes_path = self.data_dir / 'schemes.json'
        
        self.train_dataset = SchemeMatchingDataset(
            self.data_dir / 'profiles_train.json',
            schemes_path,
            self.tokenizer,
            max_length
        )
        self.val_dataset = SchemeMatchingDataset(
            self.data_dir / 'profiles_val.json',
            schemes_path,
            self.tokenizer,
            max_length
        )
        self.test_dataset = SchemeMatchingDataset(
            self.data_dir / 'profiles_test.json',
            schemes_path,
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
        self.model = SchemeMatchingModel(model_name)
        self.model.to(self.device)
        
        # Optimizer and scheduler
        self.optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        total_steps = len(self.train_loader) * num_epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=total_steps // 10,
            num_training_steps=total_steps
        )
        
        logger.info(f"Model initialized")
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
            loss = outputs['loss']
            
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
                loss = outputs['loss']
                logits = outputs['logits']
                
                total_loss += loss.item()
                
                preds = torch.argmax(logits, dim=-1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        # Calculate metrics
        accuracy = accuracy_score(all_labels, all_preds)
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_preds, average='binary'
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
        
        best_accuracy = 0
        
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
            if val_metrics['accuracy'] > best_accuracy:
                best_accuracy = val_metrics['accuracy']
                self.save_model('best_model.pt')
                logger.info(f"Saved best model with accuracy: {best_accuracy:.4f}")
        
        logger.info("\nTraining complete!")
        logger.info(f"Best validation accuracy: {best_accuracy:.4f}")
    
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
        
        return test_metrics
    
    def save_model(self, filename: str):
        """Save model checkpoint"""
        checkpoint_path = self.output_dir / filename
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict()
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
            self.model,
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
    parser = argparse.ArgumentParser(description='Train scheme matching model')
    parser.add_argument('--model_name', type=str, default='distilbert-base-multilingual-cased',
                       help='Pretrained model name')
    parser.add_argument('--data_dir', type=str, default='data/processed/nlp/schemes',
                       help='Data directory')
    parser.add_argument('--output_dir', type=str, default='models/checkpoints/scheme_matching',
                       help='Output directory')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=2e-5,
                       help='Learning rate')
    parser.add_argument('--num_epochs', type=int, default=10,
                       help='Number of epochs')
    parser.add_argument('--max_length', type=int, default=256,
                       help='Maximum sequence length')
    parser.add_argument('--export_onnx', type=str, default=None,
                       help='Export model to ONNX format')
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = SchemeMatchingTrainer(
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
    if test_metrics['accuracy'] >= 0.85:
        logger.info(f"✓ Target accuracy achieved: {test_metrics['accuracy']:.4f} >= 0.85")
    else:
        logger.warning(f"✗ Target accuracy not met: {test_metrics['accuracy']:.4f} < 0.85")
    
    # Export to ONNX if requested
    if args.export_onnx:
        trainer.export_to_onnx(args.export_onnx)


if __name__ == '__main__':
    main()
