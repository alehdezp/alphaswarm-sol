"""Tests for VulnDocs coverage analysis module.

Tests coverage analyzer, gap finder, and report generator.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from alphaswarm_sol.vulndocs.knowledge_doc import (
    VulnKnowledgeDoc,
    Severity,
    DetectionSection,
    ExploitationSection,
    MitigationSection,
    ExamplesSection,
    PatternLinkage,
    PatternLinkageType,
    RealExploitRef,
)
from alphaswarm_sol.vulndocs.analysis.coverage import (
    THREAT_MODEL_CATEGORIES,
    CoverageLevel,
    PatternMapping,
    CategoryCoverage,
    CoverageGap,
    CoverageReport,
    CoverageAnalyzer,
    analyze_coverage,
    get_coverage_summary,
)
from alphaswarm_sol.vulndocs.analysis.gaps import (
    GapType,
    GapSeverity,
    KnowledgeGap,
    GapAnalysisResult,
    GapFinder,
    find_all_gaps,
    get_priority_gaps,
    get_gap_summary,
)
from alphaswarm_sol.vulndocs.analysis.reports import (
    ReportFormat,
    CoverageMatrixCell,
    CoverageMatrix,
    ReportGenerator,
    generate_coverage_report,
    generate_coverage_matrix,
    get_toon_summary,
)
from alphaswarm_sol.vulndocs.storage.retrieval import RetrievalResult


def create_test_doc(
    doc_id: str = "reentrancy/classic/test-doc",
    category: str = "reentrancy",
    subcategory: str = "classic",
    with_detection: bool = True,
    with_exploitation: bool = True,
    with_mitigation: bool = True,
    with_examples: bool = True,
    with_pattern_link: bool = True,
) -> VulnKnowledgeDoc:
    """Create a test document with configurable sections."""
    doc = VulnKnowledgeDoc(
        id=doc_id,
        name="Test Document",
        category=category,
        subcategory=subcategory,
        severity=Severity.HIGH,
        detection=DetectionSection(
            graph_signals=["state_write_after_external_call"] if with_detection else [],
            checklist=["Check CEI pattern"] if with_detection else [],
        ),
        exploitation=ExploitationSection(
            attack_vector="Recursive call" if with_exploitation else "",
            prerequisites=["External call"] if with_exploitation else [],
            attack_steps=["Deploy attacker", "Call withdraw"] if with_exploitation else [],
        ),
        mitigation=MitigationSection(
            primary_fix="Use CEI pattern" if with_mitigation else "",
            alternative_fixes=["Reentrancy guard"] if with_mitigation else [],
            safe_pattern="CEI" if with_mitigation else "",
            how_to_verify=["Check state update order"] if with_mitigation else [],
        ),
        examples=ExamplesSection(
            vulnerable_code="balances -= amount; call()" if with_examples else "",
            fixed_code="balances -= amount; call()" if with_examples else "",
            real_exploits=[
                RealExploitRef(name="TheDAO", brief="Classic reentrancy")
            ] if with_examples else [],
        ),
        pattern_linkage=PatternLinkage(
            linkage_type=PatternLinkageType.EXACT_MATCH if with_pattern_link else PatternLinkageType.THEORETICAL,
            pattern_ids=["reentrancy-001"] if with_pattern_link else [],
        ),
    )
    return doc


class MockRetriever:
    """Mock retriever for testing."""

    def __init__(self, docs_by_category: dict = None):
        self.docs_by_category = docs_by_category or {}

    def get_by_category(self, category: str, depth=None, max_results: int = 50):
        docs = self.docs_by_category.get(category, [])
        return RetrievalResult(documents=docs)

    def get_by_pattern(self, pattern_ids: list, depth=None):
        # Return docs that link to any of the pattern_ids
        matching_docs = []
        for docs in self.docs_by_category.values():
            for doc in docs:
                if any(p in doc.pattern_linkage.pattern_ids for p in pattern_ids):
                    matching_docs.append(doc)
        return RetrievalResult(documents=matching_docs)


# =============================================================================
# Coverage Module Tests
# =============================================================================


class TestThreatModelCategories(unittest.TestCase):
    """Tests for threat model category definitions."""

    def test_all_categories_present(self):
        """All expected categories are defined."""
        expected = {
            "reentrancy", "access-control", "oracle", "mev",
            "governance", "upgradeability", "tokenomics", "dos"
        }
        self.assertEqual(set(THREAT_MODEL_CATEGORIES.keys()), expected)

    def test_categories_have_required_fields(self):
        """Each category has required fields."""
        for cat_id, info in THREAT_MODEL_CATEGORIES.items():
            self.assertIn("display", info, f"{cat_id} missing display")
            self.assertIn("subcategories", info, f"{cat_id} missing subcategories")
            self.assertIn("patterns", info, f"{cat_id} missing patterns")
            self.assertIn("critical", info, f"{cat_id} missing critical")

    def test_critical_categories_marked(self):
        """Critical categories are properly marked."""
        critical_cats = {"reentrancy", "access-control", "oracle", "upgradeability"}
        for cat_id, info in THREAT_MODEL_CATEGORIES.items():
            if cat_id in critical_cats:
                self.assertTrue(info["critical"], f"{cat_id} should be critical")
            else:
                self.assertFalse(info["critical"], f"{cat_id} should not be critical")


class TestCoverageLevel(unittest.TestCase):
    """Tests for CoverageLevel enum."""

    def test_coverage_levels(self):
        """All coverage levels exist."""
        self.assertEqual(CoverageLevel.FULL.value, "full")
        self.assertEqual(CoverageLevel.PARTIAL.value, "partial")
        self.assertEqual(CoverageLevel.MINIMAL.value, "minimal")
        self.assertEqual(CoverageLevel.NONE.value, "none")


class TestPatternMapping(unittest.TestCase):
    """Tests for PatternMapping dataclass."""

    def test_pattern_mapping_creation(self):
        """PatternMapping can be created."""
        mapping = PatternMapping(
            pattern_id="reentrancy-001",
            pattern_name="Classic Reentrancy",
            category="reentrancy",
            subcategory="classic",
        )
        self.assertEqual(mapping.pattern_id, "reentrancy-001")
        self.assertEqual(mapping.coverage_level, CoverageLevel.NONE)
        self.assertEqual(mapping.linked_docs, [])

    def test_pattern_mapping_to_dict(self):
        """PatternMapping serializes correctly."""
        mapping = PatternMapping(
            pattern_id="reentrancy-001",
            pattern_name="Classic Reentrancy",
            category="reentrancy",
            linked_docs=["doc1", "doc2"],
            has_detection_guide=True,
            coverage_level=CoverageLevel.PARTIAL,
        )
        data = mapping.to_dict()
        self.assertEqual(data["pattern_id"], "reentrancy-001")
        self.assertEqual(data["linked_docs"], ["doc1", "doc2"])
        self.assertEqual(data["coverage_level"], "partial")


class TestCategoryCoverage(unittest.TestCase):
    """Tests for CategoryCoverage dataclass."""

    def test_category_coverage_creation(self):
        """CategoryCoverage can be created."""
        coverage = CategoryCoverage(
            category="reentrancy",
            display_name="Reentrancy",
            is_critical=True,
            total_docs=5,
            expected_subcategories=4,
            covered_subcategories=3,
        )
        self.assertEqual(coverage.category, "reentrancy")
        self.assertTrue(coverage.is_critical)
        self.assertEqual(coverage.total_docs, 5)

    def test_category_coverage_to_dict(self):
        """CategoryCoverage serializes correctly."""
        coverage = CategoryCoverage(
            category="reentrancy",
            display_name="Reentrancy",
            is_critical=True,
            coverage_percent=75.5,
            coverage_level=CoverageLevel.PARTIAL,
        )
        data = coverage.to_dict()
        self.assertEqual(data["category"], "reentrancy")
        self.assertEqual(data["coverage_percent"], 75.5)
        self.assertEqual(data["coverage_level"], "partial")


class TestCoverageReport(unittest.TestCase):
    """Tests for CoverageReport dataclass."""

    def test_coverage_report_creation(self):
        """CoverageReport can be created."""
        report = CoverageReport(
            total_categories=8,
            covered_categories=6,
            overall_coverage=75.0,
        )
        self.assertEqual(report.total_categories, 8)
        self.assertEqual(report.covered_categories, 6)
        self.assertEqual(report.overall_coverage, 75.0)

    def test_coverage_report_to_dict(self):
        """CoverageReport serializes correctly."""
        report = CoverageReport(
            total_categories=8,
            covered_categories=6,
            categories=[
                CategoryCoverage(
                    category="reentrancy",
                    display_name="Reentrancy",
                    is_critical=True,
                    coverage_percent=80.0,
                )
            ],
        )
        data = report.to_dict()
        self.assertEqual(data["total_categories"], 8)
        self.assertEqual(len(data["categories"]), 1)

    def test_coverage_report_to_markdown(self):
        """CoverageReport generates markdown."""
        report = CoverageReport(
            total_categories=8,
            covered_categories=6,
            overall_coverage=75.0,
            threat_model_coverage=80.0,
            categories=[
                CategoryCoverage(
                    category="reentrancy",
                    display_name="Reentrancy",
                    is_critical=True,
                    total_docs=5,
                    expected_subcategories=4,
                    covered_subcategories=3,
                    expected_patterns=3,
                    linked_patterns=2,
                    coverage_percent=75.0,
                    coverage_level=CoverageLevel.PARTIAL,
                )
            ],
        )
        md = report.to_markdown()
        self.assertIn("Coverage Analysis Report", md)
        self.assertIn("75.0%", md)
        self.assertIn("Reentrancy", md)


class TestCoverageAnalyzer(unittest.TestCase):
    """Tests for CoverageAnalyzer class."""

    def test_analyzer_creation(self):
        """Analyzer can be created."""
        analyzer = CoverageAnalyzer()
        self.assertIsNotNone(analyzer.retriever)

    def test_analyze_empty_knowledge_base(self):
        """Analyze works with empty knowledge base."""
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        report = analyzer.analyze()

        self.assertEqual(report.total_categories, 8)
        self.assertEqual(report.covered_categories, 0)
        self.assertEqual(report.total_documents, 0)

    def test_analyze_with_documents(self):
        """Analyze works with documents."""
        doc = create_test_doc()
        mock_retriever = MockRetriever({"reentrancy": [doc]})
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        report = analyzer.analyze()

        self.assertEqual(report.total_documents, 1)
        self.assertGreater(report.covered_categories, 0)

    def test_analyze_category_coverage(self):
        """Category coverage is calculated correctly."""
        docs = [
            create_test_doc(doc_id="reentrancy/classic/doc1", subcategory="classic"),
            create_test_doc(doc_id="reentrancy/cross-function/doc2", subcategory="cross-function"),
        ]
        mock_retriever = MockRetriever({"reentrancy": docs})
        analyzer = CoverageAnalyzer(retriever=mock_retriever)

        coverage = analyzer.get_category_coverage("reentrancy")
        self.assertIsNotNone(coverage)
        self.assertEqual(coverage.total_docs, 2)
        self.assertEqual(coverage.covered_subcategories, 2)

    def test_analyze_missing_category(self):
        """Missing category returns None."""
        analyzer = CoverageAnalyzer(retriever=MockRetriever())
        coverage = analyzer.get_category_coverage("nonexistent")
        self.assertIsNone(coverage)

    def test_pattern_mapping(self):
        """Pattern mapping works correctly."""
        doc = create_test_doc()
        mock_retriever = MockRetriever({"reentrancy": [doc]})
        analyzer = CoverageAnalyzer(retriever=mock_retriever)

        mapping = analyzer.get_pattern_mapping("reentrancy-001")
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.pattern_id, "reentrancy-001")
        self.assertEqual(mapping.category, "reentrancy")
        self.assertIn("reentrancy/classic/test-doc", mapping.linked_docs)
        self.assertTrue(mapping.has_detection_guide)

    def test_pattern_mapping_unknown_pattern(self):
        """Unknown pattern returns None."""
        analyzer = CoverageAnalyzer(retriever=MockRetriever())
        mapping = analyzer.get_pattern_mapping("unknown-pattern")
        self.assertIsNone(mapping)

    def test_uncovered_patterns(self):
        """Uncovered patterns are detected."""
        # No docs linked to patterns
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)

        uncovered = analyzer.get_uncovered_patterns()
        # All patterns from threat model should be uncovered
        self.assertGreater(len(uncovered), 0)
        self.assertIn("reentrancy-001", uncovered)

    def test_gaps_by_severity(self):
        """Gaps can be filtered by severity."""
        mock_retriever = MockRetriever()  # Empty = all gaps
        analyzer = CoverageAnalyzer(retriever=mock_retriever)

        critical_gaps = analyzer.get_gaps_by_severity("critical")
        self.assertGreater(len(critical_gaps), 0)


class TestCoverageConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions."""

    @patch('alphaswarm_sol.vulndocs.analysis.coverage.CoverageAnalyzer')
    def test_analyze_coverage(self, mock_analyzer_class):
        """analyze_coverage convenience function works."""
        mock_report = CoverageReport(overall_coverage=75.0)
        mock_analyzer_class.return_value.analyze.return_value = mock_report

        report = analyze_coverage()
        self.assertEqual(report.overall_coverage, 75.0)

    @patch('alphaswarm_sol.vulndocs.analysis.coverage.analyze_coverage')
    def test_get_coverage_summary(self, mock_analyze):
        """get_coverage_summary convenience function works."""
        mock_analyze.return_value = CoverageReport(
            overall_coverage=75.0,
            threat_model_coverage=80.0,
            covered_categories=6,
            total_categories=8,
            linked_patterns=10,
            total_patterns=15,
            critical_gaps=2,
            gaps=[],
        )

        summary = get_coverage_summary()
        self.assertEqual(summary["overall_coverage"], 75.0)
        self.assertEqual(summary["categories_covered"], "6/8")
        self.assertEqual(summary["critical_gaps"], 2)


