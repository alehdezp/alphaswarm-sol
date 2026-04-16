"""Tests for Task 9.6: PPR-based Subgraph Extraction."""

import unittest
from unittest.mock import MagicMock, patch

from alphaswarm_sol.kg.ppr_subgraph import (
    PPRExtractionConfig,
    PPRSubgraphExtractor,
    PPRSubgraphResult,
    extract_ppr_subgraph,
    extract_ppr_subgraph_for_findings,
)
from alphaswarm_sol.kg.subgraph import SubGraph


def create_mock_graph(num_functions: int = 5, include_state_vars: bool = True):
    """Create a mock graph for testing."""
    graph = MagicMock()

    nodes = {}

    # Create function nodes
    for i in range(num_functions):
        func_id = f"func{i}"
        nodes[func_id] = MagicMock(
            id=func_id,
            type="Function",
            label=f"function{i}",
            properties={
                "name": f"function{i}",
                "visibility": "public" if i % 2 == 0 else "internal",
                "writes_state": i < 3,
                "has_external_calls": i == 0,
                "state_variables_written_names": [f"var{i}"] if i < 3 else [],
            },
        )

    # Create state variable nodes
    if include_state_vars:
        for i in range(3):
            var_id = f"var{i}"
            nodes[var_id] = MagicMock(
                id=var_id,
                type="StateVariable",
                label=f"var{i}",
                properties={"security_tags": []},
            )

    graph.nodes = nodes

    # Create edges (function -> state vars, function -> function)
    edges = {}
    edge_idx = 0

    for i in range(num_functions):
        # Function calls
        if i < num_functions - 1:
            edges[f"e{edge_idx}"] = MagicMock(
                id=f"e{edge_idx}",
                type="calls",
                source=f"func{i}",
                target=f"func{i+1}",
                properties={},
            )
            edge_idx += 1

        # State writes
        if i < 3 and include_state_vars:
            edges[f"e{edge_idx}"] = MagicMock(
                id=f"e{edge_idx}",
                type="writes_state",
                source=f"func{i}",
                target=f"var{i}",
                properties={},
            )
            edge_idx += 1

    graph.edges = edges

    return graph


class TestPPRExtractionConfig(unittest.TestCase):
    """Test PPRExtractionConfig dataclass."""

    def test_default_config(self):
        config = PPRExtractionConfig()
        self.assertEqual(config.context_mode, "standard")
        self.assertEqual(config.max_nodes, 50)
        self.assertTrue(config.include_edges)

    def test_strict_config(self):
        config = PPRExtractionConfig.strict()
        self.assertEqual(config.context_mode, "strict")
        self.assertEqual(config.max_nodes, 30)
        self.assertGreater(config.min_relevance, 0.001)

    def test_standard_config(self):
        config = PPRExtractionConfig.standard()
        self.assertEqual(config.context_mode, "standard")
        self.assertEqual(config.max_nodes, 50)

    def test_relaxed_config(self):
        config = PPRExtractionConfig.relaxed()
        self.assertEqual(config.context_mode, "relaxed")
        self.assertEqual(config.max_nodes, 100)
        self.assertLess(config.min_relevance, 0.001)


