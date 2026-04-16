"""Judge Agent for scoring and verdict determination.

Per 05.11-08-PLAN.md: Judge Agent evaluates Red and Blue team outputs,
scores both sides on multiple criteria, and determines verdicts with reasoning.

Key Features:
- Score attack: creativity, feasibility, economic viability
- Score defense: effectiveness, cost-efficiency, completeness
- Determine winner: did defense adequately counter attack?
- Identify novel findings that emerge from adversarial combat

Usage:
    from alphaswarm_sol.agents.adversarial.judge_agent import (
        JudgeAgent,
        Verdict,
        Score,
    )

    judge = JudgeAgent()
    verdict = judge.evaluate(
        attack_plan=red_output,
        defense_plan=blue_output,
        ground_truth=known_vuln_data,
    )

    print(f"Winner: {verdict.winner}")
    print(f"Red score: {verdict.red_score}")
    print(f"Blue score: {verdict.blue_score}")
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Verdict Types
# =============================================================================


class VerdictWinner(Enum):
    """Possible verdict outcomes."""

    RED = "red"  # Attack succeeds, defense inadequate
    BLUE = "blue"  # Defense blocks attack
    DRAW = "draw"  # Inconclusive or partial


class ScoreCategory(Enum):
    """Categories for scoring."""

    # Red team categories
    CREATIVITY = "creativity"  # Novel attack approach
    FEASIBILITY = "feasibility"  # Technical feasibility
    ECONOMIC_VIABILITY = "economic_viability"  # EV > 0
    EXPLOIT_COMPLETENESS = "exploit_completeness"  # Full PoC vs sketch
    EVIDENCE_QUALITY = "evidence_quality"  # Supporting evidence

    # Blue team categories
    EFFECTIVENESS = "effectiveness"  # Attack blocked?
    COST_EFFICIENCY = "cost_efficiency"  # Cost vs prevented loss
    COMPLETENESS = "completeness"  # All attack vectors addressed?
    SIDE_EFFECTS = "side_effects"  # Minimal collateral damage
    PRACTICALITY = "practicality"  # Easy to implement


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a score.

    Attributes:
        category: Score category
        score: Score value (0-100)
        weight: Weight in overall score
        reasoning: Explanation for this score
        evidence_refs: Supporting evidence
    """

    category: ScoreCategory
    score: float
    weight: float = 1.0
    reasoning: str = ""
    evidence_refs: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score contribution."""
        return self.score * self.weight


@dataclass
class Score:
    """Complete score for a team.

    Attributes:
        total: Overall score (0-100)
        breakdown: Detailed score breakdown by category
        strengths: Key strengths identified
        weaknesses: Key weaknesses identified
    """

    total: float = 0.0
    breakdown: List[ScoreBreakdown] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate total from breakdown if not set."""
        if self.breakdown and self.total == 0.0:
            total_weight = sum(b.weight for b in self.breakdown)
            if total_weight > 0:
                self.total = (
                    sum(b.weighted_score for b in self.breakdown) / total_weight
                )

    def add_breakdown(
        self,
        category: ScoreCategory,
        score: float,
        weight: float = 1.0,
        reasoning: str = "",
    ) -> None:
        """Add a score breakdown entry."""
        self.breakdown.append(
            ScoreBreakdown(
                category=category,
                score=score,
                weight=weight,
                reasoning=reasoning,
            )
        )
        # Recalculate total
        total_weight = sum(b.weight for b in self.breakdown)
        if total_weight > 0:
            self.total = sum(b.weighted_score for b in self.breakdown) / total_weight

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total": self.total,
            "breakdown": [
                {
                    "category": b.category.value,
                    "score": b.score,
                    "weight": b.weight,
                    "reasoning": b.reasoning,
                    "evidence_refs": b.evidence_refs,
                }
                for b in self.breakdown
            ],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


