# Model Deployment Guide for KarigAI

This guide covers deploying trained speech models to production with ONNX optimization and API serving.

## Overview

The deployment process involves:
1. Model export to ONNX format
2. Model quantization for optimization
3. API server setup with FastAPI
4. Docker containerization
5. Production deployment

## Model Export

### Export Speech Recognition Model to ONNX

```python
from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
from transformers import WhisperProcessor

# Load trained model
model_path = "./ml_models/models/speech_recognition"
processor = WhisperProcessor.from_pretrained(model_path)

# Convert to ONNX
ort_model = ORTModelForSpeechSeq2Seq.from_pretrained(
    model_path,
    export=True
)

# Save ONNX model
export_path = "./ml_models/models/exports/whisper_onnx"
ort_model.save_pretrained(export_path)
processor.save_pretrained(export_path)

print(f"Model exported to {export_path}")
```

### Export TTS Model to ONNX

```python
import torch
from training.train_tts import Tacotron2Model

# Load model
checkpoint = torch.load("./ml_models/models/tts/tts_model.pt")
config = checkpoint['config']
char_to_idx = checkpoint['char_to_idx']

model = Tacotron2Model(config, len(char_to_idx))
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

# Export to ONNX
dummy_input = torch.randint(0, len(char_to_idx), (1, 50))

torch.onnx.export(
    model,
    dummy_input,
    "./ml_models/models/exports/tts_model.onnx",
    input_names=['text_sequence'],
    output_names=['mel_spectrogram'],
    dynamic_axes={
        'text_sequence': {1: 'sequence_length'},
        'mel_spectrogram': {1: 'mel_length'}
    },
    opset_version=14
)

print("TTS model exported to ONNX")
```

## Model Quantization

### Quantize for Faster Inference

```python
from optimum.onnxruntime import ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig

# Load ONNX model
model_path = "./ml_models/models/exports/whisper_onnx"

# Create quantizer
quantizer = ORTQuantizer.from_pretrained(model_path)

# Configure quantization (INT8)
qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False)

# Quantize
quantizer.quantize(
    save_dir="./ml_models/models/exports/whisper_quantized",
    quantization_config=qconfig
)

print("Model quantized successfully")
```

**Benefits:**
- 4x smaller model size
- 2-3x faster inference
- Minimal accuracy loss (<2%)

## API Server Setup

### Start Development Server

```bash
cd karigai_backend/ml_models
python inference/speech_inference_api.py
```

Or with uvicorn:

```bash
uvicorn inference.speech_inference_api:app --reload --host 0.0.0.0 --port 8000
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/models/info

# Transcribe audio
curl -X POST http://localhost:8000/stt/transcribe \
  -F "audio=@test_audio.wav" \
  -F "language=hi"

# Synthesize speech
curl -X POST http://localhost:8000/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "नमस्ते", "language": "hi"}' \
  --output output.wav
```

### API Documentation

Access interactive API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker Deployment

### Create Dockerfile

```dockerfile
# karigai_backend/ml_models/Dockerfile

FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements-ml.txt .
RUN pip3 install --no-cache-dir -r requirements-ml.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run API server
CMD ["uvicorn", "inference.speech_inference_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build Docker Image

```bash
cd karigai_backend/ml_models
docker build -t karigai-speech-api:latest .
```

### Run Docker Container

```bash
# With GPU support
docker run --gpus all -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  karigai-speech-api:latest

