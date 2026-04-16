"""Tests for VRS skill file validation.

Tests that all 7 VRS skill files have proper structure, consistent format,
and complete documentation.

Part of Plan 05.4-08: Integration Testing
"""

from pathlib import Path
import pytest


VRS_SKILLS_DIR = Path(".claude/skills/vrs")

# All expected VRS skills
EXPECTED_SKILLS = [
    "discover.md",
    "add-vulnerability.md",
    "research.md",
    "refine.md",
    "test-pattern.md",
    "merge-findings.md",
    "generate-tests.md",
]


# =============================================================================
# Skill File Existence Tests
# =============================================================================


def test_vrs_skills_directory_exists():
    """Test that VRS skills directory exists."""
    assert VRS_SKILLS_DIR.exists(), f"VRS skills directory not found: {VRS_SKILLS_DIR}"
    assert VRS_SKILLS_DIR.is_dir(), f"VRS skills path is not a directory: {VRS_SKILLS_DIR}"


def test_readme_exists():
    """Test that README.md exists in VRS skills directory."""
    readme = VRS_SKILLS_DIR / "README.md"
    assert readme.exists(), "README.md missing from VRS skills directory"


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skill_file_exists(skill_file):
    """Test that each expected skill file exists."""
    skill_path = VRS_SKILLS_DIR / skill_file
    assert skill_path.exists(), f"Skill file missing: {skill_file}"
    assert skill_path.is_file(), f"Skill path is not a file: {skill_file}"


# =============================================================================
# Skill Content Validation Tests
# =============================================================================


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skills_have_slash_command(skill_file):
    """Test that all skills document their slash command with vrs: prefix."""
    skill_path = VRS_SKILLS_DIR / skill_file
    content = skill_path.read_text()

    # Should mention the /vrs- command
    skill_name = skill_file.replace(".md", "")
    assert f"/vrs-{skill_name}" in content or f"vrs:{skill_name}" in content, \
        f"Skill {skill_file} doesn't document its /vrs-{skill_name} command"


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skills_have_purpose(skill_file):
    """Test that all skills document their purpose."""
    skill_path = VRS_SKILLS_DIR / skill_file
    content = skill_path.read_text()

    # Should have a purpose/what it does section
    purpose_indicators = ["purpose", "what it does", "what this does"]
    has_purpose = any(indicator.lower() in content.lower() for indicator in purpose_indicators)

    assert has_purpose, f"Skill {skill_file} doesn't document its purpose"


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skills_have_workflow(skill_file):
    """Test that all skills document workflow steps."""
    skill_path = VRS_SKILLS_DIR / skill_file
    content = skill_path.read_text()

    # Should document workflow steps
    workflow_indicators = ["workflow", "steps", "process", "procedure"]
    has_workflow = any(indicator.lower() in content.lower() for indicator in workflow_indicators)

    assert has_workflow, f"Skill {skill_file} doesn't document workflow steps"


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skills_have_tools_section(skill_file):
    """Test that all skills list required tools."""
    skill_path = VRS_SKILLS_DIR / skill_file
    content = skill_path.read_text()

    # Should mention tools (Read, Write, Bash, etc.)
    tools_indicators = ["tool", "bash", "read", "write", "cli"]
    has_tools = any(indicator.lower() in content.lower() for indicator in tools_indicators)

    assert has_tools, f"Skill {skill_file} doesn't list required tools"


# =============================================================================
# Skill Consistency Tests
# =============================================================================


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skills_reference_cli_commands(skill_file):
    """Test that skills reference vulndocs CLI commands where appropriate."""
    skill_path = VRS_SKILLS_DIR / skill_file
    content = skill_path.read_text()

    # Skills that should reference CLI
    cli_skills = ["discover.md", "add-vulnerability.md", "test-pattern.md"]

    if skill_file in cli_skills:
        # Should mention alphaswarm or vulndocs CLI
        has_cli_ref = "alphaswarm" in content or "vulndocs" in content or "uv run" in content

        assert has_cli_ref, f"Skill {skill_file} should reference CLI commands"


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skills_have_output_format(skill_file):
    """Test that all skills document expected output."""
    skill_path = VRS_SKILLS_DIR / skill_file
    content = skill_path.read_text()

    # Should document output or results
    output_indicators = ["output", "result", "produce", "generate", "create"]
    has_output = any(indicator.lower() in content.lower() for indicator in output_indicators)

    assert has_output, f"Skill {skill_file} doesn't document expected output"


@pytest.mark.parametrize("skill_file", EXPECTED_SKILLS)
def test_skills_document_bash_invocation(skill_file):
    """Test that skills explain CLI commands are invoked via Bash tool."""
    skill_path = VRS_SKILLS_DIR / skill_file
    content = skill_path.read_text()

    # Skills that use CLI should mention Bash tool invocation
    cli_skills = ["discover.md", "add-vulnerability.md", "test-pattern.md"]

    if skill_file in cli_skills:
        # Should mention that CLI commands run via Bash tool
        has_bash_note = "bash" in content.lower() and ("tool" in content.lower() or "invoke" in content.lower())

        assert has_bash_note, f"Skill {skill_file} should explain Bash tool invocation"


