"""Phase 7: Execution Path Analysis.

This module provides execution path enumeration and analysis for multi-step
vulnerability detection. It enables detection of complex attack scenarios
that span multiple function calls.

Key Concepts:
- ExecutionPath: A sequence of function calls with state tracking
- PathStep: A single step in an execution path
- Invariant: A property that should hold throughout execution
- AttackScenario: A generated attack hypothesis based on path analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum


class InvariantType(Enum):
    """Types of invariants that can be tracked."""
    BALANCE_CONSERVATION = "balance_conservation"
    ACCESS_CONTROL = "access_control"
    REENTRANCY_GUARD = "reentrancy_guard"
    STATE_CONSISTENCY = "state_consistency"
    OWNERSHIP = "ownership"
    PAUSABLE = "pausable"


@dataclass
class PathStep:
    """A single step in an execution path.

    Represents a function call with its operations and state changes.
    """
    function_id: str
    function_label: str
    operations: List[str] = field(default_factory=list)
    state_reads: Dict[str, Any] = field(default_factory=dict)
    state_writes: Dict[str, Any] = field(default_factory=dict)
    external_calls: List[str] = field(default_factory=list)
    order: int = 0
    guards_passed: List[str] = field(default_factory=list)
    risk_contribution: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "function_id": self.function_id,
            "function_label": self.function_label,
            "operations": self.operations,
            "state_reads": self.state_reads,
            "state_writes": self.state_writes,
            "external_calls": self.external_calls,
            "order": self.order,
            "guards_passed": self.guards_passed,
            "risk_contribution": self.risk_contribution,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PathStep":
        """Deserialize from dictionary."""
        return PathStep(
            function_id=str(data.get("function_id", "")),
            function_label=str(data.get("function_label", "")),
            operations=list(data.get("operations", [])),
            state_reads=dict(data.get("state_reads", {})),
            state_writes=dict(data.get("state_writes", {})),
            external_calls=list(data.get("external_calls", [])),
            order=int(data.get("order", 0)),
            guards_passed=list(data.get("guards_passed", [])),
            risk_contribution=float(data.get("risk_contribution", 0.0)),
        )


@dataclass
class Invariant:
    """An invariant that should hold during execution.

    Invariants represent properties that should be maintained
    across function calls (e.g., balance conservation).
    """
    id: str
    type: InvariantType
    description: str
    check: Callable[[Dict[str, Any]], bool] = field(default=lambda s: True)
    variables_involved: List[str] = field(default_factory=list)

    def holds(self, state: Dict[str, Any]) -> bool:
        """Check if the invariant holds for the given state."""
        try:
            return self.check(state)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (without check function)."""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "variables_involved": self.variables_involved,
        }


@dataclass
class ExecutionPath:
    """An execution path through the contract.

    Represents a sequence of function calls with state tracking,
    enabling detection of multi-step vulnerabilities.
    """
    id: str
    entry_point: str
    steps: List[PathStep] = field(default_factory=list)
    state_preconditions: Dict[str, Any] = field(default_factory=dict)
    state_postconditions: Dict[str, Any] = field(default_factory=dict)
    invariants_violated: List[str] = field(default_factory=list)
    attack_potential: float = 0.0
    path_type: str = "normal"  # "normal", "attack", "privilege_escalation"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "entry_point": self.entry_point,
            "steps": [s.to_dict() for s in self.steps],
            "state_preconditions": self.state_preconditions,
            "state_postconditions": self.state_postconditions,
            "invariants_violated": self.invariants_violated,
            "attack_potential": self.attack_potential,
            "path_type": self.path_type,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ExecutionPath":
        """Deserialize from dictionary."""
        return ExecutionPath(
            id=str(data.get("id", "")),
            entry_point=str(data.get("entry_point", "")),
            steps=[PathStep.from_dict(s) for s in data.get("steps", [])],
            state_preconditions=dict(data.get("state_preconditions", {})),
            state_postconditions=dict(data.get("state_postconditions", {})),
            invariants_violated=list(data.get("invariants_violated", [])),
            attack_potential=float(data.get("attack_potential", 0.0)),
            path_type=str(data.get("path_type", "normal")),
        )

    def get_all_operations(self) -> List[str]:
        """Get all operations across all steps."""
        ops = []
        for step in self.steps:
            ops.extend(step.operations)
        return ops

    def has_external_call_before_state_update(self) -> bool:
        """Check for CEI violation pattern in path."""
        saw_external_call = False
        for step in self.steps:
            if step.external_calls:
                saw_external_call = True
            if saw_external_call and step.state_writes:
                return True
        return False

    def involves_value_movement(self) -> bool:
        """Check if path involves value movement operations."""
        value_ops = {"TRANSFERS_VALUE_OUT", "RECEIVES_VALUE_IN", "WRITES_USER_BALANCE"}
        for step in self.steps:
            if any(op in value_ops for op in step.operations):
                return True
        return False

    def involves_oracle(self) -> bool:
        """Check if path involves oracle reads."""
        for step in self.steps:
            if "READS_ORACLE" in step.operations:
                return True
        return False

    def compute_cumulative_risk(self) -> float:
        """Compute cumulative risk score for the path."""
        base_risk = sum(step.risk_contribution for step in self.steps)

        # Apply multipliers for dangerous patterns
        multiplier = 1.0
        if self.has_external_call_before_state_update():
            multiplier *= 1.5
        if self.involves_value_movement():
            multiplier *= 1.3
        if len(self.invariants_violated) > 0:
            multiplier *= 1.0 + (0.2 * len(self.invariants_violated))

        return min(base_risk * multiplier, 10.0)


