"""
Cache Module

Provides caching infrastructure for VKG, including:
- Tool result caching for incremental analysis
- Graph query result caching with TTL and pool scoping
- File-hash based invalidation
- TTL-based expiration

Usage:
    from alphaswarm_sol.cache import ToolResultCache, create_cache
    from alphaswarm_sol.cache import GraphQueryCache

    # Tool result cache
    cache = create_cache(Path(".vrs/cache"), ttl_hours=24)
    cached = cache.get("slither", project_path, config)

    # Graph query cache
    query_cache = GraphQueryCache(ttl_seconds=300)
    result = query_cache.get(graph_hash, query_text)
"""

from alphaswarm_sol.cache.tool_results import (
    CacheKey,
    CachedResult,
    ToolResultCache,
    create_cache,
)

from alphaswarm_sol.cache.graph_queries import (
    GraphQueryCache,
    CachedQueryResult,
    compute_cache_key,
)


__all__ = [
    # Tool result cache
    "CacheKey",
    "CachedResult",
    "ToolResultCache",
    "create_cache",
    # Graph query cache
    "GraphQueryCache",
    "CachedQueryResult",
    "compute_cache_key",
]
