"""Creative Discovery Loop for Tier-B hypotheses.

Per PCONTEXT-09:
- Creative loop outputs remain Tier-B
- Near-miss, mutation, and counterfactual probes are deterministic and marked unknown unless evidenced
- All outputs are evidence-gated with explicit unknowns

Design Principles:
1. Deterministic: Same inputs produce same outputs
2. Evidence-gated: All discoveries require evidence_refs or marked as unknown
3. Tier-B only: Confidence capped at 0.70
4. Budget-aware: Halts at budget ceiling, emits unknown when evidence insufficient

Creative Exploration Types:
1. Near-miss mining: Functions one op away from pattern match
2. Pattern mutation: Ordering variants / op substitutions
3. Counterfactual probes: Using PCP counterfactuals
4. Anomaly motifs: Statistical outliers in op distribution
5. Shadow patterns: Novel pattern proposals from near-miss clusters

Usage:
    from alphaswarm_sol.orchestration.creative import (
        CreativeDiscoveryLoop,
        CreativeDiscoveryConfig,
        NearMissResult,
        MutationResult,
        CounterfactualProbe,
        ShadowPattern,
    )

    # Configure creative loop
    config = CreativeDiscoveryConfig(
        max_near_misses=10,
        max_mutations=5,
        enable_shadow_patterns=True,
    )

    # Run creative discovery
    loop = CreativeDiscoveryLoop(config=config)
    results = loop.discover(
        graph=knowledge_graph,
        patterns=pattern_definitions,
        pcp=pattern_context_pack,
        budget_remaining=2000,
    )

    # All results are Tier-B
    for hypothesis in results.hypotheses:
        assert hypothesis.confidence <= 0.70
        assert len(hypothesis.unknowns) > 0 or len(hypothesis.evidence_refs) > 0
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.orchestration.schemas import (
    ScoutHypothesis,
    ScoutStatus,
    UnknownItem,
    UnknownReason,
)


# =============================================================================
# Enums and Constants
# =============================================================================


class NearMissType(str, Enum):
    """Types of near-miss discoveries."""

    MISSING_ONE_OP = "missing_one_op"  # Has all ops except one required
    EXTRA_GUARD = "extra_guard"  # Would match but has guard
    WRONG_ORDER = "wrong_order"  # Has ops but wrong ordering
    PARTIAL_SIGNATURE = "partial_signature"  # Partial behavioral signature match


class MutationType(str, Enum):
    """Types of pattern mutations."""

    OP_SUBSTITUTION = "op_substitution"  # Replace one op with related op
    ORDER_SWAP = "order_swap"  # Swap ordering of two ops
    OP_DELETION = "op_deletion"  # Remove optional op
    OP_ADDITION = "op_addition"  # Add related op


class CounterfactualType(str, Enum):
    """Types of counterfactual probes."""

    GUARD_REMOVED = "guard_removed"  # What if guard didn't exist
    OP_PRESENT = "op_present"  # What if missing op was present
    ORDER_CHANGED = "order_changed"  # What if order was different
    CONTEXT_ADDED = "context_added"  # What if protocol context was present


class ShadowPatternStatus(str, Enum):
    """Status of shadow pattern proposals."""

    PROPOSAL = "proposal"  # Initial proposal
    VALIDATED = "validated"  # Has supporting evidence
    REJECTED = "rejected"  # Insufficient evidence


# Default operation relationships for mutation
OP_RELATIONSHIPS = {
    "TRANSFERS_VALUE_OUT": ["RECEIVES_VALUE_IN", "WRITES_USER_BALANCE"],
    "WRITES_USER_BALANCE": ["READS_USER_BALANCE", "MODIFIES_CRITICAL_STATE"],
    "CHECKS_PERMISSION": ["MODIFIES_OWNER", "MODIFIES_ROLES"],
    "CALLS_EXTERNAL": ["CALLS_UNTRUSTED", "READS_EXTERNAL_VALUE"],
    "READS_ORACLE": ["READS_EXTERNAL_VALUE", "USES_BLOCK_DATA"],
}

# Max confidence for Tier-B discoveries
TIER_B_MAX_CONFIDENCE = 0.70


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class NearMissResult:
    """Result from near-miss mining.

    A near-miss is a function that almost matches a pattern but is missing
    one required element (op, ordering, guard absence).

    Attributes:
        node_id: ID of the near-miss node
        pattern_id: Pattern it almost matches
        near_miss_type: Type of near-miss
        missing_element: What's missing to complete the match
        present_elements: Elements that are present
        evidence_refs: Evidence supporting this near-miss
        confidence: Confidence score (max 0.70)
        is_unknown: Whether this is marked as unknown
        unknown_reason: Reason if marked unknown
    """

    node_id: str
    pattern_id: str
    near_miss_type: NearMissType
    missing_element: str
    present_elements: List[str]
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 0.40  # Lower default for near-miss
    is_unknown: bool = True
    unknown_reason: Optional[UnknownReason] = UnknownReason.MISSING_EVIDENCE

    def __post_init__(self) -> None:
        """Validate confidence cap."""
        if self.confidence > TIER_B_MAX_CONFIDENCE:
            self.confidence = TIER_B_MAX_CONFIDENCE
        # Mark as unknown if no evidence
        if not self.evidence_refs:
            self.is_unknown = True
            if self.unknown_reason is None:
                self.unknown_reason = UnknownReason.MISSING_EVIDENCE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "pattern_id": self.pattern_id,
            "near_miss_type": self.near_miss_type.value,
            "missing_element": self.missing_element,
            "present_elements": self.present_elements,
            "evidence_refs": self.evidence_refs,
            "confidence": round(self.confidence, 4),
            "is_unknown": self.is_unknown,
            "unknown_reason": self.unknown_reason.value if self.unknown_reason else None,
        }


@dataclass
class MutationResult:
    """Result from pattern mutation exploration.

    A mutation is a variant of a pattern with modified operations or ordering.

    Attributes:
        base_pattern_id: Original pattern being mutated
        mutation_type: Type of mutation applied
        mutation_description: Human-readable description
        affected_ops: Operations affected by mutation
        matching_nodes: Nodes that match the mutated pattern
        evidence_refs: Evidence supporting this mutation
        confidence: Confidence score (max 0.70)
        is_unknown: Whether this is marked as unknown
    """

    base_pattern_id: str
    mutation_type: MutationType
    mutation_description: str
    affected_ops: List[str]
    matching_nodes: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 0.35  # Lower default for mutations
    is_unknown: bool = True

    def __post_init__(self) -> None:
        """Validate confidence cap."""
        if self.confidence > TIER_B_MAX_CONFIDENCE:
            self.confidence = TIER_B_MAX_CONFIDENCE
        if not self.evidence_refs:
            self.is_unknown = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "base_pattern_id": self.base_pattern_id,
            "mutation_type": self.mutation_type.value,
            "mutation_description": self.mutation_description,
            "affected_ops": self.affected_ops,
            "matching_nodes": self.matching_nodes,
            "evidence_refs": self.evidence_refs,
            "confidence": round(self.confidence, 4),
            "is_unknown": self.is_unknown,
        }


@dataclass
class CounterfactualProbe:
    """Result from counterfactual probing.

    A counterfactual probe explores "what if" scenarios using PCP counterfactuals.
    Per PCP v2 spec, counterfactuals track guard removal scenarios.

    Attributes:
        probe_id: Unique probe identifier
        pattern_id: Pattern being probed
        counterfactual_type: Type of counterfactual
        removed_element: Element removed in the counterfactual
        becomes_vulnerable: Whether pattern would hold if removed
        affected_nodes: Nodes affected by this counterfactual
        evidence_refs: Evidence supporting this probe
        confidence: Confidence score (max 0.70, cannot upgrade)
        notes: Additional notes about the probe
    """

    probe_id: str
    pattern_id: str
    counterfactual_type: CounterfactualType
    removed_element: str
    becomes_vulnerable: bool
    affected_nodes: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    confidence: float = 0.30  # Lower for counterfactuals - they're hypothetical
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate confidence cap - counterfactuals cannot upgrade confidence."""
        # Per PCONTEXT-09: Counterfactuals do not upgrade confidence
        if self.confidence > 0.50:
            self.confidence = 0.50  # Extra conservative for counterfactuals

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "probe_id": self.probe_id,
            "pattern_id": self.pattern_id,
            "counterfactual_type": self.counterfactual_type.value,
            "removed_element": self.removed_element,
            "becomes_vulnerable": self.becomes_vulnerable,
            "affected_nodes": self.affected_nodes,
            "evidence_refs": self.evidence_refs,
            "confidence": round(self.confidence, 4),
            "notes": self.notes,
        }


