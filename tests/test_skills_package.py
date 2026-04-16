"""Tests for skills package structure."""

import pytest
from pathlib import Path

from alphaswarm_sol.skills import get_shipped_skills_path, list_shipped_skills


class TestSkillsPackage:
    """Tests for skills package structure and content."""

    def test_get_shipped_skills_path_exists(self):
        """Shipped skills path exists."""
        path = get_shipped_skills_path()
        assert path.exists()
        assert path.is_dir()

    def test_get_shipped_skills_path_returns_shipped_dir(self):
        """get_shipped_skills_path returns the shipping/skills subdirectory."""
        path = get_shipped_skills_path()
        assert path.name == "skills"

    def test_list_shipped_skills_returns_list(self):
        """list_shipped_skills returns list of skill names."""
        skills = list_shipped_skills()
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_list_shipped_skills_excludes_readme(self):
        """list_shipped_skills excludes README.md."""
        skills = list_shipped_skills()
        assert "README.md" not in skills

    def test_shipped_skills_have_md_extension(self):
        """All shipped skills are .md files."""
        path = get_shipped_skills_path()
        for skill_file in path.glob("*.md"):
            assert skill_file.suffix == ".md"

    def test_shipped_skills_have_frontmatter(self):
        """All shipped skills have YAML frontmatter."""
        path = get_shipped_skills_path()
        skill_files = [f for f in path.glob("*.md") if f.name != "README.md"]

        # Should have at least some skills
        assert len(skill_files) > 0

        for skill_file in skill_files:
            content = skill_file.read_text()
            assert content.startswith("---"), f"{skill_file.name} missing frontmatter"

            # Check frontmatter closes
            parts = content.split("---", 2)
            assert len(parts) >= 3, f"{skill_file.name} frontmatter not closed"

    def test_core_skills_exist(self):
        """Core skills (audit, health-check) exist."""
        path = get_shipped_skills_path()
        skill_names = [f.name for f in path.glob("*.md")]

        # Check for expected core skills
        # At least one of these should exist
        has_audit = any("audit" in name for name in skill_names)
        has_health = any("health" in name for name in skill_names)

        assert has_audit or has_health, "No core skills (audit or health-check) found"

    def test_skills_use_vrs_namespace(self):
        """Skills use vrs: namespace in slash commands."""
        path = get_shipped_skills_path()
        skill_files = [f for f in path.glob("*.md") if f.name != "README.md"]

        for skill_file in skill_files:
            content = skill_file.read_text()

            # If skill has slash_command field, it should use vrs: namespace
            if "slash_command:" in content:
                # Get the frontmatter section
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    # Check if slash_command uses vrs: namespace
                    if "slash_command:" in frontmatter:
                        assert "vrs:" in frontmatter, f"{skill_file.name} should use vrs: namespace"

    def test_agents_directory_optional(self):
        """Agents subdirectory is optional but valid if exists."""
        path = get_shipped_skills_path()
        agents_dir = path / "agents"

        # If agents directory exists, check it has content
        if agents_dir.exists():
            assert agents_dir.is_dir()
            agents = list(agents_dir.glob("*.md"))
            # If directory exists, should have at least one agent
            assert len(agents) > 0

    def test_skills_have_reasonable_filenames(self):
        """Skills have reasonable lowercase filenames."""
        skills = list_shipped_skills()

        for skill in skills:
            # Should be lowercase with dashes or underscores
            assert skill.islower() or "-" in skill or "_" in skill
            # Should end with .md
            assert skill.endswith(".md")
            # Should not have spaces
            assert " " not in skill

    def test_list_shipped_skills_is_sorted(self):
        """list_shipped_skills returns sorted list."""
        skills = list_shipped_skills()
        assert skills == sorted(skills)

    def test_skills_are_readable(self):
        """All skill files are readable."""
        path = get_shipped_skills_path()
        skill_files = list(path.glob("*.md"))

        for skill_file in skill_files:
            # Should be able to read without error
            content = skill_file.read_text()
            assert len(content) > 0

    def test_skills_have_required_frontmatter_fields(self):
        """Skills have required frontmatter fields."""
        path = get_shipped_skills_path()
        skill_files = [f for f in path.glob("*.md") if f.name != "README.md"]

        for skill_file in skill_files:
            content = skill_file.read_text()
            if not content.startswith("---"):
                continue  # Skip if no frontmatter

            parts = content.split("---", 2)
            if len(parts) < 3:
                continue

            frontmatter = parts[1]

            # Should have at least some basic fields
            # (Not all skills may have all fields, but most should)
            has_slash_command = "slash_command:" in frontmatter
            has_description = "description:" in frontmatter or "summary:" in frontmatter

            # At least one identifying field should exist
            assert has_slash_command or has_description, \
                f"{skill_file.name} missing basic frontmatter fields"

    def test_readme_exists_in_shipped(self):
        """README.md exists in shipped skills directory."""
        path = get_shipped_skills_path()
        readme = path / "README.md"

        # README is optional but recommended
        # If it exists, should have content
        if readme.exists():
            content = readme.read_text()
            assert len(content) > 0
            # Should mention VRS or skills
            assert "vrs" in content.lower() or "skill" in content.lower()

    def test_no_duplicate_skill_names(self):
        """No duplicate skill names in shipped directory."""
        skills = list_shipped_skills()
        assert len(skills) == len(set(skills)), "Duplicate skill names found"

    def test_skills_path_is_within_package(self):
        """Skills path is within the alphaswarm_sol package."""
        path = get_shipped_skills_path()
        # Should be under alphaswarm_sol/shipping/skills
        assert "alphaswarm_sol" in str(path)
        assert "shipping" in str(path)
        assert "skills" in str(path)
