"""
Unit tests for Data Synchronization Service
"""

import pytest
import asyncio
import tempfile
import shutil

from app.services.sync_service import DataSyncService, SyncStatus
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
    return OfflineManager(cache_dir=temp_cache_dir)


@pytest.fixture
def sync_service(offline_manager):
    """Create a sync service instance"""
    service = DataSyncService()
    service.offline_manager = offline_manager
    return service


@pytest.mark.asyncio
async def test_sync_all_empty_queue(sync_service):
    """Test syncing with empty queue"""
    results = await sync_service.sync_all()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_sync_single_document(sync_service, offline_manager):
    """Test syncing a single document"""
    # Add item to sync queue
    offline_manager.add_to_sync_queue("doc_1", "document", {"title": "Test Doc"})
    
    # Sync all
    results = await sync_service.sync_all()
    
    assert len(results) == 1
    assert results[0].status == SyncStatus.SUCCESS
    assert results[0].item_id == "doc_1"
    
    # Queue should be empty after successful sync
    sync_queue = offline_manager.get_sync_queue()
    assert len(sync_queue) == 0


@pytest.mark.asyncio
async def test_sync_multiple_items(sync_service, offline_manager):
    """Test syncing multiple items"""
    # Add multiple items
    offline_manager.add_to_sync_queue("doc_1", "document", {"title": "Doc 1"})
    offline_manager.add_to_sync_queue("voice_1", "voice_session", {"text": "Hello"})
    offline_manager.add_to_sync_queue("progress_1", "learning_progress", {"completion": 50})
    
    # Sync all
    results = await sync_service.sync_all()
    
    assert len(results) == 3
    assert all(r.status == SyncStatus.SUCCESS for r in results)
    
    # Queue should be empty
    sync_queue = offline_manager.get_sync_queue()
    assert len(sync_queue) == 0


@pytest.mark.asyncio
async def test_sync_unknown_item_type(sync_service, offline_manager):
    """Test syncing item with unknown type"""
    # Add item with unknown type
    offline_manager.add_to_sync_queue("unknown_1", "unknown_type", {"data": "value"})
    
    # Sync all
    results = await sync_service.sync_all()
    
    assert len(results) == 1
    assert results[0].status == SyncStatus.FAILED
    assert "No handler registered" in results[0].error


@pytest.mark.asyncio
async def test_sync_status(sync_service, offline_manager):
    """Test getting sync status"""
    # Add items to queue
    offline_manager.add_to_sync_queue("doc_1", "document", {"title": "Doc 1"})
    offline_manager.add_to_sync_queue("doc_2", "document", {"title": "Doc 2"})
    
    status = sync_service.get_sync_status()
    
    assert status["is_syncing"] is False
    assert status["queue_size"] == 2
    assert len(status["pending_items"]) == 2


@pytest.mark.asyncio
async def test_sync_single_item(sync_service, offline_manager):
    """Test syncing a single specific item"""
    # Add multiple items
    offline_manager.add_to_sync_queue("doc_1", "document", {"title": "Doc 1"})
    offline_manager.add_to_sync_queue("doc_2", "document", {"title": "Doc 2"})
    
    # Sync only doc_1
    result = await sync_service.sync_single_item("doc_1")
    
    assert result is not None
    assert result.status == SyncStatus.SUCCESS
    assert result.item_id == "doc_1"
    
    # Only doc_2 should remain in queue
    sync_queue = offline_manager.get_sync_queue()
    assert len(sync_queue) == 1
    assert sync_queue[0].item_id == "doc_2"


@pytest.mark.asyncio
async def test_sync_retry_logic(sync_service, offline_manager):
    """Test retry logic for failed syncs"""
    # Register a handler that always fails
    async def failing_handler(item):
        return False
    
    sync_service.register_sync_handler("failing_type", failing_handler)
    
    # Add item
    offline_manager.add_to_sync_queue("fail_1", "failing_type", {"data": "value"})
    
    # First sync attempt
    results = await sync_service.sync_all()
    assert results[0].status == SyncStatus.FAILED
    
    # Item should still be in queue with retry count
    sync_queue = offline_manager.get_sync_queue()
    assert len(sync_queue) == 1
    assert sync_queue[0].retry_count == 1


@pytest.mark.asyncio
async def test_custom_sync_handler(sync_service, offline_manager):
    """Test registering custom sync handler"""
    # Track if handler was called
    handler_called = False
    
    async def custom_handler(item):
        nonlocal handler_called
        handler_called = True
        return True
    
    # Register custom handler
    sync_service.register_sync_handler("custom_type", custom_handler)
    
    # Add item with custom type
    offline_manager.add_to_sync_queue("custom_1", "custom_type", {"data": "value"})
    
    # Sync
    results = await sync_service.sync_all()
    
    assert handler_called is True
    assert results[0].status == SyncStatus.SUCCESS


@pytest.mark.asyncio
async def test_clear_sync_results(sync_service, offline_manager):
    """Test clearing sync results"""
    # Add and sync items
    offline_manager.add_to_sync_queue("doc_1", "document", {"title": "Doc 1"})
    await sync_service.sync_all()
    
    # Results should exist
    status = sync_service.get_sync_status()
    assert len(status["recent_results"]) > 0
    
    # Clear results
    sync_service.clear_sync_results()
    
    # Results should be empty
    status = sync_service.get_sync_status()
    assert len(status["recent_results"]) == 0


@pytest.mark.asyncio
async def test_concurrent_sync_prevention(sync_service, offline_manager):
    """Test that concurrent syncs are prevented"""
    # Add items
    offline_manager.add_to_sync_queue("doc_1", "document", {"title": "Doc 1"})
    
    # Start first sync (don't await yet)
    sync_task = asyncio.create_task(sync_service.sync_all())
    
    # Try to start second sync immediately
    results2 = await sync_service.sync_all()
    
    # Second sync should return empty (prevented)
    assert len(results2) == 0
    
    # Wait for first sync to complete
    results1 = await sync_task
    assert len(results1) == 1