@dataclass
class AnomalyMotif:
    """Anomaly motif from statistical analysis.

    An anomaly motif is a statistically unusual combination of operations
    that may indicate a novel vulnerability pattern.

    Attributes:
        motif_id: Unique motif identifier
        operations: Operations in the motif
        occurrence_count: How many times this motif occurs
        expected_count: Expected count based on distribution
        z_score: Statistical deviation score
        example_nodes: Example nodes exhibiting this motif
        evidence_refs: Evidence supporting this motif
        is_unknown: Always true for anomalies
    """

    motif_id: str
    operations: List[str]
    occurrence_count: int
    expected_count: float
    z_score: float
    example_nodes: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    is_unknown: bool = True  # Anomalies are always unknown

    def __post_init__(self) -> None:
        """Enforce that anomalies are always unknown."""
        # Anomalies are always unknown - they're statistical observations
        self.is_unknown = True

    @property
    def confidence(self) -> float:
        """Calculate confidence from z-score (capped at 0.70)."""
        # Higher z-score = more anomalous = potentially interesting
        # But still capped at Tier-B max
        raw_conf = min(abs(self.z_score) / 5.0, 0.70)
        return round(raw_conf, 4)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "motif_id": self.motif_id,
            "operations": self.operations,
            "occurrence_count": self.occurrence_count,
            "expected_count": round(self.expected_count, 2),
            "z_score": round(self.z_score, 4),
            "example_nodes": self.example_nodes,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "is_unknown": self.is_unknown,
        }


