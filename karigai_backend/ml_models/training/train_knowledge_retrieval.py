"""
Knowledge Retrieval and QA Model Training for KarigAI

This script trains a Dense Passage Retrieval (DPR) model for retrieving
troubleshooting information and answering questions.
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
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModel,
    AdamW,
    get_linear_schedule_with_warmup
)
from sklearn.metrics import accuracy_score
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeDataset(Dataset):
    """Dataset for knowledge retrieval"""
    
    def __init__(self, data_path: str, tokenizer, max_length: int = 256):
        with open(data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        question = item['question']
        context = item['context']
        answer = item['answer']
        
        # Tokenize question
        question_encoding = self.tokenizer(
            question,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # Tokenize context
        context_encoding = self.tokenizer(
            context,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'question_input_ids': question_encoding['input_ids'].squeeze(),
            'question_attention_mask': question_encoding['attention_mask'].squeeze(),
            'context_input_ids': context_encoding['input_ids'].squeeze(),
            'context_attention_mask': context_encoding['attention_mask'].squeeze(),
            'answer': answer
        }


class DualEncoder(nn.Module):
    """Dual encoder for question and context"""
    
    def __init__(self, model_name: str, embedding_dim: int = 768):
        super().__init__()
        self.question_encoder = AutoModel.from_pretrained(model_name)
        self.context_encoder = AutoModel.from_pretrained(model_name)
        self.embedding_dim = embedding_dim
    
    def encode_question(self, input_ids, attention_mask):
        """Encode question"""
        outputs = self.question_encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        # Use [CLS] token embedding
        return outputs.last_hidden_state[:, 0, :]
    
    def encode_context(self, input_ids, attention_mask):
        """Encode context"""
        outputs = self.context_encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        # Use [CLS] token embedding
        return outputs.last_hidden_state[:, 0, :]
    
    def forward(self, question_input_ids, question_attention_mask,
                context_input_ids, context_attention_mask):
        """Forward pass"""
        question_embedding = self.encode_question(question_input_ids, question_attention_mask)
        context_embedding = self.encode_context(context_input_ids, context_attention_mask)
        return question_embedding, context_embedding


class KnowledgeRetrievalTrainer:
    """Trainer for knowledge retrieval model"""
    
    def __init__(
        self,
        model_name: str = 'bert-base-multilingual-cased',
        data_dir: str = 'data/processed/nlp/knowledge',
        output_dir: str = 'models/checkpoints/knowledge_retrieval',
        batch_size: int = 32,
        learning_rate: float = 1e-5,
        num_epochs: int = 15,
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
        self.train_dataset = KnowledgeDataset(
            self.data_dir / 'knowledge_train.json',
            self.tokenizer,
            max_length
        )
        self.val_dataset = KnowledgeDataset(
            self.data_dir / 'knowledge_val.json',
            self.tokenizer,
            max_length
        )
        self.test_dataset = KnowledgeDataset(
            self.data_dir / 'knowledge_test.json',
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
        self.model = DualEncoder(model_name)
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
    
    def contrastive_loss(self, question_embeddings, context_embeddings):
        """Compute contrastive loss for retrieval"""
        # Compute similarity scores
        scores = torch.matmul(question_embeddings, context_embeddings.T)
        
        # Labels: diagonal elements are positive pairs
        labels = torch.arange(scores.size(0)).to(self.device)
        
        # Cross-entropy loss
        loss = F.cross_entropy(scores, labels)
        return loss
    
    def train_epoch(self) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        
        progress_bar = tqdm(self.train_loader, desc='Training')
        for batch in progress_bar:
            question_input_ids = batch['question_input_ids'].to(self.device)
            question_attention_mask = batch['question_attention_mask'].to(self.device)
            context_input_ids = batch['context_input_ids'].to(self.device)
            context_attention_mask = batch['context_attention_mask'].to(self.device)
            
            self.optimizer.zero_grad()
            
            # Forward pass
            question_embeddings, context_embeddings = self.model(
                question_input_ids, question_attention_mask,
                context_input_ids, context_attention_mask
            )
            
            # Compute loss
            loss = self.contrastive_loss(question_embeddings, context_embeddings)
            
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
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in tqdm(data_loader, desc='Evaluating'):
                question_input_ids = batch['question_input_ids'].to(self.device)
                question_attention_mask = batch['question_attention_mask'].to(self.device)
                context_input_ids = batch['context_input_ids'].to(self.device)
                context_attention_mask = batch['context_attention_mask'].to(self.device)
                
                # Forward pass
                question_embeddings, context_embeddings = self.model(
                    question_input_ids, question_attention_mask,
                    context_input_ids, context_attention_mask
                )
                
                # Compute loss
                loss = self.contrastive_loss(question_embeddings, context_embeddings)
                total_loss += loss.item()
                
                # Compute accuracy (top-1 retrieval)
                scores = torch.matmul(question_embeddings, context_embeddings.T)
                predictions = torch.argmax(scores, dim=1)
                labels = torch.arange(scores.size(0)).to(self.device)
                
                correct += (predictions == labels).sum().item()
                total += labels.size(0)
        
        accuracy = correct / total
        
        return {
            'loss': total_loss / len(data_loader),
            'accuracy': accuracy
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
        
        # Export question encoder
        torch.onnx.export(
            self.model.question_encoder,
            (dummy_input_ids, dummy_attention_mask),
            output_path.replace('.onnx', '_question_encoder.onnx'),
            input_names=['input_ids', 'attention_mask'],
            output_names=['last_hidden_state'],
            dynamic_axes={
                'input_ids': {0: 'batch_size'},
                'attention_mask': {0: 'batch_size'},
                'last_hidden_state': {0: 'batch_size'}
            },
            opset_version=14
        )
        
        # Export context encoder
        torch.onnx.export(
            self.model.context_encoder,
            (dummy_input_ids, dummy_attention_mask),
            output_path.replace('.onnx', '_context_encoder.onnx'),
            input_names=['input_ids', 'attention_mask'],
            output_names=['last_hidden_state'],
            dynamic_axes={
                'input_ids': {0: 'batch_size'},
                'attention_mask': {0: 'batch_size'},
                'last_hidden_state': {0: 'batch_size'}
            },
            opset_version=14
        )
        
        logger.info(f"Models exported to ONNX")


def main():
    parser = argparse.ArgumentParser(description='Train knowledge retrieval model')
    parser.add_argument('--model_name', type=str, default='bert-base-multilingual-cased',
                       help='Pretrained model name')
    parser.add_argument('--data_dir', type=str, default='data/processed/nlp/knowledge',
                       help='Data directory')
    parser.add_argument('--output_dir', type=str, default='models/checkpoints/knowledge_retrieval',
                       help='Output directory')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=1e-5,
                       help='Learning rate')
    parser.add_argument('--num_epochs', type=int, default=15,
                       help='Number of epochs')
    parser.add_argument('--max_length', type=int, default=256,
                       help='Maximum sequence length')
    parser.add_argument('--export_onnx', type=str, default=None,
                       help='Export model to ONNX format')
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = KnowledgeRetrievalTrainer(
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
    if test_metrics['accuracy'] >= 0.75:
        logger.info(f"✓ Target accuracy achieved: {test_metrics['accuracy']:.4f} >= 0.75")
    else:
        logger.warning(f"✗ Target accuracy not met: {test_metrics['accuracy']:.4f} < 0.75")
    
    # Export to ONNX if requested
    if args.export_onnx:
        trainer.export_to_onnx(args.export_onnx)


if __name__ == '__main__':
    main()
