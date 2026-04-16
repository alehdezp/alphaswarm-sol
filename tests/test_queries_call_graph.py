"""Call graph query tests for cross-contract paths."""

from __future__ import annotations

import unittest
import pytest

from tests.graph_cache import load_graph
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.intent import ConditionSpec, EdgeSpec, MatchSpec, PathSpec, PathStepSpec
from alphaswarm_sol.queries.planner import QueryPlan

try:
    import slither  # type: ignore  # noqa: F401

    _HAS_SLITHER = True
except Exception:
    _HAS_SLITHER = False


class CallGraphQueryTests(unittest.TestCase):
    """Test suite for CALLS_CONTRACT path queries."""

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_cross_contract_chain_path(self) -> None:
        graph = load_graph("ValueMovementProtocolChain.sol")
        plan = QueryPlan(
            kind="logic",
            node_types=["Function"],
            match=MatchSpec(
                all=[
                    ConditionSpec(
                        property="state_write_after_external_call",
                        op="eq",
                        value=True,
                    )
                ]
            ),
            paths_spec=[
                PathSpec(
                    steps=[
                        PathStepSpec(edge_type="CALLS_CONTRACT", direction="out", target_type="Contract"),
                        PathStepSpec(edge_type="CONTAINS_FUNCTION", direction="out", target_type="Function"),
                        PathStepSpec(edge_type="CALLS_CONTRACT", direction="out", target_type="Contract"),
                    ]
                )
            ],
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("deposit(uint256)", labels)
        self.assertNotIn("depositSafe(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_callback_entrypoint_edge(self) -> None:
        graph = load_graph("ValueMovementCallbacks.sol")
        plan = QueryPlan(
            kind="logic",
            node_types=["Function"],
            match=MatchSpec(
                all=[
                    ConditionSpec(property="callback_entrypoint_surface", op="eq", value=True),
                ]
            ),
            edges_spec=[EdgeSpec(type="CALLS_CONTRACT", direction="out", target_type="Contract")],
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("onSwapCallback(address,uint256,uint256,bytes)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_multi_hop_call_chain_path(self) -> None:
        graph = load_graph("ValueMovementMultiHop.sol")
        plan = QueryPlan(
            kind="logic",
            node_types=["Function"],
            match=MatchSpec(
                all=[
                    ConditionSpec(property="state_write_after_external_call", op="eq", value=True),
                ]
            ),
            paths_spec=[
                PathSpec(
                    steps=[
                        PathStepSpec(edge_type="CALLS_CONTRACT", direction="out", target_type="Contract"),
                        PathStepSpec(edge_type="CONTAINS_FUNCTION", direction="out", target_type="Function"),
                        PathStepSpec(edge_type="CALLS_CONTRACT", direction="out", target_type="Contract"),
                        PathStepSpec(edge_type="CONTAINS_FUNCTION", direction="out", target_type="Function"),
                        PathStepSpec(edge_type="CALLS_CONTRACT", direction="out", target_type="Contract"),
                    ]
                )
            ],
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertIn("execute(uint256)", labels)
        self.assertNotIn("executeSafe(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    def test_internal_chain_no_direct_calls_contract(self) -> None:
        graph = load_graph("ValueMovementInternalChain.sol")
        plan = QueryPlan(
            kind="logic",
            node_types=["Function"],
            match=MatchSpec(
                all=[
                    ConditionSpec(property="state_write_after_external_call", op="eq", value=True),
                ]
            ),
            edges_spec=[EdgeSpec(type="CALLS_CONTRACT", direction="out", target_type="Contract")],
        )
        result = QueryExecutor().execute(graph, plan)
        labels = {node["label"] for node in result["nodes"]}
        self.assertNotIn("outer(uint256)", labels)

    @unittest.skipUnless(_HAS_SLITHER, "slither not available")
    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_path_depth_limit(self) -> None:
        graph = load_graph("ValueMovementMultiHop.sol")
        shallow_plan = QueryPlan(
            kind="logic",
            node_types=["Function"],
            match=MatchSpec(
                all=[
                    ConditionSpec(property="state_write_after_external_call", op="eq", value=True),
                ]
            ),
            paths_spec=[PathSpec(edge_type="CALLS_CONTRACT", direction="out", max_depth=1, target_type="Contract")],
        )
        shallow = QueryExecutor().execute(graph, shallow_plan)
        shallow_labels = {node["label"] for node in shallow["nodes"]}

        deep_plan = QueryPlan(
            kind="logic",
            node_types=["Function"],
            match=MatchSpec(
                all=[
                    ConditionSpec(property="state_write_after_external_call", op="eq", value=True),
                ]
            ),
            paths_spec=[PathSpec(edge_type="CALLS_CONTRACT", direction="out", max_depth=3, target_type="Contract")],
        )
        deep = QueryExecutor().execute(graph, deep_plan)
        deep_labels = {node["label"] for node in deep["nodes"]}

        self.assertIn("execute(uint256)", shallow_labels)
        self.assertIn("execute(uint256)", deep_labels)


if __name__ == "__main__":
    unittest.main()