@dataclass
class NovelFinding:
    """A novel vulnerability discovered through adversarial combat.

    Attributes:
        id: Unique finding identifier
        description: Description of finding
        discovered_by: "red" or "blue" or "combined"
        severity: Estimated severity
        evidence_refs: Supporting evidence
        requires_verification: Needs further validation
    """

    id: str
    description: str
    discovered_by: str = "combined"
    severity: str = "medium"
    evidence_refs: List[str] = field(default_factory=list)
    requires_verification: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "discovered_by": self.discovered_by,
            "severity": self.severity,
            "evidence_refs": self.evidence_refs,
            "requires_verification": self.requires_verification,
        }


@dataclass
class Verdict:
    """Judge's verdict on Red vs Blue combat.

    Per 05.11-08: Includes scores, winner, novel findings, and reasoning.

    Attributes:
        id: Unique verdict identifier
        red_score: Red team score (0-100)
        blue_score: Blue team score (0-100)
        winner: "red", "blue", or "draw"
        novel_findings: New vulnerabilities discovered
        reasoning: Detailed reasoning for verdict
        red_breakdown: Detailed red score
        blue_breakdown: Detailed blue score
        metadata: Additional metadata
    """

    id: str
    red_score: float
    blue_score: float
    winner: VerdictWinner
    novel_findings: List[NovelFinding] = field(default_factory=list)
    reasoning: str = ""
    red_breakdown: Optional[Score] = None
    blue_breakdown: Optional[Score] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def margin(self) -> float:
        """Score margin between winner and loser."""
        return abs(self.red_score - self.blue_score)

    @property
    def is_decisive(self) -> bool:
        """Whether verdict is decisive (margin > 10)."""
        return self.margin > 10

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "red_score": self.red_score,
            "blue_score": self.blue_score,
            "winner": self.winner.value,
            "novel_findings": [f.to_dict() for f in self.novel_findings],
            "reasoning": self.reasoning,
            "red_breakdown": self.red_breakdown.to_dict() if self.red_breakdown else None,
            "blue_breakdown": self.blue_breakdown.to_dict() if self.blue_breakdown else None,
            "metadata": self.metadata,
        }


# =============================================================================
# Judge Agent
# =============================================================================


