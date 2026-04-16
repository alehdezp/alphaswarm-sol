"""
Phase 3: Attack Path Synthesis

Synthesizes complete multi-step attack paths from iterative reasoning,
causal analysis, and vulnerability candidates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from alphaswarm_sol.reasoning.iterative import ReasoningResult, AttackChain
    from alphaswarm_sol.reasoning.causal import CausalAnalysis
    from alphaswarm_sol.kg.schema import Node


class AttackComplexity(Enum):
    """Attack complexity levels."""
    TRIVIAL = "trivial"  # Single transaction, no setup
    LOW = "low"  # Few transactions, minimal setup
    MEDIUM = "medium"  # Multiple transactions, some setup
    HIGH = "high"  # Complex multi-step, significant setup
    VERY_HIGH = "very_high"  # Sophisticated, requires deep knowledge


class AttackImpact(Enum):
    """Estimated attack impact levels."""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AttackStep:
    """Single step in an attack path."""
    step_number: int
    description: str  # Human-readable description
    function_called: str  # Function executed in this step

    # Transaction details
    transaction_type: str  # "setup", "exploit", "extract"
    requires_setup: bool = False
    setup_description: Optional[str] = None

    # Code/pseudocode for this step
    code_snippet: Optional[str] = None

    # Prerequisites
    preconditions: List[str] = field(default_factory=list)
    state_changes: List[str] = field(default_factory=list)


@dataclass
class AttackPath:
    """
    Complete multi-step attack path.

    Represents an end-to-end exploit scenario from entry point
    to vulnerability exploitation.
    """
    id: str
    name: str  # Human-readable attack name

    # Path structure
    entry_point: str  # Where attack starts (usually public function)
    steps: List[AttackStep]
    exit_point: str  # Final vulnerable function

    # Attack characteristics
    complexity: AttackComplexity
    estimated_impact: AttackImpact
    total_steps: int

    # Feasibility
    feasibility_score: float  # 0.0 to 1.0
    required_conditions: List[str] = field(default_factory=list)
    attacker_capabilities: List[str] = field(default_factory=list)

    # Output
    poc_code: Optional[str] = None
    exploit_description: Optional[str] = None

    # Evidence
    vulnerability_ids: List[str] = field(default_factory=list)
    causal_chains: List[str] = field(default_factory=list)


@dataclass
class AttackPathSet:
    """Collection of synthesized attack paths."""
    target_contract: str
    total_paths: int = 0
    paths_by_severity: Dict[str, List[AttackPath]] = field(default_factory=dict)
    highest_impact_path: Optional[str] = None
    easiest_path: Optional[str] = None

    all_paths: List[AttackPath] = field(default_factory=list)


class AttackPathSynthesizer:
    """
    Synthesizes complete attack paths from reasoning results.

    Combines:
    1. Iterative reasoning results (multi-function chains)
    2. Causal analysis (root causes and interventions)
    3. Vulnerability candidates

    To produce end-to-end exploit scenarios with PoC code.
    """

    def __init__(self, code_kg=None):
        self.code_kg = code_kg

    def synthesize(
        self,
        reasoning_result: "ReasoningResult",
        causal_analyses: Optional[List["CausalAnalysis"]] = None,
    ) -> AttackPathSet:
        """
        Synthesize attack paths from reasoning results.

        Args:
            reasoning_result: Multi-round iterative reasoning result
            causal_analyses: Optional causal analyses for candidates

        Returns:
            AttackPathSet with all synthesized paths
        """
        path_set = AttackPathSet(
            target_contract="unknown",  # Would get from KG
        )

        # Synthesize paths from attack chains
        for chain in reasoning_result.attack_chains:
            path = self._synthesize_from_chain(chain, reasoning_result)
            if path:
                path_set.all_paths.append(path)

        # Synthesize paths from final candidates (if no chains)
        if not reasoning_result.attack_chains:
            for candidate in reasoning_result.final_candidates:
                path = self._synthesize_from_candidate(
                    candidate,
                    reasoning_result,
                    causal_analyses,
                )
                if path:
                    path_set.all_paths.append(path)

        # Update metrics
        path_set.total_paths = len(path_set.all_paths)

        # Organize by severity
        path_set.paths_by_severity = self._organize_by_severity(path_set.all_paths)

        # Find highest impact and easiest
        path_set.highest_impact_path = self._find_highest_impact(path_set.all_paths)
        path_set.easiest_path = self._find_easiest(path_set.all_paths)

        return path_set

    def _synthesize_from_chain(
        self,
        chain: "AttackChain",
        reasoning: "ReasoningResult",
    ) -> Optional[AttackPath]:
        """Synthesize attack path from attack chain."""
        steps = []

        # Build steps from chain functions
        for i, fn_id in enumerate(chain.functions):
            step_type = self._infer_step_type(i, len(chain.functions), chain)

            step = AttackStep(
                step_number=i + 1,
                description=f"Call {fn_id}",
                function_called=fn_id,
                transaction_type=step_type,
                requires_setup=(i == 0 and step_type == "setup"),
                code_snippet=f"target.{fn_id}()",
            )
            steps.append(step)

        # Determine complexity
        complexity = self._estimate_complexity(len(steps), chain.feasibility)

        # Determine impact
        impact = self._estimate_impact(chain.impact)

        return AttackPath(
            id=chain.id,
            name=f"Attack via {chain.entry_point}",
            entry_point=chain.entry_point,
            steps=steps,
            exit_point=chain.exit_point,
            complexity=complexity,
            estimated_impact=impact,
            total_steps=len(steps),
            feasibility_score=chain.feasibility,
            poc_code=self._generate_poc_from_steps(steps),
            vulnerability_ids=chain.pattern_ids,
            causal_chains=[],
        )

    def _synthesize_from_candidate(
        self,
        candidate: str,
        reasoning: "ReasoningResult",
        causal_analyses: Optional[List["CausalAnalysis"]],
    ) -> Optional[AttackPath]:
        """Synthesize attack path from vulnerability candidate."""
        # Find causal analysis for this candidate
        causal = None
        if causal_analyses:
            causal = next(
                (ca for ca in causal_analyses
                 if ca.causal_graph.focal_node_id == candidate),
                None
            )

        # Build basic attack path
        steps = [
            AttackStep(
                step_number=1,
                description=f"Call vulnerable function {candidate}",
                function_called=candidate,
                transaction_type="exploit",
                code_snippet=f"target.{candidate}()",
            )
        ]

        # Add setup steps if causal analysis available
        if causal and causal.root_causes:
            setup_step = AttackStep(
                step_number=0,
                description="Setup attack conditions",
                function_called="setup",
                transaction_type="setup",
                requires_setup=True,
                setup_description="; ".join([rc.description for rc in causal.root_causes[:2]]),
            )
            steps.insert(0, setup_step)
            # Renumber
            for i, step in enumerate(steps):
                step.step_number = i + 1

        return AttackPath(
            id=f"path_{candidate}",
            name=f"Direct attack on {candidate}",
            entry_point=candidate,
            steps=steps,
            exit_point=candidate,
            complexity=AttackComplexity.LOW,
            estimated_impact=AttackImpact.MEDIUM,
            total_steps=len(steps),
            feasibility_score=0.7,
            poc_code=self._generate_poc_from_steps(steps),
            vulnerability_ids=[candidate],
            causal_chains=[rc.id for rc in causal.root_causes] if causal else [],
        )

    def _infer_step_type(
        self,
        step_index: int,
        total_steps: int,
        chain: "AttackChain",
    ) -> str:
        """Infer whether step is setup, exploit, or extract."""
        if step_index == 0:
            return "setup"
        elif step_index == total_steps - 1:
            return "exploit"
        else:
            return "intermediate"

    def _estimate_complexity(
        self,
        num_steps: int,
        feasibility: float,
    ) -> AttackComplexity:
        """Estimate attack complexity from steps and feasibility."""
        # More steps = higher complexity
        # Lower feasibility = higher complexity

        if num_steps == 1 and feasibility > 0.9:
            return AttackComplexity.TRIVIAL
        elif num_steps <= 2 and feasibility > 0.7:
            return AttackComplexity.LOW
        elif num_steps <= 4 and feasibility > 0.5:
            return AttackComplexity.MEDIUM
        elif num_steps <= 6 and feasibility > 0.3:
            return AttackComplexity.HIGH
        else:
            return AttackComplexity.VERY_HIGH

    def _estimate_impact(self, impact_str: str) -> AttackImpact:
        """Convert impact string to enum."""
        impact_map = {
            "negligible": AttackImpact.NEGLIGIBLE,
            "low": AttackImpact.LOW,
            "medium": AttackImpact.MEDIUM,
            "high": AttackImpact.HIGH,
            "critical": AttackImpact.CRITICAL,
        }
        return impact_map.get(impact_str.lower(), AttackImpact.MEDIUM)

    def _generate_poc_from_steps(self, steps: List[AttackStep]) -> str:
        """Generate PoC pseudocode from attack steps."""
        lines = ["// Attack Proof of Concept\n"]

        for step in steps:
            lines.append(f"// Step {step.step_number}: {step.description}")

            if step.requires_setup and step.setup_description:
                lines.append(f"// Setup: {step.setup_description}")

            if step.code_snippet:
                lines.append(step.code_snippet)

            if step.state_changes:
                lines.append(f"// State changes: {', '.join(step.state_changes)}")

            lines.append("")  # Blank line between steps

        return "\n".join(lines)

    def _organize_by_severity(
        self,
        paths: List[AttackPath],
    ) -> Dict[str, List[AttackPath]]:
        """Organize paths by impact severity."""
        by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "negligible": [],
        }

        for path in paths:
            by_severity[path.estimated_impact.value].append(path)

        return by_severity

    def _find_highest_impact(self, paths: List[AttackPath]) -> Optional[str]:
        """Find path with highest impact."""
        if not paths:
            return None

        # Sort by impact (critical > high > medium > low > negligible)
        impact_order = {
            AttackImpact.CRITICAL: 5,
            AttackImpact.HIGH: 4,
            AttackImpact.MEDIUM: 3,
            AttackImpact.LOW: 2,
            AttackImpact.NEGLIGIBLE: 1,
        }

        sorted_paths = sorted(
            paths,
            key=lambda p: impact_order.get(p.estimated_impact, 0),
            reverse=True
        )

        return sorted_paths[0].id if sorted_paths else None

    def _find_easiest(self, paths: List[AttackPath]) -> Optional[str]:
        """Find path with lowest complexity."""
        if not paths:
            return None

        # Sort by complexity (trivial < low < medium < high < very_high)
        complexity_order = {
            AttackComplexity.TRIVIAL: 1,
            AttackComplexity.LOW: 2,
            AttackComplexity.MEDIUM: 3,
            AttackComplexity.HIGH: 4,
            AttackComplexity.VERY_HIGH: 5,
        }

        sorted_paths = sorted(
            paths,
            key=lambda p: (
                complexity_order.get(p.complexity, 10),
                -p.feasibility_score  # Higher feasibility is easier
            )
        )

        return sorted_paths[0].id if sorted_paths else None

    def generate_report(self, path_set: AttackPathSet) -> str:
        """Generate comprehensive attack path report."""
        lines = ["# Attack Path Analysis Report\n"]

        lines.append(f"**Target Contract**: {path_set.target_contract}")
        lines.append(f"**Total Paths Found**: {path_set.total_paths}")
        lines.append("")

        # Summary by severity
        lines.append("## Attack Paths by Severity\n")
        for severity in ["critical", "high", "medium", "low", "negligible"]:
            count = len(path_set.paths_by_severity.get(severity, []))
            if count > 0:
                lines.append(f"- **{severity.upper()}**: {count} path(s)")
        lines.append("")

        # Highest impact path
        if path_set.highest_impact_path:
            path = next(
                (p for p in path_set.all_paths if p.id == path_set.highest_impact_path),
                None
            )
            if path:
                lines.append("## Highest Impact Attack\n")
                lines.append(f"**Path**: {path.name}")
                lines.append(f"**Impact**: {path.estimated_impact.value}")
                lines.append(f"**Complexity**: {path.complexity.value}")
                lines.append(f"**Steps**: {path.total_steps}")
                lines.append("")

        # Easiest path
        if path_set.easiest_path:
            path = next(
                (p for p in path_set.all_paths if p.id == path_set.easiest_path),
                None
            )
            if path:
                lines.append("## Easiest Attack\n")
                lines.append(f"**Path**: {path.name}")
                lines.append(f"**Complexity**: {path.complexity.value}")
                lines.append(f"**Feasibility**: {path.feasibility_score:.0%}")
                lines.append(f"**Steps**: {path.total_steps}")
                lines.append("")

        # All paths
        lines.append("## All Attack Paths\n")
        for i, path in enumerate(path_set.all_paths, 1):
            lines.append(f"### {i}. {path.name}")
            lines.append(f"- **Entry Point**: {path.entry_point}")
            lines.append(f"- **Exit Point**: {path.exit_point}")
            lines.append(f"- **Complexity**: {path.complexity.value}")
            lines.append(f"- **Impact**: {path.estimated_impact.value}")
            lines.append(f"- **Feasibility**: {path.feasibility_score:.0%}")
            lines.append(f"- **Total Steps**: {path.total_steps}")

            if path.poc_code:
                lines.append(f"\n**PoC**:")
                lines.append(f"```solidity")
                lines.append(path.poc_code)
                lines.append(f"```")

            lines.append("")

        return "\n".join(lines)

    def explain_attack_path(self, path: AttackPath) -> str:
        """Generate detailed explanation of attack path."""
        lines = [f"# Attack Path: {path.name}\n"]

        lines.append("## Overview")
        lines.append(f"- **ID**: {path.id}")
        lines.append(f"- **Complexity**: {path.complexity.value}")
        lines.append(f"- **Estimated Impact**: {path.estimated_impact.value}")
        lines.append(f"- **Feasibility**: {path.feasibility_score:.0%}")
        lines.append(f"- **Total Steps**: {path.total_steps}")
        lines.append("")

        lines.append("## Attack Flow")
        lines.append(f"**Entry Point**: `{path.entry_point}`")
        lines.append(f"**Exit Point**: `{path.exit_point}`")
        lines.append("")

        lines.append("## Step-by-Step Breakdown\n")
        for step in path.steps:
            lines.append(f"### Step {step.step_number}: {step.description}")
            lines.append(f"- **Type**: {step.transaction_type}")
            lines.append(f"- **Function**: `{step.function_called}`")

            if step.requires_setup:
                lines.append(f"- **Setup Required**: {step.setup_description or 'Yes'}")

            if step.preconditions:
                lines.append(f"- **Preconditions**: {', '.join(step.preconditions)}")

            if step.state_changes:
                lines.append(f"- **State Changes**: {', '.join(step.state_changes)}")

            if step.code_snippet:
                lines.append(f"\n```solidity\n{step.code_snippet}\n```")

            lines.append("")

        if path.required_conditions:
            lines.append("## Required Conditions\n")
            for condition in path.required_conditions:
                lines.append(f"- {condition}")
            lines.append("")

        if path.attacker_capabilities:
            lines.append("## Attacker Capabilities Needed\n")
            for capability in path.attacker_capabilities:
                lines.append(f"- {capability}")
            lines.append("")

        if path.poc_code:
            lines.append("## Proof of Concept\n")
            lines.append("```solidity")
            lines.append(path.poc_code)
            lines.append("```")
            lines.append("")

        if path.exploit_description:
            lines.append("## Exploit Description\n")
            lines.append(path.exploit_description)
            lines.append("")

        return "\n".join(lines)
