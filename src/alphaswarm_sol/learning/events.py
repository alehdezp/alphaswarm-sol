"""Learning event storage and management.

Task 7.3: Persistent storage for learning events that enables:
- Recording verdict feedback
- Querying events by pattern, time, or similarity
- Computing aggregate statistics for patterns
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, List, Optional

from alphaswarm_sol.learning.types import (
    EventType,
    LearningEvent,
    SimilarityKey,
    SimilarityTier,
)
from alphaswarm_sol.learning.decay import DecayCalculator, DecayConfig


@dataclass
class EventContext:
    """Additional context for a learning event.

    Captures code-level details that enable similarity matching
    and debugging of learning decisions.
    """

    function_signature: str  # e.g., "withdraw(uint256)"
    function_name: str  # e.g., "withdraw"
    contract_name: str  # e.g., "Vault"
    modifiers: List[str]  # e.g., ["nonReentrant", "onlyOwner"]
    code_snippet: str  # Relevant code for context
    context_hash: str = ""  # Hash of surrounding code context
    file_path: str = ""  # Source file path

    def __post_init__(self) -> None:
        """Compute context hash if not provided."""
        if not self.context_hash:
            content = f"{self.function_signature}|{self.code_snippet}"
            self.context_hash = hashlib.md5(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "function_signature": self.function_signature,
            "function_name": self.function_name,
            "contract_name": self.contract_name,
            "modifiers": self.modifiers,
            "code_snippet": self.code_snippet,
            "context_hash": self.context_hash,
            "file_path": self.file_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventContext":
        """Create from dict."""
        return cls(
            function_signature=data.get("function_signature", ""),
            function_name=data.get("function_name", ""),
            contract_name=data.get("contract_name", ""),
            modifiers=data.get("modifiers", []),
            code_snippet=data.get("code_snippet", ""),
            context_hash=data.get("context_hash", ""),
            file_path=data.get("file_path", ""),
        )


@dataclass
class EnrichedEvent:
    """Learning event with additional context.

    Combines the core LearningEvent with EventContext for
    full traceability and debugging.
    """

    event: LearningEvent
    context: EventContext
    reason: str  # Why this verdict was made
    auditor_id: Optional[str] = None  # Who made the decision
    bead_id: Optional[str] = None  # Associated bead if any
    adjustment: float = 0.0  # Confidence adjustment applied

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "event": self.event.to_dict(),
            "context": self.context.to_dict(),
            "reason": self.reason,
            "auditor_id": self.auditor_id,
            "bead_id": self.bead_id,
            "adjustment": round(self.adjustment, 6),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnrichedEvent":
        """Create from dict."""
        return cls(
            event=LearningEvent.from_dict(data["event"]),
            context=EventContext.from_dict(data.get("context", {})),
            reason=data.get("reason", ""),
            auditor_id=data.get("auditor_id"),
            bead_id=data.get("bead_id"),
            adjustment=data.get("adjustment", 0.0),
        )


def generate_event_id(pattern_id: str) -> str:
    """Generate a unique event ID.

    Format: evt-{pattern_prefix}-{timestamp}-{random}
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:6]
    prefix = pattern_id[:8] if pattern_id else "unknown"
    return f"evt-{prefix}-{timestamp}-{random_suffix}"


def default_adjustment(event_type: EventType) -> float:
    """Get default confidence adjustment for an event type.

    From R7.2 research:
    - Confirmed (TP): +0.02 (small positive, conservative)
    - Rejected (FP): -0.05 (larger negative, penalize FPs more)
    - Escalated: 0.0 (no change until resolved)
    - Rollback: 0.0 (handled separately)
    """
    adjustments = {
        EventType.CONFIRMED: 0.02,
        EventType.REJECTED: -0.05,
        EventType.ESCALATED: 0.0,
        EventType.ROLLBACK: 0.0,
    }
    return adjustments.get(event_type, 0.0)


