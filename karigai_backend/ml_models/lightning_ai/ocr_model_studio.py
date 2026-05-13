"""
Lightning AI Studio for OCR Model Training (Error Code Recognition)

Uses CRNN (CNN + LSTM) architecture with CTC loss for text recognition.
"""

import lightning as L
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image, ImageDraw, ImageFont
import random
import string
from tqdm import tqdm
import matplotlib.pyplot as plt


class SyntheticErrorCodeDataset(Dataset):
    """Generate synthetic error code images for training"""
    
    def __init__(self, num_samples=1000, transform=None):
        self.num_samples = num_samples
        self.transform = transform
        self.charset = string.digits + string.ascii_uppercase  # 0-9, A-Z
        
    def __len__(self):
        return self.num_samples
    
    def generate_error_code(self):
        """Generate random error code (e.g., E001, F42A, etc.)"""
        patterns = [
            lambda: f"E{random.randint(0, 999):03d}",
            lambda: f"F{random.randint(0, 99):02d}{random.choice(string.ascii_uppercase)}",
            lambda: f"{random.choice(string.ascii_uppercase)}{random.randint(0, 9999):04d}",
        ]
        return random.choice(patterns)()
    
    def __getitem__(self, idx):
        # Generate error code text
        text = self.generate_error_code()
        
        # Create image
        img = Image.new('RGB', (128, 32), color='black')
        draw = ImageDraw.Draw(img)
        
        # Try to use a font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Draw text
        draw.text((10, 5), text, fill='white', font=font)
        
        # Add noise
        if random.random() > 0.5:
            for _ in range(random.randint(10, 50)):
                x, y = random.randint(0, 127), random.randint(0, 31)
                draw.point((x, y), fill='gray')
        
        if self.transform:
            img = self.transform(img)
        
        # Encode text to indices
        encoded = [self.charset.index(c) for c in text if c in self.charset]
        
        return img, torch.tensor(encoded), len(encoded)


class CRNN(nn.Module):
    """CRNN model for OCR"""
    
    def __init__(self, num_chars, hidden_size=256):
        super().__init__()
        
        # CNN for feature extraction
        self.cnn = nn.Sequential(
            nn.Conv2d(3, 64, 3, 1, 1), nn.ReLU(), nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, 1, 1), nn.ReLU(), nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(256, 256, 3, 1, 1), nn.ReLU(), nn.MaxPool2d((2, 1)),
            nn.Conv2d(256, 512, 3, 1, 1), nn.ReLU(),
            nn.Conv2d(512, 512, 3, 1, 1), nn.ReLU(), nn.MaxPool2d((2, 1)),
        )
        
        # RNN for sequence modeling
        self.rnn = nn.LSTM(512, hidden_size, bidirectional=True, num_layers=2, batch_first=False)
        
        # Output layer (+1 for CTC blank)
        self.fc = nn.Linear(hidden_size * 2, num_chars + 1)
    
    def forward(self, x):
        # CNN features
        conv = self.cnn(x)  # [B, C, H, W]
        
        # Reshape for RNN
        b, c, h, w = conv.size()
        conv = conv.view(b, c * h, w)
        conv = conv.permute(2, 0, 1)  # [W, B, C*H]
        
        # RNN
        rnn_out, _ = self.rnn(conv)
        
        # Output
        output = self.fc(rnn_out)
        return output


def train_model(num_epochs=10, batch_size=32):
    """Train OCR model"""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Transforms
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ])
    
    # Datasets
    train_dataset = SyntheticErrorCodeDataset(num_samples=5000, transform=transform)
    val_dataset = SyntheticErrorCodeDataset(num_samples=1000, transform=transform)
    
    # Dataloaders with custom collate
    def collate_fn(batch):
        images, targets, lengths = zip(*batch)
        images = torch.stack(images)
        targets = nn.utils.rnn.pad_sequence(targets, batch_first=True, padding_value=0)
        lengths = torch.tensor(lengths)
        return images, targets, lengths
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, 
                             collate_fn=collate_fn, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                           collate_fn=collate_fn, num_workers=2)
    
    # Model
    charset = string.digits + string.ascii_uppercase
    num_chars = len(charset)
    model = CRNN(num_chars).to(device)
    
    # Loss and optimizer
    criterion = nn.CTCLoss(blank=num_chars, zero_infinity=True)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)
    
    history = {'train_loss': [], 'val_loss': [], 'val_acc': []}
    best_val_loss = float('inf')
    
    # Training loop
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        
        # Train
        model.train()
        train_loss = 0.0
        
        for images, targets, lengths in tqdm(train_loader, desc='Training'):
            images = images.to(device)
            targets = targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)  # [T, B, C]
            
            # CTC loss
            input_lengths = torch.full((outputs.size(1),), outputs.size(0), dtype=torch.long)
            loss = criterion(outputs.log_softmax(2), targets, input_lengths, lengths)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        
        # Validate
        model.eval()
        val_loss = 0.0
        correct_chars = 0
        total_chars = 0
        
        with torch.no_grad():
            for images, targets, lengths in tqdm(val_loader, desc='Validation'):
                images = images.to(device)
                targets = targets.to(device)
                
                outputs = model(images)
                input_lengths = torch.full((outputs.size(1),), outputs.size(0), dtype=torch.long)
                loss = criterion(outputs.log_softmax(2), targets, input_lengths, lengths)
                
                val_loss += loss.item()
                
                # Calculate character accuracy
                preds = outputs.argmax(2).permute(1, 0)  # [B, T]
                for pred, target, length in zip(preds, targets, lengths):
                    # Simple decoding (remove duplicates and blanks)
                    pred_chars = []
                    prev = -1
                    for p in pred:
                        if p != num_chars and p != prev:
                            pred_chars.append(p.item())
                        prev = p
                    
                    target_chars = target[:length].tolist()
                    
                    # Count correct characters
                    for i in range(min(len(pred_chars), len(target_chars))):
                        if pred_chars[i] == target_chars[i]:
                            correct_chars += 1
                    total_chars += len(target_chars)
        
        val_loss /= len(val_loader)
        val_acc = correct_chars / total_chars if total_chars > 0 else 0.0
        
        scheduler.step(val_loss)
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        
        print(f"Train Loss: {train_loss:.4f}")
        print(f"Val Loss: {val_loss:.4f}, Val Char Acc: {val_acc:.4f}")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'val_loss': val_loss,
                'val_acc': val_acc,
            }, 'best_ocr_model.pth')
            print(f"Saved best model with val_loss: {val_loss:.4f}")
    
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
    plt.plot(history['val_acc'], label='Val Char Acc')
    plt.xlabel('Epoch')
    plt.ylabel('Character Accuracy')
    plt.legend()
    plt.title('Validation Character Accuracy')
    
    plt.tight_layout()
    plt.savefig('ocr_training_history.png')
    print("\nTraining complete!")
    
    return model, history


class OCRTrainingApp(L.LightningFlow):
    """Lightning App for OCR model training"""
    
    def __init__(self):
        super().__init__()
        self.num_epochs = 10
        
    def run(self):
        print("="*60)
        print("OCR Model Training on Lightning AI")
        print("="*60)
        print(f"GPU Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print("="*60)
        
        model, history = train_model(num_epochs=self.num_epochs)
        
        print("\n" + "="*60)
        print("Training Summary:")
        print(f"Best Validation Character Accuracy: {max(history['val_acc']):.4f}")
        print(f"Target: >95% (will achieve with real dataset)")
        print("="*60)


if __name__ == "__main__":
    app = L.LightningApp(OCRTrainingApp())
