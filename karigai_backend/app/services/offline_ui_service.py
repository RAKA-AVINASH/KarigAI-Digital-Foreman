"""
Offline UI Service for KarigAI

Provides feature availability indication and graceful degradation
for network-dependent features when offline.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

from app.core.offline_manager import get_offline_manager


class FeatureAvailability(Enum):
    """Feature availability status"""
    FULLY_AVAILABLE = "fully_available"
    OFFLINE_AVAILABLE = "offline_available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class NetworkStatus(Enum):
    """Network connectivity status"""
    ONLINE = "online"
    OFFLINE = "offline"
    SLOW = "slow"
    UNKNOWN = "unknown"


@dataclass
class FeatureStatus:
    """Status of a specific feature"""
    feature_name: str
    availability: FeatureAvailability
    is_cached: bool
    message: str
    limitations: List[str]
    fallback_available: bool


class OfflineUIService:
    """
    Service for managing offline feature indication and graceful degradation.
    
    Features:
    - Feature availability checking
    - Clear offline mode indicators
    - Graceful degradation for network-dependent features
    - User-friendly status messages
    """
    
    def __init__(self):
        self.offline_manager = get_offline_manager()
        self._network_status = NetworkStatus.UNKNOWN
        
        # Define feature capabilities
        self._feature_capabilities = {
            "voice_recognition": {
                "offline_capable": True,
                "requires_cache": True,
                "degraded_offline": True,
                "fallback": "basic_voice_recognition"
            },
            "document_generation": {
                "offline_capable": True,
                "requires_cache": True,
                "degraded_offline": False,
                "fallback": "basic_templates"
            },
            "learning_modules": {
                "offline_capable": True,
                "requires_cache": True,
                "degraded_offline": False,
                "fallback": "cached_content_only"
            },
            "vision_analysis": {
                "offline_capable": False,
                "requires_cache": False,
                "degraded_offline": False,
                "fallback": "basic_ocr"
            },
            "translation": {
                "offline_capable": True,
                "requires_cache": True,
                "degraded_offline": True,
                "fallback": "cached_translations"
            },
            "whatsapp_integration": {
                "offline_capable": False,
                "requires_cache": False,
                "degraded_offline": False,
                "fallback": "local_storage"
            },
            "sync_service": {
                "offline_capable": False,
                "requires_cache": False,
                "degraded_offline": False,
                "fallback": "queue_for_sync"
            }
        }
    
    def set_network_status(self, status: NetworkStatus):
        """Update the current network status"""
        self._network_status = status
    
    def get_network_status(self) -> NetworkStatus:
        """Get the current network status"""
        return self._network_status
    
    def check_feature_availability(self, feature_name: str) -> FeatureStatus:
        """
        Check the availability of a specific feature.
        
        Args:
            feature_name: Name of the feature to check
        
        Returns:
            FeatureStatus object with availability information
        """
        if feature_name not in self._feature_capabilities:
            return FeatureStatus(
                feature_name=feature_name,
                availability=FeatureAvailability.UNAVAILABLE,
                is_cached=False,
                message=f"Unknown feature: {feature_name}",
                limitations=["Feature not recognized"],
                fallback_available=False
            )
        
        capabilities = self._feature_capabilities[feature_name]
        
        # If online, most features are fully available
        if self._network_status == NetworkStatus.ONLINE:
            return FeatureStatus(
                feature_name=feature_name,
                availability=FeatureAvailability.FULLY_AVAILABLE,
                is_cached=self._is_feature_cached(feature_name),
                message=f"{feature_name} is fully available",
                limitations=[],
                fallback_available=False
            )
        
        # If offline, check capabilities
        if self._network_status == NetworkStatus.OFFLINE:
            if not capabilities["offline_capable"]:
                return FeatureStatus(
                    feature_name=feature_name,
                    availability=FeatureAvailability.UNAVAILABLE,
                    is_cached=False,
                    message=f"{feature_name} requires internet connection",
                    limitations=["Network connection required"],
                    fallback_available=capabilities.get("fallback") is not None
                )
            
            # Check if cached data is available
            is_cached = self._is_feature_cached(feature_name)
            
            if capabilities["requires_cache"] and not is_cached:
                return FeatureStatus(
                    feature_name=feature_name,
                    availability=FeatureAvailability.UNAVAILABLE,
                    is_cached=False,
                    message=f"{feature_name} requires cached data",
                    limitations=["No cached data available"],
                    fallback_available=capabilities.get("fallback") is not None
                )
            
            # Feature is available offline
            if capabilities["degraded_offline"]:
                return FeatureStatus(
                    feature_name=feature_name,
                    availability=FeatureAvailability.DEGRADED,
                    is_cached=is_cached,
                    message=f"{feature_name} available with limited functionality",
                    limitations=["Limited to cached data", "Some features unavailable"],
                    fallback_available=False
                )
            else:
                return FeatureStatus(
                    feature_name=feature_name,
                    availability=FeatureAvailability.OFFLINE_AVAILABLE,
                    is_cached=is_cached,
                    message=f"{feature_name} available offline",
                    limitations=["Using cached data"],
                    fallback_available=False
                )
        
        # Slow network - features available but may be slow
        if self._network_status == NetworkStatus.SLOW:
            return FeatureStatus(
                feature_name=feature_name,
                availability=FeatureAvailability.DEGRADED,
                is_cached=self._is_feature_cached(feature_name),
                message=f"{feature_name} available but may be slow",
                limitations=["Slow network connection"],
                fallback_available=capabilities.get("fallback") is not None
            )
        
        # Unknown status - assume degraded
        return FeatureStatus(
            feature_name=feature_name,
            availability=FeatureAvailability.DEGRADED,
            is_cached=self._is_feature_cached(feature_name),
            message=f"{feature_name} status unknown",
            limitations=["Network status unknown"],
            fallback_available=capabilities.get("fallback") is not None
        )
    
    def _is_feature_cached(self, feature_name: str) -> bool:
        """Check if a feature has cached data available"""
        # Check usage stats to see if feature has been used
        usage_stats = self.offline_manager.get_usage_stats()
        
        for stat in usage_stats:
            if feature_name in stat["feature"]:
                return True
        
        return False
    
    def get_all_feature_statuses(self) -> Dict[str, FeatureStatus]:
        """Get status for all features"""
        statuses = {}
        
        for feature_name in self._feature_capabilities.keys():
            statuses[feature_name] = self.check_feature_availability(feature_name)
        
        return statuses
    
    def get_offline_mode_indicator(self) -> Dict[str, Any]:
        """
        Get offline mode indicator information for UI display.
        
        Returns:
            Dictionary with offline mode information
        """
        all_statuses = self.get_all_feature_statuses()
        
        # Count features by availability
        fully_available = sum(1 for s in all_statuses.values() 
                             if s.availability == FeatureAvailability.FULLY_AVAILABLE)
        offline_available = sum(1 for s in all_statuses.values() 
                               if s.availability == FeatureAvailability.OFFLINE_AVAILABLE)
        degraded = sum(1 for s in all_statuses.values() 
                      if s.availability == FeatureAvailability.DEGRADED)
        unavailable = sum(1 for s in all_statuses.values() 
                         if s.availability == FeatureAvailability.UNAVAILABLE)
        
        # Determine overall mode
        if self._network_status == NetworkStatus.ONLINE:
            mode = "online"
            message = "All features available"
            color = "green"
        elif self._network_status == NetworkStatus.OFFLINE:
            mode = "offline"
            if offline_available + degraded > 0:
                message = f"{offline_available + degraded} features available offline"
                color = "yellow"
            else:
                message = "Limited functionality offline"
                color = "red"
        elif self._network_status == NetworkStatus.SLOW:
            mode = "slow"
            message = "Slow connection - some features may be delayed"
            color = "orange"
        else:
            mode = "unknown"
            message = "Checking connection..."
            color = "gray"
        
        return {
            "mode": mode,
            "network_status": self._network_status.value,
            "message": message,
            "color": color,
            "feature_counts": {
                "fully_available": fully_available,
                "offline_available": offline_available,
                "degraded": degraded,
                "unavailable": unavailable
            },
            "cache_stats": self.offline_manager.get_cache_stats()
        }
    
    def get_feature_limitations(self, feature_name: str) -> List[str]:
        """Get current limitations for a specific feature"""
        status = self.check_feature_availability(feature_name)
        return status.limitations
    
    def get_fallback_option(self, feature_name: str) -> Optional[str]:
        """Get fallback option for a feature if available"""
        if feature_name in self._feature_capabilities:
            return self._feature_capabilities[feature_name].get("fallback")
        return None
    
    def should_use_fallback(self, feature_name: str) -> bool:
        """Determine if fallback should be used for a feature"""
        status = self.check_feature_availability(feature_name)
        
        return (
            status.availability in [FeatureAvailability.UNAVAILABLE, FeatureAvailability.DEGRADED]
            and status.fallback_available
        )
    
    def get_user_message(self, feature_name: str) -> str:
        """Get user-friendly message about feature availability"""
        status = self.check_feature_availability(feature_name)
        
        message = status.message
        
        if status.limitations:
            message += f"\nLimitations: {', '.join(status.limitations)}"
        
        if status.fallback_available:
            fallback = self.get_fallback_option(feature_name)
            message += f"\nFallback available: {fallback}"
        
        return message
    
    def register_feature(self, feature_name: str, capabilities: Dict[str, Any]):
        """
        Register a new feature with its capabilities.
        
        Args:
            feature_name: Name of the feature
            capabilities: Dictionary with feature capabilities
        """
        self._feature_capabilities[feature_name] = capabilities
    
    def get_offline_ready_features(self) -> List[str]:
        """Get list of features that work offline"""
        return [
            name for name, caps in self._feature_capabilities.items()
            if caps["offline_capable"]
        ]
    
    def get_network_dependent_features(self) -> List[str]:
        """Get list of features that require network"""
        return [
            name for name, caps in self._feature_capabilities.items()
            if not caps["offline_capable"]
        ]


# Global offline UI service instance
_offline_ui_service: Optional[OfflineUIService] = None


def get_offline_ui_service() -> OfflineUIService:
    """Get the global offline UI service instance"""
    global _offline_ui_service
    if _offline_ui_service is None:
        _offline_ui_service = OfflineUIService()
    return _offline_ui_service