# CPU only
docker run -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  karigai-speech-api:latest
```

### Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  speech-api:
    image: karigai-speech-api:latest
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - ./cache:/app/cache
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - MODEL_CACHE_DIR=/app/cache
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## Production Deployment

### Option 1: AWS Deployment

#### EC2 with GPU

1. **Launch EC2 Instance:**
   - Instance type: g4dn.xlarge or p3.2xlarge
   - AMI: Deep Learning AMI (Ubuntu)
   - Storage: 100 GB SSD

2. **Setup:**
   ```bash
   # SSH into instance
   ssh -i key.pem ubuntu@<instance-ip>
   
   # Clone repository
   git clone <repo-url>
   cd karigai_backend/ml_models
   
   # Install dependencies
   pip install -r requirements-ml.txt
   
   # Download models
   aws s3 sync s3://karigai-models/exports ./models/exports
   
   # Start API
   uvicorn inference.speech_inference_api:app --host 0.0.0.0 --port 8000
   ```

3. **Setup Nginx Reverse Proxy:**
   ```nginx
   server {
       listen 80;
       server_name api.karigai.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

#### ECS with Fargate

1. **Push Docker image to ECR:**
   ```bash
   aws ecr create-repository --repository-name karigai-speech-api
   docker tag karigai-speech-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/karigai-speech-api:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/karigai-speech-api:latest
   ```

2. **Create ECS Task Definition:**
   ```json
   {
     "family": "karigai-speech-api",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "2048",
     "memory": "8192",
     "containerDefinitions": [{
       "name": "speech-api",
       "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/karigai-speech-api:latest",
       "portMappings": [{
         "containerPort": 8000,
         "protocol": "tcp"
       }]
     }]
   }
   ```

3. **Create ECS Service with Load Balancer**

### Option 2: Google Cloud Platform

#### Cloud Run

1. **Build and push to GCR:**
   ```bash
   gcloud builds submit --tag gcr.io/<project-id>/karigai-speech-api
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy karigai-speech-api \
     --image gcr.io/<project-id>/karigai-speech-api \
     --platform managed \
     --region us-central1 \
     --memory 8Gi \
     --cpu 4 \
     --max-instances 10
   ```

#### GKE (Kubernetes)

1. **Create cluster:**
   ```bash
   gcloud container clusters create karigai-cluster \
     --num-nodes 3 \
     --machine-type n1-standard-4 \
     --accelerator type=nvidia-tesla-t4,count=1
   ```

2. **Deploy with Kubernetes:**
   ```yaml
   # deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: speech-api
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: speech-api
     template:
       metadata:
         labels:
           app: speech-api
       spec:
         containers:
         - name: speech-api
           image: gcr.io/<project-id>/karigai-speech-api
           ports:
           - containerPort: 8000
           resources:
             limits:
               nvidia.com/gpu: 1
   ```

### Option 3: Azure Deployment

#### Azure Container Instances

```bash
az container create \
  --resource-group karigai-rg \
  --name speech-api \
  --image <registry>.azurecr.io/karigai-speech-api:latest \
  --cpu 4 \
  --memory 8 \
  --gpu-count 1 \
  --gpu-sku V100 \
  --ports 8000
```

## Monitoring and Logging

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
transcription_requests = Counter('transcription_requests_total', 'Total transcription requests')
transcription_duration = Histogram('transcription_duration_seconds', 'Transcription duration')

@app.post("/stt/transcribe")
async def transcribe_audio(...):
    transcription_requests.inc()
    
    with transcription_duration.time():
        # Transcription logic
        pass

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Logging

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    'speech_api.log',
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[handler]
)
```

### Health Checks

```python
@app.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe."""
    if model_manager.stt_model is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    return {"status": "ready"}
```

## Performance Optimization

### Model Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_transcription(audio_hash: str):
    """Cache transcriptions by audio hash."""
    pass
```

### Batch Processing

```python
@app.post("/stt/batch")
async def batch_transcribe(audio_files: List[UploadFile]):
    """Process multiple files in batch for efficiency."""
    # Batch inference is more efficient than individual requests
    pass
```

### Load Balancing

Use multiple API instances behind a load balancer:

```yaml
# nginx.conf
upstream speech_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://speech_api;
    }
}
```

## Security

### API Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.post("/stt/transcribe")
async def transcribe_audio(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    ...
):
    # Verify token
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Process request
    pass
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/stt/transcribe")
@limiter.limit("10/minute")
async def transcribe_audio(...):
    pass
```

## Cost Optimization

### Auto-scaling

Configure auto-scaling based on CPU/GPU usage:

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: speech-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: speech-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Spot Instances

Use spot instances for cost savings (AWS, GCP, Azure):

```bash
# AWS EC2 Spot
aws ec2 run-instances \
  --instance-type g4dn.xlarge \
  --instance-market-options MarketType=spot
```

## Troubleshooting

### Issue: High Latency

**Solutions:**
1. Use ONNX quantized models
2. Enable batch processing
3. Add caching layer
4. Use GPU instances
5. Optimize model architecture

### Issue: Out of Memory

**Solutions:**
1. Reduce batch size
2. Use model quantization
3. Increase instance memory
4. Implement request queuing

### Issue: Model Loading Slow

**Solutions:**
1. Use model caching
2. Pre-load models on startup
3. Use faster storage (SSD)
4. Reduce model size with quantization

## Next Steps

After deployment:

1. ✅ Monitor API performance
2. ✅ Set up alerts for errors
3. ✅ Implement A/B testing for model updates
4. ✅ Collect user feedback
5. ✅ Continuously improve models

## Resources

- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **ONNX Runtime:** https://onnxruntime.ai/
- **Docker Documentation:** https://docs.docker.com/
- **Kubernetes Documentation:** https://kubernetes.io/docs/
