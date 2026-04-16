"""Tests for learning module bootstrap data generation.

Task 7.0: Verify bootstrap data generation works correctly.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from alphaswarm_sol.learning.types import (
    PatternBaseline,
    ConfidenceBounds,
    LearningEvent,
    EventType,
    SimilarityKey,
    SimilarityTier,
)
from alphaswarm_sol.learning.bootstrap import (
    BootstrapGenerator,
    generate_bootstrap_data,
    load_manifest,
)
from alphaswarm_sol.learning.bounds import (
    BoundsManager,
    calculate_bounds,
    wilson_score_interval,
    bayesian_confidence,
)
from alphaswarm_sol.learning.similarity import (
    SimilarityEngine,
    extract_guards,
    hash_guards,
)


class TestPatternBaseline(unittest.TestCase):
    """Test PatternBaseline dataclass."""

    def test_create_baseline(self) -> None:
        """Can create a pattern baseline."""
        baseline = PatternBaseline(
            pattern_id="vm-001",
            true_positives=10,
            false_positives=2,
            false_negatives=1,
            precision=0.83,
            recall=0.91,
            f1_score=0.87,
            sample_size=13,
        )
        self.assertEqual(baseline.pattern_id, "vm-001")
        self.assertEqual(baseline.precision, 0.83)
        self.assertEqual(baseline.sample_size, 13)

    def test_to_dict(self) -> None:
        """Can serialize to dict."""
        baseline = PatternBaseline(
            pattern_id="auth-001",
            true_positives=8,
            false_positives=2,
            false_negatives=0,
            precision=0.80,
            recall=1.0,
            f1_score=0.889,
            sample_size=10,
        )
        data = baseline.to_dict()
        self.assertEqual(data["pattern_id"], "auth-001")
        self.assertEqual(data["precision"], 0.8)
        self.assertIn("computed_at", data)

    def test_from_dict(self) -> None:
        """Can deserialize from dict."""
        data = {
            "pattern_id": "dos-001",
            "true_positives": 5,
            "false_positives": 1,
            "false_negatives": 2,
            "precision": 0.833,
            "recall": 0.714,
            "f1_score": 0.769,
            "sample_size": 8,
            "source": "test",
        }
        baseline = PatternBaseline.from_dict(data)
        self.assertEqual(baseline.pattern_id, "dos-001")
        self.assertEqual(baseline.true_positives, 5)
        self.assertEqual(baseline.source, "test")


class TestConfidenceBounds(unittest.TestCase):
    """Test ConfidenceBounds dataclass."""

    def test_create_bounds(self) -> None:
        """Can create confidence bounds."""
        bounds = ConfidenceBounds(
            pattern_id="vm-001",
            lower_bound=0.40,
            upper_bound=0.95,
            initial=0.80,
            observed_precision=0.80,
            sample_size=20,
        )
        self.assertEqual(bounds.pattern_id, "vm-001")
        self.assertEqual(bounds.lower_bound, 0.40)
        self.assertEqual(bounds.initial, 0.80)

    def test_clamp(self) -> None:
        """Clamp respects bounds."""
        bounds = ConfidenceBounds(
            pattern_id="test",
            lower_bound=0.30,
            upper_bound=0.90,
            initial=0.70,
            observed_precision=0.70,
        )
        self.assertEqual(bounds.clamp(0.10), 0.30)  # Below lower
        self.assertEqual(bounds.clamp(0.50), 0.50)  # Within bounds
        self.assertEqual(bounds.clamp(0.99), 0.90)  # Above upper

    def test_absolute_limits_enforced(self) -> None:
        """Absolute limits prevent extreme values."""
        bounds = ConfidenceBounds(
            pattern_id="test",
            lower_bound=0.05,  # Below absolute min
            upper_bound=1.0,   # Above absolute max
            initial=0.50,
            observed_precision=0.50,
        )
        self.assertEqual(bounds.lower_bound, 0.15)  # Enforced absolute min
        self.assertEqual(bounds.upper_bound, 0.98)  # Enforced absolute max

    def test_default_bounds(self) -> None:
        """Can create default bounds."""
        bounds = ConfidenceBounds.default("unknown-pattern")
        self.assertEqual(bounds.pattern_id, "unknown-pattern")
        self.assertEqual(bounds.lower_bound, 0.30)
        self.assertEqual(bounds.upper_bound, 0.95)
        self.assertEqual(bounds.initial, 0.70)

    def test_to_dict_from_dict(self) -> None:
        """Can round-trip through dict."""
        bounds = ConfidenceBounds(
            pattern_id="test",
            lower_bound=0.35,
            upper_bound=0.85,
            initial=0.60,
            observed_precision=0.60,
            sample_size=15,
        )
        data = bounds.to_dict()
        restored = ConfidenceBounds.from_dict(data)
        self.assertEqual(restored.pattern_id, bounds.pattern_id)
        self.assertEqual(restored.lower_bound, bounds.lower_bound)
        self.assertEqual(restored.sample_size, bounds.sample_size)


class TestSimilarityKey(unittest.TestCase):
    """Test SimilarityKey dataclass."""

    def test_create_key(self) -> None:
        """Can create a similarity key."""
        key = SimilarityKey(
            pattern_id="vm-001",
            modifier_signature="nonReentrant|onlyOwner",
            guard_hash="abc123",
        )
        self.assertEqual(key.pattern_id, "vm-001")
        self.assertIn("nonReentrant", key.modifier_signature)

    def test_exact_match(self) -> None:
        """Exact match requires all fields."""
        key1 = SimilarityKey("vm-001", "nonReentrant", "hash1")
        key2 = SimilarityKey("vm-001", "nonReentrant", "hash1")
        key3 = SimilarityKey("vm-001", "nonReentrant", "hash2")  # Different guard

        self.assertTrue(key1.matches(key2, SimilarityTier.EXACT))
        self.assertFalse(key1.matches(key3, SimilarityTier.EXACT))

    def test_structural_match(self) -> None:
        """Structural match ignores guard hash."""
        key1 = SimilarityKey("vm-001", "nonReentrant", "hash1")
        key2 = SimilarityKey("vm-001", "nonReentrant", "different_hash")
        key3 = SimilarityKey("vm-001", "different_mod", "hash1")

        self.assertTrue(key1.matches(key2, SimilarityTier.STRUCTURAL))
        self.assertFalse(key1.matches(key3, SimilarityTier.STRUCTURAL))

    def test_pattern_match(self) -> None:
        """Pattern match only checks pattern_id."""
        key1 = SimilarityKey("vm-001", "mod1", "hash1")
        key2 = SimilarityKey("vm-001", "mod2", "hash2")
        key3 = SimilarityKey("vm-002", "mod1", "hash1")

        self.assertTrue(key1.matches(key2, SimilarityTier.PATTERN))
        self.assertFalse(key1.matches(key3, SimilarityTier.PATTERN))


class TestLearningEvent(unittest.TestCase):
    """Test LearningEvent dataclass."""

    def test_create_event(self) -> None:
        """Can create a learning event."""
        key = SimilarityKey("vm-001", "mod", "hash")
        event = LearningEvent(
            id="evt-001",
            pattern_id="vm-001",
            event_type=EventType.CONFIRMED,
            timestamp=datetime.now(),
            similarity_key=key,
            finding_id="finding-123",
        )
        self.assertEqual(event.event_type, EventType.CONFIRMED)
        self.assertEqual(event.finding_id, "finding-123")

    def test_event_types(self) -> None:
        """All event types have correct values."""
        self.assertEqual(EventType.CONFIRMED.value, "confirmed")
        self.assertEqual(EventType.REJECTED.value, "rejected")
        self.assertEqual(EventType.ESCALATED.value, "escalated")
        self.assertEqual(EventType.ROLLBACK.value, "rollback")


class TestWilsonScoreInterval(unittest.TestCase):
    """Test Wilson score interval calculation."""

    def test_zero_trials(self) -> None:
        """Zero trials returns full range."""
        lower, upper = wilson_score_interval(0, 0)
        self.assertEqual(lower, 0.0)
        self.assertEqual(upper, 1.0)

    def test_all_successes(self) -> None:
        """All successes gives high upper bound."""
        lower, upper = wilson_score_interval(10, 10)
        self.assertGreater(lower, 0.6)
        self.assertEqual(upper, 1.0)

    def test_mixed_results(self) -> None:
        """Mixed results give reasonable interval."""
        lower, upper = wilson_score_interval(8, 10)  # 80% success
        self.assertGreater(lower, 0.4)
        self.assertLess(lower, 0.8)
        self.assertGreater(upper, 0.8)
        self.assertLess(upper, 1.0)

    def test_interval_contains_proportion(self) -> None:
        """Interval should contain the observed proportion."""
        for successes in [3, 7, 15]:
            for trials in [10, 20, 50]:
                if successes <= trials:
                    p = successes / trials
                    lower, upper = wilson_score_interval(successes, trials)
                    # With 95% CI, interval should usually contain p
                    self.assertLessEqual(lower, p + 0.1)
                    self.assertGreaterEqual(upper, p - 0.1)


class TestBayesianConfidence(unittest.TestCase):
    """Test Bayesian confidence calculation."""

    def test_no_data_returns_prior(self) -> None:
        """No data returns prior probability."""
        conf = bayesian_confidence(0, 0, prior_probability=0.6)
        self.assertEqual(conf, 0.6)

    def test_converges_to_precision(self) -> None:
        """With many samples, converges to raw precision."""
        # 80 TP, 20 FP = 80% precision
        conf = bayesian_confidence(80, 20)
        self.assertAlmostEqual(conf, 0.80, delta=0.02)

    def test_small_sample_pulls_to_prior(self) -> None:
        """Small sample is pulled toward prior."""
        # 2 TP, 0 FP = 100% precision, but small sample
        conf = bayesian_confidence(2, 0, prior_strength=2.0, prior_probability=0.5)
        self.assertLess(conf, 1.0)  # Pulled down from 100%
        self.assertGreater(conf, 0.5)  # But still above prior


class TestCalculateBounds(unittest.TestCase):
    """Test confidence bounds calculation from baseline."""

    def test_insufficient_data_uses_defaults(self) -> None:
        """Small sample size uses default bounds."""
        baseline = PatternBaseline(
            pattern_id="test",
            true_positives=2,
            false_positives=1,
            false_negatives=0,
            precision=0.67,
            recall=1.0,
            f1_score=0.8,
            sample_size=3,  # Below MIN_SAMPLES
        )
        bounds = calculate_bounds(baseline)
        self.assertEqual(bounds.lower_bound, 0.30)
        self.assertEqual(bounds.upper_bound, 0.95)

    def test_sufficient_data_uses_wilson(self) -> None:
        """With enough data, uses Wilson interval."""
        baseline = PatternBaseline(
            pattern_id="test",
            true_positives=16,
            false_positives=4,
            false_negatives=0,
            precision=0.80,
            recall=1.0,
            f1_score=0.89,
            sample_size=20,
        )
        bounds = calculate_bounds(baseline)
        # Should be tighter than defaults
        self.assertGreater(bounds.lower_bound, 0.30)
        self.assertLess(bounds.upper_bound, 0.95)
        # Initial should be close to precision
        self.assertAlmostEqual(bounds.initial, 0.80, delta=0.1)


class TestBoundsManager(unittest.TestCase):
    """Test BoundsManager class."""

    def test_get_unknown_returns_default(self) -> None:
        """Unknown pattern returns default bounds."""
        manager = BoundsManager()
        bounds = manager.get("unknown-pattern")
        self.assertEqual(bounds.pattern_id, "unknown-pattern")
        self.assertEqual(bounds.initial, 0.70)

    def test_set_and_get(self) -> None:
        """Can set and retrieve bounds."""
        manager = BoundsManager()
        bounds = ConfidenceBounds(
            pattern_id="test",
            lower_bound=0.40,
            upper_bound=0.90,
            initial=0.75,
            observed_precision=0.75,
        )
        manager.set(bounds)
        retrieved = manager.get("test")
        self.assertEqual(retrieved.initial, 0.75)

    def test_clamp(self) -> None:
        """Can clamp values using manager."""
        manager = BoundsManager()
        bounds = ConfidenceBounds(
            pattern_id="test",
            lower_bound=0.40,
            upper_bound=0.90,
            initial=0.70,
            observed_precision=0.70,
        )
        manager.set(bounds)

        self.assertEqual(manager.clamp("test", 0.10), 0.40)
        self.assertEqual(manager.clamp("test", 0.50), 0.50)
        self.assertEqual(manager.clamp("test", 0.99), 0.90)

    def test_save_and_load(self) -> None:
        """Can save and load bounds from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bounds.json"
            manager1 = BoundsManager(bounds_path=path)

            bounds = ConfidenceBounds(
                pattern_id="vm-001",
                lower_bound=0.35,
                upper_bound=0.85,
                initial=0.60,
                observed_precision=0.60,
            )
            manager1.set(bounds)
            manager1.save()

            # Load in new manager
            manager2 = BoundsManager(bounds_path=path)
            loaded = manager2.get("vm-001")
            self.assertEqual(loaded.initial, 0.60)


