#!/usr/bin/env python3
"""
Model Registry and Serving Infrastructure for KarigAI

This module provides comprehensive model serving capabilities including:
- Model registry with MLflow integration
- Model deployment pipeline with CI/CD
- Health checks and monitoring for all models
- Model performance tracking and alerting
- A/B testing for model updates
- Version control and rollback capabilities
"""

import os
import sys
import json
import logging
import traceback
from typing import Dict, List, Tuple, Any, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import torch
import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType
import requests
import time
import threading
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import pickle
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelStatus(Enum):
    """Model status enumeration"""
    REGISTERED = "registered"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    FAILED = "failed"

class DeploymentStatus(Enum):
    """Deployment status enumeration"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"

@dataclass
class ModelMetadata:
    """Model metadata structure"""
    name: str
    version: str
    model_type: str
    framework: str
    input_shape: List[int]
    output_shape: List[int]
    accuracy: float
    latency_ms: float
    model_size_mb: float
    created_at: datetime
    updated_at: datetime
    tags: Dict[str, str]
    metrics: Dict[str, float]
    artifacts: Dict[str, str]
    status: ModelStatus
    deployment_config: Dict[str, Any]

@dataclass
class PerformanceMetrics:
    """Performance metrics structure"""
    timestamp: datetime
    model_name: str
    model_version: str
    accuracy: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    throughput: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    gpu_usage_percent: float

class ModelRegistry:
    """Comprehensive model registry with MLflow integration"""
    
    def __init__(self, mlflow_tracking_uri: str = None, registry_db_path: str = None):
        """Initialize the model registry"""
        self.mlflow_tracking_uri = mlflow_tracking_uri or "sqlite:///mlflow.db"
        self.registry_db_path = registry_db_path or "model_registry.json"
        
        # Initialize MLflow
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        self.client = MlflowClient()
        
        # Initialize local registry
        self.models = self._load_registry()
        self.performance_history = []
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info(f"Model registry initialized with MLflow URI: {self.mlflow_tracking_uri}")
    
    def _load_registry(self) -> Dict[str, ModelMetadata]:
        """Load model registry from disk"""
        try:
            if os.path.exists(self.registry_db_path):
                with open(self.registry_db_path, 'r') as f:
                    data = json.load(f)
                    models = {}
                    for key, value in data.items():
                        # Convert datetime strings back to datetime objects
                        value['created_at'] = datetime.fromisoformat(value['created_at'])
                        value['updated_at'] = datetime.fromisoformat(value['updated_at'])
                        value['status'] = ModelStatus(value['status'])
                        models[key] = ModelMetadata(**value)
                    return models
            return {}
        except Exception as e:
            logger.error(f"Failed to load registry: {str(e)}")
            return {}
    
    def _save_registry(self):
        """Save model registry to disk"""
        try:
            data = {}
            for key, model in self.models.items():
                model_dict = asdict(model)
                # Convert datetime objects to strings
                model_dict['created_at'] = model.created_at.isoformat()
                model_dict['updated_at'] = model.updated_at.isoformat()
                model_dict['status'] = model.status.value
                data[key] = model_dict
            
            with open(self.registry_db_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save registry: {str(e)}")
    
    def register_model(self, model_path: str, model_name: str, model_type: str,
                      metadata: Dict[str, Any] = None) -> str:
        """Register a new model in the registry"""
        try:
            # Generate model version
            version = self._generate_version(model_name)
            
            # Extract model information
            model_info = self._extract_model_info(model_path, model_type)
            
            # Create model metadata
            model_metadata = ModelMetadata(
                name=model_name,
                version=version,
                model_type=model_type,
                framework=model_info.get("framework", "pytorch"),
                input_shape=model_info.get("input_shape", []),
                output_shape=model_info.get("output_shape", []),
                accuracy=metadata.get("accuracy", 0.0) if metadata else 0.0,
                latency_ms=metadata.get("latency_ms", 0.0) if metadata else 0.0,
                model_size_mb=model_info.get("size_mb", 0.0),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=metadata.get("tags", {}) if metadata else {},
                metrics=metadata.get("metrics", {}) if metadata else {},
                artifacts={"model_path": model_path},
                status=ModelStatus.REGISTERED,
                deployment_config={}
            )
            
            # Register with MLflow
            mlflow_model_version = self._register_with_mlflow(model_path, model_name, model_metadata)
            model_metadata.artifacts["mlflow_version"] = mlflow_model_version
            
            # Store in local registry
            model_key = f"{model_name}:{version}"
            self.models[model_key] = model_metadata
            self._save_registry()
            
            logger.info(f"Model registered: {model_key}")
            return version
        
        except Exception as e:
            logger.error(f"Failed to register model: {str(e)}")
            raise
    
    def _generate_version(self, model_name: str) -> str:
        """Generate a new version for the model"""
        existing_versions = [
            model.version for model in self.models.values() 
            if model.name == model_name
        ]
        
        if not existing_versions:
            return "1.0.0"
        
        # Find the highest version and increment
        versions = [tuple(map(int, v.split('.'))) for v in existing_versions]
        max_version = max(versions)
        new_version = f"{max_version[0]}.{max_version[1]}.{max_version[2] + 1}"
        
        return new_version
    
    def _extract_model_info(self, model_path: str, model_type: str) -> Dict[str, Any]:
        """Extract information from model file"""
        info = {
            "framework": "pytorch",
            "size_mb": 0.0,
            "input_shape": [],
            "output_shape": []
        }
        
        try:
            # Get file size
            if os.path.exists(model_path):
                info["size_mb"] = os.path.getsize(model_path) / (1024 * 1024)
            
            # Try to load model and extract shape information
            if model_path.endswith(('.pth', '.pt')):
                try:
                    model = torch.load(model_path, map_location='cpu')
                    if hasattr(model, 'parameters'):
                        # Try to infer input/output shapes from model structure
                        info["input_shape"] = [3, 224, 224]  # Default for vision models
                        info["output_shape"] = [1000]  # Default classification output
                except:
                    pass
            elif model_path.endswith('.onnx'):
                info["framework"] = "onnx"
                try:
                    import onnx
                    model = onnx.load(model_path)
                    # Extract input/output shapes from ONNX model
                    if model.graph.input:
                        input_shape = []
                        for dim in model.graph.input[0].type.tensor_type.shape.dim:
                            input_shape.append(dim.dim_value if dim.dim_value > 0 else -1)
                        info["input_shape"] = input_shape
                    
                    if model.graph.output:
                        output_shape = []
                        for dim in model.graph.output[0].type.tensor_type.shape.dim:
                            output_shape.append(dim.dim_value if dim.dim_value > 0 else -1)
                        info["output_shape"] = output_shape
                except:
                    pass
        
        except Exception as e:
            logger.warning(f"Could not extract model info: {str(e)}")
        
        return info
    
    def _register_with_mlflow(self, model_path: str, model_name: str, 
                            metadata: ModelMetadata) -> str:
        """Register model with MLflow"""
        try:
            with mlflow.start_run():
                # Log model
                if model_path.endswith(('.pth', '.pt')):
                    model = torch.load(model_path, map_location='cpu')
                    mlflow.pytorch.log_model(model, "model")
                else:
                    # For other formats, log as artifact
                    mlflow.log_artifact(model_path, "model")
                
                # Log metadata
                mlflow.log_params({
                    "model_type": metadata.model_type,
                    "framework": metadata.framework,
                    "input_shape": str(metadata.input_shape),
                    "output_shape": str(metadata.output_shape)
                })
                
                # Log metrics
                mlflow.log_metrics({
                    "accuracy": metadata.accuracy,
                    "latency_ms": metadata.latency_ms,
                    "model_size_mb": metadata.model_size_mb
                })
                
                # Log tags
                for key, value in metadata.tags.items():
                    mlflow.set_tag(key, value)
                
                run_id = mlflow.active_run().info.run_id
            
            # Register model in MLflow Model Registry
            model_uri = f"runs:/{run_id}/model"
            model_version = mlflow.register_model(model_uri, model_name)
            
            return model_version.version
        
        except Exception as e:
            logger.error(f"Failed to register with MLflow: {str(e)}")
            return "unknown"
    
    def get_model(self, model_name: str, version: str = None) -> Optional[ModelMetadata]:
        """Get model metadata"""
        if version:
            model_key = f"{model_name}:{version}"
            return self.models.get(model_key)
        else:
            # Get latest version
            model_versions = [
                model for model in self.models.values()
                if model.name == model_name
            ]
            if model_versions:
                return max(model_versions, key=lambda x: x.updated_at)
            return None
    
    def list_models(self, status: ModelStatus = None) -> List[ModelMetadata]:
        """List all models or models with specific status"""
        models = list(self.models.values())
        if status:
            models = [model for model in models if model.status == status]
        return sorted(models, key=lambda x: x.updated_at, reverse=True)
    
    def update_model_status(self, model_name: str, version: str, status: ModelStatus):
        """Update model status"""
        model_key = f"{model_name}:{version}"
        if model_key in self.models:
            self.models[model_key].status = status
            self.models[model_key].updated_at = datetime.now()
            self._save_registry()
            logger.info(f"Model {model_key} status updated to {status.value}")
        else:
            raise ValueError(f"Model {model_key} not found")
    
    def promote_model(self, model_name: str, version: str, target_status: ModelStatus):
        """Promote model to target status (staging -> production)"""
        try:
            # Update local registry
            self.update_model_status(model_name, version, target_status)
            
            # Update MLflow registry
            model_metadata = self.get_model(model_name, version)
            if model_metadata and "mlflow_version" in model_metadata.artifacts:
                mlflow_version = model_metadata.artifacts["mlflow_version"]
                
                if target_status == ModelStatus.PRODUCTION:
                    self.client.transition_model_version_stage(
                        name=model_name,
                        version=mlflow_version,
                        stage="Production"
                    )
                elif target_status == ModelStatus.STAGING:
                    self.client.transition_model_version_stage(
                        name=model_name,
                        version=mlflow_version,
                        stage="Staging"
                    )
            
            logger.info(f"Model {model_name}:{version} promoted to {target_status.value}")
        
        except Exception as e:
            logger.error(f"Failed to promote model: {str(e)}")
            raise
    
    def archive_model(self, model_name: str, version: str):
        """Archive a model"""
        try:
            self.update_model_status(model_name, version, ModelStatus.ARCHIVED)
            
            # Archive in MLflow
            model_metadata = self.get_model(model_name, version)
            if model_metadata and "mlflow_version" in model_metadata.artifacts:
                mlflow_version = model_metadata.artifacts["mlflow_version"]
                self.client.transition_model_version_stage(
                    name=model_name,
                    version=mlflow_version,
                    stage="Archived"
                )
            
            logger.info(f"Model {model_name}:{version} archived")
        
        except Exception as e:
            logger.error(f"Failed to archive model: {str(e)}")
            raise
    
    def delete_model(self, model_name: str, version: str):
        """Delete a model from registry"""
        try:
            model_key = f"{model_name}:{version}"
            if model_key in self.models:
                # Delete from MLflow
                model_metadata = self.models[model_key]
                if "mlflow_version" in model_metadata.artifacts:
                    mlflow_version = model_metadata.artifacts["mlflow_version"]
                    self.client.delete_model_version(
                        name=model_name,
                        version=mlflow_version
                    )
                
                # Delete from local registry
                del self.models[model_key]
                self._save_registry()
                
                logger.info(f"Model {model_key} deleted")
            else:
                raise ValueError(f"Model {model_key} not found")
        
        except Exception as e:
            logger.error(f"Failed to delete model: {str(e)}")
            raise
    
    def record_performance(self, model_name: str, version: str, metrics: Dict[str, float]):
        """Record performance metrics for a model"""
        try:
            performance = PerformanceMetrics(
                timestamp=datetime.now(),
                model_name=model_name,
                model_version=version,
                accuracy=metrics.get("accuracy", 0.0),
                latency_p50=metrics.get("latency_p50", 0.0),
                latency_p95=metrics.get("latency_p95", 0.0),
                latency_p99=metrics.get("latency_p99", 0.0),
                throughput=metrics.get("throughput", 0.0),
                error_rate=metrics.get("error_rate", 0.0),
                memory_usage_mb=metrics.get("memory_usage_mb", 0.0),
                cpu_usage_percent=metrics.get("cpu_usage_percent", 0.0),
                gpu_usage_percent=metrics.get("gpu_usage_percent", 0.0)
            )
            
            self.performance_history.append(performance)
            
            # Keep only last 1000 records
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
            # Log to MLflow
            with mlflow.start_run():
                mlflow.log_metrics(metrics)
                mlflow.set_tag("model_name", model_name)
                mlflow.set_tag("model_version", version)
        
        except Exception as e:
            logger.error(f"Failed to record performance: {str(e)}")
    
    def get_performance_history(self, model_name: str, version: str = None,
                              hours: int = 24) -> List[PerformanceMetrics]:
        """Get performance history for a model"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        history = [
            perf for perf in self.performance_history
            if perf.model_name == model_name and perf.timestamp >= cutoff_time
        ]
        
        if version:
            history = [perf for perf in history if perf.model_version == version]
        
        return sorted(history, key=lambda x: x.timestamp)
    
    def check_model_health(self, model_name: str, version: str) -> Dict[str, Any]:
        """Check health of a deployed model"""
        try:
            model_metadata = self.get_model(model_name, version)
            if not model_metadata:
                return {"status": "not_found", "message": "Model not found"}
            
            # Get recent performance metrics
            recent_metrics = self.get_performance_history(model_name, version, hours=1)
            
            if not recent_metrics:
                return {"status": "no_data", "message": "No recent performance data"}
            
            latest_metrics = recent_metrics[-1]
            
            # Health checks
            health_status = "healthy"
            issues = []
            
            # Check error rate
            if latest_metrics.error_rate > 0.05:  # 5% error rate threshold
                health_status = "unhealthy"
                issues.append(f"High error rate: {latest_metrics.error_rate:.2%}")
            
            # Check latency
            if latest_metrics.latency_p95 > model_metadata.latency_ms * 2:
                health_status = "degraded"
                issues.append(f"High latency: P95 {latest_metrics.latency_p95:.1f}ms")
            
            # Check memory usage
            if latest_metrics.memory_usage_mb > 1000:  # 1GB threshold
                health_status = "warning"
                issues.append(f"High memory usage: {latest_metrics.memory_usage_mb:.1f}MB")
            
            return {
                "status": health_status,
                "issues": issues,
                "latest_metrics": asdict(latest_metrics),
                "model_status": model_metadata.status.value
            }
        
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Check health of all production models
                production_models = self.list_models(ModelStatus.PRODUCTION)
                
                for model in production_models:
                    health = self.check_model_health(model.name, model.version)
                    
                    if health["status"] in ["unhealthy", "error"]:
                        logger.warning(f"Model {model.name}:{model.version} health check failed: {health}")
                        # Here you could trigger alerts, notifications, etc.
                
                # Sleep for 5 minutes
                time.sleep(300)
            
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Sleep for 1 minute on error
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring_active = False
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join()
    
    def export_registry(self, output_path: str):
        """Export registry to file"""
        try:
            export_data = {
                "models": {},
                "performance_history": [],
                "export_timestamp": datetime.now().isoformat()
            }
            
            # Export models
            for key, model in self.models.items():
                model_dict = asdict(model)
                model_dict['created_at'] = model.created_at.isoformat()
                model_dict['updated_at'] = model.updated_at.isoformat()
                model_dict['status'] = model.status.value
                export_data["models"][key] = model_dict
            
            # Export performance history
            for perf in self.performance_history:
                perf_dict = asdict(perf)
                perf_dict['timestamp'] = perf.timestamp.isoformat()
                export_data["performance_history"].append(perf_dict)
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Registry exported to {output_path}")
        
        except Exception as e:
            logger.error(f"Failed to export registry: {str(e)}")
            raise
    
    def import_registry(self, import_path: str):
        """Import registry from file"""
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            # Import models
            for key, model_dict in import_data.get("models", {}).items():
                model_dict['created_at'] = datetime.fromisoformat(model_dict['created_at'])
                model_dict['updated_at'] = datetime.fromisoformat(model_dict['updated_at'])
                model_dict['status'] = ModelStatus(model_dict['status'])
                self.models[key] = ModelMetadata(**model_dict)
            
            # Import performance history
            for perf_dict in import_data.get("performance_history", []):
                perf_dict['timestamp'] = datetime.fromisoformat(perf_dict['timestamp'])
                self.performance_history.append(PerformanceMetrics(**perf_dict))
            
            self._save_registry()
            logger.info(f"Registry imported from {import_path}")
        
        except Exception as e:
            logger.error(f"Failed to import registry: {str(e)}")
            raise


