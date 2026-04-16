"""Tests for VulnDocs Progressive Validation.

Tests cover all validation levels, error handling, warnings, and suggestions.

Part of Plan 05.4-03: Progressive Validation Framework
"""

from pathlib import Path

import pytest
import yaml

from alphaswarm_sol.vulndocs.types import ValidationLevel
from alphaswarm_sol.vulndocs.validation import (
    validate_vulnerability,
    validate_framework,
    suggest_research,
    ValidationResult,
    FrameworkValidationResult,
)
from alphaswarm_sol.vulndocs.schema import VulnDocIndex


# =============================================================================
# Test Validation Levels
# =============================================================================


def test_minimal_level_index_only(tmp_path):
    """Test MINIMAL level with just valid index.yaml."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create minimal valid index.yaml
    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.MINIMAL
    assert len(result.errors) == 0


def test_standard_level_with_md(tmp_path):
    """Test STANDARD level with index.yaml + overview.md."""
    vuln_dir = tmp_path / "reentrancy" / "classic"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml
    index_data = {
        "id": "reentrancy-classic",
        "category": "reentrancy",
        "subcategory": "classic",
        "severity": "high",
        "vulndoc": "reentrancy/classic",
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create overview.md
    (vuln_dir / "overview.md").write_text("# Classic Reentrancy\n\nOverview here.")

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.STANDARD
    assert len(result.errors) == 0


def test_complete_level_all_files(tmp_path):
    """Test COMPLETE level with all recommended files."""
    vuln_dir = tmp_path / "access-control" / "weak-auth"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml
    index_data = {
        "id": "access-control-weak-auth",
        "category": "access-control",
        "subcategory": "weak-auth",
        "severity": "high",
        "vulndoc": "access-control/weak-auth",
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create all recommended files
    (vuln_dir / "overview.md").write_text("# Overview")
    (vuln_dir / "detection.md").write_text("# Detection")
    (vuln_dir / "verification.md").write_text("# Verification")

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.COMPLETE
    assert len(result.errors) == 0


def test_excellent_level_with_patterns(tmp_path):
    """Test EXCELLENT level with patterns and test coverage."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml with test coverage
    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
        "test_coverage": ["tests/test_oracle_lens.py"],
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create all recommended files
    (vuln_dir / "overview.md").write_text("# Overview")
    (vuln_dir / "detection.md").write_text("# Detection")
    (vuln_dir / "verification.md").write_text("# Verification")

    # Create patterns folder with a pattern
    patterns_dir = vuln_dir / "patterns"
    patterns_dir.mkdir()

    pattern_data = {
        "id": "oracle-001-twap",
        "name": "Missing TWAP Protection",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
    }

    with open(patterns_dir / "oracle-001-twap.yaml", "w") as f:
        yaml.dump(pattern_data, f)

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.EXCELLENT
    assert len(result.errors) == 0


# =============================================================================
# Test Error Handling
# =============================================================================


def test_missing_index_yaml(tmp_path):
    """Test error when index.yaml is missing."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    result = validate_vulnerability(vuln_dir)

    assert not result.is_valid
    assert result.level is None
    assert len(result.errors) == 1
    assert "Missing required file: index.yaml" in result.errors[0]


def test_invalid_index_yaml(tmp_path):
    """Test error when index.yaml is malformed."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create invalid YAML
    (vuln_dir / "index.yaml").write_text("invalid: yaml: content: [unclosed")

    result = validate_vulnerability(vuln_dir)

    assert not result.is_valid
    assert result.level is None
    assert len(result.errors) == 1
    assert "Invalid YAML" in result.errors[0]


def test_missing_required_fields(tmp_path):
    """Test error when the only required field (id) is missing."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml missing the required 'id' field
    index_data = {
        "parent_category": "oracle",
        # Missing id - the only truly required field
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    result = validate_vulnerability(vuln_dir)

    assert not result.is_valid
    assert result.level is None
    assert len(result.errors) > 0
    # Should have error for missing 'id' field
    assert any("id" in err for err in result.errors)


def test_empty_index_yaml(tmp_path):
    """Test error when index.yaml is empty."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create empty file
    (vuln_dir / "index.yaml").write_text("")

    result = validate_vulnerability(vuln_dir)

    assert not result.is_valid
    assert result.level is None
    assert len(result.errors) == 1
    assert "index.yaml is empty" in result.errors[0]


