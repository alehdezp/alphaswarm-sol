"""
Tests for Test Summary and Verification Loop (Tasks 4.10-4.11)

Validates the verification workflow and summary generation.
"""

import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.enterprise.reports import Finding, Severity, Verdict, TestResult
from alphaswarm_sol.testing.verification import (
    VerificationSummary,
    VerificationResult,
    VerificationLoop,
    format_verification_summary,
    format_finding_result,
)


class TestVerificationSummary(unittest.TestCase):
    """Tests for VerificationSummary."""

    def test_summary_creation(self):
        """Can create summary."""
        summary = VerificationSummary()
        self.assertEqual(summary.total_findings, 0)
        self.assertEqual(summary.verification_rate, 0.0)

    def test_verification_rate_calculation(self):
        """Verification rate is calculated correctly."""
        summary = VerificationSummary(
            total_findings=10,
            verdicts_confirmed=3,
            verdicts_false_positive=2,
            verdicts_inconclusive=1,
            verdicts_pending=4,
        )
        # 6 verified out of 10
        self.assertEqual(summary.verification_rate, 0.6)

    def test_verification_rate_zero_findings(self):
        """Verification rate is 0 with no findings."""
        summary = VerificationSummary(total_findings=0)
        self.assertEqual(summary.verification_rate, 0.0)

    def test_summary_to_dict(self):
        """Summary can be serialized."""
        summary = VerificationSummary(
            total_findings=5,
            scaffolds_generated=5,
            scaffolds_compiled=3,
            compile_rate=0.6,
        )

        data = summary.to_dict()

        self.assertEqual(data["total_findings"], 5)
        self.assertIn("rates", data)
        self.assertIn("verdicts", data)


class TestVerificationResult(unittest.TestCase):
    """Tests for VerificationResult."""

    def test_result_creation(self):
        """Can create result."""
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        result = VerificationResult(finding=finding)

        self.assertEqual(result.finding.id, "VKG-001")
        self.assertEqual(result.verdict, Verdict.PENDING)
        self.assertFalse(result.compiled)

    def test_result_to_dict(self):
        """Result can be serialized."""
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        result = VerificationResult(finding=finding, verdict=Verdict.CONFIRMED)

        data = result.to_dict()

        self.assertEqual(data["finding_id"], "VKG-001")
        self.assertEqual(data["verdict"], "confirmed")


