"""
Offline Data Management System for KarigAI

This module provides offline data storage, caching, and synchronization
capabilities for the KarigAI system to support offline functionality.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import sqlite3
import hashlib
import os
from pathlib import Path
from collections import defaultdict
import threading


@dataclass
class CacheEntry:
    """Represents a cached data entry"""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    priority: int = 0  # Higher priority = more important to keep
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class SyncQueueItem:
    """Represents an item waiting to be synchronized"""
    item_id: str
    item_type: str  # 'document', 'voice_session', 'learning_progress', etc.
    data: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    last_retry: Optional[datetime] = None


class OfflineManager:
    """
    Manages offline data storage, caching, and synchronization.
    
    Features:
    - Local data storage with SQLite
    - Intelligent cache eviction based on usage patterns
    - Data synchronization queue for online/offline transitions
    - Storage capacity monitoring
    """
    
    def __init__(self, cache_dir: str = "./cache", max_cache_size_mb: int = 500):
        """
        Initialize the offline manager.
        
        Args:
            cache_dir: Directory for cache storage
            max_cache_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # Convert to bytes
        self.cache_db_path = self.cache_dir / "offline_cache.db"
        
        # In-memory cache for fast access
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.Lock()
        
        # Sync queue for offline-generated content
        self._sync_queue: List[SyncQueueItem] = []
        self._sync_lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        self._load_cache_metadata()
        self._load_sync_queue()
    
    def _init_database(self):
        """Initialize the offline cache database"""
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()
        
        # Cache metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_metadata (
                key TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                size_bytes INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 0,
                file_path TEXT
            )
        """)
        
        # Sync queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                item_id TEXT PRIMARY KEY,
                item_type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_retry TEXT
            )
        """)
        
        # Usage statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                feature TEXT PRIMARY KEY,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                total_size_bytes INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_cache_metadata(self):
        """Load cache metadata from database into memory"""
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cache_metadata")
        rows = cursor.fetchall()
        
        for row in rows:
            key, data_type, created_at, last_accessed, access_count, size_bytes, priority, file_path = row
            
            # Load data from file if it exists
            data = None
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
            
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.fromisoformat(created_at),
                last_accessed=datetime.fromisoformat(last_accessed),
                access_count=access_count,
                size_bytes=size_bytes,
                priority=priority
            )
            self._memory_cache[key] = entry
        
        conn.close()
    
    def _load_sync_queue(self):
        """Load sync queue from database into memory"""
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM sync_queue")
        rows = cursor.fetchall()
        
        for row in rows:
            item_id, item_type, data_json, created_at, retry_count, last_retry = row
            
            # Parse JSON data
            data = json.loads(data_json)
            
            # Create sync queue item
            item = SyncQueueItem(
                item_id=item_id,
                item_type=item_type,
                data=data,
                created_at=datetime.fromisoformat(created_at),
                retry_count=retry_count,
                last_retry=datetime.fromisoformat(last_retry) if last_retry else None
            )
            
            self._sync_queue.append(item)
        
        conn.close()
    
    def cache_data(self, key: str, data: Any, data_type: str = "general", priority: int = 0) -> bool:
        """
        Cache data for offline access.
        
        Args:
            key: Unique identifier for the cached data
            data: Data to cache (must be JSON-serializable)
            data_type: Type of data being cached
            priority: Priority level (higher = more important)
        
        Returns:
            True if caching was successful
        """
        with self._cache_lock:
            try:
                # Serialize data
                json_data = json.dumps(data)
                size_bytes = len(json_data.encode('utf-8'))
                
                # Check if we need to evict cache
                current_size = self.get_cache_size()
                if current_size + size_bytes > self.max_cache_size:
                    self._evict_cache(size_bytes)
                
                # Save to file
                file_path = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"
                with open(file_path, 'w') as f:
                    f.write(json_data)
                
                # Load back from JSON to ensure consistency (what we store is what we get)
                with open(file_path, 'r') as f:
                    loaded_data = json.load(f)
                
                # Create cache entry with the loaded data (ensures JSON round-trip consistency)
                entry = CacheEntry(
                    key=key,
                    data=loaded_data,  # Use loaded data instead of original
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=0,
                    size_bytes=size_bytes,
                    priority=priority
                )
                
                self._memory_cache[key] = entry
                
                # Save metadata to database
                conn = sqlite3.connect(str(self.cache_db_path))
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cache_metadata 
                    (key, data_type, created_at, last_accessed, access_count, size_bytes, priority, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key, data_type, entry.created_at.isoformat(), entry.last_accessed.isoformat(),
                    entry.access_count, size_bytes, priority, str(file_path)
                ))
                conn.commit()
                conn.close()
                
                return True
            except Exception as e:
                print(f"Error caching data: {e}")
                return False
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data.
        
        Args:
            key: Unique identifier for the cached data
        
        Returns:
            Cached data or None if not found
        """
        with self._cache_lock:
            if key not in self._memory_cache:
                return None
            
            entry = self._memory_cache[key]
            entry.update_access()
            
            # Update access statistics in database
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cache_metadata 
                SET last_accessed = ?, access_count = ?
                WHERE key = ?
            """, (entry.last_accessed.isoformat(), entry.access_count, key))
            conn.commit()
            conn.close()
            
            return entry.data
    
    def is_cached(self, key: str) -> bool:
        """Check if data is cached"""
        return key in self._memory_cache
    
    def remove_from_cache(self, key: str) -> bool:
        """Remove data from cache"""
        with self._cache_lock:
            if key not in self._memory_cache:
                return False
            
            entry = self._memory_cache[key]
            
            # Remove file
            file_path = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"
            if file_path.exists():
                file_path.unlink()
            
            # Remove from memory
            del self._memory_cache[key]
            
            # Remove from database
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_metadata WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            
            return True
    
    def _evict_cache(self, required_space: int):
        """
        Evict cache entries to free up space.
        Uses intelligent eviction based on usage patterns.
        
        Args:
            required_space: Space needed in bytes
        """
        # Calculate eviction score for each entry
        # Lower score = more likely to be evicted
        entries_with_scores = []
        
        for key, entry in self._memory_cache.items():
            # Score based on: priority, access frequency, recency
            age_days = (datetime.now() - entry.created_at).days + 1
            recency_days = (datetime.now() - entry.last_accessed).days + 1
            
            score = (
                entry.priority * 100 +  # Priority is most important
                entry.access_count * 10 +  # Frequency matters
                (1 / recency_days) * 50  # Recent access matters
            )
            
            entries_with_scores.append((key, entry, score))
        
        # Sort by score (lowest first)
        entries_with_scores.sort(key=lambda x: x[2])
        
        # Evict entries until we have enough space
        freed_space = 0
        for key, entry, score in entries_with_scores:
            if freed_space >= required_space:
                break
            
            self.remove_from_cache(key)
            freed_space += entry.size_bytes
    
    def get_cache_size(self) -> int:
        """Get current cache size in bytes"""
        return sum(entry.size_bytes for entry in self._memory_cache.values())
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_size = self.get_cache_size()
        entry_count = len(self._memory_cache)
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_cache_size / (1024 * 1024),
            "usage_percentage": (total_size / self.max_cache_size) * 100,
            "entry_count": entry_count,
            "entries": [
                {
                    "key": entry.key,
                    "size_bytes": entry.size_bytes,
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed.isoformat(),
                    "priority": entry.priority
                }
                for entry in sorted(
                    self._memory_cache.values(),
                    key=lambda e: e.access_count,
                    reverse=True
                )[:10]  # Top 10 most accessed
            ]
        }
    
    def add_to_sync_queue(self, item_id: str, item_type: str, data: Dict[str, Any]) -> bool:
        """
        Add an item to the synchronization queue.
        
        Args:
            item_id: Unique identifier for the item
            item_type: Type of item (document, voice_session, etc.)
            data: Item data to sync
        
        Returns:
            True if added successfully
        """
        with self._sync_lock:
            try:
                # Serialize and deserialize to ensure JSON consistency
                json_data = json.dumps(data)
                normalized_data = json.loads(json_data)
                
                item = SyncQueueItem(
                    item_id=item_id,
                    item_type=item_type,
                    data=normalized_data,  # Use normalized data
                    created_at=datetime.now()
                )
                
                self._sync_queue.append(item)
                
                # Save to database
                conn = sqlite3.connect(str(self.cache_db_path))
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO sync_queue 
                    (item_id, item_type, data, created_at, retry_count, last_retry)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item_id, item_type, json_data,  # Use already serialized data
                    item.created_at.isoformat(), 0, None
                ))
                conn.commit()
                conn.close()
                
                return True
            except Exception as e:
                print(f"Error adding to sync queue: {e}")
                return False
    
    def get_sync_queue(self) -> List[SyncQueueItem]:
        """Get all items in the sync queue"""
        with self._sync_lock:
            return self._sync_queue.copy()
    
    def remove_from_sync_queue(self, item_id: str) -> bool:
        """Remove an item from the sync queue after successful sync"""
        with self._sync_lock:
            self._sync_queue = [item for item in self._sync_queue if item.item_id != item_id]
            
            # Remove from database
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_queue WHERE item_id = ?", (item_id,))
            conn.commit()
            conn.close()
            
            return True
    
    def mark_sync_retry(self, item_id: str) -> bool:
        """Mark a sync item for retry"""
        with self._sync_lock:
            for item in self._sync_queue:
                if item.item_id == item_id:
                    item.retry_count += 1
                    item.last_retry = datetime.now()
                    
                    # Update database
                    conn = sqlite3.connect(str(self.cache_db_path))
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE sync_queue 
                        SET retry_count = ?, last_retry = ?
                        WHERE item_id = ?
                    """, (item.retry_count, item.last_retry.isoformat(), item_id))
                    conn.commit()
                    conn.close()
                    
                    return True
            
            return False
    
    def clear_cache(self):
        """Clear all cached data"""
        with self._cache_lock:
            # Remove all files
            for entry in self._memory_cache.values():
                file_path = self.cache_dir / f"{hashlib.md5(entry.key.encode()).hexdigest()}.json"
                if file_path.exists():
                    file_path.unlink()
            
            # Clear memory cache
            self._memory_cache.clear()
            
            # Clear database
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_metadata")
            conn.commit()
            conn.close()
    
    def update_usage_stats(self, feature: str, size_bytes: int = 0):
        """Update usage statistics for a feature"""
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO usage_stats (feature, access_count, last_accessed, total_size_bytes)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(feature) DO UPDATE SET
                access_count = access_count + 1,
                last_accessed = ?,
                total_size_bytes = total_size_bytes + ?
        """, (feature, datetime.now().isoformat(), size_bytes, datetime.now().isoformat(), size_bytes))
        
        conn.commit()
        conn.close()
    
    def get_usage_stats(self) -> List[Dict[str, Any]]:
        """Get usage statistics for all features"""
        conn = sqlite3.connect(str(self.cache_db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT feature, access_count, last_accessed, total_size_bytes
            FROM usage_stats
            ORDER BY access_count DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "feature": row[0],
                "access_count": row[1],
                "last_accessed": row[2],
                "total_size_bytes": row[3]
            }
            for row in rows
        ]


# Global offline manager instance
_offline_manager: Optional[OfflineManager] = None


def get_offline_manager() -> OfflineManager:
    """Get the global offline manager instance"""
    global _offline_manager
    if _offline_manager is None:
        _offline_manager = OfflineManager()
    return _offline_manager
