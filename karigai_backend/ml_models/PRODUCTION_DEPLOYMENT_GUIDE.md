# Production Deployment Guide

This guide covers deploying KarigAI ML models to production environments.

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Deployment Steps](#deployment-steps)
4. [Configuration](#configuration)
5. [Monitoring and Logging](#monitoring-and-logging)
6. [Scaling](#scaling)
7. [Security](#security)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)

---

## Deployment Options

### Option 1: Cloud Deployment (Recommended)

**AWS Deployment**:
- EC2 instances with GPU (g4dn.xlarge or higher)
- S3 for model storage
- ECS/EKS for container orchestration
- CloudWatch for monitoring
- ALB for load balancing

**GCP Deployment**:
- Compute Engine with GPU (n1-standard-4 + T4 GPU)
- Cloud Storage for models
- GKE for Kubernetes
- Cloud Monitoring
- Cloud Load Balancing

**Azure Deployment**:
- Virtual Machines with GPU (NC6 or higher)
- Blob Storage for models
- AKS for Kubernetes
- Azure Monitor
- Application Gateway

### Option 2: On-Premise Deployment

**Hardware Requirements**:
- Server with NVIDIA GPU (RTX 3090 or better)
- 32GB+ RAM
- 500GB+ SSD storage
- 1Gbps network connection

**Software Stack**:
- Ubuntu 20.04 LTS or later
- Docker and Docker Compose
- NVIDIA Docker runtime
- Kubernetes (optional, for scaling)

### Option 3: Hybrid Deployment

- Critical models on-premise
- Non-critical models in cloud
- API services as fallback
- Edge deployment for offline scenarios

---

## Infrastructure Requirements

### Minimum Requirements

**For API Mode** (using paid APIs):
- 2 CPU cores
- 4GB RAM
- 20GB storage
- No GPU required

**For Local Mode** (using trained models):
- 8 CPU cores
- 16GB RAM
- 100GB storage
- NVIDIA GPU with 8GB+ VRAM (recommended)

**For Hybrid Mode** (recommended):
- 4 CPU cores
- 8GB RAM
- 50GB storage
- NVIDIA GPU with 6GB+ VRAM (optional)

### Recommended Production Setup

**Application Server**:
- 16 CPU cores
- 32GB RAM
- 200GB SSD storage
- NVIDIA T4 or better GPU

**Database Server**:
- 8 CPU cores
- 16GB RAM
- 500GB SSD storage
- PostgreSQL 14+

**Cache Server**:
- 4 CPU cores
- 8GB RAM
- Redis 6+

**Load Balancer**:
- 2 CPU cores
- 4GB RAM
- NGINX or HAProxy

---

## Deployment Steps

### Step 1: Prepare Environment

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install NVIDIA Docker (for GPU support)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu20.04 nvidia-smi
```

### Step 2: Clone Repository

```bash
# Clone repository
git clone https://github.com/your-org/karigai.git
cd karigai

# Checkout production branch
git checkout production
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp karigai_backend/.env.example karigai_backend/.env

# Edit configuration
nano karigai_backend/.env
```

**Key Configuration Variables**:

```bash
# Application
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-secure-key>

# Database
DATABASE_URL=postgresql://user:password@db-host:5432/karigai
REDIS_URL=redis://redis-host:6379/0

# Model Configuration
MODEL_MODE=hybrid  # api, local, or hybrid
MODEL_DIR=/app/ml_models/models/exports
ENABLE_MODEL_FALLBACK=true
WARM_UP_MODELS=true

# API Keys (for hybrid/api mode)
OPENAI_API_KEY=<your-key>
ELEVENLABS_API_KEY=<your-key>

# Performance
MAX_WORKERS=4
MAX_BATCH_SIZE=8
ENABLE_MODEL_CACHE=true
ENABLE_RESULT_CACHE=true
RESULT_CACHE_TTL=3600

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=INFO
```

### Step 4: Download Models

```bash
# Download trained models
cd karigai_backend/ml_models
python download_models.py --all

# Verify models
python verify_models.py

# Convert to ONNX if needed
python convert_to_onnx.py --all
```

### Step 5: Build Docker Images

```bash
# Build backend image
docker build -t karigai-backend:latest -f karigai_backend/Dockerfile karigai_backend/

# Build mobile app (optional)
docker build -t karigai-mobile:latest -f karigai_mobile/Dockerfile karigai_mobile/
```

### Step 6: Deploy with Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Step 7: Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create initial data
docker-compose -f docker-compose.prod.yml exec backend python scripts/init_db.py
```

### Step 8: Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Test API
curl -X POST http://localhost:8000/api/v1/models/speech-recognition \
  -H "Content-Type: application/json" \
  -d '{"audio": "base64_encoded_audio", "language": "hi"}'

# Check metrics
curl http://localhost:9090/metrics
```

---

## Configuration

### Production Configuration File

Create `karigai_backend/config/production.yaml`:

```yaml
app:
  name: KarigAI
  environment: production
  debug: false
  host: 0.0.0.0
  port: 8000
  workers: 4

database:
  url: ${DATABASE_URL}
  pool_size: 20
  max_overflow: 10
  pool_timeout: 30

redis:
  url: ${REDIS_URL}
  max_connections: 50

models:
  mode: hybrid
  directory: /app/ml_models/models/exports
  fallback_enabled: true
  warm_up: true
  cache_enabled: true
  
  services:
    speech_recognition:
      mode: local
      timeout: 5.0
      max_retries: 2
    
    text_to_speech:
      mode: local
      timeout: 3.0
      max_retries: 2
    
    vision:
      mode: hybrid
      timeout: 10.0
      max_retries: 1
    
    nlp:
      mode: hybrid
      timeout: 5.0
      max_retries: 2

performance:
  max_batch_size: 8
  request_timeout: 30
  max_concurrent_requests: 100
  
monitoring:
  enabled: true
  metrics_port: 9090
  log_level: INFO
  sentry_dsn: ${SENTRY_DSN}

security:
  cors_origins:
    - https://karigai.com
    - https://app.karigai.com
  rate_limit: 100/minute
  api_key_required: true
```

### Load Balancer Configuration

**NGINX Configuration** (`/etc/nginx/sites-available/karigai`):

```nginx
upstream karigai_backend {
    least_conn;
    server backend1:8000 max_fails=3 fail_timeout=30s;
    server backend2:8000 max_fails=3 fail_timeout=30s;
    server backend3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.karigai.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.karigai.com;
    
    ssl_certificate /etc/ssl/certs/karigai.crt;
    ssl_certificate_key /etc/ssl/private/karigai.key;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # File upload size
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://karigai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /metrics {
        proxy_pass http://karigai_backend;
        allow 10.0.0.0/8;  # Internal network only
        deny all;
    }
}
```

---

## Monitoring and Logging

### Prometheus Configuration

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'karigai-backend'
    static_configs:
      - targets: ['backend:9090']
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

### Grafana Dashboards

Import pre-built dashboards:
- Application metrics
- Model inference metrics
- System resources
- Database performance

### Logging Configuration

**Structured Logging** (`karigai_backend/app/core/logging.py`):

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/var/log/karigai/app.log")
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

### Alerting Rules

Create `monitoring/alerts.yml`:

```yaml
groups:
  - name: karigai_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/sec"
      
      - alert: HighModelLatency
        expr: histogram_quantile(0.95, rate(model_inference_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High model inference latency"
          description: "P95 latency is {{ $value }} seconds"
      
      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / rate(cache_requests_total[5m]) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value }}"
```

---

## Scaling

### Horizontal Scaling

**Kubernetes Deployment** (`k8s/deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: karigai-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: karigai-backend
  template:
    metadata:
      labels:
        app: karigai-backend
    spec:
      containers:
      - name: backend
        image: karigai-backend:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
            nvidia.com/gpu: "1"
          limits:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: "1"
        env:
        - name: MODEL_MODE
          value: "hybrid"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: karigai-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: karigai-backend
spec:
  selector:
    app: karigai-backend
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: karigai-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: karigai-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Scaling

Adjust resources based on load:

```bash
# Increase workers
export MAX_WORKERS=8

# Increase batch size
export MAX_BATCH_SIZE=16

# Increase database connections
export DB_POOL_SIZE=40
```

---

## Security

### SSL/TLS Configuration

```bash
# Generate SSL certificate (Let's Encrypt)
sudo certbot --nginx -d api.karigai.com

# Auto-renewal
sudo certbot renew --dry-run
```

### API Authentication

Implement JWT-based authentication:

```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    # Verify JWT token
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/models/speech-recognition")
@limiter.limit("100/minute")
async def speech_recognition(request: Request):
    # Handle request
    pass
```

### Secrets Management

Use environment variables or secret management services:

```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id karigai/prod/api-keys

# HashiCorp Vault
vault kv get secret/karigai/prod/api-keys
```

---

## Backup and Recovery

### Database Backup

```bash
# Automated daily backup
0 2 * * * pg_dump -h db-host -U postgres karigai | gzip > /backups/karigai_$(date +\%Y\%m\%d).sql.gz

# Restore from backup
gunzip < /backups/karigai_20240213.sql.gz | psql -h db-host -U postgres karigai
```

### Model Backup

```bash
# Backup models to S3
aws s3 sync ml_models/models/exports s3://karigai-models/backups/$(date +%Y%m%d)/

# Restore models
aws s3 sync s3://karigai-models/backups/20240213/ ml_models/models/exports/
```

### Disaster Recovery Plan

1. **RTO (Recovery Time Objective)**: 1 hour
2. **RPO (Recovery Point Objective)**: 24 hours
3. **Backup Frequency**: Daily
4. **Backup Retention**: 30 days
5. **Failover Strategy**: Active-passive with automatic failover

---

## Troubleshooting

### Common Issues

**Issue**: Models not loading

```bash
# Check model files
ls -lh ml_models/models/exports/

# Verify ONNX models
python -c "import onnxruntime as ort; ort.InferenceSession('model.onnx')"

# Check logs
docker-compose logs backend | grep "model"
```

**Issue**: High memory usage

```bash
# Monitor memory
docker stats

# Reduce batch size
export MAX_BATCH_SIZE=4

# Disable model caching
export ENABLE_MODEL_CACHE=false
```

**Issue**: Slow inference

```bash
# Check GPU usage
nvidia-smi

# Enable GPU inference
export CUDA_VISIBLE_DEVICES=0

# Use quantized models
python convert_to_onnx.py --quantize int8
```

**Issue**: API fallback always triggered

```bash
# Check model loading errors
docker-compose logs backend | grep "ERROR"

# Verify model paths
docker-compose exec backend ls -l /app/ml_models/models/exports/

# Test model loading
docker-compose exec backend python -c "from ml_models.integration.service_integration import get_integrator; integrator = get_integrator(); integrator.load_model('speech_recognition')"
```

### Performance Tuning

1. **Enable GPU**: Set `CUDA_VISIBLE_DEVICES`
2. **Use ONNX Runtime**: Convert models to ONNX
3. **Enable quantization**: Use INT8 models
4. **Increase workers**: Set `MAX_WORKERS`
5. **Enable caching**: Set `ENABLE_MODEL_CACHE=true`
6. **Batch requests**: Set `MAX_BATCH_SIZE`

### Support

For production support:
- Email: support@karigai.com
- Slack: #karigai-production
- On-call: +1-XXX-XXX-XXXX

---

## Checklist

Before going to production:

- [ ] All models trained and exported
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database migrations run
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Security audit passed
- [ ] Documentation updated
- [ ] Team trained on deployment procedures

---

## Version History

- **v1.0.0** (2024-02-13): Initial production deployment guide

---

## License

Copyright © 2024 KarigAI. All rights reserved.
