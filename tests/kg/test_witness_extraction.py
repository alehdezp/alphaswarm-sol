"""Tests for deterministic witness extraction (Phase 5.10-04).

These tests verify:
1. Witness extraction is deterministic
2. Witness ordering is consistent across builds
3. Evidence IDs are correctly extracted
4. Negative witnesses track guards and forbidden ops
"""

import pytest
from typing import Any, Dict, List

from alphaswarm_sol.kg.slicer import (
    GraphSlicer,
    PatternSliceFocus,
    WitnessEvidence,
    NegativeWitness,
    slice_graph_for_pattern_focus,
    extract_witness_for_pattern,
)
from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode, SubGraphEdge


# ============================================================================
# Test Fixtures
# ============================================================================


def make_test_node(
    node_id: str,
    node_type: str = "Function",
    label: str = "",
    semantic_ops: list = None,
    evidence: list = None,
    **extra_props,
) -> SubGraphNode:
    """Create a test SubGraphNode with optional evidence."""
    props = {"semantic_ops": semantic_ops or []}
    if evidence:
        props["evidence"] = evidence
    props.update(extra_props)
    return SubGraphNode(
        id=node_id,
        type=node_type,
        label=label or node_id,
        properties=props,
    )


def make_test_edge(
    edge_id: str,
    source: str,
    target: str,
    edge_type: str = "calls",
) -> SubGraphEdge:
    """Create a test SubGraphEdge."""
    return SubGraphEdge(
        id=edge_id,
        type=edge_type,
        source=source,
        target=target,
    )


def make_graph_with_evidence() -> SubGraph:
    """Create a test graph with evidence IDs.

    Structure with evidence:
    - F-001: TRANSFERS_VALUE_OUT, evidence [EVD-a001, EVD-a002]
    - F-002: WRITES_USER_BALANCE, evidence [EVD-b001]
    - F-003: READS_USER_BALANCE, evidence [EVD-c001]
    """
    graph = SubGraph(
        focal_node_ids=["F-001"],
        analysis_type="vulnerability",
    )

    # Nodes with evidence
    graph.add_node(make_test_node(
        "F-001",
        semantic_ops=["TRANSFERS_VALUE_OUT"],
        evidence=[
            {"evidence_id": "EVD-a001", "file": "A.sol", "line": 10},
            {"evidence_id": "EVD-a002", "file": "A.sol", "line": 15},
        ],
    ))
    graph.add_node(make_test_node(
        "F-002",
        semantic_ops=["WRITES_USER_BALANCE"],
        evidence=[
            {"evidence_id": "EVD-b001", "file": "B.sol", "line": 20},
        ],
    ))
    graph.add_node(make_test_node(
        "F-003",
        semantic_ops=["READS_USER_BALANCE"],
        evidence=[
            {"evidence_id": "EVD-c001", "file": "C.sol", "line": 30},
        ],
    ))

    # Edges
    graph.add_edge(make_test_edge("e1", "F-001", "F-002", "calls"))
    graph.add_edge(make_test_edge("e2", "F-002", "F-003", "calls"))

    return graph


def make_unordered_graph() -> SubGraph:
    """Create a graph with intentionally unordered nodes/edges.

    Used to verify deterministic ordering in witness extraction.
    """
    graph = SubGraph(
        focal_node_ids=["F-z"],  # Start with Z to test sorting
        analysis_type="vulnerability",
    )

    # Add nodes in reverse alphabetical order
    graph.add_node(make_test_node(
        "F-z",
        semantic_ops=["OP_Z"],
        evidence=[{"evidence_id": "EVD-z001"}],
    ))
    graph.add_node(make_test_node(
        "F-a",
        semantic_ops=["OP_A"],
        evidence=[{"evidence_id": "EVD-a001"}],
    ))
    graph.add_node(make_test_node(
        "F-m",
        semantic_ops=["OP_M"],
        evidence=[{"evidence_id": "EVD-m001"}],
    ))

    # Edges in mixed order
    graph.add_edge(make_test_edge("e-z-m", "F-z", "F-m", "calls"))
    graph.add_edge(make_test_edge("e-a-m", "F-a", "F-m", "calls"))
    graph.add_edge(make_test_edge("e-z-a", "F-z", "F-a", "calls"))

    return graph


# ============================================================================
# Witness Determinism Tests
# ============================================================================


