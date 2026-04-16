"""Tests for Model Ranking System.

Comprehensive tests for the ranking module covering:
- RankingsStore: Persistent storage operations
- ModelSelector: Model selection algorithm
- FeedbackCollector: Feedback processing
- update_ranking_from_feedback: EMA update calculations
- Integration: End-to-end ranking workflow
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from alphaswarm_sol.agents.ranking.schemas import (
    Complexity,
    TaskProfile,
    ModelRanking,
    TaskFeedback,
)
from alphaswarm_sol.agents.ranking.store import (
    RankingsStore,
    DEFAULT_RANKINGS_PATH,
)
from alphaswarm_sol.agents.ranking.selector import (
    ModelSelector,
    select_model,
    DEFAULT_MODEL,
    ACCURACY_THRESHOLD,
    QUALITY_THRESHOLD,
)
from alphaswarm_sol.agents.ranking.feedback import (
    FeedbackCollector,
    update_ranking_from_feedback,
    create_initial_ranking,
    DEFAULT_DECAY_FACTOR,
    MIN_SAMPLES_FOR_EMA,
)
from alphaswarm_sol.agents.runtime.types import TaskType


# =============================================================================
# Test TaskProfile
# =============================================================================

class TestTaskProfile:
    """Tests for TaskProfile dataclass."""

    def test_default_values(self):
        """TaskProfile has sensible defaults."""
        profile = TaskProfile(task_type=TaskType.VERIFY)

        assert profile.task_type == TaskType.VERIFY
        assert profile.complexity == Complexity.MODERATE
        assert profile.context_size == 0
        assert profile.output_size == 0
        assert profile.requires_tools is False
        assert profile.latency_sensitive is False
        assert profile.accuracy_critical is False

    def test_all_values(self):
        """TaskProfile accepts all values."""
        profile = TaskProfile(
            task_type=TaskType.REASONING_HEAVY,
            complexity="complex",
            context_size=50000,
            output_size=5000,
            requires_tools=True,
            latency_sensitive=False,
            accuracy_critical=True,
        )

        assert profile.task_type == TaskType.REASONING_HEAVY
        assert profile.complexity == "complex"
        assert profile.context_size == 50000
        assert profile.accuracy_critical is True

    def test_invalid_complexity_raises(self):
        """Invalid complexity raises ValueError."""
        with pytest.raises(ValueError, match="Invalid complexity"):
            TaskProfile(task_type=TaskType.CODE, complexity="impossible")

    def test_to_dict(self):
        """TaskProfile serializes to dict."""
        profile = TaskProfile(
            task_type=TaskType.VERIFY,
            complexity="simple",
            context_size=1000,
        )
        data = profile.to_dict()

        assert data["task_type"] == "verify"
        assert data["complexity"] == "simple"
        assert data["context_size"] == 1000

    def test_from_dict(self):
        """TaskProfile deserializes from dict."""
        data = {
            "task_type": "reasoning",
            "complexity": "complex",
            "context_size": 50000,
            "accuracy_critical": True,
        }
        profile = TaskProfile.from_dict(data)

        assert profile.task_type == TaskType.REASONING
        assert profile.complexity == "complex"
        assert profile.context_size == 50000
        assert profile.accuracy_critical is True


# =============================================================================
# Test ModelRanking
# =============================================================================

class TestModelRanking:
    """Tests for ModelRanking dataclass."""

    def test_default_values(self):
        """ModelRanking has valid defaults."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
        )

        assert ranking.model_id == "test/model"
        assert ranking.task_type == "verify"
        assert ranking.success_rate == 0.0
        assert ranking.average_latency_ms == 0
        assert ranking.sample_count == 0

    def test_full_values(self):
        """ModelRanking accepts all values."""
        now = datetime.utcnow()
        ranking = ModelRanking(
            model_id="deepseek/deepseek-v3.2",
            task_type="reasoning",
            success_rate=0.92,
            average_latency_ms=2500,
            average_tokens=3000,
            quality_score=0.85,
            cost_per_task=0.0012,
            sample_count=50,
            last_updated=now,
        )

        assert ranking.model_id == "deepseek/deepseek-v3.2"
        assert ranking.success_rate == 0.92
        assert ranking.quality_score == 0.85
        assert ranking.sample_count == 50

    def test_invalid_success_rate_raises(self):
        """Invalid success rate raises ValueError."""
        with pytest.raises(ValueError, match="success_rate must be 0.0-1.0"):
            ModelRanking(
                model_id="test/model",
                task_type="verify",
                success_rate=1.5,
            )

    def test_negative_latency_raises(self):
        """Negative latency raises ValueError."""
        with pytest.raises(ValueError, match="average_latency_ms must be >= 0"):
            ModelRanking(
                model_id="test/model",
                task_type="verify",
                average_latency_ms=-100,
            )

    def test_to_dict(self):
        """ModelRanking serializes to dict."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            success_rate=0.95,
            average_latency_ms=850,
            quality_score=0.88,
        )
        data = ranking.to_dict()

        assert data["model_id"] == "test/model"
        assert data["success_rate"] == 0.95
        assert "last_updated" in data

    def test_from_dict(self):
        """ModelRanking deserializes from dict."""
        data = {
            "model_id": "minimax/minimax-m2:free",
            "task_type": "verify",
            "success_rate": 0.95,
            "average_latency_ms": 850,
            "quality_score": 0.88,
            "sample_count": 25,
            "last_updated": "2026-01-21T12:00:00",
        }
        ranking = ModelRanking.from_dict(data)

        assert ranking.model_id == "minimax/minimax-m2:free"
        assert ranking.success_rate == 0.95
        assert ranking.sample_count == 25

    def test_score_calculation(self):
        """ModelRanking.score() computes composite score."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            success_rate=1.0,
            average_latency_ms=1000,
            quality_score=0.9,
            cost_per_task=0.001,
        )

        score = ranking.score()
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Good metrics should produce good score


