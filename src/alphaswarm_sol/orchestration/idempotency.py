"""Idempotency key store and helpers for orchestration.

Prevents duplicated side effects under retries while keeping orchestration
resilient to transient failures.

Key Features:
- Deterministic key generation: hash(pool_id + bead_id + action + payload_hash)
- JSONL append-only storage under .vrs/pools/{pool_id}/idempotency.jsonl
- Reserve/commit protocol for concurrent execution protection
- Bounded retry with exponential backoff and jitter

Usage:
    from alphaswarm_sol.orchestration.idempotency import (
        IdempotencyStore, RetryConfig, idempotent_execute
    )

    store = IdempotencyStore(Path('.vrs/pools/test-pool'))
    key = store.make_key(pool_id='test-pool', bead_id='b1', action='tool', payload_hash='abc')

    # Check if already executed
    result = store.get(key)
    if result:
        return result.value  # Skip execution, return cached

    # Reserve before execution
    if not store.reserve(key):
        raise RuntimeError("Key already reserved by another process")

    try:
        value = execute_action()
        store.record_success(key, value)
    except Exception as e:
        store.record_failure(key, str(e))
        raise

Phase 07.1.1-02: Production Orchestration Hardening
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)


class IdempotencyStatus(str, Enum):
    """Status of an idempotency record."""

    RESERVED = "reserved"  # Execution in progress
    SUCCESS = "success"  # Completed successfully
    FAILURE = "failure"  # Failed (may retry)


@dataclass
class IdempotencyRecord:
    """Record of an idempotent operation.

    Attributes:
        key: Deterministic idempotency key
        status: Current status (reserved, success, failure)
        timestamp: When the record was created/updated
        attempts: Number of execution attempts
        result: Stored result if successful
        error: Error message if failed
        last_error: Most recent error (for retry tracking)
        metadata: Additional tracking data
    """

    key: str
    status: IdempotencyStatus
    timestamp: str = ""
    attempts: int = 1
    result: Optional[Any] = None
    error: Optional[str] = None
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "attempts": self.attempts,
            "result": self.result,
            "error": self.error,
            "last_error": self.last_error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IdempotencyRecord":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            status=IdempotencyStatus(data["status"]),
            timestamp=data.get("timestamp", ""),
            attempts=data.get("attempts", 1),
            result=data.get("result"),
            error=data.get("error"),
            last_error=data.get("last_error"),
            metadata=data.get("metadata", {}),
        )

    @property
    def is_complete(self) -> bool:
        """Whether the operation completed (success or permanent failure)."""
        return self.status == IdempotencyStatus.SUCCESS

    @property
    def is_retryable(self) -> bool:
        """Whether the operation can be retried."""
        return self.status == IdempotencyStatus.FAILURE


@dataclass
class RetryConfig:
    """Configuration for retry with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Maximum random jitter to add (0-1 fraction of delay)
        retryable_errors: Error substrings that indicate transient failures
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.25
    retryable_errors: tuple = (
        "timeout",
        "connection",
        "temporary",
        "rate limit",
        "retry",
        "unavailable",
        "503",
        "429",
    )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number with jitter.

        Uses exponential backoff: delay = min(base * 2^attempt, max)
        Plus random jitter to prevent thundering herd.

        Args:
            attempt: Zero-indexed attempt number

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)

        # Add jitter (random fraction of delay)
        if self.jitter > 0:
            jitter_amount = delay * self.jitter * random.random()
            delay += jitter_amount

        return delay

    def is_retryable_error(self, error: str) -> bool:
        """Check if error message indicates a retryable failure.

        Args:
            error: Error message string

        Returns:
            True if error is transient and worth retrying
        """
        error_lower = error.lower()
        return any(pattern in error_lower for pattern in self.retryable_errors)


