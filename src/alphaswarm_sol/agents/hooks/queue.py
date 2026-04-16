"""Prioritized bead queue for agent work distribution.

This module implements a min-heap priority queue for beads, ordered by:
1. Severity (critical > high > medium > low)
2. Exploitability (exploitable beads prioritized within severity)
3. Tool agreement (multiple tools flagging same issue)
4. Recency (older beads first as tiebreaker)

Per PHILOSOPHY.md Orchestration Principles:
"Each agent has a hook (inbox) with a prioritized bead queue"

Usage:
    from alphaswarm_sol.agents.hooks import PrioritizedBeadQueue, BeadPriority

    queue = PrioritizedBeadQueue()
    queue.push(bead)

    # Get highest priority bead
    next_bead = queue.pop()

    # Peek without removing
    top_bead = queue.peek()
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from heapq import heappop, heappush
from typing import List, Optional, Set

from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.types import Severity


class BeadPriority(IntEnum):
    """Priority levels for beads per PHILOSOPHY.md ordering.

    Priority is determined by:
    1. Severity: critical > high > medium > low
    2. Exploitability: exploitable beads prioritized within severity
    3. Tool agreement: multiple tools flagging same issue
    4. Recency: older beads first as tiebreaker (FIFO within priority)

    Lower enum value = higher priority (for min-heap ordering).

    Usage:
        priority = BeadPriority.CRITICAL_EXPLOITABLE
        if priority < BeadPriority.HIGH:
            print("High priority!")  # True, critical > high
    """

    CRITICAL_EXPLOITABLE = 1  # Critical + exploitable
    CRITICAL = 2  # Critical severity
    HIGH_EXPLOITABLE = 3  # High + exploitable
    HIGH = 4  # High severity
    MEDIUM_TOOL_AGREEMENT = 5  # Medium + multiple tools agree
    MEDIUM = 6  # Medium severity
    LOW = 7  # Low severity


@dataclass
class PrioritizedBead:
    """Wrapper for bead with computed priority and timestamp.

    Used internally by PrioritizedBeadQueue for heap ordering.

    Attributes:
        priority: Computed priority level
        timestamp: When added to queue (for recency tiebreaker)
        bead: The actual vulnerability bead

    Usage:
        item = PrioritizedBead(
            priority=BeadPriority.CRITICAL,
            timestamp=datetime.now(),
            bead=my_bead
        )
        # Items are compared by priority, then timestamp
    """

    priority: BeadPriority
    timestamp: datetime
    bead: VulnerabilityBead

    def __lt__(self, other: "PrioritizedBead") -> bool:
        """Comparison for heapq - lower priority value = higher priority.

        For equal priorities, older beads come first (FIFO within priority).
        """
        if self.priority != other.priority:
            return self.priority < other.priority
        # Recency tiebreaker: older beads first (FIFO within priority)
        return self.timestamp < other.timestamp

    def __eq__(self, other: object) -> bool:
        """Equality based on bead ID."""
        if not isinstance(other, PrioritizedBead):
            return NotImplemented
        return self.bead.id == other.bead.id


class PrioritizedBeadQueue:
    """Min-heap priority queue for beads.

    Implements a priority queue that orders beads by severity, exploitability,
    tool agreement, and recency. Higher severity beads are processed first.

    The queue prevents duplicate beads and provides O(1) contains check.

    Attributes:
        _heap: Internal min-heap of PrioritizedBead items
        _bead_ids: Set of bead IDs for O(1) contains check

    Usage:
        queue = PrioritizedBeadQueue()

        # Add beads
        queue.push(critical_bead)
        queue.push(medium_bead)

        # Get highest priority
        bead = queue.pop()  # Returns critical_bead

        # Check membership
        if bead.id in queue:
            print("Already queued")

        # Check size
        print(f"Queue has {len(queue)} beads")
    """

    def __init__(self) -> None:
        """Initialize empty priority queue."""
        self._heap: List[PrioritizedBead] = []
        self._bead_ids: Set[str] = set()

    def push(self, bead: VulnerabilityBead) -> None:
        """Add bead with computed priority.

        If the bead is already in the queue (by ID), this is a no-op.

        Args:
            bead: VulnerabilityBead to add to queue

        Usage:
            queue.push(bead)
            queue.push(bead)  # No effect, already in queue
        """
        if bead.id in self._bead_ids:
            return  # Already in queue
        priority = self._compute_priority(bead)
        item = PrioritizedBead(priority, datetime.now(), bead)
        heappush(self._heap, item)
        self._bead_ids.add(bead.id)

    def pop(self) -> Optional[VulnerabilityBead]:
        """Remove and return highest priority bead.

        Returns:
            Highest priority bead, or None if queue is empty

        Usage:
            bead = queue.pop()
            if bead:
                process(bead)
        """
        while self._heap:
            item = heappop(self._heap)
            # Check if this bead is still valid (not removed)
            if item.bead.id in self._bead_ids:
                self._bead_ids.remove(item.bead.id)
                return item.bead
        return None

    def peek(self) -> Optional[VulnerabilityBead]:
        """Return highest priority bead without removing.

        Removes any stale entries (beads that were removed from _bead_ids)
        until a valid bead is found or the heap is empty.

        Returns:
            Highest priority bead, or None if queue is empty

        Usage:
            top = queue.peek()
            if top and top.severity == Severity.CRITICAL:
                handle_critical()
        """
        while self._heap:
            if self._heap[0].bead.id in self._bead_ids:
                return self._heap[0].bead
            heappop(self._heap)  # Remove stale entry
        return None

    def remove(self, bead_id: str) -> bool:
        """Remove a bead from the queue by ID.

        This marks the bead as removed; it will be skipped on pop/peek.
        The actual heap entry is removed lazily during pop/peek operations.

        Args:
            bead_id: ID of bead to remove

        Returns:
            True if bead was in queue and removed, False otherwise

        Usage:
            if queue.remove("VKG-042"):
                print("Removed from queue")
        """
        if bead_id in self._bead_ids:
            self._bead_ids.remove(bead_id)
            return True
        return False

    def clear(self) -> None:
        """Remove all beads from the queue.

        Usage:
            queue.clear()
            assert len(queue) == 0
        """
        self._heap.clear()
        self._bead_ids.clear()

    def _compute_priority(self, bead: VulnerabilityBead) -> BeadPriority:
        """Compute priority per PHILOSOPHY.md ordering.

        Priority factors:
        1. Severity: critical > high > medium > low
        2. Exploitability: determined by "exploitable" in why_flagged
        3. Tool agreement: determined by "tool_agreement" in notes

        Args:
            bead: VulnerabilityBead to compute priority for

        Returns:
            BeadPriority enum value
        """
        is_critical = bead.severity == Severity.CRITICAL
        is_high = bead.severity == Severity.HIGH

        # Check exploitability from pattern context
        # "exploitable" in why_flagged indicates demonstrated exploitability
        why_flagged = bead.pattern_context.why_flagged.lower()
        is_exploitable = "exploitable" in why_flagged or "exploit" in why_flagged

        # Also check metadata for tool-provided exploitability info
        if bead.metadata.get("exploitable", False):
            is_exploitable = True

        # Check tool agreement from notes (populated by tool integration phase)
        # Notes like "[tool_agreement] Slither and Mythril both flagged"
        has_tool_agreement = any(
            "tool_agreement" in note.lower() for note in bead.notes
        )

        # Also check metadata for tool agreement info
        if bead.metadata.get("tool_agreement", False):
            has_tool_agreement = True
        if bead.metadata.get("tool_count", 0) >= 2:
            has_tool_agreement = True

        # Compute priority based on factors
        if is_critical and is_exploitable:
            return BeadPriority.CRITICAL_EXPLOITABLE
        if is_critical:
            return BeadPriority.CRITICAL
        if is_high and is_exploitable:
            return BeadPriority.HIGH_EXPLOITABLE
        if is_high:
            return BeadPriority.HIGH
        if has_tool_agreement:
            return BeadPriority.MEDIUM_TOOL_AGREEMENT
        if bead.severity == Severity.MEDIUM:
            return BeadPriority.MEDIUM
        return BeadPriority.LOW

    def get_priority(self, bead: VulnerabilityBead) -> BeadPriority:
        """Get priority for a bead without adding it to queue.

        Useful for inspecting what priority a bead would have.

        Args:
            bead: VulnerabilityBead to get priority for

        Returns:
            BeadPriority that would be assigned
        """
        return self._compute_priority(bead)

    def __len__(self) -> int:
        """Return number of beads in queue.

        Note: This is O(1) as we track bead IDs in a set.
        """
        return len(self._bead_ids)

    def __contains__(self, bead_id: str) -> bool:
        """Check if bead ID is in queue.

        Args:
            bead_id: ID to check

        Returns:
            True if bead is in queue

        Usage:
            if "VKG-042" in queue:
                print("Already queued")
        """
        return bead_id in self._bead_ids

    def __bool__(self) -> bool:
        """Return True if queue is not empty."""
        return len(self._bead_ids) > 0

    def __repr__(self) -> str:
        """Return string representation."""
        return f"PrioritizedBeadQueue(size={len(self)})"


# Export all public types
__all__ = [
    "BeadPriority",
    "PrioritizedBead",
    "PrioritizedBeadQueue",
]