# =============================================================================
# Test TaskFeedback
# =============================================================================

class TestTaskFeedback:
    """Tests for TaskFeedback dataclass."""

    def test_default_values(self):
        """TaskFeedback creates with required values."""
        feedback = TaskFeedback(
            task_id="task-123",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=850,
            tokens_used=450,
            quality_score=0.92,
            cost_usd=0.0,
        )

        assert feedback.task_id == "task-123"
        assert feedback.success is True
        assert feedback.error_message is None

    def test_with_error(self):
        """TaskFeedback captures error messages."""
        feedback = TaskFeedback(
            task_id="task-456",
            model_id="test/model",
            task_type="verify",
            success=False,
            latency_ms=5000,
            tokens_used=0,
            quality_score=0.0,
            cost_usd=0.002,
            error_message="Context length exceeded",
        )

        assert feedback.success is False
        assert feedback.error_message == "Context length exceeded"

    def test_to_dict_and_from_dict(self):
        """TaskFeedback serializes and deserializes."""
        original = TaskFeedback(
            task_id="task-789",
            model_id="deepseek/deepseek-v3.2",
            task_type="reasoning",
            success=True,
            latency_ms=2000,
            tokens_used=3500,
            quality_score=0.88,
            cost_usd=0.0015,
        )

        data = original.to_dict()
        restored = TaskFeedback.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.model_id == original.model_id
        assert restored.quality_score == original.quality_score


# =============================================================================
# Test RankingsStore
# =============================================================================

