"""
Tests for Test Scaffold Generator (Tasks 4.5, 4.6)

Validates Tier 1 and Tier 2 test scaffold generation.
"""

import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.enterprise.reports import Finding, Severity
from alphaswarm_sol.testing.detection import detect_project_structure, ProjectConfig, ProjectType
from alphaswarm_sol.testing.generator import (
    TestScaffold,
    generate_tier1_scaffold,
    generate_tier2_scaffold,
    generate_scaffolds,
    write_scaffold_to_file,
    _make_safe_identifier,
    _extract_contract_name,
    _extract_category,
)
from alphaswarm_sol.testing.tiers import TestTier


class TestTestScaffold(unittest.TestCase):
    """Tests for TestScaffold dataclass."""

    def test_scaffold_attributes(self):
        """TestScaffold has all required attributes."""
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=1,
            content="contract Test {}",
            filename="Test.t.sol",
            confidence=0.9,
        )
        self.assertEqual(scaffold.finding_id, "VKG-001")
        self.assertEqual(scaffold.tier, 1)
        self.assertEqual(scaffold.filename, "Test.t.sol")
        self.assertEqual(scaffold.confidence, 0.9)

    def test_scaffold_to_dict(self):
        """TestScaffold can be serialized to dict."""
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=2,
            content="contract Test {}",
            filename="Test.t.sol",
            compiled=True,
            confidence=0.4,
        )
        d = scaffold.to_dict()
        self.assertEqual(d["finding_id"], "VKG-001")
        self.assertEqual(d["tier"], 2)
        self.assertEqual(d["compiled"], True)
        self.assertEqual(d["confidence"], 0.4)


