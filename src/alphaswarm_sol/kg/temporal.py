"""Phase 16: Temporal Execution Layer.

This module provides functionality for tracking state transitions and
detecting time-dependent vulnerability windows in smart contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


class StateType(str, Enum):
    """Types of contract states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    PENDING = "pending"
    COMPLETED = "completed"
    EMERGENCY = "emergency"


class VulnerabilityWindow(str, Enum):
    """Types of vulnerability windows."""
    FLASH_LOAN = "flash_loan"          # Single transaction window
    MULTI_BLOCK = "multi_block"        # Spans multiple blocks
    TIMELOCK = "timelock"              # During timelock period
    INITIALIZATION = "initialization"   # During init phase
    MIGRATION = "migration"            # During upgrade/migration
    GOVERNANCE = "governance"          # During governance action
    ORACLE_UPDATE = "oracle_update"    # Between oracle updates


@dataclass
class StateTransition:
    """Represents a state transition in a contract.

    Attributes:
        id: Unique identifier
        from_state: State variables before transition
        to_state: State variables after transition
        trigger_function: Function that triggers the transition
        guard_conditions: Conditions that must be met
        enables_attacks: Attack vectors enabled by this transition
        state_vars_modified: State variables modified
    """
    id: str
    from_state: Dict[str, Any] = field(default_factory=dict)
    to_state: Dict[str, Any] = field(default_factory=dict)
    trigger_function: str = ""
    guard_conditions: List[str] = field(default_factory=list)
    enables_attacks: List[str] = field(default_factory=list)
    state_vars_modified: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "trigger_function": self.trigger_function,
            "guard_conditions": self.guard_conditions,
            "enables_attacks": self.enables_attacks,
            "state_vars_modified": self.state_vars_modified,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StateTransition":
        """Create from dictionary."""
        return StateTransition(
            id=data.get("id", ""),
            from_state=data.get("from_state", {}),
            to_state=data.get("to_state", {}),
            trigger_function=data.get("trigger_function", ""),
            guard_conditions=data.get("guard_conditions", []),
            enables_attacks=data.get("enables_attacks", []),
            state_vars_modified=data.get("state_vars_modified", []),
        )


@dataclass
class AttackWindow:
    """Represents a temporal vulnerability window.

    Attributes:
        id: Unique identifier
        window_type: Type of vulnerability window
        start_trigger: Function/event that opens window
        end_trigger: Function/event that closes window
        duration: Estimated duration (blocks or seconds)
        enabled_attacks: Attack vectors possible in this window
        risk_level: Risk level (1-10)
        mitigations: Possible mitigations
    """
    id: str
    window_type: VulnerabilityWindow
    start_trigger: str = ""
    end_trigger: str = ""
    duration: Optional[str] = None
    enabled_attacks: List[str] = field(default_factory=list)
    risk_level: int = 5
    mitigations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "window_type": self.window_type.value,
            "start_trigger": self.start_trigger,
            "end_trigger": self.end_trigger,
            "duration": self.duration,
            "enabled_attacks": self.enabled_attacks,
            "risk_level": self.risk_level,
            "mitigations": self.mitigations,
        }


@dataclass
class StateMachine:
    """State machine representation of a contract.

    Attributes:
        contract_id: ID of the contract
        states: Identified states
        transitions: State transitions
        initial_state: Initial state of the contract
        attack_windows: Identified vulnerability windows
    """
    contract_id: str
    states: List[str] = field(default_factory=list)
    transitions: List[StateTransition] = field(default_factory=list)
    initial_state: Optional[str] = None
    attack_windows: List[AttackWindow] = field(default_factory=list)

    @property
    def transition_count(self) -> int:
        return len(self.transitions)

    @property
    def state_count(self) -> int:
        return len(self.states)

    def get_transitions_from(self, state: str) -> List[StateTransition]:
        """Get transitions originating from a state."""
        return [t for t in self.transitions if state in str(t.from_state)]

    def get_transitions_to(self, state: str) -> List[StateTransition]:
        """Get transitions leading to a state."""
        return [t for t in self.transitions if state in str(t.to_state)]

    def get_dangerous_transitions(self) -> List[StateTransition]:
        """Get transitions that enable attacks."""
        return [t for t in self.transitions if t.enables_attacks]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_id": self.contract_id,
            "states": self.states,
            "transitions": [t.to_dict() for t in self.transitions],
            "initial_state": self.initial_state,
            "attack_windows": [w.to_dict() for w in self.attack_windows],
            "transition_count": self.transition_count,
            "state_count": self.state_count,
        }


