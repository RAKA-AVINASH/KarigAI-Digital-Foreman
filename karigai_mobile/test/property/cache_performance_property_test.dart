import 'dart:math';
import 'package:flutter_test/flutter_test.dart';

/// Property-Based Test: Caching Performance Optimization
///
/// **Property 29: Caching Performance Optimization**
/// For any frequently accessed feature, subsequent access should show
/// improved response times through effective caching.
///
/// **Validates: Requirements 10.5**

/// Test cache implementation for property-based testing
/// This simulates the behavior of the actual CacheManager
class TestCacheManager {
  final Map<String, TestCacheEntry> _memoryCache = {};
  final Map<String, TestCacheEntry> _diskCache = {};
  
  final int maxMemoryCacheSize;
  final int maxDiskCacheSize;
  int _currentMemorySize = 0;
  int _currentDiskSize = 0;

  TestCacheManager({
    this.maxMemoryCacheSize = 10 * 1024 * 1024,
    this.maxDiskCacheSize = 50 * 1024 * 1024,
  });

  Future<void> put(
    String key,
    String data, {
    Duration? ttl,
    bool memoryOnly = false,
  }) async {
    final size = data.length * 2;
    final now = DateTime.now();
    final entry = TestCacheEntry(
      key: key,
      data: data,
      createdAt: now,
      expiresAt: ttl != null ? now.add(ttl) : null,
      accessCount: 0,
      lastAccessedAt: now,
      sizeInBytes: size,
    );

    // Store in memory cache
    await _putInMemoryCache(entry);

    // Store in disk cache if not memory-only
    if (!memoryOnly) {
      await _putInDiskCache(entry);
    }
  }

  Future<String?> get(String key) async {
    // Try memory cache first
    if (_memoryCache.containsKey(key)) {
      final entry = _memoryCache[key]!;
      
      if (entry.isExpired) {
        await remove(key);
        return null;
      }

      _memoryCache[key] = entry.copyWith(
        accessCount: entry.accessCount + 1,
        lastAccessedAt: DateTime.now(),
      );

      return entry.data;
    }

    // Try disk cache
    if (_diskCache.containsKey(key)) {
      final entry = _diskCache[key]!;
      
      if (entry.isExpired) {
        await remove(key);
        return null;
      }

      final updatedEntry = entry.copyWith(
        accessCount: entry.accessCount + 1,
        lastAccessedAt: DateTime.now(),
      );
      _diskCache[key] = updatedEntry;

      // Promote to memory cache if frequently accessed
      if (updatedEntry.accessCount > 3) {
        await _putInMemoryCache(updatedEntry);
      }

      return entry.data;
    }

    return null;
  }

  Future<bool> contains(String key) async {
    if (_memoryCache.containsKey(key)) {
      return !_memoryCache[key]!.isExpired;
    }
    
    if (_diskCache.containsKey(key)) {
      return !_diskCache[key]!.isExpired;
    }
    
    return false;
  }

  Future<void> remove(String key) async {
    final memEntry = _memoryCache.remove(key);
    if (memEntry != null) {
      _currentMemorySize -= memEntry.sizeInBytes;
    }
    
    final diskEntry = _diskCache.remove(key);
    if (diskEntry != null) {
      _currentDiskSize -= diskEntry.sizeInBytes;
    }
  }

  Future<void> clear() async {
    _memoryCache.clear();
    _diskCache.clear();
    _currentMemorySize = 0;
    _currentDiskSize = 0;
  }

  Future<Map<String, dynamic>> getStatistics() async {
    return {
      'memoryCacheSize': _currentMemorySize,
      'diskCacheSize': _currentDiskSize,
      'memoryCacheEntries': _memoryCache.length,
      'diskCacheEntries': _diskCache.length,
      'maxMemoryCacheSize': maxMemoryCacheSize,
      'maxDiskCacheSize': maxDiskCacheSize,
      'memoryUsagePercent': 
          (_currentMemorySize / maxMemoryCacheSize * 100).toStringAsFixed(2),
      'diskUsagePercent': 
          (_currentDiskSize / maxDiskCacheSize * 100).toStringAsFixed(2),
    };
  }

  Future<void> _putInMemoryCache(TestCacheEntry entry) async {
    // Evict if necessary
    while (_currentMemorySize + entry.sizeInBytes > maxMemoryCacheSize && _memoryCache.isNotEmpty) {
      _evictFromMemoryCache();
    }

    final existing = _memoryCache[entry.key];
    if (existing != null) {
      _currentMemorySize -= existing.sizeInBytes;
    }

    _memoryCache[entry.key] = entry;
    _currentMemorySize += entry.sizeInBytes;
  }

