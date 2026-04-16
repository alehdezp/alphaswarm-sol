"""Cross-Protocol Composability Risk Model (CPCRM).

Per 05.11-10: Model DeFi as a connected system where protocol failures cascade,
identifying systemic risks that single-protocol analysis misses.

Key Features:
- Protocol dependency graph: Models DeFi ecosystem interactions
- Cascade failure simulation: Estimates TVL at risk from protocol failures
- Systemic risk scoring: Reflects protocol centrality and cascade potential
- Multi-protocol attack paths: Discovered through graph traversal

Components:
- ProtocolDependencyGraph: DeFi protocol dependency graph with centrality analysis
- CascadeSimulator: Cascade failure simulation engine
- SystemicScorer: Systemic risk scorer with GATE integration

Usage:
    from alphaswarm_sol.economics.composability import (
        ProtocolNode,
        ProtocolCategory,
        DependencyEdge,
        DependencyType,
        ProtocolDependencyGraph,
        CascadeSimulator,
        CascadeScenario,
        CascadeResult,
        FailureType,
        SystemicScorer,
        SystemicRiskAssessment,
    )

    # Build protocol dependency graph
    graph = ProtocolDependencyGraph()
    graph.add_protocol(ProtocolNode(
        protocol_id="aave-v3",
        tvl=Decimal("10_000_000_000"),
        category=ProtocolCategory.LENDING,
        chains=["ethereum", "arbitrum"],
    ))

    # Simulate cascade failure
    simulator = CascadeSimulator(graph)
    result = simulator.simulate_failure(
        trigger_protocol="chainlink",
        failure_type=FailureType.ORACLE_MANIPULATION,
    )
    print(f"TVL at risk: ${result.total_tvl_at_risk:,.0f}")

    # Compute systemic risk
    scorer = SystemicScorer(graph)
    assessment = scorer.compute_systemic_score("aave-v3")
    print(f"Systemic risk: {assessment.score}/10")
"""

from .protocol_graph import (
    ProtocolCategory,
    GovernanceType,
    GovernanceInfo,
    ProtocolNode,
    DependencyType,
    DependencyEdge,
    CriticalPath,
    Cycle,
    ProtocolDependencyGraph,
)

from .cascade_simulator import (
    FailureType,
    MarketConditions,
    CascadeScenario,
    PropagationEvent,
    CascadeResult,
    CascadeSimulator,
)

from .systemic_scorer import (
    SystemicRiskAssessment,
    CrossProtocolAttackPath,
    SystemicScorer,
)

__all__ = [
    # Protocol graph types
    "ProtocolCategory",
    "GovernanceType",
    "GovernanceInfo",
    "ProtocolNode",
    "DependencyType",
    "DependencyEdge",
    "CriticalPath",
    "Cycle",
    "ProtocolDependencyGraph",
    # Cascade simulator types
    "FailureType",
    "MarketConditions",
    "CascadeScenario",
    "PropagationEvent",
    "CascadeResult",
    "CascadeSimulator",
    # Systemic scorer types
    "SystemicRiskAssessment",
    "CrossProtocolAttackPath",
    "SystemicScorer",
]
