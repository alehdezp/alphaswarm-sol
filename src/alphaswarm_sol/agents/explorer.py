"""Phase 9: Explorer Agent.

The Explorer Agent traces execution paths from entry points and identifies
critical paths that touch privileged state or involve dangerous operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from collections import deque

from alphaswarm_sol.agents.base import (
    VerificationAgent,
    AgentResult,
    AgentEvidence,
    EvidenceType,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode


@dataclass
class TracedPath:
    """A traced execution path through the subgraph."""
    path_id: str
    node_ids: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    touches_critical_state: bool = False
    has_external_calls: bool = False
    has_value_transfer: bool = False
    risk_score: float = 0.0
    entry_point: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "path_id": self.path_id,
            "node_ids": self.node_ids,
            "operations": self.operations,
            "touches_critical_state": self.touches_critical_state,
            "has_external_calls": self.has_external_calls,
            "has_value_transfer": self.has_value_transfer,
            "risk_score": self.risk_score,
            "entry_point": self.entry_point,
        }


class ExplorerAgent(VerificationAgent):
    """Explorer Agent for path tracing and control flow analysis.

    This agent traces all possible execution paths from entry points
    (public/external functions) and identifies paths that:
    - Touch critical/privileged state
    - Involve external calls
    - Move value
    - Violate CEI patterns
    """

    # Critical state patterns that indicate privileged operations
    CRITICAL_STATE_INDICATORS = {
        "writes_privileged_state",
        "state_write_after_external_call",
        "uses_delegatecall",
        "can_modify_owner",
        "can_modify_admin",
    }

    # Value movement operations
    VALUE_MOVEMENT_OPS = {
        "TRANSFERS_VALUE_OUT",
        "RECEIVES_VALUE_IN",
        "WRITES_USER_BALANCE",
        "READS_USER_BALANCE",
    }

    # External call indicators
    EXTERNAL_CALL_INDICATORS = {
        "has_external_calls",
        "has_low_level_calls",
        "uses_delegatecall",
    }

    def __init__(self, max_path_depth: int = 5, max_paths: int = 50):
        """Initialize the Explorer Agent.

        Args:
            max_path_depth: Maximum depth to trace paths
            max_paths: Maximum number of paths to enumerate
        """
        self.max_path_depth = max_path_depth
        self.max_paths = max_paths

    @property
    def agent_name(self) -> str:
        return "explorer"

    def confidence(self) -> float:
        return 0.85

    def analyze(self, subgraph: "SubGraph", query: str = "") -> AgentResult:
        """Analyze the subgraph by tracing execution paths.

        Args:
            subgraph: SubGraph to analyze
            query: Optional query context

        Returns:
            AgentResult with critical paths as findings
        """
        if not subgraph.nodes:
            return self._create_empty_result()

        # Find entry points (public/external functions)
        entry_points = self._find_entry_points(subgraph)

        if not entry_points:
            return self._create_empty_result()

        # Trace paths from each entry point
        all_paths = []
        for entry in entry_points:
            paths = self._trace_paths_from(entry, subgraph)
            all_paths.extend(paths)
            if len(all_paths) >= self.max_paths:
                break

        # Filter for critical paths
        critical_paths = [p for p in all_paths if self._is_critical_path(p)]

        # Create evidence from critical paths
        evidence = []
        for path in critical_paths:
            evidence.append(AgentEvidence(
                type=EvidenceType.PATH,
                data=path.to_dict(),
                description=self._describe_path(path),
                confidence=self._compute_path_confidence(path),
                source_nodes=path.node_ids,
            ))

        # Compute overall confidence
        if critical_paths:
            avg_confidence = sum(
                self._compute_path_confidence(p) for p in critical_paths
            ) / len(critical_paths)
            overall_confidence = self.confidence() * avg_confidence
        else:
            overall_confidence = self.confidence() * 0.5

        return AgentResult(
            agent=self.agent_name,
            matched=bool(critical_paths),
            findings=[p.to_dict() for p in critical_paths],
            confidence=overall_confidence,
            evidence=evidence,
            metadata={
                "total_paths_traced": len(all_paths),
                "critical_paths_found": len(critical_paths),
                "entry_points_analyzed": len(entry_points),
            },
        )

    def _find_entry_points(self, subgraph: "SubGraph") -> List[str]:
        """Find all entry point functions in the subgraph."""
        entry_points = []
        for node_id, node in subgraph.nodes.items():
            if node.type == "Function":
                visibility = node.properties.get("visibility", "")
                if visibility in ["public", "external"]:
                    # Exclude view/pure functions
                    state_mut = node.properties.get("state_mutability", "")
                    if state_mut not in ["view", "pure"]:
                        entry_points.append(node_id)
        return entry_points

    def _trace_paths_from(
        self, entry_point: str, subgraph: "SubGraph"
    ) -> List[TracedPath]:
        """Trace execution paths starting from an entry point.

        Uses BFS to explore reachable functions within max_path_depth.
        """
        paths = []
        path_count = 0

        # BFS queue: (current_node, path_so_far)
        queue: deque = deque([(entry_point, [entry_point])])
        visited_paths: Set[str] = set()

        while queue and path_count < self.max_paths:
            current, path_nodes = queue.popleft()

            # Create path hash to avoid duplicates
            path_hash = "->".join(path_nodes)
            if path_hash in visited_paths:
                continue
            visited_paths.add(path_hash)

            # Create traced path if meaningful (2+ nodes or single risky node)
            if len(path_nodes) >= 2 or self._is_single_node_risky(
                path_nodes[0], subgraph
            ):
                traced = self._create_traced_path(path_nodes, subgraph, entry_point)
                paths.append(traced)
                path_count += 1

            # Explore further if not at max depth
            if len(path_nodes) < self.max_path_depth:
                for next_node in self._get_callable_from(current, subgraph):
                    if next_node not in path_nodes:  # Avoid cycles
                        queue.append((next_node, path_nodes + [next_node]))

        return paths

    def _get_callable_from(
        self, node_id: str, subgraph: "SubGraph"
    ) -> List[str]:
        """Get functions callable from a given node."""
        callable_fns = []
        for edge_id, edge in subgraph.edges.items():
            if edge.source == node_id and edge.type == "CALLS":
                if edge.target in subgraph.nodes:
                    target = subgraph.nodes[edge.target]
                    if target.type == "Function":
                        callable_fns.append(edge.target)
        return callable_fns

    def _create_traced_path(
        self,
        node_ids: List[str],
        subgraph: "SubGraph",
        entry_point: str,
    ) -> TracedPath:
        """Create a TracedPath from a list of node IDs."""
        path_id = f"path:{hash('->'.join(node_ids)) % 10000:04d}"
        operations = []
        touches_critical = False
        has_external = False
        has_value = False
        risk_score = 0.0

        for node_id in node_ids:
            node = subgraph.nodes.get(node_id)
            if not node:
                continue

            props = node.properties

            # Collect operations
            ops = props.get("semantic_ops", [])
            operations.extend(ops)

            # Check for critical state access
            for indicator in self.CRITICAL_STATE_INDICATORS:
                if props.get(indicator):
                    touches_critical = True
                    risk_score += 1.0

            # Check for external calls
            for indicator in self.EXTERNAL_CALL_INDICATORS:
                if props.get(indicator):
                    has_external = True
                    risk_score += 0.5

            # Check for value movement
            if any(op in self.VALUE_MOVEMENT_OPS for op in ops):
                has_value = True
                risk_score += 0.5

            # Additional risk factors
            if props.get("state_write_after_external_call"):
                risk_score += 2.0
            if props.get("uses_delegatecall"):
                risk_score += 2.0
            if not props.get("has_access_gate"):
                if props.get("writes_privileged_state"):
                    risk_score += 1.5

        return TracedPath(
            path_id=path_id,
            node_ids=node_ids,
            operations=list(set(operations)),
            touches_critical_state=touches_critical,
            has_external_calls=has_external,
            has_value_transfer=has_value,
            risk_score=min(risk_score, 10.0),
            entry_point=entry_point,
        )

    def _is_single_node_risky(self, node_id: str, subgraph: "SubGraph") -> bool:
        """Check if a single node is risky enough to include."""
        node = subgraph.nodes.get(node_id)
        if not node:
            return False

        props = node.properties
        risk_factors = [
            props.get("state_write_after_external_call"),
            props.get("uses_delegatecall"),
            props.get("writes_privileged_state") and not props.get("has_access_gate"),
        ]
        return any(risk_factors)

    def _is_critical_path(self, path: TracedPath) -> bool:
        """Determine if a path is critical (should be flagged)."""
        # Critical if it touches privileged state
        if path.touches_critical_state:
            return True

        # Critical if it involves value transfer with external calls
        if path.has_value_transfer and path.has_external_calls:
            return True

        # Critical if risk score is high enough
        if path.risk_score >= 3.0:
            return True

        return False

    def _compute_path_confidence(self, path: TracedPath) -> float:
        """Compute confidence score for a traced path."""
        base = 0.5

        # Higher confidence for more indicators
        if path.touches_critical_state:
            base += 0.2
        if path.has_external_calls:
            base += 0.1
        if path.has_value_transfer:
            base += 0.1

        # Risk score contribution
        base += min(path.risk_score * 0.02, 0.1)

        return min(base, 1.0)

    def _describe_path(self, path: TracedPath) -> str:
        """Generate a human-readable description of a path."""
        parts = []

        if path.touches_critical_state:
            parts.append("touches critical state")
        if path.has_external_calls:
            parts.append("makes external calls")
        if path.has_value_transfer:
            parts.append("transfers value")

        if parts:
            desc = f"Path from {path.entry_point}: {', '.join(parts)}"
        else:
            desc = f"Path from {path.entry_point} with {len(path.node_ids)} steps"

        desc += f" (risk score: {path.risk_score:.1f})"
        return desc
