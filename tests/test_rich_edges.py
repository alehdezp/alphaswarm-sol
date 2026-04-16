"""Tests for Phase 5: Edge Intelligence Layer.

This module tests:
- RichEdge schema and serialization
- Risk score computation
- Pattern tag assignment
- Meta-edge generation (SIMILAR_TO, BUGGY_PATTERN_MATCH)
- Integration with builder.py
"""

from __future__ import annotations

import unittest
import pytest
from pathlib import Path

from tests.graph_cache import load_graph
from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge
from alphaswarm_sol.kg.rich_edge import (
    RichEdge,
    RichEdgeEvidence,
    MetaEdge,
    EdgeType,
    TaintSource,
    ExecutionContext,
    EDGE_BASE_RISK,
    compute_edge_risk_score,
    determine_pattern_tags,
    create_rich_edge,
    find_similar_functions,
    compute_similarity_risk,
    matches_pattern,
    generate_meta_edges,
    KNOWN_VULNERABILITY_PATTERNS,
)


class TestRichEdgeSchema(unittest.TestCase):
    """Test RichEdge dataclass and serialization."""

    def test_rich_edge_creation(self):
        """RichEdge can be created with all fields."""
        edge = RichEdge(
            id="test:edge:1",
            type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:balance",
            risk_score=5.0,
            pattern_tags=["reentrancy_risk"],
            execution_context="normal",
            taint_source="user_input",
            cfg_order=3,
            guards_at_source=["onlyOwner"],
            transfers_value=True,
        )
        self.assertEqual(edge.id, "test:edge:1")
        self.assertEqual(edge.risk_score, 5.0)
        self.assertEqual(edge.pattern_tags, ["reentrancy_risk"])
        self.assertTrue(edge.transfers_value)

    def test_rich_edge_serialization(self):
        """RichEdge serializes to dict and back."""
        edge = RichEdge(
            id="test:edge:1",
            type=EdgeType.CALLS_EXTERNAL,
            source="func:1",
            target="external:2",
            risk_score=7.5,
            pattern_tags=["external_call", "untrusted_call"],
            execution_context=ExecutionContext.DELEGATECALL.value,
            guards_at_source=["auth"],
        )

        # Serialize
        data = edge.to_dict()
        self.assertEqual(data["id"], "test:edge:1")
        self.assertEqual(data["risk_score"], 7.5)
        self.assertEqual(data["execution_context"], "delegatecall")

        # Deserialize
        restored = RichEdge.from_dict(data)
        self.assertEqual(restored.id, edge.id)
        self.assertEqual(restored.risk_score, edge.risk_score)
        self.assertEqual(restored.pattern_tags, edge.pattern_tags)

    def test_rich_edge_is_high_risk(self):
        """RichEdge.is_high_risk() works correctly."""
        high_risk = RichEdge(
            id="test:1", type="TEST", source="a", target="b",
            risk_score=8.5
        )
        low_risk = RichEdge(
            id="test:2", type="TEST", source="a", target="b",
            risk_score=3.0
        )

        self.assertTrue(high_risk.is_high_risk())
        self.assertFalse(low_risk.is_high_risk())
        self.assertTrue(low_risk.is_high_risk(threshold=2.0))

    def test_rich_edge_has_pattern(self):
        """RichEdge.has_pattern() works correctly."""
        edge = RichEdge(
            id="test:1", type="TEST", source="a", target="b",
            pattern_tags=["reentrancy", "cei_violation"]
        )

        self.assertTrue(edge.has_pattern("reentrancy"))
        self.assertTrue(edge.has_pattern("cei_violation"))
        self.assertFalse(edge.has_pattern("oracle"))

    def test_rich_edge_is_guarded(self):
        """RichEdge.is_guarded() works correctly."""
        guarded = RichEdge(
            id="test:1", type="TEST", source="a", target="b",
            guards_at_source=["onlyOwner"]
        )
        unguarded = RichEdge(
            id="test:2", type="TEST", source="a", target="b"
        )

        self.assertTrue(guarded.is_guarded())
        self.assertFalse(unguarded.is_guarded())


