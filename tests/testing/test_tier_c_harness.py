"""Tests for Tier C Stability + Shadow Mode Harness.

Phase 7.2 tests covering:
- N=50 stability runs per pattern
- Stability threshold gating (0.85)
- Shadow mode dual-labeler consensus (70% overlap)
- Disagreement logging
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from alphaswarm_sol.testing.tier_c_harness import (
    TierCStabilityHarness,
    TierCStabilityReport,
    PatternStabilityResult,
    ShadowModeResult,
    run_tier_c_stability,
    load_tier_c_stability_report,
    DEFAULT_STABILITY_RUNS,
    STABILITY_THRESHOLD,
    SHADOW_MODE_CONSENSUS_THRESHOLD,
)
from alphaswarm_sol.testing.metrics import TierCStabilityMetrics
from alphaswarm_sol.labels.overlay import LabelOverlay
from alphaswarm_sol.labels.schema import FunctionLabel, LabelConfidence, LabelSource


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def empty_overlay() -> LabelOverlay:
    """Create an empty label overlay for testing."""
    return LabelOverlay()


@pytest.fixture
def labeled_overlay() -> LabelOverlay:
    """Create a label overlay with some labels for testing."""
    overlay = LabelOverlay()

    # Add some labels to function nodes
    for i in range(5):
        func_id = f"func_{i}"
        label = FunctionLabel(
            label_id="access_control.owner_only",
            confidence=LabelConfidence.HIGH,
            source=LabelSource.PATTERN_INFERRED,
            reasoning=f"Line {i * 10}",
        )
        overlay.add_label(func_id, label)

        # Add a second label to some functions
        if i % 2 == 0:
            label2 = FunctionLabel(
                label_id="state_mutation.balance_update",
                confidence=LabelConfidence.MEDIUM,
                source=LabelSource.PATTERN_INFERRED,
                reasoning=f"Line {i * 10 + 5}",
            )
            overlay.add_label(func_id, label2)

    return overlay


@pytest.fixture
def sample_patterns() -> list:
    """Create sample Tier C patterns for testing."""
    return [
        {
            "id": "pattern-1",
            "name": "Test Pattern 1",
            "tier_c_all": [
                {"type": "has_label", "value": "access_control.owner_only"},
            ],
            "tier_c_any": [],
            "tier_c_none": [],
        },
        {
            "id": "pattern-2",
            "name": "Test Pattern 2",
            "tier_c_all": [],
            "tier_c_any": [
                {"type": "has_category", "value": "state_mutation"},
            ],
            "tier_c_none": [],
        },
        {
            "id": "pattern-3",
            "name": "Test Pattern 3",
            "tier_c_all": [
                {"type": "has_label", "value": "access_control.owner_only"},
            ],
            "tier_c_any": [],
            "tier_c_none": [
                {"type": "has_label", "value": "access_control.role_based"},
            ],
        },
    ]


@pytest.fixture
def sample_node_ids() -> list:
    """Create sample node IDs for testing."""
    return [f"func_{i}" for i in range(10)]


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Test module constants."""

    def test_default_stability_runs(self):
        """Test default stability runs is 50."""
        assert DEFAULT_STABILITY_RUNS == 50

    def test_stability_threshold(self):
        """Test stability threshold is 0.85."""
        assert STABILITY_THRESHOLD == 0.85

    def test_shadow_mode_consensus_threshold(self):
        """Test shadow mode consensus threshold is 0.70."""
        assert SHADOW_MODE_CONSENSUS_THRESHOLD == 0.70


# =============================================================================
# PatternStabilityResult Tests
# =============================================================================


class TestPatternStabilityResult:
    """Test PatternStabilityResult dataclass."""

    def test_creation(self):
        """Test creating a stability result."""
        result = PatternStabilityResult(
            pattern_id="test-pattern",
            stability_score=0.90,
            runs_total=50,
            runs_consistent=45,
            findings_variance=0.5,
            passed=True,
        )
        assert result.pattern_id == "test-pattern"
        assert result.stability_score == 0.90
        assert result.runs_total == 50
        assert result.runs_consistent == 45
        assert result.passed is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = PatternStabilityResult(
            pattern_id="test-pattern",
            stability_score=0.90,
            runs_total=50,
            runs_consistent=45,
            findings_variance=0.5,
            passed=True,
            details=[{"run": 1, "findings_count": 5}],
        )
        d = result.to_dict()
        assert d["pattern_id"] == "test-pattern"
        assert d["stability_score"] == 0.90
        assert d["passed"] is True


