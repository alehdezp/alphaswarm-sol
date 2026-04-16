"""Evidence packet extension with protocol context fields.

Per PHILOSOPHY.md Evidence Packet Contract, evidence packets can include
optional fields for protocol context:
- protocol_context: [string] - Relevant protocol context sections
- assumptions: [string] - Assumptions that apply to this finding
- offchain_inputs: [string] - Off-chain dependencies

This module provides:
- EvidenceContextExtension: Dataclass for context fields in evidence packets
- EvidenceContextProvider: Service that provides context for findings

Per 03-CONTEXT.md decisions:
- 'Violated assumption' is a first-class finding type
- Accepted risks auto-filtered from findings
- Smart filtering: agents request only relevant properties
- Business impact derived from context

Usage:
    from alphaswarm_sol.context.integrations import (
        EvidenceContextExtension,
        EvidenceContextProvider,
    )
    from alphaswarm_sol.context import ProtocolContextPack

    # Load context pack
    pack = ProtocolContextPack.from_dict(yaml_data)

    # Create provider
    provider = EvidenceContextProvider(pack)

    # Get context for a finding
    ext = provider.get_context_for_finding(
        function_name="withdraw",
        vulnerability_class="reentrancy",
        semantic_ops=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
    )

    # Check for violated assumptions
    violated = provider.check_violated_assumptions(
        finding_description="State update after external call",
        semantic_ops=["TRANSFERS_VALUE_OUT"],
    )

    # Check if finding matches accepted risk
    is_accepted, reason = provider.check_accepted_risk(
        finding_description="Admin can pause transfers",
        function_name="pause",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..schema import ProtocolContextPack


# =============================================================================
# Semantic Operation to Assumption Category Mapping
# =============================================================================

# Maps VKG semantic operations to assumption categories that might be relevant
OPERATION_TO_ASSUMPTION_CATEGORIES: Dict[str, List[str]] = {
    "READS_ORACLE": ["price", "oracle"],
    "READS_EXTERNAL_VALUE": ["trust", "external"],
    "CALLS_UNTRUSTED": ["trust", "reentrancy"],
    "CALLS_EXTERNAL": ["trust", "external"],
    "USES_TIMESTAMP": ["time"],
    "USES_BLOCK_DATA": ["randomness", "time"],
    "LOOPS_OVER_ARRAY": ["economic", "gas"],
    "TRANSFERS_VALUE_OUT": ["trust", "economic"],
    "PERFORMS_DIVISION": ["economic", "arithmetic"],
    "PERFORMS_MULTIPLICATION": ["economic", "arithmetic"],
    "MODIFIES_CRITICAL_STATE": ["access", "state"],
    "CHECKS_PERMISSION": ["access", "authorization"],
    "MODIFIES_OWNER": ["access", "ownership"],
    "MODIFIES_ROLES": ["access", "authorization"],
    "WRITES_USER_BALANCE": ["balance", "economic"],
    "READS_USER_BALANCE": ["balance", "economic"],
    "INITIALIZES_STATE": ["state", "initialization"],
    "UPDATES_STATE": ["state"],
    "USES_DELEGATECALL": ["trust", "proxy"],
    "INTERACTS_WITH_AMM": ["price", "defi", "economic"],
}

# Maps vulnerability classes to relevant assumption categories
VULN_CLASS_TO_ASSUMPTION_CATEGORIES: Dict[str, List[str]] = {
    "reentrancy": ["trust", "reentrancy", "external"],
    "access-control": ["access", "authorization", "ownership"],
    "oracle-manipulation": ["price", "oracle", "manipulation"],
    "flash-loan": ["price", "economic", "manipulation"],
    "weak-access": ["access", "authorization"],
    "privilege-escalation": ["access", "ownership", "authorization"],
    "dos": ["economic", "gas", "array"],
    "front-running": ["economic", "time", "mev"],
    "timestamp": ["time", "randomness"],
    "arithmetic": ["economic", "arithmetic"],
    "unchecked-return": ["trust", "external"],
    "delegatecall": ["trust", "proxy"],
}

# Maps vulnerability classes to relevant role capabilities
VULN_CLASS_TO_CAPABILITIES: Dict[str, List[str]] = {
    "access-control": ["pause", "upgrade", "set_fees", "mint", "burn", "withdraw"],
    "privilege-escalation": ["set_admin", "transfer_ownership", "grant_role"],
    "oracle-manipulation": ["set_oracle", "update_price"],
    "reentrancy": ["withdraw", "transfer", "claim"],
    "flash-loan": ["flash_loan", "liquidate"],
}


@dataclass
class EvidenceContextExtension:
    """Context fields for evidence packets.

    Per PHILOSOPHY.md Evidence Packet Contract optional fields.
    These fields connect findings to protocol-level context.

    Attributes:
        protocol_context: Relevant protocol context sections
            Per 03-CONTEXT.md: targeted retrieval of relevant sections
        relevant_assumptions: Assumptions that support this finding
            Assumptions that are relevant to the function/vulnerability
        violated_assumptions: Assumptions that this finding would violate
            Per 03-CONTEXT.md: 'Violated assumption' is first-class finding type
        offchain_dependencies: Off-chain dependencies affecting this finding
            Oracles, keepers, relayers that this function depends on
        business_impact: Business impact derived from context
            Per 03-CONTEXT.md: "user funds at risk because X role can do Y"
        is_accepted_risk: Whether this matches an accepted risk
            Per 03-CONTEXT.md: Accepted risks auto-filtered from findings
        accepted_risk_reason: Why this is an accepted risk
            Populated when is_accepted_risk is True

    Usage:
        ext = EvidenceContextExtension(
            protocol_context=["Lending protocol with flash loans"],
            relevant_assumptions=["Oracle provides accurate prices"],
            violated_assumptions=["Oracle cannot be manipulated"],
            offchain_dependencies=["Chainlink ETH/USD"],
            business_impact="User funds at risk due to price manipulation",
        )

        # Convert to dict for evidence packet
        data = ext.to_dict()
    """

    # Relevant protocol context sections (per 03-CONTEXT.md: targeted retrieval)
    protocol_context: List[str] = field(default_factory=list)

    # Assumptions that support this finding
    relevant_assumptions: List[str] = field(default_factory=list)

    # Assumptions that this finding would violate
    # Per 03-CONTEXT.md: "Violated assumption" is a first-class finding type
    violated_assumptions: List[str] = field(default_factory=list)

    # Off-chain dependencies affecting this finding
    offchain_dependencies: List[str] = field(default_factory=list)

    # Business impact derived from context
    # Per 03-CONTEXT.md: "user funds at risk because X role can do Y"
    business_impact: str = ""

    # Whether this matches an accepted risk
    # Per 03-CONTEXT.md: Accepted risks auto-filtered from findings
    is_accepted_risk: bool = False
    accepted_risk_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for evidence packet integration.

        Returns:
            Dictionary with all context fields suitable for
            evidence packet extension.
        """
        result: Dict[str, Any] = {}

        # Only include non-empty fields
        if self.protocol_context:
            result["protocol_context"] = self.protocol_context
        if self.relevant_assumptions:
            result["assumptions"] = self.relevant_assumptions
        if self.violated_assumptions:
            result["violated_assumptions"] = self.violated_assumptions
        if self.offchain_dependencies:
            result["offchain_inputs"] = self.offchain_dependencies
        if self.business_impact:
            result["business_impact"] = self.business_impact
        if self.is_accepted_risk:
            result["is_accepted_risk"] = self.is_accepted_risk
            result["accepted_risk_reason"] = self.accepted_risk_reason

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceContextExtension":
        """Create from dict.

        Args:
            data: Dictionary with context fields

        Returns:
            EvidenceContextExtension instance
        """
        return cls(
            protocol_context=list(data.get("protocol_context", [])),
            relevant_assumptions=list(data.get("assumptions", [])),
            violated_assumptions=list(data.get("violated_assumptions", [])),
            offchain_dependencies=list(data.get("offchain_inputs", [])),
            business_impact=str(data.get("business_impact", "")),
            is_accepted_risk=bool(data.get("is_accepted_risk", False)),
            accepted_risk_reason=str(data.get("accepted_risk_reason", "")),
        )

    def has_context(self) -> bool:
        """Check if any context was found.

        Returns:
            True if at least one context field is populated
        """
        return bool(
            self.protocol_context
            or self.relevant_assumptions
            or self.violated_assumptions
            or self.offchain_dependencies
            or self.business_impact
        )

    def has_violated_assumptions(self) -> bool:
        """Check if any assumptions are violated.

        Per 03-CONTEXT.md: 'Violated assumption' is a first-class finding type.

        Returns:
            True if violated_assumptions is non-empty
        """
        return bool(self.violated_assumptions)


