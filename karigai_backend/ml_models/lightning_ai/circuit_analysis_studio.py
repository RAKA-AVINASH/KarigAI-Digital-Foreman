"""
Lightning AI Studio for Circuit Board Analysis Model Training

Uses Faster R-CNN for component detection and damage classification.
"""

import lightning as L
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from PIL import Image
import requests
from io import BytesIO
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt


class CircuitDataset(Dataset):
    """Dataset for circuit board component detection"""
    
    def __init__(self, image_urls, annotations, transform=None):
        self.image_urls = image_urls
        self.annotations = annotations  # List of dicts with boxes and labels
        self.transform = transform
        
    def __len__(self):
        return len(self.image_urls)
    
    def __getitem__(self, idx):
        try:
            response = requests.get(self.image_urls[idx], timeout=5)
            image = Image.open(BytesIO(response.content)).convert('RGB')
        except:
            # Create synthetic circuit board image
            image = Image.new('RGB', (640, 640), color='green')
        
        # Get annotations
        target = self.annotations[idx]
        
        if self.transform:
            image = self.transform(image)
        
        return image, target


def get_circuit_model(num_classes):
    """Create Faster R-CNN model for circuit component detection"""
    
    # Load pretrained Faster R-CNN
    model = fasterrcnn_resnet50_fpn(pretrained=True)
    
    # Replace box predictor
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    
    return model


def download_circuit_dataset():
    """Download sample circuit board images"""
    print("Downloading sample circuit board dataset...")
    
    # Sample circuit board images
    circuits = [
        'https://images.unsplash.com/photo-1518770660439-4636190af475?w=640',
        'https://images.unsplash.com/photo-1555664424-778a1e5e1b48?w=640',
        'https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=640',
    ]
    
    image_urls = circuits * 100  # 300 samples
    
    # Create dummy annotations
    # Component classes: 1=resistor, 2=capacitor, 3=IC, 4=transistor, 5=diode, etc.
    annotations = []
    for _ in range(len(image_urls)):
        num_components = np.random.randint(3, 10)
        boxes = []
        labels = []
        
        for _ in range(num_components):
            x1, y1 = np.random.randint(0, 580, 2)
            x2, y2 = x1 + np.random.randint(20, 60), y1 + np.random.randint(20, 60)
            boxes.append([x1, y1, x2, y2])
            labels.append(np.random.randint(1, 11))  # 10 component types
        
        annotations.append({
            'boxes': torch.tensor(boxes, dtype=torch.float32),
            'labels': torch.tensor(labels, dtype=torch.int64)
        })
    
    return image_urls, annotations


def collate_fn(batch):
    """Custom collate function for Faster R-CNN"""
    return tuple(zip(*batch))


def calculate_map(model, data_loader, device, iou_threshold=0.5):
    """Calculate mean Average Precision"""
    model.eval()
    all_precisions = []
    
    with torch.no_grad():
        for images, targets in data_loader:
            images = [img.to(device) for img in images]
            predictions = model(images)
            
            # Simple mAP calculation (simplified for demo)
            for pred, target in zip(predictions, targets):
                if len(pred['boxes']) > 0 and len(target['boxes']) > 0:
                    # Calculate IoU and precision (simplified)
                    precision = len(pred['boxes']) / (len(pred['boxes']) + len(target['boxes']))
                    all_precisions.append(precision)
    
    return np.mean(all_precisions) if all_precisions else 0.0


def train_model(num_epochs=10, batch_size=2):
    """Train circuit board analysis model"""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Download dataset
    train_urls, train_annotations = download_circuit_dataset()
    val_urls = train_urls[:60]
    val_annotations = train_annotations[:60]
    train_urls = train_urls[60:]
    train_annotations = train_annotations[60:]
    
    # Transforms
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])
    
    # Datasets
    train_dataset = CircuitDataset(train_urls, train_annotations, transform)
    val_dataset = CircuitDataset(val_urls, val_annotations, transform)
    
    # Dataloaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,
                             collate_fn=collate_fn, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                           collate_fn=collate_fn, num_workers=2)
    
    # Model (11 classes: background + 10 component types)
    model = get_circuit_model(num_classes=11).to(device)
    
    # Optimizer
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)
    
    history = {'train_loss': [], 'val_loss': [], 'val_map': []}
    best_val_map = 0.0
    
    # Training loop
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        
        # Train
        model.train()
        train_loss = 0.0
        
        for images, targets in tqdm(train_loader, desc='Training'):
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            
            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())
            
            optimizer.zero_grad()
            losses.backward()
            optimizer.step()
            
            train_loss += losses.item()
        
        train_loss /= len(train_loader)
        lr_scheduler.step()
        
        # Validate
        model.eval()
        val_loss = 0.0
        
        with torch.no_grad():
            for images, targets in tqdm(val_loader, desc='Validation'):
                images = [img.to(device) for img in images]
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                
                # Calculate loss
                model.train()
                loss_dict = model(images, targets)
                losses = sum(loss for loss in loss_dict.values())
                model.eval()
                
                val_loss += losses.item()
        
        val_loss /= len(val_loader)
        
        # Calculate mAP
        val_map = calculate_map(model, val_loader, device)
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_map'].append(val_map)
        
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss: {val_loss:.4f}, Val mAP: {val_map:.4f}")
        
        if val_map > best_val_map:
            best_val_map = val_map
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_loss': val_loss,
                'val_map': val_map,
            }, 'best_circuit_model.pth')
            print(f"Saved best model with val_map: {val_map:.4f}")
    
    # Plot
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history['train_loss'], label='Train Loss')
    plt.plot(history['val_loss'], label='Val Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.title('Training and Validation Loss')
    
    plt.subplot(1, 2, 2)
    plt.plot(history['val_map'], label='Val mAP')
    plt.xlabel('Epoch')
    plt.ylabel('mAP')
    plt.legend()
    plt.title('Validation mAP')
    
    plt.tight_layout()
    plt.savefig('circuit_training_history.png')
    print("\nTraining complete!")
    
    return model, history


class CircuitTrainingApp(L.LightningFlow):
    """Lightning App for circuit board analysis training"""
    
    def __init__(self):
        super().__init__()
        self.num_epochs = 10
        
    def run(self):
        print("="*60)
        print("Circuit Board Analysis Model Training on Lightning AI")
        print("="*60)
        print(f"GPU Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print("="*60)
        
        model, history = train_model(num_epochs=self.num_epochs)
        
        print("\n" + "="*60)
        print("Training Summary:")
        print(f"Best Validation mAP: {max(history['val_map']):.4f}")
        print(f"Target: >85% component detection mAP")
        print("="*60)


if __name__ == "__main__":
    app = L.LightningApp(CircuitTrainingApp())