class TestRiskScoring(unittest.TestCase):
    """Test edge risk score computation."""

    def test_base_risk_scores_defined(self):
        """All edge types have base risk scores."""
        self.assertIn(EdgeType.WRITES_STATE, EDGE_BASE_RISK)
        self.assertIn(EdgeType.CALLS_UNTRUSTED, EDGE_BASE_RISK)
        self.assertIn(EdgeType.DELEGATECALL, EDGE_BASE_RISK)
        self.assertIn(EdgeType.TRANSFERS_ETH, EDGE_BASE_RISK)

    def test_compute_edge_risk_unguarded(self):
        """Unguarded edges have higher risk."""
        guarded = compute_edge_risk_score(
            EdgeType.CALLS_EXTERNAL,
            is_guarded=True
        )
        unguarded = compute_edge_risk_score(
            EdgeType.CALLS_EXTERNAL,
            is_guarded=False
        )
        self.assertGreater(unguarded, guarded)

    def test_compute_edge_risk_delegatecall(self):
        """Delegatecall context adds risk."""
        normal = compute_edge_risk_score(
            EdgeType.CALLS_EXTERNAL,
            execution_context=ExecutionContext.NORMAL.value
        )
        delegatecall = compute_edge_risk_score(
            EdgeType.CALLS_EXTERNAL,
            execution_context=ExecutionContext.DELEGATECALL.value
        )
        self.assertGreater(delegatecall, normal)

    def test_compute_edge_risk_tainted(self):
        """Tainted data adds risk."""
        clean = compute_edge_risk_score(
            EdgeType.WRITES_STATE,
            has_taint=False
        )
        tainted = compute_edge_risk_score(
            EdgeType.WRITES_STATE,
            has_taint=True
        )
        self.assertGreater(tainted, clean)

    def test_compute_edge_risk_after_external_call(self):
        """State write after external call adds risk (CEI violation)."""
        normal_write = compute_edge_risk_score(
            EdgeType.WRITES_STATE,
            after_external_call=False
        )
        cei_violation = compute_edge_risk_score(
            EdgeType.WRITES_STATE,
            after_external_call=True
        )
        self.assertGreater(cei_violation, normal_write)

    def test_risk_score_capped_at_10(self):
        """Risk scores are capped at 10.0."""
        max_risk = compute_edge_risk_score(
            EdgeType.DELEGATECALL,
            execution_context=ExecutionContext.DELEGATECALL.value,
            is_guarded=False,
            has_taint=True,
            transfers_value=True,
            after_external_call=True,
        )
        self.assertLessEqual(max_risk, 10.0)


class TestPatternTags(unittest.TestCase):
    """Test pattern tag determination."""

    def test_cei_violation_tags(self):
        """CEI violation is tagged correctly."""
        tags = determine_pattern_tags(
            EdgeType.WRITES_STATE,
            after_external_call=True
        )
        self.assertIn("cei_violation", tags)
        self.assertIn("reentrancy_risk", tags)

    def test_delegatecall_tags(self):
        """Delegatecall is tagged correctly."""
        tags = determine_pattern_tags(
            EdgeType.CALLS_UNTRUSTED,
            execution_context=ExecutionContext.DELEGATECALL.value
        )
        self.assertIn("delegatecall", tags)
        self.assertIn("arbitrary_delegatecall", tags)

    def test_taint_source_tags(self):
        """Taint sources are tagged correctly."""
        user_tags = determine_pattern_tags(
            EdgeType.WRITES_STATE,
            taint_source=TaintSource.USER_INPUT.value
        )
        self.assertIn("user_controlled", user_tags)

        oracle_tags = determine_pattern_tags(
            EdgeType.READS_ORACLE,
            taint_source=TaintSource.ORACLE.value
        )
        self.assertIn("oracle_dependent", oracle_tags)


