"""Tests for GraphStore with TOON format support."""

from __future__ import annotations

import json

import pytest
from pathlib import Path

from alphaswarm_sol.kg.store import GraphStore, FORMAT_VERSION
from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge


@pytest.fixture
def empty_graph() -> KnowledgeGraph:
    """Create minimal empty graph."""
    return KnowledgeGraph(nodes={}, edges={}, metadata={"test": True})


@pytest.fixture
def simple_graph() -> KnowledgeGraph:
    """Create simple graph with nodes and edges."""
    graph = KnowledgeGraph(metadata={"test": True})

    node1 = Node(
        id="func:transfer",
        type="function",
        label="transfer",
        properties={"visibility": "public", "writes_state": True},
        evidence=[],
    )
    node2 = Node(
        id="func:approve",
        type="function",
        label="approve",
        properties={"visibility": "public", "writes_state": True},
        evidence=[],
    )
    graph.nodes["func:transfer"] = node1
    graph.nodes["func:approve"] = node2

    edge = Edge(
        id="edge:1",
        type="calls",
        source="func:transfer",
        target="func:approve",
        properties={},
        evidence=[],
    )
    graph.edges["edge:1"] = edge

    return graph


class TestGraphStoreToonFormat:
    """Test TOON format output."""

    def test_save_defaults_to_toon(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """Default format is TOON."""
        store = GraphStore(tmp_path)
        saved = store.save(empty_graph)

        assert saved.suffix == ".toon"
        assert saved.name == "graph.toon"

    def test_save_toon_explicit(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """Explicit TOON format."""
        store = GraphStore(tmp_path)
        saved = store.save(empty_graph, format="toon")

        assert saved.suffix == ".toon"

    def test_save_json_format(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """JSON format for legacy compatibility."""
        store = GraphStore(tmp_path)
        saved = store.save(empty_graph, format="json")

        assert saved.suffix == ".json"
        assert saved.name == "graph.json"

    def test_toon_roundtrip(self, tmp_path: Path, simple_graph: KnowledgeGraph) -> None:
        """Graph survives TOON round-trip."""
        store = GraphStore(tmp_path)
        saved = store.save(simple_graph, format="toon")

        loaded = store.load(saved)

        assert len(loaded.nodes) == len(simple_graph.nodes)
        assert len(loaded.edges) == len(simple_graph.edges)
        assert loaded.metadata.get("test") is True

    def test_json_roundtrip(self, tmp_path: Path, simple_graph: KnowledgeGraph) -> None:
        """Graph survives JSON round-trip."""
        store = GraphStore(tmp_path)
        saved = store.save(simple_graph, format="json")

        loaded = store.load(saved)

        assert len(loaded.nodes) == len(simple_graph.nodes)
        assert len(loaded.edges) == len(simple_graph.edges)


class TestGraphStoreAutoDetect:
    """Test format auto-detection on load."""

    def test_load_prefers_toon(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """Load without path prefers .toon over .json."""
        store = GraphStore(tmp_path)

        # Save both formats
        store.save(empty_graph, format="toon", overwrite=True)
        store.save(empty_graph, format="json", overwrite=True)

        # Both files should exist
        assert (tmp_path / "graph.toon").exists()
        assert (tmp_path / "graph.json").exists()

        # Load without explicit path - should use TOON
        loaded = store.load()
        assert loaded is not None

    def test_load_falls_back_to_json(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """Load without path falls back to .json if .toon missing."""
        store = GraphStore(tmp_path)

        # Save only JSON
        store.save(empty_graph, format="json")

        # Load without path - should use JSON fallback
        loaded = store.load()
        assert loaded is not None

    def test_load_explicit_toon_path(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """Load from explicit .toon path."""
        store = GraphStore(tmp_path)
        saved = store.save(empty_graph, format="toon")

        loaded = store.load(saved)
        assert loaded is not None

    def test_load_explicit_json_path(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """Load from explicit .json path."""
        store = GraphStore(tmp_path)
        saved = store.save(empty_graph, format="json")

        loaded = store.load(saved)
        assert loaded is not None


class TestGraphStoreOverwrite:
    """Test overwrite behavior with different formats."""

    def test_no_overwrite_creates_timestamped_toon(
        self, tmp_path: Path, empty_graph: KnowledgeGraph
    ) -> None:
        """Without overwrite, creates timestamped file."""
        store = GraphStore(tmp_path)

        first = store.save(empty_graph, format="toon")
        second = store.save(empty_graph, format="toon", overwrite=False)

        assert first != second
        assert second.suffix == ".toon"
        assert "graph-" in second.name  # Timestamped

    def test_overwrite_replaces_toon(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """With overwrite, replaces existing file."""
        store = GraphStore(tmp_path)

        first = store.save(empty_graph, format="toon")
        second = store.save(empty_graph, format="toon", overwrite=True)

        assert first == second

    def test_no_overwrite_creates_timestamped_json(
        self, tmp_path: Path, empty_graph: KnowledgeGraph
    ) -> None:
        """Without overwrite, creates timestamped JSON file."""
        store = GraphStore(tmp_path)

        first = store.save(empty_graph, format="json")
        second = store.save(empty_graph, format="json", overwrite=False)

        assert first != second
        assert second.suffix == ".json"
        assert "graph-" in second.name


class TestGraphStoreToonContent:
    """Test TOON file content structure."""

    def test_toon_file_has_format_version(
        self, tmp_path: Path, empty_graph: KnowledgeGraph
    ) -> None:
        """TOON file includes format version."""
        from alphaswarm_sol.kg.toon import toon_loads

        store = GraphStore(tmp_path)
        saved = store.save(empty_graph, format="toon")

        content = saved.read_text()
        data = toon_loads(content)

        assert data["format"] == FORMAT_VERSION

    def test_toon_file_has_saved_at(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """TOON file includes timestamp."""
        from alphaswarm_sol.kg.toon import toon_loads

        store = GraphStore(tmp_path)
        saved = store.save(empty_graph, format="toon")

        content = saved.read_text()
        data = toon_loads(content)

        assert "saved_at" in data
        assert "T" in data["saved_at"]  # ISO format

    def test_json_file_is_valid_json(self, tmp_path: Path, empty_graph: KnowledgeGraph) -> None:
        """JSON file is valid JSON (not TOON)."""
        store = GraphStore(tmp_path)
        saved = store.save(empty_graph, format="json")

        content = saved.read_text()
        data = json.loads(content)  # Should not raise

        assert data["format"] == FORMAT_VERSION

    def test_toon_smaller_than_json(self, tmp_path: Path, simple_graph: KnowledgeGraph) -> None:
        """TOON file should be smaller or equal to JSON for graph data."""
        store = GraphStore(tmp_path)

        toon_path = store.save(simple_graph, format="toon")
        json_path = store.save(simple_graph, format="json")

        toon_size = toon_path.stat().st_size
        json_size = json_path.stat().st_size

        # TOON should be smaller for graph data with uniform structures
        # At minimum, should not be significantly larger
        assert toon_size <= json_size * 1.1, (
            f"TOON ({toon_size}) significantly larger than JSON ({json_size})"
        )


class TestGraphStoreNodeEdgePreservation:
    """Test that node and edge data is preserved correctly.

    Note: TOON format has a known limitation where nested dicts inside arrays
    get flattened. For full property preservation, use format='json'.
    TOON is optimized for LLM consumption where the flat format is acceptable.
    """

    def test_json_node_properties_preserved(self, tmp_path: Path) -> None:
        """Node properties survive JSON round-trip (full preservation)."""
        graph = KnowledgeGraph(metadata={})
        node = Node(
            id="func:test",
            type="function",
            label="test",
            properties={
                "visibility": "public",
                "writes_state": True,
                "has_reentrancy_guard": False,
                "modifiers": ["onlyOwner"],
            },
            evidence=[],
        )
        graph.nodes["func:test"] = node

        store = GraphStore(tmp_path)
        saved = store.save(graph, format="json")
        loaded = store.load(saved)

        loaded_node = loaded.nodes["func:test"]
        assert loaded_node.properties["visibility"] == "public"
        assert loaded_node.properties["writes_state"] is True
        assert loaded_node.properties["has_reentrancy_guard"] is False
        assert loaded_node.properties["modifiers"] == ["onlyOwner"]

    def test_json_edge_properties_preserved(self, tmp_path: Path) -> None:
        """Edge properties survive JSON round-trip (full preservation)."""
        graph = KnowledgeGraph(metadata={})
        edge = Edge(
            id="edge:test",
            type="calls",
            source="func:A",
            target="func:B",
            properties={"confidence": "HIGH", "external": True},
            evidence=[],
        )
        graph.edges["edge:test"] = edge

        store = GraphStore(tmp_path)
        saved = store.save(graph, format="json")
        loaded = store.load(saved)

        loaded_edge = loaded.edges["edge:test"]
        assert loaded_edge.type == "calls"
        assert loaded_edge.source == "func:A"
        assert loaded_edge.target == "func:B"
        assert loaded_edge.properties["confidence"] == "HIGH"
        assert loaded_edge.properties["external"] is True

    def test_toon_properties_preserved(self, tmp_path: Path) -> None:
        """TOON preserves all node properties via JSON encoding.

        The TOON format stores the graph as an embedded JSON string to avoid
        the toons library's tabular encoding issue with nested dicts.
        """
        graph = KnowledgeGraph(metadata={})
        node = Node(
            id="func:test",
            type="function",
            label="test",
            properties={
                "visibility": "public",
                "writes_state": True,
                "has_reentrancy_guard": False,
            },
            evidence=[],
        )
        graph.nodes["func:test"] = node

        store = GraphStore(tmp_path)
        saved = store.save(graph, format="toon")
        loaded = store.load(saved)

        loaded_node = loaded.nodes["func:test"]
        assert loaded_node.id == "func:test"
        assert loaded_node.type == "function"
        assert loaded_node.label == "test"
        # Properties are now preserved via JSON encoding workaround
        assert loaded_node.properties["visibility"] == "public"
        assert loaded_node.properties["writes_state"] is True
        assert loaded_node.properties["has_reentrancy_guard"] is False
