"""
Property-Based Tests for Knowledge Base Query Response

**Property 18: Knowledge Base Query Response**
For any local information query about plants, attractions, or regional features,
the system should provide detailed explanations and identification

**Validates: Requirements 6.1**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from app.services.local_knowledge_service import (
    LocalKnowledgeService,
    KnowledgeCategory,
    KnowledgeItem,
    QueryResult
)


# Initialize service once for all tests
service = LocalKnowledgeService()

# Strategy for generating valid locations from the knowledge base
valid_locations = st.sampled_from(service.get_all_locations())

# Strategy for generating valid categories
valid_categories = st.sampled_from([
    KnowledgeCategory.PLANTS,
    KnowledgeCategory.ATTRACTIONS,
    KnowledgeCategory.WILDLIFE,
    KnowledgeCategory.CULTURE,
    KnowledgeCategory.CUISINE,
    KnowledgeCategory.ACTIVITIES
])

# Strategy for generating query strings
query_strings = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters=" -'"
    ),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() and not x.isspace())

# Strategy for generating item names from the knowledge base
def get_item_names():
    """Get all item names from knowledge base"""
    return [item.name for item in service.knowledge_base.values()]

item_names = st.sampled_from(get_item_names())

# Strategy for generating item IDs from the knowledge base
def get_item_ids():
    """Get all item IDs from knowledge base"""
    return list(service.knowledge_base.keys())

item_ids = st.sampled_from(get_item_ids())


class TestKnowledgeBaseQueryResponseProperty:
    """Property-based tests for knowledge base query response"""
    
    @given(
        query=query_strings,
        location=valid_locations
    )
    @settings(max_examples=100)
    def test_property_query_completeness_plants(self, query, location):
        """
        Property: For any valid query about plants, the system returns
        a QueryResult with appropriate structure
        
        **Validates: Requirements 6.1**
        """
        result = service.query_plants(query=query, location=location)
        
        # Property: Result must be a QueryResult instance
        assert isinstance(result, QueryResult)
        
        # Property: Result must have all required fields
        assert hasattr(result, 'items')
        assert hasattr(result, 'query')
        assert hasattr(result, 'location')
        assert hasattr(result, 'total_results')
        
        # Property: Query and location must match input
        assert result.query == query
        assert result.location == location
        
        # Property: Items must be a list
        assert isinstance(result.items, list)
        
        # Property: Total results must match items length
        assert result.total_results == len(result.items)

    
    @given(
        query=query_strings,
        location=valid_locations
    )
    @settings(max_examples=100)
    def test_property_query_completeness_attractions(self, query, location):
        """
        Property: For any valid query about attractions, the system returns
        a QueryResult with appropriate structure
        
        **Validates: Requirements 6.1**
        """
        result = service.query_attractions(query=query, location=location)
        
        # Property: Result must be a QueryResult instance
        assert isinstance(result, QueryResult)
        
        # Property: All returned items must be attractions
        for item in result.items:
            assert item.category == KnowledgeCategory.ATTRACTIONS
        
        # Property: Total results must match items length
        assert result.total_results == len(result.items)
    
    @given(
        query=query_strings,
        location=valid_locations
    )
    @settings(max_examples=100)
    def test_property_query_completeness_wildlife(self, query, location):
        """
        Property: For any valid query about wildlife, the system returns
        a QueryResult with appropriate structure
        
        **Validates: Requirements 6.1**
        """
        result = service.query_wildlife(query=query, location=location)
        
        # Property: Result must be a QueryResult instance
        assert isinstance(result, QueryResult)
        
        # Property: All returned items must be wildlife
        for item in result.items:
            assert item.category == KnowledgeCategory.WILDLIFE
        
        # Property: Total results must match items length
        assert result.total_results == len(result.items)
    
    @given(item_id=item_ids)
    @settings(max_examples=100)
    def test_property_detail_availability(self, item_id):
        """
        Property: For any item in the knowledge base, get_detailed_information()
        returns complete KnowledgeItem with all required fields
        
        **Validates: Requirements 6.1**
        """
        item = service.get_detailed_information(item_id)
        
        # Property: Item must exist
        assert item is not None
        
        # Property: Item must be a KnowledgeItem instance
        assert isinstance(item, KnowledgeItem)
        
        # Property: All required fields must be present and non-empty
        assert item.item_id is not None and len(item.item_id) > 0
        assert item.name is not None and len(item.name) > 0
        assert item.category is not None
        assert isinstance(item.category, KnowledgeCategory)
        assert item.description is not None and len(item.description) > 0
        assert item.location is not None and len(item.location) > 0
    
    @given(
        query=query_strings,
        location=valid_locations
    )
    @settings(max_examples=100)
    def test_property_location_filtering(self, query, location):
        """
        Property: For any query with location filter, all returned items
        match the specified location
        
        **Validates: Requirements 6.1**
        """
        result = service.query_plants(query=query, location=location)
        
        # Property: All returned items must match the location
        for item in result.items:
            assert location.lower() in item.location.lower(), (
                f"Item {item.name} location '{item.location}' does not match "
                f"query location '{location}'"
            )
    
    @given(
        query=query_strings,
        location=valid_locations,
        category=valid_categories
    )
    @settings(max_examples=100)
    def test_property_category_consistency(self, query, location, category):
        """
        Property: For any category-specific query, all returned items
        belong to that category
        
        **Validates: Requirements 6.1**
        """
        # Query based on category
        if category == KnowledgeCategory.PLANTS:
            result = service.query_plants(query=query, location=location)
        elif category == KnowledgeCategory.ATTRACTIONS:
            result = service.query_attractions(query=query, location=location)
        elif category == KnowledgeCategory.WILDLIFE:
            result = service.query_wildlife(query=query, location=location)
        else:
            # For other categories, skip this test
            assume(False)
        
        # Property: All returned items must match the category
        for item in result.items:
            assert item.category == category, (
                f"Item {item.name} category '{item.category.value}' does not match "
                f"query category '{category.value}'"
            )
    
    @given(item_name=item_names)
    @settings(max_examples=100)
    def test_property_search_reliability(self, item_name):
        """
        Property: For any item name in the knowledge base, search_by_name()
        successfully finds it
        
        **Validates: Requirements 6.1**
        """
        results = service.search_by_name(name=item_name)
        
        # Property: Search must return at least one result
        assert len(results) > 0, (
            f"Search for '{item_name}' returned no results"
        )
        
        # Property: At least one result must match the search name
        found = False
        for item in results:
            if item_name.lower() in item.name.lower():
                found = True
                break
        
        assert found, (
            f"Search for '{item_name}' did not return matching item"
        )
    
    @given(
        item_name=item_names,
        location=valid_locations
    )
    @settings(max_examples=100)
    def test_property_search_with_location_filter(self, item_name, location):
        """
        Property: For any search with location filter, all returned items
        match the specified location
        
        **Validates: Requirements 6.1**
        """
        results = service.search_by_name(name=item_name, location=location)
        
        # Property: All returned items must match the location
        for item in results:
            assert location.lower() in item.location.lower(), (
                f"Item {item.name} location '{item.location}' does not match "
                f"filter location '{location}'"
            )
    
    @given(
        query=query_strings,
        location=valid_locations
    )
    @settings(max_examples=100)
    def test_property_non_empty_descriptions(self, query, location):
        """
        Property: For any returned KnowledgeItem, description and name
        fields are non-empty
        
        **Validates: Requirements 6.1**
        """
        result = service.query_plants(query=query, location=location)
        
        # Property: All returned items must have non-empty name and description
        for item in result.items:
            assert item.name is not None
            assert len(item.name.strip()) > 0, (
                f"Item {item.item_id} has empty name"
            )
            
            assert item.description is not None
            assert len(item.description.strip()) > 0, (
                f"Item {item.item_id} has empty description"
            )
    
    @given(
        query=query_strings,
        location=valid_locations
    )
    @settings(max_examples=100)
    def test_property_result_count_accuracy(self, query, location):
        """
        Property: For any QueryResult, total_results matches the length
        of items list
        
        **Validates: Requirements 6.1**
        """
        result = service.query_attractions(query=query, location=location)
        
        # Property: Total results must exactly match items length
        assert result.total_results == len(result.items), (
            f"Total results {result.total_results} does not match "
            f"items length {len(result.items)}"
        )
    
    @given(location=valid_locations)
    @settings(max_examples=100)
    def test_property_location_highlights_completeness(self, location):
        """
        Property: For any location, get_location_highlights() returns
        complete KnowledgeItems with all required fields
        
        **Validates: Requirements 6.1**
        """
        highlights = service.get_location_highlights(location=location, limit=5)
        
        # Property: Highlights must be a list
        assert isinstance(highlights, list)
        
        # Property: All highlights must be KnowledgeItems
        for item in highlights:
            assert isinstance(item, KnowledgeItem)
            
            # Property: All required fields must be present
            assert item.item_id is not None and len(item.item_id) > 0
            assert item.name is not None and len(item.name) > 0
            assert item.description is not None and len(item.description) > 0
            assert item.location is not None and len(item.location) > 0
            
            # Property: Location must match query location
            assert location.lower() in item.location.lower()
    
    @given(
        location=valid_locations,
        limit=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100)
    def test_property_highlights_limit_respected(self, location, limit):
        """
        Property: For any location and limit, get_location_highlights()
        returns at most the specified number of items
        
        **Validates: Requirements 6.1**
        """
        highlights = service.get_location_highlights(location=location, limit=limit)
        
        # Property: Number of highlights must not exceed limit
        assert len(highlights) <= limit, (
            f"Returned {len(highlights)} highlights, exceeding limit of {limit}"
        )
    
    @given(
        location=valid_locations,
        property_name=st.text(min_size=3, max_size=50).filter(lambda x: x.strip())
    )
    @settings(max_examples=100)
    def test_property_promotional_content_includes_location(self, location, property_name):
        """
        Property: For any promotional content generation, the content
        includes the location and property name
        
        **Validates: Requirements 6.1**
        """
        content = service.generate_promotional_content(
            location=location,
            property_name=property_name
        )
        
        # Property: Content must be non-empty
        assert content is not None
        assert len(content.strip()) > 0
        
        # Property: Content must include location
        assert location in content, (
            f"Promotional content does not include location '{location}'"
        )
        
        # Property: Content must include property name
        assert property_name in content, (
            f"Promotional content does not include property name '{property_name}'"
        )
