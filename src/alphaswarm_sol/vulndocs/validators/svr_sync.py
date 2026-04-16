"""SVR field sync validator.

Task 18.5/18.6: Enforce required fields for Specific Vulnerability Reports (SVR).

This validator is stricter than the generic completeness check and focuses on
schema-level coverage for real-world testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List

from alphaswarm_sol.vulndocs.knowledge_doc import (
    PatternLinkageType,
    SourceSummary,
    VulnKnowledgeDoc,
)


@dataclass
class SVRFieldSyncResult:
    """Result of SVR field sync."""

    missing_fields: List[str] = field(default_factory=list)
    completeness_score: float = 0.0
    total_fields: int = 0

    def to_dict(self) -> Dict[str, object]:
        """Serialize to dictionary."""
        return {
            "missing_fields": self.missing_fields,
            "completeness_score": self.completeness_score,
            "total_fields": self.total_fields,
        }


def _score(missing_fields: List[str], total_fields: int) -> float:
    if total_fields == 0:
        return 0.0
    return (total_fields - len(missing_fields)) / total_fields


class SVRFieldSync:
    """Validate SVR field completeness for summaries and docs."""

    def __init__(self) -> None:
        self._doc_checks: Dict[str, Callable[[VulnKnowledgeDoc], bool]] = {
            "id": lambda d: bool(d.id),
            "name": lambda d: bool(d.name),
            "category": lambda d: bool(d.category),
            "subcategory": lambda d: bool(d.subcategory),
            "severity": lambda d: d.severity is not None,
            "one_liner": lambda d: bool(d.one_liner),
            "tldr": lambda d: bool(d.tldr),
            "detection.graph_signals": lambda d: bool(d.detection.graph_signals),
            "detection.indicators": lambda d: bool(d.detection.indicators),
            "detection.checklist": lambda d: bool(d.detection.checklist),
            "exploitation.attack_vector": lambda d: bool(d.exploitation.attack_vector),
            "exploitation.attack_steps": lambda d: bool(d.exploitation.attack_steps),
            "exploitation.potential_impact": lambda d: bool(d.exploitation.potential_impact),
            "mitigation.primary_fix": lambda d: bool(d.mitigation.primary_fix),
            "mitigation.how_to_verify": lambda d: bool(d.mitigation.how_to_verify),
            "examples.vulnerable_code": lambda d: bool(d.examples.vulnerable_code),
            "examples.fixed_code": lambda d: bool(d.examples.fixed_code),
            "examples.real_exploits": lambda d: bool(d.examples.real_exploits),
            "pattern_linkage": lambda d: (
                bool(d.pattern_linkage.pattern_ids)
                or d.pattern_linkage.linkage_type != PatternLinkageType.THEORETICAL
            ),
            "metadata.sources": lambda d: bool(d.metadata.sources),
        }

        self._summary_checks: Dict[str, Callable[[SourceSummary], bool]] = {
            "key_points": lambda s: bool(s.key_points),
            "attack_vector": lambda s: bool(s.attack_vector),
            "attack_steps": lambda s: bool(s.attack_steps),
            "mitigation": lambda s: bool(s.mitigation),
            "safe_patterns": lambda s: bool(s.safe_patterns),
            "vulnerable_code": lambda s: bool(s.vulnerable_code),
            "fixed_code": lambda s: bool(s.fixed_code),
            "incidents": lambda s: bool(s.incidents),
        }

    def sync_doc(self, doc: VulnKnowledgeDoc) -> SVRFieldSyncResult:
        """Check SVR field completeness for a merged document."""
        missing = [name for name, check in self._doc_checks.items() if not check(doc)]

        if doc.category in {"access-control", "logic"}:
            missing.extend(self._check_auth_logic_fields(doc))

        total_fields = len(self._doc_checks) + (
            4 if doc.category in {"access-control", "logic"} else 0
        )
        return SVRFieldSyncResult(
            missing_fields=sorted(set(missing)),
            completeness_score=_score(missing, total_fields),
            total_fields=total_fields,
        )

    def sync_summary(self, summary: SourceSummary) -> SVRFieldSyncResult:
        """Check SVR field completeness for a source summary."""
        missing = [
            name for name, check in self._summary_checks.items() if not check(summary)
        ]
        total_fields = len(self._summary_checks)
        return SVRFieldSyncResult(
            missing_fields=missing,
            completeness_score=_score(missing, total_fields),
            total_fields=total_fields,
        )

    def _check_auth_logic_fields(self, doc: VulnKnowledgeDoc) -> List[str]:
        checklist = " ".join(doc.detection.checklist).lower()
        missing = []

        if not _has_keyword(checklist, ["permission", "role", "access", "auth"]):
            missing.append("auth.permission_model")

        if not _has_keyword(checklist, ["trust boundary", "caller", "external"]):
            missing.append("auth.trust_boundaries")

        if not _has_keyword(checklist, ["invariant", "state", "assumption"]):
            missing.append("logic.invariants")

        if not _has_keyword(checklist, ["abuse", "misuse", "edge case"]):
            missing.append("abuse_case_checklist")

        return missing


def _has_keyword(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def sync_svr_doc(doc: VulnKnowledgeDoc) -> SVRFieldSyncResult:
    """Convenience wrapper for SVRFieldSync.sync_doc."""
    return SVRFieldSync().sync_doc(doc)


def sync_svr_summary(summary: SourceSummary) -> SVRFieldSyncResult:
    """Convenience wrapper for SVRFieldSync.sync_summary."""
    return SVRFieldSync().sync_summary(summary)