@dataclass
class ShadowPattern:
    """Shadow pattern proposal from near-miss clustering.

    A shadow pattern is a novel pattern proposal derived from clustering
    near-misses and anomaly motifs. Always flagged as proposals.

    Attributes:
        shadow_id: Unique shadow pattern identifier
        name: Proposed pattern name
        description: Pattern description
        derived_from: Source near-misses and anomalies
        required_ops: Proposed required operations
        ordering: Proposed ordering constraints
        example_nodes: Example nodes matching this shadow
        evidence_refs: Evidence supporting this shadow
        status: Always PROPOSAL for shadow patterns
        confidence: Always low for shadow patterns
    """

    shadow_id: str
    name: str
    description: str
    derived_from: List[str]  # near-miss IDs or anomaly IDs
    required_ops: List[str]
    ordering: List[Tuple[str, str]] = field(default_factory=list)  # (before, after) pairs
    example_nodes: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    status: ShadowPatternStatus = ShadowPatternStatus.PROPOSAL
    confidence: float = 0.25  # Very low for proposals

    def __post_init__(self) -> None:
        """Validate shadow pattern constraints."""
        # Shadow patterns are always proposals
        if self.status != ShadowPatternStatus.PROPOSAL:
            self.status = ShadowPatternStatus.PROPOSAL
        # Confidence always low
        if self.confidence > 0.40:
            self.confidence = 0.40

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "shadow_id": self.shadow_id,
            "name": self.name,
            "description": self.description,
            "derived_from": self.derived_from,
            "required_ops": self.required_ops,
            "ordering": [[b, a] for b, a in self.ordering],
            "example_nodes": self.example_nodes,
            "evidence_refs": self.evidence_refs,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class CreativeDiscoveryConfig:
    """Configuration for creative discovery loop.

    Attributes:
        max_near_misses: Maximum near-misses to return
        max_mutations: Maximum mutations to explore per pattern
        max_counterfactuals: Maximum counterfactual probes
        max_anomalies: Maximum anomaly motifs to return
        enable_shadow_patterns: Whether to generate shadow patterns
        min_anomaly_z_score: Minimum z-score to flag as anomaly
        budget_check_interval: How often to check budget
    """

    max_near_misses: int = 10
    max_mutations: int = 5
    max_counterfactuals: int = 10
    max_anomalies: int = 5
    enable_shadow_patterns: bool = True
    min_anomaly_z_score: float = 2.0
    budget_check_interval: int = 10


@dataclass
class CreativeDiscoveryResult:
    """Complete results from creative discovery.

    Attributes:
        near_misses: Near-miss discoveries
        mutations: Pattern mutation results
        counterfactuals: Counterfactual probe results
        anomalies: Anomaly motifs discovered
        shadow_patterns: Shadow pattern proposals
        hypotheses: Aggregated Tier-B hypotheses
        budget_exhausted: Whether budget was exhausted
        budget_remaining: Remaining budget after discovery
        timestamp: When discovery completed
    """

    near_misses: List[NearMissResult] = field(default_factory=list)
    mutations: List[MutationResult] = field(default_factory=list)
    counterfactuals: List[CounterfactualProbe] = field(default_factory=list)
    anomalies: List[AnomalyMotif] = field(default_factory=list)
    shadow_patterns: List[ShadowPattern] = field(default_factory=list)
    hypotheses: List[ScoutHypothesis] = field(default_factory=list)
    budget_exhausted: bool = False
    budget_remaining: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "near_misses": [nm.to_dict() for nm in self.near_misses],
            "mutations": [m.to_dict() for m in self.mutations],
            "counterfactuals": [cf.to_dict() for cf in self.counterfactuals],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "shadow_patterns": [sp.to_dict() for sp in self.shadow_patterns],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "budget_exhausted": self.budget_exhausted,
            "budget_remaining": self.budget_remaining,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# Near-Miss Mining
# =============================================================================


