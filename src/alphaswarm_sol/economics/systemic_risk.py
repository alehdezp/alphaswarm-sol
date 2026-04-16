"""Cross-protocol systemic risk scoring.

Per 05.11-CONTEXT.md: Compute systemic risk from cross-protocol dependencies
using contract passports and dependency centrality analysis.

Key features:
- SystemicRiskScorer: Compute systemic risk from protocol dependencies
- SystemicRiskScore: Result with total score and component breakdown
- CascadeRisk: Risk of cascade failures affecting other protocols
- DependencyCentrality: Centrality metrics for protocol dependencies

Usage:
    from alphaswarm_sol.economics.systemic_risk import (
        SystemicRiskScorer,
        SystemicRiskScore,
        CascadeRisk,
        DependencyCentrality,
    )

    scorer = SystemicRiskScorer(passports=passports)

    # Compute systemic risk for a protocol
    score = scorer.compute_systemic_risk("aave-v3")
    print(f"Systemic risk: {score.total_score:.1f}/10")
    print(f"Cascade risk: {score.cascade_risk.affected_tvl_usd:,.0f} USD")
    print(f"Centrality: {score.centrality.degree:.2f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.context.passports import ContractPassport, CrossProtocolDependency


class DependencyRole(Enum):
    """Role of a protocol in the dependency graph.

    Used to classify protocols by their systemic importance.
    """

    CORE = "core"  # Core infrastructure (bridges, oracles)
    LIQUIDITY = "liquidity"  # Major liquidity sources (DEXs, lending)
    PERIPHERAL = "peripheral"  # Application-layer protocols
    ISOLATED = "isolated"  # Minimal external dependencies


@dataclass
class DependencyCentrality:
    """Centrality metrics for a protocol in the dependency graph.

    Per 05.11-CONTEXT.md: How central is this protocol in the DeFi graph?
    Higher centrality = more systemic importance.

    Attributes:
        protocol_id: Protocol identifier
        degree: Number of direct dependencies (in + out)
        in_degree: Number of protocols that depend on this one
        out_degree: Number of protocols this one depends on
        betweenness: Betweenness centrality (0-1, how often on shortest paths)
        role: Classified role in the ecosystem
    """

    protocol_id: str
    degree: int = 0
    in_degree: int = 0
    out_degree: int = 0
    betweenness: float = 0.0
    role: DependencyRole = DependencyRole.PERIPHERAL

    def __post_init__(self) -> None:
        """Validate betweenness range."""
        if not 0.0 <= self.betweenness <= 1.0:
            self.betweenness = max(0.0, min(1.0, self.betweenness))

    @property
    def is_highly_central(self) -> bool:
        """Whether this protocol is highly central (degree >= 5 or betweenness >= 0.3)."""
        return self.degree >= 5 or self.betweenness >= 0.3

    @property
    def is_core_infrastructure(self) -> bool:
        """Whether this is core infrastructure."""
        return self.role == DependencyRole.CORE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol_id": self.protocol_id,
            "degree": self.degree,
            "in_degree": self.in_degree,
            "out_degree": self.out_degree,
            "betweenness": round(self.betweenness, 3),
            "role": self.role.value,
            "is_highly_central": self.is_highly_central,
            "is_core_infrastructure": self.is_core_infrastructure,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DependencyCentrality":
        """Create DependencyCentrality from dictionary."""
        role = data.get("role", "peripheral")
        if isinstance(role, str):
            try:
                role = DependencyRole(role)
            except ValueError:
                role = DependencyRole.PERIPHERAL

        return cls(
            protocol_id=str(data.get("protocol_id", "")),
            degree=int(data.get("degree", 0)),
            in_degree=int(data.get("in_degree", 0)),
            out_degree=int(data.get("out_degree", 0)),
            betweenness=float(data.get("betweenness", 0.0)),
            role=role,
        )


@dataclass
class CascadeRisk:
    """Risk of cascade failures if this protocol fails.

    Per 05.11-CONTEXT.md: If this protocol fails, what TVL is at risk
    across dependent protocols?

    Attributes:
        protocol_id: Protocol identifier
        affected_protocols: List of protocols that would be affected
        affected_tvl_usd: Total TVL at risk across affected protocols
        cascade_depth: Maximum depth of cascade (1 = direct, 2+ = indirect)
        critical_path_count: Number of critical dependency paths
        worst_case_scenario: Description of worst-case cascade
    """

    protocol_id: str
    affected_protocols: List[str] = field(default_factory=list)
    affected_tvl_usd: float = 0.0
    cascade_depth: int = 1
    critical_path_count: int = 0
    worst_case_scenario: str = ""

    @property
    def is_high_cascade_risk(self) -> bool:
        """Whether cascade risk is high (affects 3+ protocols or $10M+ TVL)."""
        return len(self.affected_protocols) >= 3 or self.affected_tvl_usd >= 10_000_000

    @property
    def has_deep_cascade(self) -> bool:
        """Whether cascade has depth >= 2 (indirect effects)."""
        return self.cascade_depth >= 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol_id": self.protocol_id,
            "affected_protocols": self.affected_protocols,
            "affected_tvl_usd": round(self.affected_tvl_usd, 2),
            "cascade_depth": self.cascade_depth,
            "critical_path_count": self.critical_path_count,
            "worst_case_scenario": self.worst_case_scenario,
            "is_high_cascade_risk": self.is_high_cascade_risk,
            "has_deep_cascade": self.has_deep_cascade,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CascadeRisk":
        """Create CascadeRisk from dictionary."""
        return cls(
            protocol_id=str(data.get("protocol_id", "")),
            affected_protocols=list(data.get("affected_protocols", [])),
            affected_tvl_usd=float(data.get("affected_tvl_usd", 0.0)),
            cascade_depth=int(data.get("cascade_depth", 1)),
            critical_path_count=int(data.get("critical_path_count", 0)),
            worst_case_scenario=str(data.get("worst_case_scenario", "")),
        )


@dataclass
class SystemicRiskScore:
    """Full systemic risk score with component breakdown.

    Per 05.11-CONTEXT.md: Systemic risk scoring based on dependency
    centrality and cascade risk.

    Attributes:
        protocol_id: Protocol identifier
        total_score: Combined systemic risk score (0-10)
        centrality: Dependency centrality metrics
        cascade_risk: Cascade failure risk
        oracle_dependency_score: Risk from oracle dependencies (0-3)
        bridge_dependency_score: Risk from bridge dependencies (0-2)
        governance_concentration: Risk from governance concentration (0-2)
        evidence_refs: Evidence supporting this assessment
        notes: Additional analysis notes
    """

    protocol_id: str
    total_score: float
    centrality: DependencyCentrality
    cascade_risk: CascadeRisk
    oracle_dependency_score: float = 0.0
    bridge_dependency_score: float = 0.0
    governance_concentration: float = 0.0
    evidence_refs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate score ranges."""
        if not 0.0 <= self.total_score <= 10.0:
            self.total_score = max(0.0, min(10.0, self.total_score))

    @property
    def is_high_systemic_risk(self) -> bool:
        """Whether this is high systemic risk (>= 7)."""
        return self.total_score >= 7.0

    @property
    def risk_level(self) -> str:
        """Human-readable risk level."""
        if self.total_score >= 8.0:
            return "critical"
        elif self.total_score >= 6.0:
            return "high"
        elif self.total_score >= 4.0:
            return "medium"
        elif self.total_score >= 2.0:
            return "low"
        else:
            return "minimal"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol_id": self.protocol_id,
            "total_score": round(self.total_score, 2),
            "risk_level": self.risk_level,
            "components": {
                "oracle_dependency": round(self.oracle_dependency_score, 2),
                "bridge_dependency": round(self.bridge_dependency_score, 2),
                "governance_concentration": round(self.governance_concentration, 2),
            },
            "centrality": self.centrality.to_dict(),
            "cascade_risk": self.cascade_risk.to_dict(),
            "is_high_systemic_risk": self.is_high_systemic_risk,
            "evidence_refs": self.evidence_refs,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemicRiskScore":
        """Create SystemicRiskScore from dictionary."""
        components = data.get("components", {})

        return cls(
            protocol_id=str(data.get("protocol_id", "")),
            total_score=float(data.get("total_score", 0)),
            centrality=DependencyCentrality.from_dict(data.get("centrality", {})),
            cascade_risk=CascadeRisk.from_dict(data.get("cascade_risk", {})),
            oracle_dependency_score=float(components.get("oracle_dependency", 0)),
            bridge_dependency_score=float(components.get("bridge_dependency", 0)),
            governance_concentration=float(components.get("governance_concentration", 0)),
            evidence_refs=list(data.get("evidence_refs", [])),
            notes=list(data.get("notes", [])),
        )


