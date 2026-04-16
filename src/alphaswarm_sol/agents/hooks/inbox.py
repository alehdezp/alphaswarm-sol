"""Agent inbox management for work distribution.

This module implements per-agent work inboxes with prioritized queues.

Per 05.2-CONTEXT.md retry configuration:
- max_retries: 3 (retry up to 3 times before escalating)
- requeue_on_failure: True (requeue failed work for retry)
- escalate_threshold: 3 (escalate to supervisor after 3 failures)

Usage:
    from alphaswarm_sol.agents.hooks import AgentInbox, InboxConfig, AgentRole

    inbox = AgentInbox(AgentRole.ATTACKER)
    inbox.assign(bead)

    claim = inbox.claim_work()
    if claim:
        try:
            result = process(claim.bead)
            inbox.complete_work(claim.bead.id)
        except Exception:
            if inbox.fail_work(claim.bead.id):
                # Should escalate to supervisor
                escalate(claim.bead)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.agents.hooks.queue import PrioritizedBeadQueue

if TYPE_CHECKING:
    from alphaswarm_sol.agents.hooks import AgentRole


@dataclass
class InboxConfig:
    """Configuration for agent inbox.

    Attributes:
        max_queue_size: Maximum beads allowed in queue (default 100)
        max_retries: Maximum retry attempts per bead (default 3)
        requeue_on_failure: Whether to requeue failed work (default True)
        escalate_threshold: Failures before escalation (default 3)
        timeout_seconds: Timeout for claimed work in seconds (default 3600)

    Usage:
        config = InboxConfig(
            max_queue_size=50,
            max_retries=5,
            escalate_threshold=3
        )
        inbox = AgentInbox(AgentRole.ATTACKER, config)
    """

    max_queue_size: int = 100
    max_retries: int = 3
    requeue_on_failure: bool = True
    escalate_threshold: int = 3
    timeout_seconds: int = 3600  # 1 hour default

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_queue_size": self.max_queue_size,
            "max_retries": self.max_retries,
            "requeue_on_failure": self.requeue_on_failure,
            "escalate_threshold": self.escalate_threshold,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InboxConfig":
        """Create InboxConfig from dictionary."""
        return cls(
            max_queue_size=int(data.get("max_queue_size", 100)),
            max_retries=int(data.get("max_retries", 3)),
            requeue_on_failure=bool(data.get("requeue_on_failure", True)),
            escalate_threshold=int(data.get("escalate_threshold", 3)),
            timeout_seconds=int(data.get("timeout_seconds", 3600)),
        )


@dataclass
class WorkClaim:
    """Represents claimed work from an inbox.

    When an agent claims work, a WorkClaim is created to track:
    - Which bead is being worked on
    - Which agent claimed it
    - When it was claimed
    - How many attempts have been made

    Attributes:
        bead: The VulnerabilityBead being worked on
        agent_role: Role of the agent that claimed work
        claimed_at: Timestamp of claim
        attempt: Current attempt number (1-indexed)

    Usage:
        claim = inbox.claim_work()
        if claim:
            print(f"Attempt {claim.attempt} for {claim.bead.id}")
            process(claim.bead)
            inbox.complete_work(claim.bead.id)
    """

    bead: VulnerabilityBead
    agent_role: str  # Using str to avoid circular import
    claimed_at: datetime
    attempt: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bead_id": self.bead.id,
            "agent_role": self.agent_role,
            "claimed_at": self.claimed_at.isoformat(),
            "attempt": self.attempt,
        }

    @property
    def is_first_attempt(self) -> bool:
        """Check if this is the first attempt."""
        return self.attempt == 1

    @property
    def duration_seconds(self) -> float:
        """Get duration since claim in seconds."""
        return (datetime.now() - self.claimed_at).total_seconds()


class AgentInbox:
    """Per-agent work inbox with prioritized queue.

    Each agent has an inbox that:
    - Holds a prioritized queue of beads to process
    - Tracks work in progress
    - Handles failure/retry/escalation logic
    - Supports state persistence

    Attributes:
        agent_role: Role of the agent owning this inbox
        config: Inbox configuration
        _queue: Prioritized bead queue
        _in_progress: Map of bead_id -> WorkClaim for active work
        _failure_counts: Map of bead_id -> failure count
        _completed: Set of completed bead IDs (for history)

    Usage:
        inbox = AgentInbox(AgentRole.ATTACKER)

        # Assign beads
        inbox.assign(bead1)
        inbox.assign(bead2)

        # Process work
        while claim := inbox.claim_work():
            try:
                result = process(claim.bead)
                inbox.complete_work(claim.bead.id)
            except Exception:
                if inbox.fail_work(claim.bead.id):
                    escalate_to_supervisor(claim.bead)
    """

    def __init__(
        self,
        agent_role: "AgentRole",
        config: Optional[InboxConfig] = None,
    ) -> None:
        """Initialize inbox for an agent.

        Args:
            agent_role: Role of the agent
            config: Optional inbox configuration
        """
        # Store role as string to avoid issues with enum comparison
        self.agent_role = agent_role.value if hasattr(agent_role, "value") else str(agent_role)
        self.config = config or InboxConfig()
        self._queue = PrioritizedBeadQueue()
        self._in_progress: Dict[str, WorkClaim] = {}
        self._failure_counts: Dict[str, int] = {}
        self._completed: List[str] = []  # History of completed bead IDs

    def assign(self, bead: VulnerabilityBead) -> bool:
        """Assign bead to this inbox.

        The bead is added to the prioritized queue. If the queue is full,
        the assignment is rejected.

        Args:
            bead: VulnerabilityBead to assign

        Returns:
            True if assigned, False if queue is full or already in inbox

        Usage:
            if inbox.assign(bead):
                print(f"Assigned {bead.id}")
            else:
                print("Inbox full or duplicate")
        """
        # Check if already in queue or in progress
        if bead.id in self._queue or bead.id in self._in_progress:
            return False

        # Check queue size limit
        if len(self._queue) >= self.config.max_queue_size:
            return False

        self._queue.push(bead)
        return True

    def assign_many(self, beads: List[VulnerabilityBead]) -> int:
        """Assign multiple beads to this inbox.

        Args:
            beads: List of beads to assign

        Returns:
            Number of beads successfully assigned

        Usage:
            count = inbox.assign_many(beads)
            print(f"Assigned {count}/{len(beads)} beads")
        """
        assigned = 0
        for bead in beads:
            if self.assign(bead):
                assigned += 1
        return assigned

    def claim_work(self) -> Optional[WorkClaim]:
        """Claim next available work item.

        Removes the highest priority bead from the queue and creates
        a WorkClaim for tracking. The bead is moved to in_progress.

        Returns:
            WorkClaim if work available, None if queue empty

        Usage:
            claim = inbox.claim_work()
            if claim:
                try:
                    result = process(claim.bead)
                    inbox.complete_work(claim.bead.id)
                except Exception as e:
                    inbox.fail_work(claim.bead.id)
        """
        bead = self._queue.pop()
        if bead is None:
            return None

        # Create claim with attempt count
        attempt = self._failure_counts.get(bead.id, 0) + 1
        claim = WorkClaim(
            bead=bead,
            agent_role=self.agent_role,
            claimed_at=datetime.now(),
            attempt=attempt,
        )
        self._in_progress[bead.id] = claim
        return claim

    def complete_work(self, bead_id: str) -> bool:
        """Mark work as completed successfully.

        Removes the bead from in_progress and clears failure count.

        Args:
            bead_id: ID of completed bead

        Returns:
            True if bead was in progress, False otherwise

        Usage:
            if inbox.complete_work(bead.id):
                print("Work completed")
        """
        if bead_id not in self._in_progress:
            return False

        del self._in_progress[bead_id]
        if bead_id in self._failure_counts:
            del self._failure_counts[bead_id]

        # Track in completed history
        self._completed.append(bead_id)
        return True

    def fail_work(self, bead_id: str, error: Optional[str] = None) -> bool:
        """Mark work as failed.

        Increments failure count. If requeue_on_failure is enabled and
        max_retries not exceeded, the bead is requeued. Otherwise, or
        if escalate_threshold is reached, returns True to indicate
        escalation is needed.

        Args:
            bead_id: ID of failed bead
            error: Optional error message

        Returns:
            True if should escalate to supervisor, False otherwise

        Usage:
            should_escalate = inbox.fail_work(bead.id, str(e))
            if should_escalate:
                escalate_to_supervisor(bead)
        """
        claim = self._in_progress.pop(bead_id, None)
        if claim is None:
            return False

        # Increment failure count
        self._failure_counts[bead_id] = self._failure_counts.get(bead_id, 0) + 1
        failure_count = self._failure_counts[bead_id]

        # Store error in bead notes if provided
        if error:
            claim.bead.add_note(f"[failure:{failure_count}] {error}")

        # Check if should escalate
        if failure_count >= self.config.escalate_threshold:
            return True  # Should escalate to supervisor

        # Check if should requeue
        if self.config.requeue_on_failure and failure_count < self.config.max_retries:
            self._queue.push(claim.bead)

        return False

    def release_work(self, bead_id: str) -> bool:
        """Release work back to queue without marking as failure.

        Useful for graceful shutdown or rebalancing work.

        Args:
            bead_id: ID of bead to release

        Returns:
            True if released, False if not in progress

        Usage:
            inbox.release_work(bead.id)  # Put back in queue
        """
        claim = self._in_progress.pop(bead_id, None)
        if claim is None:
            return False

        self._queue.push(claim.bead)
        return True

    def release_all(self) -> int:
        """Release all in-progress work back to queue.

        Useful for graceful shutdown.

        Returns:
            Number of beads released

        Usage:
            count = inbox.release_all()
            print(f"Released {count} beads")
        """
        count = 0
        for bead_id in list(self._in_progress.keys()):
            if self.release_work(bead_id):
                count += 1
        return count

    def get_claim(self, bead_id: str) -> Optional[WorkClaim]:
        """Get the claim for a bead in progress.

        Args:
            bead_id: ID of bead

        Returns:
            WorkClaim if in progress, None otherwise
        """
        return self._in_progress.get(bead_id)

    def get_timed_out_claims(self) -> List[WorkClaim]:
        """Get claims that have exceeded timeout.

        Returns:
            List of timed out WorkClaims

        Usage:
            for claim in inbox.get_timed_out_claims():
                inbox.fail_work(claim.bead.id, "Timeout")
        """
        timeout = self.config.timeout_seconds
        now = datetime.now()
        return [
            claim
            for claim in self._in_progress.values()
            if (now - claim.claimed_at).total_seconds() > timeout
        ]

    @property
    def pending_count(self) -> int:
        """Get number of beads waiting in queue."""
        return len(self._queue)

    @property
    def in_progress_count(self) -> int:
        """Get number of beads currently being processed."""
        return len(self._in_progress)

    @property
    def completed_count(self) -> int:
        """Get number of beads completed."""
        return len(self._completed)

    @property
    def total_count(self) -> int:
        """Get total beads (pending + in progress)."""
        return self.pending_count + self.in_progress_count

    @property
    def is_empty(self) -> bool:
        """Check if inbox has no work (pending or in progress)."""
        return self.pending_count == 0 and self.in_progress_count == 0

    @property
    def has_work(self) -> bool:
        """Check if inbox has pending work."""
        return self.pending_count > 0

    def get_failure_count(self, bead_id: str) -> int:
        """Get failure count for a bead.

        Args:
            bead_id: ID of bead

        Returns:
            Number of failures, 0 if none
        """
        return self._failure_counts.get(bead_id, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize inbox state for persistence.

        Note: Bead objects are serialized by ID only. Full bead
        reconstruction requires a bead loader.

        Returns:
            Dictionary with inbox state

        Usage:
            state = inbox.to_dict()
            save_to_yaml(state)
        """
        return {
            "agent_role": self.agent_role,
            "config": self.config.to_dict(),
            "pending_bead_ids": list(self._queue._bead_ids),
            "in_progress": {
                bid: claim.to_dict()
                for bid, claim in self._in_progress.items()
            },
            "failure_counts": self._failure_counts.copy(),
            "completed": self._completed.copy(),
        }


# Export all public types
__all__ = [
    "InboxConfig",
    "WorkClaim",
    "AgentInbox",
]
