"""v2 Result Packaging for Pattern Engine outputs.

This module provides v2-compliant pattern result packaging that:
- Emits matched/failed/unknown clause lists
- Adds clause_matrix with evidence/omission links
- Applies unknowns budget gating (excess -> insufficient evidence)
- Uses deterministic evidence IDs and omissions ledger
- Integrates validator at the packaging boundary (fail fast)

Reference: docs/reference/graph-interface-v2.md
Schema: schemas/graph_interface_v2.json
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from alphaswarm_sol.llm.interface_contract import (
    CONTRACT_VERSION,
    ClauseStatus,
    CutSetEntry,
    EvidenceRef,
    ClauseMatrixEntry,
    OmissionLedger,
    OmissionReason,
    EvidenceMissingReason,
    SliceMode,
    UnknownsBudget,
    UnknownsBudgetGate,
    GraphInterfaceValidator,
    GraphInterfaceContractViolation,
    generate_evidence_id,
    generate_build_hash,
)

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level for pattern matches."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ClauseResult:
    """Result for a single clause evaluation.

    Attributes:
        clause: Clause identifier (e.g., "visibility.public", "has_external_call")
        status: Whether the clause matched, failed, or is unknown
        evidence: List of evidence references for this clause
        omission_refs: List of omission reason codes for unknown clauses
    """

    clause: str
    status: ClauseStatus
    evidence: List[EvidenceRef] = field(default_factory=list)
    omission_refs: List[str] = field(default_factory=list)

    def to_clause_matrix_entry(self) -> ClauseMatrixEntry:
        """Convert to ClauseMatrixEntry for v2 output."""
        return ClauseMatrixEntry(
            clause=self.clause,
            status=self.status,
            evidence_refs=self.evidence,
            omission_refs=self.omission_refs,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "clause": self.clause,
            "status": self.status.value,
            "evidence_refs": [e.to_dict() for e in self.evidence],
            "omission_refs": self.omission_refs,
        }


@dataclass
class ClauseMatrix:
    """Truth table for all clauses in a pattern match.

    The clause matrix provides a complete truth table of all evaluated clauses,
    with evidence and omission links for each.

    Attributes:
        entries: List of clause results
    """

    entries: List[ClauseResult] = field(default_factory=list)

    @property
    def matched_clauses(self) -> List[str]:
        """Get list of matched clause identifiers."""
        return [e.clause for e in self.entries if e.status == ClauseStatus.MATCHED]

    @property
    def failed_clauses(self) -> List[str]:
        """Get list of failed clause identifiers."""
        return [e.clause for e in self.entries if e.status == ClauseStatus.FAILED]

    @property
    def unknown_clauses(self) -> List[str]:
        """Get list of unknown clause identifiers."""
        return [e.clause for e in self.entries if e.status == ClauseStatus.UNKNOWN]

    def add(
        self,
        clause: str,
        status: ClauseStatus,
        evidence: Optional[List[EvidenceRef]] = None,
        omission_refs: Optional[List[str]] = None,
    ) -> None:
        """Add a clause result to the matrix.

        Args:
            clause: Clause identifier
            status: Clause evaluation status
            evidence: Evidence references (for matched clauses)
            omission_refs: Omission reason codes (for unknown clauses)
        """
        self.entries.append(
            ClauseResult(
                clause=clause,
                status=status,
                evidence=evidence or [],
                omission_refs=omission_refs or [],
            )
        )

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dictionaries for v2 output."""
        return [e.to_dict() for e in self.entries]


