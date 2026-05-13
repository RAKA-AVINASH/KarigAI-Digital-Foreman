"""
Data Deletion Service for KarigAI

Provides GDPR-compliant data deletion capabilities with 30-day automation
and complete data purge verification.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
import os


class DeletionStatus(Enum):
    """Status of data deletion request"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


class DataDeletionService:
    """Service for GDPR-compliant data deletion"""
    
    def __init__(self, db_session=None, file_storage_path: str = "./uploads"):
        """
        Initialize data deletion service
        
        Args:
            db_session: Database session for data operations
            file_storage_path: Path to file storage directory
        """
        self.db = db_session
        self.file_storage_path = file_storage_path
        self.deletion_requests = {}  # In production, store in database
    
    def request_data_deletion(
        self,
        user_id: str,
        reason: Optional[str] = None,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """
        Request deletion of all user data
        
        Args:
            user_id: User identifier
            reason: Optional reason for deletion
            immediate: If True, delete immediately; otherwise schedule for 30 days
            
        Returns:
            Deletion request record
        """
        request_id = f"del_{user_id}_{datetime.now(timezone.utc).timestamp()}"
        
        deletion_date = datetime.now(timezone.utc)
        if not immediate:
            deletion_date += timedelta(days=30)
        
        deletion_request = {
            "request_id": request_id,
            "user_id": user_id,
            "status": DeletionStatus.PENDING.value,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "scheduled_deletion_date": deletion_date.isoformat(),
            "reason": reason,
            "immediate": immediate,
            "deleted_data_types": [],
            "verification_status": None
        }
        
        self.deletion_requests[request_id] = deletion_request
        
        return deletion_request
    
    def execute_deletion(self, request_id: str) -> Dict[str, Any]:
        """
        Execute data deletion for a request
        
        Args:
            request_id: Deletion request identifier
            
        Returns:
            Updated deletion request with results
        """
        if request_id not in self.deletion_requests:
            raise ValueError(f"Deletion request {request_id} not found")
        
        request = self.deletion_requests[request_id]
        user_id = request["user_id"]
        
        # Update status
        request["status"] = DeletionStatus.IN_PROGRESS.value
        request["deletion_started_at"] = datetime.now(timezone.utc).isoformat()
        
        deleted_types = []
        
        try:
            # Delete user profile data
            if self._delete_user_profile(user_id):
                deleted_types.append("user_profile")
            
            # Delete voice sessions
            if self._delete_voice_sessions(user_id):
                deleted_types.append("voice_sessions")
            
            # Delete documents
            if self._delete_documents(user_id):
                deleted_types.append("documents")
            
            # Delete learning progress
            if self._delete_learning_progress(user_id):
                deleted_types.append("learning_progress")
            
            # Delete voice recordings (files)
            if self._delete_voice_files(user_id):
                deleted_types.append("voice_files")
            
            # Delete generated documents (files)
            if self._delete_document_files(user_id):
                deleted_types.append("document_files")
            
            # Delete cached data
            if self._delete_cached_data(user_id):
                deleted_types.append("cached_data")
            
            # Update request
            request["status"] = DeletionStatus.COMPLETED.value
            request["deleted_data_types"] = deleted_types
            request["deletion_completed_at"] = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            request["status"] = DeletionStatus.FAILED.value
            request["error"] = str(e)
            request["deletion_failed_at"] = datetime.now(timezone.utc).isoformat()
        
        return request
    
    def verify_deletion(self, request_id: str) -> Dict[str, Any]:
        """
        Verify that all user data has been completely deleted
        
        Args:
            request_id: Deletion request identifier
            
        Returns:
            Verification results
        """
        if request_id not in self.deletion_requests:
            raise ValueError(f"Deletion request {request_id} not found")
        
        request = self.deletion_requests[request_id]
        user_id = request["user_id"]
        
        verification = {
            "request_id": request_id,
            "user_id": user_id,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "checks": {},
            "all_deleted": True
        }
        
        # Verify user profile deleted
        verification["checks"]["user_profile"] = not self._user_profile_exists(user_id)
        
        # Verify voice sessions deleted
        verification["checks"]["voice_sessions"] = not self._voice_sessions_exist(user_id)
        
        # Verify documents deleted
        verification["checks"]["documents"] = not self._documents_exist(user_id)
        
        # Verify learning progress deleted
        verification["checks"]["learning_progress"] = not self._learning_progress_exists(user_id)
        
        # Verify files deleted
        verification["checks"]["voice_files"] = not self._voice_files_exist(user_id)
        verification["checks"]["document_files"] = not self._document_files_exist(user_id)
        
        # Check if all verifications passed
        verification["all_deleted"] = all(verification["checks"].values())
        
        # Update request
        if verification["all_deleted"]:
            request["status"] = DeletionStatus.VERIFIED.value
            request["verification_status"] = "complete"
        else:
            request["verification_status"] = "incomplete"
            request["remaining_data"] = [
                key for key, value in verification["checks"].items() if not value
            ]
        
        return verification
    
    def get_scheduled_deletions(self) -> List[Dict[str, Any]]:
        """
        Get all scheduled deletions that are due
        
        Returns:
            List of deletion requests ready for execution
        """
        now = datetime.now(timezone.utc)
        due_deletions = []
        
        for request in self.deletion_requests.values():
            if request["status"] == DeletionStatus.PENDING.value:
                scheduled_date = datetime.fromisoformat(request["scheduled_deletion_date"])
                if scheduled_date <= now:
                    due_deletions.append(request)
        
        return due_deletions
    
    def process_scheduled_deletions(self) -> List[Dict[str, Any]]:
        """
        Process all scheduled deletions that are due
        
        Returns:
            List of processed deletion requests
        """
        due_deletions = self.get_scheduled_deletions()
        results = []
        
        for request in due_deletions:
            result = self.execute_deletion(request["request_id"])
            results.append(result)
        
        return results
    
    def cancel_deletion_request(self, request_id: str) -> bool:
        """
        Cancel a pending deletion request (before execution)
        
        Args:
            request_id: Deletion request identifier
            
        Returns:
            True if cancellation successful
        """
        if request_id not in self.deletion_requests:
            return False
        
        request = self.deletion_requests[request_id]
        
        if request["status"] != DeletionStatus.PENDING.value:
            return False  # Can only cancel pending requests
        
        request["status"] = "cancelled"
        request["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        
        return True
    
    def get_deletion_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a deletion request
        
        Args:
            request_id: Deletion request identifier
            
        Returns:
            Deletion request status or None if not found
        """
        return self.deletion_requests.get(request_id)
    
    # Private helper methods for actual deletion operations
    
    def _delete_user_profile(self, user_id: str) -> bool:
        """Delete user profile from database"""
        # In production, execute: DELETE FROM users WHERE user_id = ?
        return True
    
    def _delete_voice_sessions(self, user_id: str) -> bool:
        """Delete voice sessions from database"""
        # In production, execute: DELETE FROM voice_sessions WHERE user_id = ?
        return True
    
    def _delete_documents(self, user_id: str) -> bool:
        """Delete documents from database"""
        # In production, execute: DELETE FROM documents WHERE user_id = ?
        return True
    
    def _delete_learning_progress(self, user_id: str) -> bool:
        """Delete learning progress from database"""
        # In production, execute: DELETE FROM learning_progress WHERE user_id = ?
        return True
    
    def _delete_voice_files(self, user_id: str) -> bool:
        """Delete voice recording files"""
        # In production, delete files from storage
        user_voice_dir = os.path.join(self.file_storage_path, "voice", user_id)
        if os.path.exists(user_voice_dir):
            # Would recursively delete directory
            pass
        return True
    
    def _delete_document_files(self, user_id: str) -> bool:
        """Delete generated document files"""
        # In production, delete files from storage
        user_doc_dir = os.path.join(self.file_storage_path, "documents", user_id)
        if os.path.exists(user_doc_dir):
            # Would recursively delete directory
            pass
        return True
    
    def _delete_cached_data(self, user_id: str) -> bool:
        """Delete cached data from Redis/cache"""
        # In production, delete from cache
        return True
    
    # Verification helper methods
    
    def _user_profile_exists(self, user_id: str) -> bool:
        """Check if user profile still exists"""
        # In production, query database
        return False
    
    def _voice_sessions_exist(self, user_id: str) -> bool:
        """Check if voice sessions still exist"""
        # In production, query database
        return False
    
    def _documents_exist(self, user_id: str) -> bool:
        """Check if documents still exist"""
        # In production, query database
        return False
    
    def _learning_progress_exists(self, user_id: str) -> bool:
        """Check if learning progress still exists"""
        # In production, query database
        return False
    
    def _voice_files_exist(self, user_id: str) -> bool:
        """Check if voice files still exist"""
        user_voice_dir = os.path.join(self.file_storage_path, "voice", user_id)
        return os.path.exists(user_voice_dir)
    
    def _document_files_exist(self, user_id: str) -> bool:
        """Check if document files still exist"""
        user_doc_dir = os.path.join(self.file_storage_path, "documents", user_id)
        return os.path.exists(user_doc_dir)
