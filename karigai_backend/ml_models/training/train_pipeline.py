"""
Generic training pipeline for all KarigAI models.
Provides reusable training infrastructure with MLflow integration.
"""

import os
import yaml
import torch
import mlflow
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from torch.utils.data import DataLoader
from tqdm import tqdm


@dataclass
class TrainingConfig:
    """Configuration for training pipeline."""
    model_name: str
    batch_size: int
    learning_rate: float
    num_epochs: int
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    mixed_precision: bool = True
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    warmup_steps: int = 0
    weight_decay: float = 0.01
    save_every_n_epochs: int = 1
    eval_every_n_steps: int = 500
    log_every_n_steps: int = 50
    checkpoint_dir: str = "./ml_models/models/checkpoints"
    early_stopping_patience: int = 5
    early_stopping_min_delta: float = 0.001


class TrainingPipeline:
    """Generic training pipeline with MLflow tracking."""
    
    def __init__(
        self,
        config: TrainingConfig,
        model: torch.nn.Module,
        train_dataloader: DataLoader,
        val_dataloader: Optional[DataLoader] = None,
        optimizer: Optional[torch.optim.Optimizer] = None,
        scheduler: Optional[Any] = None,
        loss_fn: Optional[Callable] = None,
        metric_fn: Optional[Callable] = None
    ):
        self.config = config
        self.model = model.to(config.device)
        self.train_dataloader = train_dataloader
        self.val_dataloader = val_dataloader
        
        # Setup optimizer
        if optimizer is None:
            self.optimizer = torch.optim.AdamW(
                model.parameters(),
                lr=config.learning_rate,
                weight_decay=config.weight_decay
            )
        else:
            self.optimizer = optimizer
        
        self.scheduler = scheduler
        self.loss_fn = loss_fn or torch.nn.CrossEntropyLoss()
        self.metric_fn = metric_fn
        
        # Training state
        self.global_step = 0
        self.best_metric = float('inf')
        self.patience_counter = 0
        
        # Mixed precision training
        self.scaler = torch.cuda.amp.GradScaler() if config.mixed_precision else None
        
        # Create checkpoint directory
        Path(config.checkpoint_dir).mkdir(parents=True, exist_ok=True)
    
    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        num_batches = 0
        
        progress_bar = tqdm(self.train_dataloader, desc=f"Epoch {epoch}")
        
        for batch_idx, batch in enumerate(progress_bar):
            # Move batch to device
            batch = {k: v.to(self.config.device) if isinstance(v, torch.Tensor) else v 
                    for k, v in batch.items()}
            
            # Forward pass with mixed precision
            if self.config.mixed_precision and self.scaler:
                with torch.cuda.amp.autocast():
                    outputs = self.model(**batch)
                    loss = self.loss_fn(outputs, batch.get('labels'))
                    loss = loss / self.config.gradient_accumulation_steps
                
                # Backward pass
                self.scaler.scale(loss).backward()
            else:
                outputs = self.model(**batch)
                loss = self.loss_fn(outputs, batch.get('labels'))
                loss = loss / self.config.gradient_accumulation_steps
                loss.backward()
            
            # Gradient accumulation
            if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                if self.config.mixed_precision and self.scaler:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), 
                        self.config.max_grad_norm
                    )
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), 
                        self.config.max_grad_norm
                    )
                    self.optimizer.step()
                
                if self.scheduler:
                    self.scheduler.step()
                
                self.optimizer.zero_grad()
                self.global_step += 1
                
                # Logging
                if self.global_step % self.config.log_every_n_steps == 0:
                    mlflow.log_metric("train_loss", loss.item(), step=self.global_step)
                    if self.scheduler:
                        mlflow.log_metric("learning_rate", 
                                        self.scheduler.get_last_lr()[0], 
                                        step=self.global_step)
                
                # Validation
                if self.val_dataloader and self.global_step % self.config.eval_every_n_steps == 0:
                    val_metrics = self.validate()
                    for key, value in val_metrics.items():
                        mlflow.log_metric(f"val_{key}", value, step=self.global_step)
            
            total_loss += loss.item()
            num_batches += 1
            progress_bar.set_postfix({"loss": total_loss / num_batches})
        
        return {"loss": total_loss / num_batches}
    
    def validate(self) -> Dict[str, float]:
        """Validate the model."""
        if not self.val_dataloader:
            return {}
        
        self.model.eval()
        total_loss = 0
        num_batches = 0
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for batch in tqdm(self.val_dataloader, desc="Validation"):
                batch = {k: v.to(self.config.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                
                outputs = self.model(**batch)
                loss = self.loss_fn(outputs, batch.get('labels'))
                
                total_loss += loss.item()
                num_batches += 1
                
                if self.metric_fn:
                    predictions = torch.argmax(outputs, dim=-1)
                    all_predictions.extend(predictions.cpu().numpy())
                    all_labels.extend(batch.get('labels').cpu().numpy())
        
        metrics = {"loss": total_loss / num_batches}
        
        if self.metric_fn and all_predictions:
            custom_metrics = self.metric_fn(
                np.array(all_predictions), 
                np.array(all_labels)
            )
            metrics.update(custom_metrics)
        
        self.model.train()
        return metrics
    
    def save_checkpoint(self, epoch: int, metrics: Dict[str, float]):
        """Save model checkpoint."""
        checkpoint_path = Path(self.config.checkpoint_dir) / f"{self.config.model_name}_epoch_{epoch}.pt"
        
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
            'metrics': metrics,
            'global_step': self.global_step
        }, checkpoint_path)
        
        print(f"Checkpoint saved: {checkpoint_path}")
        
        # Log to MLflow
        mlflow.log_artifact(str(checkpoint_path))
    
    def train(self) -> Dict[str, Any]:
        """Main training loop."""
        print(f"Starting training on {self.config.device}")
        print(f"Model: {self.config.model_name}")
        print(f"Epochs: {self.config.num_epochs}")
        print(f"Batch size: {self.config.batch_size}")
        
        # Start MLflow run
        with mlflow.start_run(run_name=self.config.model_name):
            # Log config
            mlflow.log_params({
                "model_name": self.config.model_name,
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "num_epochs": self.config.num_epochs,
                "device": self.config.device
            })
            
            for epoch in range(1, self.config.num_epochs + 1):
                # Train
                train_metrics = self.train_epoch(epoch)
                print(f"Epoch {epoch} - Train Loss: {train_metrics['loss']:.4f}")
                
                # Validate
                if self.val_dataloader:
                    val_metrics = self.validate()
                    print(f"Epoch {epoch} - Val Loss: {val_metrics['loss']:.4f}")
                    
                    # Log epoch metrics
                    mlflow.log_metrics({
                        "epoch_train_loss": train_metrics['loss'],
                        "epoch_val_loss": val_metrics['loss']
                    }, step=epoch)
                    
                    # Early stopping check
                    current_metric = val_metrics['loss']
                    if current_metric < self.best_metric - self.config.early_stopping_min_delta:
                        self.best_metric = current_metric
                        self.patience_counter = 0
                        # Save best model
                        self.save_checkpoint(epoch, val_metrics)
                    else:
                        self.patience_counter += 1
                        if self.patience_counter >= self.config.early_stopping_patience:
                            print(f"Early stopping triggered at epoch {epoch}")
                            break
                
                # Save checkpoint
                if epoch % self.config.save_every_n_epochs == 0:
                    self.save_checkpoint(epoch, train_metrics)
            
            print("Training complete!")
            return {"best_metric": self.best_metric}


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    print("Training pipeline module loaded successfully!")
    print("Use this module to train KarigAI models with MLflow tracking.")
