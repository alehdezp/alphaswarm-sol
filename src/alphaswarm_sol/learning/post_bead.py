"""Post-bead learning pipeline for minimal, evidence-based overlays."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING

from alphaswarm_sol.learning.decay import DecayConfig
from alphaswarm_sol.learning.events import EventStore, create_event_from_finding, default_adjustment
from alphaswarm_sol.learning.fp_recorder import FalsePositiveRecorder
from alphaswarm_sol.learning.labels import is_valid_label
from alphaswarm_sol.learning.overlay import LearningOverlayStore
from alphaswarm_sol.learning.similarity import extract_guards
from alphaswarm_sol.learning.types import EventType

if TYPE_CHECKING:
    from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.types import VerdictType


DEFAULT_LEARNING_DIR = Path(".vrs/learning")

LABEL_PREFIX = "LABEL:"
EDGE_PREFIX = "EDGE:"
CONTEXT_PREFIX = "CONTEXT:"


@dataclass
class LearningConfig:
    """Configuration for post-bead learning."""

    enabled: bool = False
    overlay_enabled: bool = False
    events_enabled: bool = False
    fp_enabled: bool = False
    min_confidence: float = 0.8


@dataclass
class FindingStub:
    """Minimal finding-like object for FP warnings."""

    pattern_id: str
    modifiers: List[str]
    guard_patterns: List[str]


def load_learning_config(learning_dir: Path) -> LearningConfig:
    """Load learning config from disk."""
    config_path = learning_dir / "config.json"
    if not config_path.exists():
        return LearningConfig()
    try:
        data = _load_json(config_path)
    except ValueError:
        return LearningConfig()

    enabled = bool(data.get("enabled", False))
    return LearningConfig(
        enabled=enabled,
        overlay_enabled=bool(data.get("overlay_enabled", enabled)),
        events_enabled=bool(data.get("events_enabled", enabled)),
        fp_enabled=bool(data.get("fp_enabled", enabled)),
        min_confidence=float(data.get("overlay_min_confidence", 0.8)),
    )


def build_finding_stub(bead: "VulnerabilityBead") -> FindingStub:
    """Create a minimal finding stub from a bead."""
    modifiers, _signature = _extract_modifiers_and_signature(bead)
    guard_patterns = _extract_guard_patterns(bead)
    return FindingStub(
        pattern_id=bead.pattern_id,
        modifiers=modifiers,
        guard_patterns=guard_patterns,
    )


def build_finding_dict(bead: "VulnerabilityBead") -> Dict[str, Any]:
    """Build a finding dict compatible with learning events."""
    modifiers, signature = _extract_modifiers_and_signature(bead)
    return {
        "pattern_id": bead.pattern_id,
        "finding_id": bead.id,
        "id": bead.id,
        "function_signature": signature,
        "function_name": bead.vulnerable_code.function_name or "",
        "contract_name": bead.vulnerable_code.contract_name or "",
        "modifiers": modifiers,
        "code": bead.vulnerable_code.source,
        "code_snippet": bead.vulnerable_code.source,
        "file_path": bead.vulnerable_code.file_path,
        "inheritance_chain": bead.inheritance_chain,
    }


class PostBeadLearner:
    """Apply conservative learning updates after a bead is finalized."""

    def __init__(
        self,
        learning_dir: Path = DEFAULT_LEARNING_DIR,
        decay_config: Optional[DecayConfig] = None,
    ):
        self.learning_dir = learning_dir
        self._decay_config = decay_config
        self._config = load_learning_config(learning_dir)

    def process(self, bead: "VulnerabilityBead") -> None:
        """Process a finalized bead and record learning artifacts."""
        if not (self._config.overlay_enabled or self._config.events_enabled or self._config.fp_enabled):
            return
        if bead.verdict is None:
            return

        event_type = _event_type_from_verdict(bead)
        if event_type is None:
            return

        finding = build_finding_dict(bead)
        if self._config.events_enabled:
            self._record_event(bead, finding, event_type)

        if self._config.fp_enabled and event_type == EventType.REJECTED:
            self._record_false_positive(bead)

        if self._config.overlay_enabled:
            self._record_overlay_assertions(bead)

    def _record_event(
        self,
        bead: "VulnerabilityBead",
        finding: Dict[str, Any],
        event_type: EventType,
    ) -> None:
        store = EventStore(self.learning_dir, self._decay_config)
        confidence_before = bead.confidence
        confidence_after = _apply_adjustment(confidence_before, event_type)
        reason = bead.verdict.reason if bead.verdict else ""
        enriched = create_event_from_finding(
            finding=finding,
            event_type=event_type,
            reason=reason,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            verdict_source=_verdict_source(bead),
        )
        store.record(enriched)

    def _record_false_positive(self, bead: "VulnerabilityBead") -> None:
        recorder = FalsePositiveRecorder(self.learning_dir)
        stub = build_finding_stub(bead)
        reason = bead.verdict.reason if bead.verdict else ""
        recorder.record(stub, reason, guard_patterns=stub.guard_patterns)

    def _record_overlay_assertions(self, bead: "VulnerabilityBead") -> None:
        overlay = LearningOverlayStore(
            self.learning_dir,
            decay_config=self._decay_config,
            min_confidence=self._config.min_confidence,
        )
        notes = _collect_learning_lines(bead)
        for entry in notes:
            parsed = _parse_learning_line(entry, bead)
            if not parsed:
                continue
            kind, payload = parsed
            if kind == "label":
                overlay.record_label(**payload)
            elif kind == "edge":
                overlay.record_edge(**payload)


def _event_type_from_verdict(bead: "VulnerabilityBead") -> Optional[EventType]:
    if bead.verdict is None:
        return None
    if bead.verdict.type == VerdictType.TRUE_POSITIVE:
        return EventType.CONFIRMED
    if bead.verdict.type == VerdictType.FALSE_POSITIVE:
        return EventType.REJECTED
    return EventType.ESCALATED


def _apply_adjustment(confidence: float, event_type: EventType) -> float:
    adjustment = default_adjustment(event_type)
    new_value = confidence + adjustment
    return max(0.0, min(1.0, new_value))


def _verdict_source(bead: "VulnerabilityBead") -> str:
    if bead.verdict and bead.verdict.auditor_id:
        return "human"
    return "llm"


def _extract_modifiers_and_signature(
    bead: "VulnerabilityBead",
) -> Tuple[List[str], str]:
    """Extract modifiers and signature from graph context when available."""
    modifiers: List[str] = []
    signature = ""

    if bead.graph_context:
        node = _get_graph_node(bead)
        if node:
            props = node.get("properties", {})
            modifiers = _normalize_modifiers(props.get("modifiers", []))
            signature = _normalize_signature(props.get("signature"))

    if not signature:
        func_name = bead.vulnerable_code.function_name or ""
        signature = f"{func_name}()" if func_name else ""

    return modifiers, signature


def _get_graph_node(bead: "VulnerabilityBead") -> Optional[Dict[str, Any]]:
    nodes = bead.graph_context.get("nodes", {}) if bead.graph_context else {}
    if not nodes:
        return None

    if bead.function_id and bead.function_id in nodes:
        return nodes[bead.function_id]

    function_name = bead.vulnerable_code.function_name
    if not function_name:
        return None

    for node in nodes.values():
        props = node.get("properties", {})
        if props.get("name") == function_name:
            return node
    return None


def _normalize_modifiers(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return []


def _normalize_signature(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        name = str(value[0])
        args = value[1] if len(value) > 1 else []
        if isinstance(args, list):
            return f"{name}({','.join(args)})"
        return f"{name}()"
    return ""


def _extract_guard_patterns(bead: "VulnerabilityBead") -> List[str]:
    guards = extract_guards(bead.vulnerable_code.source)
    if not guards:
        return []
    return guards.split("|")


def _collect_learning_lines(bead: "VulnerabilityBead") -> Iterable[str]:
    lines: List[str] = []
    notes = bead.notes or []
    for note in notes:
        stripped = _strip_note_prefix(note)
        if stripped:
            lines.append(stripped)

    if bead.verdict and bead.verdict.evidence:
        lines.extend(bead.verdict.evidence)

    return lines


def _strip_note_prefix(note: str) -> str:
    if note.startswith("[") and "]" in note:
        return note.split("]", 1)[1].strip()
    return note.strip()


def _parse_learning_line(
    line: str,
    bead: "VulnerabilityBead",
) -> Optional[Tuple[str, Dict[str, Any]]]:
    if line.startswith(LABEL_PREFIX):
        return _parse_label_line(line, bead)
    if line.startswith(EDGE_PREFIX):
        return _parse_edge_line(line, bead)
    if line.startswith(CONTEXT_PREFIX):
        return _parse_context_line(line, bead)
    return None


def _parse_label_line(
    line: str,
    bead: "VulnerabilityBead",
) -> Optional[Tuple[str, Dict[str, Any]]]:
    payload = line[len(LABEL_PREFIX):].strip()
    parts = payload.split(":")
    if len(parts) < 2:
        return None
    label = parts[0].strip().upper()
    node_id, confidence = _parse_node_and_confidence(parts[1:])
    node_id = _resolve_node_id(node_id, bead)
    if not node_id or not is_valid_label(label):
        return None
    return "label", {
        "node_id": node_id,
        "label": label,
        "pattern_id": bead.pattern_id,
        "bead_id": bead.id,
        "evidence": _label_evidence(bead),
        "confidence": confidence,
    }


def _parse_edge_line(
    line: str,
    bead: "VulnerabilityBead",
) -> Optional[Tuple[str, Dict[str, Any]]]:
    payload = line[len(EDGE_PREFIX):].strip()
    parts = payload.split(":")
    if len(parts) < 2:
        return None
    relation = parts[0].strip().upper()
    rest = ":".join(parts[1:])
    edge_part, confidence = _split_confidence(rest)
    if "->" not in edge_part:
        return None
    source_raw, target_raw = edge_part.split("->", 1)
    source_id = _resolve_node_id(source_raw.strip(), bead)
    target_id = _resolve_node_id(target_raw.strip(), bead)
    if not source_id or not target_id or not is_valid_label(relation):
        return None
    return "edge", {
        "source_id": source_id,
        "target_id": target_id,
        "relation": relation,
        "pattern_id": bead.pattern_id,
        "bead_id": bead.id,
        "evidence": _label_evidence(bead),
        "confidence": confidence,
    }


def _parse_context_line(
    line: str,
    bead: "VulnerabilityBead",
) -> Optional[Tuple[str, Dict[str, Any]]]:
    payload = line[len(CONTEXT_PREFIX):].strip()
    parts = payload.split(":")
    if len(parts) < 3:
        return None
    category = parts[0].strip().upper()
    key = parts[1].strip()
    node_id, confidence = _parse_node_and_confidence(parts[2:])
    node_id = _resolve_node_id(node_id, bead)
    label = f"CONTEXT:{category}:{key}"
    if not node_id or not is_valid_label(label):
        return None
    return "label", {
        "node_id": node_id,
        "label": label,
        "pattern_id": bead.pattern_id,
        "bead_id": bead.id,
        "evidence": _label_evidence(bead),
        "confidence": confidence,
    }


def _parse_node_and_confidence(parts: List[str]) -> Tuple[str, float]:
    node_value = ":".join(parts)
    node_value, confidence = _split_confidence(node_value)
    return node_value.strip(), confidence


def _split_confidence(value: str) -> Tuple[str, float]:
    if ":" not in value:
        return value, 0.9
    head, tail = value.rsplit(":", 1)
    if _is_float(tail):
        return head, float(tail)
    return value, 0.9


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _resolve_node_id(raw: str, bead: "VulnerabilityBead") -> str:
    token = raw.strip().lower()
    if token in {"self", "target", "@self", "@target", "this"}:
        return bead.function_id or ""
    return raw.strip()


def _label_evidence(bead: "VulnerabilityBead") -> List[str]:
    evidence = []
    if bead.vulnerable_code.file_path:
        location = f"{bead.vulnerable_code.file_path}:{bead.vulnerable_code.start_line}"
        evidence.append(location)
    if bead.verdict and bead.verdict.reason:
        evidence.append(bead.verdict.reason)
    return evidence


def _load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)