class TestRankingsStore:
    """Tests for RankingsStore."""

    def test_load_from_empty_file(self, tmp_path):
        """Load returns empty dict for missing file."""
        store = RankingsStore(tmp_path / "nonexistent.yaml")
        rankings = store.load()

        assert rankings == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        """Save and load preserves rankings."""
        path = tmp_path / "rankings.yaml"
        store = RankingsStore(path)

        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            success_rate=0.95,
            average_latency_ms=850,
            quality_score=0.88,
            sample_count=25,
        )

        store.update_ranking(ranking)
        store.save()

        # Clear cache and reload
        store.clear_cache()
        loaded = store.load()

        assert "verify" in loaded
        assert "test/model" in loaded["verify"]
        loaded_ranking = loaded["verify"]["test/model"]
        assert loaded_ranking.success_rate == 0.95
        assert loaded_ranking.sample_count == 25

    def test_update_single_ranking(self, tmp_path):
        """Update replaces existing ranking."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        ranking1 = ModelRanking(
            model_id="test/model",
            task_type="verify",
            success_rate=0.80,
        )
        store.update_ranking(ranking1)

        ranking2 = ModelRanking(
            model_id="test/model",
            task_type="verify",
            success_rate=0.95,
        )
        store.update_ranking(ranking2)

        loaded = store.get_ranking("test/model", "verify")
        assert loaded.success_rate == 0.95

    def test_get_all_rankings(self, tmp_path):
        """get_all_rankings returns all rankings."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Add rankings for different task types
        store.update_ranking(ModelRanking(
            model_id="model-a",
            task_type="verify",
            success_rate=0.90,
        ))
        store.update_ranking(ModelRanking(
            model_id="model-b",
            task_type="reasoning",
            success_rate=0.85,
        ))

        all_rankings = store.get_all_rankings()
        assert len(all_rankings) == 2
        model_ids = {r.model_id for r in all_rankings}
        assert model_ids == {"model-a", "model-b"}

    def test_get_rankings_for_task(self, tmp_path):
        """get_rankings_for_task returns sorted rankings."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Add multiple models for same task type
        store.update_ranking(ModelRanking(
            model_id="model-low",
            task_type="verify",
            quality_score=0.5,
        ))
        store.update_ranking(ModelRanking(
            model_id="model-high",
            task_type="verify",
            quality_score=0.9,
        ))

        rankings = store.get_rankings_for_task("verify")
        assert len(rankings) == 2
        # Higher score first
        assert rankings[0].model_id == "model-high"

    def test_reset(self, tmp_path):
        """reset clears all rankings."""
        path = tmp_path / "rankings.yaml"
        store = RankingsStore(path)

        store.update_ranking(ModelRanking(
            model_id="test/model",
            task_type="verify",
        ))
        store.save()

        store.reset()
        assert not path.exists()
        assert store.load() == {}


# =============================================================================
# Test ModelSelector
# =============================================================================

class TestModelSelector:
    """Tests for ModelSelector."""

    def test_select_best_model_for_verify(self, tmp_path):
        """Selector picks best model for verify task."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Add rankings with different quality scores
        store.update_ranking(ModelRanking(
            model_id="model-low",
            task_type="verify",
            quality_score=0.5,
            success_rate=0.8,
            average_latency_ms=1000,
        ))
        store.update_ranking(ModelRanking(
            model_id="model-high",
            task_type="verify",
            quality_score=0.9,
            success_rate=0.95,
            average_latency_ms=500,
        ))

        selector = ModelSelector(store)
        profile = TaskProfile(
            task_type=TaskType.VERIFY,
            latency_sensitive=True,  # Should pick fastest
        )

        model = selector.select(profile)
        assert model == "model-high"  # Lower latency

    def test_select_for_accuracy_critical(self, tmp_path):
        """Accuracy-critical tasks pick highest quality."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        store.update_ranking(ModelRanking(
            model_id="fast-but-low-quality",
            task_type="reasoning",
            quality_score=0.7,
            success_rate=0.85,
            average_latency_ms=500,
        ))
        store.update_ranking(ModelRanking(
            model_id="slow-but-high-quality",
            task_type="reasoning",
            quality_score=0.95,
            success_rate=0.92,
            average_latency_ms=3000,
        ))

        selector = ModelSelector(store)
        profile = TaskProfile(
            task_type=TaskType.REASONING,
            accuracy_critical=True,
        )

        model = selector.select(profile)
        assert model == "slow-but-high-quality"

    def test_fallback_when_no_rankings(self, tmp_path):
        """Selector falls back to default when no rankings."""
        store = RankingsStore(tmp_path / "rankings.yaml")  # Empty
        selector = ModelSelector(store)

        profile = TaskProfile(task_type=TaskType.VERIFY)
        model = selector.select(profile)

        # Should return default model for task type
        assert model == "minimax/minimax-m2:free"  # DEFAULT_MODELS[VERIFY]

    def test_filter_by_context_size(self, tmp_path):
        """Models with insufficient context are filtered."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Add model with limited context
        store.update_ranking(ModelRanking(
            model_id="qwen/qwen-2.5-72b-instruct:free",  # 32K context limit
            task_type="heavy",
            quality_score=0.9,
            success_rate=0.95,
        ))
        store.update_ranking(ModelRanking(
            model_id="google/gemini-3-flash-preview",  # 1M context
            task_type="heavy",
            quality_score=0.85,
            success_rate=0.9,
        ))

        selector = ModelSelector(store)
        profile = TaskProfile(
            task_type=TaskType.HEAVY,
            context_size=100_000,  # Exceeds qwen's 32K limit
        )

        model = selector.select(profile)
        assert model == "google/gemini-3-flash-preview"

    def test_explain_selection(self, tmp_path):
        """explain_selection provides selection details."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        store.update_ranking(ModelRanking(
            model_id="test/model",
            task_type="verify",
            quality_score=0.9,
            success_rate=0.95,
        ))

        selector = ModelSelector(store)
        profile = TaskProfile(task_type=TaskType.VERIFY)

        explanation = selector.explain_selection(profile)

        assert "task_type" in explanation
        assert "selected" in explanation
        assert "sort_priority" in explanation

    def test_get_candidates(self, tmp_path):
        """get_candidates returns sorted candidate list."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        for i in range(10):
            store.update_ranking(ModelRanking(
                model_id=f"model-{i}",
                task_type="code",
                quality_score=0.5 + i * 0.05,
            ))

        selector = ModelSelector(store)
        candidates = selector.get_candidates(
            TaskProfile(task_type=TaskType.CODE),
            limit=5,
        )

        assert len(candidates) == 5


