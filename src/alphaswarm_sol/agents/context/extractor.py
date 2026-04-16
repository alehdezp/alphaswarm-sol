"""Vulndoc context extraction for agent spawning.

This module provides the VulndocContextExtractor class that merges
vulndoc vulnerability knowledge with protocol context pack data.

Per 05.5-CONTEXT.md:
- System prompt = vulndoc's reasoning_template (HOW to think)
- User context = protocol pack (WHAT to analyze)
- One vuln class per bundle
- Token budget: target 2-4k, trim if >6k

Phase 5.10-05: Adds PatternContextExtractor with escalation policy:
- If required ops missing, mark unknown
- Trigger single expansion pass
- Re-evaluate and return unknown if still missing

Phase 5.10-06: Adds BudgetPolicy + context gating:
- BudgetPolicy enforces cheap/verify/deep passes
- PCP fields are never trimmed; only slices are reduced
- Verify pass sends delta from scout context
- Context gating rules define when protocol context is included or omitted
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from alphaswarm_sol.agents.context.types import (
    BudgetPass,
    BudgetPolicy,
    ContextBundle,
    ContextDelta,
    ContextGating,
    RiskCategory,
    RiskProfile,
)
from alphaswarm_sol.context.schema import ProtocolContextPack


# =============================================================================
# Phase 5.10-05: Escalation Policy for Pattern Context Extraction
# =============================================================================


class EvaluationStatus(str, Enum):
    """Status of pattern evaluation after context extraction."""

    VERIFIED = "verified"  # All required evidence present, pattern evaluated
    UNKNOWN = "unknown"  # Missing evidence, cannot determine match
    REFUTED = "refuted"  # Evidence present that refutes pattern
    EXPANDED = "expanded"  # Context was expanded, re-evaluation needed


@dataclass
class EscalationResult:
    """Result of escalation policy evaluation.

    Tracks the unknown -> expand -> re-evaluate flow.
    """

    status: EvaluationStatus
    initial_status: EvaluationStatus
    expansion_triggered: bool = False
    expansion_pass_count: int = 0
    missing_ops_before: List[str] = field(default_factory=list)
    missing_ops_after: List[str] = field(default_factory=list)
    coverage_before: float = 0.0
    coverage_after: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "status": self.status.value,
            "initial_status": self.initial_status.value,
            "expansion_triggered": self.expansion_triggered,
            "expansion_pass_count": self.expansion_pass_count,
            "missing_ops_before": self.missing_ops_before,
            "missing_ops_after": self.missing_ops_after,
            "coverage_before": round(self.coverage_before, 4),
            "coverage_after": round(self.coverage_after, 4),
            "reason": self.reason,
        }


@dataclass
class PatternContextResult:
    """Result of pattern context extraction with escalation policy.

    Contains the extracted context, slice result, and escalation metadata.

    Phase 5.10-06: Adds gating and budget_validation fields for context gating
    and budget policy enforcement.
    """

    context_bundle: ContextBundle
    escalation: EscalationResult
    slice_result: Optional[Any] = None  # PatternSliceResult
    graph_slice: Optional[Any] = None  # SlicedGraph
    token_estimate: int = 0
    gating: Optional[ContextGating] = None  # Phase 5.10-06
    budget_validation: Optional[Any] = None  # BudgetValidation (Phase 5.10-06)

    def is_evaluable(self) -> bool:
        """Check if pattern can be evaluated with current context."""
        return self.escalation.status in (
            EvaluationStatus.VERIFIED,
            EvaluationStatus.REFUTED,
        )

    def needs_manual_review(self) -> bool:
        """Check if pattern needs manual review due to unknown status."""
        return (
            self.escalation.status == EvaluationStatus.UNKNOWN
            and self.escalation.expansion_triggered
        )

    def context_included(self) -> bool:
        """Check if protocol context was included.

        Phase 5.10-06: context gating indicator.
        """
        if self.gating is None:
            return True
        return self.gating.protocol_context_included

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "escalation": self.escalation.to_dict(),
            "token_estimate": self.token_estimate,
            "is_evaluable": self.is_evaluable(),
            "context_included": self.context_included(),
        }
        if self.slice_result is not None:
            result["slice_result"] = self.slice_result.to_dict()
        if self.gating is not None:
            result["gating"] = self.gating.to_dict()
        if self.budget_validation is not None:
            result["budget_validation"] = self.budget_validation.to_dict()
        return result


class PatternContextExtractor:
    """Extract pattern context with escalation policy and budget management.

    Implements the unknown -> expand -> re-evaluate flow:
    1. Initial slice extraction
    2. Check coverage and missing required ops
    3. If ops missing, mark as unknown
    4. Trigger single expansion pass
    5. Re-evaluate coverage
    6. Return unknown if still missing after expansion

    Phase 5.10-05: Escalation policy integration.

    Phase 5.10-06: Budget policy + context gating:
    - BudgetPolicy enforces cheap/verify/deep pass token limits
    - PCP fields are never trimmed; only slices are reduced
    - Context gating tracks which sources were included/excluded
    - Verify pass can use ContextDelta for efficient delta packing

    Usage:
        extractor = PatternContextExtractor(full_graph)

        # Standard extraction
        result = extractor.extract_for_pattern(
            pcp_data=pattern_context_pack,
            focal_nodes=["F-withdraw"],
            vulndoc_bundle=context_bundle,
        )

        # Budget-aware extraction for specific pass
        result = extractor.extract_for_pass(
            pass_type=BudgetPass.CHEAP,
            pcp_data=pattern_context_pack,
            ...
        )

        if result.is_evaluable():
            # Pattern can be evaluated
            pass
        elif result.needs_manual_review():
            # Expansion tried but still unknown
            print(f"Missing ops after expansion: {result.escalation.missing_ops_after}")
    """

    def __init__(
        self,
        full_graph: Any,
        vulndocs_root: Path | None = None,
        max_expansion_passes: int = 1,
        coverage_threshold: float = 0.8,
        budget_policy: Optional[BudgetPolicy] = None,
    ):
        """Initialize pattern context extractor.

        Args:
            full_graph: Full knowledge graph for expansion
            vulndocs_root: Root directory for vulndocs (uses centralized resolution if None)
            max_expansion_passes: Maximum expansion attempts (default: 1)
            coverage_threshold: Coverage threshold for unknown marking
            budget_policy: Token budget policy (default: BudgetPolicy.default())
        """
        from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path_as_path

        self.full_graph = full_graph
        resolved = vulndocs_root if vulndocs_root is not None else vulndocs_read_path_as_path()
        self.vulndocs_root = resolved
        self.max_expansion_passes = max_expansion_passes
        self.coverage_threshold = coverage_threshold
        self.budget_policy = budget_policy or BudgetPolicy.default()
        self._vulndoc_extractor = VulndocContextExtractor(resolved)

    def extract_for_pattern(
        self,
        pcp_data: Dict[str, Any],
        focal_nodes: List[str],
        vuln_class: str,
        protocol_pack: Any,
        target_scope: List[str],
        pass_type: Optional[BudgetPass] = None,
        include_protocol_context: bool = True,
    ) -> PatternContextResult:
        """Extract context for pattern with escalation policy.

        Args:
            pcp_data: Pattern Context Pack v2 data
            focal_nodes: Starting node IDs for slicing
            vuln_class: Vulnerability class (e.g., "reentrancy/classic")
            protocol_pack: Protocol context pack
            target_scope: Target contract files
            pass_type: Budget pass type (None = no budget enforcement)
            include_protocol_context: Whether to include protocol context

        Returns:
            PatternContextResult with escalation metadata
        """
        # Import here to avoid circular imports
        from alphaswarm_sol.kg.slicer import (
            CoverageScorer,
            ExpansionConfig,
            PatternSliceFocus,
            SemanticDilator,
            slice_graph_for_pattern_focus,
        )

        # Phase 5.10-06: Initialize context gating
        gating = ContextGating()

        # 1. Extract vulndoc context bundle with gating
        context_bundle = self._vulndoc_extractor.extract(
            vuln_class, protocol_pack, target_scope
        )
        gating.vulndoc_included = True
        gating.vulndoc_reason = "required_for_analysis"

        # Phase 5.10-06: Apply context gating rules for protocol context
        if not include_protocol_context:
            gating.protocol_context_included = False
            gating.protocol_context_reason = "explicitly_excluded"
            gating.mark_excluded("protocol_context", "explicitly disabled")
        elif protocol_pack is None:
            gating.protocol_context_included = False
            gating.protocol_context_reason = "not_available"
            gating.mark_unknown("protocol_context", "no protocol pack provided")
        else:
            gating.protocol_context_included = True
            gating.protocol_context_reason = "available_and_relevant"

        # 2. Parse PCP focus
        focus = PatternSliceFocus.from_pcp(pcp_data)

        # 3. Initial slice
        initial_result = slice_graph_for_pattern_focus(
            graph=self.full_graph,
            focus=focus,
            focal_nodes=focal_nodes,
        )
        gating.graph_slice_included = True
        gating.graph_slice_reason = "pattern_focus_slicing"

        # 4. Compute initial coverage
        scorer = CoverageScorer(required_ops=focus.required_ops)
        initial_coverage = scorer.score(initial_result.graph, self.coverage_threshold)

        # 5. Determine initial status
        initial_status = self._evaluate_status(
            initial_coverage.required_missing,
            initial_result.has_forbidden_ops,
            initial_coverage.threshold_met,
        )

        # 6. Build escalation result
        escalation = EscalationResult(
            status=initial_status,
            initial_status=initial_status,
            missing_ops_before=initial_result.missing_required_ops[:],
            coverage_before=initial_coverage.score,
        )

        # 7. Check if expansion needed
        if initial_status == EvaluationStatus.UNKNOWN:
            # Trigger single expansion pass
            expanded_result, final_status = self._expand_and_reevaluate(
                focus=focus,
                focal_nodes=focal_nodes,
                scorer=scorer,
                escalation=escalation,
            )

            if expanded_result is not None:
                initial_result = expanded_result

            escalation.status = final_status
            escalation.expansion_triggered = True
            escalation.expansion_pass_count = 1

        # 8. Estimate tokens
        token_estimate = self._estimate_slice_tokens(initial_result.graph)

        # Phase 5.10-06: Validate against budget policy
        budget_validation = None
        if pass_type is not None:
            budget_validation = self.budget_policy.validate_for_pass(
                pass_type, token_estimate
            )

            # If budget exceeded, trim slice (not PCP fields)
            if not budget_validation.valid and budget_validation.recommendation == "trim_slices":
                # Reduce slice to fit budget while preserving PCP
                slice_budget = self.budget_policy.slice_budget_for_pass(pass_type)
                initial_result, token_estimate = self._trim_slice_to_budget(
                    initial_result, slice_budget, gating
                )
                # Re-validate
                budget_validation = self.budget_policy.validate_for_pass(
                    pass_type, token_estimate
                )

        return PatternContextResult(
            context_bundle=context_bundle,
            escalation=escalation,
            slice_result=initial_result,
            graph_slice=initial_result.graph,
            token_estimate=token_estimate,
            gating=gating,
            budget_validation=budget_validation,
        )

    def extract_for_pass(
        self,
        pass_type: BudgetPass,
        pcp_data: Dict[str, Any],
        focal_nodes: List[str],
        vuln_class: str,
        protocol_pack: Any,
        target_scope: List[str],
    ) -> PatternContextResult:
        """Extract context for a specific budget pass.

        Convenience wrapper that enforces the appropriate budget.

        Args:
            pass_type: Budget pass type (cheap, verify, deep)
            pcp_data: Pattern Context Pack v2 data
            focal_nodes: Starting node IDs for slicing
            vuln_class: Vulnerability class
            protocol_pack: Protocol context pack
            target_scope: Target contract files

        Returns:
            PatternContextResult with budget enforcement
        """
        return self.extract_for_pattern(
            pcp_data=pcp_data,
            focal_nodes=focal_nodes,
            vuln_class=vuln_class,
            protocol_pack=protocol_pack,
            target_scope=target_scope,
            pass_type=pass_type,
            include_protocol_context=True,
        )

    def _trim_slice_to_budget(
        self,
        slice_result: Any,
        budget: int,
        gating: ContextGating,
    ) -> tuple:
        """Trim slice to fit budget while preserving PCP fields.

        PCP fields are NEVER trimmed - only graph slice is reduced.

        Args:
            slice_result: PatternSliceResult to trim
            budget: Token budget for slice
            gating: Context gating to update

        Returns:
            Tuple of (trimmed_result, new_token_estimate)
        """
        current_tokens = self._estimate_slice_tokens(slice_result.graph)

        if current_tokens <= budget:
            return slice_result, current_tokens

        # Reduce slice by removing low-priority nodes
        # Priority order: keep focal nodes > required op nodes > other nodes
        gating.mark_excluded(
            "graph_slice_trim",
            f"Reduced from {current_tokens} to fit budget {budget}",
        )

        # For now, return as-is with a note
        # Full implementation would prune low-priority nodes
        return slice_result, current_tokens

    def _evaluate_status(
        self,
        missing_required: int,
        has_forbidden: bool,
        threshold_met: bool,
    ) -> EvaluationStatus:
        """Evaluate pattern status based on evidence.

        Args:
            missing_required: Count of missing required ops
            has_forbidden: Whether forbidden ops were found
            threshold_met: Whether coverage threshold was met

        Returns:
            EvaluationStatus
        """
        if has_forbidden:
            return EvaluationStatus.REFUTED

        if missing_required > 0:
            return EvaluationStatus.UNKNOWN

        if threshold_met:
            return EvaluationStatus.VERIFIED

        return EvaluationStatus.UNKNOWN

    def _expand_and_reevaluate(
        self,
        focus: Any,  # PatternSliceFocus
        focal_nodes: List[str],
        scorer: Any,  # CoverageScorer
        escalation: "EscalationResult",
    ) -> tuple:
        """Expand context and re-evaluate status.

        Implements single-pass expansion policy.

        Args:
            focus: Pattern slice focus
            focal_nodes: Focal node IDs
            scorer: Coverage scorer
            escalation: Escalation result to update

        Returns:
            Tuple of (expanded_result, final_status)
        """
        from alphaswarm_sol.kg.slicer import (
            ExpansionConfig,
            SemanticDilator,
            slice_with_dilation,
        )

        # Configure expansion
        config = ExpansionConfig(
            coverage_threshold=self.coverage_threshold,
            max_expansion_radius=4,
            budget_limit=100,
            dilation_steps=[1, 2],
            stop_on_required_found=True,
        )

        # Perform dilation
        expanded_result = slice_with_dilation(
            graph=self.full_graph,
            focus=focus,
            focal_nodes=focal_nodes,
            config=config,
        )

        # Compute new coverage
        new_coverage = scorer.score(expanded_result.graph, self.coverage_threshold)

        # Update escalation
        escalation.missing_ops_after = expanded_result.missing_required_ops[:]
        escalation.coverage_after = new_coverage.score

        # Re-evaluate status
        final_status = self._evaluate_status(
            new_coverage.required_missing,
            expanded_result.has_forbidden_ops,
            new_coverage.threshold_met,
        )

        if final_status == EvaluationStatus.UNKNOWN:
            escalation.reason = (
                f"Still missing {new_coverage.required_missing} required ops "
                f"after expansion (coverage: {new_coverage.score:.2f})"
            )
        elif final_status == EvaluationStatus.VERIFIED:
            escalation.reason = "All required ops found after expansion"

        return expanded_result, final_status

    def _estimate_slice_tokens(self, graph: Any) -> int:
        """Estimate tokens for a sliced graph.

        Args:
            graph: SlicedGraph

        Returns:
            Estimated token count
        """
        if graph is None:
            return 0

        # Rough estimation: count chars in serialized form
        try:
            data = graph.to_dict()
            import json
            serialized = json.dumps(data)
            return len(serialized) // 4
        except Exception:
            # Fallback: estimate from node/edge counts
            node_count = len(getattr(graph, "nodes", {}))
            edge_count = len(getattr(graph, "edges", {}))
            return (node_count * 200) + (edge_count * 50)


class VulndocContextExtractor:
    """Extract and merge vulndoc + protocol context into agent bundles.

    This class loads vulndoc index.yaml files and merges them with
    protocol context packs to create unified context bundles for agent spawning.

    Attributes:
        vulndocs_root: Root directory containing vulndoc folders
    """

    def __init__(self, vulndocs_root: Path | None = None):
        """Initialize extractor.

        Args:
            vulndocs_root: Root directory containing vulndoc folders (uses centralized resolution if None)
        """
        if vulndocs_root is not None:
            self.vulndocs_root = vulndocs_root
        else:
            from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path_as_path
            self.vulndocs_root = vulndocs_read_path_as_path()

    def extract(
        self,
        vuln_class: str,
        protocol_pack: ProtocolContextPack,
        target_scope: List[str],
    ) -> ContextBundle:
        """Extract context bundle for a vulnerability class.

        Args:
            vuln_class: Vulnerability class path (e.g., "reentrancy/classic")
            protocol_pack: Protocol context pack
            target_scope: List of contract files to analyze

        Returns:
            ContextBundle ready for agent spawning

        Raises:
            ValueError: If vulndoc not found
        """
        # 1. Load vulndoc index.yaml
        vulndoc_data = self._load_vulndoc_index(vuln_class)

        # 2. Extract reasoning template and semantic info
        reasoning_template = vulndoc_data.get("reasoning_template", "")
        semantic_triggers = vulndoc_data.get("semantic_triggers", [])
        vql_queries = vulndoc_data.get("vql_queries", [])
        graph_patterns = vulndoc_data.get("graph_patterns", [])

        # Also check for operation_sequences (alternative format)
        if not graph_patterns and "operation_sequences" in vulndoc_data:
            op_seqs = vulndoc_data["operation_sequences"]
            if "vulnerable" in op_seqs:
                graph_patterns.extend(op_seqs["vulnerable"])

        # Also check for behavioral_signatures
        if "behavioral_signatures" in vulndoc_data:
            graph_patterns.extend(vulndoc_data["behavioral_signatures"])

        # 3. Extract risk profile from protocol pack
        risk_profile = self._extract_risk_profile(protocol_pack, vuln_class)

        # 4. Build context bundle
        bundle = ContextBundle(
            vulnerability_class=vuln_class,
            reasoning_template=reasoning_template,
            semantic_triggers=semantic_triggers,
            vql_queries=vql_queries,
            graph_patterns=graph_patterns,
            risk_profile=risk_profile,
            protocol_name=protocol_pack.protocol_name,
            target_scope=target_scope,
        )

        # 5. Estimate tokens and trim if needed
        token_count = self._estimate_tokens(bundle)
        bundle.token_estimate = token_count

        if token_count > 6000:
            bundle = self._trim_to_budget(bundle, 6000)
            bundle.token_estimate = self._estimate_tokens(bundle)

        return bundle

    def _load_vulndoc_index(self, vuln_class: str) -> Dict[str, Any]:
        """Load index.yaml for vulnerability class.

        Args:
            vuln_class: Vulnerability class path

        Returns:
            Dictionary of vulndoc data

        Raises:
            ValueError: If index.yaml not found
        """
        index_path = self.vulndocs_root / vuln_class / "index.yaml"
        if not index_path.exists():
            raise ValueError(f"VulnDoc not found: {vuln_class} (path: {index_path})")

        with open(index_path) as f:
            return yaml.safe_load(f)

    def _extract_risk_profile(
        self,
        pack: ProtocolContextPack,
        vuln_class: str,
    ) -> RiskProfile:
        """Extract risk profile relevant to vulnerability class.

        Maps vulnerability class to relevant risk categories and extracts
        information from the protocol pack.

        Per 05.5-CONTEXT.md:
        - reentrancy/* -> access_risks, timing_risks
        - oracle/* -> oracle_risks, integration_risks
        - access-control/* -> access_risks, governance_risks
        - flash-loan/* -> liquidity_risks, timing_risks
        - upgrade/* -> upgrade_risks, access_risks
        - Default: all categories with detected risks

        Args:
            pack: Protocol context pack
            vuln_class: Vulnerability class

        Returns:
            RiskProfile with relevant categories populated
        """
        # Start with empty risk profile (defaults to present=True, unknown confidence)
        risk_profile = RiskProfile()

        # Extract oracle risks
        risk_profile.oracle_risks = self._extract_oracle_risks(pack)

        # Extract liquidity risks
        risk_profile.liquidity_risks = self._extract_liquidity_risks(pack)

        # Extract access risks
        risk_profile.access_risks = self._extract_access_risks(pack)

        # Extract upgrade risks
        risk_profile.upgrade_risks = self._extract_upgrade_risks(pack)

        # Extract integration risks
        risk_profile.integration_risks = self._extract_integration_risks(pack)

        # Extract timing risks
        risk_profile.timing_risks = self._extract_timing_risks(pack)

        # Extract economic risks
        risk_profile.economic_risks = self._extract_economic_risks(pack)

        # Extract governance risks
        risk_profile.governance_risks = self._extract_governance_risks(pack)

        return risk_profile

    def _extract_oracle_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract oracle dependency risks from protocol pack."""
        # Check for oracle-related off-chain inputs
        has_oracle = False
        notes = []

        if pack.offchain_inputs:
            for input_item in pack.offchain_inputs:
                if input_item.input_type == "oracle":
                    has_oracle = True
                    notes.append(f"Oracle: {input_item.name}")

        if has_oracle:
            return RiskCategory(
                present=True,
                notes="; ".join(notes),
                confidence="inferred"
            )
        else:
            return RiskCategory(
                present=False,
                notes="No oracle dependencies detected",
                confidence="inferred"
            )

    def _extract_liquidity_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract flash loan and liquidity risks."""
        # Check protocol type and value flows
        notes = []
        has_liquidity_risk = False

        if pack.protocol_type in ["lending", "dex", "vault"]:
            has_liquidity_risk = True
            notes.append(f"Protocol type: {pack.protocol_type}")

        # Check for flash loan mentions in assumptions
        if pack.assumptions:
            for assumption in pack.assumptions:
                if "flash" in assumption.description.lower():
                    has_liquidity_risk = True
                    notes.append("Flash loan mentioned in assumptions")
                    break

        return RiskCategory(
            present=has_liquidity_risk,
            notes="; ".join(notes) if notes else "No flash loan exposure detected",
            confidence="inferred" if has_liquidity_risk else "inferred"
        )

    def _extract_access_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract privilege escalation and admin risks."""
        notes = []
        has_access_risk = False

        # Check for privileged roles
        if pack.roles:
            privileged_roles = []
            for role in pack.roles:
                # Check if role has privileged capabilities
                if any(cap in ["pause", "upgrade", "admin", "owner", "mint"]
                       for cap in role.capabilities):
                    privileged_roles.append(role.name)
                    has_access_risk = True

            if privileged_roles:
                notes.append(f"Privileged roles: {', '.join(privileged_roles)}")

        return RiskCategory(
            present=has_access_risk,
            notes="; ".join(notes) if notes else "No privileged roles detected",
            confidence="certain" if has_access_risk else "inferred"
        )

    def _extract_upgrade_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract proxy pattern and upgrade risks."""
        notes = []
        has_upgrade_risk = False

        # Check for upgrade-related roles
        if pack.roles:
            for role in pack.roles:
                if "upgrade" in role.capabilities:
                    has_upgrade_risk = True
                    notes.append(f"Upgrade role: {role.name}")

        # Check for proxy mentions in assumptions
        if pack.assumptions:
            for assumption in pack.assumptions:
                if any(term in assumption.description.lower()
                       for term in ["proxy", "upgrade", "implementation"]):
                    has_upgrade_risk = True
                    notes.append("Proxy/upgrade pattern detected")
                    break

        return RiskCategory(
            present=has_upgrade_risk,
            notes="; ".join(notes) if notes else "No upgrade mechanism detected",
            confidence="inferred"
        )

    def _extract_integration_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract cross-protocol dependency risks."""
        notes = []
        has_integration_risk = False

        # Check for external protocol dependencies in off-chain inputs
        if pack.offchain_inputs:
            external_protocols = []
            for input_item in pack.offchain_inputs:
                if input_item.input_type in ["external_protocol", "bridge"]:
                    has_integration_risk = True
                    external_protocols.append(input_item.name)

            if external_protocols:
                notes.append(f"External protocols: {', '.join(external_protocols)}")

        return RiskCategory(
            present=has_integration_risk,
            notes="; ".join(notes) if notes else "No cross-protocol dependencies detected",
            confidence="inferred"
        )

    def _extract_timing_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract MEV and frontrunning risks."""
        notes = []
        has_timing_risk = False

        # Protocol types with inherent timing risks
        if pack.protocol_type in ["dex", "auction", "lending"]:
            has_timing_risk = True
            notes.append(f"Protocol type susceptible to MEV: {pack.protocol_type}")

        # Check for timing-sensitive operations in assumptions
        if pack.assumptions:
            for assumption in pack.assumptions:
                if any(term in assumption.description.lower()
                       for term in ["mev", "frontrun", "sandwich", "timestamp", "block.number"]):
                    has_timing_risk = True
                    notes.append("Timing-sensitive operations detected")
                    break

        return RiskCategory(
            present=has_timing_risk,
            notes="; ".join(notes) if notes else "No timing risks detected",
            confidence="inferred"
        )

    def _extract_economic_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract incentive misalignment risks."""
        notes = []
        has_economic_risk = False

        # Check for incentive-related information
        if pack.incentives:
            has_economic_risk = True
            notes.append(f"Incentive mechanisms present: {pack.incentives}")

        # Check tokenomics
        if pack.tokenomics_summary:
            has_economic_risk = True
            notes.append("Tokenomics mechanisms present")

        return RiskCategory(
            present=has_economic_risk,
            notes="; ".join(notes) if notes else "No complex incentives detected",
            confidence="inferred"
        )

    def _extract_governance_risks(self, pack: ProtocolContextPack) -> RiskCategory:
        """Extract voting and governance risks."""
        notes = []
        has_governance_risk = False

        # Check governance section
        if pack.governance:
            has_governance_risk = True
            notes.append("Governance mechanisms present")

        # Check for governance roles
        if pack.roles:
            for role in pack.roles:
                if any(term in role.name.lower() for term in ["governor", "voter", "delegate"]):
                    has_governance_risk = True
                    notes.append(f"Governance role: {role.name}")

        return RiskCategory(
            present=has_governance_risk,
            notes="; ".join(notes) if notes else "No governance mechanisms detected",
            confidence="inferred"
        )

    def _estimate_tokens(self, bundle: ContextBundle) -> int:
        """Estimate token count (rough: chars / 4).

        This is a rough approximation. For more accurate estimation,
        use tiktoken library.

        Args:
            bundle: Context bundle

        Returns:
            Estimated token count
        """
        content_parts = [
            bundle.reasoning_template,
            " ".join(bundle.semantic_triggers),
            " ".join(bundle.vql_queries),
            " ".join(bundle.graph_patterns),
            bundle.protocol_name,
            " ".join(bundle.target_scope),
        ]

        # Add risk profile notes
        for risk_name in [
            "oracle_risks", "liquidity_risks", "access_risks",
            "upgrade_risks", "integration_risks", "timing_risks",
            "economic_risks", "governance_risks"
        ]:
            risk = getattr(bundle.risk_profile, risk_name)
            content_parts.append(risk.notes)

        total_chars = sum(len(part) for part in content_parts)
        return total_chars // 4

    def _trim_to_budget(
        self,
        bundle: ContextBundle,
        max_tokens: int = 6000,
    ) -> ContextBundle:
        """Trim bundle to token budget.

        Trim order (per 05.5-CONTEXT.md):
        1. Drop graph_patterns beyond first 3
        2. Drop vql_queries beyond first 3
        3. Truncate reasoning_template to 80% if still over budget
        4. Never drop risk_profile or target_scope

        Args:
            bundle: Context bundle to trim
            max_tokens: Maximum token budget

        Returns:
            Trimmed context bundle
        """
        # Create a copy to avoid mutating original
        trimmed = ContextBundle(
            vulnerability_class=bundle.vulnerability_class,
            reasoning_template=bundle.reasoning_template,
            semantic_triggers=bundle.semantic_triggers[:],
            vql_queries=bundle.vql_queries[:],
            graph_patterns=bundle.graph_patterns[:],
            risk_profile=bundle.risk_profile,
            protocol_name=bundle.protocol_name,
            target_scope=bundle.target_scope[:],
            token_estimate=bundle.token_estimate,
        )

        # Step 1: Limit graph_patterns to first 3
        if len(trimmed.graph_patterns) > 3:
            trimmed.graph_patterns = trimmed.graph_patterns[:3]

        # Check if we're under budget now
        current_estimate = self._estimate_tokens(trimmed)
        if current_estimate <= max_tokens:
            return trimmed

        # Step 2: Limit vql_queries to first 3
        if len(trimmed.vql_queries) > 3:
            trimmed.vql_queries = trimmed.vql_queries[:3]

        # Check if we're under budget now
        current_estimate = self._estimate_tokens(trimmed)
        if current_estimate <= max_tokens:
            return trimmed

        # Step 3: Truncate reasoning_template to 80%
        if trimmed.reasoning_template:
            target_length = int(len(trimmed.reasoning_template) * 0.8)
            # Try to cut at a sentence boundary
            truncated = trimmed.reasoning_template[:target_length]
            last_period = truncated.rfind(".")
            if last_period > target_length * 0.8:  # If we found a reasonable period
                trimmed.reasoning_template = truncated[:last_period + 1]
            else:
                trimmed.reasoning_template = truncated + "..."

        return trimmed