class NearMissMiner:
    """Mine near-miss candidates from graph.

    Near-miss mining finds functions that are close to matching a pattern
    but missing one required element.

    Per PCONTEXT-09: Near-miss outputs are Tier-B and marked unknown.
    """

    def __init__(self, config: Optional[CreativeDiscoveryConfig] = None):
        """Initialize near-miss miner.

        Args:
            config: Optional configuration
        """
        self.config = config or CreativeDiscoveryConfig()

    def mine_near_misses(
        self,
        nodes: Dict[str, Any],
        pattern_required_ops: Dict[str, List[str]],
        pattern_orderings: Dict[str, List[Tuple[str, str]]],
    ) -> List[NearMissResult]:
        """Mine near-miss candidates.

        Args:
            nodes: Dict of node_id -> node data (with semantic_ops, op_ordering)
            pattern_required_ops: Dict of pattern_id -> required ops
            pattern_orderings: Dict of pattern_id -> required orderings

        Returns:
            List of NearMissResult, capped at config.max_near_misses
        """
        near_misses: List[NearMissResult] = []

        for node_id, node in nodes.items():
            if node.get("type") != "Function":
                continue

            semantic_ops = set(node.get("semantic_ops", []) or [])
            op_ordering = node.get("op_ordering", []) or []

            for pattern_id, required_ops in pattern_required_ops.items():
                required_set = set(required_ops)

                # Check for missing one op
                missing = required_set - semantic_ops
                present = required_set & semantic_ops

                if len(missing) == 1 and len(present) >= 1:
                    # Near-miss: missing exactly one required op
                    near_miss = NearMissResult(
                        node_id=node_id,
                        pattern_id=pattern_id,
                        near_miss_type=NearMissType.MISSING_ONE_OP,
                        missing_element=list(missing)[0],
                        present_elements=sorted(present),
                        evidence_refs=[f"node:{node_id}"],
                        confidence=0.45,
                        is_unknown=True,
                        unknown_reason=UnknownReason.MISSING_EVIDENCE,
                    )
                    near_misses.append(near_miss)

                # Check for wrong ordering
                if pattern_id in pattern_orderings and len(missing) == 0:
                    required_order = pattern_orderings[pattern_id]
                    for before_op, after_op in required_order:
                        # Check if ordering is violated
                        has_correct_order = any(
                            pair[0] == before_op and pair[1] == after_op
                            for pair in op_ordering
                        )
                        has_wrong_order = any(
                            pair[0] == after_op and pair[1] == before_op
                            for pair in op_ordering
                        )
                        if has_wrong_order and not has_correct_order:
                            near_miss = NearMissResult(
                                node_id=node_id,
                                pattern_id=pattern_id,
                                near_miss_type=NearMissType.WRONG_ORDER,
                                missing_element=f"{before_op} before {after_op}",
                                present_elements=sorted(present),
                                evidence_refs=[f"node:{node_id}"],
                                confidence=0.40,
                                is_unknown=True,
                                unknown_reason=UnknownReason.MISSING_EVIDENCE,
                            )
                            near_misses.append(near_miss)

                if len(near_misses) >= self.config.max_near_misses:
                    break

            if len(near_misses) >= self.config.max_near_misses:
                break

        return near_misses[: self.config.max_near_misses]


# =============================================================================
# Pattern Mutation
# =============================================================================


class PatternMutator:
    """Generate pattern mutations for exploratory analysis.

    Pattern mutation creates variants of patterns with modified operations
    or ordering to explore nearby vulnerability space.

    Per PCONTEXT-09: Mutations are deterministic and Tier-B.
    """

    def __init__(
        self,
        op_relationships: Optional[Dict[str, List[str]]] = None,
        config: Optional[CreativeDiscoveryConfig] = None,
    ):
        """Initialize pattern mutator.

        Args:
            op_relationships: Dict of op -> related ops for substitution
            config: Optional configuration
        """
        self.op_relationships = op_relationships or OP_RELATIONSHIPS
        self.config = config or CreativeDiscoveryConfig()

    def generate_mutations(
        self,
        pattern_id: str,
        required_ops: List[str],
        ordering: List[Tuple[str, str]],
        nodes: Dict[str, Any],
    ) -> List[MutationResult]:
        """Generate pattern mutations.

        Args:
            pattern_id: Pattern to mutate
            required_ops: Required operations
            ordering: Required ordering constraints
            nodes: Graph nodes to test against

        Returns:
            List of MutationResult, capped at config.max_mutations
        """
        mutations: List[MutationResult] = []

        # Op substitution mutations
        for op in required_ops:
            related = self.op_relationships.get(op, [])
            for substitute in related:
                mutated_ops = [substitute if o == op else o for o in required_ops]
                matching = self._find_matching_nodes(mutated_ops, nodes)

                if matching:
                    mutation = MutationResult(
                        base_pattern_id=pattern_id,
                        mutation_type=MutationType.OP_SUBSTITUTION,
                        mutation_description=f"Replace {op} with {substitute}",
                        affected_ops=[op, substitute],
                        matching_nodes=matching[:5],  # Limit examples
                        evidence_refs=[f"node:{n}" for n in matching[:3]],
                        confidence=0.35 if matching else 0.20,
                        is_unknown=True,
                    )
                    mutations.append(mutation)

                if len(mutations) >= self.config.max_mutations:
                    return mutations

        # Order swap mutations
        if len(ordering) >= 1:
            for i, (before, after) in enumerate(ordering):
                # Try swapping order
                swapped_ordering = ordering.copy()
                swapped_ordering[i] = (after, before)
                matching = self._find_matching_order(swapped_ordering, nodes)

                if matching:
                    mutation = MutationResult(
                        base_pattern_id=pattern_id,
                        mutation_type=MutationType.ORDER_SWAP,
                        mutation_description=f"Swap {before} and {after} order",
                        affected_ops=[before, after],
                        matching_nodes=matching[:5],
                        evidence_refs=[f"node:{n}" for n in matching[:3]],
                        confidence=0.30,
                        is_unknown=True,
                    )
                    mutations.append(mutation)

                if len(mutations) >= self.config.max_mutations:
                    return mutations

        return mutations

    def _find_matching_nodes(
        self,
        required_ops: List[str],
        nodes: Dict[str, Any],
    ) -> List[str]:
        """Find nodes matching required ops."""
        matching = []
        required_set = set(required_ops)

        for node_id, node in nodes.items():
            if node.get("type") != "Function":
                continue
            semantic_ops = set(node.get("semantic_ops", []) or [])
            if required_set.issubset(semantic_ops):
                matching.append(node_id)

        return matching

    def _find_matching_order(
        self,
        ordering: List[Tuple[str, str]],
        nodes: Dict[str, Any],
    ) -> List[str]:
        """Find nodes matching ordering constraints."""
        matching = []

        for node_id, node in nodes.items():
            if node.get("type") != "Function":
                continue
            op_order = node.get("op_ordering", []) or []

            all_match = True
            for before, after in ordering:
                has_order = any(
                    pair[0] == before and pair[1] == after for pair in op_order
                )
                if not has_order:
                    all_match = False
                    break

            if all_match:
                matching.append(node_id)

        return matching


