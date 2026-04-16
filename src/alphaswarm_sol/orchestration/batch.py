"""Batch Discovery Orchestration v2.

This module implements batch discovery with:
- Adaptive batching by pattern cost/complexity
- Prefix cache versioning (graph hash + PCP version + budget policy)
- Fork-then-rank: multiple scouts propose, verifier ranks, contradiction can veto

Per PCONTEXT-07:
- Batch orchestration groups by cost/complexity
- Prefix cache keyed by graph hash + PCP version
- Fork-then-rank produces deterministic winners

Design Principles:
1. Batch outputs are append-only and deterministic
2. Cache keys include all inputs affecting output (graph + PCP + budget)
3. Fork-then-rank uses majority + confidence for ranking
4. Contradiction veto requires strong evidence (confidence > 0.7)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.agents.context.types import BudgetPolicy, BudgetPass
from alphaswarm_sol.orchestration.schemas import (
    DiversityPolicy,
    DiversityPath,
    DiversityPathType,
    ScoutHypothesis,
    ScoutStatus,
    VerificationResult,
    VerificationStatus,
    ContradictionReport,
    ContradictionStatus,
    UnknownItem,
)


# =============================================================================
# Enums and Constants
# =============================================================================


class BatchPriority(str, Enum):
    """Priority levels for batch processing."""

    CRITICAL = "critical"  # High-severity patterns, process first
    HIGH = "high"  # Complex patterns, second priority
    MEDIUM = "medium"  # Standard patterns
    LOW = "low"  # Simple patterns, last priority


class RankingMethod(str, Enum):
    """Methods for ranking fork results."""

    MAJORITY_VOTE = "majority_vote"  # Simple majority of scout hypotheses
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weight by confidence scores
    EVIDENCE_COUNT = "evidence_count"  # Rank by evidence quantity
    HYBRID = "hybrid"  # Combine multiple methods


# Default cost weights for pattern complexity estimation
DEFAULT_COST_WEIGHTS = {
    "tier_a": 1.0,  # Tier A patterns are cheapest (deterministic)
    "tier_b": 2.5,  # Tier B requires LLM verification
    "tier_c": 3.5,  # Tier C requires label-dependent checks
    "multi_hop": 1.5,  # Multi-hop analysis multiplier
    "cross_contract": 2.0,  # Cross-contract analysis multiplier
}


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class PatternCostEstimate:
    """Estimated cost for analyzing a pattern.

    Attributes:
        pattern_id: Pattern identifier
        base_cost: Base token cost estimate
        complexity_multiplier: Multiplier based on pattern complexity
        estimated_tokens: Final estimated tokens (base * multiplier)
        tier: Pattern tier (A, B, C)
        requires_context: Whether protocol context is required
    """

    pattern_id: str
    base_cost: int
    complexity_multiplier: float
    estimated_tokens: int
    tier: str = "B"
    requires_context: bool = False

    def __post_init__(self) -> None:
        """Calculate estimated tokens if not provided."""
        if self.estimated_tokens == 0:
            self.estimated_tokens = int(self.base_cost * self.complexity_multiplier)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "base_cost": self.base_cost,
            "complexity_multiplier": self.complexity_multiplier,
            "estimated_tokens": self.estimated_tokens,
            "tier": self.tier,
            "requires_context": self.requires_context,
        }


@dataclass
class AdaptiveBatch:
    """A batch of patterns grouped by cost/complexity.

    Attributes:
        batch_id: Unique batch identifier
        priority: Processing priority
        patterns: List of pattern IDs in this batch
        cost_estimates: Cost estimate for each pattern
        total_estimated_tokens: Sum of all pattern token estimates
        requires_protocol_context: Whether any pattern needs protocol context
    """

    batch_id: str
    priority: BatchPriority
    patterns: List[str]
    cost_estimates: List[PatternCostEstimate]
    total_estimated_tokens: int = 0
    requires_protocol_context: bool = False

    def __post_init__(self) -> None:
        """Calculate aggregates."""
        if self.cost_estimates:
            self.total_estimated_tokens = sum(c.estimated_tokens for c in self.cost_estimates)
            self.requires_protocol_context = any(c.requires_context for c in self.cost_estimates)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "batch_id": self.batch_id,
            "priority": self.priority.value,
            "patterns": self.patterns,
            "cost_estimates": [c.to_dict() for c in self.cost_estimates],
            "total_estimated_tokens": self.total_estimated_tokens,
            "requires_protocol_context": self.requires_protocol_context,
        }


@dataclass
class CacheKey:
    """Cache key for prefix caching.

    Per PCONTEXT-07: Prefix cache keyed by graph hash + PCP version + budget policy.

    Attributes:
        graph_hash: SHA256 of the knowledge graph
        pcp_version: Protocol Context Pack version
        budget_policy_hash: Hash of budget policy parameters
        slice_hash: Hash of the graph slice being analyzed
    """

    graph_hash: str
    pcp_version: str
    budget_policy_hash: str
    slice_hash: str = ""

    @classmethod
    def compute(
        cls,
        graph_data: str,
        pcp_version: str,
        budget_policy: BudgetPolicy,
        slice_data: Optional[str] = None,
    ) -> "CacheKey":
        """Compute cache key from inputs.

        Args:
            graph_data: Serialized graph data
            pcp_version: PCP version string
            budget_policy: Budget policy to hash
            slice_data: Optional slice-specific data

        Returns:
            CacheKey with computed hashes
        """
        graph_hash = hashlib.sha256(graph_data.encode()).hexdigest()[:16]

        budget_str = json.dumps(budget_policy.to_dict(), sort_keys=True)
        budget_hash = hashlib.sha256(budget_str.encode()).hexdigest()[:8]

        slice_hash = ""
        if slice_data:
            slice_hash = hashlib.sha256(slice_data.encode()).hexdigest()[:8]

        return cls(
            graph_hash=graph_hash,
            pcp_version=pcp_version,
            budget_policy_hash=budget_hash,
            slice_hash=slice_hash,
        )

    def to_string(self) -> str:
        """Convert to cache key string."""
        parts = [f"g:{self.graph_hash}", f"p:{self.pcp_version}", f"b:{self.budget_policy_hash}"]
        if self.slice_hash:
            parts.append(f"s:{self.slice_hash}")
        return "|".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "graph_hash": self.graph_hash,
            "pcp_version": self.pcp_version,
            "budget_policy_hash": self.budget_policy_hash,
            "slice_hash": self.slice_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheKey":
        """Deserialize from dictionary."""
        return cls(
            graph_hash=data.get("graph_hash", ""),
            pcp_version=data.get("pcp_version", ""),
            budget_policy_hash=data.get("budget_policy_hash", ""),
            slice_hash=data.get("slice_hash", ""),
        )


@dataclass
class ForkResult:
    """Result from a single scout in fork-then-rank.

    Attributes:
        scout_id: Identifier for the scout agent
        diversity_path: Which reasoning path the scout used
        hypothesis: Scout's hypothesis output
        timestamp: When the result was produced
    """

    scout_id: str
    diversity_path: DiversityPath
    hypothesis: ScoutHypothesis
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "scout_id": self.scout_id,
            "diversity_path": self.diversity_path.to_dict(),
            "hypothesis": self.hypothesis.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RankedResult:
    """Result after ranking fork results.

    Attributes:
        pattern_id: Pattern that was analyzed
        winner: The winning hypothesis
        vote_count: How many scouts voted for winner
        total_scouts: Total scouts that participated
        confidence_aggregate: Aggregated confidence score
        vetoed: Whether result was vetoed by contradiction
        veto_reason: Reason for veto if applicable
        all_results: All fork results for audit trail
    """

    pattern_id: str
    winner: ScoutHypothesis
    vote_count: int
    total_scouts: int
    confidence_aggregate: float
    vetoed: bool = False
    veto_reason: str = ""
    all_results: List[ForkResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "winner": self.winner.to_dict(),
            "vote_count": self.vote_count,
            "total_scouts": self.total_scouts,
            "confidence_aggregate": round(self.confidence_aggregate, 4),
            "vetoed": self.vetoed,
            "veto_reason": self.veto_reason,
            "all_results": [r.to_dict() for r in self.all_results],
        }


@dataclass
class BatchManifest:
    """Manifest for a batch discovery run.

    Per plan requirements:
    - Cache keys, slice hashes, evidence IDs, and protocol_context_included flag

    Attributes:
        manifest_id: Unique manifest identifier
        cache_key: Cache key for this batch
        batches: Adaptive batches in processing order
        evidence_ids: All evidence IDs referenced
        slice_hashes: Hashes of all slices used
        protocol_context_included: Whether PCP was included
        created_at: When manifest was created
        budget_policy: Budget policy used
        diversity_policy: Diversity policy used
        metadata: Additional metadata
    """

    manifest_id: str
    cache_key: CacheKey
    batches: List[AdaptiveBatch]
    evidence_ids: List[str]
    slice_hashes: List[str]
    protocol_context_included: bool
    created_at: datetime = field(default_factory=datetime.now)
    budget_policy: Optional[BudgetPolicy] = None
    diversity_policy: Optional[DiversityPolicy] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "manifest_id": self.manifest_id,
            "cache_key": self.cache_key.to_dict(),
            "batches": [b.to_dict() for b in self.batches],
            "evidence_ids": sorted(self.evidence_ids),
            "slice_hashes": sorted(self.slice_hashes),
            "protocol_context_included": self.protocol_context_included,
            "created_at": self.created_at.isoformat(),
            "budget_policy": self.budget_policy.to_dict() if self.budget_policy else None,
            "diversity_policy": self.diversity_policy.to_dict() if self.diversity_policy else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchManifest":
        """Deserialize from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        budget_data = data.get("budget_policy")
        diversity_data = data.get("diversity_policy")

        return cls(
            manifest_id=data.get("manifest_id", ""),
            cache_key=CacheKey.from_dict(data.get("cache_key", {})),
            batches=[],  # Would need full deserialization
            evidence_ids=list(data.get("evidence_ids", [])),
            slice_hashes=list(data.get("slice_hashes", [])),
            protocol_context_included=data.get("protocol_context_included", False),
            created_at=created_at,
            budget_policy=BudgetPolicy.from_dict(budget_data) if budget_data else None,
            diversity_policy=DiversityPolicy.from_dict(diversity_data) if diversity_data else None,
            metadata=dict(data.get("metadata", {})),
        )


