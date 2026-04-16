"""Learning overlay storage for minimal, label-based knowledge."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Optional

from alphaswarm_sol.learning.decay import DecayCalculator, DecayConfig
from alphaswarm_sol.learning.labels import (
    is_valid_label,
    label_relevant_to_category,
    normalize_category,
)


class AssertionKind(Enum):
    """Type of learning assertion."""

    LABEL = "label"
    EDGE = "edge"


@dataclass
class LearningAssertion:
    """A minimal learning assertion (label or edge)."""

    assertion_id: str
    kind: AssertionKind
    label: str
    node_id: str = ""
    source_id: str = ""
    target_id: str = ""
    scope: str = "project"
    pattern_id: str = ""
    bead_id: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            "assertion_id": self.assertion_id,
            "kind": self.kind.value,
            "label": self.label,
            "node_id": self.node_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "scope": self.scope,
            "pattern_id": self.pattern_id,
            "bead_id": self.bead_id,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearningAssertion":
        """Create from dict."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        return cls(
            assertion_id=data.get("assertion_id", ""),
            kind=AssertionKind(data.get("kind", "label")),
            label=data.get("label", ""),
            node_id=data.get("node_id", ""),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            scope=data.get("scope", "project"),
            pattern_id=data.get("pattern_id", ""),
            bead_id=data.get("bead_id", ""),
            evidence=list(data.get("evidence", [])),
            confidence=float(data.get("confidence", 0.0)),
            created_at=created_at,
        )


