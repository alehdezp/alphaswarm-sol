"""Tests for 3.1c-12 Regression Baseline + Improvement Loop.

Verifies:
- Baseline creation and persistence
- Regression detection
- Improvement tracking
- Batch comparison
- Unreliable result handling
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alphaswarm_sol.testing.evaluation.models import (
    EvaluationResult,
    PipelineHealth,
    RunMode,
    ScoreCard,
)
from tests.workflow_harness.lib.regression_baseline import (
    DEFAULT_REGRESSION_THRESHOLD,
    BaselineEntry,
    BaselineManager,
    ImprovementSummary,
    RegressionReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    workflow_id: str = "test-wf",
    score: int = 75,
    reliable: bool = True,
) -> EvaluationResult:
    health = PipelineHealth(
        parsed_records=5 if reliable else 1,
        expected_records=5,
        errors=0 if reliable else 4,
    )
    return EvaluationResult(
        scenario_name="test",
        workflow_id=workflow_id,
        run_mode=RunMode.SIMULATED,
        score_card=ScoreCard(
            workflow_id=workflow_id,
            overall_score=score,
            passed=score >= 60,
        ),
        pipeline_health=health,
        completed_at="2026-02-18T12:00:00Z",
    )


# ---------------------------------------------------------------------------
# BaselineEntry
# ---------------------------------------------------------------------------


class TestBaselineEntry:
    def test_avg_score(self):
        e = BaselineEntry(workflow_id="x", score=80, scores=[70, 80, 90])
        assert e.avg_score == 80.0

    def test_avg_score_empty(self):
        e = BaselineEntry(workflow_id="x", score=80, scores=[])
        assert e.avg_score == 80.0

    def test_min_max(self):
        e = BaselineEntry(workflow_id="x", score=80, scores=[60, 80, 100])
        assert e.min_score == 60
        assert e.max_score == 100


# ---------------------------------------------------------------------------
# BaselineManager — create and retrieve
# ---------------------------------------------------------------------------


class TestBaselineManagerBasic:
    def test_no_baseline_initially(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        assert mgr.get_baseline("nonexistent") is None

    def test_update_creates_baseline(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        result = _make_result(score=75)
        entry = mgr.update_baseline("test-wf", result)
        assert entry.score == 75
        assert entry.trial_count == 1

    def test_baseline_persists(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("test-wf", _make_result(score=75))

        # New manager reads from disk
        mgr2 = BaselineManager(tmp_path / "baselines")
        entry = mgr2.get_baseline("test-wf")
        assert entry is not None
        assert entry.score == 75

    def test_update_accumulates_scores(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("test-wf", _make_result(score=70))
        mgr.update_baseline("test-wf", _make_result(score=80))
        mgr.update_baseline("test-wf", _make_result(score=90))

        entry = mgr.get_baseline("test-wf")
        assert entry is not None
        assert entry.trial_count == 3
        assert entry.scores == [70, 80, 90]
        assert entry.score == 90  # Latest score

    def test_scores_capped_at_20(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        for i in range(25):
            mgr.update_baseline("test-wf", _make_result(score=50 + i))

        entry = mgr.get_baseline("test-wf")
        assert entry is not None
        assert len(entry.scores) == 20

    def test_list_baselines(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("wf-a", _make_result("wf-a", score=70))
        mgr.update_baseline("wf-b", _make_result("wf-b", score=80))

        baselines = mgr.list_baselines()
        assert len(baselines) == 2


# ---------------------------------------------------------------------------
# Regression detection
# ---------------------------------------------------------------------------


class TestRegressionDetection:
    def test_no_baseline_no_regression(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        report = mgr.check_regression("test-wf", _make_result(score=50))
        assert report.is_regression is False
        assert "first run" in report.message

    def test_score_drop_above_threshold_is_regression(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("test-wf", _make_result(score=80))

        report = mgr.check_regression("test-wf", _make_result(score=70))
        assert report.is_regression is True
        assert report.delta == -10
        assert "REGRESSION" in report.message

    def test_score_drop_within_threshold_not_regression(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("test-wf", _make_result(score=80))

        report = mgr.check_regression("test-wf", _make_result(score=78))
        assert report.is_regression is False

    def test_score_improvement_detected(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("test-wf", _make_result(score=70))

        report = mgr.check_regression("test-wf", _make_result(score=85))
        assert report.is_regression is False
        assert report.delta == 15
        assert "IMPROVED" in report.message

    def test_stable_score(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("test-wf", _make_result(score=75))

        report = mgr.check_regression("test-wf", _make_result(score=75))
        assert report.is_regression is False
        assert "STABLE" in report.message

    def test_custom_threshold(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines", regression_threshold=20)
        mgr.update_baseline("test-wf", _make_result(score=80))

        # 15 point drop, but threshold is 20 → not regression
        report = mgr.check_regression("test-wf", _make_result(score=65))
        assert report.is_regression is False


# ---------------------------------------------------------------------------
# Batch comparison
# ---------------------------------------------------------------------------


class TestBatchComparison:
    def test_check_batch(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("wf-a", _make_result("wf-a", score=80))
        mgr.update_baseline("wf-b", _make_result("wf-b", score=70))

        results = [
            _make_result("wf-a", score=90),  # improved
            _make_result("wf-b", score=55),  # regressed
            _make_result("wf-c", score=60),  # new (no baseline)
        ]
        summary = mgr.check_batch(results)

        assert isinstance(summary, ImprovementSummary)
        assert summary.total_workflows == 3
        assert summary.improved == 2  # wf-a improved, wf-c new (delta=60 > 0)
        assert summary.regressed == 1  # wf-b regressed
        assert summary.stable == 0
        assert len(summary.reports) == 3

    def test_regression_rate(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("wf-a", _make_result("wf-a", score=80))
        mgr.update_baseline("wf-b", _make_result("wf-b", score=80))

        results = [
            _make_result("wf-a", score=50),  # regressed
            _make_result("wf-b", score=50),  # regressed
        ]
        summary = mgr.check_batch(results)
        assert summary.regression_rate == 1.0


# ---------------------------------------------------------------------------
# Unreliable results
# ---------------------------------------------------------------------------


class TestUnreliableResults:
    def test_unreliable_result_preserves_existing_baseline(self, tmp_path: Path):
        mgr = BaselineManager(tmp_path / "baselines")
        mgr.update_baseline("test-wf", _make_result(score=80, reliable=True))

        # Unreliable result should not overwrite
        unreliable = _make_result(score=20, reliable=False)
        entry = mgr.update_baseline("test-wf", unreliable)
        assert entry.score == 80  # Preserved original

    def test_unreliable_result_refuses_baseline_seeding(self, tmp_path: Path):
        """P3-IMP-05: unreliable results never seed new baselines."""
        mgr = BaselineManager(tmp_path / "baselines")
        unreliable = _make_result(score=30, reliable=False)
        entry = mgr.update_baseline("test-wf", unreliable)
        assert entry.score == 0  # Refuses to seed from unreliable data


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_default_threshold(self):
        assert DEFAULT_REGRESSION_THRESHOLD == 5


# ---------------------------------------------------------------------------
# Adaptive Disagreement Threshold (R6 — EWMA tracker)
# ---------------------------------------------------------------------------


class TestAdaptiveDisagreementTracker:
    def test_fallback_threshold_below_min_observations(self, tmp_path: Path):
        """Below 25 observations, returns fixed fallback threshold."""
        from alphaswarm_sol.testing.evaluation.regression import (
            EWMA_FALLBACK_THRESHOLD,
            EWMA_MIN_OBSERVATIONS,
            AdaptiveDisagreementTracker,
        )

        tracker = AdaptiveDisagreementTracker(
            state_path=tmp_path / "tracker.json"
        )
        # Record fewer than minimum
        for i in range(EWMA_MIN_OBSERVATIONS - 1):
            tracker.record(float(i))

        assert tracker.threshold == float(EWMA_FALLBACK_THRESHOLD)
        assert not tracker.is_adaptive

    def test_ewma_activates_at_min_observations(self, tmp_path: Path):
        """At 25+ observations, EWMA activates and returns adaptive threshold."""
        from alphaswarm_sol.testing.evaluation.regression import (
            EWMA_FALLBACK_THRESHOLD,
            EWMA_MIN_OBSERVATIONS,
            AdaptiveDisagreementTracker,
        )

        tracker = AdaptiveDisagreementTracker(
            state_path=tmp_path / "tracker.json"
        )
        # Record exactly minimum observations (all the same value)
        for _ in range(EWMA_MIN_OBSERVATIONS):
            tracker.record(10.0)

        assert tracker.is_adaptive
        # With constant input, EWMA ≈ 10, variance → 0, threshold ≈ 10
        assert tracker.threshold != float(EWMA_FALLBACK_THRESHOLD)
        assert tracker.threshold == pytest.approx(10.0, abs=1.0)

    def test_persistence_roundtrip(self, tmp_path: Path):
        """State persists to disk and restores correctly."""
        from alphaswarm_sol.testing.evaluation.regression import (
            AdaptiveDisagreementTracker,
        )

        state_path = tmp_path / "tracker.json"

        # Create and populate
        tracker1 = AdaptiveDisagreementTracker(state_path=state_path)
        for v in [5.0, 10.0, 15.0, 8.0, 12.0]:
            tracker1.record(v)
        tracker1.save()

        # Reload from disk
        tracker2 = AdaptiveDisagreementTracker(state_path=state_path)
        tracker2.load()

        assert tracker2.observation_count == 5
        assert tracker2.threshold == tracker1.threshold

    def test_higher_variance_increases_threshold(self, tmp_path: Path):
        """Higher variance in disagreements leads to a higher adaptive threshold."""
        from alphaswarm_sol.testing.evaluation.regression import (
            EWMA_MIN_OBSERVATIONS,
            AdaptiveDisagreementTracker,
        )

        # Low variance tracker
        low_var = AdaptiveDisagreementTracker(
            state_path=tmp_path / "low.json"
        )
        for _ in range(EWMA_MIN_OBSERVATIONS):
            low_var.record(10.0)

        # High variance tracker
        high_var = AdaptiveDisagreementTracker(
            state_path=tmp_path / "high.json"
        )
        for i in range(EWMA_MIN_OBSERVATIONS):
            high_var.record(5.0 if i % 2 == 0 else 25.0)

        assert high_var.threshold > low_var.threshold

    def test_observation_count(self, tmp_path: Path):
        """observation_count tracks correctly."""
        from alphaswarm_sol.testing.evaluation.regression import (
            AdaptiveDisagreementTracker,
        )

        tracker = AdaptiveDisagreementTracker(
            state_path=tmp_path / "tracker.json"
        )
        assert tracker.observation_count == 0
        tracker.record(10.0)
        tracker.record(20.0)
        assert tracker.observation_count == 2
