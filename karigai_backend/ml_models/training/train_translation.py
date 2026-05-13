"""
Translation and Language Transformation Model Training for KarigAI

This script trains an mBART/mT5 model for translation between Indian languages
and language register transformation (colloquial to formal).
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    MBartForConditionalGeneration,
    MBart50TokenizerFast,
    AdamW,
    get_linear_schedule_with_warmup
)
from sacrebleu import corpus_bleu
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranslationDataset(Dataset):
    """Dataset for translation"""
    
    def __init__(self, data_path: str, tokenizer, max_length: int = 128):
        with open(data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Language code mapping for mBART
        self.lang_code_map = {
            'hi': 'hi_IN',
            'en': 'en_XX',
            'ml': 'ml_IN',
            'pa': 'pa_IN',
            'bn': 'bn_IN',
            'ta': 'ta_IN',
            'te': 'te_IN'
        }
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        source_text = item['source']
        target_text = item['target']
        source_lang = self.lang_code_map.get(item['source_lang'], 'en_XX')
        target_lang = self.lang_code_map.get(item['target_lang'], 'en_XX')
        
        # Tokenize source
        self.tokenizer.src_lang = source_lang
        source_encoding = self.tokenizer(
            source_text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Tokenize target
        with self.tokenizer.as_target_tokenizer():
            target_encoding = self.tokenizer(
                target_text,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
        
        labels = target_encoding['input_ids'].squeeze()
        labels[labels == self.tokenizer.pad_token_id] = -100
        
        return {
            'input_ids': source_encoding['input_ids'].squeeze(),
            'attention_mask': source_encoding['attention_mask'].squeeze(),
            'labels': labels,
            'source_lang': source_lang,
            'target_lang': target_lang
        }


class TranslationTrainer:
    """Trainer for translation model"""
    
    def __init__(
        self,
        model_name: str = 'facebook/mbart-large-50-many-to-many-mmt',
        data_dir: str = 'data/processed/nlp/translation',
        output_dir: str = 'models/checkpoints/translation',
        batch_size: int = 16,
        learning_rate: float = 3e-5,
        num_epochs: int = 20,
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
        
        # Load tokenizer and model
        self.tokenizer = MBart50TokenizerFast.from_pretrained(model_name)
        self.model = MBartForConditionalGeneration.from_pretrained(model_name)
        self.model.to(self.device)
        
        # Load datasets
        self.train_dataset = TranslationDataset(
            self.data_dir / 'translation_train.json',
            self.tokenizer,
            max_length
        )
        self.val_dataset = TranslationDataset(
            self.data_dir / 'translation_val.json',
            self.tokenizer,
            max_length
        )
        self.test_dataset = TranslationDataset(
            self.data_dir / 'translation_test.json',
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
            
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
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
        total_loss = 0
        all_predictions = []
        all_references = []
        
        with torch.no_grad():
            for batch in tqdm(data_loader, desc='Evaluating'):
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                # Calculate loss
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                total_loss += outputs.loss.item()
                
                # Generate translations
                generated_ids = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_length=self.max_length,
                    num_beams=4,
                    early_stopping=True
                )
                
                # Decode predictions and references
                predictions = self.tokenizer.batch_decode(
                    generated_ids,
                    skip_special_tokens=True
                )
                references = self.tokenizer.batch_decode(
                    labels,
                    skip_special_tokens=True
                )
                
                all_predictions.extend(predictions)
                all_references.extend([[ref] for ref in references])
        
        # Calculate BLEU score
        bleu_score = corpus_bleu(all_predictions, all_references).score
        
        return {
            'loss': total_loss / len(data_loader),
            'bleu': bleu_score
        }
    
    def train(self):
        """Train the model"""
        logger.info("Starting training...")
        
        best_bleu = 0
        
        for epoch in range(self.num_epochs):
            logger.info(f"\nEpoch {epoch + 1}/{self.num_epochs}")
            
            # Train
            train_loss = self.train_epoch()
            logger.info(f"Train loss: {train_loss:.4f}")
            
            # Validate
            val_metrics = self.evaluate(self.val_loader)
            logger.info(f"Val loss: {val_metrics['loss']:.4f}")
            logger.info(f"Val BLEU: {val_metrics['bleu']:.2f}")
            
            # Save best model
            if val_metrics['bleu'] > best_bleu:
                best_bleu = val_metrics['bleu']
                self.save_model('best_model.pt')
                logger.info(f"Saved best model with BLEU: {best_bleu:.2f}")
        
        logger.info("\nTraining complete!")
        logger.info(f"Best validation BLEU: {best_bleu:.2f}")
    
    def test(self):
        """Test the model"""
        logger.info("\nTesting model...")
        
        # Load best model
        self.load_model('best_model.pt')
        
        # Test
        test_metrics = self.evaluate(self.test_loader)
        logger.info(f"Test loss: {test_metrics['loss']:.4f}")
        logger.info(f"Test BLEU: {test_metrics['bleu']:.2f}")
        
        # Sample translations
        logger.info("\nSample translations:")
        self.model.eval()
        
        with open(self.data_dir / 'translation_test.json', 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        for i in range(min(5, len(test_data))):
            item = test_data[i]
            source_text = item['source']
            target_text = item['target']
            
            # Translate
            self.tokenizer.src_lang = self.train_dataset.lang_code_map.get(item['source_lang'], 'en_XX')
            inputs = self.tokenizer(source_text, return_tensors='pt').to(self.device)
            
            generated_ids = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.lang_code_to_id[
                    self.train_dataset.lang_code_map.get(item['target_lang'], 'en_XX')
                ],
                max_length=self.max_length,
                num_beams=4
            )
            
            translation = self.tokenizer.decode(generated_ids[0], skip_special_tokens=True)
            
            logger.info(f"\nSource ({item['source_lang']}): {source_text}")
            logger.info(f"Reference ({item['target_lang']}): {target_text}")
            logger.info(f"Translation: {translation}")
        
        return test_metrics
    
    def save_model(self, filename: str):
        """Save model checkpoint"""
        checkpoint_path = self.output_dir / filename
        self.model.save_pretrained(checkpoint_path)
        self.tokenizer.save_pretrained(checkpoint_path)
        logger.info(f"Model saved to {checkpoint_path}")
    
    def load_model(self, filename: str):
        """Load model checkpoint"""
        checkpoint_path = self.output_dir / filename
        self.model = MBartForConditionalGeneration.from_pretrained(checkpoint_path)
        self.model.to(self.device)
        logger.info(f"Model loaded from {checkpoint_path}")
    
    def export_to_onnx(self, output_path: str):
        """Export model to ONNX format"""
        logger.info("Exporting to ONNX...")
        self.model.eval()
        
        # Dummy input
        dummy_input_ids = torch.randint(0, 1000, (1, self.max_length)).to(self.device)
        dummy_attention_mask = torch.ones((1, self.max_length)).to(self.device)
        
        # Export encoder
        torch.onnx.export(
            self.model.model.encoder,
            (dummy_input_ids, dummy_attention_mask),
            output_path.replace('.onnx', '_encoder.onnx'),
            input_names=['input_ids', 'attention_mask'],
            output_names=['last_hidden_state'],
            dynamic_axes={
                'input_ids': {0: 'batch_size'},
                'attention_mask': {0: 'batch_size'},
                'last_hidden_state': {0: 'batch_size'}
            },
            opset_version=14
        )
        logger.info(f"Encoder exported to: {output_path.replace('.onnx', '_encoder.onnx')}")


def main():
    parser = argparse.ArgumentParser(description='Train translation model')
    parser.add_argument('--model_name', type=str, default='facebook/mbart-large-50-many-to-many-mmt',
                       help='Pretrained model name')
    parser.add_argument('--data_dir', type=str, default='data/processed/nlp/translation',
                       help='Data directory')
    parser.add_argument('--output_dir', type=str, default='models/checkpoints/translation',
                       help='Output directory')
    parser.add_argument('--batch_size', type=int, default=16,
                       help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=3e-5,
                       help='Learning rate')
    parser.add_argument('--num_epochs', type=int, default=20,
                       help='Number of epochs')
    parser.add_argument('--max_length', type=int, default=128,
                       help='Maximum sequence length')
    parser.add_argument('--export_onnx', type=str, default=None,
                       help='Export model to ONNX format')
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = TranslationTrainer(
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
    
    # Check if target BLEU is met
    if test_metrics['bleu'] >= 30.0:
        logger.info(f"✓ Target BLEU achieved: {test_metrics['bleu']:.2f} >= 30.0")
    else:
        logger.warning(f"✗ Target BLEU not met: {test_metrics['bleu']:.2f} < 30.0")
    
    # Export to ONNX if requested
    if args.export_onnx:
        trainer.export_to_onnx(args.export_onnx)


if __name__ == '__main__':
    main()