class SystemicRiskScorer:
    """Compute cross-protocol systemic risk scores.

    Per 05.11-CONTEXT.md: Uses cross_protocol_dependencies from passports
    to compute systemic risk based on dependency centrality and cascade risk.

    Usage:
        scorer = SystemicRiskScorer(passports=passports)
        score = scorer.compute_systemic_risk("aave-v3")
    """

    # TVL thresholds for cascade risk scoring
    CASCADE_TVL_THRESHOLDS = [
        (1_000_000_000, 3.0),  # >= $1B
        (100_000_000, 2.0),  # >= $100M
        (10_000_000, 1.0),  # >= $10M
        (0, 0.5),  # < $10M
    ]

    # Well-known core infrastructure protocols
    CORE_PROTOCOLS = {
        "chainlink",
        "maker",
        "aave",
        "compound",
        "uniswap",
        "curve",
        "lido",
        "ethereum",
        "arbitrum",
        "optimism",
        "polygon",
        "wormhole",
        "layerzero",
    }

    def __init__(
        self,
        passports: Optional[Dict[str, "ContractPassport"]] = None,
        protocol_tvl: Optional[Dict[str, float]] = None,
    ) -> None:
        """Initialize the systemic risk scorer.

        Args:
            passports: Optional mapping of contract_id to ContractPassport
            protocol_tvl: Optional mapping of protocol_id to TVL in USD
        """
        self._passports = passports or {}
        self._protocol_tvl = protocol_tvl or {}
        self._dependency_graph: Dict[str, Set[str]] = {}  # protocol -> dependents
        self._reverse_graph: Dict[str, Set[str]] = {}  # protocol -> dependencies

    def compute_systemic_risk(
        self,
        protocol_id: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> SystemicRiskScore:
        """Compute systemic risk score for a protocol.

        Args:
            protocol_id: Protocol identifier
            evidence_refs: Optional evidence references

        Returns:
            SystemicRiskScore with full analysis
        """
        notes: List[str] = []
        refs = evidence_refs or []

        # Build dependency graph from passports
        self._build_dependency_graph()

        # Compute centrality metrics
        centrality = self._compute_centrality(protocol_id)
        if centrality.is_highly_central:
            notes.append(f"Highly central: degree={centrality.degree}")

        # Compute cascade risk
        cascade_risk = self._compute_cascade_risk(protocol_id)
        if cascade_risk.is_high_cascade_risk:
            notes.append(f"High cascade risk: {len(cascade_risk.affected_protocols)} protocols affected")

        # Compute component scores
        oracle_score = self._compute_oracle_dependency_score(protocol_id)
        bridge_score = self._compute_bridge_dependency_score(protocol_id)
        governance_score = self._compute_governance_concentration(protocol_id)

        # Calculate total score
        # Base score from centrality (0-3)
        base_score = min(3.0, centrality.degree * 0.5)

        # Add cascade risk contribution (0-3)
        cascade_contribution = self._cascade_tvl_to_score(cascade_risk.affected_tvl_usd)

        # Add component scores
        total_score = (
            base_score
            + cascade_contribution
            + oracle_score
            + bridge_score
            + governance_score
        )
        total_score = min(10.0, total_score)

        return SystemicRiskScore(
            protocol_id=protocol_id,
            total_score=total_score,
            centrality=centrality,
            cascade_risk=cascade_risk,
            oracle_dependency_score=oracle_score,
            bridge_dependency_score=bridge_score,
            governance_concentration=governance_score,
            evidence_refs=refs,
            notes=notes,
        )

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from passports."""
        self._dependency_graph.clear()
        self._reverse_graph.clear()

        for contract_id, passport in self._passports.items():
            # Get protocol ID from contract
            protocol_id = self._contract_to_protocol(contract_id)

            if protocol_id not in self._reverse_graph:
                self._reverse_graph[protocol_id] = set()

            for dep in passport.cross_protocol_dependencies:
                dep_protocol = dep.protocol_id.lower()

                # Add to reverse graph (protocol depends on dep_protocol)
                self._reverse_graph[protocol_id].add(dep_protocol)

                # Add to dependency graph (dep_protocol has dependent protocol)
                if dep_protocol not in self._dependency_graph:
                    self._dependency_graph[dep_protocol] = set()
                self._dependency_graph[dep_protocol].add(protocol_id)

    def _contract_to_protocol(self, contract_id: str) -> str:
        """Extract protocol ID from contract ID."""
        # Simple heuristic: use lowercase contract name
        return contract_id.lower().split(".")[0]

    def _compute_centrality(self, protocol_id: str) -> DependencyCentrality:
        """Compute centrality metrics for a protocol."""
        protocol_lower = protocol_id.lower()

        # Count in-degree (protocols that depend on this one)
        in_degree = len(self._dependency_graph.get(protocol_lower, set()))

        # Count out-degree (protocols this one depends on)
        out_degree = len(self._reverse_graph.get(protocol_lower, set()))

        degree = in_degree + out_degree

        # Simple betweenness approximation
        # (Full betweenness requires all-pairs shortest paths)
        total_protocols = len(self._passports)
        if total_protocols > 0:
            betweenness = min(1.0, degree / (2 * total_protocols))
        else:
            betweenness = 0.0

        # Classify role
        if protocol_lower in self.CORE_PROTOCOLS:
            role = DependencyRole.CORE
        elif in_degree >= 3:
            role = DependencyRole.LIQUIDITY
        elif degree == 0:
            role = DependencyRole.ISOLATED
        else:
            role = DependencyRole.PERIPHERAL

        return DependencyCentrality(
            protocol_id=protocol_id,
            degree=degree,
            in_degree=in_degree,
            out_degree=out_degree,
            betweenness=betweenness,
            role=role,
        )

    def _compute_cascade_risk(self, protocol_id: str) -> CascadeRisk:
        """Compute cascade failure risk for a protocol."""
        protocol_lower = protocol_id.lower()

        # Find all protocols that would be affected if this protocol fails
        affected: Set[str] = set()
        queue = [protocol_lower]
        depth = 0
        max_depth = 0

        while queue and depth < 5:  # Limit to 5 hops
            next_queue = []
            for p in queue:
                dependents = self._dependency_graph.get(p, set())
                for dep in dependents:
                    if dep not in affected:
                        affected.add(dep)
                        next_queue.append(dep)
            if next_queue:
                max_depth = depth + 1
            queue = next_queue
            depth += 1

        # Calculate affected TVL
        affected_tvl = sum(
            self._protocol_tvl.get(p, 0)
            for p in affected
        )

        # Count critical paths (dependencies with criticality >= 8)
        critical_count = 0
        for contract_id, passport in self._passports.items():
            if self._contract_to_protocol(contract_id) in affected:
                for dep in passport.cross_protocol_dependencies:
                    if dep.protocol_id.lower() == protocol_lower and dep.criticality >= 8:
                        critical_count += 1

        # Generate worst-case scenario description
        if affected:
            worst_case = f"Failure could cascade to {len(affected)} protocols affecting ${affected_tvl:,.0f} in TVL"
        else:
            worst_case = "No significant cascade risk detected"

        return CascadeRisk(
            protocol_id=protocol_id,
            affected_protocols=list(affected),
            affected_tvl_usd=affected_tvl,
            cascade_depth=max_depth,
            critical_path_count=critical_count,
            worst_case_scenario=worst_case,
        )

    def _compute_oracle_dependency_score(self, protocol_id: str) -> float:
        """Compute oracle dependency risk score (0-3)."""
        oracle_count = 0
        critical_oracle_count = 0

        for contract_id, passport in self._passports.items():
            if self._contract_to_protocol(contract_id) == protocol_id.lower():
                for dep in passport.cross_protocol_dependencies:
                    if dep.is_oracle:
                        oracle_count += 1
                        if dep.criticality >= 8:
                            critical_oracle_count += 1

        # Score based on oracle dependency
        score = min(3.0, oracle_count * 0.5 + critical_oracle_count * 1.0)
        return score

    def _compute_bridge_dependency_score(self, protocol_id: str) -> float:
        """Compute bridge dependency risk score (0-2)."""
        from alphaswarm_sol.context.passports import DependencyType

        bridge_count = 0

        for contract_id, passport in self._passports.items():
            if self._contract_to_protocol(contract_id) == protocol_id.lower():
                for dep in passport.cross_protocol_dependencies:
                    if dep.dependency_type == DependencyType.BRIDGE:
                        bridge_count += 1

        # Score based on bridge dependency
        score = min(2.0, bridge_count * 1.0)
        return score

    def _compute_governance_concentration(self, protocol_id: str) -> float:
        """Compute governance concentration risk score (0-2)."""
        # Check for concentrated governance from passport data
        single_admin_count = 0

        for contract_id, passport in self._passports.items():
            if self._contract_to_protocol(contract_id) == protocol_id.lower():
                # Check if single admin controls critical functions
                for role, capabilities in passport.roles_controls.items():
                    if "admin" in role.lower() and len(capabilities) >= 3:
                        single_admin_count += 1

        # Score based on governance concentration
        score = min(2.0, single_admin_count * 0.5)
        return score

    def _cascade_tvl_to_score(self, tvl_usd: float) -> float:
        """Convert cascade TVL to risk score (0-3)."""
        for threshold, score in self.CASCADE_TVL_THRESHOLDS:
            if tvl_usd >= threshold:
                return score
        return 0.5

    def add_passport(self, contract_id: str, passport: "ContractPassport") -> None:
        """Add a contract passport for analysis."""
        self._passports[contract_id] = passport

    def set_protocol_tvl(self, protocol_id: str, tvl_usd: float) -> None:
        """Set TVL for a protocol."""
        self._protocol_tvl[protocol_id.lower()] = tvl_usd


# Export all types
__all__ = [
    "DependencyRole",
    "DependencyCentrality",
    "CascadeRisk",
    "SystemicRiskScore",
    "SystemicRiskScorer",
]
