"""Bead context inheritance for vulnerability investigation.

Per 03-CONTEXT.md: "Each bead inherits relevant context pack sections automatically"

This module provides:
- BeadContext: Context pack sections relevant to a bead
- BeadContextProvider: Service that provides context for beads

The bead context system enables LLM investigations to receive targeted
protocol context without loading the full context pack, supporting
efficient token usage while maintaining investigation quality.

Usage:
    from alphaswarm_sol.context.integrations import BeadContext, BeadContextProvider
    from alphaswarm_sol.context import ProtocolContextPack
    from alphaswarm_sol.beads import VulnerabilityBead

    # Load context pack
    pack = ProtocolContextPack.from_dict(yaml_data)

    # Create provider
    provider = BeadContextProvider(pack)

    # Get context for a bead
    ctx = provider.get_context_for_bead(
        vulnerability_class="reentrancy",
        function_name="withdraw",
        semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        max_tokens=2000,
    )

    # Format for LLM prompt
    prompt_section = ctx.to_prompt_section()

    # Or enrich an existing bead
    enriched_bead = provider.enrich_bead(bead)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .evidence import (
    EvidenceContextProvider,
    VULN_CLASS_TO_ASSUMPTION_CATEGORIES,
    VULN_CLASS_TO_CAPABILITIES,
)

if TYPE_CHECKING:
    from ..schema import ProtocolContextPack
    from ...beads.schema import VulnerabilityBead


@dataclass
class BeadContext:
    """Context pack sections relevant to a bead.

    Provides targeted context for LLM investigation without
    loading the full context pack.

    Per 03-CONTEXT.md: Designed for minimal, targeted retrieval
    (sections independently addressable)

    Attributes:
        protocol_name: Name of the protocol
        protocol_type: Type of protocol (lending, dex, etc.)
        relevant_roles: Roles relevant to this finding
        relevant_assumptions: Assumptions relevant to investigation
        relevant_invariants: Invariants that might be violated
        offchain_dependencies: Off-chain dependencies for this function
        security_model_summary: Summary of security model
        matching_accepted_risks: Accepted risks that might match this finding
        token_estimate: Estimated token count for budgeting

    Usage:
        ctx = BeadContext(
            protocol_name="Aave V3",
            protocol_type="lending",
            relevant_roles=[{"name": "admin", "capabilities": ["pause"]}],
            relevant_assumptions=["Oracle provides accurate prices"],
            relevant_invariants=["Total supply <= max supply"],
            security_model_summary="Trust multisig admin for emergency actions",
            token_estimate=450,
        )

        # Format for prompt
        prompt = ctx.to_prompt_section()
    """

    # Protocol overview
    protocol_name: str = ""
    protocol_type: str = ""

    # Relevant roles for this finding
    relevant_roles: List[Dict[str, Any]] = field(default_factory=list)

    # Relevant assumptions
    relevant_assumptions: List[str] = field(default_factory=list)

    # Relevant invariants (if any might be violated)
    relevant_invariants: List[str] = field(default_factory=list)

    # Off-chain dependencies
    offchain_dependencies: List[str] = field(default_factory=list)

    # Security model summary
    security_model_summary: str = ""

    # Accepted risks that might match
    matching_accepted_risks: List[str] = field(default_factory=list)

    # Token estimate for context budgeting
    token_estimate: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for bead integration.

        Returns:
            Dictionary with all context fields
        """
        return {
            "protocol_name": self.protocol_name,
            "protocol_type": self.protocol_type,
            "relevant_roles": self.relevant_roles,
            "relevant_assumptions": self.relevant_assumptions,
            "relevant_invariants": self.relevant_invariants,
            "offchain_dependencies": self.offchain_dependencies,
            "security_model_summary": self.security_model_summary,
            "matching_accepted_risks": self.matching_accepted_risks,
            "token_estimate": self.token_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeadContext":
        """Create from dict.

        Args:
            data: Dictionary with context fields

        Returns:
            BeadContext instance
        """
        return cls(
            protocol_name=str(data.get("protocol_name", "")),
            protocol_type=str(data.get("protocol_type", "")),
            relevant_roles=list(data.get("relevant_roles", [])),
            relevant_assumptions=list(data.get("relevant_assumptions", [])),
            relevant_invariants=list(data.get("relevant_invariants", [])),
            offchain_dependencies=list(data.get("offchain_dependencies", [])),
            security_model_summary=str(data.get("security_model_summary", "")),
            matching_accepted_risks=list(data.get("matching_accepted_risks", [])),
            token_estimate=int(data.get("token_estimate", 0)),
        )

    def to_prompt_section(self) -> str:
        """Format as prompt section for LLM consumption.

        Creates a structured, human-readable section that can be
        included in LLM prompts for vulnerability investigation.

        Returns:
            Formatted prompt section string
        """
        lines = []

        # Header
        lines.append("## Protocol Context")
        lines.append("")

        # Protocol overview
        if self.protocol_name or self.protocol_type:
            overview = self.protocol_name or "Unknown Protocol"
            if self.protocol_type:
                overview += f" ({self.protocol_type})"
            lines.append(f"**Protocol:** {overview}")
            lines.append("")

        # Security model
        if self.security_model_summary:
            lines.append(f"**Security Model:** {self.security_model_summary}")
            lines.append("")

        # Relevant roles
        if self.relevant_roles:
            lines.append("**Relevant Roles:**")
            for role in self.relevant_roles:
                name = role.get("name", "unknown")
                caps = role.get("capabilities", [])
                trust = role.get("trust_assumptions", [])

                lines.append(f"- **{name}**")
                if caps:
                    lines.append(f"  - Capabilities: {', '.join(caps[:5])}")
                if trust:
                    lines.append(f"  - Trust: {trust[0]}")
            lines.append("")

        # Relevant assumptions
        if self.relevant_assumptions:
            lines.append("**Relevant Assumptions:**")
            for assumption in self.relevant_assumptions:
                lines.append(f"- {assumption}")
            lines.append("")

        # Relevant invariants
        if self.relevant_invariants:
            lines.append("**Relevant Invariants:**")
            for invariant in self.relevant_invariants:
                lines.append(f"- {invariant}")
            lines.append("")

        # Off-chain dependencies
        if self.offchain_dependencies:
            lines.append("**Off-chain Dependencies:**")
            for dep in self.offchain_dependencies:
                lines.append(f"- {dep}")
            lines.append("")

        # Accepted risks note
        if self.matching_accepted_risks:
            lines.append("**Note - Accepted Risks:**")
            lines.append("The following behaviors are documented as accepted risks:")
            for risk in self.matching_accepted_risks:
                lines.append(f"- {risk}")
            lines.append("")

        return "\n".join(lines)

    def has_context(self) -> bool:
        """Check if any meaningful context was found.

        Returns:
            True if at least one context field is populated
        """
        return bool(
            self.protocol_name
            or self.relevant_roles
            or self.relevant_assumptions
            or self.relevant_invariants
            or self.offchain_dependencies
            or self.security_model_summary
        )


class BeadContextProvider:
    """Provides context for vulnerability beads.

    Inherits relevant sections from context pack based on:
    - Vulnerability class
    - Function being analyzed
    - Semantic operations involved

    Per 03-CONTEXT.md: Each bead inherits relevant context pack sections
    automatically.

    Attributes:
        pack: The ProtocolContextPack to extract context from
        evidence_provider: Optional EvidenceContextProvider for reuse

    Usage:
        provider = BeadContextProvider(context_pack)

        # Get context for a new bead
        ctx = provider.get_context_for_bead(
            vulnerability_class="reentrancy",
            function_name="withdraw",
            semantic_ops=["TRANSFERS_VALUE_OUT"],
            max_tokens=2000,
        )

        # Or enrich an existing bead
        enriched = provider.enrich_bead(existing_bead)
    """

    def __init__(
        self,
        context_pack: "ProtocolContextPack",
        evidence_provider: Optional[EvidenceContextProvider] = None,
    ):
        """Initialize with a context pack.

        Args:
            context_pack: ProtocolContextPack to provide context from
            evidence_provider: Optional EvidenceContextProvider for reuse.
                If not provided, one will be created.
        """
        self.pack = context_pack
        self.evidence_provider = evidence_provider or EvidenceContextProvider(context_pack)

    def get_context_for_bead(
        self,
        vulnerability_class: str,
        function_name: str,
        semantic_ops: List[str],
        max_tokens: int = 2000,
    ) -> BeadContext:
        """Get relevant context for a bead.

        Per 03-CONTEXT.md: Designed for minimal, targeted retrieval
        (sections independently addressable)

        Args:
            vulnerability_class: Type of vulnerability (e.g., "reentrancy")
            function_name: Function being analyzed
            semantic_ops: VKG semantic operations in the function
            max_tokens: Maximum token budget for context

        Returns:
            BeadContext with relevant sections
        """
        # Select relevant roles
        relevant_roles = self._select_relevant_roles(function_name, vulnerability_class)

        # Get relevant assumptions
        assumptions = self.evidence_provider.get_relevant_assumptions(
            function_name, semantic_ops
        )
        relevant_assumptions = [a.description for a in assumptions]

        # Get relevant invariants
        relevant_invariants = self._select_relevant_invariants(
            vulnerability_class, semantic_ops
        )

        # Get off-chain dependencies
        offchain = self.evidence_provider.get_offchain_dependencies(
            function_name, semantic_ops
        )
        offchain_deps = [o.name for o in offchain]

        # Build security model summary
        security_summary = self._build_security_summary()

        # Check for matching accepted risks
        matching_risks = self._find_matching_accepted_risks(
            vulnerability_class, function_name
        )

        # Create context
        context = BeadContext(
            protocol_name=self.pack.protocol_name,
            protocol_type=self.pack.protocol_type,
            relevant_roles=relevant_roles,
            relevant_assumptions=relevant_assumptions,
            relevant_invariants=relevant_invariants,
            offchain_dependencies=offchain_deps,
            security_model_summary=security_summary,
            matching_accepted_risks=matching_risks,
        )

        # Estimate tokens
        context.token_estimate = self._estimate_tokens(context)

        # Trim if over budget
        if context.token_estimate > max_tokens:
            context = self._trim_context(context, max_tokens)

        return context

    def _select_relevant_roles(
        self,
        function_name: str,
        vulnerability_class: str,
    ) -> List[Dict[str, Any]]:
        """Select roles relevant to this investigation.

        For access-control findings: all roles with relevant capabilities
        For reentrancy: roles that can trigger external calls
        For oracle: roles that can update prices

        Args:
            function_name: Function being analyzed
            vulnerability_class: Type of vulnerability

        Returns:
            List of role dicts with name, capabilities, trust_assumptions
        """
        relevant = []

        # Get capabilities relevant to this vulnerability
        relevant_caps = VULN_CLASS_TO_CAPABILITIES.get(vulnerability_class, [])

        for role in self.pack.roles:
            is_relevant = False

            # Check if role has relevant capabilities
            if relevant_caps:
                for cap in role.capabilities:
                    cap_lower = cap.lower()
                    if any(rc.lower() in cap_lower for rc in relevant_caps):
                        is_relevant = True
                        break

            # Check if role name appears in function name
            if role.name.lower() in function_name.lower():
                is_relevant = True

            # For access-control vulnerabilities, include all roles
            if vulnerability_class in ("access-control", "privilege-escalation"):
                is_relevant = True

            if is_relevant:
                relevant.append(self._format_role_for_context(role))

        return relevant[:5]  # Limit to 5 roles

    def _format_role_for_context(self, role: Any) -> Dict[str, Any]:
        """Format a role for bead context.

        Args:
            role: Role object

        Returns:
            Dict with role information
        """
        return {
            "name": role.name,
            "capabilities": role.capabilities[:5],  # Limit capabilities
            "trust_assumptions": role.trust_assumptions[:2],  # Limit trust assumptions
            "confidence": role.confidence.value,
        }

    def _select_relevant_invariants(
        self,
        vulnerability_class: str,
        semantic_ops: List[str],
    ) -> List[str]:
        """Select invariants relevant to this investigation.

        Args:
            vulnerability_class: Type of vulnerability
            semantic_ops: VKG semantic operations

        Returns:
            List of invariant descriptions
        """
        relevant = []

        # Map vulnerability classes to invariant categories
        vuln_to_invariant_categories: Dict[str, List[str]] = {
            "reentrancy": ["balance", "state"],
            "access-control": ["access"],
            "arithmetic": ["supply", "balance", "economic"],
            "oracle-manipulation": ["economic", "price"],
            "flash-loan": ["balance", "economic"],
            "dos": ["economic"],
        }

        relevant_categories = vuln_to_invariant_categories.get(vulnerability_class, [])

        # Always include critical invariants
        for invariant in self.pack.invariants:
            if invariant.critical:
                relevant.append(invariant.natural_language)
                continue

            # Check category match
            if invariant.category.lower() in relevant_categories:
                relevant.append(invariant.natural_language)

        # Check operations for supply/balance invariants
        if any(op in semantic_ops for op in ("WRITES_USER_BALANCE", "READS_USER_BALANCE")):
            for invariant in self.pack.invariants:
                if invariant.is_balance_invariant():
                    if invariant.natural_language not in relevant:
                        relevant.append(invariant.natural_language)

        return relevant[:5]  # Limit to 5 invariants

    def _build_security_summary(self) -> str:
        """Build a concise security model summary.

        Returns:
            Security model summary string
        """
        parts = []

        if self.pack.security_model:
            # Trust model
            if "trust_model" in self.pack.security_model:
                parts.append(self.pack.security_model["trust_model"])

            # Threat model
            if "threat_model" in self.pack.security_model:
                parts.append(f"Threats: {self.pack.security_model['threat_model']}")

            # Admin trust level
            if "admin_trust" in self.pack.security_model:
                parts.append(f"Admin: {self.pack.security_model['admin_trust']}")

        if parts:
            return ". ".join(parts)

        # Default based on protocol type
        type_defaults: Dict[str, str] = {
            "lending": "Lending protocol with oracle-dependent liquidations",
            "dex": "DEX with AMM price curves",
            "nft": "NFT marketplace with royalty distributions",
            "bridge": "Cross-chain bridge with validator set",
            "staking": "Staking protocol with reward distributions",
        }

        return type_defaults.get(self.pack.protocol_type.lower(), "")

    def _find_matching_accepted_risks(
        self,
        vulnerability_class: str,
        function_name: str,
    ) -> List[str]:
        """Find accepted risks that might match this finding.

        Args:
            vulnerability_class: Type of vulnerability
            function_name: Function being analyzed

        Returns:
            List of accepted risk descriptions
        """
        matching = []

        for risk in self.pack.accepted_risks:
            # Check function match
            if not risk.affects_function(function_name):
                continue

            # Check pattern/vulnerability class match
            desc_lower = risk.description.lower()
            vuln_lower = vulnerability_class.lower()

            # Fuzzy match on vulnerability class
            if vuln_lower in desc_lower or vuln_lower.replace("-", " ") in desc_lower:
                matching.append(risk.description)
                continue

            # Check pattern ID match
            if risk.matches_pattern(vulnerability_class):
                matching.append(risk.description)

        return matching[:3]  # Limit to 3

    def _estimate_tokens(self, context: BeadContext) -> int:
        """Estimate token count for context budgeting.

        Rough estimate: 1 token ~= 4 chars

        Args:
            context: BeadContext to estimate

        Returns:
            Estimated token count
        """
        # Generate prompt section and estimate
        prompt = context.to_prompt_section()
        return len(prompt) // 4

    def _trim_context(self, context: BeadContext, max_tokens: int) -> BeadContext:
        """Trim context to fit within token budget.

        Prioritizes:
        1. Protocol name/type (always kept)
        2. Security model (always kept)
        3. Relevant roles (trim to 3)
        4. Relevant assumptions (trim to 3)
        5. Invariants (trim to 2)
        6. Off-chain deps (trim to 2)
        7. Accepted risks (trim to 1)

        Args:
            context: BeadContext to trim
            max_tokens: Maximum token budget

        Returns:
            Trimmed BeadContext
        """
        trimmed = BeadContext(
            protocol_name=context.protocol_name,
            protocol_type=context.protocol_type,
            relevant_roles=context.relevant_roles[:3],
            relevant_assumptions=context.relevant_assumptions[:3],
            relevant_invariants=context.relevant_invariants[:2],
            offchain_dependencies=context.offchain_dependencies[:2],
            security_model_summary=context.security_model_summary,
            matching_accepted_risks=context.matching_accepted_risks[:1],
        )

        trimmed.token_estimate = self._estimate_tokens(trimmed)

        # If still over budget, be more aggressive
        if trimmed.token_estimate > max_tokens:
            trimmed.relevant_roles = trimmed.relevant_roles[:2]
            trimmed.relevant_assumptions = trimmed.relevant_assumptions[:2]
            trimmed.relevant_invariants = trimmed.relevant_invariants[:1]
            trimmed.offchain_dependencies = trimmed.offchain_dependencies[:1]
            trimmed.matching_accepted_risks = []
            trimmed.token_estimate = self._estimate_tokens(trimmed)

        return trimmed

    def enrich_bead(
        self,
        bead: "VulnerabilityBead",
    ) -> "VulnerabilityBead":
        """Enrich bead with relevant context.

        Adds context to bead's metadata without modifying core fields.
        Uses bead.metadata['protocol_context'] to store the context.

        Args:
            bead: VulnerabilityBead to enrich

        Returns:
            The same bead with context added to metadata
        """
        # Get semantic operations from pattern context
        semantic_ops = bead.pattern_context.matched_properties or []

        # Get function name from vulnerable code
        function_name = bead.vulnerable_code.function_name or ""

        # Get context for this bead
        context = self.get_context_for_bead(
            vulnerability_class=bead.vulnerability_class,
            function_name=function_name,
            semantic_ops=semantic_ops,
            max_tokens=2000,
        )

        # Store in bead metadata
        # Note: VulnerabilityBead doesn't have a 'metadata' field,
        # so we use the existing mechanism of storing context
        # This integrates with the bead's graph_context mechanism

        # Add to graph_context if it exists, otherwise create it
        if bead.graph_context is None:
            bead.graph_context = {}

        bead.graph_context["protocol_context"] = context.to_dict()
        bead.graph_context["protocol_context_prompt"] = context.to_prompt_section()

        return bead

    def get_prompt_extension(
        self,
        bead: "VulnerabilityBead",
    ) -> str:
        """Get protocol context as a prompt extension for a bead.

        If the bead has been enriched with context, returns the
        formatted prompt section. Otherwise, computes it on the fly.

        Args:
            bead: VulnerabilityBead to get context for

        Returns:
            Formatted prompt section string
        """
        # Check if context already computed
        if bead.graph_context and "protocol_context_prompt" in bead.graph_context:
            return str(bead.graph_context["protocol_context_prompt"])

        # Compute on the fly
        semantic_ops = bead.pattern_context.matched_properties or []
        function_name = bead.vulnerable_code.function_name or ""

        context = self.get_context_for_bead(
            vulnerability_class=bead.vulnerability_class,
            function_name=function_name,
            semantic_ops=semantic_ops,
            max_tokens=2000,
        )

        return context.to_prompt_section()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "BeadContext",
    "BeadContextProvider",
]
