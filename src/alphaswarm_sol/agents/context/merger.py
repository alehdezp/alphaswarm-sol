"""Context merger for combining multiple context sources.

This module provides the ContextMerger class that orchestrates merging
vulndoc knowledge with protocol context and additional context sources
into unified context bundles.

Per 05.5-CONTEXT.md:
- One vulnerability class per merge
- Protocol pack provides economic context
- Vulndoc provides reasoning methodology
- Conservative default: unknown risks assumed present

Phase 5.10-06: Adds delta packing for verify pass:
- ContextDelta computes diff between scout and verifier slices
- Only added nodes/edges and required evidence IDs are included
- Deterministic ordering by evidence ID for reproducibility
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from alphaswarm_sol.agents.context.extractor import VulndocContextExtractor
from alphaswarm_sol.agents.context.types import (
    BudgetPolicy,
    ContextBundle,
    ContextDelta,
    ContextGating,
)
from alphaswarm_sol.context.schema import ProtocolContextPack


@dataclass
class MergeResult:
    """Result of context merge operation.

    Attributes:
        success: Whether merge completed successfully
        bundle: Merged context bundle (None if failed)
        errors: List of error messages
        warnings: List of warning messages
        token_count: Final token count after merge
        trimmed: Whether content was trimmed to fit budget
        sources_used: List of sources used in merge
        gating: Context gating metadata (Phase 5.10-06)
    """

    success: bool
    bundle: Optional[ContextBundle]
    errors: List[str]
    warnings: List[str]
    token_count: int
    trimmed: bool
    sources_used: List[str]
    gating: Optional[ContextGating] = None


# =============================================================================
# Phase 5.10-06: Delta Packing for Verify Pass
# =============================================================================


class DeltaPacker:
    """Pack context deltas for verify pass.

    Computes diff between scout slice and verifier slice to minimize
    token usage in verification pass. Only new evidence is sent.

    Usage:
        packer = DeltaPacker()

        # Compute delta from scout to verifier context
        delta = packer.compute_delta(
            scout_nodes=scout_result.node_ids,
            scout_edges=scout_result.edge_ids,
            verifier_nodes=expanded_result.node_ids,
            verifier_edges=expanded_result.edge_ids,
            evidence_ids=evidence_to_verify,
            scout_coverage=scout_coverage.score,
        )

        # Pack delta for verifier
        packed = packer.pack_for_verify(delta, budget=3000)
    """

    def __init__(self, budget_policy: Optional[BudgetPolicy] = None):
        """Initialize delta packer.

        Args:
            budget_policy: Budget policy for verify pass limits
        """
        self.budget_policy = budget_policy or BudgetPolicy.default()

    def compute_delta(
        self,
        scout_nodes: set,
        scout_edges: set,
        verifier_nodes: set,
        verifier_edges: set,
        evidence_ids: Optional[List[str]] = None,
        scout_coverage: float = 0.0,
    ) -> ContextDelta:
        """Compute delta between scout and verifier slices.

        Args:
            scout_nodes: Node IDs from scout pass
            scout_edges: Edge IDs from scout pass
            verifier_nodes: Node IDs for verifier pass
            verifier_edges: Edge IDs for verifier pass
            evidence_ids: Evidence IDs to include
            scout_coverage: Coverage from scout pass

        Returns:
            ContextDelta with deterministic ordering
        """
        return ContextDelta.compute(
            scout_node_ids=scout_nodes,
            scout_edge_ids=scout_edges,
            verifier_node_ids=verifier_nodes,
            verifier_edge_ids=verifier_edges,
            evidence_ids=evidence_ids,
            scout_coverage=scout_coverage,
        )

    def pack_for_verify(
        self,
        delta: ContextDelta,
        budget: Optional[int] = None,
        include_removed: bool = False,
    ) -> Dict[str, Any]:
        """Pack delta for verify pass within budget.

        PCP fields are never trimmed - only delta content is reduced.

        Args:
            delta: Context delta to pack
            budget: Token budget (default: verify_pass_tokens)
            include_removed: Include removed nodes (default: False)

        Returns:
            Packed delta dictionary suitable for verify pass
        """
        if budget is None:
            budget = self.budget_policy.verify_pass_tokens

        packed = {
            "type": "context_delta",
            "scout_coverage": round(delta.scout_coverage, 4),
            "added_nodes": delta.added_node_ids,
            "added_edges": delta.added_edge_ids,
            "evidence_ids": delta.evidence_ids,
            "delta_tokens": delta.delta_tokens,
        }

        if include_removed and delta.removed_node_ids:
            packed["removed_nodes"] = delta.removed_node_ids

        if delta.property_changes:
            packed["property_changes"] = delta.property_changes

        # Check if within budget
        estimated_tokens = delta.delta_tokens
        if estimated_tokens > budget:
            # Trim delta while preserving evidence IDs
            packed = self._trim_delta(packed, budget)

        return packed

    def _trim_delta(
        self,
        packed: Dict[str, Any],
        budget: int,
    ) -> Dict[str, Any]:
        """Trim delta to fit budget while preserving evidence.

        Priority order for keeping content:
        1. Evidence IDs (never trimmed)
        2. Added nodes with evidence
        3. Added edges
        4. Other added nodes

        Args:
            packed: Packed delta to trim
            budget: Token budget

        Returns:
            Trimmed packed delta
        """
        # Evidence IDs are never trimmed
        # Calculate token usage
        evidence_tokens = len(packed.get("evidence_ids", [])) * 10

        remaining_budget = budget - evidence_tokens - 100  # Reserve for structure

        if remaining_budget <= 0:
            # Only evidence fits
            return {
                "type": "context_delta",
                "scout_coverage": packed["scout_coverage"],
                "evidence_ids": packed["evidence_ids"],
                "delta_tokens": evidence_tokens,
                "trimmed": True,
                "trim_reason": "budget_exceeded_evidence_only",
            }

        # Calculate node/edge budgets
        node_count = len(packed.get("added_nodes", []))
        edge_count = len(packed.get("added_edges", []))

        node_tokens = node_count * 100
        edge_tokens = edge_count * 20

        if node_tokens + edge_tokens <= remaining_budget:
            # All content fits
            return packed

        # Need to trim nodes
        node_budget = remaining_budget - edge_tokens
        max_nodes = max(1, node_budget // 100)

        trimmed = {
            "type": "context_delta",
            "scout_coverage": packed["scout_coverage"],
            "evidence_ids": packed["evidence_ids"],
            "added_nodes": packed.get("added_nodes", [])[:max_nodes],
            "added_edges": packed.get("added_edges", []),
            "delta_tokens": max_nodes * 100 + edge_tokens + evidence_tokens,
            "trimmed": True,
            "trim_reason": f"reduced_nodes_from_{node_count}_to_{max_nodes}",
        }

        return trimmed

    def should_use_delta(
        self,
        scout_tokens: int,
        delta_tokens: int,
    ) -> bool:
        """Determine if delta packing should be used.

        Delta packing is worthwhile when delta is significantly smaller
        than full context (>30% reduction).

        Args:
            scout_tokens: Token count from scout pass
            delta_tokens: Estimated delta tokens

        Returns:
            True if delta packing should be used
        """
        if scout_tokens == 0:
            return False

        reduction = (scout_tokens - delta_tokens) / scout_tokens
        return reduction > 0.3  # Use delta if >30% reduction


@dataclass
class DeltaMergeResult:
    """Result of delta merge operation for verify pass.

    Attributes:
        success: Whether merge completed successfully
        delta: Computed context delta
        packed: Packed delta for verify pass
        scout_bundle: Original scout bundle
        evidence_ids: Evidence IDs included
        within_budget: Whether packed delta fits budget
    """

    success: bool
    delta: Optional[ContextDelta]
    packed: Optional[Dict[str, Any]]
    scout_bundle: Optional[ContextBundle]
    evidence_ids: List[str]
    within_budget: bool
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "success": self.success,
            "evidence_ids": self.evidence_ids,
            "within_budget": self.within_budget,
            "errors": self.errors,
        }
        if self.delta is not None:
            result["delta"] = self.delta.to_dict()
        if self.packed is not None:
            result["packed"] = self.packed
        return result


class ContextMerger:
    """Merges vulndoc + protocol context into unified bundles.

    Per 05.5-CONTEXT.md:
    - One vulnerability class per merge
    - Protocol pack provides economic context
    - Vulndoc provides reasoning methodology
    - Conservative default: unknown risks assumed present

    The merger orchestrates the combination of multiple context sources
    and ensures the result fits within token budgets.

    Attributes:
        extractor: VulndocContextExtractor instance
        default_token_budget: Target token budget (default 4000)
        max_token_budget: Maximum token budget before trimming (default 6000)
    """

    def __init__(
        self,
        extractor: VulndocContextExtractor,
        default_token_budget: int = 4000,
        max_token_budget: int = 6000,
    ):
        """Initialize merger.

        Args:
            extractor: VulndocContextExtractor for base extraction
            default_token_budget: Target token count (default 4000)
            max_token_budget: Maximum token count before trimming (default 6000)
        """
        self.extractor = extractor
        self.default_token_budget = default_token_budget
        self.max_token_budget = max_token_budget

    def merge(
        self,
        vuln_class: str,
        protocol_pack: ProtocolContextPack,
        target_scope: List[str],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> MergeResult:
        """Merge context sources into a unified bundle.

        Args:
            vuln_class: Vulnerability class (e.g., "reentrancy/classic")
            protocol_pack: Protocol context pack
            target_scope: List of contract files to analyze
            additional_context: Optional additional context to merge

        Returns:
            MergeResult with success status and merged bundle
        """
        errors: List[str] = []
        warnings: List[str] = []
        sources_used: List[str] = []

        try:
            # 1. Extract base bundle from vulndoc
            bundle = self.extractor.extract(
                vuln_class=vuln_class,
                protocol_pack=protocol_pack,
                target_scope=target_scope,
            )
            sources_used.append("vulndoc")
            sources_used.append("protocol_pack")

            # 2. Merge additional context if provided
            if additional_context:
                bundle = self._merge_additional(bundle, additional_context)
                sources_used.append("additional_context")

            # 3. Apply conservative defaults for unknown risks
            bundle = self._apply_conservative_defaults(bundle)

            # 4. Check token budget and trim if needed
            token_count = self.extractor._estimate_tokens(bundle)
            trimmed = False
            if token_count > self.max_token_budget:
                bundle = self.extractor._trim_to_budget(bundle, self.max_token_budget)
                trimmed = True
                warnings.append(
                    f"Trimmed from {token_count} to {self.max_token_budget} tokens"
                )
                token_count = self.extractor._estimate_tokens(bundle)

            return MergeResult(
                success=True,
                bundle=bundle,
                errors=[],
                warnings=warnings,
                token_count=token_count,
                trimmed=trimmed,
                sources_used=sources_used,
            )

        except ValueError as e:
            errors.append(str(e))
            return MergeResult(
                success=False,
                bundle=None,
                errors=errors,
                warnings=warnings,
                token_count=0,
                trimmed=False,
                sources_used=sources_used,
            )

    def _merge_additional(
        self,
        bundle: ContextBundle,
        additional: Dict[str, Any],
    ) -> ContextBundle:
        """Merge additional context into bundle.

        Args:
            bundle: Base context bundle
            additional: Additional context dictionary

        Returns:
            Updated context bundle
        """
        # Add extra VQL queries
        if "vql_queries" in additional:
            bundle.vql_queries.extend(additional["vql_queries"])

        # Add extra graph patterns
        if "graph_patterns" in additional:
            bundle.graph_patterns.extend(additional["graph_patterns"])

        # Add notes to reasoning template
        if "reasoning_notes" in additional:
            bundle.reasoning_template += (
                f"\n\nAdditional Notes:\n{additional['reasoning_notes']}"
            )

        return bundle

    def _apply_conservative_defaults(self, bundle: ContextBundle) -> ContextBundle:
        """Apply conservative defaults: unknown = assume present.

        Per 05.5-CONTEXT.md: Better false positives than missed vulns.

        Args:
            bundle: Context bundle to apply defaults to

        Returns:
            Updated context bundle
        """
        # For each risk category, if confidence is "unknown", set present=True
        for field in [
            "oracle_risks",
            "liquidity_risks",
            "access_risks",
            "upgrade_risks",
            "integration_risks",
            "timing_risks",
            "economic_risks",
            "governance_risks",
        ]:
            risk_cat = getattr(bundle.risk_profile, field)
            if risk_cat.confidence == "unknown":
                risk_cat.present = True

        return bundle
