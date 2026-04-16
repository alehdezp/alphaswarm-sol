"""Tests for A/B testing infrastructure.

Task 7.5: A/B testing for pattern configurations.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from alphaswarm_sol.learning.ab_testing import (
    Variant,
    ABTestConfig,
    ABTestResult,
    PatternABTest,
    ABTestManager,
)


class TestVariant(unittest.TestCase):
    """Test Variant enum."""

    def test_variant_values(self):
        """Variants have correct values."""
        self.assertEqual(Variant.CONTROL.value, "A")
        self.assertEqual(Variant.TREATMENT.value, "B")


class TestABTestConfig(unittest.TestCase):
    """Test ABTestConfig dataclass."""

    def test_create_basic(self):
        """Create basic config."""
        config = ABTestConfig(
            test_id="test-001",
            pattern_id="vm-001",
            treatment_config={"threshold": 0.8},
        )
        self.assertEqual(config.test_id, "test-001")
        self.assertEqual(config.pattern_id, "vm-001")
        self.assertEqual(config.traffic_fraction, 0.10)  # Default
        self.assertEqual(config.min_samples, 20)  # Default
        self.assertTrue(config.is_active())

    def test_custom_params(self):
        """Custom parameters."""
        config = ABTestConfig(
            test_id="test-002",
            pattern_id="oracle-001",
            treatment_config={"new_rule": True},
            traffic_fraction=0.20,
            min_samples=50,
            description="Testing new rule",
        )
        self.assertEqual(config.traffic_fraction, 0.20)
        self.assertEqual(config.min_samples, 50)
        self.assertEqual(config.description, "Testing new rule")

    def test_invalid_traffic_fraction(self):
        """Invalid traffic fraction raises."""
        with self.assertRaises(ValueError):
            ABTestConfig(
                test_id="test",
                pattern_id="vm-001",
                treatment_config={},
                traffic_fraction=0.0,
            )
        with self.assertRaises(ValueError):
            ABTestConfig(
                test_id="test",
                pattern_id="vm-001",
                treatment_config={},
                traffic_fraction=1.0,
            )

    def test_invalid_min_samples(self):
        """Invalid min_samples raises."""
        with self.assertRaises(ValueError):
            ABTestConfig(
                test_id="test",
                pattern_id="vm-001",
                treatment_config={},
                min_samples=0,
            )

    def test_to_dict(self):
        """Convert to dict."""
        config = ABTestConfig(
            test_id="test-001",
            pattern_id="vm-001",
            treatment_config={"key": "value"},
            description="Test",
        )
        d = config.to_dict()
        self.assertEqual(d["test_id"], "test-001")
        self.assertEqual(d["pattern_id"], "vm-001")
        self.assertEqual(d["treatment_config"], {"key": "value"})
        self.assertIsNone(d["end_time"])

    def test_from_dict(self):
        """Create from dict."""
        data = {
            "test_id": "test-001",
            "pattern_id": "vm-001",
            "treatment_config": {"threshold": 0.9},
            "traffic_fraction": 0.15,
            "min_samples": 30,
            "start_time": "2026-01-08T12:00:00",
            "end_time": None,
            "description": "From dict",
        }
        config = ABTestConfig.from_dict(data)
        self.assertEqual(config.test_id, "test-001")
        self.assertEqual(config.traffic_fraction, 0.15)
        self.assertEqual(config.min_samples, 30)

    def test_round_trip(self):
        """Dict round-trip preserves data."""
        config = ABTestConfig(
            test_id="test-round-trip",
            pattern_id="dos-001",
            treatment_config={"complex": {"nested": True}},
            traffic_fraction=0.25,
        )
        restored = ABTestConfig.from_dict(config.to_dict())
        self.assertEqual(restored.test_id, config.test_id)
        self.assertEqual(restored.treatment_config, config.treatment_config)
        self.assertEqual(restored.traffic_fraction, config.traffic_fraction)

    def test_is_active(self):
        """Check is_active method."""
        config = ABTestConfig(
            test_id="test",
            pattern_id="vm-001",
            treatment_config={},
        )
        self.assertTrue(config.is_active())

        config.end_time = datetime.now()
        self.assertFalse(config.is_active())


class TestABTestResult(unittest.TestCase):
    """Test ABTestResult dataclass."""

    def test_create_result(self):
        """Create result."""
        result = ABTestResult(
            test_id="test-001",
            control_samples=100,
            treatment_samples=10,
            control_precision=0.85,
            treatment_precision=0.90,
            control_verdicts={"confirmed": 85, "rejected": 15},
            treatment_verdicts={"confirmed": 9, "rejected": 1},
            is_significant=True,
            p_value=0.05,
            winner=Variant.TREATMENT,
        )
        self.assertEqual(result.control_samples, 100)
        self.assertAlmostEqual(result.precision_diff, 0.05, places=4)

    def test_to_dict(self):
        """Convert to dict."""
        result = ABTestResult(
            test_id="test-001",
            control_samples=50,
            treatment_samples=5,
            control_precision=0.80,
            treatment_precision=0.60,
            control_verdicts={"confirmed": 40, "rejected": 10},
            treatment_verdicts={"confirmed": 3, "rejected": 2},
            is_significant=False,
            p_value=None,
            winner=None,
        )
        d = result.to_dict()
        self.assertEqual(d["control_samples"], 50)
        self.assertEqual(d["control_precision"], 0.80)
        self.assertIsNone(d["winner"])

    def test_summary(self):
        """Generate summary."""
        result = ABTestResult(
            test_id="test-001",
            control_samples=100,
            treatment_samples=10,
            control_precision=0.85,
            treatment_precision=0.95,
            control_verdicts={"confirmed": 85, "rejected": 15},
            treatment_verdicts={"confirmed": 9, "rejected": 1},
            is_significant=True,
            p_value=0.05,
            winner=Variant.TREATMENT,
        )
        summary = result.summary()
        self.assertIn("test-001", summary)
        self.assertIn("Control", summary)
        self.assertIn("Treatment", summary)
        self.assertIn("Winner", summary)


class TestPatternABTest(unittest.TestCase):
    """Test PatternABTest class."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ABTestConfig(
            test_id="test-vm-001",
            pattern_id="vm-001",
            treatment_config={"new_threshold": 0.9},
            traffic_fraction=0.10,
        )
        self.test = PatternABTest(self.config, Path(self.temp_dir))

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_consistent_assignment(self):
        """Same finding always gets same variant."""
        finding_id = "VKG-001"
        v1 = self.test.get_variant(finding_id)
        v2 = self.test.get_variant(finding_id)
        v3 = self.test.get_variant(finding_id)
        self.assertEqual(v1, v2)
        self.assertEqual(v2, v3)

    def test_different_findings_different_assignments(self):
        """Different findings can get different variants."""
        variants = set()
        for i in range(100):
            variant = self.test.get_variant(f"finding-{i}")
            variants.add(variant)

        # With 100 findings, we should see both variants
        self.assertEqual(len(variants), 2)

    def test_traffic_split_roughly_correct(self):
        """Traffic split is roughly correct."""
        treatment_count = 0
        total = 1000
        for i in range(total):
            if self.test.get_variant(f"finding-{i}") == Variant.TREATMENT:
                treatment_count += 1

        # Should be roughly 10% +/- 5%
        self.assertGreater(treatment_count, 50)  # > 5%
        self.assertLess(treatment_count, 150)  # < 15%

    def test_record_verdict(self):
        """Record verdict."""
        self.test.record_verdict("f1", Variant.CONTROL, "confirmed")
        self.assertEqual(len(self.test._results["A"]), 1)
        self.assertEqual(self.test._results["A"]["f1"]["verdict"], "confirmed")

    def test_record_multiple_verdicts(self):
        """Record multiple verdicts."""
        self.test.record_verdict("f1", Variant.CONTROL, "confirmed")
        self.test.record_verdict("f2", Variant.CONTROL, "rejected")
        self.test.record_verdict("f3", Variant.TREATMENT, "confirmed")
        self.test.record_verdict("f4", Variant.TREATMENT, "confirmed")

        self.assertEqual(len(self.test._results["A"]), 2)
        self.assertEqual(len(self.test._results["B"]), 2)

    def test_get_results_basic(self):
        """Get basic results."""
        self.test.record_verdict("f1", Variant.CONTROL, "confirmed")
        self.test.record_verdict("f2", Variant.CONTROL, "rejected")
        self.test.record_verdict("f3", Variant.TREATMENT, "confirmed")

        results = self.test.get_results()
        self.assertEqual(results.control_samples, 2)
        self.assertEqual(results.treatment_samples, 1)
        self.assertEqual(results.control_precision, 0.5)
        self.assertEqual(results.treatment_precision, 1.0)

    def test_get_results_no_samples(self):
        """Results with no samples."""
        results = self.test.get_results()
        self.assertEqual(results.control_samples, 0)
        self.assertEqual(results.treatment_samples, 0)
        self.assertEqual(results.control_precision, 0.5)  # Prior

    def test_is_complete_insufficient(self):
        """Test is not complete with insufficient samples."""
        self.test.record_verdict("f1", Variant.CONTROL, "confirmed")
        self.assertFalse(self.test.is_complete())

    def test_is_complete_sufficient(self):
        """Test is complete with sufficient samples."""
        # Record enough control samples
        for i in range(20):
            self.test.record_verdict(f"control-{i}", Variant.CONTROL, "confirmed")

        # Record enough treatment samples (10% of min_samples = 2, but min is 5)
        for i in range(5):
            self.test.record_verdict(f"treatment-{i}", Variant.TREATMENT, "confirmed")

        self.assertTrue(self.test.is_complete())

    def test_persistence(self):
        """Test results persist."""
        self.test.record_verdict("f1", Variant.CONTROL, "confirmed")
        self.test.record_verdict("f2", Variant.TREATMENT, "rejected")

        # Create new test instance
        new_test = PatternABTest(self.config, Path(self.temp_dir))
        self.assertEqual(len(new_test._results["A"]), 1)
        self.assertEqual(len(new_test._results["B"]), 1)

    def test_get_assignment_stats(self):
        """Get assignment statistics."""
        self.test.record_verdict("f1", Variant.CONTROL, "confirmed")
        self.test.record_verdict("f2", Variant.CONTROL, "confirmed")
        self.test.record_verdict("f3", Variant.TREATMENT, "confirmed")

        stats = self.test.get_assignment_stats()
        self.assertEqual(stats["control"], 2)
        self.assertEqual(stats["treatment"], 1)


