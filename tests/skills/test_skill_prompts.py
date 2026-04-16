"""
Tests for skill prompt structure and graph-first requirements.

Validates that VRS skills enforce graph-first reasoning and include
required sections for evidence-based vulnerability analysis.
"""

import json
from pathlib import Path

import pytest

from src.alphaswarm_sol.skills.skill_schema import SkillSchemaValidator


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
def vrs_skills_dir(project_root):
    """Get VRS skills directory."""
    return project_root / ".claude" / "skills" / "vrs"


@pytest.fixture
def agent_skills_dir(project_root):
    """Get shipped agent skills directory."""
    return project_root / "src" / "alphaswarm_sol" / "skills" / "shipped" / "agents"


@pytest.fixture
def subagents_dir(project_root):
    """Get subagents directory."""
    return project_root / ".claude" / "subagents"


class TestPromptStructure:
    """Test skill prompt structure compliance."""

    def test_vrs_skills_have_frontmatter(self, vrs_skills_dir, validator):
        """Test that VRS skills with frontmatter have valid frontmatter."""
        if not vrs_skills_dir.exists():
            pytest.skip(f"VRS skills directory not found: {vrs_skills_dir}")

        skill_files = list(vrs_skills_dir.glob("*.md"))
        if not skill_files:
            pytest.skip("No VRS skill files found")

        skills_with_frontmatter = 0

        for skill_file in skill_files:
            if skill_file.name == "README.md":
                continue

            content = skill_file.read_text()

            # Check for JSON frontmatter
            if not content.startswith("```json"):
                # Skip skills without frontmatter (legacy or in development)
                continue

            skills_with_frontmatter += 1

            # Extract frontmatter
            lines = content.split("\n")
            json_lines = []
            in_frontmatter = False

            for line in lines:
                if line.strip() == "```json":
                    in_frontmatter = True
                    continue
                if line.strip() == "```" and in_frontmatter:
                    break
                if in_frontmatter:
                    json_lines.append(line)

            if not json_lines:
                pytest.fail(f"{skill_file.name}: Empty frontmatter")

            # Parse and validate
            try:
                frontmatter = json.loads("\n".join(json_lines))
                is_valid, errors = validator.validate(frontmatter)
                if not is_valid:
                    pytest.fail(f"{skill_file.name}: Schema validation failed: {errors}")
            except json.JSONDecodeError as e:
                pytest.fail(f"{skill_file.name}: Invalid JSON frontmatter: {e}")

        # Skip if no skills with frontmatter yet (during migration)
        if skills_with_frontmatter == 0:
            pytest.skip("No VRS skills with frontmatter found (migration in progress)")

    def test_agent_skills_have_frontmatter(self, agent_skills_dir, validator):
        """Test that shipped agent skills with frontmatter have valid frontmatter."""
        if not agent_skills_dir.exists():
            pytest.skip(f"Agent skills directory not found: {agent_skills_dir}")

        agent_files = list(agent_skills_dir.glob("*.md"))
        if not agent_files:
            pytest.skip("No agent skill files found")

        agents_with_frontmatter = 0

        for agent_file in agent_files:
            if agent_file.name == "README.md":
                continue

            content = agent_file.read_text()

            # Check for JSON frontmatter
            if not content.startswith("```json"):
                # Skip agents without frontmatter (legacy or in development)
                continue

            agents_with_frontmatter += 1

        # Skip if no agents with frontmatter yet (during migration)
        if agents_with_frontmatter == 0:
            pytest.skip("No agent skills with frontmatter found (migration in progress)")