class EvidenceContextProvider:
    """Provides context for evidence packets.

    Takes a ProtocolContextPack and provides relevant context
    for specific findings based on function name, vulnerability class, etc.

    Per 03-CONTEXT.md: Smart filtering - agents request only relevant
    properties for current test.

    Attributes:
        pack: The ProtocolContextPack to extract context from

    Usage:
        provider = EvidenceContextProvider(context_pack)

        # Get full context for a finding
        ext = provider.get_context_for_finding(
            function_name="withdraw",
            vulnerability_class="reentrancy",
            semantic_ops=["TRANSFERS_VALUE_OUT"],
        )

        # Check specific aspects
        assumptions = provider.get_relevant_assumptions("withdraw", ["CALLS_EXTERNAL"])
        violated = provider.check_violated_assumptions("State after call", ["CALLS_EXTERNAL"])
        is_accepted, reason = provider.check_accepted_risk("Admin pause", "pause")
    """

    def __init__(self, context_pack: "ProtocolContextPack"):
        """Initialize with a context pack.

        Args:
            context_pack: ProtocolContextPack to provide context from
        """
        self.pack = context_pack

    def get_context_for_finding(
        self,
        function_name: str,
        vulnerability_class: str,
        semantic_ops: List[str],
    ) -> EvidenceContextExtension:
        """Get relevant context for a finding.

        Per 03-CONTEXT.md: Smart filtering - agents request only relevant
        properties for current test.

        This method aggregates all relevant context for a finding:
        - Relevant assumptions based on function and operations
        - Violated assumptions based on vulnerability class
        - Off-chain dependencies
        - Business impact
        - Accepted risk check

        Args:
            function_name: Name of the function being analyzed
            vulnerability_class: Type of vulnerability (e.g., "reentrancy")
            semantic_ops: VKG semantic operations in the function

        Returns:
            EvidenceContextExtension with all relevant context
        """
        # Get relevant assumptions
        relevant_assumptions = self.get_relevant_assumptions(
            function_name, semantic_ops
        )

        # Check violated assumptions based on vulnerability class
        violated_assumptions = self.check_violated_assumptions(
            vulnerability_class, semantic_ops
        )

        # Get off-chain dependencies
        offchain = self.get_offchain_dependencies(function_name, semantic_ops)

        # Get roles relevant to this vulnerability
        affected_roles = self._get_affected_roles(function_name, vulnerability_class)

        # Derive business impact
        business_impact = self.derive_business_impact(vulnerability_class, affected_roles)

        # Check accepted risk
        is_accepted, accepted_reason = self.check_accepted_risk(
            vulnerability_class, function_name
        )

        # Build protocol context summary
        protocol_context = self._build_protocol_context_summary(
            function_name, vulnerability_class, semantic_ops
        )

        return EvidenceContextExtension(
            protocol_context=protocol_context,
            relevant_assumptions=[a.description for a in relevant_assumptions],
            violated_assumptions=violated_assumptions,
            offchain_dependencies=[o.name for o in offchain],
            business_impact=business_impact,
            is_accepted_risk=is_accepted,
            accepted_risk_reason=accepted_reason,
        )

    def get_relevant_assumptions(
        self,
        function_name: str,
        semantic_ops: List[str],
    ) -> List[Any]:
        """Get assumptions relevant to this function/operations.

        Matches by:
        - affects_functions containing function_name
        - operation category (oracle assumptions for READS_ORACLE, etc.)

        Args:
            function_name: Function to get assumptions for
            semantic_ops: VKG semantic operations in the function

        Returns:
            List of relevant Assumption objects
        """
        relevant = []
        seen_descriptions = set()

        # Get assumptions that directly affect this function
        for assumption in self.pack.assumptions:
            if assumption.affects_function(function_name):
                if assumption.description not in seen_descriptions:
                    relevant.append(assumption)
                    seen_descriptions.add(assumption.description)

        # Get assumptions by operation category
        relevant_categories = set()
        for op in semantic_ops:
            categories = OPERATION_TO_ASSUMPTION_CATEGORIES.get(op, [])
            relevant_categories.update(categories)

        for assumption in self.pack.assumptions:
            if assumption.category.lower() in relevant_categories:
                if assumption.description not in seen_descriptions:
                    relevant.append(assumption)
                    seen_descriptions.add(assumption.description)

        return relevant

    def check_violated_assumptions(
        self,
        finding_description: str,
        semantic_ops: List[str],
    ) -> List[str]:
        """Check which assumptions might be violated by this finding.

        Per 03-CONTEXT.md: 'Violated assumption' is a first-class finding type

        This method identifies assumptions that the finding would violate.
        For example, an oracle manipulation finding violates the assumption
        that "Oracle prices are accurate".

        Args:
            finding_description: Description of the finding (or vulnerability class)
            semantic_ops: VKG semantic operations involved

        Returns:
            List of assumption descriptions that might be violated
        """
        violated = []
        finding_lower = finding_description.lower()

        # Get relevant categories based on operations
        relevant_categories = set()
        for op in semantic_ops:
            categories = OPERATION_TO_ASSUMPTION_CATEGORIES.get(op, [])
            relevant_categories.update(categories)

        # Also check vulnerability class keywords
        vuln_class = self._extract_vuln_class_from_description(finding_lower)
        if vuln_class:
            categories = VULN_CLASS_TO_ASSUMPTION_CATEGORIES.get(vuln_class, [])
            relevant_categories.update(categories)

        # Check assumptions in relevant categories
        for assumption in self.pack.assumptions:
            # Skip if category doesn't match
            if assumption.category.lower() not in relevant_categories:
                continue

            # Check for violation patterns
            if self._assumption_might_be_violated(assumption, finding_lower, semantic_ops):
                violated.append(assumption.description)

        return violated

    def _assumption_might_be_violated(
        self,
        assumption: Any,
        finding_lower: str,
        semantic_ops: List[str],
    ) -> bool:
        """Check if an assumption might be violated by a finding.

        Args:
            assumption: The Assumption object to check
            finding_lower: Lowercase finding description
            semantic_ops: Semantic operations involved

        Returns:
            True if the assumption might be violated
        """
        desc_lower = assumption.description.lower()

        # Oracle assumptions violated by oracle-related findings
        if "oracle" in desc_lower or "price" in desc_lower:
            if "oracle" in finding_lower or "price" in finding_lower:
                return True
            if "manipulation" in finding_lower:
                return True
            if "READS_ORACLE" in semantic_ops:
                return True

        # Trust assumptions violated by external call issues
        if "trust" in desc_lower or "external" in desc_lower:
            if "reentrancy" in finding_lower or "reentrant" in finding_lower:
                return True
            if "callback" in finding_lower:
                return True
            if "CALLS_UNTRUSTED" in semantic_ops:
                return True

        # Time assumptions violated by timestamp issues
        if "timestamp" in desc_lower or "time" in desc_lower:
            if "timestamp" in finding_lower or "front-run" in finding_lower:
                return True
            if "USES_TIMESTAMP" in semantic_ops:
                return True

        # Access assumptions violated by access control issues
        if "access" in desc_lower or "authorized" in desc_lower:
            if "access" in finding_lower or "unauthorized" in finding_lower:
                return True
            if "privilege" in finding_lower:
                return True

        return False

    def _extract_vuln_class_from_description(self, desc: str) -> Optional[str]:
        """Extract vulnerability class from a description.

        Args:
            desc: Lowercase description string

        Returns:
            Vulnerability class if detected, None otherwise
        """
        vuln_keywords = {
            "reentrancy": "reentrancy",
            "reentrant": "reentrancy",
            "access control": "access-control",
            "access-control": "access-control",
            "unauthorized": "access-control",
            "oracle": "oracle-manipulation",
            "price manipulation": "oracle-manipulation",
            "flash loan": "flash-loan",
            "flash-loan": "flash-loan",
            "dos": "dos",
            "denial of service": "dos",
            "front-run": "front-running",
            "frontrun": "front-running",
            "timestamp": "timestamp",
            "arithmetic": "arithmetic",
            "overflow": "arithmetic",
            "underflow": "arithmetic",
            "delegatecall": "delegatecall",
        }

        for keyword, vuln_class in vuln_keywords.items():
            if keyword in desc:
                return vuln_class

        return None

    def check_accepted_risk(
        self,
        finding_description: str,
        function_name: str,
    ) -> Tuple[bool, str]:
        """Check if finding matches an accepted risk.

        Per 03-CONTEXT.md: Accepted risks auto-filtered from findings

        Args:
            finding_description: Description of the finding
            function_name: Function where finding was detected

        Returns:
            Tuple of (is_accepted: bool, reason: str)
        """
        finding_lower = finding_description.lower()

        for risk in self.pack.accepted_risks:
            # Check description match (fuzzy)
            risk_desc_lower = risk.description.lower()

            # Simple substring match
            if risk_desc_lower in finding_lower or finding_lower in risk_desc_lower:
                # Check function filter
                if not risk.affects_function(function_name):
                    continue

                return True, risk.reason

            # Also check by vulnerability class keywords
            vuln_class = self._extract_vuln_class_from_description(finding_lower)
            if vuln_class and risk.matches_pattern(vuln_class):
                if risk.affects_function(function_name):
                    return True, risk.reason

        return False, ""

    def derive_business_impact(
        self,
        vulnerability_class: str,
        affected_roles: List[str],
    ) -> str:
        """Derive business impact from context.

        Per 03-CONTEXT.md: Business impact derived from context
        "user funds at risk because X role can do Y"

        Args:
            vulnerability_class: Type of vulnerability
            affected_roles: Roles that could exploit this

        Returns:
            Business impact description string
        """
        if not affected_roles:
            # Use generic impact based on vulnerability class
            return self._generic_impact_for_vuln_class(vulnerability_class)

        # Build impact from roles and their capabilities
        impacts = []

        for role_name in affected_roles:
            role = self.pack.get_role(role_name)
            if not role:
                continue

            # Get relevant capabilities for this vulnerability
            relevant_caps = VULN_CLASS_TO_CAPABILITIES.get(vulnerability_class, [])

            # Find matching capabilities
            matching_caps = [
                cap for cap in role.capabilities
                if any(rc.lower() in cap.lower() for rc in relevant_caps)
            ]

            if matching_caps:
                caps_str = ", ".join(matching_caps[:3])  # Limit to 3
                impacts.append(f"{role.name} can {caps_str}")

        if impacts:
            return f"User funds at risk because {'; '.join(impacts)}"

        return self._generic_impact_for_vuln_class(vulnerability_class)

    def _generic_impact_for_vuln_class(self, vulnerability_class: str) -> str:
        """Get generic impact description for a vulnerability class.

        Args:
            vulnerability_class: Type of vulnerability

        Returns:
            Generic impact description
        """
        impacts = {
            "reentrancy": "User funds at risk due to potential recursive withdrawal",
            "access-control": "Unauthorized access may allow fund theft or manipulation",
            "oracle-manipulation": "Price manipulation may lead to unfair liquidations or trades",
            "flash-loan": "Flash loan attacks may drain protocol reserves",
            "dos": "Service disruption may prevent users from accessing funds",
            "front-running": "Transaction ordering manipulation may cause financial loss",
            "arithmetic": "Calculation errors may cause incorrect fund distribution",
            "timestamp": "Time-based manipulation may affect protocol logic",
            "delegatecall": "Storage corruption or unauthorized code execution possible",
        }

        return impacts.get(
            vulnerability_class,
            f"Potential financial or operational impact from {vulnerability_class}",
        )

    def get_offchain_dependencies(
        self,
        function_name: str,
        semantic_ops: List[str],
    ) -> List[Any]:
        """Get off-chain dependencies for this function.

        Args:
            function_name: Function to check dependencies for
            semantic_ops: VKG semantic operations in the function

        Returns:
            List of OffchainInput objects
        """
        deps = []
        seen_names = set()

        # Get dependencies that directly affect this function
        for offchain in self.pack.offchain_inputs:
            if offchain.affects_function(function_name):
                if offchain.name not in seen_names:
                    deps.append(offchain)
                    seen_names.add(offchain.name)

        # Get dependencies by operation type
        for op in semantic_ops:
            if op in ("READS_ORACLE", "READS_EXTERNAL_VALUE"):
                # Add any oracle-type dependencies
                for offchain in self.pack.offchain_inputs:
                    if offchain.is_oracle() and offchain.name not in seen_names:
                        deps.append(offchain)
                        seen_names.add(offchain.name)

        return deps

    def _get_affected_roles(
        self,
        function_name: str,
        vulnerability_class: str,
    ) -> List[str]:
        """Get roles that could be affected by this vulnerability.

        Args:
            function_name: Function where vulnerability was found
            vulnerability_class: Type of vulnerability

        Returns:
            List of role names
        """
        affected = []

        # Get capabilities relevant to this vulnerability class
        relevant_caps = VULN_CLASS_TO_CAPABILITIES.get(vulnerability_class, [])

        for role in self.pack.roles:
            # Check if role has relevant capabilities
            for cap in role.capabilities:
                cap_lower = cap.lower()
                if any(rc.lower() in cap_lower for rc in relevant_caps):
                    affected.append(role.name)
                    break

            # Also check if role is referenced in function name
            if role.name.lower() in function_name.lower():
                if role.name not in affected:
                    affected.append(role.name)

        return affected

    def _build_protocol_context_summary(
        self,
        function_name: str,
        vulnerability_class: str,
        semantic_ops: List[str],
    ) -> List[str]:
        """Build a summary of relevant protocol context.

        Args:
            function_name: Function being analyzed
            vulnerability_class: Type of vulnerability
            semantic_ops: VKG semantic operations

        Returns:
            List of context summary strings
        """
        context = []

        # Protocol overview
        if self.pack.protocol_name:
            overview = f"{self.pack.protocol_name}"
            if self.pack.protocol_type:
                overview += f" ({self.pack.protocol_type})"
            context.append(overview)

        # Security model summary
        if self.pack.security_model:
            if "trust_model" in self.pack.security_model:
                context.append(f"Trust model: {self.pack.security_model['trust_model']}")
            if "threat_model" in self.pack.security_model:
                context.append(f"Threat model: {self.pack.security_model['threat_model']}")

        # Critical function status
        if self.pack.is_critical_function(function_name):
            context.append(f"'{function_name}' is marked as critical function")

        # Add relevant invariant summaries
        for invariant in self.pack.invariants:
            if invariant.critical:
                # Only include critical invariants
                context.append(f"Critical invariant: {invariant.natural_language}")

        return context[:5]  # Limit to 5 context items


