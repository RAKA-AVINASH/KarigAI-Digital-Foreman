"""
Unit tests for Learning Module Interface and Data Models

Tests the learning module interface, data models, and core functionality.
"""

import pytest
from datetime import datetime

from app.core.learning_module import (
    LearningModule,
    MicroSOP,
    UserProfile,
    ProgressData,
    LearningStep,
    KnowledgeGap,
    LocationInfo,
    TradeType,
    DifficultyLevel
)


@pytest.fixture
def sample_location():
    """Create sample location"""
    return LocationInfo(
        city="Bhopal",
        state="Madhya Pradesh",
        country="India"
    )


@pytest.fixture
def sample_user_profile(sample_location):
    """Create sample user profile"""
    return UserProfile(
        user_id="user123",
        primary_language="hi-IN",
        secondary_languages=["en-IN"],
        trade=TradeType.PLUMBER,
        location=sample_location,
        skill_tags=["pipe_repair", "leak_fixing"],
        experience_level=DifficultyLevel.INTERMEDIATE,
        last_active=datetime.now(),
        total_courses_completed=5
    )


@pytest.fixture
def sample_learning_steps():
    """Create sample learning steps"""
    return [
        LearningStep(
            step_number=1,
            title="Introduction",
            content="Learn the basics of pipe repair",
            duration_seconds=10,
            media_url="https://example.com/video1.mp4"
        ),
        LearningStep(
            step_number=2,
            title="Tools Required",
            content="Gather necessary tools",
            duration_seconds=10,
            quiz_question="Which tool is used for cutting pipes?",
            quiz_options=["Hammer", "Pipe cutter", "Screwdriver"],
            correct_answer=1
        ),
        LearningStep(
            step_number=3,
            title="Repair Process",
            content="Step-by-step repair instructions",
            duration_seconds=10
        )
    ]


@pytest.fixture
def sample_micro_sop(sample_learning_steps):
    """Create sample Micro-SOP"""
    return MicroSOP(
        course_id="COURSE-001",
        title="Basic Pipe Repair",
        description="Learn how to repair common pipe leaks",
        duration_seconds=30,
        supported_languages=["hi-IN", "en-IN"],
        steps=sample_learning_steps,
        prerequisites=[],
        trade_type=TradeType.PLUMBER,
        difficulty_level=DifficultyLevel.BEGINNER,
        tags=["plumbing", "repair", "pipes"]
    )


class TestLocationInfo:
    """Test LocationInfo data model"""
    
    def test_location_creation(self):
        """Test creating location info"""
        location = LocationInfo(
            city="Jaipur",
            state="Rajasthan",
            country="India",
            latitude=26.9124,
            longitude=75.7873
        )
        
        assert location.city == "Jaipur"
        assert location.state == "Rajasthan"
        assert location.latitude == 26.9124


class TestUserProfile:
    """Test UserProfile data model"""
    
    def test_user_profile_creation(self, sample_user_profile):
        """Test creating user profile"""
        assert sample_user_profile.user_id == "user123"
        assert sample_user_profile.trade == TradeType.PLUMBER
        assert sample_user_profile.experience_level == DifficultyLevel.INTERMEDIATE
    
    def test_user_profile_to_dict(self, sample_user_profile):
        """Test converting user profile to dictionary"""
        profile_dict = sample_user_profile.to_dict()
        
        assert profile_dict["user_id"] == "user123"
        assert profile_dict["trade"] == "plumber"
        assert profile_dict["location"]["city"] == "Bhopal"
        assert "skill_tags" in profile_dict


class TestLearningStep:
    """Test LearningStep data model"""
    
    def test_learning_step_creation(self):
        """Test creating a learning step"""
        step = LearningStep(
            step_number=1,
            title="Test Step",
            content="Test content",
            duration_seconds=15
        )
        
        assert step.step_number == 1
        assert step.title == "Test Step"
        assert step.duration_seconds == 15
    
    def test_learning_step_with_quiz(self):
        """Test learning step with quiz"""
        step = LearningStep(
            step_number=2,
            title="Quiz Step",
            content="Test your knowledge",
            duration_seconds=10,
            quiz_question="What is 2+2?",
            quiz_options=["3", "4", "5"],
            correct_answer=1
        )
        
        assert step.quiz_question is not None
        assert len(step.quiz_options) == 3
        assert step.correct_answer == 1