def test_skills_use_graph_queries():
    """Test that skills emphasize graph queries over manual code reading."""
    # Check key skills that should use VQL/graph queries
    key_skills = ["discover.md", "add-vulnerability.md", "refine.md"]

    for skill_file in key_skills:
        skill_path = VRS_SKILLS_DIR / skill_file
        content = skill_path.read_text()

        # Should mention VQL or graph queries
        graph_indicators = ["vql", "graph", "query", "pattern"]
        has_graph_ref = any(indicator.lower() in content.lower() for indicator in graph_indicators)

        assert has_graph_ref, f"Skill {skill_file} should mention VQL/graph queries"


# =============================================================================
# README Validation Tests
# =============================================================================


def test_readme_lists_all_skills():
    """Test that README lists all 7 VRS skills."""
    readme = VRS_SKILLS_DIR / "README.md"
    content = readme.read_text()

    # Should mention all skill names (without .md)
    for skill_file in EXPECTED_SKILLS:
        skill_name = skill_file.replace(".md", "")
        assert skill_name in content, f"README doesn't list {skill_name} skill"


def test_readme_has_workflow_diagram():
    """Test that README shows skill relationships/workflow."""
    readme = VRS_SKILLS_DIR / "README.md"
    content = readme.read_text()

    # Should have workflow/diagram indicators
    workflow_indicators = ["workflow", "flow", "diagram", "relationship"]
    has_workflow = any(indicator.lower() in content.lower() for indicator in workflow_indicators)

    assert has_workflow, "README doesn't document skill workflow/relationships"


def test_readme_explains_invocation_model():
    """Test that README explains how agents use skills."""
    readme = VRS_SKILLS_DIR / "README.md"
    content = readme.read_text()

    # Should explain the invocation model
    invocation_indicators = [
        "invocation",
        "how skills work",
        "agent",
        "bash tool",
    ]
    has_invocation = any(indicator.lower() in content.lower() for indicator in invocation_indicators)

    assert has_invocation, "README doesn't explain skill invocation model"


def test_readme_documents_vrs_prefix():
    """Test that README explains the vrs: prefix."""
    readme = VRS_SKILLS_DIR / "README.md"
    content = readme.read_text()

    # Should explain why vrs: prefix is used
    assert "vrs:" in content, "README doesn't mention vrs: prefix"
    assert "prefix" in content.lower(), "README doesn't explain prefix rationale"


# =============================================================================
# Specific Skill Validation Tests
# =============================================================================


def test_discover_skill_uses_exa():
    """Test that discover skill documents Exa MCP usage."""
    skill_path = VRS_SKILLS_DIR / "discover.md"
    content = skill_path.read_text()

    # Should mention Exa for web research
    assert "exa" in content.lower(), "discover skill doesn't mention Exa MCP"
    assert "search" in content.lower(), "discover skill doesn't mention search"


def test_add_vulnerability_uses_scaffold():
    """Test that add-vulnerability skill references scaffold command."""
    skill_path = VRS_SKILLS_DIR / "add-vulnerability.md"
    content = skill_path.read_text()

    # Should mention scaffold
    assert "scaffold" in content.lower(), "add-vulnerability doesn't mention scaffold"


def test_test_pattern_validates_patterns():
    """Test that test-pattern skill validates against real projects."""
    skill_path = VRS_SKILLS_DIR / "test-pattern.md"
    content = skill_path.read_text()

    # Should mention testing against projects
    validation_indicators = ["test", "validate", "project", "contract"]
    has_validation = any(indicator.lower() in content.lower() for indicator in validation_indicators)

    assert has_validation, "test-pattern doesn't mention validation against projects"


def test_generate_tests_uses_reasoning_template():
    """Test that generate-tests skill references reasoning_template."""
    skill_path = VRS_SKILLS_DIR / "generate-tests.md"
    content = skill_path.read_text()

    # Should mention reasoning_template for test generation
    assert "reasoning_template" in content or "reasoning template" in content.lower(), \
        "generate-tests doesn't reference reasoning_template"


def test_merge_findings_consolidates():
    """Test that merge-findings skill consolidates similar entries."""
    skill_path = VRS_SKILLS_DIR / "merge-findings.md"
    content = skill_path.read_text()

    # Should mention consolidation/merging/deduplication
    merge_indicators = ["merge", "consolidate", "deduplicate", "similar"]
    has_merge = any(indicator.lower() in content.lower() for indicator in merge_indicators)

    assert has_merge, "merge-findings doesn't mention consolidation"


def test_research_skill_is_user_guided():
    """Test that research skill documents user guidance."""
    skill_path = VRS_SKILLS_DIR / "research.md"
    content = skill_path.read_text()

    # Should distinguish from discover (user-guided vs automated)
    guidance_indicators = ["user", "guided", "topic", "request"]
    has_guidance = any(indicator.lower() in content.lower() for indicator in guidance_indicators)

    assert has_guidance, "research skill doesn't document user guidance"


def test_refine_skill_iterates_patterns():
    """Test that refine skill documents pattern iteration."""
    skill_path = VRS_SKILLS_DIR / "refine.md"
    content = skill_path.read_text()

    # Should mention iteration, feedback, improvement
    iteration_indicators = ["refine", "improve", "iterate", "feedback"]
    has_iteration = any(indicator.lower() in content.lower() for indicator in iteration_indicators)

    assert has_iteration, "refine skill doesn't document pattern iteration"
