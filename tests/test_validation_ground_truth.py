"""Tests for Ground Truth Validation (Phase 5 R5.1-5.3).

Tests the ground truth schema and matching logic for real-world validation.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from alphaswarm_sol.validation.ground_truth import (
    VulnerabilityCategory,
    Severity,
    AuditFinding,
    ProjectGroundTruth,
    VKGFinding,
    MatchResult,
    ValidationResult,
    FindingMatcher,
    normalize_category,
    is_category_match,
    format_validation_report,
)


class TestVulnerabilityCategory(unittest.TestCase):
    """Tests for VulnerabilityCategory enum."""

    def test_vkg_detectable_categories(self):
        """VKG can detect core vulnerability types."""
        detectable = VulnerabilityCategory.vkg_detectable()

        self.assertIn(VulnerabilityCategory.REENTRANCY, detectable)
        self.assertIn(VulnerabilityCategory.ACCESS_CONTROL, detectable)
        self.assertIn(VulnerabilityCategory.ORACLE_MANIPULATION, detectable)
        self.assertIn(VulnerabilityCategory.DOS, detectable)

    def test_out_of_scope_categories(self):
        """Business logic and economic issues are out of scope."""
        out_of_scope = VulnerabilityCategory.out_of_scope()

        self.assertIn(VulnerabilityCategory.BUSINESS_LOGIC, out_of_scope)
        self.assertIn(VulnerabilityCategory.ECONOMIC, out_of_scope)
        self.assertIn(VulnerabilityCategory.INFORMATIONAL, out_of_scope)

    def test_no_overlap(self):
        """Detectable and out of scope don't overlap."""
        detectable = VulnerabilityCategory.vkg_detectable()
        out_of_scope = VulnerabilityCategory.out_of_scope()

        self.assertEqual(len(detectable & out_of_scope), 0)


class TestAuditFinding(unittest.TestCase):
    """Tests for AuditFinding dataclass."""

    def test_create_finding(self):
        """Can create an audit finding."""
        finding = AuditFinding(
            id="H-01",
            title="Reentrancy in withdraw",
            category=VulnerabilityCategory.REENTRANCY,
            severity=Severity.HIGH,
            file="src/Vault.sol",
            function="withdraw",
            line_start=45,
            line_end=67,
            description="State is updated after external call",
        )

        self.assertEqual(finding.id, "H-01")
        self.assertEqual(finding.category, VulnerabilityCategory.REENTRANCY)
        self.assertTrue(finding.vkg_should_find)

    def test_finding_to_dict(self):
        """Finding serializes to dict."""
        finding = AuditFinding(
            id="M-02",
            title="Missing access control",
            category=VulnerabilityCategory.ACCESS_CONTROL,
            severity=Severity.MEDIUM,
            file="src/Token.sol",
        )

        data = finding.to_dict()

        self.assertEqual(data["id"], "M-02")
        self.assertEqual(data["category"], "access_control")
        self.assertEqual(data["severity"], "medium")
        self.assertIn("location", data)

    def test_finding_from_dict(self):
        """Finding deserializes from dict."""
        data = {
            "id": "C-01",
            "title": "Critical reentrancy",
            "category": "reentrancy",
            "severity": "critical",
            "location": {
                "file": "src/Vault.sol",
                "function": "withdraw",
                "line_start": 100,
                "line_end": 150,
            },
            "vkg_should_find": True,
        }

        finding = AuditFinding.from_dict(data)

        self.assertEqual(finding.id, "C-01")
        self.assertEqual(finding.category, VulnerabilityCategory.REENTRANCY)
        self.assertEqual(finding.severity, Severity.CRITICAL)
        self.assertEqual(finding.file, "src/Vault.sol")
        self.assertEqual(finding.line_start, 100)


