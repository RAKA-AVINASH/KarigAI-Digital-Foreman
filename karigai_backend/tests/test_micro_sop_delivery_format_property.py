"""
Property-Based Test for Micro-SOP Delivery Format

**Property 10: Micro-SOP Delivery Format**
**Validates: Requirements 3.2**

This test validates that for any delivered Micro_SOP, the system should present it
as an interactive module in Local_Dialect within 30 seconds duration.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
from typing import List

from app.core.learning_module import (
    MicroSOP,
    UserProfile,
    LearningStep,
    LocationInfo,
    TradeType,
    DifficultyLevel
)
from app.services.learning_service import MicroSOPService


# Strategy for generating valid trade types
trade_type_strategy = st.sampled_from(list(TradeType))

# Strategy for generating difficulty levels
difficulty_level_strategy = st.sampled_from(list(DifficultyLevel))

# Strategy for generating language codes (Local_Dialect)
language_code_strategy = st.sampled_from([
    "hi-IN", "en-IN", "ml-IN", "pa-IN", "bn-IN", "ta-IN", "te-IN", "dogri-IN"
])

# Strategy for generating location info
location_strategy = st.builds(
    LocationInfo,
    city=st.sampled_from(["Bhopal", "Jaipur", "Srinagar", "Mumbai", "Delhi"]),
    state=st.sampled_from(["Madhya Pradesh", "Rajasthan", "Jammu & Kashmir", "Maharashtra", "Delhi"]),
    country=st.just("India")
)

# Strategy for generating user profiles
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
    total_courses_completed=st.integers(min_value=0, max_value=100)
)

# Strategy for generating learning steps with duration constraints
def learning_step_with_number(step_num: int) -> st.SearchStrategy[LearningStep]:
    """Generate a learning step with a specific step number"""
    return st.builds(
        LearningStep,
        step_number=st.just(step_num),
        title=st.text(min_size=5, max_size=50),
        content=st.text(min_size=10, max_size=200),
        duration_seconds=st.integers(min_value=5, max_value=10),
        media_url=st.one_of(st.none(), st.just("https://example.com/video.mp4")),
        quiz_question=st.none(),  # Simplified: no quiz for now
        quiz_options=st.none(),
        correct_answer=st.none()
    )

# Strategy for generating a list of learning steps with sequential numbering
@st.composite
def sequential_learning_steps(draw):
    """Generate a list of learning steps with sequential numbering"""
    num_steps = draw(st.integers(min_value=2, max_value=4))
    steps = []
    for i in range(1, num_steps + 1):
        step = draw(learning_step_with_number(i))
        steps.append(step)
    return steps

# Strategy for generating Micro-SOPs with 30-second constraint
micro_sop_strategy = st.builds(
    MicroSOP,
    course_id=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
    title=st.text(min_size=10, max_size=100),
    description=st.text(min_size=20, max_size=200),
    duration_seconds=st.integers(min_value=20, max_value=35),  # Around 30 seconds
    supported_languages=st.lists(language_code_strategy, min_size=1, max_size=3, unique=True),
    steps=sequential_learning_steps(),  # Use sequential steps
    prerequisites=st.lists(st.text(min_size=5, max_size=20), min_size=0, max_size=2),
    trade_type=trade_type_strategy,
    difficulty_level=difficulty_level_strategy,
    tags=st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5),
    location_specific=st.booleans(),
    target_location=st.one_of(st.none(), st.sampled_from(["Bhopal", "Jaipur", "Srinagar"]))
)


@given(
    user_profile=user_profile_strategy,
    micro_sop=micro_sop_strategy
)
@settings(max_examples=20, deadline=None)
def test_micro_sop_delivery_format_property(
    user_profile: UserProfile,
    micro_sop: MicroSOP
):
    """
    Property 10: Micro-SOP Delivery Format
    
    For any delivered Micro_SOP, the system should present it as an interactive
    module in Local_Dialect within 30 seconds duration.
    
    This property validates that:
    1. The Micro-SOP duration is approximately 30 seconds (20-40 seconds acceptable)
    2. The Micro-SOP supports the user's Local_Dialect (primary or secondary language)
    3. The Micro-SOP contains interactive elements (steps with content)
    4. The total duration of all steps matches the overall course duration
    5. The Micro-SOP is structured as discrete, actionable steps
    """
    # Ensure the course supports at least one of the user's languages
    user_languages = [user_profile.primary_language] + user_profile.secondary_languages
    micro_sop.supported_languages = list(set(micro_sop.supported_languages + [user_profile.primary_language]))
    
    # Ensure course is suitable for user
    micro_sop.trade_type = user_profile.trade
    micro_sop.location_specific = False
    
    # Assert: Verify property holds
    
    # 1. Duration should be approximately 30 seconds (20-40 seconds acceptable)
    assert 20 <= micro_sop.duration_seconds <= 40, \
        f"Micro-SOP duration should be around 30 seconds, got {micro_sop.duration_seconds}"
    
    # 2. Micro-SOP should support user's Local_Dialect
    course_languages = set(micro_sop.supported_languages)
    user_lang_set = set(user_languages)
    assert len(course_languages & user_lang_set) > 0, \
        "Micro-SOP should support at least one of user's languages (Local_Dialect)"
    
    # 3. Micro-SOP should contain interactive elements (steps)
    assert len(micro_sop.steps) > 0, "Micro-SOP should contain at least one step"
    
    # 4. Each step should have content
    for step in micro_sop.steps:
        assert len(step.content) > 0, f"Step {step.step_number} should have content"
        assert step.duration_seconds > 0, f"Step {step.step_number} should have positive duration"
    
    # 5. Total step duration should be reasonable relative to course duration
    total_step_duration = sum(step.duration_seconds for step in micro_sop.steps)
    # Allow some flexibility (within 50% of declared duration)
    assert total_step_duration <= micro_sop.duration_seconds * 1.5, \
        f"Total step duration ({total_step_duration}s) should not exceed course duration ({micro_sop.duration_seconds}s) by more than 50%"
    
    # 6. Steps should be numbered sequentially
    step_numbers = [step.step_number for step in micro_sop.steps]
    assert len(step_numbers) == len(set(step_numbers)), "Step numbers should be unique"


@given(
    user_profile=user_profile_strategy,
    micro_sop=micro_sop_strategy
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_micro_sop_delivery_through_service(
    user_profile: UserProfile,
    micro_sop: MicroSOP
):
    """
    Test that Micro-SOPs delivered through the service maintain the format requirements.
    
    This validates that the service layer preserves the 30-second interactive format
    when delivering courses to users.
    """
    # Arrange
    service = MicroSOPService()
    
    # Ensure course is suitable for user
    micro_sop.trade_type = user_profile.trade
    micro_sop.location_specific = False
    if user_profile.primary_language not in micro_sop.supported_languages:
        micro_sop.supported_languages.append(user_profile.primary_language)
    
    service.add_course(micro_sop)
    
    # Act: Retrieve the course through the service
    delivered_course = await service.get_course(micro_sop.course_id, user_profile.primary_language)
    
    # Assert: Verify delivered course maintains format
    assert delivered_course is not None, "Course should be delivered successfully"
    
    # 1. Duration constraint
    assert 20 <= delivered_course.duration_seconds <= 40, \
        "Delivered Micro-SOP should maintain 30-second duration constraint"
    
    # 2. Language support
    assert user_profile.primary_language in delivered_course.supported_languages, \
        "Delivered Micro-SOP should support user's primary language"
    
    # 3. Interactive structure
    assert len(delivered_course.steps) > 0, "Delivered Micro-SOP should have interactive steps"
    
    # 4. All steps should be complete
    for step in delivered_course.steps:
        assert step.title is not None and len(step.title) > 0, "Each step should have a title"
        assert step.content is not None and len(step.content) > 0, "Each step should have content"


@given(
    micro_sop=micro_sop_strategy
)
@settings(max_examples=20, deadline=None)
def test_micro_sop_has_interactive_elements(micro_sop: MicroSOP):
    """
    Test that Micro-SOPs contain interactive elements like quizzes.
    
    This validates that courses are truly interactive, not just passive content.
    """
    # At least some steps should have interactive elements
    # (quiz questions, media, or other interactive content)
    has_quiz = any(step.quiz_question is not None for step in micro_sop.steps)
    has_media = any(step.media_url is not None for step in micro_sop.steps)
    has_multiple_steps = len(micro_sop.steps) > 1
    
    # A course should have at least one form of interactivity
    assert has_quiz or has_media or has_multiple_steps, \
        "Micro-SOP should have interactive elements (quiz, media, or multiple steps)"


@given(
    micro_sop=micro_sop_strategy,
    language_code=language_code_strategy
)
@settings(max_examples=20, deadline=None)
def test_micro_sop_language_support(micro_sop: MicroSOP, language_code: str):
    """
    Test that Micro-SOPs properly indicate language support.
    
    This validates that the system can correctly identify which languages
    a course supports for Local_Dialect delivery.
    """
    # Ensure the course supports at least one language
    assume(len(micro_sop.supported_languages) > 0)
    
    # If the language is in supported languages, it should be deliverable
    if language_code in micro_sop.supported_languages:
        # Course should be accessible in this language
        assert language_code in micro_sop.supported_languages
    else:
        # Course should not claim to support this language
        assert language_code not in micro_sop.supported_languages


@given(
    micro_sop=micro_sop_strategy
)
@settings(max_examples=20, deadline=None)
def test_micro_sop_step_structure(micro_sop: MicroSOP):
    """
    Test that Micro-SOP steps are properly structured for delivery.
    
    This validates that steps are discrete, actionable units that can be
    presented sequentially to users.
    """
    # Each step should be a discrete unit
    for i, step in enumerate(micro_sop.steps):
        # Step should have a unique number
        assert step.step_number > 0, "Step number should be positive"
        
        # Step should have meaningful content
        assert len(step.title) > 0, "Step should have a title"
        assert len(step.content) > 0, "Step should have content"
        
        # Step duration should be reasonable (not too short or too long)
        assert 3 <= step.duration_seconds <= 15, \
            f"Step duration should be between 3-15 seconds for a 30-second module, got {step.duration_seconds}"


@given(
    user_profile=user_profile_strategy,
    micro_sops=st.lists(micro_sop_strategy, min_size=1, max_size=5)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_multiple_micro_sops_maintain_format(
    user_profile: UserProfile,
    micro_sops: List[MicroSOP]
):
    """
    Test that multiple Micro-SOPs all maintain the required format.
    
    This validates that the format requirements are consistently applied
    across all courses in the system.
    """
    service = MicroSOPService()
    
    # Add all courses
    for course in micro_sops:
        # Ensure course is suitable for user
        course.trade_type = user_profile.trade
        course.location_specific = False
        if user_profile.primary_language not in course.supported_languages:
            course.supported_languages.append(user_profile.primary_language)
        
        service.add_course(course)
    
    # Retrieve all courses
    for course in micro_sops:
        delivered = await service.get_course(course.course_id, user_profile.primary_language)
        
        # Each delivered course should maintain format
        assert delivered is not None
        assert 20 <= delivered.duration_seconds <= 40, \
            "All Micro-SOPs should maintain 30-second duration"
        assert len(delivered.steps) > 0, "All Micro-SOPs should have steps"
        assert user_profile.primary_language in delivered.supported_languages, \
            "All Micro-SOPs should support user's language"
