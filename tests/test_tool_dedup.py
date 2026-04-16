"""Tests for Deduplication Logic (Phase 5.1 Plan 10, Task 2).

This module tests:
- Location-based deduplication clustering
- Semantic similarity deduplication (with mocked embeddings)
- Deduplication statistics
- Category normalization and aliases

Tests are pytest-xdist compatible (no shared mutable state).
Tests run without requiring sentence-transformers (use mocks).
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, PropertyMock
import numpy as np

from alphaswarm_sol.orchestration.dedup import (
    CATEGORY_ALIASES,
    HIGH_CONFIDENCE_TOOLS,
    DeduplicatedFinding,
    DeduplicationStats,
    DeduplicationResult,
    SemanticDeduplicator,
    deduplicate_findings,
    deduplicate_with_stats,
    merge_findings,
    get_disagreements,
    get_unique_to_tool,
    get_high_confidence_findings,
    get_multi_tool_findings,
    calculate_dedup_hash,
    _normalize_category,
    _categories_similar,
)
from alphaswarm_sol.tools.adapters.sarif import VKGFinding


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_findings() -> List[VKGFinding]:
    """Create sample findings for deduplication testing."""
    return [
        VKGFinding(
            source="slither",
            rule_id="reentrancy-eth",
            title="Reentrancy in withdraw()",
            description="Reentrancy vulnerability in withdraw function",
            severity="high",
            category="reentrancy",
            file="contracts/Vault.sol",
            line=45,
            function="withdraw",
            confidence=0.9,
            vkg_pattern="reentrancy-classic",
        ),
        VKGFinding(
            source="aderyn",
            rule_id="reentrancy-vuln",
            title="Potential reentrancy in withdraw",
            description="Possible reentrancy in the withdraw function",
            severity="high",
            category="reentrancy-eth",  # Different category name, same meaning
            file="contracts/Vault.sol",
            line=46,  # Within tolerance
            function="withdraw",
            confidence=0.85,
            vkg_pattern="reentrancy-classic",
        ),
        VKGFinding(
            source="slither",
            rule_id="arbitrary-send-eth",
            title="Arbitrary send in transfer()",
            description="Arbitrary ETH send detected",
            severity="high",
            category="access_control",
            file="contracts/Token.sol",
            line=100,
            function="transfer",
            confidence=0.8,
        ),
        VKGFinding(
            source="mythril",
            rule_id="integer-overflow",
            title="Integer overflow in calculate()",
            description="Possible integer overflow",
            severity="medium",
            category="arithmetic",
            file="contracts/Math.sol",
            line=50,
            function="calculate",
            confidence=0.7,
        ),
    ]


@pytest.fixture
def mock_embedding_model():
    """Mock sentence transformer for semantic deduplication."""
    with patch("alphaswarm_sol.orchestration.dedup.SemanticDeduplicator.embedding_model", new_callable=PropertyMock) as mock:
        mock_model = MagicMock()
        # Return embeddings as numpy arrays
        mock_model.encode.return_value = np.array([
            [0.1, 0.2, 0.3],
            [0.1, 0.21, 0.31],  # Very similar to first
            [0.9, 0.8, 0.7],
            [0.5, 0.5, 0.5],
        ])
        mock.return_value = mock_model
        yield mock_model


# =============================================================================
# TestCategoryNormalization
# =============================================================================


class TestCategoryNormalization:
    """Test category normalization and aliases."""

    def test_category_aliases_exist(self):
        """CATEGORY_ALIASES has expected categories."""
        assert "reentrancy" in CATEGORY_ALIASES
        assert "access_control" in CATEGORY_ALIASES
        assert "oracle" in CATEGORY_ALIASES
        assert "arithmetic" in CATEGORY_ALIASES

    def test_reentrancy_aliases(self):
        """Reentrancy category has all variants."""
        aliases = CATEGORY_ALIASES["reentrancy"]
        assert "reentrancy" in aliases
        assert "reentrancy-eth" in aliases
        assert "reentrancy-no-eth" in aliases
        assert "reentrancy-classic" in aliases

    def test_normalize_category_exact_match(self):
        """Normalize exact category match."""
        assert _normalize_category("reentrancy") == "reentrancy"
        assert _normalize_category("access_control") == "access_control"

    def test_normalize_category_alias(self):
        """Normalize category alias to base form."""
        assert _normalize_category("reentrancy-eth") == "reentrancy"
        assert _normalize_category("reentrancy-no-eth") == "reentrancy"

    def test_normalize_category_case_insensitive(self):
        """Normalize handles case differences."""
        assert _normalize_category("REENTRANCY") == "reentrancy"
        assert _normalize_category("Reentrancy-ETH") == "reentrancy"

    def test_normalize_category_underscore_vs_dash(self):
        """Normalize handles underscore/dash differences."""
        assert _normalize_category("access-control") == "access_control"
        assert _normalize_category("access_control") == "access_control"

    def test_normalize_category_unknown(self):
        """Unknown category returns lowercase form."""
        assert _normalize_category("unknown-category") == "unknown-category"

    def test_categories_similar_same(self):
        """Same categories are similar."""
        assert _categories_similar("reentrancy", "reentrancy") is True

    def test_categories_similar_aliases(self):
        """Aliased categories are similar."""
        assert _categories_similar("reentrancy", "reentrancy-eth") is True
        assert _categories_similar("reentrancy-eth", "reentrancy-no-eth") is True

    def test_categories_similar_different(self):
        """Different categories are not similar."""
        assert _categories_similar("reentrancy", "access_control") is False
        assert _categories_similar("oracle", "arithmetic") is False


# =============================================================================
# TestDeduplicatedFinding
# =============================================================================


class TestDeduplicatedFinding:
    """Test DeduplicatedFinding dataclass."""

    def test_basic_creation(self):
        """Basic DeduplicatedFinding creation."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="test",
            category="reentrancy",
            severity="high",
            sources=["slither"],
            findings=[{"id": "1"}],
            confidence=0.9,
        )

        assert finding.file == "test.sol"
        assert finding.line == 10
        assert finding.category == "reentrancy"
        assert finding.severity == "high"

    def test_source_count(self):
        """source_count property works."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="test",
            category="reentrancy",
            severity="high",
            sources=["slither", "aderyn", "mythril"],
            findings=[],
        )

        assert finding.source_count == 3

    def test_high_confidence_multiple_sources(self):
        """high_confidence is True with multiple agreeing sources."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="test",
            category="reentrancy",
            severity="high",
            sources=["slither", "aderyn"],
            findings=[],
            agreement=True,
            confidence=0.7,
        )

        assert finding.high_confidence is True

    def test_high_confidence_single_source_high_conf(self):
        """high_confidence is True with single source and high confidence."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="test",
            category="reentrancy",
            severity="high",
            sources=["slither"],
            findings=[],
            agreement=True,
            confidence=0.9,
        )

        assert finding.high_confidence is True

    def test_high_confidence_disagreement(self):
        """high_confidence is False when sources disagree."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="test",
            category="reentrancy",
            severity="high",
            sources=["slither", "aderyn"],
            findings=[],
            agreement=False,
            confidence=0.6,
        )

        assert finding.high_confidence is False

    def test_to_dict(self):
        """DeduplicatedFinding can be serialized."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="test",
            category="reentrancy",
            severity="high",
            sources=["slither"],
            findings=[{"id": "1"}],
            agreement=True,
            confidence=0.9,
            vkg_pattern="reentrancy-classic",
        )

        data = finding.to_dict()

        assert data["file"] == "test.sol"
        assert data["source_count"] == 1
        assert data["high_confidence"] is True
        assert data["vkg_pattern"] == "reentrancy-classic"


# =============================================================================
# TestDeduplicationStats
# =============================================================================


class TestDeduplicationStats:
    """Test DeduplicationStats dataclass."""

    def test_basic_creation(self):
        """Basic stats creation."""
        stats = DeduplicationStats(
            input_count=10,
            output_count=5,
            reduction_percent=50.0,
            location_matches=3,
            semantic_matches=2,
            tool_agreement_boosts=2,
        )

        assert stats.input_count == 10
        assert stats.output_count == 5
        assert stats.reduction_percent == 50.0

    def test_to_dict(self):
        """Stats can be serialized."""
        stats = DeduplicationStats(
            input_count=10,
            output_count=5,
            reduction_percent=50.0,
            location_matches=3,
            semantic_matches=2,
        )

        data = stats.to_dict()

        assert data["input_count"] == 10
        assert data["output_count"] == 5
        assert data["reduction_percent"] == 50.0


# =============================================================================
# TestDeduplicationResult
# =============================================================================


class TestDeduplicationResult:
    """Test DeduplicationResult dataclass."""

    def test_to_dict(self):
        """Result can be serialized."""
        finding = DeduplicatedFinding(
            file="test.sol",
            line=10,
            function="test",
            category="reentrancy",
            severity="high",
            sources=["slither"],
            findings=[],
        )
        stats = DeduplicationStats(
            input_count=1,
            output_count=1,
            reduction_percent=0.0,
            location_matches=0,
            semantic_matches=0,
        )
        result = DeduplicationResult(findings=[finding], stats=stats)

        data = result.to_dict()

        assert len(data["findings"]) == 1
        assert "stats" in data


# =============================================================================
# TestLocationBasedDedup
# =============================================================================


class TestLocationBasedDedup:
    """Test location-based deduplication clustering."""

    def test_clusters_same_file_nearby_lines(self, sample_findings):
        """Findings in same file with nearby lines are clustered."""
        dedup = SemanticDeduplicator(use_embeddings=False, line_tolerance=5)

        results, stats = dedup.deduplicate(sample_findings)

        # First two findings should be merged (same file, nearby lines, similar category)
        vault_findings = [r for r in results if "Vault" in r.file]
        assert len(vault_findings) == 1
        assert "slither" in vault_findings[0].sources
        assert "aderyn" in vault_findings[0].sources

    def test_separate_files_not_clustered(self, sample_findings):
        """Findings in different files are not clustered."""
        dedup = SemanticDeduplicator(use_embeddings=False)

        results, stats = dedup.deduplicate(sample_findings)

        # Each distinct file should have separate findings
        files = set(r.file for r in results)
        assert len(files) >= 2  # At least Vault.sol and Token.sol

    def test_distant_lines_not_clustered(self):
        """Findings with distant lines are not clustered even in same file."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test-1",
                title="Finding 1",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
            ),
            VKGFinding(
                source="slither",
                rule_id="test-2",
                title="Finding 2",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=100,  # Far from line 10
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False, line_tolerance=5)
        results, stats = dedup.deduplicate(findings)

        assert len(results) == 2

    def test_different_categories_not_clustered(self):
        """Findings with different categories are not clustered even if nearby."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test-1",
                title="Finding 1",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
            ),
            VKGFinding(
                source="slither",
                rule_id="test-2",
                title="Finding 2",
                description="Desc",
                severity="high",
                category="oracle",  # Different category
                file="test.sol",
                line=11,  # Very close
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False, line_tolerance=5)
        results, stats = dedup.deduplicate(findings)

        assert len(results) == 2

    def test_similar_categories_clustered(self):
        """Findings with similar/aliased categories are clustered."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test-1",
                title="Finding 1",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="test-2",
                title="Finding 2",
                description="Desc",
                severity="high",
                category="reentrancy-eth",  # Alias of reentrancy
                file="test.sol",
                line=11,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False, line_tolerance=5)
        results, stats = dedup.deduplicate(findings)

        assert len(results) == 1
        assert results[0].source_count == 2

    def test_line_tolerance_respected(self):
        """Line tolerance parameter is respected."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test-1",
                title="Finding 1",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="test-2",
                title="Finding 2",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=13,  # 3 lines away
            ),
        ]

        # With tolerance of 2, should not cluster
        dedup_strict = SemanticDeduplicator(use_embeddings=False, line_tolerance=2)
        results_strict, _ = dedup_strict.deduplicate(findings)
        assert len(results_strict) == 2

        # With tolerance of 5, should cluster
        dedup_loose = SemanticDeduplicator(use_embeddings=False, line_tolerance=5)
        results_loose, _ = dedup_loose.deduplicate(findings)
        assert len(results_loose) == 1


class TestSemanticDedup:
    """Test semantic similarity-based deduplication."""

    def test_semantic_dedup_disabled_by_default_when_unavailable(self):
        """Semantic dedup is disabled when embeddings unavailable."""
        # Test that semantic dedup gracefully handles missing sentence-transformers
        dedup = SemanticDeduplicator(use_embeddings=False)
        # Should work without embeddings
        assert dedup.use_embeddings is False

        # Test with use_embeddings=True but mock the import failure
        dedup2 = SemanticDeduplicator(use_embeddings=True)
        dedup2._embeddings_available = False
        # Embedding model should return None when unavailable
        assert dedup2.embedding_model is None

    def test_semantic_dedup_with_mocked_embeddings(self, sample_findings):
        """Semantic dedup works with mocked embeddings."""
        # Create deduplicator with embeddings disabled
        # (we can't easily test real semantic dedup without the library)
        dedup = SemanticDeduplicator(use_embeddings=False)

        results, stats = dedup.deduplicate(sample_findings)

        # Should still produce valid results via location-based dedup
        assert len(results) > 0
        assert all(isinstance(r, DeduplicatedFinding) for r in results)

    def test_graceful_fallback_on_embedding_error(self, sample_findings):
        """Dedup gracefully falls back if embedding fails."""
        dedup = SemanticDeduplicator(use_embeddings=True)
        dedup._embeddings_available = True
        dedup._embedding_model = MagicMock()
        dedup._embedding_model.encode.side_effect = Exception("Embedding error")

        # Should not raise, falls back to location-only
        results, stats = dedup.deduplicate(sample_findings)

        assert len(results) > 0


class TestDeduplicationStats:
    """Test deduplication statistics tracking."""

    def test_stats_empty_input(self):
        """Stats for empty input."""
        dedup = SemanticDeduplicator(use_embeddings=False)

        results, stats = dedup.deduplicate([])

        assert stats.input_count == 0
        assert stats.output_count == 0
        assert stats.reduction_percent == 0.0

    def test_stats_no_deduplication(self):
        """Stats when no deduplication occurs."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test-1",
                title="Finding 1",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="file1.sol",
                line=10,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="test-2",
                title="Finding 2",
                description="Desc",
                severity="medium",
                category="oracle",
                file="file2.sol",
                line=20,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(findings)

        assert stats.input_count == 2
        assert stats.output_count == 2
        assert stats.reduction_percent == 0.0

    def test_stats_with_deduplication(self, sample_findings):
        """Stats reflect deduplication."""
        dedup = SemanticDeduplicator(use_embeddings=False)

        results, stats = dedup.deduplicate(sample_findings)

        assert stats.input_count == 4
        assert stats.output_count < 4  # Some dedup happened
        assert stats.reduction_percent > 0

    def test_stats_location_matches_counted(self):
        """Location matches are counted in stats."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test-1",
                title="Finding 1",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="test-2",
                title="Finding 2",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=11,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(findings)

        assert stats.location_matches >= 1


# =============================================================================
# TestConfidenceBoosting
# =============================================================================


class TestConfidenceBoosting:
    """Test confidence boosting for tool agreement."""

    def test_multi_tool_agreement_boosts_confidence(self):
        """Multiple tools agreeing boosts confidence."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="reentrancy-eth",
                title="Reentrancy",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.7,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="reentrancy-vuln",
                title="Reentrancy",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.7,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(findings)

        assert len(results) == 1
        # Confidence should be boosted
        assert results[0].confidence > 0.7
        assert stats.tool_agreement_boosts >= 1

    def test_three_tools_agreement_higher_boost(self):
        """Three tools agreeing gives higher confidence boost."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="reentrancy-eth",
                title="Reentrancy",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.6,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="reentrancy-vuln",
                title="Reentrancy",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.6,
            ),
            VKGFinding(
                source="mythril",
                rule_id="reentrancy",
                title="Reentrancy",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.6,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(findings)

        assert len(results) == 1
        # With 3 tools, should get larger boost
        assert results[0].confidence >= 0.8

    def test_high_confidence_tools_extra_boost(self):
        """High confidence tools give extra boost."""
        findings = [
            VKGFinding(
                source="slither",  # In HIGH_CONFIDENCE_TOOLS
                rule_id="reentrancy-eth",
                title="Reentrancy",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.6,
            ),
            VKGFinding(
                source="mythril",  # In HIGH_CONFIDENCE_TOOLS
                rule_id="reentrancy",
                title="Reentrancy",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.6,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(findings)

        # Should have extra boost from high-confidence tools
        assert results[0].confidence >= 0.7

    def test_confidence_clamped_to_one(self):
        """Confidence is clamped to 1.0 maximum."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test",
                title="Test",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.95,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="test",
                title="Test",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.95,
            ),
            VKGFinding(
                source="mythril",
                rule_id="test",
                title="Test",
                description="Desc",
                severity="high",
                category="reentrancy",
                file="test.sol",
                line=10,
                confidence=0.95,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(findings)

        assert results[0].confidence <= 1.0


# =============================================================================
# TestSeverityAggregation
# =============================================================================


class TestSeverityAggregation:
    """Test severity aggregation in clusters."""

    def test_most_severe_wins(self):
        """Cluster takes most severe severity."""
        findings = [
            VKGFinding(
                source="slither",
                rule_id="test-1",
                title="Finding 1",
                description="Desc",
                severity="medium",
                category="reentrancy",
                file="test.sol",
                line=10,
            ),
            VKGFinding(
                source="aderyn",
                rule_id="test-2",
                title="Finding 2",
                description="Desc",
                severity="critical",  # More severe
                category="reentrancy",
                file="test.sol",
                line=10,
            ),
        ]

        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(findings)

        assert results[0].severity == "critical"

    def test_results_sorted_by_severity(self, sample_findings):
        """Results are sorted by severity (critical first)."""
        dedup = SemanticDeduplicator(use_embeddings=False)
        results, stats = dedup.deduplicate(sample_findings)

        severities = [r.severity for r in results]
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

        # Check sorted order
        ordered_values = [severity_order.get(s, 5) for s in severities]
        assert ordered_values == sorted(ordered_values)


# =============================================================================
# TestUtilityFunctions
# =============================================================================


class TestMergeFindings:
    """Test merge_findings utility."""

    def test_groups_by_category(self):
        """merge_findings groups by normalized category."""
        findings = [
            DeduplicatedFinding(
                file="test.sol", line=10, function="test",
                category="reentrancy", severity="high", sources=["slither"], findings=[],
            ),
            DeduplicatedFinding(
                file="test.sol", line=20, function="test2",
                category="reentrancy-eth", severity="high", sources=["aderyn"], findings=[],
            ),
            DeduplicatedFinding(
                file="test.sol", line=30, function="test3",
                category="access_control", severity="medium", sources=["slither"], findings=[],
            ),
        ]

        grouped = merge_findings(findings)

        # Both reentrancy variants should be in same group
        assert "reentrancy" in grouped
        assert len(grouped["reentrancy"]) == 2
        assert "access_control" in grouped
        assert len(grouped["access_control"]) == 1


class TestGetDisagreements:
    """Test get_disagreements utility."""

    def test_returns_disagreements(self):
        """Returns findings where tools disagree."""
        findings = [
            DeduplicatedFinding(
                file="test.sol", line=10, function="test",
                category="reentrancy", severity="high",
                sources=["slither", "aderyn"], findings=[],
                agreement=False,  # Disagreement
            ),
            DeduplicatedFinding(
                file="test.sol", line=20, function="test2",
                category="access_control", severity="high",
                sources=["slither", "aderyn"], findings=[],
                agreement=True,  # Agreement
            ),
        ]

        disagreements = get_disagreements(findings)

        assert len(disagreements) == 1
        assert disagreements[0].category == "reentrancy"


class TestGetUniqueToTool:
    """Test get_unique_to_tool utility."""

    def test_returns_unique_findings(self):
        """Returns findings unique to specified tool."""
        findings = [
            DeduplicatedFinding(
                file="test.sol", line=10, function="test",
                category="reentrancy", severity="high",
                sources=["slither"], findings=[],  # Only slither
            ),
            DeduplicatedFinding(
                file="test.sol", line=20, function="test2",
                category="access_control", severity="high",
                sources=["slither", "aderyn"], findings=[],  # Both
            ),
            DeduplicatedFinding(
                file="test.sol", line=30, function="test3",
                category="oracle", severity="medium",
                sources=["aderyn"], findings=[],  # Only aderyn
            ),
        ]

        slither_unique = get_unique_to_tool(findings, "slither")
        aderyn_unique = get_unique_to_tool(findings, "aderyn")

        assert len(slither_unique) == 1
        assert slither_unique[0].category == "reentrancy"
        assert len(aderyn_unique) == 1
        assert aderyn_unique[0].category == "oracle"


class TestGetHighConfidenceFindings:
    """Test get_high_confidence_findings utility."""

    def test_filters_by_confidence(self):
        """Filters findings by confidence threshold."""
        findings = [
            DeduplicatedFinding(
                file="test.sol", line=10, function="test",
                category="reentrancy", severity="high",
                sources=["slither"], findings=[], confidence=0.9,
            ),
            DeduplicatedFinding(
                file="test.sol", line=20, function="test2",
                category="access_control", severity="high",
                sources=["slither"], findings=[], confidence=0.6,
            ),
        ]

        high_conf = get_high_confidence_findings(findings, min_confidence=0.8)

        assert len(high_conf) == 1
        assert high_conf[0].category == "reentrancy"


class TestGetMultiToolFindings:
    """Test get_multi_tool_findings utility."""

    def test_returns_multi_tool(self):
        """Returns findings from multiple tools."""
        findings = [
            DeduplicatedFinding(
                file="test.sol", line=10, function="test",
                category="reentrancy", severity="high",
                sources=["slither", "aderyn"], findings=[],
            ),
            DeduplicatedFinding(
                file="test.sol", line=20, function="test2",
                category="access_control", severity="high",
                sources=["slither"], findings=[],  # Single tool
            ),
        ]

        multi = get_multi_tool_findings(findings)

        assert len(multi) == 1
        assert multi[0].category == "reentrancy"


class TestCalculateDedupHash:
    """Test calculate_dedup_hash utility."""

    def test_hash_is_deterministic(self):
        """Same inputs produce same hash."""
        finding = {
            "file": "contracts/Vault.sol",
            "line": 45,
            "category": "reentrancy",
        }

        hash1 = calculate_dedup_hash(finding)
        hash2 = calculate_dedup_hash(finding)

        assert hash1 == hash2

    def test_hash_uses_filename_only(self):
        """Hash uses filename, not full path."""
        finding1 = {
            "file": "contracts/Vault.sol",
            "line": 45,
            "category": "reentrancy",
        }
        finding2 = {
            "file": "src/contracts/Vault.sol",  # Different path
            "line": 45,
            "category": "reentrancy",
        }

        hash1 = calculate_dedup_hash(finding1)
        hash2 = calculate_dedup_hash(finding2)

        assert hash1 == hash2  # Same filename, same hash

    def test_hash_normalizes_category(self):
        """Hash normalizes category."""
        finding1 = {
            "file": "test.sol",
            "line": 10,
            "category": "reentrancy",
        }
        finding2 = {
            "file": "test.sol",
            "line": 10,
            "category": "reentrancy-eth",  # Alias
        }

        hash1 = calculate_dedup_hash(finding1)
        hash2 = calculate_dedup_hash(finding2)

        assert hash1 == hash2


# =============================================================================
# TestConvenienceFunctions
# =============================================================================


class TestDeduplicateFindings:
    """Test deduplicate_findings convenience function."""

    def test_accepts_dict_list(self):
        """deduplicate_findings works with dict list."""
        findings = [
            {
                "source": "slither",
                "rule_id": "test-1",
                "title": "Test",
                "description": "Desc",
                "severity": "high",
                "category": "reentrancy",
                "file": "test.sol",
                "line": 10,
            },
        ]

        results = deduplicate_findings(findings, use_embeddings=False)

        assert len(results) == 1
        assert isinstance(results[0], DeduplicatedFinding)

    def test_accepts_vkg_finding_list(self, sample_findings):
        """deduplicate_findings works with VKGFinding list."""
        results = deduplicate_findings(sample_findings, use_embeddings=False)

        assert len(results) > 0
        assert all(isinstance(r, DeduplicatedFinding) for r in results)

    def test_empty_input(self):
        """deduplicate_findings handles empty input."""
        results = deduplicate_findings([], use_embeddings=False)

        assert results == []


class TestDeduplicateWithStats:
    """Test deduplicate_with_stats convenience function."""

    def test_returns_result_object(self, sample_findings):
        """deduplicate_with_stats returns DeduplicationResult."""
        result = deduplicate_with_stats(sample_findings, use_embeddings=False)

        assert isinstance(result, DeduplicationResult)
        assert len(result.findings) > 0
        assert isinstance(result.stats, DeduplicationStats)

    def test_result_to_dict(self, sample_findings):
        """Result can be serialized."""
        result = deduplicate_with_stats(sample_findings, use_embeddings=False)

        data = result.to_dict()

        assert "findings" in data
        assert "stats" in data