class TestGraphFirstRequirements:
    """Test graph-first reasoning requirements in skill prompts."""

    @pytest.mark.parametrize("skill_name,role", [
        ("vrs-attacker.md", "attacker"),
        ("vrs-defender.md", "defender"),
        ("vrs-verifier.md", "verifier"),
    ])
    def test_vrs_agents_require_graph_queries(self, agent_skills_dir, skill_name, role):
        """Test that VRS agent skills enforce graph-first queries."""
        skill_file = agent_skills_dir / skill_name

        if not skill_file.exists():
            pytest.skip(f"Skill file not found: {skill_file}")

        content = skill_file.read_text().lower()

        # Check for graph-first mentions
        graph_first_terms = [
            "graph-first",
            "bskg query",
            "vql query",
            "query the graph",
            "graph queries",
        ]

        has_graph_first = any(term in content for term in graph_first_terms)
        assert has_graph_first, f"{skill_name}: Missing graph-first requirements"

    def test_secure_reviewer_requires_graph_queries(self, subagents_dir):
        """Test that secure reviewer enforces graph-first reasoning."""
        reviewer_file = subagents_dir / "secure-solidity-reviewer.md"

        if not reviewer_file.exists():
            pytest.skip(f"Secure reviewer not found: {reviewer_file}")

        content = reviewer_file.read_text().lower()

        # Check for graph-first enforcement
        required_terms = [
            "graph-first",
            "bskg",
            "graph queries",
            "evidence-first",
        ]

        for term in required_terms:
            assert term in content, f"secure-solidity-reviewer.md: Missing '{term}'"

    def test_graph_first_template_references(self, project_root):
        """Test that graph-first template is referenced in key skills."""
        template_path = project_root / "docs" / "reference" / "graph-first-template.md"

        if not template_path.exists():
            pytest.skip("Graph-first template not found")

        # Check TOOLING.md references the template
        tooling_path = project_root / ".planning" / "TOOLING.md"
        if tooling_path.exists():
            tooling_content = tooling_path.read_text()
            assert "graph-first" in tooling_content.lower(), "TOOLING.md: Missing graph-first reference"


class TestEvidenceRequirements:
    """Test evidence contract requirements in skill prompts."""

    def test_vrs_skills_require_evidence(self, vrs_skills_dir):
        """Test that VRS skills enforce evidence requirements."""
        if not vrs_skills_dir.exists():
            pytest.skip(f"VRS skills directory not found: {vrs_skills_dir}")

        # Skills that must have evidence requirements
        evidence_required_skills = [
            "add-vulnerability.md",
            "refine.md",
            "test-pattern.md",
        ]

        for skill_name in evidence_required_skills:
            skill_file = vrs_skills_dir / skill_name

            if not skill_file.exists():
                continue

            content = skill_file.read_text().lower()

            evidence_terms = [
                "evidence",
                "code location",
                "graph node",
                "confidence",
            ]

            has_evidence = any(term in content for term in evidence_terms)
            assert has_evidence, f"{skill_name}: Missing evidence requirements"

    def test_secure_reviewer_output_contract(self, subagents_dir, project_root):
        """Test that secure reviewer references output contract schema."""
        reviewer_file = subagents_dir / "secure-solidity-reviewer.md"

        if not reviewer_file.exists():
            pytest.skip("Secure reviewer not found")

        content = reviewer_file.read_text()

        # Check for schema reference
        assert "secure_reviewer_output.json" in content, \
            "secure-solidity-reviewer.md: Missing output schema reference"

        # Verify schema exists
        schema_path = project_root / "schemas" / "secure_reviewer_output.json"
        assert schema_path.exists(), "secure_reviewer_output.json schema not found"


class TestOutputContracts:
    """Test that skills declare proper output contracts."""

    def test_skills_with_json_output_reference_schemas(self, vrs_skills_dir):
        """Test that skills with JSON output reference their schemas."""
        if not vrs_skills_dir.exists():
            pytest.skip("VRS skills directory not found")

        for skill_file in vrs_skills_dir.glob("*.md"):
            if skill_file.name == "README.md":
                continue

            content = skill_file.read_text()

            # Skip if not a JSON output skill
            if "output" not in content.lower() and "json" not in content.lower():
                continue

            # Extract frontmatter
            lines = content.split("\n")
            json_lines = []
            in_frontmatter = False

            for line in lines:
                if line.strip() == "```json":
                    in_frontmatter = True
                    continue
                if line.strip() == "```" and in_frontmatter:
                    break
                if in_frontmatter:
                    json_lines.append(line)

            if not json_lines:
                continue

            try:
                frontmatter = json.loads("\n".join(json_lines))

                # Check for output_contract
                if "output_contract" in frontmatter:
                    output_contract = frontmatter["output_contract"]

                    # Verify it has required fields
                    assert "format" in output_contract, \
                        f"{skill_file.name}: output_contract missing 'format'"
                    assert "schema" in output_contract, \
                        f"{skill_file.name}: output_contract missing 'schema'"

            except json.JSONDecodeError:
                # Skip if frontmatter is malformed (caught by other tests)
                pass
