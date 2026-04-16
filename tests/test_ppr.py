"""Tests for PPR algorithm.

Task 9.1: Tests for Personalized PageRank implementation.
"""

import unittest

from alphaswarm_sol.kg.ppr import (
    PPRConfig,
    PPRResult,
    VKGPPR,
    get_relevant_nodes_ppr,
    run_ppr,
)
from alphaswarm_sol.kg.ppr_weights import (
    BASE_WEIGHTS,
    calculate_edge_weight,
    create_analysis_weights,
    get_weight_for_edge_type,
    normalize_weights,
)


class TestEdgeWeights(unittest.TestCase):
    """Test edge weight calculations."""

    def test_base_weight_calls(self):
        """CALLS edge has base weight 1.0."""
        edge = {"type": "calls"}
        weight = calculate_edge_weight(edge)
        self.assertEqual(weight, 1.0)

    def test_base_weight_external_call(self):
        """External call edge has higher weight."""
        edge = {"type": "calls_external"}
        weight = calculate_edge_weight(edge)
        self.assertEqual(weight, 1.5)

    def test_base_weight_delegatecall(self):
        """Delegatecall has highest weight."""
        edge = {"type": "delegatecall"}
        weight = calculate_edge_weight(edge)
        self.assertEqual(weight, 2.0)

    def test_risk_score_increases_weight(self):
        """Risk score increases edge weight."""
        base_edge = {"type": "calls", "risk_score": 0.0}
        risky_edge = {"type": "calls", "risk_score": 0.8}

        base_weight = calculate_edge_weight(base_edge)
        risky_weight = calculate_edge_weight(risky_edge)

        self.assertGreater(risky_weight, base_weight)
        # Should be 1.0 * (1 + 0.8) = 1.8
        self.assertAlmostEqual(risky_weight, 1.8, places=2)

    def test_risk_score_capped(self):
        """Risk score capped at 1.0 for multiplier."""
        edge = {"type": "calls", "risk_score": 2.0}
        weight = calculate_edge_weight(edge)
        # Should cap at 1.0 * (1 + 1.0) = 2.0
        self.assertEqual(weight, 2.0)

    def test_guard_penalty(self):
        """Guard penalty reduces weight."""
        unguarded = {"type": "calls", "guards_at_source": False}
        guarded = {"type": "calls", "guards_at_source": True}

        unguarded_weight = calculate_edge_weight(unguarded)
        guarded_weight = calculate_edge_weight(guarded)

        self.assertGreater(unguarded_weight, guarded_weight)

    def test_taint_increases_weight(self):
        """Tainted data flow increases weight."""
        clean = {"type": "calls", "taint_source": False}
        tainted = {"type": "calls", "taint_source": True}

        clean_weight = calculate_edge_weight(clean)
        tainted_weight = calculate_edge_weight(tainted)

        self.assertGreater(tainted_weight, clean_weight)

    def test_minimum_weight(self):
        """Weight never goes below minimum."""
        edge = {"type": "unknown_type", "guards_at_source": True}
        weight = calculate_edge_weight(edge)
        self.assertGreaterEqual(weight, 0.01)


class TestWeightNormalization(unittest.TestCase):
    """Test weight normalization."""

    def test_normalize_single_edge(self):
        """Single outgoing edge gets weight 1.0."""
        weights = {"e1": 2.0}
        out_edges = {"A": [{"id": "e1", "target": "B"}]}

        normalized = normalize_weights(weights, out_edges)

        self.assertAlmostEqual(normalized["e1"], 1.0)

    def test_normalize_multiple_edges(self):
        """Multiple edges sum to 1.0."""
        weights = {"e1": 2.0, "e2": 1.0, "e3": 1.0}
        out_edges = {
            "A": [
                {"id": "e1", "target": "B"},
                {"id": "e2", "target": "C"},
                {"id": "e3", "target": "D"},
            ]
        }

        normalized = normalize_weights(weights, out_edges)

        total = normalized["e1"] + normalized["e2"] + normalized["e3"]
        self.assertAlmostEqual(total, 1.0)

        # Higher weight should have higher normalized value
        self.assertGreater(normalized["e1"], normalized["e2"])

    def test_normalize_preserves_ratios(self):
        """Normalization preserves relative ratios."""
        weights = {"e1": 4.0, "e2": 2.0}
        out_edges = {
            "A": [
                {"id": "e1", "target": "B"},
                {"id": "e2", "target": "C"},
            ]
        }

        normalized = normalize_weights(weights, out_edges)

        # Ratio should be preserved: 4:2 = 2:1
        ratio = normalized["e1"] / normalized["e2"]
        self.assertAlmostEqual(ratio, 2.0)


