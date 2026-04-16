"""Dominance Analysis for True VKG (Phase 5.9).

This module provides dominance tree computation for CFG-based path analysis,
enabling path-qualified operation ordering that distinguishes between
"always before", "sometimes before", "never before", and "unknown" relationships.

Key concepts:
- DominanceAnalyzer: Computes dominators and post-dominators using Cooper-Harvey-Kennedy
- OrderingRelation: Path-qualified ordering semantics
- PathQualifiedOrdering: Result type with confidence and reasoning
- ModifierChainSummary: Interprocedural ordering for modifier chains

Algorithm Reference:
    "A Simple, Fast Dominance Algorithm" - Keith D. Cooper, Timothy J. Harvey,
    and Ken Kennedy, Software Practice and Experience, 2001.

Unknown Emission Criteria:
    - CFG has unreachable nodes -> emit unknown
    - Entry/exit points cannot be determined -> emit unknown
    - Modifier body not available (external) -> emit unknown for cross-modifier ordering
    - Loop with unresolvable iteration count -> emit unknown for loop-carried dependencies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# =============================================================================
# Ordering Relation Types
# =============================================================================


class OrderingRelation(Enum):
    """Path-qualified ordering relationship between two operations.

    This enum represents the true semantic relationship between operations
    based on dominance analysis, not just CFG traversal order.

    Attributes:
        ALWAYS_BEFORE: A dominates B - A always executes before B on all paths
        SOMETIMES_BEFORE: A precedes B on at least one path, but not all
        NEVER_BEFORE: A is never before B on any feasible path
        UNKNOWN: Cannot determine relationship (truncated CFG, external code, etc.)
    """

    ALWAYS_BEFORE = "always_before"
    SOMETIMES_BEFORE = "sometimes_before"
    NEVER_BEFORE = "never_before"
    UNKNOWN = "unknown"


class GuardDominance(Enum):
    """Guard's dominance relationship to a protected sink.

    This enum classifies how a guard (modifier, require, etc.) relates
    to the code it's supposed to protect.

    Attributes:
        PRESENT: Guard exists somewhere in the function
        DOMINATING: Guard dominates all paths to the sink
        BYPASSABLE: Guard exists but at least one path bypasses it
        UNKNOWN: Dominance cannot be proven (external modifier, etc.)
    """

    PRESENT = "present"
    DOMINATING = "dominating"
    BYPASSABLE = "bypassable"
    UNKNOWN = "unknown"


# =============================================================================
# Result Types
# =============================================================================


@dataclass(frozen=True)
class PathQualifiedOrdering:
    """Result of path-qualified ordering analysis.

    Attributes:
        relation: The ordering relationship between two operations
        confidence: Confidence score (0.0-1.0)
        reason: Explanation for unknown results or low confidence
        evidence: Optional evidence references for the conclusion
    """

    relation: OrderingRelation
    confidence: float = 1.0
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    def is_definite(self) -> bool:
        """Check if the ordering is definitely known (not unknown or low confidence)."""
        return self.relation != OrderingRelation.UNKNOWN and self.confidence >= 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {
            "relation": self.relation.value,
            "confidence": self.confidence,
        }
        if self.reason:
            result["reason"] = self.reason
        if self.evidence:
            result["evidence"] = self.evidence
        return result


@dataclass
class ModifierSummary:
    """Summary of a modifier's dominance effects.

    Attributes:
        name: Modifier name
        entry_ops: Operations that execute at modifier entry (before _)
        exit_ops: Operations that execute at modifier exit (after _)
        has_revert: Whether modifier can revert (guard behavior)
        dominates_body: Whether modifier entry dominates function body
        is_external: Whether modifier body is external/unavailable
    """

    name: str
    entry_ops: FrozenSet[str] = field(default_factory=frozenset)
    exit_ops: FrozenSet[str] = field(default_factory=frozenset)
    has_revert: bool = False
    dominates_body: bool = True
    is_external: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "entry_ops": list(self.entry_ops),
            "exit_ops": list(self.exit_ops),
            "has_revert": self.has_revert,
            "dominates_body": self.dominates_body,
            "is_external": self.is_external,
        }


@dataclass
class ModifierChainSummary:
    """Summary of dominance effects for a chain of modifiers.

    For a function with modifiers A, B, C applied in order:
    - A's entry dominates B's entry dominates C's entry dominates function body
    - Function body's exit dominates C's exit dominates B's exit dominates A's exit

    Attributes:
        modifiers: Ordered list of modifier summaries (outermost first)
        combined_entry_ops: All entry ops from all modifiers
        combined_exit_ops: All exit ops from all modifiers
        any_external: Whether any modifier is external
        dominance_chain_intact: Whether dominance chain is complete
    """

    modifiers: List[ModifierSummary] = field(default_factory=list)
    combined_entry_ops: FrozenSet[str] = field(default_factory=frozenset)
    combined_exit_ops: FrozenSet[str] = field(default_factory=frozenset)
    any_external: bool = False
    dominance_chain_intact: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "modifiers": [m.to_dict() for m in self.modifiers],
            "combined_entry_ops": list(self.combined_entry_ops),
            "combined_exit_ops": list(self.combined_exit_ops),
            "any_external": self.any_external,
            "dominance_chain_intact": self.dominance_chain_intact,
        }


@dataclass
class InternalCallSummary:
    """Summary of an internal function call's effects.

    Attributes:
        function_name: Name of the called function
        entry_ops: Operations at function entry
        exit_ops: Operations at function exit
        has_external_call: Whether callee makes external calls
        summary_available: Whether full summary is available
    """

    function_name: str
    entry_ops: FrozenSet[str] = field(default_factory=frozenset)
    exit_ops: FrozenSet[str] = field(default_factory=frozenset)
    has_external_call: bool = False
    summary_available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "function_name": self.function_name,
            "entry_ops": list(self.entry_ops),
            "exit_ops": list(self.exit_ops),
            "has_external_call": self.has_external_call,
            "summary_available": self.summary_available,
        }


# =============================================================================
# CFG Node Abstraction
# =============================================================================


@dataclass
class CFGNodeInfo:
    """Abstract CFG node information for dominance analysis.

    This decouples dominance analysis from Slither's specific CFG representation.

    Attributes:
        node_id: Unique identifier for the node
        node_type: Type of node (entry, exit, regular, etc.)
        successors: IDs of successor nodes
        predecessors: IDs of predecessor nodes
        operations: Semantic operations at this node
        line_number: Source line number (if available)
        is_revert: Whether this node causes a revert
    """

    node_id: int
    node_type: str
    successors: List[int] = field(default_factory=list)
    predecessors: List[int] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    line_number: int = 0
    is_revert: bool = False


# =============================================================================
# Dominance Analyzer
# =============================================================================


class DominanceAnalyzer:
    """Computes dominators and post-dominators for a control flow graph.

    Uses the Cooper-Harvey-Kennedy iterative algorithm which is simple,
    fast, and efficient for typical CFG sizes (< 30k nodes).

    The algorithm computes:
    - Dominators: Node A dominates B if all paths from entry to B go through A
    - Post-dominators: Node A post-dominates B if all paths from B to exit go through A

    Usage:
        analyzer = DominanceAnalyzer(cfg_nodes)
        if analyzer.dominates(node_a, node_b):
            # A always executes before B

    Unknown Emission:
        The analyzer emits UNKNOWN ordering when:
        - CFG has unreachable nodes (indicates incomplete analysis)
        - Entry or exit cannot be determined
        - External code prevents complete analysis
    """

    def __init__(
        self,
        nodes: List[CFGNodeInfo],
        entry_id: Optional[int] = None,
        exit_id: Optional[int] = None,
    ) -> None:
        """Initialize analyzer with CFG nodes.

        Args:
            nodes: List of CFG nodes with successor/predecessor info
            entry_id: ID of entry node (auto-detected if None)
            exit_id: ID of exit node (auto-detected if None)
        """
        self._nodes: Dict[int, CFGNodeInfo] = {n.node_id: n for n in nodes}
        self._entry_id = entry_id
        self._exit_id = exit_id

        # Auto-detect entry/exit if not provided
        if self._entry_id is None:
            self._entry_id = self._find_entry()
        if self._exit_id is None:
            self._exit_id = self._find_exit()

        # Dominance sets
        self._dominators: Dict[int, Set[int]] = {}
        self._post_dominators: Dict[int, Set[int]] = {}

        # Immediate dominators
        self._idom: Dict[int, Optional[int]] = {}
        self._ipdom: Dict[int, Optional[int]] = {}

        # Analysis state
        self._dominators_computed = False
        self._post_dominators_computed = False
        self._has_unreachable = False

    def _find_entry(self) -> Optional[int]:
        """Find entry node (node with no predecessors or type 'entry')."""
        for node in self._nodes.values():
            if node.node_type.lower() in ("entry", "entry_point", "entrypoint"):
                return node.node_id
            if not node.predecessors:
                return node.node_id
        return None

    def _find_exit(self) -> Optional[int]:
        """Find exit node (node with no successors or type 'exit')."""
        for node in self._nodes.values():
            if node.node_type.lower() in ("exit", "exit_point", "return"):
                return node.node_id
            if not node.successors:
                return node.node_id
        return None

    @property
    def entry_id(self) -> Optional[int]:
        """Get entry node ID."""
        return self._entry_id

    @property
    def exit_id(self) -> Optional[int]:
        """Get exit node ID."""
        return self._exit_id

    @property
    def has_unreachable_nodes(self) -> bool:
        """Check if CFG has unreachable nodes."""
        return self._has_unreachable

    # =========================================================================
    # Cooper-Harvey-Kennedy Dominance Algorithm
    # =========================================================================

    def compute_dominators(self) -> Dict[int, Set[int]]:
        """Compute dominators for all nodes using Cooper-Harvey-Kennedy algorithm.

        The algorithm:
            dom[entry] = {entry}
            for all other nodes n: dom[n] = all_nodes
            while changes:
                for each node n (except entry):
                    dom[n] = {n} ∪ (∩ dom[p] for p in predecessors(n))

        Returns:
            Dictionary mapping node ID to set of dominator node IDs
        """
        if self._dominators_computed:
            return self._dominators

        if self._entry_id is None or not self._nodes:
            self._dominators = {}
            self._dominators_computed = True
            return self._dominators

        all_nodes = set(self._nodes.keys())

        # Initialize: entry dominates only itself, others have all nodes
        self._dominators = {n: set(all_nodes) for n in all_nodes}
        self._dominators[self._entry_id] = {self._entry_id}

        # Iterative refinement
        changed = True
        iterations = 0
        max_iterations = len(all_nodes) * 2  # Safety bound

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for node_id in all_nodes:
                if node_id == self._entry_id:
                    continue

                node = self._nodes[node_id]
                if not node.predecessors:
                    # Unreachable from entry
                    self._has_unreachable = True
                    continue

                # New dominators = {self} ∪ (∩ dom[pred] for pred in predecessors)
                pred_doms = [self._dominators.get(p, all_nodes) for p in node.predecessors]
                if pred_doms:
                    new_dom = {node_id} | set.intersection(*pred_doms)
                else:
                    new_dom = {node_id}

                if new_dom != self._dominators[node_id]:
                    self._dominators[node_id] = new_dom
                    changed = True

        # Check for unreachable nodes (nodes not dominated by entry)
        for node_id in all_nodes:
            if node_id != self._entry_id and self._entry_id not in self._dominators.get(node_id, set()):
                self._has_unreachable = True

        self._dominators_computed = True
        self._compute_immediate_dominators()
        return self._dominators

    def _compute_immediate_dominators(self) -> None:
        """Compute immediate dominators from dominator sets."""
        if not self._dominators:
            return

        for node_id, doms in self._dominators.items():
            # Immediate dominator is the unique dominator that doesn't dominate
            # any other dominator (except itself)
            if node_id == self._entry_id:
                self._idom[node_id] = None
                continue

            # Remove self from dominators
            strict_doms = doms - {node_id}
            if not strict_doms:
                self._idom[node_id] = None
                continue

            # Find idom: dominator closest to node
            idom = None
            for candidate in strict_doms:
                candidate_doms = self._dominators.get(candidate, set()) - {candidate}
                # Candidate is idom if all other strict dominators dominate it
                if strict_doms - {candidate} <= candidate_doms:
                    idom = candidate
                    break

            self._idom[node_id] = idom

    def compute_post_dominators(self) -> Dict[int, Set[int]]:
        """Compute post-dominators using reverse CFG.

        Post-dominator: Node A post-dominates B if all paths from B to exit
        go through A.

        Returns:
            Dictionary mapping node ID to set of post-dominator node IDs
        """
        if self._post_dominators_computed:
            return self._post_dominators

        if self._exit_id is None or not self._nodes:
            self._post_dominators = {}
            self._post_dominators_computed = True
            return self._post_dominators

        all_nodes = set(self._nodes.keys())

        # Initialize: exit post-dominates only itself, others have all nodes
        self._post_dominators = {n: set(all_nodes) for n in all_nodes}
        self._post_dominators[self._exit_id] = {self._exit_id}

        # Iterative refinement on reverse CFG (use successors instead of predecessors)
        changed = True
        iterations = 0
        max_iterations = len(all_nodes) * 2

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for node_id in all_nodes:
                if node_id == self._exit_id:
                    continue

                node = self._nodes[node_id]
                if not node.successors:
                    # No path to exit (revert, infinite loop, etc.)
                    continue

                # New post-dominators = {self} ∪ (∩ pdom[succ] for succ in successors)
                succ_pdoms = [self._post_dominators.get(s, all_nodes) for s in node.successors]
                if succ_pdoms:
                    new_pdom = {node_id} | set.intersection(*succ_pdoms)
                else:
                    new_pdom = {node_id}

                if new_pdom != self._post_dominators[node_id]:
                    self._post_dominators[node_id] = new_pdom
                    changed = True

        self._post_dominators_computed = True
        self._compute_immediate_post_dominators()
        return self._post_dominators

    def _compute_immediate_post_dominators(self) -> None:
        """Compute immediate post-dominators from post-dominator sets."""
        if not self._post_dominators:
            return

        for node_id, pdoms in self._post_dominators.items():
            if node_id == self._exit_id:
                self._ipdom[node_id] = None
                continue

            strict_pdoms = pdoms - {node_id}
            if not strict_pdoms:
                self._ipdom[node_id] = None
                continue

            ipdom = None
            for candidate in strict_pdoms:
                candidate_pdoms = self._post_dominators.get(candidate, set()) - {candidate}
                if strict_pdoms - {candidate} <= candidate_pdoms:
                    ipdom = candidate
                    break

            self._ipdom[node_id] = ipdom

    # =========================================================================
    # Dominance Queries
    # =========================================================================

    def dominates(self, a: int, b: int) -> bool:
        """Check if node a dominates node b.

        Args:
            a: Potential dominator node ID
            b: Node to check

        Returns:
            True if a dominates b (a is on all paths from entry to b)
        """
        if not self._dominators_computed:
            self.compute_dominators()

        if b not in self._dominators:
            return False

        return a in self._dominators[b]

    def post_dominates(self, a: int, b: int) -> bool:
        """Check if node a post-dominates node b.

        Args:
            a: Potential post-dominator node ID
            b: Node to check

        Returns:
            True if a post-dominates b (a is on all paths from b to exit)
        """
        if not self._post_dominators_computed:
            self.compute_post_dominators()

        if b not in self._post_dominators:
            return False

        return a in self._post_dominators[b]

    def immediate_dominator(self, node_id: int) -> Optional[int]:
        """Get immediate dominator of a node.

        Args:
            node_id: Node to query

        Returns:
            ID of immediate dominator, or None if entry node
        """
        if not self._dominators_computed:
            self.compute_dominators()

        return self._idom.get(node_id)

    def immediate_post_dominator(self, node_id: int) -> Optional[int]:
        """Get immediate post-dominator of a node.

        Args:
            node_id: Node to query

        Returns:
            ID of immediate post-dominator, or None if exit node
        """
        if not self._post_dominators_computed:
            self.compute_post_dominators()

        return self._ipdom.get(node_id)

    def get_dominators(self, node_id: int) -> Set[int]:
        """Get all dominators of a node.

        Args:
            node_id: Node to query

        Returns:
            Set of dominator node IDs
        """
        if not self._dominators_computed:
            self.compute_dominators()

        return self._dominators.get(node_id, set())

    def get_post_dominators(self, node_id: int) -> Set[int]:
        """Get all post-dominators of a node.

        Args:
            node_id: Node to query

        Returns:
            Set of post-dominator node IDs
        """
        if not self._post_dominators_computed:
            self.compute_post_dominators()

        return self._post_dominators.get(node_id, set())

    # =========================================================================
    # Path-Qualified Ordering
    # =========================================================================

    def compute_ordering(self, a: int, b: int) -> PathQualifiedOrdering:
        """Compute path-qualified ordering relationship between two nodes.

        Args:
            a: First node ID
            b: Second node ID

        Returns:
            PathQualifiedOrdering with relation, confidence, and reason
        """
        # Ensure dominance is computed
        if not self._dominators_computed:
            self.compute_dominators()
        if not self._post_dominators_computed:
            self.compute_post_dominators()

        # Check for missing nodes
        if a not in self._nodes or b not in self._nodes:
            return PathQualifiedOrdering(
                relation=OrderingRelation.UNKNOWN,
                confidence=0.0,
                reason="Node not found in CFG",
            )

        # Check for unreachable nodes
        if self._has_unreachable:
            if a not in self._dominators or b not in self._dominators:
                return PathQualifiedOrdering(
                    relation=OrderingRelation.UNKNOWN,
                    confidence=0.5,
                    reason="CFG has unreachable nodes",
                )

        # ALWAYS_BEFORE: a dominates b
        if self.dominates(a, b):
            return PathQualifiedOrdering(
                relation=OrderingRelation.ALWAYS_BEFORE,
                confidence=1.0,
            )

        # Check if a can reach b on any path (SOMETIMES_BEFORE)
        if self._can_reach(a, b):
            return PathQualifiedOrdering(
                relation=OrderingRelation.SOMETIMES_BEFORE,
                confidence=0.9,
                reason="Reachable but not dominating",
            )

        # Check if b dominates a (a is NEVER_BEFORE b in this case)
        if self.dominates(b, a):
            return PathQualifiedOrdering(
                relation=OrderingRelation.NEVER_BEFORE,
                confidence=1.0,
            )

        # Neither dominates the other, not reachable
        if self._can_reach(b, a):
            return PathQualifiedOrdering(
                relation=OrderingRelation.NEVER_BEFORE,
                confidence=0.9,
                reason="Reverse reachable only",
            )

        # Parallel branches (neither reachable from the other)
        return PathQualifiedOrdering(
            relation=OrderingRelation.NEVER_BEFORE,
            confidence=0.8,
            reason="Parallel branches in CFG",
        )

    def _can_reach(self, start: int, end: int, max_depth: int = 100) -> bool:
        """Check if end is reachable from start via CFG successors.

        Args:
            start: Starting node ID
            end: Target node ID
            max_depth: Maximum search depth to prevent infinite loops

        Returns:
            True if end is reachable from start
        """
        if start == end:
            return True

        visited: Set[int] = set()
        queue = [start]
        depth = 0

        while queue and depth < max_depth:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current == end:
                return True

            node = self._nodes.get(current)
            if node:
                for succ in node.successors:
                    if succ not in visited:
                        queue.append(succ)

            depth += 1

        return False


# =============================================================================
# Slither CFG Adapter
# =============================================================================


def extract_cfg_nodes(fn: Any) -> Tuple[List[CFGNodeInfo], Optional[int], Optional[int]]:
    """Extract CFG nodes from a Slither function.

    Args:
        fn: Slither Function object

    Returns:
        Tuple of (nodes, entry_id, exit_id)
    """
    from alphaswarm_sol.kg.operations import derive_all_operations

    nodes: List[CFGNodeInfo] = []
    entry_id: Optional[int] = None
    exit_id: Optional[int] = None

    slither_nodes = getattr(fn, "nodes", []) or []
    if not slither_nodes:
        return [], None, None

    # Build node info
    node_ids: Dict[Any, int] = {}
    for idx, node in enumerate(slither_nodes):
        node_ids[node] = idx

    for idx, node in enumerate(slither_nodes):
        # Get node type
        node_type_raw = getattr(node, "type", None)
        node_type = str(node_type_raw).split(".")[-1] if node_type_raw else "regular"

        # Get successors
        successors = []
        for son in getattr(node, "sons", []) or []:
            if son in node_ids:
                successors.append(node_ids[son])

        # Get predecessors
        predecessors = []
        for father in getattr(node, "fathers", []) or []:
            if father in node_ids:
                predecessors.append(node_ids[father])

        # Get operations at this node
        operations: List[str] = []
        # Use cfg_order matching to find operations
        # This is a simplified approach - operations module gives per-function ops
        # For node-level, we'd need to filter by cfg_order

        # Detect entry/exit
        if "ENTRY" in node_type.upper():
            entry_id = idx
        if not successors and idx != entry_id:
            exit_id = idx

        # Check for revert
        is_revert = False
        for ir in getattr(node, "irs", []) or []:
            ir_str = str(type(ir).__name__).lower()
            if "revert" in ir_str or "throw" in ir_str:
                is_revert = True
                break

        # Get line number
        line_number = 0
        if hasattr(node, "source_mapping") and node.source_mapping:
            mapping = node.source_mapping
            if hasattr(mapping, "lines") and mapping.lines:
                line_number = mapping.lines[0]

        nodes.append(CFGNodeInfo(
            node_id=idx,
            node_type=node_type,
            successors=successors,
            predecessors=predecessors,
            operations=operations,
            line_number=line_number,
            is_revert=is_revert,
        ))

    # Default entry to first node if not found
    if entry_id is None and nodes:
        entry_id = 0

    return nodes, entry_id, exit_id


def create_analyzer_for_function(fn: Any) -> Optional[DominanceAnalyzer]:
    """Create a DominanceAnalyzer for a Slither function.

    Args:
        fn: Slither Function object

    Returns:
        DominanceAnalyzer or None if CFG is not available
    """
    nodes, entry_id, exit_id = extract_cfg_nodes(fn)
    if not nodes:
        return None

    return DominanceAnalyzer(nodes, entry_id, exit_id)


# =============================================================================
# Modifier Chain Analysis
# =============================================================================


def compute_modifier_summary(modifier: Any) -> ModifierSummary:
    """Compute dominance summary for a single modifier.

    Args:
        modifier: Slither Modifier object

    Returns:
        ModifierSummary with entry/exit operations and dominance info
    """
    from alphaswarm_sol.kg.operations import derive_all_operations

    name = getattr(modifier, "name", "") or "unknown"

    # Check if modifier body is available
    nodes = getattr(modifier, "nodes", []) or []
    if not nodes:
        return ModifierSummary(
            name=name,
            is_external=True,
        )

    # Get all operations in modifier
    try:
        all_ops = derive_all_operations(modifier)
    except Exception:
        return ModifierSummary(
            name=name,
            is_external=True,
        )

    # Find placeholder position (_;)
    placeholder_order: Optional[int] = None
    for idx, node in enumerate(nodes):
        node_type = str(getattr(node, "type", "")).upper()
        if "PLACEHOLDER" in node_type or "_" in node_type:
            placeholder_order = idx
            break

    # Classify operations as entry (before _) or exit (after _)
    entry_ops: Set[str] = set()
    exit_ops: Set[str] = set()
    has_revert = False

    for op in all_ops:
        op_name = op.operation.name
        if placeholder_order is not None:
            if op.cfg_order < placeholder_order:
                entry_ops.add(op_name)
            else:
                exit_ops.add(op_name)
        else:
            # No placeholder found, treat all as entry
            entry_ops.add(op_name)

        # Check for revert-like operations (guards)
        if op_name == "VALIDATES_INPUT" or op_name == "CHECKS_PERMISSION":
            has_revert = True

    return ModifierSummary(
        name=name,
        entry_ops=frozenset(entry_ops),
        exit_ops=frozenset(exit_ops),
        has_revert=has_revert,
        dominates_body=True,
        is_external=False,
    )


def compute_modifier_chain_dominance(modifiers: List[Any]) -> ModifierChainSummary:
    """Compute composite dominance for an ordered modifier chain.

    For modifiers applied in order [A, B, C]:
    - A's entry dominates B's entry dominates C's entry dominates function body
    - Function body's exit dominates C's exit dominates B's exit dominates A's exit

    Args:
        modifiers: Ordered list of Slither Modifier objects (outermost first)

    Returns:
        ModifierChainSummary with combined effects
    """
    if not modifiers:
        return ModifierChainSummary()

    summaries: List[ModifierSummary] = []
    combined_entry: Set[str] = set()
    combined_exit: Set[str] = set()
    any_external = False
    chain_intact = True

    for modifier in modifiers:
        summary = compute_modifier_summary(modifier)
        summaries.append(summary)

        combined_entry.update(summary.entry_ops)
        combined_exit.update(summary.exit_ops)

        if summary.is_external:
            any_external = True
            chain_intact = False

    return ModifierChainSummary(
        modifiers=summaries,
        combined_entry_ops=frozenset(combined_entry),
        combined_exit_ops=frozenset(combined_exit),
        any_external=any_external,
        dominance_chain_intact=chain_intact,
    )


# =============================================================================
# Internal Call Analysis
# =============================================================================


def compute_internal_call_summary(
    callee_fn: Any,
    summaries_cache: Optional[Dict[str, InternalCallSummary]] = None,
) -> InternalCallSummary:
    """Compute summary for an internal function call.

    Args:
        callee_fn: Slither Function object for the callee
        summaries_cache: Optional cache of precomputed summaries

    Returns:
        InternalCallSummary with callee's effects
    """
    from alphaswarm_sol.kg.operations import derive_all_operations

    name = getattr(callee_fn, "name", "") or "unknown"

    # Check cache
    if summaries_cache and name in summaries_cache:
        return summaries_cache[name]

    # Check if function body is available
    nodes = getattr(callee_fn, "nodes", []) or []
    if not nodes:
        return InternalCallSummary(
            function_name=name,
            summary_available=False,
        )

    # Get all operations
    try:
        all_ops = derive_all_operations(callee_fn)
    except Exception:
        return InternalCallSummary(
            function_name=name,
            summary_available=False,
        )

    # Find entry and exit operations
    entry_ops: Set[str] = set()
    exit_ops: Set[str] = set()
    has_external = False

    sorted_ops = sorted(all_ops, key=lambda x: x.cfg_order)
    if sorted_ops:
        # First operation is entry
        entry_ops.add(sorted_ops[0].operation.name)
        # Last operation is exit
        exit_ops.add(sorted_ops[-1].operation.name)

    # Check for external calls
    for op in all_ops:
        if op.operation.name in ("CALLS_EXTERNAL", "CALLS_UNTRUSTED", "TRANSFERS_VALUE_OUT"):
            has_external = True
            break

    result = InternalCallSummary(
        function_name=name,
        entry_ops=frozenset(entry_ops),
        exit_ops=frozenset(exit_ops),
        has_external_call=has_external,
        summary_available=True,
    )

    # Cache result
    if summaries_cache is not None:
        summaries_cache[name] = result

    return result


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    # Enums
    "OrderingRelation",
    "GuardDominance",
    # Result types
    "PathQualifiedOrdering",
    "ModifierSummary",
    "ModifierChainSummary",
    "InternalCallSummary",
    "CFGNodeInfo",
    # Main analyzer
    "DominanceAnalyzer",
    # Slither adapter
    "extract_cfg_nodes",
    "create_analyzer_for_function",
    # Modifier analysis
    "compute_modifier_summary",
    "compute_modifier_chain_dominance",
    # Internal call analysis
    "compute_internal_call_summary",
]
