"""Tests for Graph Query Cache.

Phase 7.1.3-04: Query & Tool Caching.

Tests cover:
- Cache hit/miss behavior
- TTL expiry
- Pool-scoped invalidation
- Graph hash invalidation
- LRU eviction
- Cache statistics
"""

import time
from unittest import TestCase, main

from alphaswarm_sol.cache.graph_queries import (
    GraphQueryCache,
    CachedQueryResult,
    compute_cache_key,
)


class TestCacheKeyGeneration(TestCase):
    """Tests for deterministic cache key generation."""

    def test_basic_key_generation(self):
        """Test generating a cache key from basic parameters."""
        key = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions WHERE visibility = public",
        )
        self.assertEqual(len(key), 24)
        self.assertTrue(all(c in "0123456789abcdef" for c in key))

    def test_deterministic_keys(self):
        """Test that same inputs produce same keys."""
        key1 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
        )
        key2 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
        )
        self.assertEqual(key1, key2)

    def test_different_graph_different_key(self):
        """Test that different graph hashes produce different keys."""
        key1 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
        )
        key2 = compute_cache_key(
            graph_hash="xyz789uvw012",
            query_text="FIND functions",
        )
        self.assertNotEqual(key1, key2)

    def test_different_query_different_key(self):
        """Test that different queries produce different keys."""
        key1 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
        )
        key2 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND contracts",
        )
        self.assertNotEqual(key1, key2)

    def test_overlay_affects_key(self):
        """Test that overlay hash affects cache key."""
        key1 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
            overlay_hash=None,
        )
        key2 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
            overlay_hash="overlay123",
        )
        self.assertNotEqual(key1, key2)

    def test_pool_affects_key(self):
        """Test that pool_id affects cache key."""
        key1 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
            pool_id=None,
        )
        key2 = compute_cache_key(
            graph_hash="abc123def456",
            query_text="FIND functions",
            pool_id="pool-001",
        )
        self.assertNotEqual(key1, key2)


class TestGraphQueryCacheBasics(TestCase):
    """Tests for basic cache operations."""

    def setUp(self):
        """Set up test cache."""
        self.cache = GraphQueryCache(ttl_seconds=300, max_entries=100)

    def test_cache_enabled_by_default(self):
        """Test cache is enabled by default."""
        self.assertTrue(self.cache.is_enabled)

    def test_cache_can_be_disabled(self):
        """Test cache can be disabled."""
        disabled = GraphQueryCache(enabled=False)
        self.assertFalse(disabled.is_enabled)

    def test_put_and_get(self):
        """Test basic put and get."""
        result = {"nodes": [{"id": "n1"}], "findings": []}
        key = self.cache.put(
            graph_hash="abc123def456",
            query_text="FIND functions",
            result=result,
        )

        self.assertGreater(len(key), 0)

        cached = self.cache.get(
            graph_hash="abc123def456",
            query_text="FIND functions",
        )
        self.assertEqual(cached, result)

    def test_get_miss_returns_none(self):
        """Test cache miss returns None."""
        cached = self.cache.get(
            graph_hash="nonexistent",
            query_text="FIND functions",
        )
        self.assertIsNone(cached)

    def test_stats_track_hits(self):
        """Test stats track cache hits."""
        self.cache.put("hash1", "query1", {"result": 1})

        self.cache.get("hash1", "query1")  # Hit
        self.cache.get("hash1", "query1")  # Hit
        self.cache.get("hash1", "query2")  # Miss

        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["writes"], 1)

    def test_disabled_cache_no_ops(self):
        """Test disabled cache performs no operations."""
        disabled = GraphQueryCache(enabled=False)

        key = disabled.put("hash1", "query1", {"result": 1})
        self.assertEqual(key, "")

        cached = disabled.get("hash1", "query1")
        self.assertIsNone(cached)


