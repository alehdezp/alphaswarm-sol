"""Adversarial Red-Blue Agent Simulation for vulnerability discovery.

Per 05.11-08-PLAN.md: Implements adversarial combat where Red Team generates attacks,
Blue Team defends, and Judge Agent scores both sides in a continuous improvement loop.

Key Components:
- RedAgent: MCTS-style attack synthesis with economic pruning
- BlueAgent: Defense generation with cost analysis and patch recommendations
- JudgeAgent: Scoring and verdict determination with reasoning
- AdversarialSimulation: Orchestrates rounds and improvement loops

Research Basis:
- Microsoft research shows 47% improvement in vulnerability discovery via adversarial combat
- Target: 20% increase in novel vulnerability discovery over cooperative verification
- Attack synthesis accuracy target: 80% viable PoCs

Usage:
    from alphaswarm_sol.agents.adversarial import (
        RedAgent,
        BlueAgent,
        JudgeAgent,
        AdversarialSimulation,
        AttackPlan,
        DefensePlan,
        Verdict,
    )

    # Create simulation
    simulation = AdversarialSimulation()

    # Run adversarial round
    result = simulation.run_round(finding)

    print(f"Winner: {result.final_verdict.winner}")
    print(f"Novel vulnerabilities: {len(result.novel_vulnerabilities)}")
    print(f"Suggested patches: {len(result.suggested_patches)}")
"""

from .red_agent import (
    RedAgent,
    AttackPlan,
    ExploitPath,
    Transaction,
    ExplorationNode,
    MCTSConfig,
)

from .blue_agent import (
    BlueAgent,
    DefensePlan,
    PatchRecommendation,
    Mitigation,
    MitigationType,
)

from .judge_agent import (
    JudgeAgent,
    Verdict,
    Score,
    VerdictWinner,
    ScoreBreakdown,
)

from .simulation import (
    AdversarialSimulation,
    SimulationResult,
    RoundResult,
    SimulationConfig,
    ImprovementMetrics,
)

__all__ = [
    # Red Agent (05.11-08 Task 1)
    "RedAgent",
    "AttackPlan",
    "ExploitPath",
    "Transaction",
    "ExplorationNode",
    "MCTSConfig",
    # Blue Agent (05.11-08 Task 2)
    "BlueAgent",
    "DefensePlan",
    "PatchRecommendation",
    "Mitigation",
    "MitigationType",
    # Judge Agent (05.11-08 Task 2)
    "JudgeAgent",
    "Verdict",
    "Score",
    "VerdictWinner",
    "ScoreBreakdown",
    # Simulation (05.11-08 Task 3)
    "AdversarialSimulation",
    "SimulationResult",
    "RoundResult",
    "SimulationConfig",
    "ImprovementMetrics",
]
