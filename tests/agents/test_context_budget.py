"""Tests for BudgetPolicy and budget enforcement in context extraction.

Phase 5.10-06: Token budget policy tests.

Tests:
- BudgetPolicy pass-specific limits
- Budget validation for each pass type
- PCP fields are never trimmed (only slices reduced)
- Escalation rules from unknown -> expand -> verify -> deep
"""

import pytest
from alphaswarm_sol.agents.context.types import (
    BudgetPass,
    BudgetPolicy,
    BudgetValidation,
    ContextDelta,
    ContextGating,
)


# =============================================================================
# BudgetPolicy Tests
# =============================================================================


def test_budget_policy_defaults():
    """Test BudgetPolicy default values."""
    policy = BudgetPolicy.default()

    assert policy.cheap_pass_tokens == 2000
    assert policy.verify_pass_tokens == 3000
    assert policy.deep_pass_tokens == 6000
    assert policy.hard_limit == 8000
    assert policy.soft_limit == 6000
    assert policy.pcp_reserved == 500


def test_budget_policy_presets():
    """Test BudgetPolicy presets (conservative, aggressive)."""
    conservative = BudgetPolicy.conservative()
    assert conservative.cheap_pass_tokens == 1500
    assert conservative.verify_pass_tokens == 2500
    assert conservative.soft_limit == 5000

    aggressive = BudgetPolicy.aggressive()
    assert aggressive.cheap_pass_tokens == 3000
    assert aggressive.verify_pass_tokens == 4500
    assert aggressive.soft_limit == 7500


def test_budget_for_pass():
    """Test getting budget for specific pass type."""
    policy = BudgetPolicy.default()

    assert policy.budget_for_pass(BudgetPass.CHEAP) == 2000
    assert policy.budget_for_pass(BudgetPass.VERIFY) == 3000
    assert policy.budget_for_pass(BudgetPass.DEEP) == 6000


def test_slice_budget_for_pass():
    """Test slice budget excludes PCP reserved tokens."""
    policy = BudgetPolicy.default()

    # Slice budget = total budget - pcp_reserved
    assert policy.slice_budget_for_pass(BudgetPass.CHEAP) == 1500  # 2000 - 500
    assert policy.slice_budget_for_pass(BudgetPass.VERIFY) == 2500  # 3000 - 500
    assert policy.slice_budget_for_pass(BudgetPass.DEEP) == 5500  # 6000 - 500


def test_validate_for_pass_within_budget():
    """Test validation when token count is within budget."""
    policy = BudgetPolicy.default()

    validation = policy.validate_for_pass(BudgetPass.CHEAP, 1500)

    assert validation.valid is True
    assert validation.pass_type == BudgetPass.CHEAP
    assert validation.budget == 2000
    assert validation.actual == 1500
    assert validation.overflow == 0
    assert validation.recommendation == "within_budget"


def test_validate_for_pass_soft_overflow():
    """Test validation when within soft limit but over pass budget."""
    policy = BudgetPolicy.default()

    # Over cheap budget (2000) but under soft limit (6000)
    validation = policy.validate_for_pass(BudgetPass.CHEAP, 4000)

    assert validation.valid is True  # Soft overflow allowed
    assert validation.overflow == 2000  # 4000 - 2000
    assert validation.recommendation == "soft_overflow_allowed"


def test_validate_for_pass_trim_required():
    """Test validation when over soft limit but under hard limit."""
    policy = BudgetPolicy.default()

    # Over soft limit (6000) but under hard limit (8000)
    validation = policy.validate_for_pass(BudgetPass.CHEAP, 7000)

    assert validation.valid is False
    assert validation.overflow == 5000  # 7000 - 2000
    assert validation.recommendation == "trim_slices"


def test_validate_for_pass_exceeds_hard_limit():
    """Test validation when over hard limit."""
    policy = BudgetPolicy.default()

    # Over hard limit (8000)
    validation = policy.validate_for_pass(BudgetPass.DEEP, 10000)

    assert validation.valid is False
    assert validation.overflow == 2000  # 10000 - 8000
    assert validation.recommendation == "exceeds_hard_limit"


def test_escalation_rules():
    """Test escalation rules for unknown -> expand -> verify flow."""
    policy = BudgetPolicy.default()

    assert policy.next_escalation("unknown") == "expand"
    assert policy.next_escalation("expand") == "verify"
    assert policy.next_escalation("verify") == "deep"
    assert policy.next_escalation("deep") == "manual"
    assert policy.next_escalation("manual") == "manual"  # Default


