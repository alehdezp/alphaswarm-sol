"""Invariant layer query tests."""

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


class InvariantQueryTests(unittest.TestCase):
    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_invariant_nodes_extracted(self) -> None:
        graph = load_graph("TotalSupplyInvariant.sol")
        plan = QueryPlan(kind="nodes", node_types=["Invariant"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("invariant:totalSupply", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_invariant_touch_without_check_total_supply(self) -> None:
        graph = load_graph("TotalSupplyInvariant.sol")
        plan = QueryPlan(kind="pattern", patterns=["invariant-touch-without-check"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("burn(address,uint256)", labels)
        self.assertNotIn("mint(address,uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_invariant_touch_without_check_vault(self) -> None:
        graph = load_graph("VaultInflation.sol")
        plan = QueryPlan(kind="pattern", patterns=["invariant-touch-without-check"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("skim(uint256)", labels)
        self.assertNotIn("deposit(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_invariant_nodes_from_config(self) -> None:
        graph = load_graph("InvariantConfigFixture.sol")
        plan = QueryPlan(kind="nodes", node_types=["Invariant"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        nodes = result["nodes"]
        labels = {node["label"] for node in nodes}
        self.assertIn("invariant:InvariantConfigFixture", labels)
        self.assertIn("invariant:totalSupplyHash", labels)
        hash_node = next(node for node in nodes if node["label"] == "invariant:totalSupplyHash")
        self.assertEqual(hash_node["properties"]["state_vars"], ["totalSupplyHash"])
        self.assertEqual(hash_node["properties"]["source_kind"], "config")

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_invariant_guard_functions_and_internal_calls(self) -> None:
        graph = load_graph("InvariantConfigFixture.sol")
        plan = QueryPlan(kind="pattern", patterns=["invariant-touch-without-check"], limit=20)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("skim(uint256)", labels)
        self.assertIn("updateHash(bytes32)", labels)
        self.assertNotIn("deposit(uint256)", labels)
        self.assertNotIn("guardedByName(uint256)", labels)
        self.assertNotIn("withdraw(uint256)", labels)
        self.assertNotIn("adjust(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_invariant_modifier_and_assert_checks(self) -> None:
        graph = load_graph("InvariantModifierFixture.sol")
        plan = QueryPlan(kind="pattern", patterns=["invariant-touch-without-check"], limit=20)
        result = QueryExecutor().execute(graph, plan)
        labels = {finding["node_label"] for finding in result.get("findings", [])}
        self.assertIn("unsafeMint(uint256)", labels)
        self.assertNotIn("mint(uint256)", labels)
        self.assertNotIn("assertCheck(uint256)", labels)
        self.assertNotIn("internalChecked(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_invariant_ast_expression_mining(self) -> None:
        graph = load_graph("InvariantModifierFixture.sol")
        plan = QueryPlan(kind="nodes", node_types=["Invariant"], limit=10)
        result = QueryExecutor().execute(graph, plan)
        nodes = result["nodes"]
        labels = {node["label"] for node in nodes}
        self.assertIn("invariant:totalSupply", labels)
        inv_node = next(node for node in nodes if node["label"] == "invariant:totalSupply")
        self.assertEqual(
            sorted(inv_node["properties"]["state_vars"]),
            ["cap", "pendingSupply", "totalSupply"],
        )


if __name__ == "__main__":
    unittest.main()
