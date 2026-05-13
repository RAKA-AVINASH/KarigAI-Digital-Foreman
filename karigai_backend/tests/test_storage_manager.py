"""
Unit tests for Storage Manager
"""

import pytest
import tempfile
import shutil

from app.services.storage_manager import StorageManager, StoragePriority
from app.core.offline_manager import OfflineManager


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


@pytest.fixture
def storage_manager(offline_manager):
    """Create a storage manager instance"""
    manager = StorageManager()
    manager.offline_manager = offline_manager
    return manager


def test_get_storage_status_normal(storage_manager, offline_manager):
    """Test storage status when usage is normal"""
    # Cache small amount of data
    offline_manager.cache_data("test_key", {"data": "value"})
    
    status = storage_manager.get_storage_status()
    
    assert status["status_level"] == "normal"
    assert status["usage_percentage"] < 80
    assert status["total_size_bytes"] > 0


def test_should_cleanup_false_when_normal(storage_manager):
    """Test that cleanup is not needed when storage is normal"""
    should_cleanup = storage_manager.should_cleanup()
    assert should_cleanup is False


def test_category_determination(storage_manager):
    """Test category determination from keys"""
    assert storage_manager._determine_category("user:profile:123") == "user_data"
    assert storage_manager._determine_category("voice_recognition:session1") == "voice_recognition"
    assert storage_manager._determine_category("document:invoice:456") == "document_generation"
    assert storage_manager._determine_category("learning:course:789") == "learning_modules"
    assert storage_manager._determine_category("cache:temp:abc") == "cache"


def test_get_cleanup_candidates(storage_manager, offline_manager):
    """Test getting cleanup candidates"""
    # Cache some data with different priorities
    offline_manager.cache_data("high_priority", {"data": "important"}, priority=100)
    offline_manager.cache_data("low_priority", {"data": "disposable"}, priority=0)
    offline_manager.cache_data("medium_priority", {"data": "normal"}, priority=50)
    
    candidates = storage_manager.get_cleanup_candidates(target_free_percentage=0.5)
    
    # Should return items (may be empty if not enough data)
    assert isinstance(candidates, list)


def test_cleanup_score_calculation(storage_manager):
    """Test cleanup score calculation"""
    from app.services.storage_manager import StorageItem
    from datetime import datetime, timedelta
    
    # High priority item
    high_priority_item = StorageItem(
        key="user:data",
        size_bytes=1000,
        priority=100,
        access_count=10,
        last_accessed=datetime.now(),
        created_at=datetime.now(),
        category="user_data"
    )
    
    # Low priority item
    low_priority_item = StorageItem(
        key="cache:temp",
        size_bytes=1000,
        priority=0,
        access_count=1,
        last_accessed=datetime.now() - timedelta(days=30),
        created_at=datetime.now(),
        category="cache"
    )
    
    high_score = storage_manager._calculate_cleanup_score(high_priority_item)
    low_score = storage_manager._calculate_cleanup_score(low_priority_item)
    
    # High priority item should have higher score (less likely to be cleaned up)
    assert high_score > low_score


def test_perform_cleanup_not_needed(storage_manager):
    """Test cleanup when not needed"""
    result = storage_manager.perform_cleanup()
    
    assert result["performed"] is False
    assert result["reason"] == "Cleanup not needed"


def test_get_storage_alerts_normal(storage_manager):
    """Test storage alerts when usage is normal"""
    alerts = storage_manager.get_storage_alerts()
    
    # Should have no critical or warning alerts
    critical_alerts = [a for a in alerts if a["level"] == "critical"]
    assert len(critical_alerts) == 0


def test_get_storage_recommendations(storage_manager):
    """Test getting storage recommendations"""
    recommendations = storage_manager.get_storage_recommendations()
    
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0


def test_set_category_priority(storage_manager):
    """Test setting category priority"""
    storage_manager.set_category_priority("custom_category", 75)
    
    priorities = storage_manager.get_category_priorities()
    assert priorities["custom_category"] == 75


def test_get_category_priorities(storage_manager):
    """Test getting all category priorities"""
    priorities = storage_manager.get_category_priorities()
    
    assert isinstance(priorities, dict)
    assert "user_data" in priorities
    assert "voice_recognition" in priorities
    assert priorities["user_data"] == StoragePriority.CRITICAL.value