class TestTier1Generator(unittest.TestCase):
    """Tests for Tier 1 (Template) generator."""

    def test_tier1_never_fails_minimal_finding(self):
        """Tier 1 generator must never throw exceptions - minimal finding."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
            description="Test description",
            location="Test.sol:1",
            recommendation="Fix it",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIsNotNone(scaffold)
        self.assertIsNotNone(scaffold.content)
        self.assertGreater(len(scaffold.content), 0)
        self.assertEqual(scaffold.tier, 1)

    def test_tier1_never_fails_empty_finding(self):
        """Tier 1 handles empty/minimal finding."""
        finding = Finding(
            id="",
            title="",
            severity=Severity.LOW,
            description="",
            location="",
            recommendation="",
        )

        # Must not throw
        scaffold = generate_tier1_scaffold(finding)
        self.assertEqual(scaffold.tier, 1)
        self.assertIn("TODO", scaffold.content)

    def test_tier1_contains_todos(self):
        """Tier 1 output contains TODO markers."""
        finding = Finding(
            id="VKG-001",
            title="Test Vuln",
            severity=Severity.CRITICAL,
            description="Reentrancy in withdraw",
            location="Vault.sol:withdraw:45",
            recommendation="Use checks-effects-interactions",
        )

        scaffold = generate_tier1_scaffold(finding)
        todo_count = scaffold.content.count("TODO")
        self.assertGreaterEqual(todo_count, 5)  # At least 5 TODOs

    def test_tier1_contains_finding_info(self):
        """Tier 1 includes finding information in comments."""
        finding = Finding(
            id="VKG-123",
            title="Critical Reentrancy",
            severity=Severity.CRITICAL,
            description="State updated after external call",
            location="Vault.sol:withdraw:45",
            recommendation="Use reentrancy guard",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIn("VKG-123", scaffold.content)
        self.assertIn("Vault.sol", scaffold.content)

    def test_tier1_filename_convention(self):
        """Tier 1 filename follows convention."""
        finding = Finding(
            id="VKG-001",
            title="Reentrancy",
            severity=Severity.HIGH,
            description="Reentrancy bug",
            location="Token.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertTrue(scaffold.filename.startswith("Test_"))
        self.assertTrue(scaffold.filename.endswith(".t.sol"))

    def test_tier1_includes_attack_pattern(self):
        """Tier 1 includes attack pattern comments."""
        finding = Finding(
            id="VKG-001",
            title="Reentrancy in withdraw",
            severity=Severity.CRITICAL,
            description="Classic reentrancy",
            location="Vault.sol:1",
            recommendation="Add reentrancy guard",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIn("Attack Pattern", scaffold.content)

    def test_tier1_category_detection_reentrancy(self):
        """Tier 1 detects reentrancy category."""
        finding = Finding(
            id="VKG-001",
            title="Reentrancy vulnerability",
            severity=Severity.HIGH,
            description="State modified after call",
            location="Test.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_tier1_scaffold(finding)
        # Should detect reentrancy category
        self.assertIn("reentrancy", scaffold.filename.lower())

    def test_tier1_category_detection_access_control(self):
        """Tier 1 detects access control category."""
        finding = Finding(
            id="VKG-002",
            title="Missing authorization check",
            severity=Severity.HIGH,
            description="No access control on admin function",
            location="Admin.sol:1",
            recommendation="Add onlyOwner",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIn("access_control", scaffold.filename.lower())

    def test_tier1_valid_solidity_structure(self):
        """Tier 1 output has valid Solidity structure."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.MEDIUM,
            description="Test",
            location="Test.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIn("// SPDX-License-Identifier:", scaffold.content)
        self.assertIn("pragma solidity", scaffold.content)
        self.assertIn("contract", scaffold.content)
        self.assertIn("function", scaffold.content)

    def test_tier1_confidence_always_high(self):
        """Tier 1 always has high confidence (it's a template)."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.LOW,
            description="",
            location="",
            recommendation="",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertEqual(scaffold.confidence, 1.0)


class TestTier2Generator(unittest.TestCase):
    """Tests for Tier 2 (Smart Template) generator."""

    def test_tier2_basic_generation(self):
        """Tier 2 generates valid scaffold."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
            description="Test description",
            location="Token.sol:transfer:50",
            recommendation="Fix it",
        )

        scaffold = generate_tier2_scaffold(finding)
        self.assertIsNotNone(scaffold)
        self.assertEqual(scaffold.tier, 2)

    def test_tier2_includes_pragma_from_source(self):
        """Tier 2 uses pragma from source contract."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
            description="Test",
            location="Test.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_tier2_scaffold(finding, source_pragma="^0.8.20")
        self.assertIn("^0.8.20", scaffold.content)

    def test_tier2_with_project_config(self):
        """Tier 2 uses project config for imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "foundry.toml").write_text('[profile.default]\n')
            (root / "lib/forge-std").mkdir(parents=True)

            config = detect_project_structure(root)
            finding = Finding(
                id="VKG-001",
                title="Test",
                severity=Severity.HIGH,
                description="Test",
                location="src/Token.sol:transfer:50",
                recommendation="Fix",
            )

            scaffold = generate_tier2_scaffold(finding, config)
            self.assertIn("forge-std", scaffold.content)

    def test_tier2_confidence_realistic(self):
        """Tier 2 confidence is in realistic range."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.MEDIUM,
            description="Test",
            location="Test.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_tier2_scaffold(finding)
        # Tier 2 should have moderate confidence (30-60%)
        self.assertGreater(scaffold.confidence, 0.0)
        self.assertLessEqual(scaffold.confidence, 0.6)

    def test_tier2_includes_test_inheritance(self):
        """Tier 2 includes Test inheritance."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.LOW,
            description="Test",
            location="Test.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_tier2_scaffold(finding)
        self.assertIn("is Test", scaffold.content)

    def test_tier2_includes_setup(self):
        """Tier 2 includes setUp function."""
        finding = Finding(
            id="VKG-001",
            title="Test",
            severity=Severity.HIGH,
            description="Test",
            location="Contract.sol:1",
            recommendation="Fix",
        )

        scaffold = generate_tier2_scaffold(finding)
        self.assertIn("function setUp()", scaffold.content)

    def test_tier2_falls_back_to_tier1_on_error(self):
        """Tier 2 falls back to Tier 1 on errors."""
        # Create a finding that might cause issues
        finding = Finding(
            id="",
            title=None,  # type: ignore - intentionally bad
            severity=Severity.LOW,
            description="",
            location="",
            recommendation="",
        )

        # Should not throw, should fall back gracefully
        scaffold = generate_tier2_scaffold(finding)
        self.assertIsNotNone(scaffold)