class TestProjectGroundTruth(unittest.TestCase):
    """Tests for ProjectGroundTruth."""

    def create_sample_ground_truth(self) -> ProjectGroundTruth:
        """Create sample ground truth for testing."""
        return ProjectGroundTruth(
            project_name="TestVault",
            project_type="lending",
            audit_source="TestAuditor",
            audit_date="2025-01-01",
            code_url="https://github.com/test/vault",
            code_commit="abc123",
            findings=[
                AuditFinding(
                    id="H-01",
                    title="Reentrancy",
                    category=VulnerabilityCategory.REENTRANCY,
                    severity=Severity.HIGH,
                    file="src/Vault.sol",
                    vkg_should_find=True,
                ),
                AuditFinding(
                    id="M-01",
                    title="Missing access control",
                    category=VulnerabilityCategory.ACCESS_CONTROL,
                    severity=Severity.MEDIUM,
                    file="src/Vault.sol",
                    vkg_should_find=True,
                ),
                AuditFinding(
                    id="L-01",
                    title="Business logic issue",
                    category=VulnerabilityCategory.BUSINESS_LOGIC,
                    severity=Severity.LOW,
                    file="src/Vault.sol",
                    vkg_should_find=False,  # Out of scope
                ),
            ],
        )

    def test_create_ground_truth(self):
        """Can create project ground truth."""
        gt = self.create_sample_ground_truth()

        self.assertEqual(gt.project_name, "TestVault")
        self.assertEqual(gt.total_findings, 3)

    def test_vkg_detectable_findings(self):
        """Can filter to VKG-detectable findings."""
        gt = self.create_sample_ground_truth()

        detectable = gt.vkg_detectable_findings

        self.assertEqual(len(detectable), 2)
        self.assertTrue(all(f.vkg_should_find for f in detectable))

    def test_out_of_scope_findings(self):
        """Can filter to out-of-scope findings."""
        gt = self.create_sample_ground_truth()

        out_of_scope = gt.out_of_scope_findings

        self.assertEqual(len(out_of_scope), 1)
        self.assertFalse(out_of_scope[0].vkg_should_find)

    def test_findings_by_category(self):
        """Can group findings by category."""
        gt = self.create_sample_ground_truth()

        by_cat = gt.findings_by_category()

        self.assertIn(VulnerabilityCategory.REENTRANCY, by_cat)
        self.assertEqual(len(by_cat[VulnerabilityCategory.REENTRANCY]), 1)

    def test_findings_by_severity(self):
        """Can group findings by severity."""
        gt = self.create_sample_ground_truth()

        by_sev = gt.findings_by_severity()

        self.assertIn(Severity.HIGH, by_sev)
        self.assertIn(Severity.MEDIUM, by_sev)
        self.assertIn(Severity.LOW, by_sev)

    def test_save_and_load(self):
        """Can save and load ground truth."""
        gt = self.create_sample_ground_truth()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ground-truth.yaml"

            gt.save(path)
            self.assertTrue(path.exists())

            loaded = ProjectGroundTruth.load(path)

            self.assertEqual(loaded.project_name, gt.project_name)
            self.assertEqual(loaded.total_findings, gt.total_findings)
            self.assertEqual(loaded.findings[0].id, gt.findings[0].id)


class TestCategoryMatching(unittest.TestCase):
    """Tests for category normalization and matching."""

    def test_normalize_category(self):
        """Categories are normalized."""
        self.assertEqual(normalize_category("reentrancy"), "reentrancy")
        self.assertEqual(normalize_category("REENTRANCY"), "reentrancy")
        self.assertEqual(normalize_category("cross-function-reentrancy"), "reentrancy")
        self.assertEqual(normalize_category("access_control"), "access_control")
        self.assertEqual(normalize_category("access-control"), "access_control")

    def test_is_category_match_exact(self):
        """Exact category match works."""
        self.assertTrue(is_category_match("reentrancy", "reentrancy"))
        self.assertTrue(is_category_match("access_control", "access_control"))

    def test_is_category_match_alias(self):
        """Category aliases match."""
        self.assertTrue(is_category_match("reentrancy", "cross-function-reentrancy"))
        self.assertTrue(is_category_match("access_control", "authorization"))
        self.assertTrue(is_category_match("dos", "denial-of-service"))

    def test_is_category_match_case_insensitive(self):
        """Category matching is case insensitive."""
        self.assertTrue(is_category_match("REENTRANCY", "reentrancy"))
        self.assertTrue(is_category_match("Access_Control", "access-control"))

    def test_is_category_match_different(self):
        """Different categories don't match."""
        self.assertFalse(is_category_match("reentrancy", "access_control"))
        self.assertFalse(is_category_match("dos", "arithmetic"))


