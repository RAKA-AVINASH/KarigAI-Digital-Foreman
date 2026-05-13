"""
Learning Service Implementation

This service provides micro-course content delivery with location and trade-specific
content curation, voice narration integration, and gamification elements.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from app.core.learning_module import (
    LearningModule,
    MicroSOP,
    UserProfile,
    ProgressData,
    KnowledgeGap,
    TradeType,
    DifficultyLevel,
    LearningStep
)


class MicroSOPService(LearningModule):
    """
    Service for delivering 30-second interactive learning modules
    with location and trade-specific content curation.
    """
    
    def __init__(self):
        """Initialize the Micro-SOP service"""
        self.courses: Dict[str, MicroSOP] = {}
        self.user_progress: Dict[str, Dict[str, ProgressData]] = {}  # user_id -> course_id -> progress
        self.user_queries: Dict[str, List[str]] = {}  # user_id -> list of query topics
        self.gamification_points: Dict[str, int] = {}  # user_id -> points
        self.user_profiles: Dict[str, UserProfile] = {}  # user_id -> profile
    
    async def get_recommended_courses(
        self, 
        user_profile: UserProfile,
        limit: int = 5
    ) -> List[MicroSOP]:
        """
        Get recommended courses for a user based on their profile and knowledge gaps.
        
        Args:
            user_profile: User profile for personalization
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended MicroSOP courses
        """
        # Identify knowledge gaps
        gaps = await self.identify_knowledge_gaps(user_profile.user_id)
        
        # Get courses for identified gaps
        recommended_course_ids = set()
        for gap in gaps:
            recommended_course_ids.update(gap.recommended_courses)
        
        # Filter courses that are suitable for the user
        recommended_courses = []
        for course_id in recommended_course_ids:
            if course_id in self.courses:
                course = self.courses[course_id]
                if course.is_suitable_for_user(user_profile):
                    recommended_courses.append(course)
        
        # If not enough recommendations from gaps, add general courses
        if len(recommended_courses) < limit:
            for course in self.courses.values():
                if course.course_id not in recommended_course_ids:
                    if course.is_suitable_for_user(user_profile):
                        recommended_courses.append(course)
                        if len(recommended_courses) >= limit:
                            break
        
        # Sort by relevance (difficulty level matching user's experience)
        recommended_courses.sort(
            key=lambda c: 0 if c.difficulty_level == user_profile.experience_level else 1
        )
        
        return recommended_courses[:limit]
    
    async def get_course(
        self, 
        course_id: str, 
        language_code: str
    ) -> Optional[MicroSOP]:
        """
        Get a specific course by ID in the requested language.
        
        Args:
            course_id: Course identifier
            language_code: Language for content delivery
            
        Returns:
            MicroSOP course or None if not found
        """
        if course_id not in self.courses:
            return None
        
        course = self.courses[course_id]
        
        # Check if course supports the requested language
        if language_code not in course.supported_languages:
            return None
        
        return course
    
    async def track_progress(
        self, 
        user_id: str, 
        course_id: str, 
        progress_data: ProgressData
    ) -> bool:
        """
        Track user progress in a course and award gamification points.
        
        Args:
            user_id: User identifier
            course_id: Course identifier
            progress_data: Progress information
            
        Returns:
            True if progress was tracked successfully
        """
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {}
        
        self.user_progress[user_id][course_id] = progress_data
        
        # Award gamification points
        if progress_data.completed:
            await self._award_points(user_id, course_id, 100)
        elif progress_data.completion_percentage >= 50:
            await self._award_points(user_id, course_id, 50)
        
        return True
    
    async def get_user_progress(
        self, 
        user_id: str, 
        course_id: Optional[str] = None
    ) -> List[ProgressData]:
        """
        Get user progress for courses.
        
        Args:
            user_id: User identifier
            course_id: Optional specific course ID
            
        Returns:
            List of progress data
        """
        if user_id not in self.user_progress:
            return []
        
        if course_id:
            if course_id in self.user_progress[user_id]:
                return [self.user_progress[user_id][course_id]]
            return []
        
        return list(self.user_progress[user_id].values())
    
    async def identify_knowledge_gaps(
        self, 
        user_id: str
    ) -> List[KnowledgeGap]:
        """
        Identify knowledge gaps based on repeated queries and quiz failures.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of identified knowledge gaps
        """
        gaps = []
        
        # Analyze repeated queries
        if user_id in self.user_queries:
            queries = self.user_queries[user_id]
            topic_counts = {}
            for query in queries:
                topic_counts[query] = topic_counts.get(query, 0) + 1
            
            # Identify repeated topics (appears 2+ times)
            for topic, count in topic_counts.items():
                if count >= 2:
                    relevant_courses = self._find_courses_for_topic(topic)
                    if relevant_courses:
                        gap = KnowledgeGap(
                            gap_id=f"GAP-{user_id}-{topic}-{datetime.now().timestamp()}",
                            user_id=user_id,
                            topic=topic,
                            identified_from="repeated_queries",
                            severity="high" if count >= 3 else "medium",
                            recommended_courses=[c.course_id for c in relevant_courses]
                        )
                        gaps.append(gap)
        
        # Analyze quiz failures
        if user_id in self.user_progress:
            for course_id, progress in self.user_progress[user_id].items():
                failed_quizzes = [step for step, correct in progress.quiz_scores.items() if not correct]
                if len(failed_quizzes) >= 2:
                    if course_id in self.courses:
                        course = self.courses[course_id]
                        gap = KnowledgeGap(
                            gap_id=f"GAP-{user_id}-{course_id}-{datetime.now().timestamp()}",
                            user_id=user_id,
                            topic=course.title,
                            identified_from="quiz_failures",
                            severity="high",
                            recommended_courses=[course_id]
                        )
                        gaps.append(gap)
        
        return gaps
    
    async def get_offline_courses(
        self, 
        user_profile: UserProfile,
        max_courses: int = 10
    ) -> List[MicroSOP]:
        """
        Get courses suitable for offline download based on user profile.
        
        Args:
            user_profile: User profile
            max_courses: Maximum number of courses
            
        Returns:
            List of courses for offline use
        """
        suitable_courses = []
        
        for course in self.courses.values():
            if course.is_suitable_for_user(user_profile):
                suitable_courses.append(course)
        
        # Prioritize by difficulty level and location-specific content
        suitable_courses.sort(
            key=lambda c: (
                0 if c.difficulty_level == user_profile.experience_level else 1,
                0 if c.location_specific else 1
            )
        )
        
        return suitable_courses[:max_courses]
    
    async def search_courses(
        self,
        query: str,
        user_profile: Optional[UserProfile] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MicroSOP]:
        """
        Search for courses by query and filters.
        
        Args:
            query: Search query
            user_profile: Optional user profile for personalization
            filters: Optional filters (trade, difficulty, etc.)
            
        Returns:
            List of matching courses
        """
        query_lower = query.lower()
        matching_courses = []
        
        for course in self.courses.values():
            # Check if query matches title, description, or tags
            if (query_lower in course.title.lower() or
                query_lower in course.description.lower() or
                any(query_lower in tag.lower() for tag in course.tags)):
                
                # Apply filters if provided
                if filters:
                    if "trade" in filters and course.trade_type.value != filters["trade"]:
                        if course.trade_type != TradeType.GENERAL:
                            continue
                    if "difficulty" in filters and course.difficulty_level.value != filters["difficulty"]:
                        continue
                
                # Check user profile suitability if provided
                if user_profile and not course.is_suitable_for_user(user_profile):
                    continue
                
                matching_courses.append(course)
        
        return matching_courses
    
    # Helper methods
    
    def _find_courses_for_topic(self, topic: str) -> List[MicroSOP]:
        """Find courses relevant to a topic"""
        relevant_courses = []
        topic_lower = topic.lower()
        
        for course in self.courses.values():
            if any(topic_lower in tag.lower() for tag in course.tags):
                relevant_courses.append(course)
            elif topic_lower in course.title.lower():
                relevant_courses.append(course)
            elif topic_lower in course.description.lower():
                relevant_courses.append(course)
        
        return relevant_courses
    
    async def _award_points(self, user_id: str, course_id: str, points: int):
        """Award gamification points to a user"""
        if user_id not in self.gamification_points:
            self.gamification_points[user_id] = 0
        self.gamification_points[user_id] += points
    
    def get_user_points(self, user_id: str) -> int:
        """Get total gamification points for a user"""
        return self.gamification_points.get(user_id, 0)
    
    def record_query(self, user_id: str, query_topic: str):
        """Record a user query for knowledge gap analysis"""
        if user_id not in self.user_queries:
            self.user_queries[user_id] = []
        self.user_queries[user_id].append(query_topic)
    
    def add_course(self, course: MicroSOP):
        """Add a course to the service"""
        self.courses[course.course_id] = course
    
    def remove_course(self, course_id: str) -> bool:
        """Remove a course from the service"""
        if course_id in self.courses:
            del self.courses[course_id]
            return True
        return False
    
    def register_user_profile(self, user_profile: UserProfile):
        """Register a user profile for personalized recommendations"""
        self.user_profiles[user_profile.user_id] = user_profile
    
    async def get_follow_up_recommendations(
        self,
        user_id: str,
        completed_course_id: str,
        limit: int = 3
    ) -> List[MicroSOP]:
        """
        Get follow-up course recommendations after completing a course.
        
        Args:
            user_id: User identifier
            completed_course_id: ID of the completed course
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended follow-up courses
        """
        if completed_course_id not in self.courses:
            return []
        
        completed_course = self.courses[completed_course_id]
        recommendations = []
        
        # Get user profile if available
        user_profile = self.user_profiles.get(user_id)
        
        # Find courses that list this course as a prerequisite
        for course in self.courses.values():
            if completed_course_id in course.prerequisites:
                if user_profile and course.is_suitable_for_user(user_profile):
                    recommendations.append(course)
                elif not user_profile:
                    recommendations.append(course)
        
        # If not enough prerequisite-based recommendations, find similar courses
        if len(recommendations) < limit:
            for course in self.courses.values():
                if course.course_id == completed_course_id:
                    continue
                if course.course_id in [r.course_id for r in recommendations]:
                    continue
                
                # Check for similar tags
                common_tags = set(course.tags) & set(completed_course.tags)
                if len(common_tags) > 0:
                    # Same trade and next difficulty level
                    if course.trade_type == completed_course.trade_type:
                        if user_profile and course.is_suitable_for_user(user_profile):
                            recommendations.append(course)
                        elif not user_profile:
                            recommendations.append(course)
                
                if len(recommendations) >= limit:
                    break
        
        return recommendations[:limit]
    
    async def get_learning_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive learning analytics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing analytics data
        """
        if user_id not in self.user_progress:
            return {
                "total_courses_started": 0,
                "total_courses_completed": 0,
                "completion_rate": 0.0,
                "total_time_spent_seconds": 0,
                "average_quiz_score": 0.0,
                "total_points": 0,
                "knowledge_gaps": [],
                "recommended_courses": []
            }
        
        progress_list = list(self.user_progress[user_id].values())
        
        total_started = len(progress_list)
        total_completed = sum(1 for p in progress_list if p.completed)
        completion_rate = (total_completed / total_started * 100) if total_started > 0 else 0.0
        
        total_time = sum(p.time_spent_seconds for p in progress_list)
        
        # Calculate average quiz score
        all_quiz_scores = []
        for progress in progress_list:
            all_quiz_scores.extend(progress.quiz_scores.values())
        
        avg_quiz_score = (sum(1 for s in all_quiz_scores if s) / len(all_quiz_scores) * 100) if all_quiz_scores else 0.0
        
        # Get knowledge gaps
        gaps = await self.identify_knowledge_gaps(user_id)
        
        # Get recommended courses
        user_profile = self.user_profiles.get(user_id)
        recommended = []
        if user_profile:
            recommended = await self.get_recommended_courses(user_profile, limit=5)
        
        return {
            "total_courses_started": total_started,
            "total_courses_completed": total_completed,
            "completion_rate": completion_rate,
            "total_time_spent_seconds": total_time,
            "average_quiz_score": avg_quiz_score,
            "total_points": self.get_user_points(user_id),
            "knowledge_gaps": [
                {
                    "topic": gap.topic,
                    "severity": gap.severity,
                    "identified_from": gap.identified_from
                }
                for gap in gaps
            ],
            "recommended_courses": [
                {
                    "course_id": course.course_id,
                    "title": course.title,
                    "difficulty": course.difficulty_level.value
                }
                for course in recommended
            ]
        }