# =============================================================================
# Gap Module Tests
# =============================================================================


class TestGapType(unittest.TestCase):
    """Tests for GapType enum."""

    def test_gap_types_exist(self):
        """All expected gap types exist."""
        self.assertEqual(GapType.MISSING_CATEGORY.value, "missing_category")
        self.assertEqual(GapType.MISSING_SUBCATEGORY.value, "missing_subcategory")
        self.assertEqual(GapType.WEAK_DETECTION.value, "weak_detection")
        self.assertEqual(GapType.UNLINKED_PATTERN.value, "unlinked_pattern")


class TestGapSeverity(unittest.TestCase):
    """Tests for GapSeverity enum."""

    def test_gap_severities_exist(self):
        """All severity levels exist."""
        self.assertEqual(GapSeverity.CRITICAL.value, "critical")
        self.assertEqual(GapSeverity.HIGH.value, "high")
        self.assertEqual(GapSeverity.MEDIUM.value, "medium")
        self.assertEqual(GapSeverity.LOW.value, "low")


class TestKnowledgeGap(unittest.TestCase):
    """Tests for KnowledgeGap dataclass."""

    def test_knowledge_gap_creation(self):
        """KnowledgeGap can be created."""
        gap = KnowledgeGap(
            gap_type=GapType.MISSING_CATEGORY,
            severity=GapSeverity.CRITICAL,
            category="reentrancy",
            title="Missing reentrancy docs",
            description="No documentation",
            recommendation="Create docs",
        )
        self.assertEqual(gap.gap_type, GapType.MISSING_CATEGORY)
        self.assertEqual(gap.severity, GapSeverity.CRITICAL)
        self.assertEqual(gap.priority, 5)  # Default

    def test_knowledge_gap_to_dict(self):
        """KnowledgeGap serializes correctly."""
        gap = KnowledgeGap(
            gap_type=GapType.WEAK_DETECTION,
            severity=GapSeverity.HIGH,
            category="oracle",
            doc_id="oracle/staleness/doc1",
            title="Weak detection",
        )
        data = gap.to_dict()
        self.assertEqual(data["gap_type"], "weak_detection")
        self.assertEqual(data["severity"], "high")
        self.assertEqual(data["doc_id"], "oracle/staleness/doc1")

    def test_knowledge_gap_from_dict(self):
        """KnowledgeGap deserializes correctly."""
        data = {
            "gap_type": "missing_subcategory",
            "severity": "medium",
            "category": "mev",
            "subcategory": "sandwich",
            "title": "Missing sandwich docs",
        }
        gap = KnowledgeGap.from_dict(data)
        self.assertEqual(gap.gap_type, GapType.MISSING_SUBCATEGORY)
        self.assertEqual(gap.severity, GapSeverity.MEDIUM)
        self.assertEqual(gap.subcategory, "sandwich")


