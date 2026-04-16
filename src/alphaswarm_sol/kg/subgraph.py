"""Phase 8: Subgraph Extraction.

This module provides query-aware subgraph extraction for focused analysis.
It enables efficient LLM consumption by extracting relevant portions of
the knowledge graph based on focal nodes and analysis requirements.

Key Concepts:
- SubGraph: A subset of the knowledge graph with relevance scoring
- Extraction: Query-aware node selection from focal points
- Relevance: Distance, risk, and query-based scoring
- Serialization: Token-efficient format for LLM consumption
- Omissions: Explicit tracking of pruned/excluded nodes and edges (v2 contract)
- Coverage: Deterministic coverage score per v2 contract formula
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import deque
import json
import re


# =============================================================================
# Omission Ledger (v2 Contract Compliance)
# =============================================================================


class CutSetReason(str, Enum):
    """Reasons for traversal blockers in the cut set."""
    MODIFIER_NOT_TRAVERSED = "modifier_not_traversed"
    INHERITED_NOT_TRAVERSED = "inherited_not_traversed"
    EXTERNAL_TARGET_UNKNOWN = "external_target_unknown"
    BUDGET_EXCEEDED = "budget_exceeded"
    DEPTH_LIMIT_REACHED = "depth_limit_reached"
    LIBRARY_EXCLUDED = "library_excluded"


class SliceMode(str, Enum):
    """Slicing mode for omission tracking."""
    STANDARD = "standard"
    DEBUG = "debug"


@dataclass
class CutSetEntry:
    """A traversal blocker in the omission cut set.

    Represents a node or edge that blocked graph traversal during
    subgraph extraction.
    """
    blocker: str  # Node or edge ID
    reason: CutSetReason
    impact: str = ""  # Human-readable impact description

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "blocker": self.blocker,
            "reason": self.reason.value,
            "impact": self.impact,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CutSetEntry":
        """Deserialize from dictionary."""
        reason_str = data.get("reason", "budget_exceeded")
        try:
            reason = CutSetReason(reason_str)
        except ValueError:
            reason = CutSetReason.BUDGET_EXCEEDED
        return CutSetEntry(
            blocker=str(data.get("blocker", "")),
            reason=reason,
            impact=str(data.get("impact", "")),
        )


@dataclass
class OmissionLedger:
    """Tracks what was omitted during subgraph extraction.

    Per v2 contract, this must be present in all subgraph outputs.
    Coverage score follows the formal definition:

    coverage_score = captured_nodes_weight / relevant_nodes_weight

    Where:
    - captured_nodes = nodes in the subgraph
    - relevant_nodes = PPR_selected ∪ query_matched ∪ dependency_closed

    Attributes:
        coverage_score: Ratio of captured to relevant nodes (0.0-1.0)
        cut_set: Traversal blockers that prevented expansion
        excluded_edges: Edge types that were filtered out
        omitted_nodes: Node IDs that were pruned (optional detail)
        slice_mode: Current slicing mode (standard/debug)
    """
    coverage_score: float = 1.0
    cut_set: List[CutSetEntry] = field(default_factory=list)
    excluded_edges: List[str] = field(default_factory=list)
    omitted_nodes: List[str] = field(default_factory=list)
    slice_mode: SliceMode = SliceMode.STANDARD

    # Internal tracking for coverage calculation
    _relevant_nodes: Set[str] = field(default_factory=set, repr=False)
    _captured_nodes: Set[str] = field(default_factory=set, repr=False)

    def add_cut_set_entry(
        self,
        blocker: str,
        reason: CutSetReason,
        impact: str = "",
    ) -> None:
        """Add a traversal blocker to the cut set."""
        self.cut_set.append(CutSetEntry(blocker, reason, impact))

    def add_excluded_edge(self, edge_type: str) -> None:
        """Record an excluded edge type."""
        if edge_type not in self.excluded_edges:
            self.excluded_edges.append(edge_type)

    def add_omitted_node(self, node_id: str) -> None:
        """Record an omitted node ID."""
        self.omitted_nodes.append(node_id)

    def compute_coverage_score(
        self,
        captured_nodes: Set[str],
        relevant_nodes: Set[str],
    ) -> float:
        """Compute coverage score per v2 contract formula.

        Args:
            captured_nodes: Nodes included in the subgraph
            relevant_nodes: PPR_selected ∪ query_matched ∪ dependency_closed

        Returns:
            Coverage ratio between 0.0 and 1.0
        """
        self._captured_nodes = captured_nodes
        self._relevant_nodes = relevant_nodes

        if not relevant_nodes:
            self.coverage_score = 1.0  # No relevant nodes = full coverage
            return self.coverage_score

        # Use uniform weighting (each node has weight 1)
        captured_weight = len(captured_nodes & relevant_nodes)
        relevant_weight = len(relevant_nodes)

        self.coverage_score = captured_weight / relevant_weight
        return self.coverage_score

    def has_omissions(self) -> bool:
        """Check if any omissions are present."""
        return (
            len(self.cut_set) > 0
            or len(self.excluded_edges) > 0
            or len(self.omitted_nodes) > 0
            or self.coverage_score < 1.0
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (v2 contract format)."""
        return {
            "coverage_score": round(self.coverage_score, 4),
            "cut_set": [entry.to_dict() for entry in self.cut_set],
            "excluded_edges": self.excluded_edges,
            "omitted_nodes": self.omitted_nodes,
            "slice_mode": self.slice_mode.value,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "OmissionLedger":
        """Deserialize from dictionary."""
        mode_str = data.get("slice_mode", "standard")
        try:
            slice_mode = SliceMode(mode_str)
        except ValueError:
            slice_mode = SliceMode.STANDARD

        ledger = OmissionLedger(
            coverage_score=float(data.get("coverage_score", 1.0)),
            excluded_edges=list(data.get("excluded_edges", [])),
            omitted_nodes=list(data.get("omitted_nodes", [])),
            slice_mode=slice_mode,
        )
        for entry_data in data.get("cut_set", []):
            ledger.cut_set.append(CutSetEntry.from_dict(entry_data))
        return ledger

    @staticmethod
    def empty() -> "OmissionLedger":
        """Create an empty omission ledger with full coverage."""
        return OmissionLedger(
            coverage_score=1.0,
            cut_set=[],
            excluded_edges=[],
            omitted_nodes=[],
            slice_mode=SliceMode.STANDARD,
        )


@dataclass
class SubGraphNode:
    """A node in the subgraph with relevance metadata."""
    id: str
    type: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0
    distance_from_focal: int = 0
    is_focal: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "properties": self.properties,
            "relevance_score": self.relevance_score,
            "distance_from_focal": self.distance_from_focal,
            "is_focal": self.is_focal,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SubGraphNode":
        """Deserialize from dictionary."""
        return SubGraphNode(
            id=str(data.get("id", "")),
            type=str(data.get("type", "")),
            label=str(data.get("label", "")),
            properties=dict(data.get("properties", {})),
            relevance_score=float(data.get("relevance_score", 0.0)),
            distance_from_focal=int(data.get("distance_from_focal", 0)),
            is_focal=bool(data.get("is_focal", False)),
        )


@dataclass
class SubGraphEdge:
    """An edge in the subgraph."""
    id: str
    type: str
    source: str
    target: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "properties": self.properties,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SubGraphEdge":
        """Deserialize from dictionary."""
        return SubGraphEdge(
            id=str(data.get("id", "")),
            type=str(data.get("type", "")),
            source=str(data.get("source", "")),
            target=str(data.get("target", "")),
            properties=dict(data.get("properties", {})),
        )


@dataclass
class SubGraph:
    """A subset of the knowledge graph with relevance scoring.

    Contains nodes and edges extracted based on focal points and
    analysis requirements, with relevance scoring for prioritization.

    Per v2 contract, all subgraph outputs include an omission ledger
    with coverage_score, cut_set, excluded_edges, and slice_mode.
    """
    nodes: Dict[str, SubGraphNode] = field(default_factory=dict)
    edges: Dict[str, SubGraphEdge] = field(default_factory=dict)
    focal_node_ids: List[str] = field(default_factory=list)
    analysis_type: str = "vulnerability"
    query: str = ""
    omissions: OmissionLedger = field(default_factory=OmissionLedger.empty)

    def add_node(self, node: SubGraphNode) -> None:
        """Add a node to the subgraph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: SubGraphEdge) -> None:
        """Add an edge to the subgraph."""
        # Only add if both endpoints exist
        if edge.source in self.nodes and edge.target in self.nodes:
            self.edges[edge.id] = edge

    def get_node(self, node_id: str) -> Optional[SubGraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> List[SubGraphNode]:
        """Get all nodes of a specific type."""
        return [n for n in self.nodes.values() if n.type == node_type]

    def get_high_relevance_nodes(self, threshold: float = 5.0) -> List[SubGraphNode]:
        """Get nodes with relevance above threshold."""
        return [n for n in self.nodes.values() if n.relevance_score >= threshold]

    def prune_by_relevance(self, min_relevance: float) -> None:
        """Remove nodes below relevance threshold (keeping focal nodes).

        Updates omission ledger with pruned nodes.
        """
        to_remove = [
            node_id for node_id, node in self.nodes.items()
            if node.relevance_score < min_relevance and not node.is_focal
        ]
        for node_id in to_remove:
            self.omissions.add_omitted_node(node_id)
            del self.nodes[node_id]
        # Remove orphaned edges
        self._remove_orphaned_edges()
        # Recompute coverage if we have relevant nodes tracked
        if self.omissions._relevant_nodes:
            self.omissions.compute_coverage_score(
                set(self.nodes.keys()),
                self.omissions._relevant_nodes,
            )

    def prune_by_risk_score(self, min_risk: float) -> None:
        """Remove nodes below risk score threshold (keeping focal nodes).

        Updates omission ledger with pruned nodes.
        """
        to_remove = []
        for node_id, node in self.nodes.items():
            if node.is_focal:
                continue
            risk = node.properties.get("risk_score", 0)
            if not risk:
                # Try to get from function properties
                risk = node.properties.get("attack_potential", 0)
            if risk < min_risk:
                to_remove.append(node_id)
        for node_id in to_remove:
            self.omissions.add_omitted_node(node_id)
            del self.nodes[node_id]
        self._remove_orphaned_edges()
        # Recompute coverage if we have relevant nodes tracked
        if self.omissions._relevant_nodes:
            self.omissions.compute_coverage_score(
                set(self.nodes.keys()),
                self.omissions._relevant_nodes,
            )

    def limit_nodes(self, max_nodes: int) -> None:
        """Limit to top N nodes by relevance (keeping focal nodes).

        Updates omission ledger with pruned nodes and adds a cut_set entry
        when the budget is exceeded.
        """
        if len(self.nodes) <= max_nodes:
            return

        # Separate focal and non-focal
        focal = [(nid, n) for nid, n in self.nodes.items() if n.is_focal]
        non_focal = [(nid, n) for nid, n in self.nodes.items() if not n.is_focal]

        # Sort non-focal by relevance (descending)
        non_focal.sort(key=lambda x: x[1].relevance_score, reverse=True)

        # Keep focal + top non-focal up to limit
        keep_count = max_nodes - len(focal)
        keep_ids = set([nid for nid, _ in focal])
        keep_ids.update([nid for nid, _ in non_focal[:keep_count]])

        # Remove nodes not in keep set and track in omissions
        to_remove = [nid for nid in self.nodes.keys() if nid not in keep_ids]
        for node_id in to_remove:
            self.omissions.add_omitted_node(node_id)
            del self.nodes[node_id]
        self._remove_orphaned_edges()

        # Add cut_set entry if we actually pruned
        if to_remove:
            self.omissions.add_cut_set_entry(
                blocker=f"max_nodes:{max_nodes}",
                reason=CutSetReason.BUDGET_EXCEEDED,
                impact=f"Pruned {len(to_remove)} nodes to fit budget of {max_nodes}",
            )

        # Recompute coverage if we have relevant nodes tracked
        if self.omissions._relevant_nodes:
            self.omissions.compute_coverage_score(
                set(self.nodes.keys()),
                self.omissions._relevant_nodes,
            )

    def order_by(self, keys: List[str]) -> List[SubGraphNode]:
        """Return nodes ordered by specified keys."""
        def sort_key(node: SubGraphNode) -> Tuple:
            values = []
            for key in keys:
                if key == "relevance_score":
                    values.append(-node.relevance_score)  # Descending
                elif key == "risk_score":
                    values.append(-node.properties.get("risk_score", 0))
                elif key == "depth" or key == "distance":
                    values.append(node.distance_from_focal)
                elif key == "centrality":
                    values.append(-self._compute_centrality(node.id))
                else:
                    values.append(0)
            return tuple(values)

        return sorted(self.nodes.values(), key=sort_key)

    def _compute_centrality(self, node_id: str) -> int:
        """Compute simple degree centrality."""
        count = 0
        for edge in self.edges.values():
            if edge.source == node_id or edge.target == node_id:
                count += 1
        return count

    def _remove_orphaned_edges(self) -> None:
        """Remove edges where either endpoint is missing."""
        to_remove = [
            edge_id for edge_id, edge in self.edges.items()
            if edge.source not in self.nodes or edge.target not in self.nodes
        ]
        for edge_id in to_remove:
            del self.edges[edge_id]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (v2 contract compliant)."""
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": {eid: e.to_dict() for eid, e in self.edges.items()},
            "focal_node_ids": self.focal_node_ids,
            "analysis_type": self.analysis_type,
            "query": self.query,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "omissions": self.omissions.to_dict(),
            "coverage_score": self.omissions.coverage_score,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SubGraph":
        """Deserialize from dictionary."""
        # Parse omissions if present, otherwise create empty ledger
        omissions_data = data.get("omissions", {})
        if omissions_data:
            omissions = OmissionLedger.from_dict(omissions_data)
        else:
            omissions = OmissionLedger.empty()

        sg = SubGraph(
            focal_node_ids=list(data.get("focal_node_ids", [])),
            analysis_type=str(data.get("analysis_type", "vulnerability")),
            query=str(data.get("query", "")),
            omissions=omissions,
        )
        for nid, ndata in data.get("nodes", {}).items():
            sg.nodes[nid] = SubGraphNode.from_dict(ndata)
        for eid, edata in data.get("edges", {}).items():
            sg.edges[eid] = SubGraphEdge.from_dict(edata)
        return sg

    def to_compact_json(self) -> str:
        """Serialize to compact JSON for LLM consumption."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    def to_llm_format(self, max_tokens: int = 2000) -> str:
        """Format subgraph for LLM consumption with token limit.

        Creates a structured text representation optimized for LLM understanding.
        Includes coverage score and omission summary per v2 contract.
        """
        lines = []
        lines.append(f"# Subgraph Analysis ({self.analysis_type})")
        if self.query:
            lines.append(f"Query: {self.query}")
        lines.append(f"Nodes: {len(self.nodes)} | Edges: {len(self.edges)} | Coverage: {self.omissions.coverage_score:.2f}")

        # Add omission summary if there are omissions
        if self.omissions.has_omissions():
            lines.append(f"Omissions: {len(self.omissions.omitted_nodes)} nodes omitted, {len(self.omissions.cut_set)} cut points")
        lines.append("")

        # Group nodes by type
        by_type: Dict[str, List[SubGraphNode]] = {}
        for node in self.order_by(["relevance_score", "risk_score"]):
            by_type.setdefault(node.type, []).append(node)

        # Format each type
        for node_type, nodes in by_type.items():
            lines.append(f"## {node_type}s ({len(nodes)})")
            for node in nodes[:10]:  # Limit per type
                focal_marker = " [FOCAL]" if node.is_focal else ""
                risk = node.properties.get("risk_score", "")
                risk_str = f" risk={risk:.1f}" if risk else ""
                role = node.properties.get("semantic_role", "")
                role_str = f" role={role}" if role else ""
                lines.append(f"- {node.label}{focal_marker}{risk_str}{role_str}")

                # Add key properties
                ops = node.properties.get("semantic_ops", [])
                if ops:
                    lines.append(f"  ops: {', '.join(ops[:5])}")
            lines.append("")

        # Estimate tokens (rough: 4 chars per token)
        result = "\n".join(lines)
        estimated_tokens = len(result) // 4
        if estimated_tokens > max_tokens:
            # Truncate
            char_limit = max_tokens * 4
            result = result[:char_limit] + "\n... (truncated)"

        return result


class SubgraphExtractor:
    """Extracts query-aware subgraphs from the knowledge graph.

    Performs ego-graph extraction starting from focal nodes,
    with vulnerability-aware expansion and relevance scoring.
    """

    def __init__(self, graph: Any):
        """Initialize with a KnowledgeGraph.

        Args:
            graph: KnowledgeGraph instance
        """
        self.graph = graph
        self._adjacency: Dict[str, Set[str]] = {}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        """Build adjacency list from graph edges."""
        for edge in self.graph.edges.values():
            self._adjacency.setdefault(edge.source, set()).add(edge.target)
            self._adjacency.setdefault(edge.target, set()).add(edge.source)

    def extract_for_analysis(
        self,
        focal_nodes: List[str],
        analysis_type: str = "vulnerability",
        query: str = "",
        max_hops: int = 2,
        max_nodes: int = 50,
        slice_mode: SliceMode = SliceMode.STANDARD,
    ) -> SubGraph:
        """Extract a subgraph for analysis starting from focal nodes.

        Args:
            focal_nodes: Starting node IDs for extraction
            analysis_type: Type of analysis ("vulnerability", "access", "data_flow")
            query: Optional query string for relevance scoring
            max_hops: Maximum distance from focal nodes
            max_nodes: Maximum nodes in result
            slice_mode: Standard or debug mode (debug bypasses some pruning)

        Returns:
            SubGraph with relevance-scored nodes and omission metadata
        """
        subgraph = SubGraph(
            focal_node_ids=focal_nodes,
            analysis_type=analysis_type,
            query=query,
        )
        subgraph.omissions.slice_mode = slice_mode

        # Step 1: Add focal nodes
        for node_id in focal_nodes:
            node = self.graph.nodes.get(node_id)
            if node:
                sg_node = self._create_subgraph_node(node, distance=0, is_focal=True)
                sg_node.relevance_score = 10.0  # Max relevance for focal
                subgraph.add_node(sg_node)

        # Step 2: BFS expansion (track depth limit in omissions)
        nodes_before_expansion = set(subgraph.nodes.keys())
        self._expand_neighbors(subgraph, max_hops, subgraph.omissions)
        nodes_after_expansion = set(subgraph.nodes.keys())

        # Step 3: Add vulnerability-relevant nodes
        if analysis_type == "vulnerability":
            self._add_vulnerability_context(subgraph, focal_nodes)

        # Step 4: Compute relevance scores
        self._compute_relevance_scores(subgraph, focal_nodes, query)

        # Step 5: Add relevant edges
        self._add_edges(subgraph)

        # Track relevant nodes BEFORE pruning (for coverage calculation)
        # relevant_nodes = BFS_selected ∪ vulnerability_context ∪ focal_nodes
        relevant_nodes = set(subgraph.nodes.keys())
        subgraph.omissions._relevant_nodes = relevant_nodes.copy()

        # Step 6: Prune and limit (unless debug mode bypasses pruning)
        if slice_mode == SliceMode.DEBUG:
            # Debug mode: still limit but track what would have been pruned
            pass  # In debug mode we skip pruning to expose full graph
        else:
            subgraph.limit_nodes(max_nodes)

        # Compute final coverage score
        captured_nodes = set(subgraph.nodes.keys())
        subgraph.omissions.compute_coverage_score(captured_nodes, relevant_nodes)

        return subgraph

    def extract_ego_graph(
        self,
        center_node: str,
        hops: int = 1,
        slice_mode: SliceMode = SliceMode.STANDARD,
    ) -> SubGraph:
        """Extract simple ego-graph around a center node.

        Args:
            center_node: Center node ID
            hops: Number of hops to expand
            slice_mode: Standard or debug mode

        Returns:
            SubGraph with ego-graph nodes and omission metadata
        """
        return self.extract_for_analysis(
            focal_nodes=[center_node],
            analysis_type="ego",
            max_hops=hops,
            max_nodes=100,
            slice_mode=slice_mode,
        )

    def _create_subgraph_node(
        self,
        node: Any,
        distance: int,
        is_focal: bool = False,
    ) -> SubGraphNode:
        """Create a SubGraphNode from a graph node."""
        # Extract relevant properties
        props = {}
        for key in [
            "semantic_ops", "behavioral_signature", "semantic_role",
            "visibility", "has_access_gate", "has_reentrancy_guard",
            "writes_state", "has_external_calls", "uses_delegatecall",
            "risk_score", "attack_potential", "security_tags",
        ]:
            if key in node.properties:
                props[key] = node.properties[key]

        return SubGraphNode(
            id=node.id,
            type=node.type,
            label=node.label,
            properties=props,
            distance_from_focal=distance,
            is_focal=is_focal,
        )

    def _expand_neighbors(
        self,
        subgraph: SubGraph,
        max_hops: int,
        omissions: Optional[OmissionLedger] = None,
    ) -> None:
        """Expand subgraph using BFS from focal nodes.

        Args:
            subgraph: SubGraph to expand
            max_hops: Maximum depth to traverse
            omissions: OmissionLedger to track cut set entries
        """
        visited = set(subgraph.nodes.keys())
        queue = deque()
        depth_limited_nodes: Set[str] = set()

        # Initialize queue with focal nodes at distance 0
        for node_id in subgraph.focal_node_ids:
            queue.append((node_id, 0))

        while queue:
            current_id, distance = queue.popleft()

            if distance >= max_hops:
                # Track nodes that were not expanded due to depth limit
                neighbors = self._adjacency.get(current_id, set())
                for neighbor_id in neighbors:
                    if neighbor_id not in visited:
                        depth_limited_nodes.add(neighbor_id)
                continue

            # Get neighbors
            neighbors = self._adjacency.get(current_id, set())
            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)

                node = self.graph.nodes.get(neighbor_id)
                if node:
                    sg_node = self._create_subgraph_node(node, distance + 1)
                    subgraph.add_node(sg_node)
                    queue.append((neighbor_id, distance + 1))

        # Record depth-limited nodes in omissions
        if omissions and depth_limited_nodes:
            omissions.add_cut_set_entry(
                blocker=f"depth_limit:{max_hops}",
                reason=CutSetReason.DEPTH_LIMIT_REACHED,
                impact=f"{len(depth_limited_nodes)} nodes beyond depth {max_hops} not traversed",
            )

    def _add_vulnerability_context(
        self,
        subgraph: SubGraph,
        focal_nodes: List[str],
    ) -> None:
        """Add vulnerability-relevant nodes not reached by BFS."""
        # Add state variables written by focal functions
        for focal_id in focal_nodes:
            node = self.graph.nodes.get(focal_id)
            if not node or node.type != "Function":
                continue

            # Find written state variables
            written_vars = node.properties.get("state_variables_written_names", [])
            for var_name in written_vars:
                for graph_node in self.graph.nodes.values():
                    if graph_node.type == "StateVariable" and graph_node.label == var_name:
                        if graph_node.id not in subgraph.nodes:
                            sg_node = self._create_subgraph_node(graph_node, distance=1)
                            sg_node.relevance_score = 7.0  # High relevance for state
                            subgraph.add_node(sg_node)

        # Add external call targets
        for focal_id in focal_nodes:
            node = self.graph.nodes.get(focal_id)
            if not node:
                continue

            if node.properties.get("has_external_calls"):
                # Find CALLS_EXTERNAL edges
                for edge in self.graph.edges.values():
                    if edge.source == focal_id and "EXTERNAL" in edge.type.upper():
                        target = self.graph.nodes.get(edge.target)
                        if target and target.id not in subgraph.nodes:
                            sg_node = self._create_subgraph_node(target, distance=1)
                            sg_node.relevance_score = 6.0
                            subgraph.add_node(sg_node)

    def _compute_relevance_scores(
        self,
        subgraph: SubGraph,
        focal_nodes: List[str],
        query: str,
    ) -> None:
        """Compute relevance scores for all nodes."""
        for node in subgraph.nodes.values():
            if node.is_focal:
                continue  # Already set to max

            score = compute_node_relevance(
                node,
                focal_nodes,
                query,
                subgraph,
            )
            node.relevance_score = score

    def _add_edges(self, subgraph: SubGraph) -> None:
        """Add edges between nodes in the subgraph."""
        node_ids = set(subgraph.nodes.keys())
        for edge in self.graph.edges.values():
            if edge.source in node_ids and edge.target in node_ids:
                sg_edge = SubGraphEdge(
                    id=edge.id,
                    type=edge.type,
                    source=edge.source,
                    target=edge.target,
                    properties=dict(edge.properties) if hasattr(edge, 'properties') else {},
                )
                subgraph.add_edge(sg_edge)


def compute_node_relevance(
    node: SubGraphNode,
    focal_nodes: List[str],
    query: str,
    subgraph: Optional[SubGraph] = None,
) -> float:
    """Compute relevance score for a node.

    Factors:
    - Distance from focal nodes (closer = higher)
    - Risk score from properties
    - Query keyword matching
    - Node type importance

    Args:
        node: Node to score
        focal_nodes: List of focal node IDs
        query: Query string for matching
        subgraph: Optional subgraph for context

    Returns:
        Relevance score (0-10)
    """
    score = 0.0

    # Distance factor (10 / (distance + 1))
    distance = node.distance_from_focal
    score += 10.0 / (distance + 1)

    # Risk score factor
    risk = node.properties.get("risk_score", 0)
    if not risk:
        risk = node.properties.get("attack_potential", 0)
    score += float(risk) * 0.5

    # Query relevance
    if query:
        query_lower = query.lower()
        # Check label match
        if node.label.lower() in query_lower or query_lower in node.label.lower():
            score += 3.0
        # Check type match
        if node.type.lower() in query_lower:
            score += 2.0
        # Check semantic role match
        role = node.properties.get("semantic_role", "")
        if role and role.lower() in query_lower:
            score += 2.0
        # Check operations match
        ops = node.properties.get("semantic_ops", [])
        for op in ops:
            if op.lower() in query_lower or query_lower in op.lower():
                score += 1.0
                break

    # Node type importance
    type_weights = {
        "Function": 1.5,
        "StateVariable": 1.3,
        "ExternalCallSite": 1.4,
        "Contract": 1.0,
        "Input": 0.8,
        "Event": 0.5,
    }
    score *= type_weights.get(node.type, 1.0)

    # Semantic role importance
    role = node.properties.get("semantic_role", "")
    role_weights = {
        "Checkpoint": 1.5,
        "EscapeHatch": 1.4,
        "EntryPoint": 1.3,
        "Guardian": 1.2,
        "StateAnchor": 1.3,
        "CriticalState": 1.4,
    }
    score *= role_weights.get(role, 1.0)

    return min(score, 10.0)


def min_distance_to_focal(node: SubGraphNode, focal_nodes: List[str]) -> int:
    """Get minimum distance from node to any focal node."""
    if node.id in focal_nodes:
        return 0
    return node.distance_from_focal


def extract_vulnerability_subgraph(
    graph: Any,
    vulnerability_type: str,
    max_nodes: int = 30,
) -> SubGraph:
    """Extract subgraph focused on a specific vulnerability type.

    Args:
        graph: KnowledgeGraph instance
        vulnerability_type: Type of vulnerability to focus on
        max_nodes: Maximum nodes in result

    Returns:
        SubGraph with vulnerability-relevant nodes
    """
    extractor = SubgraphExtractor(graph)

    # Find focal nodes based on vulnerability type
    focal_nodes = []
    vuln_patterns = {
        "reentrancy": ["has_external_calls", "state_write_after_external_call"],
        "access_control": ["writes_privileged_state", "has_access_gate"],
        "oracle": ["reads_oracle_price", "has_staleness_check"],
        "delegatecall": ["uses_delegatecall"],
    }

    target_props = vuln_patterns.get(vulnerability_type, [])
    for node in graph.nodes.values():
        if node.type == "Function":
            for prop in target_props:
                if node.properties.get(prop):
                    focal_nodes.append(node.id)
                    break

    if not focal_nodes:
        # Fallback: use all public functions
        focal_nodes = [
            n.id for n in graph.nodes.values()
            if n.type == "Function" and n.properties.get("visibility") in ["public", "external"]
        ][:5]

    return extractor.extract_for_analysis(
        focal_nodes=focal_nodes[:10],  # Limit focal nodes
        analysis_type="vulnerability",
        query=vulnerability_type,
        max_nodes=max_nodes,
    )


def get_subgraph_summary(subgraph: SubGraph) -> Dict[str, Any]:
    """Get summary statistics for a subgraph.

    Args:
        subgraph: SubGraph to summarize

    Returns:
        Dictionary with summary statistics including omission metadata
    """
    # Count by type
    type_counts: Dict[str, int] = {}
    for node in subgraph.nodes.values():
        type_counts[node.type] = type_counts.get(node.type, 0) + 1

    # Average relevance
    relevances = [n.relevance_score for n in subgraph.nodes.values()]
    avg_relevance = sum(relevances) / len(relevances) if relevances else 0

    # High relevance count
    high_relevance = len([r for r in relevances if r >= 5.0])

    # Focal nodes
    focal_count = len([n for n in subgraph.nodes.values() if n.is_focal])

    return {
        "node_count": len(subgraph.nodes),
        "edge_count": len(subgraph.edges),
        "type_counts": type_counts,
        "focal_count": focal_count,
        "avg_relevance": avg_relevance,
        "high_relevance_count": high_relevance,
        "analysis_type": subgraph.analysis_type,
        # v2 contract: omission metadata
        "coverage_score": subgraph.omissions.coverage_score,
        "omissions_present": subgraph.omissions.has_omissions(),
        "cut_set_count": len(subgraph.omissions.cut_set),
        "omitted_nodes_count": len(subgraph.omissions.omitted_nodes),
        "slice_mode": subgraph.omissions.slice_mode.value,
    }