@dataclass
class AttackScenario:
    """A generated attack scenario based on path analysis.

    Represents a hypothesis about how a vulnerability could be exploited.
    """
    id: str
    type: str  # "reentrancy", "flash_loan", "privilege_escalation", "oracle_manipulation"
    path: ExecutionPath
    description: str
    required_conditions: List[str] = field(default_factory=list)
    impact: str = "unknown"  # "low", "medium", "high", "critical"
    likelihood: str = "unknown"  # "low", "medium", "high"
    recommended_fix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "path": self.path.to_dict(),
            "description": self.description,
            "required_conditions": self.required_conditions,
            "impact": self.impact,
            "likelihood": self.likelihood,
            "recommended_fix": self.recommended_fix,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AttackScenario":
        """Deserialize from dictionary."""
        return AttackScenario(
            id=str(data.get("id", "")),
            type=str(data.get("type", "")),
            path=ExecutionPath.from_dict(data.get("path", {})),
            description=str(data.get("description", "")),
            required_conditions=list(data.get("required_conditions", [])),
            impact=str(data.get("impact", "unknown")),
            likelihood=str(data.get("likelihood", "unknown")),
            recommended_fix=str(data.get("recommended_fix", "")),
        )


class PathEnumerator:
    """Enumerates execution paths through a contract.

    Uses BFS to explore paths from entry points, tracking state changes
    and identifying potential attack paths.
    """

    def __init__(self, graph: Any, max_depth: int = 5, max_paths: int = 100):
        """Initialize the path enumerator.

        Args:
            graph: KnowledgeGraph instance
            max_depth: Maximum path depth to explore
            max_paths: Maximum number of paths to generate
        """
        self.graph = graph
        self.max_depth = max_depth
        self.max_paths = max_paths

    def get_entry_points(self) -> List[str]:
        """Get all entry point function IDs."""
        entry_points = []
        for node in self.graph.nodes.values():
            if node.type == "Function":
                visibility = node.properties.get("visibility", "")
                if visibility in ["public", "external"]:
                    # Exclude view/pure functions as entry points
                    if not node.properties.get("is_view", False):
                        if node.properties.get("state_mutability") not in ["view", "pure"]:
                            entry_points.append(node.id)
        return entry_points

    def get_callable_functions(self, from_function: str, state: Dict[str, Any]) -> List[str]:
        """Get functions callable from a given function.

        Args:
            from_function: Source function ID
            state: Current state (for guard evaluation)

        Returns:
            List of callable function IDs
        """
        callable_fns = []

        # Find CALLS edges from this function
        for edge in self.graph.edges.values():
            if edge.source == from_function and edge.type == "CALLS":
                target_node = self.graph.nodes.get(edge.target)
                if target_node and target_node.type == "Function":
                    callable_fns.append(edge.target)

        return callable_fns

    def create_step_from_function(self, fn_id: str, order: int) -> PathStep:
        """Create a PathStep from a function node.

        Args:
            fn_id: Function node ID
            order: Step order in path

        Returns:
            PathStep instance
        """
        node = self.graph.nodes.get(fn_id)
        if not node:
            return PathStep(function_id=fn_id, function_label="unknown", order=order)

        props = node.properties

        # Extract operations
        operations = props.get("semantic_ops", [])

        # Extract state reads/writes
        state_reads = {}
        for var in props.get("state_variables_read_names", []):
            state_reads[var] = "read"

        state_writes = {}
        for var in props.get("state_variables_written_names", []):
            state_writes[var] = "written"

        # Extract external calls
        external_calls = []
        if props.get("has_external_calls") or props.get("has_low_level_calls"):
            external_calls.append("external_call")
        if props.get("uses_delegatecall"):
            external_calls.append("delegatecall")

        # Extract guards
        guards = props.get("modifiers", [])

        # Compute risk contribution
        risk = 0.0
        if props.get("uses_delegatecall"):
            risk += 3.0
        if props.get("state_write_after_external_call"):
            risk += 2.0
        if props.get("has_external_calls") and not props.get("has_reentrancy_guard"):
            risk += 1.5
        if props.get("writes_privileged_state"):
            risk += 1.0

        return PathStep(
            function_id=fn_id,
            function_label=node.label,
            operations=operations,
            state_reads=state_reads,
            state_writes=state_writes,
            external_calls=external_calls,
            order=order,
            guards_passed=guards,
            risk_contribution=risk,
        )

    def enumerate_paths(
        self,
        entry_points: Optional[List[str]] = None,
        depth: Optional[int] = None
    ) -> List[ExecutionPath]:
        """Enumerate execution paths from entry points.

        Args:
            entry_points: Starting functions (default: all public/external)
            depth: Maximum path depth (default: self.max_depth)

        Returns:
            List of ExecutionPath instances
        """
        if entry_points is None:
            entry_points = self.get_entry_points()
        if depth is None:
            depth = self.max_depth

        paths = []
        path_count = 0

        for entry in entry_points:
            if path_count >= self.max_paths:
                break

            # BFS queue: (current_fn, path_so_far, state)
            queue: List[Tuple[str, List[str], Dict[str, Any]]] = [
                (entry, [entry], {})
            ]
            visited_paths: Set[str] = set()

            while queue and path_count < self.max_paths:
                current, path_ids, state = queue.pop(0)

                # Create path hash to avoid duplicates
                path_hash = "->".join(path_ids)
                if path_hash in visited_paths:
                    continue
                visited_paths.add(path_hash)

                # Create execution path
                if len(path_ids) >= 2:  # At least 2 steps for a meaningful path
                    steps = [
                        self.create_step_from_function(fn_id, i)
                        for i, fn_id in enumerate(path_ids)
                    ]

                    exec_path = ExecutionPath(
                        id=f"path:{path_hash}",
                        entry_point=entry,
                        steps=steps,
                        state_preconditions={"initial": True},
                        state_postconditions=self._compute_postconditions(steps),
                    )

                    # Compute attack potential
                    exec_path.attack_potential = exec_path.compute_cumulative_risk()

                    # Determine path type
                    if exec_path.attack_potential >= 5.0:
                        exec_path.path_type = "attack"
                    elif self._involves_privilege_change(steps):
                        exec_path.path_type = "privilege_escalation"

                    paths.append(exec_path)
                    path_count += 1

                # Explore further if not at max depth
                if len(path_ids) < depth:
                    for next_fn in self.get_callable_functions(current, state):
                        if next_fn not in path_ids:  # Avoid cycles
                            new_state = self._apply_state_changes(state, current)
                            queue.append((next_fn, path_ids + [next_fn], new_state))

        return paths

    def _compute_postconditions(self, steps: List[PathStep]) -> Dict[str, Any]:
        """Compute postconditions from path steps."""
        postconditions = {}
        for step in steps:
            postconditions.update(step.state_writes)
        return postconditions

    def _apply_state_changes(self, state: Dict[str, Any], fn_id: str) -> Dict[str, Any]:
        """Apply state changes from a function."""
        new_state = state.copy()
        node = self.graph.nodes.get(fn_id)
        if node:
            for var in node.properties.get("state_variables_written_names", []):
                new_state[var] = "modified"
        return new_state

    def _involves_privilege_change(self, steps: List[PathStep]) -> bool:
        """Check if path involves privilege changes."""
        privilege_ops = {"MODIFIES_OWNER", "MODIFIES_ROLES"}
        for step in steps:
            if any(op in privilege_ops for op in step.operations):
                return True
        return False


