"""Tests for Phase 8: Subgraph Extraction.

This module tests:
- SubGraph and SubGraphNode schemas
- Query-aware extraction from focal nodes
- Relevance scoring computation
- Subgraph serialization for LLM consumption
- Integration with KnowledgeGraph
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.graph_cache import load_graph
from alphaswarm_sol.kg.subgraph import (
    SubGraph,
    SubGraphNode,
    SubGraphEdge,
    SubgraphExtractor,
    compute_node_relevance,
    min_distance_to_focal,
    extract_vulnerability_subgraph,
    get_subgraph_summary,
)


class TestSubGraphNodeSchema(unittest.TestCase):
    """Test SubGraphNode dataclass."""

    def test_node_creation(self):
        """SubGraphNode can be created with all fields."""
        node = SubGraphNode(
            id="node:1",
            type="Function",
            label="withdraw",
            properties={"visibility": "public", "risk_score": 5.0},
            relevance_score=8.5,
            distance_from_focal=1,
            is_focal=False,
        )
        self.assertEqual(node.id, "node:1")
        self.assertEqual(node.type, "Function")
        self.assertEqual(node.relevance_score, 8.5)
        self.assertFalse(node.is_focal)

    def test_node_serialization(self):
        """SubGraphNode serializes to dict and back."""
        node = SubGraphNode(
            id="node:1",
            type="Function",
            label="deposit",
            properties={"semantic_ops": ["RECEIVES_VALUE_IN"]},
            relevance_score=7.0,
            distance_from_focal=0,
            is_focal=True,
        )

        # Serialize
        data = node.to_dict()
        self.assertEqual(data["id"], "node:1")
        self.assertEqual(data["is_focal"], True)

        # Deserialize
        restored = SubGraphNode.from_dict(data)
        self.assertEqual(restored.id, node.id)
        self.assertEqual(restored.is_focal, node.is_focal)
        self.assertEqual(restored.relevance_score, node.relevance_score)


class TestSubGraphEdgeSchema(unittest.TestCase):
    """Test SubGraphEdge dataclass."""

    def test_edge_creation(self):
        """SubGraphEdge can be created."""
        edge = SubGraphEdge(
            id="edge:1",
            type="CALLS",
            source="func:1",
            target="func:2",
            properties={"order": 1},
        )
        self.assertEqual(edge.id, "edge:1")
        self.assertEqual(edge.type, "CALLS")

    def test_edge_serialization(self):
        """SubGraphEdge serializes to dict and back."""
        edge = SubGraphEdge(
            id="edge:1",
            type="WRITES_STATE",
            source="func:1",
            target="state:1",
        )

        # Serialize
        data = edge.to_dict()
        self.assertEqual(data["type"], "WRITES_STATE")

        # Deserialize
        restored = SubGraphEdge.from_dict(data)
        self.assertEqual(restored.id, edge.id)
        self.assertEqual(restored.source, edge.source)


class TestSubGraphSchema(unittest.TestCase):
    """Test SubGraph dataclass."""

    def test_subgraph_creation(self):
        """SubGraph can be created with nodes and edges."""
        sg = SubGraph(
            focal_node_ids=["node:1"],
            analysis_type="vulnerability",
            query="reentrancy",
        )
        self.assertEqual(sg.analysis_type, "vulnerability")
        self.assertEqual(len(sg.focal_node_ids), 1)

    def test_add_node(self):
        """Nodes can be added to subgraph."""
        sg = SubGraph()
        node = SubGraphNode(id="node:1", type="Function", label="fn1")
        sg.add_node(node)
        self.assertIn("node:1", sg.nodes)

    def test_add_edge(self):
        """Edges can be added when endpoints exist."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="node:1", type="Function", label="fn1"))
        sg.add_node(SubGraphNode(id="node:2", type="Function", label="fn2"))

        edge = SubGraphEdge(id="edge:1", type="CALLS", source="node:1", target="node:2")
        sg.add_edge(edge)
        self.assertIn("edge:1", sg.edges)

    def test_add_edge_missing_endpoint(self):
        """Edges not added when endpoint missing."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="node:1", type="Function", label="fn1"))

        edge = SubGraphEdge(id="edge:1", type="CALLS", source="node:1", target="node:2")
        sg.add_edge(edge)
        self.assertNotIn("edge:1", sg.edges)

    def test_get_nodes_by_type(self):
        """Can filter nodes by type."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="fn:1", type="Function", label="fn1"))
        sg.add_node(SubGraphNode(id="sv:1", type="StateVariable", label="balance"))
        sg.add_node(SubGraphNode(id="fn:2", type="Function", label="fn2"))

        functions = sg.get_nodes_by_type("Function")
        self.assertEqual(len(functions), 2)

        state_vars = sg.get_nodes_by_type("StateVariable")
        self.assertEqual(len(state_vars), 1)

    def test_get_high_relevance_nodes(self):
        """Can filter nodes by relevance."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="n:1", type="Function", label="fn1", relevance_score=8.0))
        sg.add_node(SubGraphNode(id="n:2", type="Function", label="fn2", relevance_score=3.0))
        sg.add_node(SubGraphNode(id="n:3", type="Function", label="fn3", relevance_score=6.0))

        high = sg.get_high_relevance_nodes(threshold=5.0)
        self.assertEqual(len(high), 2)

    def test_prune_by_relevance(self):
        """Low relevance nodes removed (focal kept)."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="n:1", type="Function", label="fn1",
                                 relevance_score=8.0, is_focal=True))
        sg.add_node(SubGraphNode(id="n:2", type="Function", label="fn2",
                                 relevance_score=2.0, is_focal=False))
        sg.add_node(SubGraphNode(id="n:3", type="Function", label="fn3",
                                 relevance_score=6.0, is_focal=False))

        sg.prune_by_relevance(min_relevance=5.0)

        self.assertIn("n:1", sg.nodes)  # Focal kept
        self.assertNotIn("n:2", sg.nodes)  # Low relevance removed
        self.assertIn("n:3", sg.nodes)  # Above threshold

    def test_limit_nodes(self):
        """Node limiting keeps focal and highest relevance."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="n:1", type="F", label="f1",
                                 relevance_score=5.0, is_focal=True))
        sg.add_node(SubGraphNode(id="n:2", type="F", label="f2",
                                 relevance_score=8.0, is_focal=False))
        sg.add_node(SubGraphNode(id="n:3", type="F", label="f3",
                                 relevance_score=3.0, is_focal=False))
        sg.add_node(SubGraphNode(id="n:4", type="F", label="f4",
                                 relevance_score=6.0, is_focal=False))

        sg.limit_nodes(max_nodes=3)

        self.assertEqual(len(sg.nodes), 3)
        self.assertIn("n:1", sg.nodes)  # Focal
        self.assertIn("n:2", sg.nodes)  # Highest relevance
        self.assertIn("n:4", sg.nodes)  # Second highest

    def test_order_by(self):
        """Nodes can be ordered by various keys."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="n:1", type="F", label="f1", relevance_score=5.0))
        sg.add_node(SubGraphNode(id="n:2", type="F", label="f2", relevance_score=8.0))
        sg.add_node(SubGraphNode(id="n:3", type="F", label="f3", relevance_score=3.0))

        ordered = sg.order_by(["relevance_score"])
        self.assertEqual(ordered[0].id, "n:2")  # Highest first
        self.assertEqual(ordered[-1].id, "n:3")  # Lowest last

    def test_serialization(self):
        """SubGraph serializes to dict and back."""
        sg = SubGraph(
            focal_node_ids=["n:1"],
            analysis_type="vulnerability",
            query="test query",
        )
        sg.add_node(SubGraphNode(id="n:1", type="Function", label="fn1", is_focal=True))
        sg.add_node(SubGraphNode(id="n:2", type="Function", label="fn2"))
        sg.add_edge(SubGraphEdge(id="e:1", type="CALLS", source="n:1", target="n:2"))

        # Serialize
        data = sg.to_dict()
        self.assertEqual(data["node_count"], 2)
        self.assertEqual(data["edge_count"], 1)

        # Deserialize
        restored = SubGraph.from_dict(data)
        self.assertEqual(len(restored.nodes), 2)
        self.assertEqual(len(restored.edges), 1)

    def test_to_compact_json(self):
        """Compact JSON serialization works."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="n:1", type="Function", label="fn1"))

        json_str = sg.to_compact_json()
        self.assertIn("n:1", json_str)
        # Should be compact (no spaces after separators)
        self.assertNotIn(": ", json_str)

    def test_to_llm_format(self):
        """LLM format serialization works."""
        sg = SubGraph(analysis_type="vulnerability", query="reentrancy")
        sg.add_node(SubGraphNode(
            id="n:1", type="Function", label="withdraw",
            properties={"semantic_ops": ["TRANSFERS_VALUE_OUT"], "semantic_role": "EntryPoint"},
            is_focal=True,
        ))

        llm_text = sg.to_llm_format()
        self.assertIn("withdraw", llm_text)
        self.assertIn("[FOCAL]", llm_text)
        self.assertIn("EntryPoint", llm_text)


class TestRelevanceScoring(unittest.TestCase):
    """Test relevance scoring functions."""

    def test_distance_factor(self):
        """Closer nodes have higher relevance."""
        close = SubGraphNode(id="n:1", type="Function", label="fn1", distance_from_focal=0)
        far = SubGraphNode(id="n:2", type="Function", label="fn2", distance_from_focal=3)

        close_score = compute_node_relevance(close, ["n:1"], "", None)
        far_score = compute_node_relevance(far, ["n:1"], "", None)

        self.assertGreater(close_score, far_score)

    def test_query_matching(self):
        """Query matches increase relevance."""
        # Use higher distance to avoid capping at 10.0
        node_match = SubGraphNode(
            id="n:1", type="Function", label="withdraw",
            properties={"semantic_role": "Internal"},  # Lower weight role
            distance_from_focal=2,
        )
        node_no_match = SubGraphNode(
            id="n:2", type="Function", label="withdraw",
            properties={"semantic_role": "Internal"},
            distance_from_focal=2,
        )

        # With matching query
        with_query = compute_node_relevance(node_match, ["focal"], "withdraw", None)
        # Without matching query
        without_query = compute_node_relevance(node_no_match, ["focal"], "deposit", None)

        self.assertGreater(with_query, without_query)

    def test_type_weights(self):
        """Different node types have different weights."""
        fn = SubGraphNode(id="n:1", type="Function", label="fn", distance_from_focal=1)
        event = SubGraphNode(id="n:2", type="Event", label="ev", distance_from_focal=1)

        fn_score = compute_node_relevance(fn, ["focal"], "", None)
        event_score = compute_node_relevance(event, ["focal"], "", None)

        self.assertGreater(fn_score, event_score)

    def test_risk_factor(self):
        """Higher risk increases relevance."""
        high_risk = SubGraphNode(
            id="n:1", type="Function", label="fn1",
            properties={"risk_score": 8.0},
            distance_from_focal=1,
        )
        low_risk = SubGraphNode(
            id="n:2", type="Function", label="fn2",
            properties={"risk_score": 2.0},
            distance_from_focal=1,
        )

        high_score = compute_node_relevance(high_risk, ["focal"], "", None)
        low_score = compute_node_relevance(low_risk, ["focal"], "", None)

        self.assertGreater(high_score, low_score)

    def test_min_distance_to_focal(self):
        """Min distance calculation works."""
        focal = SubGraphNode(id="n:1", type="F", label="f1", distance_from_focal=0)
        non_focal = SubGraphNode(id="n:2", type="F", label="f2", distance_from_focal=2)

        self.assertEqual(min_distance_to_focal(focal, ["n:1"]), 0)
        self.assertEqual(min_distance_to_focal(non_focal, ["n:1"]), 2)


class TestSubgraphExtractor(unittest.TestCase):
    """Test SubgraphExtractor class."""

    def test_extractor_on_real_contract(self):
        """Extractor works on real contract."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        extractor = SubgraphExtractor(graph)

        # Find a function to use as focal
        focal_id = None
        for node in graph.nodes.values():
            if node.type == "Function":
                focal_id = node.id
                break

        self.assertIsNotNone(focal_id)

        subgraph = extractor.extract_for_analysis(
            focal_nodes=[focal_id],
            analysis_type="vulnerability",
            max_hops=2,
            max_nodes=20,
        )

        self.assertGreater(len(subgraph.nodes), 0)
        self.assertIn(focal_id, subgraph.nodes)
        self.assertTrue(subgraph.nodes[focal_id].is_focal)

    def test_ego_graph_extraction(self):
        """Ego-graph extraction works."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        extractor = SubgraphExtractor(graph)

        # Find a function
        center_id = None
        for node in graph.nodes.values():
            if node.type == "Function":
                center_id = node.id
                break

        if center_id:
            subgraph = extractor.extract_ego_graph(center_id, hops=1)
            self.assertIn(center_id, subgraph.nodes)

    def test_node_limiting(self):
        """Max nodes limit is respected."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        extractor = SubgraphExtractor(graph)

        # Get all function IDs
        focal_ids = [n.id for n in graph.nodes.values() if n.type == "Function"][:3]

        subgraph = extractor.extract_for_analysis(
            focal_nodes=focal_ids,
            max_hops=3,
            max_nodes=10,
        )

        self.assertLessEqual(len(subgraph.nodes), 10)