class TestWitnessDeterminism:
    """Tests verifying witness extraction is deterministic."""

    def test_witness_ordering_deterministic(self) -> None:
        """Witness extraction must produce same order on repeated calls."""
        graph = make_graph_with_evidence()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        # Extract witness multiple times
        results = []
        for _ in range(3):
            result = slice_graph_for_pattern_focus(
                graph=graph,
                focus=focus,
                focal_nodes=["F-001"],
            )
            results.append(result.witness)

        # All witnesses should be identical
        assert results[0].node_ids == results[1].node_ids == results[2].node_ids
        assert results[0].edge_ids == results[1].edge_ids == results[2].edge_ids
        assert results[0].evidence_ids == results[1].evidence_ids == results[2].evidence_ids
        assert results[0].operations == results[1].operations == results[2].operations

    def test_witness_sorted_by_node_id(self) -> None:
        """Witness node_ids must be sorted alphabetically."""
        graph = make_unordered_graph()
        focus = PatternSliceFocus(
            required_ops=["OP_A", "OP_M", "OP_Z"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-z"],
        )

        # Node IDs should be sorted
        assert result.witness.node_ids == sorted(result.witness.node_ids)

    def test_witness_sorted_by_edge_id(self) -> None:
        """Witness edge_ids must be sorted alphabetically."""
        graph = make_unordered_graph()
        focus = PatternSliceFocus(
            required_ops=["OP_A", "OP_M", "OP_Z"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-z"],
        )

        # Edge IDs should be sorted
        assert result.witness.edge_ids == sorted(result.witness.edge_ids)

    def test_witness_sorted_by_evidence_id(self) -> None:
        """Witness evidence_ids must be sorted."""
        graph = make_graph_with_evidence()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-001"],
        )

        # Evidence IDs should be sorted
        assert result.witness.evidence_ids == sorted(result.witness.evidence_ids)

    def test_witness_sorted_by_operation(self) -> None:
        """Witness operations must be sorted alphabetically."""
        graph = make_unordered_graph()
        focus = PatternSliceFocus(
            required_ops=["OP_Z", "OP_A", "OP_M"],  # Unordered input
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-z"],
        )

        # Operations should be sorted
        assert result.witness.operations == sorted(result.witness.operations)


# ============================================================================
# Evidence ID Extraction Tests
# ============================================================================


class TestEvidenceExtraction:
    """Tests for evidence ID extraction from witnesses."""

    def test_evidence_ids_extracted_from_nodes(self) -> None:
        """Evidence IDs must be extracted from node evidence lists."""
        graph = make_graph_with_evidence()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-001"],
        )

        # Evidence IDs from F-001 should be in witness
        assert "EVD-a001" in result.witness.evidence_ids
        assert "EVD-a002" in result.witness.evidence_ids

    def test_evidence_ids_only_from_witness_nodes(self) -> None:
        """Evidence IDs should only come from nodes with required ops."""
        graph = make_graph_with_evidence()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],  # Only F-001 has this
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-001"],
        )

        # Evidence from F-001 (has TRANSFERS_VALUE_OUT)
        assert "EVD-a001" in result.witness.evidence_ids

        # Evidence from F-002 should NOT be in witness
        # (F-002 has WRITES_USER_BALANCE, not TRANSFERS_VALUE_OUT)
        assert "EVD-b001" not in result.witness.evidence_ids

    def test_missing_witness_evidence_detected(self) -> None:
        """Missing expected witness evidence IDs should be reported."""
        graph = make_graph_with_evidence()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],
            witness_evidence_ids=["EVD-a001", "EVD-missing-001", "EVD-missing-002"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-001"],
        )

        # Missing witness IDs should be reported
        assert "EVD-missing-001" in result.missing_witness_ids
        assert "EVD-missing-002" in result.missing_witness_ids
        assert "EVD-a001" not in result.missing_witness_ids


# ============================================================================
# Witness Evidence Dataclass Tests
# ============================================================================