class TestGapAnalysisResult(unittest.TestCase):
    """Tests for GapAnalysisResult dataclass."""

    def test_gap_result_creation(self):
        """GapAnalysisResult can be created."""
        result = GapAnalysisResult(
            gaps=[],
            critical_count=0,
            overall_completeness=75.0,
        )
        self.assertEqual(result.critical_count, 0)
        self.assertEqual(result.overall_completeness, 75.0)

    def test_gap_result_to_dict(self):
        """GapAnalysisResult serializes correctly."""
        result = GapAnalysisResult(
            gaps=[
                KnowledgeGap(
                    gap_type=GapType.MISSING_CATEGORY,
                    severity=GapSeverity.CRITICAL,
                    category="test",
                )
            ],
            critical_count=1,
            detection_completeness=50.0,
        )
        data = result.to_dict()
        self.assertEqual(len(data["gaps"]), 1)
        self.assertEqual(data["critical_count"], 1)
        self.assertEqual(data["detection_completeness"], 50.0)


class TestGapFinder(unittest.TestCase):
    """Tests for GapFinder class."""

    def test_finder_creation(self):
        """GapFinder can be created."""
        finder = GapFinder()
        self.assertIsNotNone(finder.retriever)

    def test_find_all_gaps_empty(self):
        """Find gaps in empty knowledge base."""
        mock_retriever = MockRetriever()
        finder = GapFinder(retriever=mock_retriever)
        result = finder.find_all_gaps()

        # Should find missing category gaps for all categories
        self.assertGreater(len(result.gaps), 0)
        self.assertGreater(result.critical_count, 0)

    def test_find_category_gaps(self):
        """Category gaps are found."""
        mock_retriever = MockRetriever()
        finder = GapFinder(retriever=mock_retriever)
        result = finder.find_all_gaps()

        # Check for missing category gaps
        category_gaps = [g for g in result.gaps if g.gap_type == GapType.MISSING_CATEGORY]
        self.assertEqual(len(category_gaps), 8)  # All 8 categories

    def test_find_quality_gaps(self):
        """Document quality gaps are found."""
        # Doc with missing detection
        doc = create_test_doc(with_detection=False)
        mock_retriever = MockRetriever({"reentrancy": [doc]})
        finder = GapFinder(retriever=mock_retriever)
        result = finder.find_all_gaps()

        # Should find weak detection gap
        detection_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_DETECTION]
        self.assertGreater(len(detection_gaps), 0)

    def test_find_alignment_gaps(self):
        """Pattern alignment gaps are found."""
        # Doc without pattern link
        doc = create_test_doc(with_pattern_link=False)
        mock_retriever = MockRetriever({"reentrancy": [doc]})
        finder = GapFinder(retriever=mock_retriever)
        result = finder.find_all_gaps()

        # Should find orphan document gap
        orphan_gaps = [g for g in result.gaps if g.gap_type == GapType.ORPHAN_DOCUMENT]
        self.assertGreater(len(orphan_gaps), 0)

    def test_priority_queue_ordering(self):
        """Priority queue orders gaps correctly."""
        mock_retriever = MockRetriever()
        finder = GapFinder(retriever=mock_retriever)
        result = finder.find_all_gaps()

        # Priority queue should have critical gaps first
        if len(result.priority_queue) > 1:
            first_gap = result.priority_queue[0]
            self.assertIn(first_gap.severity, [GapSeverity.CRITICAL, GapSeverity.HIGH])

    def test_find_detection_gaps(self):
        """Detection gaps filter works."""
        doc = create_test_doc(with_detection=False)
        mock_retriever = MockRetriever({"reentrancy": [doc]})
        finder = GapFinder(retriever=mock_retriever)

        detection_gaps = finder.find_detection_gaps()
        self.assertGreater(len(detection_gaps), 0)
        for gap in detection_gaps:
            self.assertIn(
                gap.gap_type,
                [GapType.MISSING_DETECTION, GapType.WEAK_DETECTION]
            )

    def test_find_critical_gaps(self):
        """Critical gaps filter works."""
        mock_retriever = MockRetriever()
        finder = GapFinder(retriever=mock_retriever)

        critical_gaps = finder.find_critical_gaps()
        for gap in critical_gaps:
            self.assertEqual(gap.severity, GapSeverity.CRITICAL)

    def test_find_gaps_for_category(self):
        """Category filter works."""
        mock_retriever = MockRetriever()
        finder = GapFinder(retriever=mock_retriever)

        reentrancy_gaps = finder.find_gaps_for_category("reentrancy")
        for gap in reentrancy_gaps:
            self.assertEqual(gap.category, "reentrancy")

    def test_find_gaps_for_document(self):
        """Document filter works."""
        doc = create_test_doc(
            doc_id="reentrancy/classic/target-doc",
            with_detection=False,
            with_mitigation=False,
        )
        mock_retriever = MockRetriever({"reentrancy": [doc]})
        finder = GapFinder(retriever=mock_retriever)

        doc_gaps = finder.find_gaps_for_document("reentrancy/classic/target-doc")
        self.assertGreater(len(doc_gaps), 0)
        for gap in doc_gaps:
            self.assertEqual(gap.doc_id, "reentrancy/classic/target-doc")


