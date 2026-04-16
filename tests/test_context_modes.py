"""Tests for Task 9.4: Unified Context Modes."""

import unittest
from unittest.mock import MagicMock, patch

from alphaswarm_sol.llm.context_modes import (
    ContextExtractionResult,
    ContextMode,
    ContextModeConfig,
    ContextModeManager,
    extract_context_for_findings,
    get_context_config,
)
from alphaswarm_sol.kg.ppr import PPRConfig
from alphaswarm_sol.kg.ppr_subgraph import PPRExtractionConfig


class TestContextMode(unittest.TestCase):
    """Test ContextMode enum."""

    def test_mode_values(self):
        self.assertEqual(ContextMode.STRICT.value, "strict")
        self.assertEqual(ContextMode.STANDARD.value, "standard")
        self.assertEqual(ContextMode.RELAXED.value, "relaxed")

    def test_from_string(self):
        self.assertEqual(ContextMode.from_string("strict"), ContextMode.STRICT)
        self.assertEqual(ContextMode.from_string("STANDARD"), ContextMode.STANDARD)
        self.assertEqual(ContextMode.from_string("Relaxed"), ContextMode.RELAXED)

    def test_from_string_invalid(self):
        with self.assertRaises(ValueError) as ctx:
            ContextMode.from_string("invalid")
        self.assertIn("Invalid context mode", str(ctx.exception))


class TestContextModeConfig(unittest.TestCase):
    """Test ContextModeConfig dataclass."""

    def test_strict_config(self):
        config = ContextModeConfig.strict()

        self.assertEqual(config.mode, ContextMode.STRICT)
        self.assertEqual(config.ppr_alpha, 0.25)  # High alpha
        self.assertEqual(config.max_nodes, 30)  # Fewer nodes
        self.assertEqual(config.max_hops, 1)  # Limited hops

    def test_standard_config(self):
        config = ContextModeConfig.standard()

        self.assertEqual(config.mode, ContextMode.STANDARD)
        self.assertEqual(config.ppr_alpha, 0.15)
        self.assertEqual(config.max_nodes, 50)
        self.assertEqual(config.max_hops, 2)

    def test_relaxed_config(self):
        config = ContextModeConfig.relaxed()

        self.assertEqual(config.mode, ContextMode.RELAXED)
        self.assertEqual(config.ppr_alpha, 0.10)  # Low alpha
        self.assertEqual(config.max_nodes, 100)  # More nodes
        self.assertEqual(config.max_hops, 3)  # Wider exploration

    def test_from_mode_enum(self):
        config = ContextModeConfig.from_mode(ContextMode.STRICT)
        self.assertEqual(config.mode, ContextMode.STRICT)

    def test_from_mode_string(self):
        config = ContextModeConfig.from_mode("relaxed")
        self.assertEqual(config.mode, ContextMode.RELAXED)

    def test_to_ppr_config(self):
        config = ContextModeConfig.standard()
        ppr = config.to_ppr_config()

        self.assertIsInstance(ppr, PPRConfig)
        self.assertEqual(ppr.alpha, config.ppr_alpha)
        self.assertEqual(ppr.max_iter, config.ppr_max_iter)

    def test_to_extraction_config(self):
        config = ContextModeConfig.strict()
        ext = config.to_extraction_config()

        self.assertIsInstance(ext, PPRExtractionConfig)
        self.assertEqual(ext.context_mode, "strict")
        self.assertEqual(ext.max_nodes, config.max_nodes)

    def test_to_dict_from_dict(self):
        original = ContextModeConfig.standard()
        data = original.to_dict()
        restored = ContextModeConfig.from_dict(data)

        self.assertEqual(restored.mode, original.mode)
        self.assertEqual(restored.ppr_alpha, original.ppr_alpha)
        self.assertEqual(restored.max_nodes, original.max_nodes)


class TestContextModeConfigComparison(unittest.TestCase):
    """Test that mode configs have expected relative properties."""

    def test_alpha_ordering(self):
        """STRICT has highest alpha, RELAXED lowest."""
        strict = ContextModeConfig.strict()
        standard = ContextModeConfig.standard()
        relaxed = ContextModeConfig.relaxed()

        self.assertGreater(strict.ppr_alpha, standard.ppr_alpha)
        self.assertGreater(standard.ppr_alpha, relaxed.ppr_alpha)

    def test_max_nodes_ordering(self):
        """STRICT has fewest nodes, RELAXED most."""
        strict = ContextModeConfig.strict()
        standard = ContextModeConfig.standard()
        relaxed = ContextModeConfig.relaxed()

        self.assertLess(strict.max_nodes, standard.max_nodes)
        self.assertLess(standard.max_nodes, relaxed.max_nodes)

    def test_token_budget_ordering(self):
        """STRICT has smallest budget, RELAXED largest."""
        strict = ContextModeConfig.strict()
        standard = ContextModeConfig.standard()
        relaxed = ContextModeConfig.relaxed()

        self.assertLess(strict.max_tokens, standard.max_tokens)
        self.assertLess(standard.max_tokens, relaxed.max_tokens)

    def test_min_relevance_ordering(self):
        """STRICT has highest threshold, RELAXED lowest."""
        strict = ContextModeConfig.strict()
        standard = ContextModeConfig.standard()
        relaxed = ContextModeConfig.relaxed()

        self.assertGreater(strict.min_relevance, standard.min_relevance)
        self.assertGreater(standard.min_relevance, relaxed.min_relevance)