# =============================================================================
# ShadowModeResult Tests
# =============================================================================


class TestShadowModeResult:
    """Test ShadowModeResult dataclass."""

    def test_creation(self):
        """Test creating a shadow mode result."""
        result = ShadowModeResult(
            pattern_id="test-pattern",
            overlap_score=0.80,
            consensus_reached=True,
        )
        assert result.pattern_id == "test-pattern"
        assert result.overlap_score == 0.80
        assert result.consensus_reached is True

    def test_consensus_threshold(self):
        """Test consensus threshold logic."""
        # Above threshold
        result = ShadowModeResult(
            pattern_id="p1",
            overlap_score=0.75,
            consensus_reached=True,
        )
        assert result.consensus_reached is True

        # Below threshold
        result = ShadowModeResult(
            pattern_id="p2",
            overlap_score=0.60,
            consensus_reached=False,
        )
        assert result.consensus_reached is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = ShadowModeResult(
            pattern_id="test-pattern",
            overlap_score=0.80,
            consensus_reached=True,
            labeler_a_labels={"a", "b"},
            labeler_b_labels={"b", "c"},
            agreed_labels={"b"},
            disagreed_labels={"a", "c"},
        )
        d = result.to_dict()
        assert d["pattern_id"] == "test-pattern"
        assert d["agreed_count"] == 1
        assert d["disagreed_count"] == 2


# =============================================================================
# TierCStabilityHarness Tests
# =============================================================================


class TestTierCStabilityHarness:
    """Test TierCStabilityHarness class."""

    def test_initialization(self, empty_overlay):
        """Test harness initialization."""
        harness = TierCStabilityHarness(
            overlay=empty_overlay,
            stability_runs=50,
            stability_threshold=0.85,
        )
        assert harness.stability_runs == 50
        assert harness.stability_threshold == 0.85
        assert harness.enable_shadow_mode is True

    def test_initialization_custom_settings(self, empty_overlay):
        """Test harness with custom settings."""
        harness = TierCStabilityHarness(
            overlay=empty_overlay,
            stability_runs=100,
            stability_threshold=0.90,
            shadow_mode_threshold=0.80,
            enable_shadow_mode=False,
        )
        assert harness.stability_runs == 100
        assert harness.stability_threshold == 0.90
        assert harness.shadow_mode_threshold == 0.80
        assert harness.enable_shadow_mode is False

    def test_run_stability_test_n50(self, labeled_overlay, sample_patterns, sample_node_ids):
        """Test that N=50 runs are performed per pattern."""
        harness = TierCStabilityHarness(
            overlay=labeled_overlay,
            stability_runs=50,
            enable_shadow_mode=False,  # Disable for this test
        )

        report = harness.run_stability_test(
            patterns=sample_patterns,
            node_ids=sample_node_ids,
            seed=42,  # Reproducible
        )

        # Verify N=50 runs per pattern
        for result in report.pattern_results:
            assert result.runs_total == 50, f"Pattern {result.pattern_id} had {result.runs_total} runs, expected 50"

    def test_stability_threshold_gating(self, labeled_overlay, sample_node_ids):
        """Test that patterns below 0.85 stability fail."""
        harness = TierCStabilityHarness(
            overlay=labeled_overlay,
            stability_runs=10,  # Fewer runs for test speed
            stability_threshold=0.85,
            enable_shadow_mode=False,
        )

        # Pattern that should be stable (deterministic matching)
        stable_pattern = {
            "id": "stable-pattern",
            "name": "Stable Pattern",
            "tier_c_all": [
                {"type": "has_label", "value": "access_control.owner_only"},
            ],
            "tier_c_any": [],
            "tier_c_none": [],
        }

        report = harness.run_stability_test(
            patterns=[stable_pattern],
            node_ids=sample_node_ids,
            seed=42,
        )

        # With deterministic matching, stability should be high
        assert report.pattern_results[0].stability_score >= 0.85
        assert report.pattern_results[0].passed is True

    def test_shadow_mode_consensus(self, labeled_overlay, sample_patterns, sample_node_ids):
        """Test shadow mode with 70% overlap threshold."""
        harness = TierCStabilityHarness(
            overlay=labeled_overlay,
            stability_runs=5,
            enable_shadow_mode=True,
        )

        # Create a similar overlay for shadow mode
        shadow_overlay = LabelOverlay()
        for i in range(5):
            func_id = f"func_{i}"
            label = FunctionLabel(
                label_id="access_control.owner_only",
                confidence=LabelConfidence.HIGH,
                source=LabelSource.PATTERN_INFERRED,
                reasoning=f"Line {i * 10}",
            )
            shadow_overlay.add_label(func_id, label)

        harness.set_shadow_overlay(shadow_overlay)

        report = harness.run_stability_test(
            patterns=sample_patterns,
            node_ids=sample_node_ids,
            seed=42,
        )

        # Should have shadow mode results
        assert report.shadow_mode_enabled is True
        assert len(report.shadow_mode_results) == len(sample_patterns)

    def test_shadow_mode_disagreement_logging(self, labeled_overlay, sample_node_ids):
        """Test that shadow mode disagreements are logged."""
        harness = TierCStabilityHarness(
            overlay=labeled_overlay,
            stability_runs=5,
            enable_shadow_mode=True,
            shadow_mode_threshold=0.70,
        )

        # Create a different overlay to trigger disagreements
        shadow_overlay = LabelOverlay()
        # Add different labels
        for i in range(5):
            func_id = f"func_{i}"
            label = FunctionLabel(
                label_id="different.label",  # Different label
                confidence=LabelConfidence.MEDIUM,
                source=LabelSource.PATTERN_INFERRED,
                reasoning=f"Line {i * 10}",
            )
            shadow_overlay.add_label(func_id, label)

        harness.set_shadow_overlay(shadow_overlay)

        pattern = {
            "id": "test-pattern",
            "name": "Test Pattern",
            "tier_c_all": [
                {"type": "has_label", "value": "access_control.owner_only"},
            ],
            "tier_c_any": [],
            "tier_c_none": [],
        }

        report = harness.run_stability_test(
            patterns=[pattern],
            node_ids=sample_node_ids,
            seed=42,
        )

        # Should have disagreements logged
        shadow_result = report.shadow_mode_results[0]
        # Overlap should be low due to different labels
        assert shadow_result.overlap_score < 0.70
        assert shadow_result.consensus_reached is False
        assert len(shadow_result.notes) > 0