class TestGapConvenienceFunctions(unittest.TestCase):
    """Tests for gap convenience functions."""

    @patch('alphaswarm_sol.vulndocs.analysis.gaps.GapFinder')
    def test_find_all_gaps(self, mock_finder_class):
        """find_all_gaps convenience function works."""
        mock_result = GapAnalysisResult(gaps=[], critical_count=0)
        mock_finder_class.return_value.find_all_gaps.return_value = mock_result

        result = find_all_gaps()
        self.assertEqual(result.critical_count, 0)

    @patch('alphaswarm_sol.vulndocs.analysis.gaps.find_all_gaps')
    def test_get_priority_gaps(self, mock_find_all):
        """get_priority_gaps convenience function works."""
        mock_find_all.return_value = GapAnalysisResult(
            priority_queue=[
                KnowledgeGap(gap_type=GapType.MISSING_CATEGORY, severity=GapSeverity.CRITICAL, category="test")
            ]
        )

        gaps = get_priority_gaps(limit=5)
        self.assertEqual(len(gaps), 1)

    @patch('alphaswarm_sol.vulndocs.analysis.gaps.find_all_gaps')
    def test_get_gap_summary(self, mock_find_all):
        """get_gap_summary convenience function works."""
        mock_find_all.return_value = GapAnalysisResult(
            gaps=[],
            critical_count=2,
            high_count=3,
            medium_count=5,
            low_count=1,
            overall_completeness=60.0,
        )

        summary = get_gap_summary()
        self.assertEqual(summary["critical"], 2)
        self.assertEqual(summary["overall_completeness"], 60.0)


