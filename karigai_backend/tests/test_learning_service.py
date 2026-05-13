"""
Unit tests for Learning Service

Tests the MicroSOPService implementation for micro-course content delivery.
"""

import pytest
from datetime import datetime

from app.services.learning_service import MicroSOPService
from app.core.learning_module import (
    MicroSOP,
    UserProfile,
    ProgressData,
    LearningStep,
    LocationInfo,
    TradeType,
    DifficultyLevel
)


@pytest.fixture
def learning_service():
    """Create a learning service instance"""
    return MicroSOPService()


@pytest.fixture
def sample_user_profile():
    """Create sample user profile"""
    return UserProfile(
        user_id="user123",
        primary_language="hi-IN",
        secondary_languages=["en-IN"],
        trade=TradeType.PLUMBER,
        location=LocationInfo(city="Bhopal", state="Madhya Pradesh"),
        skill_tags=["pipe_repair", "leak_fixing"],
        experience_level=DifficultyLevel.INTERMEDIATE,
        last_active=datetime.now(),
        total_courses_completed=5
    )


@pytest.fixture
def sample_courses():
    """Create sample courses"""
    return [
        MicroSOP(
            course_id="COURSE-001",
            title="Basic Pipe Repair",
            description="Learn how to repair common pipe leaks",
            duration_seconds=30,
            supported_languages=["hi-IN", "en-IN"],
            steps=[
                LearningStep(
                    step_number=1,
                    title="Introduction",
                    content="Learn the basics",
                    duration_seconds=10
                )
            ],
            prerequisites=[],
            trade_type=TradeType.PLUMBER,
            difficulty_level=DifficultyLevel.BEGINNER,
            tags=["plumbing", "repair", "pipes"]
        ),
        MicroSOP(
            course_id="COURSE-002",
            title="Advanced Welding",
            description="Advanced pipe welding techniques",
            duration_seconds=30,
            supported_languages=["hi-IN"],
            steps=[
                LearningStep(
                    step_number=1,
                    title="Welding Basics",
                    content="Advanced techniques",
                    duration_seconds=10
                )
            ],
            prerequisites=["COURSE-001"],
            trade_type=TradeType.PLUMBER,
            difficulty_level=DifficultyLevel.ADVANCED,
            tags=["plumbing", "welding", "advanced"]
        ),
        MicroSOP(
            course_id="COURSE-003",
            title="Safety Guidelines",
            description="General safety for all trades",
            duration_seconds=30,
            supported_languages=["hi-IN", "en-IN"],
            steps=[
                LearningStep(
                    step_number=1,
                    title="Safety First",
                    content="Basic safety rules",
                    duration_seconds=10
                )
            ],
            prerequisites=[],
            trade_type=TradeType.GENERAL,
            difficulty_level=DifficultyLevel.BEGINNER,
            tags=["safety", "general"]
        )
    ]


