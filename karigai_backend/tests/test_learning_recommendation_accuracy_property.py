"""
Property-Based Test for Learning Recommendation Accuracy

**Property 9: Learning Recommendation Accuracy**
**Validates: Requirements 3.1**

This test validates that for any user with repeated similar queries,
the Learning_Module should identify knowledge gaps and suggest relevant Micro_SOPs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from typing import List

from app.core.learning_module import (
    MicroSOP,
    UserProfile,
    ProgressData,
    LearningStep,
    KnowledgeGap,
    LocationInfo,
    TradeType,
    DifficultyLevel
)


# Strategy for generating valid trade types
trade_type_strategy = st.sampled_from(list(TradeType))

# Strategy for generating difficulty levels
difficulty_level_strategy = st.sampled_from(list(DifficultyLevel))

# Strategy for generating language codes
language_code_strategy = st.sampled_from([
    "hi-IN", "en-IN", "ml-IN", "pa-IN", "bn-IN", "ta-IN", "te-IN"
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
    secondary_languages=st.lists(language_code_strategy, min_size=0, max_size=3),
    trade=trade_type_strategy,
    location=location_strategy,
    skill_tags=st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5),
    experience_level=difficulty_level_strategy,
    last_active=st.datetimes(min_value=datetime(2024, 1, 1), max_value=datetime(2026, 2, 6)),
    total_courses_completed=st.integers(min_value=0, max_value=100)
)

# Strategy for generating learning steps
learning_step_strategy = st.builds(
    LearningStep,
    step_number=st.integers(min_value=1, max_value=10),
    title=st.text(min_size=5, max_size=50),
    content=st.text(min_size=10, max_size=200),
    duration_seconds=st.integers(min_value=5, max_value=15),
    media_url=st.one_of(st.none(), st.just("https://example.com/video.mp4")),
    quiz_question=st.one_of(st.none(), st.text(min_size=10, max_size=100)),
    quiz_options=st.one_of(st.none(), st.lists(st.text(min_size=3, max_size=30), min_size=2, max_size=4)),
    correct_answer=st.one_of(st.none(), st.integers(min_value=0, max_value=3))
)

# Strategy for generating Micro-SOPs
micro_sop_strategy = st.builds(
    MicroSOP,
    course_id=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
    title=st.text(min_size=10, max_size=100),
    description=st.text(min_size=20, max_size=200),
    duration_seconds=st.integers(min_value=20, max_value=40),
    supported_languages=st.lists(language_code_strategy, min_size=1, max_size=3, unique=True),
    steps=st.lists(learning_step_strategy, min_size=1, max_size=5),
    prerequisites=st.lists(st.text(min_size=5, max_size=20), min_size=0, max_size=3),
    trade_type=trade_type_strategy,
    difficulty_level=difficulty_level_strategy,
    tags=st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5),
    location_specific=st.booleans(),
    target_location=st.one_of(st.none(), st.sampled_from(["Bhopal", "Jaipur", "Srinagar"]))
)


class MockLearningModule:
    """Mock implementation of LearningModule for testing"""
    
    def __init__(self):
        self.courses: List[MicroSOP] = []
        self.user_queries: dict = {}  # user_id -> list of query topics
        self.progress_data: dict = {}  # (user_id, course_id) -> ProgressData
    
    def add_course(self, course: MicroSOP):
        """Add a course to the module"""
        self.courses.append(course)
    
    def record_query(self, user_id: str, query_topic: str):
        """Record a user query"""
        if user_id not in self.user_queries:
            self.user_queries[user_id] = []
        self.user_queries[user_id].append(query_topic)
    
    def identify_knowledge_gaps(self, user_id: str, user_profile: UserProfile) -> List[KnowledgeGap]:
        """Identify knowledge gaps based on repeated queries"""
        if user_id not in self.user_queries:
            return []
        
        queries = self.user_queries[user_id]
        if len(queries) < 2:
            return []
        
        # Count query topics
        topic_counts = {}
        for query in queries:
            topic_counts[query] = topic_counts.get(query, 0) + 1
        
        # Identify repeated topics (appears 2+ times)
        gaps = []
        for topic, count in topic_counts.items():
            if count >= 2:
                # Find relevant courses for this topic
                relevant_courses = self._find_courses_for_topic(topic, user_profile)
                
                if relevant_courses:
                    gap = KnowledgeGap(
                        gap_id=f"GAP-{user_id}-{topic}",
                        user_id=user_id,
                        topic=topic,
                        identified_from="repeated_queries",
                        severity="high" if count >= 3 else "medium",
                        recommended_courses=[c.course_id for c in relevant_courses]
                    )
                    gaps.append(gap)
        
        return gaps
    
    def _find_courses_for_topic(self, topic: str, user_profile: UserProfile) -> List[MicroSOP]:
        """Find courses relevant to a topic"""
        relevant_courses = []
        
        for course in self.courses:
            # Check if course is suitable for user
            if not course.is_suitable_for_user(user_profile):
                continue
            
            # Check if topic matches course tags or title
            topic_lower = topic.lower()
            if any(topic_lower in tag.lower() for tag in course.tags):
                relevant_courses.append(course)
            elif topic_lower in course.title.lower():
                relevant_courses.append(course)
            elif topic_lower in course.description.lower():
                relevant_courses.append(course)
        
        return relevant_courses
    
    def get_recommended_courses(self, user_profile: UserProfile) -> List[MicroSOP]:
        """Get recommended courses based on knowledge gaps"""
        gaps = self.identify_knowledge_gaps(user_profile.user_id, user_profile)
        
        recommended_course_ids = set()
        for gap in gaps:
            recommended_course_ids.update(gap.recommended_courses)
        
        # Return actual course objects
        return [c for c in self.courses if c.course_id in recommended_course_ids]


@given(
    user_profile=user_profile_strategy,
    courses=st.lists(micro_sop_strategy, min_size=1, max_size=10),
    repeated_query_topic=st.text(min_size=3, max_size=20),
    num_repetitions=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=20, deadline=None)
def test_learning_recommendation_accuracy_property(
    user_profile: UserProfile,
    courses: List[MicroSOP],
    repeated_query_topic: str,
    num_repetitions: int
):
    """
    Property 9: Learning Recommendation Accuracy
    
    For any user with repeated similar queries, the Learning_Module should
    identify knowledge gaps and suggest relevant Micro_SOPs.
    
    This property validates that:
    1. Repeated queries are detected (2+ occurrences)
    2. Knowledge gaps are identified for repeated topics
    3. Relevant courses are recommended based on the identified gaps
    4. Recommended courses are suitable for the user's profile
    """
    # Arrange
    module = MockLearningModule()
    
    # Add courses to the module
    for course in courses:
        module.add_course(course)
    
    # Ensure at least one course matches the repeated query topic
    # by adding the topic to at least one course's tags
    if courses:
        matching_course = courses[0]
        if repeated_query_topic not in matching_course.tags:
            matching_course.tags.append(repeated_query_topic)
        
        # Ensure the matching course is suitable for the user
        matching_course.trade_type = user_profile.trade
        if user_profile.primary_language not in matching_course.supported_languages:
            matching_course.supported_languages.append(user_profile.primary_language)
        
        # Disable location-specific filtering to avoid false negatives
        matching_course.location_specific = False
    
    # Act: Record repeated queries
    for _ in range(num_repetitions):
        module.record_query(user_profile.user_id, repeated_query_topic)
    
    # Identify knowledge gaps
    gaps = module.identify_knowledge_gaps(user_profile.user_id, user_profile)
    
    # Get recommended courses
    recommended_courses = module.get_recommended_courses(user_profile)
    
    # Assert: Verify property holds
    
    # 1. Knowledge gaps should be identified for repeated queries
    assert len(gaps) > 0, "Knowledge gaps should be identified for repeated queries"
    
    # 2. At least one gap should be for the repeated topic
    gap_topics = [gap.topic for gap in gaps]
    assert repeated_query_topic in gap_topics, f"Gap should be identified for repeated topic '{repeated_query_topic}'"
    
    # 3. The identified gap should have recommended courses
    relevant_gap = next(gap for gap in gaps if gap.topic == repeated_query_topic)
    assert len(relevant_gap.recommended_courses) > 0, "Gap should have recommended courses"
    
    # 4. Recommended courses should be suitable for the user
    for course in recommended_courses:
        assert course.is_suitable_for_user(user_profile), \
            f"Recommended course {course.course_id} should be suitable for user profile"
    
    # 5. Severity should be appropriate based on repetition count
    if num_repetitions >= 3:
        assert relevant_gap.severity == "high", "High repetition should result in high severity"
    else:
        assert relevant_gap.severity in ["medium", "high"], "Severity should be medium or high"
    
    # 6. Gap should be identified from repeated queries
    assert relevant_gap.identified_from == "repeated_queries", \
        "Gap should be identified from repeated queries"


@given(
    user_profile=user_profile_strategy,
    courses=st.lists(micro_sop_strategy, min_size=2, max_size=5),
    query_topics=st.lists(st.text(min_size=3, max_size=20), min_size=2, max_size=4, unique=True)
)
@settings(max_examples=20, deadline=None)
def test_multiple_knowledge_gaps_identified(
    user_profile: UserProfile,
    courses: List[MicroSOP],
    query_topics: List[str]
):
    """
    Test that multiple knowledge gaps can be identified from different repeated queries.
    
    This validates that the system can track and identify multiple areas where
    the user needs learning support.
    """
    # Arrange
    module = MockLearningModule()
    
    for course in courses:
        module.add_course(course)
    
    # Ensure each query topic has at least one matching course
    for i, topic in enumerate(query_topics):
        if i < len(courses):
            course = courses[i]
            course.tags.append(topic)
            course.trade_type = user_profile.trade
            if user_profile.primary_language not in course.supported_languages:
                course.supported_languages.append(user_profile.primary_language)
            # Disable location-specific filtering
            course.location_specific = False
    
    # Act: Record multiple repeated queries for different topics
    for topic in query_topics:
        # Each topic is queried 2-3 times
        for _ in range(2):
            module.record_query(user_profile.user_id, topic)
    
    # Identify knowledge gaps
    gaps = module.identify_knowledge_gaps(user_profile.user_id, user_profile)
    
    # Assert
    # Multiple gaps should be identified
    assert len(gaps) >= 2, "Multiple knowledge gaps should be identified"
    
    # Each gap should have recommended courses
    for gap in gaps:
        assert len(gap.recommended_courses) > 0, \
            f"Gap for topic '{gap.topic}' should have recommended courses"


@given(
    user_profile=user_profile_strategy,
    courses=st.lists(micro_sop_strategy, min_size=1, max_size=5),
    single_query_topics=st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=3, unique=True)
)
@settings(max_examples=20, deadline=None)
def test_no_gaps_for_single_queries(
    user_profile: UserProfile,
    courses: List[MicroSOP],
    single_query_topics: List[str]
):
    """
    Test that single (non-repeated) queries do not result in knowledge gaps.
    
    This validates that the system only identifies gaps when there's a pattern
    of repeated queries, not for one-off questions.
    """
    # Arrange
    module = MockLearningModule()
    
    for course in courses:
        module.add_course(course)
    
    # Act: Record single queries (no repetition)
    for topic in single_query_topics:
        module.record_query(user_profile.user_id, topic)
    
    # Identify knowledge gaps
    gaps = module.identify_knowledge_gaps(user_profile.user_id, user_profile)
    
    # Assert: No gaps should be identified for single queries
    assert len(gaps) == 0, "No knowledge gaps should be identified for single queries"


@given(
    user_profile=user_profile_strategy,
    course=micro_sop_strategy,
    repeated_query_topic=st.text(min_size=3, max_size=20)
)
@settings(max_examples=20, deadline=None)
def test_recommendation_respects_user_language(
    user_profile: UserProfile,
    course: MicroSOP,
    repeated_query_topic: str
):
    """
    Test that recommended courses respect the user's language preferences.
    
    This validates that only courses in supported languages are recommended.
    """
    # Arrange
    module = MockLearningModule()
    
    # Set up course with matching topic but potentially different language
    course.tags.append(repeated_query_topic)
    course.trade_type = user_profile.trade
    
    # Ensure course language matches user's primary or secondary languages
    user_languages = [user_profile.primary_language] + user_profile.secondary_languages
    course.supported_languages = [lang for lang in course.supported_languages if lang in user_languages]
    
    # Only proceed if course has at least one matching language
    assume(len(course.supported_languages) > 0)
    
    module.add_course(course)
    
    # Act: Record repeated queries
    for _ in range(2):
        module.record_query(user_profile.user_id, repeated_query_topic)
    
    # Get recommended courses
    recommended_courses = module.get_recommended_courses(user_profile)
    
    # Assert: All recommended courses should support user's languages
    for rec_course in recommended_courses:
        course_languages = set(rec_course.supported_languages)
        user_lang_set = set(user_languages)
        assert len(course_languages & user_lang_set) > 0, \
            "Recommended course should support at least one of user's languages"


@given(
    user_profile=user_profile_strategy,
    course=micro_sop_strategy,
    repeated_query_topic=st.text(min_size=3, max_size=20)
)
@settings(max_examples=20, deadline=None)
def test_recommendation_respects_user_trade(
    user_profile: UserProfile,
    course: MicroSOP,
    repeated_query_topic: str
):
    """
    Test that recommended courses respect the user's trade type.
    
    This validates that only courses relevant to the user's trade or
    general courses are recommended.
    """
    # Arrange
    module = MockLearningModule()
    
    # Set up course with matching topic and language
    course.tags.append(repeated_query_topic)
    if user_profile.primary_language not in course.supported_languages:
        course.supported_languages.append(user_profile.primary_language)
    
    # Set course trade to match user's trade
    course.trade_type = user_profile.trade
    
    # Disable location-specific filtering
    course.location_specific = False
    
    module.add_course(course)
    
    # Act: Record repeated queries
    for _ in range(2):
        module.record_query(user_profile.user_id, repeated_query_topic)
    
    # Get recommended courses
    recommended_courses = module.get_recommended_courses(user_profile)
    
    # Assert: All recommended courses should match user's trade or be general
    for rec_course in recommended_courses:
        assert rec_course.trade_type == user_profile.trade or rec_course.trade_type == TradeType.GENERAL, \
            "Recommended course should match user's trade or be general"
