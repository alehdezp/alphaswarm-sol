"""Model Selection Algorithm for Task Routing.

This module provides the ModelSelector for choosing the best model based on
task profile and rankings:
- Filter by capability (context size, tools)
- Filter by accuracy threshold if critical
- Sort by priority: latency, quality, or cost
- Return top model or default

Per 05.3-CONTEXT.md:
- Used by OpenCodeRuntime._select_model()
- Integrated into PropulsionEngine via TaskRouter (Plan 08)
- Flow: PropulsionEngine -> TaskRouter -> ModelSelector -> RankingsStore

Usage:
    from alphaswarm_sol.agents.ranking import (
        ModelSelector,
        select_model,
        TaskProfile,
        RankingsStore,
    )
    from alphaswarm_sol.agents.runtime.types import TaskType

    # Full selector usage
    store = RankingsStore()
    selector = ModelSelector(store)
    model = selector.select(TaskProfile(
        task_type=TaskType.VERIFY,
        complexity="simple",
        context_size=5000,
        latency_sensitive=True,
    ))

    # Convenience function
    model = select_model(TaskProfile(
        task_type=TaskType.REASONING,
        accuracy_critical=True,
    ))
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from alphaswarm_sol.agents.runtime.types import (
    TaskType,
    DEFAULT_MODELS,
    MODEL_CONTEXT_LIMITS,
    get_context_limit,
)

from .schemas import TaskProfile, ModelRanking, Complexity
from .store import RankingsStore

logger = logging.getLogger(__name__)


# Default model when no rankings available
DEFAULT_MODEL = "google/gemini-3-flash-preview"

# Minimum success rate for accuracy-critical tasks
ACCURACY_THRESHOLD = 0.85

# Minimum quality score for accuracy-critical tasks
QUALITY_THRESHOLD = 0.80


class ModelSelector:
    """Select best model based on task profile and rankings.

    Used by OpenCodeRuntime._select_model() and integrated into
    PropulsionEngine via TaskRouter (Plan 08).

    Selection Priority:
        1. Filter by capability (context size, tools)
        2. Filter by accuracy threshold if critical
        3. Sort by:
           - latency_sensitive: latency first
           - accuracy_critical: quality first
           - Otherwise: cost first
        4. Return top model or default

    Attributes:
        store: RankingsStore for loading rankings
        _default_model: Fallback model when no rankings

    Examples:
        # Create selector
        selector = ModelSelector(RankingsStore())

        # Select for latency-sensitive task
        model = selector.select(TaskProfile(
            task_type=TaskType.VERIFY,
            latency_sensitive=True,
        ))

        # Select for accuracy-critical task
        model = selector.select(TaskProfile(
            task_type=TaskType.REASONING_HEAVY,
            accuracy_critical=True,
        ))

        # Get candidate models
        candidates = selector.get_candidates(TaskProfile(
            task_type=TaskType.CODE,
            context_size=50000,
        ))
    """

    def __init__(
        self,
        store: RankingsStore,
        default_model: str = DEFAULT_MODEL,
    ):
        """Initialize model selector.

        Args:
            store: RankingsStore for loading rankings
            default_model: Fallback model when no suitable rankings
        """
        self.store = store
        self._default_model = default_model

    def select(self, profile: TaskProfile) -> str:
        """Select best model for task.

        Priority:
            1. Filter by capability (context size, tools)
            2. Filter by accuracy threshold if critical
            3. Sort by:
               - latency_sensitive: latency first
               - accuracy_critical: quality first
               - Otherwise: cost first
            4. Return top model or default

        Args:
            profile: TaskProfile defining task requirements

        Returns:
            Model ID of the best model for the task
        """
        task_type_str = profile.task_type.value

        # Get rankings for this task type
        rankings = self.store.get_rankings_for_task(task_type_str)

        if not rankings:
            logger.debug(
                f"No rankings for task type '{task_type_str}', "
                f"using default model"
            )
            return self._get_default_for_task(profile.task_type)

        # Step 1: Filter by capabilities
        candidates = self._filter_by_capabilities(rankings, profile)

        if not candidates:
            logger.debug(
                f"No models meet capability requirements for {task_type_str}, "
                f"using default"
            )
            return self._get_default_for_task(profile.task_type)

        # Step 2: Filter by accuracy if critical
        if profile.accuracy_critical:
            candidates = self._filter_by_accuracy(candidates)

            if not candidates:
                logger.debug(
                    f"No models meet accuracy threshold for {task_type_str}, "
                    f"using best available"
                )
                # Fall back to original filtered candidates
                candidates = self._filter_by_capabilities(rankings, profile)

        # Step 3: Sort by priority
        sorted_candidates = self._sort_by_priority(candidates, profile)

        # Step 4: Return top model
        best = sorted_candidates[0]
        logger.info(
            f"Selected model '{best.model_id}' for task type '{task_type_str}' "
            f"(score={best.score():.3f})"
        )
        return best.model_id

    def _get_default_for_task(self, task_type: TaskType) -> str:
        """Get default model for a task type.

        Args:
            task_type: The task type

        Returns:
            Default model ID from DEFAULT_MODELS or global default
        """
        model = DEFAULT_MODELS.get(task_type, self._default_model)

        # Handle special values
        if model in ("claude", "codex"):
            return self._default_model

        return model

    def _filter_by_capabilities(
        self,
        rankings: List[ModelRanking],
        profile: TaskProfile,
    ) -> List[ModelRanking]:
        """Filter models by capability requirements.

        Args:
            rankings: List of model rankings
            profile: Task profile with requirements

        Returns:
            Filtered list of rankings meeting requirements
        """
        filtered = []

        for ranking in rankings:
            model_id = ranking.model_id

            # Check context size requirement
            if profile.context_size > 0:
                context_limit = get_context_limit(model_id)
                if profile.context_size > context_limit:
                    logger.debug(
                        f"Model {model_id} excluded: context {profile.context_size} "
                        f"> limit {context_limit}"
                    )
                    continue

            # Note: requires_tools filtering would go here if we had
            # a registry of model capabilities. For now, all models
            # are assumed to support basic tool use.

            filtered.append(ranking)

        return filtered

    def _filter_by_accuracy(
        self,
        rankings: List[ModelRanking],
    ) -> List[ModelRanking]:
        """Filter models by accuracy requirements.

        Args:
            rankings: List of model rankings

        Returns:
            Filtered list meeting accuracy thresholds
        """
        filtered = []

        for ranking in rankings:
            # Check success rate threshold
            if ranking.success_rate < ACCURACY_THRESHOLD:
                logger.debug(
                    f"Model {ranking.model_id} excluded: "
                    f"success_rate {ranking.success_rate:.2f} < {ACCURACY_THRESHOLD}"
                )
                continue

            # Check quality score threshold
            if ranking.quality_score < QUALITY_THRESHOLD:
                logger.debug(
                    f"Model {ranking.model_id} excluded: "
                    f"quality_score {ranking.quality_score:.2f} < {QUALITY_THRESHOLD}"
                )
                continue

            filtered.append(ranking)

        return filtered

    def _sort_by_priority(
        self,
        rankings: List[ModelRanking],
        profile: TaskProfile,
    ) -> List[ModelRanking]:
        """Sort rankings by profile priority.

        Args:
            rankings: List of model rankings
            profile: Task profile with priority flags

        Returns:
            Sorted list (best first)
        """
        if profile.latency_sensitive:
            # Sort by latency (lowest first)
            return sorted(rankings, key=lambda r: r.average_latency_ms)

        if profile.accuracy_critical:
            # Sort by quality score (highest first)
            return sorted(rankings, key=lambda r: -r.quality_score)

        # Default: sort by cost (lowest first)
        return sorted(rankings, key=lambda r: r.cost_per_task)

    def get_candidates(
        self,
        profile: TaskProfile,
        limit: int = 5,
    ) -> List[ModelRanking]:
        """Get candidate models for a task profile.

        Useful for debugging and understanding model selection.

        Args:
            profile: TaskProfile defining task requirements
            limit: Maximum number of candidates to return

        Returns:
            List of ModelRanking candidates sorted by priority
        """
        task_type_str = profile.task_type.value
        rankings = self.store.get_rankings_for_task(task_type_str)

        if not rankings:
            return []

        candidates = self._filter_by_capabilities(rankings, profile)

        if profile.accuracy_critical:
            accurate = self._filter_by_accuracy(candidates)
            if accurate:
                candidates = accurate

        sorted_candidates = self._sort_by_priority(candidates, profile)
        return sorted_candidates[:limit]

    def get_model_score(
        self,
        model_id: str,
        task_type: TaskType,
    ) -> Optional[float]:
        """Get the composite score for a model and task type.

        Args:
            model_id: Model identifier
            task_type: Task type

        Returns:
            Composite score or None if no ranking
        """
        ranking = self.store.get_ranking(model_id, task_type.value)
        if ranking:
            return ranking.score()
        return None

    def explain_selection(self, profile: TaskProfile) -> Dict[str, any]:
        """Explain the model selection process.

        Useful for debugging and understanding why a model was selected.

        Args:
            profile: TaskProfile for selection

        Returns:
            Dictionary with selection explanation
        """
        task_type_str = profile.task_type.value
        rankings = self.store.get_rankings_for_task(task_type_str)

        # Step through selection process
        all_models = [r.model_id for r in rankings]
        filtered = self._filter_by_capabilities(rankings, profile)
        filtered_models = [r.model_id for r in filtered]

        accuracy_filtered = None
        if profile.accuracy_critical:
            accuracy_filtered = self._filter_by_accuracy(filtered)
            accuracy_models = [r.model_id for r in (accuracy_filtered or [])]
        else:
            accuracy_models = filtered_models

        final_candidates = accuracy_filtered if accuracy_filtered else filtered
        sorted_candidates = self._sort_by_priority(final_candidates, profile)

        return {
            "task_type": task_type_str,
            "profile": profile.to_dict(),
            "all_rankings_count": len(rankings),
            "all_models": all_models,
            "after_capability_filter": filtered_models,
            "after_accuracy_filter": accuracy_models if profile.accuracy_critical else None,
            "sort_priority": (
                "latency" if profile.latency_sensitive
                else "quality" if profile.accuracy_critical
                else "cost"
            ),
            "final_order": [r.model_id for r in sorted_candidates],
            "selected": sorted_candidates[0].model_id if sorted_candidates else self._get_default_for_task(profile.task_type),
        }


# =============================================================================
# Convenience Function
# =============================================================================

def select_model(
    profile: TaskProfile,
    store: Optional[RankingsStore] = None,
) -> str:
    """Convenience function to select a model.

    Creates a ModelSelector with the given or default store and selects
    the best model for the profile.

    Args:
        profile: TaskProfile defining task requirements
        store: Optional RankingsStore. If None, uses default path.

    Returns:
        Model ID of the best model for the task

    Examples:
        # Simple selection
        model = select_model(TaskProfile(
            task_type=TaskType.VERIFY,
            latency_sensitive=True,
        ))

        # With custom store
        model = select_model(
            TaskProfile(task_type=TaskType.CODE),
            store=RankingsStore(Path("/custom/rankings.yaml")),
        )
    """
    if store is None:
        store = RankingsStore()

    selector = ModelSelector(store)
    return selector.select(profile)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ModelSelector",
    "select_model",
    "DEFAULT_MODEL",
    "ACCURACY_THRESHOLD",
    "QUALITY_THRESHOLD",
]
