"""Feedback Collection and EMA-Based Ranking Updates.

This module provides feedback processing for model rankings:
- update_ranking_from_feedback: EMA-based ranking updates
- FeedbackCollector: Collect and process execution feedback

Per 05.3-CONTEXT.md:
- Rankings update via EMA after each execution
- Recent feedback weighted more heavily via decay factor
- Feedback recorded automatically after each execution

EMA (Exponential Moving Average) Formula:
    new_value = decay * old_value + (1 - decay) * observation

With decay=0.95, recent observations contribute 5% to the new value,
providing gradual adaptation while maintaining stability.

Usage:
    from alphaswarm_sol.agents.ranking import (
        FeedbackCollector,
        update_ranking_from_feedback,
        TaskFeedback,
        ModelRanking,
        RankingsStore,
    )

    # Update ranking from feedback
    updated = update_ranking_from_feedback(ranking, feedback)

    # Use collector for automatic storage updates
    store = RankingsStore()
    collector = FeedbackCollector(store)
    collector.record(TaskFeedback(...))
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from .schemas import ModelRanking, TaskFeedback
from .store import RankingsStore

logger = logging.getLogger(__name__)


# Default EMA decay factor
# 0.95 means recent feedback contributes 5% to the updated value
DEFAULT_DECAY_FACTOR = 0.95

# Minimum sample count before decay applies
# First N samples use simple averaging
MIN_SAMPLES_FOR_EMA = 5


def update_ranking_from_feedback(
    ranking: ModelRanking,
    feedback: TaskFeedback,
    decay_factor: float = DEFAULT_DECAY_FACTOR,
) -> ModelRanking:
    """Update ranking using EMA (exponential moving average).

    Recent feedback is weighted more heavily via the decay factor.
    For the first MIN_SAMPLES_FOR_EMA samples, simple averaging is used
    to establish a baseline before switching to EMA.

    EMA Formula:
        new_value = decay * old_value + (1 - decay) * observation

    Args:
        ranking: Current ModelRanking to update
        feedback: TaskFeedback from execution
        decay_factor: EMA decay factor (0.0-1.0). Higher values give more
                     weight to historical data. Default: 0.95

    Returns:
        Updated ModelRanking with new metrics

    Examples:
        # Update with default decay
        updated = update_ranking_from_feedback(ranking, feedback)

        # Use higher decay for more stability
        updated = update_ranking_from_feedback(ranking, feedback, decay_factor=0.98)

        # Use lower decay for faster adaptation
        updated = update_ranking_from_feedback(ranking, feedback, decay_factor=0.90)
    """
    if not 0.0 <= decay_factor <= 1.0:
        raise ValueError(f"decay_factor must be 0.0-1.0, got {decay_factor}")

    # Verify matching model and task type
    if ranking.model_id != feedback.model_id:
        raise ValueError(
            f"Model ID mismatch: ranking={ranking.model_id}, "
            f"feedback={feedback.model_id}"
        )
    if ranking.task_type != feedback.task_type:
        raise ValueError(
            f"Task type mismatch: ranking={ranking.task_type}, "
            f"feedback={feedback.task_type}"
        )

    new_sample_count = ranking.sample_count + 1

    # Use simple averaging for first few samples to establish baseline
    if ranking.sample_count < MIN_SAMPLES_FOR_EMA:
        # Simple weighted average
        weight = 1.0 / new_sample_count

        new_success_rate = (
            ranking.success_rate * ranking.sample_count + (1.0 if feedback.success else 0.0)
        ) / new_sample_count

        new_latency = int(
            (ranking.average_latency_ms * ranking.sample_count + feedback.latency_ms)
            / new_sample_count
        )

        new_tokens = int(
            (ranking.average_tokens * ranking.sample_count + feedback.tokens_used)
            / new_sample_count
        )

        new_quality = (
            ranking.quality_score * ranking.sample_count + feedback.quality_score
        ) / new_sample_count

        new_cost = (
            ranking.cost_per_task * ranking.sample_count + feedback.cost_usd
        ) / new_sample_count

    else:
        # EMA update: new = decay * old + (1 - decay) * observation
        alpha = 1.0 - decay_factor

        new_success_rate = (
            decay_factor * ranking.success_rate
            + alpha * (1.0 if feedback.success else 0.0)
        )

        new_latency = int(
            decay_factor * ranking.average_latency_ms
            + alpha * feedback.latency_ms
        )

        new_tokens = int(
            decay_factor * ranking.average_tokens
            + alpha * feedback.tokens_used
        )

        new_quality = (
            decay_factor * ranking.quality_score
            + alpha * feedback.quality_score
        )

        new_cost = (
            decay_factor * ranking.cost_per_task
            + alpha * feedback.cost_usd
        )

    # Clamp values to valid ranges
    new_success_rate = max(0.0, min(1.0, new_success_rate))
    new_quality = max(0.0, min(1.0, new_quality))
    new_latency = max(0, new_latency)
    new_tokens = max(0, new_tokens)
    new_cost = max(0.0, new_cost)

    logger.debug(
        f"Updated ranking for {ranking.model_id}/{ranking.task_type}: "
        f"success={new_success_rate:.3f}, latency={new_latency}ms, "
        f"quality={new_quality:.3f}, samples={new_sample_count}"
    )

    return ModelRanking(
        model_id=ranking.model_id,
        task_type=ranking.task_type,
        success_rate=new_success_rate,
        average_latency_ms=new_latency,
        average_tokens=new_tokens,
        quality_score=new_quality,
        cost_per_task=new_cost,
        sample_count=new_sample_count,
        last_updated=datetime.utcnow(),
    )


def create_initial_ranking(feedback: TaskFeedback) -> ModelRanking:
    """Create initial ranking from first feedback.

    Args:
        feedback: First execution feedback

    Returns:
        New ModelRanking with values from feedback
    """
    return ModelRanking(
        model_id=feedback.model_id,
        task_type=feedback.task_type,
        success_rate=1.0 if feedback.success else 0.0,
        average_latency_ms=feedback.latency_ms,
        average_tokens=feedback.tokens_used,
        quality_score=feedback.quality_score,
        cost_per_task=feedback.cost_usd,
        sample_count=1,
        last_updated=datetime.utcnow(),
    )


class FeedbackCollector:
    """Collect and process execution feedback.

    Automatically updates rankings in the store when feedback is recorded.

    Attributes:
        store: RankingsStore for persisting rankings
        _recent_feedback: In-memory buffer of recent feedback
        _max_recent: Maximum recent feedback to keep per model

    Examples:
        # Create collector
        store = RankingsStore()
        collector = FeedbackCollector(store)

        # Record feedback (auto-updates rankings)
        collector.record(TaskFeedback(
            task_id="verify-123",
            model_id="minimax/minimax-m2:free",
            task_type="verify",
            success=True,
            latency_ms=850,
            tokens_used=450,
            quality_score=0.92,
            cost_usd=0.0,
        ))

        # Get recent feedback for a model
        recent = collector.get_recent("minimax/minimax-m2:free", limit=10)
    """

    def __init__(
        self,
        store: RankingsStore,
        max_recent: int = 100,
        decay_factor: float = DEFAULT_DECAY_FACTOR,
        auto_save: bool = True,
    ):
        """Initialize feedback collector.

        Args:
            store: RankingsStore for persisting rankings
            max_recent: Maximum recent feedback per model to keep in memory
            decay_factor: EMA decay factor for ranking updates
            auto_save: Whether to auto-save rankings after updates
        """
        self.store = store
        self._max_recent = max_recent
        self._decay_factor = decay_factor
        self._auto_save = auto_save
        self._recent_feedback: dict[str, list[TaskFeedback]] = {}

    def record(self, feedback: TaskFeedback) -> ModelRanking:
        """Record feedback and update rankings.

        Args:
            feedback: TaskFeedback from execution

        Returns:
            Updated ModelRanking
        """
        # Store in recent buffer
        key = f"{feedback.model_id}:{feedback.task_type}"
        if key not in self._recent_feedback:
            self._recent_feedback[key] = []

        self._recent_feedback[key].append(feedback)

        # Trim to max recent
        if len(self._recent_feedback[key]) > self._max_recent:
            self._recent_feedback[key] = self._recent_feedback[key][-self._max_recent:]

        # Get existing ranking or create initial
        existing = self.store.get_ranking(feedback.model_id, feedback.task_type)

        if existing is None:
            updated = create_initial_ranking(feedback)
        else:
            updated = update_ranking_from_feedback(
                existing,
                feedback,
                decay_factor=self._decay_factor,
            )

        # Update store
        self.store.update_ranking(updated)

        # Auto-save if enabled
        if self._auto_save:
            self.store.save()

        logger.info(
            f"Recorded feedback for {feedback.model_id}/{feedback.task_type}: "
            f"success={feedback.success}, score={updated.score():.3f}"
        )

        return updated

    def record_batch(self, feedbacks: List[TaskFeedback]) -> List[ModelRanking]:
        """Record multiple feedback entries.

        More efficient than individual record() calls when auto_save is enabled,
        as it saves only once at the end.

        Args:
            feedbacks: List of TaskFeedback to record

        Returns:
            List of updated ModelRanking
        """
        # Temporarily disable auto-save
        original_auto_save = self._auto_save
        self._auto_save = False

        try:
            updated = [self.record(feedback) for feedback in feedbacks]
        finally:
            self._auto_save = original_auto_save

        # Save once at end
        if original_auto_save:
            self.store.save()

        return updated

    def get_recent(
        self,
        model_id: str,
        task_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[TaskFeedback]:
        """Get recent feedback for a model.

        Args:
            model_id: Model identifier
            task_type: Optional task type filter
            limit: Maximum number of feedback entries to return

        Returns:
            List of recent TaskFeedback, newest first
        """
        results = []

        for key, feedbacks in self._recent_feedback.items():
            if key.startswith(model_id):
                if task_type is None or key == f"{model_id}:{task_type}":
                    results.extend(feedbacks)

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda f: f.timestamp, reverse=True)

        return results[:limit]

    def get_success_rate(
        self,
        model_id: str,
        task_type: str,
        window: int = 10,
    ) -> Optional[float]:
        """Get recent success rate for a model.

        Args:
            model_id: Model identifier
            task_type: Task type
            window: Number of recent executions to consider

        Returns:
            Success rate 0.0-1.0, or None if no recent feedback
        """
        recent = self.get_recent(model_id, task_type, limit=window)

        if not recent:
            return None

        successes = sum(1 for f in recent if f.success)
        return successes / len(recent)

    def clear_recent(self, model_id: Optional[str] = None) -> None:
        """Clear recent feedback buffer.

        Args:
            model_id: Optional model ID to clear. If None, clears all.
        """
        if model_id is None:
            self._recent_feedback.clear()
        else:
            keys_to_remove = [
                key for key in self._recent_feedback
                if key.startswith(model_id)
            ]
            for key in keys_to_remove:
                del self._recent_feedback[key]

    def get_stats(self) -> dict:
        """Get collector statistics.

        Returns:
            Dictionary with collector statistics
        """
        total_entries = sum(len(f) for f in self._recent_feedback.values())
        models = set(key.split(":")[0] for key in self._recent_feedback.keys())

        return {
            "total_recent_entries": total_entries,
            "models_tracked": len(models),
            "task_type_keys": len(self._recent_feedback),
            "max_recent": self._max_recent,
            "decay_factor": self._decay_factor,
            "auto_save": self._auto_save,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "update_ranking_from_feedback",
    "create_initial_ranking",
    "FeedbackCollector",
    "DEFAULT_DECAY_FACTOR",
    "MIN_SAMPLES_FOR_EMA",
]