# =============================================================================
# Counterfactual Probes
# =============================================================================


class CounterfactualProber:
    """Probe counterfactual scenarios from PCP v2.

    Counterfactual probes explore "what if" scenarios, particularly
    around guard removal as defined in PCP v2 counterfactuals.

    Per PCONTEXT-09: Counterfactuals do not upgrade confidence.
    """

    def __init__(self, config: Optional[CreativeDiscoveryConfig] = None):
        """Initialize counterfactual prober.

        Args:
            config: Optional configuration
        """
        self.config = config or CreativeDiscoveryConfig()
        self._probe_counter = 0

    def probe_counterfactuals(
        self,
        pattern_id: str,
        pcp_counterfactuals: List[Dict[str, Any]],
        anti_signals: List[Dict[str, Any]],
        guarded_nodes: Dict[str, List[str]],  # node_id -> guard_types
    ) -> List[CounterfactualProbe]:
        """Generate counterfactual probes from PCP.

        Args:
            pattern_id: Pattern being probed
            pcp_counterfactuals: PCP counterfactuals list
            anti_signals: PCP anti-signals list
            guarded_nodes: Map of node_id -> guard types present

        Returns:
            List of CounterfactualProbe, capped at config.max_counterfactuals
        """
        probes: List[CounterfactualProbe] = []

        # Process PCP counterfactuals
        for cf in pcp_counterfactuals:
            cf_id = cf.get("id", f"cf-{self._probe_counter}")
            self._probe_counter += 1

            if_removed = cf.get("if_removed", "")
            becomes_true = cf.get("becomes_true", False)
            notes = cf.get("notes", "")

            # Find affected nodes (those with this guard)
            affected = []
            for node_id, guards in guarded_nodes.items():
                # Check if this guard type matches the counterfactual
                for guard in guards:
                    if if_removed in guard or guard in if_removed:
                        affected.append(node_id)
                        break

            probe = CounterfactualProbe(
                probe_id=cf_id,
                pattern_id=pattern_id,
                counterfactual_type=CounterfactualType.GUARD_REMOVED,
                removed_element=if_removed,
                becomes_vulnerable=becomes_true,
                affected_nodes=affected[:10],
                evidence_refs=[f"node:{n}" for n in affected[:3]] if affected else [],
                confidence=0.30,  # Counterfactuals are hypothetical
                notes=notes,
            )
            probes.append(probe)

            if len(probes) >= self.config.max_counterfactuals:
                break

        # Also probe anti-signals as counterfactuals
        for anti in anti_signals:
            if len(probes) >= self.config.max_counterfactuals:
                break

            guard_id = anti.get("id", "")
            guard_type = anti.get("guard_type", "")
            bypass_notes = anti.get("bypass_notes", [])

            affected = []
            for node_id, guards in guarded_nodes.items():
                if guard_type in guards:
                    affected.append(node_id)

            if affected:
                probe = CounterfactualProbe(
                    probe_id=f"anti-{guard_id}",
                    pattern_id=pattern_id,
                    counterfactual_type=CounterfactualType.GUARD_REMOVED,
                    removed_element=guard_type,
                    becomes_vulnerable=True,
                    affected_nodes=affected[:10],
                    evidence_refs=[f"node:{n}" for n in affected[:3]],
                    confidence=0.25,
                    notes="; ".join(bypass_notes) if bypass_notes else "",
                )
                probes.append(probe)

        return probes[: self.config.max_counterfactuals]


