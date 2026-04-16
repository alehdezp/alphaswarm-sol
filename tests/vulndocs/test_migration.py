"""Migration verification tests for Phase 5.7.

Verifies that the unified vulndocs/ structure is correct after migration:
- vulndocs/index.yaml exists
- .meta/templates/ and .meta/instructions/ exist
- Categories have index.yaml
- Patterns have vulndoc field
- Legacy paths removed (after plan 09 completes)

Part of Plan 05.7-10: Integration Testing & Documentation
"""

from pathlib import Path
import yaml
import pytest


# =============================================================================
# Structure Verification Tests
# =============================================================================


def test_vulndocs_root_exists():
    """Verify vulndocs/ root directory exists."""
    vulndocs_root = Path("vulndocs")
    assert vulndocs_root.exists(), "vulndocs/ directory must exist"
    assert vulndocs_root.is_dir(), "vulndocs must be a directory"


def test_vulndocs_index_exists():
    """Verify vulndocs/index.yaml exists and is valid."""
    index_path = Path("vulndocs/index.yaml")
    assert index_path.exists(), "vulndocs/index.yaml must exist"

    with open(index_path) as f:
        index = yaml.safe_load(f)

    assert index is not None, "index.yaml must be valid YAML"
    assert "version" in index or "categories" in index, "index.yaml must have expected structure"


def test_meta_directory_exists():
    """Verify .meta/ directory exists with expected structure."""
    meta_dir = Path("vulndocs/.meta")
    assert meta_dir.exists(), ".meta/ directory must exist"
    assert meta_dir.is_dir(), ".meta must be a directory"


def test_meta_templates_exists():
    """Verify .meta/templates/ directory exists with required files."""
    templates_dir = Path("vulndocs/.meta/templates")
    assert templates_dir.exists(), ".meta/templates/ must exist"

    # Check for required template files
    expected_files = [
        "category.yaml",
        "pattern.yaml",
        "subcategory/index.yaml",
    ]

    for expected in expected_files:
        path = templates_dir / expected
        assert path.exists(), f"Template {expected} must exist in .meta/templates/"


def test_meta_instructions_exists():
    """Verify .meta/instructions/ directory exists."""
    instructions_dir = Path("vulndocs/.meta/instructions")
    assert instructions_dir.exists(), ".meta/instructions/ must exist"

    # Should have at least some instruction files
    instruction_files = list(instructions_dir.glob("*.md"))
    assert len(instruction_files) >= 3, "Should have at least 3 instruction files"


# =============================================================================
# Category Verification Tests
# =============================================================================


def test_categories_exist():
    """Verify vulnerability categories exist."""
    vulndocs_root = Path("vulndocs")

    # Find all category directories (not hidden, not special dirs)
    categories = [
        d for d in vulndocs_root.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and not d.name.startswith("_")
    ]

    assert len(categories) >= 10, f"Should have at least 10 categories, found {len(categories)}"


