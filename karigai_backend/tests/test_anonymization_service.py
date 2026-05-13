"""
Unit tests for Anonymization Service
"""

import pytest
from app.services.anonymization_service import (
    AnonymizationService,
    PrivacyPreservingAnalytics
)
from app.services.encryption_service import EncryptionService


class TestAnonymizationService:
    """Test anonymization service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        encryption_service = EncryptionService(master_key="test-key-12345")
        self.anonymization_service = AnonymizationService(encryption_service)
    
    def test_anonymize_user_data(self):
        """Test user data anonymization"""
        user_data = {
            "user_id": "user123",
            "phone_number": "+91-9876543210",
            "primary_language": "hi-IN",
            "trade_type": "plumber",
            "location_data": "123 Main St, Bhopal, Madhya Pradesh",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        anonymized = self.anonymization_service.anonymize_user_data(user_data)
        
        # Should not contain direct identifiers
        assert "user_id" not in anonymized
        assert "phone_number" not in anonymized
        
        # Should contain hashed identifiers
        assert "user_id_hash" in anonymized
        assert "phone_hash" in anonymized
        
        # Should preserve non-PII fields
        assert anonymized["primary_language"] == "hi-IN"
        assert anonymized["trade_type"] == "plumber"
        assert anonymized["created_at"] == "2024-01-01T00:00:00Z"
        
        # Should generalize location
        assert "location_region" in anonymized
        assert "123 Main St" not in anonymized["location_region"]
    
    def test_anonymize_session_data(self):
        """Test session data anonymization"""
        session_data = {
            "session_id": "session456",
            "user_id": "user123",
            "transcribed_text": "मुझे एक इनवॉइस बनाना है",
            "language_detected": "hi-IN",
            "confidence_score": 0.95,
            "created_at": "2024-01-01T10:00:00Z"
        }
        
        anonymized = self.anonymization_service.anonymize_session_data(session_data)
        
        # Should not contain direct identifiers or actual text
        assert "session_id" not in anonymized
        assert "user_id" not in anonymized
        assert "transcribed_text" not in anonymized
        
        # Should contain hashed identifiers
        assert "session_id_hash" in anonymized
        assert "user_id_hash" in anonymized
        
        # Should preserve metadata
        assert anonymized["language_detected"] == "hi-IN"
        assert anonymized["confidence_score"] == 0.95
        
        # Should include text length for analysis
        assert "text_length" in anonymized
        assert anonymized["text_length"] == len("मुझे एक इनवॉइस बनाना है")
    
    def test_anonymize_analytics_event(self):
        """Test analytics event anonymization"""
        event_data = {
            "user_id": "user789",
            "action": "document_generated",
            "event_type": "feature_usage",
            "timestamp": "2024-01-01T12:00:00Z",
            "metadata": {
                "ip_address": "192.168.1.1",
                "device_id": "device123",
                "session_duration": 300,
                "feature_used": "invoice_generation"
            }
        }
        
        anonymized = self.anonymization_service.anonymize_analytics_event(event_data)
        
        # Should not contain direct identifiers
        assert "user_id" not in anonymized
        
        # Should contain hashed identifier
        assert "user_id_hash" in anonymized
        
        # Should preserve event information
        assert anonymized["action"] == "document_generated"
        assert anonymized["event_type"] == "feature_usage"
        assert anonymized["timestamp"] == "2024-01-01T12:00:00Z"
        
        # Should anonymize metadata
        assert "ip_address" not in anonymized["metadata"]
        assert "device_id" not in anonymized["metadata"]
        assert "ip_hash" in anonymized["metadata"]
        assert "device_id_hash" in anonymized["metadata"]
        
        # Should preserve non-PII metadata
        assert anonymized["metadata"]["session_duration"] == 300
        assert anonymized["metadata"]["feature_used"] == "invoice_generation"
    
    def test_remove_pii_from_text(self):
        """Test PII removal from text"""
        text = "Contact me at +91-9876543210 or email@example.com from IP 192.168.1.1"
        
        cleaned = self.anonymization_service.remove_pii_from_text(text)
        
        # Should mask phone numbers
        assert "+91-9876543210" not in cleaned
        assert "[PHONE]" in cleaned
        
        # Should mask email addresses
        assert "email@example.com" not in cleaned
        assert "[EMAIL]" in cleaned
        
        # Should mask IP addresses
        assert "192.168.1.1" not in cleaned
        assert "[IP]" in cleaned
    
    def test_aggregate_for_b2b_insights(self):
        """Test B2B insights aggregation"""
        anonymized_data = [
            {"trade_type": "plumber", "action": "voice_input"},
            {"trade_type": "electrician", "action": "voice_input"},
            {"trade_type": "plumber", "action": "document_generated"},
            {"trade_type": "carpenter", "action": "voice_input"},
            {"trade_type": "plumber", "action": "image_analyzed"}
        ]
        
        insights = self.anonymization_service.aggregate_for_b2b_insights(
            anonymized_data,
            aggregation_type="trade_type"
        )
        
        assert insights["total_records"] == 5
        assert insights["aggregation_type"] == "trade_type"
        
        # Check aggregations
        assert insights["aggregations"]["plumber"] == 3
        assert insights["aggregations"]["electrician"] == 1
        assert insights["aggregations"]["carpenter"] == 1
        
        # Check percentages
        assert insights["percentages"]["plumber"] == 60.0
        assert insights["percentages"]["electrician"] == 20.0
        assert insights["percentages"]["carpenter"] == 20.0
    
    def test_validate_anonymization(self):
        """Test anonymization validation"""
        original = {
            "user_id": "user123",
            "phone_number": "+91-9876543210",
            "name": "राज कुमार",
            "trade_type": "plumber"
        }
        
        # Properly anonymized data
        anonymized_good = {
            "user_id_hash": "abc123...",
            "phone_hash": "def456...",
            "trade_type": "plumber"
        }
        
        # Improperly anonymized data (contains PII)
        anonymized_bad = {
            "user_id": "user123",  # Should be hashed
            "trade_type": "plumber"
        }
        
        assert self.anonymization_service.validate_anonymization(original, anonymized_good) is True
        assert self.anonymization_service.validate_anonymization(original, anonymized_bad) is False
    
    def test_hash_consistency(self):
        """Test that hashing is consistent for same input"""
        user_data1 = {"user_id": "user123", "phone_number": "+91-9876543210"}
        user_data2 = {"user_id": "user123", "phone_number": "+91-9876543210"}
        
        anonymized1 = self.anonymization_service.anonymize_user_data(user_data1)
        anonymized2 = self.anonymization_service.anonymize_user_data(user_data2)
        
        # Same input should produce same hashes
        assert anonymized1["user_id_hash"] == anonymized2["user_id_hash"]
        assert anonymized1["phone_hash"] == anonymized2["phone_hash"]


class TestPrivacyPreservingAnalytics:
    """Test privacy-preserving analytics system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        encryption_service = EncryptionService(master_key="test-key-12345")
        anonymization_service = AnonymizationService(encryption_service)
        self.analytics = PrivacyPreservingAnalytics(anonymization_service)
    
    def test_track_event(self):
        """Test event tracking with automatic anonymization"""
        event = {
            "user_id": "user123",
            "action": "voice_input",
            "timestamp": "2024-01-01T10:00:00Z"
        }
        
        self.analytics.track_event(event)
        
        # Should have one event in buffer
        assert len(self.analytics.analytics_buffer) == 1
        
        # Event should be anonymized
        tracked_event = self.analytics.analytics_buffer[0]
        assert "user_id" not in tracked_event
        assert "user_id_hash" in tracked_event
    
    def test_get_aggregated_insights(self):
        """Test getting aggregated insights"""
        events = [
            {"user_id": "user1", "action": "voice_input", "timestamp": "2024-01-01T10:00:00Z"},
            {"user_id": "user2", "action": "document_generated", "timestamp": "2024-01-01T10:01:00Z"},
            {"user_id": "user3", "action": "voice_input", "timestamp": "2024-01-01T10:02:00Z"},
        ]
        
        for event in events:
            self.analytics.track_event(event)
        
        insights = self.analytics.get_aggregated_insights(aggregation_type="action")
        
        assert insights["total_records"] == 3
        assert insights["aggregations"]["voice_input"] == 2
        assert insights["aggregations"]["document_generated"] == 1
    
    def test_clear_buffer(self):
        """Test clearing analytics buffer"""
        event = {"user_id": "user123", "action": "voice_input"}
        self.analytics.track_event(event)
        
        assert len(self.analytics.analytics_buffer) > 0
        
        self.analytics.clear_buffer()
        
        assert len(self.analytics.analytics_buffer) == 0