# =============================================================================
# Adaptive Batching
# =============================================================================


class AdaptiveBatcher:
    """Groups patterns into batches by cost/complexity.

    Per PCONTEXT-07: Batch orchestration groups by cost/complexity.
    """

    def __init__(
        self,
        cost_weights: Optional[Dict[str, float]] = None,
        max_batch_tokens: int = 4000,
        min_batch_size: int = 1,
        max_batch_size: int = 10,
    ):
        """Initialize adaptive batcher.

        Args:
            cost_weights: Weights for cost estimation
            max_batch_tokens: Maximum tokens per batch
            min_batch_size: Minimum patterns per batch
            max_batch_size: Maximum patterns per batch
        """
        self.cost_weights = cost_weights or DEFAULT_COST_WEIGHTS
        self.max_batch_tokens = max_batch_tokens
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size

    def estimate_pattern_cost(
        self,
        pattern_id: str,
        tier: str = "B",
        has_multi_hop: bool = False,
        has_cross_contract: bool = False,
        base_tokens: int = 500,
    ) -> PatternCostEstimate:
        """Estimate cost for a single pattern.

        Args:
            pattern_id: Pattern identifier
            tier: Pattern tier (A, B, C)
            has_multi_hop: Whether pattern requires multi-hop analysis
            has_cross_contract: Whether pattern crosses contracts
            base_tokens: Base token count

        Returns:
            PatternCostEstimate with computed values
        """
        # Base cost from tier
        tier_key = f"tier_{tier.lower()}"
        tier_multiplier = self.cost_weights.get(tier_key, 1.0)

        # Additional multipliers
        multiplier = tier_multiplier
        if has_multi_hop:
            multiplier *= self.cost_weights.get("multi_hop", 1.5)
        if has_cross_contract:
            multiplier *= self.cost_weights.get("cross_contract", 2.0)

        return PatternCostEstimate(
            pattern_id=pattern_id,
            base_cost=base_tokens,
            complexity_multiplier=multiplier,
            estimated_tokens=int(base_tokens * multiplier),
            tier=tier,
            requires_context=tier in ("B", "C"),
        )

    def create_batches(
        self,
        cost_estimates: List[PatternCostEstimate],
        risk_weighting: Optional[Dict[str, float]] = None,
    ) -> List[AdaptiveBatch]:
        """Create adaptive batches from cost estimates.

        Groups patterns by priority (based on tier and risk) and
        respects token limits per batch.

        Args:
            cost_estimates: Cost estimates for all patterns
            risk_weighting: Optional risk weights by pattern ID

        Returns:
            List of AdaptiveBatch objects in priority order
        """
        risk_weighting = risk_weighting or {}

        # Sort by priority: Tier A first, then by risk weight descending
        def priority_key(ce: PatternCostEstimate) -> Tuple[int, float]:
            tier_priority = {"A": 0, "B": 1, "C": 2}.get(ce.tier, 3)
            risk = risk_weighting.get(ce.pattern_id, 0.5)
            return (tier_priority, -risk)

        sorted_estimates = sorted(cost_estimates, key=priority_key)

        # Group into batches respecting token limits
        batches: List[AdaptiveBatch] = []
        current_batch: List[PatternCostEstimate] = []
        current_tokens = 0

        for estimate in sorted_estimates:
            # Check if adding this pattern exceeds limits
            if (
                current_tokens + estimate.estimated_tokens > self.max_batch_tokens
                or len(current_batch) >= self.max_batch_size
            ) and len(current_batch) >= self.min_batch_size:
                # Flush current batch
                batches.append(self._create_batch(current_batch, len(batches)))
                current_batch = []
                current_tokens = 0

            current_batch.append(estimate)
            current_tokens += estimate.estimated_tokens

        # Flush remaining
        if current_batch:
            batches.append(self._create_batch(current_batch, len(batches)))

        return batches

    def _create_batch(
        self,
        estimates: List[PatternCostEstimate],
        batch_index: int,
    ) -> AdaptiveBatch:
        """Create an AdaptiveBatch from estimates.

        Args:
            estimates: Cost estimates for this batch
            batch_index: Index of this batch

        Returns:
            AdaptiveBatch object
        """
        # Determine priority from first pattern (they're sorted by priority)
        first_tier = estimates[0].tier if estimates else "B"
        priority = {
            "A": BatchPriority.HIGH,  # Tier A is high priority (cheap, deterministic)
            "B": BatchPriority.MEDIUM,
            "C": BatchPriority.LOW,
        }.get(first_tier, BatchPriority.MEDIUM)

        # Upgrade to CRITICAL if any pattern has critical risk
        # (This would be determined by risk_weighting in practice)

        return AdaptiveBatch(
            batch_id=f"batch-{batch_index:03d}",
            priority=priority,
            patterns=[e.pattern_id for e in estimates],
            cost_estimates=estimates,
        )


