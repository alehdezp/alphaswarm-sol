"""Tests for learning decay module.

Task 7.2: Time-based decay for learning adjustments.
"""

from __future__ import annotations

import math
import unittest
from datetime import datetime, timedelta
from typing import List, Tuple

from alphaswarm_sol.learning.decay import (
    DecayConfig,
    DecayCalculator,
    LN2,
    get_decay_calculator,
    apply_decay,
    is_relevant,
    time_weighted_confidence,
)


class TestDecayConfig(unittest.TestCase):
    """Test decay configuration."""

    def test_default_config(self):
        """Default config has 30-day half-life."""
        config = DecayConfig()
        self.assertEqual(config.half_life_days, 30.0)
        self.assertEqual(config.min_factor, 0.01)
        self.assertEqual(config.max_age_days, 180.0)

    def test_custom_config(self):
        """Can create custom config."""
        config = DecayConfig(
            half_life_days=14.0,
            min_factor=0.05,
            max_age_days=90.0,
        )
        self.assertEqual(config.half_life_days, 14.0)
        self.assertEqual(config.min_factor, 0.05)
        self.assertEqual(config.max_age_days, 90.0)

    def test_invalid_half_life_raises(self):
        """Half-life must be positive."""
        with self.assertRaises(ValueError):
            DecayConfig(half_life_days=0)
        with self.assertRaises(ValueError):
            DecayConfig(half_life_days=-1)

    def test_invalid_min_factor_raises(self):
        """Min factor must be between 0 and 1."""
        with self.assertRaises(ValueError):
            DecayConfig(min_factor=-0.1)
        with self.assertRaises(ValueError):
            DecayConfig(min_factor=1.5)

    def test_invalid_max_age_raises(self):
        """Max age must be positive."""
        with self.assertRaises(ValueError):
            DecayConfig(max_age_days=0)
        with self.assertRaises(ValueError):
            DecayConfig(max_age_days=-30)


class TestDecayCalculator(unittest.TestCase):
    """Test decay calculator."""

    def setUp(self):
        """Set up test calculator."""
        self.calc = DecayCalculator()
        self.now = datetime(2026, 1, 8, 12, 0, 0)

    def test_current_event_full_weight(self):
        """Event at current time has weight 1.0."""
        factor = self.calc.calculate_factor(self.now, self.now)
        self.assertEqual(factor, 1.0)

    def test_half_life_gives_half_weight(self):
        """Event at half-life has weight ~0.5."""
        event_time = self.now - timedelta(days=30)
        factor = self.calc.calculate_factor(event_time, self.now)
        self.assertAlmostEqual(factor, 0.5, places=4)

    def test_double_half_life_gives_quarter_weight(self):
        """Event at 2x half-life has weight ~0.25."""
        event_time = self.now - timedelta(days=60)
        factor = self.calc.calculate_factor(event_time, self.now)
        self.assertAlmostEqual(factor, 0.25, places=4)

    def test_future_event_full_weight(self):
        """Future events get full weight."""
        event_time = self.now + timedelta(days=10)
        factor = self.calc.calculate_factor(event_time, self.now)
        self.assertEqual(factor, 1.0)

    def test_very_old_event_zero_weight(self):
        """Events beyond max_age get zero weight."""
        event_time = self.now - timedelta(days=200)
        factor = self.calc.calculate_factor(event_time, self.now)
        self.assertEqual(factor, 0.0)

    def test_event_at_max_age_boundary(self):
        """Events at exactly max_age boundary."""
        # At exactly 180 days, the comparison is > max_age, not >=
        # So 180 days is not beyond the boundary yet
        event_time = self.now - timedelta(days=180)
        factor = self.calc.calculate_factor(event_time, self.now)
        # Exactly at max_age: still within bounds (due to > comparison)
        self.assertGreater(factor, 0.0)

        # Just beyond max_age is zero
        event_time = self.now - timedelta(days=181)
        factor = self.calc.calculate_factor(event_time, self.now)
        self.assertEqual(factor, 0.0)

    def test_min_factor_threshold(self):
        """Factor below min_factor becomes zero."""
        # With 30-day half-life and min_factor=0.01
        # factor = 0.01 when t = -ln(0.01) / k = -ln(0.01) * 30 / ln(2) ≈ 199 days
        # So at ~150 days, factor should be around 0.03
        event_time = self.now - timedelta(days=150)
        factor = self.calc.calculate_factor(event_time, self.now)
        self.assertGreater(factor, 0.0)

        # At 200 days, below threshold (or beyond max_age)
        event_time = self.now - timedelta(days=200)
        factor = self.calc.calculate_factor(event_time, self.now)
        self.assertEqual(factor, 0.0)

    def test_apply_decay_positive(self):
        """Apply decay to positive adjustment."""
        event_time = self.now - timedelta(days=30)
        result = self.calc.apply_decay(0.02, event_time, self.now)
        self.assertAlmostEqual(result, 0.01, places=4)

    def test_apply_decay_negative(self):
        """Apply decay to negative adjustment (FP penalty)."""
        event_time = self.now - timedelta(days=30)
        result = self.calc.apply_decay(-0.05, event_time, self.now)
        self.assertAlmostEqual(result, -0.025, places=4)

    def test_apply_decay_zero_for_old_event(self):
        """Old events get zero adjustment."""
        event_time = self.now - timedelta(days=200)
        result = self.calc.apply_decay(0.02, event_time, self.now)
        self.assertEqual(result, 0.0)

    def test_is_relevant_current(self):
        """Current events are relevant."""
        self.assertTrue(self.calc.is_relevant(self.now, self.now))

    def test_is_relevant_recent(self):
        """Recent events are relevant."""
        event_time = self.now - timedelta(days=60)
        self.assertTrue(self.calc.is_relevant(event_time, self.now))

    def test_is_relevant_old_event(self):
        """Old events are not relevant."""
        event_time = self.now - timedelta(days=200)
        self.assertFalse(self.calc.is_relevant(event_time, self.now))

    def test_days_until_negligible_default(self):
        """Calculate days until 1% weight."""
        days = self.calc.days_until_negligible(0.01)
        # factor = exp(-k * t) = 0.01
        # t = -ln(0.01) / k = -ln(0.01) * half_life / ln(2)
        expected = -math.log(0.01) * 30 / LN2
        self.assertAlmostEqual(days, expected, places=2)

    def test_days_until_negligible_custom(self):
        """Calculate days until 5% weight."""
        days = self.calc.days_until_negligible(0.05)
        expected = -math.log(0.05) * 30 / LN2
        self.assertAlmostEqual(days, expected, places=2)

    def test_days_until_negligible_invalid(self):
        """Invalid thresholds raise ValueError."""
        with self.assertRaises(ValueError):
            self.calc.days_until_negligible(0)
        with self.assertRaises(ValueError):
            self.calc.days_until_negligible(1)
        with self.assertRaises(ValueError):
            self.calc.days_until_negligible(1.5)

    def test_effective_weight_sum_empty(self):
        """Empty event list gives zero sum."""
        total = self.calc.effective_weight_sum([], self.now)
        self.assertEqual(total, 0.0)

    def test_effective_weight_sum_current(self):
        """Current events sum to their count."""
        events = [self.now, self.now, self.now]
        total = self.calc.effective_weight_sum(events, self.now)
        self.assertEqual(total, 3.0)

    def test_effective_weight_sum_mixed(self):
        """Mixed age events sum correctly."""
        events = [
            self.now,  # factor=1.0
            self.now - timedelta(days=30),  # factor=0.5
            self.now - timedelta(days=60),  # factor=0.25
        ]
        total = self.calc.effective_weight_sum(events, self.now)
        self.assertAlmostEqual(total, 1.75, places=2)

    def test_half_life_property(self):
        """Half-life property returns config value."""
        self.assertEqual(self.calc.half_life_days, 30.0)


