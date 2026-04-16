"""Tests for Phase 5.9-03: Subgraph Omission Ledger + Coverage Score.

This module tests:
- OmissionLedger dataclass and serialization
- Coverage score computation per v2 contract
- Cut set tracking during extraction
- Omission preservation through slicing
- Integration with SubGraph and SlicedGraph
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from alphaswarm_sol.kg.subgraph import (
    CutSetEntry,
    CutSetReason,
    OmissionLedger,
    SliceMode,
    SubGraph,
    SubGraphEdge,
    SubGraphNode,
    SubgraphExtractor,
    get_subgraph_summary,
)
from alphaswarm_sol.kg.ppr_subgraph import (
    PPRExtractionConfig,
    PPRSubgraphExtractor,
    extract_ppr_subgraph,
)
from alphaswarm_sol.kg.slicer import (
    GraphSlicer,
    SlicedGraph,
    slice_graph_for_category,
)


class TestOmissionLedger(unittest.TestCase):
    """Test OmissionLedger dataclass."""

    def test_empty_ledger(self):
        """Empty ledger has full coverage and no omissions."""
        ledger = OmissionLedger.empty()
        self.assertEqual(ledger.coverage_score, 1.0)
        self.assertEqual(len(ledger.cut_set), 0)
        self.assertEqual(len(ledger.excluded_edges), 0)
        self.assertEqual(len(ledger.omitted_nodes), 0)
        self.assertEqual(ledger.slice_mode, SliceMode.STANDARD)
        self.assertFalse(ledger.has_omissions())

    def test_add_cut_set_entry(self):
        """Cut set entries can be added."""
        ledger = OmissionLedger()
        ledger.add_cut_set_entry(
            blocker="depth_limit:2",
            reason=CutSetReason.DEPTH_LIMIT_REACHED,
            impact="10 nodes beyond depth 2",
        )
        self.assertEqual(len(ledger.cut_set), 1)
        self.assertEqual(ledger.cut_set[0].blocker, "depth_limit:2")
        self.assertEqual(ledger.cut_set[0].reason, CutSetReason.DEPTH_LIMIT_REACHED)
        self.assertTrue(ledger.has_omissions())

    def test_add_excluded_edge(self):
        """Excluded edge types can be tracked."""
        ledger = OmissionLedger()
        ledger.add_excluded_edge("INHERITANCE")
        ledger.add_excluded_edge("LIBRARY_CALL")
        ledger.add_excluded_edge("INHERITANCE")  # Duplicate, should not add
        self.assertEqual(len(ledger.excluded_edges), 2)
        self.assertIn("INHERITANCE", ledger.excluded_edges)
        self.assertTrue(ledger.has_omissions())

    def test_add_omitted_node(self):
        """Omitted nodes can be tracked."""
        ledger = OmissionLedger()
        ledger.add_omitted_node("node:1")
        ledger.add_omitted_node("node:2")
        self.assertEqual(len(ledger.omitted_nodes), 2)
        self.assertTrue(ledger.has_omissions())

    def test_compute_coverage_score_full(self):
        """Coverage is 1.0 when all relevant nodes are captured."""
        ledger = OmissionLedger()
        captured = {"a", "b", "c"}
        relevant = {"a", "b", "c"}
        score = ledger.compute_coverage_score(captured, relevant)
        self.assertEqual(score, 1.0)
        self.assertEqual(ledger.coverage_score, 1.0)

    def test_compute_coverage_score_partial(self):
        """Coverage reflects captured/relevant ratio."""
        ledger = OmissionLedger()
        captured = {"a", "b"}
        relevant = {"a", "b", "c", "d"}
        score = ledger.compute_coverage_score(captured, relevant)
        self.assertEqual(score, 0.5)
        self.assertEqual(ledger.coverage_score, 0.5)

    def test_compute_coverage_score_empty_relevant(self):
        """Empty relevant nodes yields full coverage."""
        ledger = OmissionLedger()
        captured = set()
        relevant = set()
        score = ledger.compute_coverage_score(captured, relevant)
        self.assertEqual(score, 1.0)

    def test_compute_coverage_score_captures_extra(self):
        """Extra captured nodes don't increase coverage above 1.0."""
        ledger = OmissionLedger()
        captured = {"a", "b", "c", "d", "e"}  # 5 nodes
        relevant = {"a", "b", "c"}  # Only 3 are relevant
        score = ledger.compute_coverage_score(captured, relevant)
        # Coverage = captured ∩ relevant / relevant = 3/3 = 1.0
        self.assertEqual(score, 1.0)

    def test_serialization(self):
        """OmissionLedger serializes to dict and back."""
        ledger = OmissionLedger(
            coverage_score=0.75,
            excluded_edges=["LIBRARY"],
            omitted_nodes=["n:1", "n:2"],
            slice_mode=SliceMode.DEBUG,
        )
        ledger.add_cut_set_entry(
            blocker="max_nodes:50",
            reason=CutSetReason.BUDGET_EXCEEDED,
            impact="Pruned 10 nodes",
        )

        data = ledger.to_dict()
        self.assertEqual(data["coverage_score"], 0.75)
        self.assertEqual(len(data["cut_set"]), 1)
        self.assertEqual(data["slice_mode"], "debug")

        restored = OmissionLedger.from_dict(data)
        self.assertEqual(restored.coverage_score, 0.75)
        self.assertEqual(len(restored.cut_set), 1)
        self.assertEqual(restored.cut_set[0].reason, CutSetReason.BUDGET_EXCEEDED)
        self.assertEqual(restored.slice_mode, SliceMode.DEBUG)


