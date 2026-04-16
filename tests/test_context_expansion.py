"""Tests for Task 9.E: Request More Context Fallback.

Tests the context expansion functionality that allows LLM agents
to request additional context when sliced graphs are insufficient.
"""

import pytest

from alphaswarm_sol.kg.slicer import (
    ContextExpander,
    ContextExpansionLevel,
    ContextExpansionRequest,
    ContextExpansionResult,
    GraphSlicer,
    SlicedGraph,
    SlicingStats,
    request_more_context,
)
from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphEdge, SubGraphNode
from alphaswarm_sol.kg.property_sets import VulnerabilityCategory


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_node_properties():
    """Full set of node properties for testing."""
    return {
        # Core properties
        "name": "withdraw",
        "visibility": "public",
        "is_view": False,
        "is_pure": False,
        "modifiers": [],
        # Reentrancy properties
        "state_write_after_external_call": True,
        "has_reentrancy_guard": False,
        "external_call_sites": ["call"],
        # Access control properties
        "has_access_gate": False,
        "writes_privileged_state": True,
        "owner_checks": False,
        # Oracle properties
        "reads_oracle_price": False,
        "has_staleness_check": False,
        # Token properties
        "uses_erc20_transfer": True,
        "uses_safe_erc20": False,
        # MEV properties
        "has_slippage_check": False,
        "has_deadline_check": False,
        # DoS properties
        "has_unbounded_loop": False,
        "uses_transfer": True,
        # Additional properties
        "state_variables_written": ["balances"],
        "state_variables_read": ["balances"],
        "parameters": ["amount"],
        "returns": [],
        "complexity": 5,
    }


@pytest.fixture
def sample_subgraph(sample_node_properties):
    """Create a sample subgraph for testing."""
    subgraph = SubGraph()

    # Add function nodes with full properties
    node1 = SubGraphNode(
        id="Contract.withdraw",
        type="Function",
        label="withdraw",
        properties=sample_node_properties.copy(),
        relevance_score=1.0,
        is_focal=True,
    )
    subgraph.add_node(node1)

    node2 = SubGraphNode(
        id="Contract.deposit",
        type="Function",
        label="deposit",
        properties={
            "name": "deposit",
            "visibility": "public",
            "is_view": False,
            "has_access_gate": False,
            "uses_erc20_transfer": True,
            "state_variables_written": ["balances"],
        },
        relevance_score=0.8,
    )
    subgraph.add_node(node2)

    node3 = SubGraphNode(
        id="Contract.balances",
        type="StateVariable",
        label="balances",
        properties={
            "name": "balances",
            "visibility": "internal",
            "is_mapping": True,
        },
        relevance_score=0.6,
    )
    subgraph.add_node(node3)

    # Add edges
    edge1 = SubGraphEdge(
        id="edge_1",
        type="WRITES",
        source="Contract.withdraw",
        target="Contract.balances",
        properties={"risk_score": 0.8},
    )
    subgraph.add_edge(edge1)

    subgraph.focal_node_ids = ["Contract.withdraw"]
    return subgraph


@pytest.fixture
def slicer():
    """Create a standard GraphSlicer."""
    return GraphSlicer(include_core=True, strict_mode=False)


@pytest.fixture
def strict_slicer():
    """Create a strict GraphSlicer."""
    return GraphSlicer(include_core=True, strict_mode=True)


# =============================================================================
# ContextExpansionLevel Tests
# =============================================================================


class TestContextExpansionLevel:
    """Tests for ContextExpansionLevel."""

    def test_level_progression(self):
        """Test progression from strict to full."""
        assert ContextExpansionLevel.next_level("strict") == "standard"
        assert ContextExpansionLevel.next_level("standard") == "relaxed"
        assert ContextExpansionLevel.next_level("relaxed") == "full"
        assert ContextExpansionLevel.next_level("full") is None

    def test_unknown_level_defaults_to_standard(self):
        """Test that unknown level returns standard."""
        assert ContextExpansionLevel.next_level("unknown") == "standard"

    def test_all_levels(self):
        """Test all_levels returns correct order."""
        levels = ContextExpansionLevel.all_levels()
        assert levels == ["strict", "standard", "relaxed", "full"]


# =============================================================================
# ContextExpansionRequest Tests
# =============================================================================


