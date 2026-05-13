# Computer Vision Models Implementation Guide

## Overview

This comprehensive guide covers all computer vision models for KarigAI (Tasks 17.3-17.8):
1. OCR Model for Error Codes
2. Pattern and Design Analysis Model
3. Product Quality Assessment Model
4. Crop Disease Detection Model
5. Circuit Board Analysis Model
6. Model Deployment and Inference API

## Task 17.3: OCR Model for Error Codes and Text

### Model Architecture: CRNN (CNN + LSTM)

**Components:**
- **CNN Backbone:** Extract visual features from text regions
- **RNN (LSTM):** Sequence modeling for character recognition
- **CTC Loss:** Connectionist Temporal Classification for alignment

**Alternative:** Transformer-based OCR (TrOCR, PARSeq)

### Implementation

```python
# training/train_ocr_model.py
import torch
import torch.nn as nn

class CRNN(nn.Module):
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
        self.rnn = nn.LSTM(512, hidden_size, bidirectional=True, num_layers=2)
        
        # Output layer
        self.fc = nn.Linear(hidden_size * 2, num_chars + 1)  # +1 for CTC blank
    
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
```

### Text Detection (EAST/CRAFT)

```python
# For locating text regions before OCR
import cv2

def detect_text_regions(image):
    """Detect text regions using EAST detector"""
    # Load EAST model
    net = cv2.dnn.readNet('frozen_east_text_detection.pb')
    
    # Prepare image
    blob = cv2.dnn.blobFromImage(image, 1.0, (320, 320),
                                 (123.68, 116.78, 103.94), True, False)
    net.setInput(blob)
    
    # Get predictions
    scores, geometry = net.forward(['feature_fusion/Conv_7/Sigmoid',
                                   'feature_fusion/concat_3'])
    
    # Decode boxes
    boxes = decode_predictions(scores, geometry)
    return boxes
```

### Training Configuration

```yaml
# configs/ocr_config.yaml
model:
  type: "crnn"
  hidden_size: 256
  num_chars: 62  # 0-9, A-Z, a-z

training:
  batch_size: 64
  num_epochs: 100
  learning_rate: 0.001
  image_height: 32
  image_width: 128

data:
  train_dir: "data/vision/error_codes/processed/train"
  val_dir: "data/vision/error_codes/processed/val"
  test_dir: "data/vision/error_codes/processed/test"
  
target:
  character_accuracy: 0.95
```

### Post-Processing

```python
def decode_ctc(predictions, charset):
    """Decode CTC predictions to text"""
    # Remove duplicates and blanks
    decoded = []
    prev_char = None
    
    for pred in predictions:
        char_idx = pred.argmax()
        if char_idx != len(charset) and char_idx != prev_char:
            decoded.append(charset[char_idx])
        prev_char = char_idx
    
    return ''.join(decoded)

def validate_error_code(text, patterns):
    """Validate error code against known patterns"""
    import re
    for pattern in patterns:
        if re.match(pattern, text):
            return True, text
    
    # Try to correct common OCR errors
    corrected = correct_ocr_errors(text)
    return False, corrected
```

## Task 17.4: Pattern and Design Analysis Model

### Model Architecture: Mask R-CNN / YOLO

**For Motif Detection:**
- **Mask R-CNN:** Instance segmentation for individual motifs
- **YOLO:** Fast object detection for design elements

**For Style Transfer:**
- **CycleGAN:** Unpaired image-to-image translation
- **StyleGAN:** Generate modern variations

### Implementation

```python
# training/train_pattern_analysis.py
import torch
import torchvision
from torchvision.models.detection import maskrcnn_resnet50_fpn

class PatternAnalysisModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        # Mask R-CNN for motif detection
        self.detector = maskrcnn_resnet50_fpn(pretrained=True)
        in_features = self.detector.roi_heads.box_predictor.cls_score.in_features
        self.detector.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
        
        # Style transfer network (CycleGAN)
        self.style_transfer = CycleGANGenerator()
    
    def forward(self, images, mode='detect'):
        if mode == 'detect':
            return self.detector(images)
        elif mode == 'transfer':
            return self.style_transfer(images)
```

### Feature Extraction

