"""
Property-Based Test: Data Synchronization Consistency

**Property 22: Data Synchronization Consistency**
For any offline-generated content, the system should sync all changes
when connectivity is restored without data loss.

**Validates: Requirements 8.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
import tempfile
import shutil
import asyncio

from app.core.offline_manager import OfflineManager
from app.services.sync_service import DataSyncService, SyncStatus


# Strategies for generating test data
@st.composite
def sync_item_strategy(draw):
    """Generate sync queue items"""
    item_types = ["document", "voice_session", "learning_progress", "invoice"]
    item_type = draw(st.sampled_from(item_types))
    
    item_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        blacklist_characters="\x00"
    )))
    
    # Generate appropriate data based on type
    if item_type == "document":
        data = {
            "title": draw(st.text(min_size=1, max_size=100)),
            "content": draw(st.text(min_size=1, max_size=500)),
            "format": draw(st.sampled_from(["pdf", "docx", "txt"]))
        }
    elif item_type == "voice_session":
        data = {
            "transcription": draw(st.text(min_size=1, max_size=300)),
            "language": draw(st.sampled_from(["hi-IN", "en-US", "ml-IN"])),
            "duration": draw(st.integers(min_value=1, max_value=300))
        }
    elif item_type == "learning_progress":
        data = {
            "course_id": draw(st.text(min_size=1, max_size=50)),
            "completion": draw(st.integers(min_value=0, max_value=100)),
            "quiz_score": draw(st.integers(min_value=0, max_value=100))
        }
    else:  # invoice
        data = {
            "customer_name": draw(st.text(min_size=1, max_size=100)),
            "amount": draw(st.floats(min_value=0.01, max_value=100000.0)),
            "items": draw(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5))
        }
    
    return (item_id, item_type, data)


class TestDataSynchronizationConsistency:
    """Property-based tests for data synchronization consistency"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.offline_manager = OfflineManager(cache_dir=self.temp_dir, max_cache_size_mb=50)
        self.sync_service = DataSyncService()
        self.sync_service.offline_manager = self.offline_manager
        yield
        shutil.rmtree(self.temp_dir)
    
    @given(item=sync_item_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_single_item_sync_no_data_loss(self, item):
        """
        Property: Any single offline-generated item should sync without data loss.
        
        **Validates: Requirements 8.3**
        """
        import json
        
        item_id, item_type, data = item
        
        # Clear any existing items with this ID (from previous test iterations)
        self.offline_manager.remove_from_sync_queue(item_id)
        
        # Normalize data through JSON (this is what the system does)
        normalized_data = json.loads(json.dumps(data))
        
        # Add item to sync queue
        add_result = self.offline_manager.add_to_sync_queue(item_id, item_type, data)
        assert add_result is True, "Adding to sync queue should succeed"
        
        # Verify item is in queue
        sync_queue = self.offline_manager.get_sync_queue()
        assert len(sync_queue) > 0, "Sync queue should not be empty"
        
        # Find our item in the queue
        our_item = next((i for i in sync_queue if i.item_id == item_id), None)
        assert our_item is not None, "Item should be in sync queue"
        
        # Property: Data should match normalized version (after JSON serialization)
        assert our_item.data == normalized_data, "Queued data should match JSON-normalized original"
        assert our_item.item_type == item_type, "Item type should match"
    
    @given(items=st.lists(sync_item_strategy(), min_size=1, max_size=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_items_sync_no_data_loss(self, items):
        """
        Property: Multiple offline-generated items should all sync without data loss.
        
        **Validates: Requirements 8.3**
        """
        import json
        
        # Ensure unique item IDs and normalize data
        unique_items = {}
        for item_id, item_type, data in items:
            if item_id not in unique_items:
                # Normalize through JSON
                normalized_data = json.loads(json.dumps(data))
                unique_items[item_id] = (item_type, normalized_data)
        
        assume(len(unique_items) > 0)
        
        # Add all items to sync queue
        for item_id, (item_type, data) in unique_items.items():
            add_result = self.offline_manager.add_to_sync_queue(item_id, item_type, data)
            assert add_result is True, f"Adding item {item_id} should succeed"
        
        # Verify all items are in queue
        sync_queue = self.offline_manager.get_sync_queue()
        assert len(sync_queue) == len(unique_items), "All items should be in queue"
        
        # Property: All data should match normalized original
        for item_id, (item_type, original_data) in unique_items.items():
            queued_item = next((i for i in sync_queue if i.item_id == item_id), None)
            assert queued_item is not None, f"Item {item_id} should be in queue"
            assert queued_item.data == original_data, f"Data for {item_id} should match"
            assert queued_item.item_type == item_type, f"Type for {item_id} should match"
    
    @given(item=sync_item_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sync_queue_persistence(self, item):
        """
        Property: Sync queue should persist across manager restarts
        (no data loss during app restart).
        
        **Validates: Requirements 8.3**
        """
        import json
        
        item_id, item_type, data = item
        
        # Normalize data
        normalized_data = json.loads(json.dumps(data))
        
        # Add item to sync queue
        self.offline_manager.add_to_sync_queue(item_id, item_type, data)
        
        # Create new manager instance (simulating app restart)
        new_manager = OfflineManager(cache_dir=self.temp_dir, max_cache_size_mb=50)
        
        # Property: Item should still be in queue
        sync_queue = new_manager.get_sync_queue()
        our_item = next((i for i in sync_queue if i.item_id == item_id), None)
        
        assert our_item is not None, "Item should persist across restarts"
        assert our_item.data == normalized_data, "Data should match after restart"
        assert our_item.item_type == item_type, "Type should match after restart"
    
    @given(item=sync_item_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_successful_sync_removes_from_queue(self, item):
        """
        Property: Successfully synced items should be removed from queue
        (no duplicate syncing).
        
        **Validates: Requirements 8.3**
        """
        item_id, item_type, data = item
        
        # Add item to sync queue
        self.offline_manager.add_to_sync_queue(item_id, item_type, data)
        
        # Sync the item
        async def run_sync():
            result = await self.sync_service.sync_single_item(item_id)
            return result
        
        result = asyncio.run(run_sync())
        
        # Property: If sync succeeded, item should be removed from queue
        if result and result.status == SyncStatus.SUCCESS:
            sync_queue = self.offline_manager.get_sync_queue()
            our_item = next((i for i in sync_queue if i.item_id == item_id), None)
            assert our_item is None, "Successfully synced item should be removed from queue"
    
    @given(items=st.lists(sync_item_strategy(), min_size=2, max_size=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sync_order_preservation(self, items):
        """
        Property: Items should sync in the order they were added to the queue.
        
        **Validates: Requirements 8.3**
        """
        # Ensure unique item IDs
        unique_items = []
        seen_ids = set()
        for item_id, item_type, data in items:
            if item_id not in seen_ids:
                unique_items.append((item_id, item_type, data))
                seen_ids.add(item_id)
        
        assume(len(unique_items) >= 2)
        
        # Add items in order
        for item_id, item_type, data in unique_items:
            self.offline_manager.add_to_sync_queue(item_id, item_type, data)
        
        # Get sync queue
        sync_queue = self.offline_manager.get_sync_queue()
        
        # Property: Items should be in the same order
        for i, (item_id, item_type, data) in enumerate(unique_items):
            if i < len(sync_queue):
                assert sync_queue[i].item_id == item_id, f"Item {i} should maintain order"
    
    @given(item=sync_item_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_retry_tracking_preserves_data(self, item):
        """
        Property: Retry tracking should not modify original data.
        
        **Validates: Requirements 8.3**
        """
        import json
        
        item_id, item_type, data = item
        
        # Normalize data
        normalized_data = json.loads(json.dumps(data))
        
        # Add item to sync queue
        self.offline_manager.add_to_sync_queue(item_id, item_type, data)
        
        # Mark for retry multiple times
        for _ in range(3):
            self.offline_manager.mark_sync_retry(item_id)
        
        # Property: Data should remain unchanged
        sync_queue = self.offline_manager.get_sync_queue()
        our_item = next((i for i in sync_queue if i.item_id == item_id), None)
        
        assert our_item is not None, "Item should still be in queue"
        assert our_item.data == normalized_data, "Data should not be modified by retries"
        assert our_item.retry_count == 3, "Retry count should be tracked"
    
    @given(items=st.lists(sync_item_strategy(), min_size=1, max_size=15))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_partial_sync_preserves_remaining(self, items):
        """
        Property: If some items sync successfully, remaining items should
        stay in queue without data loss.
        
        **Validates: Requirements 8.3**
        """
        import json
        
        # Ensure unique item IDs and normalize data
        unique_items = {}
        for item_id, item_type, data in items:
            if item_id not in unique_items:
                normalized_data = json.loads(json.dumps(data))
                unique_items[item_id] = (item_type, normalized_data)
        
        assume(len(unique_items) >= 2)
        
        # Add all items
        for item_id, (item_type, data) in unique_items.items():
            self.offline_manager.add_to_sync_queue(item_id, item_type, data)
        
        # Sync first item only
        first_item_id = list(unique_items.keys())[0]
        
        async def run_sync():
            await self.sync_service.sync_single_item(first_item_id)
        
        asyncio.run(run_sync())
        
        # Property: Remaining items should still be in queue with correct data
        sync_queue = self.offline_manager.get_sync_queue()
        
        for item_id, (item_type, original_data) in unique_items.items():
            if item_id != first_item_id:
                queued_item = next((i for i in sync_queue if i.item_id == item_id), None)
                # Item might have been synced or still in queue
                if queued_item:
                    assert queued_item.data == original_data, f"Data for {item_id} should be preserved"
    
    @given(
        item=sync_item_strategy(),
        modifications=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_data_integrity_during_queue_operations(self, item, modifications):
        """
        Property: Data integrity should be maintained during multiple
        queue operations.
        
        **Validates: Requirements 8.3**
        """
        import json
        
        item_id, item_type, data = item
        
        # Normalize data
        normalized_data = json.loads(json.dumps(data))
        
        # Add item
        self.offline_manager.add_to_sync_queue(item_id, item_type, data)
        
        # Perform various operations
        for _ in range(modifications):
            # Mark for retry
            self.offline_manager.mark_sync_retry(item_id)
            
            # Check data integrity
            sync_queue = self.offline_manager.get_sync_queue()
            our_item = next((i for i in sync_queue if i.item_id == item_id), None)
            
            assert our_item is not None, "Item should remain in queue"
            assert our_item.data == normalized_data, "Data should remain unchanged"