def check_path_invariants(
    path: ExecutionPath,
    invariants: List[Invariant]
) -> List[str]:
    """Check which invariants are violated along a path.

    Args:
        path: ExecutionPath to check
        invariants: List of Invariant instances

    Returns:
        List of violated invariant IDs
    """
    violations = []
    state = path.state_preconditions.copy()

    for step in path.steps:
        # Apply state changes
        state.update(step.state_writes)

        # Check invariants
        for inv in invariants:
            if not inv.holds(state):
                if inv.id not in violations:
                    violations.append(inv.id)

    return violations


def generate_attack_scenarios(path: ExecutionPath) -> List[AttackScenario]:
    """Generate attack scenarios from an execution path.

    Analyzes the path for vulnerability patterns and generates
    hypothetical attack scenarios.

    Args:
        path: ExecutionPath to analyze

    Returns:
        List of AttackScenario instances
    """
    scenarios = []

    # Check for reentrancy pattern
    if path.has_external_call_before_state_update():
        has_guard = any(
            "nonReentrant" in step.guards_passed or
            "ReentrancyGuard" in step.guards_passed
            for step in path.steps
        )
        if not has_guard:
            scenarios.append(AttackScenario(
                id=f"scenario:reentrancy:{path.id}",
                type="reentrancy",
                path=path,
                description="Re-enter via external call to drain funds or manipulate state",
                required_conditions=["No reentrancy guard", "External call before state update"],
                impact="high" if path.involves_value_movement() else "medium",
                likelihood="high",
                recommended_fix="Add nonReentrant modifier or follow CEI pattern",
            ))

    # Check for flash loan pattern (oracle + swap/value movement)
    if path.involves_oracle() and path.involves_value_movement():
        scenarios.append(AttackScenario(
            id=f"scenario:flash_loan:{path.id}",
            type="flash_loan",
            path=path,
            description="Flash loan to manipulate oracle price then exploit",
            required_conditions=["Manipulable oracle", "Value movement based on oracle"],
            impact="critical",
            likelihood="medium",
            recommended_fix="Use TWAP oracle or add manipulation resistance",
        ))

    # Check for privilege escalation
    privilege_ops = {"MODIFIES_OWNER", "MODIFIES_ROLES"}
    for step in path.steps:
        if any(op in privilege_ops for op in step.operations):
            if not step.guards_passed:
                scenarios.append(AttackScenario(
                    id=f"scenario:privilege:{path.id}",
                    type="privilege_escalation",
                    path=path,
                    description="Gain elevated privileges through unprotected function",
                    required_conditions=["Missing access control on privilege function"],
                    impact="critical",
                    likelihood="high",
                    recommended_fix="Add access control modifier (onlyOwner, onlyRole)",
                ))
                break

    # Check for state manipulation through external calls
    has_external = any(step.external_calls for step in path.steps)
    has_state_writes = any(step.state_writes for step in path.steps)
    if has_external and has_state_writes and path.attack_potential >= 4.0:
        # Only add if not already covered by reentrancy
        if not any(s.type == "reentrancy" for s in scenarios):
            scenarios.append(AttackScenario(
                id=f"scenario:state_manipulation:{path.id}",
                type="state_manipulation",
                path=path,
                description="Manipulate contract state through external call interaction",
                required_conditions=["External call with state modification"],
                impact="medium",
                likelihood="medium",
                recommended_fix="Review external call interactions and state dependencies",
            ))

    return scenarios