```python
class DesignFeatureExtractor(nn.Module):
    """Extract design features for similarity matching"""
    
    def __init__(self):
        super().__init__()
        self.backbone = models.resnet50(pretrained=True)
        self.backbone.fc = nn.Identity()
        
        # Feature projection
        self.projector = nn.Sequential(
            nn.Linear(2048, 512),
            nn.ReLU(),
            nn.Linear(512, 128)
        )
    
    def forward(self, x):
        features = self.backbone(x)
        embeddings = self.projector(features)
        return F.normalize(embeddings, dim=1)

def compute_similarity(embedding1, embedding2):
    """Compute cosine similarity between design embeddings"""
    return F.cosine_similarity(embedding1, embedding2)
```

### Training Configuration

```yaml
# configs/pattern_config.yaml
model:
  detector: "mask_rcnn"
  backbone: "resnet50_fpn"
  num_motif_classes: 50

training:
  batch_size: 8
  num_epochs: 80
  learning_rate: 0.001
  
target:
  motif_detection_map: 0.85
  style_transfer_fid: 50.0
```

## Task 17.5: Product Quality Assessment Model

### Model Architecture: Multi-Task CNN

**Tasks:**
1. Quality grading (A/B/C classification)
2. Continuous quality score (regression)
3. Defect localization (attention maps)

### Implementation

```python
# training/train_quality_assessment.py
class QualityAssessmentModel(nn.Module):
    def __init__(self, num_grades=3, num_products=5):
        super().__init__()
        
        # Shared backbone
        self.backbone = models.efficientnet_b0(pretrained=True)
        num_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Identity()
        
        # Grade classification head
        self.grade_head = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 256),
            nn.ReLU(),
            nn.Linear(256, num_grades)
        )
        
        # Quality score regression head
        self.score_head = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()  # Output 0-1
        )
        
        # Attention for defect localization
        self.attention = nn.Sequential(
            nn.Conv2d(num_features, 1, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        features = self.backbone.features(x)
        
        # Global average pooling
        pooled = F.adaptive_avg_pool2d(features, 1).flatten(1)
        
        # Predictions
        grade = self.grade_head(pooled)
        score = self.score_head(pooled)
        attention = self.attention(features)
        
        return grade, score, attention
```

### Multi-Task Loss

```python
class QualityLoss(nn.Module):
    def __init__(self, alpha=1.0, beta=1.0):
        super().__init__()
        self.alpha = alpha  # Grade loss weight
        self.beta = beta    # Score loss weight
        self.ce_loss = nn.CrossEntropyLoss()
        self.mse_loss = nn.MSELoss()
    
    def forward(self, grade_pred, score_pred, grade_true, score_true):
        grade_loss = self.ce_loss(grade_pred, grade_true)
        score_loss = self.mse_loss(score_pred, score_true)
        return self.alpha * grade_loss + self.beta * score_loss
```

### Training Configuration

```yaml
# configs/quality_config.yaml
model:
  backbone: "efficientnet_b0"
  num_grades: 3  # A, B, C
  products: ["saffron", "walnuts", "textiles", "spices", "handicrafts"]

training:
  batch_size: 32
  num_epochs: 60
  learning_rate: 0.001
  alpha: 1.0  # Grade loss weight
  beta: 0.5   # Score loss weight

target:
  grading_accuracy: 0.88
```

## Task 17.6: Crop Disease Detection Model

### Model Architecture: DenseNet / MobileNet

**DenseNet:** Better feature reuse, higher accuracy
**MobileNet:** Lightweight, mobile-friendly

### Implementation

```python
# training/train_crop_disease.py
class CropDiseaseModel(nn.Module):
    def __init__(self, num_diseases, num_crops):
        super().__init__()
        
        # DenseNet backbone
        self.backbone = models.densenet121(pretrained=True)
        num_features = self.backbone.classifier.in_features
        
        # Disease classification
        self.disease_head = nn.Linear(num_features, num_diseases)
        
        # Severity estimation
        self.severity_head = nn.Sequential(
            nn.Linear(num_features, 128),
            nn.ReLU(),
            nn.Linear(128, 3)  # Mild, Moderate, Severe
        )
        
        # Crop type classification
        self.crop_head = nn.Linear(num_features, num_crops)
    
    def forward(self, x):
        features = self.backbone.features(x)
        features = F.adaptive_avg_pool2d(features, 1).flatten(1)
        
        disease = self.disease_head(features)
        severity = self.severity_head(features)
        crop = self.crop_head(features)
        
        return disease, severity, crop
```

### Treatment Recommendation System

