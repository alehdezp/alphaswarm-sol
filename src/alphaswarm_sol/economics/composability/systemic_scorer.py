"""Systemic risk scorer with GATE integration for CPCRM.

Per 05.11-10: Compute systemic risk scores based on protocol centrality,
cascade potential, and GATE-filtered multi-protocol attack paths.

Key Features:
- SystemicScorer: Compute systemic risk from graph centrality and cascade
- CrossProtocolAttackPath: Multi-protocol attack with economic viability
- GATE integration: Filter attack paths by economic viability (EV > 0)
- Discovery of cross-protocol exploit chains

Usage:
    from alphaswarm_sol.economics.composability.systemic_scorer import (
        SystemicScorer,
        SystemicRiskAssessment,
        CrossProtocolAttackPath,
    )

    scorer = SystemicScorer(graph)
    assessment = scorer.compute_systemic_score("aave-v3")
    print(f"Systemic risk: {assessment.score}/10")
    print(f"Critical paths: {len(assessment.critical_paths)}")

    # Discover cross-protocol attacks
    attacks = scorer.discover_cross_protocol_attacks(vulnerability)
    for attack in attacks:
        if attack.is_economically_viable:
            print(f"Viable attack: {attack.path}, EV: ${attack.expected_value:,.0f}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol_graph import ProtocolDependencyGraph, CriticalPath
    from .cascade_simulator import CascadeSimulator, CascadeResult

logger = logging.getLogger(__name__)


@dataclass
class CrossProtocolAttackPath:
    """A multi-protocol attack path with economic viability analysis.

    Per 05.11-10: Represents an attack path that spans multiple protocols,
    with GATE integration to filter economically irrational paths.

    Attributes:
        path: Ordered list of protocol IDs in the attack path
        vulnerability_id: Initial vulnerability that enables the attack
        total_extractable_value: Total value extractable across protocols
        expected_value: Expected value after costs and risk adjustment
        gas_cost_usd: Estimated gas costs
        success_probability: Combined success probability
        description: Human-readable attack description
        is_economically_viable: Whether EV > gas costs + MEV protection
        priority: Attack priority (HIGH, MEDIUM, LOW_PRIORITY)
        gate_analysis: Optional GATE payoff matrix analysis
    """

    path: List[str]
    vulnerability_id: str
    total_extractable_value: Decimal = Decimal("0")
    expected_value: float = 0.0
    gas_cost_usd: float = 0.0
    success_probability: float = 0.5
    description: str = ""
    is_economically_viable: bool = False
    priority: str = "MEDIUM"
    gate_analysis: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate and compute viability."""
        if not self.path:
            raise ValueError("path cannot be empty")

        # Compute economic viability
        self._compute_viability()

    def _compute_viability(self) -> None:
        """Compute economic viability based on EV vs costs."""
        # Estimate MEV protection cost (roughly 10% of extractable value)
        mev_protection = float(self.total_extractable_value) * 0.1

        # EV = (extractable * success_prob) - gas - mev_protection
        ev = (float(self.total_extractable_value) * self.success_probability
              - self.gas_cost_usd - mev_protection)

        self.expected_value = ev
        self.is_economically_viable = ev > 0

        # Set priority based on EV
        if ev <= 0:
            self.priority = "LOW_PRIORITY"
        elif ev > 100_000:
            self.priority = "HIGH"
        else:
            self.priority = "MEDIUM"

    @property
    def path_length(self) -> int:
        """Number of protocols in the attack path."""
        return len(self.path)

    @property
    def is_multi_step(self) -> bool:
        """Whether this requires multiple steps (3+ protocols)."""
        return len(self.path) >= 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "vulnerability_id": self.vulnerability_id,
            "total_extractable_value": str(self.total_extractable_value),
            "expected_value": round(self.expected_value, 2),
            "gas_cost_usd": round(self.gas_cost_usd, 2),
            "success_probability": self.success_probability,
            "description": self.description,
            "is_economically_viable": self.is_economically_viable,
            "priority": self.priority,
            "gate_analysis": self.gate_analysis,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrossProtocolAttackPath":
        """Create CrossProtocolAttackPath from dictionary."""
        return cls(
            path=list(data.get("path", [])),
            vulnerability_id=str(data.get("vulnerability_id", "")),
            total_extractable_value=Decimal(str(data.get("total_extractable_value", "0"))),
            gas_cost_usd=float(data.get("gas_cost_usd", 0)),
            success_probability=float(data.get("success_probability", 0.5)),
            description=str(data.get("description", "")),
            gate_analysis=data.get("gate_analysis"),
        )


