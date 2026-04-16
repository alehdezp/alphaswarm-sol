"""Coverage analysis for VulnDocs knowledge system.

Analyzes how well vulnerability knowledge covers the threat model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml

from alphaswarm_sol.vulndocs.storage.retrieval import KnowledgeRetriever, RetrievalDepth
from alphaswarm_sol.vulndocs.storage.knowledge_store import KnowledgeStore


# Threat model categories per PHILOSOPHY.md
THREAT_MODEL_CATEGORIES = {
    "reentrancy": {
        "display": "Reentrancy",
        "subcategories": [
            "classic",
            "cross-function",
            "cross-contract",
            "read-only",
        ],
        "patterns": ["reentrancy-001", "reentrancy-002", "reentrancy-003"],
        "critical": True,
    },
    "access-control": {
        "display": "Access Control",
        "subcategories": [
            "missing",
            "permissive",
            "tx-origin",
            "initialization",
        ],
        "patterns": ["auth-001", "auth-002", "auth-003"],
        "critical": True,
    },
    "oracle": {
        "display": "Oracle Manipulation",
        "subcategories": [
            "staleness",
            "manipulation",
            "flash-loan",
            "twap",
        ],
        "patterns": ["oracle-001", "oracle-002"],
        "critical": True,
    },
    "mev": {
        "display": "MEV & Ordering",
        "subcategories": [
            "sandwich",
            "frontrun",
            "backrun",
            "slippage",
            "deadline",
        ],
        "patterns": ["mev-001", "mev-002"],
        "critical": False,
    },
    "governance": {
        "display": "Governance Capture",
        "subcategories": [
            "timelock-bypass",
            "voting-power",
            "proposal-griefing",
        ],
        "patterns": ["gov-001"],
        "critical": False,
    },
    "upgradeability": {
        "display": "Upgradeability Abuse",
        "subcategories": [
            "proxy-mismatch",
            "initializer",
            "storage-collision",
            "selfdestruct",
        ],
        "patterns": ["upgrade-001", "upgrade-002"],
        "critical": True,
    },
    "tokenomics": {
        "display": "Tokenomics Flaws",
        "subcategories": [
            "inflation",
            "fee-manipulation",
            "rounding",
            "supply-limit",
        ],
        "patterns": ["token-001", "token-002"],
        "critical": False,
    },
    "dos": {
        "display": "Denial of Service",
        "subcategories": [
            "unbounded-loop",
            "gas-griefing",
            "block-dependence",
            "revert-bomb",
        ],
        "patterns": ["dos-001", "dos-002", "dos-003"],
        "critical": False,
    },
}


class CoverageLevel(Enum):
    """Coverage level for a category or subcategory."""

    FULL = "full"  # All required sections present
    PARTIAL = "partial"  # Some sections missing
    MINIMAL = "minimal"  # Only basic info
    NONE = "none"  # No coverage


@dataclass
class PatternMapping:
    """Mapping between a pattern and knowledge documents."""

    pattern_id: str
    pattern_name: str
    category: str
    subcategory: Optional[str] = None

    # Linked knowledge
    linked_docs: List[str] = field(default_factory=list)
    has_detection_guide: bool = False
    has_testing_guide: bool = False
    has_exploit_refs: bool = False

    # Coverage assessment
    coverage_level: CoverageLevel = CoverageLevel.NONE
    missing_sections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "linked_docs": self.linked_docs,
            "has_detection_guide": self.has_detection_guide,
            "has_testing_guide": self.has_testing_guide,
            "has_exploit_refs": self.has_exploit_refs,
            "coverage_level": self.coverage_level.value,
            "missing_sections": self.missing_sections,
        }


@dataclass
class CategoryCoverage:
    """Coverage statistics for a vulnerability category."""

    category: str
    display_name: str
    is_critical: bool

    # Document counts
    total_docs: int = 0
    expected_subcategories: int = 0
    covered_subcategories: int = 0

    # Section coverage
    docs_with_detection: int = 0
    docs_with_testing: int = 0
    docs_with_exploits: int = 0
    docs_with_fixes: int = 0

    # Pattern coverage
    expected_patterns: int = 0
    linked_patterns: int = 0

    # Overall assessment
    coverage_level: CoverageLevel = CoverageLevel.NONE
    coverage_percent: float = 0.0

    # Gaps identified
    missing_subcategories: List[str] = field(default_factory=list)
    missing_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category,
            "display_name": self.display_name,
            "is_critical": self.is_critical,
            "total_docs": self.total_docs,
            "expected_subcategories": self.expected_subcategories,
            "covered_subcategories": self.covered_subcategories,
            "docs_with_detection": self.docs_with_detection,
            "docs_with_testing": self.docs_with_testing,
            "docs_with_exploits": self.docs_with_exploits,
            "docs_with_fixes": self.docs_with_fixes,
            "expected_patterns": self.expected_patterns,
            "linked_patterns": self.linked_patterns,
            "coverage_level": self.coverage_level.value,
            "coverage_percent": round(self.coverage_percent, 2),
            "missing_subcategories": self.missing_subcategories,
            "missing_patterns": self.missing_patterns,
        }


@dataclass
class CoverageGap:
    """Represents a gap in knowledge coverage."""

    gap_type: str  # "missing_category", "missing_subcategory", "missing_section"
    category: str
    subcategory: Optional[str] = None
    pattern_id: Optional[str] = None
    section: Optional[str] = None
    severity: str = "medium"  # "critical", "high", "medium", "low"
    description: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "gap_type": self.gap_type,
            "category": self.category,
            "subcategory": self.subcategory,
            "pattern_id": self.pattern_id,
            "section": self.section,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
        }


@dataclass
class CoverageReport:
    """Complete coverage analysis report."""

    # Summary statistics
    total_categories: int = 0
    covered_categories: int = 0
    total_documents: int = 0
    total_patterns: int = 0
    linked_patterns: int = 0

    # Category details
    categories: List[CategoryCoverage] = field(default_factory=list)

    # Pattern mappings
    patterns: List[PatternMapping] = field(default_factory=list)

    # Gaps identified
    gaps: List[CoverageGap] = field(default_factory=list)
    critical_gaps: int = 0

    # Overall assessment
    overall_coverage: float = 0.0
    threat_model_coverage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_categories": self.total_categories,
            "covered_categories": self.covered_categories,
            "total_documents": self.total_documents,
            "total_patterns": self.total_patterns,
            "linked_patterns": self.linked_patterns,
            "categories": [c.to_dict() for c in self.categories],
            "patterns": [p.to_dict() for p in self.patterns],
            "gaps": [g.to_dict() for g in self.gaps],
            "critical_gaps": self.critical_gaps,
            "overall_coverage": round(self.overall_coverage, 2),
            "threat_model_coverage": round(self.threat_model_coverage, 2),
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# VulnDocs Coverage Analysis Report",
            "",
            "## Summary",
            "",
            f"- **Total Categories:** {self.covered_categories}/{self.total_categories}",
            f"- **Total Documents:** {self.total_documents}",
            f"- **Pattern Coverage:** {self.linked_patterns}/{self.total_patterns}",
            f"- **Overall Coverage:** {self.overall_coverage:.1f}%",
            f"- **Threat Model Coverage:** {self.threat_model_coverage:.1f}%",
            f"- **Critical Gaps:** {self.critical_gaps}",
            "",
            "## Category Coverage",
            "",
            "| Category | Docs | Subcats | Patterns | Coverage |",
            "|----------|------|---------|----------|----------|",
        ]

        for cat in self.categories:
            level_emoji = {
                CoverageLevel.FULL: "🟢",
                CoverageLevel.PARTIAL: "🟡",
                CoverageLevel.MINIMAL: "🟠",
                CoverageLevel.NONE: "🔴",
            }.get(cat.coverage_level, "⚪")

            lines.append(
                f"| {cat.display_name} | {cat.total_docs} | "
                f"{cat.covered_subcategories}/{cat.expected_subcategories} | "
                f"{cat.linked_patterns}/{cat.expected_patterns} | "
                f"{level_emoji} {cat.coverage_percent:.0f}% |"
            )

        if self.gaps:
            lines.extend([
                "",
                "## Coverage Gaps",
                "",
            ])

            # Group by severity
            for severity in ["critical", "high", "medium", "low"]:
                severity_gaps = [g for g in self.gaps if g.severity == severity]
                if severity_gaps:
                    lines.append(f"### {severity.title()} Gaps")
                    lines.append("")
                    for gap in severity_gaps:
                        lines.append(f"- **{gap.gap_type}**: {gap.description}")
                        if gap.recommendation:
                            lines.append(f"  - *Recommendation:* {gap.recommendation}")
                    lines.append("")

        return "\n".join(lines)


class CoverageAnalyzer:
    """Analyzes coverage of vulnerability knowledge.

    Example:
        analyzer = CoverageAnalyzer()
        report = analyzer.analyze()

        # Check critical gaps
        if report.critical_gaps > 0:
            print(f"Warning: {report.critical_gaps} critical gaps found")

        # Get specific category coverage
        reentrancy = analyzer.get_category_coverage("reentrancy")
    """

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        patterns_path: Optional[Path] = None,
    ):
        """Initialize analyzer.

        Args:
            retriever: Knowledge retriever for accessing docs
            patterns_path: Path to pattern YAML files
        """
        self.retriever = retriever or KnowledgeRetriever()
        self.patterns_path = patterns_path

    def analyze(self) -> CoverageReport:
        """Perform full coverage analysis.

        Returns:
            CoverageReport with analysis results
        """
        report = CoverageReport()

        # Analyze each threat model category
        for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
            cat_coverage = self._analyze_category(cat_id, cat_info)
            report.categories.append(cat_coverage)

            # Count totals
            report.total_documents += cat_coverage.total_docs
            if cat_coverage.coverage_level != CoverageLevel.NONE:
                report.covered_categories += 1

            # Track patterns
            report.total_patterns += cat_coverage.expected_patterns
            report.linked_patterns += cat_coverage.linked_patterns

            # Identify gaps
            for gap in self._identify_category_gaps(cat_id, cat_info, cat_coverage):
                report.gaps.append(gap)
                if gap.severity == "critical":
                    report.critical_gaps += 1

        # Calculate totals
        report.total_categories = len(THREAT_MODEL_CATEGORIES)

        # Calculate overall coverage
        if report.total_categories > 0:
            report.overall_coverage = (
                sum(c.coverage_percent for c in report.categories)
                / report.total_categories
            )

        # Calculate threat model coverage (critical categories weighted higher)
        critical_cats = [c for c in report.categories if c.is_critical]
        other_cats = [c for c in report.categories if not c.is_critical]

        if critical_cats or other_cats:
            critical_weight = 0.7
            other_weight = 0.3

            critical_coverage = (
                sum(c.coverage_percent for c in critical_cats) / len(critical_cats)
                if critical_cats
                else 0
            )
            other_coverage = (
                sum(c.coverage_percent for c in other_cats) / len(other_cats)
                if other_cats
                else 0
            )

            report.threat_model_coverage = (
                critical_coverage * critical_weight + other_coverage * other_weight
            )

        return report

    def _analyze_category(
        self,
        cat_id: str,
        cat_info: Dict[str, Any],
    ) -> CategoryCoverage:
        """Analyze coverage for a single category."""
        coverage = CategoryCoverage(
            category=cat_id,
            display_name=cat_info["display"],
            is_critical=cat_info.get("critical", False),
            expected_subcategories=len(cat_info.get("subcategories", [])),
            expected_patterns=len(cat_info.get("patterns", [])),
        )

        # Get documents for this category
        result = self.retriever.get_by_category(
            category=cat_id,
            depth=RetrievalDepth.MINIMAL,
            max_results=50,
        )

        coverage.total_docs = len(result.documents)

        # Analyze document coverage
        covered_subcats: Set[str] = set()
        linked_patterns: Set[str] = set()

        for doc in result.documents:
            # Track subcategory coverage
            covered_subcats.add(doc.subcategory)

            # Track section coverage
            if doc.detection.graph_signals:
                coverage.docs_with_detection += 1
            if doc.exploitation.attack_steps:
                coverage.docs_with_testing += 1
            if doc.examples.real_exploits:
                coverage.docs_with_exploits += 1
            if doc.mitigation.primary_fix:
                coverage.docs_with_fixes += 1

            # Track pattern linkage
            if doc.pattern_linkage.pattern_ids:
                linked_patterns.update(doc.pattern_linkage.pattern_ids)

        coverage.covered_subcategories = len(covered_subcats)
        coverage.linked_patterns = len(linked_patterns)

        # Identify missing subcategories
        expected_subcats = set(cat_info.get("subcategories", []))
        coverage.missing_subcategories = list(expected_subcats - covered_subcats)

        # Identify missing patterns
        expected_patterns = set(cat_info.get("patterns", []))
        coverage.missing_patterns = list(expected_patterns - linked_patterns)

        # Calculate coverage percentage
        if coverage.expected_subcategories > 0:
            subcat_coverage = (
                coverage.covered_subcategories / coverage.expected_subcategories
            )
        else:
            subcat_coverage = 1.0 if coverage.total_docs > 0 else 0.0

        if coverage.expected_patterns > 0:
            pattern_coverage = coverage.linked_patterns / coverage.expected_patterns
        else:
            pattern_coverage = 1.0 if coverage.linked_patterns > 0 else 0.0

        # Section coverage
        if coverage.total_docs > 0:
            section_coverage = (
                (coverage.docs_with_detection > 0) * 0.25
                + (coverage.docs_with_testing > 0) * 0.25
                + (coverage.docs_with_exploits > 0) * 0.25
                + (coverage.docs_with_fixes > 0) * 0.25
            )
        else:
            section_coverage = 0.0

        # Overall coverage for this category
        coverage.coverage_percent = (
            subcat_coverage * 40 + pattern_coverage * 30 + section_coverage * 30
        )

        # Determine coverage level
        if coverage.coverage_percent >= 80:
            coverage.coverage_level = CoverageLevel.FULL
        elif coverage.coverage_percent >= 50:
            coverage.coverage_level = CoverageLevel.PARTIAL
        elif coverage.coverage_percent >= 20:
            coverage.coverage_level = CoverageLevel.MINIMAL
        else:
            coverage.coverage_level = CoverageLevel.NONE

        return coverage

    def _identify_category_gaps(
        self,
        cat_id: str,
        cat_info: Dict[str, Any],
        coverage: CategoryCoverage,
    ) -> List[CoverageGap]:
        """Identify gaps in a category's coverage."""
        gaps = []

        # Critical vs non-critical severity
        base_severity = "critical" if coverage.is_critical else "high"

        # Missing category entirely
        if coverage.coverage_level == CoverageLevel.NONE:
            gaps.append(
                CoverageGap(
                    gap_type="missing_category",
                    category=cat_id,
                    severity=base_severity,
                    description=f"No documentation for {coverage.display_name}",
                    recommendation=f"Create base documentation for {coverage.display_name} vulnerabilities",
                )
            )
            return gaps  # Don't list subcategory gaps if entire category is missing

        # Missing subcategories
        for subcat in coverage.missing_subcategories:
            gaps.append(
                CoverageGap(
                    gap_type="missing_subcategory",
                    category=cat_id,
                    subcategory=subcat,
                    severity="high" if coverage.is_critical else "medium",
                    description=f"Missing docs for {cat_id}/{subcat}",
                    recommendation=f"Add knowledge document for {subcat} variant",
                )
            )

        # Missing patterns
        for pattern_id in coverage.missing_patterns:
            gaps.append(
                CoverageGap(
                    gap_type="missing_pattern_link",
                    category=cat_id,
                    pattern_id=pattern_id,
                    severity="high" if coverage.is_critical else "medium",
                    description=f"Pattern {pattern_id} not linked to knowledge docs",
                    recommendation=f"Link {pattern_id} to relevant knowledge documents",
                )
            )

        # Missing sections
        if coverage.total_docs > 0:
            if coverage.docs_with_detection == 0:
                gaps.append(
                    CoverageGap(
                        gap_type="missing_section",
                        category=cat_id,
                        section="detection",
                        severity="high",
                        description=f"No detection guidance for {coverage.display_name}",
                        recommendation="Add graph signals and detection checklist",
                    )
                )

            if coverage.docs_with_testing == 0:
                gaps.append(
                    CoverageGap(
                        gap_type="missing_section",
                        category=cat_id,
                        section="testing",
                        severity="medium",
                        description=f"No testing guidance for {coverage.display_name}",
                        recommendation="Add attack steps and test prerequisites",
                    )
                )

        return gaps

    def get_category_coverage(self, category: str) -> Optional[CategoryCoverage]:
        """Get coverage for a specific category.

        Args:
            category: Category ID

        Returns:
            CategoryCoverage or None if not in threat model
        """
        if category not in THREAT_MODEL_CATEGORIES:
            return None

        cat_info = THREAT_MODEL_CATEGORIES[category]
        return self._analyze_category(category, cat_info)

    def get_pattern_mapping(self, pattern_id: str) -> Optional[PatternMapping]:
        """Get knowledge mapping for a pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            PatternMapping showing linked knowledge
        """
        # Find pattern in threat model
        category = None
        pattern_name = pattern_id

        for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
            if pattern_id in cat_info.get("patterns", []):
                category = cat_id
                break

        if not category:
            return None

        mapping = PatternMapping(
            pattern_id=pattern_id,
            pattern_name=pattern_name,
            category=category,
        )

        # Find linked documents
        result = self.retriever.get_by_pattern(
            pattern_ids=[pattern_id],
            depth=RetrievalDepth.MINIMAL,
        )

        for doc in result.documents:
            mapping.linked_docs.append(doc.id)
            if doc.detection.graph_signals:
                mapping.has_detection_guide = True
            if doc.exploitation.attack_steps:
                mapping.has_testing_guide = True
            if doc.examples.real_exploits:
                mapping.has_exploit_refs = True

        # Determine coverage level
        if mapping.linked_docs:
            if mapping.has_detection_guide and mapping.has_testing_guide:
                mapping.coverage_level = CoverageLevel.FULL
            elif mapping.has_detection_guide or mapping.has_testing_guide:
                mapping.coverage_level = CoverageLevel.PARTIAL
            else:
                mapping.coverage_level = CoverageLevel.MINIMAL
        else:
            mapping.coverage_level = CoverageLevel.NONE

        # Identify missing sections
        if not mapping.has_detection_guide:
            mapping.missing_sections.append("detection")
        if not mapping.has_testing_guide:
            mapping.missing_sections.append("testing")
        if not mapping.has_exploit_refs:
            mapping.missing_sections.append("exploits")

        return mapping

    def get_gaps_by_severity(
        self,
        severity: str,
    ) -> List[CoverageGap]:
        """Get all gaps of a specific severity.

        Args:
            severity: Gap severity ("critical", "high", "medium", "low")

        Returns:
            List of gaps matching severity
        """
        report = self.analyze()
        return [g for g in report.gaps if g.severity == severity]

    def get_uncovered_patterns(self) -> List[str]:
        """Get list of patterns without knowledge documentation.

        Returns:
            List of pattern IDs without linked docs
        """
        uncovered = []

        for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
            for pattern_id in cat_info.get("patterns", []):
                mapping = self.get_pattern_mapping(pattern_id)
                if mapping and mapping.coverage_level == CoverageLevel.NONE:
                    uncovered.append(pattern_id)

        return uncovered


# =============================================================================
# Convenience Functions
# =============================================================================


def analyze_coverage() -> CoverageReport:
    """Run coverage analysis using default analyzer.

    Returns:
        CoverageReport with analysis results
    """
    analyzer = CoverageAnalyzer()
    return analyzer.analyze()


def get_coverage_summary() -> Dict[str, Any]:
    """Get a summary of coverage statistics.

    Returns:
        Dict with key coverage metrics
    """
    report = analyze_coverage()
    return {
        "overall_coverage": report.overall_coverage,
        "threat_model_coverage": report.threat_model_coverage,
        "categories_covered": f"{report.covered_categories}/{report.total_categories}",
        "patterns_linked": f"{report.linked_patterns}/{report.total_patterns}",
        "critical_gaps": report.critical_gaps,
        "total_gaps": len(report.gaps),
    }
