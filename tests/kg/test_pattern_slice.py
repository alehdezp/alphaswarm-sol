"""Tests for pattern-scoped slicing v2 (Phase 5.10-04).

These tests verify:
1. Edge-closure traversal includes required ops
2. Omission lists include excluded edges with both edge_id and edge_type
3. Pattern slice completeness signals
4. PCP v2 focus parsing
"""

import pytest
from typing import Any, Dict

from alphaswarm_sol.kg.slicer import (
    GraphSlicer,
    SlicedGraph,
    PatternSliceFocus,
    PatternSliceResult,
    WitnessEvidence,
    NegativeWitness,
    TypedOmissionEntry,
    OmissionReason,
    slice_graph_for_pattern_focus,
    slice_graph_for_pcp,
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
    **extra_props,
) -> SubGraphNode:
    """Create a test SubGraphNode."""
    props = {"semantic_ops": semantic_ops or []}
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


def make_reentrancy_graph() -> SubGraph:
    """Create a test graph representing a reentrancy pattern.

    Structure:
    - F-withdraw: public, TRANSFERS_VALUE_OUT, WRITES_USER_BALANCE
    - F-internal: internal helper, READS_USER_BALANCE
    - S-balance: state variable (mapping)
    - E-external: external call target (unknown)

    Edges:
    - F-withdraw --calls--> F-internal
    - F-withdraw --calls--> E-external
    - F-withdraw --writes--> S-balance
    - F-internal --reads--> S-balance
    """
    graph = SubGraph(
        focal_node_ids=["F-withdraw"],
        analysis_type="vulnerability",
    )

    # Nodes
    graph.add_node(make_test_node(
        "F-withdraw",
        semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE", "CALLS_EXTERNAL"],
        visibility="public",
        has_external_calls=True,
    ))
    graph.add_node(make_test_node(
        "F-internal",
        semantic_ops=["READS_USER_BALANCE"],
        visibility="internal",
    ))
    graph.add_node(make_test_node(
        "S-balance",
        node_type="StateVariable",
        semantic_ops=[],
    ))
    graph.add_node(make_test_node(
        "E-external",
        node_type="ExternalCallSite",
        semantic_ops=["CALLS_UNTRUSTED"],
    ))

    # Edges
    graph.add_edge(make_test_edge("e1", "F-withdraw", "F-internal", "calls"))
    graph.add_edge(make_test_edge("e2", "F-withdraw", "E-external", "external_call"))
    graph.add_edge(make_test_edge("e3", "F-withdraw", "S-balance", "writes_state"))
    graph.add_edge(make_test_edge("e4", "F-internal", "S-balance", "reads_state"))

    return graph


def make_guarded_graph() -> SubGraph:
    """Create a test graph with reentrancy guard.

    Same as reentrancy graph but with guard enabled.
    """
    graph = make_reentrancy_graph()

    # Update F-withdraw to have reentrancy guard
    withdraw_node = graph.nodes["F-withdraw"]
    withdraw_node.properties["has_reentrancy_guard"] = True
    withdraw_node.properties["has_access_gate"] = True

    return graph


# ============================================================================
# PatternSliceFocus Tests
# ============================================================================