# =============================================================================
# Evidence Assembly with Retrieval Packing (07.1.3-03)
# =============================================================================


class EvidenceAssembler:
    """Assemble and pack evidence for subagent context.

    Integrates with RetrievalPacker to produce compact evidence bundles
    while preserving evidence-first traceability.

    Usage:
        assembler = EvidenceAssembler(context_provider)

        # Assemble packed evidence for a finding
        packed = assembler.assemble_packed(
            findings=[{...}],
            max_tokens=3000,
        )

        # Get compact TOON output for subagent
        context_str = packed.toon_output
    """

    def __init__(
        self,
        context_provider: Optional["EvidenceContextProvider"] = None,
        max_tokens: int = 3000,
    ):
        """Initialize evidence assembler.

        Args:
            context_provider: Optional context provider for enrichment
            max_tokens: Default max tokens for packing
        """
        from ..retrieval_packer import RetrievalPacker

        self._provider = context_provider
        self._packer = RetrievalPacker(max_tokens=max_tokens)
        self._default_max_tokens = max_tokens

    def assemble_packed(
        self,
        findings: List[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        include_context: bool = True,
    ) -> "PackedEvidenceBundle":
        """Assemble findings into a packed evidence bundle.

        Converts finding dictionaries into EvidenceItem objects,
        enriches with context if available, and packs using TOON.

        Args:
            findings: List of finding dictionaries with evidence data
            max_tokens: Override max tokens for this assembly
            include_context: Whether to include protocol context

        Returns:
            PackedEvidenceBundle with compact TOON output
        """
        from ..retrieval_packer import EvidenceItem, PackedEvidenceBundle

        items: List["EvidenceItem"] = []

        for finding in findings:
            item = self._finding_to_evidence_item(finding)
            items.append(item)

        # Build bundle metadata
        metadata: Dict[str, Any] = {
            "finding_count": len(findings),
        }

        if include_context and self._provider:
            # Add protocol context summary if available
            metadata["protocol"] = self._provider.pack.protocol_name or "unknown"

        return self._packer.pack(
            items,
            max_tokens=max_tokens or self._default_max_tokens,
            bundle_metadata=metadata,
        )

    def _finding_to_evidence_item(
        self,
        finding: Dict[str, Any],
    ) -> "EvidenceItem":
        """Convert a finding dict to an EvidenceItem.

        Args:
            finding: Finding dictionary with evidence fields

        Returns:
            EvidenceItem instance
        """
        from ..retrieval_packer import EvidenceItem

        # Extract evidence ID (various formats supported)
        evidence_id = (
            finding.get("evidence_id")
            or finding.get("id")
            or finding.get("node_id")
            or f"EV-{hash(str(finding)) & 0xFFFFFFFF:08x}"
        )

        # Extract location
        location = finding.get("location", {})
        file_path = location.get("file", finding.get("file", ""))
        line_start = location.get("line", finding.get("line", 0))
        line_end = location.get("end_line", line_start)

        # Extract code snippet
        code_snippet = finding.get("code", finding.get("snippet", ""))

        # Extract risk score
        risk_score = float(finding.get("risk_score", finding.get("severity_score", 0.0)))

        # Extract operations
        operations = list(finding.get("operations", finding.get("semantic_ops", [])))

        # Build metadata
        metadata: Dict[str, Any] = {}
        if finding.get("pattern"):
            metadata["pattern"] = finding["pattern"]
        if finding.get("vulnerability_class"):
            metadata["vuln_class"] = finding["vulnerability_class"]
        if finding.get("confidence"):
            metadata["confidence"] = finding["confidence"]

        return EvidenceItem(
            evidence_id=evidence_id,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            code_snippet=code_snippet,
            risk_score=risk_score,
            operations=operations,
            metadata=metadata,
            node_id=finding.get("node_id"),
        )

    def unpack_bundle(
        self,
        packed: "PackedEvidenceBundle",
    ) -> List["EvidenceItem"]:
        """Unpack a bundle for verification.

        Args:
            packed: Packed evidence bundle

        Returns:
            List of EvidenceItem objects
        """
        return self._packer.unpack(packed.toon_output)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EvidenceContextExtension",
    "EvidenceContextProvider",
    "EvidenceAssembler",
    "OPERATION_TO_ASSUMPTION_CATEGORIES",
    "VULN_CLASS_TO_ASSUMPTION_CATEGORIES",
    "VULN_CLASS_TO_CAPABILITIES",
]
