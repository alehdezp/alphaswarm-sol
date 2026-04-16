"""Tests for context budget enforcement and progressive disclosure (Phase 7.1.3).

These tests validate:
- Budget enforcement trims context deterministically
- Staged disclosure respects per-stage caps and preserves evidence IDs
- Budget reports include estimated tokens and trimmed sections
"""

import pytest
from alphaswarm_sol.llm.context_budget import (
    ContextBudgetPolicy,
    ContextBudgetStage,
    ContextBudgetReport,
    ROLE_BUDGETS,
    POOL_BUDGETS,
    STAGE_BUDGETS,
    get_budget_policy,
    apply_budget,
    estimate_context_tokens,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def small_context():
    """Small context that fits within budget."""
    return "This is a small context for testing purposes."


@pytest.fixture
def medium_context():
    """Medium context with evidence IDs."""
    return """## Finding Summary

Function: Vault.withdraw
Severity: critical
Evidence: E-ABC123, E-DEF456

## Evidence Details

E-ABC123: External call at line 45
E-DEF456: State write at line 52

## Code Location

node_id: Vault.withdraw
ref: contracts/Vault.sol:45-60
"""


@pytest.fixture
def large_context():
    """Large context that exceeds budget."""
    base = """## Finding Summary

Function: Vault.withdraw
Severity: critical
Evidence: E-ABC123, E-DEF456

## Evidence Details

E-ABC123: External call at line 45
E-DEF456: State write at line 52

## Source

```solidity
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
    balances[msg.sender] -= amount;
}
```

## Metadata

Contract: Vault
Compiler: solc 0.8.17
Network: Ethereum Mainnet

## Additional Context

This function is vulnerable to reentrancy because the state update
happens after the external call. An attacker could re-enter and
drain the contract.
"""
    # Repeat to make it larger
    return base * 10


# =============================================================================
# ContextBudgetPolicy Tests
# =============================================================================


class TestContextBudgetPolicy:
    """Tests for ContextBudgetPolicy class."""

    def test_default_max_tokens(self):
        """Default max_tokens should be 6000 per CLAUDE.md."""
        policy = ContextBudgetPolicy()
        assert policy.max_tokens == 6000

    def test_hard_cap_enforcement(self):
        """max_tokens should never exceed hard_cap."""
        policy = ContextBudgetPolicy(max_tokens=10000, hard_cap=8000)
        assert policy.max_tokens == 8000

    def test_role_budget_lookup(self):
        """Role-based budget lookup should work."""
        policy = ContextBudgetPolicy(role="classifier")
        assert policy.max_tokens == ROLE_BUDGETS["classifier"]

        policy = ContextBudgetPolicy(role="attacker")
        assert policy.max_tokens == ROLE_BUDGETS["attacker"]

    def test_pool_budget_lookup(self):
        """Pool-based budget lookup should work."""
        policy = ContextBudgetPolicy(pool="triage")
        assert policy.max_tokens == POOL_BUDGETS["triage"]

        policy = ContextBudgetPolicy(pool="investigation")
        assert policy.max_tokens == POOL_BUDGETS["investigation"]

    def test_role_budget_minimum(self):
        """Role budget should not exceed explicit max_tokens."""
        policy = ContextBudgetPolicy(max_tokens=1000, role="attacker")
        # attacker budget is 6000, but explicit max is 1000
        assert policy.max_tokens == 1000

    def test_estimate_tokens(self, small_context):
        """Token estimation should use 4-chars-per-token heuristic."""
        policy = ContextBudgetPolicy()
        estimated = policy.estimate_tokens(small_context)
        # ~48 chars / 4 = ~12 tokens
        assert estimated == len(small_context) // 4

    def test_estimate_tokens_empty(self):
        """Empty string should estimate to 0 tokens."""
        policy = ContextBudgetPolicy()
        assert policy.estimate_tokens("") == 0

    def test_stage_budget_fractions(self):
        """Stage budgets should be fractions of max_tokens."""
        policy = ContextBudgetPolicy(max_tokens=6000)

        summary_budget = policy.get_stage_budget(ContextBudgetStage.SUMMARY)
        evidence_budget = policy.get_stage_budget(ContextBudgetStage.EVIDENCE)
        raw_budget = policy.get_stage_budget(ContextBudgetStage.RAW)

        assert summary_budget == int(6000 * STAGE_BUDGETS[ContextBudgetStage.SUMMARY])
        assert evidence_budget == int(6000 * STAGE_BUDGETS[ContextBudgetStage.EVIDENCE])
        assert raw_budget == int(6000 * STAGE_BUDGETS[ContextBudgetStage.RAW])


# =============================================================================
# Budget Enforcement Tests
# =============================================================================


class TestBudgetEnforcement:
    """Tests for budget enforcement behavior."""

    def test_within_budget_no_trim(self, small_context):
        """Context within budget should not be trimmed."""
        policy = ContextBudgetPolicy(max_tokens=6000)
        trimmed, report = policy.apply_budget(small_context)

        assert trimmed == small_context
        assert report.trimmed is False
        assert report.original_tokens == report.final_tokens

    def test_over_budget_trims(self, large_context):
        """Context over budget should be trimmed significantly."""
        # Set a small budget that large_context will exceed
        policy = ContextBudgetPolicy(max_tokens=500)
        trimmed, report = policy.apply_budget(
            large_context,
            stage=ContextBudgetStage.RAW
        )

        assert report.trimmed is True
        # Should trim significantly (may exceed slightly due to evidence preservation)
        assert report.final_tokens < report.original_tokens
        assert len(trimmed) < len(large_context)
        # Should be within reasonable range (evidence preservation may cause slight overage)
        assert report.final_tokens <= report.max_tokens * 1.5

    def test_deterministic_trimming(self, large_context):
        """Trimming should be deterministic (same input -> same output)."""
        policy = ContextBudgetPolicy(max_tokens=500)

        trimmed1, report1 = policy.apply_budget(
            large_context,
            stage=ContextBudgetStage.RAW
        )
        policy.reset()
        trimmed2, report2 = policy.apply_budget(
            large_context,
            stage=ContextBudgetStage.RAW
        )

        assert trimmed1 == trimmed2
        assert report1.dropped_sections == report2.dropped_sections

    def test_preserves_evidence_ids(self, medium_context):
        """Evidence IDs should be preserved during trimming."""
        policy = ContextBudgetPolicy(max_tokens=200)
        trimmed, report = policy.apply_budget(
            medium_context,
            stage=ContextBudgetStage.RAW
        )

        # Evidence IDs should be preserved
        assert "E-ABC123" in trimmed or "E-ABC123" in str(report.preserved_evidence_ids)
        assert "E-DEF456" in trimmed or "E-DEF456" in str(report.preserved_evidence_ids)

    def test_dropped_sections_tracked(self, large_context):
        """Dropped sections should be tracked in report."""
        policy = ContextBudgetPolicy(max_tokens=300)
        _, report = policy.apply_budget(large_context, stage=ContextBudgetStage.RAW)

        assert report.trimmed is True
        assert len(report.dropped_sections) > 0

    def test_code_blocks_trimmed_first(self):
        """Code blocks should be trimmed before other content."""
        context = """## Summary

Function has a bug.

```solidity
function foo() {
    // lots of code here that makes this block quite long
    uint256 x = 1;
    uint256 y = 2;
    uint256 z = 3;
    uint256 a = x + y + z;
    uint256 b = a * 2;
    require(b > 0, "Must be positive");
    emit SomeEvent(b);
}
```

## Evidence

E-ABC123: Important evidence here.
"""
        # Use a budget smaller than the context but large enough for non-code parts
        policy = ContextBudgetPolicy(max_tokens=30)
        trimmed, report = policy.apply_budget(context, stage=ContextBudgetStage.RAW)

        # Code block should be trimmed (replaced with marker)
        assert "code block trimmed" in trimmed or "uint256 x = 1" not in trimmed
        # Evidence should be preserved
        assert "E-ABC123" in trimmed or "E-ABC123" in str(report.preserved_evidence_ids)


# =============================================================================
# Progressive Disclosure Tests
# =============================================================================


class TestProgressiveDisclosure:
    """Tests for progressive disclosure behavior."""

    def test_stage_progression(self):
        """Stages should progress SUMMARY -> EVIDENCE -> RAW."""
        policy = ContextBudgetPolicy()
        assert policy.current_stage == ContextBudgetStage.SUMMARY

        # Apply at EVIDENCE stage
        policy.apply_budget("test context", stage=ContextBudgetStage.EVIDENCE)
        assert policy.current_stage == ContextBudgetStage.EVIDENCE

        # Apply at RAW stage
        policy.apply_budget("test context", stage=ContextBudgetStage.RAW)
        assert policy.current_stage == ContextBudgetStage.RAW

    def test_expand_context(self, small_context):
        """expand_context should combine contexts within budget."""
        policy = ContextBudgetPolicy(max_tokens=6000)

        # Start with summary stage
        _, report = policy.apply_budget(
            small_context,
            stage=ContextBudgetStage.SUMMARY
        )
        assert report.can_expand is True

        # Expand with more context
        additional = "Additional evidence details here."
        expanded, report = policy.expand_context(
            small_context,
            additional,
            to_stage=ContextBudgetStage.EVIDENCE
        )

        assert small_context in expanded
        assert additional in expanded
        assert policy.current_stage == ContextBudgetStage.EVIDENCE

    def test_expand_respects_budget(self, large_context):
        """expand_context should trim if combined exceeds budget."""
        policy = ContextBudgetPolicy(max_tokens=500)

        # Start with some context
        initial, _ = policy.apply_budget("Initial context.", stage=ContextBudgetStage.SUMMARY)

        # Try to expand with large context
        expanded, report = policy.expand_context(
            initial,
            large_context,
            to_stage=ContextBudgetStage.EVIDENCE
        )

        # Should be trimmed to fit (may have slight overage for evidence preservation)
        assert report.trimmed is True
        assert report.final_tokens < report.original_tokens

    def test_cannot_expand_at_raw(self, small_context):
        """Cannot expand beyond RAW stage."""
        policy = ContextBudgetPolicy(max_tokens=6000)

        # Apply at RAW stage
        _, report = policy.apply_budget(small_context, stage=ContextBudgetStage.RAW)
        assert report.can_expand is False

    def test_expansion_budget_tracking(self, small_context):
        """Expansion budget should track remaining tokens."""
        policy = ContextBudgetPolicy(max_tokens=6000)

        _, report = policy.apply_budget(small_context, stage=ContextBudgetStage.SUMMARY)

        # Should have expansion budget available
        expected_remaining = 6000 - report.final_tokens
        assert report.expansion_budget == expected_remaining


# =============================================================================
# Budget Report Tests
# =============================================================================


class TestBudgetReport:
    """Tests for ContextBudgetReport."""

    def test_report_fields(self, medium_context):
        """Report should include all required fields."""
        policy = ContextBudgetPolicy(max_tokens=6000)
        _, report = policy.apply_budget(medium_context)

        assert hasattr(report, 'stage')
        assert hasattr(report, 'original_tokens')
        assert hasattr(report, 'final_tokens')
        assert hasattr(report, 'max_tokens')
        assert hasattr(report, 'dropped_sections')
        assert hasattr(report, 'preserved_evidence_ids')
        assert hasattr(report, 'trimmed')
        assert hasattr(report, 'can_expand')
        assert hasattr(report, 'expansion_budget')

    def test_report_to_dict(self, medium_context):
        """Report should serialize to dictionary."""
        policy = ContextBudgetPolicy(max_tokens=6000)
        _, report = policy.apply_budget(medium_context)

        d = report.to_dict()

        assert 'stage' in d
        assert d['stage'] == report.stage.value
        assert 'original_tokens' in d
        assert 'final_tokens' in d
        assert 'max_tokens' in d
        assert 'dropped_sections' in d
        assert 'preserved_evidence_ids' in d
        assert 'trimmed' in d
        assert 'can_expand' in d
        assert 'expansion_budget' in d

    def test_report_from_dict(self, medium_context):
        """Report should deserialize from dictionary."""
        policy = ContextBudgetPolicy(max_tokens=6000)
        _, report = policy.apply_budget(medium_context)

        d = report.to_dict()
        restored = ContextBudgetReport.from_dict(d)

        assert restored.stage == report.stage
        assert restored.original_tokens == report.original_tokens
        assert restored.final_tokens == report.final_tokens
        assert restored.max_tokens == report.max_tokens
        assert restored.trimmed == report.trimmed


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_budget_policy(self):
        """get_budget_policy should return configured policy."""
        policy = get_budget_policy(role="attacker", max_tokens=5000)

        assert isinstance(policy, ContextBudgetPolicy)
        assert policy.max_tokens == 5000

    def test_apply_budget_function(self, medium_context):
        """apply_budget function should work correctly."""
        trimmed, report = apply_budget(
            medium_context,
            stage=ContextBudgetStage.EVIDENCE,
            max_tokens=6000,
        )

        assert isinstance(report, ContextBudgetReport)
        assert report.stage == ContextBudgetStage.EVIDENCE

    def test_estimate_context_tokens(self, small_context):
        """estimate_context_tokens should return integer."""
        tokens = estimate_context_tokens(small_context)

        assert isinstance(tokens, int)
        assert tokens == len(small_context) // 4


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_context(self):
        """Empty context should be handled gracefully."""
        policy = ContextBudgetPolicy()
        trimmed, report = policy.apply_budget("")

        assert trimmed == ""
        assert report.original_tokens == 0
        assert report.final_tokens == 0
        assert report.trimmed is False

    def test_context_with_only_evidence(self):
        """Context with only evidence IDs should preserve all."""
        context = "E-ABC123 E-DEF456 E-GHI789"
        policy = ContextBudgetPolicy(max_tokens=50)
        trimmed, report = policy.apply_budget(context, stage=ContextBudgetStage.RAW)

        # Should preserve evidence even if over budget
        preserved = report.preserved_evidence_ids
        assert any("E-ABC123" in p for p in preserved) or "E-ABC123" in trimmed
        assert any("E-DEF456" in p for p in preserved) or "E-DEF456" in trimmed

    def test_very_small_budget(self, medium_context):
        """Very small budget should still produce valid output."""
        policy = ContextBudgetPolicy(max_tokens=10)
        trimmed, report = policy.apply_budget(medium_context, stage=ContextBudgetStage.RAW)

        # Should not crash and should trim aggressively
        assert report.trimmed is True
        assert report.final_tokens > 0  # Should have some content

    def test_reset_clears_state(self):
        """reset() should clear policy state."""
        policy = ContextBudgetPolicy()
        policy.apply_budget("test", stage=ContextBudgetStage.EVIDENCE)

        assert policy.current_stage == ContextBudgetStage.EVIDENCE

        policy.reset()

        assert policy.current_stage == ContextBudgetStage.SUMMARY

    def test_unknown_role_uses_default(self):
        """Unknown role should use default budget."""
        policy = ContextBudgetPolicy(role="unknown_role")
        assert policy.max_tokens == 6000  # Default

    def test_unknown_pool_uses_default(self):
        """Unknown pool should use default budget."""
        policy = ContextBudgetPolicy(pool="unknown_pool")
        assert policy.max_tokens == 6000  # Default
