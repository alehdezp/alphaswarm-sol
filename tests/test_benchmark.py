"""
Tests for Benchmark Module

Validates:
1. Suite loading
2. Challenge parsing
3. Results tracking
4. Comparison logic
"""

import json
import tempfile
import unittest
from pathlib import Path


class SuiteLoadingTests(unittest.TestCase):
    """Tests for benchmark suite loading."""

    def test_import_benchmark_module(self):
        """Benchmark module can be imported."""
        from alphaswarm_sol.benchmark import BenchmarkSuite, Challenge, BenchmarkResults
        self.assertIsNotNone(BenchmarkSuite)
        self.assertIsNotNone(Challenge)
        self.assertIsNotNone(BenchmarkResults)

    def test_load_dvd_suite(self):
        """DVDeFi suite can be loaded."""
        from alphaswarm_sol.benchmark.suite import load_suite

        suite = load_suite("dvdefi")

        self.assertEqual(suite.name, "dvd")
        self.assertEqual(len(suite.challenges), 13)
        self.assertGreater(suite.detected_count, 0)

    def test_suite_detection_rate(self):
        """Suite calculates detection rate correctly."""
        from alphaswarm_sol.benchmark.suite import load_suite

        suite = load_suite("dvdefi")

        # 11 detected out of 12 detectable (compromised is not-applicable)
        self.assertGreaterEqual(suite.detection_rate, 0.8)

    def test_get_challenge_by_id(self):
        """Can get challenge by ID."""
        from alphaswarm_sol.benchmark.suite import load_suite

        suite = load_suite("dvdefi")
        challenge = suite.get_challenge("dvd-unstoppable")

        self.assertIsNotNone(challenge)
        self.assertEqual(challenge.id, "dvd-unstoppable")
        self.assertEqual(challenge.category, "DoS")


class ChallengeParsingTests(unittest.TestCase):
    """Tests for challenge YAML parsing."""

    def test_challenge_has_expected_fields(self):
        """Challenge has all expected fields."""
        from alphaswarm_sol.benchmark.suite import load_suite

        suite = load_suite("dvdefi")
        challenge = suite.get_challenge("dvd-truster")

        self.assertIsNotNone(challenge)
        self.assertEqual(challenge.vulnerability_type, "arbitrary-external-call")
        self.assertEqual(challenge.severity, "critical")
        self.assertGreater(len(challenge.expected_detections), 0)

    def test_expected_detections_parsed(self):
        """Expected detections are parsed correctly."""
        from alphaswarm_sol.benchmark.suite import load_suite

        suite = load_suite("dvdefi")
        challenge = suite.get_challenge("dvd-side-entrance")

        self.assertGreater(len(challenge.expected_detections), 0)
        detection = challenge.expected_detections[0]
        self.assertTrue(hasattr(detection, "pattern"))
        self.assertTrue(hasattr(detection, "contract"))


class ResultsTests(unittest.TestCase):
    """Tests for benchmark results tracking."""

    def test_create_results(self):
        """Can create benchmark results."""
        from alphaswarm_sol.benchmark.results import BenchmarkResults, ChallengeResult

        results = BenchmarkResults(suite_name="test", suite_version="1.0")
        results.add_result(ChallengeResult(
            challenge_id="test-1",
            status="detected",
            expected_detections=2,
            actual_detections=2,
        ))
        results.add_result(ChallengeResult(
            challenge_id="test-2",
            status="not-detected",
            expected_detections=1,
            actual_detections=0,
        ))

        self.assertEqual(results.total_challenges, 2)
        self.assertEqual(results.detected_count, 1)
        self.assertEqual(results.detection_rate, 0.5)

    def test_results_to_dict(self):
        """Results can be serialized to dict."""
        from alphaswarm_sol.benchmark.results import BenchmarkResults, ChallengeResult

        results = BenchmarkResults(suite_name="test", suite_version="1.0")
        results.add_result(ChallengeResult(
            challenge_id="test-1",
            status="detected",
        ))

        d = results.to_dict()

        self.assertEqual(d["suite_name"], "test")
        self.assertIn("summary", d)
        self.assertIn("challenge_results", d)

    def test_results_save_load(self):
        """Results can be saved and loaded."""
        from alphaswarm_sol.benchmark.results import BenchmarkResults, ChallengeResult

        results = BenchmarkResults(suite_name="test", suite_version="1.0")
        results.add_result(ChallengeResult(
            challenge_id="test-1",
            status="detected",
            patterns_matched=["pattern-a"],
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "results.json"
            results.save(path)

            loaded = BenchmarkResults.load(path)

            self.assertEqual(loaded.suite_name, "test")
            self.assertEqual(len(loaded.challenge_results), 1)
            self.assertEqual(loaded.challenge_results[0].patterns_matched, ["pattern-a"])


class ComparisonTests(unittest.TestCase):
    """Tests for benchmark comparison."""

    def test_compare_identical_results(self):
        """Comparing identical results shows no changes."""
        from alphaswarm_sol.benchmark.results import BenchmarkResults, ChallengeResult, compare_results

        results = BenchmarkResults(suite_name="test", suite_version="1.0")
        results.add_result(ChallengeResult(challenge_id="test-1", status="detected"))

        comparison = compare_results(results, results)

        self.assertFalse(comparison["has_regression"])
        self.assertEqual(len(comparison["regressed"]), 0)

    def test_detect_regression(self):
        """Comparison detects regressions."""
        from alphaswarm_sol.benchmark.results import BenchmarkResults, ChallengeResult, compare_results

        baseline = BenchmarkResults(suite_name="test", suite_version="1.0")
        baseline.add_result(ChallengeResult(challenge_id="test-1", status="detected"))

        current = BenchmarkResults(suite_name="test", suite_version="1.0")
        current.add_result(ChallengeResult(challenge_id="test-1", status="not-detected"))

        comparison = compare_results(current, baseline)

        self.assertTrue(comparison["has_regression"])
        self.assertIn("test-1", comparison["regressed"])

    def test_detect_improvement(self):
        """Comparison detects improvements."""
        from alphaswarm_sol.benchmark.results import BenchmarkResults, ChallengeResult, compare_results

        baseline = BenchmarkResults(suite_name="test", suite_version="1.0")
        baseline.add_result(ChallengeResult(challenge_id="test-1", status="not-detected"))

        current = BenchmarkResults(suite_name="test", suite_version="1.0")
        current.add_result(ChallengeResult(challenge_id="test-1", status="detected"))

        comparison = compare_results(current, baseline)

        self.assertFalse(comparison["has_regression"])
        self.assertIn("test-1", comparison["improved"])


class RunnerTests(unittest.TestCase):
    """Tests for benchmark runner."""

    def test_import_runner(self):
        """Runner can be imported."""
        from alphaswarm_sol.benchmark.runner import BenchmarkRunner
        self.assertIsNotNone(BenchmarkRunner)


if __name__ == "__main__":
    unittest.main()
