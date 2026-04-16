"""Tests for context merger and verifier.

Tests cover:
- Merger operations (success, failure, trimming, conservative defaults)
- Verifier validation (required fields, quality scoring, retry feedback)
- Integration (merge -> verify pipeline, retry loops)
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from alphaswarm_sol.agents.context import (
    ContextBundle,
    ContextMerger,
    ContextVerifier,
    RiskCategory,
    RiskProfile,
    VerificationError,
)
from alphaswarm_sol.agents.context.extractor import VulndocContextExtractor
from alphaswarm_sol.context.schema import ProtocolContextPack


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_protocol_pack():
    """Create a minimal protocol context pack for testing."""
    return ProtocolContextPack(
        protocol_name="TestProtocol",
        protocol_type="lending",
        roles=[],
        assumptions=[],
        invariants=[],
        offchain_inputs=[],
    )


@pytest.fixture
def extractor(tmp_path):
    """Create extractor with temporary vulndocs directory."""
    vulndocs_root = tmp_path / "vulndocs"
    vulndocs_root.mkdir()

    # Create a test vulndoc
    test_vuln = vulndocs_root / "reentrancy" / "classic"
    test_vuln.mkdir(parents=True)

    index_content = """name: Classic Reentrancy
category: reentrancy
severity: critical
reasoning_template: |
  1. Check for external calls before state updates
  2. Verify CEI pattern is followed
  3. Look for reentrancy guards
  4. Check callback execution flow
semantic_triggers:
  - TRANSFERS_VALUE_OUT
  - WRITES_USER_BALANCE
  - CALLS_EXTERNAL
vql_queries:
  - "FIND functions WHERE visibility = external AND has_external_call"
graph_patterns:
  - "R:bal->X:out->W:bal"
"""
    (test_vuln / "index.yaml").write_text(index_content)

    return VulndocContextExtractor(vulndocs_root=vulndocs_root)


@pytest.fixture
def merger(extractor):
    """Create context merger with test extractor."""
    return ContextMerger(
        extractor=extractor,
        default_token_budget=4000,
        max_token_budget=6000,
    )


@pytest.fixture
def verifier():
    """Create context verifier."""
    return ContextVerifier()


@pytest.fixture
def valid_bundle():
    """Create a valid context bundle for testing."""
    return ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI pattern\n2. Look for guards\n3. Verify state updates\n4. Test with actual calls\n5. Consider callback scenarios",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE has_external_call"],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=RiskProfile(
            access_risks=RiskCategory(present=True, confidence="certain"),
            timing_risks=RiskCategory(present=True, confidence="inferred"),
        ),
        protocol_name="TestProtocol",
        target_scope=["contracts/Test.sol"],
        token_estimate=2000,
    )


# =============================================================================
# Merger Tests
# =============================================================================


def test_merge_success_with_valid_inputs(merger, sample_protocol_pack):
    """Test successful merge with valid inputs."""
    result = merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
    )

    assert result.success is True
    assert result.bundle is not None
    assert result.bundle.vulnerability_class == "reentrancy/classic"
    assert result.bundle.protocol_name == "TestProtocol"
    assert "vulndoc" in result.sources_used
    assert "protocol_pack" in result.sources_used
    assert len(result.errors) == 0


def test_merge_applies_conservative_defaults(merger, sample_protocol_pack):
    """Test that unknown risks become present (conservative default)."""
    result = merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
    )

    assert result.success is True
    bundle = result.bundle

    # All unknown risks should be set to present=True
    for field in [
        "oracle_risks",
        "liquidity_risks",
        "access_risks",
        "upgrade_risks",
        "integration_risks",
        "timing_risks",
        "economic_risks",
        "governance_risks",
    ]:
        risk_cat = getattr(bundle.risk_profile, field)
        if risk_cat.confidence == "unknown":
            assert risk_cat.present is True, f"{field} should be present when unknown"


def test_merge_additional_context_appends(merger, sample_protocol_pack):
    """Test that additional context is merged correctly."""
    additional = {
        "vql_queries": ["FIND contracts WHERE has_delegatecall"],
        "graph_patterns": ["W:state->X:external"],
        "reasoning_notes": "Check for special case X",
    }

    result = merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
        additional_context=additional,
    )

    assert result.success is True
    bundle = result.bundle

    # Check VQL queries appended
    assert "FIND contracts WHERE has_delegatecall" in bundle.vql_queries

    # Check graph patterns appended
    assert "W:state->X:external" in bundle.graph_patterns

    # Check reasoning notes appended
    assert "Check for special case X" in bundle.reasoning_template

    # Check sources tracked
    assert "additional_context" in result.sources_used


def test_merge_trims_when_over_budget(merger, sample_protocol_pack, tmp_path):
    """Test that merger trims content when over budget."""
    # Create vulndoc with lots of content to exceed budget
    vulndocs_root = tmp_path / "vulndocs_large"
    vulndocs_root.mkdir()

    test_vuln = vulndocs_root / "reentrancy" / "classic"
    test_vuln.mkdir(parents=True)

    # Create index with LOTS of content to exceed 6000 token budget
    # Rough estimate: 4 chars = 1 token, so 24000+ chars = 6000+ tokens
    large_template = "1. " + "Check this pattern with detailed analysis. " * 2000
    large_queries = [f"FIND query {i} with detailed conditions" for i in range(200)]
    large_patterns = [f"Pattern-{i}:very:long:pattern:description" for i in range(200)]

    index_content = f"""name: Classic Reentrancy