# =============================================================================
# Test Warnings and Suggestions
# =============================================================================


def test_warns_on_missing_detection(tmp_path):
    """Test warning when detection.md is missing."""
    vuln_dir = tmp_path / "reentrancy" / "classic"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml
    index_data = {
        "id": "reentrancy-classic",
        "category": "reentrancy",
        "subcategory": "classic",
        "severity": "high",
        "vulndoc": "reentrancy/classic",
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create overview but not detection
    (vuln_dir / "overview.md").write_text("# Overview")

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.STANDARD
    # No warnings at STANDARD level (just 1 md file is enough)


def test_warns_on_missing_overview_at_standard(tmp_path):
    """Test warning when overview.md is missing at STANDARD level."""
    vuln_dir = tmp_path / "reentrancy" / "classic"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml
    index_data = {
        "id": "reentrancy-classic",
        "category": "reentrancy",
        "subcategory": "classic",
        "severity": "high",
        "vulndoc": "reentrancy/classic",
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create detection.md but not overview
    (vuln_dir / "detection.md").write_text("# Detection")

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.STANDARD
    assert result.has_warnings
    assert any("overview.md" in w for w in result.warnings)


def test_suggests_phase7_fields(tmp_path):
    """Test suggestions for empty Phase 7 fields."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml with empty Phase 7 fields
    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
        # Phase 7 fields empty
        "semantic_triggers": [],
        "vql_queries": [],
        "graph_patterns": [],
        "reasoning_template": "",
        "related_exploits": [],
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.has_suggestions
    # Should suggest comprehensive research since 5 fields are empty
    assert any("vulndocs research" in s for s in result.suggestions)


def test_suggests_pattern_creation(tmp_path):
    """Test suggestion for missing patterns at COMPLETE level."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml
    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create all recommended files
    (vuln_dir / "overview.md").write_text("# Overview")
    (vuln_dir / "detection.md").write_text("# Detection")
    (vuln_dir / "verification.md").write_text("# Verification")

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.COMPLETE
    assert result.has_suggestions
    assert any("patterns" in s for s in result.suggestions)


# =============================================================================
# Test Framework Validation
# =============================================================================


def test_validate_empty_framework(tmp_path):
    """Test framework validation with empty vulndocs."""
    vulndocs_dir = tmp_path / "vulndocs"
    vulndocs_dir.mkdir()

    result = validate_framework(vulndocs_dir)

    assert not result.has_errors
    assert len(result.vulnerabilities) == 0
    assert result.summary["total"] == 0


def test_validate_framework_with_vulns(tmp_path):
    """Test framework validation with multiple vulnerabilities."""
    vulndocs_dir = tmp_path / "vulndocs"
    vulndocs_dir.mkdir()

    # Create two vulnerabilities
    for cat, subcat, severity in [
        ("oracle", "price-manipulation", "critical"),
        ("reentrancy", "classic", "high"),
    ]:
        vuln_dir = vulndocs_dir / cat / subcat
        vuln_dir.mkdir(parents=True)

        index_data = {
            "id": f"{cat}-{subcat}",
            "category": cat,
            "subcategory": subcat,
            "severity": severity,
            "vulndoc": f"{cat}/{subcat}",
        }

        with open(vuln_dir / "index.yaml", "w") as f:
            yaml.dump(index_data, f)

    result = validate_framework(vulndocs_dir)

    assert not result.has_errors
    assert len(result.vulnerabilities) == 2
    assert result.summary["total"] == 2
    assert result.summary["minimal"] == 2


def test_validate_framework_with_errors(tmp_path):
    """Test framework validation with errors in some vulnerabilities."""
    vulndocs_dir = tmp_path / "vulndocs"
    vulndocs_dir.mkdir()

    # Create one valid vulnerability
    vuln1_dir = vulndocs_dir / "oracle" / "price-manipulation"
    vuln1_dir.mkdir(parents=True)

    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
    }

    with open(vuln1_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create one vulnerability with invalid index.yaml (missing required 'id')
    vuln2_dir = vulndocs_dir / "reentrancy" / "classic"
    vuln2_dir.mkdir(parents=True)

    # Invalid index - missing the only required field (id)
    invalid_index = {
        "parent_category": "reentrancy",
        # Missing id - the only required field
    }

    with open(vuln2_dir / "index.yaml", "w") as f:
        yaml.dump(invalid_index, f)

    result = validate_framework(vulndocs_dir)

    assert result.has_errors
    assert len(result.vulnerabilities) == 2
    assert result.summary["errors"] == 1
    assert result.summary["minimal"] == 1


# =============================================================================
# Test suggest_research Function
# =============================================================================


def test_suggest_research_empty_triggers():
    """Test research suggestion for empty semantic_triggers."""
    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
        "semantic_triggers": [],
    }

    index = VulnDocIndex.model_validate(index_data)
    suggestions = suggest_research(index, Path("/fake/path"))

    assert len(suggestions) > 0
    assert any("semantic_triggers" in s for s in suggestions)


def test_suggest_research_comprehensive():
    """Test comprehensive research suggestion when multiple fields empty."""
    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
        "semantic_triggers": [],
        "vql_queries": [],
        "graph_patterns": [],
        "reasoning_template": "",
        "related_exploits": [],
    }

    index = VulnDocIndex.model_validate(index_data)
    suggestions = suggest_research(index, Path("/fake/path"))

    # Should suggest comprehensive research
    assert any("vulndocs research" in s for s in suggestions)