# =============================================================================
# Report Module Tests
# =============================================================================


class TestReportFormat(unittest.TestCase):
    """Tests for ReportFormat enum."""

    def test_report_formats_exist(self):
        """All report formats exist."""
        self.assertEqual(ReportFormat.MARKDOWN.value, "markdown")
        self.assertEqual(ReportFormat.JSON.value, "json")
        self.assertEqual(ReportFormat.TOON.value, "toon")
        self.assertEqual(ReportFormat.HTML.value, "html")
        self.assertEqual(ReportFormat.CSV.value, "csv")


class TestCoverageMatrix(unittest.TestCase):
    """Tests for CoverageMatrix class."""

    def test_matrix_creation(self):
        """CoverageMatrix can be created."""
        matrix = CoverageMatrix(
            categories=["reentrancy", "oracle"],
            cells=[
                CoverageMatrixCell(
                    category="reentrancy",
                    section="detection",
                    coverage_level=CoverageLevel.FULL,
                    doc_count=5,
                )
            ],
        )
        self.assertEqual(len(matrix.categories), 2)
        self.assertEqual(len(matrix.cells), 1)

    def test_matrix_get_cell(self):
        """Matrix cell retrieval works."""
        cell = CoverageMatrixCell(
            category="reentrancy",
            section="detection",
            coverage_level=CoverageLevel.FULL,
        )
        matrix = CoverageMatrix(cells=[cell])

        found = matrix.get_cell("reentrancy", "detection")
        self.assertEqual(found, cell)

        not_found = matrix.get_cell("oracle", "detection")
        self.assertIsNone(not_found)

    def test_matrix_to_dict(self):
        """Matrix serializes correctly."""
        matrix = CoverageMatrix(
            categories=["reentrancy"],
            cells=[
                CoverageMatrixCell(
                    category="reentrancy",
                    section="detection",
                    coverage_level=CoverageLevel.PARTIAL,
                )
            ],
            coverage_percent=50.0,
        )
        data = matrix.to_dict()
        self.assertIn("matrix", data)
        self.assertEqual(data["coverage_percent"], 50.0)

    def test_matrix_to_markdown(self):
        """Matrix renders as markdown."""
        matrix = CoverageMatrix(
            categories=["reentrancy"],
            cells=[
                CoverageMatrixCell(
                    category="reentrancy",
                    section="detection",
                    coverage_level=CoverageLevel.FULL,
                ),
                CoverageMatrixCell(
                    category="reentrancy",
                    section="exploitation",
                    coverage_level=CoverageLevel.PARTIAL,
                ),
                CoverageMatrixCell(
                    category="reentrancy",
                    section="mitigation",
                    coverage_level=CoverageLevel.MINIMAL,
                ),
                CoverageMatrixCell(
                    category="reentrancy",
                    section="examples",
                    coverage_level=CoverageLevel.NONE,
                ),
            ],
            coverage_percent=40.0,
        )
        md = matrix.to_markdown()
        self.assertIn("Category", md)
        self.assertIn("Detection", md)
        self.assertIn("✅", md)  # FULL
        self.assertIn("🟡", md)  # PARTIAL
        self.assertIn("🟠", md)  # MINIMAL
        self.assertIn("❌", md)  # NONE

    def test_matrix_to_toon(self):
        """Matrix renders in TOON format."""
        matrix = CoverageMatrix(
            categories=["reentrancy"],
            cells=[
                CoverageMatrixCell(
                    category="reentrancy",
                    section="detection",
                    coverage_level=CoverageLevel.FULL,
                ),
                CoverageMatrixCell(
                    category="reentrancy",
                    section="exploitation",
                    coverage_level=CoverageLevel.PARTIAL,
                ),
                CoverageMatrixCell(
                    category="reentrancy",
                    section="mitigation",
                    coverage_level=CoverageLevel.MINIMAL,
                ),
                CoverageMatrixCell(
                    category="reentrancy",
                    section="examples",
                    coverage_level=CoverageLevel.NONE,
                ),
            ],
            coverage_percent=40.0,
        )
        toon = matrix.to_toon()
        self.assertIn("[COVERAGE_MATRIX]", toon)
        self.assertIn("D:F", toon)  # Detection: Full
        self.assertIn("E:P", toon)  # Exploitation: Partial