class TestVKGFinding(unittest.TestCase):
    """Tests for VKGFinding."""

    def test_create_from_pattern_match(self):
        """Can create from pattern engine output."""
        match = {
            "pattern_id": "reentrancy-classic",
            "category": "reentrancy",
            "severity": "critical",
            "location": {
                "file": "src/Vault.sol",
                "function": "withdraw",
                "line": 55,
            },
            "confidence": 0.85,
            "why_match": "State written after external call",
        }

        finding = VKGFinding.from_pattern_match(match)

        self.assertEqual(finding.pattern_id, "reentrancy-classic")
        self.assertEqual(finding.category, "reentrancy")
        self.assertEqual(finding.file, "src/Vault.sol")
        self.assertEqual(finding.function, "withdraw")
        self.assertEqual(finding.line, 55)
        self.assertEqual(finding.confidence, 0.85)


class TestFindingMatcher(unittest.TestCase):
    """Tests for FindingMatcher."""

    def test_exact_match(self):
        """Exact function match is detected."""
        matcher = FindingMatcher()

        audit_finding = AuditFinding(
            id="H-01",
            title="Reentrancy",
            category=VulnerabilityCategory.REENTRANCY,
            severity=Severity.HIGH,
            file="src/Vault.sol",
            function="withdraw",
            line_start=50,
            line_end=70,
        )

        vkg_finding = VKGFinding(
            id="VKG-001",
            pattern_id="reentrancy-classic",
            category="reentrancy",
            severity="high",
            file="src/Vault.sol",
            function="withdraw",
            line=55,
            confidence=0.9,
        )

        result = matcher.match_finding(vkg_finding, [audit_finding])

        self.assertIsNotNone(result)
        audit, match_type, confidence = result
        self.assertEqual(audit.id, "H-01")
        self.assertEqual(match_type, "exact")
        self.assertGreater(confidence, 0.5)

    def test_fuzzy_match_by_line(self):
        """Fuzzy match by line proximity works."""
        matcher = FindingMatcher(line_tolerance=10)

        audit_finding = AuditFinding(
            id="M-01",
            title="Access control",
            category=VulnerabilityCategory.ACCESS_CONTROL,
            severity=Severity.MEDIUM,
            file="src/Token.sol",
            line_start=100,
            line_end=120,
        )

        vkg_finding = VKGFinding(
            id="VKG-002",
            pattern_id="auth-missing",
            category="access_control",
            severity="medium",
            file="src/Token.sol",
            function=None,
            line=105,  # Within line range
            confidence=0.7,
        )

        result = matcher.match_finding(vkg_finding, [audit_finding])

        self.assertIsNotNone(result)

    def test_no_match_different_file(self):
        """Different files don't match."""
        matcher = FindingMatcher()

        audit_finding = AuditFinding(
            id="H-01",
            title="Reentrancy",
            category=VulnerabilityCategory.REENTRANCY,
            severity=Severity.HIGH,
            file="src/Vault.sol",
            line_start=50,
            line_end=70,
        )

        vkg_finding = VKGFinding(
            id="VKG-001",
            pattern_id="reentrancy-classic",
            category="reentrancy",
            severity="high",
            file="src/Token.sol",  # Different file
            function="withdraw",
            line=55,
            confidence=0.9,
        )

        result = matcher.match_finding(vkg_finding, [audit_finding])

        self.assertIsNone(result)

    def test_match_by_filename_only(self):
        """Matches by filename, not full path."""
        matcher = FindingMatcher()

        audit_finding = AuditFinding(
            id="H-01",
            title="Reentrancy",
            category=VulnerabilityCategory.REENTRANCY,
            severity=Severity.HIGH,
            file="contracts/Vault.sol",  # Different path
            function="withdraw",
            line_start=50,
            line_end=70,
        )

        vkg_finding = VKGFinding(
            id="VKG-001",
            pattern_id="reentrancy-classic",
            category="reentrancy",
            severity="high",
            file="src/Vault.sol",  # Different path, same filename
            function="withdraw",
            line=55,
            confidence=0.9,
        )

        result = matcher.match_finding(vkg_finding, [audit_finding])

        self.assertIsNotNone(result)


