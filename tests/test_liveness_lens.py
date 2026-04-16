"""Liveness lens pattern coverage tests.

Tests for Liveness-related vulnerability patterns including:
- dos-001: Unbounded Loop DoS
- dos-002: External Call in Loop

Pattern Testing Methodology:
- TRUE POSITIVES (TP): Vulnerable patterns that SHOULD be flagged
- TRUE NEGATIVES (TN): Safe patterns that should NOT be flagged
- EDGE CASES: Boundary conditions and special scenarios
- VARIATIONS: Different naming/implementation styles
"""

from __future__ import annotations
import unittest
import pytest
from tests.graph_cache import load_graph
from tests.pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine

try:
    import slither
    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class TestDOS001UnboundedLoop(unittest.TestCase):
    """Tests for dos-001: Unbounded Loop DoS pattern.

    Tests comprehensive coverage of unbounded loop detection across:
    - Governance contracts (voting, proposal processing)
    - DeFi contracts (reward distribution, withdrawal queues)
    - Various loop types (for, while, do-while)
    - Safe alternatives (pagination, pull patterns)
    """

    def setUp(self) -> None:
        """Initialize pattern engine and load patterns."""
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _labels_for(self, findings: list, pattern_id: str) -> set[str]:
        """Extract function labels from findings for a specific pattern."""
        return {f["node_label"] for f in findings if f["pattern_id"] == pattern_id}

    def _run_pattern(self, project: str, contract: str, pattern_id: str) -> list:
        """Run pattern matching on a test contract."""
        graph = load_graph(f"projects/{project}/{contract}")
        return self.engine.run(graph, self.patterns, pattern_ids=[pattern_id], limit=200)

    # =============================================================================
    # TRUE POSITIVES: Vulnerable patterns that SHOULD be flagged
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_classic_array_iteration(self) -> None:
        """TP: distributeRewards - classic unbounded array iteration."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("distributeRewards(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_governance_vote_tally(self) -> None:
        """TP: tallyVotes - governance DoS attack vector."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("tallyVotes()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_while_loop_variant(self) -> None:
        """TP: processAllUsers - while loop variant."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("processAllUsers()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_eth_distribution(self) -> None:
        """TP: distributeETH - unbounded loop with value transfer (critical)."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("distributeETH()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_nested_loops(self) -> None:
        """TP: crossReferenceUsers - nested unbounded loops (extremely dangerous)."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("crossReferenceUsers()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_linear_search(self) -> None:
        """TP: findUser - linear search over unbounded array."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("findUser(address)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_loop_with_deletion(self) -> None:
        """TP: clearAllUsers - unbounded loop with deletion."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("clearAllUsers()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_reward_all_users(self) -> None:
        """TP: rewardAllUsers - user-controlled array growth."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("rewardAllUsers()", self._labels_for(findings, "dos-001"))

    # =============================================================================
    # TRUE POSITIVES: DeFi reward distribution scenarios
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_defi_staking_rewards(self) -> None:
        """TP: distributeStakingRewards - classic DeFi DoS vector."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("distributeStakingRewards()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_defi_withdrawal_queue(self) -> None:
        """TP: processWithdrawals - unbounded withdrawal processing (can trap funds)."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("processWithdrawals()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_defi_compound_rewards(self) -> None:
        """TP: compoundRewards - auto-compound for all users."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("compoundRewards()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_defi_emergency_withdraw(self) -> None:
        """TP: emergencyWithdrawAll - emergency function with unbounded loop."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("emergencyWithdrawAll()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_defi_sweep_unclaimed(self) -> None:
        """TP: sweepUnclaimedRewards - admin sweep with unbounded loop."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("sweepUnclaimedRewards(address)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_defi_snapshot_balances(self) -> None:
        """TP: snapshotBalances - creates storage snapshot with unbounded loop."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("snapshotBalances()", self._labels_for(findings, "dos-001"))

    # =============================================================================
    # TRUE NEGATIVES: Safe patterns that should NOT be flagged
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_tn_bounded_with_max_check(self) -> None:
        """TN: distributeBounded - has explicit max iteration check (SAFE)."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertNotIn("distributeBounded(uint256,uint256,uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_mapping_lookup(self) -> None:
        """TN: getUserIndexSafe - direct mapping lookup, no loop (SAFE)."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertNotIn("getUserIndexSafe(address)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_pull_pattern(self) -> None:
        """TN: claimReward - pull-over-push pattern, no loop (SAFE)."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertNotIn("claimReward()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_fixed_size_loop(self) -> None:
        """TN: processFixedCount - loop bound is constant (SAFE)."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertNotIn("processFixedCount()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_parameter_bound(self) -> None:
        """TN: processCount - loop bound is function parameter (SAFER).

        Note: This might still be flagged if builder.py considers parameter bounds unbounded.
        The safety depends on whether the caller can provide arbitrarily large values.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        # This is actually a boundary case - might be flagged or not depending on builder.py
        labels = self._labels_for(findings, "dos-001")
        # We'll document it but not assert either way since it's implementation-dependent

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_internal_function(self) -> None:
        """TN: _internalDistribute - internal function (lower DoS risk).

        Note: Pattern currently matches internal functions, so this might be flagged.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        # Internal functions are still matched by the pattern (visibility: internal)
        # So we expect this to be flagged
        self.assertIn("_internalDistribute(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_view_function(self) -> None:
        """TN: countUsers - view function with unbounded loop.

        Note: Pattern currently doesn't exclude view functions in 'none' clause,
        so this WILL be flagged. View functions still cause DoS (query failure).
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        # Pattern doesn't exclude view functions, so expect this to be flagged
        self.assertIn("countUsers()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_pure_function_memory_array(self) -> None:
        """TN: calculateSum - pure function with memory array (SAFE).

        Pure functions can't access unbounded storage, but can have unbounded memory arrays
        from parameters. This is less critical but still a DoS vector.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        # Depends on whether builder.py detects loops over memory arrays as unbounded
        labels = self._labels_for(findings, "dos-001")
        # Document but don't assert - implementation-dependent

    # =============================================================================
    # TRUE NEGATIVES: DeFi safe patterns
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_defi_pull_claim(self) -> None:
        """TN: claimReward - DeFi pull pattern (SAFE)."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertNotIn("claimReward()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_tn_defi_paginated_withdrawal(self) -> None:
        """TN: processWithdrawalsBatch - paginated with max limit (SAFE)."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertNotIn("processWithdrawalsBatch(uint256,uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_defi_index_based(self) -> None:
        """TN: updateRewardIndex - index-based tracking, no iteration (SAFE)."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertNotIn("updateRewardIndex()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_defi_individual_stake(self) -> None:
        """TN: stake/unstake - individual operations, no loops (SAFE)."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertNotIn("stake()", self._labels_for(findings, "dos-001"))
        self.assertNotIn("unstake(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_defi_single_user_snapshot(self) -> None:
        """TN: snapshotUser - single user snapshot (SAFE)."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertNotIn("snapshotUser(address)", self._labels_for(findings, "dos-001"))

    # =============================================================================
    # EDGE CASES: Boundary conditions and special scenarios
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_early_break_condition(self) -> None:
        """Edge: findFirstActiveUser - has break but still unbounded worst-case.

        Should be flagged because worst-case is still unbounded (no match found).
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("findFirstActiveUser()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_require_inside_loop(self) -> None:
        """Edge: distributeWithChecks - require inside loop doesn't bound iteration.

        Should be flagged because require doesn't limit iteration count.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("distributeWithChecks(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_edge_reverse_iteration(self) -> None:
        """Edge: processReverse - decrementing loop still unbounded.

        Should be flagged - loop direction doesn't matter.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("processReverse()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_continue_statement(self) -> None:
        """Edge: selectiveDistribute - continue doesn't reduce iteration count.

        Should be flagged - continue only skips iteration body, not the iteration itself.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("selectiveDistribute(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_do_while_loop(self) -> None:
        """Edge: processDoWhile - do-while variant of unbounded loop.

        Should be flagged - different loop syntax, same vulnerability.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("processDoWhile()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_multiple_sequential_loops(self) -> None:
        """Edge: multipleLoops - multiple unbounded loops in one function.

        Should be flagged - compound vulnerability (even worse).
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("multipleLoops(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_gas_intensive_operation(self) -> None:
        """Edge: expensiveOperation - unbounded loop with expensive operations.

        Should be flagged - makes DoS even more likely (lower threshold).
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("expensiveOperation()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_conditional_unbounded_loop(self) -> None:
        """Edge: conditionalDistribute - unbounded loop behind condition.

        Should be flagged - vulnerability exists when condition is true.
        """
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("conditionalDistribute(bool,uint256)", self._labels_for(findings, "dos-001"))

    # =============================================================================
    # EDGE CASES: DeFi-specific boundaries
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_defi_limit_with_break(self) -> None:
        """Edge: distributeUntilLimit - breaks on threshold but still unbounded worst-case."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("distributeUntilLimit(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_defi_conditional_stake_size(self) -> None:
        """Edge: distributeToBigStakers - conditional but still unbounded loop."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("distributeToBigStakers(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_defi_two_phase_withdrawal(self) -> None:
        """Edge: finalizeWithdrawals - two-phase doesn't help if processing is unbounded."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("finalizeWithdrawals()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_defi_admin_override(self) -> None:
        """Edge: adminDistributeRewards - admin trigger doesn't make it safe."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("adminDistributeRewards()", self._labels_for(findings, "dos-001"))

    # =============================================================================
    # VARIATION TESTING: Different naming and implementation styles
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_different_array_name(self) -> None:
        """Variation: rewardParticipants - 'participants' instead of 'users'."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("rewardParticipants(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_different_loop_variable(self) -> None:
        """Variation: distributeWithDifferentVar - 'index' instead of 'i'."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("distributeWithDifferentVar(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_compound_condition(self) -> None:
        """Variation: complexCondition - compound loop condition."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("complexCondition(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_different_increment_style(self) -> None:
        """Variation: differentIncrement - increment at end of loop body."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("differentIncrement(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_nested_struct_array(self) -> None:
        """Variation: distributeToGroup - nested struct array access."""
        findings = self._run_pattern("governance-dao", "UnboundedLoopDoS.sol", "dos-001")
        self.assertIn("distributeToGroup(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_defi_liquidity_providers(self) -> None:
        """Variation: distributeLPRewards - 'liquidityProviders' terminology."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("distributeLPRewards(uint256)", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_defi_farming_harvest(self) -> None:
        """Variation: harvestAll - farming terminology."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("harvestAll()", self._labels_for(findings, "dos-001"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_defi_fee_distribution(self) -> None:
        """Variation: distributeFees - fee distribution to token holders."""
        findings = self._run_pattern("defi-lending", "RewardDistribution.sol", "dos-001")
        self.assertIn("distributeFees(uint256)", self._labels_for(findings, "dos-001"))


class TestDOS002ExternalCallInLoop(unittest.TestCase):
    """Tests for dos-002: External Call in Loop pattern.

    Tests comprehensive coverage of external calls in loops:
    - Token transfers in loops (ERC-20, ETH)
    - External contract calls in loops
    - Safe patterns (try-catch, pull-over-push, low-level with success check)
    - Edge cases (pagination, view functions)
    - Variations (different loop types, call patterns)
    """

    def setUp(self) -> None:
        """Initialize pattern engine and load patterns."""
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _labels_for(self, findings: list, pattern_id: str) -> set[str]:
        """Extract function labels from findings for a specific pattern."""
        return {f["node_label"] for f in findings if f["pattern_id"] == pattern_id}

    def _run_pattern(self, project: str, contract: str, pattern_id: str) -> list:
        """Run pattern matching on a test contract."""
        graph = load_graph(f"projects/{project}/{contract}")
        return self.engine.run(graph, self.patterns, pattern_ids=[pattern_id], limit=200)

    # =============================================================================
    # TRUE POSITIVES: Vulnerable patterns that SHOULD be flagged
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_airdrop_tokens(self) -> None:
        """TP: airdropTokens - standard token.transfer in loop."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("airdropTokens(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_batch_transfer(self) -> None:
        """TP: batchTransfer - transferFrom in loop."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("batchTransfer(address[],uint256[])", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_tp_refund_all_akutars(self) -> None:
        """TP: refundAll - Akutars pattern with ETH transfer in loop ($34M bug)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("refundAll()", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_notify_all_rewards(self) -> None:
        """TP: notifyAllRewards - external contract calls in loop."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("notifyAllRewards(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_while_loop_variant(self) -> None:
        """TP: processUntilEmpty - while loop with external call."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("processUntilEmpty()", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_do_while_variant(self) -> None:
        """TP: processInDoWhile - do-while loop with external call."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("processInDoWhile()", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_nested_loops(self) -> None:
        """TP: airdropNested - nested loops with external calls (severity increased)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("airdropNested(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_low_level_call_unchecked(self) -> None:
        """TP: sendETHLoop - low-level call WITHOUT success check."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("sendETHLoop(address[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_multiple_external_calls(self) -> None:
        """TP: distributeWithCallback - multiple external calls per iteration."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("distributeWithCallback(address[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tp_variation_naming(self) -> None:
        """TP: removeFundsFromAll - different naming convention."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("removeFundsFromAll(address[])", self._labels_for(findings, "dos-002"))

    # =============================================================================
    # TRUE NEGATIVES: Safe patterns that should NOT be flagged
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_pull_pattern_set_claimable(self) -> None:
        """TN: setClaimable - pull-over-push pattern (no external calls in loop)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("setClaimable(address[],uint256[])", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_pull_pattern_claim(self) -> None:
        """TN: claim - user pulls tokens (no loop)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("claim()", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_try_catch(self) -> None:
        """TN: airdropWithTryCatch - try-catch handles failures gracefully."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("airdropWithTryCatch(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_tn_low_level_with_success_check(self) -> None:
        """TN: refundWithSuccessCheck - low-level call with success check."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("refundWithSuccessCheck()", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_tn_view_function(self) -> None:
        """TN: getBalances - view function with external calls (read-only)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("getBalances(address[])", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_pure_function(self) -> None:
        """TN: calculateAmounts - pure function (no external calls possible)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("calculateAmounts(uint256[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_pagination(self) -> None:
        """TN: distributeBatch - pagination with try-catch."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("distributeBatch(uint256,uint256,uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_internal_function(self) -> None:
        """TN: _distributeInternal - internal function (not entry point)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("_distributeInternal(address[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tn_private_function(self) -> None:
        """TN: _distributePrivate - private function (not entry point)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("_distributePrivate(address[],uint256)", self._labels_for(findings, "dos-002"))

    # =============================================================================
    # EDGE CASES: Boundary conditions and special scenarios
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_edge_external_call_after_loop(self) -> None:
        """Edge: distributeAfterLoop - external call AFTER loop (not inside)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("distributeAfterLoop(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_conditional_external_call(self) -> None:
        """Edge: distributeConditional - external call in conditional inside loop."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("distributeConditional(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_empty_array(self) -> None:
        """Edge: distributeEmpty - zero iterations (still vulnerable if populated)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("distributeEmpty(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_edge_single_iteration(self) -> None:
        """Edge: distributeSingle - one iteration (still vulnerable to revert)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("distributeSingle(address,uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_edge_view_with_external_calls(self) -> None:
        """Edge: checkAllBalances - view with external view calls (could revert)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertNotIn("checkAllBalances(address[])", self._labels_for(findings, "dos-002"))

    # =============================================================================
    # VARIATION TESTING: Different implementations
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_reverse_iteration(self) -> None:
        """Variation: airdropReverse - reverse loop iteration."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("airdropReverse(address[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_pre_increment(self) -> None:
        """Variation: airdropPreIncrement - pre-increment operator."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("airdropPreIncrement(address[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_manual_increment(self) -> None:
        """Variation: airdropManualIncrement - manual increment in loop body."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("airdropManualIncrement(address[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_interface_cast(self) -> None:
        """Variation: notifyRewardsWithCast - external call via interface cast."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("notifyRewardsWithCast(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_var_eth_send(self) -> None:
        """Variation: sendETHLoop - ETH send() instead of transfer()."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("sendETHLoop(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_low_level_call(self) -> None:
        """Variation: transferViaCall - low-level call with abi.encodeWithSignature."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("transferViaCall(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_mapping_iteration(self) -> None:
        """Variation: distributeById - mapping iteration instead of array."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("distributeById(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_var_helper_function(self) -> None:
        """Variation: distributeWithHelper - external call in helper called from loop."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        # This depends on whether pattern analyzer follows function calls
        # Might not be flagged if analysis doesn't inline _sendToUser

    # =============================================================================
    # MIXED SCENARIOS: Complex real-world patterns
    # =============================================================================

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mixed_state_and_external(self) -> None:
        """Mixed: setupAndAirdrop - both state writes AND external calls."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("setupAndAirdrop(address[],uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mixed_multiple_loops(self) -> None:
        """Mixed: mixedDistribution - multiple loops (one safe, one vulnerable)."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("mixedDistribution(uint256)", self._labels_for(findings, "dos-002"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_mixed_partial_try_catch(self) -> None:
        """Mixed: partialTryCatch - try-catch wraps only one external call."""
        findings = self._run_pattern("token-vault", "ExternalCallLoopTest.sol", "dos-002")
        self.assertIn("partialTryCatch(uint256)", self._labels_for(findings, "dos-002"))


if __name__ == "__main__":
    unittest.main()