class TestExtractGuards(unittest.TestCase):
    """Test guard extraction from code."""

    def test_no_guards(self) -> None:
        """Code with no guards returns empty string."""
        code = "function withdraw() public { balance -= 1; }"
        guards = extract_guards(code)
        self.assertEqual(guards, "")

    def test_reentrancy_guard(self) -> None:
        """Detects reentrancy guards."""
        code = "function withdraw() external nonReentrant { }"
        guards = extract_guards(code)
        self.assertIn("REENTRANCY_GUARD", guards)

    def test_access_control(self) -> None:
        """Detects access control patterns."""
        code = "function setOwner(address newOwner) external onlyOwner { }"
        guards = extract_guards(code)
        self.assertIn("ACCESS_CONTROL", guards)

    def test_multiple_guards(self) -> None:
        """Detects multiple guard types."""
        code = """
        function withdraw() external nonReentrant onlyOwner whenNotPaused {
            balance -= 1;
        }
        """
        guards = extract_guards(code)
        self.assertIn("REENTRANCY_GUARD", guards)
        self.assertIn("ACCESS_CONTROL", guards)
        self.assertIn("PAUSABLE", guards)

    def test_require_msg_sender(self) -> None:
        """Detects require(msg.sender == ...) pattern."""
        code = "require(msg.sender == owner, 'Not owner');"
        guards = extract_guards(code)
        self.assertIn("ACCESS_CONTROL", guards)


