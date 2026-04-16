"""Tests for agent discovery via .vrs/AGENTS.md (REL-06).

This module validates that:
1. .vrs/AGENTS.md exists and is readable
2. Agent names follow vrs-* naming convention
3. Skill names follow /vrs-* naming convention
4. Required sections are present
5. No deprecated true_vkg references
"""

from pathlib import Path
import re
import pytest


def get_project_root() -> Path:
    """Find project root containing pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find project root")


class TestAgentDiscovery:
    """Test suite for agent discovery interface (REL-06)."""

    @pytest.fixture
    def agents_md_path(self) -> Path:
        """Return path to .vrs/AGENTS.md."""
        return get_project_root() / ".vrs" / "AGENTS.md"

    @pytest.fixture
    def agents_md_content(self, agents_md_path: Path) -> str:
        """Return content of .vrs/AGENTS.md."""
        return agents_md_path.read_text()

    def test_agents_md_exists(self, agents_md_path: Path) -> None:
        """REL-06: .vrs/AGENTS.md must exist."""
        assert agents_md_path.exists(), f".vrs/AGENTS.md not found at {agents_md_path}"

    def test_agents_md_readable(self, agents_md_content: str) -> None:
        """REL-06: .vrs/AGENTS.md must be readable and non-empty."""
        assert len(agents_md_content) > 100, ".vrs/AGENTS.md appears to be empty or too short"

    def test_agent_names_use_vrs_prefix(self, agents_md_content: str) -> None:
        """REL-06: Agent names must use vrs-* prefix (not vkg-*)."""
        # Find all agent name patterns (typically in headers or lists)
        # Look for patterns like: vrs-attacker, vrs-defender, etc.
        vrs_agents = re.findall(r"\bvrs-[a-z]+(?:-[a-z]+)*\b", agents_md_content)
        vkg_agents = re.findall(r"\bvkg-[a-z]+(?:-[a-z]+)*\b", agents_md_content)

        assert len(vrs_agents) > 0, (
            ".vrs/AGENTS.md must contain at least one vrs-* agent name"
        )
        assert len(vkg_agents) == 0, (
            f".vrs/AGENTS.md contains deprecated vkg-* agent names: {vkg_agents}"
        )

    def test_skill_names_use_vrs_prefix(self, agents_md_content: str) -> None:
        """REL-06: Skill names must use /vrs-* prefix (not /vkg:*)."""
        # Find all skill name patterns (typically /vrs-command or /vkg:command)
        vrs_skills = re.findall(r"/vrs-[a-z]+(?:-[a-z]+)*", agents_md_content)
        vkg_skills = re.findall(r"/vkg:[a-z]+(?:-[a-z]+)*", agents_md_content)

        # Skills are optional but if present must use vrs: prefix
        if vrs_skills or vkg_skills:
            assert len(vkg_skills) == 0, (
                f".vrs/AGENTS.md contains deprecated /vkg:* skill names: {vkg_skills}"
            )

    def test_agents_md_has_required_sections(self, agents_md_content: str) -> None:
        """REL-06: .vrs/AGENTS.md should have standard sections."""
        content_lower = agents_md_content.lower()

        # Check for expected content indicating proper structure
        # At minimum, should mention agents in some form
        assert any(
            word in content_lower
            for word in ["agent", "vrs-", "attacker", "defender", "verifier"]
        ), ".vrs/AGENTS.md missing expected agent-related content"

    def test_no_true_vkg_references(self, agents_md_content: str) -> None:
        """REL-06: .vrs/AGENTS.md should not reference deprecated 'true_vkg' names."""
        assert "true_vkg" not in agents_md_content.lower(), (
            ".vrs/AGENTS.md contains deprecated 'true_vkg' reference"
        )

    def test_agents_md_has_cli_commands(self, agents_md_content: str) -> None:
        """REL-06: .vrs/AGENTS.md should document CLI commands."""
        # Should reference alphaswarm CLI
        assert "alphaswarm" in agents_md_content.lower(), (
            ".vrs/AGENTS.md should document alphaswarm CLI commands"
        )

    def test_agents_md_has_version_info(self, agents_md_content: str) -> None:
        """REL-06: .vrs/AGENTS.md should include version information."""
        # Should include version reference
        assert "0.5" in agents_md_content or "version" in agents_md_content.lower(), (
            ".vrs/AGENTS.md should include version information"
        )


class TestAgentFilesExist:
    """Test that individual agent definition files exist and use correct naming."""

    @pytest.fixture
    def claude_agents_dir(self) -> Path:
        """Return path to .claude/agents/ directory."""
        return get_project_root() / ".claude" / "agents"

    def test_agents_directory_exists(self, claude_agents_dir: Path) -> None:
        """Agent definition directory should exist."""
        assert claude_agents_dir.exists(), f".claude/agents/ not found at {claude_agents_dir}"

    def test_agent_files_use_vrs_prefix(self, claude_agents_dir: Path) -> None:
        """Agent files in .claude/agents/ should use vrs-* prefix."""
        if not claude_agents_dir.exists():
            pytest.skip(".claude/agents/ directory does not exist")

        agent_files = list(claude_agents_dir.glob("*.md"))
        if not agent_files:
            pytest.skip("No agent files found in .claude/agents/")

        # Find any vkg-* prefixed files (deprecated)
        vkg_files = [f.name for f in agent_files if f.name.startswith("vkg-")]
        assert len(vkg_files) == 0, (
            f"Found deprecated vkg-* agent files: {vkg_files}. "
            "Should be renamed to vrs-*"
        )

    def test_core_agents_present(self, claude_agents_dir: Path) -> None:
        """Core agents (attacker, defender, verifier) should be present."""
        if not claude_agents_dir.exists():
            pytest.skip(".claude/agents/ directory does not exist")

        agent_files = {f.stem for f in claude_agents_dir.glob("*.md")}

        # Check for core agents with vrs- prefix
        core_agents = ["vrs-attacker", "vrs-defender", "vrs-verifier"]
        missing = [a for a in core_agents if a not in agent_files]

        assert len(missing) == 0, f"Missing core agent files: {missing}"

    def test_agent_files_not_empty(self, claude_agents_dir: Path) -> None:
        """Agent files should have meaningful content."""
        if not claude_agents_dir.exists():
            pytest.skip(".claude/agents/ directory does not exist")

        vrs_files = list(claude_agents_dir.glob("vrs-*.md"))
        if not vrs_files:
            pytest.skip("No vrs-* agent files found")

        empty_files = []
        for f in vrs_files:
            content = f.read_text()
            if len(content) < 100:  # Minimum reasonable content
                empty_files.append(f.name)

        assert len(empty_files) == 0, f"Agent files with insufficient content: {empty_files}"


class TestNoDeprecatedReferences:
    """Test that production code doesn't contain deprecated references."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Return project root."""
        return get_project_root()

    def test_no_vkg_prefix_in_agents_md(self, project_root: Path) -> None:
        """AGENTS.md should not contain vkg- prefixed names."""
        agents_md = project_root / ".vrs" / "AGENTS.md"
        if not agents_md.exists():
            pytest.skip(".vrs/AGENTS.md not found")

        content = agents_md.read_text()

        # Check for deprecated vkg- agent prefix
        vkg_agents = re.findall(r"\bvkg-[a-z]+(?:-[a-z]+)*\b", content)
        assert len(vkg_agents) == 0, (
            f"Found deprecated vkg-* references in AGENTS.md: {vkg_agents}"
        )

        # Check for deprecated /vkg: skill prefix
        vkg_skills = re.findall(r"/vkg:[a-z]+(?:-[a-z]+)*", content)
        assert len(vkg_skills) == 0, (
            f"Found deprecated /vkg:* skill references in AGENTS.md: {vkg_skills}"
        )

    def test_vrs_directory_exists(self, project_root: Path) -> None:
        """.vrs/ config directory should exist (not .vkg/)."""
        vrs_dir = project_root / ".vrs"
        vkg_dir = project_root / ".vkg"

        assert vrs_dir.exists(), ".vrs/ directory not found"
        # Note: .vkg/ might still exist with old data, but .vrs/ must exist