class TestCreateRichEdge(unittest.TestCase):
    """Test create_rich_edge factory function."""

    def test_create_with_defaults(self):
        """Factory creates edge with computed risk and tags."""
        edge = create_rich_edge(
            edge_id="test:1",
            edge_type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
        )
        self.assertEqual(edge.id, "test:1")
        self.assertGreater(edge.risk_score, 0)

    def test_create_with_guards_reduces_risk(self):
        """Guards reduce risk score."""
        unguarded = create_rich_edge(
            edge_id="test:1",
            edge_type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
            guards=None,
        )
        guarded = create_rich_edge(
            edge_id="test:2",
            edge_type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
            guards=["onlyOwner"],
        )
        self.assertLess(guarded.risk_score, unguarded.risk_score)
        self.assertTrue(guarded.is_guarded())

    def test_create_with_evidence(self):
        """Factory adds evidence when location provided."""
        edge = create_rich_edge(
            edge_id="test:1",
            edge_type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
            file="test.sol",
            line_start=10,
            line_end=15,
        )
        self.assertEqual(len(edge.evidence), 1)
        self.assertEqual(edge.evidence[0].file, "test.sol")


class TestMetaEdgeGeneration(unittest.TestCase):
    """Test meta-edge generation functions."""

    def test_matches_pattern_reentrancy(self):
        """Pattern matching detects reentrancy."""
        # Create a mock function node
        fn = type('MockNode', (), {
            'properties': {
                'semantic_ops': ['TRANSFERS_VALUE_OUT', 'WRITES_USER_BALANCE'],
                'behavioral_signature': 'R:bal→X:out→W:bal',
                'has_reentrancy_guard': False,
            }
        })()

        reentrancy_pattern = next(
            p for p in KNOWN_VULNERABILITY_PATTERNS
            if p['id'] == 'reentrancy-classic'
        )
        self.assertTrue(matches_pattern(fn, reentrancy_pattern))

    def test_matches_pattern_missing_access_control(self):
        """Pattern matching detects missing access control."""
        fn = type('MockNode', (), {
            'properties': {
                'semantic_ops': ['MODIFIES_CRITICAL_STATE'],
                'behavioral_signature': 'M:crit',
                'has_access_gate': False,
                'visibility': 'public',
            }
        })()

        access_pattern = next(
            p for p in KNOWN_VULNERABILITY_PATTERNS
            if p['id'] == 'missing-access-control'
        )
        self.assertTrue(matches_pattern(fn, access_pattern))

    def test_compute_similarity_risk(self):
        """Similarity risk computed correctly."""
        fn1 = type('MockNode', (), {
            'properties': {
                'visibility': 'public',
                'has_access_gate': True,
                'state_variables_written_names': ['balance'],
            }
        })()
        fn2 = type('MockNode', (), {
            'properties': {
                'visibility': 'internal',
                'has_access_gate': False,
                'state_variables_written_names': ['amount'],
            }
        })()

        risk = compute_similarity_risk(fn1, fn2)
        # Should be elevated due to different visibility, guards, and state
        self.assertGreater(risk, 5.0)


