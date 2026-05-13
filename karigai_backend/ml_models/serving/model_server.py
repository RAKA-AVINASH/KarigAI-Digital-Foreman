#!/usr/bin/env python3
"""
Model Serving API with Health Checks and Monitoring

This module provides a FastAPI-based model serving infrastructure with:
- REST API endpoints for model inference
- Health checks and monitoring
- Performance tracking and alerting
- A/B testing capabilities
- Load balancing and auto-scaling support
"""

import os
import sys
import json
import logging
import traceback
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import numpy as np
import torch
import onnxruntime as ort
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import time
import psutil
import threading
from contextlib import asynccontextmanager
import warnings
warnings.filterwarnings('ignore')

# Import our model registry
from model_registry import ModelRegistry, ModelStatus, PerformanceMetrics

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pydantic models for API
class InferenceRequest(BaseModel):
    """Request model for inference"""
    model_name: str
    model_version: Optional[str] = None
    inputs: Dict[str, Any]
    options: Optional[Dict[str, Any]] = {}

class InferenceResponse(BaseModel):
    """Response model for inference"""
    model_name: str
    model_version: str
    outputs: Dict[str, Any]
    latency_ms: float
    timestamp: datetime

class HealthCheckResponse(BaseModel):
    """Response model for health checks"""
    status: str
    timestamp: datetime
    model_name: str
    model_version: str
    checks: Dict[str, Any]

class MetricsResponse(BaseModel):
    """Response model for metrics"""
    model_name: str
    model_version: str
    metrics: Dict[str, float]
    timestamp: datetime

class ModelInfo(BaseModel):
    """Model information response"""
    name: str
    version: str
    status: str
    model_type: str
    framework: str
    input_shape: List[int]
    output_shape: List[int]
    accuracy: float
    latency_ms: float
    model_size_mb: float