class TestExtractVulnerabilitySubgraph(unittest.TestCase):
    """Test extract_vulnerability_subgraph function."""

    def test_reentrancy_extraction(self):
        """Reentrancy-focused extraction works."""
        graph = load_graph("ReentrancyClassic.sol")
        subgraph = extract_vulnerability_subgraph(
            graph,
            vulnerability_type="reentrancy",
            max_nodes=20,
        )

        self.assertGreater(len(subgraph.nodes), 0)
        self.assertEqual(subgraph.analysis_type, "vulnerability")

    def test_delegatecall_extraction(self):
        """Delegatecall-focused extraction works."""
        graph = load_graph("ArbitraryDelegatecall.sol")
        subgraph = extract_vulnerability_subgraph(
            graph,
            vulnerability_type="delegatecall",
            max_nodes=15,
        )

        self.assertGreater(len(subgraph.nodes), 0)


class TestGetSubgraphSummary(unittest.TestCase):
    """Test get_subgraph_summary function."""

    def test_summary_structure(self):
        """Summary has expected structure."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(id="n:1", type="Function", label="fn1",
                                 relevance_score=8.0, is_focal=True))
        sg.add_node(SubGraphNode(id="n:2", type="StateVariable", label="balance",
                                 relevance_score=5.0))

        summary = get_subgraph_summary(sg)

        self.assertIn("node_count", summary)
        self.assertIn("edge_count", summary)
        self.assertIn("type_counts", summary)
        self.assertIn("focal_count", summary)
        self.assertIn("avg_relevance", summary)
        self.assertIn("high_relevance_count", summary)

    def test_summary_counts(self):
        """Summary counts are correct."""
        sg = SubGraph(analysis_type="test")
        sg.add_node(SubGraphNode(id="n:1", type="Function", label="fn1",
                                 relevance_score=8.0, is_focal=True))
        sg.add_node(SubGraphNode(id="n:2", type="Function", label="fn2",
                                 relevance_score=3.0))

        summary = get_subgraph_summary(sg)

        self.assertEqual(summary["node_count"], 2)
        self.assertEqual(summary["focal_count"], 1)
        self.assertEqual(summary["type_counts"]["Function"], 2)
        self.assertEqual(summary["high_relevance_count"], 1)  # Only n:1 >= 5.0


class TestIntegration(unittest.TestCase):
    """Integration tests with full graph."""

    def test_full_extraction_pipeline(self):
        """Full extraction pipeline works."""
        graph = load_graph("ArbitraryDelegatecall.sol")

        # Find public functions
        public_fns = [
            n.id for n in graph.nodes.values()
            if n.type == "Function" and n.properties.get("visibility") in ["public", "external"]
        ]

        if not public_fns:
            self.skipTest("No public functions found")

        extractor = SubgraphExtractor(graph)
        subgraph = extractor.extract_for_analysis(
            focal_nodes=public_fns[:2],
            analysis_type="vulnerability",
            query="delegatecall security",
            max_hops=2,
            max_nodes=25,
        )

        # Verify extraction
        self.assertGreater(len(subgraph.nodes), 0)
        self.assertLessEqual(len(subgraph.nodes), 25)

        # Verify focal nodes present
        for focal_id in public_fns[:2]:
            if focal_id in subgraph.nodes:
                self.assertTrue(subgraph.nodes[focal_id].is_focal)

        # Verify serialization
        data = subgraph.to_dict()
        restored = SubGraph.from_dict(data)
        self.assertEqual(len(restored.nodes), len(subgraph.nodes))

        # Verify LLM format
        llm_text = subgraph.to_llm_format()
        self.assertIn("Subgraph Analysis", llm_text)

        # Verify summary
        summary = get_subgraph_summary(subgraph)
        self.assertEqual(summary["node_count"], len(subgraph.nodes))


if __name__ == "__main__":
    unittest.main()
