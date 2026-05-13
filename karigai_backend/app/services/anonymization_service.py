"""
Anonymization Service for KarigAI

Provides data anonymization capabilities for usage analytics and B2B insights.
Removes personal identifiers while preserving analytical value of the data.
"""

from typing import Dict, Any, List, Optional
import re
from datetime import datetime, timezone
from app.services.encryption_service import EncryptionService


class AnonymizationService:
    """Service for anonymizing user data for analytics"""
    
    def __init__(self, encryption_service: Optional[EncryptionService] = None):
        """
        Initialize anonymization service
        
        Args:
            encryption_service: Encryption service for hashing identifiers
        """
        self.encryption_service = encryption_service or EncryptionService()
        
        # Patterns for detecting PII
        self.phone_pattern = re.compile(r'\+?\d{10,15}')
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    def anonymize_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize user data for analytics
        
        Args:
            user_data: User data containing potential PII
            
        Returns:
            Anonymized user data with hashed identifiers
        """
        anonymized = {}
        
        # Hash user identifiers
        if "user_id" in user_data:
            anonymized["user_id_hash"] = self.encryption_service.hash_sensitive_field(
                str(user_data["user_id"])
            )
        
        if "phone_number" in user_data:
            anonymized["phone_hash"] = self.encryption_service.hash_sensitive_field(
                user_data["phone_number"]
            )
        
        # Preserve non-PII fields
        if "primary_language" in user_data:
            anonymized["primary_language"] = user_data["primary_language"]
        
        if "trade_type" in user_data:
            anonymized["trade_type"] = user_data["trade_type"]
        
        # Generalize location data (keep only city/state, remove specific address)
        if "location_data" in user_data:
            anonymized["location_region"] = self._generalize_location(user_data["location_data"])
        
        # Preserve timestamps for temporal analysis
        if "created_at" in user_data:
            anonymized["created_at"] = user_data["created_at"]
        
        if "updated_at" in user_data:
            anonymized["updated_at"] = user_data["updated_at"]
        
        return anonymized
    
    def anonymize_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize voice/interaction session data
        
        Args:
            session_data: Session data containing user interactions
            
        Returns:
            Anonymized session data
        """
        anonymized = {}
        
        # Hash session and user identifiers
        if "session_id" in session_data:
            anonymized["session_id_hash"] = self.encryption_service.hash_sensitive_field(
                str(session_data["session_id"])
            )
        
        if "user_id" in session_data:
            anonymized["user_id_hash"] = self.encryption_service.hash_sensitive_field(
                str(session_data["user_id"])
            )
        
        # Remove actual transcribed text, keep only metadata
        if "transcribed_text" in session_data:
            # Don't include actual text, only length for analysis
            anonymized["text_length"] = len(session_data["transcribed_text"])
        
        # Keep language and confidence for quality analysis
        if "language_detected" in session_data:
            anonymized["language_detected"] = session_data["language_detected"]
        
        if "confidence_score" in session_data:
            anonymized["confidence_score"] = session_data["confidence_score"]
        
        # Preserve timestamps
        if "created_at" in session_data:
            anonymized["created_at"] = session_data["created_at"]
        
        return anonymized
    
    def anonymize_analytics_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize analytics event data
        
        Args:
            event_data: Analytics event with user actions
            
        Returns:
            Anonymized event data
        """
        anonymized = {}
        
        # Hash user identifier
        if "user_id" in event_data:
            anonymized["user_id_hash"] = self.encryption_service.hash_sensitive_field(
                str(event_data["user_id"])
            )
        
        # Keep event type and action
        if "action" in event_data:
            anonymized["action"] = event_data["action"]
        
        if "event_type" in event_data:
            anonymized["event_type"] = event_data["event_type"]
        
        # Anonymize metadata
        if "metadata" in event_data:
            anonymized["metadata"] = self._anonymize_metadata(event_data["metadata"])
        
        # Preserve timestamp
        if "timestamp" in event_data:
            anonymized["timestamp"] = event_data["timestamp"]
        
        return anonymized
    
    def _anonymize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize metadata fields
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Anonymized metadata
        """
        anonymized = {}
        
        # Hash IP addresses
        if "ip_address" in metadata:
            anonymized["ip_hash"] = self.encryption_service.hash_sensitive_field(
                metadata["ip_address"]
            )
        
        # Hash device identifiers
        if "device_id" in metadata:
            anonymized["device_id_hash"] = self.encryption_service.hash_sensitive_field(
                metadata["device_id"]
            )
        
        # Keep non-identifying metadata
        non_pii_fields = ["session_duration", "feature_used", "error_occurred", 
                         "response_time", "network_type", "app_version"]
        
        for field in non_pii_fields:
            if field in metadata:
                anonymized[field] = metadata[field]
        
        return anonymized
    
    def _generalize_location(self, location_data: Any) -> str:
        """
        Generalize location data to city/state level
        
        Args:
            location_data: Location data (string or dict)
            
        Returns:
            Generalized location (city, state)
        """
        if isinstance(location_data, str):
            # Simple heuristic: extract city name if present
            # In production, use proper geocoding
            parts = location_data.split(',')
            if len(parts) >= 2:
                return f"{parts[-2].strip()}, {parts[-1].strip()}"
            return "Unknown"
        
        if isinstance(location_data, dict):
            city = location_data.get("city", "Unknown")
            state = location_data.get("state", "Unknown")
            return f"{city}, {state}"
        
        return "Unknown"
    
    def remove_pii_from_text(self, text: str) -> str:
        """
        Remove PII patterns from text
        
        Args:
            text: Text potentially containing PII
            
        Returns:
            Text with PII removed/masked
        """
        # Mask phone numbers
        text = self.phone_pattern.sub('[PHONE]', text)
        
        # Mask email addresses
        text = self.email_pattern.sub('[EMAIL]', text)
        
        # Mask IP addresses
        text = self.ip_pattern.sub('[IP]', text)
        
        return text
    
    def aggregate_for_b2b_insights(
        self,
        anonymized_data: List[Dict[str, Any]],
        aggregation_type: str = "trade_type"
    ) -> Dict[str, Any]:
        """
        Aggregate anonymized data for B2B insights
        
        Args:
            anonymized_data: List of anonymized data records
            aggregation_type: Type of aggregation (trade_type, language, region)
            
        Returns:
            Aggregated insights
        """
        insights = {
            "total_records": len(anonymized_data),
            "aggregation_type": aggregation_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "aggregations": {}
        }
        
        # Count by aggregation type
        counts = {}
        for record in anonymized_data:
            key = record.get(aggregation_type, "unknown")
            counts[key] = counts.get(key, 0) + 1
        
        insights["aggregations"] = counts
        
        # Calculate percentages
        total = len(anonymized_data)
        insights["percentages"] = {
            key: (count / total * 100) if total > 0 else 0
            for key, count in counts.items()
        }
        
        return insights
    
    def validate_anonymization(self, original: Dict[str, Any], anonymized: Dict[str, Any]) -> bool:
        """
        Validate that anonymization removed all PII
        
        Args:
            original: Original data
            anonymized: Anonymized data
            
        Returns:
            True if no PII detected in anonymized data
        """
        # Check that direct identifiers are not present
        pii_fields = ["user_id", "phone_number", "email", "address", "name"]
        
        for field in pii_fields:
            if field in anonymized:
                return False
        
        # Check that hashed versions exist for identifiers
        if "user_id" in original and "user_id_hash" not in anonymized:
            return False
        
        return True


class PrivacyPreservingAnalytics:
    """Analytics system that preserves user privacy"""
    
    def __init__(self, anonymization_service: AnonymizationService):
        """
        Initialize privacy-preserving analytics
        
        Args:
            anonymization_service: Service for anonymizing data
        """
        self.anonymization_service = anonymization_service
        self.analytics_buffer = []
    
    def track_event(self, event_data: Dict[str, Any]) -> None:
        """
        Track analytics event with automatic anonymization
        
        Args:
            event_data: Event data to track
        """
        anonymized = self.anonymization_service.anonymize_analytics_event(event_data)
        self.analytics_buffer.append(anonymized)
    
    def get_aggregated_insights(self, aggregation_type: str = "action") -> Dict[str, Any]:
        """
        Get aggregated insights from tracked events
        
        Args:
            aggregation_type: Type of aggregation
            
        Returns:
            Aggregated insights
        """
        return self.anonymization_service.aggregate_for_b2b_insights(
            self.analytics_buffer,
            aggregation_type
        )
    
    def clear_buffer(self) -> None:
        """Clear analytics buffer"""
        self.analytics_buffer = []
