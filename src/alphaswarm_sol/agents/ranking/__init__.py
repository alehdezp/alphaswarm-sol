"""Model Ranking System for Continuous Optimization.

This package provides the ranking and feedback system for model selection:
- TaskProfile: Define task requirements for model selection
- ModelRanking: Track model performance per task type
- TaskFeedback: Capture execution feedback
- ModelSelector: Select best model based on rankings
- RankingsStore: Persistent YAML storage for rankings
- FeedbackCollector: Collect and process feedback

Per 05.3-CONTEXT.md:
- Rankings update via EMA after each execution
- Recent feedback weighted more heavily via decay factor
- Rankings stored in .vrs/rankings/rankings.yaml
- Selector prioritizes based on: latency, quality, or cost

Integration:
- ModelSelector is used by OpenCodeRuntime._select_model()
- Integrated into PropulsionEngine via TaskRouter (Plan 08)
- Flow: PropulsionEngine -> TaskRouter -> ModelSelector -> RankingsStore

Usage:
    from alphaswarm_sol.agents.ranking import (
        # Schemas
        TaskProfile,
        ModelRanking,
        TaskFeedback,
        Complexity,
        # Selector
        ModelSelector,
        select_model,
        # Store
        RankingsStore,
        # Feedback
        FeedbackCollector,
        update_ranking_from_feedback,
    )

    # Select model based on task profile
    store = RankingsStore()
    selector = ModelSelector(store)
    model = selector.select(TaskProfile(
        task_type=TaskType.VERIFY,
        complexity="simple",
        latency_sensitive=True,
    ))

    # Record feedback after execution
    collector = FeedbackCollector(store)
    collector.record(TaskFeedback(
        task_id="task-123",
        model_id=model,
        task_type="verify",
        success=True,
        latency_ms=850,
        tokens_used=450,
        quality_score=0.92,
        cost_usd=0.0,
    ))
"""

from .schemas import (
    Complexity,
    TaskProfile,
    ModelRanking,
    TaskFeedback,
)

from .store import RankingsStore

from .selector import (
    ModelSelector,
    select_model,
    DEFAULT_MODEL,
)

from .feedback import (
    FeedbackCollector,
    update_ranking_from_feedback,
    DEFAULT_DECAY_FACTOR,
)


__all__ = [
    # Schemas
    "Complexity",
    "TaskProfile",
    "ModelRanking",
    "TaskFeedback",
    # Store
    "RankingsStore",
    # Selector
    "ModelSelector",
    "select_model",
    "DEFAULT_MODEL",
    # Feedback
    "FeedbackCollector",
    "update_ranking_from_feedback",
    "DEFAULT_DECAY_FACTOR",
]