# =============================================================================
# Test Edge Cases
# =============================================================================


def test_validation_with_patterns_no_coverage(tmp_path):
    """Test COMPLETE level when patterns exist but no test coverage."""
    vuln_dir = tmp_path / "oracle" / "price-manipulation"
    vuln_dir.mkdir(parents=True)

    # Create index.yaml without test coverage
    index_data = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
        "test_coverage": [],
    }

    with open(vuln_dir / "index.yaml", "w") as f:
        yaml.dump(index_data, f)

    # Create all recommended files
    (vuln_dir / "overview.md").write_text("# Overview")
    (vuln_dir / "detection.md").write_text("# Detection")
    (vuln_dir / "verification.md").write_text("# Verification")

    # Create patterns folder with a pattern
    patterns_dir = vuln_dir / "patterns"
    patterns_dir.mkdir()

    pattern_data = {
        "id": "oracle-001-twap",
        "name": "Missing TWAP Protection",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
    }

    with open(patterns_dir / "oracle-001-twap.yaml", "w") as f:
        yaml.dump(pattern_data, f)

    result = validate_vulnerability(vuln_dir)

    assert result.is_valid
    assert result.level == ValidationLevel.COMPLETE  # Not EXCELLENT
    assert result.has_suggestions
    assert any("test_coverage" in s for s in result.suggestions)


def test_validation_level_summary(tmp_path):
    """Test summary counts across different validation levels."""
    vulndocs_dir = tmp_path / "vulndocs"
    vulndocs_dir.mkdir()

    # Create vulnerabilities at different levels
    levels_data = [
        ("minimal", False, False, False),
        ("standard", True, False, False),
        ("complete", True, True, False),
        ("excellent", True, True, True),
    ]

    for i, (level_name, has_md, has_all, has_pattern) in enumerate(levels_data):
        vuln_dir = vulndocs_dir / f"cat{i}" / f"sub{i}"
        vuln_dir.mkdir(parents=True)

        index_data = {
            "id": f"cat{i}-sub{i}",
            "category": f"cat{i}",
            "subcategory": f"sub{i}",
            "severity": "medium",
            "vulndoc": f"cat{i}/sub{i}",
        }

        if level_name == "excellent":
            index_data["test_coverage"] = ["tests/test.py"]

        with open(vuln_dir / "index.yaml", "w") as f:
            yaml.dump(index_data, f)

        if has_md:
            (vuln_dir / "overview.md").write_text("# Overview")

        if has_all:
            (vuln_dir / "detection.md").write_text("# Detection")
            (vuln_dir / "verification.md").write_text("# Verification")

        if has_pattern:
            patterns_dir = vuln_dir / "patterns"
            patterns_dir.mkdir()
            pattern_data = {
                "id": f"pattern-{i}",
                "name": f"Pattern {i}",
                "severity": "medium",
                "vulndoc": f"cat{i}/sub{i}",
            }
            with open(patterns_dir / f"pattern-{i}.yaml", "w") as f:
                yaml.dump(pattern_data, f)

    result = validate_framework(vulndocs_dir)

    summary = result.summary
    assert summary["total"] == 4
    assert summary["minimal"] == 1
    assert summary["standard"] == 1
    assert summary["complete"] == 1
    assert summary["excellent"] == 1
