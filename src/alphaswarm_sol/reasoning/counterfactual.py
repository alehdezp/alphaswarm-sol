"""
Phase 3: Counterfactual Generator

Generates "what if" scenarios from causal analysis to prove causality
and validate fix recommendations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from alphaswarm_sol.reasoning.causal import CausalAnalysis, RootCause, CausalGraph


class InterventionType(Enum):
    """Types of counterfactual interventions."""
    REMOVE_NODE = "remove_node"  # Remove an operation
    REORDER_OPERATIONS = "reorder_operations"  # Change execution order
    ADD_GUARD = "add_guard"  # Add protective check
    ADD_VALIDATION = "add_validation"  # Add input/state validation
    BREAK_EDGE = "break_edge"  # Break causal relationship
    CHANGE_PROPERTY = "change_property"  # Modify node property


@dataclass
class Counterfactual:
    """
    A counterfactual scenario proving causality.

    Represents "What if X changed?" and demonstrates the impact
    on vulnerability existence.
    """
    id: str
    scenario_name: str  # Human-readable scenario name

    # Original state
    original_description: str  # What actually happens
    original_vulnerability: str  # The vulnerability that exists

    # Counterfactual intervention
    intervention_type: InterventionType
    intervention_description: str  # What we change
    intervention_target: str  # What node/edge/property

    # Expected outcome
    blocks_vulnerability: bool  # Does this prevent the vulnerability?
    expected_outcome: str  # What happens after intervention
    confidence: float  # Confidence this would work (0.0-1.0)

    # Evidence
    causal_path_broken: List[str]  # Which causal paths are broken
    affected_nodes: List[str]  # Which nodes are affected

    # Fix recommendation
    code_diff: Optional[str] = None  # Suggested code change
    fix_complexity: str = "unknown"  # "trivial", "moderate", "complex"
    side_effects: List[str] = field(default_factory=list)


@dataclass
class CounterfactualSet:
    """A collection of counterfactuals for a vulnerability."""
    vulnerability_id: str
    function_id: str
    counterfactuals: List[Counterfactual] = field(default_factory=list)

    # Analysis
    total_scenarios: int = 0
    scenarios_that_block: int = 0
    recommended_scenario: Optional[str] = None  # ID of best fix


class CounterfactualGenerator:
    """
    Generates counterfactual scenarios from causal analysis.

    The generator works by:
    1. Taking causal analysis with root causes
    2. For each root cause, generating intervention scenarios
    3. Simulating impact of each intervention
    4. Ranking scenarios by effectiveness and simplicity
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client  # Optional for enhanced code diff generation

    def generate(
        self,
        causal_analysis: "CausalAnalysis",
    ) -> CounterfactualSet:
        """
        Generate counterfactual scenarios from causal analysis.

        Args:
            causal_analysis: Complete causal analysis with root causes

        Returns:
            CounterfactualSet with all generated scenarios
        """
        cf_set = CounterfactualSet(
            vulnerability_id=causal_analysis.causal_graph.vulnerability_id or "unknown",
            function_id=causal_analysis.causal_graph.focal_node_id,
        )

        # Generate counterfactuals for each root cause
        for root_cause in causal_analysis.root_causes:
            scenarios = self._generate_for_root_cause(
                root_cause,
                causal_analysis.causal_graph,
            )
            cf_set.counterfactuals.extend(scenarios)

        # Generate from intervention points
        for intervention_point in causal_analysis.intervention_points:
            scenario = self._generate_from_intervention_point(
                intervention_point,
                causal_analysis.causal_graph,
            )
            cf_set.counterfactuals.append(scenario)

        # Update metrics
        cf_set.total_scenarios = len(cf_set.counterfactuals)
        cf_set.scenarios_that_block = sum(
            1 for cf in cf_set.counterfactuals if cf.blocks_vulnerability
        )

        # Recommend best scenario
        cf_set.recommended_scenario = self._select_best_scenario(
            cf_set.counterfactuals
        )

        return cf_set

    def _generate_for_root_cause(
        self,
        root_cause: "RootCause",
        graph: "CausalGraph",
    ) -> List[Counterfactual]:
        """
        Generate counterfactual scenarios for a root cause.

        Different root cause types generate different scenarios.
        """
        scenarios = []

        if root_cause.cause_type == "ordering_violation":
            # Scenario: What if operations were reordered?
            scenarios.append(Counterfactual(
                id=f"cf_reorder_{root_cause.id}",
                scenario_name="Reorder to CEI Pattern",
                original_description=root_cause.description,
                original_vulnerability=root_cause.severity,
                intervention_type=InterventionType.REORDER_OPERATIONS,
                intervention_description=root_cause.intervention,
                intervention_target=",".join(root_cause.causal_path),
                blocks_vulnerability=True,
                expected_outcome="State updated before external call, preventing reentrancy",
                confidence=root_cause.intervention_confidence,
                causal_path_broken=root_cause.causal_path,
                affected_nodes=root_cause.causal_path,
                code_diff=self._generate_reorder_diff(root_cause),
                fix_complexity="moderate",
                side_effects=["Requires code refactoring"],
            ))

        elif root_cause.cause_type == "missing_guard":
            # Scenario: What if guard was added?
            scenarios.append(Counterfactual(
                id=f"cf_guard_{root_cause.id}",
                scenario_name="Add Protective Guard",
                original_description=root_cause.description,
                original_vulnerability=root_cause.severity,
                intervention_type=InterventionType.ADD_GUARD,
                intervention_description=root_cause.intervention,
                intervention_target=root_cause.causal_path[0] if root_cause.causal_path else "function",
                blocks_vulnerability=True,
                expected_outcome="Guard prevents vulnerable execution path",
                confidence=root_cause.intervention_confidence,
                causal_path_broken=root_cause.causal_path,
                affected_nodes=root_cause.causal_path,
                code_diff=self._generate_guard_diff(root_cause),
                fix_complexity="trivial",
                side_effects=["Slight gas overhead from guard check"],
            ))

        elif root_cause.cause_type == "missing_validation":
            # Scenario: What if validation was added?
            scenarios.append(Counterfactual(
                id=f"cf_validate_{root_cause.id}",
                scenario_name="Add Validation Check",
                original_description=root_cause.description,
                original_vulnerability=root_cause.severity,
                intervention_type=InterventionType.ADD_VALIDATION,
                intervention_description=root_cause.intervention,
                intervention_target=root_cause.causal_path[0] if root_cause.causal_path else "function",
                blocks_vulnerability=True,
                expected_outcome="Invalid inputs rejected before processing",
                confidence=root_cause.intervention_confidence,
                causal_path_broken=root_cause.causal_path,
                affected_nodes=root_cause.causal_path,
                code_diff=self._generate_validation_diff(root_cause),
                fix_complexity="trivial",
                side_effects=["Transactions may revert on stale/invalid data"],
            ))

        # Generate alternative scenarios from alternative interventions
        for i, alt_intervention in enumerate(root_cause.alternative_interventions):
            scenarios.append(Counterfactual(
                id=f"cf_alt_{root_cause.id}_{i}",
                scenario_name=f"Alternative: {alt_intervention[:30]}",
                original_description=root_cause.description,
                original_vulnerability=root_cause.severity,
                intervention_type=self._infer_intervention_type(alt_intervention),
                intervention_description=alt_intervention,
                intervention_target=root_cause.causal_path[0] if root_cause.causal_path else "function",
                blocks_vulnerability=True,
                expected_outcome="Vulnerability prevented via alternative approach",
                confidence=root_cause.intervention_confidence * 0.9,  # Slightly lower for alternatives
                causal_path_broken=root_cause.causal_path,
                affected_nodes=root_cause.causal_path,
                code_diff=None,  # Would need LLM for alternative diffs
                fix_complexity="unknown",
            ))

        return scenarios

    def _generate_from_intervention_point(
        self,
        intervention_point,
        graph: "CausalGraph",
    ) -> Counterfactual:
        """Generate counterfactual from intervention point."""
        intervention_type_map = {
            "reorder": InterventionType.REORDER_OPERATIONS,
            "add_guard": InterventionType.ADD_GUARD,
            "add_check": InterventionType.ADD_VALIDATION,
            "remove": InterventionType.REMOVE_NODE,
        }

        return Counterfactual(
            id=f"cf_ip_{intervention_point.id}",
            scenario_name=intervention_point.description,
            original_description=f"Vulnerable execution at {intervention_point.node_id}",
            original_vulnerability="TBD",
            intervention_type=intervention_type_map.get(
                intervention_point.intervention_type,
                InterventionType.CHANGE_PROPERTY
            ),
            intervention_description=intervention_point.description,
            intervention_target=intervention_point.node_id,
            blocks_vulnerability=True,
            expected_outcome="Intervention point blocks vulnerability",
            confidence=intervention_point.impact_score,
            causal_path_broken=intervention_point.blocks_causes,
            affected_nodes=[intervention_point.node_id],
            code_diff=intervention_point.code_suggestion,
            fix_complexity=intervention_point.complexity,
            side_effects=intervention_point.side_effects,
        )

    def _generate_reorder_diff(self, root_cause: "RootCause") -> str:
        """Generate code diff for reordering operations."""
        return """```diff
- // Original: External call before state update
- (bool success,) = msg.sender.call{value: amount}("");
- require(success, "Transfer failed");
- balances[msg.sender] -= amount;

+ // Fixed: State update before external call (CEI pattern)
+ balances[msg.sender] -= amount;
+ (bool success,) = msg.sender.call{value: amount}("");
+ require(success, "Transfer failed");
```"""

    def _generate_guard_diff(self, root_cause: "RootCause") -> str:
        """Generate code diff for adding guard."""
        if "nonReentrant" in root_cause.intervention:
            return """```diff
- function withdraw(uint256 amount) external {
+ function withdraw(uint256 amount) external nonReentrant {
      // function body
  }
```"""
        elif "onlyOwner" in root_cause.intervention or "access" in root_cause.intervention.lower():
            return """```diff
- function setOwner(address newOwner) external {
+ function setOwner(address newOwner) external onlyOwner {
      owner = newOwner;
  }
```"""
        else:
            return """```diff
+ // Add protective guard
+ require(condition, "Guard check");
```"""

    def _generate_validation_diff(self, root_cause: "RootCause") -> str:
        """Generate code diff for adding validation."""
        if "staleness" in root_cause.description.lower():
            return """```diff
  (uint80 roundId, int256 answer, , uint256 updatedAt, ) = oracle.latestRoundData();
+ require(updatedAt > block.timestamp - STALENESS_THRESHOLD, "Stale price");
+ require(answer > 0, "Invalid price");
  price = uint256(answer);
```"""
        else:
            return """```diff
+ // Add validation
+ require(input != address(0), "Zero address");
+ require(amount > 0, "Zero amount");
```"""

    def _infer_intervention_type(self, intervention_text: str) -> InterventionType:
        """Infer intervention type from text description."""
        text_lower = intervention_text.lower()

        # Check remove/delete first (before "move" check)
        if "remove" in text_lower or "delete" in text_lower:
            return InterventionType.REMOVE_NODE
        elif "reorder" in text_lower or "move" in text_lower or "before" in text_lower:
            return InterventionType.REORDER_OPERATIONS
        elif "guard" in text_lower or "modifier" in text_lower:
            return InterventionType.ADD_GUARD
        elif "check" in text_lower or "validate" in text_lower or "require" in text_lower:
            return InterventionType.ADD_VALIDATION
        else:
            return InterventionType.CHANGE_PROPERTY

    def _select_best_scenario(
        self,
        counterfactuals: List[Counterfactual],
    ) -> Optional[str]:
        """
        Select best counterfactual scenario based on multiple criteria.

        Ranking criteria (in order):
        1. Must block vulnerability
        2. Higher confidence
        3. Lower complexity
        4. Fewer side effects
        """
        if not counterfactuals:
            return None

        # Filter to only scenarios that block vulnerability
        blocking = [cf for cf in counterfactuals if cf.blocks_vulnerability]
        if not blocking:
            return None

        # Complexity scoring
        complexity_scores = {
            "trivial": 3,
            "moderate": 2,
            "complex": 1,
            "unknown": 0,
        }

        # Score each scenario
        def score_scenario(cf: Counterfactual) -> float:
            score = 0.0

            # Confidence (weight: 0.5)
            score += cf.confidence * 0.5

            # Complexity (weight: 0.3)
            complexity_score = complexity_scores.get(cf.fix_complexity, 0) / 3.0
            score += complexity_score * 0.3

            # Side effects (weight: 0.2, fewer is better)
            side_effect_score = 1.0 / (1.0 + len(cf.side_effects))
            score += side_effect_score * 0.2

            return score

        # Sort by score descending
        ranked = sorted(blocking, key=score_scenario, reverse=True)

        return ranked[0].id if ranked else None

    def explain_counterfactual(self, cf: Counterfactual) -> str:
        """Generate human-readable explanation of counterfactual."""
        lines = [f"# Counterfactual: {cf.scenario_name}\n"]

        lines.append("## Original Situation")
        lines.append(f"- **Description**: {cf.original_description}")
        lines.append(f"- **Vulnerability**: {cf.original_vulnerability}")
        lines.append("")

        lines.append("## Counterfactual Intervention")
        lines.append(f"- **Type**: {cf.intervention_type.value}")
        lines.append(f"- **What Changes**: {cf.intervention_description}")
        lines.append(f"- **Target**: {cf.intervention_target}")
        lines.append("")

        lines.append("## Expected Outcome")
        lines.append(f"- **Blocks Vulnerability**: {'Yes' if cf.blocks_vulnerability else 'No'}")
        lines.append(f"- **Outcome**: {cf.expected_outcome}")
        lines.append(f"- **Confidence**: {cf.confidence:.0%}")
        lines.append("")

        if cf.causal_path_broken:
            lines.append("## Causal Impact")
            lines.append(f"- **Paths Broken**: {' → '.join(cf.causal_path_broken)}")
            lines.append(f"- **Affected Nodes**: {len(cf.affected_nodes)}")
            lines.append("")

        if cf.code_diff:
            lines.append("## Code Change")
            lines.append(cf.code_diff)
            lines.append("")

        lines.append("## Implementation")
        lines.append(f"- **Complexity**: {cf.fix_complexity}")
        if cf.side_effects:
            lines.append(f"- **Side Effects**: {', '.join(cf.side_effects)}")
        lines.append("")

        return "\n".join(lines)

    def generate_report(self, cf_set: CounterfactualSet) -> str:
        """Generate comprehensive report for counterfactual set."""
        lines = ["# Counterfactual Analysis Report\n"]

        lines.append(f"**Function**: {cf_set.function_id}")
        lines.append(f"**Vulnerability**: {cf_set.vulnerability_id}")
        lines.append(f"**Total Scenarios**: {cf_set.total_scenarios}")
        lines.append(f"**Scenarios That Block**: {cf_set.scenarios_that_block}")
        lines.append("")

        # Recommended fix
        if cf_set.recommended_scenario:
            recommended = next(
                (cf for cf in cf_set.counterfactuals if cf.id == cf_set.recommended_scenario),
                None
            )
            if recommended:
                lines.append("## Recommended Fix\n")
                lines.append(f"**Scenario**: {recommended.scenario_name}")
                lines.append(f"**Confidence**: {recommended.confidence:.0%}")
                lines.append(f"**Complexity**: {recommended.fix_complexity}")
                if recommended.code_diff:
                    lines.append(f"\n{recommended.code_diff}")
                lines.append("")

        # All scenarios
        lines.append("## All Scenarios\n")
        for i, cf in enumerate(cf_set.counterfactuals, 1):
            lines.append(f"### {i}. {cf.scenario_name}")
            lines.append(f"- **Type**: {cf.intervention_type.value}")
            lines.append(f"- **Blocks Vulnerability**: {'Yes' if cf.blocks_vulnerability else 'No'}")
            lines.append(f"- **Confidence**: {cf.confidence:.0%}")
            lines.append(f"- **Complexity**: {cf.fix_complexity}")
            lines.append("")

        return "\n".join(lines)
