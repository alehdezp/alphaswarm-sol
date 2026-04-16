"""
Tests for Quality Tracking and Fallback (Tasks 4.7-4.8)

Validates quality metrics tracking and tier fallback mechanisms.
"""

import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from alphaswarm_sol.enterprise.reports import Finding, Severity
from alphaswarm_sol.testing.generator import TestScaffold, generate_tier1_scaffold
from alphaswarm_sol.testing.tiers import TestTier
from alphaswarm_sol.testing.quality import (
    CompilationStatus,
    ExecutionStatus,
    ScaffoldQualityRecord,
    QualityMetrics,
    QualityTracker,
    generate_with_fallback,
    batch_generate_with_quality,
)


class TestCompilationStatus(unittest.TestCase):
    """Tests for CompilationStatus enum."""

    def test_all_statuses_exist(self):
        """All compilation statuses are defined."""
        self.assertEqual(CompilationStatus.NOT_ATTEMPTED.value, "not_attempted")
        self.assertEqual(CompilationStatus.SUCCESS.value, "success")
        self.assertEqual(CompilationStatus.FAILED.value, "failed")
        self.assertEqual(CompilationStatus.TIMEOUT.value, "timeout")


class TestExecutionStatus(unittest.TestCase):
    """Tests for ExecutionStatus enum."""

    def test_all_statuses_exist(self):
        """All execution statuses are defined."""
        self.assertEqual(ExecutionStatus.NOT_ATTEMPTED.value, "not_attempted")
        self.assertEqual(ExecutionStatus.PASSED.value, "passed")
        self.assertEqual(ExecutionStatus.FAILED.value, "failed")
        self.assertEqual(ExecutionStatus.ERROR.value, "error")
        self.assertEqual(ExecutionStatus.TIMEOUT.value, "timeout")


class TestScaffoldQualityRecord(unittest.TestCase):
    """Tests for ScaffoldQualityRecord."""

    def test_record_creation(self):
        """Can create quality record."""
        record = ScaffoldQualityRecord(
            scaffold_id="Test_VKG_001.t.sol",
            finding_id="VKG-001",
            tier=2,
            generated_at=datetime.now(),
            filename="Test_VKG_001.t.sol",
            confidence=0.4,
        )
        self.assertEqual(record.scaffold_id, "Test_VKG_001.t.sol")
        self.assertEqual(record.tier, 2)
        self.assertEqual(record.compilation_status, CompilationStatus.NOT_ATTEMPTED)

    def test_record_compilation_success(self):
        """Can record successful compilation."""
        record = ScaffoldQualityRecord(
            scaffold_id="test",
            finding_id="VKG-001",
            tier=2,
            generated_at=datetime.now(),
            filename="test.t.sol",
            confidence=0.5,
        )

        record.record_compilation_attempt(success=True)

        self.assertEqual(record.compilation_status, CompilationStatus.SUCCESS)
        self.assertEqual(record.compilation_attempts, 1)
        self.assertIsNone(record.compilation_error)
        self.assertTrue(record.compiled_successfully)

    def test_record_compilation_failure(self):
        """Can record failed compilation."""
        record = ScaffoldQualityRecord(
            scaffold_id="test",
            finding_id="VKG-001",
            tier=2,
            generated_at=datetime.now(),
            filename="test.t.sol",
            confidence=0.5,
        )

        record.record_compilation_attempt(success=False, error="Import not found")

        self.assertEqual(record.compilation_status, CompilationStatus.FAILED)
        self.assertEqual(record.compilation_error, "Import not found")
        self.assertFalse(record.compiled_successfully)

    def test_record_execution(self):
        """Can record test execution."""
        record = ScaffoldQualityRecord(
            scaffold_id="test",
            finding_id="VKG-001",
            tier=2,
            generated_at=datetime.now(),
            filename="test.t.sol",
            confidence=0.5,
        )

        record.record_execution_attempt(ExecutionStatus.PASSED)

        self.assertEqual(record.execution_status, ExecutionStatus.PASSED)
        self.assertTrue(record.executed_successfully)

    def test_record_to_dict(self):
        """Can serialize record to dict."""
        record = ScaffoldQualityRecord(
            scaffold_id="test",
            finding_id="VKG-001",
            tier=2,
            generated_at=datetime.now(),
            filename="test.t.sol",
            confidence=0.5,
        )

        data = record.to_dict()

        self.assertEqual(data["scaffold_id"], "test")
        self.assertEqual(data["tier"], 2)
        self.assertIn("generated_at", data)


