"""Phase 12: Annotation Caching.

This module provides caching for LLM annotations to reduce API calls
and improve response times for repeated queries.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from alphaswarm_sol.llm.annotations import LLMAnnotation


@dataclass
class CacheEntry:
    """Entry in the annotation cache.

    Attributes:
        key: Cache key (hash of query)
        annotation: Cached annotation
        created_at: Timestamp of creation
        expires_at: Timestamp of expiration
        hit_count: Number of cache hits
        metadata: Additional metadata
    """
    key: str
    annotation: LLMAnnotation
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hit_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "annotation": self.annotation.to_dict(),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "hit_count": self.hit_count,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CacheEntry":
        return CacheEntry(
            key=data.get("key", ""),
            annotation=LLMAnnotation.from_dict(data.get("annotation", {})),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            hit_count=data.get("hit_count", 0),
            metadata=data.get("metadata", {}),
        )


class AnnotationCache:
    """Cache for LLM annotations.

    Provides in-memory and optional disk-based caching for annotations
    to reduce LLM API calls.

    Attributes:
        max_size: Maximum number of entries in memory
        default_ttl: Default time-to-live in seconds
        persist_path: Optional path for disk persistence
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = 3600,  # 1 hour
        persist_path: Optional[str] = None,
    ):
        """Initialize cache.

        Args:
            max_size: Maximum entries in memory
            default_ttl: Default TTL in seconds (None = no expiry)
            persist_path: Optional path to persist cache
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.persist_path = persist_path
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

        # Load from disk if path exists
        if persist_path and os.path.exists(persist_path):
            self._load_from_disk()

    def _generate_key(
        self,
        node_id: str,
        query: str,
        context_hash: str = "",
    ) -> str:
        """Generate cache key from inputs."""
        content = f"{node_id}:{query}:{context_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(
        self,
        node_id: str,
        query: str,
        context_hash: str = "",
    ) -> Optional[LLMAnnotation]:
        """Get annotation from cache.

        Args:
            node_id: Node ID
            query: Query string
            context_hash: Optional context hash

        Returns:
            Cached annotation if found and not expired, None otherwise
        """
        key = self._generate_key(node_id, query, context_hash)
        entry = self._cache.get(key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired():
            self._stats["misses"] += 1
            del self._cache[key]
            return None

        entry.record_hit()
        self._stats["hits"] += 1
        return entry.annotation

    def put(
        self,
        node_id: str,
        query: str,
        annotation: LLMAnnotation,
        context_hash: str = "",
        ttl: Optional[float] = None,
    ) -> None:
        """Put annotation in cache.

        Args:
            node_id: Node ID
            query: Query string
            annotation: Annotation to cache
            context_hash: Optional context hash
            ttl: Optional TTL override (None = use default)
        """
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        key = self._generate_key(node_id, query, context_hash)
        ttl = ttl if ttl is not None else self.default_ttl

        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        entry = CacheEntry(
            key=key,
            annotation=annotation,
            expires_at=expires_at,
        )
        self._cache[key] = entry

        # Persist if configured
        if self.persist_path:
            self._save_to_disk()

    def invalidate(
        self,
        node_id: str,
        query: str = "",
        context_hash: str = "",
    ) -> bool:
        """Invalidate cache entry.

        Args:
            node_id: Node ID (required)
            query: Optional query string
            context_hash: Optional context hash

        Returns:
            True if entry was found and removed
        """
        if query:
            # Invalidate specific entry
            key = self._generate_key(node_id, query, context_hash)
            if key in self._cache:
                del self._cache[key]
                return True
            return False
        else:
            # Invalidate all entries for node
            removed = False
            keys_to_remove = [
                k for k, v in self._cache.items()
                if v.annotation.node_id == node_id
            ]
            for key in keys_to_remove:
                del self._cache[key]
                removed = True
            return removed

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        if self.persist_path and os.path.exists(self.persist_path):
            os.remove(self.persist_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "hit_rate": hit_rate,
        }

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find entry with lowest hit count (simple LRU approximation)
        min_key = min(self._cache.keys(), key=lambda k: self._cache[k].hit_count)
        del self._cache[min_key]
        self._stats["evictions"] += 1

    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        if not self.persist_path:
            return

        data = {
            "entries": [e.to_dict() for e in self._cache.values()],
            "stats": self._stats,
        }

        path = Path(self.persist_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(data, f)

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        if not self.persist_path or not os.path.exists(self.persist_path):
            return

        try:
            with open(self.persist_path) as f:
                data = json.load(f)

            for entry_data in data.get("entries", []):
                entry = CacheEntry.from_dict(entry_data)
                if not entry.is_expired():
                    self._cache[entry.key] = entry

            # Restore stats
            self._stats.update(data.get("stats", {}))

        except (json.JSONDecodeError, KeyError):
            pass  # Invalid cache file, start fresh


# Global cache instance
_global_cache: Optional[AnnotationCache] = None


def get_cache(
    max_size: int = 1000,
    default_ttl: Optional[float] = 3600,
    persist_path: Optional[str] = None,
) -> AnnotationCache:
    """Get or create global cache instance.

    Args:
        max_size: Maximum cache size
        default_ttl: Default TTL
        persist_path: Persistence path

    Returns:
        Global AnnotationCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = AnnotationCache(
            max_size=max_size,
            default_ttl=default_ttl,
            persist_path=persist_path,
        )
    return _global_cache


def clear_cache() -> None:
    """Clear global cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()
        _global_cache = None


__all__ = [
    "CacheEntry",
    "AnnotationCache",
    "get_cache",
    "clear_cache",
]
