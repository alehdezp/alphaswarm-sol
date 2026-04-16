"""Tests for alphaswarm bead CLI commands."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from alphaswarm_sol.cli.init import app

runner = CliRunner()


class TestBeadCLI:
    """Tests for bead CLI commands."""

    def test_bead_create_returns_id(self, tmp_path: Path, monkeypatch):
        """bead create returns bead ID."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["bead", "create", "Test bead"])
        assert result.exit_code == 0
        assert "bd-" in result.stdout

    def test_bead_create_json_output(self, tmp_path: Path, monkeypatch):
        """bead create --json returns valid JSON."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["bead", "create", "Test bead", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "id" in data
        assert data["title"] == "Test bead"

    def test_bead_list_empty(self, tmp_path: Path, monkeypatch):
        """bead list with no beads shows message."""
        monkeypatch.chdir(tmp_path)
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        (beads_dir / "index.jsonl").touch()

        result = runner.invoke(app, ["bead", "list"])
        assert result.exit_code == 0
        assert "No beads found" in result.stdout

    def test_bead_list_json(self, tmp_path: Path, monkeypatch):
        """bead list --json returns valid JSON array."""
        monkeypatch.chdir(tmp_path)
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        (beads_dir / "index.jsonl").touch()

        result = runner.invoke(app, ["bead", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_bead_create_then_list(self, tmp_path: Path, monkeypatch):
        """Created bead appears in list."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["bead", "create", "Test bead"])
        result = runner.invoke(app, ["bead", "list"])
        assert result.exit_code == 0
        assert "Test bead" in result.stdout

    def test_bead_update_status(self, tmp_path: Path, monkeypatch):
        """bead update changes status."""
        monkeypatch.chdir(tmp_path)
        create_result = runner.invoke(app, ["bead", "create", "Test bead", "--json"])
        bead_id = json.loads(create_result.stdout)["id"]

        result = runner.invoke(app, ["bead", "update", bead_id, "--status", "in_progress"])
        assert result.exit_code == 0
        assert "Updated" in result.stdout

    def test_bead_show(self, tmp_path: Path, monkeypatch):
        """bead show displays bead details."""
        monkeypatch.chdir(tmp_path)
        create_result = runner.invoke(app, ["bead", "create", "Test bead", "--json"])
        bead_id = json.loads(create_result.stdout)["id"]

        result = runner.invoke(app, ["bead", "show", bead_id])
        assert result.exit_code == 0
        assert "Test bead" in result.stdout
        assert bead_id in result.stdout

    def test_bead_show_not_found(self, tmp_path: Path, monkeypatch):
        """bead show with invalid ID returns error."""
        monkeypatch.chdir(tmp_path)
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        (beads_dir / "index.jsonl").touch()

        result = runner.invoke(app, ["bead", "show", "bd-notreal"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