class TestVerificationLoop(unittest.TestCase):
    """Tests for VerificationLoop."""

    def test_loop_creation(self):
        """Can create verification loop."""
        loop = VerificationLoop()
        self.assertEqual(loop.summary.total_findings, 0)

    def test_add_finding(self):
        """Can add finding to loop."""
        loop = VerificationLoop()
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)

        result = loop.add_finding(finding)

        self.assertIsNotNone(result)
        self.assertEqual(result.finding.id, "VKG-001")
        self.assertIsNotNone(result.scaffold)
        self.assertEqual(loop.summary.total_findings, 1)
        self.assertEqual(loop.summary.scaffolds_generated, 1)

    def test_add_multiple_findings(self):
        """Can add multiple findings."""
        loop = VerificationLoop()
        findings = [
            Finding(id="VKG-001", title="Bug 1", severity=Severity.HIGH),
            Finding(id="VKG-002", title="Bug 2", severity=Severity.MEDIUM),
            Finding(id="VKG-003", title="Bug 3", severity=Severity.LOW),
        ]

        results = loop.add_findings(findings)

        self.assertEqual(len(results), 3)
        self.assertEqual(loop.summary.total_findings, 3)
        self.assertEqual(loop.summary.scaffolds_generated, 3)

    def test_record_compilation_success(self):
        """Can record successful compilation."""
        loop = VerificationLoop()
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        loop.add_finding(finding)

        loop.record_compilation("VKG-001", success=True)

        result = loop.get_result("VKG-001")
        self.assertTrue(result.compiled)
        self.assertIsNone(result.compilation_error)
        self.assertEqual(loop.summary.scaffolds_compiled, 1)

    def test_record_compilation_failure(self):
        """Can record failed compilation."""
        loop = VerificationLoop()
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        loop.add_finding(finding)

        loop.record_compilation("VKG-001", success=False, error="Import not found")

        result = loop.get_result("VKG-001")
        self.assertFalse(result.compiled)
        self.assertEqual(result.compilation_error, "Import not found")

    def test_record_execution_passed(self):
        """Can record passed test execution."""
        loop = VerificationLoop()
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        loop.add_finding(finding)
        loop.record_compilation("VKG-001", success=True)

        loop.record_execution("VKG-001", passed=True)

        result = loop.get_result("VKG-001")
        self.assertTrue(result.executed)
        self.assertEqual(result.finding.test_result, TestResult.PASSED)

    def test_record_execution_failed(self):
        """Can record failed test execution."""
        loop = VerificationLoop()
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        loop.add_finding(finding)
        loop.record_compilation("VKG-001", success=True)

        loop.record_execution("VKG-001", passed=False)

        result = loop.get_result("VKG-001")
        self.assertTrue(result.executed)
        self.assertEqual(result.finding.test_result, TestResult.FAILED)

    def test_set_verdict(self):
        """Can set verdict for finding."""
        loop = VerificationLoop()
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        loop.add_finding(finding)

        loop.set_verdict(
            "VKG-001",
            verdict=Verdict.CONFIRMED,
            evidence=["Test passed"],
            notes="Verified manually",
        )

        result = loop.get_result("VKG-001")
        self.assertEqual(result.verdict, Verdict.CONFIRMED)
        self.assertEqual(result.notes, "Verified manually")
        self.assertEqual(result.finding.verdict, Verdict.CONFIRMED)
        self.assertEqual(loop.summary.verdicts_confirmed, 1)

    def test_get_pending_findings(self):
        """Can get findings with pending verdicts."""
        loop = VerificationLoop()
        findings = [
            Finding(id="VKG-001", title="Bug 1", severity=Severity.HIGH),
            Finding(id="VKG-002", title="Bug 2", severity=Severity.MEDIUM),
        ]
        loop.add_findings(findings)
        loop.set_verdict("VKG-001", Verdict.CONFIRMED)

        pending = loop.get_pending_findings()

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].finding.id, "VKG-002")

    def test_get_confirmed_findings(self):
        """Can get confirmed findings."""
        loop = VerificationLoop()
        findings = [
            Finding(id="VKG-001", title="Bug 1", severity=Severity.HIGH),
            Finding(id="VKG-002", title="Bug 2", severity=Severity.MEDIUM),
        ]
        loop.add_findings(findings)
        loop.set_verdict("VKG-001", Verdict.CONFIRMED)
        loop.set_verdict("VKG-002", Verdict.FALSE_POSITIVE)

        confirmed = loop.get_confirmed_findings()

        self.assertEqual(len(confirmed), 1)
        self.assertEqual(confirmed[0].finding.id, "VKG-001")

    def test_complete_sets_timestamp(self):
        """Completing loop sets timestamp."""
        loop = VerificationLoop()
        finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
        loop.add_finding(finding)

        summary = loop.complete()

        self.assertIsNotNone(summary.started_at)
        self.assertIsNotNone(summary.completed_at)

    def test_storage_integration(self):
        """Can write scaffolds to storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            loop = VerificationLoop(storage_dir=storage_dir)

            finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
            result = loop.add_finding(finding)

            # Scaffold should be written
            scaffold_path = storage_dir / "scaffolds" / result.scaffold.filename
            self.assertTrue(scaffold_path.exists())

    def test_export_results(self):
        """Can export results to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            loop = VerificationLoop()

            finding = Finding(id="VKG-001", title="Test", severity=Severity.HIGH)
            loop.add_finding(finding)
            loop.set_verdict("VKG-001", Verdict.CONFIRMED)

            loop.export_results(output_path)

            self.assertTrue(output_path.exists())
            import json
            data = json.loads(output_path.read_text())
            self.assertIn("summary", data)
            self.assertIn("results", data)