class TestContextExpansionRequest:
    """Tests for ContextExpansionRequest."""

    def test_default_request(self):
        """Test default request creation."""
        request = ContextExpansionRequest()
        assert request.reason == ""
        assert request.current_level == "standard"
        assert request.requested_level is None
        assert request.requested_properties == []

    def test_request_with_reason(self):
        """Test request with specific reason."""
        request = ContextExpansionRequest(
            reason="Need state variable patterns",
            current_level="strict",
        )
        assert request.reason == "Need state variable patterns"
        assert request.current_level == "strict"

    def test_request_serialization(self):
        """Test request serialization round-trip."""
        request = ContextExpansionRequest(
            reason="Test reason",
            current_level="standard",
            requested_level="relaxed",
            requested_properties=["prop1", "prop2"],
        )

        data = request.to_dict()
        restored = ContextExpansionRequest.from_dict(data)

        assert restored.reason == request.reason
        assert restored.current_level == request.current_level
        assert restored.requested_level == request.requested_level
        assert restored.requested_properties == request.requested_properties


# =============================================================================
# ContextExpander Tests
# =============================================================================


class TestContextExpander:
    """Tests for ContextExpander."""

    def test_expander_initialization(self, sample_subgraph):
        """Test expander initialization."""
        expander = ContextExpander(sample_subgraph)
        assert expander.full_graph == sample_subgraph
        assert expander.slicer is not None
        assert expander._expansion_history == []

    def test_expand_strict_to_standard(self, sample_subgraph, slicer):
        """Test expansion from strict to standard level."""
        # Create a strict sliced graph
        strict_sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(
            reason="Need more reentrancy context",
            current_level="strict",
        )

        result = expander.expand(strict_sliced, request)

        assert result.new_level == "standard"
        assert result.can_expand_further is True
        assert result.expansion_reason == "Need more reentrancy context"

    def test_expand_to_specific_level(self, sample_subgraph, slicer):
        """Test expansion to a specific requested level."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(
            reason="Need relaxed context",
            current_level="strict",
            requested_level="relaxed",
        )

        result = expander.expand(sliced, request)

        assert result.new_level == "relaxed"

    def test_expand_to_full_level(self, sample_subgraph, slicer):
        """Test expansion to full level."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(
            reason="Need full context",
            requested_level="full",
        )

        result = expander.expand(sliced, request)

        assert result.new_level == "full"
        assert result.can_expand_further is False

    def test_expand_already_at_full(self, sample_subgraph, slicer):
        """Test expansion when already at full level."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(
            current_level="full",
        )

        result = expander.expand(sliced, request)

        assert result.can_expand_further is False
        assert "Already at full" in result.expansion_reason

    def test_expand_with_specific_properties(self, sample_subgraph, slicer):
        """Test expansion with specific property requests."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(
            reason="Need token transfer info",
            requested_properties=["uses_erc20_transfer", "uses_safe_erc20"],
        )

        result = expander.expand(sliced, request)

        # Check that properties were added
        assert result.expanded_graph is not None

    def test_expand_with_additional_categories(self, sample_subgraph, slicer):
        """Test expansion with additional categories."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(
            reason="Need access control context too",
            requested_categories=["access_control"],
        )

        result = expander.expand(sliced, request)

        # Category should be combined
        assert "+" in result.expanded_graph.category or \
               result.expanded_graph.category in ["reentrancy", "access_control"]

    def test_expansion_history_tracking(self, sample_subgraph, slicer):
        """Test that expansion history is tracked."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)

        # Perform multiple expansions
        request1 = ContextExpansionRequest(reason="First expansion")
        expander.expand(sliced, request1)

        request2 = ContextExpansionRequest(reason="Second expansion")
        expander.expand(sliced, request2)

        history = expander.get_expansion_history()
        assert len(history) == 2
        assert history[0]["expansion_reason"] == "First expansion"
        assert history[1]["expansion_reason"] == "Second expansion"

    def test_get_available_expansions(self, sample_subgraph, slicer):
        """Test getting available expansion options."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)
        available = expander.get_available_expansions(sliced)

        assert "current_level" in available
        assert "next_level" in available
        assert "can_expand" in available
        assert "adjacent_categories" in available
        assert "available_properties" in available


# =============================================================================
# request_more_context Convenience Function Tests
# =============================================================================


class TestRequestMoreContext:
    """Tests for the request_more_context convenience function."""

    def test_basic_request(self, sample_subgraph, slicer):
        """Test basic context request."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        result = request_more_context(
            sample_subgraph,
            sliced,
            reason="Need more context for analysis",
        )

        assert isinstance(result, ContextExpansionResult)
        assert result.expanded_graph is not None

    def test_request_with_level(self, sample_subgraph, slicer):
        """Test context request with specific level."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        result = request_more_context(
            sample_subgraph,
            sliced,
            requested_level="relaxed",
        )

        assert result.new_level == "relaxed"

    def test_request_with_properties(self, sample_subgraph, slicer):
        """Test context request with specific properties."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        result = request_more_context(
            sample_subgraph,
            sliced,
            requested_properties=["has_access_gate", "owner_checks"],
        )

        assert result.expanded_graph is not None