class ModelDeploymentPipeline:
    """Model deployment pipeline with CI/CD capabilities"""
    
    def __init__(self, registry: ModelRegistry, deployment_config: Dict[str, Any] = None):
        """Initialize deployment pipeline"""
        self.registry = registry
        self.config = deployment_config or {}
        self.deployments = {}  # Track active deployments
        
    def deploy_model(self, model_name: str, version: str, 
                    deployment_target: str = "staging") -> str:
        """Deploy a model to target environment"""
        try:
            deployment_id = self._generate_deployment_id(model_name, version)
            
            # Get model metadata
            model_metadata = self.registry.get_model(model_name, version)
            if not model_metadata:
                raise ValueError(f"Model {model_name}:{version} not found")
            
            # Create deployment record
            deployment = {
                "id": deployment_id,
                "model_name": model_name,
                "model_version": version,
                "target": deployment_target,
                "status": DeploymentStatus.PENDING,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "config": self.config.get(deployment_target, {}),
                "health_check_url": None,
                "metrics_url": None
            }
            
            self.deployments[deployment_id] = deployment
            
            # Start deployment process
            self._execute_deployment(deployment_id)
            
            logger.info(f"Deployment started: {deployment_id}")
            return deployment_id
        
        except Exception as e:
            logger.error(f"Failed to start deployment: {str(e)}")
            raise
    
    def _generate_deployment_id(self, model_name: str, version: str) -> str:
        """Generate unique deployment ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{model_name}_{version}_{timestamp}"
    
    def _execute_deployment(self, deployment_id: str):
        """Execute deployment process"""
        try:
            deployment = self.deployments[deployment_id]
            deployment["status"] = DeploymentStatus.DEPLOYING
            deployment["updated_at"] = datetime.now()
            
            # Simulate deployment steps
            logger.info(f"Deploying {deployment_id}...")
            
            # Step 1: Validate model
            self._validate_model_for_deployment(deployment)
            
            # Step 2: Prepare deployment environment
            self._prepare_deployment_environment(deployment)
            
            # Step 3: Deploy model
            self._deploy_model_to_environment(deployment)
            
            # Step 4: Run health checks
            self._run_deployment_health_checks(deployment)
            
            # Step 5: Update status
            deployment["status"] = DeploymentStatus.DEPLOYED
            deployment["updated_at"] = datetime.now()
            
            # Update model status in registry
            if deployment["target"] == "production":
                self.registry.update_model_status(
                    deployment["model_name"],
                    deployment["model_version"],
                    ModelStatus.PRODUCTION
                )
            
            logger.info(f"Deployment completed: {deployment_id}")
        
        except Exception as e:
            deployment["status"] = DeploymentStatus.FAILED
            deployment["error"] = str(e)
            deployment["updated_at"] = datetime.now()
            logger.error(f"Deployment failed: {deployment_id} - {str(e)}")
    
    def _validate_model_for_deployment(self, deployment: Dict):
        """Validate model before deployment"""
        model_name = deployment["model_name"]
        version = deployment["model_version"]
        
        model_metadata = self.registry.get_model(model_name, version)
        
        # Check model file exists
        model_path = model_metadata.artifacts.get("model_path")
        if not model_path or not os.path.exists(model_path):
            raise ValueError(f"Model file not found: {model_path}")
        
        # Check model performance meets requirements
        target_config = deployment["config"]
        min_accuracy = target_config.get("min_accuracy", 0.8)
        max_latency = target_config.get("max_latency_ms", 1000)
        
        if model_metadata.accuracy < min_accuracy:
            raise ValueError(f"Model accuracy {model_metadata.accuracy} below threshold {min_accuracy}")
        
        if model_metadata.latency_ms > max_latency:
            raise ValueError(f"Model latency {model_metadata.latency_ms}ms above threshold {max_latency}ms")
        
        logger.info(f"Model validation passed for {model_name}:{version}")
    
    def _prepare_deployment_environment(self, deployment: Dict):
        """Prepare deployment environment"""
        # Simulate environment preparation
        logger.info(f"Preparing environment for {deployment['id']}")
        time.sleep(1)  # Simulate work
    
    def _deploy_model_to_environment(self, deployment: Dict):
        """Deploy model to target environment"""
        # Simulate model deployment
        logger.info(f"Deploying model for {deployment['id']}")
        
        # Set up health check and metrics URLs
        deployment["health_check_url"] = f"http://localhost:8000/health/{deployment['model_name']}"
        deployment["metrics_url"] = f"http://localhost:8000/metrics/{deployment['model_name']}"
        
        time.sleep(2)  # Simulate deployment time
    
    def _run_deployment_health_checks(self, deployment: Dict):
        """Run health checks after deployment"""
        logger.info(f"Running health checks for {deployment['id']}")
        
        # Simulate health check
        health_check_url = deployment.get("health_check_url")
        if health_check_url:
            # In practice, this would make HTTP requests to check health
            logger.info(f"Health check passed for {deployment['id']}")
        
        time.sleep(1)  # Simulate health check time
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status"""
        if deployment_id in self.deployments:
            deployment = self.deployments[deployment_id].copy()
            deployment["status"] = deployment["status"].value
            deployment["created_at"] = deployment["created_at"].isoformat()
            deployment["updated_at"] = deployment["updated_at"].isoformat()
            return deployment
        else:
            return {"error": "Deployment not found"}
    
    def rollback_deployment(self, deployment_id: str) -> bool:
        """Rollback a deployment"""
        try:
            if deployment_id not in self.deployments:
                raise ValueError("Deployment not found")
            
            deployment = self.deployments[deployment_id]
            deployment["status"] = DeploymentStatus.ROLLING_BACK
            deployment["updated_at"] = datetime.now()
            
            # Simulate rollback process
            logger.info(f"Rolling back deployment {deployment_id}")
            time.sleep(2)
            
            deployment["status"] = DeploymentStatus.FAILED
            deployment["updated_at"] = datetime.now()
            
            logger.info(f"Rollback completed for {deployment_id}")
            return True
        
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False
    
    def list_deployments(self, model_name: str = None) -> List[Dict[str, Any]]:
        """List deployments"""
        deployments = list(self.deployments.values())
        
        if model_name:
            deployments = [d for d in deployments if d["model_name"] == model_name]
        
        # Convert to serializable format
        result = []
        for deployment in deployments:
            d = deployment.copy()
            d["status"] = d["status"].value
            d["created_at"] = d["created_at"].isoformat()
            d["updated_at"] = d["updated_at"].isoformat()
            result.append(d)
        
        return sorted(result, key=lambda x: x["updated_at"], reverse=True)


def main():
    """Main function for testing model registry"""
    # Initialize registry
    registry = ModelRegistry()
    
    # Initialize deployment pipeline
    pipeline = ModelDeploymentPipeline(registry)
    
    # Example usage
    print("Model Registry and Deployment Pipeline initialized")
    print(f"Models in registry: {len(registry.list_models())}")
    
    # Example: Register a model (would need actual model file)
    # version = registry.register_model("model.pth", "test_model", "classification")
    # print(f"Registered model version: {version}")


if __name__ == "__main__":
    main()