class TestMicroSOP:
    """Test MicroSOP data model"""
    
    def test_micro_sop_creation(self, sample_micro_sop):
        """Test creating a Micro-SOP"""
        assert sample_micro_sop.course_id == "COURSE-001"
        assert sample_micro_sop.duration_seconds == 30
        assert len(sample_micro_sop.steps) == 3
        assert sample_micro_sop.trade_type == TradeType.PLUMBER
    
    def test_micro_sop_to_dict(self, sample_micro_sop):
        """Test converting Micro-SOP to dictionary"""
        sop_dict = sample_micro_sop.to_dict()
        
        assert sop_dict["course_id"] == "COURSE-001"
        assert sop_dict["trade_type"] == "plumber"
        assert len(sop_dict["steps"]) == 3
        assert "created_at" in sop_dict
    
    def test_is_suitable_for_user_matching_trade(self, sample_micro_sop, sample_user_profile):
        """Test suitability check with matching trade"""
        assert sample_micro_sop.is_suitable_for_user(sample_user_profile) is True
    
    def test_is_suitable_for_user_different_trade(self, sample_user_profile):
        """Test suitability check with different trade"""
        electrician_course = MicroSOP(
            course_id="COURSE-002",
            title="Electrical Wiring",
            description="Learn electrical wiring",
            duration_seconds=30,
            supported_languages=["hi-IN"],
            steps=[],
            prerequisites=[],
            trade_type=TradeType.ELECTRICIAN,
            difficulty_level=DifficultyLevel.BEGINNER,
            tags=["electrical"]
        )
        
        assert electrician_course.is_suitable_for_user(sample_user_profile) is False
    
    def test_is_suitable_for_user_general_trade(self, sample_user_profile):
        """Test suitability check with general trade"""
        general_course = MicroSOP(
            course_id="COURSE-003",
            title="Safety Basics",
            description="General safety guidelines",
            duration_seconds=30,
            supported_languages=["hi-IN"],
            steps=[],
            prerequisites=[],
            trade_type=TradeType.GENERAL,
            difficulty_level=DifficultyLevel.BEGINNER,
            tags=["safety"]
        )
        
        assert general_course.is_suitable_for_user(sample_user_profile) is True
    
    def test_is_suitable_for_user_language_mismatch(self, sample_user_profile):
        """Test suitability check with unsupported language"""
        tamil_course = MicroSOP(
            course_id="COURSE-004",
            title="Plumbing Basics",
            description="Basic plumbing",
            duration_seconds=30,
            supported_languages=["ta-IN"],  # Tamil only
            steps=[],
            prerequisites=[],
            trade_type=TradeType.PLUMBER,
            difficulty_level=DifficultyLevel.BEGINNER,
            tags=["plumbing"]
        )
        
        assert tamil_course.is_suitable_for_user(sample_user_profile) is False


class TestProgressData:
    """Test ProgressData model"""
    
    def test_progress_data_creation(self):
        """Test creating progress data"""
        progress = ProgressData(
            user_id="user123",
            course_id="COURSE-001",
            completion_percentage=50.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True, 2: False},
            time_spent_seconds=120
        )
        
        assert progress.user_id == "user123"
        assert progress.completion_percentage == 50.0
        assert progress.completed is False
    
    def test_update_progress(self):
        """Test updating progress"""
        progress = ProgressData(
            user_id="user123",
            course_id="COURSE-001",
            completion_percentage=30.0,
            last_accessed=datetime.now(),
            quiz_scores={},
            time_spent_seconds=60
        )
        
        progress.update_progress(step_number=1, quiz_correct=True)
        
        assert 1 in progress.quiz_scores
        assert progress.quiz_scores[1] is True
    
    def test_mark_completed(self):
        """Test marking course as completed"""
        progress = ProgressData(
            user_id="user123",
            course_id="COURSE-001",
            completion_percentage=90.0,
            last_accessed=datetime.now(),
            quiz_scores={},
            time_spent_seconds=180
        )
        
        progress.mark_completed()
        
        assert progress.completed is True
        assert progress.completion_percentage == 100.0
        assert progress.completed_at is not None
    
    def test_progress_to_dict(self):
        """Test converting progress to dictionary"""
        progress = ProgressData(
            user_id="user123",
            course_id="COURSE-001",
            completion_percentage=75.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True},
            time_spent_seconds=150
        )
        
        progress_dict = progress.to_dict()
        
        assert progress_dict["user_id"] == "user123"
        assert progress_dict["completion_percentage"] == 75.0
        assert "last_accessed" in progress_dict


class TestKnowledgeGap:
    """Test KnowledgeGap model"""
    
    def test_knowledge_gap_creation(self):
        """Test creating knowledge gap"""
        gap = KnowledgeGap(
            gap_id="GAP-001",
            user_id="user123",
            topic="Advanced Pipe Welding",
            identified_from="repeated_queries",
            severity="high",
            recommended_courses=["COURSE-005", "COURSE-006"]
        )
        
        assert gap.gap_id == "GAP-001"
        assert gap.severity == "high"
        assert len(gap.recommended_courses) == 2
        assert gap.identified_at is not None