class TestReportGenerator(unittest.TestCase):
    """Tests for ReportGenerator class."""

    def test_generator_creation(self):
        """ReportGenerator can be created."""
        generator = ReportGenerator()
        self.assertIsNotNone(generator.analyzer)
        self.assertIsNotNone(generator.gap_finder)

    def test_generate_matrix(self):
        """Matrix generation works."""
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        generator = ReportGenerator(analyzer=analyzer)

        matrix = generator.generate_matrix()
        self.assertEqual(len(matrix.categories), 8)
        self.assertEqual(len(matrix.sections), 4)

    def test_generate_full_report_markdown(self):
        """Full report generates markdown."""
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        gap_finder = GapFinder(retriever=mock_retriever)
        generator = ReportGenerator(analyzer=analyzer, gap_finder=gap_finder)

        report = generator.generate_full_report(ReportFormat.MARKDOWN)
        self.assertIn("VulnDocs", report)
        self.assertIn("Coverage", report)
        self.assertIn("##", report)  # Markdown headers

    def test_generate_full_report_json(self):
        """Full report generates valid JSON."""
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        gap_finder = GapFinder(retriever=mock_retriever)
        generator = ReportGenerator(analyzer=analyzer, gap_finder=gap_finder)

        report = generator.generate_full_report(ReportFormat.JSON)
        data = json.loads(report)
        self.assertIn("generated", data)
        self.assertIn("coverage", data)
        self.assertIn("gaps", data)
        self.assertIn("matrix", data)

    def test_generate_full_report_toon(self):
        """Full report generates TOON format."""
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        gap_finder = GapFinder(retriever=mock_retriever)
        generator = ReportGenerator(analyzer=analyzer, gap_finder=gap_finder)

        report = generator.generate_full_report(ReportFormat.TOON)
        self.assertIn("[VULNDOCS_COVERAGE]", report)
        self.assertIn("[/VULNDOCS_COVERAGE]", report)
        self.assertIn("[COVERAGE_MATRIX]", report)

    def test_generate_full_report_csv(self):
        """Full report generates CSV."""
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        gap_finder = GapFinder(retriever=mock_retriever)
        generator = ReportGenerator(analyzer=analyzer, gap_finder=gap_finder)

        report = generator.generate_full_report(ReportFormat.CSV)
        self.assertIn("metric,value", report)
        self.assertIn("overall_coverage", report)
        self.assertIn("Category Coverage", report)

    def test_generate_full_report_html(self):
        """Full report generates HTML."""
        mock_retriever = MockRetriever()
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        gap_finder = GapFinder(retriever=mock_retriever)
        generator = ReportGenerator(analyzer=analyzer, gap_finder=gap_finder)

        report = generator.generate_full_report(ReportFormat.HTML)
        self.assertIn("<!DOCTYPE html>", report)
        self.assertIn("<html>", report)
        self.assertIn("Coverage Report", report)
        self.assertIn("</html>", report)

    def test_export_report(self):
        """Report export to file works."""
        generator = ReportGenerator()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            filepath = f.name

        try:
            generator.export("# Test Report", ReportFormat.MARKDOWN, filepath)
            with open(filepath) as f:
                content = f.read()
            self.assertEqual(content, "# Test Report")
        finally:
            Path(filepath).unlink()


