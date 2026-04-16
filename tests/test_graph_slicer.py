"""Tests for GraphSlicer.

Task 9.B: Tests for category-aware property slicing.
"""

import unittest

from alphaswarm_sol.kg.property_sets import (
    CORE_PROPERTIES,
    PROPERTY_SETS,
    VulnerabilityCategory,
)
from alphaswarm_sol.kg.slicer import (
    GraphSlicer,
    SlicedGraph,
    SlicingStats,
    calculate_slicing_impact,
    slice_graph_for_category,
    slice_graph_for_finding,
)
from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphEdge, SubGraphNode


class TestSlicingStats(unittest.TestCase):
    """Test SlicingStats dataclass."""

    def test_calculate_reduction(self):
        """calculate_reduction computes correct percentage."""
        stats = SlicingStats(
            original_property_count=100,
            sliced_property_count=25,
            nodes_processed=10,
        )
        stats.calculate_reduction()

        self.assertEqual(stats.reduction_percent, 75.0)
        self.assertEqual(stats.properties_removed, 75)

    def test_calculate_reduction_zero_original(self):
        """calculate_reduction handles zero original."""
        stats = SlicingStats(
            original_property_count=0,
            sliced_property_count=0,
            nodes_processed=0,
        )
        stats.calculate_reduction()

        self.assertEqual(stats.reduction_percent, 0.0)

    def test_calculate_reduction_no_change(self):
        """calculate_reduction handles no reduction."""
        stats = SlicingStats(
            original_property_count=50,
            sliced_property_count=50,
            nodes_processed=5,
        )
        stats.calculate_reduction()

        self.assertEqual(stats.reduction_percent, 0.0)
        self.assertEqual(stats.properties_removed, 0)


class TestSlicedGraph(unittest.TestCase):
    """Test SlicedGraph dataclass."""

    def test_create_sliced_graph(self):
        """SlicedGraph can be created."""
        graph = SlicedGraph(category="reentrancy")

        self.assertEqual(graph.category, "reentrancy")
        self.assertEqual(graph.node_count(), 0)
        self.assertTrue(graph.full_graph_available)

    def test_add_node(self):
        """add_node adds nodes correctly."""
        graph = SlicedGraph()
        node = SubGraphNode(
            id="func1",
            type="Function",
            label="withdraw",
            properties={"visibility": "public"},
        )

        graph.add_node(node)

        self.assertEqual(graph.node_count(), 1)
        self.assertEqual(graph.get_node("func1"), node)

    def test_add_edge(self):
        """add_edge adds edges for existing nodes."""
        graph = SlicedGraph()
        node1 = SubGraphNode(id="n1", type="Function", label="f1")
        node2 = SubGraphNode(id="n2", type="Function", label="f2")
        graph.add_node(node1)
        graph.add_node(node2)

        edge = SubGraphEdge(id="e1", type="CALLS", source="n1", target="n2")
        graph.add_edge(edge)

        self.assertEqual(graph.edge_count(), 1)

    def test_add_edge_missing_node(self):
        """add_edge skips edges for missing nodes."""
        graph = SlicedGraph()
        node1 = SubGraphNode(id="n1", type="Function", label="f1")
        graph.add_node(node1)

        edge = SubGraphEdge(id="e1", type="CALLS", source="n1", target="missing")
        graph.add_edge(edge)

        self.assertEqual(graph.edge_count(), 0)

    def test_to_dict(self):
        """to_dict serializes correctly."""
        graph = SlicedGraph(category="access_control")
        graph.stats = SlicingStats(
            original_property_count=100,
            sliced_property_count=30,
            nodes_processed=5,
            category="access_control",
        )
        graph.stats.calculate_reduction()

        data = graph.to_dict()

        self.assertEqual(data["category"], "access_control")
        self.assertEqual(data["stats"]["reduction_percent"], 70.0)
        self.assertTrue(data["full_graph_available"])

    def test_from_dict(self):
        """from_dict deserializes correctly."""
        data = {
            "nodes": {
                "n1": {
                    "id": "n1",
                    "type": "Function",
                    "label": "test",
                    "properties": {},
                    "relevance_score": 5.0,
                    "distance_from_focal": 1,
                    "is_focal": False,
                }
            },
            "edges": {},
            "focal_node_ids": ["n1"],
            "category": "reentrancy",
            "stats": {
                "original_property_count": 50,
                "sliced_property_count": 10,
                "reduction_percent": 80.0,
            },
            "full_graph_available": False,
        }

        graph = SlicedGraph.from_dict(data)

        self.assertEqual(graph.category, "reentrancy")
        self.assertEqual(graph.node_count(), 1)
        self.assertFalse(graph.full_graph_available)
        self.assertEqual(graph.stats.reduction_percent, 80.0)


