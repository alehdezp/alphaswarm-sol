"""Phase 18: Attack Path Synthesis.

This module provides functionality for synthesizing attack paths
from knowledge graphs, identifying guard bypasses, and generating
human-readable attack descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge


class AttackDifficulty(str, Enum):
    """Difficulty level for executing an attack."""
    TRIVIAL = "trivial"           # No guards, direct exploitation
    EASY = "easy"                 # Simple bypass needed
    MODERATE = "moderate"         # Multiple conditions to satisfy
    HARD = "hard"                 # Complex bypass chain
    VERY_HARD = "very_hard"       # Multiple sophisticated bypasses


class ImpactLevel(str, Enum):
    """Impact level of a successful attack."""
    LOW = "low"                   # Minor inconvenience
    MEDIUM = "medium"             # Some funds or data at risk
    HIGH = "high"                 # Significant funds at risk
    CRITICAL = "critical"         # Total loss of funds or control


class BypassType(str, Enum):
    """Types of guard bypasses."""
    FRONTRUN = "frontrun"         # Front-run a transaction
    FLASHLOAN = "flashloan"       # Use flash loan
    REENTRANCY = "reentrancy"     # Reentrant call
    PRICE_MANIPULATION = "price_manipulation"  # Manipulate oracle
    SIGNATURE_REPLAY = "signature_replay"  # Replay signature
    TIMING = "timing"             # Timing-based bypass
    PERMISSION_ESCALATION = "permission_escalation"  # Gain permissions
    NONE = "none"                 # No bypass possible/needed


@dataclass
class GuardBypass:
    """Represents a method to bypass a guard condition.

    Attributes:
        guard: The guard being bypassed
        bypass_type: Type of bypass technique
        description: Human-readable description
        prerequisites: Conditions needed for bypass
        difficulty: How hard is this bypass
    """
    guard: str
    bypass_type: BypassType
    description: str = ""
    prerequisites: List[str] = field(default_factory=list)
    difficulty: AttackDifficulty = AttackDifficulty.MODERATE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "guard": self.guard,
            "bypass_type": self.bypass_type.value,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "difficulty": self.difficulty.value,
        }


@dataclass
class AttackStep:
    """A single step in an attack path.

    Attributes:
        function_id: ID of the function in this step
        function_name: Name of the function
        action: What happens in this step
        preconditions: What must be true before this step
        postconditions: What is true after this step
    """
    function_id: str
    function_name: str
    action: str = ""
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "function_id": self.function_id,
            "function_name": self.function_name,
            "action": self.action,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
        }


@dataclass
class AttackPath:
    """A complete attack path from entry to sink.

    Attributes:
        id: Unique identifier
        entry: Entry point function
        sink: Value sink (where damage occurs)
        steps: Ordered steps in the attack
        required_bypasses: Guards that must be bypassed
        difficulty: Overall attack difficulty
        impact: Impact if successful
        attack_type: Type of attack (reentrancy, access control, etc.)
        description: Human-readable description
    """
    id: str
    entry: str
    sink: str
    steps: List[AttackStep] = field(default_factory=list)
    required_bypasses: List[GuardBypass] = field(default_factory=list)
    difficulty: AttackDifficulty = AttackDifficulty.MODERATE
    impact: ImpactLevel = ImpactLevel.MEDIUM
    attack_type: str = ""
    description: str = ""

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def bypass_count(self) -> int:
        return len(self.required_bypasses)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entry": self.entry,
            "sink": self.sink,
            "steps": [s.to_dict() for s in self.steps],
            "required_bypasses": [b.to_dict() for b in self.required_bypasses],
            "difficulty": self.difficulty.value,
            "impact": self.impact.value,
            "attack_type": self.attack_type,
            "description": self.description,
            "step_count": self.step_count,
            "bypass_count": self.bypass_count,
        }


@dataclass
class AttackDescription:
    """Human-readable attack description.

    Attributes:
        title: Attack title
        summary: Brief summary
        steps: Numbered attack steps
        prerequisites: What attacker needs
        impact: Expected impact
        mitigation: How to fix
    """
    title: str
    summary: str = ""
    steps: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    impact: str = ""
    mitigation: str = ""

    def to_markdown(self) -> str:
        """Generate markdown description."""
        lines = [f"## {self.title}", ""]

        if self.summary:
            lines.append(f"**Summary:** {self.summary}")
            lines.append("")

        if self.prerequisites:
            lines.append("### Prerequisites")
            for prereq in self.prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")

        if self.steps:
            lines.append("### Attack Steps")
            for i, step in enumerate(self.steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if self.impact:
            lines.append(f"**Impact:** {self.impact}")
            lines.append("")

        if self.mitigation:
            lines.append("### Mitigation")
            lines.append(self.mitigation)

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "summary": self.summary,
            "steps": self.steps,
            "prerequisites": self.prerequisites,
            "impact": self.impact,
            "mitigation": self.mitigation,
        }


class AttackPathSynthesizer:
    """Synthesizes attack paths from knowledge graphs.

    Finds paths from entry points to value sinks, identifies
    required guard bypasses, and estimates attack difficulty.
    """

    # Value sink operations
    VALUE_SINK_OPS = {
        "TRANSFERS_VALUE_OUT",
        "CALLS_UNTRUSTED",
        "WRITES_USER_BALANCE",
        "MODIFIES_OWNER",
        "MODIFIES_ROLES",
    }

    # Guard bypass strategies
    BYPASS_STRATEGIES: Dict[str, BypassType] = {
        "has_reentrancy_guard": BypassType.REENTRANCY,
        "has_access_gate": BypassType.PERMISSION_ESCALATION,
        "has_staleness_check": BypassType.PRICE_MANIPULATION,
        "checks_zero_address": BypassType.SIGNATURE_REPLAY,
        "has_deadline_check": BypassType.TIMING,
    }

    def __init__(self, graph: KnowledgeGraph):
        """Initialize synthesizer with knowledge graph.

        Args:
            graph: Knowledge graph to analyze
        """
        self.graph = graph
        self._adjacency: Dict[str, List[str]] = {}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        """Build adjacency list from edges."""
        self._adjacency = {}

        for edge in self.graph.edges.values():
            if edge.source not in self._adjacency:
                self._adjacency[edge.source] = []
            self._adjacency[edge.source].append(edge.target)

    def synthesize(
        self,
        contract_id: Optional[str] = None,
        max_paths: int = 10,
        max_depth: int = 5,
    ) -> List[AttackPath]:
        """Synthesize attack paths.

        Args:
            contract_id: Optional contract to focus on
            max_paths: Maximum paths to return
            max_depth: Maximum path depth

        Returns:
            List of attack paths
        """
        # Get contract label if specified
        contract_label = None
        if contract_id:
            contract_node = self.graph.nodes.get(contract_id)
            if contract_node:
                contract_label = contract_node.label

        # Find entry points and value sinks
        entry_points = self._find_entry_points(contract_label)
        value_sinks = self._find_value_sinks(contract_label)

        paths: List[AttackPath] = []
        path_counter = 0

        for entry in entry_points:
            for sink in value_sinks:
                if entry.id == sink.id:
                    # Entry is also a sink - direct attack
                    path = self._create_direct_path(entry, path_counter)
                    if path:
                        paths.append(path)
                        path_counter += 1
                else:
                    # Find path between entry and sink
                    node_path = self._find_path(entry.id, sink.id, max_depth)
                    if node_path:
                        path = self._create_path(node_path, path_counter)
                        if path:
                            paths.append(path)
                            path_counter += 1

                if len(paths) >= max_paths:
                    break
            if len(paths) >= max_paths:
                break

        # Sort by impact and difficulty
        paths.sort(key=lambda p: (
            -self._impact_score(p.impact),
            self._difficulty_score(p.difficulty),
        ))

        return paths[:max_paths]

    def _find_entry_points(self, contract_label: Optional[str]) -> List[Node]:
        """Find public/external functions as entry points."""
        entries: List[Node] = []

        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            # Filter by contract
            if contract_label:
                if node.properties.get("contract_name") != contract_label:
                    continue

            # Check visibility
            visibility = node.properties.get("visibility", "")
            if visibility in ("public", "external"):
                entries.append(node)

        return entries

    def _find_value_sinks(self, contract_label: Optional[str]) -> List[Node]:
        """Find functions with value-affecting or vulnerable operations."""
        sinks: List[Node] = []

        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            # Filter by contract
            if contract_label:
                if node.properties.get("contract_name") != contract_label:
                    continue

            # Check for sink operations
            semantic_ops = node.properties.get("semantic_ops", []) or []
            if any(op in self.VALUE_SINK_OPS for op in semantic_ops):
                sinks.append(node)
                continue

            # Check properties that indicate value movement
            if (node.properties.get("transfers_value_out") or
                node.properties.get("calls_external") or
                node.properties.get("writes_privileged_state")):
                sinks.append(node)
                continue

            # Check for DoS vulnerabilities (unbounded loops)
            if node.properties.get("has_unbounded_loop"):
                sinks.append(node)
                continue

            # Check for signature vulnerabilities (ecrecover)
            if node.properties.get("uses_ecrecover"):
                sinks.append(node)
                continue

            # Check for reentrancy vulnerabilities
            if node.properties.get("state_write_after_external_call"):
                sinks.append(node)
                continue

        return sinks

    def _find_path(
        self,
        start: str,
        end: str,
        max_depth: int,
    ) -> Optional[List[str]]:
        """Find path between two nodes using BFS."""
        if start == end:
            return [start]

        visited: Set[str] = {start}
        queue: List[Tuple[str, List[str]]] = [(start, [start])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            neighbors = self._adjacency.get(current, [])
            for neighbor in neighbors:
                if neighbor == end:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def _create_direct_path(
        self,
        node: Node,
        path_id: int,
    ) -> Optional[AttackPath]:
        """Create attack path for direct vulnerability."""
        props = node.properties

        # Determine attack type
        attack_type = self._determine_attack_type(props)
        if not attack_type:
            return None

        # Get bypasses needed
        bypasses = self._find_bypasses(props)

        # Create step
        step = AttackStep(
            function_id=node.id,
            function_name=node.label,
            action=f"Call {node.label}() to trigger {attack_type}",
            preconditions=self._get_preconditions(props),
            postconditions=self._get_postconditions(props, attack_type),
        )

        # Estimate difficulty and impact
        difficulty = self._estimate_difficulty(bypasses, props)
        impact = self._estimate_impact(props)

        return AttackPath(
            id=f"path_{path_id}",
            entry=node.label,
            sink=node.label,
            steps=[step],
            required_bypasses=bypasses,
            difficulty=difficulty,
            impact=impact,
            attack_type=attack_type,
            description=self._generate_description(attack_type, node.label, bypasses),
        )

    def _create_path(
        self,
        node_ids: List[str],
        path_id: int,
    ) -> Optional[AttackPath]:
        """Create attack path from node sequence."""
        if not node_ids:
            return None

        steps: List[AttackStep] = []
        all_bypasses: List[GuardBypass] = []

        # Get all nodes
        nodes: List[Node] = []
        for node_id in node_ids:
            node = self.graph.nodes.get(node_id)
            if node and node.type == "Function":
                nodes.append(node)

        if not nodes:
            return None

        # Create steps
        for i, node in enumerate(nodes):
            is_entry = (i == 0)
            is_sink = (i == len(nodes) - 1)

            action = ""
            if is_entry:
                action = f"Enter via {node.label}()"
            elif is_sink:
                action = f"Exploit sink in {node.label}()"
            else:
                action = f"Traverse through {node.label}()"

            step = AttackStep(
                function_id=node.id,
                function_name=node.label,
                action=action,
                preconditions=self._get_preconditions(node.properties),
                postconditions=self._get_postconditions(node.properties, ""),
            )
            steps.append(step)

            # Collect bypasses
            bypasses = self._find_bypasses(node.properties)
            all_bypasses.extend(bypasses)

        # Entry and sink
        entry_name = nodes[0].label
        sink_name = nodes[-1].label
        sink_props = nodes[-1].properties

        # Determine attack type from sink
        attack_type = self._determine_attack_type(sink_props) or "unknown"

        # Deduplicate bypasses
        seen_guards: Set[str] = set()
        unique_bypasses: List[GuardBypass] = []
        for bypass in all_bypasses:
            if bypass.guard not in seen_guards:
                seen_guards.add(bypass.guard)
                unique_bypasses.append(bypass)

        # Estimate difficulty and impact
        difficulty = self._estimate_difficulty(unique_bypasses, sink_props)
        impact = self._estimate_impact(sink_props)

        return AttackPath(
            id=f"path_{path_id}",
            entry=entry_name,
            sink=sink_name,
            steps=steps,
            required_bypasses=unique_bypasses,
            difficulty=difficulty,
            impact=impact,
            attack_type=attack_type,
            description=self._generate_description(attack_type, sink_name, unique_bypasses),
        )

    def _determine_attack_type(self, props: Dict[str, Any]) -> Optional[str]:
        """Determine attack type from function properties."""
        # Reentrancy
        if props.get("state_write_after_external_call"):
            if not props.get("has_reentrancy_guard"):
                return "reentrancy"

        # Access control
        if props.get("writes_privileged_state"):
            if not props.get("has_access_gate"):
                return "unauthorized_access"

        # Oracle manipulation
        if props.get("reads_oracle_price"):
            if not props.get("has_staleness_check"):
                return "oracle_manipulation"

        # Slippage
        if props.get("swap_like"):
            if props.get("risk_missing_slippage_parameter"):
                return "slippage_exploitation"

        # DoS
        if props.get("has_unbounded_loop"):
            return "denial_of_service"

        # ecrecover
        if props.get("uses_ecrecover"):
            if not props.get("checks_zero_address"):
                return "signature_malleability"

        # General external call risk
        if props.get("calls_external") or props.get("transfers_value_out"):
            return "value_extraction"

        return None

    def _find_bypasses(self, props: Dict[str, Any]) -> List[GuardBypass]:
        """Find required guard bypasses for a function."""
        bypasses: List[GuardBypass] = []

        for guard_prop, bypass_type in self.BYPASS_STRATEGIES.items():
            if props.get(guard_prop):
                # Guard is present - need to bypass it
                bypass = GuardBypass(
                    guard=guard_prop,
                    bypass_type=bypass_type,
                    description=f"Bypass {guard_prop} via {bypass_type.value}",
                    prerequisites=self._bypass_prerequisites(bypass_type),
                    difficulty=self._bypass_difficulty(bypass_type),
                )
                bypasses.append(bypass)

        return bypasses

    def _bypass_prerequisites(self, bypass_type: BypassType) -> List[str]:
        """Get prerequisites for a bypass type."""
        prereqs: Dict[BypassType, List[str]] = {
            BypassType.FLASHLOAN: ["Flash loan liquidity available", "Repay within tx"],
            BypassType.REENTRANCY: ["Controllable callback", "State not locked"],
            BypassType.PRICE_MANIPULATION: ["Sufficient capital", "Manipulable oracle"],
            BypassType.FRONTRUN: ["Visible pending tx", "Higher gas price"],
            BypassType.TIMING: ["Block timestamp control", "Time window exists"],
            BypassType.PERMISSION_ESCALATION: ["Privilege path exists"],
            BypassType.SIGNATURE_REPLAY: ["Valid signature obtainable", "No nonce check"],
        }
        return prereqs.get(bypass_type, [])

    def _bypass_difficulty(self, bypass_type: BypassType) -> AttackDifficulty:
        """Get difficulty for a bypass type."""
        difficulties: Dict[BypassType, AttackDifficulty] = {
            BypassType.FLASHLOAN: AttackDifficulty.EASY,
            BypassType.REENTRANCY: AttackDifficulty.MODERATE,
            BypassType.PRICE_MANIPULATION: AttackDifficulty.HARD,
            BypassType.FRONTRUN: AttackDifficulty.EASY,
            BypassType.TIMING: AttackDifficulty.MODERATE,
            BypassType.PERMISSION_ESCALATION: AttackDifficulty.HARD,
            BypassType.SIGNATURE_REPLAY: AttackDifficulty.MODERATE,
            BypassType.NONE: AttackDifficulty.TRIVIAL,
        }
        return difficulties.get(bypass_type, AttackDifficulty.MODERATE)

    def _get_preconditions(self, props: Dict[str, Any]) -> List[str]:
        """Get preconditions from function properties."""
        preconditions: List[str] = []

        modifiers = props.get("modifiers", []) or []
        for mod in modifiers:
            preconditions.append(f"Must satisfy {mod}")

        if props.get("has_access_gate"):
            preconditions.append("Must have access permission")

        if props.get("requires_payment"):
            preconditions.append("Must send ETH value")

        return preconditions

    def _get_postconditions(
        self,
        props: Dict[str, Any],
        attack_type: str,
    ) -> List[str]:
        """Get postconditions from function properties."""
        postconditions: List[str] = []

        if props.get("writes_state"):
            postconditions.append("State modified")

        if props.get("transfers_value_out"):
            postconditions.append("Value transferred out")

        if props.get("writes_privileged_state"):
            postconditions.append("Privileged state modified")

        if attack_type == "reentrancy":
            postconditions.append("Re-entry possible before state update")

        return postconditions

    def _estimate_difficulty(
        self,
        bypasses: List[GuardBypass],
        props: Dict[str, Any],
    ) -> AttackDifficulty:
        """Estimate overall attack difficulty."""
        if not bypasses:
            # No guards to bypass
            if props.get("has_access_gate"):
                return AttackDifficulty.MODERATE
            return AttackDifficulty.TRIVIAL

        # Aggregate bypass difficulties
        max_difficulty = max(
            self._difficulty_score(b.difficulty) for b in bypasses
        )

        # More bypasses = harder
        if len(bypasses) > 2:
            max_difficulty = min(max_difficulty + 1, 4)

        difficulty_levels = list(AttackDifficulty)
        return difficulty_levels[min(max_difficulty, len(difficulty_levels) - 1)]

    def _estimate_impact(self, props: Dict[str, Any]) -> ImpactLevel:
        """Estimate impact of successful attack."""
        # Critical if can modify owner/roles
        if props.get("writes_privileged_state"):
            semantic_ops = props.get("semantic_ops", []) or []
            if any(op in ["MODIFIES_OWNER", "MODIFIES_ROLES"] for op in semantic_ops):
                return ImpactLevel.CRITICAL

        # High if transfers value
        if props.get("transfers_value_out") or props.get("uses_erc20_transfer"):
            return ImpactLevel.HIGH

        # Medium for state writes
        if props.get("writes_state"):
            return ImpactLevel.MEDIUM

        return ImpactLevel.LOW

    def _difficulty_score(self, difficulty: AttackDifficulty) -> int:
        """Convert difficulty to numeric score."""
        scores = {
            AttackDifficulty.TRIVIAL: 0,
            AttackDifficulty.EASY: 1,
            AttackDifficulty.MODERATE: 2,
            AttackDifficulty.HARD: 3,
            AttackDifficulty.VERY_HARD: 4,
        }
        return scores.get(difficulty, 2)

    def _impact_score(self, impact: ImpactLevel) -> int:
        """Convert impact to numeric score."""
        scores = {
            ImpactLevel.LOW: 1,
            ImpactLevel.MEDIUM: 2,
            ImpactLevel.HIGH: 3,
            ImpactLevel.CRITICAL: 4,
        }
        return scores.get(impact, 2)

    def _generate_description(
        self,
        attack_type: str,
        sink_name: str,
        bypasses: List[GuardBypass],
    ) -> str:
        """Generate human-readable attack description."""
        descriptions = {
            "reentrancy": f"Reentrant call to {sink_name} allows draining funds",
            "unauthorized_access": f"Missing access control on {sink_name} allows unauthorized state modification",
            "oracle_manipulation": f"Manipulate oracle to exploit {sink_name}",
            "slippage_exploitation": f"Sandwich attack on {sink_name} due to missing slippage protection",
            "denial_of_service": f"Unbounded loop in {sink_name} enables DoS",
            "signature_malleability": f"ecrecover in {sink_name} vulnerable to zero address",
            "value_extraction": f"Value extraction possible via {sink_name}",
        }

        desc = descriptions.get(attack_type, f"Exploit {sink_name}")

        if bypasses:
            bypass_list = ", ".join(b.bypass_type.value for b in bypasses)
            desc += f" (requires: {bypass_list})"

        return desc

    def generate_attack_description(self, path: AttackPath) -> AttackDescription:
        """Generate detailed attack description.

        Args:
            path: Attack path to describe

        Returns:
            Human-readable attack description
        """
        title = f"{path.attack_type.replace('_', ' ').title()} Attack via {path.entry}"

        summary = path.description

        # Generate step descriptions
        steps: List[str] = []
        for i, step in enumerate(path.steps):
            step_desc = step.action
            if step.preconditions:
                step_desc += f" (requires: {', '.join(step.preconditions)})"
            steps.append(step_desc)

        # Collect prerequisites from bypasses
        prerequisites: List[str] = []
        for bypass in path.required_bypasses:
            prerequisites.extend(bypass.prerequisites)

        # Impact description
        impact = f"{path.impact.value.upper()}: "
        if path.impact == ImpactLevel.CRITICAL:
            impact += "Complete loss of funds or control"
        elif path.impact == ImpactLevel.HIGH:
            impact += "Significant funds at risk"
        elif path.impact == ImpactLevel.MEDIUM:
            impact += "Partial funds or data at risk"
        else:
            impact += "Minor impact"

        # Mitigation based on attack type
        mitigations = {
            "reentrancy": "Add ReentrancyGuard or use CEI pattern",
            "unauthorized_access": "Add access control modifier (onlyOwner, onlyRole)",
            "oracle_manipulation": "Use TWAP oracle or add staleness checks",
            "slippage_exploitation": "Add slippage parameter and deadline check",
            "denial_of_service": "Add loop bounds or use pagination",
            "signature_malleability": "Check for zero address after ecrecover",
            "value_extraction": "Add access control and reentrancy protection",
        }
        mitigation = mitigations.get(path.attack_type, "Review and add appropriate guards")

        return AttackDescription(
            title=title,
            summary=summary,
            steps=steps,
            prerequisites=list(set(prerequisites)),  # Deduplicate
            impact=impact,
            mitigation=mitigation,
        )


def synthesize_attack_paths(
    graph: KnowledgeGraph,
    contract_id: Optional[str] = None,
    max_paths: int = 10,
) -> List[AttackPath]:
    """Synthesize attack paths from a knowledge graph.

    Convenience function for quick attack path synthesis.

    Args:
        graph: Knowledge graph to analyze
        contract_id: Optional contract to focus on
        max_paths: Maximum paths to return

    Returns:
        List of attack paths
    """
    synthesizer = AttackPathSynthesizer(graph)
    return synthesizer.synthesize(contract_id, max_paths)


__all__ = [
    "AttackDifficulty",
    "ImpactLevel",
    "BypassType",
    "GuardBypass",
    "AttackStep",
    "AttackPath",
    "AttackDescription",
    "AttackPathSynthesizer",
    "synthesize_attack_paths",
]