class TestPatternSliceFocus:
    """Tests for PatternSliceFocus creation and parsing."""

    def test_from_pcp_basic(self) -> None:
        """PatternSliceFocus.from_pcp() parses basic PCP v2 data."""
        pcp_data = {
            "op_signatures": {
                "required_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                "forbidden_ops": ["CHECKS_REENTRANCY_GUARD"],
            },
            "witness": {
                "minimal_required": ["EVD-00000001", "EVD-00000002"],
            },
            "anti_signals": [
                {"guard_type": "reentrancy_guard"},
                {"guard_type": "access_control"},
            ],
        }

        focus = PatternSliceFocus.from_pcp(pcp_data)

        assert focus.required_ops == ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"]
        assert focus.forbidden_ops == ["CHECKS_REENTRANCY_GUARD"]
        assert focus.witness_evidence_ids == ["EVD-00000001", "EVD-00000002"]
        assert focus.anti_signal_guard_types == ["reentrancy_guard", "access_control"]

    def test_from_pcp_with_ordering_variants(self) -> None:
        """PatternSliceFocus.from_pcp() parses ordering variants."""
        pcp_data = {
            "op_signatures": {
                "required_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                "ordering_variants": [
                    {
                        "id": "seq-001",
                        "sequence": ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                    },
                ],
            },
        }

        focus = PatternSliceFocus.from_pcp(pcp_data)

        assert len(focus.ordering_variants) == 1
        assert focus.ordering_variants[0] == [
            "READS_USER_BALANCE", "TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"
        ]

    def test_from_pcp_empty_data(self) -> None:
        """PatternSliceFocus.from_pcp() handles empty data gracefully."""
        focus = PatternSliceFocus.from_pcp({})

        assert focus.required_ops == []
        assert focus.forbidden_ops == []
        assert focus.witness_evidence_ids == []
        assert focus.anti_signal_guard_types == []
        assert focus.ordering_variants == []

    def test_default_max_edge_hops(self) -> None:
        """PatternSliceFocus has sensible default for max_edge_hops."""
        focus = PatternSliceFocus()
        assert focus.max_edge_hops == 2


# ============================================================================
# Pattern-Scoped Slicing Tests
# ============================================================================


class TestPatternSlice:
    """Tests for pattern-scoped slicing with edge-closure."""

    def test_required_ops_always_present(self) -> None:
        """Slicing must include nodes with required operations."""
        graph = make_reentrancy_graph()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        # F-withdraw has both required ops, must be in result
        assert "F-withdraw" in result.graph.nodes

        # Required ops should be found
        assert "TRANSFERS_VALUE_OUT" in result.witness.operations
        assert "WRITES_USER_BALANCE" in result.witness.operations

    def test_edge_closure_includes_neighbors(self) -> None:
        """Edge-closure traversal must include neighbors within max_hops."""
        graph = make_reentrancy_graph()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],
            max_edge_hops=2,
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        # Direct neighbors should be included (1 hop)
        assert "F-internal" in result.graph.nodes
        assert "E-external" in result.graph.nodes
        assert "S-balance" in result.graph.nodes

    def test_missing_required_ops_signaled(self) -> None:
        """Missing required operations must be reported."""
        graph = make_reentrancy_graph()
        focus = PatternSliceFocus(
            required_ops=["NONEXISTENT_OP", "TRANSFERS_VALUE_OUT"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        assert "NONEXISTENT_OP" in result.missing_required_ops
        assert "TRANSFERS_VALUE_OUT" not in result.missing_required_ops
        assert not result.is_complete

    def test_forbidden_ops_detected(self) -> None:
        """Forbidden operations must be detected."""
        graph = make_reentrancy_graph()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],
            forbidden_ops=["CALLS_EXTERNAL"],  # F-withdraw has this
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        assert result.has_forbidden_ops is True
        assert not result.is_complete


class TestTypedOmissions:
    """Tests for typed omission entries with edge_id and edge_type."""

    def test_omission_includes_edge_type(self) -> None:
        """Omission entries must include edge_type for debugging."""
        # Create a graph where depth limit will cause omissions
        graph = SubGraph(focal_node_ids=["N-1"])

        # Chain: N-1 -> N-2 -> N-3 -> N-4
        graph.add_node(make_test_node("N-1", semantic_ops=["OP_A"]))
        graph.add_node(make_test_node("N-2", semantic_ops=[]))
        graph.add_node(make_test_node("N-3", semantic_ops=[]))
        graph.add_node(make_test_node("N-4", semantic_ops=["OP_B"]))

        graph.add_edge(make_test_edge("e1", "N-1", "N-2", "calls"))
        graph.add_edge(make_test_edge("e2", "N-2", "N-3", "writes_state"))
        graph.add_edge(make_test_edge("e3", "N-3", "N-4", "reads_state"))

        focus = PatternSliceFocus(
            required_ops=["OP_A"],
            max_edge_hops=2,  # Will stop before reaching N-4
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["N-1"],
        )

        # Should have omissions due to depth limit
        assert len(result.typed_omissions) > 0

        # Each omission must have edge_id and edge_type
        for omission in result.typed_omissions:
            assert omission.edge_id, "Omission must have edge_id"
            assert omission.edge_type, "Omission must have edge_type"
            assert omission.reason == OmissionReason.DEPTH_LIMIT

    def test_omission_entry_serialization(self) -> None:
        """TypedOmissionEntry must serialize/deserialize correctly."""
        entry = TypedOmissionEntry(
            edge_id="e-test-001",
            edge_type="calls",
            reason=OmissionReason.DEPTH_LIMIT,
            details="Beyond max_hops=2",
        )

        data = entry.to_dict()

        assert data["edge_id"] == "e-test-001"
        assert data["edge_type"] == "calls"
        assert data["reason"] == "depth_limit"
        assert data["details"] == "Beyond max_hops=2"

        restored = TypedOmissionEntry.from_dict(data)

        assert restored.edge_id == entry.edge_id
        assert restored.edge_type == entry.edge_type
        assert restored.reason == entry.reason
        assert restored.details == entry.details


class TestGuardNodes:
    """Tests for counter/anti-signal (guard) handling."""

    def test_guard_nodes_included(self) -> None:
        """Nodes with guard properties should be tracked."""
        graph = make_guarded_graph()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],
            anti_signal_guard_types=["reentrancy_guard", "access_control"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        # Negative witness should include guard types
        assert "reentrancy_guard" in result.negative_witness.guard_types
        assert "access_control" in result.negative_witness.guard_types

    def test_negative_witness_excludes_forbidden_ops(self) -> None:
        """Negative witness should track forbidden operations."""
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],
            forbidden_ops=["CHECKS_PERMISSION", "CHECKS_OWNER"],
        )

        graph = make_reentrancy_graph()
        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        assert result.negative_witness.excluded_operations == [
            "CHECKS_PERMISSION", "CHECKS_OWNER"
        ]