class TestGraphSlicer(unittest.TestCase):
    """Test GraphSlicer class."""

    def _create_sample_subgraph(self) -> SubGraph:
        """Create a sample subgraph with many properties."""
        graph = SubGraph()

        # Add a function node with many properties
        props = {
            # Core properties
            "name": "withdraw",
            "visibility": "public",
            "modifiers": [],
            "has_external_calls": True,
            "external_call_count": 1,
            "reads_state": True,
            "writes_state": True,
            "state_variables_read": ["balances"],
            "state_variables_written": ["balances"],
            # Reentrancy properties
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
            "external_call_sites": ["msg.sender.call"],
            # Oracle properties (irrelevant for reentrancy)
            "reads_oracle_price": False,
            "has_staleness_check": False,
            "has_sequencer_uptime_check": False,
            # MEV properties (irrelevant for reentrancy)
            "swap_like": False,
            "has_slippage_parameter": False,
            "risk_missing_slippage_parameter": False,
            # Crypto properties (irrelevant for reentrancy)
            "uses_ecrecover": False,
            "checks_zero_address": False,
            "uses_chainid": False,
        }

        node = SubGraphNode(
            id="func_withdraw",
            type="Function",
            label="withdraw",
            properties=props,
            relevance_score=10.0,
            is_focal=True,
        )
        graph.add_node(node)
        graph.focal_node_ids = ["func_withdraw"]

        return graph

    def test_slice_for_reentrancy(self):
        """slice_for_category filters to reentrancy properties."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        sliced = slicer.slice_for_category(graph, "reentrancy")

        # Check reentrancy properties are kept
        node = sliced.get_node("func_withdraw")
        self.assertIn("state_write_after_external_call", node.properties)
        self.assertIn("has_reentrancy_guard", node.properties)
        self.assertIn("external_call_sites", node.properties)

        # Check irrelevant properties are removed
        self.assertNotIn("reads_oracle_price", node.properties)
        self.assertNotIn("swap_like", node.properties)
        self.assertNotIn("uses_ecrecover", node.properties)

    def test_slice_for_category_enum(self):
        """slice_for_category works with enum."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        sliced = slicer.slice_for_category(
            graph, VulnerabilityCategory.ACCESS_CONTROL
        )

        self.assertEqual(sliced.category, "access_control")

    def test_core_properties_included(self):
        """Core properties are always included."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer(include_core=True)

        sliced = slicer.slice_for_category(graph, "oracle")

        node = sliced.get_node("func_withdraw")
        self.assertIn("visibility", node.properties)
        self.assertIn("name", node.properties)

    def test_strict_mode(self):
        """strict_mode only includes required properties."""
        graph = self._create_sample_subgraph()

        # Normal mode includes optional
        slicer_normal = GraphSlicer(strict_mode=False)
        sliced_normal = slicer_normal.slice_for_category(graph, "reentrancy")

        # Strict mode excludes optional
        slicer_strict = GraphSlicer(strict_mode=True)
        sliced_strict = slicer_strict.slice_for_category(graph, "reentrancy")

        # Strict should have fewer or equal properties
        normal_props = len(sliced_normal.get_node("func_withdraw").properties)
        strict_props = len(sliced_strict.get_node("func_withdraw").properties)

        self.assertLessEqual(strict_props, normal_props)

    def test_statistics_tracked(self):
        """Slicing statistics are tracked correctly."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        sliced = slicer.slice_for_category(graph, "reentrancy")

        self.assertGreater(sliced.stats.original_property_count, 0)
        self.assertGreater(sliced.stats.sliced_property_count, 0)
        self.assertEqual(sliced.stats.nodes_processed, 1)
        self.assertLess(
            sliced.stats.sliced_property_count,
            sliced.stats.original_property_count,
        )

    def test_reduction_calculated(self):
        """Reduction percentage is calculated."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        sliced = slicer.slice_for_category(graph, "reentrancy")

        self.assertGreater(sliced.stats.reduction_percent, 0)
        self.assertLess(sliced.stats.reduction_percent, 100)

    def test_focal_nodes_preserved(self):
        """Focal node IDs are preserved."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        sliced = slicer.slice_for_category(graph, "reentrancy")

        self.assertEqual(sliced.focal_node_ids, ["func_withdraw"])

    def test_node_metadata_preserved(self):
        """Node metadata (relevance, focal) is preserved."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        sliced = slicer.slice_for_category(graph, "reentrancy")

        node = sliced.get_node("func_withdraw")
        self.assertEqual(node.relevance_score, 10.0)
        self.assertTrue(node.is_focal)


class TestSliceForFinding(unittest.TestCase):
    """Test slice_for_finding method."""

    def _create_sample_subgraph(self) -> SubGraph:
        """Create sample subgraph."""
        graph = SubGraph()
        node = SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                "visibility": "public",
                "state_write_after_external_call": True,
                "has_access_gate": False,
                "reads_oracle_price": False,
            },
        )
        graph.add_node(node)
        return graph

    def test_slice_for_finding_with_pattern_id(self):
        """slice_for_finding infers category from pattern_id."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        class Finding:
            pattern_id = "reentrancy-001"

        sliced = slicer.slice_for_finding(graph, Finding())

        self.assertEqual(sliced.category, "reentrancy")

    def test_slice_for_finding_with_category(self):
        """slice_for_finding uses category directly."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        class Finding:
            category = VulnerabilityCategory.ACCESS_CONTROL

        sliced = slicer.slice_for_finding(graph, Finding())

        self.assertEqual(sliced.category, "access_control")

    def test_slice_for_finding_dict(self):
        """slice_for_finding works with dict finding."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        finding = {"pattern_id": "oracle-001"}

        sliced = slicer.slice_for_finding(graph, finding)

        self.assertEqual(sliced.category, "oracle")

    def test_slice_for_finding_fallback(self):
        """slice_for_finding falls back to GENERAL."""
        graph = self._create_sample_subgraph()
        slicer = GraphSlicer()

        class Finding:
            pass

        sliced = slicer.slice_for_finding(graph, Finding())

        self.assertEqual(sliced.category, "general")