class TestPPRSubgraphExtractor(unittest.TestCase):
    """Test PPRSubgraphExtractor class."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.extractor = PPRSubgraphExtractor(self.graph)

    def test_initialization(self):
        self.assertIn("func0", self.extractor._node_ids)
        self.assertIn("var0", self.extractor._node_ids)
        self.assertIsNotNone(self.extractor.seed_mapper)

    def test_extract_from_seeds_basic(self):
        result = self.extractor.extract_from_seeds(["func0"])

        self.assertIsInstance(result, PPRSubgraphResult)
        self.assertIsInstance(result.subgraph, SubGraph)
        self.assertIn("func0", result.subgraph.nodes)
        self.assertTrue(result.ppr_result.converged)

    def test_extract_from_seeds_config(self):
        config = PPRExtractionConfig.strict()
        result = self.extractor.extract_from_seeds(["func0"], config)

        # Strict mode should have fewer nodes
        self.assertLessEqual(len(result.subgraph.nodes), config.max_nodes)
        self.assertEqual(result.config.context_mode, "strict")

    def test_extract_from_findings(self):
        findings = [
            {"node_id": "func0", "severity": "high"},
            {"node_id": "func1", "severity": "medium"},
        ]

        result = self.extractor.extract_from_findings(findings)

        self.assertIn("func0", result.subgraph.nodes)
        self.assertIn("func1", result.subgraph.nodes)
        self.assertEqual(len(result.seed_mapping.primary_seeds), 2)

    def test_extract_from_pattern(self):
        pattern_results = [
            {"node_id": "func0", "score": 0.9},
        ]

        result = self.extractor.extract_from_pattern(
            pattern_results,
            pattern_id="test-pattern",
        )

        self.assertIn("func0", result.subgraph.nodes)

    def test_extract_from_function_names(self):
        result = self.extractor.extract_from_function_names(["function0", "function1"])

        # Should find func0 and func1 by label
        self.assertIn("func0", result.subgraph.nodes)
        self.assertIn("func1", result.subgraph.nodes)

    def test_extract_empty_seeds(self):
        result = self.extractor.extract_from_seeds([])

        self.assertTrue(result.subgraph.nodes == {} or len(result.subgraph.nodes) == 0)
        self.assertIn("error", result.stats)

    def test_extract_invalid_seeds(self):
        result = self.extractor.extract_from_seeds(["nonexistent"])

        # Should handle gracefully
        self.assertEqual(len(result.seed_mapping.warnings), 1)

    def test_focal_nodes_marked(self):
        result = self.extractor.extract_from_seeds(["func0", "func1"])

        func0 = result.subgraph.nodes.get("func0")
        func1 = result.subgraph.nodes.get("func1")

        self.assertTrue(func0.is_focal)
        self.assertTrue(func1.is_focal)

    def test_ppr_score_in_properties(self):
        result = self.extractor.extract_from_seeds(["func0"])

        for node in result.subgraph.nodes.values():
            self.assertIn("ppr_score", node.properties)

    def test_relevance_scoring(self):
        result = self.extractor.extract_from_seeds(["func0"])

        func0 = result.subgraph.nodes.get("func0")
        self.assertEqual(func0.relevance_score, 10.0)  # Focal = max relevance

        # Non-focal nodes should have lower relevance
        for node in result.subgraph.nodes.values():
            if not node.is_focal:
                self.assertLess(node.relevance_score, 10.0)

    def test_edges_included(self):
        result = self.extractor.extract_from_seeds(
            ["func0", "func1"],
            PPRExtractionConfig(include_edges=True),
        )

        # Should have edge from func0 -> func1
        self.assertGreater(len(result.subgraph.edges), 0)

    def test_edges_excluded(self):
        result = self.extractor.extract_from_seeds(
            ["func0", "func1"],
            PPRExtractionConfig(include_edges=False),
        )

        self.assertEqual(len(result.subgraph.edges), 0)

    def test_state_variable_expansion(self):
        result = self.extractor.extract_from_seeds(
            ["func0"],
            PPRExtractionConfig(expand_state_vars=True),
        )

        # func0 writes to var0, which should be included
        self.assertIn("var0", result.subgraph.nodes)


class TestPPRSubgraphExtractorContextModes(unittest.TestCase):
    """Test context mode differences."""

    def setUp(self):
        # Create a larger graph for context mode testing
        self.graph = create_mock_graph(num_functions=20)
        self.extractor = PPRSubgraphExtractor(self.graph)

    def test_strict_mode_fewer_nodes(self):
        strict_result = self.extractor.extract_from_seeds(
            ["func0"],
            PPRExtractionConfig.strict(),
        )
        relaxed_result = self.extractor.extract_from_seeds(
            ["func0"],
            PPRExtractionConfig.relaxed(),
        )

        self.assertLessEqual(
            len(strict_result.subgraph.nodes),
            len(relaxed_result.subgraph.nodes),
        )

    def test_context_modes_converge(self):
        for mode in ["strict", "standard", "relaxed"]:
            config = getattr(PPRExtractionConfig, mode)()
            result = self.extractor.extract_from_seeds(["func0"], config)

            self.assertTrue(result.ppr_result.converged)


class TestPPRSubgraphResult(unittest.TestCase):
    """Test PPRSubgraphResult dataclass."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.extractor = PPRSubgraphExtractor(self.graph)

    def test_get_top_nodes(self):
        result = self.extractor.extract_from_seeds(["func0"])

        top_nodes = result.get_top_nodes(k=3)
        self.assertLessEqual(len(top_nodes), 3)

        # Top node should be seed
        if top_nodes:
            top_id, top_score = top_nodes[0]
            self.assertEqual(top_id, "func0")

    def test_token_estimate(self):
        result = self.extractor.extract_from_seeds(["func0"])

        estimate = result.get_token_estimate()
        self.assertGreater(estimate, 0)
        # Estimate should scale with nodes + edges
        expected_min = len(result.subgraph.nodes) * 50
        self.assertGreaterEqual(estimate, expected_min)

    def test_stats_populated(self):
        result = self.extractor.extract_from_seeds(["func0"])

        self.assertIn("total_graph_nodes", result.stats)
        self.assertIn("extracted_nodes", result.stats)
        self.assertIn("ppr_converged", result.stats)
        self.assertIn("reduction_ratio", result.stats)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        self.graph = create_mock_graph()

    def test_extract_ppr_subgraph(self):
        subgraph = extract_ppr_subgraph(
            self.graph,
            seeds=["func0"],
            context_mode="standard",
            max_nodes=10,
        )

        self.assertIsInstance(subgraph, SubGraph)
        self.assertIn("func0", subgraph.nodes)
        self.assertLessEqual(len(subgraph.nodes), 10)

    def test_extract_ppr_subgraph_modes(self):
        for mode in ["strict", "standard", "relaxed"]:
            subgraph = extract_ppr_subgraph(
                self.graph,
                seeds=["func0"],
                context_mode=mode,
            )
            self.assertIn("func0", subgraph.nodes)

    def test_extract_ppr_subgraph_for_findings(self):
        findings = [
            {"node_id": "func0", "severity": "high"},
        ]

        result = extract_ppr_subgraph_for_findings(
            self.graph,
            findings,
            context_mode="standard",
        )

        self.assertIsInstance(result, PPRSubgraphResult)
        self.assertIn("func0", result.subgraph.nodes)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_graph(self):
        graph = MagicMock()
        graph.nodes = {}
        graph.edges = {}

        extractor = PPRSubgraphExtractor(graph)
        result = extractor.extract_from_seeds(["func0"])

        self.assertEqual(len(result.subgraph.nodes), 0)

    def test_graph_without_edges(self):
        graph = MagicMock()
        graph.nodes = {
            "func0": MagicMock(
                id="func0",
                type="Function",
                label="func0",
                properties={},
            ),
        }
        graph.edges = {}

        extractor = PPRSubgraphExtractor(graph)
        result = extractor.extract_from_seeds(["func0"])

        self.assertIn("func0", result.subgraph.nodes)

    def test_dict_graph_format(self):
        """Test with dictionary-based nodes."""
        graph = MagicMock()
        graph.nodes = {
            "func0": {
                "id": "func0",
                "type": "Function",
                "label": "func0",
                "properties": {},
            },
        }
        graph.edges = {}

        extractor = PPRSubgraphExtractor(graph)
        result = extractor.extract_from_seeds(["func0"])

        self.assertIn("func0", result.subgraph.nodes)

    def test_max_nodes_limit(self):
        graph = create_mock_graph(num_functions=100)
        extractor = PPRSubgraphExtractor(graph)

        config = PPRExtractionConfig(max_nodes=5)
        result = extractor.extract_from_seeds(["func0"], config)

        self.assertLessEqual(len(result.subgraph.nodes), 5)