class StateMachineBuilder:
    """Builds state machine from knowledge graph.

    Extracts state transitions and vulnerability windows from function analysis.
    """

    def __init__(self, graph: KnowledgeGraph):
        """Initialize builder with knowledge graph.

        Args:
            graph: Knowledge graph to analyze
        """
        self.graph = graph

    def build(self, contract_id: str) -> StateMachine:
        """Build state machine for a contract.

        Args:
            contract_id: ID of the contract node

        Returns:
            StateMachine representing the contract
        """
        # Get contract info
        contract_node = self.graph.nodes.get(contract_id)
        contract_label = contract_node.label if contract_node else None

        # Identify states from state variables
        states = self._identify_states(contract_id, contract_label)

        # Extract transitions from functions
        transitions = self._extract_transitions(contract_id, contract_label)

        # Detect vulnerability windows
        attack_windows = self._detect_attack_windows(contract_id, transitions)

        # Determine initial state
        initial_state = self._determine_initial_state(states, transitions)

        return StateMachine(
            contract_id=contract_id,
            states=states,
            transitions=transitions,
            initial_state=initial_state,
            attack_windows=attack_windows,
        )

    def _identify_states(
        self,
        contract_id: str,
        contract_label: Optional[str],
    ) -> List[str]:
        """Identify contract states from state variables."""
        states: Set[str] = set()

        # Look for state-indicating variables
        for node in self.graph.nodes.values():
            if node.type != "StateVariable":
                continue

            var_name = node.label.lower()
            props = node.properties

            # Boolean state flags
            if props.get("is_boolean", False):
                if any(kw in var_name for kw in ["paused", "pause"]):
                    states.add("paused")
                    states.add("active")
                elif any(kw in var_name for kw in ["locked", "lock"]):
                    states.add("locked")
                    states.add("unlocked")
                elif any(kw in var_name for kw in ["initialized", "init"]):
                    states.add("uninitialized")
                    states.add("initialized")

            # Enum-like state variables
            if "status" in var_name or "state" in var_name:
                states.add("pending")
                states.add("completed")

        # Default states if none found
        if not states:
            states.add("active")

        return sorted(list(states))

    def _extract_transitions(
        self,
        contract_id: str,
        contract_label: Optional[str],
    ) -> List[StateTransition]:
        """Extract state transitions from functions."""
        transitions: List[StateTransition] = []

        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue

            # Check if function belongs to contract
            func_contract = node.properties.get("contract_name", "")
            if func_contract != contract_label and contract_id != node.id:
                continue

            # Skip if function doesn't modify state
            if not node.properties.get("writes_state", False):
                continue

            transition = self._analyze_function_transition(node)
            if transition:
                transitions.append(transition)

        return transitions

    def _analyze_function_transition(self, func_node: Node) -> Optional[StateTransition]:
        """Analyze a function for state transitions."""
        func_name = func_node.label
        props = func_node.properties

        # Extract guard conditions
        guards: List[str] = []
        if props.get("has_access_gate", False):
            guards.append("access_control")
        if props.get("has_reentrancy_guard", False):
            guards.append("reentrancy_guard")
        if "whenNotPaused" in str(props.get("modifiers", [])):
            guards.append("not_paused")

        # Detect state changes
        from_state: Dict[str, Any] = {}
        to_state: Dict[str, Any] = {}
        state_vars: List[str] = []

        # Check for pause/unpause
        if "pause" in func_name.lower():
            if "unpause" in func_name.lower():
                from_state["paused"] = True
                to_state["paused"] = False
            else:
                from_state["paused"] = False
                to_state["paused"] = True
            state_vars.append("paused")

        # Check for initialization
        if props.get("is_initializer_like", False):
            from_state["initialized"] = False
            to_state["initialized"] = True
            state_vars.append("initialized")

        # Check for ownership changes
        if props.get("writes_privileged_state", False):
            semantic_ops = props.get("semantic_ops", []) or []
            if "MODIFIES_OWNER" in semantic_ops:
                state_vars.append("owner")
            if "MODIFIES_ROLES" in semantic_ops:
                state_vars.append("roles")

        # Detect enabled attacks
        enabled_attacks: List[str] = []

        # Check for reentrancy vulnerability
        if props.get("state_write_after_external_call", False):
            if not props.get("has_reentrancy_guard", False):
                enabled_attacks.append("reentrancy")

        # Check for access control issues
        if props.get("writes_privileged_state", False):
            if not props.get("has_access_gate", False):
                enabled_attacks.append("unauthorized_access")

        # Check for flash loan vulnerability
        if props.get("reads_oracle_price", False):
            if not props.get("has_staleness_check", False):
                enabled_attacks.append("price_manipulation")

        # Only create transition if there's meaningful state change
        if state_vars or enabled_attacks:
            return StateTransition(
                id=f"trans_{func_node.id}",
                from_state=from_state,
                to_state=to_state,
                trigger_function=func_name,
                guard_conditions=guards,
                enables_attacks=enabled_attacks,
                state_vars_modified=state_vars,
            )

        return None

    def _detect_attack_windows(
        self,
        contract_id: str,
        transitions: List[StateTransition],
    ) -> List[AttackWindow]:
        """Detect temporal vulnerability windows."""
        windows: List[AttackWindow] = []

        # Check for initialization window
        init_transitions = [t for t in transitions if "initialized" in t.state_vars_modified]
        if init_transitions:
            windows.append(AttackWindow(
                id=f"window_{contract_id}_init",
                window_type=VulnerabilityWindow.INITIALIZATION,
                start_trigger="deployment",
                end_trigger="initialize()",
                duration="until initialized",
                enabled_attacks=["unprotected_init", "front_running_init"],
                risk_level=8,
                mitigations=["Use constructor", "Deploy and init in same tx"],
            ))

        # Check for flash loan window
        for node in self.graph.nodes.values():
            if node.type != "Function":
                continue
            if node.properties.get("reads_oracle_price", False):
                if not node.properties.get("has_staleness_check", False):
                    windows.append(AttackWindow(
                        id=f"window_{node.id}_flash",
                        window_type=VulnerabilityWindow.FLASH_LOAN,
                        start_trigger="oracle read",
                        end_trigger="same transaction",
                        duration="1 transaction",
                        enabled_attacks=["price_manipulation", "flash_loan_attack"],
                        risk_level=7,
                        mitigations=["Use TWAP", "Check staleness", "Commit-reveal"],
                    ))
                    break  # Only add one flash loan window per contract

        # Check for pause/unpause window
        pause_transitions = [t for t in transitions if "paused" in t.state_vars_modified]
        if pause_transitions:
            windows.append(AttackWindow(
                id=f"window_{contract_id}_pause",
                window_type=VulnerabilityWindow.GOVERNANCE,
                start_trigger="pause()",
                end_trigger="unpause()",
                duration="governance controlled",
                enabled_attacks=["dos", "griefing"],
                risk_level=4,
                mitigations=["Timelock on pause", "Multi-sig"],
            ))

        # Check for dangerous transitions
        dangerous = [t for t in transitions if t.enables_attacks]
        for trans in dangerous:
            if "reentrancy" in trans.enables_attacks:
                windows.append(AttackWindow(
                    id=f"window_{trans.id}_reentrant",
                    window_type=VulnerabilityWindow.FLASH_LOAN,
                    start_trigger=trans.trigger_function,
                    end_trigger="function return",
                    duration="during external call",
                    enabled_attacks=["reentrancy"],
                    risk_level=9,
                    mitigations=["ReentrancyGuard", "CEI pattern", "Mutex"],
                ))

        return windows

    def _determine_initial_state(
        self,
        states: List[str],
        transitions: List[StateTransition],
    ) -> Optional[str]:
        """Determine the initial state of the contract."""
        # If we have uninitialized state, that's initial
        if "uninitialized" in states:
            return "uninitialized"

        # If we have active state, that's likely initial
        if "active" in states:
            return "active"

        # Return first state if any
        return states[0] if states else None


def build_state_machine(
    graph: KnowledgeGraph,
    contract_id: str,
) -> StateMachine:
    """Build a state machine for a contract.

    Convenience function for quick state machine building.

    Args:
        graph: Knowledge graph to analyze
        contract_id: ID of the contract

    Returns:
        StateMachine for the contract
    """
    builder = StateMachineBuilder(graph)
    return builder.build(contract_id)


def detect_temporal_vulnerabilities(
    state_machine: StateMachine,
) -> List[AttackWindow]:
    """Get all vulnerability windows from a state machine.

    Args:
        state_machine: State machine to analyze

    Returns:
        List of attack windows
    """
    return state_machine.attack_windows


def get_dangerous_transitions(
    state_machine: StateMachine,
) -> List[StateTransition]:
    """Get transitions that enable attacks.

    Args:
        state_machine: State machine to analyze

    Returns:
        List of dangerous transitions
    """
    return state_machine.get_dangerous_transitions()


__all__ = [
    "StateType",
    "VulnerabilityWindow",
    "StateTransition",
    "AttackWindow",
    "StateMachine",
    "StateMachineBuilder",
    "build_state_machine",
    "detect_temporal_vulnerabilities",
    "get_dangerous_transitions",
]
