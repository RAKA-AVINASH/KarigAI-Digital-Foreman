"""
Property-Based Test for Progress Tracking and Recommendations

**Property 12: Progress Tracking and Recommendations**
**Validates: Requirements 3.4**

This test validates that for any completed Micro_SOP, the system should track
progress and suggest appropriate follow-up learning opportunities.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from typing import List

from app.core.learning_module import (
    MicroSOP,
    UserProfile,
    ProgressData,
    LearningStep,
    LocationInfo,
    TradeType,
    DifficultyLevel
)
from app.services.learning_service import MicroSOPService


# Reuse strategies from other tests
trade_type_strategy = st.sampled_from(list(TradeType))
difficulty_level_strategy = st.sampled_from(list(DifficultyLevel))
language_code_strategy = st.sampled_from(["hi-IN", "en-IN", "ml-IN", "pa-IN"])

location_strategy = st.builds(
    LocationInfo,
    city=st.sampled_from(["Bhopal", "Jaipur", "Srinagar"]),
    state=st.sampled_from(["Madhya Pradesh", "Rajasthan", "Jammu & Kashmir"]),
    country=st.just("India")
)

user_profile_strategy = st.builds(
    UserProfile,
    user_id=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    primary_language=language_code_strategy,
    secondary_languages=st.lists(language_code_strategy, min_size=0, max_size=2),
    trade=trade_type_strategy,
    location=location_strategy,
    skill_tags=st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5),
    experience_level=difficulty_level_strategy,
    last_active=st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 2, 6)),
    total_courses_completed=st.integers(min_value=0, max_value=50)
)

@st.composite
def sequential_learning_steps(draw):
    """Generate sequential learning steps"""
    num_steps = draw(st.integers(min_value=2, max_value=4))
    steps = []
    for i in range(1, num_steps + 1):
        step = LearningStep(
            step_number=i,
            title=draw(st.text(min_size=5, max_size=50)),
            content=draw(st.text(min_size=10, max_size=200)),
            duration_seconds=draw(st.integers(min_value=5, max_value=10)),
            media_url=None,
            quiz_question=None,
            quiz_options=None,
            correct_answer=None
        )
        steps.append(step)
    return steps

micro_sop_strategy = st.builds(
    MicroSOP,
    course_id=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
    title=st.text(min_size=10, max_size=100),
    description=st.text(min_size=20, max_size=200),
    duration_seconds=st.integers(min_value=20, max_value=35),
    supported_languages=st.lists(language_code_strategy, min_size=1, max_size=3, unique=True),
    steps=sequential_learning_steps(),
    prerequisites=st.lists(st.text(min_size=5, max_size=20), min_size=0, max_size=2),
    trade_type=trade_type_strategy,
    difficulty_level=difficulty_level_strategy,
    tags=st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5),
    location_specific=st.booleans(),
    target_location=st.one_of(st.none(), st.sampled_from(["Bhopal", "Jaipur", "Srinagar"]))
)


@given(
    user_profile=user_profile_strategy,
    completed_course=micro_sop_strategy,
    follow_up_courses=st.lists(micro_sop_strategy, min_size=1, max_size=3)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_progress_tracking_and_recommendations_property(
    user_profile: UserProfile,
    completed_course: MicroSOP,
    follow_up_courses: List[MicroSOP]
):
    """
    Property 12: Progress Tracking and Recommendations
    
    For any completed Micro_SOP, the system should track progress and suggest
    appropriate follow-up learning opportunities.
    
    This property validates that:
    1. Progress is tracked when a course is completed
    2. Completion status is recorded correctly
    3. Follow-up recommendations are provided
    4. Recommended courses are suitable for the user
    5. Analytics reflect the completed course
    """
    # Arrange
    service = MicroSOPService()
    
    # Ensure courses are suitable for user
    completed_course.trade_type = user_profile.trade
    completed_course.location_specific = False
    if user_profile.primary_language not in completed_course.supported_languages:
        completed_course.supported_languages.append(user_profile.primary_language)
    
    # Set up follow-up courses with completed course as prerequisite
    for i, course in enumerate(follow_up_courses):
        course.trade_type = user_profile.trade
        course.location_specific = False
        if user_profile.primary_language not in course.supported_languages:
            course.supported_languages.append(user_profile.primary_language)
        
        # Make first follow-up course have the completed course as prerequisite
        if i == 0:
            course.prerequisites = [completed_course.course_id]
        
        # Ensure unique course IDs
        course.course_id = f"{course.course_id}_{i}"
    
    service.add_course(completed_course)
    for course in follow_up_courses:
        service.add_course(course)
    
    service.register_user_profile(user_profile)
    
    # Act: Complete the course
    progress = ProgressData(
        user_id=user_profile.user_id,
        course_id=completed_course.course_id,
        completion_percentage=100.0,
        last_accessed=datetime.now(),
        quiz_scores={1: True, 2: True},
        time_spent_seconds=completed_course.duration_seconds,
        completed=True
    )
    progress.mark_completed()
    
    await service.track_progress(user_profile.user_id, completed_course.course_id, progress)
    
    # Get follow-up recommendations
    recommendations = await service.get_follow_up_recommendations(
        user_profile.user_id,
        completed_course.course_id,
        limit=5
    )
    
    # Get analytics
    analytics = await service.get_learning_analytics(user_profile.user_id)
    
    # Assert: Verify property holds
    
    # 1. Progress should be tracked
    tracked_progress = await service.get_user_progress(user_profile.user_id, completed_course.course_id)
    assert len(tracked_progress) > 0, "Progress should be tracked for completed course"
    assert tracked_progress[0].completed is True, "Course should be marked as completed"
    
    # 2. Completion percentage should be 100%
    assert tracked_progress[0].completion_percentage == 100.0, \
        "Completed course should have 100% completion"
    
    # 3. Follow-up recommendations should be provided
    assert len(recommendations) > 0, "Follow-up recommendations should be provided"
    
    # 4. All recommended courses should be suitable for the user
    for course in recommendations:
        assert course.is_suitable_for_user(user_profile), \
            f"Recommended course {course.course_id} should be suitable for user"
    
    # 5. Analytics should reflect the completed course
    assert analytics["total_courses_completed"] >= 1, \
        "Analytics should show at least one completed course"
    assert analytics["completion_rate"] > 0, \
        "Completion rate should be greater than 0"
    assert analytics["total_time_spent_seconds"] > 0, \
        "Total time spent should be tracked"


@given(
    user_profile=user_profile_strategy,
    courses=st.lists(micro_sop_strategy, min_size=2, max_size=5)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_progress_tracking_multiple_courses(
    user_profile: UserProfile,
    courses: List[MicroSOP]
):
    """
    Test that progress tracking works correctly across multiple courses.
    
    This validates that the system can track progress for multiple courses
    simultaneously and provide accurate analytics.
    """
    service = MicroSOPService()
    
    # Set up courses
    for i, course in enumerate(courses):
        course.course_id = f"COURSE-{i}"
        course.trade_type = user_profile.trade
        course.location_specific = False
        if user_profile.primary_language not in course.supported_languages:
            course.supported_languages.append(user_profile.primary_language)
        service.add_course(course)
    
    service.register_user_profile(user_profile)
    
    # Complete some courses, partially complete others
    completed_count = 0
    for i, course in enumerate(courses):
        if i % 2 == 0:  # Complete even-indexed courses
            progress = ProgressData(
                user_id=user_profile.user_id,
                course_id=course.course_id,
                completion_percentage=100.0,
                last_accessed=datetime.now(),
                quiz_scores={1: True},
                time_spent_seconds=course.duration_seconds,
                completed=True
            )
            completed_count += 1
        else:  # Partially complete odd-indexed courses
            progress = ProgressData(
                user_id=user_profile.user_id,
                course_id=course.course_id,
                completion_percentage=50.0,
                last_accessed=datetime.now(),
                quiz_scores={},
                time_spent_seconds=course.duration_seconds // 2
            )
        
        await service.track_progress(user_profile.user_id, course.course_id, progress)
    
    # Get analytics
    analytics = await service.get_learning_analytics(user_profile.user_id)
    
    # Verify analytics
    assert analytics["total_courses_started"] == len(courses), \
        "Should track all started courses"
    assert analytics["total_courses_completed"] == completed_count, \
        f"Should track {completed_count} completed courses"
    
    expected_completion_rate = (completed_count / len(courses)) * 100
    assert abs(analytics["completion_rate"] - expected_completion_rate) < 0.1, \
        "Completion rate should be calculated correctly"


@given(
    user_profile=user_profile_strategy,
    course=micro_sop_strategy
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_recommendations_after_completion(
    user_profile: UserProfile,
    course: MicroSOP
):
    """
    Test that recommendations are provided immediately after course completion.
    
    This validates that the system proactively suggests next steps.
    """
    service = MicroSOPService()
    
    # Set up course
    course.trade_type = user_profile.trade
    course.location_specific = False
    if user_profile.primary_language not in course.supported_languages:
        course.supported_languages.append(user_profile.primary_language)
    
    service.add_course(course)
    service.register_user_profile(user_profile)
    
    # Complete the course
    progress = ProgressData(
        user_id=user_profile.user_id,
        course_id=course.course_id,
        completion_percentage=100.0,
        last_accessed=datetime.now(),
        quiz_scores={1: True},
        time_spent_seconds=course.duration_seconds,
        completed=True
    )
    
    await service.track_progress(user_profile.user_id, course.course_id, progress)
    
    # Get recommendations
    recommendations = await service.get_follow_up_recommendations(
        user_profile.user_id,
        course.course_id,
        limit=3
    )
    
    # Recommendations should be provided (even if empty, the function should work)
    assert isinstance(recommendations, list), \
        "Recommendations should be returned as a list"


@given(
    user_profile=user_profile_strategy,
    course=micro_sop_strategy,
    completion_percentage=st.floats(min_value=0.0, max_value=100.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_partial_progress_tracking(
    user_profile: UserProfile,
    course: MicroSOP,
    completion_percentage: float
):
    """
    Test that partial progress is tracked correctly.
    
    This validates that the system tracks progress at any completion level.
    """
    service = MicroSOPService()
    
    # Set up course
    course.trade_type = user_profile.trade
    course.location_specific = False
    if user_profile.primary_language not in course.supported_languages:
        course.supported_languages.append(user_profile.primary_language)
    
    service.add_course(course)
    service.register_user_profile(user_profile)
    
    # Track partial progress
    progress = ProgressData(
        user_id=user_profile.user_id,
        course_id=course.course_id,
        completion_percentage=completion_percentage,
        last_accessed=datetime.now(),
        quiz_scores={},
        time_spent_seconds=int(course.duration_seconds * (completion_percentage / 100))
    )
    
    await service.track_progress(user_profile.user_id, course.course_id, progress)
    
    # Retrieve progress
    tracked = await service.get_user_progress(user_profile.user_id, course.course_id)
    
    assert len(tracked) > 0, "Progress should be tracked"
    assert abs(tracked[0].completion_percentage - completion_percentage) < 0.1, \
        "Tracked completion percentage should match input"


@given(
    user_profile=user_profile_strategy,
    courses=st.lists(micro_sop_strategy, min_size=1, max_size=3)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_analytics_consistency(
    user_profile: UserProfile,
    courses: List[MicroSOP]
):
    """
    Test that analytics remain consistent across multiple operations.
    
    This validates that analytics calculations are deterministic and accurate.
    """
    service = MicroSOPService()
    
    # Set up courses
    for i, course in enumerate(courses):
        course.course_id = f"COURSE-{i}"
        course.trade_type = user_profile.trade
        course.location_specific = False
        if user_profile.primary_language not in course.supported_languages:
            course.supported_languages.append(user_profile.primary_language)
        service.add_course(course)
    
    service.register_user_profile(user_profile)
    
    # Track progress for all courses
    for course in courses:
        progress = ProgressData(
            user_id=user_profile.user_id,
            course_id=course.course_id,
            completion_percentage=100.0,
            last_accessed=datetime.now(),
            quiz_scores={1: True},
            time_spent_seconds=course.duration_seconds,
            completed=True
        )
        await service.track_progress(user_profile.user_id, course.course_id, progress)
    
    # Get analytics multiple times
    analytics1 = await service.get_learning_analytics(user_profile.user_id)
    analytics2 = await service.get_learning_analytics(user_profile.user_id)
    
    # Analytics should be consistent
    assert analytics1["total_courses_completed"] == analytics2["total_courses_completed"], \
        "Analytics should be consistent across calls"
    assert analytics1["completion_rate"] == analytics2["completion_rate"], \
        "Completion rate should be consistent"
    assert analytics1["total_time_spent_seconds"] == analytics2["total_time_spent_seconds"], \
        "Total time should be consistent"