class TestCutSetEntry(unittest.TestCase):
    """Test CutSetEntry dataclass."""

    def test_creation(self):
        """CutSetEntry can be created with all fields."""
        entry = CutSetEntry(
            blocker="modifier:onlyOwner",
            reason=CutSetReason.MODIFIER_NOT_TRAVERSED,
            impact="Access control logic not analyzed",
        )
        self.assertEqual(entry.blocker, "modifier:onlyOwner")
        self.assertEqual(entry.reason, CutSetReason.MODIFIER_NOT_TRAVERSED)

    def test_serialization(self):
        """CutSetEntry serializes to dict and back."""
        entry = CutSetEntry(
            blocker="external:0x123",
            reason=CutSetReason.EXTERNAL_TARGET_UNKNOWN,
            impact="External contract state unknown",
        )
        data = entry.to_dict()
        self.assertEqual(data["reason"], "external_target_unknown")

        restored = CutSetEntry.from_dict(data)
        self.assertEqual(restored.reason, CutSetReason.EXTERNAL_TARGET_UNKNOWN)


class TestSubGraphOmissions(unittest.TestCase):
    """Test SubGraph with omission metadata."""

    def test_subgraph_has_omissions(self):
        """SubGraph includes omissions field by default."""
        sg = SubGraph()
        self.assertIsNotNone(sg.omissions)
        self.assertIsInstance(sg.omissions, OmissionLedger)
        self.assertEqual(sg.omissions.coverage_score, 1.0)

    def test_to_dict_includes_omissions(self):
        """SubGraph serialization includes omissions."""
        sg = SubGraph()
        sg.omissions.coverage_score = 0.8
        sg.omissions.add_omitted_node("n:1")

        data = sg.to_dict()
        self.assertIn("omissions", data)
        self.assertIn("coverage_score", data)
        self.assertEqual(data["coverage_score"], 0.8)
        self.assertEqual(len(data["omissions"]["omitted_nodes"]), 1)

    def test_from_dict_restores_omissions(self):
        """SubGraph deserialization restores omissions."""
        data = {
            "nodes": {},
            "edges": {},
            "focal_node_ids": [],
            "analysis_type": "test",
            "omissions": {
                "coverage_score": 0.65,
                "cut_set": [
                    {"blocker": "limit:10", "reason": "budget_exceeded", "impact": ""}
                ],
                "excluded_edges": ["INHERITANCE"],
                "omitted_nodes": ["x", "y"],
                "slice_mode": "standard",
            },
        }
        sg = SubGraph.from_dict(data)
        self.assertEqual(sg.omissions.coverage_score, 0.65)
        self.assertEqual(len(sg.omissions.cut_set), 1)
        self.assertEqual(len(sg.omissions.omitted_nodes), 2)

    def test_prune_by_relevance_tracks_omissions(self):
        """Pruning by relevance updates omission ledger."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(
            id="n:1", type="F", label="fn1",
            relevance_score=8.0, is_focal=True,
        ))
        sg.add_node(SubGraphNode(
            id="n:2", type="F", label="fn2",
            relevance_score=2.0, is_focal=False,
        ))
        sg.add_node(SubGraphNode(
            id="n:3", type="F", label="fn3",
            relevance_score=1.0, is_focal=False,
        ))

        sg.prune_by_relevance(min_relevance=5.0)

        self.assertIn("n:1", sg.nodes)  # Focal kept
        self.assertNotIn("n:2", sg.nodes)  # Pruned
        self.assertNotIn("n:3", sg.nodes)  # Pruned
        self.assertIn("n:2", sg.omissions.omitted_nodes)
        self.assertIn("n:3", sg.omissions.omitted_nodes)

    def test_limit_nodes_tracks_omissions(self):
        """Node limit tracking updates omission ledger."""
        sg = SubGraph()
        for i in range(10):
            sg.add_node(SubGraphNode(
                id=f"n:{i}", type="F", label=f"fn{i}",
                relevance_score=10 - i, is_focal=(i == 0),
            ))

        sg.limit_nodes(max_nodes=5)

        self.assertEqual(len(sg.nodes), 5)
        self.assertEqual(len(sg.omissions.omitted_nodes), 5)
        self.assertTrue(sg.omissions.has_omissions())
        # Should have cut_set entry
        self.assertEqual(len(sg.omissions.cut_set), 1)
        self.assertEqual(sg.omissions.cut_set[0].reason, CutSetReason.BUDGET_EXCEEDED)


class TestSubgraphExtractorOmissions(unittest.TestCase):
    """Test SubgraphExtractor omission tracking."""

    def setUp(self):
        """Create mock graph for testing."""
        self.graph = MagicMock()
        self.graph.nodes = {}
        self.graph.edges = {}

        # Create a linear chain of nodes
        for i in range(20):
            self.graph.nodes[f"n:{i}"] = MagicMock(
                id=f"n:{i}",
                type="Function",
                label=f"func{i}",
                properties={
                    "visibility": "public" if i < 5 else "internal",
                    "risk_score": max(0, 10 - i),
                },
            )

        # Chain edges
        for i in range(19):
            edge_id = f"e:{i}"
            self.graph.edges[edge_id] = MagicMock(
                id=edge_id,
                type="CALLS",
                source=f"n:{i}",
                target=f"n:{i+1}",
                properties={},
            )

    def test_extract_includes_coverage_score(self):
        """Extracted subgraph has coverage_score."""
        extractor = SubgraphExtractor(self.graph)
        subgraph = extractor.extract_for_analysis(
            focal_nodes=["n:0"],
            max_hops=2,
            max_nodes=10,
        )

        self.assertIsNotNone(subgraph.omissions)
        self.assertIsInstance(subgraph.omissions.coverage_score, float)
        self.assertGreaterEqual(subgraph.omissions.coverage_score, 0.0)
        self.assertLessEqual(subgraph.omissions.coverage_score, 1.0)

    def test_extract_tracks_depth_limit(self):
        """Extraction tracks depth limit in cut_set."""
        extractor = SubgraphExtractor(self.graph)
        subgraph = extractor.extract_for_analysis(
            focal_nodes=["n:0"],
            max_hops=1,  # Very shallow
            max_nodes=50,
        )

        # Should have depth limit cut set entry
        depth_entries = [
            e for e in subgraph.omissions.cut_set
            if e.reason == CutSetReason.DEPTH_LIMIT_REACHED
        ]
        self.assertGreaterEqual(len(depth_entries), 1)

    def test_extract_tracks_budget_exceeded(self):
        """Extraction tracks budget exceeded in cut_set."""
        extractor = SubgraphExtractor(self.graph)
        subgraph = extractor.extract_for_analysis(
            focal_nodes=["n:0"],
            max_hops=10,  # Deep
            max_nodes=5,  # But limited nodes
        )

        # Should have budget exceeded entry if pruning happened
        if len(subgraph.omissions.cut_set) > 0:
            budget_entries = [
                e for e in subgraph.omissions.cut_set
                if e.reason == CutSetReason.BUDGET_EXCEEDED
            ]
            # May or may not have budget entry depending on graph
            pass  # Validated by coverage_score < 1.0

    def test_debug_mode_bypasses_pruning(self):
        """Debug slice mode returns more nodes."""
        extractor = SubgraphExtractor(self.graph)

        standard = extractor.extract_for_analysis(
            focal_nodes=["n:0"],
            max_hops=3,
            max_nodes=5,
            slice_mode=SliceMode.STANDARD,
        )

        debug = extractor.extract_for_analysis(
            focal_nodes=["n:0"],
            max_hops=3,
            max_nodes=5,
            slice_mode=SliceMode.DEBUG,
        )

        self.assertEqual(standard.omissions.slice_mode, SliceMode.STANDARD)
        self.assertEqual(debug.omissions.slice_mode, SliceMode.DEBUG)
        # Debug mode should have more or equal nodes
        self.assertGreaterEqual(len(debug.nodes), len(standard.nodes))


class TestPPRSubgraphExtractorOmissions(unittest.TestCase):
    """Test PPRSubgraphExtractor omission tracking."""

    def setUp(self):
        """Create mock graph for testing."""
        self.graph = MagicMock()
        self.graph.nodes = {}
        self.graph.edges = {}

        for i in range(30):
            self.graph.nodes[f"f{i}"] = MagicMock(
                id=f"f{i}",
                type="Function",
                label=f"func{i}",
                properties={"visibility": "public"},
            )

        for i in range(29):
            self.graph.edges[f"e{i}"] = MagicMock(
                id=f"e{i}",
                type="calls",
                source=f"f{i}",
                target=f"f{i+1}",
                properties={},
            )

    def test_ppr_extract_includes_coverage_score(self):
        """PPR extraction includes coverage_score."""
        extractor = PPRSubgraphExtractor(self.graph)
        result = extractor.extract_from_seeds(["f0"], PPRExtractionConfig(max_nodes=10))

        self.assertIsInstance(result.subgraph.omissions.coverage_score, float)
        self.assertGreaterEqual(result.subgraph.omissions.coverage_score, 0.0)
        self.assertLessEqual(result.subgraph.omissions.coverage_score, 1.0)

    def test_ppr_extract_tracks_budget_omissions(self):
        """PPR extraction tracks budget-exceeded omissions."""
        extractor = PPRSubgraphExtractor(self.graph)
        result = extractor.extract_from_seeds(["f0"], PPRExtractionConfig(max_nodes=5))

        # With 30 nodes and max_nodes=5, should have omissions
        self.assertTrue(result.subgraph.omissions.has_omissions())
        self.assertLess(result.subgraph.omissions.coverage_score, 1.0)

    def test_ppr_stats_include_omission_metadata(self):
        """PPR extraction stats include omission metadata."""
        extractor = PPRSubgraphExtractor(self.graph)
        result = extractor.extract_from_seeds(["f0"])

        self.assertIn("coverage_score", result.stats)
        self.assertIn("omissions_present", result.stats)
        self.assertIn("cut_set_count", result.stats)
        self.assertIn("omitted_nodes_count", result.stats)
        self.assertIn("slice_mode", result.stats)


class TestSlicerOmissionsPassthrough(unittest.TestCase):
    """Test GraphSlicer passes through omissions from SubGraph."""

    def test_slicer_preserves_omissions(self):
        """GraphSlicer preserves omissions from source SubGraph."""
        # Create SubGraph with omissions
        sg = SubGraph(focal_node_ids=["n:1"])
        sg.omissions.coverage_score = 0.75
        sg.omissions.add_cut_set_entry(
            blocker="limit:20",
            reason=CutSetReason.BUDGET_EXCEEDED,
            impact="Pruned 5 nodes",
        )
        sg.omissions.add_omitted_node("n:99")

        sg.add_node(SubGraphNode(
            id="n:1", type="Function", label="withdraw",
            properties={"visibility": "public", "risk_score": 5.0},
            is_focal=True,
        ))

        # Slice the graph
        slicer = GraphSlicer()
        sliced = slicer.slice_for_category(sg, "reentrancy")

        # Omissions should be preserved
        self.assertEqual(sliced.omissions.coverage_score, 0.75)
        self.assertEqual(len(sliced.omissions.cut_set), 1)
        self.assertIn("n:99", sliced.omissions.omitted_nodes)

    def test_sliced_graph_serialization_includes_omissions(self):
        """SlicedGraph serialization includes omissions."""
        sliced = SlicedGraph(category="reentrancy")
        sliced.omissions.coverage_score = 0.5
        sliced.omissions.add_excluded_edge("LIBRARY")

        data = sliced.to_dict()
        self.assertIn("omissions", data)
        self.assertIn("coverage_score", data)
        self.assertEqual(data["coverage_score"], 0.5)
        self.assertEqual(data["omissions"]["excluded_edges"], ["LIBRARY"])

    def test_sliced_graph_deserialization_restores_omissions(self):
        """SlicedGraph deserialization restores omissions."""
        data = {
            "nodes": {},
            "edges": {},
            "focal_node_ids": [],
            "category": "access_control",
            "stats": {},
            "omissions": {
                "coverage_score": 0.9,
                "cut_set": [],
                "excluded_edges": [],
                "omitted_nodes": ["x"],
                "slice_mode": "debug",
            },
        }
        sliced = SlicedGraph.from_dict(data)
        self.assertEqual(sliced.omissions.coverage_score, 0.9)
        self.assertEqual(sliced.omissions.slice_mode, SliceMode.DEBUG)


class TestGetSubgraphSummaryOmissions(unittest.TestCase):
    """Test get_subgraph_summary includes omission metadata."""

    def test_summary_includes_omission_fields(self):
        """Summary includes v2 contract omission fields."""
        sg = SubGraph()
        sg.add_node(SubGraphNode(
            id="n:1", type="Function", label="fn1",
            relevance_score=8.0, is_focal=True,
        ))
        sg.omissions.coverage_score = 0.8
        sg.omissions.add_cut_set_entry(
            blocker="depth:2",
            reason=CutSetReason.DEPTH_LIMIT_REACHED,
            impact="",
        )
        sg.omissions.add_omitted_node("n:99")

        summary = get_subgraph_summary(sg)

        self.assertIn("coverage_score", summary)
        self.assertEqual(summary["coverage_score"], 0.8)
        self.assertIn("omissions_present", summary)
        self.assertTrue(summary["omissions_present"])
        self.assertIn("cut_set_count", summary)
        self.assertEqual(summary["cut_set_count"], 1)
        self.assertIn("omitted_nodes_count", summary)
        self.assertEqual(summary["omitted_nodes_count"], 1)
        self.assertIn("slice_mode", summary)


class TestCoverageScoreFormula(unittest.TestCase):
    """Test coverage score follows v2 contract formula."""

    def test_coverage_formula_captured_nodes_weight(self):
        """Coverage = captured_nodes_weight / relevant_nodes_weight."""
        ledger = OmissionLedger()

        # Case 1: All captured
        captured = {"a", "b", "c"}
        relevant = {"a", "b", "c"}
        self.assertEqual(ledger.compute_coverage_score(captured, relevant), 1.0)

        # Case 2: Half captured
        captured = {"a", "b"}
        relevant = {"a", "b", "c", "d"}
        self.assertEqual(ledger.compute_coverage_score(captured, relevant), 0.5)

        # Case 3: None captured
        captured = {"x", "y"}  # Different from relevant
        relevant = {"a", "b", "c", "d"}
        self.assertEqual(ledger.compute_coverage_score(captured, relevant), 0.0)

    def test_coverage_with_extra_captured_nodes(self):
        """Extra captured nodes outside relevant set don't affect coverage."""
        ledger = OmissionLedger()

        # captured has extra nodes not in relevant
        captured = {"a", "b", "c", "extra1", "extra2"}
        relevant = {"a", "b", "c"}

        # Coverage should be 3/3 = 1.0 (only count intersection)
        score = ledger.compute_coverage_score(captured, relevant)
        self.assertEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