class TestSignificanceChecking(unittest.TestCase):
    """Test statistical significance checking."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ABTestConfig(
            test_id="test-significance",
            pattern_id="vm-001",
            treatment_config={},
            traffic_fraction=0.10,
        )
        self.test = PatternABTest(self.config, Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_not_significant_insufficient_samples(self):
        """Not significant with insufficient samples."""
        # Few samples
        self.test.record_verdict("f1", Variant.CONTROL, "confirmed")
        self.test.record_verdict("f2", Variant.TREATMENT, "rejected")

        results = self.test.get_results()
        self.assertFalse(results.is_significant)
        self.assertIsNone(results.p_value)

    def test_significant_large_difference(self):
        """Significant with large difference and enough samples."""
        # Control: 100% precision
        for i in range(15):
            self.test.record_verdict(f"control-{i}", Variant.CONTROL, "confirmed")

        # Treatment: 60% precision
        for i in range(6):
            self.test.record_verdict(f"treatment-tp-{i}", Variant.TREATMENT, "confirmed")
        for i in range(4):
            self.test.record_verdict(f"treatment-fp-{i}", Variant.TREATMENT, "rejected")

        results = self.test.get_results()
        self.assertTrue(results.is_significant)
        self.assertIsNotNone(results.p_value)
        self.assertEqual(results.winner, Variant.CONTROL)

    def test_not_significant_small_difference(self):
        """Not significant with small difference."""
        # Control: 80% precision
        for i in range(8):
            self.test.record_verdict(f"control-tp-{i}", Variant.CONTROL, "confirmed")
        for i in range(2):
            self.test.record_verdict(f"control-fp-{i}", Variant.CONTROL, "rejected")

        # Treatment: 75% precision (not enough difference)
        for i in range(15):
            self.test.record_verdict(f"treatment-tp-{i}", Variant.TREATMENT, "confirmed")
        for i in range(5):
            self.test.record_verdict(f"treatment-fp-{i}", Variant.TREATMENT, "rejected")

        results = self.test.get_results()
        # 5% difference is not significant
        self.assertFalse(results.is_significant)


class TestABTestManager(unittest.TestCase):
    """Test ABTestManager class."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ABTestManager(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_test(self):
        """Create new test."""
        test_id = self.manager.create_test(
            pattern_id="vm-001",
            treatment_config={"new_rule": True},
            description="Test new reentrancy rule",
        )
        self.assertTrue(test_id.startswith("test_vm-001"))

        test = self.manager.get_test(test_id)
        self.assertIsNotNone(test)
        self.assertEqual(test.config.pattern_id, "vm-001")

    def test_cannot_create_duplicate(self):
        """Cannot create duplicate active test."""
        self.manager.create_test("vm-001", {})

        with self.assertRaises(ValueError):
            self.manager.create_test("vm-001", {})

    def test_get_active_test(self):
        """Get active test for pattern."""
        test_id = self.manager.create_test("vm-001", {})

        active = self.manager.get_active_test("vm-001")
        self.assertIsNotNone(active)
        self.assertEqual(active.config.test_id, test_id)

        # No active test for different pattern
        self.assertIsNone(self.manager.get_active_test("vm-002"))

    def test_end_test(self):
        """End a test."""
        test_id = self.manager.create_test("vm-001", {})
        test = self.manager.get_test(test_id)

        # Record some verdicts
        test.record_verdict("f1", Variant.CONTROL, "confirmed")

        # End the test
        result = self.manager.end_test(test_id)
        self.assertIsNotNone(result)
        self.assertEqual(result.test_id, test_id)

        # Test should no longer be active
        self.assertIsNone(self.manager.get_active_test("vm-001"))

    def test_get_tests_for_pattern(self):
        """Get all tests for pattern."""
        # Create first test for vm-001
        test_id_1 = self.manager.create_test("vm-001", {"v": 1})

        # Create test for different pattern
        test_id_2 = self.manager.create_test("oracle-001", {"v": 2})

        # Should only get vm-001 tests
        tests = self.manager.get_tests_for_pattern("vm-001")
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].config.test_id, test_id_1)

        # Should get oracle-001 test
        oracle_tests = self.manager.get_tests_for_pattern("oracle-001")
        self.assertEqual(len(oracle_tests), 1)

    def test_get_all_active_tests(self):
        """Get all active tests."""
        self.manager.create_test("vm-001", {})
        self.manager.create_test("oracle-001", {})

        active = self.manager.get_all_active_tests()
        self.assertEqual(len(active), 2)

    def test_get_all_results(self):
        """Get results for all tests."""
        self.manager.create_test("vm-001", {})
        self.manager.create_test("oracle-001", {})

        results = self.manager.get_all_results()
        self.assertEqual(len(results), 2)

    def test_persistence(self):
        """Tests persist across manager instances."""
        test_id = self.manager.create_test("vm-001", {"key": "value"})
        test = self.manager.get_test(test_id)
        test.record_verdict("f1", Variant.CONTROL, "confirmed")

        # Create new manager
        new_manager = ABTestManager(Path(self.temp_dir))
        restored_test = new_manager.get_test(test_id)
        self.assertIsNotNone(restored_test)
        self.assertEqual(len(restored_test._results["A"]), 1)

    def test_summary(self):
        """Generate summary."""
        self.manager.create_test("vm-001", {})
        test_id = self.manager.create_test("oracle-001", {})
        self.manager.end_test(test_id)

        summary = self.manager.summary()
        self.assertIn("Active Tests", summary)
        self.assertIn("Completed Tests", summary)

    def test_summary_empty(self):
        """Summary for empty manager."""
        summary = self.manager.summary()
        self.assertIn("No tests created", summary)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_corrupted_storage(self):
        """Handle corrupted storage file."""
        # Write corrupted data
        storage_path = Path(self.temp_dir)
        test_file = storage_path / "ab_test_test-001.json"
        storage_path.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w") as f:
            f.write("invalid json {{{")

        # Should handle gracefully
        manager = ABTestManager(storage_path)
        self.assertEqual(len(manager._tests), 0)

    def test_record_with_metadata(self):
        """Record verdict with metadata."""
        config = ABTestConfig(
            test_id="test-001",
            pattern_id="vm-001",
            treatment_config={},
        )
        test = PatternABTest(config, Path(self.temp_dir))

        test.record_verdict(
            "f1",
            Variant.CONTROL,
            "confirmed",
            metadata={"confidence": 0.95, "reason": "PoC verified"},
        )

        self.assertEqual(
            test._results["A"]["f1"]["metadata"]["confidence"],
            0.95,
        )


if __name__ == "__main__":
    unittest.main()
