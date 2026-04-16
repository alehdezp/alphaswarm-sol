"""Confidence bounds calculation and management.

Based on R7.2 research: Bayesian calibration with Wilson score intervals.

Key design decisions:
1. Use Bayesian updating for small sample handling
2. Wilson score interval for bound calculation
3. Absolute limits (0.15 min, 0.98 max) prevent runaway
4. Prior strength of 2.0 balances responsiveness vs stability
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from alphaswarm_sol.learning.types import ConfidenceBounds, PatternBaseline


def wilson_score_interval(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Calculate Wilson score confidence interval.

    More accurate than normal approximation for small samples
    and proportions near 0 or 1.

    Args:
        successes: Number of successes (true positives)
        trials: Total trials (TP + FP)
        confidence: Confidence level (default 95%)

    Returns:
        (lower_bound, upper_bound) tuple
    """
    if trials == 0:
        return (0.0, 1.0)

    # Z-score for confidence level
    z_scores = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    z = z_scores.get(confidence, 1.96)

    n = trials
    p = successes / n

    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)

    return (lower, upper)


def bayesian_confidence(
    true_positives: int,
    false_positives: int,
    prior_strength: float = 2.0,
    prior_probability: float = 0.5,
) -> float:
    """Calculate calibrated confidence using Bayesian updating.

    With small samples, this pulls toward the prior.
    With large samples, it approaches raw precision.

    Args:
        true_positives: Number of confirmed TPs
        false_positives: Number of confirmed FPs
        prior_strength: Pseudo-observation count (higher = more conservative)
        prior_probability: Prior belief about TP rate

    Returns:
        Calibrated confidence value
    """
    # Add pseudo-observations
    effective_tp = true_positives + prior_strength * prior_probability
    effective_fp = false_positives + prior_strength * (1 - prior_probability)

    total = effective_tp + effective_fp
    if total == 0:
        return prior_probability

    return effective_tp / total


def calculate_bounds(
    baseline: PatternBaseline,
    confidence_level: float = 0.95,
    absolute_min: float = 0.15,
    absolute_max: float = 0.98,
) -> ConfidenceBounds:
    """Calculate confidence bounds from baseline data.

    Strategy:
    - Use Wilson score interval for statistical bounds
    - Apply absolute limits to prevent extreme values
    - Use observed precision as initial confidence

    Args:
        baseline: Pattern baseline metrics
        confidence_level: Statistical confidence level
        absolute_min: Absolute minimum bound
        absolute_max: Absolute maximum bound

    Returns:
        ConfidenceBounds for the pattern
    """
    # For patterns with insufficient data, use conservative defaults
    if baseline.sample_size < 5:
        return ConfidenceBounds.default(baseline.pattern_id)

    # Calculate Wilson score interval
    tp = baseline.true_positives
    fp = baseline.false_positives
    total = tp + fp

    if total == 0:
        return ConfidenceBounds.default(baseline.pattern_id)

    lower, upper = wilson_score_interval(tp, total, confidence_level)

    # Apply absolute limits
    lower = max(absolute_min, lower)
    upper = min(absolute_max, upper)

    # Initial confidence is the observed precision, bounded
    initial = max(lower, min(upper, baseline.precision))

    return ConfidenceBounds(
        pattern_id=baseline.pattern_id,
        lower_bound=round(lower, 4),
        upper_bound=round(upper, 4),
        initial=round(initial, 4),
        observed_precision=round(baseline.precision, 4),
        sample_size=baseline.sample_size,
    )


class BoundsManager:
    """Manage confidence bounds for all patterns.

    Provides:
    - Loading/saving bounds from JSON
    - Default bounds for unknown patterns
    - Bound lookup by pattern ID
    """

    def __init__(
        self,
        bounds_path: Path | None = None,
        absolute_min: float = 0.15,
        absolute_max: float = 0.98,
    ):
        """Initialize bounds manager.

        Args:
            bounds_path: Path to bounds JSON file
            absolute_min: Absolute minimum for any bound
            absolute_max: Absolute maximum for any bound
        """
        self.bounds_path = bounds_path
        self.absolute_min = absolute_min
        self.absolute_max = absolute_max
        self._bounds: dict[str, ConfidenceBounds] = {}

        if bounds_path and bounds_path.exists():
            self.load()

    def get(self, pattern_id: str) -> ConfidenceBounds:
        """Get bounds for a pattern, or default if unknown."""
        if pattern_id in self._bounds:
            return self._bounds[pattern_id]
        return ConfidenceBounds.default(pattern_id)

    def set(self, bounds: ConfidenceBounds) -> None:
        """Set bounds for a pattern."""
        self._bounds[bounds.pattern_id] = bounds

    def clamp(self, pattern_id: str, value: float) -> float:
        """Clamp a value to the bounds for a pattern."""
        bounds = self.get(pattern_id)
        return bounds.clamp(value)

    def load(self) -> None:
        """Load bounds from JSON file."""
        if not self.bounds_path or not self.bounds_path.exists():
            return

        with open(self.bounds_path, "r") as f:
            data = json.load(f)

        for pattern_id, bounds_data in data.items():
            self._bounds[pattern_id] = ConfidenceBounds.from_dict(bounds_data)

    def save(self) -> None:
        """Save bounds to JSON file."""
        if not self.bounds_path:
            return

        self.bounds_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            pattern_id: bounds.to_dict()
            for pattern_id, bounds in self._bounds.items()
        }

        with open(self.bounds_path, "w") as f:
            json.dump(data, f, indent=2)

    def all_bounds(self) -> dict[str, ConfidenceBounds]:
        """Get all stored bounds."""
        return dict(self._bounds)

    def update_from_baselines(
        self,
        baselines: dict[str, PatternBaseline],
        confidence_level: float = 0.95,
    ) -> None:
        """Update bounds from baseline data.

        Args:
            baselines: Pattern baselines to compute bounds from
            confidence_level: Statistical confidence level
        """
        for pattern_id, baseline in baselines.items():
            bounds = calculate_bounds(
                baseline,
                confidence_level=confidence_level,
                absolute_min=self.absolute_min,
                absolute_max=self.absolute_max,
            )
            self._bounds[pattern_id] = bounds

    def summary(self) -> str:
        """Generate a summary of all bounds."""
        lines = ["Pattern Confidence Bounds Summary", "=" * 50]

        for pattern_id, bounds in sorted(self._bounds.items()):
            lines.append(
                f"{pattern_id}: [{bounds.lower_bound:.2f}, {bounds.upper_bound:.2f}] "
                f"initial={bounds.initial:.2f} (n={bounds.sample_size})"
            )

        return "\n".join(lines)
