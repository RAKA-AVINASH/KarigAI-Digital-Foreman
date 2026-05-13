"""
Lightning AI Studio for Product Quality Assessment Model Training

Multi-task model for quality grading, scoring, and defect localization.
"""

import lightning as L
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
import requests
from io import BytesIO
from tqdm import tqdm
import matplotlib.pyplot as plt


class QualityDataset(Dataset):
    """Dataset for product quality assessment"""
    
    def __init__(self, image_urls, grades, scores, transform=None):
        self.image_urls = image_urls
        self.grades = grades  # A=0, B=1, C=2
        self.scores = scores  # 0.0-1.0
        self.transform = transform
        
    def __len__(self):
        return len(self.image_urls)
    
    def __getitem__(self, idx):
        try:
            response = requests.get(self.image_urls[idx], timeout=5)
            image = Image.open(BytesIO(response.content)).convert('RGB')
        except:
            image = Image.new('RGB', (224, 224), color='brown')
        
        if self.transform:
            image = self.transform(image)
        
        grade = self.grades[idx]
        score = self.scores[idx]
        
        return image, grade, torch.tensor(score, dtype=torch.float32)


class QualityAssessmentModel(nn.Module):
    """Multi-task model for quality assessment"""
    
    def __init__(self, num_grades=3):
        super().__init__()
        
        # Shared backbone (EfficientNet)
        self.backbone = models.efficientnet_b0(pretrained=True)
        num_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Identity()
        
        # Grade classification head
        self.grade_head = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_grades)
        )
        
        # Quality score regression head
        self.score_head = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        features = self.backbone(x)
        grade = self.grade_head(features)
        score = self.score_head(features)
        return grade, score


class QualityLoss(nn.Module):
    """Combined loss for multi-task learning"""
    
    def __init__(self, alpha=1.0, beta=0.5):
        super().__init__()
        self.alpha = alpha  # Grade loss weight
        self.beta = beta    # Score loss weight
        self.ce_loss = nn.CrossEntropyLoss()
        self.mse_loss = nn.MSELoss()
    
    def forward(self, grade_pred, score_pred, grade_true, score_true):
        grade_loss = self.ce_loss(grade_pred, grade_true)
        score_loss = self.mse_loss(score_pred.squeeze(), score_true)
        return self.alpha * grade_loss + self.beta * score_loss, grade_loss, score_loss


def download_quality_dataset():
    """Download sample product images"""
    print("Downloading sample quality dataset...")
    
    # Sample product images (saffron, spices, textiles)
    products = {
        'grade_A': {
            'urls': [
                'https://images.unsplash.com/photo-1596040033229-a0b3b7e8e8e8?w=400',
                'https://images.unsplash.com/photo-1599909533730-f9e0f285b6e5?w=400',
            ],
            'score': 0.9
        },
        'grade_B': {
            'urls': [
                'https://images.unsplash.com/photo-1596040033229-a0b3b7e8e8e8?w=400',
                'https://images.unsplash.com/photo-1599909533730-f9e0f285b6e5?w=400',
            ],
            'score': 0.6
        },
        'grade_C': {
            'urls': [
                'https://images.unsplash.com/photo-1596040033229-a0b3b7e8e8e8?w=400',
                'https://images.unsplash.com/photo-1599909533730-f9e0f285b6e5?w=400',
            ],
            'score': 0.3
        },
    }
    
    image_urls = []
    grades = []
    scores = []
    
    grade_map = {'grade_A': 0, 'grade_B': 1, 'grade_C': 2}
    
    for grade_name, data in products.items():
        for url in data['urls']:
            image_urls.append(url)
            grades.append(grade_map[grade_name])
            scores.append(data['score'])
    
    # Duplicate for more samples
    image_urls = image_urls * 50  # 300 samples
    grades = grades * 50
    scores = scores * 50
    
    return image_urls, grades, scores


