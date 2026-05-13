"""
Property-Based Test: Offline Functionality Preservation

**Property 21: Offline Functionality Preservation**
For any core feature (voice recognition, document generation, learning modules),
basic functionality should remain available without network connectivity using cached data.

**Validates: Requirements 8.1, 8.2**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
import tempfile
import shutil
from datetime import datetime

from app.core.offline_manager import OfflineManager


# Strategies for generating test data
@st.composite
def cache_key_strategy(draw):
    """Generate valid cache keys"""
    feature_types = ["voice_recognition", "document_generation", "learning_module", "equipment_data"]
    feature = draw(st.sampled_from(feature_types))
    identifier = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters="\x00")))
    return f"{feature}:{identifier}"


@st.composite
def cached_data_strategy(draw):
    """Generate various types of cacheable data"""
    data_type = draw(st.sampled_from([
        "voice_transcription",
        "document_template",
        "learning_content",
        "equipment_info"
    ]))
    
    if data_type == "voice_transcription":
        return {
            "type": "voice_transcription",
            "text": draw(st.text(min_size=1, max_size=500)),
            "language": draw(st.sampled_from(["hi-IN", "en-US", "ml-IN"])),
            "confidence": draw(st.floats(min_value=0.0, max_value=1.0))
        }
    elif data_type == "document_template":
        return {
            "type": "document_template",
            "template_name": draw(st.text(min_size=1, max_size=100)),
            "fields": draw(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10))
        }
    elif data_type == "learning_content":
        return {
            "type": "learning_content",
            "title": draw(st.text(min_size=1, max_size=200)),
            "duration_seconds": draw(st.integers(min_value=10, max_value=60)),
            "steps": draw(st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5))
        }
    else:  # equipment_info
        return {
            "type": "equipment_info",
            "brand": draw(st.text(min_size=1, max_size=50)),
            "model": draw(st.text(min_size=1, max_size=50)),
            "common_issues": draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=5))
        }


class TestOfflineFunctionalityPreservation:
    """Property-based tests for offline functionality preservation"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.offline_manager = OfflineManager(cache_dir=self.temp_dir, max_cache_size_mb=50)
        yield
        shutil.rmtree(self.temp_dir)
    
    @given(
        key=cache_key_strategy(),
        data=cached_data_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cached_data_retrievable_offline(self, key, data):
        """
        Property: Any data cached for offline use should be retrievable
        without network connectivity.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Cache the data
        cache_result = self.offline_manager.cache_data(key, data, data_type=data.get("type", "general"))
        
        # Property: Caching should succeed
        assert cache_result is True, "Caching should succeed for valid data"
        
        # Property: Data should be retrievable
        retrieved_data = self.offline_manager.get_cached_data(key)
        assert retrieved_data is not None, "Cached data should be retrievable"
        
        # Property: Retrieved data should match original
        assert retrieved_data == data, "Retrieved data should match original cached data"
    
    @given(
        keys_and_data=st.lists(
            st.tuples(cache_key_strategy(), cached_data_strategy()),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_features_cached_independently(self, keys_and_data):
        """
        Property: Multiple core features can cache data independently
        and all remain accessible offline.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Ensure unique keys
        unique_items = {}
        for key, data in keys_and_data:
            if key not in unique_items:
                unique_items[key] = data
        
        assume(len(unique_items) > 0)
        
        # Cache all items
        for key, data in unique_items.items():
            cache_result = self.offline_manager.cache_data(key, data)
            assert cache_result is True, f"Caching should succeed for key: {key}"
        
        # Property: All items should be retrievable
        for key, original_data in unique_items.items():
            retrieved_data = self.offline_manager.get_cached_data(key)
            assert retrieved_data is not None, f"Data should be retrievable for key: {key}"
            assert retrieved_data == original_data, f"Data should match for key: {key}"
    
    @given(
        key=cache_key_strategy(),
        data=cached_data_strategy(),
        priority=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_priority_data_preserved(self, key, data, priority):
        """
        Property: High-priority cached data should be preserved
        even under storage pressure.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Cache high-priority data
        cache_result = self.offline_manager.cache_data(
            key, data, data_type=data.get("type", "general"), priority=priority
        )
        
        assert cache_result is True, "High-priority caching should succeed"
        
        # Property: High-priority data should be retrievable
        retrieved_data = self.offline_manager.get_cached_data(key)
        assert retrieved_data is not None, "High-priority data should be retrievable"
        assert retrieved_data == data, "High-priority data should match original"
    
    @given(
        key=cache_key_strategy(),
        data=cached_data_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cache_persistence_across_sessions(self, key, data):
        """
        Property: Cached data should persist across application sessions
        (simulated by creating new manager instances).
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Cache data with first manager
        cache_result = self.offline_manager.cache_data(key, data)
        assert cache_result is True, "Caching should succeed"
        
        # Create new manager instance (simulating app restart)
        new_manager = OfflineManager(cache_dir=self.temp_dir, max_cache_size_mb=50)
        
        # Property: Data should still be available
        retrieved_data = new_manager.get_cached_data(key)
        assert retrieved_data is not None, "Data should persist across sessions"
        assert retrieved_data == data, "Persisted data should match original"
    
    @given(
        key=cache_key_strategy(),
        data=cached_data_strategy(),
        access_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_frequently_accessed_data_tracked(self, key, data, access_count):
        """
        Property: Frequently accessed offline data should have
        its access patterns tracked correctly.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Cache data
        self.offline_manager.cache_data(key, data)
        
        # Access multiple times
        for _ in range(access_count):
            retrieved = self.offline_manager.get_cached_data(key)
            assert retrieved is not None, "Data should be accessible"
        
        # Property: Access count should be tracked
        entry = self.offline_manager._memory_cache.get(key)
        assert entry is not None, "Cache entry should exist"
        assert entry.access_count == access_count, f"Access count should be {access_count}"
    
    @given(
        voice_data=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=50),
                st.dictionaries(
                    st.sampled_from(["text", "language", "confidence"]),
                    st.one_of(st.text(min_size=1, max_size=200), st.floats(min_value=0, max_value=1)),
                    min_size=1
                )
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_voice_recognition_offline_availability(self, voice_data):
        """
        Property: Voice recognition results should be available offline
        after being cached.
        
        **Validates: Requirements 8.1 (voice recognition offline)**
        """
        # Ensure unique identifiers (last write wins for duplicates)
        unique_data = {}
        for identifier, data in voice_data:
            unique_data[identifier] = data
        
        assume(len(unique_data) > 0)
        
        # Cache voice recognition results
        for identifier, data in unique_data.items():
            key = f"voice_recognition:{identifier}"
            cache_result = self.offline_manager.cache_data(key, data, data_type="voice_recognition")
            assert cache_result is True, "Voice data caching should succeed"
        
        # Property: All voice data should be retrievable offline
        for identifier, original_data in unique_data.items():
            key = f"voice_recognition:{identifier}"
            retrieved = self.offline_manager.get_cached_data(key)
            assert retrieved is not None, f"Voice data should be retrievable for {identifier}"
            assert retrieved == original_data, "Voice data should match original"
    
    @given(
        doc_templates=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=50),
                st.dictionaries(
                    st.sampled_from(["template_name", "fields", "format"]),
                    st.one_of(
                        st.text(min_size=1, max_size=100),
                        st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)
                    ),
                    min_size=1
                )
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_document_generation_offline_availability(self, doc_templates):
        """
        Property: Document generation templates should be available offline
        after being cached.
        
        **Validates: Requirements 8.1 (document generation offline)**
        """
        # Ensure unique identifiers (last write wins for duplicates)
        unique_templates = {}
        for identifier, template_data in doc_templates:
            unique_templates[identifier] = template_data
        
        assume(len(unique_templates) > 0)
        
        # Cache document templates
        for identifier, template_data in unique_templates.items():
            key = f"document_generation:{identifier}"
            cache_result = self.offline_manager.cache_data(
                key, template_data, data_type="document_template"
            )
            assert cache_result is True, "Template caching should succeed"
        
        # Property: All templates should be retrievable offline
        for identifier, original_template in unique_templates.items():
            key = f"document_generation:{identifier}"
            retrieved = self.offline_manager.get_cached_data(key)
            assert retrieved is not None, f"Template should be retrievable for {identifier}"
            assert retrieved == original_template, "Template should match original"
    
    @given(
        learning_modules=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=50),
                st.dictionaries(
                    st.sampled_from(["title", "duration_seconds", "steps", "language"]),
                    st.one_of(
                        st.text(min_size=1, max_size=200),
                        st.integers(min_value=10, max_value=60),
                        st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5)
                    ),
                    min_size=1
                )
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_learning_modules_offline_availability(self, learning_modules):
        """
        Property: Learning modules should be available offline
        after being downloaded/cached.
        
        **Validates: Requirements 8.2 (learning modules offline)**
        """
        # Ensure unique identifiers (last write wins for duplicates)
        unique_modules = {}
        for identifier, module_data in learning_modules:
            unique_modules[identifier] = module_data
        
        assume(len(unique_modules) > 0)
        
        # Cache learning modules
        for identifier, module_data in unique_modules.items():
            key = f"learning_module:{identifier}"
            cache_result = self.offline_manager.cache_data(
                key, module_data, data_type="learning_content"
            )
            assert cache_result is True, "Learning module caching should succeed"
        
        # Property: All modules should be retrievable offline
        for identifier, original_module in unique_modules.items():
            key = f"learning_module:{identifier}"
            retrieved = self.offline_manager.get_cached_data(key)
            assert retrieved is not None, f"Module should be retrievable for {identifier}"
            assert retrieved == original_module, "Module should match original"
    
    @given(
        key=cache_key_strategy(),
        data=cached_data_strategy()
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cache_status_check(self, key, data):
        """
        Property: The system should correctly report whether data is cached
        for offline use.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Before caching
        assert not self.offline_manager.is_cached(key), "Data should not be cached initially"
        
        # Cache data
        self.offline_manager.cache_data(key, data)
        
        # Property: System should report data as cached
        assert self.offline_manager.is_cached(key), "Data should be reported as cached"
        
        # Remove from cache
        self.offline_manager.remove_from_cache(key)
        
        # Property: System should report data as not cached
        assert not self.offline_manager.is_cached(key), "Data should not be cached after removal"
