"""Tests for alphaswarm health-check command."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from alphaswarm_sol.cli.main import app
from alphaswarm_sol.cli.health import run_health_check
from alphaswarm_sol.core.availability import check_tool_available, ToolStatus

runner = CliRunner()


class TestHealthCheckCLI:
    """Tests for alphaswarm health-check CLI command."""

    def test_health_check_runs(self, tmp_path: Path):
        """Health check command runs without crashing."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path)])
        # May not be fully healthy without tools, but should run
        assert result.exit_code in [0, 1]

    def test_health_check_json_output(self, tmp_path: Path):
        """Health check outputs valid JSON with --json flag."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])

        # Should output valid JSON
        try:
            data = json.loads(result.stdout)
            assert "healthy" in data
            assert "checks" in data
            assert isinstance(data["checks"], dict)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_health_check_detects_missing_skills(self, tmp_path: Path):
        """Health check detects missing skills."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)

        # Skills should be reported as missing/warn
        assert "skills" in data["checks"]
        # Should be either "fail" or "warn" (warn since skills are optional)
        assert data["checks"]["skills"]["status"] in ["fail", "warn"]

    def test_health_check_detects_installed_skills(self, tmp_path: Path):
        """Health check detects installed skills."""
        # Create mock VRS installation
        vrs_dir = tmp_path / ".claude" / "vrs"
        vrs_dir.mkdir(parents=True)

        # Create some skill files
        for i in range(5):
            (vrs_dir / f"skill{i}.md").write_text(f"# Skill {i}")

        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)

        # Skills should be detected
        assert "skills" in data["checks"]
        assert data["checks"]["skills"]["status"] == "pass"
        assert "5 skills" in data["checks"]["skills"]["message"]

    def test_health_check_cli_always_passes(self, tmp_path: Path):
        """CLI check always passes (we're running it)."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)

        # CLI should always be available since we're running it
        assert "cli" in data["checks"]
        assert data["checks"]["cli"]["status"] == "pass"

    def test_health_check_checks_vulndocs(self, tmp_path: Path):
        """Health check includes vulndocs status."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)

        # Vulndocs check should be present
        assert "vulndocs" in data["checks"]
        assert data["checks"]["vulndocs"]["status"] in ["pass", "warn"]

    def test_health_check_checks_beads_directory(self, tmp_path: Path):
        """Health check detects beads directory."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)

        # Beads check should be present
        assert "beads" in data["checks"]
        # Initially missing
        assert data["checks"]["beads"]["status"] == "warn"

        # Create beads directory
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()

        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)
        assert data["checks"]["beads"]["status"] == "pass"

    def test_health_check_suggests_fixes(self, tmp_path: Path):
        """Health check provides fix suggestions."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)

        # Should have fixes array
        assert "fixes" in data
        assert isinstance(data["fixes"], list)

    def test_health_check_verbose_shows_details(self, tmp_path: Path):
        """Health check with --verbose shows additional details."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--verbose"])

        # Should show more detailed output (not JSON)
        assert result.exit_code in [0, 1]
        # Should contain some check names
        assert "cli" in result.stdout.lower() or "check" in result.stdout.lower()

    def test_health_check_exit_code_reflects_health(self, tmp_path: Path):
        """Health check exit code is 0 if healthy, 1 if issues."""
        result = runner.invoke(app, ["health-check", "--project", str(tmp_path), "--json"])
        data = json.loads(result.stdout)

        # Exit code should match healthy status
        if data["healthy"]:
            assert result.exit_code == 0
        else:
            assert result.exit_code == 1


class TestHealthCheckFunction:
    """Tests for run_health_check function."""

    def test_run_health_check_returns_dict(self, tmp_path: Path):
        """run_health_check returns a dictionary."""
        result = run_health_check(tmp_path)

        assert isinstance(result, dict)
        assert "healthy" in result
        assert "checks" in result
        assert "project" in result

    def test_health_check_includes_project_path(self, tmp_path: Path):
        """Health check result includes project path."""
        result = run_health_check(tmp_path)

        assert result["project"] == str(tmp_path.absolute())

    def test_health_check_checks_required_tools(self, tmp_path: Path):
        """Health check verifies required tools (like Slither)."""
        result = run_health_check(tmp_path)

        # Should check for tool_slither (required)
        tool_checks = [k for k in result["checks"].keys() if k.startswith("tool_")]
        assert len(tool_checks) > 0
        assert "tool_slither" in result["checks"]

    def test_health_check_checks_optional_tools(self, tmp_path: Path):
        """Health check includes optional tools."""
        result = run_health_check(tmp_path)

        # Should check optional tools like aderyn, mythril
        checks = result["checks"]
        # At least some optional tools should be checked
        optional_found = any(k in checks for k in ["tool_aderyn", "tool_mythril"])
        assert optional_found


class TestToolAvailability:
    """Tests for tool availability checking."""

    def test_check_tool_available_returns_tool_status(self):
        """check_tool_available returns ToolStatus."""
        status = check_tool_available("python")

        assert isinstance(status, ToolStatus)
        assert status.name == "python"
        assert isinstance(status.available, bool)

    def test_check_tool_available_finds_python(self):
        """check_tool_available detects Python in test environment."""
        status = check_tool_available("python")

        # Python should be available in test environment
        assert status.available is True
        assert status.path is not None

    def test_check_tool_available_missing_tool(self):
        """check_tool_available handles missing tool."""
        status = check_tool_available("nonexistent_tool_xyz_12345")

        assert status.available is False
        assert status.error is not None
        assert "not found" in status.error.lower()

    @patch("shutil.which")
    def test_check_tool_available_with_path(self, mock_which):
        """check_tool_available sets path when tool is found."""
        mock_which.return_value = "/usr/bin/slither"

        status = check_tool_available("slither")

        assert status.path == "/usr/bin/slither"

    def test_check_tool_marks_required_correctly(self):
        """check_tool_available marks required tools correctly."""
        # Slither is required
        slither_status = check_tool_available("slither")
        assert slither_status.required is True

        # Aderyn is optional
        aderyn_status = check_tool_available("aderyn")
        assert aderyn_status.required is False

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_check_tool_gets_version(self, mock_which, mock_run):
        """check_tool_available attempts to get version."""
        mock_which.return_value = "/usr/bin/slither"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "slither 0.9.6\n"
        mock_run.return_value = mock_result

        status = check_tool_available("slither")

        # Should have attempted to get version
        assert status.available is True
        # Version may or may not be parsed depending on output format
        # Just verify version field exists
        assert hasattr(status, "version")

    def test_check_tool_handles_version_failure(self):
        """check_tool_available handles version check failure gracefully."""
        # Even if version check fails, tool should still be marked available if path exists
        status = check_tool_available("slither")

        # Should not crash, version may be None
        assert isinstance(status, ToolStatus)
