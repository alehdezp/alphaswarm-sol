"""Core types for the learning module.

This module defines the fundamental data structures for conservative learning:
- PatternBaseline: Historical performance metrics per pattern
- ConfidenceBounds: Min/max confidence limits to prevent runaway learning
- LearningEvent: Individual verdict events that update confidence
- SimilarityKey: Key for finding similarity matching
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Type of learning event."""

    CONFIRMED = "confirmed"  # Verdict confirmed the finding (TP)
    REJECTED = "rejected"  # Verdict rejected the finding (FP)
    ESCALATED = "escalated"  # Finding escalated to human review
    ROLLBACK = "rollback"  # Confidence rolled back to baseline


class SimilarityTier(Enum):
    """Similarity tier for finding matching.

    Tier 1 (Exact): Same pattern + modifiers + guard patterns
    Tier 2 (Structural): Same pattern + similar modifiers
    Tier 3 (Pattern): Same pattern only
    """

    EXACT = 1
    STRUCTURAL = 2
    PATTERN = 3


@dataclass
class PatternBaseline:
    """Baseline metrics for a single pattern.

    Derived from benchmark data and used as the fallback
    when learning produces bad results.
    """

    pattern_id: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    sample_size: int
    source: str = "benchmark"  # Where the baseline came from
    computed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "pattern_id": self.pattern_id,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "sample_size": self.sample_size,
            "source": self.source,
            "computed_at": self.computed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatternBaseline":
        """Create from dict."""
        computed_at = data.get("computed_at")
        if isinstance(computed_at, str):
            computed_at = datetime.fromisoformat(computed_at)
        elif computed_at is None:
            computed_at = datetime.now()

        return cls(
            pattern_id=data["pattern_id"],
            true_positives=data["true_positives"],
            false_positives=data["false_positives"],
            false_negatives=data["false_negatives"],
            precision=data["precision"],
            recall=data["recall"],
            f1_score=data["f1_score"],
            sample_size=data["sample_size"],
            source=data.get("source", "benchmark"),
            computed_at=computed_at,
        )


@dataclass
class ConfidenceBounds:
    """Confidence bounds for a pattern.

    These bounds prevent confidence from going too low (death spiral)
    or too high (overconfidence). Derived from observed precision
    with statistical margins.
    """

    pattern_id: str
    lower_bound: float  # Never go below this (minimum 0.15)
    upper_bound: float  # Never exceed this (maximum 0.98)
    initial: float  # Starting confidence
    observed_precision: float  # From baseline data
    sample_size: int = 0  # How many samples informed this
    computed_at: datetime = field(default_factory=datetime.now)

    # Absolute limits - these cannot be exceeded
    ABSOLUTE_MIN: float = 0.15
    ABSOLUTE_MAX: float = 0.98

    def __post_init__(self) -> None:
        """Enforce absolute limits."""
        self.lower_bound = max(self.ABSOLUTE_MIN, self.lower_bound)
        self.upper_bound = min(self.ABSOLUTE_MAX, self.upper_bound)
        self.initial = max(self.lower_bound, min(self.upper_bound, self.initial))

    def clamp(self, value: float) -> float:
        """Clamp a value to these bounds."""
        return max(self.lower_bound, min(self.upper_bound, value))

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "pattern_id": self.pattern_id,
            "lower_bound": round(self.lower_bound, 4),
            "upper_bound": round(self.upper_bound, 4),
            "initial": round(self.initial, 4),
            "observed_precision": round(self.observed_precision, 4),
            "sample_size": self.sample_size,
            "computed_at": self.computed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfidenceBounds":
        """Create from dict."""
        computed_at = data.get("computed_at")
        if isinstance(computed_at, str):
            computed_at = datetime.fromisoformat(computed_at)
        elif computed_at is None:
            computed_at = datetime.now()

        return cls(
            pattern_id=data["pattern_id"],
            lower_bound=data["lower_bound"],
            upper_bound=data["upper_bound"],
            initial=data["initial"],
            observed_precision=data["observed_precision"],
            sample_size=data.get("sample_size", 0),
            computed_at=computed_at,
        )

    @classmethod
    def default(cls, pattern_id: str) -> "ConfidenceBounds":
        """Create default bounds for patterns with insufficient data."""
        return cls(
            pattern_id=pattern_id,
            lower_bound=0.30,
            upper_bound=0.95,
            initial=0.70,
            observed_precision=0.70,
            sample_size=0,
        )