class JudgeAgent:
    """Judge Agent for evaluating Red vs Blue combat.

    Per 05.11-08: Scores both teams on multiple criteria and determines
    verdict with detailed reasoning.

    Scoring Criteria:
    - Red Team: creativity, feasibility, economic viability, completeness, evidence
    - Blue Team: effectiveness, cost-efficiency, completeness, side effects, practicality

    Usage:
        judge = JudgeAgent()
        verdict = judge.evaluate(attack_plan, defense_plan, ground_truth)
    """

    # Weight configurations
    RED_WEIGHTS = {
        ScoreCategory.CREATIVITY: 0.15,
        ScoreCategory.FEASIBILITY: 0.25,
        ScoreCategory.ECONOMIC_VIABILITY: 0.25,
        ScoreCategory.EXPLOIT_COMPLETENESS: 0.20,
        ScoreCategory.EVIDENCE_QUALITY: 0.15,
    }

    BLUE_WEIGHTS = {
        ScoreCategory.EFFECTIVENESS: 0.30,
        ScoreCategory.COST_EFFICIENCY: 0.20,
        ScoreCategory.COMPLETENESS: 0.20,
        ScoreCategory.SIDE_EFFECTS: 0.15,
        ScoreCategory.PRACTICALITY: 0.15,
    }

    def __init__(
        self,
        strict_evidence: bool = True,
        use_llm: bool = False,
    ):
        """Initialize Judge Agent.

        Args:
            strict_evidence: Require evidence for high scores
            use_llm: Enable LLM for reasoning generation
        """
        self.strict_evidence = strict_evidence
        self.use_llm = use_llm
        self._verdict_history: List[Verdict] = []

    def evaluate(
        self,
        attack_plan: Any,
        defense_plan: Any,
        ground_truth: Optional[Dict[str, Any]] = None,
    ) -> Verdict:
        """Evaluate Red vs Blue combat and produce verdict.

        Per 05.11-08: Score attack and defense, determine winner.

        Args:
            attack_plan: AttackPlan from Red Agent
            defense_plan: DefensePlan from Blue Agent
            ground_truth: Optional ground truth for validation

        Returns:
            Verdict with scores, winner, and reasoning
        """
        ground_truth = ground_truth or {}
        attack_id = getattr(attack_plan, "id", "unknown")
        defense_id = getattr(defense_plan, "id", "unknown")

        logger.info(f"JudgeAgent: Evaluating {attack_id} vs {defense_id}")

        # Score Red Team
        red_score = self._score_red_team(attack_plan, ground_truth)

        # Score Blue Team
        blue_score = self._score_blue_team(defense_plan, attack_plan, ground_truth)

        # Determine winner
        winner = self._determine_winner(red_score, blue_score, attack_plan, defense_plan)

        # Identify novel findings
        novel_findings = self._identify_novel_findings(
            attack_plan, defense_plan, ground_truth
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            red_score, blue_score, winner, attack_plan, defense_plan
        )

        verdict = Verdict(
            id=f"verdict:{attack_id}:{defense_id}",
            red_score=red_score.total,
            blue_score=blue_score.total,
            winner=winner,
            novel_findings=novel_findings,
            reasoning=reasoning,
            red_breakdown=red_score,
            blue_breakdown=blue_score,
            metadata={
                "attack_id": attack_id,
                "defense_id": defense_id,
                "ground_truth_available": bool(ground_truth),
            },
        )

        self._verdict_history.append(verdict)

        logger.info(
            f"JudgeAgent: Verdict for {attack_id} - "
            f"Red={red_score.total:.1f}, Blue={blue_score.total:.1f}, "
            f"Winner={winner.value}"
        )

        return verdict

    def _score_red_team(
        self,
        attack_plan: Any,
        ground_truth: Dict[str, Any],
    ) -> Score:
        """Score Red Team attack plan.

        Args:
            attack_plan: AttackPlan
            ground_truth: Ground truth data

        Returns:
            Score with breakdown
        """
        score = Score()

        # Creativity: Novel attack approach
        creativity = self._score_creativity(attack_plan)
        score.add_breakdown(
            ScoreCategory.CREATIVITY,
            creativity,
            self.RED_WEIGHTS[ScoreCategory.CREATIVITY],
            "Assessed attack novelty and approach",
        )

        # Feasibility: Technical feasibility
        feasibility = self._score_feasibility(attack_plan)
        score.add_breakdown(
            ScoreCategory.FEASIBILITY,
            feasibility,
            self.RED_WEIGHTS[ScoreCategory.FEASIBILITY],
            "Assessed technical viability of exploit",
        )

        # Economic Viability: EV > 0
        econ_viability = self._score_economic_viability(attack_plan)
        score.add_breakdown(
            ScoreCategory.ECONOMIC_VIABILITY,
            econ_viability,
            self.RED_WEIGHTS[ScoreCategory.ECONOMIC_VIABILITY],
            f"Expected profit: ${float(getattr(attack_plan, 'expected_profit', 0)):,.2f}",
        )

        # Exploit Completeness: Full PoC vs sketch
        completeness = self._score_exploit_completeness(attack_plan)
        score.add_breakdown(
            ScoreCategory.EXPLOIT_COMPLETENESS,
            completeness,
            self.RED_WEIGHTS[ScoreCategory.EXPLOIT_COMPLETENESS],
            "Assessed completeness of exploit path",
        )

        # Evidence Quality: Supporting evidence
        evidence = self._score_evidence_quality(attack_plan)
        score.add_breakdown(
            ScoreCategory.EVIDENCE_QUALITY,
            evidence,
            self.RED_WEIGHTS[ScoreCategory.EVIDENCE_QUALITY],
            "Assessed evidence supporting attack",
        )

        # Identify strengths and weaknesses
        if econ_viability > 70:
            score.strengths.append("Economically viable attack with positive EV")
        if feasibility > 70:
            score.strengths.append("Technically feasible exploit path")
        if creativity > 70:
            score.strengths.append("Novel or creative attack approach")

        if econ_viability < 50:
            score.weaknesses.append("Attack may not be economically rational")
        if completeness < 50:
            score.weaknesses.append("Exploit path incomplete or missing steps")
        if evidence < 50:
            score.weaknesses.append("Insufficient evidence supporting attack")

        return score

    def _score_blue_team(
        self,
        defense_plan: Any,
        attack_plan: Any,
        ground_truth: Dict[str, Any],
    ) -> Score:
        """Score Blue Team defense plan.

        Args:
            defense_plan: DefensePlan
            attack_plan: AttackPlan being defended
            ground_truth: Ground truth data

        Returns:
            Score with breakdown
        """
        score = Score()

        # Effectiveness: Attack blocked?
        effectiveness = self._score_effectiveness(defense_plan, attack_plan)
        score.add_breakdown(
            ScoreCategory.EFFECTIVENESS,
            effectiveness,
            self.BLUE_WEIGHTS[ScoreCategory.EFFECTIVENESS],
            f"Defense effectiveness: {getattr(defense_plan, 'effectiveness', 0):.1%}",
        )

        # Cost Efficiency: Cost vs prevented loss
        cost_efficiency = self._score_cost_efficiency(defense_plan, attack_plan)
        score.add_breakdown(
            ScoreCategory.COST_EFFICIENCY,
            cost_efficiency,
            self.BLUE_WEIGHTS[ScoreCategory.COST_EFFICIENCY],
            f"Cost/benefit ratio: {getattr(defense_plan, 'cost_benefit_ratio', 0):.2f}",
        )

        # Completeness: All attack vectors addressed?
        completeness = self._score_defense_completeness(defense_plan, attack_plan)
        score.add_breakdown(
            ScoreCategory.COMPLETENESS,
            completeness,
            self.BLUE_WEIGHTS[ScoreCategory.COMPLETENESS],
            "Assessed coverage of attack vectors",
        )

        # Side Effects: Minimal collateral damage
        side_effects = self._score_side_effects(defense_plan)
        score.add_breakdown(
            ScoreCategory.SIDE_EFFECTS,
            side_effects,
            self.BLUE_WEIGHTS[ScoreCategory.SIDE_EFFECTS],
            f"Side effects: {len(getattr(defense_plan, 'side_effects', []))}",
        )

        # Practicality: Easy to implement
        practicality = self._score_practicality(defense_plan)
        score.add_breakdown(
            ScoreCategory.PRACTICALITY,
            practicality,
            self.BLUE_WEIGHTS[ScoreCategory.PRACTICALITY],
            "Assessed implementation practicality",
        )

        # Identify strengths and weaknesses
        if effectiveness > 70:
            score.strengths.append("High effectiveness in blocking attack")
        if cost_efficiency > 70:
            score.strengths.append("Cost-efficient defense strategy")
        if side_effects > 70:
            score.strengths.append("Minimal side effects from patches")

        if effectiveness < 50:
            score.weaknesses.append("Defense may not fully block attack")
        if cost_efficiency < 50:
            score.weaknesses.append("High implementation cost relative to prevented loss")
        if completeness < 50:
            score.weaknesses.append("Some attack vectors not addressed")

        return score

    def _score_creativity(self, attack_plan: Any) -> float:
        """Score attack creativity (0-100)."""
        score = 50.0  # Base score

        # Check for multiple attack vectors
        path = getattr(attack_plan, "exploit_path", None)
        if path and hasattr(path, "transactions"):
            tx_count = len(path.transactions)
            if tx_count > 5:
                score += 20  # Complex multi-step attack
            elif tx_count > 3:
                score += 10

            # Check for diverse transaction types
            tx_types = set()
            for tx in path.transactions:
                if hasattr(tx, "tx_type"):
                    tx_types.add(tx.tx_type.value if hasattr(tx.tx_type, "value") else str(tx.tx_type))
            if len(tx_types) > 3:
                score += 15  # Diverse attack techniques

        # Check for flash loan usage (amplification)
        if getattr(attack_plan, "mev_vulnerability", False):
            score += 10  # Considers MEV implications

        return min(score, 100)

    def _score_feasibility(self, attack_plan: Any) -> float:
        """Score attack feasibility (0-100)."""
        score = 50.0

        # Check success probability
        success_prob = getattr(attack_plan, "success_probability", 0.5)
        score += success_prob * 30  # Up to 30 points for high probability

        # Check if exploit path exists
        path = getattr(attack_plan, "exploit_path", None)
        if path and hasattr(path, "transactions") and path.transactions:
            score += 10  # Has concrete path

        # Check causal chain
        chain = getattr(attack_plan, "causal_chain", [])
        if len(chain) > 2:
            score += 10  # Has causal reasoning

        return min(score, 100)

    def _score_economic_viability(self, attack_plan: Any) -> float:
        """Score economic viability (0-100)."""
        expected_profit = float(getattr(attack_plan, "expected_profit", 0))
        required_capital = float(getattr(attack_plan, "required_capital", 0))

        if expected_profit <= 0:
            return 20.0  # Non-viable

        # Calculate ROI
        if required_capital > 0:
            roi = expected_profit / required_capital
        else:
            roi = expected_profit / 1000  # Minimal capital

        if roi > 10:
            return 95.0  # Extremely profitable
        elif roi > 5:
            return 85.0
        elif roi > 2:
            return 75.0
        elif roi > 1:
            return 65.0
        elif roi > 0.5:
            return 55.0
        else:
            return 40.0

    def _score_exploit_completeness(self, attack_plan: Any) -> float:
        """Score exploit completeness (0-100)."""
        score = 30.0  # Base score

        path = getattr(attack_plan, "exploit_path", None)
        if not path:
            return score

        transactions = getattr(path, "transactions", [])

        # Points for transaction count
        if len(transactions) >= 3:
            score += 20
        elif len(transactions) >= 1:
            score += 10

        # Points for extraction step
        has_extraction = any(
            getattr(tx, "tx_type", None) and
            getattr(tx.tx_type, "value", "") in ("withdraw", "transfer")
            for tx in transactions
        )
        if has_extraction:
            score += 15

        # Points for causal chain
        chain = getattr(attack_plan, "causal_chain", [])
        if chain:
            score += min(len(chain) * 5, 20)

        # Points for evidence
        evidence = getattr(attack_plan, "evidence_refs", [])
        if evidence:
            score += min(len(evidence) * 5, 15)

        return min(score, 100)

    def _score_evidence_quality(self, attack_plan: Any) -> float:
        """Score evidence quality (0-100)."""
        score = 40.0  # Base score

        evidence = getattr(attack_plan, "evidence_refs", [])
        if evidence:
            score += min(len(evidence) * 10, 40)

        # GATE matrix provides strong evidence
        if getattr(attack_plan, "gate_matrix_id", ""):
            score += 15

        # Causal chain provides reasoning evidence
        chain = getattr(attack_plan, "causal_chain", [])
        if len(chain) > 2:
            score += 10

        return min(score, 100)

    def _score_effectiveness(self, defense_plan: Any, attack_plan: Any) -> float:
        """Score defense effectiveness (0-100)."""
        effectiveness = getattr(defense_plan, "effectiveness", 0.0)

        # Convert 0-1 effectiveness to 0-100 score
        score = effectiveness * 100

        # Bonus for high effectiveness
        if effectiveness > 0.9:
            score += 5

        return min(score, 100)

    def _score_cost_efficiency(self, defense_plan: Any, attack_plan: Any) -> float:
        """Score cost efficiency (0-100)."""
        cost = float(getattr(defense_plan, "cost_estimate", 1))
        prevented_loss = float(getattr(attack_plan, "expected_profit", 0))

        if cost == 0:
            return 95.0  # Free defense is excellent

        if prevented_loss == 0:
            return 50.0  # No loss to prevent

        ratio = prevented_loss / cost

        if ratio > 100:
            return 95.0
        elif ratio > 50:
            return 85.0
        elif ratio > 10:
            return 75.0
        elif ratio > 5:
            return 65.0
        elif ratio > 1:
            return 55.0
        else:
            return 35.0  # Cost exceeds prevented loss

    def _score_defense_completeness(
        self, defense_plan: Any, attack_plan: Any
    ) -> float:
        """Score defense completeness (0-100)."""
        score = 40.0  # Base score

        patches = getattr(defense_plan, "patches", [])
        mitigations = getattr(defense_plan, "mitigations", [])
        invariants = getattr(defense_plan, "invariants_suggested", [])

        # Points for patches
        if patches:
            score += min(len(patches) * 10, 25)

        # Points for mitigations
        if mitigations:
            score += min(len(mitigations) * 8, 20)

        # Points for invariants
        if invariants:
            score += min(len(invariants) * 3, 15)

        return min(score, 100)

    def _score_side_effects(self, defense_plan: Any) -> float:
        """Score side effects - lower is worse (0-100)."""
        side_effects = getattr(defense_plan, "side_effects", [])

        # Fewer side effects is better
        if len(side_effects) == 0:
            return 95.0
        elif len(side_effects) <= 2:
            return 75.0
        elif len(side_effects) <= 4:
            return 55.0
        else:
            return 35.0

    def _score_practicality(self, defense_plan: Any) -> float:
        """Score implementation practicality (0-100)."""
        score = 60.0  # Base score

        patches = getattr(defense_plan, "patches", [])
        if not patches:
            return score

        # Score based on average complexity
        complexity_scores = {
            "trivial": 90,
            "simple": 75,
            "moderate": 55,
            "complex": 35,
            "architectural": 15,
        }

        complexities = []
        for patch in patches:
            complexity = getattr(patch, "complexity", None)
            if complexity:
                comp_value = complexity.value if hasattr(complexity, "value") else str(complexity)
                complexities.append(complexity_scores.get(comp_value, 50))

        if complexities:
            score = sum(complexities) / len(complexities)

        return score

    def _determine_winner(
        self,
        red_score: Score,
        blue_score: Score,
        attack_plan: Any,
        defense_plan: Any,
    ) -> VerdictWinner:
        """Determine winner based on scores.

        Args:
            red_score: Red team score
            blue_score: Blue team score
            attack_plan: Attack plan
            defense_plan: Defense plan

        Returns:
            Verdict winner
        """
        margin = abs(red_score.total - blue_score.total)

        # Draw if margin is small
        if margin < 5:
            return VerdictWinner.DRAW

        # Check defense effectiveness
        effectiveness = getattr(defense_plan, "effectiveness", 0.0)

        # If defense is highly effective (>80%), blue wins
        if effectiveness > 0.8:
            return VerdictWinner.BLUE

        # If attack is not viable, blue wins
        expected_profit = float(getattr(attack_plan, "expected_profit", 0))
        if expected_profit <= 0:
            return VerdictWinner.BLUE

        # Otherwise, higher score wins
        if red_score.total > blue_score.total:
            return VerdictWinner.RED
        elif blue_score.total > red_score.total:
            return VerdictWinner.BLUE
        else:
            return VerdictWinner.DRAW

    def _identify_novel_findings(
        self,
        attack_plan: Any,
        defense_plan: Any,
        ground_truth: Dict[str, Any],
    ) -> List[NovelFinding]:
        """Identify novel vulnerabilities from adversarial combat.

        Args:
            attack_plan: Attack plan
            defense_plan: Defense plan
            ground_truth: Known vulnerabilities

        Returns:
            List of novel findings
        """
        findings: List[NovelFinding] = []
        known_vulns = set(ground_truth.get("known_vulnerabilities", []))

        # Check attack plan for novel patterns
        causal_chain = getattr(attack_plan, "causal_chain", [])
        for node in causal_chain:
            if node.startswith("step:") and node not in known_vulns:
                findings.append(
                    NovelFinding(
                        id=f"novel:{node}",
                        description=f"Novel exploit step: {node.replace('step:', '')}",
                        discovered_by="red",
                        severity=getattr(
                            attack_plan, "metadata", {}
                        ).get("severity", "medium"),
                        requires_verification=True,
                    )
                )

        # Check defense for identified gaps
        patches = getattr(defense_plan, "patches", [])
        for patch in patches:
            breaks_at = getattr(patch, "breaks_chain_at", "")
            if breaks_at and breaks_at not in known_vulns:
                findings.append(
                    NovelFinding(
                        id=f"novel:defense:{breaks_at}",
                        description=f"Defense gap identified: {breaks_at}",
                        discovered_by="blue",
                        severity="medium",
                        requires_verification=True,
                    )
                )

        return findings[:5]  # Limit to 5 novel findings

    def _generate_reasoning(
        self,
        red_score: Score,
        blue_score: Score,
        winner: VerdictWinner,
        attack_plan: Any,
        defense_plan: Any,
    ) -> str:
        """Generate reasoning for verdict.

        Args:
            red_score: Red team score
            blue_score: Blue team score
            winner: Verdict winner
            attack_plan: Attack plan
            defense_plan: Defense plan

        Returns:
            Reasoning string
        """
        lines = [
            f"## Verdict: {winner.value.upper()}",
            "",
            f"**Red Team Score:** {red_score.total:.1f}/100",
            f"**Blue Team Score:** {blue_score.total:.1f}/100",
            "",
        ]

        # Winner analysis
        if winner == VerdictWinner.RED:
            lines.append("### Attack Succeeds")
            lines.append("The Red Team's attack plan demonstrates a viable exploit that ")
            lines.append("the Blue Team's defenses do not adequately counter.")
        elif winner == VerdictWinner.BLUE:
            lines.append("### Defense Succeeds")
            lines.append("The Blue Team's defense plan effectively blocks the attack ")
            lines.append("with acceptable cost and minimal side effects.")
        else:
            lines.append("### Inconclusive")
            lines.append("Neither team demonstrated clear dominance. ")
            lines.append("Further investigation recommended.")

        lines.append("")

        # Red team analysis
        lines.append("### Red Team Analysis")
        if red_score.strengths:
            lines.append("**Strengths:**")
            for s in red_score.strengths:
                lines.append(f"- {s}")
        if red_score.weaknesses:
            lines.append("**Weaknesses:**")
            for w in red_score.weaknesses:
                lines.append(f"- {w}")

        lines.append("")

        # Blue team analysis
        lines.append("### Blue Team Analysis")
        if blue_score.strengths:
            lines.append("**Strengths:**")
            for s in blue_score.strengths:
                lines.append(f"- {s}")
        if blue_score.weaknesses:
            lines.append("**Weaknesses:**")
            for w in blue_score.weaknesses:
                lines.append(f"- {w}")

        return "\n".join(lines)

    def get_verdict_history(self) -> List[Verdict]:
        """Get list of all verdicts for analysis."""
        return self._verdict_history

    def get_red_win_rate(self) -> float:
        """Calculate Red Team win rate."""
        if not self._verdict_history:
            return 0.0
        red_wins = sum(
            1 for v in self._verdict_history
            if v.winner == VerdictWinner.RED
        )
        return red_wins / len(self._verdict_history)

    def get_blue_win_rate(self) -> float:
        """Calculate Blue Team win rate."""
        if not self._verdict_history:
            return 0.0
        blue_wins = sum(
            1 for v in self._verdict_history
            if v.winner == VerdictWinner.BLUE
        )
        return blue_wins / len(self._verdict_history)

    def clear_history(self) -> None:
        """Clear verdict history for new simulation."""
        self._verdict_history.clear()


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "JudgeAgent",
    "Verdict",
    "Score",
    "ScoreBreakdown",
    "ScoreCategory",
    "VerdictWinner",
    "NovelFinding",
]
