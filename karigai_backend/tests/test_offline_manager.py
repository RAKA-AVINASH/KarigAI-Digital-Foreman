"""
Unit tests for Offline Manager
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.core.offline_manager import OfflineManager, CacheEntry


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def offline_manager(temp_cache_dir):
    """Create an offline manager instance"""
    return OfflineManager(cache_dir=temp_cache_dir, max_cache_size_mb=10)


def test_cache_data(offline_manager):
    """Test caching data"""
    data = {"key": "value", "number": 42}
    result = offline_manager.cache_data("test_key", data, data_type="test")
    
    assert result is True
    assert offline_manager.is_cached("test_key")


def test_get_cached_data(offline_manager):
    """Test retrieving cached data"""
    data = {"key": "value", "number": 42}
    offline_manager.cache_data("test_key", data)
    
    retrieved = offline_manager.get_cached_data("test_key")
    assert retrieved == data


def test_cache_miss(offline_manager):
    """Test cache miss returns None"""
    result = offline_manager.get_cached_data("nonexistent_key")
    assert result is None


def test_remove_from_cache(offline_manager):
    """Test removing data from cache"""
    data = {"key": "value"}
    offline_manager.cache_data("test_key", data)
    
    assert offline_manager.is_cached("test_key")
    
    result = offline_manager.remove_from_cache("test_key")
    assert result is True
    assert not offline_manager.is_cached("test_key")


def test_cache_eviction(offline_manager):
    """Test cache eviction when size limit is reached"""
    # Create large data entries
    large_data = {"data": "x" * 1000000}  # ~1MB
    
    # Cache multiple entries to exceed limit
    for i in range(15):  # 15MB of data, limit is 10MB
        offline_manager.cache_data(f"key_{i}", large_data, priority=i % 3)
    
    # Check that cache size is within limit
    cache_size = offline_manager.get_cache_size()
    assert cache_size <= offline_manager.max_cache_size


def test_cache_priority(offline_manager):
    """Test that higher priority items are kept during eviction"""
    # Cache low priority item
    offline_manager.cache_data("low_priority", {"data": "x" * 1000000}, priority=0)
    
    # Cache high priority item
    offline_manager.cache_data("high_priority", {"data": "x" * 1000000}, priority=100)
    
    # Fill cache to trigger eviction
    for i in range(10):
        offline_manager.cache_data(f"filler_{i}", {"data": "x" * 1000000}, priority=50)
    
    # High priority should still be cached
    assert offline_manager.is_cached("high_priority")


def test_access_count_tracking(offline_manager):
    """Test that access counts are tracked"""
    data = {"key": "value"}
    offline_manager.cache_data("test_key", data)
    
    # Access multiple times
    for _ in range(5):
        offline_manager.get_cached_data("test_key")
    
    # Check access count in memory cache
    entry = offline_manager._memory_cache["test_key"]
    assert entry.access_count == 5


def test_cache_stats(offline_manager):
    """Test cache statistics"""
    # Cache some data
    for i in range(3):
        offline_manager.cache_data(f"key_{i}", {"data": f"value_{i}"})
    
    stats = offline_manager.get_cache_stats()
    
    assert stats["entry_count"] == 3
    assert stats["total_size_bytes"] > 0
    assert 0 <= stats["usage_percentage"] <= 100


def test_add_to_sync_queue(offline_manager):
    """Test adding items to sync queue"""
    data = {"field": "value"}
    result = offline_manager.add_to_sync_queue("item_1", "document", data)
    
    assert result is True
    
    sync_queue = offline_manager.get_sync_queue()
    assert len(sync_queue) == 1
    assert sync_queue[0].item_id == "item_1"
    assert sync_queue[0].item_type == "document"


def test_remove_from_sync_queue(offline_manager):
    """Test removing items from sync queue"""
    offline_manager.add_to_sync_queue("item_1", "document", {"data": "value"})
    
    result = offline_manager.remove_from_sync_queue("item_1")
    assert result is True
    
    sync_queue = offline_manager.get_sync_queue()
    assert len(sync_queue) == 0


def test_mark_sync_retry(offline_manager):
    """Test marking sync items for retry"""
    offline_manager.add_to_sync_queue("item_1", "document", {"data": "value"})
    
    result = offline_manager.mark_sync_retry("item_1")
    assert result is True
    
    sync_queue = offline_manager.get_sync_queue()
    assert sync_queue[0].retry_count == 1
    assert sync_queue[0].last_retry is not None


def test_clear_cache(offline_manager):
    """Test clearing all cache"""
    # Cache some data
    for i in range(3):
        offline_manager.cache_data(f"key_{i}", {"data": f"value_{i}"})
    
    offline_manager.clear_cache()
    
    stats = offline_manager.get_cache_stats()
    assert stats["entry_count"] == 0
    assert stats["total_size_bytes"] == 0


def test_usage_stats(offline_manager):
    """Test usage statistics tracking"""
    offline_manager.update_usage_stats("voice_recognition", 1000)
    offline_manager.update_usage_stats("voice_recognition", 500)
    offline_manager.update_usage_stats("document_generation", 2000)
    
    stats = offline_manager.get_usage_stats()
    
    assert len(stats) == 2
    
    # Find voice_recognition stats
    voice_stats = next(s for s in stats if s["feature"] == "voice_recognition")
    assert voice_stats["access_count"] == 2
    assert voice_stats["total_size_bytes"] == 1500


def test_cache_persistence(temp_cache_dir):
    """Test that cache persists across manager instances"""
    # Create first manager and cache data
    manager1 = OfflineManager(cache_dir=temp_cache_dir)
    manager1.cache_data("persistent_key", {"data": "persistent_value"})
    
    # Create second manager with same cache dir
    manager2 = OfflineManager(cache_dir=temp_cache_dir)
    
    # Data should be available
    assert manager2.is_cached("persistent_key")
    data = manager2.get_cached_data("persistent_key")
    assert data == {"data": "persistent_value"}


def test_sync_queue_persistence(temp_cache_dir):
    """Test that sync queue persists across manager instances"""
    # Create first manager and add to sync queue
    manager1 = OfflineManager(cache_dir=temp_cache_dir)
    manager1.add_to_sync_queue("item_1", "document", {"data": "value"})
    
    # Create second manager with same cache dir
    manager2 = OfflineManager(cache_dir=temp_cache_dir)
    
    # Sync queue should be available
    sync_queue = manager2.get_sync_queue()
    assert len(sync_queue) == 1
    assert sync_queue[0].item_id == "item_1"