class TestSliceForPattern(unittest.TestCase):
    """Test slice_for_pattern method."""

    def test_slice_for_reentrancy_pattern(self):
        """slice_for_pattern recognizes reentrancy patterns."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(id="n1", type="F", label="f", properties={}))

        slicer = GraphSlicer()
        sliced = slicer.slice_for_pattern(graph, "reentrancy-classic")

        self.assertEqual(sliced.category, "reentrancy")

    def test_slice_for_auth_pattern(self):
        """slice_for_pattern recognizes auth patterns."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(id="n1", type="F", label="f", properties={}))

        slicer = GraphSlicer()
        sliced = slicer.slice_for_pattern(graph, "auth-001")

        self.assertEqual(sliced.category, "access_control")

    def test_slice_for_vm_pattern(self):
        """slice_for_pattern recognizes vm patterns."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(id="n1", type="F", label="f", properties={}))

        slicer = GraphSlicer()
        sliced = slicer.slice_for_pattern(graph, "vm-001")

        self.assertEqual(sliced.category, "access_control")


class TestSliceMultipleCategories(unittest.TestCase):
    """Test slice_multiple_categories method."""

    def test_slice_multiple(self):
        """slice_multiple_categories includes properties from all categories."""
        graph = SubGraph()
        node = SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties={
                # Core
                "visibility": "public",
                # Reentrancy
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
                # Access control
                "has_access_gate": False,
                "writes_privileged_state": True,
                # Oracle (not included)
                "reads_oracle_price": False,
            },
        )
        graph.add_node(node)

        slicer = GraphSlicer()
        sliced = slicer.slice_multiple_categories(
            graph, ["reentrancy", "access_control"]
        )

        props = sliced.get_node("func1").properties

        # Both category properties should be included
        self.assertIn("state_write_after_external_call", props)
        self.assertIn("has_access_gate", props)

        # Combined category name
        self.assertIn("reentrancy", sliced.category)
        self.assertIn("access_control", sliced.category)

    def test_slice_multiple_with_enums(self):
        """slice_multiple_categories works with enums."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(id="n1", type="F", label="f", properties={}))

        slicer = GraphSlicer()
        sliced = slicer.slice_multiple_categories(
            graph,
            [VulnerabilityCategory.REENTRANCY, VulnerabilityCategory.DOS],
        )

        self.assertIn("reentrancy", sliced.category)
        self.assertIn("dos", sliced.category)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def test_slice_graph_for_category(self):
        """slice_graph_for_category works."""
        graph = SubGraph()
        graph.add_node(
            SubGraphNode(
                id="n1",
                type="Function",
                label="test",
                properties={"visibility": "public"},
            )
        )

        sliced = slice_graph_for_category(graph, "reentrancy")

        self.assertEqual(sliced.category, "reentrancy")

    def test_slice_graph_for_finding(self):
        """slice_graph_for_finding works."""
        graph = SubGraph()
        graph.add_node(
            SubGraphNode(
                id="n1",
                type="Function",
                label="test",
                properties={"visibility": "public"},
            )
        )

        finding = {"pattern_id": "oracle-001"}
        sliced = slice_graph_for_finding(graph, finding)

        self.assertEqual(sliced.category, "oracle")


