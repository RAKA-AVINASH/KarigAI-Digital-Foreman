"""
Property-Based Tests for Data Deletion Compliance

**Property 26: Data Deletion Compliance**
**Validates: Requirements 9.4**

For any user data deletion request, the system should remove all associated
personal data within 30 days.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from datetime import datetime, timedelta, timezone

from app.services.data_deletion_service import (
    DataDeletionService,
    DeletionStatus
)


# Strategy for generating user IDs
user_id_strategy = st.text(
    min_size=5,
    max_size=20,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))
)


class TestDataDeletionComplianceProperty:
    """Property-based tests for data deletion compliance"""
    
    @given(user_id=user_id_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_deletion_request_creates_valid_record(self, user_id):
        """
        Property: Any deletion request creates a valid record
        
        For any user ID:
        1. Deletion request should be created successfully
        2. Request should have all required fields
        3. Request should be in PENDING status
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        # Create deletion request
        request = deletion_service.request_data_deletion(user_id=user_id)
        
        # Property 1: Request created successfully
        assert request is not None
        assert "request_id" in request
        
        # Property 2: All required fields present
        required_fields = [
            "request_id", "user_id", "status", "requested_at",
            "scheduled_deletion_date", "immediate", "deleted_data_types"
        ]
        for field in required_fields:
            assert field in request, f"Required field {field} missing"
        
        # Property 3: Initial status is PENDING
        assert request["status"] == DeletionStatus.PENDING.value
        assert request["user_id"] == user_id
    
    @given(user_id=user_id_strategy, immediate=st.booleans())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_scheduled_deletion_date_property(self, user_id, immediate):
        """
        Property: Scheduled deletion date respects 30-day window
        
        For any user ID and immediate flag:
        1. If immediate=False, deletion scheduled for ~30 days from now
        2. If immediate=True, deletion scheduled for immediate execution
        3. Scheduled date is always in the future or present
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        request = deletion_service.request_data_deletion(
            user_id=user_id,
            immediate=immediate
        )
        
        requested_at = datetime.fromisoformat(request["requested_at"])
        scheduled_date = datetime.fromisoformat(request["scheduled_deletion_date"])
        
        # Property 1: Scheduled date is not significantly in the past (allow microsecond differences)
        time_diff = (scheduled_date - requested_at).total_seconds()
        assert time_diff >= -0.001, "Scheduled date should not be in the past (allowing for timing precision)"
        
        time_diff_seconds = (scheduled_date - requested_at).total_seconds()
        
        if immediate:
            # Property 2: Immediate deletions scheduled within 1 minute
            assert time_diff_seconds < 60, "Immediate deletion should be scheduled within 1 minute"
        else:
            # Property 3: Non-immediate deletions scheduled for ~30 days
            time_diff_days = time_diff_seconds / 86400  # Convert to days
            assert 29 <= time_diff_days <= 31, "Non-immediate deletion should be scheduled for ~30 days"
    
    @given(user_id=user_id_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_deletion_execution_completeness_property(self, user_id):
        """
        Property: Deletion execution removes all data types
        
        For any user ID:
        1. Execution should complete successfully
        2. All expected data types should be deleted
        3. Status should transition from PENDING to COMPLETED
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        # Create and execute deletion
        request = deletion_service.request_data_deletion(user_id=user_id, immediate=True)
        request_id = request["request_id"]
        
        result = deletion_service.execute_deletion(request_id)
        
        # Property 1: Execution completed
        assert result["status"] == DeletionStatus.COMPLETED.value
        
        # Property 2: All expected data types deleted
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
            assert data_type in result["deleted_data_types"], \
                f"Data type {data_type} should be deleted"
        
        # Property 3: Timestamps recorded
        assert "deletion_started_at" in result
        assert "deletion_completed_at" in result
    
    @given(user_id=user_id_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_deletion_verification_property(self, user_id):
        """
        Property: Deletion verification confirms complete data removal
        
        For any user ID:
        1. After deletion, verification should pass all checks
        2. All data existence checks should return False
        3. Request should be marked as VERIFIED
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        # Create, execute, and verify deletion
        request = deletion_service.request_data_deletion(user_id=user_id, immediate=True)
        request_id = request["request_id"]
        
        deletion_service.execute_deletion(request_id)
        verification = deletion_service.verify_deletion(request_id)
        
        # Property 1: All checks passed
        assert verification["all_deleted"] is True, "All data should be deleted"
        
        # Property 2: Individual checks all pass
        for check_name, check_result in verification["checks"].items():
            assert check_result is True, f"Verification check {check_name} failed"
        
        # Property 3: Request marked as verified
        updated_request = deletion_service.get_deletion_status(request_id)
        assert updated_request["status"] == DeletionStatus.VERIFIED.value
        assert updated_request["verification_status"] == "complete"
    
    @given(user_id=user_id_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_pending_deletion_cancellable_property(self, user_id):
        """
        Property: Pending deletions can be cancelled
        
        For any user ID:
        1. Pending deletion requests can be cancelled
        2. Cancelled requests cannot be executed
        3. Executed requests cannot be cancelled
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        # Create pending deletion
        request = deletion_service.request_data_deletion(user_id=user_id, immediate=False)
        request_id = request["request_id"]
        
        # Property 1: Pending request can be cancelled
        cancel_result = deletion_service.cancel_deletion_request(request_id)
        assert cancel_result is True, "Pending deletion should be cancellable"
        
        # Verify cancellation
        updated_request = deletion_service.get_deletion_status(request_id)
        assert updated_request["status"] == "cancelled"
        
        # Create and execute another deletion
        request2 = deletion_service.request_data_deletion(user_id=user_id + "_2", immediate=True)
        request_id2 = request2["request_id"]
        deletion_service.execute_deletion(request_id2)
        
        # Property 2: Executed request cannot be cancelled
        cancel_result2 = deletion_service.cancel_deletion_request(request_id2)
        assert cancel_result2 is False, "Executed deletion should not be cancellable"
    
    @given(
        user_ids=st.lists(user_id_strategy, min_size=1, max_size=10, unique=True)
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_batch_deletion_processing_property(self, user_ids):
        """
        Property: Multiple scheduled deletions can be processed in batch
        
        For any list of user IDs:
        1. All immediate deletions should be identified as due
        2. Batch processing should complete all due deletions
        3. Each deletion should be verified independently
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        # Create multiple immediate deletion requests
        request_ids = []
        for user_id in user_ids:
            request = deletion_service.request_data_deletion(user_id=user_id, immediate=True)
            request_ids.append(request["request_id"])
        
        # Property 1: All should be identified as due
        due_deletions = deletion_service.get_scheduled_deletions()
        due_request_ids = [req["request_id"] for req in due_deletions]
        
        for request_id in request_ids:
            assert request_id in due_request_ids, "Immediate deletion should be due"
        
        # Property 2: Batch processing completes all
        results = deletion_service.process_scheduled_deletions()
        
        # At least our requests should be processed
        processed_request_ids = [res["request_id"] for res in results]
        for request_id in request_ids:
            assert request_id in processed_request_ids, "Request should be processed"
        
        # Property 3: Each can be verified
        for request_id in request_ids:
            verification = deletion_service.verify_deletion(request_id)
            assert verification["all_deleted"] is True, "Each deletion should be complete"
    
    @given(user_id=user_id_strategy, reason=st.text(min_size=0, max_size=200))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_deletion_reason_preserved_property(self, user_id, reason):
        """
        Property: Deletion reason is preserved in request
        
        For any user ID and reason:
        1. Reason should be stored in deletion request
        2. Reason should be retrievable throughout deletion lifecycle
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        request = deletion_service.request_data_deletion(
            user_id=user_id,
            reason=reason
        )
        
        # Property 1: Reason stored
        assert request["reason"] == reason
        
        # Property 2: Reason retrievable after execution
        request_id = request["request_id"]
        deletion_service.execute_deletion(request_id)
        
        updated_request = deletion_service.get_deletion_status(request_id)
        assert updated_request["reason"] == reason, "Reason should be preserved"
    
    @given(user_id=user_id_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_deletion_idempotency_property(self, user_id):
        """
        Property: Deletion operations are idempotent
        
        For any user ID:
        1. Multiple deletion requests for same user should be independent
        2. Each request should have unique ID
        3. Executing same request twice should not cause errors
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        # Create multiple requests for same user
        request1 = deletion_service.request_data_deletion(user_id=user_id, immediate=True)
        request2 = deletion_service.request_data_deletion(user_id=user_id, immediate=True)
        
        # Property 1: Requests are independent
        assert request1["request_id"] != request2["request_id"], "Request IDs should be unique"
        
        # Property 2: Both can be executed
        result1 = deletion_service.execute_deletion(request1["request_id"])
        result2 = deletion_service.execute_deletion(request2["request_id"])
        
        assert result1["status"] == DeletionStatus.COMPLETED.value
        assert result2["status"] == DeletionStatus.COMPLETED.value
    
    @given(user_id=user_id_strategy)
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_deletion_timeline_consistency_property(self, user_id):
        """
        Property: Deletion timeline is logically consistent
        
        For any user ID:
        1. requested_at <= deletion_started_at <= deletion_completed_at
        2. All timestamps are valid ISO format
        3. Timestamps progress in logical order
        
        **Validates: Requirements 9.4**
        """
        deletion_service = DataDeletionService()
        
        request = deletion_service.request_data_deletion(user_id=user_id, immediate=True)
        request_id = request["request_id"]
        
        result = deletion_service.execute_deletion(request_id)
        
        # Parse timestamps
        requested_at = datetime.fromisoformat(result["requested_at"])
        started_at = datetime.fromisoformat(result["deletion_started_at"])
        completed_at = datetime.fromisoformat(result["deletion_completed_at"])
        
        # Property 1: Timestamps in logical order
        assert requested_at <= started_at, "Start time should be after request time"
        assert started_at <= completed_at, "Completion time should be after start time"
        
        # Property 2: All are valid datetime objects
        assert isinstance(requested_at, datetime)
        assert isinstance(started_at, datetime)
        assert isinstance(completed_at, datetime)