# =============================================================================
# Fork-Then-Rank
# =============================================================================


class ForkThenRank:
    """Fork-then-rank orchestration for batch discovery.

    Per PCONTEXT-07: Fork-then-rank produces deterministic winners.

    Multiple scouts propose hypotheses with different reasoning paths,
    then a verifier ranks them and contradiction can veto.
    """

    def __init__(
        self,
        ranking_method: RankingMethod = RankingMethod.HYBRID,
        veto_threshold: float = 0.7,
        min_scouts: int = 2,
        diversity_policy: Optional[DiversityPolicy] = None,
    ):
        """Initialize fork-then-rank.

        Args:
            ranking_method: Method for ranking fork results
            veto_threshold: Confidence threshold for veto (contradiction)
            min_scouts: Minimum number of scouts required
            diversity_policy: Policy for diverse reasoning paths
        """
        self.ranking_method = ranking_method
        self.veto_threshold = veto_threshold
        self.min_scouts = min_scouts
        self.diversity_policy = diversity_policy or DiversityPolicy.default()

    def rank_results(
        self,
        pattern_id: str,
        fork_results: List[ForkResult],
        contradiction: Optional[ContradictionReport] = None,
    ) -> RankedResult:
        """Rank fork results and determine winner.

        Uses the configured ranking method to select a winner from
        scout hypotheses. Contradiction can veto if confidence > threshold.

        Args:
            pattern_id: Pattern being ranked
            fork_results: Results from all scouts
            contradiction: Optional contradiction report

        Returns:
            RankedResult with winner and audit trail
        """
        if not fork_results:
            # No results - return empty hypothesis
            from alphaswarm_sol.orchestration.schemas import UnknownReason
            empty_hyp = ScoutHypothesis(
                pattern_id=pattern_id,
                status=ScoutStatus.UNKNOWN,
                evidence_refs=[],
                unknowns=[UnknownItem(field="all", reason=UnknownReason.MISSING_EVIDENCE)],
                confidence=0.0,
            )
            return RankedResult(
                pattern_id=pattern_id,
                winner=empty_hyp,
                vote_count=0,
                total_scouts=0,
                confidence_aggregate=0.0,
                all_results=[],
            )

        # Group by status for voting
        status_counts: Dict[ScoutStatus, int] = {}
        status_hypotheses: Dict[ScoutStatus, List[ScoutHypothesis]] = {}

        for result in fork_results:
            status = result.hypothesis.status
            status_counts[status] = status_counts.get(status, 0) + 1
            if status not in status_hypotheses:
                status_hypotheses[status] = []
            status_hypotheses[status].append(result.hypothesis)

        # Determine winning status by method
        if self.ranking_method == RankingMethod.MAJORITY_VOTE:
            winner_status = max(status_counts.keys(), key=lambda s: status_counts[s])
            winner_hyp = self._select_by_confidence(status_hypotheses[winner_status])
        elif self.ranking_method == RankingMethod.CONFIDENCE_WEIGHTED:
            winner_hyp = self._select_by_weighted_confidence(fork_results)
            winner_status = winner_hyp.status
        elif self.ranking_method == RankingMethod.EVIDENCE_COUNT:
            winner_hyp = self._select_by_evidence(fork_results)
            winner_status = winner_hyp.status
        else:  # HYBRID
            # Combine majority vote with confidence weighting
            winner_status = max(status_counts.keys(), key=lambda s: status_counts[s])
            candidates = status_hypotheses[winner_status]
            winner_hyp = self._select_by_confidence(candidates)

        # Calculate aggregate confidence
        confidence_aggregate = sum(r.hypothesis.confidence for r in fork_results) / len(fork_results)

        # Check for contradiction veto
        vetoed = False
        veto_reason = ""
        if contradiction and contradiction.status == ContradictionStatus.REFUTED:
            if contradiction.confidence >= self.veto_threshold:
                vetoed = True
                veto_reason = f"Refuted with confidence {contradiction.confidence:.2f}"

        return RankedResult(
            pattern_id=pattern_id,
            winner=winner_hyp,
            vote_count=status_counts.get(winner_status, 0),
            total_scouts=len(fork_results),
            confidence_aggregate=confidence_aggregate,
            vetoed=vetoed,
            veto_reason=veto_reason,
            all_results=fork_results,
        )

    def _select_by_confidence(self, hypotheses: List[ScoutHypothesis]) -> ScoutHypothesis:
        """Select hypothesis with highest confidence.

        Args:
            hypotheses: List of hypotheses to choose from

        Returns:
            Hypothesis with highest confidence
        """
        return max(hypotheses, key=lambda h: h.confidence)

    def _select_by_weighted_confidence(self, results: List[ForkResult]) -> ScoutHypothesis:
        """Select hypothesis using confidence-weighted voting.

        Args:
            results: All fork results

        Returns:
            Hypothesis with highest weighted score
        """
        # Weight by confidence and evidence count
        def score(result: ForkResult) -> float:
            h = result.hypothesis
            evidence_factor = min(len(h.evidence_refs) / 3.0, 1.0)  # Max out at 3 evidence
            return h.confidence * (1.0 + evidence_factor * 0.5)

        best = max(results, key=score)
        return best.hypothesis

    def _select_by_evidence(self, results: List[ForkResult]) -> ScoutHypothesis:
        """Select hypothesis with most evidence.

        Args:
            results: All fork results

        Returns:
            Hypothesis with most evidence refs
        """
        best = max(results, key=lambda r: len(r.hypothesis.evidence_refs))
        return best.hypothesis


