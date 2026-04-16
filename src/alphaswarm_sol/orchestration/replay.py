"""Deterministic replay engine for orchestration runs.

This module provides the ReplayEngine for reconstructing pool state from event logs,
enabling reproducible audits, regression testing, and state verification.

Design Principles:
1. Event log is source of truth - pool state derived from events
2. Deterministic ordering - events sorted by timestamp + event_id
3. Explicit randomness - seed parameter for any nondeterministic operations
4. Strict validation - optionally compare replayed state vs current snapshot

Usage:
    from alphaswarm_sol.orchestration.replay import ReplayEngine, ReplayResult

    engine = ReplayEngine()

    # Basic replay
    result = engine.replay("pool-001")
    print(f"Reconstructed pool with {result.bead_count} beads")

    # Strict mode - validate against current snapshot
    result = engine.replay("pool-001", strict=True)
    if result.mismatches:
        print(f"Found {len(result.mismatches)} mismatches")

    # With explicit seed for determinism
    result = engine.replay("pool-001", seed=42)

Phase: 07.1.1-04 - Deterministic Replay
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from alphaswarm_sol.beads.event_store import BeadEvent, BeadEventStore, get_pool_event_store
from alphaswarm_sol.orchestration.pool import PoolManager, PoolStorage
from alphaswarm_sol.orchestration.schemas import (
    Pool,
    PoolStatus,
    Scope,
    Verdict,
    VerdictConfidence,
    EvidencePacket,
)


@dataclass
class PoolEvent:
    """A single pool-level event (status change, bead assignment, verdict).

    Attributes:
        event_id: Unique event identifier (computed from content hash)
        pool_id: The pool this event affects
        event_type: Type of event (pool_created, status_changed, bead_added, etc.)
        payload: Event data
        payload_hash: SHA-256 hash of payload for integrity
        timestamp: When the event occurred (ISO format)
        actor: Who/what caused the event
    """

    pool_id: str
    event_type: str
    payload: Dict[str, Any]
    actor: str
    timestamp: str = ""
    event_id: str = ""
    payload_hash: str = ""

    def __post_init__(self) -> None:
        """Compute payload_hash and event_id if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
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
        content = f"{self.pool_id}:{self.event_type}:{self.payload_hash}:{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "event_id": self.event_id,
            "pool_id": self.pool_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "timestamp": self.timestamp,
            "actor": self.actor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PoolEvent":
        """Deserialize event from dictionary."""
        return cls(
            event_id=data.get("event_id", ""),
            pool_id=data["pool_id"],
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            payload_hash=data.get("payload_hash", ""),
            timestamp=data.get("timestamp", ""),
            actor=data.get("actor", "unknown"),
        )

    def to_jsonl(self) -> str:
        """Serialize event to JSONL line (no trailing newline)."""
        return json.dumps(self.to_dict(), separators=(",", ":"))


@dataclass
class StateMismatch:
    """A mismatch between replayed and current pool state.

    Attributes:
        field: The field that differs
        expected: Value from replayed state
        actual: Value from current snapshot
        message: Human-readable description
    """

    field: str
    expected: Any
    actual: Any
    message: str = ""

    def __post_init__(self) -> None:
        if not self.message:
            self.message = f"Field '{self.field}' mismatch: expected {self.expected!r}, got {self.actual!r}"


@dataclass
class ReplayResult:
    """Result of replay operation.

    Attributes:
        pool: Reconstructed Pool object (or None if replay failed)
        beads: Dictionary of bead_id -> bead state from event replay
        event_count: Number of events processed
        bead_count: Number of beads reconstructed
        verdict_count: Number of verdicts in replayed pool
        mismatches: List of mismatches (only in strict mode)
        success: Whether replay completed successfully
        error: Error message if replay failed
        seed: Random seed used for replay
    """

    pool: Optional[Pool] = None
    beads: Dict[str, Any] = field(default_factory=dict)
    event_count: int = 0
    bead_count: int = 0
    verdict_count: int = 0
    mismatches: List[StateMismatch] = field(default_factory=list)
    success: bool = True
    error: str = ""
    seed: int = 0


