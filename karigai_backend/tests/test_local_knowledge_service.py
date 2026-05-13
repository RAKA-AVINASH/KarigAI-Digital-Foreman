"""
Tests for Local Knowledge Base Service
"""

import pytest
from app.services.local_knowledge_service import (
    LocalKnowledgeService,
    KnowledgeCategory,
    KnowledgeItem,
    QueryResult
)


class TestLocalKnowledgeService:
    """Test suite for LocalKnowledgeService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return LocalKnowledgeService()
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.knowledge_base is not None
        assert service.location_index is not None
        assert len(service.knowledge_base) > 0
    
    def test_query_plants_kashmir(self, service):
        """Test querying plants in Kashmir"""
        result = service.query_plants("saffron", "Kashmir")
        
        assert isinstance(result, QueryResult)
        assert result.query == "saffron"
        assert result.location == "Kashmir"
        assert result.total_results > 0
        assert len(result.items) > 0
        
        # Check that results are plants
        for item in result.items:
            assert item.category == KnowledgeCategory.PLANTS
            assert "Kashmir" in item.location
    
    def test_query_plants_no_results(self, service):
        """Test querying plants with no matches"""
        result = service.query_plants("nonexistent", "Kashmir")
        
        assert result.total_results == 0
        assert len(result.items) == 0
    
    def test_query_attractions_kashmir(self, service):
        """Test querying attractions in Kashmir"""
        result = service.query_attractions("lake", "Kashmir")
        
        assert result.total_results > 0
        assert len(result.items) > 0
        
        # Check that results are attractions
        for item in result.items:
            assert item.category == KnowledgeCategory.ATTRACTIONS
    
    def test_query_attractions_jaipur(self, service):
        """Test querying attractions in Jaipur"""
        result = service.query_attractions("fort", "Jaipur")
        
        assert result.total_results > 0
        
        # Verify location match
        for item in result.items:
            assert "Jaipur" in item.location
    
    def test_query_wildlife(self, service):
        """Test querying wildlife information"""
        result = service.query_wildlife("bird", "Kashmir")
        
        assert isinstance(result, QueryResult)
        assert result.query == "bird"
        assert result.location == "Kashmir"
    
    def test_get_location_highlights_kashmir(self, service):
        """Test getting location highlights for Kashmir"""
        highlights = service.get_location_highlights("Kashmir", limit=5)
        
        assert isinstance(highlights, list)
        assert len(highlights) <= 5
        assert len(highlights) > 0
        
        # Verify all items are from Kashmir
        for item in highlights:
            assert "Kashmir" in item.location
    
    def test_get_location_highlights_limit(self, service):
        """Test that highlights respect limit parameter"""
        highlights = service.get_location_highlights("Kashmir", limit=2)
        
        assert len(highlights) <= 2
    
    def test_get_location_highlights_nonexistent(self, service):
        """Test getting highlights for nonexistent location"""
        highlights = service.get_location_highlights("Nonexistent", limit=5)
        
        assert isinstance(highlights, list)
        assert len(highlights) == 0
    
    def test_generate_promotional_content(self, service):
        """Test generating promotional content"""
        content = service.generate_promotional_content(
            location="Kashmir",
            property_name="Mountain View Homestay",
            target_audience="general"
        )
        
        assert isinstance(content, str)
        assert len(content) > 0
        assert "Kashmir" in content
        assert "Mountain View Homestay" in content
    
    def test_generate_promotional_content_nonexistent_location(self, service):
        """Test promotional content for location with no data"""
        content = service.generate_promotional_content(
            location="Unknown Place",
            property_name="Test Property"
        )
        
        assert isinstance(content, str)
        assert "Unknown Place" in content
        assert "Test Property" in content
    
    def test_get_detailed_information(self, service):
        """Test getting detailed information for specific item"""
        # Get an item ID from the knowledge base
        item_id = list(service.knowledge_base.keys())[0]
        
        item = service.get_detailed_information(item_id)
        
        assert item is not None
        assert isinstance(item, KnowledgeItem)
        assert item.item_id == item_id
        assert item.name is not None
        assert item.description is not None
    
    def test_get_detailed_information_nonexistent(self, service):
        """Test getting information for nonexistent item"""
        item = service.get_detailed_information("nonexistent_id")
        
        assert item is None
    
    def test_search_by_name(self, service):
        """Test searching by name"""
        results = service.search_by_name("Saffron")
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Verify name match
        for item in results:
            assert "saffron" in item.name.lower() or (
                item.local_name and "saffron" in item.local_name.lower()
            )
    
    def test_search_by_name_with_location_filter(self, service):
        """Test searching by name with location filter"""
        results = service.search_by_name("tree", location="Kashmir")
        
        assert isinstance(results, list)
        
        # Verify location filter
        for item in results:
            assert "Kashmir" in item.location
    
    def test_search_by_name_no_results(self, service):
        """Test searching with no matches"""
        results = service.search_by_name("nonexistent item")
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_get_all_locations(self, service):
        """Test getting all locations"""
        locations = service.get_all_locations()
        
        assert isinstance(locations, list)
        assert len(locations) > 0
        assert "kashmir" in locations
    
    def test_get_categories(self, service):
        """Test getting all categories"""
        categories = service.get_categories()
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "plants" in categories
        assert "attractions" in categories
    
    def test_knowledge_item_has_required_fields(self, service):
        """Test that knowledge items have all required fields"""
        for item in service.knowledge_base.values():
            assert item.item_id is not None
            assert item.name is not None
            assert item.category is not None
            assert item.description is not None
            assert item.location is not None
    
    def test_location_index_consistency(self, service):
        """Test that location index is consistent with knowledge base"""
        # Count items in index
        index_count = sum(len(items) for items in service.location_index.values())
        
        # Should match knowledge base size
        assert index_count == len(service.knowledge_base)
    
    def test_query_result_structure(self, service):
        """Test that query results have proper structure"""
        result = service.query_plants("tree", "Kashmir")
        
        assert hasattr(result, 'items')
        assert hasattr(result, 'query')
        assert hasattr(result, 'location')
        assert hasattr(result, 'total_results')
        assert result.total_results == len(result.items)
    
    def test_promotional_content_includes_highlights(self, service):
        """Test that promotional content includes location highlights"""
        content = service.generate_promotional_content(
            location="Kashmir",
            property_name="Test Property"
        )
        
        highlights = service.get_location_highlights("Kashmir", limit=3)
        
        if highlights:
            # At least one highlight should be mentioned
            highlight_mentioned = any(
                item.name in content for item in highlights
            )
            assert highlight_mentioned
    
    def test_search_by_local_name(self, service):
        """Test searching by local name"""
        # Search for items with local names
        all_items = list(service.knowledge_base.values())
        items_with_local_names = [
            item for item in all_items if item.local_name
        ]
        
        if items_with_local_names:
            test_item = items_with_local_names[0]
            results = service.search_by_name(test_item.local_name)
            
            assert len(results) > 0
            assert test_item in results