def enumerate_attack_paths(graph: Any, max_depth: int = 5) -> List[ExecutionPath]:
    """Enumerate paths with high attack potential.

    Args:
        graph: KnowledgeGraph instance
        max_depth: Maximum path depth

    Returns:
        List of ExecutionPath instances with attack_potential >= 3.0
    """
    enumerator = PathEnumerator(graph, max_depth=max_depth, max_paths=200)
    all_paths = enumerator.enumerate_paths()

    # Filter to attack paths
    attack_paths = [p for p in all_paths if p.attack_potential >= 3.0]

    # Sort by attack potential (highest first)
    attack_paths.sort(key=lambda p: p.attack_potential, reverse=True)

    return attack_paths


def get_path_analysis_summary(graph: Any) -> Dict[str, Any]:
    """Get a summary of path analysis for the graph.

    Args:
        graph: KnowledgeGraph instance

    Returns:
        Dictionary with path analysis summary
    """
    enumerator = PathEnumerator(graph, max_depth=4, max_paths=50)
    paths = enumerator.enumerate_paths()

    # Categorize paths
    attack_paths = [p for p in paths if p.path_type == "attack"]
    privilege_paths = [p for p in paths if p.path_type == "privilege_escalation"]
    normal_paths = [p for p in paths if p.path_type == "normal"]

    # Generate scenarios for attack paths
    all_scenarios = []
    for path in attack_paths[:10]:  # Limit scenario generation
        scenarios = generate_attack_scenarios(path)
        all_scenarios.extend(scenarios)

    # Count scenario types
    scenario_types: Dict[str, int] = {}
    for s in all_scenarios:
        scenario_types[s.type] = scenario_types.get(s.type, 0) + 1

    return {
        "total_paths": len(paths),
        "attack_paths": len(attack_paths),
        "privilege_escalation_paths": len(privilege_paths),
        "normal_paths": len(normal_paths),
        "total_scenarios": len(all_scenarios),
        "scenario_types": scenario_types,
        "highest_risk_path": max(paths, key=lambda p: p.attack_potential).to_dict() if paths else None,
        "entry_points": enumerator.get_entry_points(),
    }