class EventStore:
    """Persistent storage for learning events.

    Uses JSONL (JSON Lines) format for append-only storage.
    Supports querying by pattern, time range, and similarity.
    """

    def __init__(
        self,
        storage_path: Path,
        decay_config: Optional[DecayConfig] = None,
    ):
        """Initialize event store.

        Args:
            storage_path: Directory for event storage
            decay_config: Configuration for time decay calculations
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._events_file = self.storage_path / "events.jsonl"
        self._index_file = self.storage_path / "index.json"
        self._decay_calc = DecayCalculator(decay_config)

        # In-memory index for fast lookups
        self._pattern_index: dict[str, List[str]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load or build the pattern index."""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r") as f:
                    self._pattern_index = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._rebuild_index()
        else:
            self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the pattern index from events file."""
        self._pattern_index = {}
        for enriched in self._iter_all_events():
            pattern_id = enriched.event.pattern_id
            if pattern_id not in self._pattern_index:
                self._pattern_index[pattern_id] = []
            self._pattern_index[pattern_id].append(enriched.event.id)
        self._save_index()

    def _save_index(self) -> None:
        """Save the pattern index."""
        with open(self._index_file, "w") as f:
            json.dump(self._pattern_index, f)

    def _iter_all_events(self) -> Iterator[EnrichedEvent]:
        """Iterate over all events in storage."""
        if not self._events_file.exists():
            return

        with open(self._events_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    yield EnrichedEvent.from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    continue

    def record(self, enriched: EnrichedEvent) -> str:
        """Record a new learning event.

        Args:
            enriched: The enriched event to record

        Returns:
            The event ID
        """
        # Ensure event ID is set
        if not enriched.event.id:
            enriched.event.id = generate_event_id(enriched.event.pattern_id)

        # Append to events file
        with open(self._events_file, "a") as f:
            f.write(json.dumps(enriched.to_dict()) + "\n")

        # Update index
        pattern_id = enriched.event.pattern_id
        if pattern_id not in self._pattern_index:
            self._pattern_index[pattern_id] = []
        self._pattern_index[pattern_id].append(enriched.event.id)
        self._save_index()

        return enriched.event.id

    def create_and_record(
        self,
        event_type: EventType,
        pattern_id: str,
        finding_id: str,
        similarity_key: SimilarityKey,
        context: EventContext,
        reason: str,
        confidence_before: float,
        confidence_after: float,
        verdict_source: str = "llm",
        auditor_id: Optional[str] = None,
        bead_id: Optional[str] = None,
    ) -> str:
        """Create and record a new event (convenience method).

        Args:
            event_type: Type of event
            pattern_id: Pattern that triggered the finding
            finding_id: ID of the finding
            similarity_key: Key for similarity matching
            context: Additional context
            reason: Why this verdict was made
            confidence_before: Confidence before this event
            confidence_after: Confidence after this event
            verdict_source: Source of the verdict (llm/human/test)
            auditor_id: Who made the decision
            bead_id: Associated bead if any

        Returns:
            The event ID
        """
        event_id = generate_event_id(pattern_id)
        event = LearningEvent(
            id=event_id,
            pattern_id=pattern_id,
            event_type=event_type,
            timestamp=datetime.now(),
            similarity_key=similarity_key,
            finding_id=finding_id,
            verdict_source=verdict_source,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
        )

        adjustment = confidence_after - confidence_before
        enriched = EnrichedEvent(
            event=event,
            context=context,
            reason=reason,
            auditor_id=auditor_id,
            bead_id=bead_id,
            adjustment=adjustment,
        )

        return self.record(enriched)

    def get_events_for_pattern(
        self,
        pattern_id: str,
        max_age_days: Optional[int] = None,
    ) -> List[EnrichedEvent]:
        """Get all events for a pattern.

        Args:
            pattern_id: Pattern to query
            max_age_days: Optional max age filter

        Returns:
            List of enriched events
        """
        events = []
        cutoff = None
        if max_age_days:
            cutoff = datetime.now() - timedelta(days=max_age_days)

        for enriched in self._iter_all_events():
            if enriched.event.pattern_id != pattern_id:
                continue
            if cutoff and enriched.event.timestamp < cutoff:
                continue
            events.append(enriched)

        return events

    def get_recent_events(self, days: int = 30) -> List[EnrichedEvent]:
        """Get events from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of recent enriched events
        """
        cutoff = datetime.now() - timedelta(days=days)
        events = []

        for enriched in self._iter_all_events():
            if enriched.event.timestamp >= cutoff:
                events.append(enriched)

        return events

    def get_similar_events(
        self,
        similarity_key: SimilarityKey,
        tier: SimilarityTier = SimilarityTier.STRUCTURAL,
        max_age_days: int = 180,
    ) -> List[EnrichedEvent]:
        """Get events with similar findings.

        Args:
            similarity_key: Key to match against
            tier: Similarity tier for matching
            max_age_days: Maximum age of events to consider

        Returns:
            List of similar enriched events
        """
        events = []
        cutoff = datetime.now() - timedelta(days=max_age_days)

        for enriched in self._iter_all_events():
            if enriched.event.timestamp < cutoff:
                continue
            if enriched.event.similarity_key.matches(similarity_key, tier):
                events.append(enriched)

        return events

    def count_by_type(self, pattern_id: str) -> dict[str, int]:
        """Count events by type for a pattern.

        Args:
            pattern_id: Pattern to query

        Returns:
            Dict mapping event type to count
        """
        counts = {t.value: 0 for t in EventType}

        for enriched in self._iter_all_events():
            if enriched.event.pattern_id == pattern_id:
                counts[enriched.event.event_type.value] += 1

        return counts

    def compute_effective_counts(
        self,
        pattern_id: str,
        now: Optional[datetime] = None,
    ) -> dict[str, float]:
        """Compute decay-weighted event counts for a pattern.

        Args:
            pattern_id: Pattern to query
            now: Reference time for decay calculation

        Returns:
            Dict with effective_confirmed, effective_rejected, etc.
        """
        now = now or datetime.now()
        counts = {
            "effective_confirmed": 0.0,
            "effective_rejected": 0.0,
            "effective_escalated": 0.0,
            "total_events": 0,
        }

        for enriched in self._iter_all_events():
            if enriched.event.pattern_id != pattern_id:
                continue

            counts["total_events"] += 1
            weight = self._decay_calc.calculate_factor(
                enriched.event.timestamp, now
            )

            if enriched.event.event_type == EventType.CONFIRMED:
                counts["effective_confirmed"] += weight
            elif enriched.event.event_type == EventType.REJECTED:
                counts["effective_rejected"] += weight
            elif enriched.event.event_type == EventType.ESCALATED:
                counts["effective_escalated"] += weight

        return counts

    def get_patterns_with_events(self) -> List[str]:
        """Get list of patterns that have recorded events.

        Returns:
            List of pattern IDs
        """
        return list(self._pattern_index.keys())

    def clear_pattern_events(self, pattern_id: str) -> int:
        """Clear all events for a pattern (for testing/rollback).

        Args:
            pattern_id: Pattern to clear

        Returns:
            Number of events cleared
        """
        events_to_keep = []
        cleared = 0

        for enriched in self._iter_all_events():
            if enriched.event.pattern_id == pattern_id:
                cleared += 1
            else:
                events_to_keep.append(enriched)

        # Rewrite events file
        with open(self._events_file, "w") as f:
            for enriched in events_to_keep:
                f.write(json.dumps(enriched.to_dict()) + "\n")

        # Update index
        if pattern_id in self._pattern_index:
            del self._pattern_index[pattern_id]
            self._save_index()

        return cleared

    def get_event_count(self) -> int:
        """Get total number of events in storage.

        Returns:
            Total event count
        """
        count = 0
        for _ in self._iter_all_events():
            count += 1
        return count


# Factory function for creating events from findings
def create_event_from_finding(
    finding: dict[str, Any],
    event_type: EventType,
    reason: str,
    confidence_before: float,
    confidence_after: float,
    verdict_source: str = "llm",
) -> EnrichedEvent:
    """Create an EnrichedEvent from a finding dict.

    Args:
        finding: Finding dict with pattern_id, function info, etc.
        event_type: Type of verdict
        reason: Why this verdict was made
        confidence_before: Confidence before
        confidence_after: Confidence after
        verdict_source: Source of verdict

    Returns:
        EnrichedEvent ready to record
    """
    pattern_id = finding.get("pattern_id", "unknown")
    finding_id = finding.get("finding_id", finding.get("id", "unknown"))

    # Create similarity key
    similarity_key = SimilarityKey.from_finding(finding)

    # Create context
    context = EventContext(
        function_signature=finding.get("function_signature", ""),
        function_name=finding.get("function_name", ""),
        contract_name=finding.get("contract_name", ""),
        modifiers=finding.get("modifiers", []),
        code_snippet=finding.get("code", finding.get("code_snippet", "")),
        file_path=finding.get("file_path", ""),
    )

    # Create event
    event_id = generate_event_id(pattern_id)
    event = LearningEvent(
        id=event_id,
        pattern_id=pattern_id,
        event_type=event_type,
        timestamp=datetime.now(),
        similarity_key=similarity_key,
        finding_id=finding_id,
        verdict_source=verdict_source,
        confidence_before=confidence_before,
        confidence_after=confidence_after,
    )

    adjustment = confidence_after - confidence_before
    return EnrichedEvent(
        event=event,
        context=context,
        reason=reason,
        adjustment=adjustment,
    )