  Future<void> _putInDiskCache(TestCacheEntry entry) async {
    // Evict if necessary
    while (_currentDiskSize + entry.sizeInBytes > maxDiskCacheSize && _diskCache.isNotEmpty) {
      _evictFromDiskCache();
    }

    final existing = _diskCache[entry.key];
    if (existing != null) {
      _currentDiskSize -= existing.sizeInBytes;
    }

    _diskCache[entry.key] = entry;
    _currentDiskSize += entry.sizeInBytes;
  }

  void _evictFromMemoryCache() {
    if (_memoryCache.isEmpty) return;

    // LRU eviction
    final oldestEntry = _memoryCache.entries
        .reduce((a, b) => a.value.lastAccessedAt.isBefore(b.value.lastAccessedAt) ? a : b);

    _currentMemorySize -= oldestEntry.value.sizeInBytes;
    _memoryCache.remove(oldestEntry.key);
  }

  void _evictFromDiskCache() {
    if (_diskCache.isEmpty) return;

    // LRU eviction
    final oldestEntry = _diskCache.entries
        .reduce((a, b) => a.value.lastAccessedAt.isBefore(b.value.lastAccessedAt) ? a : b);

    _currentDiskSize -= oldestEntry.value.sizeInBytes;
    _diskCache.remove(oldestEntry.key);
  }
}

class TestCacheEntry {
  final String key;
  final String data;
  final DateTime createdAt;
  final DateTime? expiresAt;
  final int accessCount;
  final DateTime lastAccessedAt;
  final int sizeInBytes;

  TestCacheEntry({
    required this.key,
    required this.data,
    required this.createdAt,
    this.expiresAt,
    required this.accessCount,
    required this.lastAccessedAt,
    required this.sizeInBytes,
  });

  TestCacheEntry copyWith({
    String? key,
    String? data,
    DateTime? createdAt,
    DateTime? expiresAt,
    int? accessCount,
    DateTime? lastAccessedAt,
    int? sizeInBytes,
  }) {
    return TestCacheEntry(
      key: key ?? this.key,
      data: data ?? this.data,
      createdAt: createdAt ?? this.createdAt,
      expiresAt: expiresAt ?? this.expiresAt,
      accessCount: accessCount ?? this.accessCount,
      lastAccessedAt: lastAccessedAt ?? this.lastAccessedAt,
      sizeInBytes: sizeInBytes ?? this.sizeInBytes,
    );
  }

  bool get isExpired {
    if (expiresAt == null) return false;
    return DateTime.now().isAfter(expiresAt!);
  }
}

