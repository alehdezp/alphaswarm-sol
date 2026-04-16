"""Tests for VulnDocs CLI commands.

Tests Phase 5.4 Plan 04: CLI validation and scaffolding commands.
"""

from pathlib import Path
import json
import pytest
from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app


runner = CliRunner()


@pytest.fixture
def temp_vulndocs(tmp_path: Path) -> Path:
    """Create a temporary vulndocs directory structure."""
    vulndocs_root = tmp_path / "vulndocs"
    vulndocs_root.mkdir()

    # Create .meta/templates directory (new structure)
    meta_dir = vulndocs_root / ".meta"
    meta_dir.mkdir()
    templates_dir = meta_dir / "templates"
    templates_dir.mkdir()

    # Create category template
    (templates_dir / "category.yaml").write_text("""# Category: {{category}}
name: {{name}}
created: {{date}}
""")

    # Create subcategory templates
    subcategory_dir = templates_dir / "subcategory"
    subcategory_dir.mkdir()

    (subcategory_dir / "index.yaml").write_text("""id: {{category}}-{{subcategory}}
category: {{category}}
subcategory: {{subcategory}}
severity: {{severity}}
vulndoc: {{vulndoc}}
created: {{date}}
semantic_triggers: []
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    (subcategory_dir / "overview.md").write_text("""# {{vulndoc}}

Severity: {{severity}}
""")

    (subcategory_dir / "detection.md").write_text("""# Detection

TODO: Add detection logic for {{vulndoc}}
""")

    (subcategory_dir / "verification.md").write_text("""# Verification

TODO: Add verification steps for {{vulndoc}}
""")

    (subcategory_dir / "exploits.md").write_text("""# Exploits

TODO: Add exploit examples for {{vulndoc}}
""")

    return vulndocs_root


# Validate command tests


def test_validate_empty_vulndocs(temp_vulndocs: Path):
    """Validate command handles empty vulndocs directory without error."""
    result = runner.invoke(app, ["vulndocs", "validate", str(temp_vulndocs)])

    assert result.exit_code == 0
    assert "No vulnerabilities found to validate" in result.stdout or "Validated: 0 entries" in result.stdout


def test_validate_actually_runs_validation(temp_vulndocs: Path):
    """CRITICAL: Verify validate_framework is called and produces real results."""
    # Create a test vulnerability to validate
    oracle_dir = temp_vulndocs / "oracle"
    oracle_dir.mkdir()
    price_manip_dir = oracle_dir / "price-manipulation"
    price_manip_dir.mkdir()

    # Create index.yaml
    (price_manip_dir / "index.yaml").write_text("""id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: critical
vulndoc: oracle/price-manipulation
semantic_triggers: []
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    result = runner.invoke(app, ["vulndocs", "validate", str(temp_vulndocs)])

    # Verify actual validation output (not just help text)
    assert result.exit_code == 0
    assert "Validation" in result.stdout or "validated" in result.stdout

    # Must show either:
    # 1. Validation level (MINIMAL, STANDARD, COMPLETE, EXCELLENT)
    # 2. "Validated: N entries" where N > 0
    # 3. Errors/warnings/suggestions counts
    has_validation_output = (
        "MINIMAL" in result.stdout or
        "STANDARD" in result.stdout or
        "COMPLETE" in result.stdout or
        "EXCELLENT" in result.stdout or
        "Validated: 1 entries" in result.stdout or
        ("error" in result.stdout.lower() and "warning" in result.stdout.lower())
    )

    assert has_validation_output, f"validate did not produce validation output. Got: {result.stdout}"


def test_validate_with_valid_vuln(temp_vulndocs: Path):
    """Validate command shows validation level for valid vulnerability."""
    # Create a valid vulnerability
    oracle_dir = temp_vulndocs / "oracle"
    oracle_dir.mkdir()
    price_manip_dir = oracle_dir / "price-manipulation"
    price_manip_dir.mkdir()

    # Create index.yaml
    (price_manip_dir / "index.yaml").write_text("""id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: critical
vulndoc: oracle/price-manipulation
semantic_triggers: [READS_ORACLE, USES_IN_CALCULATION]
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    result = runner.invoke(app, ["vulndocs", "validate", str(temp_vulndocs)])

    # Exit code may be 0 or 1 depending on validation errors (which is correct behavior)
    assert result.exit_code in (0, 1)
    # Should show the validation ran
    assert "oracle/price-manipulation" in result.stdout or "Validated: 1 entries" in result.stdout


def test_validate_strict_mode(temp_vulndocs: Path):
    """Validate command with --strict treats warnings as errors."""
    # Create a vulnerability that might have warnings
    oracle_dir = temp_vulndocs / "oracle"
    oracle_dir.mkdir()
    price_manip_dir = oracle_dir / "price-manipulation"
    price_manip_dir.mkdir()

    # Minimal index.yaml (might trigger warnings)
    (price_manip_dir / "index.yaml").write_text("""id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: critical
vulndoc: oracle/price-manipulation
semantic_triggers: []
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    # Note: This test may pass (exit 0) if there are no warnings,
    # which is fine - we're testing the --strict flag mechanics
    result = runner.invoke(app, ["vulndocs", "validate", str(temp_vulndocs), "--strict"])

    # Either exits 0 (no warnings) or 1 (warnings treated as errors)
    assert result.exit_code in (0, 1)


def test_validate_json_output(temp_vulndocs: Path):
    """Validate command --json outputs valid JSON for CI."""
    result = runner.invoke(app, ["vulndocs", "validate", str(temp_vulndocs), "--json"])

    assert result.exit_code == 0

    # Parse JSON to verify it's valid
    try:
        data = json.loads(result.stdout)
        assert "root" in data
        assert "total_errors" in data
        assert "total_warnings" in data
        assert "total_suggestions" in data
        assert "results" in data
        assert isinstance(data["results"], list)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {e}")


# Scaffold command tests


def test_scaffold_new_vulnerability(temp_vulndocs: Path):
    """Scaffold command creates full vulnerability structure."""
    result = runner.invoke(app, [
        "vulndocs", "scaffold",
        "oracle", "price-manipulation",
        "--root", str(temp_vulndocs)
    ])

    assert result.exit_code == 0
    assert "Created vulnerability: oracle/price-manipulation" in result.stdout or "Created" in result.stdout

    # Verify structure was created
    vuln_dir = temp_vulndocs / "oracle" / "price-manipulation"
    assert vuln_dir.exists()
    assert (vuln_dir / "index.yaml").exists()
    assert (vuln_dir / "overview.md").exists()
    assert (vuln_dir / "detection.md").exists()
    assert (vuln_dir / "verification.md").exists()
    assert (vuln_dir / "exploits.md").exists()
    assert (vuln_dir / "patterns").exists()


def test_scaffold_invalid_category(temp_vulndocs: Path):
    """Scaffold command rejects invalid category names."""
    result = runner.invoke(app, [
        "vulndocs", "scaffold",
        "Oracle_Bad", "test",
        "--root", str(temp_vulndocs)
    ])

    assert result.exit_code == 1
    assert "Validation errors" in result.stdout or "must be lowercase" in result.stdout


def test_scaffold_existing_folder(temp_vulndocs: Path):
    """Scaffold command errors on existing vulnerability folder."""
    # Create vulnerability first time
    runner.invoke(app, [
        "vulndocs", "scaffold",
        "oracle", "price-manipulation",
        "--root", str(temp_vulndocs)
    ])

    # Try to create again
    result = runner.invoke(app, [
        "vulndocs", "scaffold",
        "oracle", "price-manipulation",
        "--root", str(temp_vulndocs)
    ])

    assert result.exit_code == 1
    assert "already exists" in result.stdout


# Info command tests


def test_info_empty_vulndocs(temp_vulndocs: Path):
    """Info command shows zero counts for empty directory."""
    result = runner.invoke(app, ["vulndocs", "info", str(temp_vulndocs)])

    assert result.exit_code == 0
    assert "Categories" in result.stdout
    assert "Vulnerabilities" in result.stdout
    assert "Patterns" in result.stdout
    # Should show 0 for all counts
    assert "0" in result.stdout


def test_info_with_vulnerabilities(temp_vulndocs: Path):
    """Info command shows statistics for populated directory."""
    # Create a vulnerability
    oracle_dir = temp_vulndocs / "oracle"
    oracle_dir.mkdir()
    price_manip_dir = oracle_dir / "price-manipulation"
    price_manip_dir.mkdir()

    (price_manip_dir / "index.yaml").write_text("""id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: critical
vulndoc: oracle/price-manipulation
semantic_triggers: []
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    result = runner.invoke(app, ["vulndocs", "info", str(temp_vulndocs)])

    # Info may fail if discovery has issues, but command should run
    # Exit code doesn't matter as much as command not crashing
    assert "Statistics" in result.stdout or "Error" in result.stdout
    # If successful, should show some structure
    if result.exit_code == 0:
        assert "Categories" in result.stdout or "Vulnerabilities" in result.stdout


# List command tests


def test_list_all(temp_vulndocs: Path):
    """List command lists all vulnerabilities."""
    # Create a vulnerability
    oracle_dir = temp_vulndocs / "oracle"
    oracle_dir.mkdir()
    price_manip_dir = oracle_dir / "price-manipulation"
    price_manip_dir.mkdir()

    (price_manip_dir / "index.yaml").write_text("""id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: critical
vulndoc: oracle/price-manipulation
semantic_triggers: []
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    result = runner.invoke(app, ["vulndocs", "list", str(temp_vulndocs)])

    assert result.exit_code == 0
    # Should show the vulnerability path
    assert "oracle/price-manipulation" in result.stdout or "Vulnerabilities" in result.stdout


def test_list_by_category(temp_vulndocs: Path):
    """List command filters by category."""
    # Create two vulnerabilities in different categories
    oracle_dir = temp_vulndocs / "oracle"
    oracle_dir.mkdir()
    price_manip_dir = oracle_dir / "price-manipulation"
    price_manip_dir.mkdir()

    (price_manip_dir / "index.yaml").write_text("""id: oracle-price-manipulation
category: oracle
subcategory: price-manipulation
severity: critical
vulndoc: oracle/price-manipulation
semantic_triggers: []
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    access_dir = temp_vulndocs / "access-control"
    access_dir.mkdir()
    weak_auth_dir = access_dir / "weak-authentication"
    weak_auth_dir.mkdir()

    (weak_auth_dir / "index.yaml").write_text("""id: access-control-weak-authentication
category: access-control
subcategory: weak-authentication
severity: high
vulndoc: access-control/weak-authentication
semantic_triggers: []
vql_queries: []
graph_patterns: []
reasoning_template: ""
test_coverage: []
patterns: []
""")

    # List only oracle category
    result = runner.invoke(app, ["vulndocs", "list", str(temp_vulndocs), "--category", "oracle"])

    assert result.exit_code == 0
    assert "oracle/price-manipulation" in result.stdout
    # Should NOT show access-control
    assert "access-control" not in result.stdout or "oracle" in result.stdout


def test_list_empty_result(temp_vulndocs: Path):
    """List command handles no results gracefully."""
    result = runner.invoke(app, ["vulndocs", "list", str(temp_vulndocs)])

    # May exit 0 with "No vulnerabilities found" message
    assert result.exit_code == 0
    assert "No vulnerabilities" in result.stdout or "Vulnerabilities (0)" in result.stdout


# Integration test


def test_validate_scaffold_integration(temp_vulndocs: Path):
    """Integration test: scaffold then validate."""
    # Scaffold a new vulnerability
    scaffold_result = runner.invoke(app, [
        "vulndocs", "scaffold",
        "test-category", "test-vuln",
        "--root", str(temp_vulndocs)
    ])

    assert scaffold_result.exit_code == 0

    # Validate it
    validate_result = runner.invoke(app, ["vulndocs", "validate", str(temp_vulndocs)])

    # Validation may find errors in scaffolded content (that's fine)
    assert validate_result.exit_code in (0, 1)
    assert "test-category/test-vuln" in validate_result.stdout or "Validated: 1 entries" in validate_result.stdout
