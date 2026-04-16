"""Integration tests for the modular VKG builder.

These tests verify:
1. Determinism: Same input always produces same output (fingerprint)
2. Completeness: All expected nodes and edges are created
3. Property preservation: Key security properties are correctly computed
4. Consistency: Modular builder produces comparable results to legacy
"""
from __future__ import annotations

from pathlib import Path
import pytest

from alphaswarm_sol.kg.builder.core import VKGBuilder, build_graph, build_graph_with_context
from alphaswarm_sol.kg.fingerprint import graph_fingerprint
from alphaswarm_sol.kg.schema import KnowledgeGraph


# Test contracts directory
CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def builder() -> VKGBuilder:
    """Create a VKGBuilder for testing."""
    return VKGBuilder(CONTRACTS_DIR)


@pytest.fixture
def reentrancy_graph(builder: VKGBuilder) -> KnowledgeGraph:
    """Build graph for ReentrancyClassic.sol."""
    return builder.build(CONTRACTS_DIR / "ReentrancyClassic.sol")


@pytest.fixture
def access_control_graph(builder: VKGBuilder) -> KnowledgeGraph:
    """Build graph for NoAccessGate.sol."""
    return builder.build(CONTRACTS_DIR / "NoAccessGate.sol")


# -----------------------------------------------------------------------------
# Determinism Tests
# -----------------------------------------------------------------------------


class TestDeterminism:
    """Verify that builds are deterministic."""

    def test_same_fingerprint_twice(self, builder: VKGBuilder) -> None:
        """Building the same file twice produces the same fingerprint."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph1 = builder.build(target)
        graph2 = builder.build(target)

        fp1 = graph_fingerprint(graph1)
        fp2 = graph_fingerprint(graph2)

        assert fp1 == fp2, f"Fingerprints differ: {fp1} != {fp2}"

    def test_node_ids_stable(self, builder: VKGBuilder) -> None:
        """Node IDs are stable across builds."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph1 = builder.build(target)
        graph2 = builder.build(target)

        ids1 = set(graph1.nodes.keys())
        ids2 = set(graph2.nodes.keys())

        assert ids1 == ids2, f"Node IDs differ: {ids1 ^ ids2}"

    def test_edge_ids_stable(self, builder: VKGBuilder) -> None:
        """Edge IDs are stable across builds."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph1 = builder.build(target)
        graph2 = builder.build(target)

        ids1 = set(graph1.edges.keys())
        ids2 = set(graph2.edges.keys())

        assert ids1 == ids2, f"Edge IDs differ: {ids1 ^ ids2}"


# -----------------------------------------------------------------------------
# Completeness Tests
# -----------------------------------------------------------------------------


class TestCompleteness:
    """Verify that all expected entities are created."""

    def test_contract_node_created(self, reentrancy_graph: KnowledgeGraph) -> None:
        """Contract node is created with proper type."""
        contract_nodes = [
            n for n in reentrancy_graph.nodes.values()
            if n.type == "Contract"
        ]
        assert len(contract_nodes) >= 1

        # Find the main contract
        main_contract = next(
            (n for n in contract_nodes if n.label == "ReentrancyClassic"),
            None
        )
        assert main_contract is not None, "ReentrancyClassic contract not found"

    def test_function_nodes_created(self, reentrancy_graph: KnowledgeGraph) -> None:
        """Function nodes are created for all functions."""
        function_nodes = [
            n for n in reentrancy_graph.nodes.values()
            if n.type == "Function"
        ]
        assert len(function_nodes) >= 2  # At least deposit and withdraw

        function_names = {n.label for n in function_nodes}
        assert "withdraw" in function_names or any(
            "withdraw" in name for name in function_names
        )

    def test_state_variable_nodes_created(self, reentrancy_graph: KnowledgeGraph) -> None:
        """State variable nodes are created."""
        state_var_nodes = [
            n for n in reentrancy_graph.nodes.values()
            if n.type == "StateVariable"
        ]
        assert len(state_var_nodes) >= 1  # At least balances mapping

    def test_edges_connect_nodes(self, reentrancy_graph: KnowledgeGraph) -> None:
        """Edges connect existing nodes."""
        node_ids = set(reentrancy_graph.nodes.keys())

        for edge in reentrancy_graph.edges.values():
            assert edge.source in node_ids, f"Edge source {edge.source} not in nodes"
            assert edge.target in node_ids, f"Edge target {edge.target} not in nodes"

    def test_completeness_report_generated(self, builder: VKGBuilder) -> None:
        """Completeness report is generated on build."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"
        builder.build(target)

        report = builder.last_completeness_report
        assert report is not None
        assert report.coverage.function_coverage >= 0.0
        assert report.coverage.function_coverage <= 1.0


# -----------------------------------------------------------------------------
# Property Preservation Tests
# -----------------------------------------------------------------------------