class TestReportConvenienceFunctions(unittest.TestCase):
    """Tests for report convenience functions."""

    @patch('alphaswarm_sol.vulndocs.analysis.reports.ReportGenerator')
    def test_generate_coverage_report(self, mock_generator_class):
        """generate_coverage_report convenience function works."""
        mock_generator_class.return_value.generate_full_report.return_value = "# Report"

        report = generate_coverage_report()
        self.assertEqual(report, "# Report")

    @patch('alphaswarm_sol.vulndocs.analysis.reports.ReportGenerator')
    def test_generate_coverage_matrix(self, mock_generator_class):
        """generate_coverage_matrix convenience function works."""
        mock_matrix = CoverageMatrix()
        mock_generator_class.return_value.generate_matrix.return_value = mock_matrix

        matrix = generate_coverage_matrix()
        self.assertEqual(matrix, mock_matrix)

    @patch('alphaswarm_sol.vulndocs.analysis.reports.ReportGenerator')
    def test_get_toon_summary(self, mock_generator_class):
        """get_toon_summary convenience function works."""
        mock_generator_class.return_value.generate_full_report.return_value = "[TOON]"

        toon = get_toon_summary()
        self.assertEqual(toon, "[TOON]")
        mock_generator_class.return_value.generate_full_report.assert_called_with(
            ReportFormat.TOON
        )