# =============================================================================
# Anomaly Motif Detection
# =============================================================================


class AnomalyDetector:
    """Detect anomaly motifs in operation distribution.

    Anomaly motifs are statistically unusual combinations of operations
    that may indicate novel vulnerability patterns.

    Per PCONTEXT-09: Anomalies are always marked as unknown.
    """

    def __init__(self, config: Optional[CreativeDiscoveryConfig] = None):
        """Initialize anomaly detector.

        Args:
            config: Optional configuration
        """
        self.config = config or CreativeDiscoveryConfig()

    def detect_anomalies(
        self,
        nodes: Dict[str, Any],
    ) -> List[AnomalyMotif]:
        """Detect anomaly motifs in node operations.

        Uses simple frequency analysis to find unusual op combinations.

        Args:
            nodes: Graph nodes

        Returns:
            List of AnomalyMotif, capped at config.max_anomalies
        """
        # Count op pair co-occurrences
        pair_counts: Dict[Tuple[str, str], int] = {}
        op_counts: Dict[str, int] = {}
        total_functions = 0

        for node_id, node in nodes.items():
            if node.get("type") != "Function":
                continue

            semantic_ops = sorted(node.get("semantic_ops", []) or [])
            if not semantic_ops:
                continue

            total_functions += 1

            for op in semantic_ops:
                op_counts[op] = op_counts.get(op, 0) + 1

            # Count pairs
            for i, op1 in enumerate(semantic_ops):
                for op2 in semantic_ops[i + 1 :]:
                    pair = (op1, op2)
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

        if total_functions < 5:
            return []  # Not enough data for statistics

        # Calculate expected counts and z-scores
        anomalies: List[AnomalyMotif] = []

        for pair, count in pair_counts.items():
            op1, op2 = pair
            # Expected count based on independent occurrence
            p1 = op_counts.get(op1, 0) / total_functions
            p2 = op_counts.get(op2, 0) / total_functions
            expected = p1 * p2 * total_functions

            if expected < 0.5:
                continue  # Skip very rare pairs

            # Simple z-score approximation
            # Assuming binomial distribution
            std_dev = (expected * (1 - expected / total_functions)) ** 0.5
            if std_dev < 0.1:
                continue

            z_score = (count - expected) / std_dev

            if abs(z_score) >= self.config.min_anomaly_z_score:
                # Find example nodes
                examples = []
                for node_id, node in nodes.items():
                    if node.get("type") != "Function":
                        continue
                    ops = set(node.get("semantic_ops", []) or [])
                    if op1 in ops and op2 in ops:
                        examples.append(node_id)
                        if len(examples) >= 3:
                            break

                motif_id = f"motif-{hashlib.sha256(f'{op1}:{op2}'.encode()).hexdigest()[:8]}"
                anomaly = AnomalyMotif(
                    motif_id=motif_id,
                    operations=[op1, op2],
                    occurrence_count=count,
                    expected_count=expected,
                    z_score=z_score,
                    example_nodes=examples,
                    evidence_refs=[f"node:{n}" for n in examples],
                    is_unknown=True,
                )
                anomalies.append(anomaly)

        # Sort by absolute z-score descending
        anomalies.sort(key=lambda a: abs(a.z_score), reverse=True)

        return anomalies[: self.config.max_anomalies]


# =============================================================================
# Shadow Pattern Generation
# =============================================================================