class TestSimilarityEngine(unittest.TestCase):
    """Test SimilarityEngine class."""

    def test_add_and_find(self) -> None:
        """Can add keys and find similar ones."""
        engine = SimilarityEngine()
        key1 = SimilarityKey("vm-001", "nonReentrant", "hash1")
        key2 = SimilarityKey("vm-001", "nonReentrant", "hash2")
        key3 = SimilarityKey("vm-002", "nonReentrant", "hash1")

        engine.add_key(key1)
        engine.add_key(key2)
        engine.add_key(key3)

        # Find similar to key1
        matches = engine.find_similar(key1, SimilarityTier.STRUCTURAL)
        # Should find key1 and key2 (same pattern + modifiers)
        self.assertEqual(len(matches), 2)

    def test_should_transfer_fp(self) -> None:
        """FP transfer respects tier setting."""
        engine = SimilarityEngine(transfer_tier=SimilarityTier.STRUCTURAL)
        key1 = SimilarityKey("vm-001", "nonReentrant", "hash1")
        key2 = SimilarityKey("vm-001", "nonReentrant", "hash2")
        key3 = SimilarityKey("vm-001", "different", "hash1")

        self.assertTrue(engine.should_transfer_fp(key1, key2))
        self.assertFalse(engine.should_transfer_fp(key1, key3))


