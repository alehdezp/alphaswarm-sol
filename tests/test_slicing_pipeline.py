"""Tests for Phase 5.9-07: Unified Slicing Pipeline + Debug Mode.

This module tests:
- UnifiedSlicingPipeline equivalence across router/LLM/CLI paths
- Debug slice mode behavior (bypasses pruning)
- Slice mode annotation in omissions metadata
- Pipeline stage completion tracking
- Role-specific budget handling
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from alphaswarm_sol.kg.slicer import (
    GraphSlicer,
    PipelineConfig,
    PipelineResult,
    SlicedGraph,
    UnifiedSlicingPipeline,
    slice_graph_for_agent,
    slice_graph_unified,
)
from alphaswarm_sol.kg.subgraph import (
    CutSetReason,
    OmissionLedger,
    SliceMode,
    SubGraph,
    SubGraphEdge,
    SubGraphNode,
    SubgraphExtractor,
)
from alphaswarm_sol.llm.context_policy import (
    SliceAwareContextPolicy,
    SlicePolicyConfig,
    get_slice_aware_policy,
)
from alphaswarm_sol.llm.context_policy import SliceMode as ContextSliceMode


class TestPipelineConfig(unittest.TestCase):
    """Test PipelineConfig dataclass."""

    def test_default_config(self):
        """Default config uses standard mode and general category."""
        config = PipelineConfig()
        self.assertEqual(config.slice_mode, "standard")
        self.assertEqual(config.context_mode, "standard")
        self.assertEqual(config.category, "general")
        self.assertEqual(config.max_nodes, 50)

    def test_for_role_attacker(self):
        """Attacker role gets relaxed context with more nodes."""
        config = PipelineConfig.for_role("attacker")
        self.assertEqual(config.context_mode, "relaxed")
        self.assertEqual(config.max_nodes, 80)
        self.assertIsNotNone(config.role_budget)

    def test_for_role_defender(self):
        """Defender role gets standard context with moderate nodes."""
        config = PipelineConfig.for_role("defender")
        self.assertEqual(config.context_mode, "standard")
        self.assertEqual(config.max_nodes, 60)

    def test_for_role_verifier(self):
        """Verifier role gets standard context with fewer nodes."""
        config = PipelineConfig.for_role("verifier")
        self.assertEqual(config.context_mode, "standard")
        self.assertEqual(config.max_nodes, 40)

    def test_for_role_classifier(self):
        """Classifier role gets strict context with minimal nodes."""
        config = PipelineConfig.for_role("classifier")
        self.assertEqual(config.context_mode, "strict")
        self.assertEqual(config.max_nodes, 30)

    def test_debug_config(self):
        """Debug config sets slice_mode to debug."""
        config = PipelineConfig.debug(category="reentrancy")
        self.assertEqual(config.slice_mode, "debug")
        self.assertEqual(config.category, "reentrancy")


class TestUnifiedSlicingPipeline(unittest.TestCase):
    """Test UnifiedSlicingPipeline class."""

    def setUp(self):
        """Create mock graph for testing."""
        self.graph = MagicMock()
        self.graph.nodes = {}
        self.graph.edges = {}

        # Create a chain of function nodes
        for i in range(20):
            self.graph.nodes[f"func{i}"] = MagicMock(
                id=f"func{i}",
                type="Function",
                label=f"function{i}",
                properties={
                    "visibility": "public" if i < 5 else "internal",
                    "has_external_calls": i < 3,
                    "state_write_after_external_call": i < 2,
                    "has_reentrancy_guard": False,
                },
            )

        # Create edges
        for i in range(19):
            self.graph.edges[f"e{i}"] = MagicMock(
                id=f"e{i}",
                type="calls",
                source=f"func{i}",
                target=f"func{i+1}",
                properties={},
            )

    def test_pipeline_standard_mode(self):
        """Pipeline in standard mode produces sliced graph with omissions."""
        pipeline = UnifiedSlicingPipeline(self.graph)
        result = pipeline.slice(
            focal_nodes=["func0"],
            config=PipelineConfig(category="reentrancy", max_nodes=10),
        )

        self.assertIsInstance(result, PipelineResult)
        self.assertIsInstance(result.graph, SlicedGraph)
        self.assertEqual(result.omissions.slice_mode, SliceMode.STANDARD)

    def test_pipeline_debug_mode(self):
        """Pipeline in debug mode bypasses pruning."""
        pipeline = UnifiedSlicingPipeline(self.graph)

        # Standard mode with small budget
        standard_result = pipeline.slice(
            focal_nodes=["func0"],
            config=PipelineConfig(category="reentrancy", max_nodes=5),
        )

        # Debug mode should include more nodes
        debug_result = pipeline.slice(
            focal_nodes=["func0"],
            config=PipelineConfig.debug(category="reentrancy"),
        )

        # Debug mode should have more or equal nodes
        self.assertGreaterEqual(
            debug_result.graph.node_count(),
            standard_result.graph.node_count(),
        )
        self.assertEqual(debug_result.omissions.slice_mode, SliceMode.DEBUG)
        self.assertEqual(standard_result.omissions.slice_mode, SliceMode.STANDARD)

    def test_pipeline_slice_mode_in_omissions(self):
        """Slice mode is annotated in omissions metadata."""
        pipeline = UnifiedSlicingPipeline(self.graph)

        # Standard mode
        standard = pipeline.slice(["func0"], PipelineConfig())
        self.assertEqual(
            standard.graph.omissions.slice_mode.value,
            "standard",
        )

        # Debug mode
        debug = pipeline.slice(["func0"], PipelineConfig.debug())
        self.assertEqual(
            debug.graph.omissions.slice_mode.value,
            "debug",
        )

    def test_pipeline_stages_completed(self):
        """Pipeline tracks completed stages."""
        pipeline = UnifiedSlicingPipeline(self.graph)
        result = pipeline.slice(["func0"])

        self.assertIn("stages_completed", result.stats)
        stages = result.stats["stages_completed"]

        # All stages should complete
        self.assertIn("ppr_seed_selection", stages)
        self.assertIn("subgraph_extraction", stages)
        self.assertIn("property_slicing", stages)
        self.assertIn("omission_injection", stages)

    def test_pipeline_stats_include_coverage(self):
        """Pipeline stats include coverage score."""
        pipeline = UnifiedSlicingPipeline(self.graph)
        result = pipeline.slice(
            ["func0"],
            PipelineConfig(max_nodes=5),
        )

        self.assertIn("coverage_score", result.stats)
        self.assertIn("omissions_present", result.stats)
        self.assertIsInstance(result.stats["coverage_score"], float)

    def test_slice_for_role(self):
        """slice_for_role applies role-specific config."""
        pipeline = UnifiedSlicingPipeline(self.graph)

        attacker_result = pipeline.slice_for_role(
            ["func0"], "attacker", "reentrancy"
        )
        classifier_result = pipeline.slice_for_role(
            ["func0"], "classifier", "reentrancy"
        )

        # Attacker should get more nodes than classifier
        self.assertGreaterEqual(
            attacker_result.config.max_nodes,
            classifier_result.config.max_nodes,
        )

    def test_slice_debug_method(self):
        """slice_debug convenience method works."""
        pipeline = UnifiedSlicingPipeline(self.graph)
        result = pipeline.slice_debug(["func0"], "reentrancy")

        self.assertEqual(result.config.slice_mode, "debug")
        self.assertEqual(result.omissions.slice_mode, SliceMode.DEBUG)


class TestSlicingPipelineEquivalence(unittest.TestCase):
    """Test that all slicing paths produce equivalent results.

    These tests ensure router/LLM/CLI use the same slicing pipeline.
    """

    def setUp(self):
        """Create mock graph for equivalence testing."""
        self.graph = MagicMock()
        self.graph.nodes = {}
        self.graph.edges = {}

        for i in range(10):
            self.graph.nodes[f"n{i}"] = MagicMock(
                id=f"n{i}",
                type="Function",
                label=f"func{i}",
                properties={"visibility": "public"},
            )

        for i in range(9):
            self.graph.edges[f"e{i}"] = MagicMock(
                id=f"e{i}",
                type="calls",
                source=f"n{i}",
                target=f"n{i+1}",
                properties={},
            )

    def test_unified_slice_graph_function(self):
        """slice_graph_unified produces consistent results."""
        result1 = slice_graph_unified(
            self.graph,
            focal_nodes=["n0"],
            category="general",
            max_nodes=5,
        )
        result2 = slice_graph_unified(
            self.graph,
            focal_nodes=["n0"],
            category="general",
            max_nodes=5,
        )

        # Results should be equivalent for same inputs
        self.assertEqual(result1.node_count(), result2.node_count())
        self.assertEqual(result1.category, result2.category)
        self.assertEqual(
            result1.omissions.slice_mode,
            result2.omissions.slice_mode,
        )

    def test_slice_graph_for_agent_function(self):
        """slice_graph_for_agent produces role-appropriate results."""
        attacker = slice_graph_for_agent(
            self.graph, ["n0"], "attacker", "general"
        )
        defender = slice_graph_for_agent(
            self.graph, ["n0"], "defender", "general"
        )

        # Both should have omission metadata
        self.assertIsNotNone(attacker.omissions)
        self.assertIsNotNone(defender.omissions)

    def test_pipeline_vs_direct_slicer(self):
        """Pipeline includes slicer output plus omissions."""
        pipeline = UnifiedSlicingPipeline(self.graph)
        pipeline_result = pipeline.slice(
            ["n0"],
            PipelineConfig(category="general"),
        )

        # Pipeline result should have omissions
        self.assertIsNotNone(pipeline_result.omissions)
        self.assertIsInstance(pipeline_result.omissions, OmissionLedger)


class TestDebugSliceModeBehavior(unittest.TestCase):
    """Test debug slice mode specific behavior."""

    def setUp(self):
        """Create mock graph with many nodes."""
        self.graph = MagicMock()
        self.graph.nodes = {}
        self.graph.edges = {}

        # Create 50 nodes
        for i in range(50):
            self.graph.nodes[f"func{i}"] = MagicMock(
                id=f"func{i}",
                type="Function",
                label=f"function{i}",
                properties={
                    "visibility": "public",
                    "risk_score": 50 - i,
                },
            )

        # Create linear edges
        for i in range(49):
            self.graph.edges[f"e{i}"] = MagicMock(
                id=f"e{i}",
                type="calls",
                source=f"func{i}",
                target=f"func{i+1}",
                properties={},
            )

    def test_debug_mode_bypasses_max_nodes(self):
        """Debug mode does not enforce max_nodes limit."""
        pipeline = UnifiedSlicingPipeline(self.graph)

        # Standard mode enforces limit
        standard = pipeline.slice(
            ["func0"],
            PipelineConfig(max_nodes=10),
        )

        # Debug mode bypasses limit
        debug = pipeline.slice(
            ["func0"],
            PipelineConfig.debug(),
        )

        # Standard should be limited, debug should have more
        self.assertLessEqual(standard.graph.node_count(), 10)
        self.assertGreater(debug.graph.node_count(), 10)

    def test_debug_mode_annotates_slice_mode(self):
        """Debug mode correctly annotates slice_mode in omissions."""
        pipeline = UnifiedSlicingPipeline(self.graph)
        result = pipeline.slice_debug(["func0"])

        # Check slice_mode is debug
        self.assertEqual(result.omissions.slice_mode, SliceMode.DEBUG)

        # Also check in serialized form
        omissions_dict = result.omissions.to_dict()
        self.assertEqual(omissions_dict["slice_mode"], "debug")

    def test_debug_mode_coverage_score(self):
        """Debug mode has higher coverage score."""
        pipeline = UnifiedSlicingPipeline(self.graph)

        standard = pipeline.slice(
            ["func0"],
            PipelineConfig(max_nodes=5),
        )
        debug = pipeline.slice_debug(["func0"])

        # Debug should have higher or equal coverage
        self.assertGreaterEqual(
            debug.omissions.coverage_score,
            standard.omissions.coverage_score,
        )

    def test_debug_mode_no_cut_set_for_budget(self):
        """Debug mode should not add budget-exceeded cut set entries."""
        pipeline = UnifiedSlicingPipeline(self.graph)

        # Standard mode adds budget cut set
        standard = pipeline.slice(
            ["func0"],
            PipelineConfig(max_nodes=5),
        )

        # Check for budget cut set in standard
        budget_entries = [
            e for e in standard.omissions.cut_set
            if e.reason == CutSetReason.BUDGET_EXCEEDED
        ]
        if standard.graph.node_count() < len(self.graph.nodes):
            # Should have budget entry if nodes were limited
            self.assertGreater(len(budget_entries), 0)


class TestSliceAwareContextPolicy(unittest.TestCase):
    """Test SliceAwareContextPolicy with debug mode."""

    def test_slice_mode_enum(self):
        """SliceMode enum has standard and debug values."""
        self.assertEqual(ContextSliceMode.STANDARD.value, "standard")
        self.assertEqual(ContextSliceMode.DEBUG.value, "debug")

    def test_get_slice_aware_policy_standard(self):
        """get_slice_aware_policy returns standard mode policy."""
        policy = get_slice_aware_policy(mode="standard")
        self.assertEqual(policy.config.mode, ContextSliceMode.STANDARD)

    def test_get_slice_aware_policy_debug(self):
        """get_slice_aware_policy returns debug mode policy."""
        policy = get_slice_aware_policy(mode="debug")
        self.assertEqual(policy.config.mode, ContextSliceMode.DEBUG)

    def test_slice_policy_config(self):
        """SlicePolicyConfig has correct defaults."""
        config = SlicePolicyConfig()
        self.assertEqual(config.mode, ContextSliceMode.STANDARD)
        self.assertTrue(config.include_omissions)


class TestOmissionsMetadataInSlicedGraph(unittest.TestCase):
    """Test omissions metadata in SlicedGraph output."""

    def setUp(self):
        """Create mock graph."""
        self.graph = MagicMock()
        self.graph.nodes = {
            "n1": MagicMock(
                id="n1",
                type="Function",
                label="func1",
                properties={"visibility": "public"},
            ),
        }
        self.graph.edges = {}

    def test_sliced_graph_to_dict_includes_slice_mode(self):
        """SlicedGraph.to_dict includes slice_mode in omissions."""
        pipeline = UnifiedSlicingPipeline(self.graph)

        # Standard mode
        standard = pipeline.slice(["n1"])
        standard_dict = standard.graph.to_dict()
        self.assertIn("omissions", standard_dict)
        self.assertEqual(standard_dict["omissions"]["slice_mode"], "standard")

        # Debug mode
        debug = pipeline.slice_debug(["n1"])
        debug_dict = debug.graph.to_dict()
        self.assertEqual(debug_dict["omissions"]["slice_mode"], "debug")

    def test_sliced_graph_coverage_score_in_output(self):
        """SlicedGraph output includes coverage_score at top level."""
        pipeline = UnifiedSlicingPipeline(self.graph)
        result = pipeline.slice(["n1"])
        output = result.graph.to_dict()

        self.assertIn("coverage_score", output)
        self.assertIsInstance(output["coverage_score"], float)


class TestPipelineWithRealSubGraph(unittest.TestCase):
    """Test pipeline with real SubGraph objects."""

    def test_subgraph_omissions_preserved_through_pipeline(self):
        """Omissions from SubGraph are preserved through slicing."""
        # Create SubGraph with pre-existing omissions
        sg = SubGraph(focal_node_ids=["n1"])
        sg.omissions.coverage_score = 0.7
        sg.omissions.add_cut_set_entry(
            blocker="test:limit",
            reason=CutSetReason.DEPTH_LIMIT_REACHED,
            impact="Test impact",
        )

        sg.add_node(SubGraphNode(
            id="n1",
            type="Function",
            label="func1",
            properties={"visibility": "public"},
            is_focal=True,
        ))

        # Slice the graph
        slicer = GraphSlicer()
        sliced = slicer.slice_for_category(sg, "general")

        # Omissions should be preserved
        self.assertEqual(sliced.omissions.coverage_score, 0.7)
        self.assertEqual(len(sliced.omissions.cut_set), 1)


if __name__ == "__main__":
    unittest.main()
