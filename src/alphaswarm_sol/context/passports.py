"""Contract passports with cross-protocol dependencies.

Per 05.11-CONTEXT.md: Each contract gets a compact passport attached to its node
that summarizes its economic role, assets handled, critical actions, and dependencies.

Key features:
- ContractPassport: Per-contract economic summary with cross-protocol deps
- CrossProtocolDependency: External protocol dependencies with criticality
- PassportBuilder: Generates passports from context pack and code analysis
- Systemic risk scoring based on dependency centrality

Usage:
    from alphaswarm_sol.context.passports import (
        ContractPassport, PassportBuilder, CrossProtocolDependency
    )

    # Build passports from context pack
    builder = PassportBuilder(context_pack, kg)
    passports = builder.build_all()

    # Get passport for a contract
    passport = passports.get("Vault")
    print(f"Purpose: {passport.economic_purpose}")
    print(f"Cross-protocol deps: {len(passport.cross_protocol_dependencies)}")
    print(f"Systemic risk: {passport.systemic_risk_score}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .types import Confidence

if TYPE_CHECKING:
    from .schema import ProtocolContextPack


class DependencyType(Enum):
    """Types of cross-protocol dependencies.

    Per 05.11-CONTEXT.md: External dependencies categorized by function.
    """

    ORACLE = "oracle"  # Price feeds, data oracles
    LIQUIDITY = "liquidity"  # Liquidity sources, AMM pools
    GOVERNANCE = "governance"  # External governance tokens/votes
    COLLATERAL = "collateral"  # External collateral assets
    BRIDGE = "bridge"  # Cross-chain bridges
    KEEPER = "keeper"  # External keepers/bots
    CUSTODY = "custody"  # External custody/vaults
    LENDING = "lending"  # External lending protocols


class LifecycleStage(Enum):
    """Contract lifecycle stages.

    Per 05.11-CONTEXT.md: Function lifecycle stage model.
    """

    INIT = "init"  # Setup and role assignment
    ACTIVE = "active"  # Normal operation
    PAUSED = "paused"  # Limited actions, often admin-only
    EMERGENCY = "emergency"  # Rescue/withdrawal paths only
    SUNSET = "sunset"  # Shutdown or migration phase
    UPGRADE = "upgrade"  # Governance-driven changes


@dataclass
class CrossProtocolDependency:
    """A cross-protocol dependency with criticality and cascade impact.

    Per 05.11-CONTEXT.md: Track external protocol dependencies that affect
    this contract's security and systemic risk.

    Attributes:
        protocol_id: External protocol identifier (e.g., "chainlink", "aave-v3")
        dependency_type: Type of dependency (oracle, liquidity, governance, etc.)
        description: Human-readable description
        criticality: Criticality score 1-10 (10 = critical)
        failure_cascade_impact: Description of what happens if dependency fails
        last_verified_date: When this dependency was last verified
        confidence: Confidence in this dependency mapping
        affected_functions: Functions that depend on this protocol
    """

    protocol_id: str
    dependency_type: DependencyType
    description: str = ""
    criticality: int = 5
    failure_cascade_impact: str = ""
    last_verified_date: str = ""
    confidence: Confidence = Confidence.INFERRED
    affected_functions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate criticality range and set default date."""
        if not 1 <= self.criticality <= 10:
            raise ValueError(f"criticality must be 1-10, got {self.criticality}")
        if not self.last_verified_date:
            self.last_verified_date = datetime.utcnow().strftime("%Y-%m-%d")

    @property
    def is_critical(self) -> bool:
        """Whether this dependency is critical (>= 8)."""
        return self.criticality >= 8

    @property
    def is_oracle(self) -> bool:
        """Whether this is an oracle dependency."""
        return self.dependency_type == DependencyType.ORACLE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol_id": self.protocol_id,
            "dependency_type": self.dependency_type.value,
            "description": self.description,
            "criticality": self.criticality,
            "failure_cascade_impact": self.failure_cascade_impact,
            "last_verified_date": self.last_verified_date,
            "confidence": self.confidence.value,
            "affected_functions": self.affected_functions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrossProtocolDependency":
        """Create CrossProtocolDependency from dictionary."""
        dep_type = data.get("dependency_type", "oracle")
        if isinstance(dep_type, str):
            dep_type = DependencyType(dep_type)

        confidence = data.get("confidence", "inferred")
        if isinstance(confidence, str):
            confidence = Confidence.from_string(confidence)

        return cls(
            protocol_id=str(data.get("protocol_id", "")),
            dependency_type=dep_type,
            description=str(data.get("description", "")),
            criticality=int(data.get("criticality", 5)),
            failure_cascade_impact=str(data.get("failure_cascade_impact", "")),
            last_verified_date=str(data.get("last_verified_date", "")),
            confidence=confidence,
            affected_functions=list(data.get("affected_functions", [])),
        )


