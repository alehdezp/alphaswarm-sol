"""
Tests for skill schema v2 validation.

Tests validate that shipped skills and repo skills comply with schema v2.
"""

import json
from pathlib import Path

import pytest

from src.alphaswarm_sol.skills.skill_schema import (
    SkillSchemaValidator,
    validate_skill_schema,
)


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def schema_path(project_root):
    """Get skill schema v2 path."""
    return project_root / "schemas" / "skill_schema_v2.json"


@pytest.fixture
def validator(schema_path):
    """Create validator instance."""
    return SkillSchemaValidator(schema_path=schema_path)


@pytest.fixture
def shipped_skills_dir(project_root):
    """Get shipped skills directory."""
    return project_root / "src" / "alphaswarm_sol" / "shipping" / "skills"


@pytest.fixture
def repo_skills_dir(project_root):
    """Get repo .claude/skills directory."""
    return project_root / ".claude" / "skills"


class TestSchemaStructure:
    """Test schema v2 structure and completeness."""

    def test_schema_exists(self, schema_path):
        """Schema v2 file exists."""
        assert schema_path.exists(), f"Schema not found: {schema_path}"

    def test_schema_valid_json(self, schema_path):
        """Schema is valid JSON."""
        schema = json.loads(schema_path.read_text())
        assert schema is not None
        assert isinstance(schema, dict)

    def test_schema_has_required_fields(self, schema_path):
        """Schema defines all required fields."""
        schema = json.loads(schema_path.read_text())

        required = schema.get("required", [])

        # Core fields
        assert "name" in required
        assert "description" in required
        assert "slash_command" in required
        assert "context" in required
        assert "role" in required
        assert "model_tier" in required
        assert "tools" in required

        # Evidence and contracts
        assert "evidence_requirements" in required
        assert "output_contract" in required
        assert "failure_modes" in required
        assert "version" in required

    def test_schema_defines_role_enum(self, schema_path):
        """Schema constrains role field to valid values."""
        schema = json.loads(schema_path.read_text())

        role_def = schema["properties"]["role"]
        assert role_def["type"] == "string"
        assert "enum" in role_def

        # Check core roles present
        roles = role_def["enum"]
        assert "attacker" in roles
        assert "defender" in roles
        assert "verifier" in roles
        assert "orchestrator" in roles
        assert "researcher" in roles

    def test_schema_defines_evidence_requirements(self, schema_path):
        """Schema defines evidence_requirements structure."""
        schema = json.loads(schema_path.read_text())

        evidence_def = schema["properties"]["evidence_requirements"]
        assert evidence_def["type"] == "object"

        required = evidence_def.get("required", [])
        assert "must_link_code" in required
        assert "min_evidence_items" in required
        assert "cite_graph_nodes" in required

    def test_schema_defines_output_contract(self, schema_path):
        """Schema defines output_contract structure."""
        schema = json.loads(schema_path.read_text())

        output_def = schema["properties"]["output_contract"]
        assert output_def["type"] == "object"

        required = output_def.get("required", [])
        assert "format" in required
        assert "schema" in required


class TestValidator:
    """Test validator functionality."""

    def test_validator_initialization(self, validator):
        """Validator initializes successfully."""
        assert validator.schema is not None
        assert validator.validator is not None

    def test_extract_frontmatter_valid(self, validator, tmp_path):
        """Extract frontmatter from valid skill file."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text("""---
name: test-skill
description: Test skill
---

# Test Skill

