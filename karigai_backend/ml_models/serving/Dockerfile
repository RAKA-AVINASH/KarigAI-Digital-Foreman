# KarigAI Model Serving Docker Image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for models and data
RUN mkdir -p /app/models /app/data /app/logs /app/backups

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_REGISTRY_PATH=/app/data/model_registry.json
ENV MLFLOW_TRACKING_URI=sqlite:///app/data/mlflow.db
ENV LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/system/status || exit 1

# Create non-root user
RUN useradd -m -u 1000 karigai && chown -R karigai:karigai /app
USER karigai

# Run the application
CMD ["python", "model_server.py", "--host", "0.0.0.0", "--port", "8000"]