class TestWitnessEvidence:
    """Tests for WitnessEvidence dataclass."""

    def test_is_empty_when_no_data(self) -> None:
        """is_empty() should return True when no evidence present."""
        witness = WitnessEvidence()
        assert witness.is_empty() is True

    def test_not_empty_with_evidence_ids(self) -> None:
        """is_empty() should return False when evidence_ids present."""
        witness = WitnessEvidence(evidence_ids=["EVD-001"])
        assert witness.is_empty() is False

    def test_not_empty_with_node_ids(self) -> None:
        """is_empty() should return False when node_ids present."""
        witness = WitnessEvidence(node_ids=["F-001"])
        assert witness.is_empty() is False

    def test_not_empty_with_edge_ids(self) -> None:
        """is_empty() should return False when edge_ids present."""
        witness = WitnessEvidence(edge_ids=["e-001"])
        assert witness.is_empty() is False

    def test_serialization_roundtrip(self) -> None:
        """WitnessEvidence must serialize and deserialize correctly."""
        original = WitnessEvidence(
            evidence_ids=["EVD-001", "EVD-002"],
            node_ids=["F-001", "F-002"],
            edge_ids=["e-001"],
            operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        data = original.to_dict()
        restored = WitnessEvidence.from_dict(data)

        assert restored.evidence_ids == original.evidence_ids
        assert restored.node_ids == original.node_ids
        assert restored.edge_ids == original.edge_ids
        assert restored.operations == original.operations


# ============================================================================
# Negative Witness Tests
# ============================================================================


class TestNegativeWitness:
    """Tests for NegativeWitness (anti-signals/guards)."""

    def test_negative_witness_tracks_guard_types(self) -> None:
        """NegativeWitness should track expected guard types."""
        witness = NegativeWitness(
            guard_types=["reentrancy_guard", "access_control"],
        )

        assert "reentrancy_guard" in witness.guard_types
        assert "access_control" in witness.guard_types

    def test_negative_witness_tracks_excluded_ops(self) -> None:
        """NegativeWitness should track forbidden operations."""
        witness = NegativeWitness(
            excluded_operations=["CHECKS_PERMISSION", "CHECKS_OWNER"],
        )

        assert "CHECKS_PERMISSION" in witness.excluded_operations
        assert "CHECKS_OWNER" in witness.excluded_operations

    def test_negative_witness_serialization(self) -> None:
        """NegativeWitness must serialize and deserialize correctly."""
        original = NegativeWitness(
            guard_types=["reentrancy_guard"],
            excluded_operations=["CHECKS_PERMISSION"],
            guard_evidence_ids=["EVD-guard-001"],
        )

        data = original.to_dict()
        restored = NegativeWitness.from_dict(data)

        assert restored.guard_types == original.guard_types
        assert restored.excluded_operations == original.excluded_operations
        assert restored.guard_evidence_ids == original.guard_evidence_ids


# ============================================================================
# Extract Witness Convenience Function Tests
# ============================================================================


class TestExtractWitnessFunction:
    """Tests for extract_witness_for_pattern() convenience function."""

    def test_extract_witness_standalone(self) -> None:
        """extract_witness_for_pattern() should work without full slicing."""
        graph = make_graph_with_evidence()

        witness = extract_witness_for_pattern(
            graph=graph,
            required_ops=["TRANSFERS_VALUE_OUT"],
            focal_nodes=["F-001"],
        )

        assert isinstance(witness, WitnessEvidence)
        assert "F-001" in witness.node_ids
        assert "TRANSFERS_VALUE_OUT" in witness.operations

    def test_extract_witness_deterministic(self) -> None:
        """extract_witness_for_pattern() must be deterministic."""
        graph = make_graph_with_evidence()

        witnesses = [
            extract_witness_for_pattern(graph, ["TRANSFERS_VALUE_OUT"], ["F-001"])
            for _ in range(3)
        ]

        assert witnesses[0].node_ids == witnesses[1].node_ids == witnesses[2].node_ids
        assert witnesses[0].evidence_ids == witnesses[1].evidence_ids == witnesses[2].evidence_ids


# ============================================================================
# Integration Tests
# ============================================================================


class TestWitnessIntegration:
    """Integration tests for witness extraction in full slicing flow."""

    def test_witness_links_to_slice_nodes(self) -> None:
        """Witness node_ids should be subset of sliced graph nodes."""
        graph = make_graph_with_evidence()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-001"],
        )

        # All witness nodes should be in the sliced graph
        for node_id in result.witness.node_ids:
            assert node_id in result.graph.nodes, f"Witness node {node_id} not in slice"

    def test_witness_edges_connect_witness_nodes(self) -> None:
        """Witness edges should connect witness nodes."""
        graph = make_graph_with_evidence()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-001"],
        )

        # All witness edges should connect witness nodes
        for edge_id in result.witness.edge_ids:
            if edge_id in result.graph.edges:
                edge = result.graph.edges[edge_id]
                # At least one endpoint should be in witness nodes
                assert (
                    edge.source in result.witness.node_ids or
                    edge.target in result.witness.node_ids
                ), f"Witness edge {edge_id} does not connect witness nodes"