```python
class TreatmentRecommender:
    def __init__(self, treatment_db_path):
        with open(treatment_db_path) as f:
            self.treatments = json.load(f)
    
    def recommend(self, disease, severity, crop, location):
        """Recommend treatments based on disease and context"""
        key = f"{crop}_{disease}"
        
        if key in self.treatments:
            treatments = self.treatments[key]
            
            # Filter by severity
            filtered = [t for t in treatments if t['severity'] == severity]
            
            # Prioritize local solutions
            local = [t for t in filtered if t['available_in'] == location]
            
            return local if local else filtered
        
        return []
```

### Training Configuration

```yaml
# configs/crop_disease_config.yaml
model:
  backbone: "densenet121"
  num_diseases: 38
  num_crops: 14

training:
  batch_size: 32
  num_epochs: 50
  learning_rate: 0.001
  
data:
  use_plantvillage: true
  custom_data_dir: "data/vision/crops/processed"

target:
  disease_accuracy: 0.92
  severity_accuracy: 0.85
```

## Task 17.7: Circuit Board Analysis Model

### Model Architecture: Faster R-CNN

**For Component Detection:**
- Faster R-CNN with ResNet50 backbone
- Bounding box regression for component localization
- Multi-class classification for component types

### Implementation

```python
# training/train_circuit_analysis.py
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

class CircuitBoardModel(nn.Module):
    def __init__(self, num_components, num_damage_types):
        super().__init__()
        
        # Faster R-CNN for component detection
        self.detector = fasterrcnn_resnet50_fpn(pretrained=True)
        in_features = self.detector.roi_heads.box_predictor.cls_score.in_features
        self.detector.roi_heads.box_predictor = FastRCNNPredictor(
            in_features, num_components
        )
        
        # Damage classification head
        self.damage_classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_damage_types)
        )
    
    def forward(self, images, targets=None):
        if self.training:
            return self.detector(images, targets)
        else:
            detections = self.detector(images)
            # Add damage classification
            for detection in detections:
                boxes = detection['boxes']
                # Extract ROI features and classify damage
                # ... (implementation details)
            return detections
```

### Hotspot Detection

```python
class HotspotDetector:
    """Detect diagnostic hotspots on circuit boards"""
    
    def __init__(self, model):
        self.model = model
        self.grad_cam = GradCAM(model)
    
    def detect_hotspots(self, image):
        """Generate attention heatmap for diagnostics"""
        # Get model predictions
        with torch.no_grad():
            output = self.model(image)
        
        # Generate Grad-CAM
        heatmap = self.grad_cam.generate(image, target_class=output.argmax())
        
        # Find hotspot regions
        hotspots = self.extract_hotspots(heatmap, threshold=0.7)
        
        return hotspots, heatmap
```

### Training Configuration

```yaml
# configs/circuit_config.yaml
model:
  detector: "faster_rcnn"
  backbone: "resnet50"
  num_components: 20
  num_damage_types: 6

training:
  batch_size: 4
  num_epochs: 100
  learning_rate: 0.001
  
target:
  component_detection_map: 0.85
  damage_classification_acc: 0.80
```

## Task 17.8: Model Deployment and Inference API

### ONNX Export

```python
# utils/export_models.py
def export_to_onnx(model, model_name, input_size=(1, 3, 224, 224)):
    """Export PyTorch model to ONNX format"""
    model.eval()
    dummy_input = torch.randn(input_size)
    
    torch.onnx.export(
        model,
        dummy_input,
        f"models/exports/{model_name}.onnx",
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        },
        opset_version=13
    )
    
    print(f"Exported {model_name} to ONNX")
```

### Model Quantization

```python
# utils/quantize_models.py
import torch.quantization

def quantize_model(model, calibration_data):
    """Quantize model to INT8 for faster inference"""
    # Prepare for quantization
    model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
    torch.quantization.prepare(model, inplace=True)
    
    # Calibrate with sample data
    with torch.no_grad():
        for data in calibration_data:
            model(data)
    
    # Convert to quantized model
    torch.quantization.convert(model, inplace=True)
    
    return model
```

### FastAPI Inference Server