class PoolEventStore:
    """Append-only event log for pool-level mutations.

    Stores events as JSONL files at .vrs/pools/{pool_id}/events/pool.jsonl

    Example:
        store = PoolEventStore(Path(".vrs/pools"), "pool-001")
        store.append_event(PoolEvent(
            pool_id="pool-001",
            event_type="pool_created",
            payload=pool.to_dict(),
            actor="system",
        ))
    """

    def __init__(self, pools_root: Path, pool_id: str):
        """Initialize pool event store.

        Args:
            pools_root: Root directory for pools (e.g., .vrs/pools)
            pool_id: Pool identifier
        """
        self.pools_root = Path(pools_root)
        self.pool_id = pool_id
        self.events_path = self.pools_root / pool_id / "events" / "pool.jsonl"
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: PoolEvent) -> PoolEvent:
        """Append an event to the log.

        Args:
            event: PoolEvent to append

        Returns:
            The event with computed fields
        """
        if not event.event_id:
            event = PoolEvent(
                pool_id=event.pool_id,
                event_type=event.event_type,
                payload=event.payload,
                actor=event.actor,
                timestamp=event.timestamp,
            )

        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(event.to_jsonl() + "\n")

        return event

    def list_events(
        self,
        event_type: Optional[str] = None,
    ) -> List[PoolEvent]:
        """List events from the log.

        Args:
            event_type: Optional filter by event type

        Returns:
            List of PoolEvent objects, ordered by timestamp + event_id
        """
        if not self.events_path.exists():
            return []

        events: List[PoolEvent] = []

        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = PoolEvent.from_dict(data)

                    if event_type and event.event_type != event_type:
                        continue

                    events.append(event)
                except json.JSONDecodeError:
                    continue

        # Sort by timestamp, then event_id for determinism
        events.sort(key=lambda e: (e.timestamp, e.event_id))
        return events

    def count_events(self) -> int:
        """Count total events in the log."""
        if not self.events_path.exists():
            return 0

        count = 0
        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count