class TestRelevanceScoring(unittest.TestCase):
    """Test relevance score computation."""

    def setUp(self):
        self.graph = create_mock_graph()
        self.extractor = PPRSubgraphExtractor(self.graph)

    def test_ppr_to_relevance_focal(self):
        # Focal nodes always get max relevance
        relevance = self.extractor._ppr_to_relevance(0.5, is_focal=True)
        self.assertEqual(relevance, 10.0)

    def test_ppr_to_relevance_high_score(self):
        # High PPR score -> higher relevance than low score
        high_relevance = self.extractor._ppr_to_relevance(0.1, is_focal=False)
        low_relevance = self.extractor._ppr_to_relevance(0.001, is_focal=False)
        self.assertGreater(high_relevance, low_relevance)

    def test_ppr_to_relevance_low_score(self):
        # Low PPR score -> low relevance
        relevance = self.extractor._ppr_to_relevance(0.0001, is_focal=False)
        self.assertLess(relevance, 5.0)

    def test_ppr_to_relevance_zero(self):
        relevance = self.extractor._ppr_to_relevance(0, is_focal=False)
        self.assertEqual(relevance, 0.0)

    def test_distance_estimation(self):
        # Seeds have distance 0
        dist = self.extractor._estimate_distance("func0", ["func0"], 0.5)
        self.assertEqual(dist, 0)

        # High PPR score = close
        dist = self.extractor._estimate_distance("func1", ["func0"], 0.15)
        self.assertEqual(dist, 1)

        # Medium PPR score
        dist = self.extractor._estimate_distance("func2", ["func0"], 0.05)
        self.assertEqual(dist, 2)

        # Low PPR score = far
        dist = self.extractor._estimate_distance("func3", ["func0"], 0.005)
        self.assertEqual(dist, 3)