class TestValidationResult(unittest.TestCase):
    """Tests for ValidationResult and metrics calculation."""

    def test_precision_calculation(self):
        """Precision is calculated correctly."""
        gt = ProjectGroundTruth(
            project_name="Test",
            project_type="lending",
            audit_source="Test",
            audit_date="2025-01-01",
            findings=[],
        )

        result = ValidationResult(
            project_name="Test",
            timestamp="2025-01-01",
            ground_truth=gt,
            vkg_findings=[],
            matches=[],
        )

        # 3 TP, 1 FP = 3/(3+1) = 0.75
        result.true_positives = [
            (VKGFinding("1", "p", "c", "h", "f", None, 1, 0.5), AuditFinding("A1", "T", VulnerabilityCategory.REENTRANCY, Severity.HIGH, "f")),
            (VKGFinding("2", "p", "c", "h", "f", None, 2, 0.5), AuditFinding("A2", "T", VulnerabilityCategory.REENTRANCY, Severity.HIGH, "f")),
            (VKGFinding("3", "p", "c", "h", "f", None, 3, 0.5), AuditFinding("A3", "T", VulnerabilityCategory.REENTRANCY, Severity.HIGH, "f")),
        ]
        result.false_positives = [
            VKGFinding("4", "p", "c", "h", "f", None, 4, 0.5),
        ]

        self.assertAlmostEqual(result.precision, 0.75, places=2)

    def test_recall_calculation(self):
        """Recall is calculated correctly."""
        gt = ProjectGroundTruth(
            project_name="Test",
            project_type="lending",
            audit_source="Test",
            audit_date="2025-01-01",
            findings=[],
        )

        result = ValidationResult(
            project_name="Test",
            timestamp="2025-01-01",
            ground_truth=gt,
            vkg_findings=[],
            matches=[],
        )

        # 2 TP, 2 FN = 2/(2+2) = 0.50
        result.true_positives = [
            (VKGFinding("1", "p", "c", "h", "f", None, 1, 0.5), AuditFinding("A1", "T", VulnerabilityCategory.REENTRANCY, Severity.HIGH, "f")),
            (VKGFinding("2", "p", "c", "h", "f", None, 2, 0.5), AuditFinding("A2", "T", VulnerabilityCategory.REENTRANCY, Severity.HIGH, "f")),
        ]
        result.false_negatives = [
            AuditFinding("A3", "T", VulnerabilityCategory.ACCESS_CONTROL, Severity.MEDIUM, "f"),
            AuditFinding("A4", "T", VulnerabilityCategory.DOS, Severity.LOW, "f"),
        ]

        self.assertAlmostEqual(result.recall, 0.50, places=2)

    def test_f1_score_calculation(self):
        """F1 score is calculated correctly."""
        gt = ProjectGroundTruth(
            project_name="Test",
            project_type="lending",
            audit_source="Test",
            audit_date="2025-01-01",
            findings=[],
        )

        result = ValidationResult(
            project_name="Test",
            timestamp="2025-01-01",
            ground_truth=gt,
            vkg_findings=[],
            matches=[],
        )

        # Precision = 0.8, Recall = 0.5
        # F1 = 2 * 0.8 * 0.5 / (0.8 + 0.5) = 0.8 / 1.3 = 0.615
        result.true_positives = [
            (VKGFinding(str(i), "p", "c", "h", "f", None, i, 0.5), AuditFinding(f"A{i}", "T", VulnerabilityCategory.REENTRANCY, Severity.HIGH, "f"))
            for i in range(4)
        ]
        result.false_positives = [VKGFinding("FP", "p", "c", "h", "f", None, 10, 0.5)]
        result.false_negatives = [
            AuditFinding(f"FN{i}", "T", VulnerabilityCategory.DOS, Severity.LOW, "f")
            for i in range(4)
        ]

        self.assertAlmostEqual(result.precision, 0.8, places=2)
        self.assertAlmostEqual(result.recall, 0.5, places=2)
        self.assertAlmostEqual(result.f1_score, 0.615, places=2)

    def test_to_dict(self):
        """Result serializes to dict."""
        gt = ProjectGroundTruth(
            project_name="Test",
            project_type="lending",
            audit_source="Test",
            audit_date="2025-01-01",
            findings=[],
        )

        result = ValidationResult(
            project_name="Test",
            timestamp="2025-01-01T00:00:00",
            ground_truth=gt,
            vkg_findings=[],
            matches=[],
        )

        data = result.to_dict()

        self.assertIn("metrics", data)
        self.assertIn("precision", data["metrics"])
        self.assertIn("recall", data["metrics"])
        self.assertIn("f1_score", data["metrics"])