# =============================================================================
# Test FeedbackCollector
# =============================================================================

class TestFeedbackCollector:
    """Tests for FeedbackCollector."""

    def test_record_feedback(self, tmp_path):
        """Recording feedback updates rankings."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=850,
            tokens_used=450,
            quality_score=0.92,
            cost_usd=0.0,
        )

        updated = collector.record(feedback)

        assert updated.model_id == "test/model"
        assert updated.success_rate == 1.0
        assert updated.sample_count == 1

    def test_ema_update_calculation(self, tmp_path):
        """EMA updates weight recent feedback."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)

        # Record initial feedbacks to establish baseline
        for i in range(10):
            collector.record(TaskFeedback(
                task_id=f"task-{i}",
                model_id="test/model",
                task_type="verify",
                success=True,
                latency_ms=1000,
                tokens_used=500,
                quality_score=0.8,
                cost_usd=0.0,
            ))

        # Record a significantly different feedback
        updated = collector.record(TaskFeedback(
            task_id="task-new",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=500,  # Much faster
            tokens_used=250,  # Half the tokens
            quality_score=0.95,  # Higher quality
            cost_usd=0.0,
        ))

        # EMA should move toward new values but not fully
        assert updated.average_latency_ms < 1000
        assert updated.average_latency_ms > 500
        assert updated.quality_score > 0.8
        assert updated.quality_score < 0.95

    def test_get_recent_feedback(self, tmp_path):
        """get_recent returns recent feedback entries."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)

        # Record multiple feedbacks
        for i in range(15):
            collector.record(TaskFeedback(
                task_id=f"task-{i}",
                model_id="test/model",
                task_type="verify",
                success=True,
                latency_ms=1000,
                tokens_used=500,
                quality_score=0.8,
                cost_usd=0.0,
            ))

        recent = collector.get_recent("test/model", limit=10)
        assert len(recent) == 10

    def test_record_batch(self, tmp_path):
        """record_batch updates all feedbacks efficiently."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)

        feedbacks = [
            TaskFeedback(
                task_id=f"task-{i}",
                model_id="test/model",
                task_type="verify",
                success=True,
                latency_ms=1000 + i * 100,
                tokens_used=500,
                quality_score=0.8,
                cost_usd=0.0,
            )
            for i in range(5)
        ]

        updated = collector.record_batch(feedbacks)
        assert len(updated) == 5
        assert updated[-1].sample_count == 5


# =============================================================================
# Test update_ranking_from_feedback
# =============================================================================