class TestIntegration(unittest.TestCase):
    """Integration tests for PPR subgraph extraction."""

    def test_full_extraction_flow(self):
        """Test complete extraction from findings to subgraph."""
        # Use larger graph to ensure reduction happens
        graph = create_mock_graph(num_functions=50)
        extractor = PPRSubgraphExtractor(graph)

        # Start with findings
        findings = [
            {"node_id": "func0", "severity": "critical"},
            {"node_id": "func2", "severity": "high"},
        ]

        # Use strict config to ensure reduction
        result = extractor.extract_from_findings(
            findings,
            PPRExtractionConfig.strict(),  # Strict limits to 30 nodes
        )

        # Verify extraction results
        self.assertIn("func0", result.subgraph.nodes)
        self.assertIn("func2", result.subgraph.nodes)
        self.assertTrue(result.ppr_result.converged)

        # Verify PPR-based ordering
        top_nodes = result.get_top_nodes(k=2)
        top_ids = [n[0] for n in top_nodes]
        self.assertIn("func0", top_ids)
        self.assertIn("func2", top_ids)

        # Verify reduction occurred (50 nodes down to ~30 max)
        self.assertGreater(result.stats["reduction_ratio"], 0)
        self.assertLess(len(result.subgraph.nodes), 50)

    def test_multiple_extractions_same_graph(self):
        """Test multiple extractions on the same graph."""
        graph = create_mock_graph()
        extractor = PPRSubgraphExtractor(graph)

        result1 = extractor.extract_from_seeds(["func0"])
        result2 = extractor.extract_from_seeds(["func1"])

        # Different seeds should give different focal nodes
        self.assertTrue(result1.subgraph.nodes["func0"].is_focal)
        self.assertTrue(result2.subgraph.nodes["func1"].is_focal)


if __name__ == "__main__":
    unittest.main()
