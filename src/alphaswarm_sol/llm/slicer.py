"""
Context Slicer

Extracts minimal KG subgraph for each analysis level.
Level 0: No slice needed
Level 1: Focal node only
Level 2: + Immediate neighbors
Level 3: + 2-hop neighborhood
"""

from dataclasses import dataclass
from typing import List, Set, Optional, Any, Tuple
from types import SimpleNamespace

from .triage import TriageLevel


@dataclass
class ContextSlice:
    """Extracted subgraph for analysis."""
    focal_node: str
    included_nodes: List[str]
    included_edges: List[Tuple[str, str, Any]]
    depth: int
    token_estimate: int

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/debugging."""
        return {
            "focal_node": self.focal_node,
            "node_count": len(self.included_nodes),
            "edge_count": len(self.included_edges),
            "depth": self.depth,
            "token_estimate": self.token_estimate,
        }


class ContextSlicer:
    """Extract minimal KG context for each analysis level."""

    # Depth per level
    DEPTH = {
        TriageLevel.LEVEL_0_SKIP: 0,
        TriageLevel.LEVEL_1_QUICK: 0,      # Focal only
        TriageLevel.LEVEL_2_FOCUSED: 1,    # + immediate neighbors
        TriageLevel.LEVEL_3_DEEP: 2,       # + 2-hop neighborhood
    }

    def slice(
        self,
        kg: Optional[Any],
        focal_node_id: str,
        level: TriageLevel
    ) -> ContextSlice:
        """
        Extract context slice for given level.

        Args:
            kg: Knowledge graph object (optional)
            focal_node_id: ID of the focal function node
            level: Triage level determining slice depth

        Returns:
            ContextSlice with extracted subgraph
        """
        depth = self.DEPTH[level]

        if depth == 0 or kg is None:
            # Focal node only
            return ContextSlice(
                focal_node=focal_node_id,
                included_nodes=[focal_node_id],
                included_edges=[],
                depth=0,
                token_estimate=50
            )

        try:
            return self._slice_with_pipeline(kg, focal_node_id, depth)
        except Exception:
            return self._slice_with_bfs(kg, focal_node_id, depth)

    def _slice_with_pipeline(
        self,
        kg: Any,
        focal_node_id: str,
        depth: int,
    ) -> ContextSlice:
        """Slice using the unified pipeline for consistent omissions metadata."""
        from alphaswarm_sol.kg.slicer import PipelineConfig, UnifiedSlicingPipeline

        graph = self._normalize_graph(kg)
        pipeline = UnifiedSlicingPipeline(graph)
        config = self._config_for_depth(depth)

        result = pipeline.slice([focal_node_id], config)
        nodes = list(result.graph.nodes.keys())

        edges: List[Tuple[str, str, Any]] = []
        for edge in result.graph.edges.values():
            if isinstance(edge, dict):
                source = edge.get("source")
                target = edge.get("target")
                edge_data = dict(edge)
            else:
                source = getattr(edge, "source", None)
                target = getattr(edge, "target", None)
                edge_data = edge.to_dict() if hasattr(edge, "to_dict") else {}
            if source is not None and target is not None:
                edges.append((source, target, edge_data))

        token_est = len(nodes) * 50 + len(edges) * 20
        return ContextSlice(
            focal_node=focal_node_id,
            included_nodes=nodes,
            included_edges=edges,
            depth=depth,
            token_estimate=token_est,
        )

    def _slice_with_bfs(
        self,
        kg: Any,
        focal_node_id: str,
        depth: int,
    ) -> ContextSlice:
        """Legacy BFS slicing fallback for robustness."""
        nodes: Set[str] = {focal_node_id}
        edges: List[Tuple[str, str, Any]] = []
        frontier = {focal_node_id}

        for _ in range(depth):
            new_frontier = set()
            for node_id in frontier:
                neighbors = self._get_neighbors(kg, node_id)
                for neighbor_id, edge_data in neighbors:
                    if neighbor_id not in nodes:
                        new_frontier.add(neighbor_id)
                        nodes.add(neighbor_id)
                        edges.append((node_id, neighbor_id, edge_data))
            frontier = new_frontier

        token_est = len(nodes) * 50 + len(edges) * 20
        return ContextSlice(
            focal_node=focal_node_id,
            included_nodes=list(nodes),
            included_edges=edges,
            depth=depth,
            token_estimate=token_est,
        )

    def _config_for_depth(self, depth: int) -> Any:
        """Map triage depth to unified pipeline config."""
        from alphaswarm_sol.kg.slicer import PipelineConfig

        if depth <= 0:
            return PipelineConfig(max_nodes=1, max_hops=0, category="general")
        if depth == 1:
            return PipelineConfig(
                max_nodes=25,
                max_hops=1,
                context_mode="standard",
                category="general",
            )
        return PipelineConfig(
            max_nodes=50,
            max_hops=2,
            context_mode="relaxed",
            category="general",
        )

    def _normalize_graph(self, kg: Any) -> Any:
        """Normalize dict-based graphs for unified pipeline compatibility."""
        if not isinstance(kg, dict):
            return kg

        nodes_list = kg.get("nodes", [])
        nodes_dict: dict[str, Any] = {}
        for node in nodes_list:
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            if not node_id:
                continue
            nodes_dict[node_id] = SimpleNamespace(
                id=node_id,
                type=node.get("type", ""),
                label=node.get("label", node_id),
                properties=node.get("properties", {}),
            )

        edges_list: list[Any] = []
        for edge in kg.get("edges", []):
            if isinstance(edge, dict):
                source = edge.get("source", "")
                target = edge.get("target", "")
                edge_copy = dict(edge)
                edge_copy.setdefault("id", f"{source}->{target}")
                edges_list.append(edge_copy)
            else:
                edges_list.append(edge)

        return SimpleNamespace(
            nodes=nodes_dict,
            edges=edges_list,
            metadata=kg.get("metadata", {}),
        )

    def _get_neighbors(
        self, kg: Any, node_id: str
    ) -> List[Tuple[str, Any]]:
        """
        Get neighbors of a node.

        Args:
            kg: Knowledge graph object
            node_id: Node ID to get neighbors for

        Returns:
            List of (neighbor_id, edge_data) tuples
        """
        neighbors = []

        # Handle dict-based KG representation
        if isinstance(kg, dict):
            edges = kg.get("edges", [])
            for edge in edges:
                if isinstance(edge, dict):
                    source = edge.get("source")
                    target = edge.get("target")
                    if source == node_id:
                        neighbors.append((target, edge))
                    elif target == node_id:
                        neighbors.append((source, edge))
                else:
                    # Handle tuple/list edges
                    if len(edge) >= 2:
                        if edge[0] == node_id:
                            neighbors.append((edge[1], edge[2] if len(edge) > 2 else {}))
                        elif edge[1] == node_id:
                            neighbors.append((edge[0], edge[2] if len(edge) > 2 else {}))

        # Handle networkx-like KG representation
        elif hasattr(kg, 'edges'):
            if hasattr(kg, 'successors'):
                # Directed graph
                for neighbor in kg.successors(node_id):
                    edge_data = kg.get_edge_data(node_id, neighbor)
                    neighbors.append((neighbor, edge_data or {}))
                for neighbor in kg.predecessors(node_id):
                    edge_data = kg.get_edge_data(neighbor, node_id)
                    neighbors.append((neighbor, edge_data or {}))
            elif hasattr(kg, 'neighbors'):
                # Undirected graph
                for neighbor in kg.neighbors(node_id):
                    edge_data = kg.get_edge_data(node_id, neighbor)
                    neighbors.append((neighbor, edge_data or {}))

        return neighbors

    def serialize_slice(self, slice_obj: ContextSlice) -> str:
        """
        Serialize context slice to token-efficient string.

        Args:
            slice_obj: ContextSlice to serialize

        Returns:
            Compact string representation
        """
        parts = [
            f"focal:{slice_obj.focal_node}",
            f"nodes:{len(slice_obj.included_nodes)}",
            f"edges:{len(slice_obj.included_edges)}",
            f"depth:{slice_obj.depth}"
        ]

        if slice_obj.included_edges:
            # Include edge summary
            edge_strs = []
            for src, tgt, data in slice_obj.included_edges[:10]:  # Limit to 10
                edge_type = data.get("type", "?") if isinstance(data, dict) else "?"
                edge_strs.append(f"{src}->{tgt}({edge_type})")
            parts.append(f"edges:[{','.join(edge_strs)}]")

        return "|".join(parts)