class IdempotencyStore:
    """Store for idempotency keys with JSONL persistence.

    Provides:
    - Deterministic key generation from pool/bead/action/payload
    - JSONL append-only storage for durability
    - Reserve/commit protocol for concurrent execution
    - Query interface for cached results

    Storage format:
        .vrs/pools/{pool_id}/idempotency.jsonl

    Each line is a JSON record representing a state transition.
    The latest record for each key represents current state.
    """

    JSONL_FILENAME = "idempotency.jsonl"

    def __init__(self, pool_path: Path):
        """Initialize idempotency store.

        Args:
            pool_path: Path to pool directory (e.g., .vrs/pools/pool-abc)
        """
        self.pool_path = Path(pool_path)
        self.pool_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, IdempotencyRecord] = {}
        self._load_cache()

    @property
    def jsonl_path(self) -> Path:
        """Path to JSONL storage file."""
        return self.pool_path / self.JSONL_FILENAME

    def _load_cache(self) -> None:
        """Load all records into memory cache."""
        if not self.jsonl_path.exists():
            return

        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    record = IdempotencyRecord.from_dict(data)
                    self._cache[record.key] = record
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Skipping corrupted idempotency record: {e}")

    def _append_record(self, record: IdempotencyRecord) -> None:
        """Append record to JSONL file and update cache."""
        self._cache[record.key] = record

        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    @staticmethod
    def make_key(
        pool_id: str,
        bead_id: str,
        action: str,
        payload_hash: str,
    ) -> str:
        """Generate deterministic idempotency key.

        Key format: SHA256(pool_id + bead_id + action + payload_hash)[:16]

        Args:
            pool_id: Pool identifier
            bead_id: Bead identifier
            action: Action type (e.g., 'tool', 'agent', 'spawn')
            payload_hash: Hash of the action payload

        Returns:
            16-character hex string key
        """
        combined = f"{pool_id}:{bead_id}:{action}:{payload_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    @staticmethod
    def hash_payload(payload: Any) -> str:
        """Hash a payload for key generation.

        Args:
            payload: Any JSON-serializable payload

        Returns:
            SHA256 hash of JSON-serialized payload
        """
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        """Get record for idempotency key.

        Args:
            key: Idempotency key

        Returns:
            Record if exists, None otherwise
        """
        return self._cache.get(key)

    def reserve(self, key: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Reserve a key before execution.

        Returns False if key is already reserved or completed.
        This provides basic concurrent execution protection.

        Args:
            key: Idempotency key to reserve
            metadata: Optional metadata to attach

        Returns:
            True if reserved, False if already exists
        """
        existing = self._cache.get(key)

        # Already completed - don't re-reserve
        if existing and existing.is_complete:
            return False

        # Already reserved by another execution
        if existing and existing.status == IdempotencyStatus.RESERVED:
            # Check if it's stale (> 10 minutes old)
            try:
                reserved_time = datetime.fromisoformat(existing.timestamp.replace("Z", "+00:00"))
                age_seconds = (datetime.now(timezone.utc) - reserved_time).total_seconds()
                if age_seconds < 600:  # 10 minutes
                    return False
                # Stale reservation - allow re-reserve
                logger.warning(f"Re-reserving stale key {key} (age: {age_seconds}s)")
            except (ValueError, TypeError):
                return False

        # Create reservation record
        record = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.RESERVED,
            attempts=1 if not existing else existing.attempts + 1,
            metadata=metadata or {},
        )
        self._append_record(record)
        return True

    def record_success(self, key: str, result: Any) -> IdempotencyRecord:
        """Record successful completion.

        Args:
            key: Idempotency key
            result: Result value to cache

        Returns:
            Updated record
        """
        existing = self._cache.get(key)
        record = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.SUCCESS,
            attempts=existing.attempts if existing else 1,
            result=result,
            metadata=existing.metadata if existing else {},
        )
        self._append_record(record)
        logger.debug(f"Recorded success for idempotency key {key}")
        return record

    def record_failure(
        self,
        key: str,
        error: str,
        permanent: bool = False,
    ) -> IdempotencyRecord:
        """Record execution failure.

        Args:
            key: Idempotency key
            error: Error message
            permanent: If True, marks as non-retryable

        Returns:
            Updated record
        """
        existing = self._cache.get(key)
        record = IdempotencyRecord(
            key=key,
            status=IdempotencyStatus.SUCCESS if permanent else IdempotencyStatus.FAILURE,
            attempts=existing.attempts if existing else 1,
            error=error if permanent else None,
            last_error=error,
            metadata=existing.metadata if existing else {},
        )
        self._append_record(record)
        logger.debug(f"Recorded failure for idempotency key {key}: {error}")
        return record

    def clear_key(self, key: str) -> bool:
        """Clear a key from the store (for testing/recovery).

        Note: This doesn't remove from JSONL, just updates cache.
        JSONL is append-only for audit trail.

        Args:
            key: Key to clear

        Returns:
            True if key existed
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def list_keys(self, status: Optional[IdempotencyStatus] = None) -> list[str]:
        """List all keys, optionally filtered by status.

        Args:
            status: Filter by status (None = all)

        Returns:
            List of keys
        """
        if status is None:
            return list(self._cache.keys())
        return [k for k, v in self._cache.items() if v.status == status]

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about stored records.

        Returns:
            Dict with counts by status
        """
        stats = {
            "total": len(self._cache),
            "reserved": 0,
            "success": 0,
            "failure": 0,
        }
        for record in self._cache.values():
            stats[record.status.value] += 1
        return stats


# Type variable for generic retry wrapper
T = TypeVar("T")


def idempotent_execute(
    store: IdempotencyStore,
    key: str,
    func: Callable[[], T],
    retry_config: Optional[RetryConfig] = None,
) -> T:
    """Execute a function with idempotency and retry support.

    If the key has a cached successful result, returns it without re-executing.
    Otherwise reserves the key, executes the function, and records the result.

    Args:
        store: Idempotency store instance
        key: Idempotency key for this operation
        func: Zero-argument callable to execute
        retry_config: Retry configuration (None = no retries)

    Returns:
        Function result (from cache or fresh execution)

    Raises:
        Exception: If all retries exhausted or non-retryable error
        RuntimeError: If key reservation fails
    """
    config = retry_config or RetryConfig(max_retries=0)

    # Check for cached result
    existing = store.get(key)
    if existing and existing.is_complete:
        logger.debug(f"Returning cached result for key {key}")
        return existing.result

    # Reserve key
    if not store.reserve(key):
        # Check if it completed while we were trying to reserve
        existing = store.get(key)
        if existing and existing.is_complete:
            return existing.result
        raise RuntimeError(f"Failed to reserve idempotency key {key}")

    # Execute with retries
    last_error: Optional[Exception] = None
    attempt = 0

    while attempt <= config.max_retries:
        try:
            result = func()
            store.record_success(key, result)
            return result

        except Exception as e:
            last_error = e
            error_str = str(e)

            # Check if retryable
            if not config.is_retryable_error(error_str):
                store.record_failure(key, error_str, permanent=True)
                raise

            # Check if retries exhausted
            if attempt >= config.max_retries:
                store.record_failure(key, error_str, permanent=True)
                raise

            # Record transient failure and retry
            store.record_failure(key, error_str, permanent=False)

            delay = config.calculate_delay(attempt)
            logger.info(
                f"Retry {attempt + 1}/{config.max_retries} for key {key} "
                f"after {delay:.2f}s delay: {error_str}"
            )
            time.sleep(delay)
            attempt += 1

            # Re-reserve for next attempt
            store.reserve(key)

    # Should not reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError(f"Unexpected state in idempotent_execute for key {key}")


# Export for module
__all__ = [
    "IdempotencyStatus",
    "IdempotencyRecord",
    "RetryConfig",
    "IdempotencyStore",
    "idempotent_execute",
]