Content here.
""")

        frontmatter = validator.extract_frontmatter(skill_file)
        assert frontmatter is not None
        assert frontmatter["name"] == "test-skill"
        assert frontmatter["description"] == "Test skill"

    def test_extract_frontmatter_missing(self, validator, tmp_path):
        """Return None for missing frontmatter."""
        skill_file = tmp_path / "test.md"
        skill_file.write_text("# No frontmatter\n\nJust content.")

        frontmatter = validator.extract_frontmatter(skill_file)
        assert frontmatter is None

    def test_validate_minimal_valid_skill(self, validator):
        """Validate minimal valid skill frontmatter."""
        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "slash_command": "test:skill",
            "context": "fork",
            "role": "tester",
            "model_tier": "sonnet",
            "tools": ["Read"],
            "evidence_requirements": {
                "must_link_code": True,
                "min_evidence_items": 1,
                "cite_graph_nodes": True
            },
            "output_contract": {
                "format": "json",
                "schema": {"type": "object"}
            },
            "failure_modes": [
                {"condition": "No files", "resolution": "Check path"}
            ],
            "version": "1.0.0"
        }

        is_valid, errors = validator.validate(frontmatter)
        assert is_valid, f"Validation failed: {errors}"

    def test_validate_missing_required_field(self, validator):
        """Validation fails when required field missing."""
        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            # Missing slash_command
            "context": "fork",
            "role": "tester",
            "model_tier": "sonnet",
            "tools": ["Read"],
            "evidence_requirements": {
                "must_link_code": True,
                "min_evidence_items": 1,
                "cite_graph_nodes": True
            },
            "output_contract": {
                "format": "json",
                "schema": {"type": "object"}
            },
            "failure_modes": [],
            "version": "1.0.0"
        }

        is_valid, errors = validator.validate(frontmatter)
        assert not is_valid
        assert any("slash_command" in err for err in errors)

    def test_validate_invalid_role(self, validator):
        """Validation fails for invalid role value."""
        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "slash_command": "test:skill",
            "context": "fork",
            "role": "invalid-role",  # Not in enum
            "model_tier": "sonnet",
            "tools": ["Read"],
            "evidence_requirements": {
                "must_link_code": True,
                "min_evidence_items": 1,
                "cite_graph_nodes": True
            },
            "output_contract": {
                "format": "json",
                "schema": {"type": "object"}
            },
            "failure_modes": [],
            "version": "1.0.0"
        }

        is_valid, errors = validator.validate(frontmatter)
        assert not is_valid
        assert any("role" in err for err in errors)

    def test_validate_deprecated_without_sunset(self, validator):
        """Validation warns for deprecated without sunset_date."""
        frontmatter = {
            "name": "test-skill",
            "description": "Test skill",
            "slash_command": "test:skill",
            "context": "fork",
            "role": "tester",
            "model_tier": "sonnet",
            "tools": ["Read"],
            "evidence_requirements": {
                "must_link_code": True,
                "min_evidence_items": 1,
                "cite_graph_nodes": True
            },
            "output_contract": {
                "format": "json",
                "schema": {"type": "object"}
            },
            "failure_modes": [],
            "version": "1.0.0",
            "deprecated": True
            # Missing sunset_date
        }

        is_valid, errors = validator.validate(frontmatter)
        assert not is_valid
        assert any("sunset_date" in err for err in errors)


class TestShippedSkills:
    """Test shipped skills in src/alphaswarm_sol/shipping/skills/."""

    def test_shipped_skills_directory_exists(self, shipped_skills_dir):
        """Shipped skills directory exists."""
        assert shipped_skills_dir.exists()
        assert shipped_skills_dir.is_dir()

    def test_shipped_skills_have_md_files(self, shipped_skills_dir):
        """Shipped skills directory contains .md files."""
        md_files = list(shipped_skills_dir.glob("*.md"))
        # Filter out README
        skill_files = [f for f in md_files if f.name != "README.md"]
        assert len(skill_files) > 0, "No skill .md files found in shipped/"

    @pytest.mark.skip(reason="Shipped skills not yet migrated to schema v2")
    def test_validate_all_shipped_skills(self, shipped_skills_dir):
        """All shipped skills validate against schema v2."""
        valid_count, invalid_count, errors = validate_skill_schema(
            shipped_skills_dir,
            strict=False  # Allow missing frontmatter during migration
        )

        if invalid_count > 0:
            pytest.fail(f"Shipped skills validation failed:\n" + "\n".join(errors))


class TestRepoSkills:
    """Test repo skills in .claude/skills/."""

    def test_repo_skills_directory_exists(self, repo_skills_dir):
        """Repo skills directory exists."""
        assert repo_skills_dir.exists()
        assert repo_skills_dir.is_dir()

    def test_repo_skills_have_skill_files(self, repo_skills_dir):
        """Repo skills contain SKILL.md files."""
        skill_files = list(repo_skills_dir.rglob("SKILL.md"))
        assert len(skill_files) > 0, "No SKILL.md files found in .claude/skills/"

    @pytest.mark.skip(reason="Repo skills not yet migrated to schema v2")
    def test_validate_all_repo_skills(self, repo_skills_dir):
        """All repo skills validate against schema v2."""
        # Find all SKILL.md files
        skill_files = list(repo_skills_dir.rglob("SKILL.md"))

        validator = SkillSchemaValidator()
        failures = []

        for skill_file in skill_files:
            is_valid, errors = validator.validate_file(skill_file, strict=False)
            if not is_valid:
                failures.append((skill_file, errors))

        if failures:
            error_msg = "Repo skills validation failed:\n"
            for skill_file, errors in failures:
                error_msg += f"\n{skill_file}:\n"
                error_msg += "\n".join(f"  - {err}" for err in errors)
            pytest.fail(error_msg)


class TestValidatorCLI:
    """Test validator CLI script."""

    def test_validator_cli_exists(self, project_root):
        """Validator CLI script exists."""
        cli_path = project_root / "scripts" / "validate_skill_schema.py"
        assert cli_path.exists()

    def test_validator_cli_executable(self, project_root):
        """Validator CLI script is executable."""
        cli_path = project_root / "scripts" / "validate_skill_schema.py"
        # Check if file has execute permission
        import os
        assert os.access(cli_path, os.X_OK)

    def test_validator_cli_help(self, project_root):
        """Validator CLI --help works."""
        import subprocess

        cli_path = project_root / "scripts" / "validate_skill_schema.py"
        result = subprocess.run(
            ["uv", "run", "python", str(cli_path), "--help"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "validate skill frontmatter" in result.stdout.lower()


class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow_valid_skill(self, validator, tmp_path):
        """Complete workflow: create skill, validate, passes."""
        skill_file = tmp_path / "valid-skill.md"
        skill_file.write_text("""---
name: valid-skill
description: A valid test skill
slash_command: test:valid
context: fork
role: tester
model_tier: sonnet
tools:
  - Read
  - Write
evidence_requirements:
  must_link_code: true
  min_evidence_items: 2
  cite_graph_nodes: true
  graph_first: true
output_contract:
  format: json
  schema:
    type: object
    required: [status]
failure_modes:
  - condition: No input
    resolution: Check arguments
version: 1.0.0
max_token_budget: 4000
---

# Valid Skill

This is a valid skill.
""")

        is_valid, errors = validator.validate_file(skill_file, strict=True)
        assert is_valid, f"Validation failed: {errors}"

    def test_full_workflow_invalid_skill(self, validator, tmp_path):
        """Complete workflow: create invalid skill, validate, fails."""
        skill_file = tmp_path / "invalid-skill.md"
        skill_file.write_text("""---
name: invalid-skill
description: Missing required fields
slash_command: test:invalid
# Missing: context, role, model_tier, tools, evidence_requirements, etc.
---

# Invalid Skill

This skill is missing required fields.
""")

        is_valid, errors = validator.validate_file(skill_file, strict=True)
        assert not is_valid
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