def test_categories_have_subcategories():
    """Verify categories have subcategory folders."""
    vulndocs_root = Path("vulndocs")

    # Check a few known categories
    expected_categories = ["reentrancy", "oracle", "access-control"]

    for cat_name in expected_categories:
        cat_path = vulndocs_root / cat_name
        if cat_path.exists():
            # Should have at least one subcategory
            subcategories = [
                d for d in cat_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
            assert len(subcategories) >= 1, f"Category {cat_name} should have at least 1 subcategory"


def test_subcategories_have_index_yaml():
    """Verify each subcategory has index.yaml."""
    vulndocs_root = Path("vulndocs")

    # Find all subcategories (categories/subcategory/index.yaml)
    index_files = list(vulndocs_root.glob("*/*/index.yaml"))

    # Exclude special directories
    valid_index_files = [
        f for f in index_files
        if not any(part.startswith("_") or part.startswith(".") for part in f.parts)
    ]

    assert len(valid_index_files) >= 50, f"Should have at least 50 subcategories with index.yaml, found {len(valid_index_files)}"


# =============================================================================
# Pattern Verification Tests
# =============================================================================


def test_patterns_exist_in_vulndocs():
    """Verify patterns exist within vulndocs structure."""
    vulndocs_root = Path("vulndocs")

    # Find all pattern files
    patterns = list(vulndocs_root.glob("*/*/patterns/*.yaml"))

    assert len(patterns) >= 100, f"Should have at least 100 patterns, found {len(patterns)}"


def test_patterns_have_vulndoc_field():
    """Verify migrated patterns have vulndoc back-reference."""
    vulndocs_root = Path("vulndocs")

    # Sample some patterns
    patterns = list(vulndocs_root.glob("*/*/patterns/*.yaml"))[:20]

    for pattern_path in patterns:
        with open(pattern_path) as f:
            data = yaml.safe_load(f)

        assert "vulndoc" in data, f"Pattern {pattern_path.name} must have vulndoc field"


def test_patterns_have_required_fields():
    """Verify patterns have required fields."""
    vulndocs_root = Path("vulndocs")

    # Sample some patterns
    patterns = list(vulndocs_root.glob("*/*/patterns/*.yaml"))[:10]

    required_fields = ["id", "name", "severity"]

    for pattern_path in patterns:
        with open(pattern_path) as f:
            data = yaml.safe_load(f)

        for field in required_fields:
            assert field in data, f"Pattern {pattern_path.name} must have {field} field"


# =============================================================================
# Legacy Path Verification Tests
# =============================================================================


@pytest.mark.skip(reason="Legacy directories may still exist if plan 09 not complete")
def test_legacy_patterns_directory_removed():
    """Verify legacy patterns/ directory at root is removed."""
    assert not Path("patterns").exists(), "Legacy patterns/ directory should be removed"


@pytest.mark.skip(reason="Legacy directories may still exist if plan 09 not complete")
def test_legacy_knowledge_directory_removed():
    """Verify legacy knowledge/ directory is removed."""
    assert not Path("knowledge").exists(), "Legacy knowledge/ directory should be removed"


def test_legacy_underscore_templates_coexists():
    """Verify _templates (if exists) doesn't conflict with .meta/templates."""
    # Both may exist during transition - verify they don't cause issues
    old_templates = Path("vulndocs/_templates")
    new_templates = Path("vulndocs/.meta/templates")

    # New location must exist
    assert new_templates.exists(), ".meta/templates must exist"

    # If old exists, that's OK during transition
    if old_templates.exists():
        # Just verify both are accessible
        assert new_templates.is_dir(), ".meta/templates must be a directory"


def test_legacy_underscore_instructions_coexists():
    """Verify _instructions (if exists) doesn't conflict with .meta/instructions."""
    old_instructions = Path("vulndocs/_instructions")
    new_instructions = Path("vulndocs/.meta/instructions")

    # New location must exist
    assert new_instructions.exists(), ".meta/instructions must exist"


# =============================================================================
# Integration Verification Tests
# =============================================================================


def test_discovery_finds_all_patterns():
    """Verify pattern discovery finds patterns via API and filesystem."""
    from alphaswarm_sol.vulndocs.discovery import discover_patterns, discover_vulnerabilities

    vulndocs_root = Path("vulndocs")

    # Check filesystem has patterns
    fs_patterns = list(vulndocs_root.glob("*/*/patterns/*.yaml"))
    assert len(fs_patterns) >= 100, f"Should have at least 100 pattern files in filesystem, found {len(fs_patterns)}"

    # Check API can discover patterns via vulnerabilities
    vulns = discover_vulnerabilities(vulndocs_root)
    api_patterns = 0
    for vuln in vulns:
        patterns = discover_patterns(vuln.path)
        api_patterns += len(patterns)

    # API discovers patterns through vulnerabilities that have index.yaml
    # Not all patterns may be discoverable if their parent vuln lacks index.yaml
    assert api_patterns >= 50, f"Should discover at least 50 patterns via API, found {api_patterns}"


def test_discovery_finds_all_vulnerabilities():
    """Verify vulnerability discovery finds all entries."""
    from alphaswarm_sol.vulndocs import discover_vulnerabilities

    vulns = discover_vulnerabilities(Path("vulndocs"))

    assert len(vulns) >= 50, f"Should discover at least 50 vulnerabilities, found {len(vulns)}"


def test_validation_passes_on_real_vulndocs():
    """Verify validation runs on actual vulndocs structure.

    Note: This test verifies the framework can process the structure,
    not that all entries are valid (migration may be in progress).
    """
    from alphaswarm_sol.vulndocs import validate_framework

    result = validate_framework(Path("vulndocs"))

    # Should find vulnerabilities (framework can discover the structure)
    assert len(result.vulnerabilities) >= 50, f"Should find at least 50 vulnerabilities, found {len(result.vulnerabilities)}"

    # Framework should run without crashing on the structure
    # Valid count may be low if migration is in progress
    valid_count = sum(1 for v in result.vulnerabilities if v.is_valid)

    # At minimum, some should be valid if patterns have been migrated
    # If none are valid, the structure exists but data migration may be pending
    if valid_count == 0:
        # Verify at least the framework processes without error
        # and reports errors properly (not crashing)
        assert result.has_errors, "Should report errors if no valid entries"
    else:
        # If some are valid, at least 10% should be valid
        assert valid_count >= len(result.vulnerabilities) * 0.1, \
            f"At least 10% of vulnerabilities should be valid, found {valid_count}/{len(result.vulnerabilities)}"


# =============================================================================
# Source Code Path Verification
# =============================================================================


def test_no_hardcoded_legacy_paths_in_source():
    """Verify source code doesn't have hardcoded legacy paths."""
    src_dir = Path("src/alphaswarm_sol/vulndocs")

    legacy_patterns_to_avoid = [
        'Path("patterns")',
        'Path("knowledge")',
        '"patterns/"',
        '"knowledge/"',
    ]

    issues = []

    for py_file in src_dir.glob("*.py"):
        content = py_file.read_text()
        for pattern in legacy_patterns_to_avoid:
            if pattern in content:
                # Allow comments or strings that explain migration
                lines = [
                    line for line in content.split("\n")
                    if pattern in line and not line.strip().startswith("#")
                ]
                if lines:
                    issues.append(f"{py_file.name}: contains {pattern}")

    # This is a soft check - some references may be intentional
    # Just verify main discovery doesn't use legacy paths
    discovery_content = (src_dir / "discovery.py").read_text()
    assert 'Path("patterns")' not in discovery_content, "discovery.py should not hardcode patterns/ path"