class TestGraphQueryCacheTTL(TestCase):
    """Tests for TTL-based expiration."""

    def test_ttl_expiry(self):
        """Test entries expire after TTL."""
        # Very short TTL for testing
        cache = GraphQueryCache(ttl_seconds=1, max_entries=100)

        cache.put("hash1", "query1", {"result": 1})

        # Should be available immediately
        self.assertIsNotNone(cache.get("hash1", "query1"))

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should be expired
        self.assertIsNone(cache.get("hash1", "query1"))

    def test_clear_expired(self):
        """Test clear_expired removes expired entries."""
        cache = GraphQueryCache(ttl_seconds=1, max_entries=100)

        cache.put("hash1", "query1", {"result": 1})
        cache.put("hash2", "query2", {"result": 2})

        # Wait for expiry
        time.sleep(1.1)

        # Both should be expired
        removed = cache.clear_expired()
        self.assertEqual(removed, 2)

        stats = cache.get_stats()
        self.assertEqual(stats["current_entries"], 0)
        self.assertEqual(stats["expired_cleared"], 2)

    def test_no_ttl_never_expires(self):
        """Test entries with TTL=0 never expire."""
        cache = GraphQueryCache(ttl_seconds=0, max_entries=100)

        cache.put("hash1", "query1", {"result": 1})

        # Should not expire
        self.assertIsNotNone(cache.get("hash1", "query1"))


class TestGraphQueryCacheInvalidation(TestCase):
    """Tests for cache invalidation."""

    def setUp(self):
        """Set up test cache."""
        self.cache = GraphQueryCache(ttl_seconds=300, max_entries=100)

    def test_invalidate_specific_key(self):
        """Test invalidating a specific cache entry."""
        key = self.cache.put("hash1", "query1", {"result": 1})
        self.cache.put("hash1", "query2", {"result": 2})

        self.assertTrue(self.cache.invalidate(key))
        self.assertIsNone(self.cache.get("hash1", "query1"))
        self.assertIsNotNone(self.cache.get("hash1", "query2"))

    def test_invalidate_nonexistent(self):
        """Test invalidating nonexistent key returns False."""
        self.assertFalse(self.cache.invalidate("nonexistent"))

    def test_invalidate_pool(self):
        """Test invalidating all entries for a pool."""
        self.cache.put("hash1", "query1", {"result": 1}, pool_id="pool-A")
        self.cache.put("hash1", "query2", {"result": 2}, pool_id="pool-A")
        self.cache.put("hash1", "query3", {"result": 3}, pool_id="pool-B")

        removed = self.cache.invalidate_pool("pool-A")
        self.assertEqual(removed, 2)

        # Pool-A entries gone
        self.assertIsNone(self.cache.get("hash1", "query1", pool_id="pool-A"))
        self.assertIsNone(self.cache.get("hash1", "query2", pool_id="pool-A"))

        # Pool-B entry remains
        self.assertIsNotNone(self.cache.get("hash1", "query3", pool_id="pool-B"))

    def test_invalidate_graph(self):
        """Test invalidating all entries for a graph hash."""
        self.cache.put("hash-A", "query1", {"result": 1})
        self.cache.put("hash-A", "query2", {"result": 2})
        self.cache.put("hash-B", "query3", {"result": 3})

        removed = self.cache.invalidate_graph("hash-A")
        self.assertEqual(removed, 2)

        # hash-A entries gone
        self.assertIsNone(self.cache.get("hash-A", "query1"))
        self.assertIsNone(self.cache.get("hash-A", "query2"))

        # hash-B entry remains
        self.assertIsNotNone(self.cache.get("hash-B", "query3"))

    def test_clear_all(self):
        """Test clearing all cache entries."""
        self.cache.put("hash1", "query1", {"result": 1})
        self.cache.put("hash2", "query2", {"result": 2})
        self.cache.put("hash3", "query3", {"result": 3})

        removed = self.cache.clear_all()
        self.assertEqual(removed, 3)

        stats = self.cache.get_stats()
        self.assertEqual(stats["current_entries"], 0)


class TestGraphQueryCacheEviction(TestCase):
    """Tests for LRU eviction."""

    def test_eviction_on_max_entries(self):
        """Test LRU eviction when max entries exceeded."""
        cache = GraphQueryCache(ttl_seconds=300, max_entries=3)

        # Fill cache
        cache.put("hash1", "query1", {"result": 1})
        cache.put("hash2", "query2", {"result": 2})
        cache.put("hash3", "query3", {"result": 3})

        # Access query1 to make it more recently used
        cache.get("hash1", "query1")
        cache.get("hash1", "query1")

        # Add another entry - should evict query2 (least accessed)
        cache.put("hash4", "query4", {"result": 4})

        stats = cache.get_stats()
        self.assertLessEqual(stats["current_entries"], 3)

    def test_eviction_preserves_frequently_used(self):
        """Test that frequently accessed entries survive eviction."""
        cache = GraphQueryCache(ttl_seconds=300, max_entries=2)

        cache.put("hash1", "query1", {"result": 1})

        # Access many times
        for _ in range(10):
            cache.get("hash1", "query1")

        cache.put("hash2", "query2", {"result": 2})
        cache.put("hash3", "query3", {"result": 3})  # Should evict query2

        # query1 should survive due to high access count
        self.assertIsNotNone(cache.get("hash1", "query1"))