class TestAnalysisWeights(unittest.TestCase):
    """Test analysis-specific weight tuning."""

    def test_reentrancy_boosts_external(self):
        """Reentrancy analysis boosts external call weight."""
        base = BASE_WEIGHTS["calls_external"]
        tuned = create_analysis_weights("reentrancy")["calls_external"]

        self.assertGreater(tuned, base)

    def test_access_control_reduces_guard_penalty(self):
        """Access control analysis reduces guard penalty."""
        base = BASE_WEIGHTS["has_modifier"]
        tuned = create_analysis_weights("access_control")["has_modifier"]

        self.assertGreater(tuned, base)


class TestPPRConfig(unittest.TestCase):
    """Test PPR configuration."""

    def test_default_config(self):
        """Default config has expected values."""
        config = PPRConfig()
        self.assertEqual(config.alpha, 0.15)
        self.assertEqual(config.max_iter, 50)

    def test_strict_config(self):
        """Strict config has higher alpha."""
        strict = PPRConfig.strict()
        standard = PPRConfig.standard()

        self.assertGreater(strict.alpha, standard.alpha)

    def test_relaxed_config(self):
        """Relaxed config has lower alpha."""
        relaxed = PPRConfig.relaxed()
        standard = PPRConfig.standard()

        self.assertLess(relaxed.alpha, standard.alpha)


class TestPPRResult(unittest.TestCase):
    """Test PPRResult methods."""

    def test_get_top_nodes(self):
        """get_top_nodes returns sorted results."""
        result = PPRResult(
            scores={"A": 0.5, "B": 0.3, "C": 0.2},
            iterations=10,
            converged=True,
            seeds=["A"],
            config=PPRConfig(),
        )

        top = result.get_top_nodes(k=2)

        self.assertEqual(len(top), 2)
        self.assertEqual(top[0][0], "A")
        self.assertEqual(top[1][0], "B")

    def test_get_nodes_above_threshold(self):
        """get_nodes_above_threshold filters correctly."""
        result = PPRResult(
            scores={"A": 0.5, "B": 0.3, "C": 0.1},
            iterations=10,
            converged=True,
            seeds=["A"],
            config=PPRConfig(),
        )

        above = result.get_nodes_above_threshold(0.25)

        self.assertIn("A", above)
        self.assertIn("B", above)
        self.assertNotIn("C", above)

    def test_get_relative_threshold_nodes(self):
        """get_relative_threshold_nodes uses relative threshold."""
        result = PPRResult(
            scores={"A": 1.0, "B": 0.5, "C": 0.05, "D": 0.01},
            iterations=10,
            converged=True,
            seeds=["A"],
            config=PPRConfig(),
        )

        # 10% of max (1.0) = 0.1
        above = result.get_relative_threshold_nodes(factor=0.10)

        self.assertIn("A", above)
        self.assertIn("B", above)
        self.assertNotIn("C", above)
        self.assertNotIn("D", above)