class TestBootstrapGenerator(unittest.TestCase):
    """Test BootstrapGenerator class."""

    def test_generate_baselines_from_manifests(self) -> None:
        """Can generate baselines from test project manifests."""
        test_projects = Path(__file__).parent / "projects"

        if not test_projects.exists():
            self.skipTest("Test projects directory not found")

        generator = BootstrapGenerator(test_projects)
        baselines = generator.generate_baselines()

        # Should find at least some patterns
        self.assertGreater(len(baselines), 0)

        # Each baseline should have valid data
        for baseline in baselines.values():
            self.assertIsInstance(baseline.pattern_id, str)
            self.assertGreaterEqual(baseline.precision, 0.0)
            self.assertLessEqual(baseline.precision, 1.0)

    def test_generate_bounds_from_baselines(self) -> None:
        """Can generate bounds from baselines."""
        generator = BootstrapGenerator(Path("."))

        # Create some test baselines
        baselines = {
            "vm-001": PatternBaseline(
                pattern_id="vm-001",
                true_positives=16,
                false_positives=4,
                false_negatives=2,
                precision=0.80,
                recall=0.89,
                f1_score=0.84,
                sample_size=22,
            ),
            "auth-001": PatternBaseline(
                pattern_id="auth-001",
                true_positives=9,
                false_positives=1,
                false_negatives=0,
                precision=0.90,
                recall=1.0,
                f1_score=0.95,
                sample_size=10,
            ),
        }

        bounds = generator.generate_confidence_bounds(baselines)

        self.assertEqual(len(bounds), 2)
        self.assertIn("vm-001", bounds)
        self.assertIn("auth-001", bounds)

        # Bounds should be reasonable
        for b in bounds.values():
            self.assertLess(b.lower_bound, b.upper_bound)
            self.assertLessEqual(b.lower_bound, b.initial)
            self.assertGreaterEqual(b.upper_bound, b.initial)

    def test_save_and_load_baselines(self) -> None:
        """Can save and load baselines from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "baselines.json"
            generator = BootstrapGenerator(Path("."))

            baselines = {
                "test-001": PatternBaseline(
                    pattern_id="test-001",
                    true_positives=10,
                    false_positives=2,
                    false_negatives=1,
                    precision=0.83,
                    recall=0.91,
                    f1_score=0.87,
                    sample_size=13,
                ),
            }

            generator.save_baselines(baselines, path)
            loaded = generator.load_baselines(path)

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded["test-001"].precision, 0.83)


class TestGenerateBootstrapData(unittest.TestCase):
    """Test the main generate_bootstrap_data function."""

    def test_generate_creates_files(self) -> None:
        """Generate creates output files."""
        test_projects = Path(__file__).parent / "projects"

        if not test_projects.exists():
            self.skipTest("Test projects directory not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            baselines, bounds = generate_bootstrap_data(
                test_projects=test_projects,
                patterns=None,
                output_dir=output_dir,
            )

            # Check files created
            baseline_path = output_dir / "pattern_baseline.json"
            bounds_path = output_dir / "confidence_bounds.json"

            self.assertTrue(baseline_path.exists())
            self.assertTrue(bounds_path.exists())

            # Check files are valid JSON
            with open(baseline_path) as f:
                json.load(f)
            with open(bounds_path) as f:
                json.load(f)

            # Check return values
            self.assertEqual(len(baselines), len(bounds))


if __name__ == "__main__":
    unittest.main()