class TestValidateProject(unittest.TestCase):
    """Integration tests for project validation workflow."""

    def test_full_validation_workflow(self):
        """Full validation workflow produces correct metrics."""
        # Setup ground truth
        gt = ProjectGroundTruth(
            project_name="TestVault",
            project_type="lending",
            audit_source="TestAuditor",
            audit_date="2025-01-01",
            findings=[
                AuditFinding(
                    id="H-01",
                    title="Reentrancy in withdraw",
                    category=VulnerabilityCategory.REENTRANCY,
                    severity=Severity.HIGH,
                    file="src/Vault.sol",
                    function="withdraw",
                    line_start=50,
                    line_end=70,
                    vkg_should_find=True,
                ),
                AuditFinding(
                    id="M-01",
                    title="Missing access control",
                    category=VulnerabilityCategory.ACCESS_CONTROL,
                    severity=Severity.MEDIUM,
                    file="src/Vault.sol",
                    function="setFee",
                    line_start=100,
                    line_end=110,
                    vkg_should_find=True,
                ),
                AuditFinding(
                    id="L-01",
                    title="Business logic flaw",
                    category=VulnerabilityCategory.BUSINESS_LOGIC,
                    severity=Severity.LOW,
                    file="src/Vault.sol",
                    line_start=200,
                    line_end=250,
                    vkg_should_find=False,  # Out of scope
                ),
            ],
        )

        # VKG findings
        vkg_findings = [
            VKGFinding(
                id="VKG-001",
                pattern_id="reentrancy-classic",
                category="reentrancy",
                severity="high",
                file="src/Vault.sol",
                function="withdraw",
                line=55,
                confidence=0.9,
            ),
            VKGFinding(
                id="VKG-002",
                pattern_id="unknown-pattern",
                category="unknown",
                severity="low",
                file="src/Token.sol",  # Different file - FP
                function="transfer",
                line=30,
                confidence=0.3,
            ),
        ]

        # Run validation
        matcher = FindingMatcher()
        result = matcher.validate_project(gt, vkg_findings)

        # Check results
        # TP: VKG-001 matches H-01
        # FP: VKG-002 (different file, no match)
        # FN: M-01 (not detected by VKG)
        # Business logic finding (L-01) is not counted in recall

        self.assertEqual(len(result.true_positives), 1)
        self.assertEqual(len(result.false_positives), 1)
        self.assertEqual(len(result.false_negatives), 1)

        # Precision = 1/(1+1) = 0.5
        self.assertAlmostEqual(result.precision, 0.5, places=2)

        # Recall = 1/(1+1) = 0.5 (only 2 VKG-detectable findings)
        self.assertAlmostEqual(result.recall, 0.5, places=2)


class TestFormatReport(unittest.TestCase):
    """Tests for report formatting."""

    def test_format_validation_report(self):
        """Report formatting works."""
        gt = ProjectGroundTruth(
            project_name="TestProject",
            project_type="lending",
            audit_source="Auditor",
            audit_date="2025-01-01",
            findings=[
                AuditFinding("H-01", "Bug", VulnerabilityCategory.REENTRANCY, Severity.HIGH, "f.sol"),
            ],
        )

        result = ValidationResult(
            project_name="TestProject",
            timestamp="2025-01-01",
            ground_truth=gt,
            vkg_findings=[],
            matches=[],
        )

        report = format_validation_report(result)

        self.assertIn("TestProject", report)
        self.assertIn("VALIDATION REPORT", report)
        self.assertIn("METRICS", report)
        self.assertIn("Precision", report)


if __name__ == "__main__":
    unittest.main()
