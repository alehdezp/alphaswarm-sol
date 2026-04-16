"""
Tests for Findings CLI Commands

Tests the findings CLI interface using Typer's CliRunner.
"""

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from alphaswarm_sol.cli import app
from alphaswarm_sol.findings.model import (
    Evidence,
    Finding,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    Location,
)
from alphaswarm_sol.findings.store import FindingsStore

runner = CliRunner()


class TestFindingsListCommand(unittest.TestCase):
    """Tests for 'vkg findings list' command."""

    def setUp(self):
        """Create temp directory and store with test findings."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_test_finding(
        self,
        pattern="test-pattern",
        severity=FindingSeverity.HIGH,
        status=FindingStatus.PENDING,
        line=42,
    ):
        """Helper to add a test finding."""
        finding = Finding(
            pattern=pattern,
            severity=severity,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=line, function="testFunc"),
            description=f"Test finding for {pattern}",
            status=status,
        )
        self.store.add(finding)
        self.store.save()
        return finding

    def test_list_empty(self):
        """Test listing when no findings exist."""
        result = runner.invoke(app, ["findings", "list", "--vkg-dir", str(self.vkg_dir)])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No findings found", result.stdout)

    def test_list_with_findings(self):
        """Test listing with findings."""
        f1 = self._add_test_finding(pattern="auth-001", line=10)
        f2 = self._add_test_finding(pattern="reentrancy-001", line=20)

        result = runner.invoke(app, ["findings", "list", "--vkg-dir", str(self.vkg_dir)])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("auth-001", result.stdout)
        self.assertIn("reentrancy-001", result.stdout)
        self.assertIn("Total: 2", result.stdout)

    def test_list_filter_severity(self):
        """Test filtering by severity."""
        self._add_test_finding(pattern="critical-001", severity=FindingSeverity.CRITICAL, line=10)
        self._add_test_finding(pattern="low-001", severity=FindingSeverity.LOW, line=20)

        result = runner.invoke(
            app,
            ["findings", "list", "--severity", "critical", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("critical-001", result.stdout)
        self.assertNotIn("low-001", result.stdout)

    def test_list_filter_status(self):
        """Test filtering by status."""
        self._add_test_finding(pattern="pending-001", status=FindingStatus.PENDING, line=10)
        confirmed = self._add_test_finding(
            pattern="confirmed-001", status=FindingStatus.PENDING, line=20
        )
        # Update status
        self.store.update(confirmed.id, status=FindingStatus.CONFIRMED)
        self.store.save()

        result = runner.invoke(
            app,
            ["findings", "list", "--status", "confirmed", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("confirmed-001", result.stdout)
        self.assertNotIn("pending-001", result.stdout)

    def test_list_filter_pattern(self):
        """Test filtering by pattern."""
        self._add_test_finding(pattern="auth-001", line=10)
        self._add_test_finding(pattern="auth-001", line=20)
        self._add_test_finding(pattern="reentrancy-001", line=30)

        result = runner.invoke(
            app,
            ["findings", "list", "--pattern", "auth-001", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("auth-001", result.stdout)
        self.assertNotIn("reentrancy-001", result.stdout)

    def test_list_json_format(self):
        """Test JSON output format."""
        self._add_test_finding(pattern="test-001")

        result = runner.invoke(
            app,
            ["findings", "list", "--format", "json", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)

        data = json.loads(result.stdout)
        self.assertIn("findings", data)
        self.assertIn("summary", data)
        self.assertEqual(len(data["findings"]), 1)

    def test_list_csv_format(self):
        """Test CSV output format."""
        self._add_test_finding(pattern="test-001")

        result = runner.invoke(
            app,
            ["findings", "list", "--format", "csv", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("id,severity,confidence,pattern", result.stdout)
        self.assertIn("test-001", result.stdout)

    def test_list_limit(self):
        """Test limiting results."""
        for i in range(10):
            self._add_test_finding(pattern=f"test-{i:03d}", line=i + 1)

        result = runner.invoke(
            app,
            ["findings", "list", "--limit", "3", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        # Should only show 3 findings (priority sorted)


class TestFindingsShowCommand(unittest.TestCase):
    """Tests for 'vkg findings show' command."""

    def setUp(self):
        """Create temp directory and store."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_show_existing(self):
        """Test showing an existing finding."""
        finding = Finding(
            pattern="auth-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(
                file="Vault.sol", line=42, function="withdraw", contract="Vault"
            ),
            description="Missing access control on privileged function",
            evidence=Evidence(
                behavioral_signature="W:owner",
                properties_matched=["writes_privileged_state"],
                code_snippet="function withdraw() public { owner = msg.sender; }",
            ),
            verification_steps=["Check ownership", "Verify exploit"],
            recommended_fix="Add onlyOwner modifier",
            cwe="CWE-284",
        )
        self.store.add(finding)
        self.store.save()

        result = runner.invoke(
            app, ["findings", "show", finding.id, "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn(finding.id, result.stdout)
        self.assertIn("auth-001", result.stdout)
        self.assertIn("Vault.sol:42", result.stdout)
        self.assertIn("W:owner", result.stdout)
        self.assertIn("CWE-284", result.stdout)

    def test_show_not_found(self):
        """Test showing non-existent finding."""
        result = runner.invoke(
            app, ["findings", "show", "VKG-NONEXISTENT", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not found", result.stdout)


class TestFindingsNextCommand(unittest.TestCase):
    """Tests for 'vkg findings next' command."""

    def setUp(self):
        """Create temp directory and store."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_finding(self, pattern, severity, line):
        """Add a test finding."""
        finding = Finding(
            pattern=pattern,
            severity=severity,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=line),
            description=f"Test {pattern}",
        )
        self.store.add(finding)
        self.store.save()
        return finding

    def test_next_empty(self):
        """Test next with no findings."""
        result = runner.invoke(
            app, ["findings", "next", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No findings matching criteria", result.stdout)

    def test_next_priority(self):
        """Test next returns highest priority finding."""
        low = self._add_finding("low-001", FindingSeverity.LOW, 10)
        critical = self._add_finding("critical-001", FindingSeverity.CRITICAL, 20)
        medium = self._add_finding("medium-001", FindingSeverity.MEDIUM, 30)

        result = runner.invoke(
            app, ["findings", "next", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("critical-001", result.stdout)

    def test_next_skips_confirmed(self):
        """Test next skips confirmed findings."""
        critical = self._add_finding("critical-001", FindingSeverity.CRITICAL, 10)
        low = self._add_finding("low-001", FindingSeverity.LOW, 20)

        # Mark critical as confirmed
        self.store.update(critical.id, status=FindingStatus.CONFIRMED)
        self.store.save()

        result = runner.invoke(
            app, ["findings", "next", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("low-001", result.stdout)


class TestFindingsUpdateCommand(unittest.TestCase):
    """Tests for 'vkg findings update' command."""

    def setUp(self):
        """Create temp directory and store."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_finding(self):
        """Add a test finding."""
        finding = Finding(
            pattern="test-001",
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=42),
            description="Test finding",
        )
        self.store.add(finding)
        self.store.save()
        return finding

    def test_update_status(self):
        """Test updating finding status."""
        finding = self._add_finding()

        result = runner.invoke(
            app,
            [
                "findings",
                "update",
                finding.id,
                "--status",
                "confirmed",
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("pending -> confirmed", result.stdout)

        # Verify persisted
        store2 = FindingsStore(self.vkg_dir)
        updated = store2.get(finding.id)
        self.assertEqual(updated.status, FindingStatus.CONFIRMED)

    def test_update_requires_reason_for_false_positive(self):
        """Test that false_positive requires a reason."""
        finding = self._add_finding()

        result = runner.invoke(
            app,
            [
                "findings",
                "update",
                finding.id,
                "--status",
                "false_positive",
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("--reason is required", result.stdout)

    def test_update_false_positive_with_reason(self):
        """Test marking as false_positive with reason."""
        finding = self._add_finding()

        result = runner.invoke(
            app,
            [
                "findings",
                "update",
                finding.id,
                "--status",
                "false_positive",
                "--reason",
                "Protected by onlyOwner",
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("false_positive", result.stdout)

    def test_update_add_note(self):
        """Test adding investigation note."""
        finding = self._add_finding()

        result = runner.invoke(
            app,
            [
                "findings",
                "update",
                finding.id,
                "--note",
                "Investigated thoroughly - confirmed issue",
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Added note", result.stdout)

    def test_update_not_found(self):
        """Test updating non-existent finding."""
        result = runner.invoke(
            app,
            [
                "findings",
                "update",
                "VKG-NONEXISTENT",
                "--status",
                "confirmed",
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not found", result.stdout)

    def test_update_requires_status_or_note(self):
        """Test that update requires --status or --note."""
        finding = self._add_finding()

        result = runner.invoke(
            app,
            [
                "findings",
                "update",
                finding.id,
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Provide --status or --note", result.stdout)


class TestFindingsEscalateCommand(unittest.TestCase):
    """Tests for 'vkg findings escalate' command."""

    def setUp(self):
        """Create temp directory and store."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_finding(self):
        """Add a test finding."""
        finding = Finding(
            pattern="test-001",
            severity=FindingSeverity.MEDIUM,
            confidence=FindingConfidence.MEDIUM,
            location=Location(file="Test.sol", line=42),
            description="Test finding",
        )
        self.store.add(finding)
        self.store.save()
        return finding

    def test_escalate(self):
        """Test escalating a finding."""
        finding = self._add_finding()

        result = runner.invoke(
            app,
            [
                "findings",
                "escalate",
                finding.id,
                "--reason",
                "Uncertain about context - needs human review",
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Escalated", result.stdout)
        self.assertIn("escalated", result.stdout)

        # Verify persisted
        store2 = FindingsStore(self.vkg_dir)
        updated = store2.get(finding.id)
        self.assertEqual(updated.status, FindingStatus.ESCALATED)


class TestFindingsRefreshCommand(unittest.TestCase):
    """Tests for 'vkg findings refresh' command."""

    def setUp(self):
        """Create temp directory and store."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_finding(self, pattern="test-001", line=42):
        """Add a test finding."""
        finding = Finding(
            pattern=pattern,
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=line),
            description="Test finding",
        )
        self.store.add(finding)
        self.store.save()
        return finding

    def test_refresh_empty(self):
        """Test refresh with no findings."""
        result = runner.invoke(
            app, ["findings", "refresh", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No findings to check", result.stdout)

    def test_refresh_with_findings(self):
        """Test refresh with findings."""
        self._add_finding("test-001", 10)
        self._add_finding("test-002", 20)

        result = runner.invoke(
            app, ["findings", "refresh", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Checking 2 findings", result.stdout)

    def test_refresh_clear(self):
        """Test clearing all findings."""
        self._add_finding("test-001", 10)
        self._add_finding("test-002", 20)

        result = runner.invoke(
            app, ["findings", "refresh", "--clear", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cleared 2 findings", result.stdout)

        # Verify cleared
        store2 = FindingsStore(self.vkg_dir)
        self.assertEqual(len(store2), 0)


class TestFindingsStatusCommand(unittest.TestCase):
    """Tests for 'vkg findings status' command (session handoff)."""

    def setUp(self):
        """Create temp directory and store."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_finding(
        self,
        pattern="test-001",
        severity=FindingSeverity.HIGH,
        status=FindingStatus.PENDING,
        line=42,
    ):
        """Add a test finding."""
        finding = Finding(
            pattern=pattern,
            severity=severity,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=line),
            description=f"Test finding for {pattern}",
            status=status,
        )
        self.store.add(finding)
        self.store.save()
        return finding

    def test_status_empty(self):
        """Test status with no findings."""
        result = runner.invoke(
            app, ["findings", "status", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Not Started", result.stdout)
        self.assertIn("vkg build", result.stdout)

    def test_status_with_pending(self):
        """Test status with pending findings."""
        self._add_finding("critical-001", FindingSeverity.CRITICAL)
        self._add_finding("high-001", FindingSeverity.HIGH, line=50)

        result = runner.invoke(
            app, ["findings", "status", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Ready for Investigation", result.stdout)
        self.assertIn("Total: 2", result.stdout)
        self.assertIn("Pending: 2", result.stdout)
        self.assertIn("vkg findings next", result.stdout)

    def test_status_with_confirmed(self):
        """Test status with some confirmed findings."""
        f1 = self._add_finding("auth-001", FindingSeverity.HIGH, line=10)
        f2 = self._add_finding("auth-002", FindingSeverity.MEDIUM, line=20)

        # Confirm one finding
        self.store.update(f1.id, status=FindingStatus.CONFIRMED)
        self.store.save()

        result = runner.invoke(
            app, ["findings", "status", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Confirmed: 1", result.stdout)
        self.assertIn("Pending: 1", result.stdout)

    def test_status_complete(self):
        """Test status when all findings are investigated."""
        f1 = self._add_finding("auth-001", FindingSeverity.HIGH, line=10)
        f2 = self._add_finding("auth-002", FindingSeverity.MEDIUM, line=20)

        # Confirm/reject all findings
        self.store.update(f1.id, status=FindingStatus.CONFIRMED)
        self.store.update(f2.id, status=FindingStatus.FALSE_POSITIVE)
        self.store.save()

        result = runner.invoke(
            app, ["findings", "status", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Complete", result.stdout)
        self.assertIn("vkg findings export", result.stdout)

    def test_status_json_format(self):
        """Test status with JSON output."""
        self._add_finding("critical-001", FindingSeverity.CRITICAL)
        self._add_finding("high-001", FindingSeverity.HIGH, line=50)

        result = runner.invoke(
            app, ["findings", "status", "--format", "json", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)

        data = json.loads(result.stdout)
        self.assertIn("session_state", data)
        self.assertIn("next_action", data)
        self.assertIn("recommended_commands", data)
        self.assertEqual(data["session_state"]["total_findings"], 2)
        self.assertEqual(data["session_state"]["pending"], 2)

    def test_status_json_includes_next_finding(self):
        """Test JSON status includes next finding details."""
        f = self._add_finding("critical-001", FindingSeverity.CRITICAL)

        result = runner.invoke(
            app, ["findings", "status", "--format", "json", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)

        data = json.loads(result.stdout)
        self.assertIsNotNone(data["next_finding"])
        self.assertEqual(data["next_finding"]["pattern"], "critical-001")

    def test_status_with_escalated(self):
        """Test status prioritizes escalated findings."""
        f1 = self._add_finding("medium-001", FindingSeverity.MEDIUM, line=10)
        f2 = self._add_finding("low-001", FindingSeverity.LOW, line=20)

        # Escalate the medium finding
        self.store.update(f1.id, status=FindingStatus.ESCALATED)
        self.store.save()

        result = runner.invoke(
            app, ["findings", "status", "--vkg-dir", str(self.vkg_dir)]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Needs Human Review", result.stdout)
        self.assertIn("Escalated: 1", result.stdout)


class TestFindingsExportCommand(unittest.TestCase):
    """Tests for 'vkg findings export' command."""

    def setUp(self):
        """Create temp directory and store."""
        self.temp_dir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.temp_dir) / ".vkg"
        self.store = FindingsStore(self.vkg_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_finding(self, pattern="test-001"):
        """Add a test finding."""
        finding = Finding(
            pattern=pattern,
            severity=FindingSeverity.HIGH,
            confidence=FindingConfidence.HIGH,
            location=Location(file="Test.sol", line=42, function="test"),
            description=f"Test finding for {pattern}",
            evidence=Evidence(behavioral_signature="W:state"),
            cwe="CWE-284",
        )
        self.store.add(finding)
        self.store.save()
        return finding

    def test_export_json(self):
        """Test JSON export."""
        self._add_finding()

        result = runner.invoke(
            app,
            ["findings", "export", "--format", "json", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)

        data = json.loads(result.stdout)
        self.assertIn("findings", data)

    def test_export_sarif(self):
        """Test SARIF export."""
        self._add_finding()

        result = runner.invoke(
            app,
            ["findings", "export", "--format", "sarif", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)

        sarif = json.loads(result.stdout)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertIn("runs", sarif)
        self.assertEqual(len(sarif["runs"]), 1)
        self.assertIn("results", sarif["runs"][0])

    def test_export_csv(self):
        """Test CSV export."""
        self._add_finding()

        result = runner.invoke(
            app,
            ["findings", "export", "--format", "csv", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("id,severity,confidence,pattern", result.stdout)
        self.assertIn("test-001", result.stdout)

    def test_export_markdown(self):
        """Test Markdown export."""
        self._add_finding()

        result = runner.invoke(
            app,
            ["findings", "export", "--format", "markdown", "--vkg-dir", str(self.vkg_dir)],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("# Security Findings Report", result.stdout)
        self.assertIn("## Summary by Severity", result.stdout)
        self.assertIn("test-001", result.stdout)

    def test_export_to_file(self):
        """Test exporting to file."""
        self._add_finding()
        output_path = Path(self.temp_dir) / "findings.json"

        result = runner.invoke(
            app,
            [
                "findings",
                "export",
                "--format",
                "json",
                "--output",
                str(output_path),
                "--vkg-dir",
                str(self.vkg_dir),
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
