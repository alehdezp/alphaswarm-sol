"""Counterfactual query engine for what-if reasoning.

Per 05.11-07-PLAN.md: Enables counterfactual queries like:
- "If timelock_on_setAdmin existed, would chain break?"
- "If reentrancy_guard existed, what paths remain?"
- "If oracle had TWAP, what amplification is possible?"

Key features:
- CounterfactualEngine: Query engine for what-if analysis
- CounterfactualQuery: Query specification (condition, target, scope)
- CounterfactualResult: Result with chain_blocked, loss_reduction, remaining_paths

Usage:
    from alphaswarm_sol.economics.causal.counterfactual_engine import (
        CounterfactualEngine,
        CounterfactualQuery,
        CounterfactualResult,
    )

    engine = CounterfactualEngine()

    # Query: What if reentrancy guard existed?
    query = CounterfactualQuery(
        condition="reentrancy_guard_exists",
        target_edge="step:external_call",
        scope=CounterfactualScope.ALL_PATHS,
    )

    result = engine.query(ceg, query)
    print(f"Chain blocked: {result.chain_blocked}")
    print(f"Loss reduction: {result.loss_reduction:.1%}")
    print(f"Minimal fix: {result.minimal_fix}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from alphaswarm_sol.context.types import (
    CausalEdgeType,
    Confidence,
)

if TYPE_CHECKING:
    from .exploitation_graph import (
        CausalExploitationGraph,
        CausalPath,
        CEGEdge,
        CausalNode,
    )


class CounterfactualScope(Enum):
    """Scope of counterfactual analysis.

    Determines which paths are analyzed in the counterfactual query.
    """

    SINGLE_PATH = "single_path"  # Analyze a specific path only
    ALL_PATHS = "all_paths"  # Analyze all paths from root to loss
    FIRST_PATH = "first_path"  # Analyze first (highest probability) path


class CounterfactualType(Enum):
    """Type of counterfactual condition.

    Determines how the counterfactual is applied to the graph.
    """

    GUARD_EXISTS = "guard_exists"  # A guard/mitigation exists
    PARAM_CHANGED = "param_changed"  # A parameter value is changed
    EDGE_REMOVED = "edge_removed"  # A specific edge is removed
    NODE_BLOCKED = "node_blocked"  # A specific node is blocked


@dataclass
class CounterfactualQuery:
    """A counterfactual query for what-if analysis.

    Per 05.11-07-PLAN.md: Supports queries like:
    - "If timelock_on_setAdmin existed, would chain break?"
    - "If reentrancy_guard existed, what paths remain?"

    Attributes:
        condition: The hypothetical change (guard_exists, param_changed)
        target_edge: Which edge to evaluate blocking (node ID or edge ID)
        scope: Which paths to analyze
        counterfactual_type: How the counterfactual is applied
        blocking_probability: Probability that the counterfactual blocks (0-1)
        description: Human-readable description
    """

    condition: str
    target_edge: str
    scope: CounterfactualScope = CounterfactualScope.ALL_PATHS
    counterfactual_type: CounterfactualType = CounterfactualType.GUARD_EXISTS
    blocking_probability: float = 1.0
    description: str = ""

    def __post_init__(self) -> None:
        """Validate blocking probability range."""
        if not 0.0 <= self.blocking_probability <= 1.0:
            raise ValueError(f"blocking_probability must be 0.0-1.0, got {self.blocking_probability}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "condition": self.condition,
            "target_edge": self.target_edge,
            "scope": self.scope.value,
            "counterfactual_type": self.counterfactual_type.value,
            "blocking_probability": round(self.blocking_probability, 3),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CounterfactualQuery":
        """Create CounterfactualQuery from dictionary."""
        scope = data.get("scope", "all_paths")
        if isinstance(scope, str):
            scope = CounterfactualScope(scope)

        cf_type = data.get("counterfactual_type", "guard_exists")
        if isinstance(cf_type, str):
            cf_type = CounterfactualType(cf_type)

        return cls(
            condition=str(data.get("condition", "")),
            target_edge=str(data.get("target_edge", "")),
            scope=scope,
            counterfactual_type=cf_type,
            blocking_probability=float(data.get("blocking_probability", 1.0)),
            description=str(data.get("description", "")),
        )


@dataclass
class CounterfactualResult:
    """Result of a counterfactual query.

    Per 05.11-07-PLAN.md: Contains:
    - chain_blocked: Does the counterfactual break the chain?
    - loss_reduction: How much loss is prevented?
    - remaining_paths: Alternative attack paths
    - minimal_fix: Smallest change that blocks all paths

    Attributes:
        chain_blocked: Whether the counterfactual breaks the exploitation chain
        loss_reduction: Percentage of loss prevented (0-1)
        remaining_paths: List of paths that remain after counterfactual
        blocked_paths: List of paths that are blocked
        minimal_fix: The smallest change that blocks all paths
        confidence: Confidence in this result
        analysis_notes: Notes from the analysis
        evidence_refs: Evidence supporting this result
    """

    chain_blocked: bool
    loss_reduction: float
    remaining_paths: List["CausalPath"] = field(default_factory=list)
    blocked_paths: List["CausalPath"] = field(default_factory=list)
    minimal_fix: str = ""
    confidence: Confidence = Confidence.INFERRED
    analysis_notes: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate loss reduction range."""
        if not 0.0 <= self.loss_reduction <= 1.0:
            raise ValueError(f"loss_reduction must be 0.0-1.0, got {self.loss_reduction}")

    @property
    def is_effective(self) -> bool:
        """Whether the counterfactual is effective (blocks chain or reduces loss)."""
        return self.chain_blocked or self.loss_reduction > 0.5

    @property
    def partial_mitigation(self) -> bool:
        """Whether the counterfactual provides partial but not complete mitigation."""
        return not self.chain_blocked and self.loss_reduction > 0

    @property
    def paths_blocked_count(self) -> int:
        """Number of paths blocked by the counterfactual."""
        return len(self.blocked_paths)

    @property
    def paths_remaining_count(self) -> int:
        """Number of paths remaining after the counterfactual."""
        return len(self.remaining_paths)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chain_blocked": self.chain_blocked,
            "loss_reduction": round(self.loss_reduction, 3),
            "remaining_paths_count": self.paths_remaining_count,
            "blocked_paths_count": self.paths_blocked_count,
            "minimal_fix": self.minimal_fix,
            "confidence": self.confidence.value,
            "analysis_notes": self.analysis_notes,
            "evidence_refs": self.evidence_refs,
            "is_effective": self.is_effective,
            "partial_mitigation": self.partial_mitigation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CounterfactualResult":
        """Create CounterfactualResult from dictionary."""
        confidence = data.get("confidence", "inferred")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)

        return cls(
            chain_blocked=bool(data.get("chain_blocked", False)),
            loss_reduction=float(data.get("loss_reduction", 0.0)),
            remaining_paths=[],  # Paths not serialized in summary form
            blocked_paths=[],
            minimal_fix=str(data.get("minimal_fix", "")),
            confidence=confidence,
            analysis_notes=list(data.get("analysis_notes", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
        )


class CounterfactualEngine:
    """Engine for counterfactual queries on Causal Exploitation Graphs.

    Per 05.11-07-PLAN.md: Enables what-if reasoning for mitigation analysis.

    Usage:
        engine = CounterfactualEngine()

        # Simple query
        result = engine.query(ceg, CounterfactualQuery(
            condition="reentrancy_guard",
            target_edge="step:external_call",
        ))

        # Check if mitigation works
        if result.chain_blocked:
            print("Mitigation prevents exploitation")
        else:
            print(f"Loss reduction: {result.loss_reduction:.1%}")
    """

    def __init__(self) -> None:
        """Initialize the counterfactual engine."""
        self._cache: Dict[str, CounterfactualResult] = {}

    def query(
        self,
        graph: "CausalExploitationGraph",
        query: CounterfactualQuery,
    ) -> CounterfactualResult:
        """Execute a counterfactual query on a CEG.

        Args:
            graph: CausalExploitationGraph to analyze
            query: CounterfactualQuery specification

        Returns:
            CounterfactualResult with analysis
        """
        # Check cache
        cache_key = f"{graph.graph_id}:{query.condition}:{query.target_edge}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get all paths from root causes to financial losses
        root_causes = graph.get_root_causes()
        financial_losses = graph.get_financial_losses()

        all_paths: List["CausalPath"] = []
        for root in root_causes:
            for loss in financial_losses:
                paths = graph.get_all_paths(root.id, loss.id)
                all_paths.extend(paths)

        if not all_paths:
            # No paths to analyze
            return CounterfactualResult(
                chain_blocked=True,
                loss_reduction=1.0,
                minimal_fix=query.condition,
                analysis_notes=["No exploitation paths found"],
            )

        # Apply scope filter
        if query.scope == CounterfactualScope.FIRST_PATH:
            # Sort by probability and take first
            all_paths = sorted(all_paths, key=lambda p: p.cumulative_probability, reverse=True)
            all_paths = all_paths[:1]
        elif query.scope == CounterfactualScope.SINGLE_PATH:
            # Filter to paths containing target
            all_paths = [p for p in all_paths if self._path_contains_target(p, query.target_edge)]

        # Evaluate counterfactual on each path
        blocked_paths: List["CausalPath"] = []
        remaining_paths: List["CausalPath"] = []
        evidence_refs: Set[str] = set()
        notes: List[str] = []

        for path in all_paths:
            if self._counterfactual_blocks_path(path, query):
                blocked_paths.append(path)
                notes.append(f"Path {path.path_id} blocked by {query.condition}")
            else:
                remaining_paths.append(path)

            evidence_refs.update(path.evidence_refs)

        # Compute loss reduction
        total_blocked_loss = sum(p.cumulative_probability * p.amplification_factor for p in blocked_paths)
        total_original_loss = sum(p.cumulative_probability * p.amplification_factor for p in all_paths)

        loss_reduction = 0.0
        if total_original_loss > 0:
            loss_reduction = total_blocked_loss / total_original_loss

        # Check if chain is fully blocked
        chain_blocked = len(remaining_paths) == 0 and len(blocked_paths) > 0

        # Find minimal fix
        minimal_fix = ""
        if remaining_paths:
            minimal_fix = graph.find_minimal_fix(remaining_paths) or query.condition
        elif chain_blocked:
            minimal_fix = query.condition

        result = CounterfactualResult(
            chain_blocked=chain_blocked,
            loss_reduction=loss_reduction,
            remaining_paths=remaining_paths,
            blocked_paths=blocked_paths,
            minimal_fix=minimal_fix,
            confidence=Confidence.INFERRED if len(all_paths) > 3 else Confidence.CERTAIN,
            analysis_notes=notes,
            evidence_refs=list(evidence_refs),
        )

        self._cache[cache_key] = result
        return result

    def _path_contains_target(
        self,
        path: "CausalPath",
        target: str,
    ) -> bool:
        """Check if a path contains the target node or edge.

        Args:
            path: CausalPath to check
            target: Target node or edge ID

        Returns:
            True if path contains target
        """
        # Check nodes
        for node in path.nodes:
            if target in node.id or node.id == target:
                return True

        # Check edges
        for edge in path.edges:
            if target in edge.source or target in edge.target:
                return True
            if f"{edge.source}->{edge.target}" == target:
                return True

        return False

    def _counterfactual_blocks_path(
        self,
        path: "CausalPath",
        query: CounterfactualQuery,
    ) -> bool:
        """Check if a counterfactual blocks a path.

        Args:
            path: CausalPath to check
            query: CounterfactualQuery to apply

        Returns:
            True if counterfactual blocks this path
        """
        # Check if target is in the path
        if not self._path_contains_target(path, query.target_edge):
            return False

        # Apply blocking based on counterfactual type
        if query.counterfactual_type == CounterfactualType.GUARD_EXISTS:
            # Guard blocks if target matches any exploit step
            for node in path.nodes:
                if query.target_edge in node.id:
                    # Apply blocking probability
                    import random
                    return random.random() < query.blocking_probability

        elif query.counterfactual_type == CounterfactualType.EDGE_REMOVED:
            # Edge removed blocks if target edge is in path
            for edge in path.edges:
                if query.target_edge in edge.source or query.target_edge in edge.target:
                    return True

        elif query.counterfactual_type == CounterfactualType.NODE_BLOCKED:
            # Node blocked blocks if target node is in path
            for node in path.nodes:
                if query.target_edge == node.id or query.target_edge in node.id:
                    return True

        elif query.counterfactual_type == CounterfactualType.PARAM_CHANGED:
            # Parameter change - check if it affects amplification
            # For now, assume it reduces amplification by 50%
            for edge in path.edges:
                if edge.is_amplifying and query.target_edge in edge.target:
                    return False  # Reduces but doesn't block

        # Default: check if target matches anything in path
        return self._path_contains_target(path, query.target_edge)

    def batch_query(
        self,
        graph: "CausalExploitationGraph",
        queries: List[CounterfactualQuery],
    ) -> List[CounterfactualResult]:
        """Execute multiple counterfactual queries.

        Args:
            graph: CausalExploitationGraph to analyze
            queries: List of CounterfactualQuery specifications

        Returns:
            List of CounterfactualResult objects
        """
        return [self.query(graph, q) for q in queries]

    def find_effective_mitigations(
        self,
        graph: "CausalExploitationGraph",
        candidate_mitigations: List[str],
        min_loss_reduction: float = 0.5,
    ) -> List[tuple[str, CounterfactualResult]]:
        """Find which candidate mitigations are effective.

        Args:
            graph: CausalExploitationGraph to analyze
            candidate_mitigations: List of mitigation IDs to test
            min_loss_reduction: Minimum loss reduction to be considered effective

        Returns:
            List of (mitigation_id, result) tuples for effective mitigations
        """
        effective: List[tuple[str, CounterfactualResult]] = []

        for mitigation in candidate_mitigations:
            query = CounterfactualQuery(
                condition=mitigation,
                target_edge=mitigation,
                scope=CounterfactualScope.ALL_PATHS,
            )
            result = self.query(graph, query)

            if result.chain_blocked or result.loss_reduction >= min_loss_reduction:
                effective.append((mitigation, result))

        # Sort by effectiveness (chain blocked first, then by loss reduction)
        effective.sort(key=lambda x: (not x[1].chain_blocked, -x[1].loss_reduction))

        return effective

    def clear_cache(self) -> None:
        """Clear the query cache."""
        self._cache.clear()


# Export all types
__all__ = [
    "CounterfactualScope",
    "CounterfactualType",
    "CounterfactualQuery",
    "CounterfactualResult",
    "CounterfactualEngine",
]