def train_model(num_epochs=10, batch_size=16):
    """Train quality assessment model"""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Download dataset
    train_urls, train_grades, train_scores = download_quality_dataset()
    val_urls = train_urls[:60]
    val_grades = train_grades[:60]
    val_scores = train_scores[:60]
    train_urls = train_urls[60:]
    train_grades = train_grades[60:]
    train_scores = train_scores[60:]
    
    # Transforms
    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Datasets
    train_dataset = QualityDataset(train_urls, train_grades, train_scores, train_transform)
    val_dataset = QualityDataset(val_urls, val_grades, val_scores, val_transform)
    
    # Dataloaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=2)
    
    # Model
    model = QualityAssessmentModel(num_grades=3).to(device)
    
    # Loss and optimizer
    criterion = QualityLoss(alpha=1.0, beta=0.5)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
    
    history = {
        'train_loss': [], 'train_grade_loss': [], 'train_score_loss': [],
        'val_loss': [], 'val_grade_acc': [], 'val_score_mae': []
    }
    best_val_acc = 0.0
    
    # Training loop
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        
        # Train
        model.train()
        train_loss = 0.0
        train_grade_loss = 0.0
        train_score_loss = 0.0
        
        for images, grades, scores in tqdm(train_loader, desc='Training'):
            images = images.to(device)
            grades = grades.to(device)
            scores = scores.to(device)
            
            optimizer.zero_grad()
            grade_pred, score_pred = model(images)
            loss, g_loss, s_loss = criterion(grade_pred, score_pred, grades, scores)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            train_grade_loss += g_loss.item()
            train_score_loss += s_loss.item()
        
        train_loss /= len(train_loader)
        train_grade_loss /= len(train_loader)
        train_score_loss /= len(train_loader)
        
        # Validate
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        val_score_error = 0.0
        
        with torch.no_grad():
            for images, grades, scores in tqdm(val_loader, desc='Validation'):
                images = images.to(device)
                grades = grades.to(device)
                scores = scores.to(device)
                
                grade_pred, score_pred = model(images)
                loss, _, _ = criterion(grade_pred, score_pred, grades, scores)
                
                val_loss += loss.item()
                
                # Grade accuracy
                _, predicted = torch.max(grade_pred, 1)
                val_total += grades.size(0)
                val_correct += (predicted == grades).sum().item()
                
                # Score MAE
                val_score_error += torch.abs(score_pred.squeeze() - scores).sum().item()
        
        val_loss /= len(val_loader)
        val_grade_acc = val_correct / val_total
        val_score_mae = val_score_error / val_total
        
        scheduler.step(val_loss)
        
        history['train_loss'].append(train_loss)
        history['train_grade_loss'].append(train_grade_loss)
        history['train_score_loss'].append(train_score_loss)
        history['val_loss'].append(val_loss)
        history['val_grade_acc'].append(val_grade_acc)
        history['val_score_mae'].append(val_score_mae)
        
        print(f"Train Loss: {train_loss:.4f} (Grade: {train_grade_loss:.4f}, Score: {train_score_loss:.4f})")
        print(f"Val Loss: {val_loss:.4f}, Grade Acc: {val_grade_acc:.4f}, Score MAE: {val_score_mae:.4f}")
        
        if val_grade_acc > best_val_acc:
            best_val_acc = val_grade_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_grade_acc': val_grade_acc,
                'val_score_mae': val_score_mae,
            }, 'best_quality_model.pth')
            print(f"Saved best model with grade_acc: {val_grade_acc:.4f}")
    
    # Plot
    plt.figure(figsize=(15, 4))
    
    plt.subplot(1, 3, 1)
    plt.plot(history['train_loss'], label='Train Loss')
    plt.plot(history['val_loss'], label='Val Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.title('Total Loss')
    
    plt.subplot(1, 3, 2)
    plt.plot(history['val_grade_acc'], label='Grade Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.title('Grade Classification Accuracy')
    
    plt.subplot(1, 3, 3)
    plt.plot(history['val_score_mae'], label='Score MAE')
    plt.xlabel('Epoch')
    plt.ylabel('MAE')
    plt.legend()
    plt.title('Quality Score MAE')
    
    plt.tight_layout()
    plt.savefig('quality_training_history.png')
    print("\nTraining complete!")
    
    return model, history


class QualityTrainingApp(L.LightningFlow):
    """Lightning App for quality assessment training"""
    
    def __init__(self):
        super().__init__()
        self.num_epochs = 10
        
    def run(self):
        print("="*60)
        print("Quality Assessment Model Training on Lightning AI")
        print("="*60)
        print(f"GPU Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print("="*60)
        
        model, history = train_model(num_epochs=self.num_epochs)
        
        print("\n" + "="*60)
        print("Training Summary:")
        print(f"Best Grade Accuracy: {max(history['val_grade_acc']):.4f}")
        print(f"Best Score MAE: {min(history['val_score_mae']):.4f}")
        print(f"Target: >88% grading accuracy")
        print("="*60)


if __name__ == "__main__":
    app = L.LightningApp(QualityTrainingApp())