class TestVKGPPR(unittest.TestCase):
    """Test VKGPPR class."""

    def _create_simple_graph(self):
        """Create simple test graph."""
        return {
            "nodes": [
                {"id": "A"},
                {"id": "B"},
                {"id": "C"},
            ],
            "edges": [
                {"id": "e1", "source": "A", "target": "B", "type": "calls"},
                {"id": "e2", "source": "B", "target": "C", "type": "writes_state"},
            ],
        }

    def test_extract_nodes(self):
        """Nodes are extracted correctly."""
        graph = self._create_simple_graph()
        ppr = VKGPPR(graph)

        self.assertEqual(len(ppr.nodes), 3)
        self.assertIn("A", ppr.nodes)
        self.assertIn("B", ppr.nodes)
        self.assertIn("C", ppr.nodes)

    def test_extract_edges(self):
        """Edges are extracted correctly."""
        graph = self._create_simple_graph()
        ppr = VKGPPR(graph)

        self.assertEqual(len(ppr.edges), 2)

    def test_in_edges_built(self):
        """In-edge mapping is built correctly."""
        graph = self._create_simple_graph()
        ppr = VKGPPR(graph)

        # B has one incoming edge (from A)
        self.assertEqual(len(ppr.in_edges["B"]), 1)
        # A has no incoming edges
        self.assertEqual(len(ppr.in_edges["A"]), 0)

    def test_out_edges_built(self):
        """Out-edge mapping is built correctly."""
        graph = self._create_simple_graph()
        ppr = VKGPPR(graph)

        # A has one outgoing edge (to B)
        self.assertEqual(len(ppr.out_edges["A"]), 1)
        # C has no outgoing edges
        self.assertEqual(len(ppr.out_edges["C"]), 0)

    def test_weights_normalized(self):
        """Edge weights are normalized per source."""
        graph = {
            "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "edges": [
                {"id": "e1", "source": "A", "target": "B", "type": "calls"},
                {"id": "e2", "source": "A", "target": "C", "type": "calls"},
            ],
        }
        ppr = VKGPPR(graph)

        # Weights from A should sum to 1
        w1 = ppr.edge_weights.get("e1", 0)
        w2 = ppr.edge_weights.get("e2", 0)
        self.assertAlmostEqual(w1 + w2, 1.0)


class TestPPRAlgorithm(unittest.TestCase):
    """Test PPR algorithm correctness."""

    def _create_chain_graph(self):
        """Create A -> B -> C chain graph."""
        return {
            "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "edges": [
                {"id": "e1", "source": "A", "target": "B", "type": "calls"},
                {"id": "e2", "source": "B", "target": "C", "type": "calls"},
            ],
        }

    def test_seeds_get_highest_scores(self):
        """Seed nodes should have highest PPR scores."""
        graph = self._create_chain_graph()
        result = run_ppr(graph, seeds=["A"])

        # A should be first (it's the seed)
        top = result.get_top_nodes(k=3)
        self.assertEqual(top[0][0], "A")

    def test_convergence(self):
        """Algorithm should converge."""
        graph = self._create_chain_graph()
        result = run_ppr(graph, seeds=["A"])

        # Should converge within max_iter
        self.assertTrue(result.converged)
        self.assertLess(result.iterations, 50)

    def test_all_scores_positive(self):
        """All scores should be non-negative."""
        graph = self._create_chain_graph()
        result = run_ppr(graph, seeds=["A"])

        self.assertTrue(all(s >= 0 for s in result.scores.values()))

    def test_scores_decrease_with_distance(self):
        """Scores decrease with distance from seed."""
        graph = self._create_chain_graph()
        result = run_ppr(graph, seeds=["A"])

        # A > B > C (distance ordering)
        self.assertGreater(result.scores["A"], result.scores["B"])
        self.assertGreater(result.scores["B"], result.scores["C"])

    def test_multiple_seeds(self):
        """Multiple seeds both get high scores."""
        graph = self._create_chain_graph()
        result = run_ppr(graph, seeds=["A", "C"])

        # Both A and C should have high scores
        self.assertGreater(result.scores["A"], result.scores["B"])
        self.assertGreater(result.scores["C"], result.scores["B"])

    def test_no_valid_seeds(self):
        """Handles no valid seeds gracefully."""
        graph = self._create_chain_graph()
        result = run_ppr(graph, seeds=["X", "Y"])  # Non-existent

        # Should return uniform distribution
        self.assertTrue(result.converged)
        scores = list(result.scores.values())
        self.assertTrue(all(abs(s - scores[0]) < 0.01 for s in scores))

    def test_empty_graph(self):
        """Handles empty graph gracefully."""
        graph = {"nodes": [], "edges": []}
        result = run_ppr(graph, seeds=["A"])

        self.assertEqual(len(result.scores), 0)
        self.assertTrue(result.converged)


class TestPPRWeightEffects(unittest.TestCase):
    """Test that weights affect PPR correctly."""

    def test_higher_weight_more_flow(self):
        """Higher weight edges get more probability flow."""
        graph = {
            "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "edges": [
                # External call has higher base weight
                {"id": "e1", "source": "A", "target": "B", "type": "calls_external"},
                # Normal call has lower base weight
                {"id": "e2", "source": "A", "target": "C", "type": "calls"},
            ],
        }

        result = run_ppr(graph, seeds=["A"])

        # B should get more flow than C (higher edge weight)
        self.assertGreater(result.scores["B"], result.scores["C"])

    def test_risk_score_effect(self):
        """Risk scores affect flow direction."""
        graph = {
            "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "edges": [
                {"id": "e1", "source": "A", "target": "B", "type": "calls", "risk_score": 0.9},
                {"id": "e2", "source": "A", "target": "C", "type": "calls", "risk_score": 0.0},
            ],
        }

        result = run_ppr(graph, seeds=["A"])

        # B should get more flow (higher risk)
        self.assertGreater(result.scores["B"], result.scores["C"])