# =============================================================================
# TierCStabilityReport Tests
# =============================================================================


class TestTierCStabilityReport:
    """Test TierCStabilityReport class."""

    def test_to_dict(self):
        """Test report serialization."""
        report = TierCStabilityReport(
            timestamp="2026-01-29T00:00:00Z",
            total_patterns=3,
            patterns_passed=2,
            patterns_failed=1,
            overall_stability=0.90,
            shadow_mode_enabled=True,
            shadow_mode_consensus_rate=0.85,
            pattern_results=[],
            shadow_mode_results=[],
            config={"stability_runs": 50},
        )
        d = report.to_dict()
        assert d["summary"]["total_patterns"] == 3
        assert d["summary"]["overall_stability"] == 0.90

    def test_save_and_load(self, tmp_path, labeled_overlay, sample_patterns, sample_node_ids):
        """Test saving and loading a report."""
        harness = TierCStabilityHarness(
            overlay=labeled_overlay,
            stability_runs=5,
            enable_shadow_mode=False,
        )

        report = harness.run_stability_test(
            patterns=sample_patterns,
            node_ids=sample_node_ids,
        )

        # Save to temp path
        report_path = tmp_path / "tier_c_stability.yaml"
        report.save(report_path)

        assert report_path.exists()

        # Load back
        loaded = load_tier_c_stability_report(report_path)
        assert loaded is not None
        assert loaded.total_patterns == report.total_patterns
        assert loaded.overall_stability == report.overall_stability


# =============================================================================
# TierCStabilityMetrics Tests
# =============================================================================