# =============================================================================
# Integration Tests
# =============================================================================


class TestCoverageAnalysisIntegration(unittest.TestCase):
    """Integration tests for coverage analysis pipeline."""

    def test_full_analysis_pipeline(self):
        """Full pipeline from analysis to report works."""
        # Create test data
        docs = [
            create_test_doc(
                doc_id="reentrancy/classic/doc1",
                subcategory="classic",
            ),
            create_test_doc(
                doc_id="reentrancy/cross-function/doc2",
                subcategory="cross-function",
                with_detection=False,
            ),
        ]
        mock_retriever = MockRetriever({"reentrancy": docs})

        # Run analysis
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        report = analyzer.analyze()

        # Find gaps
        gap_finder = GapFinder(retriever=mock_retriever)
        gaps = gap_finder.find_all_gaps()

        # Generate report
        generator = ReportGenerator(analyzer=analyzer, gap_finder=gap_finder)
        matrix = generator.generate_matrix()
        full_report = generator.generate_full_report()

        # Verify results
        self.assertGreater(report.total_documents, 0)
        self.assertGreater(len(gaps.gaps), 0)
        self.assertGreater(len(matrix.cells), 0)
        self.assertIn("Coverage", full_report)

    def test_gap_priority_reflects_threat_model(self):
        """Gaps for critical categories are prioritized."""
        mock_retriever = MockRetriever()  # Empty = all gaps
        gap_finder = GapFinder(retriever=mock_retriever)
        result = gap_finder.find_all_gaps()

        # First gaps should be critical (from critical categories)
        if result.priority_queue:
            first_gap = result.priority_queue[0]
            self.assertEqual(first_gap.severity, GapSeverity.CRITICAL)


class TestThreatModelAlignment(unittest.TestCase):
    """Tests for threat model alignment per PHILOSOPHY.md."""

    def test_all_attack_surfaces_mapped(self):
        """All attack surfaces map to at least one pattern."""
        for cat_id, cat_info in THREAT_MODEL_CATEGORIES.items():
            patterns = cat_info.get("patterns", [])
            self.assertGreater(
                len(patterns), 0,
                f"Category {cat_id} has no patterns"
            )

    def test_subcategories_cover_variants(self):
        """Subcategories cover known vulnerability variants."""
        reentrancy_subcats = THREAT_MODEL_CATEGORIES["reentrancy"]["subcategories"]
        self.assertIn("classic", reentrancy_subcats)
        self.assertIn("cross-function", reentrancy_subcats)
        self.assertIn("read-only", reentrancy_subcats)

        access_subcats = THREAT_MODEL_CATEGORIES["access-control"]["subcategories"]
        self.assertIn("missing", access_subcats)
        self.assertIn("tx-origin", access_subcats)

    def test_critical_categories_weighted(self):
        """Critical categories are weighted in threat model coverage."""
        doc = create_test_doc(category="reentrancy")  # Critical category
        mock_retriever = MockRetriever({"reentrancy": [doc]})
        analyzer = CoverageAnalyzer(retriever=mock_retriever)
        report = analyzer.analyze()

        # Threat model coverage should be > 0 even with only one critical category
        self.assertGreater(report.threat_model_coverage, 0)


if __name__ == "__main__":
    unittest.main()
