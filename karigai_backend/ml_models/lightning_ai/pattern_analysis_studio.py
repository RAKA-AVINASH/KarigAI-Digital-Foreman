"""
Lightning AI Studio for Pattern Analysis Model Training

Uses Mask R-CNN for traditional pattern/motif detection in artisan products.
"""

import lightning as L
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from PIL import Image
import requests
from io import BytesIO
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt


class PatternDataset(Dataset):
    """Dataset for pattern/motif detection"""
    
    def __init__(self, image_urls, annotations, transform=None):
        self.image_urls = image_urls
        self.annotations = annotations  # List of dicts with boxes, labels, masks
        self.transform = transform
        
    def __len__(self):
        return len(self.image_urls)
    
    def __getitem__(self, idx):
        try:
            response = requests.get(self.image_urls[idx], timeout=5)
            image = Image.open(BytesIO(response.content)).convert('RGB')
        except:
            image = Image.new('RGB', (640, 640), color='white')
        
        # Get annotations
        target = self.annotations[idx]
        
        if self.transform:
            image = self.transform(image)
        
        return image, target


def get_pattern_model(num_classes):
    """Create Mask R-CNN model for pattern detection"""
    
    # Load pretrained Mask R-CNN
    model = maskrcnn_resnet50_fpn(pretrained=True)
    
    # Replace box predictor
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    
    # Replace mask predictor
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    hidden_layer = 256
    model.roi_heads.mask_predictor = MaskRCNNPredictor(
        in_features_mask, hidden_layer, num_classes
    )
    
    return model


def download_pattern_dataset():
    """Download sample pattern/textile images"""
    print("Downloading sample pattern dataset...")
    
    # Sample textile/pattern images
    patterns = [
        'https://images.unsplash.com/photo-1601924994987-69e26d50dc26?w=640',
        'https://images.unsplash.com/photo-1558769132-cb1aea3c8e5e?w=640',
        'https://images.unsplash.com/photo-1590736969955-71cc94901144?w=640',
    ]
    
    image_urls = patterns * 100  # 300 samples
    
    # Create dummy annotations (in real scenario, use proper annotations)
    annotations = []
    for _ in range(len(image_urls)):
        # Dummy bounding boxes and masks
        num_objects = np.random.randint(1, 4)
        boxes = []
        labels = []
        masks = []
        
        for _ in range(num_objects):
            x1, y1 = np.random.randint(0, 500, 2)
            x2, y2 = x1 + np.random.randint(50, 140), y1 + np.random.randint(50, 140)
            boxes.append([x1, y1, x2, y2])
            labels.append(np.random.randint(1, 6))  # 5 motif classes
            
            # Dummy mask
            mask = np.zeros((640, 640), dtype=np.uint8)
            mask[y1:y2, x1:x2] = 1
            masks.append(mask)
        
        annotations.append({
            'boxes': torch.tensor(boxes, dtype=torch.float32),
            'labels': torch.tensor(labels, dtype=torch.int64),
            'masks': torch.tensor(np.array(masks), dtype=torch.uint8)
        })
    
    return image_urls, annotations


def collate_fn(batch):
    """Custom collate function for Mask R-CNN"""
    return tuple(zip(*batch))


def train_model(num_epochs=10, batch_size=2):
    """Train pattern analysis model"""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Download dataset
    train_urls, train_annotations = download_pattern_dataset()
    val_urls = train_urls[:60]
    val_annotations = train_annotations[:60]
    train_urls = train_urls[60:]
    train_annotations = train_annotations[60:]
    
    # Transforms
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])
    
    # Datasets
    train_dataset = PatternDataset(train_urls, train_annotations, transform)
    val_dataset = PatternDataset(val_urls, val_annotations, transform)
    
    # Dataloaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,
                             collate_fn=collate_fn, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                           collate_fn=collate_fn, num_workers=2)
    
    # Model (6 classes: background + 5 motif types)
    model = get_pattern_model(num_classes=6).to(device)
    
    # Optimizer
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)
    
    history = {'train_loss': [], 'val_loss': []}
    best_val_loss = float('inf')
    
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
                
                # Set model to train mode temporarily for loss calculation
                model.train()
                loss_dict = model(images, targets)
                losses = sum(loss for loss in loss_dict.values())
                model.eval()
                
                val_loss += losses.item()
        
        val_loss /= len(val_loader)
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss: {val_loss:.4f}")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_loss': val_loss,
            }, 'best_pattern_model.pth')
            print(f"Saved best model with val_loss: {val_loss:.4f}")
    
    # Plot
    plt.figure(figsize=(8, 6))
    plt.plot(history['train_loss'], label='Train Loss')
    plt.plot(history['val_loss'], label='Val Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.title('Training and Validation Loss')
    plt.savefig('pattern_training_history.png')
    print("\nTraining complete!")
    
    return model, history


class PatternTrainingApp(L.LightningFlow):
    """Lightning App for pattern analysis training"""
    
    def __init__(self):
        super().__init__()
        self.num_epochs = 10
        
    def run(self):
        print("="*60)
        print("Pattern Analysis Model Training on Lightning AI")
        print("="*60)
        print(f"GPU Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print("="*60)
        
        model, history = train_model(num_epochs=self.num_epochs)
        
        print("\n" + "="*60)
        print("Training Summary:")
        print(f"Best Validation Loss: {min(history['val_loss']):.4f}")
        print(f"Target: >85% motif detection mAP")
        print("="*60)


if __name__ == "__main__":
    app = L.LightningApp(PatternTrainingApp())