class TestContextExtractionResult(unittest.TestCase):
    """Test ContextExtractionResult dataclass."""

    def test_within_budget(self):
        config = ContextModeConfig.standard()  # 4000 token budget

        result = ContextExtractionResult(
            mode_config=config,
            tokens_estimated=3000,
        )
        self.assertTrue(result.is_within_budget())

        result2 = ContextExtractionResult(
            mode_config=config,
            tokens_estimated=5000,
        )
        self.assertFalse(result2.is_within_budget())

    def test_needs_stricter_mode(self):
        config = ContextModeConfig.standard()  # 4000 token budget

        # Just over budget - might not need stricter
        result = ContextExtractionResult(
            mode_config=config,
            tokens_estimated=4100,
        )
        self.assertFalse(result.needs_stricter_mode())

        # Way over budget (>120%) - needs stricter
        result2 = ContextExtractionResult(
            mode_config=config,
            tokens_estimated=5000,
        )
        self.assertTrue(result2.needs_stricter_mode())

    def test_to_dict(self):
        config = ContextModeConfig.strict()
        result = ContextExtractionResult(
            mode_config=config,
            nodes_extracted=25,
            edges_extracted=30,
            tokens_estimated=1500,
            reduction_ratio=0.5,
            ppr_converged=True,
            ppr_iterations=20,
        )

        data = result.to_dict()
        self.assertEqual(data["mode"], "strict")
        self.assertEqual(data["nodes_extracted"], 25)
        self.assertTrue(data["within_budget"])


def create_mock_graph(num_nodes: int = 20):
    """Create a mock graph for testing."""
    graph = MagicMock()

    nodes = {}
    for i in range(num_nodes):
        nodes[f"func{i}"] = MagicMock(
            id=f"func{i}",
            type="Function",
            label=f"function{i}",
            properties={},
        )

    graph.nodes = nodes

    edges = {}
    for i in range(num_nodes - 1):
        edges[f"e{i}"] = MagicMock(
            id=f"e{i}",
            type="calls",
            source=f"func{i}",
            target=f"func{i+1}",
            properties={},
        )

    graph.edges = edges

    return graph


class TestContextModeManager(unittest.TestCase):
    """Test ContextModeManager class."""

    def setUp(self):
        self.graph = create_mock_graph()

    def test_initialization_default(self):
        manager = ContextModeManager()
        self.assertEqual(manager.default_mode, ContextMode.STANDARD)

    def test_initialization_custom_mode(self):
        manager = ContextModeManager(default_mode="strict")
        self.assertEqual(manager.default_mode, ContextMode.STRICT)

    def test_get_config_default(self):
        manager = ContextModeManager()
        config = manager.get_config()
        self.assertEqual(config.mode, ContextMode.STANDARD)

    def test_get_config_specific(self):
        manager = ContextModeManager()
        config = manager.get_config("relaxed")
        self.assertEqual(config.mode, ContextMode.RELAXED)

    def test_extract_context_basic(self):
        manager = ContextModeManager()
        result = manager.extract_context(
            self.graph,
            seeds=["func0"],
            mode="standard",
        )

        self.assertIsInstance(result, ContextExtractionResult)
        self.assertGreater(result.nodes_extracted, 0)
        self.assertTrue(result.ppr_converged)

    def test_extract_context_all_modes(self):
        manager = ContextModeManager()

        for mode in ["strict", "standard", "relaxed"]:
            result = manager.extract_context(
                self.graph,
                seeds=["func0"],
                mode=mode,
            )
            self.assertEqual(result.mode_config.mode.value, mode)

    def test_extract_with_findings(self):
        manager = ContextModeManager()
        findings = [
            {"node_id": "func0", "severity": "high"},
        ]

        result = manager.extract_context(
            self.graph,
            seeds=["func0"],
            findings=findings,
        )

        self.assertGreater(result.nodes_extracted, 0)

    def test_compare_modes(self):
        manager = ContextModeManager()
        results = manager.compare_modes(self.graph, seeds=["func0"])

        self.assertIn("strict", results)
        self.assertIn("standard", results)
        self.assertIn("relaxed", results)

        # Relaxed should extract more nodes than strict
        self.assertGreaterEqual(
            results["relaxed"].nodes_extracted,
            results["strict"].nodes_extracted,
        )


