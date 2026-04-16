"""Full coverage pattern tests for comprehensive vulnerability list."""

from __future__ import annotations

import unittest
import pytest
from tests.graph_cache import load_graph
from tests.pattern_loader import load_all_patterns
from alphaswarm_sol.queries.patterns import PatternEngine

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class FullCoveragePatternTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _labels_for(self, findings, pattern_id: str) -> set[str]:
        return {finding["node_label"] for finding in findings if finding["pattern_id"] == pattern_id}

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_reentrancy_core_patterns(self) -> None:
        graph = load_graph("ValueMovementReentrancy.sol")
        pattern_ids = [
            "classic-reentrancy-state-before-external",
            "eth-transfer-reentrancy",
            "balance-update-after-transfer",
            "loop-reentrancy",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("withdraw(uint256)", self._labels_for(findings, "classic-reentrancy-state-before-external"))
        self.assertIn("withdraw(uint256)", self._labels_for(findings, "eth-transfer-reentrancy"))
        self.assertIn("withdraw(uint256)", self._labels_for(findings, "balance-update-after-transfer"))
        self.assertIn("batchWithdraw(address[],uint256)", self._labels_for(findings, "loop-reentrancy"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_cross_function_reentrancy_patterns(self) -> None:
        graph = load_graph("ValueMovementInheritanceComposition.sol")
        pattern_ids = [
            "cross-function-inheritance-reentrancy",
            "cross-function-composition-reentrancy",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("derivedWithdraw(uint256)", self._labels_for(findings, "cross-function-inheritance-reentrancy"))
        self.assertIn("harvest(uint256)", self._labels_for(findings, "cross-function-composition-reentrancy"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_protocol_chain_patterns(self) -> None:
        graph = load_graph("ValueMovementProtocolChain.sol")
        pattern_ids = [
            "protocol-level-reentrancy",
            "defi-protocol-reentrancy",
            "callback-chain-reentrancy",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("deposit(uint256)", self._labels_for(findings, "protocol-level-reentrancy"))
        self.assertIn("deposit(uint256)", self._labels_for(findings, "defi-protocol-reentrancy"))
        self.assertIn("deposit(uint256)", self._labels_for(findings, "callback-chain-reentrancy"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_read_only_reentrancy_patterns(self) -> None:
        graph = load_graph("ReadOnlyReentrancy.sol")
        pattern_ids = [
            "read-only-reentrancy",
            "read-only-balance-share-reentrancy",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("getBalance(address)", self._labels_for(findings, "read-only-reentrancy"))
        self.assertIn("getBalance(address)", self._labels_for(findings, "read-only-balance-share-reentrancy"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_read_only_oracle_reentrancy(self) -> None:
        graph = load_graph("ReadOnlyOracleReentrancy.sol")
        pattern_ids = ["read-only-oracle-reentrancy"]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("getPrice()", self._labels_for(findings, "read-only-oracle-reentrancy"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_token_reentrancy_patterns(self) -> None:
        graph = load_graph("ValueMovementTokens.sol")
        pattern_ids = [
            "erc777-hook-reentrancy",
            "erc721-callback-reentrancy",
            "erc1155-callback-reentrancy",
            "erc4626-vault-reentrancy",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("send777(address,uint256)", self._labels_for(findings, "erc777-hook-reentrancy"))
        self.assertIn("sendNft(address,uint256)", self._labels_for(findings, "erc721-callback-reentrancy"))
        self.assertIn("sendItems(address,uint256[],uint256[])", self._labels_for(findings, "erc1155-callback-reentrancy"))
        self.assertIn("vaultDeposit(uint256)", self._labels_for(findings, "erc4626-vault-reentrancy"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_external_call_safety_patterns(self) -> None:
        graph = load_graph("ValueMovementExternalCalls.sol")
        pattern_ids = [
            "unchecked-return-value",
            "gas-stipend-issue",
            "call-return-data-handling",
            "arbitrary-call-target",
            "arbitrary-calldata",
            "value-forwarding-issue",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("uncheckedCall(address,bytes)", self._labels_for(findings, "unchecked-return-value"))
        self.assertIn("callWithGas(address,bytes)", self._labels_for(findings, "gas-stipend-issue"))
        self.assertIn("decodeReturn(address)", self._labels_for(findings, "call-return-data-handling"))
        self.assertIn("uncheckedCall(address,bytes)", self._labels_for(findings, "arbitrary-call-target"))
        self.assertNotIn("allowedCall(address,bytes)", self._labels_for(findings, "arbitrary-call-target"))
        self.assertIn("uncheckedCall(address,bytes)", self._labels_for(findings, "arbitrary-calldata"))
        self.assertIn("forward(address,bytes)", self._labels_for(findings, "value-forwarding-issue"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_delegatecall_patterns(self) -> None:
        graph = load_graph("ValueMovementDelegatecall.sol")
        pattern_ids = [
            "arbitrary-delegatecall-target",
            "delegatecall-storage-collision",
            "delegatecall-context-issue",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("delegateAny(address,bytes)", self._labels_for(findings, "arbitrary-delegatecall-target"))
        self.assertIn("delegateAny(address,bytes)", self._labels_for(findings, "delegatecall-storage-collision"))
        self.assertIn("delegateWithSender(address,bytes)", self._labels_for(findings, "delegatecall-context-issue"))
        self.assertNotIn("upgradeDelegate(address,bytes)", self._labels_for(findings, "arbitrary-delegatecall-target"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_token_transfer_accounting_patterns(self) -> None:
        graph = load_graph("ValueMovementTokens.sol")
        pattern_ids = [
            "erc20-transfer-issue",
            "token-approval-race",
            "fee-on-transfer-handling",
            "balance-vs-accounting",
            "share-calculation-issue",
            "supply-accounting-issue",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("unsafeTransfer(address,address,uint256)", self._labels_for(findings, "erc20-transfer-issue"))
        self.assertNotIn("customGuardTransfer(address,address,uint256)", self._labels_for(findings, "erc20-transfer-issue"))
        self.assertIn("approveSpender(address,address,uint256)", self._labels_for(findings, "token-approval-race"))
        self.assertIn("feeOnTransferDeposit(address,uint256)", self._labels_for(findings, "fee-on-transfer-handling"))
        self.assertIn("recordSpot()", self._labels_for(findings, "balance-vs-accounting"))
        self.assertNotIn("spotPrice()", self._labels_for(findings, "balance-vs-accounting"))
        self.assertIn("deposit(uint256)", self._labels_for(findings, "share-calculation-issue"))
        self.assertIn("mint(address,uint256)", self._labels_for(findings, "supply-accounting-issue"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_value_extraction_patterns(self) -> None:
        graph = load_graph("ValueExtraction.sol")
        pattern_ids = [
            "withdrawal-without-balance-check",
            "deposit-without-checks",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn("withdraw(uint256)", self._labels_for(findings, "withdrawal-without-balance-check"))
        self.assertIn("deposit(uint256)", self._labels_for(findings, "deposit-without-checks"))

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_flash_loan_patterns(self) -> None:
        graph = load_graph("ValueMovementFlashLoan.sol")
        pattern_ids = [
            "flash-loan-callback-safety",
            "flash-loan-protected-operations",
        ]
        findings = self.engine.run(graph, self.patterns, pattern_ids=pattern_ids, limit=200)

        self.assertIn(
            "executeOperation(address,uint256,uint256,address,bytes)",
            self._labels_for(findings, "flash-loan-callback-safety"),
        )
        self.assertNotIn(
            "safeExecuteOperation(address,uint256,uint256,address,bytes)",
            self._labels_for(findings, "flash-loan-callback-safety"),
        )
        self.assertIn("sensitivePrice()", self._labels_for(findings, "flash-loan-protected-operations"))


if __name__ == "__main__":
    unittest.main()
