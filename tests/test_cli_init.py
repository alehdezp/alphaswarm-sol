"""Tests for alphaswarm init command."""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from alphaswarm_sol.cli.init import app
from alphaswarm_sol.skills import get_shipped_skills_path, list_shipped_skills

runner = CliRunner()


class TestInitCommand:
    """Tests for alphaswarm init command."""

    def test_init_creates_vrs_directory(self, tmp_path: Path):
        """Init creates .claude/vrs/ directory."""
        result = runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        assert result.exit_code == 0
        assert (tmp_path / ".claude" / "vrs").exists()

    def test_init_creates_beads_directory(self, tmp_path: Path):
        """Init creates .beads/ directory."""
        result = runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        assert result.exit_code == 0
        assert (tmp_path / ".beads").exists()
        assert (tmp_path / ".beads" / "index.jsonl").exists()

    def test_init_copies_skills(self, tmp_path: Path):
        """Init copies all shipped skills."""
        result = runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        assert result.exit_code == 0

        vrs_dir = tmp_path / ".claude" / "vrs"
        skills = list(vrs_dir.glob("*.md"))
        # Filter out README
        skills = [s for s in skills if s.name != "README.md"]
        assert len(skills) > 0
        # Check for at least one core skill
        skill_names = [s.name for s in skills]
        assert any("audit" in name or "health" in name for name in skill_names)

    def test_init_copies_agents_if_exist(self, tmp_path: Path):
        """Init copies agent definitions if they exist."""
        result = runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        assert result.exit_code == 0

        agents_dir = tmp_path / ".claude" / "vrs" / "agents"
        # Agents directory is optional
        if agents_dir.exists():
            agents = list(agents_dir.glob("*.md"))
            assert len(agents) > 0

    def test_init_refuses_without_force(self, tmp_path: Path):
        """Init refuses to overwrite without --force."""
        # First init
        runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])

        # Second init should fail
        result = runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        assert result.exit_code == 1
        assert "already installed" in result.stdout.lower()

    def test_init_force_reinstalls(self, tmp_path: Path):
        """Init with --force reinstalls."""
        runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        result = runner.invoke(app, ["init", str(tmp_path), "--force", "--skip-health-check"])
        assert result.exit_code == 0
        assert "installed successfully" in result.stdout.lower()

    def test_init_does_not_modify_existing_claude_files(self, tmp_path: Path):
        """Init does not touch existing .claude/ root files."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        existing_file = claude_dir / "settings.yaml"
        existing_file.write_text("existing: content")

        runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])

        assert existing_file.read_text() == "existing: content"

    def test_init_creates_cache_gitignore(self, tmp_path: Path):
        """Init creates .gitignore in cache directory."""
        runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        cache_dir = tmp_path / ".claude" / "vrs" / "cache"
        assert cache_dir.exists()
        gitignore = cache_dir / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "*" in content
        assert "!.gitignore" in content

    def test_init_creates_metadata_file(self, tmp_path: Path):
        """Init creates .vrs-meta.json with version info."""
        result = runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        assert result.exit_code == 0

        meta_file = tmp_path / ".claude" / "vrs" / ".vrs-meta.json"
        assert meta_file.exists()

        meta = json.loads(meta_file.read_text())
        assert "version" in meta
        assert "installed_at" in meta
        assert "skills_count" in meta
        assert meta["skills_count"] > 0

    def test_init_copies_readme(self, tmp_path: Path):
        """Init copies README.md to vrs directory."""
        result = runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])
        assert result.exit_code == 0

        readme = tmp_path / ".claude" / "vrs" / "README.md"
        # README is optional but if shipped, should be copied
        skills_source = get_shipped_skills_path()
        if (skills_source / "README.md").exists():
            assert readme.exists()

    def test_init_nonexistent_path_fails(self):
        """Init with nonexistent path fails gracefully."""
        result = runner.invoke(app, ["init", "/nonexistent/path/xyz", "--skip-health-check"])
        # Should fail because path doesn't exist
        assert result.exit_code != 0


class TestHealthCheckCommand:
    """Tests for alphaswarm health-check command."""

    def test_health_check_detects_missing_installation(self, tmp_path: Path):
        """Health check detects missing VRS installation."""
        result = runner.invoke(app, ["health-check", str(tmp_path)])
        assert result.exit_code == 1
        assert "missing" in result.stdout.lower() or "issues" in result.stdout.lower()

    def test_health_check_passes_after_init(self, tmp_path: Path):
        """Health check passes after successful init."""
        # First init
        runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])

        # Then health check
        result = runner.invoke(app, ["health-check", str(tmp_path)])
        assert result.exit_code == 0
        assert "healthy" in result.stdout.lower()

    def test_health_check_detects_missing_beads_index(self, tmp_path: Path):
        """Health check detects missing beads index."""
        # Create partial installation
        vrs_dir = tmp_path / ".claude" / "vrs"
        vrs_dir.mkdir(parents=True)
        (vrs_dir / "test.md").write_text("# Test")

        result = runner.invoke(app, ["health-check", str(tmp_path)])
        assert result.exit_code == 1
        assert "index.jsonl" in result.stdout.lower() or "beads" in result.stdout.lower()

    def test_health_check_detects_too_few_skills(self, tmp_path: Path):
        """Health check detects insufficient skill files."""
        vrs_dir = tmp_path / ".claude" / "vrs"
        vrs_dir.mkdir(parents=True)
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        (beads_dir / "index.jsonl").touch()

        # Create only 2 skills (less than expected minimum of 5)
        (vrs_dir / "skill1.md").write_text("# Skill 1")
        (vrs_dir / "skill2.md").write_text("# Skill 2")

        # Create metadata
        meta = vrs_dir / ".vrs-meta.json"
        meta.write_text(json.dumps({"version": "0.5.0", "installed_at": "2026-01-01", "skills_count": 2}))

        result = runner.invoke(app, ["health-check", str(tmp_path)])
        assert result.exit_code == 1
        # Should detect too few skills
        assert "skill" in result.stdout.lower()

    def test_health_check_shows_version_info(self, tmp_path: Path):
        """Health check displays version information."""
        runner.invoke(app, ["init", str(tmp_path), "--skip-health-check"])

        result = runner.invoke(app, ["health-check", str(tmp_path)])
        assert "version" in result.stdout.lower() or "0.5" in result.stdout.lower()
