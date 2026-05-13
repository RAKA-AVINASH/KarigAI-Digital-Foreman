"""
Learning Module Interface and Data Models

This module provides the abstract interface for learning and recommendation systems
with support for micro-courses, progress tracking, and personalized content delivery.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class TradeType(Enum):
    """Types of trades/professions"""
    PLUMBER = "plumber"
    ELECTRICIAN = "electrician"
    CARPENTER = "carpenter"
    APPLIANCE_REPAIR = "appliance_repair"
    FARMER = "farmer"
    TEXTILE_ARTISAN = "textile_artisan"
    CONSTRUCTION = "construction"
    MOBILE_REPAIR = "mobile_repair"
    HOMESTAY_OWNER = "homestay_owner"
    GENERAL = "general"


class DifficultyLevel(Enum):
    """Difficulty levels for learning content"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class LocationInfo:
    """User location information"""
    city: str
    state: str
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class UserProfile:
    """User profile for personalized learning"""
    user_id: str
    primary_language: str
    secondary_languages: List[str]
    trade: TradeType
    location: LocationInfo
    skill_tags: List[str]
    experience_level: DifficultyLevel
    last_active: datetime
    total_courses_completed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "primary_language": self.primary_language,
            "secondary_languages": self.secondary_languages,
            "trade": self.trade.value,
            "location": {
                "city": self.location.city,
                "state": self.location.state,
                "country": self.location.country
            },
            "skill_tags": self.skill_tags,
            "experience_level": self.experience_level.value,
            "last_active": self.last_active.isoformat(),
            "total_courses_completed": self.total_courses_completed
        }


@dataclass
class LearningStep:
    """Individual step in a learning module"""
    step_number: int
    title: str
    content: str
    duration_seconds: int
    media_url: Optional[str] = None
    quiz_question: Optional[str] = None
    quiz_options: Optional[List[str]] = None
    correct_answer: Optional[int] = None


@dataclass
class MicroSOP:
    """Micro Standard Operating Procedure - 30-second learning module"""
    course_id: str
    title: str
    description: str
    duration_seconds: int
    supported_languages: List[str]
    steps: List[LearningStep]
    prerequisites: List[str]
    trade_type: TradeType
    difficulty_level: DifficultyLevel
    tags: List[str]
    location_specific: bool = False
    target_location: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def is_suitable_for_user(self, user_profile: UserProfile) -> bool:
        """Check if this course is suitable for the user"""
        # Check trade match
        if self.trade_type != TradeType.GENERAL and self.trade_type != user_profile.trade:
            return False
        
        # Check language support
        if user_profile.primary_language not in self.supported_languages:
            if not any(lang in self.supported_languages for lang in user_profile.secondary_languages):
                return False
        
        # Check location if location-specific
        if self.location_specific and self.target_location:
            if self.target_location.lower() not in user_profile.location.city.lower():
                if self.target_location.lower() not in user_profile.location.state.lower():
                    return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "course_id": self.course_id,
            "title": self.title,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "supported_languages": self.supported_languages,
            "steps": [
                {
                    "step_number": step.step_number,
                    "title": step.title,
                    "content": step.content,
                    "duration_seconds": step.duration_seconds,
                    "media_url": step.media_url,
                    "quiz_question": step.quiz_question,
                    "quiz_options": step.quiz_options,
                    "correct_answer": step.correct_answer
                }
                for step in self.steps
            ],
            "prerequisites": self.prerequisites,
            "trade_type": self.trade_type.value,
            "difficulty_level": self.difficulty_level.value,
            "tags": self.tags,
            "location_specific": self.location_specific,
            "target_location": self.target_location,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ProgressData:
    """User progress tracking data"""
    user_id: str
    course_id: str
    completion_percentage: float
    last_accessed: datetime
    quiz_scores: Dict[int, bool]  # step_number -> correct/incorrect
    time_spent_seconds: int
    completed: bool = False
    completed_at: Optional[datetime] = None
    
    def update_progress(self, step_number: int, quiz_correct: Optional[bool] = None):
        """Update progress for a step"""
        self.last_accessed = datetime.now()
        
        if quiz_correct is not None:
            self.quiz_scores[step_number] = quiz_correct
    
    def mark_completed(self):
        """Mark course as completed"""
        self.completed = True
        self.completed_at = datetime.now()
        self.completion_percentage = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "course_id": self.course_id,
            "completion_percentage": self.completion_percentage,
            "last_accessed": self.last_accessed.isoformat(),
            "quiz_scores": self.quiz_scores,
            "time_spent_seconds": self.time_spent_seconds,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class KnowledgeGap:
    """Identified knowledge gap for a user"""
    gap_id: str
    user_id: str
    topic: str
    identified_from: str  # e.g., "repeated_queries", "quiz_failures"
    severity: str  # "low", "medium", "high"
    recommended_courses: List[str]
    identified_at: datetime = None
    
    def __post_init__(self):
        if self.identified_at is None:
            self.identified_at = datetime.now()


class LearningModule(ABC):
    """Abstract base class for learning module"""
    
    @abstractmethod
    async def get_recommended_courses(
        self, 
        user_profile: UserProfile,
        limit: int = 5
    ) -> List[MicroSOP]:
        """
        Get recommended courses for a user
        
        Args:
            user_profile: User profile for personalization
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended MicroSOP courses
        """
        pass
    
    @abstractmethod
    async def get_course(
        self, 
        course_id: str, 
        language_code: str
    ) -> Optional[MicroSOP]:
        """
        Get a specific course by ID
        
        Args:
            course_id: Course identifier
            language_code: Language for content delivery
            
        Returns:
            MicroSOP course or None if not found
        """
        pass
    
    @abstractmethod
    async def track_progress(
        self, 
        user_id: str, 
        course_id: str, 
        progress_data: ProgressData
    ) -> bool:
        """
        Track user progress in a course
        
        Args:
            user_id: User identifier
            course_id: Course identifier
            progress_data: Progress information
            
        Returns:
            True if progress was tracked successfully
        """
        pass
    
    @abstractmethod
    async def get_user_progress(
        self, 
        user_id: str, 
        course_id: Optional[str] = None
    ) -> List[ProgressData]:
        """
        Get user progress for courses
        
        Args:
            user_id: User identifier
            course_id: Optional specific course ID
            
        Returns:
            List of progress data
        """
        pass
    
    @abstractmethod
    async def identify_knowledge_gaps(
        self, 
        user_id: str
    ) -> List[KnowledgeGap]:
        """
        Identify knowledge gaps for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of identified knowledge gaps
        """
        pass
    
    @abstractmethod
    async def get_offline_courses(
        self, 
        user_profile: UserProfile,
        max_courses: int = 10
    ) -> List[MicroSOP]:
        """
        Get courses suitable for offline download
        
        Args:
            user_profile: User profile
            max_courses: Maximum number of courses
            
        Returns:
            List of courses for offline use
        """
        pass
    
    @abstractmethod
    async def search_courses(
        self,
        query: str,
        user_profile: Optional[UserProfile] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MicroSOP]:
        """
        Search for courses
        
        Args:
            query: Search query
            user_profile: Optional user profile for personalization
            filters: Optional filters (trade, difficulty, etc.)
            
        Returns:
            List of matching courses
        """
        pass
