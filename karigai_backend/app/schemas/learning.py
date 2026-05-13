from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class LearningStep(BaseModel):
    step_number: int
    title: str
    content: str
    duration_seconds: int
    media_url: Optional[str] = None


class MicroSOPResponse(BaseModel):
    course_id: str
    title: str
    description: str
    duration_seconds: int
    language: str
    category: str
    steps: List[LearningStep]
    prerequisites: List[str]
    difficulty_level: str


class ProgressUpdateRequest(BaseModel):
    user_id: str
    course_id: str
    completion_percentage: float
    quiz_scores: Optional[Dict[str, Any]] = None
    time_spent: Optional[int] = None


class LearningProgressResponse(BaseModel):
    progress_id: str
    user_id: str
    course_id: str
    completion_percentage: float
    last_accessed: Optional[datetime] = None
    quiz_scores: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True