# ============================================================================
# Pattern Slice Result Tests
# ============================================================================


class TestPatternSliceResult:
    """Tests for PatternSliceResult completeness and serialization."""

    def test_complete_when_all_requirements_met(self) -> None:
        """is_complete should be True when all requirements are met."""
        graph = make_reentrancy_graph()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        assert result.is_complete is True
        assert result.missing_required_ops == []
        assert result.has_forbidden_ops is False

    def test_incomplete_when_ops_missing(self) -> None:
        """is_complete should be False when required ops missing."""
        graph = make_reentrancy_graph()
        focus = PatternSliceFocus(
            required_ops=["NONEXISTENT_OP"],
        )

        result = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        assert result.is_complete is False
        assert "NONEXISTENT_OP" in result.missing_required_ops

    def test_result_serialization_roundtrip(self) -> None:
        """PatternSliceResult must serialize and deserialize correctly."""
        graph = make_reentrancy_graph()
        focus = PatternSliceFocus(
            required_ops=["TRANSFERS_VALUE_OUT"],
        )

        original = slice_graph_for_pattern_focus(
            graph=graph,
            focus=focus,
            focal_nodes=["F-withdraw"],
        )

        data = original.to_dict()
        restored = PatternSliceResult.from_dict(data)

        assert restored.is_complete == original.is_complete
        assert restored.missing_required_ops == original.missing_required_ops
        assert restored.has_forbidden_ops == original.has_forbidden_ops
        assert len(restored.graph.nodes) == len(original.graph.nodes)


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_slice_graph_for_pcp_parses_raw_data(self) -> None:
        """slice_graph_for_pcp() should parse raw PCP data."""
        pcp_data = {
            "op_signatures": {
                "required_ops": ["TRANSFERS_VALUE_OUT"],
            },
        }
        graph = make_reentrancy_graph()

        result = slice_graph_for_pcp(
            graph=graph,
            pcp_data=pcp_data,
            focal_nodes=["F-withdraw"],
        )

        assert isinstance(result, PatternSliceResult)
        assert "F-withdraw" in result.graph.nodes