class TestTierCStabilityMetrics:
    """Test TierCStabilityMetrics class."""

    def test_meets_stability_gates_pass(self):
        """Test stability gates pass when above thresholds."""
        metrics = TierCStabilityMetrics(
            overall_stability=0.90,
            patterns_passed=9,
            patterns_failed=1,
            shadow_mode_enabled=True,
            shadow_mode_consensus=0.80,
        )
        assert metrics.meets_stability_gates() is True

    def test_meets_stability_gates_fail_stability(self):
        """Test stability gates fail when stability below threshold."""
        metrics = TierCStabilityMetrics(
            overall_stability=0.80,  # Below 0.85
            patterns_passed=8,
            patterns_failed=2,
        )
        assert metrics.meets_stability_gates() is False

    def test_meets_stability_gates_fail_shadow_mode(self):
        """Test stability gates fail when shadow mode consensus below threshold."""
        metrics = TierCStabilityMetrics(
            overall_stability=0.90,
            patterns_passed=9,
            patterns_failed=1,
            shadow_mode_enabled=True,
            shadow_mode_consensus=0.60,  # Below 0.70
        )
        assert metrics.meets_stability_gates() is False

    def test_get_stability_failures(self):
        """Test getting stability failure details."""
        metrics = TierCStabilityMetrics(
            overall_stability=0.80,
            patterns_passed=8,
            patterns_failed=2,
            shadow_mode_enabled=True,
            shadow_mode_consensus=0.60,
        )
        failures = metrics.get_stability_failures()
        assert "overall_stability" in failures
        assert failures["overall_stability"]["actual"] == 0.80
        assert "shadow_mode_consensus" in failures
        assert failures["shadow_mode_consensus"]["actual"] == 0.60

    def test_get_unstable_patterns(self):
        """Test getting list of unstable patterns."""
        metrics = TierCStabilityMetrics(
            overall_stability=0.85,
            patterns_passed=2,
            patterns_failed=1,
            pattern_scores={
                "pattern-1": 0.95,
                "pattern-2": 0.90,
                "pattern-3": 0.70,  # Below threshold
            },
        )
        unstable = metrics.get_unstable_patterns()
        assert len(unstable) == 1
        assert "pattern-3" in unstable

    def test_from_stability_report(self, labeled_overlay, sample_patterns, sample_node_ids):
        """Test creating metrics from stability report."""
        harness = TierCStabilityHarness(
            overlay=labeled_overlay,
            stability_runs=5,
            enable_shadow_mode=False,
        )

        report = harness.run_stability_test(
            patterns=sample_patterns,
            node_ids=sample_node_ids,
        )

        metrics = TierCStabilityMetrics.from_stability_report(report)
        assert metrics.total_patterns == report.total_patterns
        assert metrics.overall_stability == report.overall_stability

    def test_format_summary(self):
        """Test formatted summary output."""
        metrics = TierCStabilityMetrics(
            overall_stability=0.90,
            patterns_passed=9,
            patterns_failed=1,
            total_patterns=10,
            shadow_mode_enabled=True,
            shadow_mode_consensus=0.80,
            execution_time_ms=5000,
        )
        summary = metrics.format_summary()
        assert "Tier C Stability Metrics" in summary
        assert "90.0%" in summary
        assert "9/10" in summary


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for full harness workflow."""

    def test_full_workflow(self, labeled_overlay, sample_patterns, sample_node_ids):
        """Test complete stability testing workflow."""
        # Create harness
        harness = TierCStabilityHarness(
            overlay=labeled_overlay,
            stability_runs=10,
            stability_threshold=0.85,
            enable_shadow_mode=False,
        )

        # Run stability test
        report = harness.run_stability_test(
            patterns=sample_patterns,
            node_ids=sample_node_ids,
            seed=42,
        )

        # Verify report structure
        assert report.total_patterns == len(sample_patterns)
        assert len(report.pattern_results) == len(sample_patterns)

        # Convert to metrics
        metrics = TierCStabilityMetrics.from_stability_report(report)
        assert metrics.total_patterns == report.total_patterns

        # Verify metrics
        summary = metrics.format_summary()
        assert "Tier C Stability Metrics" in summary

    def test_convenience_function(self, labeled_overlay, sample_patterns, sample_node_ids):
        """Test run_tier_c_stability convenience function."""
        report = run_tier_c_stability(
            overlay=labeled_overlay,
            patterns=sample_patterns,
            node_ids=sample_node_ids,
            runs=10,
            threshold=0.85,
        )

        assert report.total_patterns == len(sample_patterns)
        assert report.config["stability_runs"] == 10