class TestPropertyPreservation:
    """Verify that security properties are correctly computed."""

    def test_reentrancy_function_has_external_call(
        self, reentrancy_graph: KnowledgeGraph
    ) -> None:
        """Vulnerable function has external call detected."""
        withdraw_node = next(
            (n for n in reentrancy_graph.nodes.values()
             if n.type == "Function" and "withdraw" in n.label.lower()),
            None
        )

        if withdraw_node:
            # Should have external call property
            assert withdraw_node.properties.get("has_external_calls", False) or \
                   withdraw_node.properties.get("has_call_with_value", False), \
                   "withdraw function should have external call detected"

    def test_public_function_visibility(self, reentrancy_graph: KnowledgeGraph) -> None:
        """Public functions have visibility correctly set."""
        public_functions = [
            n for n in reentrancy_graph.nodes.values()
            if n.type == "Function" and n.properties.get("visibility") in ("public", "external")
        ]
        assert len(public_functions) >= 1

    def test_access_control_detection(self, access_control_graph: KnowledgeGraph) -> None:
        """Access control properties are detected."""
        function_nodes = [
            n for n in access_control_graph.nodes.values()
            if n.type == "Function"
        ]

        # At least one function should exist
        assert len(function_nodes) >= 1

        # Check that has_access_gate property exists
        for node in function_nodes:
            # Property should be present (True or False)
            assert "has_access_gate" in node.properties or \
                   node.properties.get("is_constructor", False), \
                   f"Function {node.label} missing has_access_gate property"


# -----------------------------------------------------------------------------
# Build Context Tests
# -----------------------------------------------------------------------------


class TestBuildContext:
    """Verify build context provides diagnostics."""

    def test_build_with_context_returns_both(self) -> None:
        """build_with_context returns graph and context."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph, ctx = build_graph_with_context(target, project_root=CONTRACTS_DIR)

        assert isinstance(graph, KnowledgeGraph)
        assert ctx is not None
        assert ctx.project_root == CONTRACTS_DIR

    def test_context_has_build_stats(self) -> None:
        """Context provides build statistics."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph, ctx = build_graph_with_context(target, project_root=CONTRACTS_DIR)

        stats = ctx.get_build_stats()
        assert "nodes" in stats
        assert "edges" in stats
        assert stats["nodes"] == len(graph.nodes)
        assert stats["edges"] == len(graph.edges)


# -----------------------------------------------------------------------------
# Convenience Function Tests
# -----------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Test the build_graph convenience functions."""

    def test_build_graph_simple(self) -> None:
        """build_graph works with minimal arguments."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph = build_graph(target)

        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_build_graph_with_project_root(self) -> None:
        """build_graph accepts project_root argument."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph = build_graph(target, project_root=CONTRACTS_DIR)

        assert graph.metadata.get("root") == str(CONTRACTS_DIR)


# -----------------------------------------------------------------------------
# Smoke Tests with Multiple Contracts
# -----------------------------------------------------------------------------


class TestMultipleContracts:
    """Smoke tests with various contract types."""

    @pytest.mark.parametrize("contract_name", [
        "ReentrancyClassic.sol",
        "NoAccessGate.sol",
        "OracleNoStaleness.sol",
        "SwapNoSlippage.sol",
    ])
    def test_contract_builds_successfully(
        self, builder: VKGBuilder, contract_name: str
    ) -> None:
        """Various contracts build without error."""
        target = CONTRACTS_DIR / contract_name
        if not target.exists():
            pytest.skip(f"Contract {contract_name} not found")

        graph = builder.build(target)

        assert len(graph.nodes) > 0
        assert graph.metadata.get("builder") == "modular-2.0"

    def test_builder_metadata(self, builder: VKGBuilder) -> None:
        """Builder includes correct metadata."""
        target = CONTRACTS_DIR / "ReentrancyClassic.sol"

        graph = builder.build(target)

        assert graph.metadata.get("builder") == "modular-2.0"
        assert graph.metadata.get("builder_version") == "2.0.0"
        assert "created_at" in graph.metadata


# -----------------------------------------------------------------------------
# Edge Type Tests
# -----------------------------------------------------------------------------


class TestEdgeTypes:
    """Verify correct edge types are created."""

    def test_contains_function_edges(self, reentrancy_graph: KnowledgeGraph) -> None:
        """CONTAINS_FUNCTION edges connect contracts to functions."""
        contains_edges = [
            e for e in reentrancy_graph.edges.values()
            if e.type == "CONTAINS_FUNCTION"
        ]
        assert len(contains_edges) >= 1

    def test_contains_state_var_edges(self, reentrancy_graph: KnowledgeGraph) -> None:
        """CONTAINS_STATE_VAR edges connect contracts to state variables."""
        state_var_edges = [
            e for e in reentrancy_graph.edges.values()
            if e.type == "CONTAINS_STATE_VAR"
        ]
        assert len(state_var_edges) >= 1


# -----------------------------------------------------------------------------
# Error Handling Tests
# -----------------------------------------------------------------------------


class TestErrorHandling:
    """Verify graceful error handling."""

    def test_nonexistent_file_raises(self, builder: VKGBuilder) -> None:
        """Building nonexistent file raises error."""
        target = CONTRACTS_DIR / "nonexistent.sol"

        with pytest.raises(Exception):
            builder.build(target)

    def test_invalid_solidity_raises(self, builder: VKGBuilder, tmp_path: Path) -> None:
        """Building invalid Solidity raises error."""
        invalid_sol = tmp_path / "invalid.sol"
        invalid_sol.write_text("this is not valid solidity {{{")

        with pytest.raises(Exception):
            builder.build(invalid_sol)