class ReplayEngine:
    """Engine for deterministic pool reconstruction from event logs.

    Reconstructs pool state by replaying events in timestamp order,
    enabling audits, regression testing, and state verification.

    Example:
        engine = ReplayEngine()

        # Basic replay
        result = engine.replay("pool-001")

        # Strict mode - validate against current snapshot
        result = engine.replay("pool-001", strict=True)

        # Custom root directory
        engine = ReplayEngine(vrs_root=Path("/custom/.vrs"))
        result = engine.replay("pool-001")
    """

    def __init__(
        self,
        vrs_root: Optional[Path] = None,
    ):
        """Initialize replay engine.

        Args:
            vrs_root: Root .vrs directory (defaults to .vrs in cwd)
        """
        self.vrs_root = Path(vrs_root) if vrs_root else Path.cwd() / ".vrs"
        self.pools_root = self.vrs_root / "pools"

    def replay(
        self,
        pool_id: str,
        strict: bool = False,
        seed: int = 0,
    ) -> ReplayResult:
        """Replay pool state from event logs.

        Args:
            pool_id: Pool identifier to replay
            strict: If True, validate replayed state against current snapshot
            seed: Random seed for deterministic replay of any nondeterministic steps

        Returns:
            ReplayResult with reconstructed pool and validation info
        """
        # Set seed for deterministic replay
        random.seed(seed)

        result = ReplayResult(seed=seed)

        try:
            # Load bead events
            bead_event_store = get_pool_event_store(self.vrs_root, pool_id)
            bead_events = bead_event_store.list_events()

            # Load pool events
            pool_event_store = PoolEventStore(self.pools_root, pool_id)
            pool_events = pool_event_store.list_events()

            # Combine and sort all events
            all_events: List[Tuple[str, Any]] = []
            for e in bead_events:
                all_events.append((e.timestamp, "bead", e))
            for e in pool_events:
                all_events.append((e.timestamp, "pool", e))

            # Sort by timestamp, then event_id for determinism
            all_events.sort(key=lambda x: (x[0], x[2].event_id))

            result.event_count = len(all_events)

            # Replay events to reconstruct state
            reconstructed_pool = self._replay_events(pool_id, all_events)

            if reconstructed_pool is None:
                # Try to load from snapshot if no events
                pool_storage = PoolStorage(self.pools_root)
                reconstructed_pool = pool_storage.get_pool(pool_id)

                if reconstructed_pool is None:
                    result.success = False
                    result.error = f"Pool {pool_id} not found and no events to replay"
                    return result

            result.pool = reconstructed_pool
            result.bead_count = len(reconstructed_pool.bead_ids)
            result.verdict_count = len(reconstructed_pool.verdicts)

            # Replay beads from bead events
            result.beads = bead_event_store.replay()

            # Strict mode: validate against current snapshot
            if strict:
                result.mismatches = self._validate_against_snapshot(pool_id, reconstructed_pool)

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _replay_events(
        self,
        pool_id: str,
        events: List[Tuple[str, str, Any]],
    ) -> Optional[Pool]:
        """Replay events to reconstruct pool state.

        Args:
            pool_id: Pool identifier
            events: List of (timestamp, event_source, event) tuples

        Returns:
            Reconstructed Pool or None if not enough events
        """
        pool: Optional[Pool] = None
        bead_ids: List[str] = []
        verdicts: Dict[str, Verdict] = {}
        status = PoolStatus.INTAKE
        scope: Optional[Scope] = None
        metadata: Dict[str, Any] = {}
        initiated_by = ""
        created_at = None
        updated_at = None
        phases_complete: List[str] = []

        for timestamp, source, event in events:
            if source == "pool":
                event_type = event.event_type
                payload = event.payload

                if event_type == "pool_created":
                    # Initialize pool from creation event
                    scope_data = payload.get("scope", {})
                    scope = Scope(
                        files=scope_data.get("files", []),
                        contracts=scope_data.get("contracts", []),
                        focus_areas=scope_data.get("focus_areas", []),
                    )
                    bead_ids = payload.get("bead_ids", [])
                    initiated_by = payload.get("initiated_by", "")
                    metadata = payload.get("metadata", {})
                    created_at = datetime.fromisoformat(
                        payload.get("created_at", timestamp).rstrip("Z")
                    )
                    status_str = payload.get("status", "intake")
                    try:
                        status = PoolStatus.from_string(status_str)
                    except ValueError:
                        status = PoolStatus.INTAKE

                elif event_type == "status_changed":
                    status_str = payload.get("status", "intake")
                    try:
                        status = PoolStatus.from_string(status_str)
                    except ValueError:
                        pass
                    if payload.get("phases_complete"):
                        phases_complete = payload["phases_complete"]

                elif event_type == "bead_added":
                    bead_id = payload.get("bead_id")
                    if bead_id and bead_id not in bead_ids:
                        bead_ids.append(bead_id)

                elif event_type == "bead_removed":
                    bead_id = payload.get("bead_id")
                    if bead_id and bead_id in bead_ids:
                        bead_ids.remove(bead_id)

                elif event_type == "verdict_recorded":
                    verdict_data = payload.get("verdict", {})
                    finding_id = verdict_data.get("finding_id")
                    if finding_id:
                        confidence_str = verdict_data.get("confidence", "uncertain")
                        try:
                            confidence = VerdictConfidence(confidence_str)
                        except ValueError:
                            confidence = VerdictConfidence.UNCERTAIN

                        evidence_data = verdict_data.get("evidence_packet")
                        evidence_packet = None
                        if evidence_data:
                            evidence_packet = EvidencePacket.from_dict(evidence_data)

                        verdict = Verdict(
                            finding_id=finding_id,
                            confidence=confidence,
                            is_vulnerable=verdict_data.get("is_vulnerable", False),
                            rationale=verdict_data.get("rationale", ""),
                            evidence_packet=evidence_packet,
                        )
                        verdicts[finding_id] = verdict

                elif event_type == "metadata_updated":
                    metadata.update(payload.get("metadata", {}))

                updated_at = datetime.fromisoformat(timestamp.rstrip("Z"))

            elif source == "bead":
                # Bead events are handled by BeadEventStore.replay()
                # But we track bead IDs for pool state
                if event.event_type == "pool_assigned":
                    bead_id = event.bead_id
                    if bead_id and bead_id not in bead_ids:
                        bead_ids.append(bead_id)

        # If we have enough state, construct the pool
        if scope is not None:
            pool = Pool(
                id=pool_id,
                scope=scope,
                bead_ids=bead_ids,
                status=status,
                initiated_by=initiated_by,
                metadata=metadata,
            )
            pool.verdicts = verdicts
            pool.phases_complete = phases_complete
            if created_at:
                pool.created_at = created_at
            if updated_at:
                pool.updated_at = updated_at

        return pool

    def _validate_against_snapshot(
        self,
        pool_id: str,
        replayed_pool: Pool,
    ) -> List[StateMismatch]:
        """Validate replayed state against current snapshot.

        Args:
            pool_id: Pool identifier
            replayed_pool: Pool reconstructed from events

        Returns:
            List of mismatches found
        """
        mismatches: List[StateMismatch] = []

        # Load current snapshot
        pool_storage = PoolStorage(self.pools_root)
        current_pool = pool_storage.get_pool(pool_id)

        if current_pool is None:
            mismatches.append(StateMismatch(
                field="pool",
                expected="exists",
                actual="not found",
                message=f"Current snapshot not found for pool {pool_id}",
            ))
            return mismatches

        # Compare key fields
        if replayed_pool.status != current_pool.status:
            mismatches.append(StateMismatch(
                field="status",
                expected=replayed_pool.status.value,
                actual=current_pool.status.value,
            ))

        if set(replayed_pool.bead_ids) != set(current_pool.bead_ids):
            mismatches.append(StateMismatch(
                field="bead_ids",
                expected=sorted(replayed_pool.bead_ids),
                actual=sorted(current_pool.bead_ids),
            ))

        if len(replayed_pool.verdicts) != len(current_pool.verdicts):
            mismatches.append(StateMismatch(
                field="verdict_count",
                expected=len(replayed_pool.verdicts),
                actual=len(current_pool.verdicts),
            ))

        # Compare verdicts by finding_id
        for finding_id, replayed_verdict in replayed_pool.verdicts.items():
            current_verdict = current_pool.verdicts.get(finding_id)
            if current_verdict is None:
                mismatches.append(StateMismatch(
                    field=f"verdict[{finding_id}]",
                    expected="exists",
                    actual="not found",
                ))
            elif replayed_verdict.is_vulnerable != current_verdict.is_vulnerable:
                mismatches.append(StateMismatch(
                    field=f"verdict[{finding_id}].is_vulnerable",
                    expected=replayed_verdict.is_vulnerable,
                    actual=current_verdict.is_vulnerable,
                ))
            elif replayed_verdict.confidence != current_verdict.confidence:
                mismatches.append(StateMismatch(
                    field=f"verdict[{finding_id}].confidence",
                    expected=replayed_verdict.confidence.value,
                    actual=current_verdict.confidence.value,
                ))

        # Check for verdicts in current but not in replayed
        for finding_id in current_pool.verdicts:
            if finding_id not in replayed_pool.verdicts:
                mismatches.append(StateMismatch(
                    field=f"verdict[{finding_id}]",
                    expected="not found",
                    actual="exists",
                    message=f"Verdict {finding_id} in snapshot but not in replay",
                ))

        return mismatches

    def get_diff_summary(self, result: ReplayResult) -> str:
        """Generate human-readable diff summary.

        Args:
            result: ReplayResult from replay operation

        Returns:
            Formatted diff summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("REPLAY DIFF SUMMARY")
        lines.append("=" * 60)

        if not result.success:
            lines.append(f"REPLAY FAILED: {result.error}")
            return "\n".join(lines)

        lines.append(f"Pool: {result.pool.id if result.pool else 'N/A'}")
        lines.append(f"Events processed: {result.event_count}")
        lines.append(f"Beads reconstructed: {result.bead_count}")
        lines.append(f"Verdicts: {result.verdict_count}")
        lines.append(f"Seed: {result.seed}")

        if result.mismatches:
            lines.append("")
            lines.append(f"MISMATCHES FOUND: {len(result.mismatches)}")
            lines.append("-" * 60)
            for mismatch in result.mismatches:
                lines.append(f"  - {mismatch.message}")
        else:
            lines.append("")
            lines.append("NO MISMATCHES - Replay matches current state")

        lines.append("=" * 60)
        return "\n".join(lines)


# Export for module
__all__ = [
    "PoolEvent",
    "PoolEventStore",
    "StateMismatch",
    "ReplayResult",
    "ReplayEngine",
]