@dataclass
class EvidenceMissing:
    """Record of missing evidence for a clause.

    Attributes:
        reason: Reason code for missing evidence
        clause: Clause this applies to
        details: Additional explanation
    """

    reason: EvidenceMissingReason
    clause: str
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: Dict[str, Any] = {
            "reason": self.reason.value,
            "clause": self.clause,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class FindingV2:
    """v2-compliant finding structure.

    Attributes:
        id: Unique finding identifier
        pattern_id: Pattern that matched
        severity: Severity level
        confidence: Confidence score (0.0-1.0)
        clause_matrix: Truth table for all clauses
        evidence_refs: Combined evidence references for this finding
        evidence_missing: Reasons why evidence is missing
        omissions: Omission ledger for this finding
        insufficient_evidence: True if unknowns budget exceeded
    """

    id: str
    pattern_id: str
    severity: str
    confidence: float
    clause_matrix: ClauseMatrix
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    evidence_missing: List[EvidenceMissing] = field(default_factory=list)
    omissions: Optional[OmissionLedger] = None
    insufficient_evidence: bool = False
    # Additional metadata from pattern engine
    node_id: Optional[str] = None
    node_label: Optional[str] = None
    node_type: Optional[str] = None

    @property
    def matched_clauses(self) -> List[str]:
        """Get list of matched clause identifiers."""
        return self.clause_matrix.matched_clauses

    @property
    def failed_clauses(self) -> List[str]:
        """Get list of failed clause identifiers."""
        return self.clause_matrix.failed_clauses

    @property
    def unknown_clauses(self) -> List[str]:
        """Get list of unknown clause identifiers."""
        return self.clause_matrix.unknown_clauses

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for v2 output."""
        result: Dict[str, Any] = {
            "id": self.id,
            "pattern_id": self.pattern_id,
            "severity": self.severity,
            "confidence": self.confidence,
            "matched_clauses": self.matched_clauses,
            "failed_clauses": self.failed_clauses,
            "unknown_clauses": self.unknown_clauses,
            "clause_matrix": self.clause_matrix.to_list(),
            "omissions": (
                self.omissions.to_dict()
                if self.omissions
                else OmissionLedger(coverage_score=1.0).to_dict()
            ),
        }
        # Must have either evidence_refs or evidence_missing
        if self.evidence_refs:
            result["evidence_refs"] = [e.to_dict() for e in self.evidence_refs]
        if self.evidence_missing:
            result["evidence_missing"] = [e.to_dict() for e in self.evidence_missing]
        # If neither, add legacy_no_evidence
        if not self.evidence_refs and not self.evidence_missing:
            result["evidence_missing"] = [
                {
                    "reason": EvidenceMissingReason.LEGACY_NO_EVIDENCE.value,
                    "clause": "legacy",
                    "details": "Evidence not available from pattern engine",
                }
            ]
        if self.insufficient_evidence:
            result["insufficient_evidence"] = True
        return result


@dataclass
class ResultsV2:
    """v2-compliant pattern results output.

    This is the top-level structure for pattern query results that
    complies with the Graph Interface Contract v2.

    Attributes:
        interface_version: Contract version string
        build_hash: 12-char graph build hash
        timestamp: ISO8601 generation timestamp
        query_kind: Query type (pattern, logic, etc.)
        query_id: Query identifier
        query_source: Raw query string
        findings: List of v2 findings
        omissions: Global omission ledger
        nodes_count: Number of nodes in result
        edges_count: Number of edges in result
    """

    interface_version: str = CONTRACT_VERSION
    build_hash: str = "000000000000"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    query_kind: str = "pattern"
    query_id: str = ""
    query_source: str = ""
    findings: List[FindingV2] = field(default_factory=list)
    omissions: Optional[OmissionLedger] = None
    nodes_count: int = 0
    edges_count: int = 0

    @property
    def coverage_score(self) -> float:
        """Get global coverage score."""
        if self.omissions:
            return self.omissions.coverage_score
        return 1.0

    @property
    def unknowns_count(self) -> int:
        """Get total count of unknown clauses across all findings."""
        return sum(len(f.unknown_clauses) for f in self.findings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for v2 output."""
        return {
            "interface_version": self.interface_version,
            "build_hash": self.build_hash,
            "timestamp": self.timestamp,
            "query": {
                "kind": self.query_kind,
                "id": self.query_id,
                "source": self.query_source,
            },
            "summary": {
                "nodes": self.nodes_count,
                "edges": self.edges_count,
                "findings": len(self.findings),
                "coverage_score": self.coverage_score,
                "omissions_present": (
                    self.omissions is not None
                    and (
                        len(self.omissions.cut_set) > 0
                        or len(self.omissions.excluded_edges) > 0
                    )
                ),
                "unknowns_count": self.unknowns_count,
            },
            "findings": [f.to_dict() for f in self.findings],
            "omissions": (
                self.omissions.to_dict()
                if self.omissions
                else OmissionLedger(coverage_score=1.0).to_dict()
            ),
        }


class PatternResultPackager:
    """Package pattern engine results to v2-compliant format.

    This packager transforms raw pattern engine findings into the
    Graph Interface Contract v2 format, including:
    - Clause matrix with evidence and omission links
    - Unknowns budget gating
    - Deterministic evidence IDs
    - Contract validation at the packaging boundary
    """

    def __init__(
        self,
        build_hash: Optional[str] = None,
        unknowns_budget: Optional[UnknownsBudget] = None,
        validator: Optional[GraphInterfaceValidator] = None,
        strict: bool = True,
    ):
        """Initialize packager.

        Args:
            build_hash: Graph build hash (12 chars hex)
            unknowns_budget: Budget for unknown clauses gating
            validator: Contract validator (created if None)
            strict: If True, raise on validation errors
        """
        self.build_hash = build_hash or "000000000000"
        self.unknowns_budget = unknowns_budget or UnknownsBudget()
        self.budget_gate = UnknownsBudgetGate(self.unknowns_budget)
        self.validator = validator or GraphInterfaceValidator(strict=strict)
        self.strict = strict
        self._finding_counter = 0

    def package(
        self,
        findings: List[Dict[str, Any]],
        *,
        query_id: str = "",
        query_source: str = "",
        nodes_count: int = 0,
        edges_count: int = 0,
        global_omissions: Optional[OmissionLedger] = None,
    ) -> ResultsV2:
        """Package raw pattern engine findings to v2 format.

        Args:
            findings: Raw findings from PatternEngine.run()
            query_id: Query identifier
            query_source: Raw query string
            nodes_count: Number of nodes in graph
            edges_count: Number of edges in graph
            global_omissions: Global omission ledger

        Returns:
            ResultsV2 instance

        Raises:
            GraphInterfaceContractViolation: If validation fails in strict mode
        """
        v2_findings = []
        for raw in findings:
            v2_finding = self._transform_finding(raw)
            v2_findings.append(v2_finding)

        # Apply unknowns budget gating
        for finding in v2_findings:
            finding_dict = finding.to_dict()
            passes, reason = self.budget_gate.check(finding_dict)
            if not passes:
                finding.insufficient_evidence = True
                logger.info(
                    f"Finding {finding.id} marked insufficient: {reason}"
                )

        result = ResultsV2(
            build_hash=self.build_hash,
            query_kind="pattern",
            query_id=query_id,
            query_source=query_source,
            findings=v2_findings,
            omissions=global_omissions or OmissionLedger(coverage_score=1.0),
            nodes_count=nodes_count,
            edges_count=edges_count,
        )

        # Validate at packaging boundary (fail fast)
        output_dict = result.to_dict()
        if self.strict:
            self.validator.validate_and_raise(output_dict)
        else:
            is_valid, errors = self.validator.validate(output_dict)
            if not is_valid:
                for error in errors:
                    logger.warning(f"Graph Interface Contract warning: {error}")

        return result

    def _transform_finding(self, raw: Dict[str, Any]) -> FindingV2:
        """Transform a raw finding to v2 format.

        Args:
            raw: Raw finding from PatternEngine

        Returns:
            FindingV2 instance
        """
        self._finding_counter += 1
        finding_id = f"FND-{self._finding_counter:04d}"

        pattern_id = raw.get("pattern_id", "unknown")
        severity = raw.get("severity", "medium")
        node_id = raw.get("node_id", "")
        node_label = raw.get("node_label", "")
        node_type = raw.get("node_type", "")

        # Build clause matrix from explain data
        clause_matrix = self._build_clause_matrix(raw, node_id)

        # Collect evidence refs from clause matrix
        evidence_refs = self._collect_evidence_refs(clause_matrix, node_id, node_label)

        # Build evidence_missing for legacy data
        evidence_missing = self._build_evidence_missing(clause_matrix)

        # Calculate confidence based on unknowns
        confidence = self._calculate_confidence(clause_matrix)

        # Build finding-level omissions
        finding_omissions = self._build_finding_omissions(raw)

        return FindingV2(
            id=finding_id,
            pattern_id=pattern_id,
            severity=severity,
            confidence=confidence,
            clause_matrix=clause_matrix,
            evidence_refs=evidence_refs,
            evidence_missing=evidence_missing,
            omissions=finding_omissions,
            node_id=node_id,
            node_label=node_label,
            node_type=node_type,
        )

    def _build_clause_matrix(
        self, raw: Dict[str, Any], node_id: str
    ) -> ClauseMatrix:
        """Build clause matrix from raw finding data.

        Args:
            raw: Raw finding dictionary
            node_id: Node ID for evidence generation

        Returns:
            ClauseMatrix instance
        """
        matrix = ClauseMatrix()
        explain = raw.get("explain") or {}

        # Process "all" conditions (must all match)
        for item in explain.get("all", []):
            clause_id = self._make_clause_id("all", item)
            matched = item.get("matched", False)
            status = ClauseStatus.MATCHED if matched else ClauseStatus.FAILED
            evidence = self._make_evidence_for_clause(item, node_id) if matched else []
            matrix.add(clause_id, status, evidence=evidence)

        # Process "any" conditions (at least one must match)
        for item in explain.get("any", []):
            clause_id = self._make_clause_id("any", item)
            matched = item.get("matched", False)
            status = ClauseStatus.MATCHED if matched else ClauseStatus.FAILED
            evidence = self._make_evidence_for_clause(item, node_id) if matched else []
            matrix.add(clause_id, status, evidence=evidence)

        # Process "none" conditions (none must match)
        for item in explain.get("none", []):
            clause_id = self._make_clause_id("none", item)
            matched = item.get("matched", False)
            # For "none", matched=False is good (clause passes)
            status = ClauseStatus.MATCHED if not matched else ClauseStatus.FAILED
            evidence = [] if matched else self._make_evidence_for_clause(item, node_id)
            matrix.add(clause_id, status, evidence=evidence)

        # Process operation conditions (ops_all, ops_any, ops_none)
        for key in ("ops_all", "ops_any", "ops_none"):
            for item in explain.get(key, []):
                clause_id = self._make_ops_clause_id(key, item)
                matched = item.get("matched", False)
                if key == "ops_none":
                    status = ClauseStatus.MATCHED if not matched else ClauseStatus.FAILED
                else:
                    status = ClauseStatus.MATCHED if matched else ClauseStatus.FAILED
                evidence = self._make_evidence_for_ops_clause(item, node_id) if matched else []
                matrix.add(clause_id, status, evidence=evidence)

        # Process edge conditions
        for item in explain.get("edges", []):
            clause_id = f"edge:{item.get('edge_type', 'unknown')}"
            matched = item.get("matched", False)
            status = ClauseStatus.MATCHED if matched else ClauseStatus.FAILED
            matrix.add(clause_id, status)

        # Process path conditions
        for item in explain.get("paths", []):
            edge_type = item.get("edge_type") or "multi"
            clause_id = f"path:{edge_type}"
            matched = item.get("matched", False)
            status = ClauseStatus.MATCHED if matched else ClauseStatus.FAILED
            matrix.add(clause_id, status)

        # Process tier_b if present
        tier_b = explain.get("tier_b") or {}
        if tier_b:
            matched = tier_b.get("matched", False)
            confidence = tier_b.get("confidence", "unknown")
            clause_id = f"tier_b:risk_tags:{confidence}"
            status = ClauseStatus.MATCHED if matched else ClauseStatus.FAILED
            matrix.add(clause_id, status)

        # If no clauses were added from explain, create a legacy clause
        if not matrix.entries:
            # Pattern matched but no explain data
            matrix.add(
                "pattern:matched",
                ClauseStatus.MATCHED,
                omission_refs=[OmissionReason.LIBRARY_EXCLUDED.value],
            )

        return matrix

    def _make_clause_id(self, group: str, item: Dict[str, Any]) -> str:
        """Make clause ID from condition item.

        Args:
            group: Condition group (all, any, none)
            item: Condition item dictionary

        Returns:
            Clause identifier string
        """
        prop = item.get("property", "unknown")
        op = item.get("op", "eq")
        return f"{group}:{prop}.{op}"

    def _make_ops_clause_id(self, group: str, item: Dict[str, Any]) -> str:
        """Make clause ID from operation condition item.

        Args:
            group: Operation group (ops_all, ops_any, ops_none)
            item: Operation condition dictionary

        Returns:
            Clause identifier string
        """
        cond_type = item.get("condition_type", "unknown")
        expected = item.get("expected", "")
        if isinstance(expected, dict):
            # sequence_order: {before: X, after: Y}
            before = expected.get("before", "")
            after = expected.get("after", "")
            return f"{group}:{cond_type}:{before}->{after}"
        if isinstance(expected, list):
            return f"{group}:{cond_type}:{','.join(str(e) for e in expected[:3])}"
        return f"{group}:{cond_type}:{expected}"

    def _make_evidence_for_clause(
        self, item: Dict[str, Any], node_id: str
    ) -> List[EvidenceRef]:
        """Create evidence refs for a matched clause.

        Args:
            item: Condition item dictionary
            node_id: Node ID for evidence

        Returns:
            List of evidence references
        """
        # For now, create a basic evidence ref from available data
        # Full evidence would require source location tracking
        if not node_id:
            return []

        evidence_id = generate_evidence_id(self.build_hash, node_id, 1, 0)
        return [
            EvidenceRef(
                file="unknown",
                line=1,
                node_id=node_id,
                snippet_id=evidence_id,
                build_hash=self.build_hash,
            )
        ]

    def _make_evidence_for_ops_clause(
        self, item: Dict[str, Any], node_id: str
    ) -> List[EvidenceRef]:
        """Create evidence refs for a matched operation clause.

        Args:
            item: Operation condition dictionary
            node_id: Node ID for evidence

        Returns:
            List of evidence references
        """
        return self._make_evidence_for_clause(item, node_id)

    def _collect_evidence_refs(
        self, clause_matrix: ClauseMatrix, node_id: str, node_label: str
    ) -> List[EvidenceRef]:
        """Collect all evidence refs from clause matrix.

        Args:
            clause_matrix: Clause matrix with evidence
            node_id: Node ID
            node_label: Node label for snippet

        Returns:
            Deduplicated list of evidence references
        """
        seen_ids: set = set()
        evidence_refs: List[EvidenceRef] = []

        for entry in clause_matrix.entries:
            for ref in entry.evidence:
                if ref.snippet_id not in seen_ids:
                    seen_ids.add(ref.snippet_id)
                    evidence_refs.append(ref)

        return evidence_refs

    def _build_evidence_missing(
        self, clause_matrix: ClauseMatrix
    ) -> List[EvidenceMissing]:
        """Build evidence_missing list from clause matrix.

        Args:
            clause_matrix: Clause matrix

        Returns:
            List of EvidenceMissing for unknown clauses
        """
        missing: List[EvidenceMissing] = []

        for entry in clause_matrix.entries:
            if entry.status == ClauseStatus.UNKNOWN:
                # Determine reason from omission_refs
                reason = EvidenceMissingReason.LEGACY_NO_EVIDENCE
                if entry.omission_refs:
                    try:
                        reason = EvidenceMissingReason(entry.omission_refs[0])
                    except ValueError:
                        pass
                missing.append(
                    EvidenceMissing(
                        reason=reason,
                        clause=entry.clause,
                        details="Clause evaluation could not determine status",
                    )
                )

        return missing

    def _calculate_confidence(self, clause_matrix: ClauseMatrix) -> float:
        """Calculate confidence score from clause matrix.

        Confidence is reduced by unknown clauses.

        Args:
            clause_matrix: Clause matrix

        Returns:
            Confidence score (0.0-1.0)
        """
        total = len(clause_matrix.entries)
        if total == 0:
            return 1.0

        matched = len(clause_matrix.matched_clauses)
        unknown = len(clause_matrix.unknown_clauses)

        # Base confidence from matched ratio
        base_confidence = matched / total

        # Penalty for unknowns
        unknown_penalty = (unknown / total) * 0.5

        return max(0.0, min(1.0, base_confidence - unknown_penalty))

    def _build_finding_omissions(
        self, raw: Dict[str, Any]
    ) -> OmissionLedger:
        """Build finding-level omissions ledger.

        Args:
            raw: Raw finding dictionary

        Returns:
            OmissionLedger instance
        """
        # Extract any omission info from explain
        explain = raw.get("explain") or {}

        cut_set: List[CutSetEntry] = []
        excluded_edges: List[str] = []

        # Check for tier_b context that indicates omissions
        tier_b_context = explain.get("tier_b_context") or {}
        if tier_b_context and not tier_b_context.get("matched"):
            # Tier B didn't match, could indicate missing risk tags
            cut_set.append(
                CutSetEntry(
                    blocker="tier_b_analysis",
                    reason=OmissionReason.LIBRARY_EXCLUDED,
                    impact="Risk tag analysis did not match",
                )
            )

        # Calculate coverage from clause matrix in raw
        total_clauses = sum(
            len(explain.get(k, [])) for k in ["all", "any", "none", "ops_all", "ops_any", "ops_none", "edges", "paths"]
        )
        coverage = 1.0 if total_clauses > 0 else 0.8  # Default to high coverage

        return OmissionLedger(
            coverage_score=coverage,
            cut_set=cut_set,
            excluded_edges=excluded_edges,
            slice_mode=SliceMode.STANDARD,
        )


def package_pattern_results(
    findings: List[Dict[str, Any]],
    *,
    build_hash: str = "000000000000",
    query_id: str = "",
    query_source: str = "",
    nodes_count: int = 0,
    edges_count: int = 0,
    unknowns_budget: Optional[UnknownsBudget] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """Package pattern engine findings to v2-compliant dictionary.

    Convenience function for packaging pattern results with default settings.

    Args:
        findings: Raw findings from PatternEngine.run()
        build_hash: Graph build hash
        query_id: Query identifier
        query_source: Raw query string
        nodes_count: Number of nodes in graph
        edges_count: Number of edges in graph
        unknowns_budget: Budget for unknown clauses gating
        strict: If True, raise on validation errors

    Returns:
        v2-compliant output dictionary

    Raises:
        GraphInterfaceContractViolation: If validation fails in strict mode
    """
    packager = PatternResultPackager(
        build_hash=build_hash,
        unknowns_budget=unknowns_budget,
        strict=strict,
    )
    result = packager.package(
        findings,
        query_id=query_id,
        query_source=query_source,
        nodes_count=nodes_count,
        edges_count=edges_count,
    )
    return result.to_dict()


__all__ = [
    # v2 Result structures
    "ResultsV2",
    "FindingV2",
    "ClauseMatrix",
    "ClauseResult",
    "EvidenceMissing",
    "ConfidenceLevel",
    # Packager
    "PatternResultPackager",
    # Convenience function
    "package_pattern_results",
]
