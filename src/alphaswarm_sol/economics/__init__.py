"""Economics module for game-theoretic attack modeling and risk scoring.

The economics module provides payoff field definitions, game-theoretic
modeling tools, causal loss amplification analysis, and systemic risk
scoring for vulnerability analysis.

Per 05.11-CONTEXT.md:
- Game-theoretic payoff fields (05.11-01)
- Economic rationality gate (05.11-03)
- Economic risk scoring with three components (05.11-04)
- Causal loss amplification from exploitation chains (05.11-04)
- Cross-protocol systemic risk scoring (05.11-04)
- Game-Theoretic Attack Synthesis Engine (GATE) (05.11-06)

Core Types:
- AttackPayoff: Expected profit, costs, and success probability for attackers
- DefensePayoff: Detection probability, mitigation cost, and timelock delays
- PayoffMatrix: 3-player game model (Attacker, Protocol, MEV Searchers)
- RationalityGate: Economic rationality filtering (05.11-03)
- EconomicRiskScorer: Comprehensive risk scoring with three components (05.11-04)
- CausalAnalyzer: Loss amplification from causal chains (05.11-04)
- SystemicRiskScorer: Cross-protocol systemic risk (05.11-04)
- AttackSynthesisEngine: 3-player game synthesis for vulnerabilities (05.11-06)
- NashEquilibriumSolver: Nash equilibrium computation (05.11-06)
- IncentiveAnalyzer: Incentive alignment analysis (05.11-06)

Usage:
    from alphaswarm_sol.economics import (
        AttackPayoff,
        DefensePayoff,
        PayoffMatrix,
        RationalityGate,
        EconomicRiskScorer,
        compute_economic_risk,
        CausalAnalyzer,
        SystemicRiskScorer,
    )

    # Game-theoretic payoff analysis
    attack = AttackPayoff(
        expected_profit_usd=100000,
        gas_cost_usd=500,
        mev_risk=0.3,
        success_probability=0.7
    )

    matrix = PayoffMatrix(
        scenario="oracle_manipulation",
        attacker_payoff=attack,
        defender_payoff=DefensePayoff()
    )

    print(f"Expected value: ${matrix.attacker_expected_value:,.2f}")

    # Rationality filtering (05.11-03)
    gate = RationalityGate()
    result = gate.evaluate_attack_ev(vulnerability, protocol_state)

    # Economic risk scoring (05.11-04)
    breakdown = compute_economic_risk(
        value_at_risk_usd=1_000_000,
        privilege_concentration=0.7,
        payoff_matrix=matrix,
    )

    print(f"Risk: {breakdown.total_score:.1f}/10")
    print(f"Priority: {breakdown.priority.value}")
"""

from .payoff import (
    AttackPayoff,
    DefensePayoff,
    PayoffMatrix,
    PayoffOutcome,
    PayoffPlayer,
)

from .rationality_gate import (
    EVThreshold,
    DEFAULT_EV_THRESHOLD,
    EVResult,
    RationalityGate,
    filter_by_economic_rationality,
    get_priority_sorted_vulnerabilities,
)

from .risk import (
    RiskPriority,
    RiskBreakdown,
    EconomicRiskScorer,
    compute_economic_risk,
)

from .causal_analysis import (
    AmplificationType,
    AmplificationSource,
    LossAmplificationFactor,
    LossPath,
    CausalAnalyzer,
    compute_loss_amplification,
)

from .systemic_risk import (
    DependencyRole,
    DependencyCentrality,
    CascadeRisk,
    SystemicRiskScore,
    SystemicRiskScorer,
)

# GATE: Game-Theoretic Attack Synthesis Engine (05.11-06)
from .gate import (
    AttackStrategy,
    ProtocolDefense,
    MEVStrategy,
    AttackPayoffMatrix,
    AttackSynthesisEngine,
    compute_attack_ev,
    NashResult,
    BlockingCondition,
    BlockingConditionType,
    NashEquilibriumSolver,
    IncentiveMisalignment,
    IncentiveReport,
    IncentiveAnalyzer,
)

__all__ = [
    # Payoff types
    "AttackPayoff",
    "DefensePayoff",
    "PayoffMatrix",
    "PayoffOutcome",
    "PayoffPlayer",
    # Rationality gate (05.11-03)
    "EVThreshold",
    "DEFAULT_EV_THRESHOLD",
    "EVResult",
    "RationalityGate",
    "filter_by_economic_rationality",
    "get_priority_sorted_vulnerabilities",
    # Risk module (05.11-04)
    "RiskPriority",
    "RiskBreakdown",
    "EconomicRiskScorer",
    "compute_economic_risk",
    # Causal analysis module (05.11-04)
    "AmplificationType",
    "AmplificationSource",
    "LossAmplificationFactor",
    "LossPath",
    "CausalAnalyzer",
    "compute_loss_amplification",
    # Systemic risk module (05.11-04)
    "DependencyRole",
    "DependencyCentrality",
    "CascadeRisk",
    "SystemicRiskScore",
    "SystemicRiskScorer",
    # GATE module (05.11-06)
    "AttackStrategy",
    "ProtocolDefense",
    "MEVStrategy",
    "AttackPayoffMatrix",
    "AttackSynthesisEngine",
    "compute_attack_ev",
    "NashResult",
    "BlockingCondition",
    "BlockingConditionType",
    "NashEquilibriumSolver",
    "IncentiveMisalignment",
    "IncentiveReport",
    "IncentiveAnalyzer",
]
