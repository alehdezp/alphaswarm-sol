"""Persistent Storage for Model Rankings.

This module provides YAML-based persistent storage for model rankings:
- Load rankings from .vrs/rankings/rankings.yaml
- Save rankings with atomic write
- CRUD operations for individual rankings
- Query rankings by model and task type

Per 05.3-CONTEXT.md:
- Rankings stored in YAML format (human-readable, git-friendly)
- Project-level storage in .vrs/rankings/
- Latest only - single file with current rankings

Usage:
    from alphaswarm_sol.agents.ranking.store import RankingsStore
    from alphaswarm_sol.agents.ranking.schemas import ModelRanking

    # Load/save rankings
    store = RankingsStore()
    rankings = store.load()

    # Get specific ranking
    ranking = store.get_ranking("minimax/minimax-m2:free", "verify")

    # Update ranking
    store.update_ranking(ModelRanking(
        model_id="minimax/minimax-m2:free",
        task_type="verify",
        success_rate=0.95,
        ...
    ))

    # Reset all rankings
    store.reset()
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import ModelRanking

logger = logging.getLogger(__name__)


# Default rankings file path
DEFAULT_RANKINGS_PATH = Path(".vrs/rankings/rankings.yaml")


class RankingsStore:
    """Persistent storage for model rankings.

    Stores rankings in YAML format at .vrs/rankings/rankings.yaml.
    Rankings are organized by task type, with each task type containing
    a list of model rankings sorted by composite score.

    File format:
        ```yaml
        version: 1
        updated: 2026-01-21T12:00:00
        rankings:
          verify:
            - model_id: minimax/minimax-m2:free
              success_rate: 0.95
              average_latency_ms: 850
              ...
          reasoning:
            - model_id: deepseek/deepseek-v3.2
              ...
        ```

    Attributes:
        path: Path to the rankings YAML file
        _cache: In-memory cache of loaded rankings
        _dirty: Whether cache has unsaved changes

    Examples:
        # Default path
        store = RankingsStore()

        # Custom path
        store = RankingsStore(Path("/custom/path/rankings.yaml"))

        # Load and query
        rankings = store.load()
        verify_ranking = store.get_ranking("minimax/minimax-m2:free", "verify")
    """

    def __init__(self, path: Optional[Path] = None):
        """Initialize rankings store.

        Args:
            path: Path to rankings YAML file. If None, uses default
                 .vrs/rankings/rankings.yaml
        """
        self.path = path or DEFAULT_RANKINGS_PATH
        self._cache: Optional[Dict[str, Dict[str, ModelRanking]]] = None
        self._dirty: bool = False

    def _ensure_directory(self) -> None:
        """Ensure the parent directory exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Dict[str, ModelRanking]]:
        """Load rankings from YAML file.

        Returns:
            Dictionary mapping task_type -> model_id -> ModelRanking.
            Returns empty dict if file doesn't exist.

        Note:
            Results are cached. Call reset() to clear cache.
        """
        if self._cache is not None:
            return self._cache

        self._cache = {}

        if not self.path.exists():
            logger.debug(f"Rankings file not found: {self.path}")
            return self._cache

        try:
            import yaml

            with open(self.path, "r") as f:
                data = yaml.safe_load(f) or {}

            # Parse rankings by task type
            rankings_data = data.get("rankings", {})
            for task_type, model_rankings in rankings_data.items():
                self._cache[task_type] = {}
                for ranking_dict in model_rankings:
                    if isinstance(ranking_dict, dict):
                        ranking = ModelRanking.from_dict(ranking_dict)
                        self._cache[task_type][ranking.model_id] = ranking

            logger.debug(
                f"Loaded {sum(len(r) for r in self._cache.values())} rankings "
                f"from {self.path}"
            )

        except Exception as e:
            logger.warning(f"Failed to load rankings from {self.path}: {e}")
            self._cache = {}

        return self._cache

    def save(self, rankings: Optional[Dict[str, Dict[str, ModelRanking]]] = None) -> None:
        """Save rankings to YAML file.

        Args:
            rankings: Rankings to save. If None, saves current cache.

        Note:
            Uses atomic write (write to temp file, then rename) to prevent
            data corruption on crash.
        """
        if rankings is not None:
            self._cache = rankings

        if self._cache is None:
            logger.warning("No rankings to save")
            return

        self._ensure_directory()

        try:
            import yaml

            # Build output structure
            output = {
                "version": 1,
                "updated": datetime.utcnow().isoformat(),
                "rankings": {},
            }

            for task_type, model_rankings in self._cache.items():
                output["rankings"][task_type] = [
                    ranking.to_dict()
                    for ranking in sorted(
                        model_rankings.values(),
                        key=lambda r: r.score(),
                        reverse=True,  # Best first
                    )
                ]

            # Atomic write
            temp_path = self.path.with_suffix(".yaml.tmp")
            with open(temp_path, "w") as f:
                yaml.dump(output, f, default_flow_style=False, sort_keys=False)

            temp_path.rename(self.path)
            self._dirty = False

            logger.debug(
                f"Saved {sum(len(r) for r in self._cache.values())} rankings "
                f"to {self.path}"
            )

        except Exception as e:
            logger.error(f"Failed to save rankings to {self.path}: {e}")
            raise

    def get_ranking(self, model_id: str, task_type: str) -> Optional[ModelRanking]:
        """Get ranking for a specific model and task type.

        Args:
            model_id: Model identifier (e.g., "minimax/minimax-m2:free")
            task_type: Task type (e.g., "verify")

        Returns:
            ModelRanking if found, None otherwise
        """
        rankings = self.load()
        task_rankings = rankings.get(task_type, {})
        return task_rankings.get(model_id)

    def get_rankings_for_task(self, task_type: str) -> List[ModelRanking]:
        """Get all rankings for a task type, sorted by score.

        Args:
            task_type: Task type (e.g., "verify")

        Returns:
            List of ModelRanking sorted by composite score (best first)
        """
        rankings = self.load()
        task_rankings = rankings.get(task_type, {})
        return sorted(
            task_rankings.values(),
            key=lambda r: r.score(),
            reverse=True,
        )

    def update_ranking(self, ranking: ModelRanking) -> None:
        """Update or create a ranking entry.

        Args:
            ranking: ModelRanking to update/create
        """
        rankings = self.load()

        if ranking.task_type not in rankings:
            rankings[ranking.task_type] = {}

        rankings[ranking.task_type][ranking.model_id] = ranking
        self._dirty = True
        self._cache = rankings

        logger.debug(
            f"Updated ranking: {ranking.model_id} for {ranking.task_type} "
            f"(score={ranking.score():.3f})"
        )

    def remove_ranking(self, model_id: str, task_type: str) -> bool:
        """Remove a ranking entry.

        Args:
            model_id: Model identifier
            task_type: Task type

        Returns:
            True if ranking was removed, False if not found
        """
        rankings = self.load()

        if task_type in rankings and model_id in rankings[task_type]:
            del rankings[task_type][model_id]
            if not rankings[task_type]:
                del rankings[task_type]
            self._dirty = True
            self._cache = rankings
            logger.debug(f"Removed ranking: {model_id} for {task_type}")
            return True

        return False

    def get_all_rankings(self) -> List[ModelRanking]:
        """Get all rankings across all task types.

        Returns:
            List of all ModelRanking entries
        """
        rankings = self.load()
        all_rankings = []
        for task_rankings in rankings.values():
            all_rankings.extend(task_rankings.values())
        return all_rankings

    def get_best_model(self, task_type: str) -> Optional[str]:
        """Get the best model ID for a task type.

        Args:
            task_type: Task type (e.g., "verify")

        Returns:
            Model ID of best-ranked model, or None if no rankings
        """
        rankings = self.get_rankings_for_task(task_type)
        if rankings:
            return rankings[0].model_id
        return None

    def get_top_models(self, task_type: str, n: int = 3) -> List[str]:
        """Get top N model IDs for a task type.

        Args:
            task_type: Task type
            n: Number of top models to return

        Returns:
            List of model IDs, best first
        """
        rankings = self.get_rankings_for_task(task_type)
        return [r.model_id for r in rankings[:n]]

    def reset(self) -> None:
        """Reset all rankings and clear cache."""
        self._cache = {}
        self._dirty = True

        if self.path.exists():
            try:
                self.path.unlink()
                logger.info(f"Deleted rankings file: {self.path}")
            except Exception as e:
                logger.warning(f"Failed to delete rankings file: {e}")

    def clear_cache(self) -> None:
        """Clear in-memory cache without deleting file."""
        self._cache = None
        self._dirty = False

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes.

        Returns:
            True if cache has been modified since last save
        """
        return self._dirty

    def exists(self) -> bool:
        """Check if rankings file exists.

        Returns:
            True if rankings file exists on disk
        """
        return self.path.exists()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored rankings.

        Returns:
            Dictionary with ranking statistics
        """
        rankings = self.load()
        total_rankings = sum(len(r) for r in rankings.values())
        task_types = list(rankings.keys())

        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "total_rankings": total_rankings,
            "task_types": task_types,
            "task_type_counts": {
                task_type: len(model_rankings)
                for task_type, model_rankings in rankings.items()
            },
            "has_unsaved_changes": self._dirty,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RankingsStore",
    "DEFAULT_RANKINGS_PATH",
]