category: reentrancy
severity: critical
reasoning_template: |
  {large_template}
semantic_triggers:
  - TRANSFERS_VALUE_OUT
  - WRITES_USER_BALANCE
vql_queries:
{chr(10).join(f"  - {q}" for q in large_queries)}
graph_patterns:
{chr(10).join(f"  - {p}" for p in large_patterns)}
"""
    (test_vuln / "index.yaml").write_text(index_content)

    # Create new extractor and merger with large content
    large_extractor = VulndocContextExtractor(vulndocs_root=vulndocs_root)
    large_merger = ContextMerger(
        extractor=large_extractor,
        default_token_budget=4000,
        max_token_budget=6000,
    )

    result = large_merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
    )

    assert result.success is True
    assert result.trimmed is True
    assert len(result.warnings) > 0
    assert "Trimmed" in result.warnings[0]


def test_merge_failure_invalid_vulndoc(merger, sample_protocol_pack):
    """Test merge failure with missing vulndoc."""
    result = merger.merge(
        vuln_class="nonexistent/vuln",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
    )

    assert result.success is False
    assert result.bundle is None
    assert len(result.errors) > 0
    assert "VulnDoc not found" in result.errors[0]


def test_merge_result_tracks_sources(merger, sample_protocol_pack):
    """Test that merge result tracks all sources used."""
    result = merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
        additional_context={"vql_queries": ["test"]},
    )

    assert result.success is True
    assert "vulndoc" in result.sources_used
    assert "protocol_pack" in result.sources_used
    assert "additional_context" in result.sources_used


# =============================================================================
# Verifier Tests
# =============================================================================


def test_verify_valid_bundle_passes(verifier, valid_bundle):
    """Test that valid bundle passes verification."""
    result = verifier.verify(valid_bundle)

    assert result.valid is True
    assert len(result.errors) == 0
    assert result.quality_score > 0.8
    assert result.feedback_for_retry is None


def test_verify_missing_field_fails(verifier, valid_bundle):
    """Test that missing required field fails verification."""
    # Remove required field
    valid_bundle.reasoning_template = ""

    result = verifier.verify(valid_bundle)

    assert result.valid is False
    assert len(result.errors) > 0
    assert any("reasoning_template" in err.field for err in result.errors)
    assert result.feedback_for_retry is not None


def test_verify_short_template_fails(verifier, valid_bundle):
    """Test that too-short template fails verification."""
    valid_bundle.reasoning_template = "Short"  # < 100 chars

    result = verifier.verify(valid_bundle)

    assert result.valid is False
    assert len(result.errors) > 0
    assert any(
        err.field == "reasoning_template" and err.error_type == "too_short"
        for err in result.errors
    )


def test_verify_invalid_operations_warns(verifier, valid_bundle):
    """Test that invalid semantic operations produce warnings."""
    valid_bundle.semantic_triggers = ["INVALID_OPERATION", "ANOTHER_BAD_ONE"]

    result = verifier.verify(valid_bundle)

    # Should still be valid (warnings only)
    assert result.valid is True
    assert len(result.warnings) > 0
    assert any(
        "INVALID_OPERATION" in warn.message for warn in result.warnings
    )


def test_verify_many_unknown_risks_warns(verifier, valid_bundle):
    """Test that many unknown risks produce warning."""
    # Set all risks to unknown
    for field in [
        "oracle_risks",
        "liquidity_risks",
        "access_risks",
        "upgrade_risks",
        "integration_risks",
        "timing_risks",
        "economic_risks",
        "governance_risks",
    ]:
        setattr(
            valid_bundle.risk_profile,
            field,
            RiskCategory(present=False, confidence="unknown"),
        )

    result = verifier.verify(valid_bundle)

    assert result.valid is True  # Warnings don't block
    assert len(result.warnings) > 0
    assert any(
        "risk categories are unknown" in warn.message for warn in result.warnings
    )


def test_verify_quality_score_calculation(verifier, valid_bundle):
    """Test quality score calculation with errors and warnings."""
    # Create bundle with multiple issues
    valid_bundle.reasoning_template = "Short"  # Error: too short
    valid_bundle.semantic_triggers = ["INVALID_OP"]  # Warning: invalid op

    result = verifier.verify(valid_bundle)

    # Quality score should be reduced
    # Base 1.0 - (1+ errors * 0.25) - (3+ warnings * 0.05) = ~0.60
    assert result.quality_score < 1.0
    assert result.quality_score >= 0.55  # Allow tolerance for multiple warnings


def test_verify_retry_feedback_format(verifier, valid_bundle):
    """Test that retry feedback is formatted correctly."""
    valid_bundle.reasoning_template = ""  # Missing required field
    valid_bundle.semantic_triggers = ["INVALID_OP"]  # Invalid operation

    result = verifier.verify(valid_bundle)

    assert result.valid is False
    assert result.feedback_for_retry is not None

    feedback = result.feedback_for_retry
    assert "ERRORS (must fix):" in feedback
    assert "WARNINGS (should fix):" in feedback
    assert "[reasoning_template]" in feedback
    assert "[semantic_triggers]" in feedback


def test_verify_step_structure_check(verifier, valid_bundle):
    """Test that numbered steps are detected."""
    # Template with numbered steps
    valid_bundle.reasoning_template = "1. First step\n2. Second step\n3. Third step\n" + "x" * 100

    result = verifier.verify(valid_bundle)

    # Should pass without step structure warning
    assert result.valid is True
    assert not any(
        "numbered steps" in warn.message for warn in result.warnings
    )

    # Template without numbered steps
    valid_bundle.reasoning_template = "Do this and that and the other thing\n" * 10

    result = verifier.verify(valid_bundle)

    # Should have warning about step structure
    assert result.valid is True
    assert any(
        "numbered steps" in warn.message for warn in result.warnings
    )


def test_verify_empty_semantic_triggers_fails(verifier, valid_bundle):
    """Test that empty semantic triggers fails verification."""
    valid_bundle.semantic_triggers = []

    result = verifier.verify(valid_bundle)

    assert result.valid is False
    assert any(
        err.field == "semantic_triggers" and err.error_type == "missing"
        for err in result.errors
    )


# =============================================================================
# Integration Tests
# =============================================================================


def test_merge_then_verify_pipeline(merger, verifier, sample_protocol_pack):
    """Test full merge -> verify pipeline."""
    # Step 1: Merge
    merge_result = merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
    )

    assert merge_result.success is True

    # Step 2: Verify
    verify_result = verifier.verify(merge_result.bundle)

    assert verify_result.valid is True
    assert verify_result.quality_score > 0.7


def test_retry_loop_with_feedback(merger, verifier, sample_protocol_pack):
    """Test retry loop with verification feedback."""
    # First attempt - will have issues
    merge_result = merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
    )

    assert merge_result.success is True
    bundle = merge_result.bundle

    # Introduce error
    bundle.reasoning_template = "Too short"

    # Verify - should fail
    verify_result = verifier.verify(bundle)
    assert verify_result.valid is False
    assert verify_result.feedback_for_retry is not None

    # Simulate retry: fix the issue
    bundle.reasoning_template = "1. Check this\n2. Verify that\n3. Look for pattern\n4. Confirm vulnerability\n5. Document finding\n" + "x" * 50

    # Verify again - should pass
    verify_result = verifier.verify(bundle)
    assert verify_result.valid is True


def test_merge_with_additional_and_verify(merger, verifier, sample_protocol_pack):
    """Test merge with additional context then verify."""
    additional = {
        "vql_queries": ["FIND functions WHERE has_modifier = nonReentrant"],
        "reasoning_notes": "Pay special attention to callback functions",
    }

    merge_result = merger.merge(
        vuln_class="reentrancy/classic",
        protocol_pack=sample_protocol_pack,
        target_scope=["contracts/Pool.sol"],
        additional_context=additional,
    )

    assert merge_result.success is True
    assert "additional_context" in merge_result.sources_used

    verify_result = verifier.verify(merge_result.bundle)
    assert verify_result.valid is True
