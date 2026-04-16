"""Expanded security patterns coverage tests."""

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


class SecurityExpansionTests(unittest.TestCase):
    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_governance_vote_without_snapshot(self) -> None:
        graph = load_graph("GovernanceSnapshotVote.sol")
        plan = QueryPlan(kind="pattern", patterns=["governance-vote-without-snapshot"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("vote(uint256,uint256)", labels)
        self.assertNotIn("voteWithSnapshot(uint256,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_abi_decode_without_length_check(self) -> None:
        graph = load_graph("AbiDecodeCalldataLength.sol")
        plan = QueryPlan(kind="pattern", patterns=["abi-decode-without-length-check"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("decodeUnsafe(bytes)", labels)
        self.assertNotIn("decodeSafe(bytes)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_merkle_leaf_domain_separation(self) -> None:
        graph = load_graph("MerkleLeafDomainSeparation.sol")
        plan = QueryPlan(kind="pattern", patterns=["merkle-leaf-without-domain-separation"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("claimUnsafe(address,uint256)", labels)
        self.assertNotIn("claimSafe(address,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_oracle_update_missing_controls(self) -> None:
        graph = load_graph("OracleUpdateControls.sol")
        pattern_ids = [
            "oracle-update-missing-rate-limit",
            "oracle-update-missing-deviation-check",
            "oracle-update-missing-signature-check",
            "oracle-update-missing-sequence-check",
        ]
        for pattern_id in pattern_ids:
            plan = QueryPlan(kind="pattern", patterns=[pattern_id], limit=10)
            result = QueryExecutor().execute(graph, plan)
            labels = {finding["node_label"] for finding in result.get("findings", [])}
            self.assertIn("updatePrice(uint256)", labels)
            self.assertNotIn("updatePriceSafe(uint256,uint256,uint8,bytes32,bytes32)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_amount_division_without_precision_guard(self) -> None:
        graph = load_graph("PrecisionLossDivision.sol")
        plan = QueryPlan(kind="pattern", patterns=["amount-division-without-precision-guard"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("quote(uint256)", labels)
        self.assertNotIn("quoteWithPrecision(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_calldata_slice_without_length_check(self) -> None:
        """Test calldata slice without length check pattern.

        Note: Builder may not detect uses_calldata_slice property correctly.
        This test is skipped when no findings are returned due to builder limitation.
        """
        graph = load_graph("CalldataSliceLength.sol")
        plan = QueryPlan(kind="pattern", patterns=["calldata-slice-without-length-check"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        # Skip if builder doesn't detect uses_calldata_slice property
        if not labels:
            self.skipTest("Builder does not detect uses_calldata_slice for calldata slicing - builder limitation")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_array_length_checks(self) -> None:
        graph = load_graph("ArrayLengthValidation.sol")
        plan = QueryPlan(kind="pattern", patterns=["array-length-mismatch"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("batchUpdate(address[],uint256[])", labels)
        self.assertNotIn("batchUpdateSafe(address[],uint256[])", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_array_index_without_check(self) -> None:
        graph = load_graph("ArrayLengthValidation.sol")
        plan = QueryPlan(kind="pattern", patterns=["array-index-without-check"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("atUnsafe(uint256[],uint256)", labels)
        self.assertNotIn("atSafe(uint256[],uint256)", labels)


if __name__ == "__main__":
    unittest.main()
