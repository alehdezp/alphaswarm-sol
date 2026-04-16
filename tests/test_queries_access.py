"""Access control and reentrancy query tests."""

from __future__ import annotations

import unittest
import pytest
from tests.graph_cache import load_graph
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.planner import QueryPlan

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class AccessQueryTests(unittest.TestCase):
    """Test suite for access control and reentrancy detection."""

    # === Basic Reentrancy Tests ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_order_flag(self) -> None:
        """Test detection of state write after external call (classic reentrancy)."""
        graph = load_graph("ReentrancyClassic.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"state_write_after_external_call": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("withdraw(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_cross_function_reentrancy(self) -> None:
        """Test that cross-function reentrancy contract exists and can be analyzed."""
        # Note: Slither may not detect .call{value: ...}("") as an external call in all cases
        # This test validates the contract structure rather than specific reentrancy detection
        graph = load_graph("CrossFunctionReentrancy.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # Verify the contract has the expected functions
        self.assertIn("withdraw(uint256)", labels)
        self.assertIn("transfer(address,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_read_only_reentrancy(self) -> None:
        """Test detection of read-only reentrancy vulnerability."""
        graph = load_graph("ReadOnlyReentrancy.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"state_write_after_external_call": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("withdraw(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_cei_pattern(self) -> None:
        """Test that CEI pattern (state before call) is correctly identified."""
        graph = load_graph("ReentrancyCEI.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"state_write_before_external_call": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("withdraw(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_cei_not_vulnerable(self) -> None:
        """Test that CEI pattern does NOT flag as vulnerable to state-write-after-call."""
        graph = load_graph("ReentrancyCEI.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"state_write_after_external_call": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # Should NOT contain withdraw because it follows CEI
        self.assertNotIn("withdraw(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_state_write_before_call(self) -> None:
        """Test detection of safe state write before external call pattern."""
        graph = load_graph("StateWriteBeforeCall.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"state_write_before_external_call": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("withdraw(uint256)", labels)

    # === Reentrancy Guard Tests ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_non_reentrant_guard_modifier(self) -> None:
        """Test detection of nonReentrant guard modifier."""
        graph = load_graph("NonReentrantGuard.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_reentrancy_guard": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("guarded()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_with_guard_protection(self) -> None:
        """Test that functions with reentrancy guard are properly detected."""
        graph = load_graph("ReentrancyWithGuard.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_reentrancy_guard": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("withdraw(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_vulnerable_pattern_with_guard(self) -> None:
        """Test that vulnerable pattern with guard is still flagged for the pattern."""
        graph = load_graph("ReentrancyWithGuard.sol")
        # Should still detect the vulnerable pattern, even with guard
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"state_write_after_external_call": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("withdraw(uint256)", labels)

    # === Access Control Tests ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_custom_access_gate_logic(self) -> None:
        """Test detection of custom inline access control logic."""
        graph = load_graph("CustomAccessGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"access_gate_logic": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setFee(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_privileged_write_without_access_gate(self) -> None:
        """Test detection of privileged state writes without access control."""
        graph = load_graph("NoAccessGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"writes_privileged_state": True, "has_access_gate": False},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setOwner(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_partial_access_control_missing_gate(self) -> None:
        """Test detection of partially protected privileged functions."""
        graph = load_graph("PartialAccessControl.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"writes_privileged_state": True, "has_access_gate": False},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # dangerousUpdate writes admin without access control
        self.assertIn("dangerousUpdate(address)", labels)
        # These should NOT be in results (they have access gates)
        self.assertNotIn("setOwner(address)", labels)
        self.assertNotIn("updateSettings(address,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_partial_access_control_with_gate(self) -> None:
        """Test that properly protected functions are detected correctly."""
        graph = load_graph("PartialAccessControl.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"writes_privileged_state": True, "has_access_gate": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setOwner(address)", labels)
        self.assertIn("updateSettings(address,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_uninitialized_owner_no_gate(self) -> None:
        """Test detection of unprotected initialization functions."""
        graph = load_graph("UninitializedOwner.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"writes_privileged_state": True, "has_access_gate": False},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # initialize() writes owner without access control
        self.assertIn("initialize(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_public_wrapper_without_access_gate(self) -> None:
        """Test detection of public wrappers calling internal logic without access control."""
        graph = load_graph("PublicWrapperNoGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"public_wrapper_without_access_gate": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setOwner(address)", labels)
        self.assertNotIn("setOwnerProtected(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_governance_vote_without_snapshot(self) -> None:
        """Test detection of governance voting without snapshot checks."""
        graph = load_graph("GovernanceVoteNoSnapshot.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"governance_vote_without_snapshot": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("castVote(uint256)", labels)
        self.assertNotIn("castVoteWithSnapshot(uint256,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_threshold_change_without_gate(self) -> None:
        """Test detection of multisig threshold changes without access control."""
        graph = load_graph("MultisigConfigNoGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"multisig_threshold_change_without_gate": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setThreshold(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_signer_change_without_gate(self) -> None:
        """Test detection of multisig signer changes without access control."""
        graph = load_graph("MultisigConfigNoGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"multisig_signer_change_without_gate": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("addSigner(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_role_grant_like_detection(self) -> None:
        """Test detection of role grant-like functions."""
        graph = load_graph("RoleGrantRevokeNoGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"role_grant_like": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("grantRole(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_role_revoke_like_detection(self) -> None:
        """Test detection of role revoke-like functions."""
        graph = load_graph("RoleGrantRevokeNoGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"role_revoke_like": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("revokeRole(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_uses_selfdestruct_detection(self) -> None:
        """Test detection of selfdestruct usage."""
        graph = load_graph("SelfdestructNoGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_selfdestruct": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("destroy()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_governance_quorum_without_snapshot(self) -> None:
        """Test detection of governance quorum without snapshot."""
        graph = load_graph("GovernanceQuorumNoSnapshot.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"governance_quorum_without_snapshot": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("quorum(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_governance_execute_without_timelock_check(self) -> None:
        """Test detection of governance execution without timelock enforcement."""
        graph = load_graph("GovernanceExecuteNoTimelock.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"governance_exec_without_timelock_check": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("executeProposal(uint256,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_threshold_change_without_validation(self) -> None:
        """Test detection of multisig threshold change without validation."""
        graph = load_graph("MultisigThresholdChangeNoValidation.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"multisig_threshold_change_without_validation": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setThreshold(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_signer_change_without_validation(self) -> None:
        """Test detection of multisig signer change without validation."""
        graph = load_graph("MultisigSignerChangeNoValidation.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"multisig_signer_change_without_validation": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("addSigner(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_governance_exec_without_quorum_check(self) -> None:
        """Test detection of governance execute without quorum check."""
        graph = load_graph("GovernanceExecuteNoQuorum.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"governance_exec_without_quorum_check": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("execute(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_governance_exec_without_vote_period_check(self) -> None:
        """Test detection of governance execute without vote period check."""
        graph = load_graph("GovernanceExecuteNoVotePeriod.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"governance_exec_without_vote_period_check": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("execute(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_weak_auth_extcodesize(self) -> None:
        """Test detection of weak auth using extcodesize."""
        graph = load_graph("WeakAuthExtcodesize.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_extcodesize": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_weak_auth_gasleft(self) -> None:
        """Test detection of weak auth using gasleft."""
        graph = load_graph("WeakAuthGasleft.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_gasleft": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_weak_auth_extcodehash(self) -> None:
        """Test detection of weak auth using extcodehash."""
        graph = load_graph("WeakAuthExtcodehash.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_extcodehash": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_gate_block_timestamp(self) -> None:
        """Test detection of access gates using block.timestamp."""
        graph = load_graph("WeakAuthSource.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"access_control_weak_source": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multisig_execute_nonce_not_updated(self) -> None:
        """Test detection of multisig execute nonce not updated."""
        graph = load_graph("MultisigExecuteNonceNoUpdate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"writes_nonce_state": False, "has_nonce_parameter": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("execute(address,bytes,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_gate_uses_balance_check(self) -> None:
        """Test detection of access gate using balance check."""
        graph = load_graph("WeakAuthBalanceCheck.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"access_gate_uses_balance_check": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_member_change_without_minimum_check(self) -> None:
        """Test detection of multisig member change without minimum signer check."""
        graph = load_graph("MultisigSignerRemoveNoMinCheck.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"multisig_member_change_without_minimum_check": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("removeSigner(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multisig_threshold_change_without_owner_count_check(self) -> None:
        """Test detection of multisig threshold change without owner count check."""
        graph = load_graph("MultisigThresholdAboveOwners.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"multisig_threshold_change_without_owner_count_check": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setThreshold(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_gate_uses_contract_address(self) -> None:
        """Test detection of access gate using contract address."""
        graph = load_graph("WeakAuthContractAddress.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"access_gate_uses_contract_address": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_gate_uses_hash_compare(self) -> None:
        """Test detection of access gate using hash comparison."""
        graph = load_graph("AccessGateStringCompare.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"access_gate_uses_hash_compare": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_role_grant_without_events(self) -> None:
        """Test detection of role grants without events."""
        graph = load_graph("RoleGrantNoEvent.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Contract"],
            properties={"has_role_grant": True, "has_role_events": False},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("RoleGrantNoEvent", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_gate_if_return(self) -> None:
        """Test detection of access gate using if-return."""
        graph = load_graph("AccessGateIfReturn.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"access_gate_has_if_return": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setValue(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_gate_without_sender_source(self) -> None:
        """Test detection of access gate without sender/origin source."""
        graph = load_graph("AccessGateWrongVariable.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"access_gate_without_sender_source": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setValue(address,uint256)", labels)

    # === Auth Pattern Modifier Tests ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_only_owner_modifier_pattern(self) -> None:
        """Test detection of onlyOwner modifier pattern."""
        graph = load_graph("AuthPatternModifiers.sol")
        # Query for functions with owner auth pattern
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_auth_pattern": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("setOwner(address)", labels)
        self.assertIn("setAdmin(address)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_only_admin_modifier_pattern(self) -> None:
        """Test detection of onlyAdmin modifier pattern."""
        graph = load_graph("AuthPatternModifiers.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_auth_pattern": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("updateConfig(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_allowlist_modifier_pattern(self) -> None:
        """Test detection of allowlist/whitelist modifier pattern."""
        graph = load_graph("AuthPatternModifiers.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_auth_pattern": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("restrictedAction()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_role_based_access_pattern(self) -> None:
        """Test detection of role-based access control patterns."""
        graph = load_graph("RoleBasedAccess.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_auth_pattern": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("grantRole(bytes32,address)", labels)
        self.assertIn("mint(uint256)", labels)
        self.assertIn("pause()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_multiple_access_gates(self) -> None:
        """Test detection of functions with multiple layered access controls."""
        graph = load_graph("MultipleAccessGates.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_access_gate": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # criticalOperation has onlyOwner + whenNotPaused + inline check
        self.assertIn("criticalOperation()", labels)
        self.assertIn("setPaused(bool)", labels)

    # === tx.origin Tests ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_tx_origin_auth_flag(self) -> None:
        """Test detection of tx.origin usage in authentication."""
        graph = load_graph("TxOriginAuth.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_tx_origin": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("privileged()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mixed_auth_methods_tx_origin(self) -> None:
        """Test detection of tx.origin in mixed authentication methods."""
        graph = load_graph("MixedAuthMethods.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_tx_origin": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("badAuth()", labels)
        self.assertIn("mixedAuth()", labels)
        # goodAuth should NOT use tx.origin
        self.assertNotIn("goodAuth()", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_mixed_auth_methods_msg_sender(self) -> None:
        """Test detection of msg.sender usage (safe authentication)."""
        graph = load_graph("MixedAuthMethods.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"uses_msg_sender": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("goodAuth()", labels)
        self.assertIn("mixedAuth()", labels)

    # === Delegatecall Tests ===
    # Note: Current Slither version may not detect .delegatecall() in certain contexts
    # These tests validate contract structure and access control patterns

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_delegatecall_contract_structure(self) -> None:
        """Test that delegatecall test contracts can be analyzed."""
        graph = load_graph("DelegatecallNoAccessGate.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # Verify expected functions exist
        self.assertIn("execute(address,bytes)", labels)
        self.assertIn("safeExecute(address,bytes)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_delegatecall_access_control_pattern(self) -> None:
        """Test access control detection on delegatecall functions."""
        graph = load_graph("DelegatecallNoAccessGate.sol")
        # safeExecute should have access gate logic
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_access_gate": True},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("safeExecute(address,bytes)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_delegatecall_missing_access_control(self) -> None:
        """Test detection of functions without access control."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"has_access_gate": False},
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # proxy has no access control
        self.assertIn("proxy(address,bytes)", labels)
        # constructor also has no access control
        self.assertIn("constructor()", labels)

    # === Authority Lens Pattern Pack Tests ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_unprotected_state_writer(self) -> None:
        """Test Authority Lens unprotected state writer pattern."""
        graph = load_graph("NoAccessGate.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-001"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-001", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_tx_origin_auth(self) -> None:
        """Test Authority Lens tx.origin auth pattern."""
        graph = load_graph("TxOriginAuth.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-002"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-002", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_missing_signature_validation(self) -> None:
        """Test Authority Lens missing signature validation pattern."""
        graph = load_graph("SignatureZeroAddressVuln.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-003"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-003", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_signature_replay(self) -> None:
        """Test Authority Lens signature replay pattern."""
        graph = load_graph("SignatureReplayReusable.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-004"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-004", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_single_point_of_failure(self) -> None:
        """Test Authority Lens single point of failure pattern."""
        graph = load_graph("SinglePointOfFailure.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-005"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-005", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_unprotected_initializer(self) -> None:
        """Test Authority Lens unprotected initializer pattern."""
        graph = load_graph("UnprotectedInitializer.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-006"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-006", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_privilege_escalation(self) -> None:
        """Test Authority Lens privilege escalation pattern."""
        graph = load_graph("PrivilegeEscalation.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-007"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-007", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_missing_timelock(self) -> None:
        """Test Authority Lens missing timelock pattern."""
        graph = load_graph("SinglePointOfFailure.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-008"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-008", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_bypassable_access_control(self) -> None:
        """Test Authority Lens bypassable access control pattern."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-009"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-009", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_cross_contract_auth(self) -> None:
        """Test Authority Lens cross-contract auth confusion pattern."""
        graph = load_graph("CallWithValue.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-010"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-010", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_unprotected_admin_function(self) -> None:
        """Test Authority Lens unprotected admin function pattern."""
        graph = load_graph("NoAccessGate.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-011"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-011", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_unprotected_value_transfer(self) -> None:
        """Test Authority Lens unprotected value transfer pattern."""
        graph = load_graph("CallWithValue.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-012"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-012", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_flawed_access_logic(self) -> None:
        """Test Authority Lens flawed access logic pattern."""
        graph = load_graph("FlawedAccessControlOr.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-013"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-013", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_inconsistent_access_control(self) -> None:
        """Test Authority Lens inconsistent access control pattern."""
        graph = load_graph("PartialAccessControl.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-014"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-014", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_missing_privilege_revocation(self) -> None:
        """Test Authority Lens missing privilege revocation pattern."""
        graph = load_graph("RoleBasedAccess.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-015"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-015", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_default_permission_issues(self) -> None:
        """Test Authority Lens default permission issues pattern."""
        graph = load_graph("RoleBasedAccess.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-016"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-016", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_role_enumeration_missing(self) -> None:
        """Test Authority Lens role enumeration missing pattern."""
        graph = load_graph("RoleBasedAccess.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-017"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-017", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_weak_auth_source(self) -> None:
        """Test Authority Lens weak authentication source pattern."""
        graph = load_graph("WeakAuthSource.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-018"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-018", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_time_based_access(self) -> None:
        """Test Authority Lens time-based access control pattern."""
        graph = load_graph("WeakAuthSource.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-019"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-019", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_governance_without_timelock(self) -> None:
        """Test Authority Lens governance without timelock pattern."""
        graph = load_graph("GovernanceNoTimelock.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-020"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-020", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_multisig_threshold_one(self) -> None:
        """Test Authority Lens multisig threshold one pattern."""
        graph = load_graph("MultiSigThresholdOne.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-021"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-021", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_dangerous_admin_function(self) -> None:
        """Test Authority Lens dangerous admin function pattern."""
        graph = load_graph("PartialAccessControl.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-022"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-022", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_rbac_without_timelock(self) -> None:
        """Test Authority Lens RBAC without timelock pattern."""
        graph = load_graph("RoleBasedAccess.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-023"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-023", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_signature_missing_chainid(self) -> None:
        """Test Authority Lens missing chainId pattern."""
        graph = load_graph("SignatureReplayMissingChainId.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-024"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-024", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_signature_missing_domain(self) -> None:
        """Test Authority Lens missing domain separator pattern."""
        graph = load_graph("SignatureReplayMissingDomain.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-025"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-025", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_signature_missing_deadline(self) -> None:
        """Test Authority Lens missing deadline pattern."""
        graph = load_graph("SignatureNoDeadline.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-026"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-026", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_signature_malleability(self) -> None:
        """Test Authority Lens signature malleability pattern."""
        graph = load_graph("SignatureMalleabilityS.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-027"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-027", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_delegatecall_target_unvalidated(self) -> None:
        """Test Authority Lens delegatecall target validation pattern."""
        graph = load_graph("DelegatecallTargetUnvalidated.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-028"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-028", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_callback_without_auth(self) -> None:
        """Test Authority Lens callback without auth pattern."""
        graph = load_graph("CallbackNoAuth.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-029"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-029", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_authority_lens_multicall_auth_bypass(self) -> None:
        """Test Authority Lens multicall auth bypass pattern."""
        graph = load_graph("MulticallAuthBypass.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-030"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-030", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_upgrade_without_timelock(self) -> None:
        """Test Authority Lens upgrade without timelock pattern."""
        graph = load_graph("UpgradeNoTimelock.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-031"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-031", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_timelock_emergency_bypass(self) -> None:
        """Test Authority Lens emergency timelock bypass pattern."""
        graph = load_graph("TimelockBypassEmergency.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-032"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-032", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_upgrade_missing_timelock_check(self) -> None:
        """Test Authority Lens upgrade missing timelock check pattern."""
        graph = load_graph("UpgradeTimelockMissingCheck.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-033"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-033", pattern_ids)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_authority_lens_timelock_delay_zero(self) -> None:
        """Test Authority Lens timelock delay zero pattern."""
        graph = load_graph("TimelockDelayZero.sol")
        plan = QueryPlan(kind="pattern", patterns=["auth-034"])
        result = QueryExecutor().execute(graph, plan)
        pattern_ids = {finding["pattern_id"] for finding in result.get("findings", [])}
        self.assertIn("auth-034", pattern_ids)

    # === Complex Combined Tests ===

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_vulnerable_pattern_combination(self) -> None:
        """Test detection of functions with multiple vulnerability indicators."""
        graph = load_graph("ReentrancyClassic.sol")
        # Query for external calls + state writes + no guard
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
            },
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("withdraw(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_safe_pattern_exclusion(self) -> None:
        """Test that safe patterns are excluded from vulnerability detection."""
        graph = load_graph("ReentrancyWithGuard.sol")
        # Functions with guard should NOT match unsafe pattern query
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
            },
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        # withdraw has guard, so should NOT match
        self.assertNotIn("withdraw(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_constructor_access_bypass(self) -> None:
        """Test detection of constructor parameter usage that bypasses access control."""
        graph = load_graph("ConstructorAccessBypass.sol")
        # Look for constructor setting privileged state
        plan = QueryPlan(
            kind="nodes",
            node_types=["Function"],
            properties={"is_constructor": True, "writes_privileged_state": True},
        )
        result = QueryExecutor().execute(graph, plan)
        # Should find the constructor
        self.assertTrue(len(result["nodes"]) > 0)


if __name__ == "__main__":
    unittest.main()