# =============================================================================
# Batch Discovery Orchestrator v2
# =============================================================================


class BatchDiscoveryOrchestrator:
    """Batch discovery orchestrator v2 with adaptive batching and fork-then-rank.

    Per plan requirements:
    - Adaptive batching by pattern cost/complexity
    - Prefix cache versioning (graph hash + PCP version + budget policy)
    - Fork-then-rank: multiple scouts propose, verifier ranks, contradiction can veto

    Usage:
        orchestrator = BatchDiscoveryOrchestrator(
            budget_policy=BudgetPolicy(),
            diversity_policy=DiversityPolicy.default(),
        )

        # Create batches from patterns
        batches = orchestrator.create_adaptive_batches(pattern_costs)

        # Create manifest
        manifest = orchestrator.create_manifest(
            graph_data="...",
            pcp_version="v2.0",
            batches=batches,
            evidence_ids=["EVD-001", "EVD-002"],
        )

        # Run fork-then-rank
        result = orchestrator.fork_then_rank(
            pattern_id="reentrancy-classic",
            fork_results=scout_results,
        )
    """

    def __init__(
        self,
        budget_policy: Optional[BudgetPolicy] = None,
        diversity_policy: Optional[DiversityPolicy] = None,
        ranking_method: RankingMethod = RankingMethod.HYBRID,
        veto_threshold: float = 0.7,
        cost_weights: Optional[Dict[str, float]] = None,
        max_batch_tokens: int = 4000,
    ):
        """Initialize batch discovery orchestrator.

        Args:
            budget_policy: Budget policy for token management
            diversity_policy: Diversity policy for reasoning paths
            ranking_method: Method for ranking fork results
            veto_threshold: Confidence threshold for contradiction veto
            cost_weights: Weights for cost estimation
            max_batch_tokens: Maximum tokens per batch
        """
        self.budget_policy = budget_policy or BudgetPolicy.default()
        self.diversity_policy = diversity_policy or DiversityPolicy.default()

        self.batcher = AdaptiveBatcher(
            cost_weights=cost_weights,
            max_batch_tokens=max_batch_tokens,
        )

        self.ranker = ForkThenRank(
            ranking_method=ranking_method,
            veto_threshold=veto_threshold,
            diversity_policy=self.diversity_policy,
        )

        self._cache: Dict[str, Any] = {}
        self._results: List[RankedResult] = []

    def estimate_pattern_cost(
        self,
        pattern_id: str,
        tier: str = "B",
        has_multi_hop: bool = False,
        has_cross_contract: bool = False,
        base_tokens: int = 500,
    ) -> PatternCostEstimate:
        """Estimate cost for a pattern.

        Args:
            pattern_id: Pattern identifier
            tier: Pattern tier (A, B, C)
            has_multi_hop: Whether multi-hop analysis needed
            has_cross_contract: Whether cross-contract analysis needed
            base_tokens: Base token count

        Returns:
            PatternCostEstimate
        """
        return self.batcher.estimate_pattern_cost(
            pattern_id=pattern_id,
            tier=tier,
            has_multi_hop=has_multi_hop,
            has_cross_contract=has_cross_contract,
            base_tokens=base_tokens,
        )

    def create_adaptive_batches(
        self,
        cost_estimates: List[PatternCostEstimate],
        risk_weighting: Optional[Dict[str, float]] = None,
    ) -> List[AdaptiveBatch]:
        """Create adaptive batches from cost estimates.

        Args:
            cost_estimates: Cost estimates for patterns
            risk_weighting: Optional risk weights

        Returns:
            List of AdaptiveBatch in priority order
        """
        return self.batcher.create_batches(cost_estimates, risk_weighting)

    def compute_cache_key(
        self,
        graph_data: str,
        pcp_version: str,
        slice_data: Optional[str] = None,
    ) -> CacheKey:
        """Compute cache key for prefix caching.

        Args:
            graph_data: Serialized graph
            pcp_version: PCP version
            slice_data: Optional slice data

        Returns:
            CacheKey with all components
        """
        return CacheKey.compute(
            graph_data=graph_data,
            pcp_version=pcp_version,
            budget_policy=self.budget_policy,
            slice_data=slice_data,
        )

    def create_manifest(
        self,
        graph_data: str,
        pcp_version: str,
        batches: List[AdaptiveBatch],
        evidence_ids: List[str],
        slice_hashes: Optional[List[str]] = None,
        protocol_context_included: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BatchManifest:
        """Create a batch manifest.

        Args:
            graph_data: Serialized graph for cache key
            pcp_version: PCP version
            batches: Adaptive batches
            evidence_ids: Evidence IDs referenced
            slice_hashes: Slice hashes (computed if not provided)
            protocol_context_included: Whether PCP was included
            metadata: Additional metadata

        Returns:
            BatchManifest with full context
        """
        cache_key = self.compute_cache_key(graph_data, pcp_version)

        # Generate manifest ID from cache key
        manifest_id = f"manifest-{cache_key.graph_hash[:8]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Compute slice hashes if not provided
        if slice_hashes is None:
            slice_hashes = []
            for batch in batches:
                batch_data = json.dumps(batch.patterns, sort_keys=True)
                slice_hash = hashlib.sha256(batch_data.encode()).hexdigest()[:8]
                slice_hashes.append(slice_hash)

        return BatchManifest(
            manifest_id=manifest_id,
            cache_key=cache_key,
            batches=batches,
            evidence_ids=sorted(set(evidence_ids)),
            slice_hashes=slice_hashes,
            protocol_context_included=protocol_context_included,
            budget_policy=self.budget_policy,
            diversity_policy=self.diversity_policy,
            metadata=metadata or {},
        )

    def fork_then_rank(
        self,
        pattern_id: str,
        fork_results: List[ForkResult],
        contradiction: Optional[ContradictionReport] = None,
    ) -> RankedResult:
        """Run fork-then-rank on scout results.

        Args:
            pattern_id: Pattern being ranked
            fork_results: Results from scouts
            contradiction: Optional contradiction report

        Returns:
            RankedResult with deterministic winner
        """
        result = self.ranker.rank_results(pattern_id, fork_results, contradiction)
        self._results.append(result)
        return result

    def get_cached(self, cache_key: CacheKey) -> Optional[Any]:
        """Get cached result.

        Args:
            cache_key: Key to look up

        Returns:
            Cached value or None
        """
        return self._cache.get(cache_key.to_string())

    def set_cached(self, cache_key: CacheKey, value: Any) -> None:
        """Set cached result.

        Args:
            cache_key: Key to store under
            value: Value to cache
        """
        self._cache[cache_key.to_string()] = value

    def get_results(self) -> List[RankedResult]:
        """Get all ranked results from this session.

        Returns:
            List of RankedResult objects
        """
        return list(self._results)

    def clear_results(self) -> None:
        """Clear accumulated results."""
        self._results.clear()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "BatchPriority",
    "RankingMethod",
    # Data structures
    "PatternCostEstimate",
    "AdaptiveBatch",
    "CacheKey",
    "ForkResult",
    "RankedResult",
    "BatchManifest",
    # Classes
    "AdaptiveBatcher",
    "ForkThenRank",
    "BatchDiscoveryOrchestrator",
    # Constants
    "DEFAULT_COST_WEIGHTS",
]