class TestQualityMetrics(unittest.TestCase):
    """Tests for QualityMetrics."""

    def test_initial_metrics(self):
        """Initial metrics are zero."""
        metrics = QualityMetrics()
        self.assertEqual(metrics.total_generated, 0)
        self.assertEqual(metrics.compile_rate, 0.0)
        self.assertEqual(metrics.execution_rate, 0.0)

    def test_compile_rate_calculation(self):
        """Compile rate is calculated correctly."""
        metrics = QualityMetrics(
            compilation_attempts=10,
            compilation_successes=4,
        )
        self.assertEqual(metrics.compile_rate, 0.4)

    def test_execution_rate_calculation(self):
        """Execution rate is calculated correctly."""
        metrics = QualityMetrics(
            execution_attempts=10,
            execution_successes=3,
        )
        self.assertEqual(metrics.execution_rate, 0.3)

    def test_meets_tier1_target(self):
        """Tier 1 always meets target."""
        metrics = QualityMetrics()
        self.assertTrue(metrics.meets_tier_target(TestTier.TIER_1_TEMPLATE))

    def test_meets_tier2_target(self):
        """Tier 2 target met at 25%+."""
        metrics = QualityMetrics(
            compilation_attempts=100,
            compilation_successes=30,
        )
        self.assertTrue(metrics.meets_tier_target(TestTier.TIER_2_SMART))

    def test_fails_tier2_target(self):
        """Tier 2 target not met below 25%."""
        metrics = QualityMetrics(
            compilation_attempts=100,
            compilation_successes=20,
        )
        self.assertFalse(metrics.meets_tier_target(TestTier.TIER_2_SMART))

    def test_metrics_to_dict(self):
        """Can serialize metrics to dict."""
        metrics = QualityMetrics(
            total_generated=10,
            tier2_generated=8,
            compilation_attempts=8,
            compilation_successes=3,
        )

        data = metrics.to_dict()

        self.assertEqual(data["total_generated"], 10)
        self.assertIn("compile_rate", data)


class TestQualityTracker(unittest.TestCase):
    """Tests for QualityTracker."""

    def test_tracker_creation(self):
        """Can create tracker."""
        tracker = QualityTracker()
        self.assertEqual(tracker.metrics.total_generated, 0)

    def test_record_generation(self):
        """Can record scaffold generation."""
        tracker = QualityTracker()
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=2,
            content="contract {}",
            filename="Test.t.sol",
            confidence=0.4,
        )

        record = tracker.record_generation(scaffold)

        self.assertEqual(record.finding_id, "VKG-001")
        self.assertEqual(record.tier, 2)
        self.assertEqual(tracker.metrics.total_generated, 1)
        self.assertEqual(tracker.metrics.tier2_generated, 1)

    def test_record_compilation(self):
        """Can record compilation result."""
        tracker = QualityTracker()
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=2,
            content="contract {}",
            filename="Test.t.sol",
            confidence=0.4,
        )
        tracker.record_generation(scaffold)

        tracker.record_compilation("Test.t.sol", success=True)

        record = tracker.get_record("Test.t.sol")
        self.assertTrue(record.compiled_successfully)
        self.assertEqual(tracker.metrics.compilation_successes, 1)

    def test_record_execution(self):
        """Can record execution result."""
        tracker = QualityTracker()
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=2,
            content="contract {}",
            filename="Test.t.sol",
            confidence=0.4,
        )
        tracker.record_generation(scaffold)

        tracker.record_execution("Test.t.sol", ExecutionStatus.PASSED)

        record = tracker.get_record("Test.t.sol")
        self.assertEqual(record.execution_status, ExecutionStatus.PASSED)

    def test_record_fallback(self):
        """Can record tier fallback."""
        tracker = QualityTracker()
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=1,
            content="contract {}",
            filename="Test.t.sol",
            confidence=1.0,
        )
        tracker.record_generation(scaffold)

        tracker.record_fallback("Test.t.sol", from_tier=2, reason="Low confidence")

        record = tracker.get_record("Test.t.sol")
        self.assertEqual(record.fell_back_from_tier, 2)
        self.assertEqual(record.fallback_reason, "Low confidence")
        self.assertEqual(tracker.metrics.fallback_count, 1)

    def test_get_summary(self):
        """Can get tracking summary."""
        tracker = QualityTracker()
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=2,
            content="contract {}",
            filename="Test.t.sol",
            confidence=0.4,
        )
        tracker.record_generation(scaffold)

        summary = tracker.get_summary()

        self.assertIn("metrics", summary)
        self.assertIn("tier_targets", summary)
        self.assertIn("current_performance", summary)

    def test_persistence(self):
        """Tracker persists data to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "quality.json"

            # Create tracker and add data
            tracker1 = QualityTracker(storage_path=storage_path)
            scaffold = TestScaffold(
                finding_id="VKG-001",
                tier=2,
                content="contract {}",
                filename="Test.t.sol",
                confidence=0.4,
            )
            tracker1.record_generation(scaffold)
            tracker1.record_compilation("Test.t.sol", success=True)

            # Create new tracker and verify data loaded
            tracker2 = QualityTracker(storage_path=storage_path)
            self.assertEqual(tracker2.metrics.total_generated, 1)
            self.assertEqual(tracker2.metrics.compilation_successes, 1)


class TestGenerateWithFallback(unittest.TestCase):
    """Tests for generate_with_fallback function."""

    def test_generates_tier2_when_possible(self):
        """Generates Tier 2 scaffold when possible."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
            description="Test",
            location="Test.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_with_fallback(
            finding,
            target_tier=TestTier.TIER_2_SMART,
        )

        self.assertIsNotNone(scaffold)
        # Should be Tier 2 or Tier 1 (fallback)
        self.assertIn(scaffold.tier, [1, 2])

    def test_falls_back_to_tier1(self):
        """Falls back to Tier 1 when Tier 2 fails."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
            description="Test",
            location="",  # Empty location may cause issues
            recommendation="",
        )

        tracker = QualityTracker()
        scaffold = generate_with_fallback(
            finding,
            target_tier=TestTier.TIER_2_SMART,
            tracker=tracker,
        )

        # Should always return something
        self.assertIsNotNone(scaffold)
        self.assertGreater(len(scaffold.content), 0)

    def test_records_generation(self):
        """Records generation in tracker."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        tracker = QualityTracker()
        scaffold = generate_with_fallback(
            finding,
            target_tier=TestTier.TIER_2_SMART,
            tracker=tracker,
        )

        self.assertEqual(tracker.metrics.total_generated, 1)
        record = tracker.get_record(scaffold.filename)
        self.assertIsNotNone(record)


