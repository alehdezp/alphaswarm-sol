"""Adversarial Simulation orchestration for Red vs Blue combat.

Per 05.11-08-PLAN.md: Orchestrates Red Team attacks, Blue Team defenses,
and Judge evaluation in a continuous improvement loop.

Key Features:
- Multi-round combat simulation
- Improvement loop: update strategies based on outcomes
- Novel vulnerability discovery tracking
- Strategy adaptation metrics

Research Basis:
- Target: 20% increase in novel vulnerability discovery (per Microsoft research)
- Attack synthesis accuracy: 80% viable PoCs

Usage:
    from alphaswarm_sol.agents.adversarial.simulation import (
        AdversarialSimulation,
        SimulationResult,
        SimulationConfig,
    )

    simulation = AdversarialSimulation()
    result = simulation.run_round(finding)

    print(f"Final verdict: {result.final_verdict.winner}")
    print(f"Novel vulnerabilities: {len(result.novel_vulnerabilities)}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .red_agent import RedAgent, AttackPlan, MCTSConfig
from .blue_agent import BlueAgent, DefensePlan, PatchRecommendation
from .judge_agent import JudgeAgent, Verdict, VerdictWinner, NovelFinding

logger = logging.getLogger(__name__)


# =============================================================================
# Simulation Configuration
# =============================================================================


@dataclass
class SimulationConfig:
    """Configuration for adversarial simulation.

    Attributes:
        max_rounds: Maximum rounds per finding
        min_rounds: Minimum rounds before early stop
        convergence_threshold: Win rate stability for early stop
        mcts_iterations: MCTS iterations for Red Agent
        mcts_depth: Max depth for MCTS exploration
        use_llm: Enable LLM for agents
        track_improvement: Enable improvement loop metrics
    """

    max_rounds: int = 3
    min_rounds: int = 1
    convergence_threshold: float = 0.1  # 10% stability
    mcts_iterations: int = 100
    mcts_depth: int = 10
    use_llm: bool = False
    track_improvement: bool = True


@dataclass
class ImprovementMetrics:
    """Metrics for improvement loop tracking.

    Attributes:
        red_win_rate: Red Team win rate over time
        blue_win_rate: Blue Team win rate over time
        novel_discovery_rate: Novel findings per round
        attack_viability_rate: Percentage of viable attacks
        defense_effectiveness_avg: Average defense effectiveness
        strategy_adaptations: Count of strategy adaptations
    """

    red_win_rate: float = 0.0
    blue_win_rate: float = 0.0
    novel_discovery_rate: float = 0.0
    attack_viability_rate: float = 0.0
    defense_effectiveness_avg: float = 0.0
    strategy_adaptations: int = 0
    round_history: List[Dict[str, Any]] = field(default_factory=list)

    def update(
        self,
        red_wins: int,
        blue_wins: int,
        total_rounds: int,
        novel_findings: int,
        viable_attacks: int,
        total_attacks: int,
        effectiveness_sum: float,
    ) -> None:
        """Update metrics from latest data."""
        if total_rounds > 0:
            self.red_win_rate = red_wins / total_rounds
            self.blue_win_rate = blue_wins / total_rounds
            self.novel_discovery_rate = novel_findings / total_rounds

        if total_attacks > 0:
            self.attack_viability_rate = viable_attacks / total_attacks
            self.defense_effectiveness_avg = effectiveness_sum / total_attacks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "red_win_rate": self.red_win_rate,
            "blue_win_rate": self.blue_win_rate,
            "novel_discovery_rate": self.novel_discovery_rate,
            "attack_viability_rate": self.attack_viability_rate,
            "defense_effectiveness_avg": self.defense_effectiveness_avg,
            "strategy_adaptations": self.strategy_adaptations,
            "round_history": self.round_history,
        }


# =============================================================================
# Round and Simulation Results
# =============================================================================


@dataclass
class RoundResult:
    """Result from a single combat round.

    Attributes:
        round_number: Round index (1-based)
        attack_plan: Red Team's attack
        defense_plan: Blue Team's defense
        verdict: Judge's verdict
        novel_findings: New vulnerabilities found this round
    """

    round_number: int
    attack_plan: AttackPlan
    defense_plan: DefensePlan
    verdict: Verdict
    novel_findings: List[NovelFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "round_number": self.round_number,
            "attack_plan": self.attack_plan.to_dict(),
            "defense_plan": self.defense_plan.to_dict(),
            "verdict": self.verdict.to_dict(),
            "novel_findings": [f.to_dict() for f in self.novel_findings],
        }


@dataclass
class SimulationResult:
    """Complete result from adversarial simulation.

    Per 05.11-08: Contains all rounds, final verdict, and improvement metrics.

    Attributes:
        finding_id: ID of finding being investigated
        rounds: All round results
        final_verdict: Judge's final verdict
        attack_success_rate: Red Team success rate
        defense_effectiveness: Blue Team effectiveness
        novel_vulnerabilities: All novel findings discovered
        suggested_patches: Best patches from Blue Team
        improvement_metrics: Improvement loop metrics
        metadata: Additional metadata
    """

    finding_id: str
    rounds: List[RoundResult] = field(default_factory=list)
    final_verdict: Optional[Verdict] = None
    attack_success_rate: float = 0.0
    defense_effectiveness: float = 0.0
    novel_vulnerabilities: List[NovelFinding] = field(default_factory=list)
    suggested_patches: List[PatchRecommendation] = field(default_factory=list)
    improvement_metrics: Optional[ImprovementMetrics] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate aggregated metrics from rounds."""
        if self.rounds:
            self._calculate_metrics()

    def _calculate_metrics(self) -> None:
        """Calculate metrics from round results."""
        if not self.rounds:
            return

        # Attack success rate
        red_wins = sum(
            1 for r in self.rounds
            if r.verdict.winner == VerdictWinner.RED
        )
        self.attack_success_rate = red_wins / len(self.rounds)

        # Defense effectiveness
        self.defense_effectiveness = sum(
            r.defense_plan.effectiveness
            for r in self.rounds
        ) / len(self.rounds)

        # Final verdict is from last round
        self.final_verdict = self.rounds[-1].verdict

        # Collect all novel findings
        seen_ids = set()
        for r in self.rounds:
            for f in r.novel_findings:
                if f.id not in seen_ids:
                    self.novel_vulnerabilities.append(f)
                    seen_ids.add(f.id)

        # Collect best patches (highest effectiveness)
        all_patches = []
        for r in self.rounds:
            all_patches.extend(r.defense_plan.patches)

        # Sort by effectiveness proxy (inverse complexity + gas impact)
        def patch_score(p: PatchRecommendation) -> float:
            complexity_scores = {
                "trivial": 4,
                "simple": 3,
                "moderate": 2,
                "complex": 1,
                "architectural": 0,
            }
            comp = p.complexity.value if hasattr(p.complexity, "value") else str(p.complexity)
            return complexity_scores.get(comp, 2) - (p.gas_impact / 10000)

        all_patches.sort(key=patch_score, reverse=True)
        self.suggested_patches = all_patches[:5]  # Top 5 patches

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "finding_id": self.finding_id,
            "rounds": [r.to_dict() for r in self.rounds],
            "final_verdict": self.final_verdict.to_dict() if self.final_verdict else None,
            "attack_success_rate": self.attack_success_rate,
            "defense_effectiveness": self.defense_effectiveness,
            "novel_vulnerabilities": [f.to_dict() for f in self.novel_vulnerabilities],
            "suggested_patches": [p.to_dict() for p in self.suggested_patches],
            "improvement_metrics": (
                self.improvement_metrics.to_dict()
                if self.improvement_metrics
                else None
            ),
            "metadata": self.metadata,
        }