class TestCachedQueryResult(TestCase):
    """Tests for CachedQueryResult dataclass."""

    def test_is_expired_within_ttl(self):
        """Test is_expired returns False within TTL."""
        result = CachedQueryResult(
            key="test-key",
            result={"nodes": []},
            graph_hash="abc123",
            query_text="FIND functions",
            expires_at=time.time() + 300,
        )
        self.assertFalse(result.is_expired())

    def test_is_expired_after_ttl(self):
        """Test is_expired returns True after TTL."""
        result = CachedQueryResult(
            key="test-key",
            result={"nodes": []},
            graph_hash="abc123",
            query_text="FIND functions",
            expires_at=time.time() - 1,  # Already expired
        )
        self.assertTrue(result.is_expired())

    def test_is_expired_no_expiry(self):
        """Test is_expired returns False with no expiry set."""
        result = CachedQueryResult(
            key="test-key",
            result={"nodes": []},
            graph_hash="abc123",
            query_text="FIND functions",
            expires_at=0,
        )
        self.assertFalse(result.is_expired())

    def test_touch_increments_access_count(self):
        """Test touch increments access count."""
        result = CachedQueryResult(
            key="test-key",
            result={"nodes": []},
            graph_hash="abc123",
            query_text="FIND functions",
        )
        self.assertEqual(result.access_count, 0)

        result.touch()
        self.assertEqual(result.access_count, 1)

        result.touch()
        self.assertEqual(result.access_count, 2)

    def test_to_dict_round_trip(self):
        """Test serialization round trip."""
        original = CachedQueryResult(
            key="test-key",
            result={"nodes": [{"id": "n1"}], "findings": []},
            graph_hash="abc123def456",
            query_text="FIND functions",
            overlay_hash="overlay789",
            pool_id="pool-001",
            access_count=5,
        )

        data = original.to_dict()
        restored = CachedQueryResult.from_dict(data)

        self.assertEqual(restored.key, original.key)
        self.assertEqual(restored.result, original.result)
        self.assertEqual(restored.graph_hash, original.graph_hash)
        self.assertEqual(restored.query_text, original.query_text)
        self.assertEqual(restored.overlay_hash, original.overlay_hash)
        self.assertEqual(restored.pool_id, original.pool_id)
        self.assertEqual(restored.access_count, original.access_count)


class TestGraphQueryCacheStats(TestCase):
    """Tests for cache statistics."""

    def test_empty_cache_stats(self):
        """Test stats for empty cache."""
        cache = GraphQueryCache()
        stats = cache.get_stats()

        self.assertTrue(stats["enabled"])
        self.assertEqual(stats["current_entries"], 0)
        self.assertEqual(stats["pools_tracked"], 0)
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)
        self.assertEqual(stats["hit_rate"], 0.0)

    def test_hit_rate_calculation(self):
        """Test hit rate is calculated correctly."""
        cache = GraphQueryCache()

        cache.put("hash1", "query1", {"result": 1})

        # 3 hits
        cache.get("hash1", "query1")
        cache.get("hash1", "query1")
        cache.get("hash1", "query1")
        # 1 miss
        cache.get("hash1", "query2")

        stats = cache.get_stats()
        self.assertEqual(stats["hit_rate"], 0.75)

    def test_pools_tracked(self):
        """Test pools_tracked count."""
        cache = GraphQueryCache()

        cache.put("hash1", "query1", {"result": 1}, pool_id="pool-A")
        cache.put("hash2", "query2", {"result": 2}, pool_id="pool-B")
        cache.put("hash3", "query3", {"result": 3}, pool_id="pool-A")

        stats = cache.get_stats()
        self.assertEqual(stats["pools_tracked"], 2)


if __name__ == "__main__":
    main()