def test_budget_policy_serialization():
    """Test BudgetPolicy to_dict/from_dict roundtrip."""
    policy = BudgetPolicy(
        cheap_pass_tokens=1800,
        verify_pass_tokens=2800,
        deep_pass_tokens=5500,
        hard_limit=7500,
        soft_limit=5500,
        pcp_reserved=400,
    )

    data = policy.to_dict()
    restored = BudgetPolicy.from_dict(data)

    assert restored.cheap_pass_tokens == 1800
    assert restored.verify_pass_tokens == 2800
    assert restored.deep_pass_tokens == 5500
    assert restored.hard_limit == 7500
    assert restored.soft_limit == 5500
    assert restored.pcp_reserved == 400


def test_budget_validation_serialization():
    """Test BudgetValidation to_dict."""
    validation = BudgetValidation(
        valid=True,
        pass_type=BudgetPass.CHEAP,
        budget=2000,
        actual=1500,
        overflow=0,
        recommendation="within_budget",
    )

    data = validation.to_dict()

    assert data["valid"] is True
    assert data["pass_type"] == "cheap"
    assert data["budget"] == 2000
    assert data["actual"] == 1500
    assert data["overflow"] == 0
    assert data["recommendation"] == "within_budget"


# =============================================================================
# ContextGating Tests
# =============================================================================


def test_context_gating_defaults():
    """Test ContextGating default values (all included)."""
    gating = ContextGating()

    assert gating.protocol_context_included is True
    assert gating.protocol_context_reason == "default"
    assert gating.graph_slice_included is True
    assert gating.vulndoc_included is True
    assert gating.unknowns_marked == []
    assert gating.exclusions == []


def test_context_gating_mark_unknown():
    """Test marking items as unknown due to missing context."""
    gating = ContextGating()

    gating.mark_unknown("oracle_dependency", "no oracle data in PCP")
    gating.mark_unknown("access_control", "role data incomplete")

    assert len(gating.unknowns_marked) == 2
    assert "oracle_dependency: no oracle data in PCP" in gating.unknowns_marked
    assert "access_control: role data incomplete" in gating.unknowns_marked


def test_context_gating_mark_excluded():
    """Test marking items as explicitly excluded."""
    gating = ContextGating()

    gating.mark_excluded("full_graph", "budget exceeded")
    gating.mark_excluded("external_calls", "not relevant for pattern")

    assert len(gating.exclusions) == 2
    assert "full_graph: budget exceeded" in gating.exclusions


def test_context_gating_serialization():
    """Test ContextGating to_dict/from_dict roundtrip."""
    gating = ContextGating(
        protocol_context_included=False,
        protocol_context_reason="not_available",
        unknowns_marked=["item1: reason1"],
        exclusions=["item2: reason2"],
    )

    data = gating.to_dict()
    restored = ContextGating.from_dict(data)

    assert restored.protocol_context_included is False
    assert restored.protocol_context_reason == "not_available"
    assert len(restored.unknowns_marked) == 1
    assert len(restored.exclusions) == 1


# =============================================================================
# Integration: Budget Policy with Gating
# =============================================================================


def test_budget_policy_pcp_never_trimmed():
    """Test that PCP reserved tokens are not trimmed.

    PCP fields (Protocol Context Pack) are critical for analysis and
    should never be reduced to fit budget - only graph slices are trimmed.
    """
    policy = BudgetPolicy(
        cheap_pass_tokens=1000,
        pcp_reserved=500,
    )

    # Slice budget should be total - reserved
    slice_budget = policy.slice_budget_for_pass(BudgetPass.CHEAP)
    assert slice_budget == 500  # 1000 - 500

    # PCP reserved should always be positive
    assert policy.pcp_reserved > 0


def test_context_gating_tracks_exclusions():
    """Test that gating properly tracks what was excluded and why."""
    gating = ContextGating()

    # Simulate budget-driven exclusion
    gating.protocol_context_included = True
    gating.graph_slice_included = True
    gating.mark_excluded("deep_analysis_nodes", "budget limit for cheap pass")
    gating.mark_unknown("cross_contract_flow", "not in initial slice radius")

    data = gating.to_dict()

    # Should track both what's included and what's not
    assert data["protocol_context_included"] is True
    assert data["graph_slice_included"] is True
    assert len(data["exclusions"]) == 1
    assert len(data["unknowns_marked"]) == 1