class TestCalculateSlicingImpact(unittest.TestCase):
    """Test calculate_slicing_impact function."""

    def test_impact_all_categories(self):
        """calculate_slicing_impact returns data for all categories."""
        graph = SubGraph()
        # Add a node with many properties
        props = {p: True for p in CORE_PROPERTIES}
        props.update({
            "state_write_after_external_call": True,
            "has_access_gate": False,
            "reads_oracle_price": True,
            "swap_like": False,
        })
        graph.add_node(
            SubGraphNode(
                id="func1",
                type="Function",
                label="test",
                properties=props,
            )
        )

        impact = calculate_slicing_impact(graph)

        # Should have entry for each category
        for category in VulnerabilityCategory:
            self.assertIn(category.value, impact)
            self.assertIn("reduction_percent", impact[category.value])

    def test_impact_structure(self):
        """calculate_slicing_impact has expected structure."""
        graph = SubGraph()
        graph.add_node(
            SubGraphNode(
                id="n1",
                type="Function",
                label="test",
                properties={"visibility": "public"},
            )
        )

        impact = calculate_slicing_impact(graph)

        reentrancy = impact["reentrancy"]
        self.assertIn("reduction_percent", reentrancy)
        self.assertIn("original_properties", reentrancy)
        self.assertIn("sliced_properties", reentrancy)
        self.assertIn("nodes_processed", reentrancy)


class TestEdgeHandling(unittest.TestCase):
    """Test edge handling in slicing."""

    def test_edges_preserved(self):
        """Edges between existing nodes are preserved."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(id="n1", type="F", label="f1", properties={}))
        graph.add_node(SubGraphNode(id="n2", type="F", label="f2", properties={}))
        graph.add_edge(SubGraphEdge(id="e1", type="CALLS", source="n1", target="n2"))

        slicer = GraphSlicer()
        sliced = slicer.slice_for_category(graph, "reentrancy")

        self.assertEqual(sliced.edge_count(), 1)

    def test_edges_with_properties_preserved(self):
        """Edge properties are preserved."""
        graph = SubGraph()
        graph.add_node(SubGraphNode(id="n1", type="F", label="f1", properties={}))
        graph.add_node(SubGraphNode(id="n2", type="F", label="f2", properties={}))
        edge = SubGraphEdge(
            id="e1",
            type="CALLS",
            source="n1",
            target="n2",
            properties={"risk_score": 0.8},
        )
        graph.add_edge(edge)

        slicer = GraphSlicer()
        sliced = slicer.slice_for_category(graph, "reentrancy")

        sliced_edge = list(sliced.edges.values())[0]
        self.assertEqual(sliced_edge.properties.get("risk_score"), 0.8)


class TestReductionTargets(unittest.TestCase):
    """Test that slicing achieves target reductions."""

    def test_significant_reduction(self):
        """Slicing achieves significant reduction (>50%)."""
        graph = SubGraph()

        # Create node with ALL possible properties (simulating full graph)
        all_props = {}
        # Add all core properties
        for p in CORE_PROPERTIES:
            all_props[p] = "test"
        # Add all category-specific properties
        for category in VulnerabilityCategory:
            prop_set = PROPERTY_SETS[category]
            for p in prop_set.required:
                all_props[p] = True
            for p in prop_set.optional:
                all_props[p] = False

        node = SubGraphNode(
            id="func1",
            type="Function",
            label="test",
            properties=all_props,
        )
        graph.add_node(node)

        # Slice for a specific category
        slicer = GraphSlicer()
        sliced = slicer.slice_for_category(graph, "reentrancy")

        # Should achieve at least 50% reduction
        self.assertGreaterEqual(sliced.stats.reduction_percent, 50.0)

    def test_reentrancy_has_relevant_props(self):
        """Reentrancy slicing keeps relevant properties."""
        graph = SubGraph()
        props = {
            "state_write_after_external_call": True,
            "has_reentrancy_guard": False,
            "reads_oracle_price": True,  # Should be excluded
        }
        graph.add_node(
            SubGraphNode(
                id="func1",
                type="Function",
                label="withdraw",
                properties=props,
            )
        )

        slicer = GraphSlicer(include_core=False)
        sliced = slicer.slice_for_category(graph, "reentrancy")

        node_props = sliced.get_node("func1").properties
        self.assertIn("state_write_after_external_call", node_props)
        self.assertIn("has_reentrancy_guard", node_props)
        self.assertNotIn("reads_oracle_price", node_props)


if __name__ == "__main__":
    unittest.main()
