"""
Tool Result Cache

File-hash based caching for static analysis tool results.
Enables incremental analysis by caching results keyed by:
- Tool name
- Project file hashes (SHA256)
- Tool configuration hash

Cache invalidates automatically when source files change.

Usage:
    cache = ToolResultCache(Path(".vrs/cache"))

    # Check for cached results
    cached = cache.get("slither", project_path, config)
    if cached:
        findings = cached.findings

    # Store results
    cache.put("slither", project_path, config, findings, execution_time)

    # Clear when needed
    cache.invalidate_all(project_path)
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

import structlog

from alphaswarm_sol.tools.adapters.sarif import VKGFinding
from alphaswarm_sol.tools.config import ToolConfig

logger = structlog.get_logger(__name__)


@dataclass
class CacheKey:
    """Key for identifying cached tool results.

    Combines tool identity with project state and configuration
    to create unique, reproducible cache keys.

    Attributes:
        tool: Tool name (e.g., "slither")
        file_hash: SHA256 hash of all source files
        config_hash: Hash of tool configuration
        version: Tool version (if available)
        pool_id: Optional pool identifier for scoping
        run_id: Optional run identifier for scoping
    """

    tool: str
    file_hash: str
    config_hash: str
    version: str = ""
    pool_id: Optional[str] = None
    run_id: Optional[str] = None

    def to_filename(self) -> str:
        """Generate cache filename from key.

        Returns:
            Filename like: slither_abc123def456_config12.json
            Or with pool: slither_abc123def456_config12_pool001.json
        """
        base = f"{self.tool}_{self.file_hash[:12]}_{self.config_hash[:8]}"
        if self.pool_id:
            # Sanitize pool_id for filesystem
            safe_pool = self.pool_id.replace("/", "_").replace("\\", "_")[:16]
            base = f"{base}_{safe_pool}"
        if self.run_id:
            safe_run = self.run_id.replace("/", "_").replace("\\", "_")[:12]
            base = f"{base}_{safe_run}"
        return f"{base}.json"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "tool": self.tool,
            "file_hash": self.file_hash,
            "config_hash": self.config_hash,
            "version": self.version,
        }
        if self.pool_id:
            result["pool_id"] = self.pool_id
        if self.run_id:
            result["run_id"] = self.run_id
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheKey":
        """Create from dictionary."""
        return cls(
            tool=data["tool"],
            file_hash=data["file_hash"],
            config_hash=data["config_hash"],
            version=data.get("version", ""),
            pool_id=data.get("pool_id"),
            run_id=data.get("run_id"),
        )


@dataclass
class CachedResult:
    """Cached tool execution result.

    Stores the findings along with metadata for cache management.

    Attributes:
        key: Cache key that identifies this result
        findings: List of VKG findings from tool execution
        execution_time: Original execution time in seconds
        cached_at: When the result was cached
        expires_at: When the cached result expires (optional)
    """

    key: CacheKey
    findings: List[VKGFinding]
    execution_time: float
    cached_at: datetime
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if cached result has expired.

        Returns:
            True if expired or has no expiration.
        """
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "execution_time": self.execution_time,
            "cached_at": self.cached_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedResult":
        """Create from dictionary."""
        findings = [VKGFinding.from_dict(f) for f in data.get("findings", [])]
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])

        return cls(
            key=CacheKey.from_dict(data["key"]),
            findings=findings,
            execution_time=data.get("execution_time", 0),
            cached_at=datetime.fromisoformat(data["cached_at"]),
            expires_at=expires_at,
        )


