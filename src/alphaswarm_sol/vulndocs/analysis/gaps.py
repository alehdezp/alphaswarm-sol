"""Gap finding for VulnDocs knowledge system.

Provides detailed gap analysis beyond basic coverage:
- Deep section-level gap detection
- Pattern-document alignment analysis
- Knowledge completeness scoring
- Actionable recommendations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc
from alphaswarm_sol.vulndocs.storage.retrieval import KnowledgeRetriever, RetrievalDepth
from alphaswarm_sol.vulndocs.analysis.coverage import (
    THREAT_MODEL_CATEGORIES,
    CoverageLevel,
)


class GapType(Enum):
    """Types of knowledge gaps."""

    # Category/subcategory gaps
    MISSING_CATEGORY = "missing_category"
    MISSING_SUBCATEGORY = "missing_subcategory"

    # Document section gaps
    MISSING_DETECTION = "missing_detection"
    MISSING_EXPLOITATION = "missing_exploitation"
    MISSING_MITIGATION = "missing_mitigation"
    MISSING_EXAMPLES = "missing_examples"

    # Content quality gaps
    WEAK_DETECTION = "weak_detection"  # Detection without graph signals
    WEAK_EXPLOITATION = "weak_exploitation"  # No attack steps
    WEAK_MITIGATION = "weak_mitigation"  # No verification steps
    INCOMPLETE_EXAMPLES = "incomplete_examples"  # Missing vulnerable/fixed code

    # Pattern alignment gaps
    UNLINKED_PATTERN = "unlinked_pattern"  # Pattern exists but not linked
    ORPHAN_DOCUMENT = "orphan_document"  # Doc without pattern link
    MISALIGNED_CATEGORY = "misaligned_category"  # Doc/pattern category mismatch


class GapSeverity(Enum):
    """Severity of knowledge gaps."""

    CRITICAL = "critical"  # Blocks effective detection
    HIGH = "high"  # Significantly impacts detection quality
    MEDIUM = "medium"  # Reduces effectiveness
    LOW = "low"  # Minor improvement opportunity


@dataclass
class KnowledgeGap:
    """Detailed knowledge gap with actionable recommendations."""

    # Gap identification
    gap_type: GapType
    severity: GapSeverity
    category: str
    subcategory: Optional[str] = None

    # Target entity
    doc_id: Optional[str] = None
    pattern_id: Optional[str] = None
    section: Optional[str] = None

    # Description
    title: str = ""
    description: str = ""
    impact: str = ""

    # Recommendations
    recommendation: str = ""
    effort: str = "medium"  # "low", "medium", "high"
    priority: int = 5  # 1-10, 1 = highest

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "gap_type": self.gap_type.value,
            "severity": self.severity.value,
            "category": self.category,
            "subcategory": self.subcategory,
            "doc_id": self.doc_id,
            "pattern_id": self.pattern_id,
            "section": self.section,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "recommendation": self.recommendation,
            "effort": self.effort,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGap":
        """Deserialize from dictionary."""
        return cls(
            gap_type=GapType(data["gap_type"]),
            severity=GapSeverity(data["severity"]),
            category=data["category"],
            subcategory=data.get("subcategory"),
            doc_id=data.get("doc_id"),
            pattern_id=data.get("pattern_id"),
            section=data.get("section"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            impact=data.get("impact", ""),
            recommendation=data.get("recommendation", ""),
            effort=data.get("effort", "medium"),
            priority=data.get("priority", 5),
            metadata=data.get("metadata", {}),
        )


@dataclass
class GapAnalysisResult:
    """Result of gap analysis."""

    # All gaps found
    gaps: List[KnowledgeGap] = field(default_factory=list)

    # Summary by severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Summary by type
    gaps_by_type: Dict[str, int] = field(default_factory=dict)

    # Priority queue (top gaps to address)
    priority_queue: List[KnowledgeGap] = field(default_factory=list)

    # Completeness scores
    overall_completeness: float = 0.0
    detection_completeness: float = 0.0
    exploitation_completeness: float = 0.0
    mitigation_completeness: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "gaps": [g.to_dict() for g in self.gaps],
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "gaps_by_type": self.gaps_by_type,
            "priority_queue": [g.to_dict() for g in self.priority_queue[:10]],
            "overall_completeness": round(self.overall_completeness, 2),
            "detection_completeness": round(self.detection_completeness, 2),
            "exploitation_completeness": round(self.exploitation_completeness, 2),
            "mitigation_completeness": round(self.mitigation_completeness, 2),
        }


class GapFinder:
    """Finds and analyzes knowledge gaps in the VulnDocs system.

    Example:
        finder = GapFinder()
        result = finder.find_all_gaps()

        # Get priority gaps to address
        for gap in result.priority_queue[:5]:
            print(f"{gap.severity.value}: {gap.title}")
            print(f"  Recommendation: {gap.recommendation}")

        # Get gaps by type
        detection_gaps = finder.find_detection_gaps()
    """

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        """Initialize gap finder.

        Args:
            retriever: Knowledge retriever for accessing docs
        """
        self.retriever = retriever or KnowledgeRetriever()

    def find_all_gaps(self) -> GapAnalysisResult:
        """Find all knowledge gaps.

        Returns:
            GapAnalysisResult with all identified gaps
        """
        result = GapAnalysisResult()

        # Find gaps by category
        category_gaps = self._find_category_gaps()
        result.gaps.extend(category_gaps)

        # Find document quality gaps
        quality_gaps = self._find_quality_gaps()
        result.gaps.extend(quality_gaps)

        # Find pattern alignment gaps
        alignment_gaps = self._find_alignment_gaps()
        result.gaps.extend(alignment_gaps)

        # Calculate summaries
        self._calculate_summaries(result)

        # Build priority queue
        result.priority_queue = sorted(
            result.gaps,
            key=lambda g: (
                # Severity weight
                {"critical": 0, "high": 1, "medium": 2, "low": 3}[g.severity.value],
                # Then by explicit priority
                g.priority,
                # Then by effort (prefer low effort)
                {"low": 0, "medium": 1, "high": 2}[g.effort],
            ),
        )

        return result

    def _find_category_gaps(self) -> List[KnowledgeGap]:
        """Find gaps at the category/subcategory level."""
        gaps = []

        for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
            is_critical = cat_info.get("critical", False)

            # Get docs for this category
            result = self.retriever.get_by_category(
                category=cat_id,
                depth=RetrievalDepth.MINIMAL,
                max_results=100,
            )

            # Check for empty category
            if not result.documents:
                gaps.append(
                    KnowledgeGap(
                        gap_type=GapType.MISSING_CATEGORY,
                        severity=GapSeverity.CRITICAL if is_critical else GapSeverity.HIGH,
                        category=cat_id,
                        title=f"Missing category: {cat_info['display']}",
                        description=f"No knowledge documents exist for {cat_info['display']}",
                        impact="Cannot provide knowledge context for this vulnerability class",
                        recommendation=f"Create foundational documentation for {cat_info['display']}",
                        effort="high",
                        priority=1 if is_critical else 2,
                    )
                )
                continue

            # Check for missing subcategories
            covered_subcats = {doc.subcategory for doc in result.documents}
            expected_subcats = set(cat_info.get("subcategories", []))
            missing_subcats = expected_subcats - covered_subcats

            for subcat in missing_subcats:
                gaps.append(
                    KnowledgeGap(
                        gap_type=GapType.MISSING_SUBCATEGORY,
                        severity=GapSeverity.HIGH if is_critical else GapSeverity.MEDIUM,
                        category=cat_id,
                        subcategory=subcat,
                        title=f"Missing subcategory: {cat_id}/{subcat}",
                        description=f"No documentation for {subcat} variant of {cat_info['display']}",
                        impact=f"Detection guidance missing for {subcat} vulnerabilities",
                        recommendation=f"Create knowledge document for {subcat}",
                        effort="medium",
                        priority=3 if is_critical else 4,
                    )
                )

        return gaps

    def _find_quality_gaps(self) -> List[KnowledgeGap]:
        """Find gaps in document quality."""
        gaps = []

        # Get all documents
        for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
            result = self.retriever.get_by_category(
                category=cat_id,
                depth=RetrievalDepth.FULL,
                max_results=100,
            )

            is_critical = cat_info.get("critical", False)

            for doc in result.documents:
                doc_gaps = self._analyze_document_quality(doc, is_critical)
                gaps.extend(doc_gaps)

        return gaps

    def _analyze_document_quality(
        self,
        doc: VulnKnowledgeDoc,
        is_critical: bool,
    ) -> List[KnowledgeGap]:
        """Analyze quality gaps in a single document."""
        gaps = []

        # Detection section analysis
        if not doc.detection.graph_signals:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.WEAK_DETECTION,
                    severity=GapSeverity.HIGH,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="detection",
                    title=f"Missing graph signals: {doc.name}",
                    description="No graph signals defined for pattern detection",
                    impact="Tier A pattern matching cannot use this document",
                    recommendation="Add graph_signals with semantic properties",
                    effort="medium",
                    priority=2,
                )
            )

        if not doc.detection.checklist:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.WEAK_DETECTION,
                    severity=GapSeverity.MEDIUM,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="detection",
                    title=f"Missing detection checklist: {doc.name}",
                    description="No detection checklist for manual review",
                    impact="Auditors lack structured guidance",
                    recommendation="Add detection checklist items",
                    effort="low",
                    priority=5,
                )
            )

        # Exploitation section analysis
        if not doc.exploitation.attack_steps:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.WEAK_EXPLOITATION,
                    severity=GapSeverity.MEDIUM,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="exploitation",
                    title=f"Missing attack steps: {doc.name}",
                    description="No attack steps defined",
                    impact="Cannot generate test scenarios",
                    recommendation="Add step-by-step attack procedure",
                    effort="medium",
                    priority=4,
                )
            )

        if not doc.exploitation.prerequisites:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.WEAK_EXPLOITATION,
                    severity=GapSeverity.LOW,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="exploitation",
                    title=f"Missing prerequisites: {doc.name}",
                    description="No prerequisites for exploitation",
                    impact="Risk assessment may be incomplete",
                    recommendation="Document exploitation prerequisites",
                    effort="low",
                    priority=6,
                )
            )

        # Mitigation section analysis
        if not doc.mitigation.primary_fix:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.WEAK_MITIGATION,
                    severity=GapSeverity.HIGH,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="mitigation",
                    title=f"Missing primary fix: {doc.name}",
                    description="No primary fix recommendation",
                    impact="Developers lack remediation guidance",
                    recommendation="Add primary fix recommendation",
                    effort="low",
                    priority=3,
                )
            )

        if not doc.mitigation.how_to_verify:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.WEAK_MITIGATION,
                    severity=GapSeverity.MEDIUM,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="mitigation",
                    title=f"Missing verification steps: {doc.name}",
                    description="No steps to verify fix effectiveness",
                    impact="Cannot validate remediation",
                    recommendation="Add verification checklist",
                    effort="low",
                    priority=5,
                )
            )

        # Examples section analysis
        if not doc.examples.vulnerable_code:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.INCOMPLETE_EXAMPLES,
                    severity=GapSeverity.MEDIUM,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="examples",
                    title=f"Missing vulnerable code example: {doc.name}",
                    description="No vulnerable code example",
                    impact="LLM context lacks concrete examples",
                    recommendation="Add vulnerable code snippet",
                    effort="medium",
                    priority=4,
                )
            )

        if not doc.examples.fixed_code:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.INCOMPLETE_EXAMPLES,
                    severity=GapSeverity.MEDIUM,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    section="examples",
                    title=f"Missing fixed code example: {doc.name}",
                    description="No fixed code example",
                    impact="Developers lack remediation reference",
                    recommendation="Add fixed code snippet",
                    effort="medium",
                    priority=4,
                )
            )

        return gaps

    def _find_alignment_gaps(self) -> List[KnowledgeGap]:
        """Find pattern-document alignment gaps."""
        gaps = []

        # Track all pattern IDs mentioned in threat model
        all_patterns: Set[str] = set()
        for cat_info in THREAT_MODEL_CATEGORIES.values():
            all_patterns.update(cat_info.get("patterns", []))

        # Get all documents and track their pattern links
        linked_patterns: Set[str] = set()
        orphan_docs: List[VulnKnowledgeDoc] = []

        for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
            result = self.retriever.get_by_category(
                category=cat_id,
                depth=RetrievalDepth.MINIMAL,
                max_results=100,
            )

            for doc in result.documents:
                if doc.pattern_linkage.pattern_ids:
                    linked_patterns.update(doc.pattern_linkage.pattern_ids)
                else:
                    orphan_docs.append(doc)

        # Find unlinked patterns
        unlinked_patterns = all_patterns - linked_patterns
        for pattern_id in unlinked_patterns:
            # Find which category this pattern belongs to
            category = None
            is_critical = False
            for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
                if pattern_id in cat_info.get("patterns", []):
                    category = cat_id
                    is_critical = cat_info.get("critical", False)
                    break

            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.UNLINKED_PATTERN,
                    severity=GapSeverity.HIGH if is_critical else GapSeverity.MEDIUM,
                    category=category or "unknown",
                    pattern_id=pattern_id,
                    title=f"Unlinked pattern: {pattern_id}",
                    description=f"Pattern {pattern_id} has no linked knowledge documents",
                    impact="Pattern findings lack knowledge context",
                    recommendation=f"Link {pattern_id} to relevant knowledge documents",
                    effort="low",
                    priority=3,
                )
            )

        # Report orphan documents
        for doc in orphan_docs:
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.ORPHAN_DOCUMENT,
                    severity=GapSeverity.LOW,
                    category=doc.category,
                    subcategory=doc.subcategory,
                    doc_id=doc.id,
                    title=f"Orphan document: {doc.name}",
                    description="Document not linked to any patterns",
                    impact="Document may not be surfaced during analysis",
                    recommendation="Link to relevant patterns or remove if obsolete",
                    effort="low",
                    priority=7,
                )
            )

        return gaps

    def _calculate_summaries(self, result: GapAnalysisResult) -> None:
        """Calculate summary statistics for the result."""
        # Count by severity
        for gap in result.gaps:
            if gap.severity == GapSeverity.CRITICAL:
                result.critical_count += 1
            elif gap.severity == GapSeverity.HIGH:
                result.high_count += 1
            elif gap.severity == GapSeverity.MEDIUM:
                result.medium_count += 1
            else:
                result.low_count += 1

            # Count by type
            gap_type = gap.gap_type.value
            result.gaps_by_type[gap_type] = result.gaps_by_type.get(gap_type, 0) + 1

        # Calculate completeness scores
        total_docs = 0
        detection_complete = 0
        exploitation_complete = 0
        mitigation_complete = 0

        for cat_id in THREAT_MODEL_CATEGORIES:
            docs = self.retriever.get_by_category(
                category=cat_id,
                depth=RetrievalDepth.FULL,
                max_results=100,
            )
            total_docs += len(docs.documents)

            for doc in docs.documents:
                if doc.detection.graph_signals and doc.detection.checklist:
                    detection_complete += 1
                if doc.exploitation.attack_steps and doc.exploitation.prerequisites:
                    exploitation_complete += 1
                if doc.mitigation.primary_fix and doc.mitigation.how_to_verify:
                    mitigation_complete += 1

        if total_docs > 0:
            result.detection_completeness = detection_complete / total_docs * 100
            result.exploitation_completeness = exploitation_complete / total_docs * 100
            result.mitigation_completeness = mitigation_complete / total_docs * 100
            result.overall_completeness = (
                result.detection_completeness * 0.4
                + result.exploitation_completeness * 0.3
                + result.mitigation_completeness * 0.3
            )

    def find_detection_gaps(self) -> List[KnowledgeGap]:
        """Find only detection-related gaps.

        Returns:
            List of gaps affecting detection quality
        """
        all_gaps = self.find_all_gaps()
        return [
            g
            for g in all_gaps.gaps
            if g.gap_type
            in (GapType.MISSING_DETECTION, GapType.WEAK_DETECTION)
            or g.section == "detection"
        ]

    def find_exploitation_gaps(self) -> List[KnowledgeGap]:
        """Find only exploitation-related gaps.

        Returns:
            List of gaps affecting exploitation guidance
        """
        all_gaps = self.find_all_gaps()
        return [
            g
            for g in all_gaps.gaps
            if g.gap_type
            in (GapType.MISSING_EXPLOITATION, GapType.WEAK_EXPLOITATION)
            or g.section == "exploitation"
        ]

    def find_mitigation_gaps(self) -> List[KnowledgeGap]:
        """Find only mitigation-related gaps.

        Returns:
            List of gaps affecting remediation guidance
        """
        all_gaps = self.find_all_gaps()
        return [
            g
            for g in all_gaps.gaps
            if g.gap_type
            in (GapType.MISSING_MITIGATION, GapType.WEAK_MITIGATION)
            or g.section == "mitigation"
        ]

    def find_critical_gaps(self) -> List[KnowledgeGap]:
        """Find only critical severity gaps.

        Returns:
            List of critical gaps
        """
        all_gaps = self.find_all_gaps()
        return [g for g in all_gaps.gaps if g.severity == GapSeverity.CRITICAL]

    def find_gaps_for_category(self, category: str) -> List[KnowledgeGap]:
        """Find gaps for a specific category.

        Args:
            category: Category ID

        Returns:
            List of gaps for this category
        """
        all_gaps = self.find_all_gaps()
        return [g for g in all_gaps.gaps if g.category == category]

    def find_gaps_for_document(self, doc_id: str) -> List[KnowledgeGap]:
        """Find gaps for a specific document.

        Args:
            doc_id: Document ID

        Returns:
            List of gaps for this document
        """
        all_gaps = self.find_all_gaps()
        return [g for g in all_gaps.gaps if g.doc_id == doc_id]


# =============================================================================
# Convenience Functions
# =============================================================================


def find_all_gaps() -> GapAnalysisResult:
    """Find all knowledge gaps using default finder.

    Returns:
        GapAnalysisResult with all identified gaps
    """
    finder = GapFinder()
    return finder.find_all_gaps()


def get_priority_gaps(limit: int = 10) -> List[KnowledgeGap]:
    """Get top priority gaps to address.

    Args:
        limit: Maximum number of gaps to return

    Returns:
        List of priority-sorted gaps
    """
    result = find_all_gaps()
    return result.priority_queue[:limit]


def get_gap_summary() -> Dict[str, Any]:
    """Get summary of all gaps.

    Returns:
        Dict with gap statistics
    """
    result = find_all_gaps()
    return {
        "total_gaps": len(result.gaps),
        "critical": result.critical_count,
        "high": result.high_count,
        "medium": result.medium_count,
        "low": result.low_count,
        "by_type": result.gaps_by_type,
        "overall_completeness": result.overall_completeness,
    }