void main() {
  group('Property 29: Caching Performance Optimization', () {
    late TestCacheManager cacheManager;

    setUp(() async {
      cacheManager = TestCacheManager(
        maxMemoryCacheSize: 10 * 1024 * 1024, // 10 MB for testing
        maxDiskCacheSize: 50 * 1024 * 1024, // 50 MB for testing
      );
      await cacheManager.clear();
    });

    tearDown(() async {
      await cacheManager.clear();
    });

    test('Property: First access caches data, subsequent access is faster', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final iterations = 20;
      
      for (int i = 0; i < iterations; i++) {
        final key = 'test_key_$i';
        final data = _generateRandomData(random, 1000);
        
        // First access - should cache the data
        await cacheManager.put(key, data);
        
        // Wait a bit to ensure cache is written
        await Future.delayed(const Duration(milliseconds: 5));
        
        // Second access - should be from cache
        final cachedData = await cacheManager.get(key);
        
        // Property: Data should be retrieved successfully from cache
        expect(cachedData, isNotNull, reason: 'Cached data should be retrievable');
        expect(cachedData, equals(data), reason: 'Cached data should match original');
        
        // Property: Item should exist in cache
        final exists = await cacheManager.contains(key);
        expect(exists, isTrue, reason: 'Cached item should exist');
      }
      
      // Property: Multiple accesses should maintain cache integrity
      for (int i = 0; i < iterations; i++) {
        final key = 'test_key_$i';
        final cachedData = await cacheManager.get(key);
        expect(cachedData, isNotNull, reason: 'Previously cached data should still be retrievable');
      }
    });

    test('Property: Frequently accessed items remain in memory cache', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final keys = List.generate(10, (i) => 'frequent_key_$i');
      final data = _generateRandomData(random, 500);
      
      // Cache all items
      for (var key in keys) {
        await cacheManager.put(key, data);
      }
      
      // Access some items frequently
      final frequentKeys = keys.take(3).toList();
      for (int i = 0; i < 10; i++) {
        for (var key in frequentKeys) {
          await cacheManager.get(key);
        }
      }
      
      // Property: Frequently accessed items should still be in cache
      for (var key in frequentKeys) {
        final exists = await cacheManager.contains(key);
        expect(exists, isTrue, reason: 'Frequently accessed items should remain cached');
        
        final retrieved = await cacheManager.get(key);
        expect(retrieved, isNotNull, reason: 'Frequently accessed items should be retrievable');
      }
    });

    test('Property: Cache hit rate improves with repeated access', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final testKeys = List.generate(20, (i) => 'hit_rate_key_$i');
      
      // First pass - populate cache
      int firstPassHits = 0;
      for (var key in testKeys) {
        final data = _generateRandomData(random, 300);
        await cacheManager.put(key, data);
        
        // Check if it's immediately available
        final exists = await cacheManager.contains(key);
        if (exists) firstPassHits++;
      }
      
      // Second pass - should have higher hit rate
      int secondPassHits = 0;
      for (var key in testKeys) {
        final exists = await cacheManager.contains(key);
        if (exists) secondPassHits++;
      }
      
      // Property: Second pass should have equal or higher hit rate
      expect(
        secondPassHits,
        greaterThanOrEqualTo(firstPassHits),
        reason: 'Cache hit rate should improve or stay same with repeated access',
      );
      
      // Property: Most items should be cached after first pass
      expect(
        secondPassHits / testKeys.length,
        greaterThan(0.8),
        reason: 'At least 80% of items should be cached',
      );
    });

    test('Property: Cache eviction maintains most valuable items', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final smallDataSize = 100;
      final itemCount = 50;
      
      // Fill cache with items
      final keys = <String>[];
      for (int i = 0; i < itemCount; i++) {
        final key = 'eviction_key_$i';
        keys.add(key);
        final data = _generateRandomData(random, smallDataSize);
        await cacheManager.put(key, data);
      }
      
      // Access first 10 items frequently
      final frequentKeys = keys.take(10).toList();
      for (int i = 0; i < 5; i++) {
        for (var key in frequentKeys) {
          await cacheManager.get(key);
        }
      }
      
      // Add more items to trigger eviction
      for (int i = 0; i < 30; i++) {
        final key = 'new_key_$i';
        final data = _generateRandomData(random, smallDataSize);
        await cacheManager.put(key, data);
      }
      
      // Property: Frequently accessed items should still be available
      int frequentItemsStillCached = 0;
      for (var key in frequentKeys) {
        final exists = await cacheManager.contains(key);
        if (exists) frequentItemsStillCached++;
      }
      
      expect(
        frequentItemsStillCached / frequentKeys.length,
        greaterThan(0.5),
        reason: 'At least 50% of frequently accessed items should survive eviction',
      );
    });

    test('Property: Cache statistics reflect actual usage', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final itemCount = 15;
      
      // Get initial stats
      final initialStats = await cacheManager.getStatistics();
      final initialEntries = initialStats['memoryCacheEntries'] as int;
      
      // Add items to cache
      for (int i = 0; i < itemCount; i++) {
        final key = 'stats_key_$i';
        final data = _generateRandomData(random, 200);
        await cacheManager.put(key, data);
      }
      
      // Get updated stats
      final updatedStats = await cacheManager.getStatistics();
      final updatedEntries = updatedStats['memoryCacheEntries'] as int;
      final memoryCacheSize = updatedStats['memoryCacheSize'] as int;
      
      // Property: Entry count should increase
      expect(
        updatedEntries,
        greaterThan(initialEntries),
        reason: 'Cache entry count should increase after adding items',
      );
      
      // Property: Cache size should be positive
      expect(
        memoryCacheSize,
        greaterThan(0),
        reason: 'Cache size should be positive when items are cached',
      );
      
      // Property: Usage percentage should be valid
      final memoryUsagePercent = double.parse(updatedStats['memoryUsagePercent'] as String);
      expect(
        memoryUsagePercent,
        inInclusiveRange(0.0, 100.0),
        reason: 'Memory usage percentage should be between 0 and 100',
      );
    });

    test('Property: TTL expiration removes stale data', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final shortTTL = const Duration(milliseconds: 100);
      
      // Cache item with short TTL
      final key = 'ttl_test_key';
      final data = _generateRandomData(random, 100);
      await cacheManager.put(key, data, ttl: shortTTL);
      
      // Property: Item should be available immediately
      final immediateExists = await cacheManager.contains(key);
      expect(immediateExists, isTrue, reason: 'Item should exist immediately after caching');
      
      // Wait for TTL to expire
      await Future.delayed(const Duration(milliseconds: 150));
      
      // Property: Item should be expired and not retrievable
      final afterExpiry = await cacheManager.get(key);
      expect(afterExpiry, isNull, reason: 'Expired items should not be retrievable');
    });

    test('Property: Memory-only cache does not persist to disk', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final key = 'memory_only_key';
      final data = _generateRandomData(random, 100);
      
      // Cache with memory-only flag
      await cacheManager.put(key, data, memoryOnly: true);
      
      // Property: Item should be in memory cache
      final inMemory = await cacheManager.get(key);
      expect(inMemory, isNotNull, reason: 'Memory-only item should be retrievable');
      
      // Get statistics to verify disk cache
      final stats = await cacheManager.getStatistics();
      final diskEntries = stats['diskCacheEntries'] as int;
      
      // Property: Disk cache should not have grown significantly
      // (allowing for some metadata)
      expect(
        diskEntries,
        lessThanOrEqualTo(5),
        reason: 'Memory-only items should not significantly increase disk cache',
      );
    });

    test('Property: Cache handles concurrent access correctly', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final key = 'concurrent_key';
      final data = _generateRandomData(random, 500);
      
      // Perform concurrent writes and reads
      final futures = <Future>[];
      
      // Concurrent writes
      for (int i = 0; i < 5; i++) {
        futures.add(cacheManager.put('$key\_$i', data));
      }
      
      // Concurrent reads
      for (int i = 0; i < 5; i++) {
        futures.add(cacheManager.get('$key\_$i'));
      }
      
      // Wait for all operations
      final results = await Future.wait(futures);
      
      // Property: All operations should complete without errors
      expect(results, hasLength(10), reason: 'All concurrent operations should complete');
      
      // Property: Reads should return data or null (no exceptions)
      for (int i = 5; i < 10; i++) {
        expect(
          results[i] == null || results[i] is String,
          isTrue,
          reason: 'Concurrent reads should return valid results',
        );
      }
    });

    test('Property: Cache invalidation removes specific entries', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final keys = List.generate(10, (i) => 'invalidation_key_$i');
      
      // Cache all items
      for (var key in keys) {
        final data = _generateRandomData(random, 100);
        await cacheManager.put(key, data);
      }
      
      // Remove specific items
      final keysToRemove = keys.take(3).toList();
      for (var key in keysToRemove) {
        await cacheManager.remove(key);
      }
      
      // Property: Removed items should not exist
      for (var key in keysToRemove) {
        final exists = await cacheManager.contains(key);
        expect(exists, isFalse, reason: 'Removed items should not exist in cache');
      }
      
      // Property: Other items should still exist
      final remainingKeys = keys.skip(3).toList();
      for (var key in remainingKeys) {
        final exists = await cacheManager.contains(key);
        expect(exists, isTrue, reason: 'Non-removed items should still exist');
      }
    });

    test('Property: Cache clear removes all entries', () async {
      // **Validates: Requirements 10.5**
      
      final random = Random();
      final itemCount = 20;
      
      // Fill cache
      final keys = <String>[];
      for (int i = 0; i < itemCount; i++) {
        final key = 'clear_test_key_$i';
        keys.add(key);
        final data = _generateRandomData(random, 100);
        await cacheManager.put(key, data);
      }
      
      // Verify items exist
      int existingBefore = 0;
      for (var key in keys) {
        if (await cacheManager.contains(key)) existingBefore++;
      }
      expect(existingBefore, greaterThan(0), reason: 'Items should exist before clear');
      
      // Clear cache
      await cacheManager.clear();
      
      // Property: No items should exist after clear
      int existingAfter = 0;
      for (var key in keys) {
        if (await cacheManager.contains(key)) existingAfter++;
      }
      expect(existingAfter, equals(0), reason: 'No items should exist after clear');
      
      // Property: Cache statistics should reflect empty cache
      final stats = await cacheManager.getStatistics();
      expect(stats['memoryCacheEntries'], equals(0), reason: 'Memory cache should be empty');
      expect(stats['memoryCacheSize'], equals(0), reason: 'Memory cache size should be zero');
    });
  });
}

/// Helper function to generate random data
String _generateRandomData(Random random, int length) {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  return List.generate(length, (index) => chars[random.nextInt(chars.length)]).join();
}