class TestVerificationWorkflow(unittest.TestCase):
    """Tests for complete verification workflow."""

    def test_full_workflow(self):
        """Test complete verification workflow."""
        loop = VerificationLoop()

        # 1. Add findings
        findings = [
            Finding(
                id="VKG-001",
                title="Reentrancy",
                severity=Severity.CRITICAL,
                description="State modified after call",
            ),
            Finding(
                id="VKG-002",
                title="Missing access control",
                severity=Severity.HIGH,
                description="No onlyOwner modifier",
            ),
        ]
        loop.add_findings(findings)
        self.assertEqual(loop.summary.total_findings, 2)

        # 2. Record compilation
        loop.record_compilation("VKG-001", success=True)
        loop.record_compilation("VKG-002", success=False, error="Import error")
        self.assertEqual(loop.summary.scaffolds_compiled, 1)

        # 3. Record execution (only for compiled)
        loop.record_execution("VKG-001", passed=True)
        self.assertEqual(loop.summary.tests_executed, 1)

        # 4. Set verdicts
        loop.set_verdict(
            "VKG-001",
            Verdict.CONFIRMED,
            evidence=["Funds were drained"],
        )
        loop.set_verdict(
            "VKG-002",
            Verdict.INCONCLUSIVE,
            notes="Could not compile test",
        )

        # 5. Complete and verify
        summary = loop.complete()

        self.assertEqual(summary.verdicts_confirmed, 1)
        self.assertEqual(summary.verdicts_inconclusive, 1)
        self.assertEqual(summary.verdicts_pending, 0)
        self.assertEqual(summary.verification_rate, 1.0)


class TestFormatFunctions(unittest.TestCase):
    """Tests for formatting functions."""

    def test_format_verification_summary(self):
        """Can format summary as text."""
        summary = VerificationSummary(
            total_findings=10,
            scaffolds_generated=10,
            scaffolds_compiled=4,
            tests_executed=3,
            verdicts_confirmed=2,
            verdicts_false_positive=1,
            verdicts_inconclusive=1,
            verdicts_pending=6,
            compile_rate=0.4,
            execution_rate=0.3,
        )

        text = format_verification_summary(summary)

        self.assertIn("VERIFICATION SUMMARY", text)
        self.assertIn("Total Findings:      10", text)
        self.assertIn("Confirmed:         2", text)
        self.assertIn("40.0%", text)

    def test_format_finding_result(self):
        """Can format finding result as text."""
        finding = Finding(id="VKG-001", title="Reentrancy", severity=Severity.CRITICAL)
        result = VerificationResult(
            finding=finding,
            verdict=Verdict.CONFIRMED,
            notes="Classic CEI violation",
        )

        text = format_finding_result(result)

        self.assertIn("VKG-001", text)
        self.assertIn("Reentrancy", text)
        self.assertIn("critical", text)
        self.assertIn("confirmed", text)


class TestQualityIntegration(unittest.TestCase):
    """Tests for quality tracker integration."""

    def test_tracks_quality_metrics(self):
        """Loop tracks quality metrics."""
        loop = VerificationLoop()

        # Add several findings
        for i in range(5):
            finding = Finding(id=f"VKG-{i:03d}", title=f"Bug {i}", severity=Severity.HIGH)
            loop.add_finding(finding)

        # Record compilations (2 success, 3 fail)
        for i in range(5):
            success = i < 2
            loop.record_compilation(f"VKG-{i:03d}", success=success)

        # Check compile rate in summary
        summary = loop.get_summary()
        self.assertEqual(summary.scaffolds_compiled, 2)
        self.assertEqual(summary.compile_rate, 0.4)


if __name__ == "__main__":
    unittest.main()
