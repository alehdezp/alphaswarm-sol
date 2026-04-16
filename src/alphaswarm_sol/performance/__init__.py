"""Performance optimization module for True VKG.

Provides profiling, caching, incremental builds, and parallel processing.
"""

from alphaswarm_sol.performance.profiler import (
    ProfileResult,
    BuildProfiler,
    profile_build,
)
from alphaswarm_sol.performance.cache import (
    CacheEntry,
    CacheStore,
    GraphCache,
    cache_result,
)
from alphaswarm_sol.performance.incremental import (
    ChangeDetector,
    IncrementalBuilder,
    detect_changes,
)
from alphaswarm_sol.performance.parallel import (
    ParallelProcessor,
    BatchProcessor,
    parallel_detect,
)

__all__ = [
    "ProfileResult",
    "BuildProfiler",
    "profile_build",
    "CacheEntry",
    "CacheStore",
    "GraphCache",
    "cache_result",
    "ChangeDetector",
    "IncrementalBuilder",
    "detect_changes",
    "ParallelProcessor",
    "BatchProcessor",
    "parallel_detect",
]