class ShadowPatternGenerator:
    """Generate shadow pattern proposals from near-misses and anomalies.

    Shadow patterns are novel pattern proposals derived from clustering
    similar near-misses and anomaly motifs.

    Per PCONTEXT-09: Shadow patterns are always flagged as proposals.
    """

    def __init__(self, config: Optional[CreativeDiscoveryConfig] = None):
        """Initialize shadow pattern generator.

        Args:
            config: Optional configuration
        """
        self.config = config or CreativeDiscoveryConfig()

    def generate_shadow_patterns(
        self,
        near_misses: List[NearMissResult],
        anomalies: List[AnomalyMotif],
    ) -> List[ShadowPattern]:
        """Generate shadow pattern proposals.

        Args:
            near_misses: Near-miss results to cluster
            anomalies: Anomaly motifs to consider

        Returns:
            List of ShadowPattern proposals
        """
        if not self.config.enable_shadow_patterns:
            return []

        shadows: List[ShadowPattern] = []

        # Group near-misses by missing element type
        missing_groups: Dict[str, List[NearMissResult]] = {}
        for nm in near_misses:
            if nm.near_miss_type == NearMissType.MISSING_ONE_OP:
                key = nm.missing_element
                if key not in missing_groups:
                    missing_groups[key] = []
                missing_groups[key].append(nm)

        # Create shadow patterns from clusters of 2+ near-misses
        for missing_op, group in missing_groups.items():
            if len(group) < 2:
                continue

            # Find common present elements
            common_present = set(group[0].present_elements)
            for nm in group[1:]:
                common_present &= set(nm.present_elements)

            if len(common_present) >= 1:
                shadow_id = f"shadow-{hashlib.sha256(f'{missing_op}:{sorted(common_present)}'.encode()).hexdigest()[:8]}"

                # Propose a pattern without the missing op
                shadow = ShadowPattern(
                    shadow_id=shadow_id,
                    name=f"Shadow pattern without {missing_op}",
                    description=f"Functions with {sorted(common_present)} but missing {missing_op} - potential variant vulnerability",
                    derived_from=[nm.node_id for nm in group[:5]],
                    required_ops=sorted(common_present),
                    example_nodes=[nm.node_id for nm in group[:5]],
                    evidence_refs=[f"node:{nm.node_id}" for nm in group[:3]],
                    status=ShadowPatternStatus.PROPOSAL,
                    confidence=0.25,
                )
                shadows.append(shadow)

        # Create shadow patterns from high-z-score anomalies
        for anomaly in anomalies:
            if anomaly.z_score > 3.0:  # Strong anomaly
                shadow_id = f"shadow-anom-{anomaly.motif_id}"
                shadow = ShadowPattern(
                    shadow_id=shadow_id,
                    name=f"Anomalous {'+'.join(anomaly.operations)} pattern",
                    description=f"Statistically unusual co-occurrence of {anomaly.operations} (z={anomaly.z_score:.2f})",
                    derived_from=[anomaly.motif_id],
                    required_ops=anomaly.operations,
                    example_nodes=anomaly.example_nodes,
                    evidence_refs=anomaly.evidence_refs,
                    status=ShadowPatternStatus.PROPOSAL,
                    confidence=0.20,
                )
                shadows.append(shadow)

        return shadows[:5]  # Limit shadow patterns


# =============================================================================
# Main Creative Discovery Loop
# =============================================================================