class TestUpdateRankingFromFeedback:
    """Tests for update_ranking_from_feedback function."""

    def test_success_rate_update(self):
        """Success rate updates with EMA."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            success_rate=0.8,
            sample_count=10,
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=0.9,
            cost_usd=0.0,
        )

        updated = update_ranking_from_feedback(ranking, feedback)

        # Success rate should increase (was 0.8, feedback is success=True)
        assert updated.success_rate > ranking.success_rate
        assert updated.success_rate <= 1.0
        assert updated.sample_count == 11

    def test_latency_averaging(self):
        """Latency updates via EMA."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            average_latency_ms=1000,
            sample_count=10,
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=500,  # Much faster
            tokens_used=500,
            quality_score=0.9,
            cost_usd=0.0,
        )

        updated = update_ranking_from_feedback(ranking, feedback)

        # Latency should decrease toward 500
        assert updated.average_latency_ms < 1000
        assert updated.average_latency_ms > 500  # EMA, not instant

    def test_quality_score_ema(self):
        """Quality score updates via EMA."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            quality_score=0.7,
            sample_count=10,
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=0.95,  # Higher quality
            cost_usd=0.0,
        )

        updated = update_ranking_from_feedback(ranking, feedback)

        # Quality should increase toward 0.95
        assert updated.quality_score > 0.7
        assert updated.quality_score < 0.95

    def test_cost_tracking(self):
        """Cost updates via EMA."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            cost_per_task=0.001,
            sample_count=10,
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=0.9,
            cost_usd=0.002,  # Higher cost
        )

        updated = update_ranking_from_feedback(ranking, feedback)

        # Cost should increase toward 0.002
        assert updated.cost_per_task > 0.001
        assert updated.cost_per_task < 0.002

    def test_first_samples_use_simple_average(self):
        """First MIN_SAMPLES_FOR_EMA use simple averaging."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            success_rate=1.0,
            quality_score=0.9,
            sample_count=2,  # Below MIN_SAMPLES_FOR_EMA
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=False,  # Failure
            latency_ms=1000,
            tokens_used=500,
            quality_score=0.3,  # Low quality
            cost_usd=0.0,
        )

        updated = update_ranking_from_feedback(ranking, feedback)

        # Simple average: (1.0*2 + 0) / 3 = 0.667
        assert 0.6 < updated.success_rate < 0.7

    def test_model_mismatch_raises(self):
        """Mismatched model IDs raise ValueError."""
        ranking = ModelRanking(
            model_id="model-a",
            task_type="verify",
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="model-b",  # Different!
            task_type="verify",
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=0.9,
            cost_usd=0.0,
        )

        with pytest.raises(ValueError, match="Model ID mismatch"):
            update_ranking_from_feedback(ranking, feedback)

    def test_task_type_mismatch_raises(self):
        """Mismatched task types raise ValueError."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="reasoning",  # Different!
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=0.9,
            cost_usd=0.0,
        )

        with pytest.raises(ValueError, match="Task type mismatch"):
            update_ranking_from_feedback(ranking, feedback)


# =============================================================================
# Integration Tests
# =============================================================================

