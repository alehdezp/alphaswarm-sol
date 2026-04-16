"""Core schema for the True VKG knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.rich_edge import RichEdge


@dataclass(frozen=True)
class Evidence:
    """Soft evidence that anchors a node or edge to source code.

    Phase 5.10: Added evidence_id field for canonical, deterministic,
    graph-versioned evidence identification. The evidence_id is:
    - Deterministic: Same inputs always produce same ID
    - Graph-versioned: Tied to specific build hash for reproducibility
    - Source-linked: Encodes file path and line range

    The evidence_id field is optional for backward compatibility but
    should be populated when a build hash is available.
    """

    file: str
    line_start: int | None = None
    line_end: int | None = None
    detail: str | None = None
    evidence_id: str | None = None  # EVD-xxxxxxxx format

    def to_dict(self) -> dict[str, Any]:
        result = {
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "detail": self.detail,
        }
        if self.evidence_id is not None:
            result["evidence_id"] = self.evidence_id
        return result

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Evidence":
        return Evidence(
            file=str(data.get("file") or ""),
            line_start=data.get("line_start"),
            line_end=data.get("line_end"),
            detail=data.get("detail"),
            evidence_id=data.get("evidence_id"),
        )

    def with_evidence_id(self, evidence_id: str) -> "Evidence":
        """Create a new Evidence with the given evidence_id.

        Since Evidence is frozen, this creates a new instance.

        Args:
            evidence_id: The canonical evidence ID (EVD-xxxxxxxx format)

        Returns:
            New Evidence instance with evidence_id set
        """
        return Evidence(
            file=self.file,
            line_start=self.line_start,
            line_end=self.line_end,
            detail=self.detail,
            evidence_id=evidence_id,
        )


@dataclass
class Node:
    """Graph node."""

    id: str
    type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "properties": self.properties,
            "evidence": [e.to_dict() for e in self.evidence],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Node":
        return Node(
            id=str(data.get("id") or ""),
            type=str(data.get("type") or ""),
            label=str(data.get("label") or ""),
            properties=dict(data.get("properties") or {}),
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
        )


@dataclass
class Edge:
    """Graph edge."""

    id: str
    type: str
    source: str
    target: str
    properties: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "properties": self.properties,
            "evidence": [e.to_dict() for e in self.evidence],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Edge":
        return Edge(
            id=str(data.get("id") or ""),
            type=str(data.get("type") or ""),
            source=str(data.get("source") or ""),
            target=str(data.get("target") or ""),
            properties=dict(data.get("properties") or {}),
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
        )


@dataclass
class KnowledgeGraph:
    """Knowledge graph container."""

    metadata: dict[str, Any] = field(default_factory=dict)
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)
    # Phase 5: Rich edges with intelligence (risk scores, pattern tags, etc.)
    rich_edges: dict[str, Any] = field(default_factory=dict)  # RichEdge objects
    # Phase 5: Meta-edges for higher-order relationships
    meta_edges: dict[str, Any] = field(default_factory=dict)  # MetaEdge objects

    def add_node(self, node: Node) -> Node:
        existing = self.nodes.get(node.id)
        if existing is None:
            self.nodes[node.id] = node
            return node
        if node.evidence:
            existing.evidence.extend(node.evidence)
        existing.properties.update(node.properties)
        return existing

    def add_edge(self, edge: Edge) -> Edge:
        existing = self.edges.get(edge.id)
        if existing is None:
            self.edges[edge.id] = edge
            return edge
        if edge.evidence:
            existing.evidence.extend(edge.evidence)
        existing.properties.update(edge.properties)
        return existing

    def add_rich_edge(self, rich_edge: "RichEdge") -> "RichEdge":
        """Add a RichEdge with intelligence metadata.

        Args:
            rich_edge: RichEdge with risk scores, pattern tags, etc.

        Returns:
            The added or existing RichEdge
        """
        existing = self.rich_edges.get(rich_edge.id)
        if existing is None:
            self.rich_edges[rich_edge.id] = rich_edge
            return rich_edge
        # Merge evidence and properties
        if rich_edge.evidence:
            existing.evidence.extend(rich_edge.evidence)
        existing.properties.update(rich_edge.properties)
        # Take max risk score
        existing.risk_score = max(existing.risk_score, rich_edge.risk_score)
        # Merge pattern tags
        for tag in rich_edge.pattern_tags:
            if tag not in existing.pattern_tags:
                existing.pattern_tags.append(tag)
        return existing

    def add_meta_edge(self, meta_edge: "RichEdge") -> "RichEdge":
        """Add a meta-edge for higher-order relationships.

        Args:
            meta_edge: MetaEdge (SIMILAR_TO, BUGGY_PATTERN_MATCH, etc.)

        Returns:
            The added or existing meta-edge
        """
        existing = self.meta_edges.get(meta_edge.id)
        if existing is None:
            self.meta_edges[meta_edge.id] = meta_edge
            return meta_edge
        return existing

    def get_high_risk_edges(self, threshold: float = 7.0) -> list[Any]:
        """Get all RichEdges with risk score above threshold.

        Args:
            threshold: Minimum risk score (default 7.0)

        Returns:
            List of high-risk RichEdge objects
        """
        return [e for e in self.rich_edges.values() if e.risk_score >= threshold]

    def get_edges_with_pattern(self, pattern: str) -> list[Any]:
        """Get all RichEdges with a specific pattern tag.

        Args:
            pattern: Pattern tag to search for (e.g., "reentrancy_risk")

        Returns:
            List of RichEdge objects with the pattern tag
        """
        return [e for e in self.rich_edges.values() if pattern in e.pattern_tags]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "rich_edges": [e.to_dict() for e in self.rich_edges.values()],
            "meta_edges": [e.to_dict() for e in self.meta_edges.values()],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "KnowledgeGraph":
        # Import here to avoid circular dependency
        from alphaswarm_sol.kg.rich_edge import RichEdge, MetaEdge

        graph = KnowledgeGraph(metadata=dict(data.get("metadata") or {}))
        for node_data in data.get("nodes", []):
            node = Node.from_dict(node_data)
            graph.nodes[node.id] = node
        for edge_data in data.get("edges", []):
            edge = Edge.from_dict(edge_data)
            graph.edges[edge.id] = edge
        # Load rich edges
        for rich_edge_data in data.get("rich_edges", []):
            rich_edge = RichEdge.from_dict(rich_edge_data)
            graph.rich_edges[rich_edge.id] = rich_edge
        # Load meta edges
        for meta_edge_data in data.get("meta_edges", []):
            meta_edge = MetaEdge.from_dict(meta_edge_data)
            graph.meta_edges[meta_edge.id] = meta_edge
        return graph
