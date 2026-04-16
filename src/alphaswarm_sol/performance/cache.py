"""Phase 19: Caching Layer.

This module provides caching functionality for expensive computations
in the VKG build pipeline.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Entry in the cache.

    Attributes:
        key: Cache key
        value: Cached value
        created_at: Timestamp when cached
        expires_at: Timestamp when entry expires
        hits: Number of cache hits
        size_bytes: Estimated size in bytes
    """
    key: str
    value: T
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    hits: int = 0
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at


class CacheStore(Generic[T]):
    """In-memory cache with LRU eviction and TTL support.

    Provides bounded caching with automatic eviction when
    memory limit is reached.
    """

    def __init__(
        self,
        max_entries: int = 1000,
        max_memory_bytes: int = 100 * 1024 * 1024,  # 100MB
        default_ttl_seconds: Optional[float] = None,
    ):
        """Initialize cache.

        Args:
            max_entries: Maximum number of entries
            max_memory_bytes: Maximum memory usage in bytes
            default_ttl_seconds: Default TTL for entries
        """
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_bytes
        self.default_ttl_seconds = default_ttl_seconds

        self._entries: Dict[str, CacheEntry[T]] = {}
        self._access_order: list[str] = []
        self._total_bytes: int = 0

        # Stats
        self._hits: int = 0
        self._misses: int = 0

    @property
    def size(self) -> int:
        """Get number of entries."""
        return len(self._entries)

    @property
    def memory_bytes(self) -> int:
        """Get total memory usage."""
        return self._total_bytes

    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def get(self, key: str) -> Optional[T]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            self.delete(key)
            self._misses += 1
            return None

        # Update LRU order
        self._touch(key)
        entry.hits += 1
        self._hits += 1

        return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl_seconds: Optional[float] = None,
        size_bytes: Optional[int] = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL override
            size_bytes: Size override
        """
        # Calculate size if not provided
        if size_bytes is None:
            size_bytes = self._estimate_size(value)

        # Calculate expiry
        expires_at = None
        ttl = ttl_seconds or self.default_ttl_seconds
        if ttl is not None:
            expires_at = time.time() + ttl

        # Evict if needed
        self._evict_if_needed(size_bytes)

        # Remove old entry if exists
        if key in self._entries:
            self.delete(key)

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            expires_at=expires_at,
            size_bytes=size_bytes,
        )

        self._entries[key] = entry
        self._access_order.append(key)
        self._total_bytes += size_bytes

    def delete(self, key: str) -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted
        """
        entry = self._entries.pop(key, None)
        if entry:
            self._total_bytes -= entry.size_bytes
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._access_order.clear()
        self._total_bytes = 0

    def _touch(self, key: str) -> None:
        """Update LRU order for key."""
        if key in self._access_order:
            self._access_order.remove(key)
            self._access_order.append(key)

    def _evict_if_needed(self, new_size: int) -> None:
        """Evict entries if limits exceeded."""
        # Evict expired entries first
        self._evict_expired()

        # Evict by count limit
        while len(self._entries) >= self.max_entries and self._access_order:
            oldest_key = self._access_order[0]
            self.delete(oldest_key)

        # Evict by memory limit
        while (
            self._total_bytes + new_size > self.max_memory_bytes
            and self._access_order
        ):
            oldest_key = self._access_order[0]
            self.delete(oldest_key)

    def _evict_expired(self) -> int:
        """Evict expired entries.

        Returns:
            Number of entries evicted
        """
        expired = [
            key for key, entry in self._entries.items()
            if entry.is_expired
        ]
        for key in expired:
            self.delete(key)
        return len(expired)

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value."""
        try:
            return len(json.dumps(value, default=str).encode())
        except (TypeError, ValueError):
            return 1024  # Default estimate

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "entries": len(self._entries),
            "memory_bytes": self._total_bytes,
            "max_entries": self.max_entries,
            "max_memory_bytes": self.max_memory_bytes,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


class GraphCache:
    """Specialized cache for knowledge graphs.

    Caches graph builds by contract hash for incremental builds.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_memory_bytes: int = 200 * 1024 * 1024,  # 200MB
    ):
        """Initialize graph cache.

        Args:
            cache_dir: Directory for disk cache (optional)
            max_memory_bytes: Maximum memory for in-memory cache
        """
        self.cache_dir = cache_dir
        self._memory_cache: CacheStore[Dict[str, Any]] = CacheStore(
            max_entries=100,
            max_memory_bytes=max_memory_bytes,
        )

    def get_contract_hash(self, source_code: str) -> str:
        """Get hash for contract source code.

        Args:
            source_code: Contract source code

        Returns:
            Hash string
        """
        return hashlib.sha256(source_code.encode()).hexdigest()[:16]

    def get_graph(self, contract_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached graph by contract hash.

        Args:
            contract_hash: Contract hash

        Returns:
            Cached graph data or None
        """
        # Try memory cache first
        graph = self._memory_cache.get(contract_hash)
        if graph is not None:
            return graph

        # Try disk cache
        if self.cache_dir:
            cache_file = self.cache_dir / f"{contract_hash}.json"
            if cache_file.exists():
                try:
                    with open(cache_file) as f:
                        graph = json.load(f)
                    # Warm memory cache
                    self._memory_cache.set(contract_hash, graph)
                    return graph
                except (json.JSONDecodeError, IOError):
                    pass

        return None

    def set_graph(
        self,
        contract_hash: str,
        graph_data: Dict[str, Any],
        persist: bool = False,
    ) -> None:
        """Cache graph data.

        Args:
            contract_hash: Contract hash
            graph_data: Graph data to cache
            persist: Whether to persist to disk
        """
        # Memory cache
        self._memory_cache.set(contract_hash, graph_data)

        # Disk cache
        if persist and self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / f"{contract_hash}.json"
            try:
                with open(cache_file, 'w') as f:
                    json.dump(graph_data, f)
            except IOError:
                pass  # Silently fail disk writes

    def invalidate(self, contract_hash: str) -> None:
        """Invalidate cached graph.

        Args:
            contract_hash: Contract hash
        """
        self._memory_cache.delete(contract_hash)

        if self.cache_dir:
            cache_file = self.cache_dir / f"{contract_hash}.json"
            try:
                cache_file.unlink(missing_ok=True)
            except IOError:
                pass

    def clear(self) -> None:
        """Clear all cached graphs."""
        self._memory_cache.clear()

        if self.cache_dir and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except IOError:
                    pass

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._memory_cache.get_stats()
        stats["cache_dir"] = str(self.cache_dir) if self.cache_dir else None
        return stats


def cache_result(
    cache: CacheStore[T],
    key_fn: Optional[Callable[..., str]] = None,
    ttl_seconds: Optional[float] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to cache function results.

    Args:
        cache: Cache store to use
        key_fn: Function to generate cache key from args
        ttl_seconds: TTL for cached results

    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            if key_fn:
                key = key_fn(*args, **kwargs)
            else:
                key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # Check cache
            result = cache.get(key)
            if result is not None:
                return result

            # Compute result
            result = func(*args, **kwargs)

            # Cache result
            cache.set(key, result, ttl_seconds=ttl_seconds)

            return result
        return wrapper
    return decorator


__all__ = [
    "CacheEntry",
    "CacheStore",
    "GraphCache",
    "cache_result",
]