class TestHelperFunctions(unittest.TestCase):
    """Tests for helper functions."""

    def test_make_safe_identifier_basic(self):
        """Make safe identifier from normal string."""
        result = _make_safe_identifier("VKG-001")
        self.assertEqual(result, "VKG_001")

    def test_make_safe_identifier_special_chars(self):
        """Handle special characters."""
        result = _make_safe_identifier("test@#$%vuln")
        self.assertNotIn("@", result)
        self.assertNotIn("#", result)

    def test_make_safe_identifier_leading_number(self):
        """Handle leading numbers."""
        result = _make_safe_identifier("123test")
        self.assertTrue(result[0].isalpha())

    def test_make_safe_identifier_empty(self):
        """Handle empty string."""
        result = _make_safe_identifier("")
        self.assertEqual(result, "Unknown")

    def test_extract_contract_name_from_path(self):
        """Extract contract name from file path."""
        result = _extract_contract_name("src/Token.sol:transfer:45")
        self.assertEqual(result, "Token")

    def test_extract_contract_name_simple_path(self):
        """Extract from simple path."""
        result = _extract_contract_name("Vault.sol")
        self.assertEqual(result, "Vault")

    def test_extract_contract_name_empty(self):
        """Handle empty location."""
        result = _extract_contract_name("")
        self.assertEqual(result, "TargetContract")

    def test_extract_category_reentrancy(self):
        """Detect reentrancy category."""
        finding = Finding(
            id="1",
            title="Reentrancy in withdraw",
            severity=Severity.HIGH,
            description="",
            location="",
            recommendation="",
        )
        result = _extract_category(finding)
        self.assertEqual(result, "reentrancy")

    def test_extract_category_access_control(self):
        """Detect access control category."""
        finding = Finding(
            id="1",
            title="Missing owner check",
            severity=Severity.HIGH,
            description="unauthorized access possible",
            location="",
            recommendation="",
        )
        result = _extract_category(finding)
        self.assertEqual(result, "access_control")

    def test_extract_category_unknown(self):
        """Return unknown for unrecognized category."""
        finding = Finding(
            id="1",
            title="Something else",
            severity=Severity.LOW,
            description="random issue",
            location="",
            recommendation="",
        )
        result = _extract_category(finding)
        self.assertEqual(result, "unknown")


class TestBatchGeneration(unittest.TestCase):
    """Tests for batch scaffold generation."""

    def test_generate_multiple_scaffolds(self):
        """Generate scaffolds for multiple findings."""
        findings = [
            Finding(id="VKG-001", title="Bug 1", severity=Severity.HIGH, description="", location="A.sol", recommendation=""),
            Finding(id="VKG-002", title="Bug 2", severity=Severity.MEDIUM, description="", location="B.sol", recommendation=""),
            Finding(id="VKG-003", title="Bug 3", severity=Severity.LOW, description="", location="C.sol", recommendation=""),
        ]

        scaffolds = generate_scaffolds(findings)
        self.assertEqual(len(scaffolds), 3)
        self.assertTrue(all(s.tier == 1 for s in scaffolds))

    def test_generate_tier2_batch(self):
        """Generate Tier 2 scaffolds in batch."""
        findings = [
            Finding(id="VKG-001", title="Bug 1", severity=Severity.HIGH, description="", location="A.sol", recommendation=""),
        ]

        scaffolds = generate_scaffolds(findings, tier=TestTier.TIER_2_SMART)
        self.assertEqual(len(scaffolds), 1)
        self.assertEqual(scaffolds[0].tier, 2)


class TestFileOutput(unittest.TestCase):
    """Tests for writing scaffolds to files."""

    def test_write_scaffold_to_file(self):
        """Write scaffold to file system."""
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=1,
            content="// Test content",
            filename="Test_VKG_001.t.sol",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "test"
            result_path = write_scaffold_to_file(scaffold, output_dir)

            self.assertTrue(result_path.exists())
            self.assertEqual(result_path.name, "Test_VKG_001.t.sol")
            self.assertEqual(result_path.read_text(), "// Test content")

    def test_write_scaffold_creates_directory(self):
        """Writing scaffold creates output directory if needed."""
        scaffold = TestScaffold(
            finding_id="VKG-001",
            tier=1,
            content="content",
            filename="Test.t.sol",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "path" / "test"
            result_path = write_scaffold_to_file(scaffold, output_dir)

            self.assertTrue(result_path.exists())
            self.assertTrue(output_dir.exists())


class TestAttackPatterns(unittest.TestCase):
    """Tests for attack pattern generation."""

    def test_reentrancy_pattern(self):
        """Reentrancy findings get reentrancy attack pattern."""
        finding = Finding(
            id="VKG-001",
            title="Reentrancy vulnerability",
            severity=Severity.CRITICAL,
            description="",
            location="",
            recommendation="",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIn("Attack Pattern: Reentrancy", scaffold.content)
        self.assertIn("callback", scaffold.content.lower())

    def test_access_control_pattern(self):
        """Access control findings get appropriate pattern."""
        finding = Finding(
            id="VKG-001",
            title="Unauthorized access",
            severity=Severity.HIGH,
            description="Missing permission check",
            location="",
            recommendation="",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIn("Attack Pattern: Missing Access Control", scaffold.content)

    def test_oracle_pattern(self):
        """Oracle findings get oracle attack pattern."""
        finding = Finding(
            id="VKG-001",
            title="Oracle manipulation",
            severity=Severity.HIGH,
            description="Price oracle can be manipulated",
            location="",
            recommendation="",
        )

        scaffold = generate_tier1_scaffold(finding)
        self.assertIn("Oracle", scaffold.content)


if __name__ == "__main__":
    unittest.main()
