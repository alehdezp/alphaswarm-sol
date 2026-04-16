"""Pattern pack regression tests."""

from __future__ import annotations

import unittest
from alphaswarm_sol.kg.schema import Edge, KnowledgeGraph, Node
from alphaswarm_sol.queries.patterns import PatternEngine
from tests.pattern_loader import load_all_patterns


class PatternPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = list(load_all_patterns())
        self.engine = PatternEngine()

    def _make_graph(self) -> KnowledgeGraph:
        graph = KnowledgeGraph(metadata={"test": True})
        fn = Node(
            id="func:1",
            type="Function",
            label="withdraw",
            properties={
                "visibility": "public",
                "writes_state": True,
                "has_access_gate": False,
                "attacker_controlled_write": True,
                "uses_delegatecall": True,
                "has_user_input": True,
            },
        )
        state = Node(id="state:1", type="StateVariable", label="balances", properties={})
        graph.add_node(fn)
        graph.add_node(state)
        graph.add_edge(
            Edge(
                id="edge:1",
                type="FUNCTION_INPUT_TAINTS_STATE",
                source=fn.id,
                target=state.id,
            )
        )
        return graph

    def test_weak_access_control_matches(self) -> None:
        graph = self._make_graph()
        findings = self.engine.run(graph, self.patterns, pattern_ids=["weak-access-control"])
        self.assertTrue(any(f["pattern_id"] == "weak-access-control" for f in findings))

    def test_attacker_controlled_write_matches(self) -> None:
        graph = self._make_graph()
        findings = self.engine.run(graph, self.patterns, pattern_ids=["attacker-controlled-write"])
        self.assertTrue(any(f["pattern_id"] == "attacker-controlled-write" for f in findings))

    def test_dataflow_edge_matches(self) -> None:
        graph = self._make_graph()
        findings = self.engine.run(graph, self.patterns, pattern_ids=["dataflow-input-taints-state"])
        self.assertTrue(any(f["pattern_id"] == "dataflow-input-taints-state" for f in findings))

    def test_explain_mode(self) -> None:
        graph = self._make_graph()
        findings = self.engine.run(
            graph,
            self.patterns,
            pattern_ids=["weak-access-control"],
            explain=True,
        )
        self.assertTrue(findings)
        self.assertIn("explain", findings[0])


if __name__ == "__main__":
    unittest.main()
