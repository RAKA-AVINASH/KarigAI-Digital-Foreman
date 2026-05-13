"""
Lightning AI Studio for Equipment Identification Model Training

This script trains the equipment identification model on Lightning AI with T4 GPU.
"""

import lightning as L
from lightning.app.components import TracerPythonScript
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
import requests
from io import BytesIO
import os
from pathlib import Path
import json
from tqdm import tqdm
import matplotlib.pyplot as plt


class EquipmentDataset(Dataset):
    """Dataset for equipment identification using ImageNet subset"""
    
    def __init__(self, image_urls, labels, transform=None):
        self.image_urls = image_urls
        self.labels = labels
        self.transform = transform
        self.label_to_idx = {label: idx for idx, label in enumerate(set(labels))}
        
    def __len__(self):
        return len(self.image_urls)
    
    def __getitem__(self, idx):
        # Download image
        try:
            response = requests.get(self.image_urls[idx], timeout=5)
            image = Image.open(BytesIO(response.content)).convert('RGB')
        except:
            # Return black image if download fails
            image = Image.new('RGB', (224, 224), color='black')
        
        if self.transform:
            image = self.transform(image)
        
        label_idx = self.label_to_idx[self.labels[idx]]
        return image, label_idx


class EquipmentModel(nn.Module):
    """Equipment identification model with ResNet50 backbone"""
    
    def __init__(self, num_classes):
        super().__init__()
        self.backbone = models.resnet50(pretrained=True)
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()
        
        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(num_features, num_features // 4),
            nn.ReLU(),
            nn.Linear(num_features // 4, 1),
            nn.Sigmoid()
        )
        
        # Classifier
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        features = self.backbone(x)
        attention_weights = self.attention(features)
        attended_features = features * attention_weights
        output = self.classifier(attended_features)
        return output


def download_sample_dataset():
    """Download sample equipment images from ImageNet"""
    print("Downloading sample dataset...")
    
    # Sample ImageNet URLs for appliances
    # In production, use proper ImageNet API or dataset
    equipment_categories = {
        'refrigerator': [
            'https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?w=400',
            'https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=400',
        ],
        'washing_machine': [
            'https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?w=400',
            'https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?w=400',
        ],
        'air_conditioner': [
            'https://images.unsplash.com/photo-1631545806609-4b0e8b6c2f8e?w=400',
            'https://images.unsplash.com/photo-1635274831481-c7e2f8e1e1e1?w=400',
        ],
    }
    
    image_urls = []
    labels = []
    
    for category, urls in equipment_categories.items():
        for url in urls:
            image_urls.append(url)
            labels.append(category)
    
    # Duplicate for more training samples
    image_urls = image_urls * 50  # 300 samples
    labels = labels * 50
    
    return image_urls, labels


def train_model(num_epochs=10, batch_size=16):
    """Train equipment identification model"""
    
    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Download dataset
    train_urls, train_labels = download_sample_dataset()
    val_urls, val_labels = train_urls[:60], train_labels[:60]  # 20% for validation
    train_urls, train_labels = train_urls[60:], train_labels[60:]
    
    # Data transforms
    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Create datasets
    train_dataset = EquipmentDataset(train_urls, train_labels, train_transform)
    val_dataset = EquipmentDataset(val_urls, val_labels, val_transform)
    
    # Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=2)
    
    # Initialize model
    num_classes = len(set(train_labels))
    model = EquipmentModel(num_classes).to(device)
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
    
    # Training history
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}
    
    # Training loop
    best_val_acc = 0.0
    
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for images, labels in tqdm(train_loader, desc='Training'):
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
        
        train_loss /= len(train_loader)
        train_acc = train_correct / train_total
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for images, labels in tqdm(val_loader, desc='Validation'):
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_loss /= len(val_loader)
        val_acc = val_correct / val_total
        
        # Update scheduler
        scheduler.step(val_loss)
        
        # Save history
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
            }, 'best_equipment_model.pth')
            print(f"Saved best model with val_acc: {val_acc:.4f}")
    
    # Plot training history
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history['train_loss'], label='Train Loss')
    plt.plot(history['val_loss'], label='Val Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.title('Training and Validation Loss')
    
    plt.subplot(1, 2, 2)
    plt.plot(history['train_acc'], label='Train Acc')
    plt.plot(history['val_acc'], label='Val Acc')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.title('Training and Validation Accuracy')
    
    plt.tight_layout()
    plt.savefig('training_history.png')
    print("\nTraining complete! Saved training_history.png")
    
    return model, history


class EquipmentTrainingApp(L.LightningFlow):
    """Lightning App for equipment identification training"""
    
    def __init__(self):
        super().__init__()
        self.num_epochs = 10  # Start with 10 epochs for validation
        
    def run(self):
        print("="*60)
        print("Equipment Identification Model Training on Lightning AI")
        print("="*60)
        print(f"GPU Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print("="*60)
        
        # Train model
        model, history = train_model(num_epochs=self.num_epochs)
        
        print("\n" + "="*60)
        print("Training Summary:")
        print(f"Best Validation Accuracy: {max(history['val_acc']):.4f}")
        print(f"Final Train Accuracy: {history['train_acc'][-1]:.4f}")
        print(f"Final Val Accuracy: {history['val_acc'][-1]:.4f}")
        print("="*60)
        
        print("\nModel saved as: best_equipment_model.pth")
        print("Training history saved as: training_history.png")
        print("\nTo download results, use Lightning AI dashboard")


if __name__ == "__main__":
    # Run as Lightning App
    app = L.LightningApp(EquipmentTrainingApp())