```python
# inference/vision_inference_api.py
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import onnxruntime as ort
import cv2
import numpy as np

app = FastAPI(title="KarigAI Vision API")

# Load ONNX models
equipment_session = ort.InferenceSession("models/exports/equipment.onnx")
ocr_session = ort.InferenceSession("models/exports/ocr.onnx")
quality_session = ort.InferenceSession("models/exports/quality.onnx")
crop_session = ort.InferenceSession("models/exports/crop_disease.onnx")
circuit_session = ort.InferenceSession("models/exports/circuit.onnx")

@app.post("/vision/equipment/identify")
async def identify_equipment(file: UploadFile = File(...)):
    """Identify equipment from image"""
    # Read image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preprocess
    image = preprocess_image(image, size=224)
    
    # Inference
    outputs = equipment_session.run(None, {'input': image})
    predictions = postprocess_equipment(outputs)
    
    return JSONResponse(content=predictions)

@app.post("/vision/ocr/read_error_code")
async def read_error_code(file: UploadFile = File(...)):
    """Read error code from display image"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Detect text regions
    text_regions = detect_text_regions(image)
    
    # OCR on each region
    error_codes = []
    for region in text_regions:
        cropped = crop_region(image, region)
        preprocessed = preprocess_ocr(cropped)
        
        outputs = ocr_session.run(None, {'input': preprocessed})
        text = decode_ctc(outputs[0])
        error_codes.append(text)
    
    return JSONResponse(content={'error_codes': error_codes})

@app.post("/vision/quality/assess")
async def assess_quality(file: UploadFile = File(...), product_type: str = "saffron"):
    """Assess product quality"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preprocess
    image = preprocess_image(image, size=224)
    
    # Inference
    outputs = quality_session.run(None, {'input': image})
    grade, score, attention = postprocess_quality(outputs)
    
    return JSONResponse(content={
        'grade': grade,
        'score': float(score),
        'defects': extract_defects(attention)
    })

@app.post("/vision/crop/diagnose")
async def diagnose_crop_disease(file: UploadFile = File(...)):
    """Diagnose crop disease"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preprocess
    image = preprocess_image(image, size=224)
    
    # Inference
    outputs = crop_session.run(None, {'input': image})
    disease, severity, crop = postprocess_crop(outputs)
    
    # Get treatment recommendations
    treatments = get_treatments(disease, severity, crop)
    
    return JSONResponse(content={
        'disease': disease,
        'severity': severity,
        'crop': crop,
        'treatments': treatments
    })

@app.post("/vision/circuit/analyze")
async def analyze_circuit(file: UploadFile = File(...)):
    """Analyze circuit board"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preprocess
    image = preprocess_image(image, size=640)
    
    # Inference
    outputs = circuit_session.run(None, {'input': image})
    components, damages, hotspots = postprocess_circuit(outputs)
    
    return JSONResponse(content={
        'components': components,
        'damages': damages,
        'hotspots': hotspots
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "models_loaded": 5}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Batch Processing

```python
@app.post("/vision/batch/process")
async def batch_process(files: List[UploadFile] = File(...), task: str = "equipment"):
    """Process multiple images in batch"""
    results = []
    
    # Load images
    images = []
    for file in files:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        images.append(preprocess_image(image))
    
    # Batch inference
    batch = np.stack(images)
    
    if task == "equipment":
        outputs = equipment_session.run(None, {'input': batch})
    elif task == "quality":
        outputs = quality_session.run(None, {'input': batch})
    # ... other tasks
    
    # Postprocess each result
    for i, output in enumerate(outputs[0]):
        results.append(postprocess(output, task))
    
    return JSONResponse(content={'results': results})
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy models and code
COPY models/exports /app/models/exports
COPY inference /app/inference
COPY utils /app/utils

# Expose port
EXPOSE 8001

# Run server
CMD ["python", "inference/vision_inference_api.py"]
```

### Performance Optimization

```python
# Async batch processing
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def async_inference(image, session):
    """Run inference asynchronously"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        session.run,
        None,
        {'input': image}
    )
    return result
```

## Summary

All computer vision models (Tasks 17.3-17.8) are now documented with:
- ✅ Model architectures and implementations
- ✅ Training configurations and hyperparameters
- ✅ Loss functions and optimization strategies
- ✅ Evaluation metrics and target accuracies
- ✅ Export and deployment procedures
- ✅ FastAPI inference server
- ✅ Batch processing and optimization

## Next Steps

1. **Collect datasets** for each model type
2. **Train models** using provided scripts
3. **Evaluate** on test sets to meet accuracy targets
4. **Export to ONNX** for deployment
5. **Deploy API server** with Docker
6. **Integrate** with KarigAI backend services
7. **Test end-to-end** with Flutter mobile app