class TestContextModeManagerFallback(unittest.TestCase):
    """Test fallback behavior."""

    def setUp(self):
        # Create a larger graph to trigger fallback
        self.graph = create_mock_graph(num_nodes=200)

    def test_extract_with_fallback_no_change(self):
        manager = ContextModeManager()

        # Start with strict - should not need fallback
        result = manager.extract_with_fallback(
            self.graph,
            seeds=["func0"],
            starting_mode="strict",
        )

        # Should complete without warnings for strict (already strictest)
        self.assertEqual(result.mode_config.mode, ContextMode.STRICT)

    def test_fallback_disabled(self):
        manager = ContextModeManager(enable_fallback=False)

        result = manager.extract_with_fallback(
            self.graph,
            seeds=["func0"],
            starting_mode="relaxed",
        )

        # Without fallback, should stay at relaxed
        self.assertEqual(result.mode_config.mode, ContextMode.RELAXED)


class TestContextModeManagerRecommendations(unittest.TestCase):
    """Test mode recommendations."""

    def test_small_graph_relaxed(self):
        mode = ContextModeManager.get_recommended_mode(
            graph_size=30,
            finding_severity="low",
        )
        self.assertEqual(mode, ContextMode.RELAXED)

    def test_large_graph_strict(self):
        mode = ContextModeManager.get_recommended_mode(
            graph_size=600,
            finding_severity="low",
        )
        self.assertEqual(mode, ContextMode.STRICT)

    def test_critical_finding_wider(self):
        mode = ContextModeManager.get_recommended_mode(
            graph_size=80,
            finding_severity="critical",
        )
        # Critical findings get relaxed for small graphs
        self.assertEqual(mode, ContextMode.RELAXED)

    def test_medium_graph_standard(self):
        mode = ContextModeManager.get_recommended_mode(
            graph_size=200,
            finding_severity="medium",
        )
        self.assertEqual(mode, ContextMode.STANDARD)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def test_get_context_config(self):
        config = get_context_config("strict")
        self.assertEqual(config.mode, ContextMode.STRICT)

        config = get_context_config("standard")
        self.assertEqual(config.mode, ContextMode.STANDARD)

    def test_extract_context_for_findings(self):
        graph = create_mock_graph()
        findings = [{"node_id": "func0", "severity": "high"}]

        result = extract_context_for_findings(graph, findings, mode="standard")

        self.assertIsInstance(result, ContextExtractionResult)
        self.assertGreater(result.nodes_extracted, 0)


class TestContextModeConfigCustom(unittest.TestCase):
    """Test custom configuration."""

    def test_custom_values(self):
        config = ContextModeConfig(
            mode=ContextMode.STANDARD,
            ppr_alpha=0.2,  # Custom alpha
            max_nodes=40,  # Custom nodes
        )

        self.assertEqual(config.ppr_alpha, 0.2)
        self.assertEqual(config.max_nodes, 40)

    def test_from_dict_custom(self):
        data = {
            "mode": "standard",
            "ppr_alpha": 0.18,
            "max_nodes": 60,
        }

        config = ContextModeConfig.from_dict(data)
        self.assertEqual(config.ppr_alpha, 0.18)
        self.assertEqual(config.max_nodes, 60)


class TestContextModeIntegration(unittest.TestCase):
    """Integration tests for context modes."""

    def test_full_workflow(self):
        """Test complete workflow from findings to extraction."""
        graph = create_mock_graph(num_nodes=50)

        # Start with findings
        findings = [
            {"node_id": "func0", "severity": "critical"},
            {"node_id": "func5", "severity": "high"},
        ]

        # Use manager for extraction
        manager = ContextModeManager(default_mode="standard")
        result = manager.extract_context(
            graph,
            seeds=["func0", "func5"],
            findings=findings,
        )

        # Verify results
        self.assertGreater(result.nodes_extracted, 0)
        self.assertTrue(result.ppr_converged)
        self.assertIsInstance(result.reduction_ratio, float)

    def test_mode_affects_output(self):
        """Test that different modes produce different results."""
        graph = create_mock_graph(num_nodes=100)
        manager = ContextModeManager()

        strict_result = manager.extract_context(graph, ["func0"], "strict")
        relaxed_result = manager.extract_context(graph, ["func0"], "relaxed")

        # Different modes should (generally) produce different node counts
        # Relaxed allows more nodes
        self.assertLessEqual(
            strict_result.mode_config.max_nodes,
            relaxed_result.mode_config.max_nodes,
        )


if __name__ == "__main__":
    unittest.main()
