"""Cascade failure simulator for CPCRM.

Per 05.11-10: Simulate cascade failures through the protocol dependency graph
to estimate TVL at risk from protocol failures.

Key Features:
- CascadeSimulator: Simulate failure propagation through dependencies
- CascadeScenario: Define trigger and market conditions
- CascadeResult: Full cascade analysis with timeline and bottlenecks
- Propagation rules based on dependency type

Usage:
    from alphaswarm_sol.economics.composability.cascade_simulator import (
        CascadeSimulator,
        CascadeScenario,
        FailureType,
        MarketConditions,
    )

    simulator = CascadeSimulator(graph)
    result = simulator.simulate_failure(
        trigger_protocol="chainlink",
        failure_type=FailureType.ORACLE_MANIPULATION,
    )
    print(f"Affected protocols: {len(result.affected_protocols)}")
    print(f"TVL at risk: ${result.total_tvl_at_risk:,.0f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol_graph import ProtocolDependencyGraph, DependencyType


class FailureType(Enum):
    """Types of protocol failures that can trigger cascades.

    Per 05.11-10: Different failure types have different propagation
    characteristics and affected dependencies.
    """

    ORACLE_MANIPULATION = "oracle_manipulation"  # Oracle price manipulation
    EXPLOIT = "exploit"  # Smart contract exploit
    GOVERNANCE_ATTACK = "governance_attack"  # Malicious governance action
    LIQUIDITY_CRISIS = "liquidity_crisis"  # Liquidity drain/bank run
    BRIDGE_HACK = "bridge_hack"  # Bridge compromise
    DEPEG = "depeg"  # Stablecoin/token depeg
    INSOLVENCY = "insolvency"  # Protocol becomes insolvent


@dataclass
class MarketConditions:
    """Market conditions affecting cascade propagation.

    Attributes:
        eth_price_usd: ETH price in USD
        gas_price_gwei: Gas price in Gwei
        market_volatility: Volatility index (0-1, higher = more volatile)
        liquidity_stress: Liquidity stress level (0-1, higher = stressed)
    """

    eth_price_usd: float = 2000.0
    gas_price_gwei: float = 50.0
    market_volatility: float = 0.3
    liquidity_stress: float = 0.2

    @property
    def is_stressed(self) -> bool:
        """Whether market conditions are stressed."""
        return self.market_volatility > 0.5 or self.liquidity_stress > 0.5

    @property
    def cascade_multiplier(self) -> float:
        """Multiplier for cascade speed based on conditions.

        Higher volatility and stress = faster cascade propagation.
        """
        return 1.0 + self.market_volatility + self.liquidity_stress

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "eth_price_usd": self.eth_price_usd,
            "gas_price_gwei": self.gas_price_gwei,
            "market_volatility": self.market_volatility,
            "liquidity_stress": self.liquidity_stress,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketConditions":
        """Create MarketConditions from dictionary."""
        return cls(
            eth_price_usd=float(data.get("eth_price_usd", 2000.0)),
            gas_price_gwei=float(data.get("gas_price_gwei", 50.0)),
            market_volatility=float(data.get("market_volatility", 0.3)),
            liquidity_stress=float(data.get("liquidity_stress", 0.2)),
        )

    @classmethod
    def stressed(cls) -> "MarketConditions":
        """Create stressed market conditions."""
        return cls(
            market_volatility=0.7,
            liquidity_stress=0.6,
        )

    @classmethod
    def normal(cls) -> "MarketConditions":
        """Create normal market conditions."""
        return cls(
            market_volatility=0.2,
            liquidity_stress=0.1,
        )


@dataclass
class CascadeScenario:
    """A cascade failure scenario to simulate.

    Per 05.11-10: Defines the trigger protocol, failure type,
    and market conditions for simulation.

    Attributes:
        trigger: Protocol ID that triggers the cascade
        failure_type: Type of failure
        market_conditions: Market conditions during cascade
        failure_severity: Severity of the initial failure (0-1)
    """

    trigger: str
    failure_type: FailureType
    market_conditions: MarketConditions = field(default_factory=MarketConditions)
    failure_severity: float = 1.0

    def __post_init__(self) -> None:
        """Validate scenario."""
        self.trigger = self.trigger.lower()
        if not 0.0 <= self.failure_severity <= 1.0:
            raise ValueError(f"failure_severity must be 0-1, got {self.failure_severity}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trigger": self.trigger,
            "failure_type": self.failure_type.value,
            "market_conditions": self.market_conditions.to_dict(),
            "failure_severity": self.failure_severity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CascadeScenario":
        """Create CascadeScenario from dictionary."""
        failure_type = data.get("failure_type", "exploit")
        if isinstance(failure_type, str):
            failure_type = FailureType(failure_type)

        return cls(
            trigger=str(data.get("trigger", "")),
            failure_type=failure_type,
            market_conditions=MarketConditions.from_dict(
                data.get("market_conditions", {})
            ),
            failure_severity=float(data.get("failure_severity", 1.0)),
        )


@dataclass
class PropagationEvent:
    """A single propagation event in the cascade timeline.

    Attributes:
        protocol: Protocol ID affected
        time_offset: Time since cascade start
        impact_severity: Severity of impact (0-1)
        propagation_source: Protocol that caused this propagation
        dependency_type: Type of dependency that caused propagation
    """

    protocol: str
    time_offset: timedelta
    impact_severity: float
    propagation_source: str
    dependency_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "protocol": self.protocol,
            "time_offset_seconds": int(self.time_offset.total_seconds()),
            "impact_severity": self.impact_severity,
            "propagation_source": self.propagation_source,
            "dependency_type": self.dependency_type,
        }


@dataclass
class CascadeResult:
    """Result of cascade failure simulation.

    Per 05.11-10: Full cascade analysis with affected protocols,
    TVL at risk, timeline, and bottleneck identification.

    Attributes:
        trigger_protocol: Protocol that triggered the cascade
        failure_type: Type of initial failure
        affected_protocols: List of affected protocols (ordered by impact time)
        total_tvl_at_risk: Total TVL at risk across all affected protocols
        propagation_timeline: Ordered list of propagation events
        critical_bottlenecks: Single points of failure (protocols that propagate to many)
        cascade_depth: Maximum depth of propagation
        simulation_time: How long the simulation ran
    """

    trigger_protocol: str
    failure_type: FailureType
    affected_protocols: List[str] = field(default_factory=list)
    total_tvl_at_risk: Decimal = Decimal("0")
    propagation_timeline: List[PropagationEvent] = field(default_factory=list)
    critical_bottlenecks: List[str] = field(default_factory=list)
    cascade_depth: int = 0
    simulation_time: timedelta = field(default_factory=lambda: timedelta(hours=24))

    @property
    def is_systemic(self) -> bool:
        """Whether this is a systemic cascade (affects 5+ protocols)."""
        return len(self.affected_protocols) >= 5

    @property
    def is_high_impact(self) -> bool:
        """Whether this is high-impact (>$100M at risk)."""
        return self.total_tvl_at_risk >= Decimal("100_000_000")

    @property
    def affected_count(self) -> int:
        """Number of affected protocols."""
        return len(self.affected_protocols)

    def get_timeline_summary(self) -> List[Tuple[str, str, float]]:
        """Get simplified timeline summary.

        Returns:
            List of (time_str, protocol, severity) tuples
        """
        return [
            (
                str(event.time_offset),
                event.protocol,
                event.impact_severity,
            )
            for event in self.propagation_timeline
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trigger_protocol": self.trigger_protocol,
            "failure_type": self.failure_type.value,
            "affected_protocols": self.affected_protocols,
            "total_tvl_at_risk": str(self.total_tvl_at_risk),
            "propagation_timeline": [e.to_dict() for e in self.propagation_timeline],
            "critical_bottlenecks": self.critical_bottlenecks,
            "cascade_depth": self.cascade_depth,
            "simulation_time_seconds": int(self.simulation_time.total_seconds()),
            "is_systemic": self.is_systemic,
            "is_high_impact": self.is_high_impact,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CascadeResult":
        """Create CascadeResult from dictionary."""
        failure_type = data.get("failure_type", "exploit")
        if isinstance(failure_type, str):
            failure_type = FailureType(failure_type)

        return cls(
            trigger_protocol=str(data.get("trigger_protocol", "")),
            failure_type=failure_type,
            affected_protocols=list(data.get("affected_protocols", [])),
            total_tvl_at_risk=Decimal(str(data.get("total_tvl_at_risk", "0"))),
            cascade_depth=int(data.get("cascade_depth", 0)),
            critical_bottlenecks=list(data.get("critical_bottlenecks", [])),
        )


class CascadeSimulator:
    """Cascade failure simulator for protocol dependency graph.

    Per 05.11-10: Simulates how failures propagate through the DeFi
    ecosystem via protocol dependencies.

    Propagation rules:
    - ORACLE failure: Affects dependents within oracle staleness window
    - LIQUIDITY crisis: Affects dependents with > 30% liquidity from source
    - EXPLOIT: Affects collateral dependents immediately
    - Propagation stops when criticality < threshold

    Usage:
        simulator = CascadeSimulator(graph)
        result = simulator.simulate_failure(
            trigger_protocol="chainlink",
            failure_type=FailureType.ORACLE_MANIPULATION,
        )
    """

    # Thresholds for propagation
    DEFAULT_CRITICALITY_THRESHOLD = 5.0
    LIQUIDITY_DEPENDENCY_THRESHOLD = 0.3  # 30%

    # Propagation time estimates by dependency type
    PROPAGATION_TIMES = {
        "oracle": timedelta(minutes=30),  # Oracle staleness typically 30m-1h
        "liquidity": timedelta(hours=2),  # Liquidity cascades slower
        "collateral": timedelta(minutes=15),  # Collateral liquidations fast
        "governance": timedelta(days=1),  # Governance attacks slow
        "bridge": timedelta(hours=1),  # Bridge failures moderate
    }

    # Impact severity by failure type and dependency
    IMPACT_MATRIX: Dict[str, Dict[str, float]] = {
        "oracle_manipulation": {
            "oracle": 0.9,  # High impact on oracle dependents
            "liquidity": 0.3,
            "collateral": 0.7,
            "governance": 0.1,
            "bridge": 0.2,
        },
        "exploit": {
            "oracle": 0.2,
            "liquidity": 0.6,
            "collateral": 0.9,  # High impact on collateral dependents
            "governance": 0.3,
            "bridge": 0.4,
        },
        "governance_attack": {
            "oracle": 0.3,
            "liquidity": 0.4,
            "collateral": 0.5,
            "governance": 0.8,  # High impact on governance dependents
            "bridge": 0.3,
        },
        "liquidity_crisis": {
            "oracle": 0.2,
            "liquidity": 0.9,  # High impact on liquidity dependents
            "collateral": 0.7,
            "governance": 0.2,
            "bridge": 0.5,
        },
        "bridge_hack": {
            "oracle": 0.3,
            "liquidity": 0.6,
            "collateral": 0.7,
            "governance": 0.2,
            "bridge": 0.9,  # High impact on bridge dependents
        },
        "depeg": {
            "oracle": 0.4,
            "liquidity": 0.7,
            "collateral": 0.9,  # High impact on collateral
            "governance": 0.2,
            "bridge": 0.5,
        },
        "insolvency": {
            "oracle": 0.3,
            "liquidity": 0.8,
            "collateral": 0.9,
            "governance": 0.4,
            "bridge": 0.6,
        },
    }

    def __init__(
        self,
        graph: "ProtocolDependencyGraph",
        criticality_threshold: float = DEFAULT_CRITICALITY_THRESHOLD,
    ) -> None:
        """Initialize cascade simulator.

        Args:
            graph: Protocol dependency graph
            criticality_threshold: Minimum criticality to propagate (default 5.0)
        """
        self._graph = graph
        self._criticality_threshold = criticality_threshold

    def simulate_failure(
        self,
        trigger_protocol: str,
        failure_type: FailureType,
        market_conditions: Optional[MarketConditions] = None,
        max_depth: int = 10,
    ) -> CascadeResult:
        """Simulate a cascade failure from a trigger protocol.

        Per 05.11-10: Model failure propagation through dependency edges,
        tracking affected protocols, timeline, and TVL at risk.

        Args:
            trigger_protocol: Protocol ID that triggers the cascade
            failure_type: Type of failure
            market_conditions: Market conditions (optional)
            max_depth: Maximum propagation depth

        Returns:
            CascadeResult with full cascade analysis
        """
        trigger = trigger_protocol.lower()
        conditions = market_conditions or MarketConditions()

        # Track state
        affected: List[str] = []
        visited: Set[str] = {trigger}
        timeline: List[PropagationEvent] = []
        total_tvl = Decimal("0")
        bottleneck_counts: Dict[str, int] = {}

        # BFS for cascade propagation
        current_depth = 0
        current_level = [(trigger, timedelta(0), 1.0)]  # (protocol, time, severity)

        while current_level and current_depth < max_depth:
            next_level: List[Tuple[str, timedelta, float]] = []

            for source_protocol, base_time, source_severity in current_level:
                # Get dependents (protocols that depend on this one)
                dependents = self._graph.get_dependents(source_protocol)

                for edge in dependents:
                    target = edge.source  # The dependent protocol
                    if target in visited:
                        continue

                    # Check criticality threshold
                    if edge.criticality < self._criticality_threshold:
                        continue

                    # Calculate impact severity
                    impact = self._calculate_impact(
                        failure_type=failure_type,
                        dependency_type=edge.dependency_type.value,
                        edge_criticality=edge.criticality,
                        source_severity=source_severity,
                        market_conditions=conditions,
                    )

                    # Skip if impact too low
                    if impact < 0.1:
                        continue

                    # Calculate propagation time
                    prop_time = self._calculate_propagation_time(
                        edge.dependency_type.value,
                        conditions,
                    )
                    event_time = base_time + prop_time

                    # Add to affected
                    affected.append(target)
                    visited.add(target)

                    # Add timeline event
                    timeline.append(PropagationEvent(
                        protocol=target,
                        time_offset=event_time,
                        impact_severity=impact,
                        propagation_source=source_protocol,
                        dependency_type=edge.dependency_type.value,
                    ))

                    # Track TVL at risk
                    target_node = self._graph.get_protocol(target)
                    if target_node:
                        total_tvl += target_node.tvl * Decimal(str(impact))

                    # Track bottleneck propagation counts
                    bottleneck_counts[source_protocol] = bottleneck_counts.get(source_protocol, 0) + 1

                    # Queue for next level
                    next_level.append((target, event_time, impact))

            current_level = next_level
            current_depth += 1

        # Sort timeline by time
        timeline.sort(key=lambda e: e.time_offset)

        # Identify bottlenecks (protocols that propagate to 3+ others)
        bottlenecks = [p for p, count in bottleneck_counts.items() if count >= 3]

        # Calculate simulation time (latest event + buffer)
        sim_time = timeline[-1].time_offset if timeline else timedelta(hours=24)
        sim_time += timedelta(hours=1)

        return CascadeResult(
            trigger_protocol=trigger,
            failure_type=failure_type,
            affected_protocols=affected,
            total_tvl_at_risk=total_tvl,
            propagation_timeline=timeline,
            critical_bottlenecks=bottlenecks,
            cascade_depth=current_depth,
            simulation_time=sim_time,
        )

    def simulate_scenario(self, scenario: CascadeScenario) -> CascadeResult:
        """Simulate a predefined cascade scenario.

        Args:
            scenario: CascadeScenario to simulate

        Returns:
            CascadeResult with full cascade analysis
        """
        return self.simulate_failure(
            trigger_protocol=scenario.trigger,
            failure_type=scenario.failure_type,
            market_conditions=scenario.market_conditions,
        )

    def _calculate_impact(
        self,
        failure_type: FailureType,
        dependency_type: str,
        edge_criticality: float,
        source_severity: float,
        market_conditions: MarketConditions,
    ) -> float:
        """Calculate impact severity for a propagation.

        Args:
            failure_type: Type of failure
            dependency_type: Type of dependency edge
            edge_criticality: Criticality of the edge (1-10)
            source_severity: Severity at the source protocol
            market_conditions: Market conditions

        Returns:
            Impact severity (0-1)
        """
        # Get base impact from matrix
        failure_impacts = self.IMPACT_MATRIX.get(failure_type.value, {})
        base_impact = failure_impacts.get(dependency_type, 0.3)

        # Scale by edge criticality (normalized 0-1)
        criticality_factor = edge_criticality / 10.0

        # Scale by source severity (decay as cascade propagates)
        decay_factor = source_severity * 0.8

        # Market conditions amplify impact
        market_factor = 1.0 + (market_conditions.market_volatility * 0.3)

        impact = base_impact * criticality_factor * decay_factor * market_factor
        return min(1.0, max(0.0, impact))

    def _calculate_propagation_time(
        self,
        dependency_type: str,
        market_conditions: MarketConditions,
    ) -> timedelta:
        """Calculate propagation time for a dependency type.

        Args:
            dependency_type: Type of dependency
            market_conditions: Market conditions

        Returns:
            Propagation time as timedelta
        """
        base_time = self.PROPAGATION_TIMES.get(dependency_type, timedelta(hours=1))

        # Stressed markets = faster propagation
        multiplier = 1.0 / market_conditions.cascade_multiplier

        return timedelta(seconds=base_time.total_seconds() * multiplier)

    def estimate_worst_case(self, protocol_id: str) -> CascadeResult:
        """Estimate worst-case cascade for a protocol.

        Tries all failure types and returns the worst outcome.

        Args:
            protocol_id: Protocol to analyze

        Returns:
            CascadeResult for worst-case scenario
        """
        worst_result: Optional[CascadeResult] = None
        worst_tvl = Decimal("0")

        # Try all failure types with stressed market conditions
        stressed = MarketConditions.stressed()

        for failure_type in FailureType:
            result = self.simulate_failure(
                trigger_protocol=protocol_id,
                failure_type=failure_type,
                market_conditions=stressed,
            )

            if result.total_tvl_at_risk > worst_tvl:
                worst_tvl = result.total_tvl_at_risk
                worst_result = result

        # Return worst case or empty result
        return worst_result or CascadeResult(
            trigger_protocol=protocol_id,
            failure_type=FailureType.EXPLOIT,
        )


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "FailureType",
    "MarketConditions",
    "CascadeScenario",
    "PropagationEvent",
    "CascadeResult",
    "CascadeSimulator",
]
