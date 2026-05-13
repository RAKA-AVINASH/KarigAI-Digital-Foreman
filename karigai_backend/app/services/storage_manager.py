"""
Storage Manager for KarigAI

Manages storage prioritization, automatic cleanup, and capacity monitoring.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from app.core.offline_manager import get_offline_manager


class StoragePriority(Enum):
    """Storage priority levels"""
    CRITICAL = 100  # Must keep (user data, recent work)
    HIGH = 75  # Important (frequently used features)
    MEDIUM = 50  # Normal (cached content)
    LOW = 25  # Optional (rarely used)
    DISPOSABLE = 0  # Can be deleted anytime


@dataclass
class StorageItem:
    """Represents an item in storage"""
    key: str
    size_bytes: int
    priority: int
    access_count: int
    last_accessed: datetime
    created_at: datetime
    category: str


class StorageManager:
    """
    Manages storage with usage-based prioritization and automatic cleanup.
    
    Features:
    - Usage-based prioritization
    - Automatic cleanup of least-used content
    - Storage capacity monitoring and alerts
    - Intelligent eviction strategies
    """
    
    def __init__(self, warning_threshold: float = 0.8, critical_threshold: float = 0.95):
        """
        Initialize the storage manager.
        
        Args:
            warning_threshold: Percentage of capacity that triggers warning (0.0-1.0)
            critical_threshold: Percentage of capacity that triggers critical alert (0.0-1.0)
        """
        self.offline_manager = get_offline_manager()
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        # Category priorities
        self._category_priorities = {
            "user_data": StoragePriority.CRITICAL.value,
            "recent_work": StoragePriority.CRITICAL.value,
            "voice_recognition": StoragePriority.HIGH.value,
            "document_generation": StoragePriority.HIGH.value,
            "learning_modules": StoragePriority.HIGH.value,
            "equipment_data": StoragePriority.MEDIUM.value,
            "translations": StoragePriority.MEDIUM.value,
            "templates": StoragePriority.MEDIUM.value,
            "cache": StoragePriority.LOW.value,
            "temp": StoragePriority.DISPOSABLE.value
        }
    
    def get_storage_status(self) -> Dict[str, Any]:
        """
        Get current storage status.
        
        Returns:
            Dictionary with storage information
        """
        cache_stats = self.offline_manager.get_cache_stats()
        
        total_size = cache_stats["total_size_bytes"]
        max_size = self.offline_manager.max_cache_size
        usage_percentage = (total_size / max_size) * 100 if max_size > 0 else 0
        
        # Determine status level
        if usage_percentage >= self.critical_threshold * 100:
            status_level = "critical"
            message = "Storage critically full - cleanup required"
        elif usage_percentage >= self.warning_threshold * 100:
            status_level = "warning"
            message = "Storage usage high - consider cleanup"
        else:
            status_level = "normal"
            message = "Storage usage normal"
        
        return {
            "status_level": status_level,
            "message": message,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_bytes": max_size,
            "max_size_mb": max_size / (1024 * 1024),
            "usage_percentage": usage_percentage,
            "available_bytes": max_size - total_size,
            "available_mb": (max_size - total_size) / (1024 * 1024),
            "warning_threshold": self.warning_threshold * 100,
            "critical_threshold": self.critical_threshold * 100
        }
    
    def should_cleanup(self) -> bool:
        """Check if cleanup should be performed"""
        status = self.get_storage_status()
        return status["usage_percentage"] >= self.warning_threshold * 100
    
    def get_cleanup_candidates(self, target_free_percentage: float = 0.3) -> List[StorageItem]:
        """
        Get list of items that can be cleaned up, prioritized by least important.
        
        Args:
            target_free_percentage: Target percentage of free space (0.0-1.0)
        
        Returns:
            List of storage items sorted by cleanup priority (least important first)
        """
        cache_stats = self.offline_manager.get_cache_stats()
        entries = cache_stats.get("entries", [])
        
        # Convert to StorageItem objects
        storage_items = []
        for entry in entries:
            # Determine category from key
            category = self._determine_category(entry["key"])
            
            item = StorageItem(
                key=entry["key"],
                size_bytes=entry["size_bytes"],
                priority=entry["priority"],
                access_count=entry["access_count"],
                last_accessed=datetime.fromisoformat(entry["last_accessed"]),
                created_at=datetime.now(),  # Not stored in cache stats
                category=category
            )
            storage_items.append(item)
        
        # Calculate cleanup score for each item (lower score = higher cleanup priority)
        scored_items = []
        for item in storage_items:
            score = self._calculate_cleanup_score(item)
            scored_items.append((score, item))
        
        # Sort by score (lowest first = highest cleanup priority)
        scored_items.sort(key=lambda x: x[0])
        
        # Calculate how much space we need to free
        max_size = self.offline_manager.max_cache_size
        current_size = cache_stats["total_size_bytes"]
        target_size = max_size * (1 - target_free_percentage)
        space_to_free = current_size - target_size
        
        # Select items until we have enough space
        candidates = []
        freed_space = 0
        
        for score, item in scored_items:
            if freed_space >= space_to_free:
                break
            candidates.append(item)
            freed_space += item.size_bytes
        
        return candidates
    
    def _determine_category(self, key: str) -> str:
        """Determine the category of an item from its key"""
        key_lower = key.lower()
        
        if "user" in key_lower or "profile" in key_lower:
            return "user_data"
        elif "voice" in key_lower or "speech" in key_lower:
            return "voice_recognition"
        elif "document" in key_lower or "invoice" in key_lower:
            return "document_generation"
        elif "learning" in key_lower or "course" in key_lower:
            return "learning_modules"
        elif "equipment" in key_lower or "device" in key_lower:
            return "equipment_data"
        elif "translation" in key_lower or "language" in key_lower:
            return "translations"
        elif "template" in key_lower:
            return "templates"
        elif "cache" in key_lower:
            return "cache"
        elif "temp" in key_lower:
            return "temp"
        else:
            return "cache"
    
    def _calculate_cleanup_score(self, item: StorageItem) -> float:
        """
        Calculate cleanup score for an item.
        Lower score = higher cleanup priority.
        
        Factors:
        - Category priority (most important)
        - Access frequency
        - Recency of access
        - Item priority
        - Size (larger items slightly preferred for cleanup to free more space)
        """
        # Base score from category
        category_priority = self._category_priorities.get(item.category, StoragePriority.MEDIUM.value)
        
        # Time since last access (in days)
        days_since_access = (datetime.now() - item.last_accessed).days + 1
        recency_factor = 1 / days_since_access  # More recent = higher score
        
        # Access frequency factor
        frequency_factor = item.access_count
        
        # Item priority
        priority_factor = item.priority
        
        # Size factor (slightly prefer larger items for cleanup to free more space)
        size_factor = -0.01 * (item.size_bytes / (1024 * 1024))  # Negative to slightly reduce score
        
        # Calculate final score
        score = (
            category_priority * 10 +  # Category is most important
            priority_factor * 5 +  # Item priority
            frequency_factor * 3 +  # Access frequency
            recency_factor * 50 +  # Recency
            size_factor  # Size (minor factor)
        )
        
        return score
    
    def perform_cleanup(self, target_free_percentage: float = 0.3) -> Dict[str, Any]:
        """
        Perform automatic cleanup of least-used content.
        
        Args:
            target_free_percentage: Target percentage of free space (0.0-1.0)
        
        Returns:
            Dictionary with cleanup results
        """
        initial_status = self.get_storage_status()
        
        if not self.should_cleanup():
            return {
                "performed": False,
                "reason": "Cleanup not needed",
                "initial_usage": initial_status["usage_percentage"],
                "items_removed": 0,
                "space_freed_mb": 0
            }
        
        # Get cleanup candidates
        candidates = self.get_cleanup_candidates(target_free_percentage)
        
        # Remove items
        removed_count = 0
        space_freed = 0
        removed_items = []
        
        for item in candidates:
            if self.offline_manager.remove_from_cache(item.key):
                removed_count += 1
                space_freed += item.size_bytes
                removed_items.append({
                    "key": item.key,
                    "category": item.category,
                    "size_mb": item.size_bytes / (1024 * 1024)
                })
        
        final_status = self.get_storage_status()
        
        return {
            "performed": True,
            "reason": "Storage cleanup completed",
            "initial_usage": initial_status["usage_percentage"],
            "final_usage": final_status["usage_percentage"],
            "items_removed": removed_count,
            "space_freed_bytes": space_freed,
            "space_freed_mb": space_freed / (1024 * 1024),
            "removed_items": removed_items[:10]  # First 10 items
        }
    
    def get_storage_alerts(self) -> List[Dict[str, Any]]:
        """Get storage-related alerts"""
        alerts = []
        status = self.get_storage_status()
        
        if status["status_level"] == "critical":
            alerts.append({
                "level": "critical",
                "message": "Storage critically full - immediate cleanup required",
                "usage_percentage": status["usage_percentage"],
                "action": "perform_cleanup"
            })
        elif status["status_level"] == "warning":
            alerts.append({
                "level": "warning",
                "message": "Storage usage high - cleanup recommended",
                "usage_percentage": status["usage_percentage"],
                "action": "consider_cleanup"
            })
        
        # Check for items that haven't been accessed in a long time
        cache_stats = self.offline_manager.get_cache_stats()
        old_items = []
        
        for entry in cache_stats.get("entries", []):
            last_accessed = datetime.fromisoformat(entry["last_accessed"])
            days_old = (datetime.now() - last_accessed).days
            
            if days_old > 30:  # Not accessed in 30 days
                old_items.append(entry["key"])
        
        if old_items:
            alerts.append({
                "level": "info",
                "message": f"{len(old_items)} items not accessed in 30+ days",
                "action": "review_old_items",
                "item_count": len(old_items)
            })
        
        return alerts
    
    def get_storage_recommendations(self) -> List[str]:
        """Get storage optimization recommendations"""
        recommendations = []
        status = self.get_storage_status()
        
        if status["usage_percentage"] > 80:
            recommendations.append("Consider performing cleanup to free up space")
        
        # Check for large items
        cache_stats = self.offline_manager.get_cache_stats()
        large_items = [e for e in cache_stats.get("entries", []) 
                      if e["size_bytes"] > 5 * 1024 * 1024]  # > 5MB
        
        if large_items:
            recommendations.append(f"Found {len(large_items)} large items (>5MB) - review if needed")
        
        # Check for rarely accessed items
        rarely_accessed = [e for e in cache_stats.get("entries", []) 
                          if e["access_count"] < 2]
        
        if rarely_accessed and len(rarely_accessed) > 10:
            recommendations.append(f"{len(rarely_accessed)} items rarely accessed - consider cleanup")
        
        if not recommendations:
            recommendations.append("Storage is well optimized")
        
        return recommendations
    
    def set_category_priority(self, category: str, priority: int):
        """Set priority for a category"""
        self._category_priorities[category] = priority
    
    def get_category_priorities(self) -> Dict[str, int]:
        """Get all category priorities"""
        return self._category_priorities.copy()


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get the global storage manager instance"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager
