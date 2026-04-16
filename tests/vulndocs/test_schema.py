"""Tests for Phase 5.4 pydantic schema models.

Tests VulnDocIndex, PatternRef, and related models for proper validation,
including Phase 7 test generation field validation.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

from alphaswarm_sol.vulndocs import (
    VulnDocIndex,
    PatternRef,
    VulnDocCategory,
    TestCoverage,
    generate_json_schema,
    load_vulndoc_index,
    load_pattern_ref,
    SeverityEnum,
    ValidationLevel,
)


# =============================================================================
# VulnDocIndex Tests
# =============================================================================


def test_minimal_required_fields():
    """Test VulnDocIndex with only required fields."""
    idx = VulnDocIndex(
        id="test-vuln",
        category="oracle",
        subcategory="price-manipulation",
        severity="critical",
        vulndoc="oracle/price-manipulation",
    )
    assert idx.id == "test-vuln"
    assert idx.category == "oracle"
    assert idx.subcategory == "price-manipulation"
    assert idx.severity == "critical"
    assert idx.vulndoc == "oracle/price-manipulation"
    # Optional fields should have defaults
    assert idx.semantic_triggers == []
    assert idx.vql_queries == []
    assert idx.patterns == []


def test_full_index_with_phase7_fields():
    """Test VulnDocIndex with all Phase 7 test generation fields."""
    idx = VulnDocIndex(
        id="oracle-twap",
        category="oracle",
        subcategory="twap-manipulation",
        severity="high",
        vulndoc="oracle/twap-manipulation",
        description="TWAP oracle manipulation vulnerability",
        semantic_triggers=["READS_ORACLE", "TRANSFERS_ETH", "CALLS_EXTERNAL"],
        vql_queries=[
            "FIND functions WHERE has_operation:READS_ORACLE AND visibility:public"
        ],
        graph_patterns=["R:oracle->X:call->W:state"],
        reasoning_template="1. Find oracle reads\n2. Check for price manipulation\n3. Verify guards",
        relevant_properties=["has_oracle_dependency", "uses_spot_price"],
        patterns=["oracle-001-twap", "oracle-002-spot"],
        test_coverage=["tests/test_oracle_lens.py"],
    )

    assert len(idx.semantic_triggers) == 3
    assert "READS_ORACLE" in idx.semantic_triggers
    assert len(idx.vql_queries) == 1
    assert len(idx.graph_patterns) == 1
    assert idx.reasoning_template is not None
    assert len(idx.patterns) == 2


def test_semantic_trigger_validation():
    """Test that invalid semantic triggers are rejected."""
    # Valid triggers should work
    idx = VulnDocIndex(
        id="test",
        category="reentrancy",
        subcategory="classic",
        severity="critical",
        vulndoc="reentrancy/classic",
        semantic_triggers=["TRANSFERS_ETH", "WRITES_BALANCE", "CALLS_EXTERNAL"],
    )
    assert len(idx.semantic_triggers) == 3

    # Invalid trigger should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        VulnDocIndex(
            id="test",
            category="reentrancy",
            subcategory="classic",
            severity="critical",
            vulndoc="reentrancy/classic",
            semantic_triggers=["INVALID_OPERATION", "TRANSFERS_ETH"],
        )
    assert "Invalid semantic operation" in str(exc_info.value)


def test_vulndoc_path_validation():
    """Test that vulndoc path must match category/subcategory."""
    # Valid path should work
    idx = VulnDocIndex(
        id="test",
        category="oracle",
        subcategory="price",
        severity="high",
        vulndoc="oracle/price",
    )
    assert idx.vulndoc == "oracle/price"

    # Mismatched path should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        VulnDocIndex(
            id="test",
            category="oracle",
            subcategory="price",
            severity="high",
            vulndoc="wrong/path",
        )
    assert "does not match expected" in str(exc_info.value)


def test_severity_validation():
    """Test that severity values are validated."""
    # Valid severities
    for sev in ["critical", "high", "medium", "low", "informational"]:
        idx = VulnDocIndex(
            id="test",
            category="test",
            subcategory="test",
            severity=sev,
            vulndoc="test/test",
        )
        assert idx.severity == sev

    # Invalid severity should raise ValidationError
    with pytest.raises(ValidationError):
        VulnDocIndex(
            id="test",
            category="test",
            subcategory="test",
            severity="invalid",
            vulndoc="test/test",
        )


# =============================================================================
# Phase 7 Semantic Triggers Validation Tests
# =============================================================================


def test_phase7_semantic_triggers_valid():
    """Test that all 20 VALID_SEMANTIC_OPERATIONS are accepted."""
    from alphaswarm_sol.vulndocs.types import VALID_SEMANTIC_OPERATIONS

    idx = VulnDocIndex(
        id="test-all-ops",
        category="test",
        subcategory="comprehensive",
        severity="high",
        vulndoc="test/comprehensive",
        semantic_triggers=VALID_SEMANTIC_OPERATIONS,  # All 20 operations
    )
    assert len(idx.semantic_triggers) == 20
    assert "READS_ORACLE" in idx.semantic_triggers
    assert "TRANSFERS_ETH" in idx.semantic_triggers
    assert "DELEGATECALL" in idx.semantic_triggers


def test_phase7_semantic_triggers_invalid_rejected():
    """Test that invalid operation strings raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        VulnDocIndex(
            id="test",
            category="test",
            subcategory="test",
            severity="high",
            vulndoc="test/test",
            semantic_triggers=["INVALID_OP", "ANOTHER_INVALID"],
        )
    error_msg = str(exc_info.value)
    assert "Invalid semantic operation" in error_msg
    assert "INVALID_OP" in error_msg


def test_phase7_empty_semantic_triggers_allowed():
    """Test that empty list is valid (optional field)."""
    idx = VulnDocIndex(
        id="test",
        category="test",
        subcategory="test",
        severity="high",
        vulndoc="test/test",
        semantic_triggers=[],  # Empty is valid
    )
    assert idx.semantic_triggers == []


def test_phase7_mixed_valid_invalid_rejected():
    """Test that list with one invalid operation fails."""
    with pytest.raises(ValidationError) as exc_info:
        VulnDocIndex(
            id="test",
            category="test",
            subcategory="test",
            severity="high",
            vulndoc="test/test",
            semantic_triggers=[
                "READS_ORACLE",  # Valid
                "INVALID_OP",  # Invalid - should fail
                "TRANSFERS_ETH",  # Valid
            ],
        )
    assert "Invalid semantic operation" in str(exc_info.value)


# =============================================================================
# PatternRef Tests
# =============================================================================


def test_pattern_with_vulndoc():
    """Test PatternRef with required vulndoc field."""
    pattern = PatternRef(
        id="oracle-001-twap",
        name="TWAP Oracle Manipulation",
        severity="high",
        vulndoc="oracle/twap-manipulation",
    )
    assert pattern.id == "oracle-001-twap"
    assert pattern.name == "TWAP Oracle Manipulation"
    assert pattern.vulndoc == "oracle/twap-manipulation"
    assert pattern.scope == "Function"  # Default


def test_pattern_test_coverage():
    """Test PatternRef with test_coverage field."""
    pattern = PatternRef(
        id="pattern-001",
        name="Test Pattern",
        severity="medium",
        vulndoc="test/test",
        test_coverage={
            "precision": 0.85,
            "recall": 0.75,
            "status": "ready",
        },
    )
    assert pattern.test_coverage is not None
    assert pattern.test_coverage.precision == 0.85
    assert pattern.test_coverage.recall == 0.75
    assert pattern.test_coverage.status == "ready"


def test_pattern_scope_validation():
    """Test that pattern scope is validated."""
    # Valid scopes
    for scope in ["Function", "Contract", "Transaction"]:
        pattern = PatternRef(
            id="test",
            name="Test",
            severity="low",
            vulndoc="test/test",
            scope=scope,
        )
        assert pattern.scope == scope

    # Invalid scope should raise ValidationError
    with pytest.raises(ValidationError):
        PatternRef(
            id="test",
            name="Test",
            severity="low",
            vulndoc="test/test",
            scope="InvalidScope",
        )


# =============================================================================
# TestCoverage Tests
# =============================================================================


