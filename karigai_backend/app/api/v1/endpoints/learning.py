from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.learning import MicroSOPResponse, LearningProgressResponse, ProgressUpdateRequest
from app.services.learning_service import MicroSOPService

router = APIRouter()


@router.get("/recommendations/{user_id}", response_model=List[MicroSOPResponse])
async def get_recommendations(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get personalized learning recommendations"""
    learning_service = MicroSOPService(db)
    
    try:
        recommendations = await learning_service.get_recommendations(user_id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/course/{course_id}", response_model=MicroSOPResponse)
async def get_course(
    course_id: str,
    language_code: str = "hi-IN",
    db: Session = Depends(get_db)
):
    """Get course content by ID"""
    learning_service = MicroSOPService(db)
    
    try:
        course = await learning_service.get_course(course_id, language_code)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        return course
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/progress", response_model=LearningProgressResponse)
async def update_progress(
    request: ProgressUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update learning progress"""
    learning_service = MicroSOPService(db)
    
    try:
        progress = await learning_service.update_progress(request)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{user_id}", response_model=List[LearningProgressResponse])
async def get_user_progress(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user's learning progress"""
    learning_service = MicroSOPService(db)
    
    try:
        progress = await learning_service.get_user_progress(user_id)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/offline/{user_id}")
async def get_offline_courses(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get courses available for offline access"""
    learning_service = MicroSOPService(db)
    
    try:
        courses = await learning_service.get_offline_courses(user_id)
        return {"offline_courses": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_course_categories():
    """Get available course categories"""
    return {
        "categories": [
            "carpentry",
            "textiles",
            "mechanics",
            "hvac",
            "hospitality",
            "agriculture"
        ]
    }