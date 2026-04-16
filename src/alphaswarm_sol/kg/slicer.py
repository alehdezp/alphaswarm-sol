"""Graph Slicer for category-aware property filtering.

Task 9.B: Implement GraphSlicer for LLM context optimization.
Phase 5.10-04: Pattern-scoped slicing v2 with edge-closure and witness extraction.

This module provides property-level slicing of knowledge graphs based on
vulnerability category. While SubgraphExtractor selects WHICH nodes to include,
GraphSlicer filters WHICH properties each node should have.

Key Concepts:
- Category-aware slicing: Each vulnerability category has relevant properties
- Property filtering: Remove irrelevant properties to reduce token usage
- Statistics tracking: Monitor reduction achieved by slicing
- Integration with SubGraph: Works on SubGraph or creates SlicedGraph

Pattern-Scoped Slicing v2 (Phase 5.10-04):
- Edge-closure slicing seeded by required ops and witness evidence
- Counter/anti-signal inclusion for guards and mitigations
- Deterministic pruning with typed omission reporting
- Witness + negative witness extraction with evidence IDs

Expected Impact:
- Full graph: ~2000 tokens per function (200+ emitted properties)
- Sliced graph: ~500 tokens per function (8-12 properties)
- Reduction: ~75%
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union

from alphaswarm_sol.kg.property_sets import (
    CORE_PROPERTIES,
    VulnerabilityCategory,
    get_category_from_pattern_id,
    get_property_set,
    get_relevant_properties,
)
from alphaswarm_sol.kg.subgraph import (
    CutSetReason,
    OmissionLedger,
    SubGraph,
    SubGraphEdge,
    SubGraphNode,
)


# =============================================================================
# Pattern-Scoped Slicing v2 (Phase 5.10-04)
# =============================================================================


class OmissionReason(str, Enum):
    """Reason for omission in pattern-scoped slicing."""

    EDGE_CLOSURE_EXCLUDED = "edge_closure_excluded"
    REQUIRED_OP_MISSING = "required_op_missing"
    WITNESS_MISSING = "witness_missing"
    BUDGET_EXCEEDED = "budget_exceeded"
    DEPTH_LIMIT = "depth_limit"
    ANTI_SIGNAL_EXCLUDED = "anti_signal_excluded"
    MULTI_HOP_EXPANSION = "multi_hop_expansion"
    DILATION_LIMIT = "dilation_limit"


# =============================================================================
# Phase 5.10-05: Coverage Scoring and Expansion Rules
# =============================================================================


class EvidenceWeight(str, Enum):
    """Weight categories for evidence in coverage scoring."""

    REQUIRED = "required"  # Must have for pattern to match
    STRONG = "strong"  # Important but not strictly required
    WEAK = "weak"  # Nice to have, minor contribution


@dataclass
class EvidenceItem:
    """An evidence item with weight for coverage scoring.

    Evidence items track what information is needed for pattern evaluation
    and how important each item is to the overall coverage score.
    """

    operation: str
    weight: EvidenceWeight
    node_id: str = ""
    found: bool = False

    def weight_value(self) -> float:
        """Get numeric weight value for scoring."""
        weights = {
            EvidenceWeight.REQUIRED: 1.0,
            EvidenceWeight.STRONG: 0.6,
            EvidenceWeight.WEAK: 0.3,
        }
        return weights.get(self.weight, 0.3)


@dataclass
class CoverageScore:
    """Coverage score for pattern evidence evaluation.

    The coverage score measures how much of the required evidence
    is present in the current slice. Used to decide if expansion
    is needed.

    Formula:
        coverage = sum(found_item.weight) / sum(all_item.weight)

    Attributes:
        score: Coverage ratio (0.0 to 1.0)
        required_missing: Count of missing required evidence
        strong_missing: Count of missing strong evidence
        weak_missing: Count of missing weak evidence
        threshold_met: True if coverage >= threshold
        evidence_items: List of all evidence items with found status
    """

    score: float = 0.0
    required_missing: int = 0
    strong_missing: int = 0
    weak_missing: int = 0
    threshold_met: bool = False
    evidence_items: List["EvidenceItem"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "score": round(self.score, 4),
            "required_missing": self.required_missing,
            "strong_missing": self.strong_missing,
            "weak_missing": self.weak_missing,
            "threshold_met": self.threshold_met,
            "evidence_items": [
                {
                    "operation": e.operation,
                    "weight": e.weight.value,
                    "node_id": e.node_id,
                    "found": e.found,
                }
                for e in self.evidence_items
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoverageScore":
        """Deserialize from dictionary."""
        items = []
        for e in data.get("evidence_items", []):
            weight_str = e.get("weight", "weak")
            try:
                weight = EvidenceWeight(weight_str)
            except ValueError:
                weight = EvidenceWeight.WEAK
            items.append(EvidenceItem(
                operation=str(e.get("operation", "")),
                weight=weight,
                node_id=str(e.get("node_id", "")),
                found=bool(e.get("found", False)),
            ))

        return cls(
            score=float(data.get("score", 0.0)),
            required_missing=int(data.get("required_missing", 0)),
            strong_missing=int(data.get("strong_missing", 0)),
            weak_missing=int(data.get("weak_missing", 0)),
            threshold_met=bool(data.get("threshold_met", False)),
            evidence_items=items,
        )


@dataclass
class ExpansionConfig:
    """Configuration for semantic dilation / slice expansion.

    Controls how far and under what conditions slices can expand
    to gather more evidence.

    Attributes:
        coverage_threshold: Minimum coverage score to avoid expansion (0.0-1.0)
        max_expansion_radius: Maximum hops to expand beyond initial slice
        budget_limit: Maximum nodes allowed after expansion
        multi_hop_trigger: Expand when required ops are separated by call chains
        dilation_steps: List of radius increases to try [1, 2, 3]
        stop_on_required_found: Stop expansion when all required ops found
    """

    coverage_threshold: float = 0.8
    max_expansion_radius: int = 4
    budget_limit: int = 100
    multi_hop_trigger: bool = True
    dilation_steps: List[int] = field(default_factory=lambda: [1, 2, 3])
    stop_on_required_found: bool = True

    @classmethod
    def default(cls) -> "ExpansionConfig":
        """Get default expansion configuration."""
        return cls()

    @classmethod
    def conservative(cls) -> "ExpansionConfig":
        """Get conservative expansion configuration (minimal expansion)."""
        return cls(
            coverage_threshold=0.9,
            max_expansion_radius=2,
            budget_limit=50,
            dilation_steps=[1],
        )

    @classmethod
    def aggressive(cls) -> "ExpansionConfig":
        """Get aggressive expansion configuration (expand more)."""
        return cls(
            coverage_threshold=0.6,
            max_expansion_radius=6,
            budget_limit=200,
            dilation_steps=[1, 2, 3, 4],
        )


@dataclass
class ExpansionResult:
    """Result of a slice expansion operation.

    Tracks what was expanded, why, and whether coverage improved.
    """

    expanded: bool = False
    previous_coverage: float = 0.0
    new_coverage: float = 0.0
    expansion_radius: int = 0
    nodes_added: int = 0
    edges_added: int = 0
    multi_hop_triggered: bool = False
    budget_exceeded: bool = False
    reason: str = ""
    typed_omissions: List["TypedOmissionEntry"] = field(default_factory=list)

    def coverage_improved(self) -> bool:
        """Check if coverage improved after expansion."""
        return self.new_coverage > self.previous_coverage

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "expanded": self.expanded,
            "previous_coverage": round(self.previous_coverage, 4),
            "new_coverage": round(self.new_coverage, 4),
            "expansion_radius": self.expansion_radius,
            "nodes_added": self.nodes_added,
            "edges_added": self.edges_added,
            "multi_hop_triggered": self.multi_hop_triggered,
            "budget_exceeded": self.budget_exceeded,
            "reason": self.reason,
            "typed_omissions": [o.to_dict() for o in self.typed_omissions],
        }


@dataclass(frozen=True)
class TypedOmissionEntry:
    """An omission entry with edge type for debugging.

    Per v2 contract, omission entries include both edge_id and edge_type
    to enable debugging why specific context was excluded.
    """

    edge_id: str
    edge_type: str
    reason: OmissionReason
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "edge_id": self.edge_id,
            "edge_type": self.edge_type,
            "reason": self.reason.value,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TypedOmissionEntry":
        """Deserialize from dictionary."""
        reason_str = data.get("reason", "edge_closure_excluded")
        try:
            reason = OmissionReason(reason_str)
        except ValueError:
            reason = OmissionReason.EDGE_CLOSURE_EXCLUDED
        return cls(
            edge_id=str(data.get("edge_id", "")),
            edge_type=str(data.get("edge_type", "")),
            reason=reason,
            details=str(data.get("details", "")),
        )


@dataclass
class WitnessEvidence:
    """Evidence for witness extraction with evidence IDs.

    Witnesses are the minimal proof subgraph required for pattern matches.
    """

    evidence_ids: List[str] = field(default_factory=list)
    node_ids: List[str] = field(default_factory=list)
    edge_ids: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "evidence_ids": self.evidence_ids,
            "node_ids": self.node_ids,
            "edge_ids": self.edge_ids,
            "operations": self.operations,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WitnessEvidence":
        """Deserialize from dictionary."""
        return cls(
            evidence_ids=list(data.get("evidence_ids", [])),
            node_ids=list(data.get("node_ids", [])),
            edge_ids=list(data.get("edge_ids", [])),
            operations=list(data.get("operations", [])),
        )

    def is_empty(self) -> bool:
        """Check if witness has no evidence."""
        return not (self.evidence_ids or self.node_ids or self.edge_ids)


@dataclass
class NegativeWitness:
    """Evidence that must NOT exist for pattern to match.

    Negative witnesses are guards, mitigations, or other anti-signals
    that would invalidate a vulnerability pattern.
    """

    guard_types: List[str] = field(default_factory=list)
    excluded_operations: List[str] = field(default_factory=list)
    guard_evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "guard_types": self.guard_types,
            "excluded_operations": self.excluded_operations,
            "guard_evidence_ids": self.guard_evidence_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegativeWitness":
        """Deserialize from dictionary."""
        return cls(
            guard_types=list(data.get("guard_types", [])),
            excluded_operations=list(data.get("excluded_operations", [])),
            guard_evidence_ids=list(data.get("guard_evidence_ids", [])),
        )


@dataclass
class PatternSliceFocus:
    """Focus inputs for pattern-scoped slicing from PCP v2.

    These inputs seed the edge-closure algorithm and define what
    evidence is required for the pattern match.
    """

    required_ops: List[str] = field(default_factory=list)
    witness_evidence_ids: List[str] = field(default_factory=list)
    anti_signal_guard_types: List[str] = field(default_factory=list)
    ordering_variants: List[List[str]] = field(default_factory=list)
    forbidden_ops: List[str] = field(default_factory=list)
    max_edge_hops: int = 2

    @classmethod
    def from_pcp(cls, pcp_data: Dict[str, Any]) -> "PatternSliceFocus":
        """Create from PCP v2 data.

        Args:
            pcp_data: PCP v2 dictionary or PatternContextPackV2 fields

        Returns:
            PatternSliceFocus with extracted inputs
        """
        # Handle both raw dict and nested structure
        op_sigs = pcp_data.get("op_signatures", {})
        witness = pcp_data.get("witness", {})
        anti_signals = pcp_data.get("anti_signals", [])

        required_ops = op_sigs.get("required_ops", []) if op_sigs else []
        forbidden_ops = op_sigs.get("forbidden_ops", []) if op_sigs else []

        # Extract ordering variants
        ordering_variants = []
        for variant in op_sigs.get("ordering_variants", []) if op_sigs else []:
            seq = variant.get("sequence", [])
            if seq:
                ordering_variants.append(seq)

        # Extract witness evidence IDs
        witness_ids = witness.get("minimal_required", []) if witness else []

        # Extract anti-signal guard types
        guard_types = [a.get("guard_type", "") for a in anti_signals if a.get("guard_type")]

        return cls(
            required_ops=required_ops,
            witness_evidence_ids=witness_ids,
            anti_signal_guard_types=guard_types,
            ordering_variants=ordering_variants,
            forbidden_ops=forbidden_ops,
        )


@dataclass
class PatternSliceResult:
    """Result of pattern-scoped slicing with witnesses and omissions.

    Contains the sliced graph, extracted witnesses, typed omission list,
    and coverage scoring for expansion decisions (Phase 5.10-05).
    """

    graph: "SlicedGraph"
    witness: WitnessEvidence
    negative_witness: NegativeWitness
    typed_omissions: List[TypedOmissionEntry] = field(default_factory=list)
    missing_required_ops: List[str] = field(default_factory=list)
    missing_witness_ids: List[str] = field(default_factory=list)
    has_forbidden_ops: bool = False
    is_complete: bool = True
    coverage: Optional[CoverageScore] = None
    expansion_result: Optional[ExpansionResult] = None

    def needs_expansion(self, threshold: float = 0.8) -> bool:
        """Check if slice needs expansion based on coverage score.

        Args:
            threshold: Minimum coverage to avoid expansion

        Returns:
            True if coverage is below threshold and expansion may help
        """
        if self.coverage is None:
            # No coverage computed - check basic completeness
            return not self.is_complete

        return (
            self.coverage.score < threshold
            and self.coverage.required_missing > 0
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "graph": self.graph.to_dict(),
            "witness": self.witness.to_dict(),
            "negative_witness": self.negative_witness.to_dict(),
            "typed_omissions": [o.to_dict() for o in self.typed_omissions],
            "missing_required_ops": self.missing_required_ops,
            "missing_witness_ids": self.missing_witness_ids,
            "has_forbidden_ops": self.has_forbidden_ops,
            "is_complete": self.is_complete,
        }
        if self.coverage is not None:
            result["coverage"] = self.coverage.to_dict()
        if self.expansion_result is not None:
            result["expansion_result"] = self.expansion_result.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternSliceResult":
        """Deserialize from dictionary."""
        coverage = None
        if "coverage" in data:
            coverage = CoverageScore.from_dict(data["coverage"])

        return cls(
            graph=SlicedGraph.from_dict(data.get("graph", {})),
            witness=WitnessEvidence.from_dict(data.get("witness", {})),
            negative_witness=NegativeWitness.from_dict(data.get("negative_witness", {})),
            typed_omissions=[
                TypedOmissionEntry.from_dict(o)
                for o in data.get("typed_omissions", [])
            ],
            missing_required_ops=data.get("missing_required_ops", []),
            missing_witness_ids=data.get("missing_witness_ids", []),
            has_forbidden_ops=data.get("has_forbidden_ops", False),
            is_complete=data.get("is_complete", True),
            coverage=coverage,
        )


class CoverageScorer:
    """Compute coverage scores for pattern evidence evaluation.

    This class evaluates how much of the required evidence is present
    in a slice and determines if expansion is needed.

    Phase 5.10-05: Coverage scoring for semantic dilation.
    """

    def __init__(
        self,
        required_ops: List[str],
        strong_ops: Optional[List[str]] = None,
        weak_ops: Optional[List[str]] = None,
    ):
        """Initialize coverage scorer.

        Args:
            required_ops: Operations that MUST be present
            strong_ops: Important operations (default: empty)
            weak_ops: Nice-to-have operations (default: empty)
        """
        self.required_ops = required_ops
        self.strong_ops = strong_ops or []
        self.weak_ops = weak_ops or []

    def score(
        self,
        graph: Union[SubGraph, "SlicedGraph"],
        threshold: float = 0.8,
    ) -> CoverageScore:
        """Compute coverage score for a graph.

        Args:
            graph: Graph to evaluate
            threshold: Threshold for threshold_met flag

        Returns:
            CoverageScore with detailed evidence breakdown
        """
        # Collect all operations in graph
        found_ops: Set[str] = set()
        node_op_map: Dict[str, str] = {}  # op -> node_id

        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            props = getattr(node, "properties", {})
            node_ops = props.get("semantic_ops", []) or []
            for op in node_ops:
                if op not in found_ops:
                    found_ops.add(op)
                    node_id = getattr(node, "id", str(node))
                    node_op_map[op] = node_id

        # Build evidence items
        evidence_items: List[EvidenceItem] = []

        # Required ops
        required_missing = 0
        for op in self.required_ops:
            found = op in found_ops
            if not found:
                required_missing += 1
            evidence_items.append(EvidenceItem(
                operation=op,
                weight=EvidenceWeight.REQUIRED,
                node_id=node_op_map.get(op, ""),
                found=found,
            ))

        # Strong ops
        strong_missing = 0
        for op in self.strong_ops:
            found = op in found_ops
            if not found:
                strong_missing += 1
            evidence_items.append(EvidenceItem(
                operation=op,
                weight=EvidenceWeight.STRONG,
                node_id=node_op_map.get(op, ""),
                found=found,
            ))

        # Weak ops
        weak_missing = 0
        for op in self.weak_ops:
            found = op in found_ops
            if not found:
                weak_missing += 1
            evidence_items.append(EvidenceItem(
                operation=op,
                weight=EvidenceWeight.WEAK,
                node_id=node_op_map.get(op, ""),
                found=found,
            ))

        # Compute score
        total_weight = sum(item.weight_value() for item in evidence_items)
        found_weight = sum(
            item.weight_value() for item in evidence_items if item.found
        )

        score = found_weight / total_weight if total_weight > 0 else 1.0

        return CoverageScore(
            score=score,
            required_missing=required_missing,
            strong_missing=strong_missing,
            weak_missing=weak_missing,
            threshold_met=score >= threshold,
            evidence_items=evidence_items,
        )


class SemanticDilator:
    """Perform semantic dilation to expand slices until coverage is sufficient.

    Semantic dilation progressively expands the slice radius until:
    1. Coverage threshold is met
    2. Maximum expansion radius is reached
    3. Budget limit is exceeded

    This implements the "unknown -> expand -> re-evaluate" pattern.

    Phase 5.10-05: Semantic dilation for controlled context expansion.
    """

    def __init__(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        config: Optional[ExpansionConfig] = None,
    ):
        """Initialize dilator.

        Args:
            graph: Full graph to expand from
            config: Expansion configuration
        """
        self.graph = graph
        self.config = config or ExpansionConfig.default()
        self._adjacency: Dict[str, Set[str]] = {}
        self._edge_index: Dict[Tuple[str, str], List[Any]] = {}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        """Build adjacency and edge index from graph."""
        edges = getattr(self.graph, "edges", {})
        if isinstance(edges, dict):
            edges = edges.values()

        for edge in edges:
            source = getattr(edge, "source", "")
            target = getattr(edge, "target", "")
            if source and target:
                self._adjacency.setdefault(source, set()).add(target)
                self._adjacency.setdefault(target, set()).add(source)
                key = (source, target)
                self._edge_index.setdefault(key, []).append(edge)
                rev_key = (target, source)
                self._edge_index.setdefault(rev_key, []).append(edge)

    def dilate(
        self,
        focal_nodes: List[str],
        required_ops: List[str],
        initial_radius: int = 2,
        scorer: Optional[CoverageScorer] = None,
    ) -> Tuple[Set[str], Set[str], ExpansionResult]:
        """Perform semantic dilation to expand slice.

        The dilation process:
        1. Start with initial slice at initial_radius
        2. Compute coverage score
        3. If coverage < threshold, expand by one dilation step
        4. Repeat until threshold met, max radius reached, or budget exceeded

        Args:
            focal_nodes: Starting node IDs
            required_ops: Required operations to find
            initial_radius: Starting expansion radius
            scorer: Coverage scorer (created from required_ops if not provided)

        Returns:
            Tuple of (included_nodes, included_edges, ExpansionResult)
        """
        if scorer is None:
            scorer = CoverageScorer(required_ops=required_ops)

        # Initial expansion
        current_radius = initial_radius
        included_nodes, included_edges = self._expand_to_radius(
            focal_nodes, required_ops, current_radius
        )

        # Build temporary subgraph for scoring
        temp_graph = self._build_temp_graph(included_nodes)
        coverage = scorer.score(temp_graph, self.config.coverage_threshold)
        initial_coverage = coverage.score

        result = ExpansionResult(
            expanded=False,
            previous_coverage=initial_coverage,
            new_coverage=initial_coverage,
            expansion_radius=current_radius,
            nodes_added=0,
            edges_added=0,
        )

        # Check if multi-hop trigger applies
        multi_hop_needed = self._check_multi_hop_trigger(
            included_nodes, required_ops
        )

        if coverage.threshold_met and not multi_hop_needed:
            # No expansion needed
            result.reason = "Coverage threshold met"
            return included_nodes, included_edges, result

        # Semantic dilation loop
        for step in self.config.dilation_steps:
            new_radius = current_radius + step

            if new_radius > self.config.max_expansion_radius:
                result.reason = f"Max expansion radius ({self.config.max_expansion_radius}) reached"
                result.typed_omissions.append(TypedOmissionEntry(
                    edge_id="",
                    edge_type="",
                    reason=OmissionReason.DILATION_LIMIT,
                    details=f"Stopped at radius {current_radius}, max is {self.config.max_expansion_radius}",
                ))
                break

            # Expand
            new_nodes, new_edges = self._expand_to_radius(
                focal_nodes, required_ops, new_radius
            )

            # Check budget
            if len(new_nodes) > self.config.budget_limit:
                result.budget_exceeded = True
                result.reason = f"Budget limit ({self.config.budget_limit}) exceeded"
                result.typed_omissions.append(TypedOmissionEntry(
                    edge_id="",
                    edge_type="",
                    reason=OmissionReason.BUDGET_EXCEEDED,
                    details=f"Expansion to radius {new_radius} would include {len(new_nodes)} nodes",
                ))
                break

            # Compute new coverage
            temp_graph = self._build_temp_graph(new_nodes)
            new_coverage = scorer.score(temp_graph, self.config.coverage_threshold)

            # Update tracking
            nodes_added = len(new_nodes) - len(included_nodes)
            edges_added = len(new_edges) - len(included_edges)

            included_nodes = new_nodes
            included_edges = new_edges
            current_radius = new_radius

            result.expanded = True
            result.new_coverage = new_coverage.score
            result.expansion_radius = new_radius
            result.nodes_added += nodes_added
            result.edges_added += edges_added

            # Check if we should stop
            if new_coverage.threshold_met:
                result.reason = "Coverage threshold met after dilation"
                break

            # Check for required ops found (optional early stop)
            if self.config.stop_on_required_found and new_coverage.required_missing == 0:
                result.reason = "All required ops found"
                break

            # Check multi-hop again
            if multi_hop_needed:
                multi_hop_resolved = not self._check_multi_hop_trigger(
                    included_nodes, required_ops
                )
                if multi_hop_resolved:
                    result.multi_hop_triggered = True
                    result.reason = "Multi-hop separation resolved"
                    break

        return included_nodes, included_edges, result

    def _expand_to_radius(
        self,
        focal_nodes: List[str],
        required_ops: List[str],
        radius: int,
    ) -> Tuple[Set[str], Set[str]]:
        """Expand from focal nodes to given radius.

        Also includes nodes with required operations regardless of distance.

        Args:
            focal_nodes: Starting node IDs
            required_ops: Required operations (nodes with these are included)
            radius: BFS radius

        Returns:
            Tuple of (included_node_ids, included_edge_ids)
        """
        included_nodes: Set[str] = set(focal_nodes)
        included_edges: Set[str] = set()

        # BFS expansion
        visited: Set[str] = set(focal_nodes)
        queue: deque = deque()

        for node_id in focal_nodes:
            queue.append((node_id, 0))

        while queue:
            current_id, depth = queue.popleft()

            if depth >= radius:
                continue

            neighbors = self._adjacency.get(current_id, set())
            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                included_nodes.add(neighbor_id)

                # Add edges
                for edge in self._edge_index.get((current_id, neighbor_id), []):
                    edge_id = getattr(edge, "id", f"{current_id}->{neighbor_id}")
                    included_edges.add(edge_id)

                queue.append((neighbor_id, depth + 1))

        # Also include nodes with required ops anywhere in graph
        graph_nodes = getattr(self.graph, "nodes", {})
        if isinstance(graph_nodes, dict):
            graph_nodes = graph_nodes.values()

        for node in graph_nodes:
            props = getattr(node, "properties", {})
            node_ops = props.get("semantic_ops", []) or []
            if any(op in node_ops for op in required_ops):
                node_id = getattr(node, "id", str(node))
                included_nodes.add(node_id)

        return included_nodes, included_edges

    def _build_temp_graph(self, node_ids: Set[str]) -> SubGraph:
        """Build temporary SubGraph for coverage scoring."""
        temp = SubGraph(focal_node_ids=list(node_ids)[:5])

        graph_nodes = getattr(self.graph, "nodes", {})
        if isinstance(graph_nodes, dict):
            for node_id in node_ids:
                if node_id in graph_nodes:
                    node = graph_nodes[node_id]
                    temp.add_node(SubGraphNode(
                        id=node_id,
                        type=getattr(node, "type", ""),
                        label=getattr(node, "label", ""),
                        properties=dict(getattr(node, "properties", {})),
                    ))

        return temp

    def _check_multi_hop_trigger(
        self,
        included_nodes: Set[str],
        required_ops: List[str],
    ) -> bool:
        """Check if required ops are separated by call chains.

        Multi-hop trigger activates when required operations exist in the
        full graph but are not reachable within the current slice.

        Args:
            included_nodes: Currently included node IDs
            required_ops: Required operations

        Returns:
            True if multi-hop expansion is needed
        """
        if not self.config.multi_hop_trigger:
            return False

        # Find which required ops are in included vs full graph
        ops_in_included: Set[str] = set()
        graph_nodes = getattr(self.graph, "nodes", {})

        if isinstance(graph_nodes, dict):
            for node_id in included_nodes:
                if node_id in graph_nodes:
                    node = graph_nodes[node_id]
                    props = getattr(node, "properties", {})
                    ops_in_included.update(props.get("semantic_ops", []) or [])

        # Find ops in full graph
        ops_in_full: Set[str] = set()
        all_nodes = graph_nodes.values() if isinstance(graph_nodes, dict) else graph_nodes
        for node in all_nodes:
            props = getattr(node, "properties", {})
            ops_in_full.update(props.get("semantic_ops", []) or [])

        # Check if any required ops exist in full graph but not included
        for op in required_ops:
            if op in ops_in_full and op not in ops_in_included:
                return True

        return False


@dataclass
class SlicingStats:
    """Statistics about property slicing operation."""

    original_property_count: int = 0
    sliced_property_count: int = 0
    nodes_processed: int = 0
    properties_removed: int = 0
    category: str = ""
    reduction_percent: float = 0.0

    def calculate_reduction(self) -> None:
        """Calculate reduction percentage."""
        if self.original_property_count > 0:
            self.reduction_percent = (
                (self.original_property_count - self.sliced_property_count)
                / self.original_property_count
                * 100
            )
        self.properties_removed = (
            self.original_property_count - self.sliced_property_count
        )


@dataclass
class SlicedGraph:
    """A graph sliced to category-relevant properties.

    Extends SubGraph concept with slicing metadata and statistics.
    Per v2 contract, includes omission ledger from source SubGraph.
    """

    nodes: Dict[str, SubGraphNode] = field(default_factory=dict)
    edges: Dict[str, SubGraphEdge] = field(default_factory=dict)
    focal_node_ids: List[str] = field(default_factory=list)
    category: str = ""
    stats: SlicingStats = field(default_factory=SlicingStats)
    full_graph_available: bool = True  # Agent can request more context
    omissions: OmissionLedger = field(default_factory=OmissionLedger.empty)

    def add_node(self, node: SubGraphNode) -> None:
        """Add a node to the sliced graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: SubGraphEdge) -> None:
        """Add an edge to the sliced graph."""
        if edge.source in self.nodes and edge.target in self.nodes:
            self.edges[edge.id] = edge

    def get_node(self, node_id: str) -> Optional[SubGraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def node_count(self) -> int:
        """Get number of nodes."""
        return len(self.nodes)

    def edge_count(self) -> int:
        """Get number of edges."""
        return len(self.edges)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (v2 contract compliant)."""
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
            "focal_node_ids": self.focal_node_ids,
            "category": self.category,
            "stats": {
                "original_property_count": self.stats.original_property_count,
                "sliced_property_count": self.stats.sliced_property_count,
                "nodes_processed": self.stats.nodes_processed,
                "properties_removed": self.stats.properties_removed,
                "reduction_percent": self.stats.reduction_percent,
            },
            "full_graph_available": self.full_graph_available,
            "omissions": self.omissions.to_dict(),
            "coverage_score": self.omissions.coverage_score,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SlicedGraph":
        """Deserialize from dictionary."""
        # Parse omissions if present
        omissions_data = data.get("omissions", {})
        if omissions_data:
            omissions = OmissionLedger.from_dict(omissions_data)
        else:
            omissions = OmissionLedger.empty()

        graph = SlicedGraph(
            focal_node_ids=data.get("focal_node_ids", []),
            category=data.get("category", ""),
            full_graph_available=data.get("full_graph_available", True),
            omissions=omissions,
        )

        for node_data in data.get("nodes", {}).values():
            graph.add_node(SubGraphNode.from_dict(node_data))

        for edge_data in data.get("edges", {}).values():
            graph.add_edge(SubGraphEdge.from_dict(edge_data))

        stats_data = data.get("stats", {})
        graph.stats = SlicingStats(
            original_property_count=stats_data.get("original_property_count", 0),
            sliced_property_count=stats_data.get("sliced_property_count", 0),
            nodes_processed=stats_data.get("nodes_processed", 0),
            properties_removed=stats_data.get("properties_removed", 0),
            reduction_percent=stats_data.get("reduction_percent", 0.0),
            category=graph.category,
        )

        return graph


class GraphSlicer:
    """Slice graphs to category-relevant properties.

    This class filters properties on graph nodes based on vulnerability
    category, reducing context size for LLM consumption while preserving
    detection-relevant information.

    Usage:
        slicer = GraphSlicer()

        # Slice for a specific category
        sliced = slicer.slice_for_category(subgraph, "reentrancy")

        # Slice based on a finding
        sliced = slicer.slice_for_finding(subgraph, finding)

        # Check statistics
        print(f"Reduced by {sliced.stats.reduction_percent:.1f}%")
    """

    def __init__(
        self,
        include_core: bool = True,
        strict_mode: bool = False,
    ):
        """Initialize GraphSlicer.

        Args:
            include_core: Always include CORE_PROPERTIES
            strict_mode: Only include required properties (exclude optional)
        """
        self.include_core = include_core
        self.strict_mode = strict_mode

    def slice_for_category(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        category: Union[VulnerabilityCategory, str],
    ) -> SlicedGraph:
        """Slice graph to category-relevant properties.

        Args:
            graph: SubGraph or KnowledgeGraph to slice
            category: Vulnerability category (enum or string)

        Returns:
            SlicedGraph with only relevant properties
        """
        # Normalize category
        if isinstance(category, str):
            try:
                category_enum = VulnerabilityCategory(category.lower())
            except ValueError:
                category_enum = VulnerabilityCategory.GENERAL
        else:
            category_enum = category

        # Get relevant properties for this category
        prop_set = get_property_set(category_enum)
        if self.strict_mode:
            relevant = set(prop_set.required)
        else:
            relevant = set(prop_set.all_properties())

        if self.include_core:
            relevant |= set(CORE_PROPERTIES)

        # Create sliced graph
        sliced = SlicedGraph(
            category=category_enum.value,
        )

        # Copy focal node IDs if available
        if hasattr(graph, "focal_node_ids"):
            sliced.focal_node_ids = list(graph.focal_node_ids)

        # Pass through omissions from source graph (v2 contract compliance)
        if hasattr(graph, "omissions") and graph.omissions is not None:
            # Copy the omission ledger from source SubGraph
            sliced.omissions = OmissionLedger(
                coverage_score=graph.omissions.coverage_score,
                cut_set=list(graph.omissions.cut_set),
                excluded_edges=list(graph.omissions.excluded_edges),
                omitted_nodes=list(graph.omissions.omitted_nodes),
                slice_mode=graph.omissions.slice_mode,
            )

        # Track statistics
        stats = SlicingStats(category=category_enum.value)

        # Process nodes
        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            # Handle both SubGraphNode and Node from schema
            if hasattr(node, "properties"):
                original_props = node.properties
            else:
                original_props = {}

            stats.original_property_count += len(original_props)
            stats.nodes_processed += 1

            # Filter properties
            filtered_props = self._filter_properties(original_props, relevant)
            stats.sliced_property_count += len(filtered_props)

            # Create sliced node
            sliced_node = SubGraphNode(
                id=node.id if hasattr(node, "id") else str(node),
                type=node.type if hasattr(node, "type") else "unknown",
                label=node.label if hasattr(node, "label") else "",
                properties=filtered_props,
                relevance_score=getattr(node, "relevance_score", 0.0),
                distance_from_focal=getattr(node, "distance_from_focal", 0),
                is_focal=getattr(node, "is_focal", False),
            )
            sliced.add_node(sliced_node)

        # Copy edges
        edges = graph.edges.values() if hasattr(graph, "edges") else []
        for edge in edges:
            sliced_edge = SubGraphEdge(
                id=edge.id if hasattr(edge, "id") else str(edge),
                type=edge.type if hasattr(edge, "type") else "unknown",
                source=edge.source if hasattr(edge, "source") else "",
                target=edge.target if hasattr(edge, "target") else "",
                properties=getattr(edge, "properties", {}),
            )
            sliced.add_edge(sliced_edge)

        # Calculate statistics
        stats.calculate_reduction()
        sliced.stats = stats

        return sliced

    def slice_for_finding(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        finding: Any,
    ) -> SlicedGraph:
        """Slice graph based on a finding's pattern category.

        Args:
            graph: Graph to slice
            finding: Finding with pattern_id or category information

        Returns:
            SlicedGraph sliced to the finding's category
        """
        # Extract category from finding
        category = self._get_category_from_finding(finding)
        return self.slice_for_category(graph, category)

    def slice_for_pattern(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        pattern_id: str,
    ) -> SlicedGraph:
        """Slice graph based on a pattern ID.

        Args:
            graph: Graph to slice
            pattern_id: Pattern ID like "reentrancy-001" or "vm-basic"

        Returns:
            SlicedGraph sliced to the pattern's inferred category
        """
        category = get_category_from_pattern_id(pattern_id)
        return self.slice_for_category(graph, category)

    def slice_multiple_categories(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        categories: List[Union[VulnerabilityCategory, str]],
    ) -> SlicedGraph:
        """Slice graph for multiple categories (union of properties).

        Useful when analyzing for multiple vulnerability types simultaneously.

        Args:
            graph: Graph to slice
            categories: List of categories to include

        Returns:
            SlicedGraph with properties relevant to any of the categories
        """
        # Collect all relevant properties
        all_relevant: Set[str] = set()

        for category in categories:
            if isinstance(category, str):
                try:
                    category_enum = VulnerabilityCategory(category.lower())
                except ValueError:
                    continue
            else:
                category_enum = category

            prop_set = get_property_set(category_enum)
            if self.strict_mode:
                all_relevant |= set(prop_set.required)
            else:
                all_relevant |= set(prop_set.all_properties())

        if self.include_core:
            all_relevant |= set(CORE_PROPERTIES)

        # Create combined category name
        category_names = []
        for cat in categories:
            if isinstance(cat, VulnerabilityCategory):
                category_names.append(cat.value)
            else:
                category_names.append(str(cat).lower())

        # Create sliced graph
        sliced = SlicedGraph(
            category="+".join(category_names),
        )

        if hasattr(graph, "focal_node_ids"):
            sliced.focal_node_ids = list(graph.focal_node_ids)

        # Pass through omissions from source graph (v2 contract compliance)
        if hasattr(graph, "omissions") and graph.omissions is not None:
            sliced.omissions = OmissionLedger(
                coverage_score=graph.omissions.coverage_score,
                cut_set=list(graph.omissions.cut_set),
                excluded_edges=list(graph.omissions.excluded_edges),
                omitted_nodes=list(graph.omissions.omitted_nodes),
                slice_mode=graph.omissions.slice_mode,
            )

        # Track statistics
        stats = SlicingStats(category=sliced.category)

        # Process nodes
        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            if hasattr(node, "properties"):
                original_props = node.properties
            else:
                original_props = {}

            stats.original_property_count += len(original_props)
            stats.nodes_processed += 1

            filtered_props = self._filter_properties(original_props, all_relevant)
            stats.sliced_property_count += len(filtered_props)

            sliced_node = SubGraphNode(
                id=node.id if hasattr(node, "id") else str(node),
                type=node.type if hasattr(node, "type") else "unknown",
                label=node.label if hasattr(node, "label") else "",
                properties=filtered_props,
                relevance_score=getattr(node, "relevance_score", 0.0),
                distance_from_focal=getattr(node, "distance_from_focal", 0),
                is_focal=getattr(node, "is_focal", False),
            )
            sliced.add_node(sliced_node)

        # Copy edges
        edges = graph.edges.values() if hasattr(graph, "edges") else []
        for edge in edges:
            sliced_edge = SubGraphEdge(
                id=edge.id if hasattr(edge, "id") else str(edge),
                type=edge.type if hasattr(edge, "type") else "unknown",
                source=edge.source if hasattr(edge, "source") else "",
                target=edge.target if hasattr(edge, "target") else "",
                properties=getattr(edge, "properties", {}),
            )
            sliced.add_edge(sliced_edge)

        stats.calculate_reduction()
        sliced.stats = stats

        return sliced

    # =========================================================================
    # Pattern-Scoped Slicing v2 (Phase 5.10-04)
    # =========================================================================

    def slice_for_pattern_focus(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        focus: PatternSliceFocus,
        focal_nodes: List[str],
        category: Optional[Union[VulnerabilityCategory, str]] = None,
    ) -> PatternSliceResult:
        """Pattern-scoped slicing v2 with edge-closure and witness extraction.

        Implements PCP v2 slicing contract:
        1. Edge-closure traversal seeded by required ops
        2. Counter/anti-signal inclusion for guards
        3. Deterministic pruning with typed omissions
        4. Witness + negative witness extraction

        Args:
            graph: Graph to slice
            focus: PatternSliceFocus from PCP v2
            focal_nodes: Starting node IDs
            category: Optional category for property filtering

        Returns:
            PatternSliceResult with witnesses, omissions, and missing signals
        """
        # Build adjacency for edge-closure traversal
        adjacency = self._build_adjacency_from_graph(graph)
        edge_index = self._build_edge_index(graph)

        # Step 1: Find nodes with required operations
        seed_nodes = self._find_nodes_with_ops(
            graph, focus.required_ops, focal_nodes
        )

        # Step 2: Edge-closure traversal
        included_nodes, included_edges, typed_omissions = self._edge_closure_traverse(
            graph,
            seed_nodes,
            adjacency,
            edge_index,
            max_hops=focus.max_edge_hops,
        )

        # Step 3: Add counter/anti-signal nodes (guards)
        guard_nodes, guard_evidence = self._find_guard_nodes(
            graph,
            included_nodes,
            focus.anti_signal_guard_types,
        )
        included_nodes.update(guard_nodes)

        # Step 4: Check for missing required operations
        missing_ops = self._check_missing_ops(
            graph, included_nodes, focus.required_ops
        )

        # Step 5: Check for forbidden operations
        has_forbidden = self._check_forbidden_ops(
            graph, included_nodes, focus.forbidden_ops
        )

        # Step 6: Build sliced graph
        sliced = self._build_sliced_graph(
            graph,
            included_nodes,
            included_edges,
            focal_nodes,
            category,
        )

        # Step 7: Extract witnesses deterministically
        witness = self._extract_witness(
            graph,
            sliced,
            focus.required_ops,
            focus.witness_evidence_ids,
        )

        # Step 8: Extract negative witness
        negative_witness = NegativeWitness(
            guard_types=focus.anti_signal_guard_types,
            excluded_operations=focus.forbidden_ops,
            guard_evidence_ids=guard_evidence,
        )

        # Step 9: Check for missing witness evidence
        missing_witness = self._check_missing_witness(
            graph, focus.witness_evidence_ids
        )

        # Determine completeness
        is_complete = (
            len(missing_ops) == 0
            and len(missing_witness) == 0
            and not has_forbidden
        )

        return PatternSliceResult(
            graph=sliced,
            witness=witness,
            negative_witness=negative_witness,
            typed_omissions=typed_omissions,
            missing_required_ops=missing_ops,
            missing_witness_ids=missing_witness,
            has_forbidden_ops=has_forbidden,
            is_complete=is_complete,
        )

    def _build_adjacency_from_graph(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
    ) -> Dict[str, Set[str]]:
        """Build bidirectional adjacency map from graph edges."""
        adjacency: Dict[str, Set[str]] = {}

        edges = graph.edges.values() if hasattr(graph, "edges") else []
        for edge in edges:
            source = getattr(edge, "source", "")
            target = getattr(edge, "target", "")
            if source and target:
                adjacency.setdefault(source, set()).add(target)
                adjacency.setdefault(target, set()).add(source)

        return adjacency

    def _build_edge_index(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
    ) -> Dict[Tuple[str, str], List[Any]]:
        """Build edge index: (source, target) -> list of edges."""
        edge_index: Dict[Tuple[str, str], List[Any]] = {}

        edges = graph.edges.values() if hasattr(graph, "edges") else []
        for edge in edges:
            source = getattr(edge, "source", "")
            target = getattr(edge, "target", "")
            if source and target:
                key = (source, target)
                edge_index.setdefault(key, []).append(edge)
                # Add reverse for undirected traversal
                rev_key = (target, source)
                edge_index.setdefault(rev_key, []).append(edge)

        return edge_index

    def _find_nodes_with_ops(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        required_ops: List[str],
        focal_nodes: List[str],
    ) -> Set[str]:
        """Find nodes that have any of the required operations."""
        seed_nodes = set(focal_nodes)

        if not required_ops:
            return seed_nodes

        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            props = getattr(node, "properties", {})
            node_ops = props.get("semantic_ops", []) or []
            if any(op in node_ops for op in required_ops):
                node_id = getattr(node, "id", str(node))
                seed_nodes.add(node_id)

        return seed_nodes

    def _edge_closure_traverse(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        seed_nodes: Set[str],
        adjacency: Dict[str, Set[str]],
        edge_index: Dict[Tuple[str, str], List[Any]],
        max_hops: int,
    ) -> Tuple[Set[str], Set[str], List[TypedOmissionEntry]]:
        """Edge-closure traversal with typed omission tracking.

        Args:
            graph: Source graph
            seed_nodes: Starting node IDs
            adjacency: Adjacency map
            edge_index: Edge lookup
            max_hops: Maximum traversal depth

        Returns:
            Tuple of (included_nodes, included_edges, typed_omissions)
        """
        included_nodes: Set[str] = set(seed_nodes)
        included_edges: Set[str] = set()
        typed_omissions: List[TypedOmissionEntry] = []

        # BFS from seeds
        visited: Set[str] = set(seed_nodes)
        queue: deque = deque()

        for node_id in seed_nodes:
            queue.append((node_id, 0))

        while queue:
            current_id, depth = queue.popleft()

            if depth >= max_hops:
                # Track omissions at depth limit
                neighbors = adjacency.get(current_id, set())
                for neighbor_id in neighbors:
                    if neighbor_id not in visited:
                        # Get edge(s) that would be excluded
                        edges_to_neighbor = edge_index.get((current_id, neighbor_id), [])
                        for edge in edges_to_neighbor:
                            edge_id = getattr(edge, "id", f"{current_id}->{neighbor_id}")
                            edge_type = getattr(edge, "type", "unknown")
                            typed_omissions.append(TypedOmissionEntry(
                                edge_id=edge_id,
                                edge_type=edge_type,
                                reason=OmissionReason.DEPTH_LIMIT,
                                details=f"Beyond max_hops={max_hops}",
                            ))
                continue

            neighbors = adjacency.get(current_id, set())
            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                included_nodes.add(neighbor_id)

                # Add all edges between current and neighbor
                edges_to_neighbor = edge_index.get((current_id, neighbor_id), [])
                for edge in edges_to_neighbor:
                    edge_id = getattr(edge, "id", f"{current_id}->{neighbor_id}")
                    included_edges.add(edge_id)

                queue.append((neighbor_id, depth + 1))

        return included_nodes, included_edges, typed_omissions

    def _find_guard_nodes(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        included_nodes: Set[str],
        guard_types: List[str],
    ) -> Tuple[Set[str], List[str]]:
        """Find nodes that represent guards/anti-signals.

        Returns:
            Tuple of (guard_node_ids, guard_evidence_ids)
        """
        guard_nodes: Set[str] = set()
        guard_evidence: List[str] = []

        if not guard_types:
            return guard_nodes, guard_evidence

        # Guard type to property mapping
        guard_property_map = {
            "reentrancy_guard": "has_reentrancy_guard",
            "access_control": "has_access_gate",
            "pausable": "has_pausable_modifier",
            "timelock": "has_timelock",
            "oracle_check": "has_oracle_validation",
            "slippage_check": "has_slippage_protection",
            "balance_check": "has_balance_check",
        }

        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            node_id = getattr(node, "id", str(node))
            props = getattr(node, "properties", {})

            # Check if node has any guard type
            for guard_type in guard_types:
                prop_name = guard_property_map.get(guard_type)
                if prop_name and props.get(prop_name):
                    guard_nodes.add(node_id)
                    # Extract evidence IDs if available
                    evidence_list = props.get("evidence", [])
                    for ev in evidence_list:
                        if isinstance(ev, dict):
                            ev_id = ev.get("evidence_id")
                            if ev_id:
                                guard_evidence.append(ev_id)

        return guard_nodes, guard_evidence

    def _check_missing_ops(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        included_nodes: Set[str],
        required_ops: List[str],
    ) -> List[str]:
        """Check which required operations are missing from included nodes."""
        found_ops: Set[str] = set()

        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            node_id = getattr(node, "id", str(node))
            if node_id not in included_nodes:
                continue
            props = getattr(node, "properties", {})
            node_ops = props.get("semantic_ops", []) or []
            found_ops.update(node_ops)

        missing = [op for op in required_ops if op not in found_ops]
        return missing

    def _check_forbidden_ops(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        included_nodes: Set[str],
        forbidden_ops: List[str],
    ) -> bool:
        """Check if any forbidden operations exist in included nodes."""
        if not forbidden_ops:
            return False

        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            node_id = getattr(node, "id", str(node))
            if node_id not in included_nodes:
                continue
            props = getattr(node, "properties", {})
            node_ops = props.get("semantic_ops", []) or []
            if any(op in node_ops for op in forbidden_ops):
                return True

        return False

    def _build_sliced_graph(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        included_nodes: Set[str],
        included_edges: Set[str],
        focal_nodes: List[str],
        category: Optional[Union[VulnerabilityCategory, str]],
    ) -> SlicedGraph:
        """Build SlicedGraph from included nodes and edges."""
        # Normalize category
        category_str = ""
        relevant_props: Optional[Set[str]] = None

        if category:
            if isinstance(category, str):
                try:
                    category_enum = VulnerabilityCategory(category.lower())
                except ValueError:
                    category_enum = VulnerabilityCategory.GENERAL
            else:
                category_enum = category

            category_str = category_enum.value
            prop_set = get_property_set(category_enum)
            if self.strict_mode:
                relevant_props = set(prop_set.required)
            else:
                relevant_props = set(prop_set.all_properties())
            if self.include_core:
                relevant_props |= set(CORE_PROPERTIES)

        sliced = SlicedGraph(
            category=category_str,
            focal_node_ids=list(focal_nodes),
        )

        stats = SlicingStats(category=category_str)

        # Add nodes
        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            node_id = getattr(node, "id", str(node))
            if node_id not in included_nodes:
                continue

            props = getattr(node, "properties", {})
            stats.original_property_count += len(props)
            stats.nodes_processed += 1

            # Filter properties if category specified
            if relevant_props is not None:
                filtered_props = self._filter_properties(props, relevant_props)
            else:
                filtered_props = dict(props)

            stats.sliced_property_count += len(filtered_props)

            sliced_node = SubGraphNode(
                id=node_id,
                type=getattr(node, "type", "unknown"),
                label=getattr(node, "label", ""),
                properties=filtered_props,
                relevance_score=getattr(node, "relevance_score", 0.0),
                distance_from_focal=getattr(node, "distance_from_focal", 0),
                is_focal=node_id in focal_nodes,
            )
            sliced.add_node(sliced_node)

        # Add edges
        edges = graph.edges if hasattr(graph, "edges") else {}
        if isinstance(edges, dict):
            edges = edges.values()

        for edge in edges:
            edge_id = getattr(edge, "id", "")
            if edge_id in included_edges:
                sliced_edge = SubGraphEdge(
                    id=edge_id,
                    type=getattr(edge, "type", "unknown"),
                    source=getattr(edge, "source", ""),
                    target=getattr(edge, "target", ""),
                    properties=getattr(edge, "properties", {}),
                )
                sliced.add_edge(sliced_edge)

        stats.calculate_reduction()
        sliced.stats = stats

        return sliced

    def _extract_witness(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        sliced: SlicedGraph,
        required_ops: List[str],
        expected_evidence_ids: List[str],
    ) -> WitnessEvidence:
        """Extract witness evidence deterministically.

        Witness extraction is ordered by:
        1. Node ID (sorted)
        2. Operation name (sorted)
        3. Evidence ID (sorted)

        This ensures deterministic ordering across builds.
        """
        evidence_ids: List[str] = []
        node_ids: List[str] = []
        edge_ids: List[str] = []
        operations: List[str] = []

        # Collect nodes with required ops (sorted for determinism)
        for node_id in sorted(sliced.nodes.keys()):
            node = sliced.nodes[node_id]
            node_ops = node.properties.get("semantic_ops", []) or []

            # Check if node has any required op
            has_required = any(op in node_ops for op in required_ops)
            if has_required:
                node_ids.append(node_id)

                # Add operations found (sorted)
                for op in sorted(node_ops):
                    if op in required_ops and op not in operations:
                        operations.append(op)

                # Extract evidence IDs (sorted)
                evidence_list = node.properties.get("evidence", [])
                for ev in evidence_list:
                    if isinstance(ev, dict):
                        ev_id = ev.get("evidence_id")
                        if ev_id and ev_id not in evidence_ids:
                            evidence_ids.append(ev_id)

        # Collect edges between witness nodes (sorted)
        for edge_id in sorted(sliced.edges.keys()):
            edge = sliced.edges[edge_id]
            if edge.source in node_ids and edge.target in node_ids:
                if edge_id not in edge_ids:
                    edge_ids.append(edge_id)

        # Add expected evidence IDs that were found
        for ev_id in sorted(expected_evidence_ids):
            if ev_id in evidence_ids and ev_id not in evidence_ids:
                evidence_ids.append(ev_id)

        return WitnessEvidence(
            evidence_ids=sorted(evidence_ids),
            node_ids=sorted(node_ids),
            edge_ids=sorted(edge_ids),
            operations=sorted(operations),
        )

    def _check_missing_witness(
        self,
        graph: Union[SubGraph, "KnowledgeGraph"],
        expected_evidence_ids: List[str],
    ) -> List[str]:
        """Check which expected witness evidence IDs are missing from graph."""
        if not expected_evidence_ids:
            return []

        # Collect all evidence IDs in graph
        found_ids: Set[str] = set()

        nodes = graph.nodes.values() if hasattr(graph, "nodes") else []
        for node in nodes:
            props = getattr(node, "properties", {})
            evidence_list = props.get("evidence", [])
            for ev in evidence_list:
                if isinstance(ev, dict):
                    ev_id = ev.get("evidence_id")
                    if ev_id:
                        found_ids.add(ev_id)

        # Check for missing
        missing = [ev_id for ev_id in expected_evidence_ids if ev_id not in found_ids]
        return missing

    def _filter_properties(
        self,
        properties: Dict[str, Any],
        relevant: Set[str],
    ) -> Dict[str, Any]:
        """Filter properties to only those in relevant set.

        Args:
            properties: Original property dictionary
            relevant: Set of relevant property names

        Returns:
            Filtered property dictionary
        """
        return {k: v for k, v in properties.items() if k in relevant}

    def _get_category_from_finding(self, finding: Any) -> VulnerabilityCategory:
        """Extract category from a finding.

        Args:
            finding: Finding object or dictionary

        Returns:
            VulnerabilityCategory inferred from finding
        """
        # Try to get category directly
        if hasattr(finding, "category"):
            category = finding.category
            if isinstance(category, VulnerabilityCategory):
                return category
            try:
                return VulnerabilityCategory(str(category).lower())
            except ValueError:
                pass

        # Try to get from pattern_id
        pattern_id = None
        if hasattr(finding, "pattern_id"):
            pattern_id = finding.pattern_id
        elif isinstance(finding, dict):
            pattern_id = finding.get("pattern_id") or finding.get("pattern")

        if pattern_id:
            return get_category_from_pattern_id(pattern_id)

        # Fallback to GENERAL
        return VulnerabilityCategory.GENERAL


def slice_graph_for_category(
    graph: Union[SubGraph, "KnowledgeGraph"],
    category: Union[VulnerabilityCategory, str],
    include_core: bool = True,
    strict_mode: bool = False,
) -> SlicedGraph:
    """Convenience function to slice a graph for a category.

    Args:
        graph: Graph to slice
        category: Vulnerability category
        include_core: Include CORE_PROPERTIES
        strict_mode: Only required properties

    Returns:
        SlicedGraph with category-relevant properties
    """
    slicer = GraphSlicer(include_core=include_core, strict_mode=strict_mode)
    return slicer.slice_for_category(graph, category)


def slice_graph_for_finding(
    graph: Union[SubGraph, "KnowledgeGraph"],
    finding: Any,
    include_core: bool = True,
    strict_mode: bool = False,
) -> SlicedGraph:
    """Convenience function to slice a graph for a finding.

    Args:
        graph: Graph to slice
        finding: Finding with pattern/category info
        include_core: Include CORE_PROPERTIES
        strict_mode: Only required properties

    Returns:
        SlicedGraph sliced to finding's category
    """
    slicer = GraphSlicer(include_core=include_core, strict_mode=strict_mode)
    return slicer.slice_for_finding(graph, finding)


def calculate_slicing_impact(
    graph: Union[SubGraph, "KnowledgeGraph"],
) -> Dict[str, Dict[str, float]]:
    """Calculate slicing impact for all categories.

    Useful for understanding potential token savings across categories.

    Args:
        graph: Graph to analyze

    Returns:
        Dictionary mapping category -> {reduction_percent, property_count}
    """
    slicer = GraphSlicer()
    results = {}

    for category in VulnerabilityCategory:
        sliced = slicer.slice_for_category(graph, category)
        results[category.value] = {
            "reduction_percent": sliced.stats.reduction_percent,
            "original_properties": sliced.stats.original_property_count,
            "sliced_properties": sliced.stats.sliced_property_count,
            "nodes_processed": sliced.stats.nodes_processed,
        }

    return results


# =============================================================================
# Pattern-Scoped Slicing v2 Convenience Functions (Phase 5.10-04)
# =============================================================================


def slice_graph_for_pattern_focus(
    graph: Union[SubGraph, "KnowledgeGraph"],
    focus: PatternSliceFocus,
    focal_nodes: List[str],
    category: Optional[Union[VulnerabilityCategory, str]] = None,
    include_core: bool = True,
    strict_mode: bool = False,
) -> PatternSliceResult:
    """Pattern-scoped slicing v2 convenience function.

    This is the primary entry point for PCP v2 pattern-scoped slicing.
    It implements edge-closure traversal with witness extraction and
    typed omission reporting.

    Args:
        graph: Graph to slice
        focus: PatternSliceFocus from PCP v2
        focal_nodes: Starting node IDs
        category: Optional category for property filtering
        include_core: Include CORE_PROPERTIES
        strict_mode: Only required properties

    Returns:
        PatternSliceResult with witnesses, omissions, and completeness info

    Example:
        >>> focus = PatternSliceFocus.from_pcp(pcp_data)
        >>> result = slice_graph_for_pattern_focus(
        ...     graph=kg,
        ...     focus=focus,
        ...     focal_nodes=["F-withdraw-001"],
        ...     category="reentrancy",
        ... )
        >>> if result.is_complete:
        ...     print("Pattern has all required evidence")
        >>> else:
        ...     print(f"Missing: {result.missing_required_ops}")
    """
    slicer = GraphSlicer(include_core=include_core, strict_mode=strict_mode)
    return slicer.slice_for_pattern_focus(graph, focus, focal_nodes, category)


def slice_graph_for_pcp(
    graph: Union[SubGraph, "KnowledgeGraph"],
    pcp_data: Dict[str, Any],
    focal_nodes: List[str],
    category: Optional[Union[VulnerabilityCategory, str]] = None,
    include_core: bool = True,
    strict_mode: bool = False,
) -> PatternSliceResult:
    """Pattern-scoped slicing from raw PCP v2 data.

    Convenience function that parses PCP v2 data and performs slicing.

    Args:
        graph: Graph to slice
        pcp_data: Raw PCP v2 dictionary or PatternContextPackV2 data
        focal_nodes: Starting node IDs
        category: Optional category for property filtering
        include_core: Include CORE_PROPERTIES
        strict_mode: Only required properties

    Returns:
        PatternSliceResult with witnesses and omissions

    Example:
        >>> pcp_data = yaml.safe_load(pcp_yaml)
        >>> result = slice_graph_for_pcp(kg, pcp_data, ["F-001"])
    """
    focus = PatternSliceFocus.from_pcp(pcp_data)
    return slice_graph_for_pattern_focus(
        graph, focus, focal_nodes, category, include_core, strict_mode
    )


def extract_witness_for_pattern(
    graph: Union[SubGraph, "KnowledgeGraph"],
    required_ops: List[str],
    focal_nodes: List[str],
) -> WitnessEvidence:
    """Extract witness evidence for a pattern deterministically.

    Standalone witness extraction without full slicing.

    Args:
        graph: Graph to search
        required_ops: Required semantic operations
        focal_nodes: Starting node IDs

    Returns:
        WitnessEvidence with deterministic ordering
    """
    focus = PatternSliceFocus(required_ops=required_ops)
    slicer = GraphSlicer()
    result = slicer.slice_for_pattern_focus(graph, focus, focal_nodes)
    return result.witness


# =============================================================================
# Task 9.E: Request More Context Fallback
# =============================================================================


class ContextExpansionLevel:
    """Defines progressive levels of context expansion.

    When sliced context is insufficient, agents can request more context
    in controlled, progressive steps.
    """

    STRICT = "strict"  # Minimal: only required category properties
    STANDARD = "standard"  # Default: required + optional properties
    RELAXED = "relaxed"  # Wide: category + adjacent category properties
    FULL = "full"  # Complete: all properties (no slicing)

    _progression = [STRICT, STANDARD, RELAXED, FULL]

    @classmethod
    def next_level(cls, current: str) -> Optional[str]:
        """Get the next expansion level.

        Args:
            current: Current expansion level

        Returns:
            Next level or None if already at FULL
        """
        try:
            idx = cls._progression.index(current)
            if idx < len(cls._progression) - 1:
                return cls._progression[idx + 1]
            return None
        except ValueError:
            return cls.STANDARD

    @classmethod
    def all_levels(cls) -> List[str]:
        """Get all expansion levels in order."""
        return cls._progression.copy()


@dataclass
class ContextExpansionRequest:
    """Request for additional context from an LLM agent.

    Agents can request more context when sliced graphs are insufficient
    for vulnerability analysis.
    """

    reason: str = ""  # Why more context is needed
    current_level: str = "standard"
    requested_level: Optional[str] = None  # Specific level or None for auto
    requested_properties: List[str] = field(default_factory=list)
    requested_categories: List[str] = field(default_factory=list)
    node_ids: List[str] = field(default_factory=list)  # Specific nodes

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "reason": self.reason,
            "current_level": self.current_level,
            "requested_level": self.requested_level,
            "requested_properties": self.requested_properties,
            "requested_categories": self.requested_categories,
            "node_ids": self.node_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextExpansionRequest":
        """Deserialize from dictionary."""
        return cls(
            reason=data.get("reason", ""),
            current_level=data.get("current_level", "standard"),
            requested_level=data.get("requested_level"),
            requested_properties=data.get("requested_properties", []),
            requested_categories=data.get("requested_categories", []),
            node_ids=data.get("node_ids", []),
        )


@dataclass
class ContextExpansionResult:
    """Result of a context expansion request."""

    original_graph: SlicedGraph
    expanded_graph: SlicedGraph
    new_level: str
    properties_added: int = 0
    nodes_affected: int = 0
    expansion_reason: str = ""
    can_expand_further: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "new_level": self.new_level,
            "properties_added": self.properties_added,
            "nodes_affected": self.nodes_affected,
            "expansion_reason": self.expansion_reason,
            "can_expand_further": self.can_expand_further,
            "expanded_graph": self.expanded_graph.to_dict(),
        }


class ContextExpander:
    """Handles context expansion requests from LLM agents.

    When an LLM determines that sliced context is insufficient for analysis,
    it can request more context through this class.

    Usage:
        expander = ContextExpander(full_graph, slicer)

        # Create sliced graph
        sliced = slicer.slice_for_category(subgraph, "reentrancy")

        # Agent requests more context
        request = ContextExpansionRequest(
            reason="Need cross-function state access to verify reentrancy",
            current_level="strict",
        )
        result = expander.expand(sliced, request)

        # Check if more expansion possible
        if result.can_expand_further:
            # Agent can request more if still insufficient
            pass
    """

    # Adjacent categories for RELAXED expansion
    _adjacent_categories: Dict[str, List[str]] = {
        "reentrancy": ["value_movement", "external_calls"],
        "access_control": ["privilege", "state_integrity"],
        "oracle": ["price_manipulation", "external_calls"],
        "dos": ["gas_consumption", "loops"],
        "mev": ["price_manipulation", "value_movement"],
        "token": ["value_movement", "erc_compliance"],
        "upgrade": ["proxy", "storage"],
        "crypto": ["signature", "randomness"],
        "logic": ["state_integrity", "invariant"],
        "governance": ["access_control", "voting"],
    }

    def __init__(
        self,
        full_graph: Union[SubGraph, "KnowledgeGraph"],
        slicer: Optional[GraphSlicer] = None,
    ):
        """Initialize context expander.

        Args:
            full_graph: The full/original graph for expansion
            slicer: GraphSlicer instance (creates one if not provided)
        """
        self.full_graph = full_graph
        self.slicer = slicer or GraphSlicer()
        self._expansion_history: List[ContextExpansionResult] = []

    def expand(
        self,
        current: SlicedGraph,
        request: ContextExpansionRequest,
    ) -> ContextExpansionResult:
        """Expand context based on request.

        Args:
            current: Currently sliced graph
            request: Expansion request from agent

        Returns:
            ContextExpansionResult with expanded graph
        """
        # Determine target level
        if request.requested_level:
            target_level = request.requested_level
        else:
            target_level = ContextExpansionLevel.next_level(request.current_level)
            if target_level is None:
                # Already at full - return same graph
                return ContextExpansionResult(
                    original_graph=current,
                    expanded_graph=current,
                    new_level=ContextExpansionLevel.FULL,
                    can_expand_further=False,
                    expansion_reason="Already at full context level",
                )

        # Handle specific property requests
        if request.requested_properties:
            expanded = self._expand_with_properties(
                current, request.requested_properties
            )
            result = ContextExpansionResult(
                original_graph=current,
                expanded_graph=expanded,
                new_level=request.current_level,  # Level unchanged
                properties_added=expanded.stats.sliced_property_count
                - current.stats.sliced_property_count,
                nodes_affected=expanded.stats.nodes_processed,
                expansion_reason=request.reason,
                can_expand_further=target_level != ContextExpansionLevel.FULL,
            )
            self._expansion_history.append(result)
            return result

        # Handle category expansion
        if request.requested_categories:
            categories = [current.category] + request.requested_categories
            expanded = self.slicer.slice_multiple_categories(
                self.full_graph, categories
            )
            result = ContextExpansionResult(
                original_graph=current,
                expanded_graph=expanded,
                new_level=request.current_level,
                properties_added=expanded.stats.sliced_property_count
                - current.stats.sliced_property_count,
                nodes_affected=expanded.stats.nodes_processed,
                expansion_reason=request.reason,
                can_expand_further=True,
            )
            self._expansion_history.append(result)
            return result

        # Standard level-based expansion
        expanded = self._expand_to_level(current, target_level)
        result = ContextExpansionResult(
            original_graph=current,
            expanded_graph=expanded,
            new_level=target_level,
            properties_added=expanded.stats.sliced_property_count
            - current.stats.sliced_property_count,
            nodes_affected=expanded.stats.nodes_processed,
            expansion_reason=request.reason,
            can_expand_further=target_level != ContextExpansionLevel.FULL,
        )
        self._expansion_history.append(result)
        return result

    def _expand_to_level(self, current: SlicedGraph, level: str) -> SlicedGraph:
        """Expand to a specific level.

        Args:
            current: Current sliced graph
            level: Target expansion level

        Returns:
            Expanded SlicedGraph
        """
        category = current.category.split("+")[0]  # Handle multi-category

        if level == ContextExpansionLevel.STRICT:
            # Re-slice with strict mode
            strict_slicer = GraphSlicer(include_core=True, strict_mode=True)
            return strict_slicer.slice_for_category(self.full_graph, category)

        elif level == ContextExpansionLevel.STANDARD:
            # Re-slice with standard mode
            standard_slicer = GraphSlicer(include_core=True, strict_mode=False)
            return standard_slicer.slice_for_category(self.full_graph, category)

        elif level == ContextExpansionLevel.RELAXED:
            # Include adjacent categories
            adjacent = self._adjacent_categories.get(category, [])
            categories = [category] + adjacent[:2]  # Limit to 2 adjacent
            return self.slicer.slice_multiple_categories(self.full_graph, categories)

        elif level == ContextExpansionLevel.FULL:
            # Return full graph without property slicing
            return self._create_full_context()

        else:
            # Unknown level, return standard
            return self.slicer.slice_for_category(self.full_graph, category)

    def _expand_with_properties(
        self,
        current: SlicedGraph,
        additional_properties: List[str],
    ) -> SlicedGraph:
        """Expand by adding specific properties.

        Args:
            current: Current sliced graph
            additional_properties: Properties to add

        Returns:
            SlicedGraph with additional properties
        """
        # Get current properties from first node as reference
        current_props: Set[str] = set()
        for node in current.nodes.values():
            current_props.update(node.properties.keys())
            break

        # Add requested properties
        all_props = current_props | set(additional_properties)

        # Re-slice with expanded property set
        expanded = SlicedGraph(
            category=current.category,
            focal_node_ids=current.focal_node_ids.copy(),
        )

        stats = SlicingStats(category=current.category)

        # Process from full graph
        nodes = (
            self.full_graph.nodes.values()
            if hasattr(self.full_graph, "nodes")
            else []
        )
        for node in nodes:
            if hasattr(node, "properties"):
                original_props = node.properties
            else:
                original_props = {}

            stats.original_property_count += len(original_props)
            stats.nodes_processed += 1

            # Filter to expanded set
            filtered_props = {k: v for k, v in original_props.items() if k in all_props}
            stats.sliced_property_count += len(filtered_props)

            sliced_node = SubGraphNode(
                id=node.id if hasattr(node, "id") else str(node),
                type=node.type if hasattr(node, "type") else "unknown",
                label=node.label if hasattr(node, "label") else "",
                properties=filtered_props,
                relevance_score=getattr(node, "relevance_score", 0.0),
                distance_from_focal=getattr(node, "distance_from_focal", 0),
                is_focal=getattr(node, "is_focal", False),
            )
            expanded.add_node(sliced_node)

        # Copy edges
        edges = (
            self.full_graph.edges.values()
            if hasattr(self.full_graph, "edges")
            else []
        )
        for edge in edges:
            sliced_edge = SubGraphEdge(
                id=edge.id if hasattr(edge, "id") else str(edge),
                type=edge.type if hasattr(edge, "type") else "unknown",
                source=edge.source if hasattr(edge, "source") else "",
                target=edge.target if hasattr(edge, "target") else "",
                properties=getattr(edge, "properties", {}),
            )
            expanded.add_edge(sliced_edge)

        stats.calculate_reduction()
        expanded.stats = stats

        return expanded

    def _create_full_context(self) -> SlicedGraph:
        """Create a SlicedGraph with all properties (no slicing).

        Returns:
            SlicedGraph containing all original properties
        """
        full = SlicedGraph(
            category="full",
            full_graph_available=False,  # Can't expand further
        )

        stats = SlicingStats(category="full")

        nodes = (
            self.full_graph.nodes.values()
            if hasattr(self.full_graph, "nodes")
            else []
        )
        for node in nodes:
            if hasattr(node, "properties"):
                props = node.properties
            else:
                props = {}

            stats.original_property_count += len(props)
            stats.sliced_property_count += len(props)
            stats.nodes_processed += 1

            full_node = SubGraphNode(
                id=node.id if hasattr(node, "id") else str(node),
                type=node.type if hasattr(node, "type") else "unknown",
                label=node.label if hasattr(node, "label") else "",
                properties=props.copy(),
                relevance_score=getattr(node, "relevance_score", 0.0),
                distance_from_focal=getattr(node, "distance_from_focal", 0),
                is_focal=getattr(node, "is_focal", False),
            )
            full.add_node(full_node)

        edges = (
            self.full_graph.edges.values()
            if hasattr(self.full_graph, "edges")
            else []
        )
        for edge in edges:
            full_edge = SubGraphEdge(
                id=edge.id if hasattr(edge, "id") else str(edge),
                type=edge.type if hasattr(edge, "type") else "unknown",
                source=edge.source if hasattr(edge, "source") else "",
                target=edge.target if hasattr(edge, "target") else "",
                properties=getattr(edge, "properties", {}),
            )
            full.add_edge(full_edge)

        stats.calculate_reduction()  # Should be 0% reduction
        full.stats = stats

        return full

    def get_expansion_history(self) -> List[Dict[str, Any]]:
        """Get history of all expansions.

        Returns:
            List of expansion result dictionaries
        """
        return [r.to_dict() for r in self._expansion_history]

    def get_available_expansions(self, current: SlicedGraph) -> Dict[str, Any]:
        """Get available expansion options for current context.

        Args:
            current: Current sliced graph

        Returns:
            Dictionary describing available expansions
        """
        category = current.category.split("+")[0]

        # Determine current level based on strict_mode (approximate)
        current_level = ContextExpansionLevel.STANDARD
        if current.stats.reduction_percent > 80:
            current_level = ContextExpansionLevel.STRICT
        elif current.stats.reduction_percent < 20:
            current_level = ContextExpansionLevel.RELAXED

        next_level = ContextExpansionLevel.next_level(current_level)
        adjacent = self._adjacent_categories.get(category, [])

        # Get available properties not currently included
        current_props: Set[str] = set()
        for node in current.nodes.values():
            current_props.update(node.properties.keys())
            break

        all_props: Set[str] = set()
        nodes = (
            self.full_graph.nodes.values()
            if hasattr(self.full_graph, "nodes")
            else []
        )
        for node in nodes:
            if hasattr(node, "properties"):
                all_props.update(node.properties.keys())
            break

        available_props = all_props - current_props

        return {
            "current_level": current_level,
            "next_level": next_level,
            "can_expand": next_level is not None,
            "adjacent_categories": adjacent,
            "available_properties": list(available_props)[:20],  # Limit preview
            "available_property_count": len(available_props),
            "expansion_history_count": len(self._expansion_history),
        }


def request_more_context(
    full_graph: Union[SubGraph, "KnowledgeGraph"],
    current: SlicedGraph,
    reason: str = "",
    requested_level: Optional[str] = None,
    requested_properties: Optional[List[str]] = None,
) -> ContextExpansionResult:
    """Convenience function to request more context.

    This is the primary interface for LLM agents to request expanded context.

    Args:
        full_graph: Full graph for expansion
        current: Current sliced graph
        reason: Why more context is needed
        requested_level: Specific level to expand to
        requested_properties: Specific properties to add

    Returns:
        ContextExpansionResult with expanded graph

    Example:
        # Agent realizes it needs more context
        result = request_more_context(
            full_graph,
            current_sliced,
            reason="Need state variable access patterns for cross-function analysis",
        )
        expanded = result.expanded_graph
    """
    expander = ContextExpander(full_graph)

    request = ContextExpansionRequest(
        reason=reason,
        current_level=ContextExpansionLevel.STANDARD,  # Assume standard
        requested_level=requested_level,
        requested_properties=requested_properties or [],
    )

    return expander.expand(current, request)


# =============================================================================
# Task 05.9-07: Unified Slicing Pipeline
# =============================================================================


@dataclass
class PipelineConfig:
    """Configuration for the unified slicing pipeline.

    Attributes:
        slice_mode: "standard" or "debug" - debug bypasses pruning
        context_mode: "strict", "standard", or "relaxed" for PPR
        category: Vulnerability category for property slicing
        max_nodes: Maximum nodes in subgraph
        max_hops: Maximum hops for BFS expansion
        role_budget: Optional role-specific token budget
        include_core_properties: Always include CORE_PROPERTIES
        strict_property_mode: Only required properties (not optional)
        apply_context_policy: Whether to apply ContextPolicy filtering
    """

    slice_mode: str = "standard"
    context_mode: str = "standard"
    category: str = "general"
    max_nodes: int = 50
    max_hops: int = 2
    role_budget: Optional[int] = None
    include_core_properties: bool = True
    strict_property_mode: bool = False
    apply_context_policy: bool = True

    @classmethod
    def for_role(cls, role: str) -> "PipelineConfig":
        """Get config tailored to agent role.

        Args:
            role: Agent role ("attacker", "defender", "verifier", "classifier")

        Returns:
            PipelineConfig optimized for the role
        """
        role_configs = {
            "attacker": cls(
                context_mode="relaxed",
                max_nodes=80,
                max_hops=3,
                role_budget=3000,
            ),
            "defender": cls(
                context_mode="standard",
                max_nodes=60,
                max_hops=2,
                role_budget=2500,
            ),
            "verifier": cls(
                context_mode="standard",
                max_nodes=40,
                max_hops=2,
                role_budget=2000,
            ),
            "classifier": cls(
                context_mode="strict",
                max_nodes=30,
                max_hops=1,
                role_budget=1500,
            ),
        }
        return role_configs.get(role.lower(), cls())

    @classmethod
    def debug(cls, **kwargs: Any) -> "PipelineConfig":
        """Get debug config that bypasses pruning."""
        config = cls(**kwargs)
        config.slice_mode = "debug"
        return config


@dataclass
class PipelineResult:
    """Result from the unified slicing pipeline.

    Contains the sliced graph plus pipeline metadata for diagnostics.
    """

    graph: SlicedGraph
    omissions: OmissionLedger
    stats: Dict[str, Any] = field(default_factory=dict)
    config: PipelineConfig = field(default_factory=PipelineConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "graph": self.graph.to_dict(),
            "omissions": self.omissions.to_dict(),
            "stats": self.stats,
            "config": {
                "slice_mode": self.config.slice_mode,
                "context_mode": self.config.context_mode,
                "category": self.config.category,
                "max_nodes": self.config.max_nodes,
            },
        }


class UnifiedSlicingPipeline:
    """Unified slicing pipeline for all LLM-facing surfaces.

    This pipeline ensures consistent, omission-aware context for all agents
    by combining:
    1. PPR seed selection and relevance scoring
    2. Subgraph extraction (BFS from focal nodes)
    3. GraphSlicer property filtering (category-aware)
    4. ContextPolicy data minimization (optional)
    5. Omission ledger injection

    All agents receive slices from this same pipeline with role-specific budgets.

    Usage:
        pipeline = UnifiedSlicingPipeline(graph)

        # Standard slicing for reentrancy analysis
        result = pipeline.slice(
            focal_nodes=["func_withdraw"],
            config=PipelineConfig(category="reentrancy"),
        )

        # Role-specific slicing
        result = pipeline.slice_for_role(
            focal_nodes=["func_withdraw"],
            role="attacker",
            category="reentrancy",
        )

        # Debug mode (bypasses pruning)
        result = pipeline.slice(
            focal_nodes=["func_withdraw"],
            config=PipelineConfig.debug(category="reentrancy"),
        )
    """

    def __init__(self, graph: Any):
        """Initialize with a KnowledgeGraph.

        Args:
            graph: KnowledgeGraph instance
        """
        self.graph = graph
        self._slicer = GraphSlicer()
        self._adjacency: Dict[str, Set[str]] = {}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        """Build adjacency list from graph edges."""
        if not hasattr(self.graph, "edges"):
            return
        edges = self.graph.edges
        if isinstance(edges, dict):
            edges = edges.values()
        for edge in edges:
            source = getattr(edge, "source", "")
            target = getattr(edge, "target", "")
            if isinstance(edge, dict):
                source = edge.get("source", "")
                target = edge.get("target", "")
            self._adjacency.setdefault(source, set()).add(target)
            self._adjacency.setdefault(target, set()).add(source)

    def slice(
        self,
        focal_nodes: List[str],
        config: Optional[PipelineConfig] = None,
    ) -> PipelineResult:
        """Execute unified slicing pipeline.

        Pipeline stages:
        1. PPR seed selection (relevance scoring)
        2. Subgraph extraction (BFS + relevance pruning)
        3. Property slicing (category-aware filtering)
        4. ContextPolicy filtering (data minimization)
        5. Omission ledger injection

        Args:
            focal_nodes: Starting node IDs for analysis
            config: Pipeline configuration

        Returns:
            PipelineResult with sliced graph and metadata
        """
        if config is None:
            config = PipelineConfig()

        # Track pipeline stats
        stats: Dict[str, Any] = {
            "pipeline_version": "2.0",
            "slice_mode": config.slice_mode,
            "stages_completed": [],
        }

        # Stage 1: PPR seed selection and relevance scoring
        ppr_scores = self._run_ppr_scoring(focal_nodes, config)
        stats["stages_completed"].append("ppr_seed_selection")
        stats["ppr_scores_computed"] = len(ppr_scores)

        # Stage 2: Subgraph extraction with BFS
        subgraph = self._extract_subgraph(focal_nodes, ppr_scores, config)
        stats["stages_completed"].append("subgraph_extraction")
        stats["subgraph_nodes"] = len(subgraph.nodes)
        stats["subgraph_edges"] = len(subgraph.edges)

        # Stage 3: Property slicing (category-aware)
        self._slicer.include_core = config.include_core_properties
        self._slicer.strict_mode = config.strict_property_mode
        sliced = self._slicer.slice_for_category(subgraph, config.category)
        stats["stages_completed"].append("property_slicing")
        stats["sliced_nodes"] = sliced.node_count()
        stats["property_reduction_percent"] = sliced.stats.reduction_percent

        # Stage 4: ContextPolicy filtering (optional)
        if config.apply_context_policy:
            # ContextPolicy integration would go here
            # For now we preserve the sliced graph as-is
            stats["stages_completed"].append("context_policy")

        # Stage 5: Omission ledger injection
        # Mark slice_mode in omissions
        from alphaswarm_sol.kg.subgraph import SliceMode
        if config.slice_mode == "debug":
            sliced.omissions.slice_mode = SliceMode.DEBUG
        else:
            sliced.omissions.slice_mode = SliceMode.STANDARD

        stats["stages_completed"].append("omission_injection")
        stats["coverage_score"] = sliced.omissions.coverage_score
        stats["omissions_present"] = sliced.omissions.has_omissions()

        return PipelineResult(
            graph=sliced,
            omissions=sliced.omissions,
            stats=stats,
            config=config,
        )

    def slice_for_role(
        self,
        focal_nodes: List[str],
        role: str,
        category: str = "general",
    ) -> PipelineResult:
        """Execute pipeline with role-specific configuration.

        Args:
            focal_nodes: Starting node IDs
            role: Agent role ("attacker", "defender", "verifier", "classifier")
            category: Vulnerability category

        Returns:
            PipelineResult optimized for the agent role
        """
        config = PipelineConfig.for_role(role)
        config.category = category
        return self.slice(focal_nodes, config)

    def slice_debug(
        self,
        focal_nodes: List[str],
        category: str = "general",
    ) -> PipelineResult:
        """Execute pipeline in debug mode (no pruning).

        Debug mode:
        - Bypasses node limit pruning
        - Bypasses relevance threshold pruning
        - Marks slice_mode as "debug" in omissions
        - Preserves all candidate nodes for diagnosis

        Args:
            focal_nodes: Starting node IDs
            category: Vulnerability category

        Returns:
            PipelineResult with full context for debugging
        """
        config = PipelineConfig.debug(
            category=category,
            max_nodes=10000,  # Very high limit
        )
        return self.slice(focal_nodes, config)

    def _run_ppr_scoring(
        self,
        focal_nodes: List[str],
        config: PipelineConfig,
    ) -> Dict[str, float]:
        """Stage 1: PPR seed selection and relevance scoring.

        Args:
            focal_nodes: Starting node IDs (seeds)
            config: Pipeline configuration

        Returns:
            Dict mapping node_id -> PPR relevance score
        """
        # Try to use PPR if available
        try:
            from alphaswarm_sol.kg.ppr import PPRConfig, run_ppr

            ppr_config = self._get_ppr_config(config.context_mode)
            ppr_result = run_ppr(self.graph, focal_nodes, ppr_config)
            return ppr_result.scores
        except (ImportError, Exception):
            # Fallback: BFS-based scoring
            return self._fallback_ppr_scoring(focal_nodes, config.max_hops)

    def _get_ppr_config(self, context_mode: str) -> Any:
        """Get PPR config for context mode."""
        from alphaswarm_sol.kg.ppr import PPRConfig

        config_map = {
            "strict": PPRConfig.strict(),
            "standard": PPRConfig.standard(),
            "relaxed": PPRConfig.relaxed(),
        }
        return config_map.get(context_mode, PPRConfig.standard())

    def _fallback_ppr_scoring(
        self,
        focal_nodes: List[str],
        max_hops: int,
    ) -> Dict[str, float]:
        """Fallback scoring using BFS distance.

        Args:
            focal_nodes: Starting nodes
            max_hops: Maximum BFS depth

        Returns:
            Dict mapping node_id -> relevance score
        """
        scores: Dict[str, float] = {}
        visited: Set[str] = set()
        from collections import deque

        queue = deque()
        for node_id in focal_nodes:
            queue.append((node_id, 0))
            visited.add(node_id)
            scores[node_id] = 1.0  # Max score for focal

        while queue:
            current_id, distance = queue.popleft()
            if distance >= max_hops:
                continue

            neighbors = self._adjacency.get(current_id, set())
            for neighbor_id in neighbors:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                # Score decays with distance
                scores[neighbor_id] = 1.0 / (distance + 2)
                queue.append((neighbor_id, distance + 1))

        return scores

    def _extract_subgraph(
        self,
        focal_nodes: List[str],
        ppr_scores: Dict[str, float],
        config: PipelineConfig,
    ) -> SubGraph:
        """Stage 2: Subgraph extraction using PPR scores.

        Args:
            focal_nodes: Focal node IDs
            ppr_scores: PPR relevance scores
            config: Pipeline configuration

        Returns:
            SubGraph with relevant nodes and omission metadata
        """
        subgraph = SubGraph(
            focal_node_ids=focal_nodes,
            analysis_type="unified_pipeline",
        )

        # Sort nodes by PPR score
        sorted_nodes = sorted(
            ppr_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Track relevant nodes for coverage calculation
        relevant_nodes = set(ppr_scores.keys())
        subgraph.omissions._relevant_nodes = relevant_nodes.copy()

        # Determine how many nodes to include
        if config.slice_mode == "debug":
            # Debug mode: include all scored nodes
            nodes_to_include = [node_id for node_id, _ in sorted_nodes]
        else:
            # Standard mode: apply max_nodes limit
            nodes_to_include = [
                node_id for node_id, _ in sorted_nodes[:config.max_nodes]
            ]

        # Track omitted nodes
        omitted = [
            node_id for node_id, _ in sorted_nodes[config.max_nodes:]
        ] if len(sorted_nodes) > config.max_nodes else []

        # Add nodes to subgraph
        focal_set = set(focal_nodes)
        for node_id in nodes_to_include:
            node = self._get_node(node_id)
            if node is None:
                continue

            ppr_score = ppr_scores.get(node_id, 0.0)
            is_focal = node_id in focal_set

            sg_node = self._create_subgraph_node(
                node,
                ppr_score,
                is_focal,
                focal_nodes,
            )
            subgraph.add_node(sg_node)

        # Record omissions
        if omitted:
            for node_id in omitted:
                subgraph.omissions.add_omitted_node(node_id)
            from alphaswarm_sol.kg.subgraph import CutSetReason
            subgraph.omissions.add_cut_set_entry(
                blocker=f"max_nodes:{config.max_nodes}",
                reason=CutSetReason.BUDGET_EXCEEDED,
                impact=f"Pruned {len(omitted)} nodes to fit budget",
            )

        # Add edges between included nodes
        self._add_edges(subgraph)

        # Compute coverage score
        captured_nodes = set(subgraph.nodes.keys())
        subgraph.omissions.compute_coverage_score(captured_nodes, relevant_nodes)

        return subgraph

    def _get_node(self, node_id: str) -> Optional[Any]:
        """Get node from graph by ID."""
        if hasattr(self.graph, "nodes"):
            if isinstance(self.graph.nodes, dict):
                return self.graph.nodes.get(node_id)
        return None

    def _create_subgraph_node(
        self,
        node: Any,
        ppr_score: float,
        is_focal: bool,
        focal_nodes: List[str],
    ) -> SubGraphNode:
        """Create SubGraphNode from graph node."""
        node_id = getattr(node, "id", str(node))
        node_type = getattr(node, "type", "")
        label = getattr(node, "label", "")

        if isinstance(node, dict):
            node_id = node.get("id", str(node))
            node_type = node.get("type", "")
            label = node.get("label", "")

        props = {}
        if hasattr(node, "properties"):
            props = dict(node.properties) if isinstance(node.properties, dict) else {}
        elif isinstance(node, dict):
            props = dict(node.get("properties", {}))

        # Estimate distance from focal
        distance = 0 if is_focal else self._estimate_distance(node_id, focal_nodes, ppr_score)

        # Map PPR score to relevance (0-10 scale)
        relevance = 10.0 if is_focal else min(10.0, ppr_score * 100)

        return SubGraphNode(
            id=node_id,
            type=node_type,
            label=label,
            properties=props,
            relevance_score=relevance,
            distance_from_focal=distance,
            is_focal=is_focal,
        )

    def _estimate_distance(
        self,
        node_id: str,
        focal_nodes: List[str],
        ppr_score: float,
    ) -> int:
        """Estimate graph distance from PPR score."""
        if node_id in focal_nodes:
            return 0
        if ppr_score >= 0.1:
            return 1
        if ppr_score >= 0.01:
            return 2
        return 3

    def _add_edges(self, subgraph: SubGraph) -> None:
        """Add edges between nodes in subgraph."""
        node_ids = set(subgraph.nodes.keys())

        if not hasattr(self.graph, "edges"):
            return

        edges = self.graph.edges
        if isinstance(edges, dict):
            edges = edges.values()

        for edge in edges:
            source = getattr(edge, "source", "")
            target = getattr(edge, "target", "")
            edge_id = getattr(edge, "id", f"{source}->{target}")
            edge_type = getattr(edge, "type", "")

            if isinstance(edge, dict):
                source = edge.get("source", "")
                target = edge.get("target", "")
                edge_id = edge.get("id", f"{source}->{target}")
                edge_type = edge.get("type", "")

            if source in node_ids and target in node_ids:
                props = {}
                if hasattr(edge, "properties"):
                    props = dict(edge.properties) if isinstance(edge.properties, dict) else {}
                elif isinstance(edge, dict):
                    props = dict(edge.get("properties", {}))

                sg_edge = SubGraphEdge(
                    id=edge_id,
                    type=edge_type,
                    source=source,
                    target=target,
                    properties=props,
                )
                subgraph.add_edge(sg_edge)


# Convenience functions for unified pipeline


def slice_graph_unified(
    graph: Any,
    focal_nodes: List[str],
    category: str = "general",
    max_nodes: int = 50,
    slice_mode: str = "standard",
) -> SlicedGraph:
    """Slice graph using unified pipeline.

    This is the primary entry point for all LLM-facing slicing operations.

    Args:
        graph: KnowledgeGraph instance
        focal_nodes: Starting node IDs
        category: Vulnerability category for property filtering
        max_nodes: Maximum nodes in result
        slice_mode: "standard" or "debug"

    Returns:
        SlicedGraph with omission-aware metadata
    """
    pipeline = UnifiedSlicingPipeline(graph)
    config = PipelineConfig(
        category=category,
        max_nodes=max_nodes,
        slice_mode=slice_mode,
    )
    result = pipeline.slice(focal_nodes, config)
    return result.graph


def slice_graph_for_agent(
    graph: Any,
    focal_nodes: List[str],
    role: str,
    category: str = "general",
) -> SlicedGraph:
    """Slice graph optimized for a specific agent role.

    Args:
        graph: KnowledgeGraph instance
        focal_nodes: Starting node IDs
        role: Agent role ("attacker", "defender", "verifier", "classifier")
        category: Vulnerability category

    Returns:
        SlicedGraph optimized for the agent role
    """
    pipeline = UnifiedSlicingPipeline(graph)
    result = pipeline.slice_for_role(focal_nodes, role, category)
    return result.graph


# =============================================================================
# Phase 5.10-05: Coverage Scoring and Semantic Dilation Convenience Functions
# =============================================================================


def compute_coverage_score(
    graph: Union[SubGraph, SlicedGraph],
    required_ops: List[str],
    strong_ops: Optional[List[str]] = None,
    weak_ops: Optional[List[str]] = None,
    threshold: float = 0.8,
) -> CoverageScore:
    """Compute coverage score for a graph.

    This is the primary entry point for evaluating whether a slice
    has sufficient evidence for pattern matching.

    Args:
        graph: Graph to evaluate
        required_ops: Operations that MUST be present
        strong_ops: Important operations (default: empty)
        weak_ops: Nice-to-have operations (default: empty)
        threshold: Threshold for threshold_met flag

    Returns:
        CoverageScore with detailed evidence breakdown

    Example:
        >>> coverage = compute_coverage_score(
        ...     slice,
        ...     required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        ...     threshold=0.8,
        ... )
        >>> if not coverage.threshold_met:
        ...     print(f"Missing {coverage.required_missing} required ops")
    """
    scorer = CoverageScorer(
        required_ops=required_ops,
        strong_ops=strong_ops,
        weak_ops=weak_ops,
    )
    return scorer.score(graph, threshold)


def expand_slice_for_coverage(
    graph: Any,
    focal_nodes: List[str],
    required_ops: List[str],
    config: Optional[ExpansionConfig] = None,
    initial_radius: int = 2,
) -> Tuple[PatternSliceResult, ExpansionResult]:
    """Expand a slice until coverage threshold is met.

    This implements the "unknown -> expand -> re-evaluate" pattern
    for controlled context expansion.

    Args:
        graph: Full graph to expand from
        focal_nodes: Starting node IDs
        required_ops: Required operations to find
        config: Expansion configuration (default: standard)
        initial_radius: Starting expansion radius

    Returns:
        Tuple of (PatternSliceResult, ExpansionResult)

    Example:
        >>> result, expansion = expand_slice_for_coverage(
        ...     full_graph,
        ...     focal_nodes=["F-withdraw"],
        ...     required_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        ... )
        >>> if expansion.expanded:
        ...     print(f"Expanded from {expansion.previous_coverage:.2f} to {expansion.new_coverage:.2f}")
    """
    if config is None:
        config = ExpansionConfig.default()

    # Create dilator
    dilator = SemanticDilator(graph, config)

    # Create scorer
    scorer = CoverageScorer(required_ops=required_ops)

    # Perform dilation
    included_nodes, included_edges, expansion_result = dilator.dilate(
        focal_nodes=focal_nodes,
        required_ops=required_ops,
        initial_radius=initial_radius,
        scorer=scorer,
    )

    # Build final slice result
    slicer = GraphSlicer()
    sliced = slicer._build_sliced_graph(
        graph, included_nodes, included_edges, focal_nodes, None
    )

    # Compute final coverage
    coverage = scorer.score(sliced, config.coverage_threshold)

    # Check for missing ops
    missing_ops = [
        item.operation
        for item in coverage.evidence_items
        if item.weight == EvidenceWeight.REQUIRED and not item.found
    ]

    # Build pattern slice result
    result = PatternSliceResult(
        graph=sliced,
        witness=WitnessEvidence(),  # TODO: extract witness
        negative_witness=NegativeWitness(),
        missing_required_ops=missing_ops,
        is_complete=len(missing_ops) == 0,
        coverage=coverage,
        expansion_result=expansion_result,
    )

    return result, expansion_result


def slice_with_dilation(
    graph: Any,
    focus: PatternSliceFocus,
    focal_nodes: List[str],
    config: Optional[ExpansionConfig] = None,
    category: Optional[Union[VulnerabilityCategory, str]] = None,
) -> PatternSliceResult:
    """Pattern-scoped slicing with automatic dilation for coverage.

    This combines pattern slicing with semantic dilation to ensure
    sufficient evidence coverage before returning unknown.

    Args:
        graph: Graph to slice
        focus: PatternSliceFocus from PCP v2
        focal_nodes: Starting node IDs
        config: Expansion configuration
        category: Optional category for property filtering

    Returns:
        PatternSliceResult with coverage and expansion info

    Example:
        >>> focus = PatternSliceFocus.from_pcp(pcp_data)
        >>> result = slice_with_dilation(
        ...     graph=kg,
        ...     focus=focus,
        ...     focal_nodes=["F-withdraw"],
        ...     config=ExpansionConfig.default(),
        ... )
        >>> if result.needs_expansion():
        ...     print("Coverage still insufficient after dilation")
    """
    if config is None:
        config = ExpansionConfig.default()

    # First, do standard pattern slicing
    slicer = GraphSlicer()
    initial_result = slicer.slice_for_pattern_focus(
        graph, focus, focal_nodes, category
    )

    # Check if coverage is sufficient
    scorer = CoverageScorer(required_ops=focus.required_ops)
    initial_coverage = scorer.score(initial_result.graph, config.coverage_threshold)

    if initial_coverage.threshold_met and initial_coverage.required_missing == 0:
        # Coverage sufficient, no dilation needed
        initial_result.coverage = initial_coverage
        return initial_result

    # Perform dilation
    dilator = SemanticDilator(graph, config)
    included_nodes, included_edges, expansion_result = dilator.dilate(
        focal_nodes=focal_nodes,
        required_ops=focus.required_ops,
        initial_radius=focus.max_edge_hops,
        scorer=scorer,
    )

    # Rebuild slice with expanded nodes
    sliced = slicer._build_sliced_graph(
        graph, included_nodes, included_edges, focal_nodes, category
    )

    # Compute final coverage
    final_coverage = scorer.score(sliced, config.coverage_threshold)

    # Extract witnesses with expanded graph
    witness = slicer._extract_witness(
        graph, sliced, focus.required_ops, focus.witness_evidence_ids
    )

    # Check for missing ops after expansion
    missing_ops = [
        item.operation
        for item in final_coverage.evidence_items
        if item.weight == EvidenceWeight.REQUIRED and not item.found
    ]

    # Check for missing witness IDs
    missing_witness = slicer._check_missing_witness(
        graph, focus.witness_evidence_ids
    )

    # Check for forbidden ops
    has_forbidden = slicer._check_forbidden_ops(
        graph, included_nodes, focus.forbidden_ops
    )

    # Determine completeness
    is_complete = (
        len(missing_ops) == 0
        and len(missing_witness) == 0
        and not has_forbidden
    )

    # Build negative witness
    guard_nodes, guard_evidence = slicer._find_guard_nodes(
        graph, included_nodes, focus.anti_signal_guard_types
    )
    negative_witness = NegativeWitness(
        guard_types=focus.anti_signal_guard_types,
        excluded_operations=focus.forbidden_ops,
        guard_evidence_ids=guard_evidence,
    )

    # Merge typed omissions from initial slice and expansion
    all_omissions = list(initial_result.typed_omissions)
    all_omissions.extend(expansion_result.typed_omissions)

    return PatternSliceResult(
        graph=sliced,
        witness=witness,
        negative_witness=negative_witness,
        typed_omissions=all_omissions,
        missing_required_ops=missing_ops,
        missing_witness_ids=missing_witness,
        has_forbidden_ops=has_forbidden,
        is_complete=is_complete,
        coverage=final_coverage,
        expansion_result=expansion_result,
    )