class CreativeDiscoveryLoop:
    """Creative discovery loop for Tier-B hypotheses.

    Per PCONTEXT-09:
    - Creative loop outputs remain Tier-B
    - Near-miss, mutation, and counterfactual probes are deterministic
    - All outputs marked unknown unless evidenced
    - Budget-aware with halt at ceiling

    Inputs: PCP v2 + slice + protocol context (if gated) + budget
    Steps: near-miss mining -> ordered/mutated variants -> counterfactual probes -> anomaly motifs
    Outputs: Tier-B hypotheses only; confidence cannot exceed evidence-gated thresholds

    Usage:
        loop = CreativeDiscoveryLoop(config=CreativeDiscoveryConfig())
        results = loop.discover(
            graph=knowledge_graph,
            patterns=pattern_definitions,
            pcp=pattern_context_pack,
            budget_remaining=2000,
        )
    """

    def __init__(self, config: Optional[CreativeDiscoveryConfig] = None):
        """Initialize creative discovery loop.

        Args:
            config: Optional configuration
        """
        self.config = config or CreativeDiscoveryConfig()

        # Initialize sub-components
        self.near_miss_miner = NearMissMiner(config=self.config)
        self.pattern_mutator = PatternMutator(config=self.config)
        self.counterfactual_prober = CounterfactualProber(config=self.config)
        self.anomaly_detector = AnomalyDetector(config=self.config)
        self.shadow_generator = ShadowPatternGenerator(config=self.config)

    def discover(
        self,
        nodes: Dict[str, Any],
        pattern_required_ops: Dict[str, List[str]],
        pattern_orderings: Dict[str, List[Tuple[str, str]]],
        pcp_counterfactuals: Optional[List[Dict[str, Any]]] = None,
        pcp_anti_signals: Optional[List[Dict[str, Any]]] = None,
        guarded_nodes: Optional[Dict[str, List[str]]] = None,
        budget_remaining: int = 2000,
    ) -> CreativeDiscoveryResult:
        """Run creative discovery loop.

        Args:
            nodes: Graph nodes as dict
            pattern_required_ops: Pattern ID -> required ops
            pattern_orderings: Pattern ID -> ordering constraints
            pcp_counterfactuals: PCP counterfactuals (optional)
            pcp_anti_signals: PCP anti-signals (optional)
            guarded_nodes: Node ID -> guard types present
            budget_remaining: Token budget remaining

        Returns:
            CreativeDiscoveryResult with all discoveries
        """
        result = CreativeDiscoveryResult()
        budget = budget_remaining

        # Step 1: Near-miss mining
        if budget > 100:
            result.near_misses = self.near_miss_miner.mine_near_misses(
                nodes=nodes,
                pattern_required_ops=pattern_required_ops,
                pattern_orderings=pattern_orderings,
            )
            budget -= len(result.near_misses) * 10  # Cost estimate

        # Step 2: Pattern mutations
        if budget > 100:
            for pattern_id, required_ops in list(pattern_required_ops.items())[:3]:
                ordering = pattern_orderings.get(pattern_id, [])
                mutations = self.pattern_mutator.generate_mutations(
                    pattern_id=pattern_id,
                    required_ops=required_ops,
                    ordering=ordering,
                    nodes=nodes,
                )
                result.mutations.extend(mutations)
                budget -= len(mutations) * 15
                if budget <= 0:
                    break

        # Step 3: Counterfactual probes
        if budget > 100 and pcp_counterfactuals:
            for pattern_id in list(pattern_required_ops.keys())[:3]:
                probes = self.counterfactual_prober.probe_counterfactuals(
                    pattern_id=pattern_id,
                    pcp_counterfactuals=pcp_counterfactuals or [],
                    anti_signals=pcp_anti_signals or [],
                    guarded_nodes=guarded_nodes or {},
                )
                result.counterfactuals.extend(probes)
                budget -= len(probes) * 10
                if budget <= 0:
                    break

        # Step 4: Anomaly motif detection
        if budget > 50:
            result.anomalies = self.anomaly_detector.detect_anomalies(nodes)
            budget -= len(result.anomalies) * 20

        # Step 5: Shadow pattern generation
        if budget > 50 and self.config.enable_shadow_patterns:
            result.shadow_patterns = self.shadow_generator.generate_shadow_patterns(
                near_misses=result.near_misses,
                anomalies=result.anomalies,
            )
            budget -= len(result.shadow_patterns) * 30

        # Generate aggregated hypotheses
        result.hypotheses = self._generate_hypotheses(result)

        result.budget_exhausted = budget <= 0
        result.budget_remaining = max(0, budget)

        return result

    def _generate_hypotheses(
        self,
        result: CreativeDiscoveryResult,
    ) -> List[ScoutHypothesis]:
        """Generate ScoutHypothesis objects from discoveries.

        All hypotheses are Tier-B with explicit unknown handling.

        Args:
            result: Creative discovery result so far

        Returns:
            List of ScoutHypothesis (Tier-B)
        """
        hypotheses: List[ScoutHypothesis] = []

        # Near-miss hypotheses
        for nm in result.near_misses:
            try:
                hypothesis = ScoutHypothesis(
                    pattern_id=f"near-miss:{nm.pattern_id}",
                    status=ScoutStatus.UNKNOWN,  # Near-misses are always unknown
                    evidence_refs=nm.evidence_refs if nm.evidence_refs else ["EVD-pending"],
                    unknowns=[UnknownItem(field=nm.missing_element, reason=nm.unknown_reason or UnknownReason.MISSING_EVIDENCE)],
                    confidence=nm.confidence,
                    notes=f"Near-miss ({nm.near_miss_type.value}): missing {nm.missing_element}",
                )
                hypotheses.append(hypothesis)
            except ValueError:
                # Invalid hypothesis (e.g., invalid evidence format)
                pass

        # Mutation hypotheses
        for mut in result.mutations:
            if mut.matching_nodes:
                try:
                    hypothesis = ScoutHypothesis(
                        pattern_id=f"mutation:{mut.base_pattern_id}",
                        status=ScoutStatus.UNKNOWN,  # Mutations are always unknown
                        evidence_refs=mut.evidence_refs if mut.evidence_refs else ["EVD-pending"],
                        unknowns=[UnknownItem(field="mutation_validation", reason=UnknownReason.REQUIRES_EXPANSION)],
                        confidence=mut.confidence,
                        notes=f"Mutation ({mut.mutation_type.value}): {mut.mutation_description}",
                    )
                    hypotheses.append(hypothesis)
                except ValueError:
                    pass

        # Shadow pattern hypotheses
        for sp in result.shadow_patterns:
            try:
                hypothesis = ScoutHypothesis(
                    pattern_id=f"shadow:{sp.shadow_id}",
                    status=ScoutStatus.UNKNOWN,  # Shadows are proposals
                    evidence_refs=sp.evidence_refs if sp.evidence_refs else ["EVD-pending"],
                    unknowns=[UnknownItem(field="pattern_validation", reason=UnknownReason.REQUIRES_EXPANSION)],
                    confidence=sp.confidence,
                    notes=f"Shadow pattern proposal: {sp.name}",
                )
                hypotheses.append(hypothesis)
            except ValueError:
                pass

        return hypotheses


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "NearMissType",
    "MutationType",
    "CounterfactualType",
    "ShadowPatternStatus",
    # Data structures
    "NearMissResult",
    "MutationResult",
    "CounterfactualProbe",
    "AnomalyMotif",
    "ShadowPattern",
    "CreativeDiscoveryConfig",
    "CreativeDiscoveryResult",
    # Miners/Detectors
    "NearMissMiner",
    "PatternMutator",
    "CounterfactualProber",
    "AnomalyDetector",
    "ShadowPatternGenerator",
    # Main loop
    "CreativeDiscoveryLoop",
    # Constants
    "OP_RELATIONSHIPS",
    "TIER_B_MAX_CONFIDENCE",
]
