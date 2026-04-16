"""
Tests for Finding Schema Extension (Task 4.9)

Validates verdict and test result fields added to the Finding class.
"""

import unittest
from datetime import datetime

from alphaswarm_sol.enterprise.reports import (
    Finding,
    Severity,
    Verdict,
    TestResult,
)


class TestVerdictEnum(unittest.TestCase):
    """Tests for Verdict enum."""

    def test_all_verdicts_exist(self):
        """All verdict values are defined."""
        self.assertEqual(Verdict.PENDING.value, "pending")
        self.assertEqual(Verdict.CONFIRMED.value, "confirmed")
        self.assertEqual(Verdict.FALSE_POSITIVE.value, "false_positive")
        self.assertEqual(Verdict.INCONCLUSIVE.value, "inconclusive")
        self.assertEqual(Verdict.WONT_FIX.value, "wont_fix")

    def test_verdict_count(self):
        """Exactly 5 verdicts defined."""
        self.assertEqual(len(Verdict), 5)


class TestTestResultEnum(unittest.TestCase):
    """Tests for TestResult enum."""

    def test_all_results_exist(self):
        """All test result values are defined."""
        self.assertEqual(TestResult.NOT_RUN.value, "not_run")
        self.assertEqual(TestResult.PASSED.value, "passed")
        self.assertEqual(TestResult.FAILED.value, "failed")
        self.assertEqual(TestResult.ERROR.value, "error")

    def test_result_count(self):
        """Exactly 4 results defined."""
        self.assertEqual(len(TestResult), 4)


class TestFindingVerification(unittest.TestCase):
    """Tests for Finding verification fields."""

    def test_finding_has_default_verdict(self):
        """Finding defaults to PENDING verdict."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )
        self.assertEqual(finding.verdict, Verdict.PENDING)

    def test_finding_has_default_test_result(self):
        """Finding defaults to NOT_RUN test result."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )
        self.assertEqual(finding.test_result, TestResult.NOT_RUN)

    def test_finding_defaults_not_verified(self):
        """New finding is not verified."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )
        self.assertFalse(finding.is_verified)
        self.assertFalse(finding.is_true_positive)

    def test_finding_default_fields_empty(self):
        """Verification fields default to empty."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )
        self.assertEqual(finding.verdict_evidence, [])
        self.assertIsNone(finding.verdict_timestamp)
        self.assertIsNone(finding.test_scaffold_id)
        self.assertEqual(finding.auditor_notes, "")


class TestSetVerdict(unittest.TestCase):
    """Tests for set_verdict method."""

    def test_set_verdict_confirmed(self):
        """Can set verdict to CONFIRMED."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.set_verdict(Verdict.CONFIRMED)

        self.assertEqual(finding.verdict, Verdict.CONFIRMED)
        self.assertTrue(finding.is_verified)
        self.assertTrue(finding.is_true_positive)

    def test_set_verdict_false_positive(self):
        """Can set verdict to FALSE_POSITIVE."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.set_verdict(Verdict.FALSE_POSITIVE)

        self.assertEqual(finding.verdict, Verdict.FALSE_POSITIVE)
        self.assertTrue(finding.is_verified)
        self.assertFalse(finding.is_true_positive)

    def test_set_verdict_with_evidence(self):
        """Can set verdict with evidence."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.set_verdict(
            Verdict.CONFIRMED,
            evidence=["Test passed", "Funds were drained"],
        )

        self.assertEqual(len(finding.verdict_evidence), 2)
        self.assertIn("Test passed", finding.verdict_evidence)

    def test_set_verdict_with_notes(self):
        """Can set verdict with auditor notes."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.set_verdict(
            Verdict.CONFIRMED,
            notes="Classic CEI violation",
        )

        self.assertEqual(finding.auditor_notes, "Classic CEI violation")

    def test_set_verdict_sets_timestamp(self):
        """set_verdict sets timestamp."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        before = datetime.now()
        finding.set_verdict(Verdict.CONFIRMED)
        after = datetime.now()

        self.assertIsNotNone(finding.verdict_timestamp)
        self.assertGreaterEqual(finding.verdict_timestamp, before)
        self.assertLessEqual(finding.verdict_timestamp, after)


class TestLinkTest(unittest.TestCase):
    """Tests for link_test method."""

    def test_link_test_scaffold(self):
        """Can link test scaffold to finding."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.link_test("Test_VKG_001_reentrancy")

        self.assertEqual(finding.test_scaffold_id, "Test_VKG_001_reentrancy")


