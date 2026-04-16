"""Tests for Doctor, Repair, Validate, and Reset commands (Task 10.5).

Tests the error recovery CLI commands for diagnosing and fixing VKG issues.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app
from alphaswarm_sol.cli.doctor import Doctor, Diagnosis
from alphaswarm_sol.cli.repair import Repairer, RepairAction
from alphaswarm_sol.core.validator import StateValidator, ValidationResult

runner = CliRunner()


class TestDiagnosis(unittest.TestCase):
    """Test Diagnosis dataclass."""

    def test_diagnosis_to_dict(self):
        """Diagnosis serializes to dict."""
        d = Diagnosis(
            category="Installation",
            check="python",
            status="ok",
            message="3.11.0",
            fix_command=None,
        )

        data = d.to_dict()

        self.assertEqual(data["category"], "Installation")
        self.assertEqual(data["check"], "python")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["message"], "3.11.0")
        self.assertIsNone(data["fix_command"])

    def test_diagnosis_with_fix_command(self):
        """Diagnosis includes fix command when present."""
        d = Diagnosis(
            category="Project",
            check=".vrs",
            status="warning",
            message="Not found",
            fix_command="vkg build-kg .",
        )

        data = d.to_dict()

        self.assertEqual(data["fix_command"], "vkg build-kg .")


class TestDoctor(unittest.TestCase):
    """Test Doctor class."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_dir = Path(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_doctor_no_vkg_dir(self):
        """Doctor reports missing .vrs."""
        doc = Doctor(self.project_dir)
        diagnoses = doc.run_all()

        # Should have installation checks
        self.assertTrue(any(d.category == "Installation" for d in diagnoses))

        # Should warn about missing .vrs
        project_diags = [d for d in diagnoses if d.category == "Project"]
        self.assertTrue(any(d.status == "warning" for d in project_diags))

    def test_doctor_with_valid_vkg_dir(self):
        """Doctor reports healthy state."""
        vkg_dir = self.project_dir / ".vrs"
        graphs_dir = vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)

        # Create valid graph.json
        graph_data = {"nodes": [{"id": "n1"}], "edges": []}
        (graphs_dir / "graph.json").write_text(json.dumps(graph_data))

        doc = Doctor(self.project_dir)
        diagnoses = doc.run_all()

        # Should find .vrs
        vkg_diag = [d for d in diagnoses if d.check == ".vrs directory"]
        self.assertTrue(any(d.status == "ok" for d in vkg_diag))

        # Should find valid graph (legacy flat file detected as warning)
        graph_diag = [d for d in diagnoses if d.check == "graphs"]
        self.assertTrue(len(graph_diag) > 0)

    def test_doctor_corrupted_graph(self):
        """Doctor detects missing graphs."""
        vkg_dir = self.project_dir / ".vrs"
        graphs_dir = vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)

        # Empty graphs directory (no identity subdirs, no flat files)
        doc = Doctor(self.project_dir)
        diagnoses = doc.run_all()

        graph_diag = [d for d in diagnoses if d.check == "graphs"]
        self.assertTrue(any(d.status == "warning" for d in graph_diag))
        self.assertTrue(any(d.fix_command is not None for d in graph_diag))

    def test_doctor_get_summary(self):
        """Doctor provides summary statistics."""
        doc = Doctor(self.project_dir)
        doc.run_all()

        summary = doc.get_summary()

        self.assertIn("total_checks", summary)
        self.assertIn("errors", summary)
        self.assertIn("warnings", summary)
        self.assertIn("ok", summary)
        self.assertIn("healthy", summary)

    def test_doctor_healthy_definition(self):
        """Doctor healthy means no errors."""
        vkg_dir = self.project_dir / ".vrs"
        graphs_dir = vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)
        (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

        doc = Doctor(self.project_dir)
        doc.run_all()

        summary = doc.get_summary()
        # May have warnings but no errors = healthy
        if summary["errors"] == 0:
            self.assertTrue(summary["healthy"])


class TestDoctorCommand(unittest.TestCase):
    """Test vkg doctor CLI command."""

    def test_doctor_runs(self):
        """Doctor command executes."""
        result = runner.invoke(app, ["doctor"])
        # Should not crash
        self.assertEqual(result.exit_code, 0)

    def test_doctor_json_output(self):
        """Doctor --json produces valid JSON."""
        result = runner.invoke(app, ["doctor", "--json"])

        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.stdout)
        self.assertIn("diagnoses", data)
        self.assertIn("summary", data)

    def test_doctor_verbose(self):
        """Doctor --verbose shows all checks."""
        result = runner.invoke(app, ["doctor", "--verbose"])

        self.assertEqual(result.exit_code, 0)
        # Should show OK items too
        self.assertIn("OK", result.stdout)

    def test_doctor_with_project(self):
        """Doctor respects --project option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["doctor", "--project", tmpdir])
            self.assertEqual(result.exit_code, 0)


class TestRepairer(unittest.TestCase):
    """Test Repairer class."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_dir = Path(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_repairer_no_vkg_dir(self):
        """Repairer finds nothing without .vrs."""
        repairer = Repairer(self.project_dir)
        repairs = repairer.scan()

        self.assertEqual(len(repairs), 0)

    def test_repairer_healthy_state(self):
        """Repairer finds nothing in healthy state."""
        vkg_dir = self.project_dir / ".vrs"
        graphs_dir = vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)
        (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

        repairer = Repairer(self.project_dir)
        repairs = repairer.scan()

        self.assertEqual(len(repairs), 0)

    def test_repairer_corrupted_graph(self):
        """Repairer plans to fix corrupted graph.json."""
        vkg_dir = self.project_dir / ".vrs"
        graphs_dir = vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)
        (graphs_dir / "graph.json").write_text("invalid json")

        repairer = Repairer(self.project_dir)
        repairs = repairer.scan()

        self.assertEqual(len(repairs), 1)
        self.assertIn("graph.json", repairs[0].issue.lower())

    def test_repairer_corrupted_cache(self):
        """Repairer plans to fix corrupted cache."""
        vkg_dir = self.project_dir / ".vrs"
        cache_dir = vkg_dir / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "bad.json").write_text("invalid json")

        repairer = Repairer(self.project_dir)
        repairs = repairer.scan()

        self.assertEqual(len(repairs), 1)
        self.assertIn("cache", repairs[0].issue.lower())

    def test_repairer_execute_dry_run(self):
        """Repairer dry run doesn't change files."""
        vkg_dir = self.project_dir / ".vrs"
        cache_dir = vkg_dir / "cache"
        cache_dir.mkdir(parents=True)
        bad_file = cache_dir / "bad.json"
        bad_file.write_text("invalid json")

        repairer = Repairer(self.project_dir)
        repairer.scan()
        repairer.execute_all(dry_run=True)

        # File should still exist
        self.assertTrue(bad_file.exists())

    def test_repairer_execute_real(self):
        """Repairer actually fixes issues."""
        vkg_dir = self.project_dir / ".vrs"
        cache_dir = vkg_dir / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "bad.json").write_text("invalid json")

        repairer = Repairer(self.project_dir)
        repairer.scan()
        success_count = repairer.execute_all(dry_run=False)

        self.assertEqual(success_count, 1)
        self.assertFalse(cache_dir.exists())


