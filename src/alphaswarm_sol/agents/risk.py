"""Phase 9: Risk Agent.

The Risk Agent generates and assesses attack scenarios from the subgraph,
estimating likelihood, impact, and exploitability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

from alphaswarm_sol.agents.base import (
    VerificationAgent,
    AgentResult,
    AgentEvidence,
    EvidenceType,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode


class ScenarioType(str, Enum):
    """Types of attack scenarios."""
    REENTRANCY = "reentrancy"
    FLASH_LOAN = "flash_loan"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ORACLE_MANIPULATION = "oracle_manipulation"
    FRONT_RUNNING = "front_running"
    VALUE_EXTRACTION = "value_extraction"
    ACCESS_CONTROL_BYPASS = "access_control_bypass"
    DENIAL_OF_SERVICE = "denial_of_service"


class Likelihood(str, Enum):
    """Attack likelihood levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Impact(str, Enum):
    """Attack impact levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AttackAssessment:
    """Assessment of an attack scenario.

    Contains likelihood, impact, required conditions, and exploitability score.
    """
    id: str
    scenario_type: ScenarioType
    description: str
    likelihood: Likelihood = Likelihood.MEDIUM
    impact: Impact = Impact.MEDIUM
    required_conditions: List[str] = field(default_factory=list)
    exploitability_score: float = 0.0
    affected_functions: List[str] = field(default_factory=list)
    attack_steps: List[str] = field(default_factory=list)
    mitigation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scenario_type": self.scenario_type.value,
            "description": self.description,
            "likelihood": self.likelihood.value,
            "impact": self.impact.value,
            "required_conditions": self.required_conditions,
            "exploitability_score": self.exploitability_score,
            "affected_functions": self.affected_functions,
            "attack_steps": self.attack_steps,
            "mitigation": self.mitigation,
        }


# Impact weights for exploitability scoring
IMPACT_WEIGHTS = {
    Impact.LOW: 1.0,
    Impact.MEDIUM: 2.0,
    Impact.HIGH: 4.0,
    Impact.CRITICAL: 8.0,
}

# Likelihood weights for exploitability scoring
LIKELIHOOD_WEIGHTS = {
    Likelihood.LOW: 0.5,
    Likelihood.MEDIUM: 1.0,
    Likelihood.HIGH: 2.0,
}


class RiskAgent(VerificationAgent):
    """Risk Agent for attack scenario generation and assessment.

    This agent generates attack scenarios from the subgraph and assesses:
    - Likelihood: How easy is the attack to execute?
    - Impact: What damage can be done?
    - Exploitability: Combined score based on attack surface
    """

    # Threshold for flagging high-risk scenarios
    EXPLOITABILITY_THRESHOLD = 5.0

    def __init__(self, exploitability_threshold: float = 5.0):
        """Initialize the Risk Agent.

        Args:
            exploitability_threshold: Minimum score to flag as high-risk
        """
        self.exploitability_threshold = exploitability_threshold

    @property
    def agent_name(self) -> str:
        return "risk"

    def confidence(self) -> float:
        return 0.80

    def analyze(self, subgraph: "SubGraph", query: str = "") -> AgentResult:
        """Analyze the subgraph for attack scenarios.

        Args:
            subgraph: SubGraph to analyze
            query: Optional query context

        Returns:
            AgentResult with attack assessments as findings
        """
        if not subgraph.nodes:
            return self._create_empty_result()

        # Generate attack scenarios
        scenarios = self._generate_attack_scenarios(subgraph)

        # Assess each scenario
        assessed = []
        for scenario in scenarios:
            assessment = self._assess_scenario(scenario, subgraph)
            assessed.append(assessment)

        # Filter to high-risk scenarios
        high_risk = [
            a for a in assessed
            if a.exploitability_score >= self.exploitability_threshold
        ]

        # Sort by exploitability score
        high_risk.sort(key=lambda a: a.exploitability_score, reverse=True)

        # Create evidence
        evidence = []
        for assessment in high_risk:
            evidence.append(AgentEvidence(
                type=EvidenceType.SCENARIO,
                data=assessment.to_dict(),
                description=assessment.description,
                confidence=self._compute_assessment_confidence(assessment),
                source_nodes=assessment.affected_functions,
            ))

        # Compute overall confidence
        if high_risk:
            avg_confidence = sum(
                self._compute_assessment_confidence(a) for a in high_risk
            ) / len(high_risk)
            overall_confidence = self.confidence() * avg_confidence
        else:
            overall_confidence = self.confidence() * 0.5

        return AgentResult(
            agent=self.agent_name,
            matched=bool(high_risk),
            findings=[a.to_dict() for a in high_risk],
            confidence=overall_confidence,
            evidence=evidence,
            metadata={
                "scenarios_generated": len(scenarios),
                "high_risk_count": len(high_risk),
                "max_exploitability": max(
                    (a.exploitability_score for a in assessed), default=0.0
                ),
            },
        )

    def _generate_attack_scenarios(
        self, subgraph: "SubGraph"
    ) -> List[AttackAssessment]:
        """Generate potential attack scenarios from the subgraph."""
        scenarios = []

        for node_id, node in subgraph.nodes.items():
            if node.type != "Function":
                continue

            props = node.properties

            # Reentrancy scenario
            if props.get("state_write_after_external_call"):
                if not props.get("has_reentrancy_guard"):
                    scenarios.append(AttackAssessment(
                        id=f"reentrancy:{node_id}",
                        scenario_type=ScenarioType.REENTRANCY,
                        description=f"Reentrancy attack via {node.label}",
                        affected_functions=[node_id],
                        attack_steps=[
                            "Call vulnerable function",
                            "During external call, re-enter the function",
                            "Exploit state inconsistency",
                        ],
                        mitigation="Add reentrancy guard or use CEI pattern",
                    ))

            # Privilege escalation scenario
            if props.get("writes_privileged_state"):
                if not props.get("has_access_gate"):
                    scenarios.append(AttackAssessment(
                        id=f"privilege:{node_id}",
                        scenario_type=ScenarioType.PRIVILEGE_ESCALATION,
                        description=f"Privilege escalation via {node.label}",
                        affected_functions=[node_id],
                        attack_steps=[
                            "Identify unprotected privileged function",
                            "Call function without authorization",
                            "Gain elevated privileges",
                        ],
                        mitigation="Add access control modifier",
                    ))

            # Oracle manipulation scenario
            if props.get("reads_oracle_price"):
                if not props.get("has_staleness_check"):
                    scenarios.append(AttackAssessment(
                        id=f"oracle:{node_id}",
                        scenario_type=ScenarioType.ORACLE_MANIPULATION,
                        description=f"Oracle manipulation via {node.label}",
                        affected_functions=[node_id],
                        attack_steps=[
                            "Manipulate oracle price",
                            "Trigger function with stale/manipulated price",
                            "Profit from price discrepancy",
                        ],
                        mitigation="Add staleness check and TWAP",
                    ))

            # Flash loan scenario
            if "TRANSFERS_VALUE_OUT" in props.get("semantic_ops", []):
                if props.get("has_external_calls") and not props.get("checks_balance_before_transfer"):
                    scenarios.append(AttackAssessment(
                        id=f"flashloan:{node_id}",
                        scenario_type=ScenarioType.FLASH_LOAN,
                        description=f"Flash loan attack via {node.label}",
                        affected_functions=[node_id],
                        attack_steps=[
                            "Take flash loan",
                            "Call vulnerable function with borrowed funds",
                            "Extract value before repayment",
                        ],
                        mitigation="Add balance checks and flash loan protection",
                    ))

            # Front-running scenario
            if props.get("swap_like") or "swap" in node.label.lower():
                if not props.get("has_deadline_check"):
                    scenarios.append(AttackAssessment(
                        id=f"frontrun:{node_id}",
                        scenario_type=ScenarioType.FRONT_RUNNING,
                        description=f"Front-running attack on {node.label}",
                        affected_functions=[node_id],
                        attack_steps=[
                            "Monitor mempool for profitable transactions",
                            "Submit transaction with higher gas price",
                            "Extract MEV from victim transaction",
                        ],
                        mitigation="Add deadline parameter and slippage protection",
                    ))

            # DoS scenario
            if props.get("has_unbounded_loop"):
                scenarios.append(AttackAssessment(
                    id=f"dos:{node_id}",
                    scenario_type=ScenarioType.DENIAL_OF_SERVICE,
                    description=f"DoS attack via unbounded loop in {node.label}",
                    affected_functions=[node_id],
                    attack_steps=[
                        "Increase loop iterations (e.g., add many small deposits)",
                        "Function exceeds gas limit",
                        "Contract becomes unusable",
                    ],
                    mitigation="Add pagination or limit loop iterations",
                ))

            # Value extraction scenario
            if props.get("uses_delegatecall"):
                if not props.get("has_access_gate"):
                    scenarios.append(AttackAssessment(
                        id=f"delegatecall:{node_id}",
                        scenario_type=ScenarioType.VALUE_EXTRACTION,
                        description=f"Value extraction via delegatecall in {node.label}",
                        affected_functions=[node_id],
                        attack_steps=[
                            "Craft malicious implementation contract",
                            "Call unprotected delegatecall function",
                            "Execute arbitrary code in context of victim",
                        ],
                        mitigation="Restrict delegatecall to trusted contracts only",
                    ))

        return scenarios

    def _assess_scenario(
        self, scenario: AttackAssessment, subgraph: "SubGraph"
    ) -> AttackAssessment:
        """Assess a scenario for likelihood, impact, and exploitability."""
        # Determine likelihood based on scenario type and conditions
        likelihood = self._estimate_likelihood(scenario, subgraph)
        scenario.likelihood = likelihood

        # Determine impact based on scenario type
        impact = self._estimate_impact(scenario, subgraph)
        scenario.impact = impact

        # Extract required conditions
        scenario.required_conditions = self._extract_conditions(scenario, subgraph)

        # Compute exploitability score
        scenario.exploitability_score = self._compute_exploitability(scenario)

        return scenario

    def _estimate_likelihood(
        self, scenario: AttackAssessment, subgraph: "SubGraph"
    ) -> Likelihood:
        """Estimate attack likelihood."""
        # High likelihood for common, easily exploitable patterns
        high_likelihood_types = {
            ScenarioType.PRIVILEGE_ESCALATION,
            ScenarioType.ACCESS_CONTROL_BYPASS,
        }
        if scenario.scenario_type in high_likelihood_types:
            return Likelihood.HIGH

        # Medium likelihood for scenarios requiring specific conditions
        medium_likelihood_types = {
            ScenarioType.REENTRANCY,
            ScenarioType.DENIAL_OF_SERVICE,
            ScenarioType.VALUE_EXTRACTION,
        }
        if scenario.scenario_type in medium_likelihood_types:
            return Likelihood.MEDIUM

        # Low likelihood for complex scenarios
        return Likelihood.LOW

    def _estimate_impact(
        self, scenario: AttackAssessment, subgraph: "SubGraph"
    ) -> Impact:
        """Estimate attack impact."""
        # Critical impact for value extraction and privilege escalation
        critical_impact_types = {
            ScenarioType.VALUE_EXTRACTION,
            ScenarioType.REENTRANCY,
        }
        if scenario.scenario_type in critical_impact_types:
            return Impact.CRITICAL

        # High impact for financial manipulation
        high_impact_types = {
            ScenarioType.FLASH_LOAN,
            ScenarioType.ORACLE_MANIPULATION,
            ScenarioType.PRIVILEGE_ESCALATION,
        }
        if scenario.scenario_type in high_impact_types:
            return Impact.HIGH

        # Medium impact for MEV and DoS
        medium_impact_types = {
            ScenarioType.FRONT_RUNNING,
            ScenarioType.DENIAL_OF_SERVICE,
        }
        if scenario.scenario_type in medium_impact_types:
            return Impact.MEDIUM

        return Impact.LOW

    def _extract_conditions(
        self, scenario: AttackAssessment, subgraph: "SubGraph"
    ) -> List[str]:
        """Extract required conditions for the attack."""
        conditions = []

        if scenario.scenario_type == ScenarioType.REENTRANCY:
            conditions.append("No reentrancy guard")
            conditions.append("State written after external call")
            conditions.append("Attacker-controlled callback")

        elif scenario.scenario_type == ScenarioType.PRIVILEGE_ESCALATION:
            conditions.append("No access control")
            conditions.append("Function modifies privileged state")

        elif scenario.scenario_type == ScenarioType.FLASH_LOAN:
            conditions.append("External call before state update")
            conditions.append("Sufficient liquidity for flash loan")
            conditions.append("Profitable price impact")

        elif scenario.scenario_type == ScenarioType.ORACLE_MANIPULATION:
            conditions.append("Oracle price can be manipulated")
            conditions.append("No staleness check")
            conditions.append("Sufficient capital to move price")

        elif scenario.scenario_type == ScenarioType.FRONT_RUNNING:
            conditions.append("Transaction in public mempool")
            conditions.append("No deadline protection")
            conditions.append("Profitable MEV opportunity")

        elif scenario.scenario_type == ScenarioType.DENIAL_OF_SERVICE:
            conditions.append("Unbounded loop controllable by attacker")
            conditions.append("Gas cost can exceed block limit")

        elif scenario.scenario_type == ScenarioType.VALUE_EXTRACTION:
            conditions.append("Delegatecall to attacker-controlled address")
            conditions.append("No access restriction")

        return conditions

    def _compute_exploitability(self, scenario: AttackAssessment) -> float:
        """Compute exploitability score from likelihood and impact."""
        likelihood_weight = LIKELIHOOD_WEIGHTS.get(scenario.likelihood, 1.0)
        impact_weight = IMPACT_WEIGHTS.get(scenario.impact, 2.0)

        # Base score from likelihood * impact
        base_score = likelihood_weight * impact_weight

        # Adjust based on number of required conditions (more = harder)
        condition_penalty = len(scenario.required_conditions) * 0.2
        adjusted_score = base_score - condition_penalty

        return max(adjusted_score, 0.0)

    def _compute_assessment_confidence(self, assessment: AttackAssessment) -> float:
        """Compute confidence for an assessment."""
        # Higher confidence for common attack patterns
        base = 0.7

        if assessment.scenario_type in {ScenarioType.REENTRANCY, ScenarioType.PRIVILEGE_ESCALATION}:
            base = 0.9
        elif assessment.scenario_type in {ScenarioType.FLASH_LOAN, ScenarioType.ORACLE_MANIPULATION}:
            base = 0.8

        # Adjust based on exploitability
        if assessment.exploitability_score >= 8.0:
            base += 0.05
        elif assessment.exploitability_score >= 5.0:
            base += 0.02

        return min(base, 1.0)
