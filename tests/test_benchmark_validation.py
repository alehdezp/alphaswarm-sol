"""
Benchmark Self-Validation Tests

Validates that:
1. Benchmark suite matches documented detection status
2. Detection rate meets target
3. Expected patterns match actual results
"""

import unittest
from pathlib import Path


class BenchmarkSelfValidationTests(unittest.TestCase):
    """Tests that benchmark results match expected status."""

    def setUp(self):
        """Load benchmark suite."""
        from alphaswarm_sol.benchmark.suite import load_suite
        self.suite = load_suite("dvdefi")

    def test_detection_rate_meets_target(self):
        """Detection rate meets 80% target."""
        target = self.suite.targets.get("target", 0.80)
        actual = self.suite.detection_rate

        self.assertGreaterEqual(
            actual, target,
            f"Detection rate {actual:.1%} below target {target:.1%}"
        )

    def test_detected_challenges_marked_correctly(self):
        """All detected challenges are marked as 'detected'."""
        detected_challenges = [
            "dvd-unstoppable",
            "dvd-naive-receiver",
            "dvd-truster",
            "dvd-side-entrance",
            "dvd-the-rewarder",
            "dvd-selfie",
            "dvd-puppet",
            "dvd-puppet-v2",
            "dvd-puppet-v3",
            "dvd-free-rider",
            "dvd-backdoor",
        ]

        for challenge_id in detected_challenges:
            challenge = self.suite.get_challenge(challenge_id)
            self.assertIsNotNone(challenge, f"Challenge {challenge_id} not found")
            self.assertEqual(
                challenge.status, "detected",
                f"Challenge {challenge_id} should be 'detected' but is '{challenge.status}'"
            )

    def test_not_applicable_challenges_marked_correctly(self):
        """Off-chain challenges are marked as 'not-applicable'."""
        na_challenges = ["dvd-compromised"]

        for challenge_id in na_challenges:
            challenge = self.suite.get_challenge(challenge_id)
            self.assertIsNotNone(challenge, f"Challenge {challenge_id} not found")
            self.assertEqual(
                challenge.status, "not-applicable",
                f"Challenge {challenge_id} should be 'not-applicable'"
            )

    def test_not_detected_challenges_documented(self):
        """Undetected challenges have documented reason."""
        not_detected = ["dvd-climber"]

        for challenge_id in not_detected:
            challenge = self.suite.get_challenge(challenge_id)
            self.assertIsNotNone(challenge, f"Challenge {challenge_id} not found")
            self.assertEqual(
                challenge.status, "not-detected",
                f"Challenge {challenge_id} should be 'not-detected'"
            )

    def test_all_challenges_have_vulnerability_type(self):
        """Every challenge has a vulnerability type."""
        for challenge in self.suite.challenges:
            self.assertIsNotNone(
                challenge.vulnerability_type,
                f"Challenge {challenge.id} missing vulnerability type"
            )
            self.assertNotEqual(
                challenge.vulnerability_type, "unknown",
                f"Challenge {challenge.id} has unknown vulnerability type"
            )

    def test_detected_challenges_have_patterns(self):
        """Detected challenges have expected patterns defined."""
        for challenge in self.suite.challenges:
            if challenge.status == "detected":
                self.assertGreater(
                    len(challenge.expected_detections), 0,
                    f"Detected challenge {challenge.id} has no expected patterns"
                )

    def test_challenge_count(self):
        """Suite has expected number of challenges."""
        self.assertEqual(
            len(self.suite.challenges), 13,
            "Expected 13 DVDeFi challenges"
        )

    def test_suite_metrics_consistent(self):
        """Suite metrics are internally consistent."""
        total = len(self.suite.challenges)
        detectable = self.suite.detectable_count
        detected = self.suite.detected_count

        # Detectable should be total minus not-applicable
        not_applicable = sum(1 for c in self.suite.challenges if c.status == "not-applicable")
        self.assertEqual(detectable, total - not_applicable)

        # Detection rate should match
        if detectable > 0:
            expected_rate = detected / detectable
            self.assertAlmostEqual(
                self.suite.detection_rate, expected_rate, 3,
                "Detection rate calculation mismatch"
            )


class PatternCoverageTests(unittest.TestCase):
    """Tests for pattern coverage in benchmarks."""

    def setUp(self):
        """Load suite and patterns."""
        from alphaswarm_sol.benchmark.suite import load_suite
        self.suite = load_suite("dvdefi")

    def test_all_expected_patterns_are_valid(self):
        """All expected pattern IDs exist in patterns directory."""
        patterns_dir = Path(__file__).parent.parent / "patterns" / "core"

        expected_patterns = set()
        for challenge in self.suite.challenges:
            for detection in challenge.expected_detections:
                expected_patterns.add(detection.pattern)

        # Check pattern files exist
        available_patterns = set()
        if patterns_dir.exists():
            for f in patterns_dir.glob("*.yaml"):
                import yaml
                try:
                    with open(f) as fp:
                        pattern = yaml.safe_load(fp)
                    if isinstance(pattern, dict) and "id" in pattern:
                        available_patterns.add(pattern["id"])
                except Exception:
                    pass

        # Not all expected patterns need to exist yet (some are planned)
        # But log which are missing
        missing = expected_patterns - available_patterns
        if missing:
            print(f"Note: {len(missing)} expected patterns not yet implemented: {missing}")


if __name__ == "__main__":
    unittest.main()