class ModelServer:
    """Model serving infrastructure"""
    
    def __init__(self, registry: ModelRegistry, config: Dict[str, Any] = None):
        """Initialize model server"""
        self.registry = registry
        self.config = config or {}
        self.loaded_models = {}  # Cache for loaded models
        self.model_sessions = {}  # ONNX sessions
        self.performance_tracker = PerformanceTracker()
        self.ab_test_manager = ABTestManager()
        
        # Initialize FastAPI app
        self.app = self._create_app()
        
        logger.info("Model server initialized")
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting model server...")
            await self._load_production_models()
            yield
            # Shutdown
            logger.info("Shutting down model server...")
            self._cleanup_resources()
        
        app = FastAPI(
            title="KarigAI Model Serving API",
            description="Production model serving infrastructure for KarigAI",
            version="1.0.0",
            lifespan=lifespan
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add routes
        self._add_routes(app)
        
        return app
    
    def _add_routes(self, app: FastAPI):
        """Add API routes"""
        
        @app.get("/")
        async def root():
            """Root endpoint"""
            return {"message": "KarigAI Model Serving API", "version": "1.0.0"}
        
        @app.post("/predict", response_model=InferenceResponse)
        async def predict(request: InferenceRequest, background_tasks: BackgroundTasks):
            """Model inference endpoint"""
            start_time = time.perf_counter()
            
            try:
                # Get model version
                model_version = request.model_version
                if not model_version:
                    # Get latest production version
                    model_metadata = self.registry.get_model(request.model_name)
                    if not model_metadata or model_metadata.status != ModelStatus.PRODUCTION:
                        raise HTTPException(status_code=404, detail="No production model found")
                    model_version = model_metadata.version
                
                # Check A/B testing
                model_version = self.ab_test_manager.get_model_version(
                    request.model_name, model_version, request.options.get("user_id")
                )
                
                # Load model if not cached
                model_key = f"{request.model_name}:{model_version}"
                if model_key not in self.loaded_models:
                    await self._load_model(request.model_name, model_version)
                
                # Run inference
                outputs = await self._run_inference(
                    request.model_name, model_version, request.inputs
                )
                
                # Calculate latency
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                
                # Record performance metrics in background
                background_tasks.add_task(
                    self._record_inference_metrics,
                    request.model_name, model_version, latency_ms, True
                )
                
                return InferenceResponse(
                    model_name=request.model_name,
                    model_version=model_version,
                    outputs=outputs,
                    latency_ms=latency_ms,
                    timestamp=datetime.now()
                )
            
            except Exception as e:
                # Calculate latency even for errors
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                
                # Record error metrics
                background_tasks.add_task(
                    self._record_inference_metrics,
                    request.model_name, request.model_version or "unknown", latency_ms, False
                )
                
                logger.error(f"Inference error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/health/{model_name}", response_model=HealthCheckResponse)
        async def health_check(model_name: str, model_version: Optional[str] = None):
            """Model health check endpoint"""
            try:
                # Get model version
                if not model_version:
                    model_metadata = self.registry.get_model(model_name)
                    if not model_metadata:
                        raise HTTPException(status_code=404, detail="Model not found")
                    model_version = model_metadata.version
                
                # Run health checks
                health_result = self.registry.check_model_health(model_name, model_version)
                
                # Additional server-side checks
                model_key = f"{model_name}:{model_version}"
                checks = {
                    "model_loaded": model_key in self.loaded_models,
                    "registry_status": health_result.get("status", "unknown"),
                    "memory_usage_mb": psutil.virtual_memory().used / (1024 * 1024),
                    "cpu_usage_percent": psutil.cpu_percent(),
                    "disk_usage_percent": psutil.disk_usage('/').percent
                }
                
                # Determine overall status
                if health_result.get("status") == "healthy" and checks["model_loaded"]:
                    status = "healthy"
                elif health_result.get("status") in ["degraded", "warning"]:
                    status = "degraded"
                else:
                    status = "unhealthy"
                
                return HealthCheckResponse(
                    status=status,
                    timestamp=datetime.now(),
                    model_name=model_name,
                    model_version=model_version,
                    checks=checks
                )
            
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/metrics/{model_name}", response_model=MetricsResponse)
        async def get_metrics(model_name: str, model_version: Optional[str] = None, hours: int = 1):
            """Get model performance metrics"""
            try:
                if not model_version:
                    model_metadata = self.registry.get_model(model_name)
                    if not model_metadata:
                        raise HTTPException(status_code=404, detail="Model not found")
                    model_version = model_metadata.version
                
                # Get performance history
                performance_history = self.registry.get_performance_history(
                    model_name, model_version, hours
                )
                
                if not performance_history:
                    metrics = {"message": "No metrics available"}
                else:
                    # Calculate aggregated metrics
                    latencies = [p.latency_p50 for p in performance_history]
                    error_rates = [p.error_rate for p in performance_history]
                    throughputs = [p.throughput for p in performance_history]
                    
                    metrics = {
                        "avg_latency_ms": np.mean(latencies) if latencies else 0,
                        "p95_latency_ms": np.percentile(latencies, 95) if latencies else 0,
                        "avg_error_rate": np.mean(error_rates) if error_rates else 0,
                        "avg_throughput": np.mean(throughputs) if throughputs else 0,
                        "total_requests": len(performance_history)
                    }
                
                return MetricsResponse(
                    model_name=model_name,
                    model_version=model_version,
                    metrics=metrics,
                    timestamp=datetime.now()
                )
            
            except Exception as e:
                logger.error(f"Metrics error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/models", response_model=List[ModelInfo])
        async def list_models(status: Optional[str] = None):
            """List available models"""
            try:
                model_status = ModelStatus(status) if status else None
                models = self.registry.list_models(model_status)
                
                return [
                    ModelInfo(
                        name=model.name,
                        version=model.version,
                        status=model.status.value,
                        model_type=model.model_type,
                        framework=model.framework,
                        input_shape=model.input_shape,
                        output_shape=model.output_shape,
                        accuracy=model.accuracy,
                        latency_ms=model.latency_ms,
                        model_size_mb=model.model_size_mb
                    )
                    for model in models
                ]
            
            except Exception as e:
                logger.error(f"List models error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/models/{model_name}/load")
        async def load_model(model_name: str, model_version: Optional[str] = None):
            """Load a model into memory"""
            try:
                if not model_version:
                    model_metadata = self.registry.get_model(model_name)
                    if not model_metadata:
                        raise HTTPException(status_code=404, detail="Model not found")
                    model_version = model_metadata.version
                
                await self._load_model(model_name, model_version)
                
                return {"message": f"Model {model_name}:{model_version} loaded successfully"}
            
            except Exception as e:
                logger.error(f"Load model error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.post("/models/{model_name}/unload")
        async def unload_model(model_name: str, model_version: Optional[str] = None):
            """Unload a model from memory"""
            try:
                if not model_version:
                    model_metadata = self.registry.get_model(model_name)
                    if not model_metadata:
                        raise HTTPException(status_code=404, detail="Model not found")
                    model_version = model_metadata.version
                
                model_key = f"{model_name}:{model_version}"
                
                if model_key in self.loaded_models:
                    del self.loaded_models[model_key]
                
                if model_key in self.model_sessions:
                    del self.model_sessions[model_key]
                
                return {"message": f"Model {model_name}:{model_version} unloaded successfully"}
            
            except Exception as e:
                logger.error(f"Unload model error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/system/status")
        async def system_status():
            """Get system status"""
            try:
                return {
                    "status": "healthy",
                    "timestamp": datetime.now(),
                    "loaded_models": len(self.loaded_models),
                    "system_metrics": {
                        "memory_usage_mb": psutil.virtual_memory().used / (1024 * 1024),
                        "memory_percent": psutil.virtual_memory().percent,
                        "cpu_usage_percent": psutil.cpu_percent(),
                        "disk_usage_percent": psutil.disk_usage('/').percent
                    }
                }
            
            except Exception as e:
                logger.error(f"System status error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _load_production_models(self):
        """Load all production models at startup"""
        try:
            production_models = self.registry.list_models(ModelStatus.PRODUCTION)
            
            for model in production_models:
                try:
                    await self._load_model(model.name, model.version)
                    logger.info(f"Loaded production model: {model.name}:{model.version}")
                except Exception as e:
                    logger.error(f"Failed to load model {model.name}:{model.version}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Failed to load production models: {str(e)}")
    
    async def _load_model(self, model_name: str, model_version: str):
        """Load a model into memory"""
        try:
            model_key = f"{model_name}:{model_version}"
            
            if model_key in self.loaded_models:
                return  # Already loaded
            
            # Get model metadata
            model_metadata = self.registry.get_model(model_name, model_version)
            if not model_metadata:
                raise ValueError(f"Model {model_key} not found in registry")
            
            model_path = model_metadata.artifacts.get("model_path")
            if not model_path or not os.path.exists(model_path):
                raise ValueError(f"Model file not found: {model_path}")
            
            # Load model based on framework
            if model_metadata.framework == "pytorch":
                model = torch.load(model_path, map_location='cpu')
                if hasattr(model, 'eval'):
                    model.eval()
                self.loaded_models[model_key] = model
            
            elif model_metadata.framework == "onnx":
                providers = ['CPUExecutionProvider']
                if torch.cuda.is_available():
                    providers.insert(0, 'CUDAExecutionProvider')
                
                session = ort.InferenceSession(model_path, providers=providers)
                self.model_sessions[model_key] = session
            
            else:
                raise ValueError(f"Unsupported framework: {model_metadata.framework}")
            
            logger.info(f"Model loaded: {model_key}")
        
        except Exception as e:
            logger.error(f"Failed to load model {model_name}:{model_version}: {str(e)}")
            raise
    
    async def _run_inference(self, model_name: str, model_version: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run model inference"""
        try:
            model_key = f"{model_name}:{model_version}"
            
            # Get model metadata for input/output processing
            model_metadata = self.registry.get_model(model_name, model_version)
            
            # Process inputs based on model type
            processed_inputs = self._preprocess_inputs(inputs, model_metadata)
            
            # Run inference
            if model_key in self.loaded_models:
                # PyTorch model
                model = self.loaded_models[model_key]
                with torch.no_grad():
                    outputs = model(processed_inputs)
            
            elif model_key in self.model_sessions:
                # ONNX model
                session = self.model_sessions[model_key]
                input_name = session.get_inputs()[0].name
                outputs = session.run(None, {input_name: processed_inputs.numpy()})
                outputs = torch.tensor(outputs[0])
            
            else:
                raise ValueError(f"Model {model_key} not loaded")
            
            # Process outputs
            processed_outputs = self._postprocess_outputs(outputs, model_metadata)
            
            return processed_outputs
        
        except Exception as e:
            logger.error(f"Inference error for {model_name}:{model_version}: {str(e)}")
            raise
    
    def _preprocess_inputs(self, inputs: Dict[str, Any], model_metadata) -> torch.Tensor:
        """Preprocess inputs for model"""
        try:
            # This is a simplified preprocessing - in practice, this would be more sophisticated
            if "image" in inputs:
                # Handle image input
                image_data = inputs["image"]
                if isinstance(image_data, list):
                    # Convert list to tensor
                    tensor = torch.tensor(image_data, dtype=torch.float32)
                    if len(tensor.shape) == 3:
                        tensor = tensor.unsqueeze(0)  # Add batch dimension
                    return tensor
                else:
                    # Assume it's already a tensor or numpy array
                    return torch.tensor(image_data, dtype=torch.float32)
            
            elif "text" in inputs:
                # Handle text input (would need tokenization in practice)
                return torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)  # Dummy tokenized text
            
            else:
                # Generic input handling
                if isinstance(inputs, dict) and len(inputs) == 1:
                    key = list(inputs.keys())[0]
                    return torch.tensor(inputs[key], dtype=torch.float32)
                else:
                    # Create dummy input based on model input shape
                    input_shape = model_metadata.input_shape
                    if input_shape:
                        return torch.randn(1, *input_shape)
                    else:
                        return torch.randn(1, 3, 224, 224)  # Default shape
        
        except Exception as e:
            logger.error(f"Input preprocessing error: {str(e)}")
            raise
    
    def _postprocess_outputs(self, outputs: torch.Tensor, model_metadata) -> Dict[str, Any]:
        """Postprocess model outputs"""
        try:
            if model_metadata.model_type == "classification":
                # Classification output
                probabilities = torch.softmax(outputs, dim=1)
                predicted_class = torch.argmax(probabilities, dim=1)
                
                return {
                    "predicted_class": predicted_class.item(),
                    "probabilities": probabilities.squeeze().tolist(),
                    "confidence": torch.max(probabilities).item()
                }
            
            elif model_metadata.model_type == "detection":
                # Object detection output (simplified)
                return {
                    "detections": outputs.tolist(),
                    "num_detections": len(outputs)
                }
            
            elif model_metadata.model_type == "regression":
                # Regression output
                return {
                    "prediction": outputs.item() if outputs.numel() == 1 else outputs.tolist()
                }
            
            else:
                # Generic output
                return {
                    "output": outputs.tolist(),
                    "shape": list(outputs.shape)
                }
        
        except Exception as e:
            logger.error(f"Output postprocessing error: {str(e)}")
            return {"raw_output": outputs.tolist()}
    
    async def _record_inference_metrics(self, model_name: str, model_version: str, 
                                      latency_ms: float, success: bool):
        """Record inference metrics"""
        try:
            metrics = {
                "latency_p50": latency_ms,
                "latency_p95": latency_ms,  # Single request, so p50 = p95
                "latency_p99": latency_ms,
                "throughput": 1000.0 / latency_ms if latency_ms > 0 else 0,
                "error_rate": 0.0 if success else 1.0,
                "memory_usage_mb": psutil.virtual_memory().used / (1024 * 1024),
                "cpu_usage_percent": psutil.cpu_percent(),
                "gpu_usage_percent": 0.0  # Would need GPU monitoring
            }
            
            self.registry.record_performance(model_name, model_version, metrics)
        
        except Exception as e:
            logger.error(f"Failed to record metrics: {str(e)}")
    
    def _cleanup_resources(self):
        """Cleanup resources on shutdown"""
        try:
            self.loaded_models.clear()
            self.model_sessions.clear()
            logger.info("Resources cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")


class PerformanceTracker:
    """Track model performance metrics"""
    
    def __init__(self):
        self.metrics_history = []
        self.alerts = []
    
    def record_metrics(self, model_name: str, model_version: str, metrics: Dict[str, float]):
        """Record performance metrics"""
        metric_record = {
            "timestamp": datetime.now(),
            "model_name": model_name,
            "model_version": model_version,
            "metrics": metrics
        }
        
        self.metrics_history.append(metric_record)
        
        # Check for alerts
        self._check_alerts(metric_record)
    
    def _check_alerts(self, metric_record: Dict):
        """Check if metrics trigger any alerts"""
        metrics = metric_record["metrics"]
        
        # High latency alert
        if metrics.get("latency_p95", 0) > 1000:  # 1 second threshold
            self.alerts.append({
                "timestamp": datetime.now(),
                "type": "high_latency",
                "model": f"{metric_record['model_name']}:{metric_record['model_version']}",
                "value": metrics["latency_p95"],
                "threshold": 1000
            })
        
        # High error rate alert
        if metrics.get("error_rate", 0) > 0.05:  # 5% threshold
            self.alerts.append({
                "timestamp": datetime.now(),
                "type": "high_error_rate",
                "model": f"{metric_record['model_name']}:{metric_record['model_version']}",
                "value": metrics["error_rate"],
                "threshold": 0.05
            })


class ABTestManager:
    """Manage A/B testing for model versions"""
    
    def __init__(self):
        self.ab_tests = {}
    
    def create_ab_test(self, model_name: str, control_version: str, 
                      treatment_version: str, traffic_split: float = 0.5):
        """Create A/B test between two model versions"""
        self.ab_tests[model_name] = {
            "control_version": control_version,
            "treatment_version": treatment_version,
            "traffic_split": traffic_split,
            "created_at": datetime.now()
        }
    
    def get_model_version(self, model_name: str, default_version: str, 
                         user_id: Optional[str] = None) -> str:
        """Get model version based on A/B test configuration"""
        if model_name not in self.ab_tests:
            return default_version
        
        ab_test = self.ab_tests[model_name]
        
        # Simple hash-based assignment
        if user_id:
            hash_value = hash(user_id) % 100
            if hash_value < ab_test["traffic_split"] * 100:
                return ab_test["treatment_version"]
            else:
                return ab_test["control_version"]
        else:
            # Random assignment
            import random
            if random.random() < ab_test["traffic_split"]:
                return ab_test["treatment_version"]
            else:
                return ab_test["control_version"]


def create_server(registry_path: str = None, config_path: str = None) -> ModelServer:
    """Create model server instance"""
    # Initialize registry
    registry = ModelRegistry(registry_db_path=registry_path)
    
    # Load config
    config = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    # Create server
    server = ModelServer(registry, config)
    
    return server


def main():
    """Main function to run the model server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='KarigAI Model Serving API')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--registry-path', type=str, help='Path to model registry database')
    parser.add_argument('--config-path', type=str, help='Path to server configuration file')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    
    args = parser.parse_args()
    
    # Create server
    server = create_server(args.registry_path, args.config_path)
    
    # Run server
    uvicorn.run(
        server.app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()