class TestPPRContextModes(unittest.TestCase):
    """Test context mode behavior."""

    def _create_deep_graph(self):
        """Create graph with depth to test exploration."""
        return {
            "nodes": [{"id": f"N{i}"} for i in range(6)],
            "edges": [
                {"id": "e1", "source": "N0", "target": "N1", "type": "calls"},
                {"id": "e2", "source": "N1", "target": "N2", "type": "calls"},
                {"id": "e3", "source": "N2", "target": "N3", "type": "calls"},
                {"id": "e4", "source": "N3", "target": "N4", "type": "calls"},
                {"id": "e5", "source": "N4", "target": "N5", "type": "calls"},
            ],
        }

    def test_strict_stays_close(self):
        """Strict mode concentrates near seeds."""
        graph = self._create_deep_graph()

        strict_result = run_ppr(graph, seeds=["N0"], config=PPRConfig.strict())
        relaxed_result = run_ppr(graph, seeds=["N0"], config=PPRConfig.relaxed())

        # In strict mode, distant nodes should have lower relative score
        strict_ratio = strict_result.scores["N4"] / strict_result.scores["N0"]
        relaxed_ratio = relaxed_result.scores["N4"] / relaxed_result.scores["N0"]

        self.assertLess(strict_ratio, relaxed_ratio)

    def test_relaxed_explores_widely(self):
        """Relaxed mode explores more distant nodes."""
        graph = self._create_deep_graph()

        strict_result = run_ppr(graph, seeds=["N0"], config=PPRConfig.strict())
        relaxed_result = run_ppr(graph, seeds=["N0"], config=PPRConfig.relaxed())

        # Relaxed should give more total score to distant nodes
        strict_distant = sum(
            strict_result.scores.get(f"N{i}", 0) for i in range(3, 6)
        )
        relaxed_distant = sum(
            relaxed_result.scores.get(f"N{i}", 0) for i in range(3, 6)
        )

        self.assertGreater(relaxed_distant, strict_distant)


class TestPPRIntegration(unittest.TestCase):
    """Integration tests with realistic graphs."""

    def test_reentrancy_pattern(self):
        """PPR on reentrancy-like graph identifies relevant nodes."""
        graph = {
            "nodes": [
                {"id": "withdraw"},
                {"id": "external_call"},
                {"id": "balance_update"},
                {"id": "unrelated_func"},
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "withdraw",
                    "target": "external_call",
                    "type": "calls_external",
                    "risk_score": 0.9,
                },
                {
                    "id": "e2",
                    "source": "withdraw",
                    "target": "balance_update",
                    "type": "writes_state",
                },
                {
                    "id": "e3",
                    "source": "unrelated_func",
                    "target": "balance_update",
                    "type": "reads_state",
                },
            ],
        }

        result = run_ppr(graph, seeds=["withdraw"], analysis_type="reentrancy")

        # Key behavior: PPR identifies nodes relevant to the seed
        top_nodes = result.get_top_nodes(k=4)
        top_node_ids = [n[0] for n in top_nodes]

        # withdraw (seed) should be in top positions (gets teleport + dangling redistribution)
        self.assertIn("withdraw", top_node_ids[:2])

        # external_call should rank well (receives high-weight flow from seed)
        self.assertIn("external_call", top_node_ids[:3])

        # All nodes should have positive scores (connected graph)
        self.assertTrue(all(score > 0 for score in result.scores.values()))


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def test_get_relevant_nodes_ppr(self):
        """get_relevant_nodes_ppr returns list of node IDs."""
        graph = {
            "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "edges": [
                {"id": "e1", "source": "A", "target": "B", "type": "calls"},
            ],
        }

        nodes = get_relevant_nodes_ppr(graph, seeds=["A"], context_mode="standard")

        self.assertIsInstance(nodes, list)
        self.assertEqual(nodes[0], "A")  # Seed should be first


if __name__ == "__main__":
    unittest.main()