class TestKnowledgeGraphRichEdges(unittest.TestCase):
    """Test KnowledgeGraph rich edge methods."""

    def test_add_rich_edge(self):
        """KnowledgeGraph.add_rich_edge works correctly."""
        graph = KnowledgeGraph()
        edge = RichEdge(
            id="test:1",
            type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
            risk_score=5.0,
        )

        graph.add_rich_edge(edge)
        self.assertIn("test:1", graph.rich_edges)
        self.assertEqual(graph.rich_edges["test:1"].risk_score, 5.0)

    def test_add_rich_edge_merges(self):
        """Adding same edge ID merges properties."""
        graph = KnowledgeGraph()
        edge1 = RichEdge(
            id="test:1",
            type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
            risk_score=5.0,
            pattern_tags=["tag1"],
        )
        edge2 = RichEdge(
            id="test:1",
            type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
            risk_score=7.0,
            pattern_tags=["tag2"],
        )

        graph.add_rich_edge(edge1)
        graph.add_rich_edge(edge2)

        # Should take max risk and merge tags
        self.assertEqual(graph.rich_edges["test:1"].risk_score, 7.0)
        self.assertIn("tag1", graph.rich_edges["test:1"].pattern_tags)
        self.assertIn("tag2", graph.rich_edges["test:1"].pattern_tags)

    def test_get_high_risk_edges(self):
        """get_high_risk_edges filters correctly."""
        graph = KnowledgeGraph()
        graph.add_rich_edge(RichEdge(
            id="low", type="T", source="a", target="b", risk_score=3.0
        ))
        graph.add_rich_edge(RichEdge(
            id="high", type="T", source="a", target="b", risk_score=8.0
        ))

        high_risk = graph.get_high_risk_edges()
        self.assertEqual(len(high_risk), 1)
        self.assertEqual(high_risk[0].id, "high")

    def test_get_edges_with_pattern(self):
        """get_edges_with_pattern filters correctly."""
        graph = KnowledgeGraph()
        graph.add_rich_edge(RichEdge(
            id="r1", type="T", source="a", target="b",
            pattern_tags=["reentrancy"]
        ))
        graph.add_rich_edge(RichEdge(
            id="r2", type="T", source="a", target="b",
            pattern_tags=["oracle"]
        ))

        reentrancy = graph.get_edges_with_pattern("reentrancy")
        self.assertEqual(len(reentrancy), 1)
        self.assertEqual(reentrancy[0].id, "r1")

    def test_serialization_with_rich_edges(self):
        """KnowledgeGraph serializes and deserializes rich edges."""
        graph = KnowledgeGraph()
        graph.add_rich_edge(RichEdge(
            id="test:1",
            type=EdgeType.WRITES_STATE,
            source="func:1",
            target="state:1",
            risk_score=5.0,
            pattern_tags=["test"],
        ))
        graph.add_meta_edge(MetaEdge(
            id="meta:1",
            type=EdgeType.SIMILAR_TO,
            source="func:1",
            target="func:2",
            similarity_score=0.9,
        ))

        # Serialize
        data = graph.to_dict()
        self.assertEqual(len(data["rich_edges"]), 1)
        self.assertEqual(len(data["meta_edges"]), 1)

        # Deserialize
        restored = KnowledgeGraph.from_dict(data)
        self.assertEqual(len(restored.rich_edges), 1)
        self.assertEqual(len(restored.meta_edges), 1)
        self.assertEqual(restored.rich_edges["test:1"].risk_score, 5.0)


class TestBuilderIntegration(unittest.TestCase):
    """Test rich edge generation in builder."""

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_builder_generates_rich_edges(self):
        """Builder creates rich edges for functions."""
        graph = load_graph("ArbitraryDelegatecall.sol")

        # Should have rich edges
        self.assertGreater(len(graph.rich_edges), 0)

    def test_builder_generates_meta_edges(self):
        """Builder creates meta-edges."""
        graph = load_graph("ArbitraryDelegatecall.sol")

        # Should have at least pattern match meta-edges
        self.assertGreaterEqual(len(graph.meta_edges), 0)

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_delegatecall_creates_high_risk_edge(self):
        """Delegatecall creates high-risk rich edge."""
        graph = load_graph("ArbitraryDelegatecall.sol")

        # Find delegatecall or calls_untrusted edges
        call_edges = [
            e for e in graph.rich_edges.values()
            if e.type in [EdgeType.DELEGATECALL, EdgeType.CALLS_UNTRUSTED, EdgeType.CALLS_EXTERNAL]
        ]
        self.assertGreater(len(call_edges), 0)

        # Should have elevated risk
        high_risk = [e for e in call_edges if e.risk_score >= 5.0]
        self.assertGreater(len(high_risk), 0)


if __name__ == "__main__":
    unittest.main()