# =============================================================================
# Adversarial Simulation
# =============================================================================


class AdversarialSimulation:
    """Orchestrator for Red vs Blue adversarial combat.

    Per 05.11-08: Runs multi-round simulation with improvement loop.

    Key Features:
    - Orchestrates Red -> Blue -> Judge pipeline
    - Tracks improvement metrics over rounds
    - Adapts strategies based on outcomes
    - Discovers novel vulnerabilities through combat

    Usage:
        simulation = AdversarialSimulation()
        result = simulation.run_round(finding)

        # Multi-finding simulation
        simulation.run_full_simulation(findings)
    """

    def __init__(
        self,
        config: Optional[SimulationConfig] = None,
        red_agent: Optional[RedAgent] = None,
        blue_agent: Optional[BlueAgent] = None,
        judge_agent: Optional[JudgeAgent] = None,
    ):
        """Initialize adversarial simulation.

        Args:
            config: Simulation configuration
            red_agent: Optional pre-configured Red Agent
            blue_agent: Optional pre-configured Blue Agent
            judge_agent: Optional pre-configured Judge Agent
        """
        self.config = config or SimulationConfig()

        # Initialize agents
        self.red_agent = red_agent or RedAgent(use_llm=self.config.use_llm)
        self.blue_agent = blue_agent or BlueAgent(use_llm=self.config.use_llm)
        self.judge_agent = judge_agent or JudgeAgent(use_llm=self.config.use_llm)

        # Tracking state
        self._simulation_history: List[SimulationResult] = []
        self._global_metrics = ImprovementMetrics()
        self._mitigation_db: Dict[str, Any] = {}
        self._successful_attacks: List[AttackPlan] = []
        self._effective_defenses: List[DefensePlan] = []

    def run_round(
        self,
        finding: Dict[str, Any],
        protocol_state: Optional[Dict[str, Any]] = None,
        ground_truth: Optional[Dict[str, Any]] = None,
    ) -> SimulationResult:
        """Run adversarial simulation for a finding.

        Per 05.11-08: Orchestrate Red attacks -> Blue defends -> Judge evaluates.

        Args:
            finding: Vulnerability finding to investigate
            protocol_state: Protocol state (TVL, gas, etc.)
            ground_truth: Known ground truth for validation

        Returns:
            SimulationResult with all rounds and metrics
        """
        finding_id = finding.get("id", "unknown")
        protocol_state = protocol_state or {}
        ground_truth = ground_truth or {}

        logger.info(f"AdversarialSimulation: Starting simulation for {finding_id}")

        rounds: List[RoundResult] = []
        all_novel_findings: List[NovelFinding] = []

        # Run rounds
        for round_num in range(1, self.config.max_rounds + 1):
            logger.info(f"AdversarialSimulation: Round {round_num}/{self.config.max_rounds}")

            # Phase 1: Red Team synthesizes attack
            mcts_config = MCTSConfig(
                max_iterations=self.config.mcts_iterations,
                max_depth=self.config.mcts_depth,
                use_llm=self.config.use_llm,
            )

            # Adapt strategy based on previous outcomes
            adapted_finding = self._adapt_red_strategy(finding, rounds)
            attack_plan = self.red_agent.synthesize_attack(
                finding=adapted_finding,
                protocol_state=protocol_state,
                budget=mcts_config,
            )

            # Phase 2: Blue Team generates defense
            defense_plan = self.blue_agent.generate_defense(
                attack_plan=attack_plan,
                mitigation_db=self._mitigation_db,
            )

            # Phase 3: Judge evaluates
            verdict = self.judge_agent.evaluate(
                attack_plan=attack_plan,
                defense_plan=defense_plan,
                ground_truth=ground_truth,
            )

            # Collect novel findings
            novel_findings = verdict.novel_findings.copy()
            all_novel_findings.extend(novel_findings)

            # Store round result
            round_result = RoundResult(
                round_number=round_num,
                attack_plan=attack_plan,
                defense_plan=defense_plan,
                verdict=verdict,
                novel_findings=novel_findings,
            )
            rounds.append(round_result)

            # Update mitigation database with effective defenses
            self._update_mitigation_db(defense_plan, verdict)

            # Track successful attacks for improvement
            if attack_plan.is_viable:
                self._successful_attacks.append(attack_plan)

            if defense_plan.effectiveness > 0.7:
                self._effective_defenses.append(defense_plan)

            # Check for early convergence
            if self._should_early_stop(rounds):
                logger.info(f"AdversarialSimulation: Early stop at round {round_num}")
                break

        # Calculate improvement metrics
        metrics = self._calculate_improvement_metrics(rounds)

        # Build result
        result = SimulationResult(
            finding_id=finding_id,
            rounds=rounds,
            improvement_metrics=metrics,
            metadata={
                "config": {
                    "max_rounds": self.config.max_rounds,
                    "mcts_iterations": self.config.mcts_iterations,
                },
                "protocol_state": protocol_state,
            },
        )

        self._simulation_history.append(result)

        logger.info(
            f"AdversarialSimulation: Completed {finding_id}, "
            f"attack_rate={result.attack_success_rate:.1%}, "
            f"defense_eff={result.defense_effectiveness:.1%}, "
            f"novel_findings={len(result.novel_vulnerabilities)}"
        )

        return result

    def run_full_simulation(
        self,
        findings: List[Dict[str, Any]],
        protocol_state: Optional[Dict[str, Any]] = None,
    ) -> List[SimulationResult]:
        """Run simulation across multiple findings.

        Args:
            findings: List of vulnerability findings
            protocol_state: Protocol state

        Returns:
            List of simulation results
        """
        results = []
        for finding in findings:
            result = self.run_round(finding, protocol_state)
            results.append(result)
        return results

    def _adapt_red_strategy(
        self,
        finding: Dict[str, Any],
        previous_rounds: List[RoundResult],
    ) -> Dict[str, Any]:
        """Adapt Red Team strategy based on previous outcomes.

        Args:
            finding: Original finding
            previous_rounds: Previous round results

        Returns:
            Adapted finding with strategy hints
        """
        adapted = finding.copy()

        if not previous_rounds:
            return adapted

        # Check if Red has been losing
        red_wins = sum(
            1 for r in previous_rounds
            if r.verdict.winner == VerdictWinner.RED
        )
        red_win_rate = red_wins / len(previous_rounds)

        if red_win_rate < 0.5:
            # Increase aggression
            adapted["strategy_hint"] = "aggressive"
            adapted["metadata"] = adapted.get("metadata", {})
            adapted["metadata"]["adaptation"] = "increased_aggression"
            self._global_metrics.strategy_adaptations += 1

            # Look for successful attacks to learn from
            if self._successful_attacks:
                adapted["reference_attacks"] = [
                    a.id for a in self._successful_attacks[-3:]
                ]
        else:
            # Maintain strategy
            adapted["strategy_hint"] = "maintain"

        return adapted

    def _update_mitigation_db(
        self,
        defense_plan: DefensePlan,
        verdict: Verdict,
    ) -> None:
        """Update mitigation database with effective defenses.

        Args:
            defense_plan: Defense plan from Blue Team
            verdict: Judge's verdict
        """
        # Only store if defense was effective
        if verdict.winner == VerdictWinner.BLUE:
            for mitigation in defense_plan.mitigations:
                key = mitigation.mitigation_type.value
                if key not in self._mitigation_db:
                    self._mitigation_db[key] = {
                        "count": 0,
                        "total_effectiveness": 0.0,
                        "examples": [],
                    }
                self._mitigation_db[key]["count"] += 1
                self._mitigation_db[key]["total_effectiveness"] += mitigation.effectiveness
                self._mitigation_db[key]["examples"].append(mitigation.id)

    def _should_early_stop(self, rounds: List[RoundResult]) -> bool:
        """Check if simulation should stop early.

        Args:
            rounds: Completed rounds

        Returns:
            True if should stop early
        """
        if len(rounds) < self.config.min_rounds:
            return False

        # Check for convergence
        if len(rounds) >= 2:
            recent_winners = [r.verdict.winner for r in rounds[-2:]]
            if all(w == recent_winners[0] for w in recent_winners):
                # Same winner in last 2 rounds
                return True

        return False

    def _calculate_improvement_metrics(
        self,
        rounds: List[RoundResult],
    ) -> ImprovementMetrics:
        """Calculate improvement metrics from rounds.

        Args:
            rounds: All completed rounds

        Returns:
            ImprovementMetrics
        """
        metrics = ImprovementMetrics()

        if not rounds:
            return metrics

        red_wins = sum(
            1 for r in rounds
            if r.verdict.winner == VerdictWinner.RED
        )
        blue_wins = sum(
            1 for r in rounds
            if r.verdict.winner == VerdictWinner.BLUE
        )
        novel_findings = sum(len(r.novel_findings) for r in rounds)
        viable_attacks = sum(
            1 for r in rounds
            if r.attack_plan.is_viable
        )
        effectiveness_sum = sum(r.defense_plan.effectiveness for r in rounds)

        metrics.update(
            red_wins=red_wins,
            blue_wins=blue_wins,
            total_rounds=len(rounds),
            novel_findings=novel_findings,
            viable_attacks=viable_attacks,
            total_attacks=len(rounds),
            effectiveness_sum=effectiveness_sum,
        )

        # Track round history
        metrics.round_history = [
            {
                "round": r.round_number,
                "winner": r.verdict.winner.value,
                "red_score": r.verdict.red_score,
                "blue_score": r.verdict.blue_score,
                "novel_findings": len(r.novel_findings),
            }
            for r in rounds
        ]

        return metrics

    def get_global_metrics(self) -> ImprovementMetrics:
        """Get global improvement metrics across all simulations."""
        return self._global_metrics

    def get_simulation_history(self) -> List[SimulationResult]:
        """Get all simulation results."""
        return self._simulation_history

    def get_novel_discoveries(self) -> List[NovelFinding]:
        """Get all novel discoveries across simulations."""
        findings = []
        seen_ids = set()
        for result in self._simulation_history:
            for finding in result.novel_vulnerabilities:
                if finding.id not in seen_ids:
                    findings.append(finding)
                    seen_ids.add(finding.id)
        return findings

    def get_best_patches(self) -> List[PatchRecommendation]:
        """Get best patches across all simulations."""
        all_patches = []
        for result in self._simulation_history:
            all_patches.extend(result.suggested_patches)

        # Deduplicate by ID
        seen_ids = set()
        unique_patches = []
        for patch in all_patches:
            if patch.id not in seen_ids:
                unique_patches.append(patch)
                seen_ids.add(patch.id)

        return unique_patches[:10]  # Top 10

    def reset(self) -> None:
        """Reset simulation state for new run."""
        self._simulation_history.clear()
        self._global_metrics = ImprovementMetrics()
        self._mitigation_db.clear()
        self._successful_attacks.clear()
        self._effective_defenses.clear()
        self.red_agent.clear_attack_history()
        self.blue_agent.clear_defense_history()
        self.judge_agent.clear_history()


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "AdversarialSimulation",
    "SimulationResult",
    "RoundResult",
    "SimulationConfig",
    "ImprovementMetrics",
]
