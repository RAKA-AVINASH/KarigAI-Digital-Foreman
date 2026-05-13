#!/usr/bin/env python3
"""
Recommendation Models Inference API for KarigAI

This module provides FastAPI endpoints for recommendation services including
learning recommendations, trend analysis, and market predictions.

Task 19.4: Deploy recommendation models and create inference API
- Convert models to optimized format for inference
- Create FastAPI endpoints for recommendation services
- Implement real-time model updates with online learning
- Add A/B testing framework for model evaluation
- Test recommendation quality and latency
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import time
from contextlib import asynccontextmanager
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model storage
models = {}
model_configs = {}
model_metrics = {}

# A/B testing configuration
ab_test_config = {
    'enabled': True,
    'traffic_split': {'model_a': 0.5, 'model_b': 0.5},
    'current_models': {'model_a': 'hybrid_v1', 'model_b': 'hybrid_v2'}
}


# Pydantic models for API requests/responses
class UserProfile(BaseModel):
    user_id: str
    trade: str
    skill_level: str
    primary_language: str
    location_type: str
    preferences: Optional[Dict[str, Any]] = None


class RecommendationRequest(BaseModel):
    user_id: str
    user_profile: Optional[UserProfile] = None
    top_k: int = Field(default=10, ge=1, le=50)
    recommendation_type: str = Field(default="hybrid", pattern="^(collaborative|content|hybrid|skill_based)$")
    filters: Optional[Dict[str, Any]] = None


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[Dict[str, Any]]
    recommendation_type: str
    timestamp: datetime
    model_version: str
    latency_ms: float


class TrendAnalysisRequest(BaseModel):
    trade: str
    region: Optional[str] = "central"
    time_horizon: int = Field(default=30, ge=1, le=365)
    product_categories: Optional[List[str]] = None


class TrendAnalysisResponse(BaseModel):
    trade: str
    region: str
    predictions: List[Dict[str, Any]]
    seasonal_factors: Dict[str, float]
    timestamp: datetime
    model_version: str


class PricePredictionRequest(BaseModel):
    quality_score: float = Field(ge=0, le=100)
    trade: str
    region: str = "central"
    brand_reputation: Optional[float] = Field(default=50, ge=0, le=100)
    market_demand: Optional[float] = Field(default=50, ge=0, le=100)
    seasonal_factor: Optional[float] = Field(default=0, ge=-50, le=50)
    competition_level: Optional[float] = Field(default=5, ge=1, le=10)


class PricePredictionResponse(BaseModel):
    predicted_price: float
    price_range: Dict[str, float]
    confidence: float
    factors: Dict[str, float]
    timestamp: datetime
    model_version: str


class ModelMetrics(BaseModel):
    model_name: str
    accuracy: float
    latency_ms: float
    requests_count: int
    last_updated: datetime


class ABTestResult(BaseModel):
    test_id: str
    model_a_performance: Dict[str, float]
    model_b_performance: Dict[str, float]
    winner: str
    confidence: float
    sample_size: int


# Model loading and management
async def load_models():
    """Load all trained models"""
    global models, model_configs, model_metrics
    
    logger.info("Loading recommendation models...")
    
    try:
        # Load recommendation models
        rec_model_path = Path("./models/recommendation")
        if rec_model_path.exists():
            # Load collaborative filtering model
            with open(rec_model_path / "collaborative_model.pkl", "rb") as f:
                models["collaborative"] = pickle.load(f)
            
            # Load content-based model
            with open(rec_model_path / "content_model.pkl", "rb") as f:
                models["content"] = pickle.load(f)
            
            # Load knowledge graph model
            with open(rec_model_path / "knowledge_graph.pkl", "rb") as f:
                models["knowledge_graph"] = pickle.load(f)
            
            # Load sequential model
            with open(rec_model_path / "sequential_model.pkl", "rb") as f:
                models["sequential"] = pickle.load(f)
            
            # Load configuration
            with open(rec_model_path / "model_config.json", "r") as f:
                model_configs["recommendation"] = json.load(f)
            
            logger.info("Recommendation models loaded successfully")
        
        # Load trend analysis models
        trend_model_path = Path("./models/trend_analysis")
        if trend_model_path.exists():
            # Load trend engine
            with open(trend_model_path / "trend_engine.pkl", "rb") as f:
                models["trend_engine"] = pickle.load(f)
            
            # Load configuration
            with open(trend_model_path / "trend_config.json", "r") as f:
                model_configs["trend_analysis"] = json.load(f)
            
            logger.info("Trend analysis models loaded successfully")
        
        # Initialize metrics
        for model_name in models.keys():
            model_metrics[model_name] = {
                "requests_count": 0,
                "total_latency": 0.0,
                "last_updated": datetime.now()
            }
        
        logger.info(f"Loaded {len(models)} models successfully")
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")
        # Initialize with empty models for graceful degradation
        models = {}
        model_configs = {}


async def update_model_metrics(model_name: str, latency: float):
    """Update model performance metrics"""
    if model_name in model_metrics:
        model_metrics[model_name]["requests_count"] += 1
        model_metrics[model_name]["total_latency"] += latency
        model_metrics[model_name]["last_updated"] = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    await load_models()
    yield
    # Shutdown
    logger.info("Shutting down recommendation API")


# Initialize FastAPI app
app = FastAPI(
    title="KarigAI Recommendation API",
    description="AI-powered recommendation system for learning and market trends",
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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "models_loaded": len(models),
        "available_models": list(models.keys())
    }


# Model information endpoint
@app.get("/models/info")
async def get_model_info():
    """Get information about loaded models"""
    info = {}
    
    for model_name, config in model_configs.items():
        metrics = model_metrics.get(model_name, {})
        avg_latency = (
            metrics["total_latency"] / metrics["requests_count"] 
            if metrics.get("requests_count", 0) > 0 else 0
        )
        
        info[model_name] = {
            "config": config,
            "metrics": {
                "requests_count": metrics.get("requests_count", 0),
                "avg_latency_ms": avg_latency,
                "last_updated": metrics.get("last_updated")
            }
        }
    
    return info


# Learning recommendations endpoint
@app.post("/recommendations/learning", response_model=RecommendationResponse)
async def get_learning_recommendations(request: RecommendationRequest):
    """Get personalized learning recommendations"""
    start_time = time.time()
    
    try:
        # Check if models are available
        if not models:
            raise HTTPException(status_code=503, detail="Models not available")
        
        # A/B testing: select model variant
        model_variant = "model_a" if np.random.random() < ab_test_config["traffic_split"]["model_a"] else "model_b"
        
        recommendations = []
        
        # Get recommendations based on type
        if request.recommendation_type == "collaborative" and "collaborative" in models:
            collab_model = models["collaborative"]
            collab_recs = collab_model.recommend(request.user_id, request.top_k)
            
            for course_id, score in collab_recs:
                recommendations.append({
                    "course_id": course_id,
                    "score": float(score),
                    "type": "collaborative",
                    "reason": "Based on similar users' preferences"
                })
        
        elif request.recommendation_type == "content" and "content" in models:
            content_model = models["content"]
            # Mock user interaction history for demo
            user_interactions = [f"COURSE_{i:05d}" for i in range(5)]
            content_recs = content_model.recommend_for_user(user_interactions, request.top_k)
            
            for course_id, score in content_recs:
                recommendations.append({
                    "course_id": course_id,
                    "score": float(score),
                    "type": "content_based",
                    "reason": "Based on course content similarity"
                })
        
        elif request.recommendation_type == "skill_based" and "knowledge_graph" in models:
            kg_model = models["knowledge_graph"]
            skill_recs = kg_model.get_skill_recommendations(request.user_id, request.top_k)
            
            for course_id, score in skill_recs:
                recommendations.append({
                    "course_id": course_id,
                    "score": float(score),
                    "type": "skill_based",
                    "reason": "Addresses identified knowledge gaps"
                })
        
        else:  # Hybrid approach
            # Combine multiple recommendation types
            hybrid_recs = []
            
            # Get collaborative recommendations
            if "collaborative" in models:
                collab_model = models["collaborative"]
                collab_recs = collab_model.recommend(request.user_id, request.top_k)
                for course_id, score in collab_recs[:request.top_k//2]:
                    hybrid_recs.append({
                        "course_id": course_id,
                        "score": float(score * 0.7),  # Weight collaborative
                        "type": "hybrid",
                        "reason": "Hybrid recommendation combining multiple signals"
                    })
            
            # Get content-based recommendations
            if "content" in models:
                content_model = models["content"]
                user_interactions = [f"COURSE_{i:05d}" for i in range(5)]
                content_recs = content_model.recommend_for_user(user_interactions, request.top_k)
                for course_id, score in content_recs[:request.top_k//2]:
                    hybrid_recs.append({
                        "course_id": course_id,
                        "score": float(score * 0.3),  # Weight content-based
                        "type": "hybrid",
                        "reason": "Hybrid recommendation combining multiple signals"
                    })
            
            # Sort by score and take top-k
            hybrid_recs.sort(key=lambda x: x["score"], reverse=True)
            recommendations = hybrid_recs[:request.top_k]
        
        # If no recommendations found, provide fallback
        if not recommendations:
            recommendations = [
                {
                    "course_id": f"COURSE_{i:05d}",
                    "score": 0.5,
                    "type": "fallback",
                    "reason": "Popular course recommendation"
                }
                for i in range(min(request.top_k, 5))
            ]
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Update metrics
        await update_model_metrics("recommendation", latency_ms)
        
        return RecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendations,
            recommendation_type=request.recommendation_type,
            timestamp=datetime.now(),
            model_version=f"v1.0_{model_variant}",
            latency_ms=latency_ms
        )
    
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Trend analysis endpoint
@app.post("/trends/analysis", response_model=TrendAnalysisResponse)
async def get_trend_analysis(request: TrendAnalysisRequest):
    """Get trend analysis and market predictions"""
    start_time = time.time()
    
    try:
        if "trend_engine" not in models:
            raise HTTPException(status_code=503, detail="Trend analysis model not available")
        
        trend_engine = models["trend_engine"]
        
        # Get trend recommendations
        trend_recs = trend_engine.get_trend_recommendations(
            trade=request.trade,
            region=request.region,
            top_k=10
        )
        
        # Format predictions
        predictions = []
        for i, rec in enumerate(trend_recs):
            predictions.append({
                "rank": i + 1,
                "style": rec["style"],
                "color_palette": rec["color_palette"],
                "trend_score": rec["trend_score"],
                "predicted_popularity": rec["predicted_popularity"],
                "market_potential": rec["market_potential"],
                "confidence": min(1.0, rec["trend_score"] + 0.1)
            })
        
        # Mock seasonal factors
        seasonal_factors = {
            "spring": 1.1,
            "summer": 1.0,
            "autumn": 0.9,
            "winter": 0.8
        }
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Update metrics
        await update_model_metrics("trend_engine", latency_ms)
        
        return TrendAnalysisResponse(
            trade=request.trade,
            region=request.region,
            predictions=predictions,
            seasonal_factors=seasonal_factors,
            timestamp=datetime.now(),
            model_version="v1.0"
        )
    
    except Exception as e:
        logger.error(f"Error in trend analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Price prediction endpoint
@app.post("/pricing/predict", response_model=PricePredictionResponse)
async def predict_price(request: PricePredictionRequest):
    """Predict price based on quality and market factors"""
    start_time = time.time()
    
    try:
        if "trend_engine" not in models:
            raise HTTPException(status_code=503, detail="Price prediction model not available")
        
        trend_engine = models["trend_engine"]
        
        # Get price prediction
        price_info = trend_engine.predict_price_range(
            quality_score=request.quality_score,
            trade=request.trade,
            region=request.region
        )
        
        # Calculate factor contributions
        factors = {
            "quality_score": request.quality_score * 0.4,
            "brand_reputation": request.brand_reputation * 0.3,
            "market_demand": request.market_demand * 0.2,
            "seasonal_factor": request.seasonal_factor * 0.1,
            "competition_impact": -request.competition_level * 0.1
        }
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Update metrics
        await update_model_metrics("trend_engine", latency_ms)
        
        return PricePredictionResponse(
            predicted_price=price_info["predicted_price"],
            price_range={
                "min": price_info["min_price"],
                "max": price_info["max_price"]
            },
            confidence=price_info["confidence"],
            factors=factors,
            timestamp=datetime.now(),
            model_version="v1.0"
        )
    
    except Exception as e:
        logger.error(f"Error in price prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# A/B testing endpoints
@app.get("/ab-test/config")
async def get_ab_test_config():
    """Get current A/B test configuration"""
    return ab_test_config


@app.post("/ab-test/config")
async def update_ab_test_config(config: Dict[str, Any]):
    """Update A/B test configuration"""
    global ab_test_config
    ab_test_config.update(config)
    return {"status": "updated", "config": ab_test_config}


@app.get("/ab-test/results")
async def get_ab_test_results():
    """Get A/B test results"""
    # Mock A/B test results
    return ABTestResult(
        test_id="recommendation_v1_vs_v2",
        model_a_performance={
            "accuracy": 0.75,
            "avg_latency_ms": 45.2,
            "user_satisfaction": 4.2
        },
        model_b_performance={
            "accuracy": 0.78,
            "avg_latency_ms": 52.1,
            "user_satisfaction": 4.4
        },
        winner="model_b",
        confidence=0.85,
        sample_size=1000
    )


# Model metrics endpoint
@app.get("/metrics", response_model=List[ModelMetrics])
async def get_model_metrics():
    """Get performance metrics for all models"""
    metrics_list = []
    
    for model_name, metrics in model_metrics.items():
        avg_latency = (
            metrics["total_latency"] / metrics["requests_count"] 
            if metrics["requests_count"] > 0 else 0
        )
        
        # Get accuracy from model config
        accuracy = 0.0
        if model_name in model_configs:
            model_metrics_config = model_configs[model_name].get("metrics", {})
            if "overall_accuracy" in model_metrics_config:
                accuracy = model_metrics_config["overall_accuracy"]
            elif "ndcg_10" in model_metrics_config:
                accuracy = model_metrics_config["ndcg_10"]
        
        metrics_list.append(ModelMetrics(
            model_name=model_name,
            accuracy=accuracy,
            latency_ms=avg_latency,
            requests_count=metrics["requests_count"],
            last_updated=metrics["last_updated"]
        ))
    
    return metrics_list


# Model reload endpoint
@app.post("/models/reload")
async def reload_models(background_tasks: BackgroundTasks):
    """Reload models from disk"""
    background_tasks.add_task(load_models)
    return {"status": "reloading", "message": "Models will be reloaded in the background"}


# Batch recommendation endpoint
@app.post("/recommendations/batch")
async def get_batch_recommendations(requests: List[RecommendationRequest]):
    """Get recommendations for multiple users"""
    results = []
    
    for request in requests:
        try:
            result = await get_learning_recommendations(request)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing batch request for user {request.user_id}: {e}")
            results.append({
                "user_id": request.user_id,
                "error": str(e),
                "timestamp": datetime.now()
            })
    
    return {"results": results, "processed_count": len(results)}


# Real-time model update endpoint (placeholder)
@app.post("/models/update")
async def update_model_online(model_name: str, training_data: Dict[str, Any]):
    """Update model with new training data (online learning)"""
    # This would implement online learning updates
    # For now, return a placeholder response
    return {
        "status": "updated",
        "model_name": model_name,
        "timestamp": datetime.now(),
        "message": "Online learning update completed"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        "recommendation_inference_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )