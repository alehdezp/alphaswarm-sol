"""Game-Theoretic Attack Synthesis Engine (GATE) for vulnerability analysis.

Per 05.11-06: GATE differentiates AlphaSwarm by proving whether attacks are
worth exploiting given real economic constraints, reducing false positives
by filtering economically irrational vulnerabilities.

The GATE system models vulnerabilities as 3-player games:
- Attacker: Maximize profit (exploit vs honest behavior)
- Protocol: Minimize losses (guards, timelocks, monitoring)
- MEV Searchers: Frontrun/backrun the attack (compete for MEV)

Core Components:
- AttackSynthesisEngine: Computes 3-player payoff matrices
- NashEquilibriumSolver: Finds stable strategy profiles (Nash equilibria)
- IncentiveAnalyzer: Identifies blocking conditions and incentive misalignments

Usage:
    from alphaswarm_sol.economics.gate import (
        AttackSynthesisEngine,
        AttackPayoffMatrix,
        compute_attack_ev,
        NashEquilibriumSolver,
        NashResult,
        BlockingCondition,
        IncentiveAnalyzer,
        IncentiveReport,
    )

    # Synthesize attack payoff matrix
    engine = AttackSynthesisEngine()
    matrix = engine.compute_attack_ev(
        vulnerability=vuln_data,
        protocol_state={"tvl_usd": 10_000_000, "gas_price_gwei": 50},
    )

    # Solve for Nash equilibrium
    solver = NashEquilibriumSolver()
    result = solver.solve_nash_equilibrium(matrix)

    if result.is_attack_dominant:
        print(f"Attack is rational: EV = ${result.attacker_payoff:,.2f}")
    else:
        print(f"Attack blocked by: {result.blocking_conditions}")

    # Analyze incentive alignment
    analyzer = IncentiveAnalyzer()
    report = analyzer.analyze_incentives(protocol_state)
    if not report.is_honest_dominant:
        print(f"Misalignment: {report.misalignment_reasons}")
"""

from .attack_synthesis import (
    AttackStrategy,
    ProtocolDefense,
    MEVStrategy,
    AttackPayoffMatrix,
    AttackSynthesisEngine,
    compute_attack_ev,
)

from .nash_solver import (
    NashResult,
    BlockingCondition,
    BlockingConditionType,
    NashEquilibriumSolver,
)

from .incentive_analysis import (
    IncentiveMisalignment,
    IncentiveReport,
    IncentiveAnalyzer,
)

__all__ = [
    # Attack synthesis (05.11-06 Task 1)
    "AttackStrategy",
    "ProtocolDefense",
    "MEVStrategy",
    "AttackPayoffMatrix",
    "AttackSynthesisEngine",
    "compute_attack_ev",
    # Nash solver (05.11-06 Task 2)
    "NashResult",
    "BlockingCondition",
    "BlockingConditionType",
    "NashEquilibriumSolver",
    # Incentive analysis (05.11-06 Task 2)
    "IncentiveMisalignment",
    "IncentiveReport",
    "IncentiveAnalyzer",
]
