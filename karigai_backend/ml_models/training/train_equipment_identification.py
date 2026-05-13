"""
Equipment Identification Model Training

This script trains a ResNet50 or EfficientNet model for equipment identification
with multi-label classification for brand, model, and type.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models
import timm
from pathlib import Path
import json
import cv2
import numpy as np
from tqdm import tqdm
import mlflow
import mlflow.pytorch
from sklearn.metrics import accuracy_score, top_k_accuracy_score, classification_report
import sys
sys.path.append('..')
from utils.vision_augmentation import VisionAugmentation


class EquipmentDataset(Dataset):
    """Dataset for equipment identification"""
    
    def __init__(self, data_dir, split='train', transform=None):
        """
        Initialize dataset
        
        Args:
            data_dir: Base directory containing processed data
            split: 'train', 'val', or 'test'
            transform: Augmentation transforms
        """
        self.data_dir = Path(data_dir) / split
        self.transform = transform
        
        # Load images and labels
        self.images = []
        self.labels = []
        
        # Assuming directory structure: data_dir/split/category/image.jpg
        for category_dir in self.data_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                for img_path in category_dir.glob('*.*'):
                    if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        self.images.append(img_path)
                        self.labels.append(category)
        
        # Create label mappings
        self.unique_labels = sorted(list(set(self.labels)))
        self.label_to_idx = {label: idx for idx, label in enumerate(self.unique_labels)}
        self.idx_to_label = {idx: label for label, idx in self.label_to_idx.items()}
        
        print(f"Loaded {len(self.images)} images from {split} split")
        print(f"Number of categories: {len(self.unique_labels)}")
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        img_path = self.images[idx]
        label = self.labels[idx]
        
        # Load image
        image = cv2.imread(str(img_path))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Apply transforms
        if self.transform:
            augmented = self.transform(image=image)
            image = augmented['image']
        
        label_idx = self.label_to_idx[label]
        
        return image, label_idx


class EquipmentIdentificationModel(nn.Module):
    """Equipment identification model with attention mechanism"""
    
    def __init__(self, num_classes, model_name='resnet50', pretrained=True):
        """
        Initialize model
        
        Args:
            num_classes: Number of equipment categories
            model_name: 'resnet50' or 'efficientnet_b0'
            pretrained: Whether to use pretrained weights
        """
        super(EquipmentIdentificationModel, self).__init__()
        
        if model_name == 'resnet50':
            self.backbone = models.resnet50(pretrained=pretrained)
            num_features = self.backbone.fc.in_features
            self.backbone.fc = nn.Identity()  # Remove final FC layer
        elif model_name == 'efficientnet_b0':
            self.backbone = timm.create_model('efficientnet_b0', pretrained=pretrained)
            num_features = self.backbone.classifier.in_features
            self.backbone.classifier = nn.Identity()
        else:
            raise ValueError(f"Unsupported model: {model_name}")
        
        # Attention mechanism for error code region detection
        self.attention = nn.Sequential(
            nn.Linear(num_features, num_features // 4),
            nn.ReLU(),
            nn.Linear(num_features // 4, 1),
            nn.Sigmoid()
        )
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        # Extract features
        features = self.backbone(x)
        
        # Apply attention
        attention_weights = self.attention(features)
        attended_features = features * attention_weights
        
        # Classification
        output = self.classifier(attended_features)
        
        return output, attention_weights


class FocalLoss(nn.Module):
    """Focal Loss for handling class imbalance"""
    
    def __init__(self, alpha=1, gamma=2):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.ce = nn.CrossEntropyLoss(reduction='none')
    
    def forward(self, inputs, targets):
        ce_loss = self.ce(inputs, targets)
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        return focal_loss.mean()


def train_epoch(model, dataloader, criterion, optimizer, device):
    """Train for one epoch"""
    model.train()
    running_loss = 0.0
    predictions = []
    targets = []
    
    pbar = tqdm(dataloader, desc='Training')
    for images, labels in pbar:
        images = images.to(device)
        labels = labels.to(device)
        
        optimizer.zero_grad()
        
        outputs, _ = model(images)
        loss = criterion(outputs, labels)
        
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()
        
        _, preds = torch.max(outputs, 1)
        predictions.extend(preds.cpu().numpy())
        targets.extend(labels.cpu().numpy())
        
        pbar.set_postfix({'loss': loss.item()})
    
    epoch_loss = running_loss / len(dataloader)
    epoch_acc = accuracy_score(targets, predictions)
    
    return epoch_loss, epoch_acc


def validate(model, dataloader, criterion, device):
    """Validate model"""
    model.eval()
    running_loss = 0.0
    predictions = []
    targets = []
    all_probs = []
    
    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc='Validation'):
            images = images.to(device)
            labels = labels.to(device)
            
            outputs, _ = model(images)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            
            probs = torch.softmax(outputs, dim=1)
            all_probs.append(probs.cpu().numpy())
            
            _, preds = torch.max(outputs, 1)
            predictions.extend(preds.cpu().numpy())
            targets.extend(labels.cpu().numpy())
    
    epoch_loss = running_loss / len(dataloader)
    epoch_acc = accuracy_score(targets, predictions)
    
    # Calculate top-5 accuracy
    all_probs = np.vstack(all_probs)
    top5_acc = top_k_accuracy_score(targets, all_probs, k=5, labels=range(all_probs.shape[1]))
    
    return epoch_loss, epoch_acc, top5_acc


def main():
    # Configuration
    config = {
        'data_dir': '../data/vision/equipment/processed',
        'model_name': 'resnet50',  # or 'efficientnet_b0'
        'image_size': 224,
        'batch_size': 32,
        'num_epochs': 50,
        'learning_rate': 0.001,
        'weight_decay': 1e-4,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'num_workers': 4,
        'save_dir': '../models/checkpoints/equipment',
        'use_focal_loss': True,
        'focal_alpha': 1.0,
        'focal_gamma': 2.0,
    }
    
    print("Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # Create save directory
    Path(config['save_dir']).mkdir(parents=True, exist_ok=True)
    
    # Initialize MLflow
    mlflow.set_experiment("equipment_identification")
    
    with mlflow.start_run():
        # Log parameters
        mlflow.log_params(config)
        
        # Initialize augmentation
        aug = VisionAugmentation(image_size=config['image_size'])
        train_transform = aug.get_classification_train_transforms()
        val_transform = aug.get_classification_val_transforms()
        
        # Create datasets
        print("\nLoading datasets...")
        train_dataset = EquipmentDataset(
            config['data_dir'], 
            split='train', 
            transform=train_transform
        )
        val_dataset = EquipmentDataset(
            config['data_dir'], 
            split='val', 
            transform=val_transform
        )
        test_dataset = EquipmentDataset(
            config['data_dir'], 
            split='test', 
            transform=val_transform
        )
        
        # Create dataloaders
        train_loader = DataLoader(
            train_dataset, 
            batch_size=config['batch_size'], 
            shuffle=True,
            num_workers=config['num_workers'],
            pin_memory=True
        )
        val_loader = DataLoader(
            val_dataset, 
            batch_size=config['batch_size'], 
            shuffle=False,
            num_workers=config['num_workers'],
            pin_memory=True
        )
        test_loader = DataLoader(
            test_dataset, 
            batch_size=config['batch_size'], 
            shuffle=False,
            num_workers=config['num_workers'],
            pin_memory=True
        )
        
        # Initialize model
        print("\nInitializing model...")
        num_classes = len(train_dataset.unique_labels)
        model = EquipmentIdentificationModel(
            num_classes=num_classes,
            model_name=config['model_name'],
            pretrained=True
        )
        model = model.to(config['device'])
        
        # Loss function
        if config['use_focal_loss']:
            criterion = FocalLoss(
                alpha=config['focal_alpha'], 
                gamma=config['focal_gamma']
            )
        else:
            criterion = nn.CrossEntropyLoss()
        
        # Optimizer
        optimizer = optim.Adam(
            model.parameters(), 
            lr=config['learning_rate'],
            weight_decay=config['weight_decay']
        )
        
        # Learning rate scheduler
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )
        
        # Training loop
        print("\nStarting training...")
        best_val_acc = 0.0
        
        for epoch in range(config['num_epochs']):
            print(f"\nEpoch {epoch+1}/{config['num_epochs']}")
            
            # Train
            train_loss, train_acc = train_epoch(
                model, train_loader, criterion, optimizer, config['device']
            )
            
            # Validate
            val_loss, val_acc, val_top5_acc = validate(
                model, val_loader, criterion, config['device']
            )
            
            # Update learning rate
            scheduler.step(val_loss)
            
            # Log metrics
            mlflow.log_metrics({
                'train_loss': train_loss,
                'train_acc': train_acc,
                'val_loss': val_loss,
                'val_acc': val_acc,
                'val_top5_acc': val_top5_acc,
            }, step=epoch)
            
            print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
            print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}, Val Top-5 Acc: {val_top5_acc:.4f}")
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                checkpoint_path = Path(config['save_dir']) / 'best_model.pth'
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'val_acc': val_acc,
                    'val_top5_acc': val_top5_acc,
                    'label_mapping': train_dataset.label_to_idx,
                }, checkpoint_path)
                print(f"Saved best model with val_acc: {val_acc:.4f}")
        
        # Test evaluation
        print("\nEvaluating on test set...")
        checkpoint = torch.load(Path(config['save_dir']) / 'best_model.pth')
        model.load_state_dict(checkpoint['model_state_dict'])
        
        test_loss, test_acc, test_top5_acc = validate(
            model, test_loader, criterion, config['device']
        )
        
        print(f"\nTest Results:")
        print(f"  Test Acc: {test_acc:.4f}")
        print(f"  Test Top-5 Acc: {test_top5_acc:.4f}")
        
        # Log final metrics
        mlflow.log_metrics({
            'test_acc': test_acc,
            'test_top5_acc': test_top5_acc,
            'best_val_acc': best_val_acc,
        })
        
        # Log model
        mlflow.pytorch.log_model(model, "model")
        
        # Save label mapping
        label_mapping_path = Path(config['save_dir']) / 'label_mapping.json'
        with open(label_mapping_path, 'w') as f:
            json.dump(train_dataset.label_to_idx, f, indent=2)
        mlflow.log_artifact(str(label_mapping_path))
        
        print(f"\nTraining complete!")
        print(f"Best validation accuracy: {best_val_acc:.4f}")
        print(f"Test accuracy: {test_acc:.4f}")
        print(f"Test top-5 accuracy: {test_top5_acc:.4f}")
        
        # Check if target accuracy is met
        if test_top5_acc >= 0.90:
            print("✓ Target accuracy (>90% top-5) achieved!")
        else:
            print(f"✗ Target accuracy not met. Current: {test_top5_acc:.2%}, Target: 90%")


if __name__ == '__main__':
    main()