@dataclass
class LearningEvent:
    """A single learning event (verdict on a finding).

    Events update pattern confidence over time. They include
    similarity keys for transferring lessons to similar findings.
    """

    id: str
    pattern_id: str
    event_type: EventType
    timestamp: datetime
    similarity_key: "SimilarityKey"
    finding_id: str
    verdict_source: str = "llm"  # llm | human | test
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "id": self.id,
            "pattern_id": self.pattern_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "similarity_key": self.similarity_key.to_dict(),
            "finding_id": self.finding_id,
            "verdict_source": self.verdict_source,
            "confidence_before": round(self.confidence_before, 4),
            "confidence_after": round(self.confidence_after, 4),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningEvent":
        """Create from dict."""
        return cls(
            id=data["id"],
            pattern_id=data["pattern_id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            similarity_key=SimilarityKey.from_dict(data["similarity_key"]),
            finding_id=data["finding_id"],
            verdict_source=data.get("verdict_source", "llm"),
            confidence_before=data.get("confidence_before", 0.0),
            confidence_after=data.get("confidence_after", 0.0),
            notes=data.get("notes", ""),
        )


@dataclass
class SimilarityKey:
    """Key for finding similarity lookup.

    Used to determine if two findings are "similar" enough
    to transfer learning events between them.

    From R7.1 research:
    - Tier 1 (Exact): pattern_id + modifier_signature + guard_hash
    - Tier 2 (Structural): pattern_id + modifier_signature
    - Tier 3 (Pattern): pattern_id only
    """

    pattern_id: str
    modifier_signature: str  # Sorted, joined modifiers
    guard_hash: str  # Hash of guard-related code patterns
    inheritance_hash: str = ""  # Hash of inheritance chain

    def matches(self, other: "SimilarityKey", tier: SimilarityTier) -> bool:
        """Check if this key matches another at the given tier."""
        if tier == SimilarityTier.EXACT:
            return (
                self.pattern_id == other.pattern_id
                and self.modifier_signature == other.modifier_signature
                and self.guard_hash == other.guard_hash
            )
        if tier == SimilarityTier.STRUCTURAL:
            return (
                self.pattern_id == other.pattern_id
                and self.modifier_signature == other.modifier_signature
            )
        # Tier 3: Pattern only
        return self.pattern_id == other.pattern_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "pattern_id": self.pattern_id,
            "modifier_signature": self.modifier_signature,
            "guard_hash": self.guard_hash,
            "inheritance_hash": self.inheritance_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimilarityKey":
        """Create from dict."""
        return cls(
            pattern_id=data["pattern_id"],
            modifier_signature=data.get("modifier_signature", ""),
            guard_hash=data.get("guard_hash", ""),
            inheritance_hash=data.get("inheritance_hash", ""),
        )

    @classmethod
    def from_finding(cls, finding: dict[str, Any]) -> "SimilarityKey":
        """Create from a finding dict.

        Args:
            finding: Finding dict with pattern_id, modifiers, code, etc.
        """
        # Import here to avoid circular imports
        from alphaswarm_sol.learning.similarity import extract_guards

        pattern_id = finding.get("pattern_id", "unknown")
        modifiers = sorted(finding.get("modifiers", []))
        code = finding.get("code", "")
        inheritance = finding.get("inheritance_chain", [])

        return cls(
            pattern_id=pattern_id,
            modifier_signature="|".join(modifiers),
            guard_hash=extract_guards(code),
            inheritance_hash="|".join(sorted(inheritance)),
        )
