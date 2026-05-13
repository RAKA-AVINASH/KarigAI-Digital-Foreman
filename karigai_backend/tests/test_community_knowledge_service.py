"""
Unit tests for Community Knowledge Service
"""

import pytest
from datetime import datetime
from app.services.community_knowledge_service import (
    CommunityKnowledgeService,
    ContentType,
    KnowledgeEntry,
    UserReputation
)


@pytest.fixture
def service():
    """Create a fresh service instance for each test"""
    return CommunityKnowledgeService()


@pytest.fixture
def sample_entry(service):
    """Create a sample knowledge entry"""
    return service.add_solution(
        user_id="user123",
        problem_description="Water pipe leaking under sink",
        solution_description="Tighten the connection with wrench and apply plumber's tape",
        content_type=ContentType.VIDEO,
        content_url="https://example.com/video123",
        trade_type="plumbing",
        language="hindi"
    )


class TestCommunityKnowledgeService:
    """Test suite for Community Knowledge Service"""
    
    def test_add_solution_creates_entry(self, service):
        """Test that adding a solution creates a knowledge entry"""
        entry = service.add_solution(
            user_id="user1",
            problem_description="Electrical short circuit",
            solution_description="Check circuit breaker and replace fuse",
            content_type=ContentType.TEXT,
            content_url="https://example.com/solution1",
            trade_type="electrical",
            language="english"
        )
        
        assert entry.entry_id is not None
        assert entry.user_id == "user1"
        assert entry.problem_description == "Electrical short circuit"
        assert entry.trade_type == "electrical"
        assert entry.quality_score == 0.5  # Initial neutral score
        assert entry.upvotes == 0
        assert entry.downvotes == 0
    
    def test_auto_tagging_generates_relevant_tags(self, service):
        """Test that auto-tagging generates relevant tags"""
        entry = service.add_solution(
            user_id="user2",
            problem_description="Water leak in pipe connection",
            solution_description="Fix the leak by tightening pipe",
            content_type=ContentType.VIDEO,
            content_url="https://example.com/video1",
            trade_type="plumbing",
            language="hindi"
        )
        
        assert "plumbing" in entry.tags
        # Should detect water/leak/pipe keywords
        assert len(entry.tags) > 1
    
    def test_search_solutions_finds_relevant_entries(self, service, sample_entry):
        """Test that search finds relevant solutions"""
        # Add another entry
        service.add_solution(
            user_id="user2",
            problem_description="Door hinge broken",
            solution_description="Replace hinge with new screws",
            content_type=ContentType.TEXT,
            content_url="https://example.com/solution2",
            trade_type="carpentry",
            language="hindi"
        )
        
        # Search for plumbing issue
        results = service.search_solutions(
            problem_query="pipe leak water",
            trade_type="plumbing"
        )
        
        assert results.total_count >= 1
        assert any("plumbing" in e.trade_type for e in results.entries)
    
    def test_search_filters_by_trade_type(self, service):
        """Test that search correctly filters by trade type"""
        # Add entries for different trades
        service.add_solution(
            user_id="user1",
            problem_description="Pipe leak",
            solution_description="Fix pipe",
            content_type=ContentType.VIDEO,
            content_url="https://example.com/v1",
            trade_type="plumbing",
            language="hindi"
        )
        
        service.add_solution(
            user_id="user2",
            problem_description="Wire short",
            solution_description="Fix wire",
            content_type=ContentType.VIDEO,
            content_url="https://example.com/v2",
            trade_type="electrical",
            language="hindi"
        )
        
        # Search only for plumbing
        results = service.search_solutions(
            problem_query="fix problem",
            trade_type="plumbing"
        )
        
        assert all(e.trade_type == "plumbing" for e in results.entries)
    
    def test_search_filters_by_quality_score(self, service):
        """Test that search filters by minimum quality score"""
        entry = service.add_solution(
            user_id="user1",
            problem_description="Test problem",
            solution_description="Test solution",
            content_type=ContentType.TEXT,
            content_url="https://example.com/test",
            trade_type="plumbing",
            language="hindi"
        )
        
        # Rate it poorly
        service.rate_solution(entry.entry_id, "user2", is_helpful=False)
        service.rate_solution(entry.entry_id, "user3", is_helpful=False)
        
        # Search with high quality threshold
        results = service.search_solutions(
            problem_query="test",
            min_quality_score=0.7
        )
        
        # Should not include the poorly rated entry
        assert entry.entry_id not in [e.entry_id for e in results.entries]
    
    def test_rate_solution_updates_votes(self, service, sample_entry):
        """Test that rating a solution updates vote counts"""
        entry_id = sample_entry.entry_id
        
        # Rate as helpful
        updated_entry = service.rate_solution(entry_id, "user2", is_helpful=True)
        assert updated_entry.upvotes == 1
        assert updated_entry.downvotes == 0
        
        # Rate as not helpful
        updated_entry = service.rate_solution(entry_id, "user3", is_helpful=False)
        assert updated_entry.upvotes == 1
        assert updated_entry.downvotes == 1
    
    def test_rate_solution_updates_quality_score(self, service, sample_entry):
        """Test that rating updates quality score"""
        entry_id = sample_entry.entry_id
        initial_score = sample_entry.quality_score
        
        # Add positive ratings
        service.rate_solution(entry_id, "user2", is_helpful=True)
        service.rate_solution(entry_id, "user3", is_helpful=True)
        service.rate_solution(entry_id, "user4", is_helpful=True)
        
        updated_entry = service.knowledge_base[entry_id]
        assert updated_entry.quality_score > initial_score
    
    def test_increment_views_updates_count(self, service, sample_entry):
        """Test that incrementing views updates the count"""
        entry_id = sample_entry.entry_id
        initial_views = sample_entry.views
        
        service.increment_views(entry_id)
        service.increment_views(entry_id)
        
        assert service.knowledge_base[entry_id].views == initial_views + 2
    
    def test_user_reputation_tracks_contributions(self, service):
        """Test that user reputation tracks contributions"""
        user_id = "user123"
        
        # Add multiple solutions
        service.add_solution(
            user_id=user_id,
            problem_description="Problem 1",
            solution_description="Solution 1",
            content_type=ContentType.TEXT,
            content_url="https://example.com/s1",
            trade_type="plumbing",
            language="hindi"
        )
        
        service.add_solution(
            user_id=user_id,
            problem_description="Problem 2",
            solution_description="Solution 2",
            content_type=ContentType.TEXT,
            content_url="https://example.com/s2",
            trade_type="plumbing",
            language="hindi"
        )
        
        reputation = service.get_user_reputation(user_id)
        assert reputation.total_contributions == 2
    
    def test_user_reputation_tracks_helpful_contributions(self, service):
        """Test that reputation tracks helpful contributions"""
        user_id = "user123"
        
        entry = service.add_solution(
            user_id=user_id,
            problem_description="Test problem",
            solution_description="Test solution",
            content_type=ContentType.TEXT,
            content_url="https://example.com/test",
            trade_type="plumbing",
            language="hindi"
        )
        
        # Rate as helpful
        service.rate_solution(entry.entry_id, "user2", is_helpful=True)
        
        reputation = service.get_user_reputation(user_id)
        assert reputation.helpful_contributions == 1
    
    def test_user_reputation_calculates_score(self, service):
        """Test that reputation score is calculated correctly"""
        user_id = "user123"
        
        # Add solution
        entry = service.add_solution(
            user_id=user_id,
            problem_description="Test",
            solution_description="Test",
            content_type=ContentType.TEXT,
            content_url="https://example.com/test",
            trade_type="plumbing",
            language="hindi"
        )
        
        # Rate as helpful
        service.rate_solution(entry.entry_id, "user2", is_helpful=True)
        
        reputation = service.get_user_reputation(user_id)
        # 1 helpful out of 1 total = 100% = 100.0 score
        assert reputation.reputation_score == 100.0
    
    def test_user_level_progression(self, service):
        """Test that user level progresses with reputation"""
        user_id = "user123"
        
        # Start as beginner
        reputation = service.get_user_reputation(user_id)
        assert reputation.level == "beginner"
        
        # Add multiple helpful contributions
        for i in range(10):
            entry = service.add_solution(
                user_id=user_id,
                problem_description=f"Problem {i}",
                solution_description=f"Solution {i}",
                content_type=ContentType.TEXT,
                content_url=f"https://example.com/s{i}",
                trade_type="plumbing",
                language="hindi"
            )
            # Rate each as helpful
            service.rate_solution(entry.entry_id, f"user{i}", is_helpful=True)
        
        reputation = service.get_user_reputation(user_id)
        # Should progress to expert level
        assert reputation.level in ["expert", "master"]
    
    def test_badges_awarded_for_achievements(self, service):
        """Test that badges are awarded for achievements"""
        user_id = "user123"
        
        # Add 10 contributions to get contributor badge
        for i in range(10):
            service.add_solution(
                user_id=user_id,
                problem_description=f"Problem {i}",
                solution_description=f"Solution {i}",
                content_type=ContentType.TEXT,
                content_url=f"https://example.com/s{i}",
                trade_type="plumbing",
                language="hindi"
            )
        
        reputation = service.get_user_reputation(user_id)
        assert "contributor" in reputation.badges
    
    def test_get_trending_solutions(self, service):
        """Test that trending solutions are retrieved correctly"""
        # Add entries with different engagement
        entry1 = service.add_solution(
            user_id="user1",
            problem_description="Popular problem",
            solution_description="Popular solution",
            content_type=ContentType.VIDEO,
            content_url="https://example.com/v1",
            trade_type="plumbing",
            language="hindi"
        )
        
        entry2 = service.add_solution(
            user_id="user2",
            problem_description="Less popular problem",
            solution_description="Less popular solution",
            content_type=ContentType.TEXT,
            content_url="https://example.com/v2",
            trade_type="plumbing",
            language="hindi"
        )
        
        # Make entry1 more popular
        for i in range(5):
            service.increment_views(entry1.entry_id)
            service.rate_solution(entry1.entry_id, f"user{i}", is_helpful=True)
        
        trending = service.get_trending_solutions(limit=10)
        
        assert len(trending) > 0
        # Most popular should be first
        assert trending[0].entry_id == entry1.entry_id
    
    def test_get_trending_filters_by_trade_type(self, service):
        """Test that trending solutions can be filtered by trade type"""
        service.add_solution(
            user_id="user1",
            problem_description="Plumbing issue",
            solution_description="Fix",
            content_type=ContentType.VIDEO,
            content_url="https://example.com/v1",
            trade_type="plumbing",
            language="hindi"
        )
        
        service.add_solution(
            user_id="user2",
            problem_description="Electrical issue",
            solution_description="Fix",
            content_type=ContentType.VIDEO,
            content_url="https://example.com/v2",
            trade_type="electrical",
            language="hindi"
        )
        
        trending = service.get_trending_solutions(trade_type="plumbing")
        
        assert all(e.trade_type == "plumbing" for e in trending)
    
    def test_search_returns_empty_for_no_matches(self, service):
        """Test that search returns empty results when no matches found"""
        results = service.search_solutions(
            problem_query="nonexistent problem xyz123",
            trade_type="plumbing"
        )
        
        assert results.total_count == 0
        assert len(results.entries) == 0
    
    def test_entry_to_dict_serialization(self, service, sample_entry):
        """Test that knowledge entry can be serialized to dict"""
        entry_dict = sample_entry.to_dict()
        
        assert isinstance(entry_dict, dict)
        assert entry_dict["entry_id"] == sample_entry.entry_id
        assert entry_dict["user_id"] == sample_entry.user_id
        assert entry_dict["content_type"] == sample_entry.content_type.value
        assert isinstance(entry_dict["created_at"], str)
    
    def test_reputation_to_dict_serialization(self, service):
        """Test that user reputation can be serialized to dict"""
        reputation = service.get_user_reputation("user123")
        rep_dict = reputation.to_dict()
        
        assert isinstance(rep_dict, dict)
        assert rep_dict["user_id"] == "user123"
        assert "reputation_score" in rep_dict
        assert "level" in rep_dict