class TestCustomConfig(unittest.TestCase):
    """Test calculator with custom config."""

    def test_shorter_half_life(self):
        """Shorter half-life decays faster."""
        config = DecayConfig(half_life_days=7.0)
        calc = DecayCalculator(config)
        now = datetime(2026, 1, 8, 12, 0, 0)

        # At 7 days, factor should be 0.5
        event_time = now - timedelta(days=7)
        factor = calc.calculate_factor(event_time, now)
        self.assertAlmostEqual(factor, 0.5, places=4)

        # At 30 days, factor should be much lower
        event_time = now - timedelta(days=30)
        factor = calc.calculate_factor(event_time, now)
        self.assertLess(factor, 0.06)  # ~0.05 with 7-day half-life

    def test_longer_half_life(self):
        """Longer half-life decays slower."""
        config = DecayConfig(half_life_days=60.0)
        calc = DecayCalculator(config)
        now = datetime(2026, 1, 8, 12, 0, 0)

        # At 30 days, factor should be > 0.5
        event_time = now - timedelta(days=30)
        factor = calc.calculate_factor(event_time, now)
        self.assertGreater(factor, 0.7)

        # At 60 days, factor should be 0.5
        event_time = now - timedelta(days=60)
        factor = calc.calculate_factor(event_time, now)
        self.assertAlmostEqual(factor, 0.5, places=4)


