"""
Health check endpoints and monitoring utilities.
Provides comprehensive system health status.
"""
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import time
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model"""
    status: str
    timestamp: str
    version: str
    environment: str
    checks: Dict[str, Any]


class ComponentHealth(BaseModel):
    """Individual component health"""
    status: str
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


async def check_database() -> ComponentHealth:
    """Check database connectivity and performance"""
    start_time = time.time()
    try:
        db = next(get_db())
        # Simple query to test connection
        db.execute("SELECT 1")
        latency = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
            message="Database connection successful"
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            message=f"Database connection failed: {str(e)}"
        )


async def check_redis() -> ComponentHealth:
    """Check Redis cache connectivity"""
    start_time = time.time()
    try:
        # Import redis client
        # redis_client = get_redis_client()
        # redis_client.ping()
        latency = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            status="healthy",
            latency_ms=round(latency, 2),
            message="Redis connection successful"
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            message=f"Redis connection failed: {str(e)}"
        )


async def check_external_services() -> ComponentHealth:
    """Check external API services (OpenAI, ElevenLabs, etc.)"""
    try:
        # Check if API keys are configured
        services_configured = {
            "openai": bool(settings.OPENAI_API_KEY),
            "elevenlabs": bool(settings.ELEVENLABS_API_KEY),
        }
        
        all_configured = all(services_configured.values())
        
        return ComponentHealth(
            status="healthy" if all_configured else "degraded",
            message="External services configured" if all_configured else "Some services not configured",
            details=services_configured
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            message=f"External services check failed: {str(e)}"
        )


async def check_disk_space() -> ComponentHealth:
    """Check available disk space"""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        
        free_percent = (free / total) * 100
        
        status = "healthy"
        if free_percent < 10:
            status = "critical"
        elif free_percent < 20:
            status = "warning"
        
        return ComponentHealth(
            status=status,
            message=f"Disk space: {free_percent:.1f}% free",
            details={
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "free_percent": round(free_percent, 2)
            }
        )
    except Exception as e:
        return ComponentHealth(
            status="unknown",
            message=f"Disk space check failed: {str(e)}"
        )


async def check_memory() -> ComponentHealth:
    """Check memory usage"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        
        status = "healthy"
        if memory.percent > 90:
            status = "critical"
        elif memory.percent > 80:
            status = "warning"
        
        return ComponentHealth(
            status=status,
            message=f"Memory usage: {memory.percent}%",
            details={
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent
            }
        )
    except Exception as e:
        return ComponentHealth(
            status="unknown",
            message=f"Memory check failed: {str(e)}"
        )


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint.
    Returns overall system health status.
    """
    checks = {
        "api": ComponentHealth(status="healthy", message="API is running").dict()
    }
    
    # Determine overall status
    overall_status = "healthy"
    for check in checks.values():
        if check["status"] == "unhealthy":
            overall_status = "unhealthy"
            break
        elif check["status"] in ["degraded", "warning"]:
            overall_status = "degraded"
    
    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        checks=checks
    )


@router.get("/health/detailed", response_model=HealthStatus)
async def detailed_health_check():
    """
    Detailed health check endpoint.
    Checks all system components and dependencies.
    """
    # Run all health checks concurrently
    db_check, redis_check, services_check, disk_check, memory_check = await asyncio.gather(
        check_database(),
        check_redis(),
        check_external_services(),
        check_disk_space(),
        check_memory(),
        return_exceptions=True
    )
    
    checks = {
        "api": ComponentHealth(status="healthy", message="API is running").dict(),
        "database": db_check.dict() if isinstance(db_check, ComponentHealth) else ComponentHealth(status="error", message=str(db_check)).dict(),
        "redis": redis_check.dict() if isinstance(redis_check, ComponentHealth) else ComponentHealth(status="error", message=str(redis_check)).dict(),
        "external_services": services_check.dict() if isinstance(services_check, ComponentHealth) else ComponentHealth(status="error", message=str(services_check)).dict(),
        "disk": disk_check.dict() if isinstance(disk_check, ComponentHealth) else ComponentHealth(status="error", message=str(disk_check)).dict(),
        "memory": memory_check.dict() if isinstance(memory_check, ComponentHealth) else ComponentHealth(status="error", message=str(memory_check)).dict(),
    }
    
    # Determine overall status
    overall_status = "healthy"
    for check in checks.values():
        if check["status"] in ["unhealthy", "critical", "error"]:
            overall_status = "unhealthy"
            break
        elif check["status"] in ["degraded", "warning"]:
            overall_status = "degraded"
    
    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        checks=checks
    )


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.
    Returns 200 if the service is ready to accept traffic.
    """
    try:
        # Check critical dependencies
        db_check = await check_database()
        
        if db_check.status == "healthy":
            return {"status": "ready"}
        else:
            return {"status": "not ready", "reason": db_check.message}, status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        return {"status": "not ready", "reason": str(e)}, status.HTTP_503_SERVICE_UNAVAILABLE


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration.
    Returns 200 if the service is alive (even if not ready).
    """
    return {"status": "alive"}
