# Equipment Identification Model Training Guide

## Overview

This guide covers training a deep learning model for equipment identification with multi-label classification for brand, model, and equipment type. The model uses ResNet50 or EfficientNet architecture with an attention mechanism for error code region detection.

## Model Architecture

### ResNet50 (Recommended)
- **Parameters:** 25.6M
- **Input Size:** 224x224x3
- **Features:** Pre-trained on ImageNet, fine-tuned for equipment
- **Attention Mechanism:** For error code region detection
- **Output:** Multi-class classification (equipment categories)

### EfficientNet-B0 (Alternative)
- **Parameters:** 5.3M (lighter, faster)
- **Input Size:** 224x224x3
- **Features:** Efficient architecture with compound scaling
- **Better for:** Mobile deployment, resource-constrained environments

## Dataset Requirements

### Minimum Dataset Size
- **Training:** 8,000+ images (80%)
- **Validation:** 1,000+ images (10%)
- **Test:** 1,000+ images (10%)
- **Total:** 10,000+ images

### Equipment Categories

```python
equipment_categories = {
    'refrigerators': ['Samsung', 'LG', 'Whirlpool', 'Godrej', 'Haier'],
    'washing_machines': ['IFB', 'Bosch', 'Samsung', 'LG', 'Whirlpool'],
    'air_conditioners': ['Voltas', 'Blue Star', 'Daikin', 'LG', 'Samsung'],
    'water_heaters': ['Bajaj', 'Racold', 'AO Smith', 'Havells'],
    'pumps': ['Crompton', 'Kirloskar', 'Shakti', 'Texmo'],
    'generators': ['Honda', 'Yamaha', 'Kirloskar', 'Greaves'],
    'power_tools': ['Bosch', 'Makita', 'DeWalt', 'Black+Decker'],
    'hand_tools': ['Stanley', 'Taparia', 'Jhalani', 'Venus']
}
```

### Directory Structure

```
ml_models/data/vision/equipment/
├── processed/
│   ├── train/
│   │   ├── refrigerator_samsung/
│   │   ├── refrigerator_lg/
│   │   ├── washing_machine_ifb/
│   │   └── ...
│   ├── val/
│   │   └── (same structure)
│   └── test/
│       └── (same structure)
└── annotations/
    └── equipment_labels.json
```

## Training Configuration

### Hyperparameters

```python
config = {
    'model_name': 'resnet50',  # or 'efficientnet_b0'
    'image_size': 224,
    'batch_size': 32,
    'num_epochs': 50,
    'learning_rate': 0.001,
    'weight_decay': 1e-4,
    'use_focal_loss': True,  # For class imbalance
    'focal_alpha': 1.0,
    'focal_gamma': 2.0,
}
```

### Loss Functions

**Cross-Entropy Loss (Balanced Classes):**
```python
criterion = nn.CrossEntropyLoss()
```

**Focal Loss (Imbalanced Classes):**
```python
class FocalLoss(nn.Module):
    def __init__(self, alpha=1, gamma=2):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
    
    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        return focal_loss.mean()
```

## Training Process

### Step 1: Prepare Dataset

```bash
cd karigai_backend/ml_models

# Organize dataset
python -c "
from utils.vision_dataset_preparation import VisionDatasetManager
manager = VisionDatasetManager()
manager.organize_dataset('equipment', 'path/to/raw/equipment/images')
manager.validate_dataset('equipment')
manager.generate_manifest('equipment')
"
```

### Step 2: Start Training

```bash
# Basic training
python training/train_equipment_identification.py

# With custom config (edit script first)
python training/train_equipment_identification.py --config custom_config.yaml
```

### Step 3: Monitor Training

```bash
# Start MLflow UI
mlflow ui

# Open browser to http://localhost:5000
# View training metrics, compare runs, analyze results
```

### Step 4: Evaluate Model

The script automatically evaluates on the test set after training and reports:
- **Test Accuracy:** Overall classification accuracy
- **Top-5 Accuracy:** Target >90%
- **Per-Class Metrics:** Precision, recall, F1-score

## Training Strategies

### Transfer Learning (Recommended)

**Freeze Encoder (Fast Training):**
```python
# Freeze backbone layers
for param in model.backbone.parameters():
    param.requires_grad = False

# Only train classifier
optimizer = optim.Adam(model.classifier.parameters(), lr=0.001)
```

**Full Fine-Tuning (Better Performance):**
```python
# Train all layers
optimizer = optim.Adam(model.parameters(), lr=0.001)
```

**Progressive Unfreezing:**
```python
# Epoch 1-10: Train classifier only
# Epoch 11-30: Unfreeze last 2 blocks
# Epoch 31-50: Train all layers
```

### Data Augmentation

The training script uses comprehensive augmentation:
- Random rotation (±45°)
- Horizontal/vertical flips
- Scale and shift
- Color jittering
- Blur and noise
- Optical distortion

### Handling Class Imbalance

**Focal Loss:**
- Automatically focuses on hard examples
- Reduces weight of easy examples
- Gamma=2 (default), higher = more focus on hard examples

**Class Weights:**
```python
# Calculate class weights
class_counts = [count for count in class_distribution.values()]
class_weights = 1.0 / torch.tensor(class_counts, dtype=torch.float)
criterion = nn.CrossEntropyLoss(weight=class_weights)
```

**Oversampling:**
```python
from torch.utils.data import WeightedRandomSampler

# Create sampler
sampler = WeightedRandomSampler(
    weights=sample_weights,
    num_samples=len(dataset),
    replacement=True
)

# Use in dataloader
train_loader = DataLoader(dataset, sampler=sampler, ...)
```

## Attention Mechanism

The model includes an attention mechanism for error code region detection:

```python
class AttentionModule(nn.Module):
    def __init__(self, in_features):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(in_features, in_features // 4),
            nn.ReLU(),
            nn.Linear(in_features // 4, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        attention_weights = self.attention(x)
        return x * attention_weights, attention_weights
```

**Benefits:**
- Focuses on important regions (error codes, brand logos)
- Improves classification accuracy
- Provides interpretability (visualize attention)

## Performance Targets

### Accuracy Targets
- **Top-1 Accuracy:** >85%
- **Top-5 Accuracy:** >90% (Required)
- **Per-Class Accuracy:** >80% for major categories

### Inference Speed
- **GPU (RTX 3060):** <50ms per image
- **CPU (Intel i7):** <200ms per image
- **Mobile (Snapdragon 888):** <500ms per image

### Model Size
- **ResNet50:** ~100 MB
- **EfficientNet-B0:** ~20 MB
- **Quantized (INT8):** ~25 MB (ResNet50)

## Evaluation Metrics

### Classification Metrics

```python
from sklearn.metrics import classification_report, confusion_matrix

# Generate classification report
report = classification_report(y_true, y_pred, target_names=class_names)
print(report)

# Confusion matrix
cm = confusion_matrix(y_true, y_pred)
```

### Top-K Accuracy

```python
from sklearn.metrics import top_k_accuracy_score

# Calculate top-5 accuracy
top5_acc = top_k_accuracy_score(y_true, y_probs, k=5)
print(f"Top-5 Accuracy: {top5_acc:.4f}")
```

## Model Export

### PyTorch Model

```python
# Save model
torch.save({
    'model_state_dict': model.state_dict(),
    'label_mapping': label_to_idx,
    'config': config,
}, 'equipment_model.pth')

# Load model
checkpoint = torch.load('equipment_model.pth')
model.load_state_dict(checkpoint['model_state_dict'])
```

### ONNX Export

```python
# Export to ONNX
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(
    model,
    dummy_input,
    'equipment_model.onnx',
    input_names=['input'],
    output_names=['output'],
    dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
)
```

### TensorRT Optimization

```bash
# Convert ONNX to TensorRT
trtexec --onnx=equipment_model.onnx \
        --saveEngine=equipment_model.trt \
        --fp16  # Use FP16 precision
```

## Troubleshooting

### Low Accuracy

**Possible Causes:**
1. Insufficient training data
2. Class imbalance
3. Poor data quality
4. Overfitting

**Solutions:**
- Collect more diverse data
- Use focal loss or class weights
- Improve data quality and labeling
- Add regularization (dropout, weight decay)
- Use data augmentation

### Overfitting

**Symptoms:**
- High training accuracy, low validation accuracy
- Large gap between train and val loss

**Solutions:**
```python
# Increase dropout
model.classifier = nn.Sequential(
    nn.Dropout(0.7),  # Increase from 0.5
    nn.Linear(num_features, 512),
    nn.ReLU(),
    nn.Dropout(0.5),  # Increase from 0.3
    nn.Linear(512, num_classes)
)

# Add weight decay
optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-3)

# Early stopping
if val_loss > best_val_loss for 10 epochs:
    break
```

### Slow Training

**Solutions:**
- Reduce batch size if GPU memory is full
- Use mixed precision training
- Increase num_workers for data loading
- Use smaller model (EfficientNet-B0)

```python
# Mixed precision training
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

for images, labels in dataloader:
    with autocast():
        outputs = model(images)
        loss = criterion(outputs, labels)
    
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
```

## Advanced Techniques

### Multi-Label Classification

For equipment with multiple attributes (brand + model + type):

```python
class MultiLabelModel(nn.Module):
    def __init__(self, num_brands, num_models, num_types):
        super().__init__()
        self.backbone = models.resnet50(pretrained=True)
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()
        
        # Separate heads for each attribute
        self.brand_head = nn.Linear(num_features, num_brands)
        self.model_head = nn.Linear(num_features, num_models)
        self.type_head = nn.Linear(num_features, num_types)
    
    def forward(self, x):
        features = self.backbone(x)
        brand = self.brand_head(features)
        model = self.model_head(features)
        type = self.type_head(features)
        return brand, model, type
```

### Ensemble Models

Combine multiple models for better accuracy:

```python
class EnsembleModel(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)
    
    def forward(self, x):
        outputs = [model(x) for model in self.models]
        # Average predictions
        return torch.mean(torch.stack(outputs), dim=0)
```

## Next Steps

After training the equipment identification model:

1. **Evaluate on test set** - Ensure >90% top-5 accuracy
2. **Export to ONNX** - For deployment optimization
3. **Integrate with backend** - Replace mock service
4. **Test end-to-end** - With Flutter app
5. **Deploy to production** - With monitoring

## Resources

- **PyTorch Documentation:** https://pytorch.org/docs/
- **Timm Library:** https://github.com/rwightman/pytorch-image-models
- **MLflow:** https://mlflow.org/docs/
- **ResNet Paper:** https://arxiv.org/abs/1512.03385
- **EfficientNet Paper:** https://arxiv.org/abs/1905.11946
- **Focal Loss Paper:** https://arxiv.org/abs/1708.02002