class ToolResultCache:
    """File-hash based cache for tool results.

    Stores tool execution results keyed by file hashes, enabling
    incremental analysis that skips unchanged code.

    Cache invalidation:
    - Automatic when source files change (hash mismatch)
    - Automatic when TTL expires
    - Manual via invalidate() methods

    Thread safety: File operations use atomic writes to avoid corruption
    during concurrent access.

    Example:
        cache = ToolResultCache(Path(".vrs/cache"), ttl_hours=24)

        # Check cache
        cached = cache.get("slither", project_path, config)
        if cached:
            print(f"Using cached results ({len(cached.findings)} findings)")
            return cached.findings

        # Run tool and cache results
        findings = run_slither(project_path, config)
        cache.put("slither", project_path, config, findings, exec_time)
    """

    # Subdirectory for tool results
    CACHE_SUBDIR: ClassVar[str] = "tool_results"

    # Default TTL (24 hours)
    DEFAULT_TTL_HOURS: ClassVar[int] = 24

    # Paths to skip when hashing (common libraries)
    SKIP_PATHS: ClassVar[List[str]] = [
        "node_modules",
        "lib/",
        ".cache",
        ".git",
        "out/",
        "artifacts/",
        "cache/",
    ]

    def __init__(
        self,
        cache_dir: Path,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ):
        """Initialize cache.

        Args:
            cache_dir: Root directory for cache storage.
            ttl_hours: Time-to-live in hours for cached results.
        """
        self.cache_dir = Path(cache_dir) / self.CACHE_SUBDIR
        self.ttl_hours = ttl_hours
        self._stats = CacheStats()

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(
            "cache_initialized",
            cache_dir=str(self.cache_dir),
            ttl_hours=ttl_hours,
        )

    def get_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file.

        Args:
            file_path: Path to file.

        Returns:
            Hex-encoded SHA256 hash.
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except OSError as e:
            logger.warning("file_hash_error", file=str(file_path), error=str(e))
            return ""

    def get_project_hash(self, project_path: Path) -> str:
        """Compute combined hash of all Solidity files in project.

        Hash includes both file paths and contents to detect:
        - File content changes
        - File additions/removals
        - File renames

        Args:
            project_path: Project root directory.

        Returns:
            Hex-encoded SHA256 hash of project state.
        """
        sha256 = hashlib.sha256()
        sol_files = sorted(project_path.rglob("*.sol"))

        hashed_count = 0
        for sol_file in sol_files:
            # Skip common library paths
            rel_path = str(sol_file.relative_to(project_path))
            if any(skip in rel_path for skip in self.SKIP_PATHS):
                continue

            # Include relative path in hash (detects moves/renames)
            sha256.update(rel_path.encode("utf-8"))

            # Include file content hash
            file_hash = self.get_file_hash(sol_file)
            if file_hash:
                sha256.update(file_hash.encode("utf-8"))
                hashed_count += 1

        logger.debug(
            "project_hashed",
            project=str(project_path),
            files=hashed_count,
        )

        return sha256.hexdigest()

    def get_config_hash(self, config: ToolConfig) -> str:
        """Compute hash of tool configuration.

        Args:
            config: Tool configuration.

        Returns:
            Hex-encoded SHA256 hash.
        """
        # Serialize config to JSON for consistent hashing
        config_str = json.dumps(config.to_dict(), sort_keys=True)
        return hashlib.sha256(config_str.encode("utf-8")).hexdigest()

    def get(
        self,
        tool: str,
        project_path: Path,
        config: ToolConfig,
        pool_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[CachedResult]:
        """Get cached result if available and valid.

        Returns None if:
        - No cached result exists
        - Project files have changed (hash mismatch)
        - Cache entry has expired

        Args:
            tool: Tool name.
            project_path: Project root directory.
            config: Tool configuration.
            pool_id: Optional pool identifier for scoping.
            run_id: Optional run identifier for scoping.

        Returns:
            CachedResult or None.
        """
        # Compute current project hash
        project_hash = self.get_project_hash(project_path)
        config_hash = self.get_config_hash(config)

        # Build expected cache key
        key = CacheKey(
            tool=tool,
            file_hash=project_hash,
            config_hash=config_hash,
            pool_id=pool_id,
            run_id=run_id,
        )

        # Check if cache file exists
        cache_file = self.cache_dir / key.to_filename()
        if not cache_file.exists():
            self._stats.misses += 1
            logger.debug("cache_miss", tool=tool, reason="not_found")
            return None

        # Load and validate cached result
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached = CachedResult.from_dict(data)

            # Verify hash matches (should always match if filename matched)
            if cached.key.file_hash != project_hash:
                self._stats.misses += 1
                logger.debug("cache_miss", tool=tool, reason="hash_mismatch")
                return None

            # Check expiration
            if cached.is_expired():
                self._stats.misses += 1
                logger.debug("cache_miss", tool=tool, reason="expired")
                # Clean up expired entry
                self._remove_file(cache_file)
                return None

            self._stats.hits += 1
            logger.debug(
                "cache_hit",
                tool=tool,
                findings=len(cached.findings),
                age_hours=self._age_hours(cached.cached_at),
            )
            return cached

        except (json.JSONDecodeError, KeyError, OSError) as e:
            self._stats.misses += 1
            logger.warning(
                "cache_read_error",
                tool=tool,
                file=str(cache_file),
                error=str(e),
            )
            # Remove corrupted cache file
            self._remove_file(cache_file)
            return None

    def put(
        self,
        tool: str,
        project_path: Path,
        config: ToolConfig,
        findings: List[VKGFinding],
        exec_time: float,
        pool_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> bool:
        """Cache tool execution results.

        Args:
            tool: Tool name.
            project_path: Project root directory.
            config: Tool configuration used.
            findings: List of findings to cache.
            exec_time: Execution time in seconds.
            pool_id: Optional pool identifier for scoping.
            run_id: Optional run identifier for scoping.

        Returns:
            True if cached successfully.
        """
        # Compute hashes
        project_hash = self.get_project_hash(project_path)
        config_hash = self.get_config_hash(config)

        # Build cache key and result
        key = CacheKey(
            tool=tool,
            file_hash=project_hash,
            config_hash=config_hash,
            pool_id=pool_id,
            run_id=run_id,
        )

        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.ttl_hours) if self.ttl_hours > 0 else None

        result = CachedResult(
            key=key,
            findings=findings,
            execution_time=exec_time,
            cached_at=now,
            expires_at=expires,
        )

        # Write to cache (atomic write via temp file)
        cache_file = self.cache_dir / key.to_filename()
        temp_file = cache_file.with_suffix(".tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)

            # Atomic rename
            temp_file.rename(cache_file)

            self._stats.writes += 1
            logger.debug(
                "cache_write",
                tool=tool,
                findings=len(findings),
                file=str(cache_file),
            )
            return True

        except OSError as e:
            logger.warning(
                "cache_write_error",
                tool=tool,
                error=str(e),
            )
            self._remove_file(temp_file)
            return False

    def invalidate(self, tool: str, project_path: Path) -> int:
        """Invalidate cached results for a specific tool and project.

        Args:
            tool: Tool name.
            project_path: Project root directory.

        Returns:
            Number of cache entries removed.
        """
        project_hash = self.get_project_hash(project_path)
        pattern = f"{tool}_{project_hash[:12]}_*.json"

        removed = 0
        for cache_file in self.cache_dir.glob(pattern):
            if self._remove_file(cache_file):
                removed += 1

        if removed:
            logger.info(
                "cache_invalidated",
                tool=tool,
                project=str(project_path),
                removed=removed,
            )

        return removed

    def invalidate_all(self, project_path: Path) -> int:
        """Invalidate all cached results for a project.

        Args:
            project_path: Project root directory.

        Returns:
            Number of cache entries removed.
        """
        project_hash = self.get_project_hash(project_path)
        pattern = f"*_{project_hash[:12]}_*.json"

        removed = 0
        for cache_file in self.cache_dir.glob(pattern):
            if self._remove_file(cache_file):
                removed += 1

        if removed:
            logger.info(
                "cache_invalidated_all",
                project=str(project_path),
                removed=removed,
            )

        return removed

    def clear_expired(self) -> int:
        """Remove all expired cache entries.

        Returns:
            Number of expired entries removed.
        """
        removed = 0
        now = datetime.now(timezone.utc)

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                expires_str = data.get("expires_at")
                if expires_str:
                    expires = datetime.fromisoformat(expires_str)
                    if now > expires:
                        if self._remove_file(cache_file):
                            removed += 1

            except (json.JSONDecodeError, OSError):
                # Remove corrupted files too
                if self._remove_file(cache_file):
                    removed += 1

        if removed:
            logger.info("cache_expired_cleared", removed=removed)

        self._stats.expired_cleared += removed
        return removed

    def invalidate_pool(self, pool_id: str) -> int:
        """Invalidate all cached results for a pool.

        Args:
            pool_id: Pool identifier.

        Returns:
            Number of cache entries removed.
        """
        removed = 0
        # Sanitize pool_id for filename matching
        safe_pool = pool_id.replace("/", "_").replace("\\", "_")[:16]
        pattern = f"*_{safe_pool}*.json"

        for cache_file in self.cache_dir.glob(pattern):
            # Verify this entry belongs to the pool by reading metadata
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key_data = data.get("key", {})
                if key_data.get("pool_id") == pool_id:
                    if self._remove_file(cache_file):
                        removed += 1
            except (json.JSONDecodeError, OSError):
                # Can't verify, skip
                continue

        if removed:
            logger.info(
                "cache_pool_invalidated",
                pool_id=pool_id,
                removed=removed,
            )

        return removed

    def invalidate_run(self, run_id: str, pool_id: Optional[str] = None) -> int:
        """Invalidate all cached results for a run.

        Args:
            run_id: Run identifier.
            pool_id: Optional pool identifier for narrower scoping.

        Returns:
            Number of cache entries removed.
        """
        removed = 0
        safe_run = run_id.replace("/", "_").replace("\\", "_")[:12]

        # Build pattern
        if pool_id:
            safe_pool = pool_id.replace("/", "_").replace("\\", "_")[:16]
            pattern = f"*_{safe_pool}_{safe_run}.json"
        else:
            pattern = f"*_{safe_run}.json"

        for cache_file in self.cache_dir.glob(pattern):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key_data = data.get("key", {})
                if key_data.get("run_id") == run_id:
                    if pool_id is None or key_data.get("pool_id") == pool_id:
                        if self._remove_file(cache_file):
                            removed += 1
            except (json.JSONDecodeError, OSError):
                continue

        if removed:
            logger.info(
                "cache_run_invalidated",
                run_id=run_id,
                pool_id=pool_id,
                removed=removed,
            )

        return removed

    def list_pools(self) -> List[str]:
        """List all pools with cached entries.

        Returns:
            List of pool identifiers.
        """
        pools: set[str] = set()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key_data = data.get("key", {})
                pool_id = key_data.get("pool_id")
                if pool_id:
                    pools.add(pool_id)
            except (json.JSONDecodeError, OSError):
                continue

        return sorted(pools)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache usage statistics.

        Returns:
            Dictionary with hit/miss rates, size, pool info, etc.
        """
        # Count cache files, total size, and pool distribution
        file_count = 0
        total_size = 0
        pools: set[str] = set()
        tool_counts: Dict[str, int] = {}

        for cache_file in self.cache_dir.glob("*.json"):
            file_count += 1
            try:
                total_size += cache_file.stat().st_size
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                key_data = data.get("key", {})
                pool_id = key_data.get("pool_id")
                if pool_id:
                    pools.add(pool_id)
                tool = key_data.get("tool", "unknown")
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
            except (OSError, json.JSONDecodeError):
                pass

        total_requests = self._stats.hits + self._stats.misses
        hit_rate = (
            self._stats.hits / total_requests * 100 if total_requests > 0 else 0
        )

        return {
            "cache_dir": str(self.cache_dir),
            "ttl_hours": self.ttl_hours,
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "writes": self._stats.writes,
            "expired_cleared": self._stats.expired_cleared,
            "hit_rate_percent": round(hit_rate, 1),
            "pools_tracked": len(pools),
            "tool_distribution": tool_counts,
        }

    def _remove_file(self, path: Path) -> bool:
        """Safely remove a file.

        Args:
            path: File to remove.

        Returns:
            True if removed successfully.
        """
        try:
            path.unlink(missing_ok=True)
            return True
        except OSError as e:
            logger.warning("file_remove_error", file=str(path), error=str(e))
            return False

    def _age_hours(self, cached_at: datetime) -> float:
        """Calculate age in hours.

        Args:
            cached_at: When result was cached.

        Returns:
            Age in hours.
        """
        now = datetime.now(timezone.utc)
        # Handle naive datetimes
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        delta = now - cached_at
        return delta.total_seconds() / 3600


@dataclass
class CacheStats:
    """Internal statistics for cache operations."""

    hits: int = 0
    misses: int = 0
    writes: int = 0
    expired_cleared: int = 0


# Convenience functions


def create_cache(cache_dir: Path, ttl_hours: int = 24) -> ToolResultCache:
    """Create a tool result cache.

    Args:
        cache_dir: Root cache directory.
        ttl_hours: Cache TTL in hours.

    Returns:
        ToolResultCache instance.
    """
    return ToolResultCache(cache_dir, ttl_hours)


__all__ = [
    "CacheKey",
    "CachedResult",
    "ToolResultCache",
    "create_cache",
]