class TestMicroSOPService:
    """Test MicroSOPService class"""
    
    @pytest.mark.asyncio
    async def test_add_and_get_course(self, learning_service, sample_courses):
        """Test adding and retrieving a course"""
        course = sample_courses[0]
        learning_service.add_course(course)
        
        retrieved = await learning_service.get_course(course.course_id, "hi-IN")
        
        assert retrieved is not None
        assert retrieved.course_id == course.course_id
        assert retrieved.title == course.title
    
    @pytest.mark.asyncio
    async def test_get_course_unsupported_language(self, learning_service, sample_courses):
        """Test getting course in unsupported language"""
        course = sample_courses[0]
        learning_service.add_course(course)
        
        retrieved = await learning_service.get_course(course.course_id, "ta-IN")
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_get_course_not_found(self, learning_service):
        """Test getting non-existent course"""
        retrieved = await learning_service.get_course("NONEXISTENT", "hi-IN")
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_remove_course(self, learning_service, sample_courses):
        """Test removing a course"""
        course = sample_courses[0]
        learning_service.add_course(course)
        
        removed = learning_service.remove_course(course.course_id)
        assert removed is True
        
        retrieved = await learning_service.get_course(course.course_id, "hi-IN")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_track_progress(self, learning_service, sample_courses):
        """Test tracking user progress"""
        course = sample_courses[0]
        learning_service.add_course(course)
        
        progress = ProgressData(
            user_id="user123",
            course_id=course.course_id,
            completion_percentage=50.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True},
            time_spent_seconds=120
        )
        
        success = await learning_service.track_progress("user123", course.course_id, progress)
        
        assert success is True
        
        retrieved_progress = await learning_service.get_user_progress("user123", course.course_id)
        assert len(retrieved_progress) == 1
        assert retrieved_progress[0].completion_percentage == 50.0
    
    @pytest.mark.asyncio
    async def test_gamification_points_on_completion(self, learning_service, sample_courses):
        """Test that gamification points are awarded on course completion"""
        course = sample_courses[0]
        learning_service.add_course(course)
        
        progress = ProgressData(
            user_id="user123",
            course_id=course.course_id,
            completion_percentage=100.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True},
            time_spent_seconds=180,
            completed=True
        )
        
        await learning_service.track_progress("user123", course.course_id, progress)
        
        points = learning_service.get_user_points("user123")
        assert points == 100
    
    @pytest.mark.asyncio
    async def test_gamification_points_on_partial_completion(self, learning_service, sample_courses):
        """Test that partial points are awarded for 50%+ completion"""
        course = sample_courses[0]
        learning_service.add_course(course)
        
        progress = ProgressData(
            user_id="user123",
            course_id=course.course_id,
            completion_percentage=60.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True},
            time_spent_seconds=90
        )
        
        await learning_service.track_progress("user123", course.course_id, progress)
        
        points = learning_service.get_user_points("user123")
        assert points == 50
    
    @pytest.mark.asyncio
    async def test_identify_knowledge_gaps_from_repeated_queries(self, learning_service, sample_courses):
        """Test identifying knowledge gaps from repeated queries"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        # Record repeated queries using a topic that matches course tags
        learning_service.record_query("user123", "repair")
        learning_service.record_query("user123", "repair")
        learning_service.record_query("user123", "repair")
        
        gaps = await learning_service.identify_knowledge_gaps("user123")
        
        assert len(gaps) > 0
        assert any(gap.topic == "repair" for gap in gaps)
        assert any(gap.severity == "high" for gap in gaps)
    
    @pytest.mark.asyncio
    async def test_identify_knowledge_gaps_from_quiz_failures(self, learning_service, sample_courses):
        """Test identifying knowledge gaps from quiz failures"""
        course = sample_courses[0]
        learning_service.add_course(course)
        
        # Record progress with multiple quiz failures
        progress = ProgressData(
            user_id="user123",
            course_id=course.course_id,
            completion_percentage=80.0,
            last_accessed=datetime.now(),
            quiz_scores={1: False, 2: False, 3: True},
            time_spent_seconds=150
        )
        
        await learning_service.track_progress("user123", course.course_id, progress)
        
        gaps = await learning_service.identify_knowledge_gaps("user123")
        
        assert len(gaps) > 0
        assert any(gap.identified_from == "quiz_failures" for gap in gaps)
    
    @pytest.mark.asyncio
    async def test_get_recommended_courses(self, learning_service, sample_courses, sample_user_profile):
        """Test getting recommended courses based on user profile"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        # Record some queries to create knowledge gaps
        learning_service.record_query(sample_user_profile.user_id, "repair")
        learning_service.record_query(sample_user_profile.user_id, "repair")
        
        recommendations = await learning_service.get_recommended_courses(sample_user_profile, limit=5)
        
        assert len(recommendations) > 0
        # All recommendations should be suitable for the user
        for course in recommendations:
            assert course.is_suitable_for_user(sample_user_profile)
    
    @pytest.mark.asyncio
    async def test_get_offline_courses(self, learning_service, sample_courses, sample_user_profile):
        """Test getting courses for offline download"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        offline_courses = await learning_service.get_offline_courses(sample_user_profile, max_courses=10)
        
        assert len(offline_courses) > 0
        # All offline courses should be suitable for the user
        for course in offline_courses:
            assert course.is_suitable_for_user(sample_user_profile)
    
    @pytest.mark.asyncio
    async def test_search_courses_by_title(self, learning_service, sample_courses):
        """Test searching courses by title"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        results = await learning_service.search_courses("pipe")
        
        assert len(results) > 0
        assert any("pipe" in course.title.lower() for course in results)
    
    @pytest.mark.asyncio
    async def test_search_courses_by_tag(self, learning_service, sample_courses):
        """Test searching courses by tag"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        results = await learning_service.search_courses("safety")
        
        assert len(results) > 0
        assert any("safety" in tag.lower() for course in results for tag in course.tags)
    
    @pytest.mark.asyncio
    async def test_search_courses_with_trade_filter(self, learning_service, sample_courses):
        """Test searching courses with trade filter"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        results = await learning_service.search_courses(
            "repair",
            filters={"trade": "plumber"}
        )
        
        assert len(results) > 0
        for course in results:
            assert course.trade_type == TradeType.PLUMBER or course.trade_type == TradeType.GENERAL
    
    @pytest.mark.asyncio
    async def test_search_courses_with_difficulty_filter(self, learning_service, sample_courses):
        """Test searching courses with difficulty filter"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        results = await learning_service.search_courses(
            "plumbing",
            filters={"difficulty": "beginner"}
        )
        
        assert len(results) > 0
        for course in results:
            assert course.difficulty_level == DifficultyLevel.BEGINNER
    
    @pytest.mark.asyncio
    async def test_get_user_progress_all_courses(self, learning_service, sample_courses):
        """Test getting all user progress"""
        course1 = sample_courses[0]
        course2 = sample_courses[1]
        learning_service.add_course(course1)
        learning_service.add_course(course2)
        
        progress1 = ProgressData(
            user_id="user123",
            course_id=course1.course_id,
            completion_percentage=50.0,
            last_accessed=datetime.now(),
            quiz_scores={},
            time_spent_seconds=60
        )
        
        progress2 = ProgressData(
            user_id="user123",
            course_id=course2.course_id,
            completion_percentage=75.0,
            last_accessed=datetime.now(),
            quiz_scores={},
            time_spent_seconds=90
        )
        
        await learning_service.track_progress("user123", course1.course_id, progress1)
        await learning_service.track_progress("user123", course2.course_id, progress2)
        
        all_progress = await learning_service.get_user_progress("user123")
        
        assert len(all_progress) == 2


class TestProgressTrackingAndRecommendations:
    """Test progress tracking and recommendation engine"""
    
    @pytest.mark.asyncio
    async def test_follow_up_recommendations_based_on_prerequisites(self, learning_service, sample_courses, sample_user_profile):
        """Test that follow-up recommendations include courses with completed course as prerequisite"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        learning_service.register_user_profile(sample_user_profile)
        
        # Complete the first course
        completed_course_id = sample_courses[0].course_id
        
        # Get follow-up recommendations
        recommendations = await learning_service.get_follow_up_recommendations(
            sample_user_profile.user_id,
            completed_course_id,
            limit=3
        )
        
        # Should recommend the advanced course that has COURSE-001 as prerequisite
        assert len(recommendations) > 0
        # The advanced course (COURSE-002) has COURSE-001 as prerequisite
        assert any(course.course_id == "COURSE-002" for course in recommendations)
    
    @pytest.mark.asyncio
    async def test_follow_up_recommendations_similar_courses(self, learning_service, sample_courses, sample_user_profile):
        """Test that follow-up recommendations include similar courses"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        learning_service.register_user_profile(sample_user_profile)
        
        # Complete a course
        completed_course_id = sample_courses[0].course_id
        
        recommendations = await learning_service.get_follow_up_recommendations(
            sample_user_profile.user_id,
            completed_course_id,
            limit=3
        )
        
        # Should get some recommendations
        assert len(recommendations) > 0
        
        # All recommendations should be suitable for the user
        for course in recommendations:
            assert course.is_suitable_for_user(sample_user_profile)
    
    @pytest.mark.asyncio
    async def test_learning_analytics_empty_user(self, learning_service):
        """Test learning analytics for user with no progress"""
        analytics = await learning_service.get_learning_analytics("new_user")
        
        assert analytics["total_courses_started"] == 0
        assert analytics["total_courses_completed"] == 0
        assert analytics["completion_rate"] == 0.0
        assert analytics["total_time_spent_seconds"] == 0
        assert analytics["total_points"] == 0
    
    @pytest.mark.asyncio
    async def test_learning_analytics_with_progress(self, learning_service, sample_courses, sample_user_profile):
        """Test learning analytics with user progress"""
        for course in sample_courses:
            learning_service.add_course(course)
        
        learning_service.register_user_profile(sample_user_profile)
        
        # Add some progress
        progress1 = ProgressData(
            user_id=sample_user_profile.user_id,
            course_id=sample_courses[0].course_id,
            completion_percentage=100.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True, 2: True},
            time_spent_seconds=180,
            completed=True
        )
        
        progress2 = ProgressData(
            user_id=sample_user_profile.user_id,
            course_id=sample_courses[1].course_id,
            completion_percentage=50.0,
            last_accessed=datetime.now(),
            quiz_scores={1: False},
            time_spent_seconds=90
        )
        
        await learning_service.track_progress(sample_user_profile.user_id, sample_courses[0].course_id, progress1)
        await learning_service.track_progress(sample_user_profile.user_id, sample_courses[1].course_id, progress2)
        
        # Get analytics
        analytics = await learning_service.get_learning_analytics(sample_user_profile.user_id)
        
        assert analytics["total_courses_started"] == 2
        assert analytics["total_courses_completed"] == 1
        assert analytics["completion_rate"] == 50.0
        assert analytics["total_time_spent_seconds"] == 270
        assert analytics["total_points"] == 150  # 100 for completion + 50 for 50%
    
    @pytest.mark.asyncio
    async def test_learning_analytics_quiz_scores(self, learning_service, sample_courses, sample_user_profile):
        """Test that analytics correctly calculate average quiz scores"""
        course = sample_courses[0]
        learning_service.add_course(course)
        learning_service.register_user_profile(sample_user_profile)
        
        # Add progress with mixed quiz scores
        progress = ProgressData(
            user_id=sample_user_profile.user_id,
            course_id=course.course_id,
            completion_percentage=100.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True, 2: True, 3: False, 4: True},  # 75% correct
            time_spent_seconds=180,
            completed=True
        )
        
        await learning_service.track_progress(sample_user_profile.user_id, course.course_id, progress)
        
        analytics = await learning_service.get_learning_analytics(sample_user_profile.user_id)
        
        assert analytics["average_quiz_score"] == 75.0
    
    @pytest.mark.asyncio
    async def test_register_user_profile(self, learning_service, sample_user_profile):
        """Test registering a user profile"""
        learning_service.register_user_profile(sample_user_profile)
        
        assert sample_user_profile.user_id in learning_service.user_profiles
        assert learning_service.user_profiles[sample_user_profile.user_id] == sample_user_profile