class TestTimeWeightedConfidence(unittest.TestCase):
    """Test time-weighted confidence calculation."""

    def setUp(self):
        """Set up test time."""
        self.now = datetime(2026, 1, 8, 12, 0, 0)

    def test_no_events_returns_prior(self):
        """With no events, returns prior probability."""
        conf = time_weighted_confidence([], now=self.now)
        self.assertEqual(conf, 0.5)

    def test_no_events_custom_prior(self):
        """Custom prior is respected."""
        conf = time_weighted_confidence(
            [], prior_probability=0.7, now=self.now
        )
        self.assertEqual(conf, 0.7)

    def test_all_tp_increases_confidence(self):
        """All true positives increase confidence."""
        events: List[Tuple[datetime, bool]] = [
            (self.now, True),
            (self.now, True),
            (self.now, True),
        ]
        conf = time_weighted_confidence(events, now=self.now)
        self.assertGreater(conf, 0.5)

    def test_all_fp_decreases_confidence(self):
        """All false positives decrease confidence."""
        events: List[Tuple[datetime, bool]] = [
            (self.now, False),
            (self.now, False),
            (self.now, False),
        ]
        conf = time_weighted_confidence(events, now=self.now)
        self.assertLess(conf, 0.5)

    def test_old_events_less_impact(self):
        """Older events have less impact than recent."""
        recent_events: List[Tuple[datetime, bool]] = [
            (self.now, True),
            (self.now, True),
        ]
        old_events: List[Tuple[datetime, bool]] = [
            (self.now - timedelta(days=60), True),
            (self.now - timedelta(days=60), True),
        ]

        recent_conf = time_weighted_confidence(recent_events, now=self.now)
        old_conf = time_weighted_confidence(old_events, now=self.now)

        # Recent events should have stronger effect
        self.assertGreater(recent_conf, old_conf)

    def test_prior_strength_effect(self):
        """Higher prior strength resists change more."""
        events: List[Tuple[datetime, bool]] = [
            (self.now, True),
            (self.now, True),
        ]

        low_prior_conf = time_weighted_confidence(
            events, prior_strength=1.0, now=self.now
        )
        high_prior_conf = time_weighted_confidence(
            events, prior_strength=10.0, now=self.now
        )

        # With higher prior strength, confidence moves less
        # Both should be > 0.5 (all TP), but high_prior closer to 0.5
        self.assertGreater(low_prior_conf, high_prior_conf)

    def test_mixed_events(self):
        """Mixed events balance out."""
        events: List[Tuple[datetime, bool]] = [
            (self.now, True),
            (self.now, False),
        ]
        conf = time_weighted_confidence(
            events, prior_strength=0, prior_probability=0.5, now=self.now
        )
        # With zero prior and equal TP/FP, should be exactly 0.5
        self.assertAlmostEqual(conf, 0.5, places=4)


class TestConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions."""

    def test_get_decay_calculator_singleton(self):
        """get_decay_calculator returns singleton."""
        calc1 = get_decay_calculator()
        calc2 = get_decay_calculator()
        self.assertIs(calc1, calc2)

    def test_apply_decay_function(self):
        """Module-level apply_decay works."""
        now = datetime.now()
        event_time = now - timedelta(days=30)
        result = apply_decay(0.02, event_time)
        # Should be approximately 0.01 (half of 0.02)
        self.assertAlmostEqual(result, 0.01, delta=0.002)

    def test_is_relevant_function_current(self):
        """Module-level is_relevant for current event."""
        self.assertTrue(is_relevant(datetime.now()))

    def test_is_relevant_function_old(self):
        """Module-level is_relevant for old event."""
        old_event = datetime.now() - timedelta(days=200)
        self.assertFalse(is_relevant(old_event))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_exactly_zero_days_ago(self):
        """Event exactly 0 days ago."""
        calc = DecayCalculator()
        now = datetime.now()
        factor = calc.calculate_factor(now, now)
        self.assertEqual(factor, 1.0)

    def test_very_small_time_difference(self):
        """Very small time difference."""
        calc = DecayCalculator()
        now = datetime.now()
        event = now - timedelta(seconds=1)
        factor = calc.calculate_factor(event, now)
        self.assertAlmostEqual(factor, 1.0, places=6)

    def test_exactly_at_max_age(self):
        """Event exactly at max_age boundary."""
        config = DecayConfig(max_age_days=180)
        calc = DecayCalculator(config)
        now = datetime.now()
        event = now - timedelta(days=180)
        factor = calc.calculate_factor(event, now)
        # At exactly max_age (due to > comparison), still has weight
        self.assertGreater(factor, 0.0)

        # Just beyond max_age is zero
        event = now - timedelta(days=181)
        factor = calc.calculate_factor(event, now)
        self.assertEqual(factor, 0.0)

    def test_just_before_max_age(self):
        """Event just before max_age."""
        config = DecayConfig(max_age_days=180, min_factor=0.001)
        calc = DecayCalculator(config)
        now = datetime.now()
        event = now - timedelta(days=179)
        factor = calc.calculate_factor(event, now)
        # Should still have some weight
        self.assertGreater(factor, 0.0)

    def test_exponential_decay_formula(self):
        """Verify exponential decay formula is correct."""
        calc = DecayCalculator()
        now = datetime.now()

        # factor = exp(-k * t) where k = ln(2) / half_life
        # At t = half_life, factor = exp(-ln(2)) = 1/2
        event = now - timedelta(days=30)
        factor = calc.calculate_factor(event, now)
        expected = math.exp(-LN2)
        self.assertAlmostEqual(factor, expected, places=6)


if __name__ == "__main__":
    unittest.main()