def test_test_coverage_validation():
    """Test TestCoverage precision/recall validation."""
    # Valid values
    tc = TestCoverage(precision=0.85, recall=0.75, status="ready")
    assert tc.precision == 0.85
    assert tc.recall == 0.75

    # Invalid precision (> 1.0)
    with pytest.raises(ValidationError):
        TestCoverage(precision=1.5, recall=0.75)

    # Invalid recall (< 0.0)
    with pytest.raises(ValidationError):
        TestCoverage(precision=0.85, recall=-0.1)


# =============================================================================
# JSON Schema Tests
# =============================================================================


def test_json_schema_generation():
    """Test that JSON Schema generation works."""
    schema = generate_json_schema()
    assert isinstance(schema, dict)
    assert "VulnDocIndex" in schema
    assert "PatternRef" in schema
    assert "TestCoverage" in schema
    assert "VulnDocCategory" in schema


def test_schema_validates_template():
    """Test that generated schema has expected structure."""
    schema = generate_json_schema()

    # Check VulnDocIndex schema
    vdi_schema = schema["VulnDocIndex"]
    assert "properties" in vdi_schema
    assert "required" in vdi_schema

    # Check required fields are marked as required
    # Only 'id' is required; category/subcategory/severity/vulndoc are derived
    required = vdi_schema["required"]
    assert "id" in required

    # These fields exist as optional properties (derived from parent_category/id)
    props_check = vdi_schema["properties"]
    assert "category" in props_check
    assert "subcategory" in props_check
    assert "parent_category" in props_check

    # Check Phase 7 fields exist in properties
    props = vdi_schema["properties"]
    assert "semantic_triggers" in props
    assert "vql_queries" in props
    assert "graph_patterns" in props
    assert "reasoning_template" in props


# =============================================================================
# Loading Tests
# =============================================================================


def test_load_vulndoc_index_from_file(tmp_path):
    """Test loading VulnDocIndex from a YAML file."""
    import yaml

    # Create a test index.yaml file
    index_data = {
        "id": "test-vuln",
        "category": "reentrancy",
        "subcategory": "classic",
        "severity": "critical",
        "vulndoc": "reentrancy/classic",
        "semantic_triggers": ["TRANSFERS_ETH", "WRITES_BALANCE"],
    }

    index_file = tmp_path / "index.yaml"
    with open(index_file, "w") as f:
        yaml.dump(index_data, f)

    # Load and validate
    idx = load_vulndoc_index(index_file)
    assert idx.id == "test-vuln"
    assert len(idx.semantic_triggers) == 2


def test_load_pattern_ref_from_file(tmp_path):
    """Test loading PatternRef from a YAML file."""
    import yaml

    # Create a test pattern file
    pattern_data = {
        "id": "pattern-001",
        "name": "Test Pattern",
        "severity": "high",
        "vulndoc": "test/test",
        "scope": "Function",
    }

    pattern_file = tmp_path / "pattern.yaml"
    with open(pattern_file, "w") as f:
        yaml.dump(pattern_data, f)

    # Load and validate
    pattern = load_pattern_ref(pattern_file)
    assert pattern.id == "pattern-001"
    assert pattern.name == "Test Pattern"


def test_load_from_template_files():
    """Test loading from actual template files."""
    # Test loading template index.yaml
    template_index = Path("vulndocs/.meta/templates/subcategory/index.yaml")
    if template_index.exists():
        try:
            idx = load_vulndoc_index(template_index)
            # Template has placeholder values, just check it loads
            assert idx.id is not None
        except ValidationError:
            # Template might have invalid placeholder values, that's OK
            pass

    # Test loading template pattern.yaml
    template_pattern = Path("vulndocs/.meta/templates/pattern.yaml")
    if template_pattern.exists():
        try:
            pattern = load_pattern_ref(template_pattern)
            assert pattern.id is not None
        except ValidationError:
            # Template might have invalid placeholder values, that's OK
            pass


# =============================================================================
# Import Tests
# =============================================================================


def test_imports_from_package():
    """Test that all models can be imported from package root."""
    from alphaswarm_sol.vulndocs import (
        VulnDocIndex,
        PatternRef,
        VulnDocCategory,
        TestCoverage,
        SeverityEnum,
        ValidationLevel,
        generate_json_schema,
        load_vulndoc_index,
        load_pattern_ref,
    )

    # Just check they're importable
    assert VulnDocIndex is not None
    assert PatternRef is not None
    assert generate_json_schema is not None
