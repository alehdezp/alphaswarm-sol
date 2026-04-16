"""ProtocolContextPack - complete protocol context schema.

The ProtocolContextPack is the main schema for capturing protocol-level context
including roles, economics, assumptions, invariants, and off-chain dependencies.
Designed for LLM-generated content with confidence tracking.

Per 03-CONTEXT.md decisions:
- YAML format for human readability
- Confidence levels on each field
- Function-level granularity for assumptions
- Designed for minimal, targeted retrieval

Usage:
    from alphaswarm_sol.context.schema import ProtocolContextPack
    from alphaswarm_sol.context.types import Role, Assumption, Confidence

    pack = ProtocolContextPack(
        protocol_name="Aave V3",
        protocol_type="lending",
        roles=[
            Role(
                name="admin",
                capabilities=["pause", "upgrade"],
                trust_assumptions=["trusted multisig"],
                confidence=Confidence.CERTAIN
            )
        ],
        assumptions=[
            Assumption(
                description="Oracle prices are accurate",
                category="price",
                affects_functions=["liquidate", "borrow"],
                confidence=Confidence.INFERRED,
                source="whitepaper"
            )
        ]
    )

    # Serialize to dict
    data = pack.to_dict()

    # Deserialize from dict
    restored = ProtocolContextPack.from_dict(data)

    # Get specific section for targeted retrieval
    roles_data = pack.get_section("roles")

    # Get relevant assumptions for a function
    liquidate_assumptions = pack.get_relevant_assumptions("liquidate")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    Confidence,
    Role,
    Assumption,
    Invariant,
    OffchainInput,
    ValueFlow,
    AcceptedRisk,
    CausalEdge,
)


@dataclass
class ProtocolContextPack:
    """Complete protocol context pack for LLM reasoning.

    This is the main schema for capturing protocol-level context including
    roles, economics, assumptions, invariants, and off-chain dependencies.
    Designed for LLM-generated content with confidence tracking.

    Per 05.11-CONTEXT.md: Extended with causal edges for exploitation reasoning
    and payoff model placeholders for game-theoretic analysis.

    Attributes:
        version: Pack version for evolution tracking
        schema_version: Schema format version
        protocol_name: Name of the protocol
        protocol_type: Type of protocol (lending, dex, nft, bridge, etc.)
        generated_at: When this pack was generated
        auto_generated: Whether LLM-generated (not human-reviewed)
        reviewed: Whether a human reviewed this pack
        roles: Protocol roles with capabilities
        value_flows: Economic value movements
        incentives: Protocol incentives
        tokenomics_summary: Security-focused tokenomics summary
        assumptions: Protocol assumptions
        invariants: Protocol invariants
        offchain_inputs: Off-chain dependencies
        security_model: Overall security model summary
        critical_functions: Manual + auto-detected critical functions
        accepted_risks: Known/accepted behaviors
        governance: Governance information
        sources: Source documents with reliability tiers
        deployment: Chain-specific deployment context
        notes: Freeform notes for nuance
        causal_edges: Causal relationships for exploitation reasoning (05.11)
        attack_payoff_model: Game-theoretic attack payoff model (05.11)
        defender_payoff_model: Game-theoretic defender payoff model (05.11)

    Sections for targeted retrieval:
        - metadata: version, protocol info, generation metadata
        - roles: roles list
        - economics: value_flows, incentives, tokenomics_summary
        - assumptions: assumptions list
        - invariants: invariants list
        - offchain_inputs: offchain_inputs list
        - security: security_model, critical_functions
        - accepted_risks: accepted_risks list
        - governance: governance dict
        - sources: sources list
        - deployment: deployment dict
        - causal: causal_edges list (05.11)
        - payoff: attack_payoff_model, defender_payoff_model (05.11)
    """

    # Metadata
    version: str = "1.0"
    schema_version: str = "1.1"  # Updated for 05.11 extensions
    protocol_name: str = ""
    protocol_type: str = ""  # lending, dex, nft, bridge, etc.

    # Generation metadata
    generated_at: str = ""  # ISO timestamp
    auto_generated: bool = True
    reviewed: bool = False

    # Roles and capabilities (hybrid approach per 03-CONTEXT.md)
    roles: List[Role] = field(default_factory=list)

    # Economic model
    value_flows: List[ValueFlow] = field(default_factory=list)
    incentives: List[str] = field(default_factory=list)
    tokenomics_summary: str = ""  # Freeform, security-focused

    # Assumptions (freeform tags per research decision)
    assumptions: List[Assumption] = field(default_factory=list)

    # Invariants (semi-formal + natural language per 03-CONTEXT.md)
    invariants: List[Invariant] = field(default_factory=list)

    # Off-chain inputs
    offchain_inputs: List[OffchainInput] = field(default_factory=list)

    # Security model section (dedicated per 03-CONTEXT.md)
    security_model: Dict[str, Any] = field(default_factory=dict)

    # Critical functions (manual + auto-detected per 03-CONTEXT.md)
    critical_functions: List[str] = field(default_factory=list)

    # Accepted risks (auto-filtered from findings per 03-CONTEXT.md)
    accepted_risks: List[AcceptedRisk] = field(default_factory=list)

    # Governance (per 03-CONTEXT.md content extraction)
    governance: Dict[str, Any] = field(default_factory=dict)

    # Sources with reliability tiers
    sources: List[Dict[str, Any]] = field(default_factory=list)

    # Optional deployment context
    deployment: Dict[str, Any] = field(default_factory=dict)

    # Notes for nuance (hybrid structure per 03-CONTEXT.md)
    notes: str = ""

    # Causal edges for exploitation reasoning (05.11)
    causal_edges: List[CausalEdge] = field(default_factory=list)

    # Game-theoretic payoff models (05.11) - stored as dicts, typed in economics module
    attack_payoff_model: Optional[Dict[str, Any]] = None
    defender_payoff_model: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Initialize generated_at if not set."""
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire pack to dict for YAML serialization.

        Returns:
            Complete dict representation suitable for YAML encoding
        """
        result = {
            # Metadata
            "version": self.version,
            "schema_version": self.schema_version,
            "protocol_name": self.protocol_name,
            "protocol_type": self.protocol_type,
            # Generation metadata
            "generated_at": self.generated_at,
            "auto_generated": self.auto_generated,
            "reviewed": self.reviewed,
            # Roles
            "roles": [r.to_dict() for r in self.roles],
            # Economics
            "value_flows": [v.to_dict() for v in self.value_flows],
            "incentives": self.incentives,
            "tokenomics_summary": self.tokenomics_summary,
            # Assumptions
            "assumptions": [a.to_dict() for a in self.assumptions],
            # Invariants
            "invariants": [i.to_dict() for i in self.invariants],
            # Off-chain inputs
            "offchain_inputs": [o.to_dict() for o in self.offchain_inputs],
            # Security
            "security_model": self.security_model,
            "critical_functions": self.critical_functions,
            # Accepted risks
            "accepted_risks": [r.to_dict() for r in self.accepted_risks],
            # Governance
            "governance": self.governance,
            # Sources
            "sources": self.sources,
            # Deployment
            "deployment": self.deployment,
            # Notes
            "notes": self.notes,
            # Causal edges (05.11)
            "causal_edges": [e.to_dict() for e in self.causal_edges],
        }
        # Include payoff models if set (05.11)
        if self.attack_payoff_model:
            result["attack_payoff_model"] = self.attack_payoff_model
        if self.defender_payoff_model:
            result["defender_payoff_model"] = self.defender_payoff_model
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolContextPack":
        """Reconstruct ProtocolContextPack from dict.

        Args:
            data: Dictionary with pack data (e.g., from YAML load)

        Returns:
            ProtocolContextPack instance
        """
        return cls(
            # Metadata
            version=str(data.get("version", "1.0")),
            schema_version=str(data.get("schema_version", "1.1")),
            protocol_name=str(data.get("protocol_name", "")),
            protocol_type=str(data.get("protocol_type", "")),
            # Generation metadata
            generated_at=str(data.get("generated_at", "")),
            auto_generated=bool(data.get("auto_generated", True)),
            reviewed=bool(data.get("reviewed", False)),
            # Roles
            roles=[Role.from_dict(r) for r in data.get("roles", [])],
            # Economics
            value_flows=[ValueFlow.from_dict(v) for v in data.get("value_flows", [])],
            incentives=list(data.get("incentives", [])),
            tokenomics_summary=str(data.get("tokenomics_summary", "")),
            # Assumptions
            assumptions=[Assumption.from_dict(a) for a in data.get("assumptions", [])],
            # Invariants
            invariants=[Invariant.from_dict(i) for i in data.get("invariants", [])],
            # Off-chain inputs
            offchain_inputs=[OffchainInput.from_dict(o) for o in data.get("offchain_inputs", [])],
            # Security
            security_model=dict(data.get("security_model", {})),
            critical_functions=list(data.get("critical_functions", [])),
            # Accepted risks
            accepted_risks=[AcceptedRisk.from_dict(r) for r in data.get("accepted_risks", [])],
            # Governance
            governance=dict(data.get("governance", {})),
            # Sources
            sources=list(data.get("sources", [])),
            # Deployment
            deployment=dict(data.get("deployment", {})),
            # Notes
            notes=str(data.get("notes", "")),
            # Causal edges (05.11)
            causal_edges=[CausalEdge.from_dict(e) for e in data.get("causal_edges", [])],
            # Payoff models (05.11)
            attack_payoff_model=data.get("attack_payoff_model"),
            defender_payoff_model=data.get("defender_payoff_model"),
        )

    def get_section(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific section for targeted retrieval.

        Per 03-CONTEXT.md: designed for minimal, targeted retrieval
        so LLMs don't fill context window unnecessarily.

        Args:
            name: Section name (metadata, roles, economics, assumptions,
                  invariants, offchain_inputs, security, accepted_risks,
                  governance, sources, deployment, causal, payoff)

        Returns:
            Dict with section data, or None if section not found
        """
        sections = {
            "metadata": {
                "version": self.version,
                "schema_version": self.schema_version,
                "protocol_name": self.protocol_name,
                "protocol_type": self.protocol_type,
                "generated_at": self.generated_at,
                "auto_generated": self.auto_generated,
                "reviewed": self.reviewed,
            },
            "roles": {
                "roles": [r.to_dict() for r in self.roles],
            },
            "economics": {
                "value_flows": [v.to_dict() for v in self.value_flows],
                "incentives": self.incentives,
                "tokenomics_summary": self.tokenomics_summary,
            },
            "assumptions": {
                "assumptions": [a.to_dict() for a in self.assumptions],
            },
            "invariants": {
                "invariants": [i.to_dict() for i in self.invariants],
            },
            "offchain_inputs": {
                "offchain_inputs": [o.to_dict() for o in self.offchain_inputs],
            },
            "security": {
                "security_model": self.security_model,
                "critical_functions": self.critical_functions,
            },
            "accepted_risks": {
                "accepted_risks": [r.to_dict() for r in self.accepted_risks],
            },
            "governance": {
                "governance": self.governance,
            },
            "sources": {
                "sources": self.sources,
            },
            "deployment": {
                "deployment": self.deployment,
            },
            "notes": {
                "notes": self.notes,
            },
            # 05.11 extensions
            "causal": {
                "causal_edges": [e.to_dict() for e in self.causal_edges],
            },
            "payoff": {
                "attack_payoff_model": self.attack_payoff_model,
                "defender_payoff_model": self.defender_payoff_model,
            },
        }
        return sections.get(name)

    def token_estimate(self) -> int:
        """Estimate token count for context budgeting.

        Rough estimation: ~4 characters per token for English text.
        Used for context window management.

        Returns:
            Estimated token count
        """
        import json
        # Serialize to JSON and estimate tokens
        json_str = json.dumps(self.to_dict(), indent=2)
        # Rough estimate: 4 chars per token
        return len(json_str) // 4

    def get_relevant_assumptions(self, function_name: str) -> List[Assumption]:
        """Get assumptions relevant to a specific function.

        Per 03-CONTEXT.md: function-level granularity for context.

        Args:
            function_name: Function to get assumptions for

        Returns:
            List of relevant Assumption objects
        """
        relevant = []
        for assumption in self.assumptions:
            if assumption.affects_function(function_name):
                relevant.append(assumption)
        return relevant

    def get_relevant_offchain_inputs(self, function_name: str) -> List[OffchainInput]:
        """Get off-chain inputs relevant to a specific function.

        Args:
            function_name: Function to get inputs for

        Returns:
            List of relevant OffchainInput objects
        """
        relevant = []
        for input_dep in self.offchain_inputs:
            if input_dep.affects_function(function_name):
                relevant.append(input_dep)
        return relevant

    def is_accepted_risk(
        self,
        description: str,
        function_name: Optional[str] = None,
        pattern_id: Optional[str] = None,
    ) -> bool:
        """Check if a finding matches an accepted risk.

        Per 03-CONTEXT.md: auto-filter accepted risks from findings.

        Args:
            description: Finding description to check
            function_name: Optional function name for filtering
            pattern_id: Optional pattern ID for filtering

        Returns:
            True if this finding should be filtered as accepted risk
        """
        description_lower = description.lower()

        for risk in self.accepted_risks:
            # Check if description matches (fuzzy)
            risk_desc_lower = risk.description.lower()
            # Simple substring match - could be enhanced with fuzzy matching
            if risk_desc_lower in description_lower or description_lower in risk_desc_lower:
                # Check function filter
                if function_name and not risk.affects_function(function_name):
                    continue
                # Check pattern filter
                if pattern_id and risk.patterns and not risk.matches_pattern(pattern_id):
                    continue
                return True

        return False

    def get_role(self, name: str) -> Optional[Role]:
        """Get a specific role by name.

        Args:
            name: Role name to find

        Returns:
            Role if found, None otherwise
        """
        for role in self.roles:
            if role.name.lower() == name.lower():
                return role
        return None

    def is_critical_function(self, function_name: str) -> bool:
        """Check if a function is marked as critical.

        Args:
            function_name: Function name to check

        Returns:
            True if function is in critical_functions list
        """
        fn_lower = function_name.lower()
        for critical in self.critical_functions:
            if critical.lower() == fn_lower or critical.lower().endswith(f".{fn_lower}"):
                return True
        return False

    def get_source_by_tier(self, tier: int) -> List[Dict[str, Any]]:
        """Get sources filtered by reliability tier.

        Per 03-CONTEXT.md: Tier 1 (official), Tier 2 (audits), Tier 3 (community)

        Args:
            tier: Tier to filter by (1, 2, or 3)

        Returns:
            List of sources matching the tier
        """
        return [s for s in self.sources if s.get("tier") == tier]

    def get_invariants_by_category(self, category: str) -> List[Invariant]:
        """Get invariants filtered by category.

        Args:
            category: Category to filter by (supply, balance, access, economic)

        Returns:
            List of matching Invariant objects
        """
        return [i for i in self.invariants if i.category.lower() == category.lower()]

    def get_critical_invariants(self) -> List[Invariant]:
        """Get all invariants marked as critical.

        Returns:
            List of critical Invariant objects
        """
        return [i for i in self.invariants if i.critical]

    def confidence_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary of confidence levels across sections.

        Returns:
            Dict with confidence counts per section
        """
        summary: Dict[str, Dict[str, int]] = {
            "roles": {"certain": 0, "inferred": 0, "unknown": 0},
            "assumptions": {"certain": 0, "inferred": 0, "unknown": 0},
            "invariants": {"certain": 0, "inferred": 0, "unknown": 0},
            "offchain_inputs": {"certain": 0, "inferred": 0, "unknown": 0},
            "value_flows": {"certain": 0, "inferred": 0, "unknown": 0},
        }

        for role in self.roles:
            summary["roles"][role.confidence.value] += 1

        for assumption in self.assumptions:
            summary["assumptions"][assumption.confidence.value] += 1

        for invariant in self.invariants:
            summary["invariants"][invariant.confidence.value] += 1

        for offchain in self.offchain_inputs:
            summary["offchain_inputs"][offchain.confidence.value] += 1

        for flow in self.value_flows:
            summary["value_flows"][flow.confidence.value] += 1

        return summary

    def merge(self, other: "ProtocolContextPack") -> "ProtocolContextPack":
        """Merge another context pack into this one.

        Creates a new pack with combined data. In case of conflicts,
        items with higher confidence are preferred.

        Args:
            other: Another ProtocolContextPack to merge

        Returns:
            New merged ProtocolContextPack
        """
        # Merge roles (prefer higher confidence)
        merged_roles = {r.name: r for r in self.roles}
        for role in other.roles:
            if role.name not in merged_roles or role.confidence > merged_roles[role.name].confidence:
                merged_roles[role.name] = role

        # Merge assumptions (by description)
        merged_assumptions = {a.description: a for a in self.assumptions}
        for assumption in other.assumptions:
            if (
                assumption.description not in merged_assumptions
                or assumption.confidence > merged_assumptions[assumption.description].confidence
            ):
                merged_assumptions[assumption.description] = assumption

        # Merge invariants (by natural_language)
        merged_invariants = {i.natural_language: i for i in self.invariants}
        for invariant in other.invariants:
            if (
                invariant.natural_language not in merged_invariants
                or invariant.confidence > merged_invariants[invariant.natural_language].confidence
            ):
                merged_invariants[invariant.natural_language] = invariant

        # Merge other lists (simple concatenation with dedup by name)
        def merge_by_name(list1: List[Any], list2: List[Any]) -> List[Any]:
            seen = {item.name for item in list1}
            result = list(list1)
            for item in list2:
                if item.name not in seen:
                    result.append(item)
                    seen.add(item.name)
            return result

        return ProtocolContextPack(
            version=self.version,
            schema_version=self.schema_version,
            protocol_name=self.protocol_name or other.protocol_name,
            protocol_type=self.protocol_type or other.protocol_type,
            generated_at=datetime.utcnow().isoformat() + "Z",
            auto_generated=self.auto_generated and other.auto_generated,
            reviewed=self.reviewed or other.reviewed,
            roles=list(merged_roles.values()),
            value_flows=merge_by_name(self.value_flows, other.value_flows),
            incentives=list(set(self.incentives + other.incentives)),
            tokenomics_summary=self.tokenomics_summary or other.tokenomics_summary,
            assumptions=list(merged_assumptions.values()),
            invariants=list(merged_invariants.values()),
            offchain_inputs=merge_by_name(self.offchain_inputs, other.offchain_inputs),
            security_model={**self.security_model, **other.security_model},
            critical_functions=list(set(self.critical_functions + other.critical_functions)),
            accepted_risks=self.accepted_risks + other.accepted_risks,
            governance={**self.governance, **other.governance},
            sources=self.sources + other.sources,
            deployment={**self.deployment, **other.deployment},
            notes=f"{self.notes}\n\n{other.notes}".strip() if other.notes else self.notes,
        )


    def get_causal_edges_from(self, source_node: str) -> List[CausalEdge]:
        """Get all causal edges originating from a specific node.

        Args:
            source_node: Source node ID

        Returns:
            List of CausalEdge objects from this source
        """
        return [e for e in self.causal_edges if e.source_node == source_node]

    def get_causal_edges_to(self, target_node: str) -> List[CausalEdge]:
        """Get all causal edges targeting a specific node.

        Args:
            target_node: Target node ID

        Returns:
            List of CausalEdge objects to this target
        """
        return [e for e in self.causal_edges if e.target_node == target_node]

    def get_blocking_edges(self) -> List[CausalEdge]:
        """Get all blocking/mitigation causal edges.

        Returns:
            List of CausalEdge objects with BLOCKS edge type
        """
        return [e for e in self.causal_edges if e.is_blocking]

    def get_high_probability_edges(self) -> List[CausalEdge]:
        """Get all high-probability causal edges (>= 0.7).

        Returns:
            List of CausalEdge objects with probability >= 0.7
        """
        return [e for e in self.causal_edges if e.is_high_probability]

    def get_stale_assumptions(self, current_date: Optional[str] = None) -> List[Assumption]:
        """Get all assumptions that have expired based on TTL.

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            List of stale Assumption objects
        """
        return [a for a in self.assumptions if a.is_stale(current_date)]

    def get_stale_roles(self, current_date: Optional[str] = None) -> List[Role]:
        """Get all roles that have expired based on TTL.

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            List of stale Role objects
        """
        return [r for r in self.roles if r.is_stale(current_date)]

    def get_stale_invariants(self, current_date: Optional[str] = None) -> List[Invariant]:
        """Get all invariants that have expired based on TTL.

        Args:
            current_date: Current date in ISO format (defaults to today)

        Returns:
            List of stale Invariant objects
        """
        return [i for i in self.invariants if i.is_stale(current_date)]

    def has_payoff_models(self) -> bool:
        """Check if this pack has payoff models attached.

        Returns:
            True if either attack or defender payoff model is set
        """
        return self.attack_payoff_model is not None or self.defender_payoff_model is not None


# Export for module
__all__ = ["ProtocolContextPack"]
