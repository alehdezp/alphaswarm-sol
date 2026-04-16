"""Time-based decay for learning adjustments.

Implements exponential decay so old learning events have diminishing influence.
This prevents stale data from permanently affecting pattern confidence.

Key design decisions (from R7.2):
- 30-day half-life by default
- Events older than 180 days are ignored
- Minimum threshold prevents very small weights
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

# Natural log of 2 - used for half-life calculations
LN2 = 0.693147180559945


@dataclass
class DecayConfig:
    """Configuration for decay calculations.

    Attributes:
        half_life_days: Days until adjustment weight is halved (default 30)
        min_factor: Minimum decay factor - below this, treat as 0 (default 0.01)
        max_age_days: Events older than this are completely ignored (default 180)
    """

    half_life_days: float = 30.0
    min_factor: float = 0.01
    max_age_days: float = 180.0

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.half_life_days <= 0:
            raise ValueError("half_life_days must be positive")
        if self.min_factor < 0 or self.min_factor > 1:
            raise ValueError("min_factor must be between 0 and 1")
        if self.max_age_days <= 0:
            raise ValueError("max_age_days must be positive")


class DecayCalculator:
    """Calculate time-based decay factors for learning events.

    Uses exponential decay: factor = exp(-k * t)
    where k = ln(2) / half_life_days

    This ensures that after half_life_days, the factor is exactly 0.5.
    """

    def __init__(self, config: Optional[DecayConfig] = None):
        """Initialize decay calculator.

        Args:
            config: Decay configuration (uses defaults if None)
        """
        self.config = config or DecayConfig()
        # Decay constant k = ln(2) / half_life
        self._decay_constant = LN2 / self.config.half_life_days

    @property
    def half_life_days(self) -> float:
        """Get the configured half-life in days."""
        return self.config.half_life_days

    def calculate_factor(
        self,
        event_time: datetime,
        now: Optional[datetime] = None,
    ) -> float:
        """Calculate decay factor for an event.

        Args:
            event_time: When the event occurred
            now: Current time (defaults to datetime.now())

        Returns:
            Decay factor between 0.0 and 1.0
            - 1.0 for current events
            - 0.5 at half_life_days
            - 0.0 for events beyond max_age_days or below min_factor
        """
        now = now or datetime.now()

        # Calculate age in days
        age_seconds = (now - event_time).total_seconds()
        age_days = age_seconds / 86400.0

        # Future events get full weight
        if age_days < 0:
            return 1.0

        # Events beyond max age are ignored
        if age_days > self.config.max_age_days:
            return 0.0

        # Calculate exponential decay
        factor = math.exp(-self._decay_constant * age_days)

        # Apply minimum threshold
        if factor < self.config.min_factor:
            return 0.0

        return factor

    def apply_decay(
        self,
        base_adjustment: float,
        event_time: datetime,
        now: Optional[datetime] = None,
    ) -> float:
        """Apply decay to an adjustment value.

        Args:
            base_adjustment: Original adjustment (e.g., -0.05 for FP)
            event_time: When the event occurred
            now: Current time (defaults to datetime.now())

        Returns:
            Decayed adjustment value
        """
        factor = self.calculate_factor(event_time, now)
        return base_adjustment * factor

    def is_relevant(
        self,
        event_time: datetime,
        now: Optional[datetime] = None,
    ) -> bool:
        """Check if an event is still relevant (not fully decayed).

        Args:
            event_time: When the event occurred
            now: Current time

        Returns:
            True if the event still has non-zero weight
        """
        return self.calculate_factor(event_time, now) > 0.0

    def days_until_negligible(self, threshold: float = 0.01) -> float:
        """Calculate days until factor falls below threshold.

        Args:
            threshold: Factor threshold (default 0.01 = 1%)

        Returns:
            Number of days until decay factor < threshold
        """
        if threshold <= 0 or threshold >= 1:
            raise ValueError("threshold must be between 0 and 1")
        # factor = exp(-k * t)
        # threshold = exp(-k * t)
        # ln(threshold) = -k * t
        # t = -ln(threshold) / k
        return -math.log(threshold) / self._decay_constant

    def effective_weight_sum(
        self,
        event_times: List[datetime],
        now: Optional[datetime] = None,
    ) -> float:
        """Calculate sum of decay-weighted events.

        Useful for computing effective sample size.

        Args:
            event_times: List of event timestamps
            now: Current time

        Returns:
            Sum of decay factors for all events
        """
        return sum(self.calculate_factor(t, now) for t in event_times)


def time_weighted_confidence(
    events: List[tuple[datetime, bool]],
    prior_strength: float = 2.0,
    prior_probability: float = 0.5,
    half_life_days: float = 30.0,
    now: Optional[datetime] = None,
) -> float:
    """Calculate time-weighted confidence from events.

    Combines Bayesian updating with time decay.

    Args:
        events: List of (timestamp, is_true_positive) tuples
        prior_strength: Pseudo-observation count
        prior_probability: Prior belief about TP rate
        half_life_days: Days until event weight halves
        now: Current time

    Returns:
        Calibrated confidence value between 0 and 1
    """
    now = now or datetime.now()
    calculator = DecayCalculator(DecayConfig(half_life_days=half_life_days))

    # Start with prior pseudo-observations
    effective_tp = prior_strength * prior_probability
    effective_fp = prior_strength * (1 - prior_probability)

    # Add weighted events
    for event_time, is_tp in events:
        weight = calculator.calculate_factor(event_time, now)
        if is_tp:
            effective_tp += weight
        else:
            effective_fp += weight

    total = effective_tp + effective_fp
    if total == 0:
        return prior_probability

    return effective_tp / total


# Default calculator instance
_default_calculator: Optional[DecayCalculator] = None


def get_decay_calculator() -> DecayCalculator:
    """Get the default decay calculator singleton.

    Returns:
        Default DecayCalculator instance
    """
    global _default_calculator
    if _default_calculator is None:
        _default_calculator = DecayCalculator()
    return _default_calculator


def apply_decay(adjustment: float, event_time: datetime) -> float:
    """Convenience function to apply decay with default calculator.

    Args:
        adjustment: Base adjustment value
        event_time: When the event occurred

    Returns:
        Decayed adjustment value
    """
    return get_decay_calculator().apply_decay(adjustment, event_time)


def is_relevant(event_time: datetime) -> bool:
    """Convenience function to check if event is still relevant.

    Args:
        event_time: When the event occurred

    Returns:
        True if event still has non-zero weight
    """
    return get_decay_calculator().is_relevant(event_time)