class TestRecordTestResult(unittest.TestCase):
    """Tests for record_test_result method."""

    def test_record_passed(self):
        """Can record PASSED test result."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.record_test_result(TestResult.PASSED)

        self.assertEqual(finding.test_result, TestResult.PASSED)

    def test_record_failed(self):
        """Can record FAILED test result."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.record_test_result(TestResult.FAILED)

        self.assertEqual(finding.test_result, TestResult.FAILED)

    def test_record_error(self):
        """Can record ERROR test result."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        finding.record_test_result(TestResult.ERROR)

        self.assertEqual(finding.test_result, TestResult.ERROR)


class TestFindingSerialization(unittest.TestCase):
    """Tests for Finding serialization with verdict fields."""

    def test_to_dict_includes_verdict_fields(self):
        """to_dict includes verification fields."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        data = finding.to_dict()

        self.assertIn("verdict", data)
        self.assertIn("verdict_evidence", data)
        self.assertIn("verdict_timestamp", data)
        self.assertIn("test_scaffold_id", data)
        self.assertIn("test_result", data)
        self.assertIn("auditor_notes", data)

    def test_to_dict_verdict_values(self):
        """to_dict uses string values for enums."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )
        finding.set_verdict(Verdict.CONFIRMED)
        finding.record_test_result(TestResult.PASSED)

        data = finding.to_dict()

        self.assertEqual(data["verdict"], "confirmed")
        self.assertEqual(data["test_result"], "passed")

    def test_to_dict_timestamp_format(self):
        """to_dict formats timestamp as ISO string."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )
        finding.set_verdict(Verdict.CONFIRMED)

        data = finding.to_dict()

        self.assertIsNotNone(data["verdict_timestamp"])
        # Should be ISO format string
        self.assertIn("T", data["verdict_timestamp"])

    def test_to_dict_null_timestamp_when_pending(self):
        """to_dict has null timestamp when not verified."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
        )

        data = finding.to_dict()

        self.assertIsNone(data["verdict_timestamp"])


class TestBackwardCompatibility(unittest.TestCase):
    """Tests for backward compatibility."""

    def test_existing_fields_unchanged(self):
        """Original fields still work."""
        finding = Finding(
            id="VKG-001",
            title="Test Finding",
            severity=Severity.CRITICAL,
            description="Test description",
            location="Test.sol:10",
            evidence=["evidence1", "evidence2"],
            recommendation="Fix it",
        )

        self.assertEqual(finding.id, "VKG-001")
        self.assertEqual(finding.title, "Test Finding")
        self.assertEqual(finding.severity, Severity.CRITICAL)
        self.assertEqual(finding.description, "Test description")
        self.assertEqual(finding.location, "Test.sol:10")
        self.assertEqual(finding.evidence, ["evidence1", "evidence2"])
        self.assertEqual(finding.recommendation, "Fix it")

    def test_minimal_finding_works(self):
        """Can create Finding with only required fields."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.LOW,
        )

        self.assertEqual(finding.id, "VKG-001")
        self.assertEqual(finding.description, "")
        self.assertEqual(finding.evidence, [])

    def test_to_dict_has_original_fields(self):
        """to_dict still has all original fields."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
            description="Desc",
            location="Loc",
            recommendation="Rec",
        )

        data = finding.to_dict()

        self.assertEqual(data["id"], "VKG-001")
        self.assertEqual(data["title"], "Test")
        self.assertEqual(data["severity"], "high")
        self.assertEqual(data["description"], "Desc")
        self.assertEqual(data["location"], "Loc")
        self.assertEqual(data["recommendation"], "Rec")


class TestVerificationWorkflow(unittest.TestCase):
    """Tests for complete verification workflow."""

    def test_full_verification_workflow(self):
        """Test complete finding verification workflow."""
        # 1. Create finding
        finding = Finding(
            id="VKG-001",
            title="Reentrancy in withdraw",
            severity=Severity.CRITICAL,
            description="State modified after external call",
            location="Vault.sol:withdraw:45",
            recommendation="Add reentrancy guard",
        )
        self.assertFalse(finding.is_verified)

        # 2. Link test scaffold
        finding.link_test("Test_VKG_001_reentrancy")
        self.assertEqual(finding.test_scaffold_id, "Test_VKG_001_reentrancy")

        # 3. Record test result
        finding.record_test_result(TestResult.PASSED)
        self.assertEqual(finding.test_result, TestResult.PASSED)

        # 4. Set verdict
        finding.set_verdict(
            Verdict.CONFIRMED,
            evidence=["Test passed - funds were drained", "CEI pattern violated"],
            notes="Classic reentrancy vulnerability",
        )

        # 5. Verify final state
        self.assertTrue(finding.is_verified)
        self.assertTrue(finding.is_true_positive)
        self.assertEqual(finding.verdict, Verdict.CONFIRMED)
        self.assertEqual(len(finding.verdict_evidence), 2)
        self.assertIsNotNone(finding.verdict_timestamp)

        # 6. Serialize and verify
        data = finding.to_dict()
        self.assertEqual(data["verdict"], "confirmed")
        self.assertEqual(data["test_result"], "passed")
        self.assertIn("funds were drained", data["verdict_evidence"][0])


if __name__ == "__main__":
    unittest.main()