def make_assertion_id(
    kind: AssertionKind,
    label: str,
    node_id: str = "",
    source_id: str = "",
    target_id: str = "",
    pattern_id: str = "",
    bead_id: str = "",
) -> str:
    """Create deterministic assertion IDs for deduplication."""
    payload = "|".join(
        [
            kind.value,
            label,
            node_id,
            source_id,
            target_id,
            pattern_id,
            bead_id,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class LearningOverlayStore:
    """Persistent store for minimal learning overlays."""

    def __init__(
        self,
        storage_path: Path,
        decay_config: Optional[DecayConfig] = None,
        min_confidence: float = 0.8,
    ):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._overlay_file = self.storage_path / "overlay.jsonl"
        self._decay = DecayCalculator(decay_config)
        self._min_confidence = min_confidence
        self._index: set[str] = set()
        self._load_index()

    def _load_index(self) -> None:
        """Load assertion IDs for deduplication."""
        self._index = set()
        if not self._overlay_file.exists():
            return
        with open(self._overlay_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    assertion_id = data.get("assertion_id", "")
                    if assertion_id:
                        self._index.add(assertion_id)
                except json.JSONDecodeError:
                    continue

    def record_label(
        self,
        node_id: str,
        label: str,
        pattern_id: str,
        bead_id: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
        scope: str = "project",
    ) -> bool:
        """Record a label assertion."""
        assertion_id = make_assertion_id(
            AssertionKind.LABEL,
            label,
            node_id=node_id,
            pattern_id=pattern_id,
            bead_id=bead_id,
        )
        assertion = LearningAssertion(
            assertion_id=assertion_id,
            kind=AssertionKind.LABEL,
            label=label,
            node_id=node_id,
            scope=scope,
            pattern_id=pattern_id,
            bead_id=bead_id,
            evidence=evidence or [],
            confidence=confidence,
        )
        return self.record_assertion(assertion)

    def record_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        pattern_id: str,
        bead_id: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.0,
        scope: str = "project",
    ) -> bool:
        """Record an edge assertion."""
        assertion_id = make_assertion_id(
            AssertionKind.EDGE,
            relation,
            source_id=source_id,
            target_id=target_id,
            pattern_id=pattern_id,
            bead_id=bead_id,
        )
        assertion = LearningAssertion(
            assertion_id=assertion_id,
            kind=AssertionKind.EDGE,
            label=relation,
            source_id=source_id,
            target_id=target_id,
            scope=scope,
            pattern_id=pattern_id,
            bead_id=bead_id,
            evidence=evidence or [],
            confidence=confidence,
        )
        return self.record_assertion(assertion)

    def record_assertion(self, assertion: LearningAssertion) -> bool:
        """Record a learning assertion if valid and not duplicate."""
        if not is_valid_label(assertion.label):
            return False
        if assertion.confidence < self._min_confidence:
            return False
        if assertion.assertion_id in self._index:
            return False

        with open(self._overlay_file, "a") as f:
            f.write(json.dumps(assertion.to_dict()) + "\n")
        self._index.add(assertion.assertion_id)
        return True

    def iter_assertions(self) -> Iterable[LearningAssertion]:
        """Iterate over stored assertions."""
        if not self._overlay_file.exists():
            return []
        assertions = []
        with open(self._overlay_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    assertion = LearningAssertion.from_dict(data)
                    assertions.append(assertion)
                except (json.JSONDecodeError, ValueError):
                    continue
        return assertions

    def get_labels(
        self,
        node_id: str,
        category: Optional[str] = None,
        max_items: int = 5,
    ) -> List[LearningAssertion]:
        """Get label assertions for a node."""
        normalized = normalize_category(category)
        matches = []
        for assertion in self.iter_assertions():
            if assertion.kind != AssertionKind.LABEL:
                continue
            if assertion.node_id != node_id:
                continue
            if not label_relevant_to_category(assertion.label, normalized):
                continue
            if not self._is_relevant(assertion):
                continue
            matches.append(assertion)

        matches.sort(key=lambda a: (a.confidence, a.created_at), reverse=True)
        return matches[:max_items]

    def get_edges(
        self,
        node_id: str,
        category: Optional[str] = None,
        max_items: int = 5,
        direction: str = "any",
    ) -> List[LearningAssertion]:
        """Get edge assertions for a node."""
        normalized = normalize_category(category)
        matches = []
        for assertion in self.iter_assertions():
            if assertion.kind != AssertionKind.EDGE:
                continue
            if direction == "out" and assertion.source_id != node_id:
                continue
            if direction == "in" and assertion.target_id != node_id:
                continue
            if direction == "any" and node_id not in (assertion.source_id, assertion.target_id):
                continue
            if not label_relevant_to_category(assertion.label, normalized):
                continue
            if not self._is_relevant(assertion):
                continue
            matches.append(assertion)

        matches.sort(key=lambda a: (a.confidence, a.created_at), reverse=True)
        return matches[:max_items]

    def stats(self) -> dict:
        """Return overlay statistics."""
        total = 0
        labels = 0
        edges = 0
        for assertion in self.iter_assertions():
            total += 1
            if assertion.kind == AssertionKind.LABEL:
                labels += 1
            elif assertion.kind == AssertionKind.EDGE:
                edges += 1
        return {
            "total": total,
            "labels": labels,
            "edges": edges,
            "path": str(self._overlay_file),
        }

    def _is_relevant(self, assertion: LearningAssertion) -> bool:
        """Check if an assertion is still relevant after decay."""
        return self._decay.is_relevant(assertion.created_at)


def format_overlay_context(
    labels: List[LearningAssertion],
    edges: List[LearningAssertion],
    fp_warnings: Optional[List[str]] = None,
) -> str:
    """Format overlay knowledge into a compact prompt section."""
    sections: List[str] = []

    if labels:
        lines = ["## Learned Labels (Project Memory)"]
        for item in labels:
            lines.append(
                f"- {item.label}: {item.node_id} (confidence {item.confidence:.2f})"
            )
        sections.append("\n".join(lines))

    if edges:
        lines = ["## Learned Relationships (Project Memory)"]
        for item in edges:
            lines.append(
                f"- {item.label}: {item.source_id} -> {item.target_id} "
                f"(confidence {item.confidence:.2f})"
            )
        sections.append("\n".join(lines))

    if fp_warnings:
        lines = ["## False Positive Warnings"]
        for warning in fp_warnings:
            lines.append(f"- {warning}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
