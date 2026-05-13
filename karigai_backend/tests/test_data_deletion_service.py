"""
Unit tests for Data Deletion Service
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.services.data_deletion_service import (
    DataDeletionService,
    DeletionStatus
)


class TestDataDeletionService:
    """Test data deletion service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.deletion_service = DataDeletionService(db_session=None)
    
    def test_request_data_deletion_scheduled(self):
        """Test requesting scheduled data deletion (30 days)"""
        request = self.deletion_service.request_data_deletion(
            user_id="user123",
            reason="User requested account closure"
        )
        
        assert request["user_id"] == "user123"
        assert request["status"] == DeletionStatus.PENDING.value
        assert request["immediate"] is False
        assert "request_id" in request
        assert "scheduled_deletion_date" in request
        
        # Verify scheduled for 30 days from now
        scheduled_date = datetime.fromisoformat(request["scheduled_deletion_date"])
        now = datetime.now(timezone.utc)
        days_diff = (scheduled_date - now).days
        assert 29 <= days_diff <= 30  # Allow for timing variations
    
    def test_request_data_deletion_immediate(self):
        """Test requesting immediate data deletion"""
        request = self.deletion_service.request_data_deletion(
            user_id="user456",
            immediate=True
        )
        
        assert request["user_id"] == "user456"
        assert request["immediate"] is True
        
        # Verify scheduled for immediate deletion
        scheduled_date = datetime.fromisoformat(request["scheduled_deletion_date"])
        now = datetime.now(timezone.utc)
        time_diff = (scheduled_date - now).total_seconds()
        assert time_diff < 60  # Should be within a minute
    
    def test_execute_deletion(self):
        """Test executing data deletion"""
        # Create deletion request
        request = self.deletion_service.request_data_deletion(
            user_id="user789",
            immediate=True
        )
        request_id = request["request_id"]
        
        # Execute deletion
        result = self.deletion_service.execute_deletion(request_id)
        
        assert result["status"] == DeletionStatus.COMPLETED.value
        assert "deletion_started_at" in result
        assert "deletion_completed_at" in result
        
        # Verify all data types were deleted
        expected_types = [
            "user_profile",
            "voice_sessions",
            "documents",
            "learning_progress",
            "voice_files",
            "document_files",
            "cached_data"
        ]
        for data_type in expected_types:
            assert data_type in result["deleted_data_types"]
    
    def test_execute_deletion_invalid_request(self):
        """Test executing deletion with invalid request ID"""
        with pytest.raises(ValueError, match="not found"):
            self.deletion_service.execute_deletion("invalid_request_id")
    
    def test_verify_deletion(self):
        """Test verifying data deletion"""
        # Create and execute deletion
        request = self.deletion_service.request_data_deletion(
            user_id="user999",
            immediate=True
        )
        request_id = request["request_id"]
        self.deletion_service.execute_deletion(request_id)
        
        # Verify deletion
        verification = self.deletion_service.verify_deletion(request_id)
        
        assert verification["request_id"] == request_id
        assert verification["user_id"] == "user999"
        assert "verified_at" in verification
        assert "checks" in verification
        
        # All checks should pass (data deleted)
        assert verification["all_deleted"] is True
        for check_name, check_result in verification["checks"].items():
            assert check_result is True, f"Check {check_name} failed"
        
        # Request should be marked as verified
        updated_request = self.deletion_service.get_deletion_status(request_id)
        assert updated_request["status"] == DeletionStatus.VERIFIED.value
    
    def test_get_scheduled_deletions(self):
        """Test getting scheduled deletions that are due"""
        # Create a deletion scheduled for the past (should be due)
        request1 = self.deletion_service.request_data_deletion(
            user_id="user_past",
            immediate=True
        )
        
        # Create a deletion scheduled for the future (not due)
        request2 = self.deletion_service.request_data_deletion(
            user_id="user_future",
            immediate=False
        )
        
        # Get due deletions
        due_deletions = self.deletion_service.get_scheduled_deletions()
        
        # Only the immediate deletion should be due
        assert len(due_deletions) >= 1
        due_user_ids = [req["user_id"] for req in due_deletions]
        assert "user_past" in due_user_ids
        assert "user_future" not in due_user_ids
    
    def test_process_scheduled_deletions(self):
        """Test processing all scheduled deletions"""
        # Create multiple immediate deletions
        self.deletion_service.request_data_deletion(user_id="user_a", immediate=True)
        self.deletion_service.request_data_deletion(user_id="user_b", immediate=True)
        
        # Process scheduled deletions
        results = self.deletion_service.process_scheduled_deletions()
        
        assert len(results) >= 2
        for result in results:
            assert result["status"] == DeletionStatus.COMPLETED.value
    
    def test_cancel_deletion_request(self):
        """Test canceling a pending deletion request"""
        # Create deletion request
        request = self.deletion_service.request_data_deletion(
            user_id="user_cancel",
            immediate=False
        )
        request_id = request["request_id"]
        
        # Cancel the request
        result = self.deletion_service.cancel_deletion_request(request_id)
        assert result is True
        
        # Verify request is cancelled
        updated_request = self.deletion_service.get_deletion_status(request_id)
        assert updated_request["status"] == "cancelled"
        assert "cancelled_at" in updated_request
    
    def test_cancel_deletion_request_already_executed(self):
        """Test that executed deletions cannot be cancelled"""
        # Create and execute deletion
        request = self.deletion_service.request_data_deletion(
            user_id="user_executed",
            immediate=True
        )
        request_id = request["request_id"]
        self.deletion_service.execute_deletion(request_id)
        
        # Try to cancel (should fail)
        result = self.deletion_service.cancel_deletion_request(request_id)
        assert result is False
    
    def test_get_deletion_status(self):
        """Test getting deletion request status"""
        request = self.deletion_service.request_data_deletion(
            user_id="user_status",
            reason="Testing status retrieval"
        )
        request_id = request["request_id"]
        
        # Get status
        status = self.deletion_service.get_deletion_status(request_id)
        
        assert status is not None
        assert status["user_id"] == "user_status"
        assert status["reason"] == "Testing status retrieval"
        assert status["status"] == DeletionStatus.PENDING.value
    
    def test_get_deletion_status_not_found(self):
        """Test getting status for non-existent request"""
        status = self.deletion_service.get_deletion_status("nonexistent_id")
        assert status is None
    
    def test_deletion_request_includes_timestamp(self):
        """Test that deletion requests include proper timestamps"""
        request = self.deletion_service.request_data_deletion(user_id="user_time")
        
        assert "requested_at" in request
        assert "scheduled_deletion_date" in request
        
        # Verify timestamps are valid ISO format
        requested_at = datetime.fromisoformat(request["requested_at"])
        scheduled_date = datetime.fromisoformat(request["scheduled_deletion_date"])
        
        assert isinstance(requested_at, datetime)
        assert isinstance(scheduled_date, datetime)
    
    def test_30_day_deletion_window(self):
        """Test that non-immediate deletions are scheduled for exactly 30 days"""
        request = self.deletion_service.request_data_deletion(
            user_id="user_30day",
            immediate=False
        )
        
        requested_at = datetime.fromisoformat(request["requested_at"])
        scheduled_date = datetime.fromisoformat(request["scheduled_deletion_date"])
        
        time_diff = scheduled_date - requested_at
        assert 29 <= time_diff.days <= 30  # Allow for timing variations