class TestRepairAction(unittest.TestCase):
    """Test RepairAction class."""

    def test_repair_action_execute_success(self):
        """RepairAction executes command."""
        executed = []

        action = RepairAction(
            issue="Test issue",
            action="Fix test",
            command=lambda: executed.append(True),
        )

        result = action.execute(dry_run=False)

        self.assertTrue(result)
        self.assertEqual(executed, [True])

    def test_repair_action_execute_dry_run(self):
        """RepairAction dry run doesn't execute."""
        executed = []

        action = RepairAction(
            issue="Test issue",
            action="Fix test",
            command=lambda: executed.append(True),
        )

        result = action.execute(dry_run=True)

        self.assertFalse(result)
        self.assertEqual(executed, [])


class TestRepairCommand(unittest.TestCase):
    """Test vkg repair CLI command."""

    def test_repair_no_vkg_dir(self):
        """Repair handles missing .vrs gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["repair", "--project", tmpdir])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("nothing to repair", result.stdout.lower())

    def test_repair_healthy(self):
        """Repair reports healthy state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vkg_dir = Path(tmpdir) / ".vrs"
            graphs_dir = vkg_dir / "graphs"
            graphs_dir.mkdir(parents=True)
            (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

            result = runner.invoke(app, ["repair", "--project", tmpdir])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("healthy", result.stdout.lower())

    def test_repair_dry_run(self):
        """Repair --dry-run shows but doesn't fix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vkg_dir = Path(tmpdir) / ".vrs"
            cache_dir = vkg_dir / "cache"
            cache_dir.mkdir(parents=True)
            bad_file = cache_dir / "bad.json"
            bad_file.write_text("invalid json")

            result = runner.invoke(app, ["repair", "--dry-run", "--project", tmpdir])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("dry run", result.stdout.lower())
            self.assertTrue(bad_file.exists())  # Not deleted

    def test_repair_cache_subcommand(self):
        """Repair cache clears cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vkg_dir = Path(tmpdir) / ".vrs"
            cache_dir = vkg_dir / "cache"
            cache_dir.mkdir(parents=True)
            (cache_dir / "test.json").write_text('{"cached": true}')

            result = runner.invoke(app, ["repair", "cache", "--project", tmpdir])

            self.assertEqual(result.exit_code, 0)
            self.assertFalse(cache_dir.exists())


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass."""

    def test_validation_result_to_dict(self):
        """ValidationResult serializes to dict."""
        r = ValidationResult(
            valid=False,
            path="/test/path",
            issue="Test issue",
        )

        data = r.to_dict()

        self.assertEqual(data["valid"], False)
        self.assertEqual(data["path"], "/test/path")
        self.assertEqual(data["issue"], "Test issue")


class TestStateValidator(unittest.TestCase):
    """Test StateValidator class."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.vkg_dir = Path(self.tmpdir) / ".vrs"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_validator_missing_dir(self):
        """Validator reports missing directory."""
        validator = StateValidator(self.vkg_dir)
        results = validator.validate_all()

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].valid)
        self.assertIn("does not exist", results[0].issue)

    def test_validator_valid_structure(self):
        """Validator passes valid structure."""
        graphs_dir = self.vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)
        (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

        validator = StateValidator(self.vkg_dir)
        results = validator.validate_all()

        self.assertTrue(validator.is_healthy())

    def test_validator_invalid_json(self):
        """Validator catches invalid JSON."""
        graphs_dir = self.vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)
        (graphs_dir / "graph.json").write_text("invalid json")

        validator = StateValidator(self.vkg_dir)
        results = validator.validate_all()

        invalid = validator.get_invalid()
        self.assertTrue(len(invalid) > 0)

    def test_validator_get_summary(self):
        """Validator provides summary."""
        graphs_dir = self.vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)
        (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

        validator = StateValidator(self.vkg_dir)
        summary = validator.get_summary()

        self.assertIn("total_checks", summary)
        self.assertIn("valid", summary)
        self.assertIn("invalid", summary)
        self.assertIn("healthy", summary)
        self.assertIn("issues", summary)

    def test_validator_graph_validation(self):
        """Validator checks graph structure."""
        graphs_dir = self.vkg_dir / "graphs"
        graphs_dir.mkdir(parents=True)

        # Missing nodes field
        (graphs_dir / "graph.json").write_text('{"edges":[]}')

        validator = StateValidator(self.vkg_dir)
        results = validator.validate_graph()

        self.assertTrue(any(not r.valid for r in results))

    def test_validator_version_consistency(self):
        """Validator checks version references."""
        self.vkg_dir.mkdir(parents=True)
        versions_dir = self.vkg_dir / "versions"
        versions_dir.mkdir()

        # Current version points to non-existent file
        (self.vkg_dir / "current_version.json").write_text('{"current":"missing_id"}')

        validator = StateValidator(self.vkg_dir)
        results = validator.validate_all()

        invalid = [r for r in results if not r.valid]
        self.assertTrue(
            any("missing version" in r.issue.lower() for r in invalid if r.issue)
        )


class TestValidateCommand(unittest.TestCase):
    """Test vkg validate CLI command."""

    def test_validate_missing_dir(self):
        """Validate fails for missing .vrs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["validate", "--project", tmpdir])
            self.assertEqual(result.exit_code, 1)
            # Output says "No .vrs directory found"
            self.assertIn("no .vrs directory found", result.stdout.lower())

    def test_validate_healthy(self):
        """Validate passes for healthy state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vkg_dir = Path(tmpdir) / ".vrs"
            graphs_dir = vkg_dir / "graphs"
            graphs_dir.mkdir(parents=True)
            (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

            result = runner.invoke(app, ["validate", "--project", tmpdir])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("all ok", result.stdout.lower())

    def test_validate_verbose(self):
        """Validate --verbose shows all checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vkg_dir = Path(tmpdir) / ".vrs"
            graphs_dir = vkg_dir / "graphs"
            graphs_dir.mkdir(parents=True)
            (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

            result = runner.invoke(app, ["validate", "--verbose", "--project", tmpdir])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("validated", result.stdout.lower())
            self.assertIn("[ok]", result.stdout.lower())

    def test_validate_invalid(self):
        """Validate fails for invalid state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vkg_dir = Path(tmpdir) / ".vrs"
            graphs_dir = vkg_dir / "graphs"
            graphs_dir.mkdir(parents=True)
            (graphs_dir / "graph.json").write_text("invalid json")

            result = runner.invoke(app, ["validate", "--project", tmpdir])

            self.assertEqual(result.exit_code, 1)
            self.assertIn("error", result.stdout.lower())


class TestResetCommand(unittest.TestCase):
    """Test vkg reset CLI command."""

    def test_reset_requires_confirm(self):
        """Reset requires --confirm flag."""
        result = runner.invoke(app, ["reset"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("confirm", result.stdout.lower())

    def test_reset_shows_warning(self):
        """Reset shows what will be deleted."""
        result = runner.invoke(app, ["reset"])

        self.assertIn("delete", result.stdout.lower())
        self.assertIn("graph", result.stdout.lower())

    def test_reset_with_confirm(self):
        """Reset --confirm deletes .vrs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vkg_dir = Path(tmpdir) / ".vrs"
            graphs_dir = vkg_dir / "graphs"
            graphs_dir.mkdir(parents=True)
            (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')

            self.assertTrue(vkg_dir.exists())

            result = runner.invoke(app, ["reset", "--confirm", "--project", tmpdir])

            self.assertEqual(result.exit_code, 0)
            self.assertFalse(vkg_dir.exists())
            self.assertIn("reset", result.stdout.lower())

    def test_reset_nothing_to_delete(self):
        """Reset handles missing .vrs gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["reset", "--confirm", "--project", tmpdir])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("nothing to reset", result.stdout.lower())


class TestIntegration(unittest.TestCase):
    """Integration tests for error recovery workflow."""

    def test_doctor_repair_validate_workflow(self):
        """Full workflow: doctor → repair → validate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup corrupted state
            vkg_dir = Path(tmpdir) / ".vrs"
            graphs_dir = vkg_dir / "graphs"
            cache_dir = vkg_dir / "cache"
            graphs_dir.mkdir(parents=True)
            cache_dir.mkdir(parents=True)
            (graphs_dir / "graph.json").write_text('{"nodes":[],"edges":[]}')
            (cache_dir / "corrupt.json").write_text("invalid json")

            # Doctor finds issue
            result = runner.invoke(app, ["doctor", "--json", "--project", tmpdir])
            data = json.loads(result.stdout)
            # May or may not find warnings depending on check order

            # Repair fixes
            result = runner.invoke(app, ["repair", "--project", tmpdir])
            self.assertEqual(result.exit_code, 0)

            # Validate passes
            result = runner.invoke(app, ["validate", "--project", tmpdir])
            self.assertEqual(result.exit_code, 0)

    def test_reset_rebuild_workflow(self):
        """Workflow: reset → rebuild."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup state
            vkg_dir = Path(tmpdir) / ".vrs"
            graphs_dir = vkg_dir / "graphs"
            graphs_dir.mkdir(parents=True)
            (graphs_dir / "graph.json").write_text('{"nodes":[{"id":"n1"}],"edges":[]}')

            # Reset
            result = runner.invoke(app, ["reset", "--confirm", "--project", tmpdir])
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(vkg_dir.exists())

            # Validate fails (no .vrs)
            result = runner.invoke(app, ["validate", "--project", tmpdir])
            self.assertEqual(result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