class TestBatchGenerateWithQuality(unittest.TestCase):
    """Tests for batch_generate_with_quality function."""

    def test_generates_multiple_scaffolds(self):
        """Generates scaffolds for multiple findings."""
        findings = [
            Finding(id="VKG-001", title="Bug 1", severity=Severity.HIGH),
            Finding(id="VKG-002", title="Bug 2", severity=Severity.MEDIUM),
            Finding(id="VKG-003", title="Bug 3", severity=Severity.LOW),
        ]

        tracker = QualityTracker()
        scaffolds = batch_generate_with_quality(findings, tracker=tracker)

        self.assertEqual(len(scaffolds), 3)
        self.assertEqual(tracker.metrics.total_generated, 3)

    def test_tracks_all_generations(self):
        """Tracks quality for all generated scaffolds."""
        findings = [
            Finding(id=f"VKG-{i:03d}", title=f"Bug {i}", severity=Severity.HIGH)
            for i in range(5)
        ]

        tracker = QualityTracker()
        scaffolds = batch_generate_with_quality(findings, tracker=tracker)

        self.assertEqual(tracker.metrics.total_generated, 5)
        for scaffold in scaffolds:
            record = tracker.get_record(scaffold.filename)
            self.assertIsNotNone(record)


class TestQualityTargets(unittest.TestCase):
    """Tests for quality target validation."""

    def test_tier2_realistic_target(self):
        """Tier 2 has realistic 30-40% target."""
        # Create metrics that should pass (35%)
        metrics = QualityMetrics(
            compilation_attempts=100,
            compilation_successes=35,
        )
        self.assertTrue(metrics.meets_tier_target(TestTier.TIER_2_SMART))

        # Create metrics that should fail (20%)
        metrics2 = QualityMetrics(
            compilation_attempts=100,
            compilation_successes=20,
        )
        self.assertFalse(metrics2.meets_tier_target(TestTier.TIER_2_SMART))

    def test_tier2_minimum_at_25_percent(self):
        """Tier 2 minimum is 25%."""
        # Exactly at minimum
        metrics = QualityMetrics(
            compilation_attempts=100,
            compilation_successes=25,
        )
        self.assertTrue(metrics.meets_tier_target(TestTier.TIER_2_SMART))

        # Just below minimum
        metrics2 = QualityMetrics(
            compilation_attempts=100,
            compilation_successes=24,
        )
        self.assertFalse(metrics2.meets_tier_target(TestTier.TIER_2_SMART))


if __name__ == "__main__":
    unittest.main()