@dataclass
class SystemicRiskAssessment:
    """Full systemic risk assessment for a protocol.

    Per 05.11-10: Combines centrality, cascade risk, and attack paths
    into a comprehensive systemic risk score.

    Attributes:
        protocol_id: Protocol being assessed
        score: Overall systemic risk score (0-10)
        centrality_component: Score component from graph centrality (0-3)
        cascade_component: Score component from cascade analysis (0-4)
        dependency_component: Score component from dependency count (0-3)
        critical_paths: High-impact failure paths
        attack_paths: Discovered cross-protocol attack paths
        cascade_result: Optional full cascade simulation result
        evidence_refs: References supporting this assessment
        notes: Additional analysis notes
    """

    protocol_id: str
    score: float
    centrality_component: float = 0.0
    cascade_component: float = 0.0
    dependency_component: float = 0.0
    critical_paths: List["CriticalPath"] = field(default_factory=list)
    attack_paths: List[CrossProtocolAttackPath] = field(default_factory=list)
    cascade_result: Optional["CascadeResult"] = None
    evidence_refs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate score range."""
        if not 0.0 <= self.score <= 10.0:
            self.score = max(0.0, min(10.0, self.score))

    @property
    def is_high_systemic_risk(self) -> bool:
        """Whether this is high systemic risk (>= 7)."""
        return self.score >= 7.0

    @property
    def risk_level(self) -> str:
        """Human-readable risk level."""
        if self.score >= 8.0:
            return "critical"
        elif self.score >= 6.0:
            return "high"
        elif self.score >= 4.0:
            return "medium"
        elif self.score >= 2.0:
            return "low"
        else:
            return "minimal"

    @property
    def viable_attack_count(self) -> int:
        """Number of economically viable attack paths."""
        return sum(1 for a in self.attack_paths if a.is_economically_viable)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol_id": self.protocol_id,
            "score": round(self.score, 2),
            "risk_level": self.risk_level,
            "components": {
                "centrality": round(self.centrality_component, 2),
                "cascade": round(self.cascade_component, 2),
                "dependency": round(self.dependency_component, 2),
            },
            "critical_paths": [p.to_dict() for p in self.critical_paths],
            "attack_paths": [a.to_dict() for a in self.attack_paths],
            "viable_attack_count": self.viable_attack_count,
            "is_high_systemic_risk": self.is_high_systemic_risk,
            "evidence_refs": self.evidence_refs,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemicRiskAssessment":
        """Create SystemicRiskAssessment from dictionary."""
        components = data.get("components", {})

        return cls(
            protocol_id=str(data.get("protocol_id", "")),
            score=float(data.get("score", 0)),
            centrality_component=float(components.get("centrality", 0)),
            cascade_component=float(components.get("cascade", 0)),
            dependency_component=float(components.get("dependency", 0)),
            attack_paths=[
                CrossProtocolAttackPath.from_dict(a)
                for a in data.get("attack_paths", [])
            ],
            evidence_refs=list(data.get("evidence_refs", [])),
            notes=list(data.get("notes", [])),
        )


class SystemicScorer:
    """Systemic risk scorer with GATE integration.

    Per 05.11-10: Computes systemic risk scores based on:
    - Protocol centrality in the dependency graph
    - Cascade failure potential and TVL at risk
    - Multi-protocol attack paths filtered by economic viability

    GATE Integration:
    - Discovered attack paths are filtered using AttackSynthesisEngine
    - Only paths with EV > 0 (after gas + MEV protection) are marked viable
    - Economically irrational paths are tagged as LOW_PRIORITY

    Usage:
        scorer = SystemicScorer(graph)
        assessment = scorer.compute_systemic_score("chainlink")

        # Discover and filter attacks
        attacks = scorer.discover_cross_protocol_attacks(vuln)
        viable = [a for a in attacks if a.is_economically_viable]
    """

    # TVL thresholds for cascade scoring
    CASCADE_TVL_THRESHOLDS = [
        (Decimal("10_000_000_000"), 4.0),  # >= $10B
        (Decimal("1_000_000_000"), 3.0),   # >= $1B
        (Decimal("100_000_000"), 2.0),     # >= $100M
        (Decimal("10_000_000"), 1.0),      # >= $10M
        (Decimal("0"), 0.5),               # < $10M
    ]

    def __init__(
        self,
        graph: "ProtocolDependencyGraph",
        simulator: Optional["CascadeSimulator"] = None,
    ) -> None:
        """Initialize systemic scorer.

        Args:
            graph: Protocol dependency graph
            simulator: Optional cascade simulator (created if not provided)
        """
        self._graph = graph
        self._simulator = simulator
        self._centrality_cache: Optional[Dict[str, float]] = None

    def compute_systemic_score(
        self,
        protocol_id: str,
        include_cascade: bool = True,
        evidence_refs: Optional[List[str]] = None,
    ) -> SystemicRiskAssessment:
        """Compute systemic risk score for a protocol.

        Per 05.11-10: Combines centrality, cascade risk, and dependency count
        into a comprehensive systemic risk score (0-10).

        Args:
            protocol_id: Protocol to assess
            include_cascade: Whether to run cascade simulation
            evidence_refs: Optional evidence references

        Returns:
            SystemicRiskAssessment with full analysis
        """
        protocol = protocol_id.lower()
        notes: List[str] = []
        refs = evidence_refs or []

        # Get or compute centrality
        if self._centrality_cache is None:
            self._centrality_cache = self._graph.compute_centrality()

        centrality = self._centrality_cache.get(protocol, 0.0)

        # Centrality component (0-3)
        centrality_component = centrality * 3.0
        if centrality >= 0.7:
            notes.append(f"High centrality: {centrality:.2f}")

        # Dependency component (0-3)
        deps_out = len(self._graph.get_dependencies(protocol))
        deps_in = len(self._graph.get_dependents(protocol))
        dep_count = deps_out + deps_in
        dependency_component = min(3.0, dep_count * 0.3)

        if deps_in >= 5:
            notes.append(f"Critical infrastructure: {deps_in} dependents")

        # Cascade component (0-4)
        cascade_component = 0.0
        cascade_result: Optional["CascadeResult"] = None

        if include_cascade:
            from .cascade_simulator import CascadeSimulator, FailureType

            simulator = self._simulator or CascadeSimulator(self._graph)
            cascade_result = simulator.estimate_worst_case(protocol)

            cascade_component = self._tvl_to_cascade_score(cascade_result.total_tvl_at_risk)

            if cascade_result.is_systemic:
                notes.append(f"Systemic cascade: {cascade_result.affected_count} protocols affected")
            if cascade_result.is_high_impact:
                notes.append(f"High impact: ${cascade_result.total_tvl_at_risk:,.0f} TVL at risk")

        # Find critical paths
        critical_paths = [
            p for p in self._graph.find_critical_paths()
            if protocol in p.path
        ][:5]  # Top 5

        # Total score
        total_score = centrality_component + cascade_component + dependency_component
        total_score = min(10.0, total_score)

        logger.info(
            f"Systemic score for {protocol}: {total_score:.1f}/10 "
            f"(centrality={centrality_component:.1f}, cascade={cascade_component:.1f}, "
            f"deps={dependency_component:.1f})"
        )

        return SystemicRiskAssessment(
            protocol_id=protocol,
            score=total_score,
            centrality_component=centrality_component,
            cascade_component=cascade_component,
            dependency_component=dependency_component,
            critical_paths=critical_paths,
            cascade_result=cascade_result,
            evidence_refs=refs,
            notes=notes,
        )

    def discover_cross_protocol_attacks(
        self,
        vulnerability: Dict[str, Any],
        max_path_length: int = 4,
    ) -> List[CrossProtocolAttackPath]:
        """Discover multi-protocol attack paths for a vulnerability.

        Per 05.11-10: Combines single-protocol vulnerabilities into
        multi-step attacks and filters by economic viability using GATE.

        Args:
            vulnerability: Vulnerability data dict with:
                - id: Vulnerability identifier
                - protocol_id: Affected protocol
                - severity: Severity level
                - potential_profit_usd: Estimated profit (optional)
            max_path_length: Maximum attack path length

        Returns:
            List of CrossProtocolAttackPath with economic viability analysis
        """
        vuln_id = vulnerability.get("id", "unknown")
        start_protocol = vulnerability.get("protocol_id", "").lower()
        severity = vulnerability.get("severity", "medium").lower()
        base_profit = float(vulnerability.get("potential_profit_usd", 100_000))

        if not start_protocol:
            logger.warning(f"No protocol_id in vulnerability {vuln_id}")
            return []

        attack_paths: List[CrossProtocolAttackPath] = []

        # Find all paths from the vulnerable protocol
        critical_paths = self._graph.find_critical_paths()

        for critical_path in critical_paths:
            if start_protocol not in critical_path.path:
                continue

            # Extract path starting from vulnerable protocol
            start_idx = critical_path.path.index(start_protocol)
            attack_path = critical_path.path[start_idx:start_idx + max_path_length]

            if len(attack_path) < 2:
                continue

            # Calculate extractable value across path
            total_tvl = Decimal("0")
            for p in attack_path:
                node = self._graph.get_protocol(p)
                if node:
                    total_tvl += node.tvl

            # Estimate extractable value based on severity
            extraction_rates = {
                "critical": 0.05,  # 5% of TVL
                "high": 0.02,
                "medium": 0.01,
                "low": 0.001,
            }
            rate = extraction_rates.get(severity, 0.01)
            extractable = total_tvl * Decimal(str(rate)) + Decimal(str(base_profit))

            # Estimate gas cost (scales with path length)
            gas_cost = 500.0 * len(attack_path)  # Base $500 per protocol

            # Success probability decreases with path length
            success_prob = 0.7 ** len(attack_path)

            # Create attack path with GATE analysis
            attack = CrossProtocolAttackPath(
                path=attack_path,
                vulnerability_id=vuln_id,
                total_extractable_value=extractable,
                gas_cost_usd=gas_cost,
                success_probability=success_prob,
                description=self._generate_attack_description(attack_path, vuln_id),
            )

            # Run GATE analysis if available
            gate_analysis = self._run_gate_analysis(vulnerability, attack)
            if gate_analysis:
                attack.gate_analysis = gate_analysis

                # Update viability based on GATE
                if "expected_value_usd" in gate_analysis:
                    attack.expected_value = gate_analysis["expected_value_usd"]
                    attack.is_economically_viable = attack.expected_value > 0
                    attack.priority = "LOW_PRIORITY" if not attack.is_economically_viable else attack.priority

            attack_paths.append(attack)

        # Sort by expected value descending
        attack_paths.sort(key=lambda a: a.expected_value, reverse=True)

        logger.info(
            f"Discovered {len(attack_paths)} cross-protocol attacks for {vuln_id}, "
            f"{sum(1 for a in attack_paths if a.is_economically_viable)} viable"
        )

        return attack_paths

    def score_finding(
        self,
        finding: Dict[str, Any],
        protocol_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add systemic risk score to a finding.

        Per 05.11-10: Enrich a finding with systemic risk information
        from the protocol dependency graph.

        Args:
            finding: Finding dict to enrich
            protocol_id: Optional protocol override

        Returns:
            Finding with added systemic_risk field
        """
        protocol = protocol_id or finding.get("protocol_id", "").lower()

        if not protocol:
            finding["systemic_risk"] = {
                "score": 0.0,
                "risk_level": "unknown",
                "notes": ["No protocol_id provided"],
            }
            return finding

        # Compute systemic risk
        assessment = self.compute_systemic_score(protocol, include_cascade=False)

        # Add to finding
        finding["systemic_risk"] = {
            "score": round(assessment.score, 2),
            "risk_level": assessment.risk_level,
            "centrality": round(assessment.centrality_component, 2),
            "dependency_count": len(self._graph.get_dependencies(protocol)) +
                               len(self._graph.get_dependents(protocol)),
            "critical_paths": len(assessment.critical_paths),
            "notes": assessment.notes,
        }

        return finding

    def _tvl_to_cascade_score(self, tvl: Decimal) -> float:
        """Convert cascade TVL at risk to score component (0-4)."""
        for threshold, score in self.CASCADE_TVL_THRESHOLDS:
            if tvl >= threshold:
                return score
        return 0.5

    def _generate_attack_description(
        self,
        path: List[str],
        vuln_id: str,
    ) -> str:
        """Generate human-readable attack description."""
        if len(path) == 2:
            return f"Exploit {vuln_id} in {path[0]} to cascade to {path[1]}"
        else:
            middle = " -> ".join(path[1:-1])
            return f"Exploit {vuln_id} in {path[0]} -> {middle} -> cascade to {path[-1]}"

    def _run_gate_analysis(
        self,
        vulnerability: Dict[str, Any],
        attack: CrossProtocolAttackPath,
    ) -> Optional[Dict[str, Any]]:
        """Run GATE analysis on an attack path.

        Per 05.11-10: Use AttackSynthesisEngine to compute EV and filter
        economically irrational paths.

        Args:
            vulnerability: Base vulnerability data
            attack: CrossProtocolAttackPath to analyze

        Returns:
            GATE analysis dict or None if GATE unavailable
        """
        try:
            from ..gate.attack_synthesis import compute_attack_ev

            # Build multi-step vulnerability for GATE
            multi_step_vuln = {
                "id": f"{vulnerability.get('id', 'unknown')}-multi-step",
                "severity": vulnerability.get("severity", "medium"),
                "pattern_id": f"multi-protocol-{len(attack.path)}-step",
                "potential_profit_usd": float(attack.total_extractable_value),
                "success_probability": attack.success_probability,
                "gas_cost_estimate": int(attack.gas_cost_usd * 2000),  # Estimate gas units
            }

            # Run GATE
            matrix = compute_attack_ev(
                vulnerability=multi_step_vuln,
                tvl_usd=float(attack.total_extractable_value),
            )

            return {
                "expected_value_usd": matrix.expected_value_usd,
                "is_attack_dominant": matrix.is_attack_dominant(),
                "dominant_strategies": matrix.dominant_strategies,
                "scenario": matrix.scenario,
            }

        except ImportError:
            logger.debug("GATE module not available, skipping analysis")
            return None
        except Exception as e:
            logger.warning(f"GATE analysis failed: {e}")
            return None


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "CrossProtocolAttackPath",
    "SystemicRiskAssessment",
    "SystemicScorer",
]
