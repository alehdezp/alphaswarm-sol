"""
Graph Query Cache

Caches query results keyed by graph hash, query text, overlay hash, and pool_id.
Supports TTL, pool scoping, and explicit invalidation.

Usage:
    from alphaswarm_sol.cache.graph_queries import GraphQueryCache

    cache = GraphQueryCache(ttl_seconds=300)

    # Check for cached result
    result = cache.get(
        graph_hash="abc123def456",
        query_text="FIND functions WHERE visibility = public",
        overlay_hash="xyz789",
        pool_id="pool-001",
    )

    # Store result
    cache.put(
        graph_hash="abc123def456",
        query_text="FIND functions WHERE visibility = public",
        result={"nodes": [...], "findings": [...]},
        overlay_hash="xyz789",
        pool_id="pool-001",
    )

    # Invalidate by pool
    cache.invalidate_pool("pool-001")
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


def _compute_cache_key(
    graph_hash: str,
    query_text: str,
    overlay_hash: Optional[str] = None,
    pool_id: Optional[str] = None,
) -> str:
    """Compute deterministic cache key from query parameters.

    Args:
        graph_hash: Hash of the knowledge graph
        query_text: Query text (VQL, NL, or pattern)
        overlay_hash: Optional hash of label overlay
        pool_id: Optional pool identifier for scoping

    Returns:
        SHA256-based cache key string (24 hex chars)
    """
    key_parts = [graph_hash, query_text]
    if overlay_hash:
        key_parts.append(overlay_hash)
    if pool_id:
        key_parts.append(pool_id)

    combined = "\x00".join(key_parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:24]


@dataclass
class CachedQueryResult:
    """A cached query result with metadata.

    Attributes:
        key: Deterministic cache key
        result: Query result dictionary
        graph_hash: Hash of graph used
        query_text: Original query text
        overlay_hash: Hash of overlay if used
        pool_id: Pool ID if scoped
        created_at: When cached (UTC timestamp)
        expires_at: When it expires (UTC timestamp)
        access_count: Number of cache hits
    """

    key: str
    result: Dict[str, Any]
    graph_hash: str
    query_text: str
    overlay_hash: Optional[str] = None
    pool_id: Optional[str] = None
    created_at: float = field(default_factory=lambda: time.time())
    expires_at: float = 0.0
    access_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired.

        Returns:
            True if expired, False otherwise
        """
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Update access count and timestamp."""
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "key": self.key,
            "result": self.result,
            "graph_hash": self.graph_hash,
            "query_text": self.query_text,
            "overlay_hash": self.overlay_hash,
            "pool_id": self.pool_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedQueryResult":
        """Deserialize from dictionary."""
        return cls(
            key=data["key"],
            result=data["result"],
            graph_hash=data["graph_hash"],
            query_text=data["query_text"],
            overlay_hash=data.get("overlay_hash"),
            pool_id=data.get("pool_id"),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at", 0.0),
            access_count=data.get("access_count", 0),
        )


@dataclass
class CacheStats:
    """Statistics for cache operations."""

    hits: int = 0
    misses: int = 0
    writes: int = 0
    invalidations: int = 0
    expired_cleared: int = 0


class GraphQueryCache:
    """In-memory cache for graph query results.

    Provides memoization of query results with:
    - Deterministic keys based on graph hash, query, overlay, pool
    - TTL-based expiration
    - Pool-scoped invalidation
    - LRU eviction when max entries exceeded

    Thread-safe for concurrent reads; writes should be serialized
    for best performance.

    Example:
        cache = GraphQueryCache(ttl_seconds=300, max_entries=1000)

        # Try cache first
        result = cache.get(graph_hash, query_text, overlay_hash, pool_id)
        if result is None:
            result = executor.execute(graph, plan)
            cache.put(graph_hash, query_text, result, overlay_hash, pool_id)

        # Clear stale entries
        cache.clear_expired()

        # Invalidate pool
        cache.invalidate_pool("pool-001")
    """

    # Default TTL: 5 minutes
    DEFAULT_TTL_SECONDS: ClassVar[int] = 300

    # Default max entries before LRU eviction
    DEFAULT_MAX_ENTRIES: ClassVar[int] = 1000

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        enabled: bool = True,
    ) -> None:
        """Initialize cache.

        Args:
            ttl_seconds: Time-to-live for entries (0 = no expiry)
            max_entries: Maximum entries before eviction
            enabled: Whether caching is enabled
        """
        self._cache: Dict[str, CachedQueryResult] = {}
        self._pool_index: Dict[str, List[str]] = {}  # pool_id -> [keys]
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._enabled = enabled
        self._stats = CacheStats()

        logger.debug(
            "graph_query_cache_initialized",
            ttl_seconds=ttl_seconds,
            max_entries=max_entries,
            enabled=enabled,
        )

    @property
    def is_enabled(self) -> bool:
        """Check if cache is enabled."""
        return self._enabled

    @property
    def ttl_seconds(self) -> int:
        """Get TTL in seconds."""
        return self._ttl_seconds

    def get(
        self,
        graph_hash: str,
        query_text: str,
        overlay_hash: Optional[str] = None,
        pool_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get cached query result if available.

        Args:
            graph_hash: Hash of the knowledge graph
            query_text: Query text
            overlay_hash: Optional overlay hash
            pool_id: Optional pool ID for scoping

        Returns:
            Cached result dictionary or None if miss
        """
        if not self._enabled:
            return None

        key = _compute_cache_key(graph_hash, query_text, overlay_hash, pool_id)
        entry = self._cache.get(key)

        if entry is None:
            self._stats.misses += 1
            logger.debug("query_cache_miss", key=key[:12], reason="not_found")
            return None

        if entry.is_expired():
            self._stats.misses += 1
            self._remove_entry(key)
            logger.debug("query_cache_miss", key=key[:12], reason="expired")
            return None

        entry.touch()
        self._stats.hits += 1
        logger.debug(
            "query_cache_hit",
            key=key[:12],
            access_count=entry.access_count,
        )
        return entry.result

    def put(
        self,
        graph_hash: str,
        query_text: str,
        result: Dict[str, Any],
        overlay_hash: Optional[str] = None,
        pool_id: Optional[str] = None,
    ) -> str:
        """Cache a query result.

        Args:
            graph_hash: Hash of the knowledge graph
            query_text: Query text
            result: Query result dictionary to cache
            overlay_hash: Optional overlay hash
            pool_id: Optional pool ID for scoping

        Returns:
            Cache key used for storage
        """
        if not self._enabled:
            return ""

        key = _compute_cache_key(graph_hash, query_text, overlay_hash, pool_id)

        # Evict if at capacity
        if len(self._cache) >= self._max_entries and key not in self._cache:
            self._evict_lru()

        # Compute expiration
        expires_at = 0.0
        if self._ttl_seconds > 0:
            expires_at = time.time() + self._ttl_seconds

        entry = CachedQueryResult(
            key=key,
            result=result,
            graph_hash=graph_hash,
            query_text=query_text,
            overlay_hash=overlay_hash,
            pool_id=pool_id,
            expires_at=expires_at,
        )

        self._cache[key] = entry
        self._stats.writes += 1

        # Update pool index
        if pool_id:
            if pool_id not in self._pool_index:
                self._pool_index[pool_id] = []
            if key not in self._pool_index[pool_id]:
                self._pool_index[pool_id].append(key)

        logger.debug(
            "query_cache_write",
            key=key[:12],
            pool_id=pool_id,
            ttl=self._ttl_seconds,
        )

        return key

    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was removed, False if not found
        """
        if key in self._cache:
            self._remove_entry(key)
            self._stats.invalidations += 1
            logger.debug("query_cache_invalidated", key=key[:12])
            return True
        return False

    def invalidate_pool(self, pool_id: str) -> int:
        """Invalidate all entries for a pool.

        Args:
            pool_id: Pool identifier

        Returns:
            Number of entries removed
        """
        keys = self._pool_index.pop(pool_id, [])
        removed = 0

        for key in keys:
            if key in self._cache:
                del self._cache[key]
                removed += 1

        if removed:
            self._stats.invalidations += removed
            logger.info(
                "query_cache_pool_invalidated",
                pool_id=pool_id,
                removed=removed,
            )

        return removed

    def invalidate_graph(self, graph_hash: str) -> int:
        """Invalidate all entries for a graph hash.

        Args:
            graph_hash: Graph hash to invalidate

        Returns:
            Number of entries removed
        """
        to_remove = [
            key
            for key, entry in self._cache.items()
            if entry.graph_hash == graph_hash
        ]

        removed = 0
        for key in to_remove:
            self._remove_entry(key)
            removed += 1

        if removed:
            self._stats.invalidations += removed
            logger.info(
                "query_cache_graph_invalidated",
                graph_hash=graph_hash[:12],
                removed=removed,
            )

        return removed

    def clear_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        to_remove = [
            key
            for key, entry in self._cache.items()
            if entry.expires_at > 0 and now > entry.expires_at
        ]

        for key in to_remove:
            self._remove_entry(key)

        if to_remove:
            self._stats.expired_cleared += len(to_remove)
            logger.debug("query_cache_expired_cleared", count=len(to_remove))

        return len(to_remove)

    def clear_all(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed
        """
        count = len(self._cache)
        self._cache.clear()
        self._pool_index.clear()

        if count:
            logger.info("query_cache_cleared", count=count)

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_requests = self._stats.hits + self._stats.misses
        hit_rate = self._stats.hits / total_requests if total_requests > 0 else 0.0

        return {
            "enabled": self._enabled,
            "ttl_seconds": self._ttl_seconds,
            "max_entries": self._max_entries,
            "current_entries": len(self._cache),
            "pools_tracked": len(self._pool_index),
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "writes": self._stats.writes,
            "invalidations": self._stats.invalidations,
            "expired_cleared": self._stats.expired_cleared,
            "hit_rate": round(hit_rate, 3),
        }

    def _remove_entry(self, key: str) -> None:
        """Remove entry and clean up pool index."""
        entry = self._cache.pop(key, None)
        if entry and entry.pool_id and entry.pool_id in self._pool_index:
            try:
                self._pool_index[entry.pool_id].remove(key)
                if not self._pool_index[entry.pool_id]:
                    del self._pool_index[entry.pool_id]
            except ValueError:
                pass

    def _evict_lru(self) -> None:
        """Evict least-recently-used entry."""
        if not self._cache:
            return

        # Find entry with lowest access count (simple LRU approximation)
        # In production, could use OrderedDict or proper LRU structure
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].access_count, self._cache[k].created_at),
        )
        self._remove_entry(lru_key)
        logger.debug("query_cache_evicted_lru", key=lru_key[:12])


# Convenience function
def compute_cache_key(
    graph_hash: str,
    query_text: str,
    overlay_hash: Optional[str] = None,
    pool_id: Optional[str] = None,
) -> str:
    """Compute cache key for external use.

    Args:
        graph_hash: Hash of the knowledge graph
        query_text: Query text
        overlay_hash: Optional overlay hash
        pool_id: Optional pool ID

    Returns:
        Cache key string
    """
    return _compute_cache_key(graph_hash, query_text, overlay_hash, pool_id)


__all__ = [
    "GraphQueryCache",
    "CachedQueryResult",
    "compute_cache_key",
]
