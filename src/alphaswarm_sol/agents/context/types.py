"""Agent context types for vulnerability analysis.

This module defines types for merging vulndoc vulnerability knowledge
with protocol context pack data into unified context bundles for agent spawning.

Per 05.5-CONTEXT.md decisions:
- System prompt = vulndoc's reasoning_template (HOW to think)
- User context = protocol pack (WHAT to analyze)
- One vuln class per bundle (fresh context, focused reasoning)
- Token budget: target 2-4k, trim exploits/examples if >6k

Phase 5.10-06 additions:
- BudgetPolicy: Three-pass token budget management (cheap/verify/deep)
- ContextDelta: Delta-based context packing for verifier pass
- Context gating: Protocol context inclusion rules

Usage:
    from alphaswarm_sol.agents.context import ContextBundle, RiskProfile, RiskCategory
    from alphaswarm_sol.agents.context.types import BudgetPolicy, ContextDelta

    # Create risk profile
    risk_profile = RiskProfile(
        oracle_risks=RiskCategory(present=True, notes="Uses Chainlink"),
        liquidity_risks=RiskCategory(present=False, notes="No flash loan"),
        access_risks=RiskCategory(present=True, notes="Admin multisig")
    )

    # Create context bundle
    bundle = ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI pattern...",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE ..."],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=risk_profile,
        protocol_name="Aave V3",
        target_scope=["contracts/Pool.sol"],
        token_estimate=3500
    )

    # Create budget policy
    budget = BudgetPolicy()
    budget.validate_for_pass("cheap", bundle.token_estimate)

    # Convert to system prompt
    system_prompt = bundle.to_system_prompt()

    # Convert to user context
    user_context = bundle.to_user_context()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set


# =============================================================================
# Phase 5.10-06: Budget Policy for Three-Pass Execution
# =============================================================================


class BudgetPass(str, Enum):
    """Budget pass types for multi-pass vulnerability analysis."""

    CHEAP = "cheap"  # Initial scout pass, minimal context
    VERIFY = "verify"  # Verification pass, delta context from scout
    DEEP = "deep"  # Deep analysis pass, full context allowed


@dataclass
class BudgetPolicy:
    """Token budget policy for three-pass execution.

    Enforces token limits for each analysis pass:
    - Cheap pass: Fast initial scan with minimal context
    - Verify pass: Verification using delta context from scout
    - Deep pass: Full context for thorough analysis

    The policy ensures PCP (Protocol Context Pack) fields are never trimmed;
    only graph slices are reduced when budgets are exceeded.

    Attributes:
        cheap_pass_tokens: Token limit for cheap (scout) pass
        verify_pass_tokens: Token limit for verify pass
        deep_pass_tokens: Token limit for deep analysis pass
        hard_limit: Absolute maximum tokens (never exceed)
        soft_limit: Target budget (allow slight overflow)
        pcp_reserved: Tokens reserved for PCP fields (never trimmed)
        escalation_rules: Rules for escalating from cheap to verify to deep
    """

    cheap_pass_tokens: int = 2000
    verify_pass_tokens: int = 3000
    deep_pass_tokens: int = 6000
    hard_limit: int = 8000
    soft_limit: int = 6000
    pcp_reserved: int = 500  # Reserve for PCP fields (never trimmed)
    escalation_rules: Dict[str, str] = field(default_factory=lambda: {
        "unknown": "expand",  # If status unknown, escalate to expand
        "expand": "verify",  # After expansion, go to verify pass
        "verify": "deep",  # If verify inconclusive, go to deep
        "deep": "manual",  # After deep, manual review needed
    })

    def budget_for_pass(self, pass_type: BudgetPass) -> int:
        """Get token budget for a specific pass.

        Args:
            pass_type: The pass type

        Returns:
            Token budget for the pass
        """
        budgets = {
            BudgetPass.CHEAP: self.cheap_pass_tokens,
            BudgetPass.VERIFY: self.verify_pass_tokens,
            BudgetPass.DEEP: self.deep_pass_tokens,
        }
        return budgets.get(pass_type, self.soft_limit)

    def slice_budget_for_pass(self, pass_type: BudgetPass) -> int:
        """Get slice-only budget (excluding PCP reserved).

        Args:
            pass_type: The pass type

        Returns:
            Token budget for graph slice (total - pcp_reserved)
        """
        return self.budget_for_pass(pass_type) - self.pcp_reserved

    def validate_for_pass(
        self,
        pass_type: BudgetPass,
        token_count: int,
    ) -> "BudgetValidation":
        """Validate token count against pass budget.

        Args:
            pass_type: The pass type
            token_count: Current token count

        Returns:
            BudgetValidation with status and recommendations
        """
        budget = self.budget_for_pass(pass_type)

        if token_count <= budget:
            return BudgetValidation(
                valid=True,
                pass_type=pass_type,
                budget=budget,
                actual=token_count,
                overflow=0,
                recommendation="within_budget",
            )

        if token_count <= self.soft_limit:
            return BudgetValidation(
                valid=True,
                pass_type=pass_type,
                budget=budget,
                actual=token_count,
                overflow=token_count - budget,
                recommendation="soft_overflow_allowed",
            )

        if token_count <= self.hard_limit:
            return BudgetValidation(
                valid=False,
                pass_type=pass_type,
                budget=budget,
                actual=token_count,
                overflow=token_count - budget,
                recommendation="trim_slices",
            )

        return BudgetValidation(
            valid=False,
            pass_type=pass_type,
            budget=budget,
            actual=token_count,
            overflow=token_count - self.hard_limit,
            recommendation="exceeds_hard_limit",
        )

    def next_escalation(self, current_state: str) -> str:
        """Get next escalation state.

        Args:
            current_state: Current state (unknown, expand, verify, deep)

        Returns:
            Next state per escalation rules
        """
        return self.escalation_rules.get(current_state, "manual")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "cheap_pass_tokens": self.cheap_pass_tokens,
            "verify_pass_tokens": self.verify_pass_tokens,
            "deep_pass_tokens": self.deep_pass_tokens,
            "hard_limit": self.hard_limit,
            "soft_limit": self.soft_limit,
            "pcp_reserved": self.pcp_reserved,
            "escalation_rules": self.escalation_rules,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetPolicy":
        """Deserialize from dictionary."""
        return cls(
            cheap_pass_tokens=data.get("cheap_pass_tokens", 2000),
            verify_pass_tokens=data.get("verify_pass_tokens", 3000),
            deep_pass_tokens=data.get("deep_pass_tokens", 6000),
            hard_limit=data.get("hard_limit", 8000),
            soft_limit=data.get("soft_limit", 6000),
            pcp_reserved=data.get("pcp_reserved", 500),
            escalation_rules=data.get("escalation_rules", {}),
        )

    @classmethod
    def default(cls) -> "BudgetPolicy":
        """Create default budget policy."""
        return cls()

    @classmethod
    def conservative(cls) -> "BudgetPolicy":
        """Create conservative (lower budgets) policy."""
        return cls(
            cheap_pass_tokens=1500,
            verify_pass_tokens=2500,
            deep_pass_tokens=5000,
            soft_limit=5000,
        )

    @classmethod
    def aggressive(cls) -> "BudgetPolicy":
        """Create aggressive (higher budgets) policy."""
        return cls(
            cheap_pass_tokens=3000,
            verify_pass_tokens=4500,
            deep_pass_tokens=7500,
            soft_limit=7500,
        )


@dataclass
class BudgetValidation:
    """Result of budget validation.

    Attributes:
        valid: Whether token count is acceptable
        pass_type: The pass type validated
        budget: The budget limit for this pass
        actual: Actual token count
        overflow: Amount over budget (0 if under)
        recommendation: Action recommendation
    """

    valid: bool
    pass_type: BudgetPass
    budget: int
    actual: int
    overflow: int
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "valid": self.valid,
            "pass_type": self.pass_type.value,
            "budget": self.budget,
            "actual": self.actual,
            "overflow": self.overflow,
            "recommendation": self.recommendation,
        }


# =============================================================================
# Phase 5.10-06: Context Delta for Verifier Pass
# =============================================================================


@dataclass
class ContextDelta:
    """Delta between scout slice and verifier slice.

    Used for verify pass to send only new/changed context instead
    of full context. This reduces token usage by sending deltas.

    The delta includes:
    - Added nodes/edges not in scout context
    - Evidence IDs that need verification
    - Property changes (if any properties differ)

    Evidence IDs are sorted deterministically for reproducibility.

    Attributes:
        added_node_ids: Node IDs added since scout pass
        added_edge_ids: Edge IDs added since scout pass
        removed_node_ids: Node IDs removed (rare, for debugging)
        evidence_ids: Evidence IDs to verify (sorted)
        property_changes: Properties that changed values
        scout_coverage: Coverage score from scout pass
        delta_tokens: Estimated tokens for delta only
    """

    added_node_ids: List[str] = field(default_factory=list)
    added_edge_ids: List[str] = field(default_factory=list)
    removed_node_ids: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    property_changes: Dict[str, Any] = field(default_factory=dict)
    scout_coverage: float = 0.0
    delta_tokens: int = 0

    def is_empty(self) -> bool:
        """Check if delta is empty (no changes)."""
        return (
            not self.added_node_ids
            and not self.added_edge_ids
            and not self.removed_node_ids
            and not self.evidence_ids
            and not self.property_changes
        )

    def node_count(self) -> int:
        """Get count of nodes affected by delta."""
        return len(self.added_node_ids) + len(self.removed_node_ids)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with deterministic ordering."""
        return {
            "added_node_ids": sorted(self.added_node_ids),
            "added_edge_ids": sorted(self.added_edge_ids),
            "removed_node_ids": sorted(self.removed_node_ids),
            "evidence_ids": sorted(self.evidence_ids),
            "property_changes": self.property_changes,
            "scout_coverage": round(self.scout_coverage, 4),
            "delta_tokens": self.delta_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextDelta":
        """Deserialize from dictionary."""
        return cls(
            added_node_ids=list(data.get("added_node_ids", [])),
            added_edge_ids=list(data.get("added_edge_ids", [])),
            removed_node_ids=list(data.get("removed_node_ids", [])),
            evidence_ids=list(data.get("evidence_ids", [])),
            property_changes=dict(data.get("property_changes", {})),
            scout_coverage=float(data.get("scout_coverage", 0.0)),
            delta_tokens=int(data.get("delta_tokens", 0)),
        )

    @classmethod
    def compute(
        cls,
        scout_node_ids: Set[str],
        scout_edge_ids: Set[str],
        verifier_node_ids: Set[str],
        verifier_edge_ids: Set[str],
        evidence_ids: Optional[List[str]] = None,
        scout_coverage: float = 0.0,
    ) -> "ContextDelta":
        """Compute delta between scout and verifier slices.

        Args:
            scout_node_ids: Node IDs from scout pass
            scout_edge_ids: Edge IDs from scout pass
            verifier_node_ids: Node IDs for verifier pass
            verifier_edge_ids: Edge IDs for verifier pass
            evidence_ids: Evidence IDs to include
            scout_coverage: Coverage from scout pass

        Returns:
            ContextDelta with deterministic ordering
        """
        added_nodes = sorted(verifier_node_ids - scout_node_ids)
        added_edges = sorted(verifier_edge_ids - scout_edge_ids)
        removed_nodes = sorted(scout_node_ids - verifier_node_ids)

        # Sort evidence IDs deterministically
        sorted_evidence = sorted(evidence_ids) if evidence_ids else []

        # Estimate delta tokens (rough: 100 tokens per node, 20 per edge, 10 per evidence)
        delta_tokens = (
            len(added_nodes) * 100
            + len(added_edges) * 20
            + len(sorted_evidence) * 10
        )

        return cls(
            added_node_ids=added_nodes,
            added_edge_ids=added_edges,
            removed_node_ids=removed_nodes,
            evidence_ids=sorted_evidence,
            scout_coverage=scout_coverage,
            delta_tokens=delta_tokens,
        )


# =============================================================================
# Phase 5.10-06: Context Gating Metadata
# =============================================================================


@dataclass
class ContextGating:
    """Metadata for context gating decisions.

    Tracks which context sources were included/excluded and why.
    Used for auditing and debugging context packing decisions.

    Attributes:
        protocol_context_included: Whether PCP was included
        protocol_context_reason: Why included/excluded
        graph_slice_included: Whether graph slice was included
        graph_slice_reason: Why included/excluded
        vulndoc_included: Whether vulndoc was included
        vulndoc_reason: Why included/excluded
        unknowns_marked: List of items marked unknown due to missing context
        exclusions: List of explicitly excluded items
    """

    protocol_context_included: bool = True
    protocol_context_reason: str = "default"
    graph_slice_included: bool = True
    graph_slice_reason: str = "default"
    vulndoc_included: bool = True
    vulndoc_reason: str = "default"
    unknowns_marked: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)

    def mark_unknown(self, item: str, reason: str) -> None:
        """Mark an item as unknown due to missing context.

        Args:
            item: Item identifier
            reason: Why it's marked unknown
        """
        self.unknowns_marked.append(f"{item}: {reason}")

    def mark_excluded(self, item: str, reason: str) -> None:
        """Mark an item as explicitly excluded.

        Args:
            item: Item identifier
            reason: Why it's excluded
        """
        self.exclusions.append(f"{item}: {reason}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "protocol_context_included": self.protocol_context_included,
            "protocol_context_reason": self.protocol_context_reason,
            "graph_slice_included": self.graph_slice_included,
            "graph_slice_reason": self.graph_slice_reason,
            "vulndoc_included": self.vulndoc_included,
            "vulndoc_reason": self.vulndoc_reason,
            "unknowns_marked": self.unknowns_marked,
            "exclusions": self.exclusions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextGating":
        """Deserialize from dictionary."""
        return cls(
            protocol_context_included=data.get("protocol_context_included", True),
            protocol_context_reason=data.get("protocol_context_reason", "default"),
            graph_slice_included=data.get("graph_slice_included", True),
            graph_slice_reason=data.get("graph_slice_reason", "default"),
            vulndoc_included=data.get("vulndoc_included", True),
            vulndoc_reason=data.get("vulndoc_reason", "default"),
            unknowns_marked=list(data.get("unknowns_marked", [])),
            exclusions=list(data.get("exclusions", [])),
        )


class ContextSection(Enum):
    """Sections within a context bundle.

    Used for selective retrieval and token budget management.
    """
    REASONING_TEMPLATE = "reasoning_template"
    SEMANTIC_TRIGGERS = "semantic_triggers"
    VQL_QUERIES = "vql_queries"
    GRAPH_PATTERNS = "graph_patterns"
    RISK_PROFILE = "risk_profile"
    TARGET_SCOPE = "target_scope"


@dataclass
class RiskCategory:
    """Single risk category with presence indicator and notes.

    Conservative default: Unknown exposure = assume present.
    Better false positives than missed vulnerabilities.

    Attributes:
        present: Whether this risk type is detected
        notes: Freeform notes about the risk
        confidence: Level of certainty ("certain", "inferred", "unknown")
    """
    present: bool = True  # Default: assume present
    notes: str = ""
    confidence: str = "unknown"  # certain, inferred, unknown

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "present": self.present,
            "notes": self.notes,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskCategory":
        """Deserialize from dictionary."""
        return cls(
            present=data.get("present", True),
            notes=data.get("notes", ""),
            confidence=data.get("confidence", "unknown"),
        )


@dataclass
class RiskProfile:
    """Protocol risk profile extracted from context pack.

    Covers 8 risk categories relevant for vulnerability analysis.
    Each category has presence indicator + freeform notes.

    Attributes:
        oracle_risks: Oracle dependencies, price feed exposure
        liquidity_risks: Flash loan exposure, liquidity depth
        access_risks: Privilege escalation, admin key risks
        upgrade_risks: Proxy patterns, implementation changes
        integration_risks: Cross-protocol dependencies
        timing_risks: MEV, frontrunning exposure
        economic_risks: Incentive misalignment, game theory
        governance_risks: Voting manipulation, timelock bypass
    """
    oracle_risks: RiskCategory = field(default_factory=RiskCategory)
    liquidity_risks: RiskCategory = field(default_factory=RiskCategory)
    access_risks: RiskCategory = field(default_factory=RiskCategory)
    upgrade_risks: RiskCategory = field(default_factory=RiskCategory)
    integration_risks: RiskCategory = field(default_factory=RiskCategory)
    timing_risks: RiskCategory = field(default_factory=RiskCategory)
    economic_risks: RiskCategory = field(default_factory=RiskCategory)
    governance_risks: RiskCategory = field(default_factory=RiskCategory)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "oracle_risks": self.oracle_risks.to_dict(),
            "liquidity_risks": self.liquidity_risks.to_dict(),
            "access_risks": self.access_risks.to_dict(),
            "upgrade_risks": self.upgrade_risks.to_dict(),
            "integration_risks": self.integration_risks.to_dict(),
            "timing_risks": self.timing_risks.to_dict(),
            "economic_risks": self.economic_risks.to_dict(),
            "governance_risks": self.governance_risks.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskProfile":
        """Deserialize from dictionary."""
        return cls(
            oracle_risks=RiskCategory.from_dict(data.get("oracle_risks", {})),
            liquidity_risks=RiskCategory.from_dict(data.get("liquidity_risks", {})),
            access_risks=RiskCategory.from_dict(data.get("access_risks", {})),
            upgrade_risks=RiskCategory.from_dict(data.get("upgrade_risks", {})),
            integration_risks=RiskCategory.from_dict(data.get("integration_risks", {})),
            timing_risks=RiskCategory.from_dict(data.get("timing_risks", {})),
            economic_risks=RiskCategory.from_dict(data.get("economic_risks", {})),
            governance_risks=RiskCategory.from_dict(data.get("governance_risks", {})),
        )

    def get_relevant_for_vuln_class(self, vuln_class: str) -> Dict[str, RiskCategory]:
        """Get risk categories relevant for a vulnerability class.

        Mapping per 05.5-CONTEXT.md:
        - reentrancy/* -> access_risks, timing_risks
        - oracle/* -> oracle_risks, integration_risks
        - access-control/* -> access_risks, governance_risks
        - flash-loan/* -> liquidity_risks, timing_risks
        - upgrade/* -> upgrade_risks, access_risks
        - Default: all categories with present=True

        Args:
            vuln_class: Vulnerability class (e.g., "reentrancy/classic")

        Returns:
            Dictionary of relevant risk categories
        """
        # Extract category from vuln_class
        category = vuln_class.split("/")[0] if "/" in vuln_class else vuln_class

        # Mapping from vuln category to relevant risk categories
        mappings = {
            "reentrancy": ["access_risks", "timing_risks"],
            "oracle": ["oracle_risks", "integration_risks"],
            "access-control": ["access_risks", "governance_risks"],
            "flash-loan": ["liquidity_risks", "timing_risks"],
            "upgrade": ["upgrade_risks", "access_risks"],
        }

        relevant_keys = mappings.get(category)

        if relevant_keys:
            # Return only specified categories
            result = {}
            for key in relevant_keys:
                result[key] = getattr(self, key)
            return result
        else:
            # Default: return all categories that are present
            result = {}
            for key in [
                "oracle_risks", "liquidity_risks", "access_risks",
                "upgrade_risks", "integration_risks", "timing_risks",
                "economic_risks", "governance_risks"
            ]:
                risk = getattr(self, key)
                if risk.present:
                    result[key] = risk
            return result


@dataclass
class ContextBundle:
    """Unified context bundle merging vulndoc + protocol pack.

    This bundle provides everything a vulnerability analysis agent needs:
    - HOW to think (reasoning template from vulndoc)
    - WHAT to analyze (protocol context from pack)

    One vulnerability class per bundle for focused reasoning.

    Attributes:
        vulnerability_class: Vuln class (e.g., "reentrancy/classic")
        reasoning_template: Step-by-step detection methodology
        semantic_triggers: Operations to look for
        vql_queries: Pre-run query hints
        graph_patterns: Vulnerable operation sequences
        risk_profile: Protocol risk categories
        protocol_name: Protocol being analyzed
        target_scope: Contract files in scope
        token_estimate: Estimated token count
    """
    vulnerability_class: str
    reasoning_template: str
    semantic_triggers: List[str]
    vql_queries: List[str]
    graph_patterns: List[str]
    risk_profile: RiskProfile
    protocol_name: str
    target_scope: List[str]
    token_estimate: int = 0

    def to_system_prompt(self) -> str:
        """Convert bundle to system prompt format.

        System prompt contains the reasoning methodology (HOW to think).

        Returns:
            Formatted system prompt string
        """
        sections = []

        # Header
        sections.append(f"# Vulnerability Analysis: {self.vulnerability_class}")
        sections.append("")

        # Reasoning template
        sections.append("## Detection Methodology")
        sections.append("")
        sections.append(self.reasoning_template)
        sections.append("")

        # Semantic triggers
        sections.append("## Semantic Triggers")
        sections.append("")
        sections.append("Look for these operations:")
        for trigger in self.semantic_triggers:
            sections.append(f"- {trigger}")
        sections.append("")

        # Graph patterns
        if self.graph_patterns:
            sections.append("## Vulnerable Patterns")
            sections.append("")
            sections.append("Look for these operation sequences:")
            for pattern in self.graph_patterns:
                sections.append(f"- {pattern}")
            sections.append("")

        # VQL query hints
        if self.vql_queries:
            sections.append("## Starting Queries")
            sections.append("")
            sections.append("Begin investigation with these VQL queries:")
            for query in self.vql_queries:
                sections.append(f"- {query}")
            sections.append("")

        return "\n".join(sections)

    def to_user_context(self) -> str:
        """Convert bundle to user context format.

        User context contains protocol-specific information (WHAT to analyze).

        Returns:
            Formatted user context string
        """
        sections = []

        # Header
        sections.append(f"# Protocol: {self.protocol_name}")
        sections.append("")

        # Target scope
        sections.append("## Target Scope")
        sections.append("")
        for file in self.target_scope:
            sections.append(f"- {file}")
        sections.append("")

        # Risk profile
        sections.append("## Risk Profile")
        sections.append("")
        relevant_risks = self.risk_profile.get_relevant_for_vuln_class(
            self.vulnerability_class
        )

        if relevant_risks:
            for risk_name, risk_cat in relevant_risks.items():
                # Format risk name nicely
                display_name = risk_name.replace("_", " ").title()
                sections.append(f"### {display_name}")
                sections.append(f"**Present:** {'Yes' if risk_cat.present else 'No'}")
                if risk_cat.notes:
                    sections.append(f"**Notes:** {risk_cat.notes}")
                sections.append(f"**Confidence:** {risk_cat.confidence}")
                sections.append("")
        else:
            sections.append("No specific risks identified for this vulnerability class.")
            sections.append("")

        return "\n".join(sections)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "vulnerability_class": self.vulnerability_class,
            "reasoning_template": self.reasoning_template,
            "semantic_triggers": self.semantic_triggers,
            "vql_queries": self.vql_queries,
            "graph_patterns": self.graph_patterns,
            "risk_profile": self.risk_profile.to_dict(),
            "protocol_name": self.protocol_name,
            "target_scope": self.target_scope,
            "token_estimate": self.token_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextBundle":
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ContextBundle instance
        """
        return cls(
            vulnerability_class=data["vulnerability_class"],
            reasoning_template=data["reasoning_template"],
            semantic_triggers=data["semantic_triggers"],
            vql_queries=data["vql_queries"],
            graph_patterns=data["graph_patterns"],
            risk_profile=RiskProfile.from_dict(data["risk_profile"]),
            protocol_name=data["protocol_name"],
            target_scope=data["target_scope"],
            token_estimate=data.get("token_estimate", 0),
        )