@dataclass
class ContractPassport:
    """Per-contract economic summary with cross-protocol dependencies.

    Per 05.11-CONTEXT.md: Compact passport attached to contract nodes
    that captures economic role, controls, and dependencies.

    Attributes:
        contract_id: Contract identifier (name or address)
        economic_purpose: What economic role this contract serves
        assets_handled: Assets under custody/control (ETH, USDC, tokens)
        critical_actions: High-risk actions (deposit, withdraw, liquidate, upgrade)
        allowed_lifecycle_stages: Which stages this contract can be in
        roles_controls: Map of role -> capabilities for this contract
        external_dependencies: Off-chain dependencies (oracles, keepers)
        cross_protocol_dependencies: External protocol dependencies
        invariant_ids: References to InvariantRegistry entries
        systemic_risk_score: Derived from dependency centrality (0-10)
        created_at: When this passport was created
        last_updated: When this passport was last updated
    """

    contract_id: str
    economic_purpose: str = ""
    assets_handled: List[str] = field(default_factory=list)
    critical_actions: List[str] = field(default_factory=list)
    allowed_lifecycle_stages: List[LifecycleStage] = field(default_factory=list)
    roles_controls: Dict[str, List[str]] = field(default_factory=dict)
    external_dependencies: List[str] = field(default_factory=list)
    cross_protocol_dependencies: List[CrossProtocolDependency] = field(default_factory=list)
    invariant_ids: List[str] = field(default_factory=list)
    systemic_risk_score: float = 0.0
    created_at: str = ""
    last_updated: str = ""

    def __post_init__(self) -> None:
        """Initialize timestamps and validate risk score."""
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.last_updated:
            self.last_updated = now

        if not 0.0 <= self.systemic_risk_score <= 10.0:
            raise ValueError(f"systemic_risk_score must be 0-10, got {self.systemic_risk_score}")

    @property
    def has_critical_dependencies(self) -> bool:
        """Check if contract has any critical dependencies."""
        return any(dep.is_critical for dep in self.cross_protocol_dependencies)

    @property
    def dependency_count(self) -> int:
        """Total number of cross-protocol dependencies."""
        return len(self.cross_protocol_dependencies)

    @property
    def is_high_systemic_risk(self) -> bool:
        """Whether this contract has high systemic risk (>= 7)."""
        return self.systemic_risk_score >= 7.0

    @property
    def oracle_dependencies(self) -> List[CrossProtocolDependency]:
        """Get oracle dependencies."""
        return [dep for dep in self.cross_protocol_dependencies if dep.is_oracle]

    def add_dependency(self, dependency: CrossProtocolDependency) -> None:
        """Add a cross-protocol dependency.

        Args:
            dependency: CrossProtocolDependency to add
        """
        self.cross_protocol_dependencies.append(dependency)
        self._recalculate_systemic_risk()

    def add_invariant(self, invariant_id: str) -> None:
        """Add an invariant reference.

        Args:
            invariant_id: InvariantRegistry entry ID
        """
        if invariant_id not in self.invariant_ids:
            self.invariant_ids.append(invariant_id)

    def _recalculate_systemic_risk(self) -> None:
        """Recalculate systemic risk score based on dependencies.

        Risk factors:
        - Number of critical dependencies
        - Dependency centrality (unique protocols)
        - Oracle reliance
        - Assets at risk
        """
        if not self.cross_protocol_dependencies:
            self.systemic_risk_score = 0.0
            return

        # Base score from dependency criticality (weighted average)
        total_criticality = sum(dep.criticality for dep in self.cross_protocol_dependencies)
        avg_criticality = total_criticality / len(self.cross_protocol_dependencies)

        # Bonus for critical dependencies
        critical_count = sum(1 for dep in self.cross_protocol_dependencies if dep.is_critical)
        critical_bonus = min(critical_count * 0.5, 2.0)

        # Bonus for oracle dependencies (higher manipulation risk)
        oracle_count = len(self.oracle_dependencies)
        oracle_bonus = min(oracle_count * 0.3, 1.0)

        # Dependency centrality (more unique protocols = more risk)
        unique_protocols = len(set(dep.protocol_id for dep in self.cross_protocol_dependencies))
        centrality_bonus = min(unique_protocols * 0.2, 1.5)

        # Calculate final score (capped at 10)
        risk_score = avg_criticality + critical_bonus + oracle_bonus + centrality_bonus
        self.systemic_risk_score = min(risk_score, 10.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "contract_id": self.contract_id,
            "economic_purpose": self.economic_purpose,
            "assets_handled": self.assets_handled,
            "critical_actions": self.critical_actions,
            "allowed_lifecycle_stages": [s.value for s in self.allowed_lifecycle_stages],
            "roles_controls": self.roles_controls,
            "external_dependencies": self.external_dependencies,
            "cross_protocol_dependencies": [dep.to_dict() for dep in self.cross_protocol_dependencies],
            "invariant_ids": self.invariant_ids,
            "systemic_risk_score": self.systemic_risk_score,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContractPassport":
        """Create ContractPassport from dictionary."""
        stages = []
        for stage in data.get("allowed_lifecycle_stages", []):
            if isinstance(stage, str):
                stages.append(LifecycleStage(stage))
            elif isinstance(stage, LifecycleStage):
                stages.append(stage)

        return cls(
            contract_id=str(data.get("contract_id", "")),
            economic_purpose=str(data.get("economic_purpose", "")),
            assets_handled=list(data.get("assets_handled", [])),
            critical_actions=list(data.get("critical_actions", [])),
            allowed_lifecycle_stages=stages,
            roles_controls=dict(data.get("roles_controls", {})),
            external_dependencies=list(data.get("external_dependencies", [])),
            cross_protocol_dependencies=[
                CrossProtocolDependency.from_dict(dep)
                for dep in data.get("cross_protocol_dependencies", [])
            ],
            invariant_ids=list(data.get("invariant_ids", [])),
            systemic_risk_score=float(data.get("systemic_risk_score", 0.0)),
            created_at=str(data.get("created_at", "")),
            last_updated=str(data.get("last_updated", "")),
        )


class PassportBuilder:
    """Builder for contract passports from context pack and code analysis.

    Per 05.11-CONTEXT.md: Generate passports for each contract combining
    dossier information with code-derived facts.

    Usage:
        builder = PassportBuilder(context_pack, kg_nodes)
        passports = builder.build_all()

        # Get specific passport
        vault_passport = builder.get_passport("Vault")
    """

    def __init__(
        self,
        context_pack: Optional["ProtocolContextPack"] = None,
        kg_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Initialize the passport builder.

        Args:
            context_pack: Optional ProtocolContextPack for dossier data
            kg_nodes: Optional list of KG contract nodes
        """
        self._context_pack = context_pack
        self._kg_nodes = kg_nodes or []
        self._passports: Dict[str, ContractPassport] = {}

    def build_all(self) -> Dict[str, ContractPassport]:
        """Build passports for all known contracts.

        Returns:
            Dict mapping contract_id to ContractPassport
        """
        # Start with contracts from KG
        for node in self._kg_nodes:
            if node.get("type") == "contract":
                contract_id = node.get("label") or node.get("id", "")
                if contract_id and contract_id not in self._passports:
                    self._passports[contract_id] = self._build_passport_from_node(node)

        # Enrich with context pack data
        if self._context_pack:
            self._enrich_from_context_pack()

        return self._passports.copy()

    def _build_passport_from_node(self, node: Dict[str, Any]) -> ContractPassport:
        """Build initial passport from KG contract node.

        Args:
            node: KG contract node

        Returns:
            ContractPassport with code-derived facts
        """
        contract_id = node.get("label") or node.get("id", "")
        props = node.get("properties", {})

        # Extract facts from node properties
        critical_actions = []
        external_deps = []
        assets = []

        # Functions with high-risk operations
        functions = props.get("functions", [])
        for fn in functions:
            fn_props = fn.get("properties", {}) if isinstance(fn, dict) else {}
            ops = fn_props.get("operations", [])

            if "TRANSFERS_VALUE_OUT" in ops or "WRITES_USER_BALANCE" in ops:
                fn_name = fn.get("name", "") if isinstance(fn, dict) else str(fn)
                if fn_name:
                    critical_actions.append(fn_name)

            if "READS_ORACLE" in ops or "CALLS_EXTERNAL" in ops:
                fn_name = fn.get("name", "") if isinstance(fn, dict) else str(fn)
                if fn_name:
                    external_deps.append(f"external:{fn_name}")

        # Default lifecycle stages
        stages = [LifecycleStage.ACTIVE]
        if props.get("has_pause", False):
            stages.append(LifecycleStage.PAUSED)
        if props.get("is_upgradeable", False):
            stages.append(LifecycleStage.UPGRADE)

        return ContractPassport(
            contract_id=contract_id,
            economic_purpose="",  # To be enriched from context pack
            assets_handled=assets,
            critical_actions=list(set(critical_actions)),
            allowed_lifecycle_stages=stages,
            external_dependencies=list(set(external_deps)),
        )

    def _enrich_from_context_pack(self) -> None:
        """Enrich passports with data from context pack."""
        if not self._context_pack:
            return

        # Map roles to contracts
        for role in self._context_pack.roles:
            for cap in role.capabilities:
                # Try to match capability to contract
                for contract_id, passport in self._passports.items():
                    if contract_id.lower() in cap.lower():
                        if role.name not in passport.roles_controls:
                            passport.roles_controls[role.name] = []
                        passport.roles_controls[role.name].append(cap)

        # Map offchain inputs to dependencies
        for offchain in self._context_pack.offchain_inputs:
            # Create cross-protocol dependency
            dep_type = DependencyType.ORACLE if offchain.is_oracle() else DependencyType.KEEPER
            dep = CrossProtocolDependency(
                protocol_id=offchain.name,
                dependency_type=dep_type,
                description=offchain.description,
                criticality=7 if offchain.is_oracle() else 5,
                affected_functions=offchain.affects_functions,
                confidence=offchain.confidence,
            )

            # Add to affected contracts
            for fn in offchain.affects_functions:
                for contract_id, passport in self._passports.items():
                    if contract_id.lower() in fn.lower():
                        passport.add_dependency(dep)
                        break

        # Map value flows to economic purpose
        for flow in self._context_pack.value_flows:
            for contract_id, passport in self._passports.items():
                if contract_id.lower() in flow.name.lower():
                    if not passport.economic_purpose:
                        passport.economic_purpose = f"Handles {flow.asset} {flow.name}"
                    if flow.asset and flow.asset not in passport.assets_handled:
                        passport.assets_handled.append(flow.asset)

        # Map invariants
        for idx, invariant in enumerate(self._context_pack.invariants):
            invariant_id = f"inv:{idx}:{invariant.category}"
            # Match invariants to contracts by checking natural language
            for contract_id, passport in self._passports.items():
                if contract_id.lower() in invariant.natural_language.lower():
                    passport.add_invariant(invariant_id)

        # Map critical functions
        for critical_fn in self._context_pack.critical_functions:
            for contract_id, passport in self._passports.items():
                if contract_id.lower() in critical_fn.lower():
                    fn_name = critical_fn.split(".")[-1] if "." in critical_fn else critical_fn
                    if fn_name not in passport.critical_actions:
                        passport.critical_actions.append(fn_name)

    def get_passport(self, contract_id: str) -> Optional[ContractPassport]:
        """Get passport for a specific contract.

        Args:
            contract_id: Contract identifier

        Returns:
            ContractPassport if found, None otherwise
        """
        return self._passports.get(contract_id)

    def add_cross_protocol_dependency(
        self,
        contract_id: str,
        dependency: CrossProtocolDependency,
    ) -> bool:
        """Manually add a cross-protocol dependency to a passport.

        Args:
            contract_id: Target contract
            dependency: CrossProtocolDependency to add

        Returns:
            True if added, False if contract not found
        """
        if contract_id not in self._passports:
            return False

        self._passports[contract_id].add_dependency(dependency)
        return True

    def get_high_risk_contracts(self, threshold: float = 7.0) -> List[ContractPassport]:
        """Get contracts with high systemic risk.

        Args:
            threshold: Minimum systemic risk score

        Returns:
            List of high-risk ContractPassport objects
        """
        return [
            passport
            for passport in self._passports.values()
            if passport.systemic_risk_score >= threshold
        ]

    def get_oracle_dependent_contracts(self) -> List[ContractPassport]:
        """Get contracts that depend on oracles.

        Returns:
            List of oracle-dependent ContractPassport objects
        """
        return [
            passport
            for passport in self._passports.values()
            if any(dep.is_oracle for dep in passport.cross_protocol_dependencies)
        ]

    def stats(self) -> Dict[str, Any]:
        """Get passport builder statistics.

        Returns:
            Dict with counts and summaries
        """
        total = len(self._passports)
        high_risk = len(self.get_high_risk_contracts())
        oracle_dependent = len(self.get_oracle_dependent_contracts())

        total_deps = sum(
            passport.dependency_count
            for passport in self._passports.values()
        )

        return {
            "total_contracts": total,
            "high_risk_contracts": high_risk,
            "oracle_dependent_contracts": oracle_dependent,
            "total_dependencies": total_deps,
            "avg_systemic_risk": sum(
                p.systemic_risk_score for p in self._passports.values()
            ) / total if total > 0 else 0.0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert all passports to dictionary for serialization."""
        return {
            contract_id: passport.to_dict()
            for contract_id, passport in self._passports.items()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PassportBuilder":
        """Create PassportBuilder from dictionary."""
        builder = cls()
        for contract_id, passport_data in data.items():
            builder._passports[contract_id] = ContractPassport.from_dict(passport_data)
        return builder


# Export all types
__all__ = [
    "DependencyType",
    "LifecycleStage",
    "CrossProtocolDependency",
    "ContractPassport",
    "PassportBuilder",
]