class TestRankingIntegration:
    """End-to-end integration tests."""

    def test_feedback_updates_improve_selection(self, tmp_path):
        """Recording good feedback improves model ranking."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)
        selector = ModelSelector(store)

        # Add two models with similar initial rankings
        store.update_ranking(ModelRanking(
            model_id="model-a",
            task_type="verify",
            quality_score=0.8,
            success_rate=0.8,
            average_latency_ms=1000,
            sample_count=5,
        ))
        store.update_ranking(ModelRanking(
            model_id="model-b",
            task_type="verify",
            quality_score=0.8,
            success_rate=0.8,
            average_latency_ms=1000,
            sample_count=5,
        ))

        # Record consistently good feedback for model-a
        for i in range(10):
            collector.record(TaskFeedback(
                task_id=f"task-{i}",
                model_id="model-a",
                task_type="verify",
                success=True,
                latency_ms=500,  # Faster
                tokens_used=400,
                quality_score=0.95,  # Higher quality
                cost_usd=0.0,
            ))

        # Record mediocre feedback for model-b
        for i in range(10):
            collector.record(TaskFeedback(
                task_id=f"task-b-{i}",
                model_id="model-b",
                task_type="verify",
                success=i % 2 == 0,  # 50% success
                latency_ms=1500,  # Slower
                tokens_used=600,
                quality_score=0.6,
                cost_usd=0.001,
            ))

        # Model-a should now be preferred
        profile = TaskProfile(task_type=TaskType.VERIFY)
        selected = selector.select(profile)

        assert selected == "model-a"

    def test_full_workflow(self, tmp_path):
        """Full workflow: profile -> select -> execute -> feedback -> update."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)
        selector = ModelSelector(store)

        # 1. Create task profile
        profile = TaskProfile(
            task_type=TaskType.VERIFY,
            complexity="simple",
            latency_sensitive=True,
        )

        # 2. Select model (falls back to default since no rankings)
        model = selector.select(profile)
        assert model is not None

        # 3. Simulate execution and record feedback
        feedback = TaskFeedback(
            task_id="exec-001",
            model_id=model,
            task_type="verify",
            success=True,
            latency_ms=750,
            tokens_used=400,
            quality_score=0.88,
            cost_usd=0.0,
        )
        ranking = collector.record(feedback)

        # 4. Verify ranking was updated
        assert ranking.sample_count == 1
        assert ranking.success_rate == 1.0

        # 5. Save and verify persistence
        store.save()
        store.clear_cache()
        loaded = store.get_ranking(model, "verify")
        assert loaded is not None
        assert loaded.sample_count == 1

    def test_select_model_convenience_function(self, tmp_path):
        """select_model() convenience function works."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        store.update_ranking(ModelRanking(
            model_id="quick-model",
            task_type="verify",
            quality_score=0.9,
            average_latency_ms=300,
        ))

        profile = TaskProfile(
            task_type=TaskType.VERIFY,
            latency_sensitive=True,
        )

        model = select_model(profile, store)
        assert model == "quick-model"


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_rankings_file(self, tmp_path):
        """Handle empty YAML file."""
        path = tmp_path / "rankings.yaml"
        path.write_text("")

        store = RankingsStore(path)
        rankings = store.load()

        assert rankings == {}

    def test_corrupted_yaml_file(self, tmp_path):
        """Handle corrupted YAML file gracefully."""
        path = tmp_path / "rankings.yaml"
        path.write_text("{{{{not valid yaml")

        store = RankingsStore(path)
        rankings = store.load()

        assert rankings == {}  # Graceful degradation

    def test_zero_decay_factor(self):
        """Zero decay factor uses only new observation."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            quality_score=0.5,
            sample_count=10,
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=1.0,
            cost_usd=0.0,
        )

        updated = update_ranking_from_feedback(ranking, feedback, decay_factor=0.0)

        # With decay=0, new value should be fully used
        assert updated.quality_score == 1.0

    def test_one_decay_factor(self):
        """Decay factor of 1.0 preserves old value."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
            quality_score=0.5,
            sample_count=10,
        )

        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=1.0,
            cost_usd=0.0,
        )

        updated = update_ranking_from_feedback(ranking, feedback, decay_factor=1.0)

        # With decay=1, old value should be preserved
        assert updated.quality_score == 0.5

    def test_invalid_decay_factor_raises(self):
        """Invalid decay factor raises ValueError."""
        ranking = ModelRanking(
            model_id="test/model",
            task_type="verify",
        )
        feedback = TaskFeedback(
            task_id="task-1",
            model_id="test/model",
            task_type="verify",
            success=True,
            latency_ms=1000,
            tokens_used=500,
            quality_score=0.9,
            cost_usd=0.0,
        )

        with pytest.raises(ValueError, match="decay_factor must be 0.0-1.0"):
            update_ranking_from_feedback(ranking, feedback, decay_factor=1.5)

    def test_concurrent_updates(self, tmp_path):
        """Multiple updates in sequence work correctly."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Simulate concurrent updates
        for i in range(100):
            store.update_ranking(ModelRanking(
                model_id=f"model-{i % 5}",  # 5 different models
                task_type="verify",
                quality_score=0.5 + (i % 10) * 0.05,
                sample_count=i + 1,
            ))

        store.save()
        all_rankings = store.get_all_rankings()

        assert len(all_rankings) == 5
