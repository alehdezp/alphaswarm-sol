"""Work queue with concurrency limits and backpressure for orchestration.

Provides durable work queue with:
- Persistent state via JSONL append-only log
- Concurrency limits (max_in_flight)
- Queue depth limits (max_queue_depth)
- Per-action limits for fine-grained control
- FIFO ordering with deterministic tie-breakers
- Backpressure signaling when limits exceeded

Storage Structure:
    .vrs/pools/{pool_id}/queue.jsonl

Usage:
    from alphaswarm_sol.orchestration.queue import WorkQueue, WorkItem, QueueLimits

    queue = WorkQueue(Path('.vrs/pools/test-pool'))

    # Enqueue work
    item = WorkItem(pool_id='test-pool', bead_id='b1', action='spawn_attacker')
    queue.enqueue(item)

    # Reserve items for processing (respects limits)
    reserved = queue.reserve(max_items=5)

    # Acknowledge completion
    queue.ack(item.item_id)

    # Handle failure with retry
    queue.nack(item.item_id, retry=True)

    # Get queue snapshot
    snapshot = queue.snapshot()

Phase 07.1.1-03: Production Orchestration Hardening - Work Queue
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkItemStatus(str, Enum):
    """Status of a work item."""

    QUEUED = "queued"  # Waiting to be processed
    RESERVED = "reserved"  # Being processed
    COMPLETED = "completed"  # Successfully processed
    FAILED = "failed"  # Failed processing
    DEAD = "dead"  # Exhausted retries


@dataclass
class WorkItem:
    """A unit of work in the queue.

    Attributes:
        pool_id: Pool this work belongs to
        bead_id: Bead being processed (or "*" for pool-level work)
        action: Action type (e.g., 'spawn_attacker', 'run_tool')
        payload_hash: Hash of action payload for deduplication
        enqueued_at: When the item was enqueued (ISO format)
        item_id: Unique item identifier (auto-generated from content hash)
        status: Current status
        reserved_at: When item was reserved
        attempts: Number of processing attempts
        metadata: Additional tracking data
    """

    pool_id: str
    bead_id: str
    action: str
    payload_hash: str = ""
    enqueued_at: str = ""
    item_id: str = ""
    status: WorkItemStatus = WorkItemStatus.QUEUED
    reserved_at: Optional[str] = None
    attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.enqueued_at:
            self.enqueued_at = datetime.now(timezone.utc).isoformat()

        if not self.item_id:
            # Generate deterministic ID from content
            content = f"{self.pool_id}:{self.bead_id}:{self.action}:{self.payload_hash}:{self.enqueued_at}"
            self.item_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "item_id": self.item_id,
            "pool_id": self.pool_id,
            "bead_id": self.bead_id,
            "action": self.action,
            "payload_hash": self.payload_hash,
            "enqueued_at": self.enqueued_at,
            "status": self.status.value,
            "reserved_at": self.reserved_at,
            "attempts": self.attempts,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkItem":
        """Create from dictionary."""
        return cls(
            item_id=data["item_id"],
            pool_id=data["pool_id"],
            bead_id=data["bead_id"],
            action=data["action"],
            payload_hash=data.get("payload_hash", ""),
            enqueued_at=data.get("enqueued_at", ""),
            status=WorkItemStatus(data.get("status", "queued")),
            reserved_at=data.get("reserved_at"),
            attempts=data.get("attempts", 0),
            metadata=data.get("metadata", {}),
        )

    @property
    def ordering_key(self) -> tuple:
        """Key for deterministic FIFO ordering.

        Returns tuple of (enqueued_at, item_id) for stable sorting.
        """
        return (self.enqueued_at, self.item_id)


@dataclass
class QueueLimits:
    """Configuration for queue limits.

    Attributes:
        max_in_flight: Maximum items being processed concurrently
        max_queue_depth: Maximum items waiting in queue (0 = unlimited)
        per_action_limits: Optional per-action concurrency limits
        max_retries: Maximum retry attempts before marking dead
        stale_reservation_seconds: Seconds before reserved item is considered stale
    """

    max_in_flight: int = 10
    max_queue_depth: int = 100
    per_action_limits: Dict[str, int] = field(default_factory=dict)
    max_retries: int = 3
    stale_reservation_seconds: int = 600  # 10 minutes

    def get_action_limit(self, action: str) -> int:
        """Get concurrency limit for a specific action.

        Falls back to max_in_flight if no per-action limit set.
        """
        return self.per_action_limits.get(action, self.max_in_flight)


@dataclass
class QueueSnapshot:
    """Point-in-time snapshot of queue state.

    Attributes:
        queued: Number of items waiting
        reserved: Number of items being processed
        completed: Number of completed items
        failed: Number of failed items
        dead: Number of dead (exhausted retries) items
        total: Total items ever enqueued
        by_action: Breakdown by action type
        at_capacity: Whether queue is at capacity
        backpressure: Whether backpressure is active
    """

    queued: int = 0
    reserved: int = 0
    completed: int = 0
    failed: int = 0
    dead: int = 0
    total: int = 0
    by_action: Dict[str, Dict[str, int]] = field(default_factory=dict)
    at_capacity: bool = False
    backpressure: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "queued": self.queued,
            "reserved": self.reserved,
            "completed": self.completed,
            "failed": self.failed,
            "dead": self.dead,
            "total": self.total,
            "by_action": self.by_action,
            "at_capacity": self.at_capacity,
            "backpressure": self.backpressure,
        }


class BackpressureError(Exception):
    """Raised when queue is at capacity and cannot accept more items."""

    pass


class WorkQueue:
    """Persistent work queue with concurrency limits and backpressure.

    Provides durable work queue backed by JSONL append-only log.
    Supports reservation protocol for concurrent processing.

    Storage format:
        .vrs/pools/{pool_id}/queue.jsonl

    Each line is a JSON record representing a state transition.
    The latest record for each item_id represents current state.

    Example:
        queue = WorkQueue(Path('.vrs/pools/test-pool'))

        # Enqueue work
        item = WorkItem(pool_id='test-pool', bead_id='b1', action='spawn_attacker')
        queue.enqueue(item)

        # Reserve and process
        reserved = queue.reserve(max_items=5)
        for item in reserved:
            try:
                process(item)
                queue.ack(item.item_id)
            except Exception:
                queue.nack(item.item_id, retry=True)
    """

    JSONL_FILENAME = "queue.jsonl"

    def __init__(
        self,
        pool_path: Path,
        limits: Optional[QueueLimits] = None,
    ):
        """Initialize work queue.

        Args:
            pool_path: Path to pool directory (e.g., .vrs/pools/pool-abc)
            limits: Queue limits configuration
        """
        self.pool_path = Path(pool_path)
        self.pool_path.mkdir(parents=True, exist_ok=True)
        self.limits = limits or QueueLimits()

        # In-memory state rebuilt from JSONL
        self._items: Dict[str, WorkItem] = {}
        self._load_state()

    @property
    def jsonl_path(self) -> Path:
        """Path to JSONL storage file."""
        return self.pool_path / self.JSONL_FILENAME

    def _load_state(self) -> None:
        """Load all records into memory from JSONL."""
        if not self.jsonl_path.exists():
            return

        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    item = WorkItem.from_dict(data)
                    self._items[item.item_id] = item
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Skipping corrupted queue record: {e}")

    def _append_record(self, item: WorkItem) -> None:
        """Append item state to JSONL and update cache."""
        self._items[item.item_id] = item

        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item.to_dict()) + "\n")

    def _count_by_status(self, status: WorkItemStatus) -> int:
        """Count items by status."""
        return sum(1 for i in self._items.values() if i.status == status)

    def _count_reserved_by_action(self, action: str) -> int:
        """Count reserved items for a specific action."""
        return sum(
            1 for i in self._items.values()
            if i.status == WorkItemStatus.RESERVED and i.action == action
        )

    def _is_stale_reservation(self, item: WorkItem) -> bool:
        """Check if a reserved item is stale (timed out)."""
        if item.status != WorkItemStatus.RESERVED or not item.reserved_at:
            return False

        try:
            reserved_time = datetime.fromisoformat(item.reserved_at.replace("Z", "+00:00"))
            age_seconds = (datetime.now(timezone.utc) - reserved_time).total_seconds()
            return age_seconds > self.limits.stale_reservation_seconds
        except (ValueError, TypeError):
            return False

    def enqueue(
        self,
        item: WorkItem,
        force: bool = False,
    ) -> bool:
        """Add item to queue.

        Args:
            item: Work item to enqueue
            force: If True, bypass backpressure check

        Returns:
            True if enqueued, False if duplicate

        Raises:
            BackpressureError: If queue at capacity and force=False
        """
        # Check for duplicate
        existing = self._items.get(item.item_id)
        if existing and existing.status in (
            WorkItemStatus.QUEUED,
            WorkItemStatus.RESERVED,
        ):
            logger.debug(f"Duplicate item ignored: {item.item_id}")
            return False

        # Check queue depth limit
        queued_count = self._count_by_status(WorkItemStatus.QUEUED)
        if (
            not force
            and self.limits.max_queue_depth > 0
            and queued_count >= self.limits.max_queue_depth
        ):
            raise BackpressureError(
                f"Queue at capacity: {queued_count}/{self.limits.max_queue_depth}"
            )

        # Set status and enqueue
        item.status = WorkItemStatus.QUEUED
        item.attempts = 0
        self._append_record(item)

        logger.debug(f"Enqueued item {item.item_id} for action {item.action}")
        return True

    def reserve(
        self,
        max_items: Optional[int] = None,
        action_filter: Optional[str] = None,
    ) -> List[WorkItem]:
        """Reserve items for processing.

        Respects max_in_flight and per-action limits.
        Items are returned in FIFO order with deterministic tie-breakers.

        Args:
            max_items: Maximum items to reserve (None = up to max_in_flight)
            action_filter: Only reserve items with this action

        Returns:
            List of reserved items (may be empty if at capacity or no work)
        """
        # Calculate available capacity
        current_reserved = self._count_by_status(WorkItemStatus.RESERVED)
        available_global = self.limits.max_in_flight - current_reserved

        if available_global <= 0:
            return []

        # Get queued items sorted by ordering key (FIFO + deterministic)
        queued = [
            i for i in self._items.values()
            if i.status == WorkItemStatus.QUEUED
            and (action_filter is None or i.action == action_filter)
        ]

        # Also include stale reservations (timed out)
        stale = [
            i for i in self._items.values()
            if self._is_stale_reservation(i)
            and (action_filter is None or i.action == action_filter)
        ]

        if stale:
            logger.info(f"Found {len(stale)} stale reservations, re-reserving")

        candidates = queued + stale
        candidates.sort(key=lambda x: x.ordering_key)

        # Apply limits
        max_to_reserve = max_items or available_global
        max_to_reserve = min(max_to_reserve, available_global)

        reserved = []
        now = datetime.now(timezone.utc).isoformat()

        for item in candidates:
            if len(reserved) >= max_to_reserve:
                break

            # Check per-action limit
            action_limit = self.limits.get_action_limit(item.action)
            action_reserved = self._count_reserved_by_action(item.action)
            if action_reserved >= action_limit:
                continue

            # Reserve the item
            item.status = WorkItemStatus.RESERVED
            item.reserved_at = now
            item.attempts += 1
            self._append_record(item)
            reserved.append(item)

        if reserved:
            logger.debug(f"Reserved {len(reserved)} items")

        return reserved

    def ack(self, item_id: str) -> bool:
        """Acknowledge successful processing.

        Args:
            item_id: ID of completed item

        Returns:
            True if acknowledged, False if item not found or not reserved
        """
        item = self._items.get(item_id)
        if not item:
            logger.warning(f"Ack for unknown item: {item_id}")
            return False

        if item.status != WorkItemStatus.RESERVED:
            logger.warning(f"Ack for non-reserved item: {item_id} (status: {item.status})")
            return False

        item.status = WorkItemStatus.COMPLETED
        self._append_record(item)

        logger.debug(f"Acknowledged completion: {item_id}")
        return True

    def nack(
        self,
        item_id: str,
        retry: bool = True,
        error: Optional[str] = None,
    ) -> bool:
        """Negative acknowledgment (processing failed).

        Args:
            item_id: ID of failed item
            retry: If True, requeue for retry (if retries remaining)
            error: Optional error message to record

        Returns:
            True if acknowledged, False if item not found or not reserved
        """
        item = self._items.get(item_id)
        if not item:
            logger.warning(f"Nack for unknown item: {item_id}")
            return False

        if item.status != WorkItemStatus.RESERVED:
            logger.warning(f"Nack for non-reserved item: {item_id} (status: {item.status})")
            return False

        if error:
            item.metadata["last_error"] = error

        # Check retry eligibility
        if retry and item.attempts < self.limits.max_retries:
            item.status = WorkItemStatus.QUEUED
            item.reserved_at = None
            logger.debug(f"Requeued item {item_id} for retry (attempt {item.attempts}/{self.limits.max_retries})")
        elif retry:
            # Exhausted retries
            item.status = WorkItemStatus.DEAD
            logger.warning(f"Item {item_id} exhausted retries, marked dead")
        else:
            item.status = WorkItemStatus.FAILED
            logger.debug(f"Item {item_id} marked failed (no retry)")

        self._append_record(item)
        return True

    def snapshot(self) -> Dict[str, Any]:
        """Get point-in-time snapshot of queue state.

        Returns:
            Dictionary with queue statistics
        """
        # Count by status
        queued = 0
        reserved = 0
        completed = 0
        failed = 0
        dead = 0
        by_action: Dict[str, Dict[str, int]] = {}

        for item in self._items.values():
            # Track by action
            if item.action not in by_action:
                by_action[item.action] = {
                    "queued": 0,
                    "reserved": 0,
                    "completed": 0,
                    "failed": 0,
                    "dead": 0,
                }

            action_stats = by_action[item.action]

            if item.status == WorkItemStatus.QUEUED:
                queued += 1
                action_stats["queued"] += 1
            elif item.status == WorkItemStatus.RESERVED:
                reserved += 1
                action_stats["reserved"] += 1
            elif item.status == WorkItemStatus.COMPLETED:
                completed += 1
                action_stats["completed"] += 1
            elif item.status == WorkItemStatus.FAILED:
                failed += 1
                action_stats["failed"] += 1
            elif item.status == WorkItemStatus.DEAD:
                dead += 1
                action_stats["dead"] += 1

        # Check capacity status
        at_capacity = reserved >= self.limits.max_in_flight
        backpressure = (
            self.limits.max_queue_depth > 0
            and queued >= self.limits.max_queue_depth
        )

        return QueueSnapshot(
            queued=queued,
            reserved=reserved,
            completed=completed,
            failed=failed,
            dead=dead,
            total=len(self._items),
            by_action=by_action,
            at_capacity=at_capacity,
            backpressure=backpressure,
        ).to_dict()

    def get_item(self, item_id: str) -> Optional[WorkItem]:
        """Get item by ID.

        Args:
            item_id: Item identifier

        Returns:
            WorkItem if found, None otherwise
        """
        return self._items.get(item_id)

    def list_items(
        self,
        status: Optional[WorkItemStatus] = None,
        action: Optional[str] = None,
    ) -> List[WorkItem]:
        """List items optionally filtered by status and/or action.

        Args:
            status: Filter by status
            action: Filter by action

        Returns:
            List of matching items
        """
        items = list(self._items.values())

        if status is not None:
            items = [i for i in items if i.status == status]

        if action is not None:
            items = [i for i in items if i.action == action]

        return items

    def clear(self, include_completed: bool = False) -> int:
        """Clear queue state (for testing/recovery).

        Args:
            include_completed: If True, also clear completed items

        Returns:
            Number of items cleared
        """
        if include_completed:
            count = len(self._items)
            self._items.clear()
        else:
            # Only clear queued/reserved items
            to_remove = [
                k for k, v in self._items.items()
                if v.status in (WorkItemStatus.QUEUED, WorkItemStatus.RESERVED)
            ]
            count = len(to_remove)
            for k in to_remove:
                del self._items[k]

        return count

    def compact(self) -> int:
        """Compact JSONL by rewriting with only current state.

        Useful for reducing file size after many updates.

        Returns:
            Number of bytes saved
        """
        if not self.jsonl_path.exists():
            return 0

        old_size = self.jsonl_path.stat().st_size

        # Write current state to temp file
        temp_path = self.jsonl_path.with_suffix(".jsonl.tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            for item in self._items.values():
                f.write(json.dumps(item.to_dict()) + "\n")

        # Replace original
        temp_path.replace(self.jsonl_path)

        new_size = self.jsonl_path.stat().st_size
        saved = old_size - new_size

        if saved > 0:
            logger.info(f"Compacted queue, saved {saved} bytes")

        return saved


# Export for module
__all__ = [
    "WorkItemStatus",
    "WorkItem",
    "QueueLimits",
    "QueueSnapshot",
    "BackpressureError",
    "WorkQueue",
]