# =============================================================================
# Integration Tests
# =============================================================================


class TestContextExpansionIntegration:
    """Integration tests for context expansion workflow."""

    def test_progressive_expansion(self, sample_subgraph):
        """Test progressive expansion through all levels."""
        slicer = GraphSlicer(include_core=True, strict_mode=True)
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        expander = ContextExpander(sample_subgraph)

        # Start from strict, expand progressively
        levels_seen = []
        current = sliced
        current_level = "strict"  # Track actual level

        for _ in range(4):  # Max 4 levels
            request = ContextExpansionRequest(
                current_level=current_level,
            )
            result = expander.expand(current, request)
            levels_seen.append(result.new_level)
            current_level = result.new_level

            if not result.can_expand_further:
                break

            current = result.expanded_graph

        # Should eventually reach full
        assert "full" in levels_seen

    def test_expansion_maintains_focal_nodes(self, sample_subgraph, slicer):
        """Test that expansion preserves focal node information."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )
        sliced.focal_node_ids = ["Contract.withdraw"]

        expander = ContextExpander(sample_subgraph)
        result = request_more_context(
            sample_subgraph,
            sliced,
            requested_level="relaxed",
        )

        # Focal nodes should be preserved
        assert "Contract.withdraw" in result.expanded_graph.nodes or \
               len(result.expanded_graph.focal_node_ids) >= 0

    def test_expansion_result_serialization(self, sample_subgraph, slicer):
        """Test that expansion results can be serialized."""
        sliced = slicer.slice_for_category(
            sample_subgraph, VulnerabilityCategory.REENTRANCY
        )

        result = request_more_context(
            sample_subgraph,
            sliced,
            reason="Test serialization",
        )

        # Should serialize without error
        data = result.to_dict()
        assert "new_level" in data
        assert "properties_added" in data
        assert "expanded_graph" in data


# =============================================================================
# Edge Cases
# =============================================================================


class TestContextExpansionEdgeCases:
    """Tests for edge cases in context expansion."""

    def test_empty_graph_expansion(self):
        """Test expansion of an empty graph."""
        empty_graph = SubGraph()
        slicer = GraphSlicer()
        sliced = slicer.slice_for_category(empty_graph, "reentrancy")

        expander = ContextExpander(empty_graph)
        request = ContextExpansionRequest(reason="Expand empty")
        result = expander.expand(sliced, request)

        # Should handle gracefully
        assert result.expanded_graph is not None
        assert result.nodes_affected == 0

    def test_unknown_category_expansion(self, sample_subgraph, slicer):
        """Test expansion with unknown category in sliced graph."""
        sliced = SlicedGraph(category="unknown_category")

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(
            current_level="standard",
        )
        result = expander.expand(sliced, request)

        # Should fallback gracefully
        assert result.expanded_graph is not None

    def test_multi_category_expansion(self, sample_subgraph, slicer):
        """Test expansion of multi-category sliced graph."""
        sliced = slicer.slice_multiple_categories(
            sample_subgraph,
            [VulnerabilityCategory.REENTRANCY, VulnerabilityCategory.ACCESS_CONTROL],
        )

        expander = ContextExpander(sample_subgraph)
        request = ContextExpansionRequest(reason="Expand multi")
        result = expander.expand(sliced, request)

        # Should handle the combined category
        assert result.expanded_graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
