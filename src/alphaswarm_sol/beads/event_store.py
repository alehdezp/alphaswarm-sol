"""Append-only event log for bead state tracking.

This module provides event-sourced bead state tracking, enabling deterministic
replay of bead history for audits, recovery, and debugging.

Design Principles:
1. Append-only: Events are never modified or deleted
2. Deterministic: Replay produces identical state
3. Git-friendly: JSONL format for easy diffing
4. Pool-aware: Optional pool-specific event logs

Event Types:
- bead_created: New bead saved to storage
- bead_updated: Existing bead modified
- bead_deleted: Bead removed from storage
- work_state_updated: Agent work state persisted
- pool_assigned: Bead assigned to a pool

Usage:
    from alphaswarm_sol.beads.event_store import BeadEventStore, BeadEvent

    # Create store
    store = BeadEventStore(Path(".vrs/beads"))

    # Append events
    store.append_event(BeadEvent(
        bead_id="VKG-001",
        event_type="bead_created",
        payload=bead.to_dict(),
        actor="system",
    ))

    # List all events
    events = store.list_events()

    # Replay to reconstruct state
    beads = store.replay()  # dict[bead_id, VulnerabilityBead]
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BeadEvent:
    """A single bead mutation event.

    Attributes:
        event_id: Unique event identifier (computed from content hash)
        bead_id: The bead this event affects
        event_type: Type of mutation (bead_created, bead_updated, etc.)
        payload: Event data (bead dict for creates/updates, empty for deletes)
        payload_hash: SHA-256 hash of payload for integrity verification
        timestamp: When the event occurred (ISO format)
        actor: Who/what caused the event (agent ID, "system", etc.)
        pool_id: Optional pool association
    """

    bead_id: str
    event_type: str
    payload: Dict[str, Any]
    actor: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    pool_id: Optional[str] = None
    event_id: str = ""
    payload_hash: str = ""

    def __post_init__(self) -> None:
        """Compute payload_hash and event_id if not provided."""
        if not self.payload_hash:
            self.payload_hash = self._compute_payload_hash()
        if not self.event_id:
            self.event_id = self._compute_event_id()

    def _compute_payload_hash(self) -> str:
        """Compute SHA-256 hash of payload."""
        payload_json = json.dumps(self.payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload_json.encode()).hexdigest()[:32]

    def _compute_event_id(self) -> str:
        """Compute deterministic event ID from content."""
        # Stable hash of bead_id + event_type + payload_hash + timestamp
        content = f"{self.bead_id}:{self.event_type}:{self.payload_hash}:{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "event_id": self.event_id,
            "bead_id": self.bead_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "pool_id": self.pool_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeadEvent":
        """Deserialize event from dictionary."""
        return cls(
            event_id=data.get("event_id", ""),
            bead_id=data["bead_id"],
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            payload_hash=data.get("payload_hash", ""),
            timestamp=data.get("timestamp", ""),
            actor=data.get("actor", "unknown"),
            pool_id=data.get("pool_id"),
        )

    def to_jsonl(self) -> str:
        """Serialize event to JSONL line (no trailing newline)."""
        return json.dumps(self.to_dict(), separators=(",", ":"))


class BeadEventStore:
    """Append-only event log for bead mutations.

    Stores events as JSONL files for git-friendly append-only behavior.
    Supports deterministic replay to reconstruct bead state.

    Default paths:
    - Global: {root}/events.jsonl
    - Pool-specific: .vrs/pools/{pool_id}/events/beads.jsonl

    Example:
        store = BeadEventStore(Path(".vrs/beads"))

        # Append event
        store.append_event(BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload=bead.to_dict(),
            actor="system",
        ))

        # Replay all events
        beads = store.replay()
    """

    def __init__(self, root: Path, pool_id: Optional[str] = None):
        """Initialize event store.

        Args:
            root: Root directory for event logs (e.g., .vrs/beads)
            pool_id: Optional pool ID for pool-specific event log
        """
        self.root = Path(root)
        self.pool_id = pool_id

        # Determine event log path
        if pool_id:
            # Pool-specific: .vrs/pools/{pool_id}/events/beads.jsonl
            vrs_root = self.root.parent  # .vrs
            self.events_path = vrs_root / "pools" / pool_id / "events" / "beads.jsonl"
        else:
            # Global: {root}/events.jsonl
            self.events_path = self.root / "events.jsonl"

        # Ensure parent directory exists
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: BeadEvent) -> BeadEvent:
        """Append an event to the log.

        Args:
            event: BeadEvent to append

        Returns:
            The event with computed event_id and payload_hash
        """
        # Ensure event has computed fields
        if not event.event_id:
            event = BeadEvent(
                bead_id=event.bead_id,
                event_type=event.event_type,
                payload=event.payload,
                actor=event.actor,
                timestamp=event.timestamp,
                pool_id=event.pool_id,
            )

        # Append to JSONL file
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(event.to_jsonl() + "\n")

        return event

    def list_events(
        self,
        bead_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[BeadEvent]:
        """List events from the log.

        Args:
            bead_id: Optional filter by bead ID
            event_type: Optional filter by event type

        Returns:
            List of BeadEvent objects, ordered by timestamp
        """
        if not self.events_path.exists():
            return []

        events: List[BeadEvent] = []

        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = BeadEvent.from_dict(data)

                    # Apply filters
                    if bead_id and event.bead_id != bead_id:
                        continue
                    if event_type and event.event_type != event_type:
                        continue

                    events.append(event)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

        # Sort by timestamp, then event_id for determinism
        events.sort(key=lambda e: (e.timestamp, e.event_id))
        return events

    def replay(
        self,
        bead_id: Optional[str] = None,
    ) -> Dict[str, "VulnerabilityBead"]:
        """Replay events to reconstruct bead state.

        Args:
            bead_id: Optional filter to replay only a specific bead

        Returns:
            Dictionary mapping bead_id to reconstructed VulnerabilityBead
        """
        # Import here to avoid circular dependency
        from alphaswarm_sol.beads.schema import VulnerabilityBead

        beads: Dict[str, VulnerabilityBead] = {}
        events = self.list_events(bead_id=bead_id)

        for event in events:
            bid = event.bead_id

            if event.event_type in ("bead_created", "bead_updated", "pool_assigned"):
                # Create or update bead from payload
                if event.payload:
                    try:
                        beads[bid] = VulnerabilityBead.from_dict(event.payload)
                    except (KeyError, ValueError):
                        # Skip malformed payloads
                        continue

            elif event.event_type == "work_state_updated":
                # Update work state on existing bead
                if bid in beads:
                    work_state = event.payload.get("work_state")
                    last_agent = event.payload.get("last_agent")
                    if work_state is not None:
                        beads[bid].work_state = work_state
                    if last_agent:
                        beads[bid].last_agent = last_agent
                    beads[bid].last_updated = datetime.fromisoformat(
                        event.timestamp.rstrip("Z")
                    )

            elif event.event_type == "bead_deleted":
                # Remove bead from state
                if bid in beads:
                    del beads[bid]

        return beads

    def count_events(self) -> int:
        """Count total events in the log.

        Returns:
            Number of events
        """
        if not self.events_path.exists():
            return 0

        count = 0
        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def get_event_by_id(self, event_id: str) -> Optional[BeadEvent]:
        """Get a specific event by ID.

        Args:
            event_id: Event identifier

        Returns:
            BeadEvent if found, None otherwise
        """
        for event in self.list_events():
            if event.event_id == event_id:
                return event
        return None

    def clear(self) -> int:
        """Clear all events (for testing only).

        Returns:
            Number of events cleared
        """
        count = self.count_events()
        if self.events_path.exists():
            self.events_path.unlink()
        return count


# Helper function to create pool-specific event store
def get_pool_event_store(vrs_root: Path, pool_id: str) -> BeadEventStore:
    """Get event store for a specific pool.

    Args:
        vrs_root: Root .vrs directory
        pool_id: Pool identifier

    Returns:
        BeadEventStore configured for the pool
    """
    return BeadEventStore(vrs_root / "beads", pool_id=pool_id)


__all__ = [
    "BeadEvent",
    "BeadEventStore",
    "get_pool_event_store",
]
