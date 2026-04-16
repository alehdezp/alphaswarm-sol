"""Phase 6: Hierarchical Node Classification.

This module provides semantic role classification for function and state variable nodes.
Classification enables higher-level reasoning about contract security architecture.

Semantic Roles:
- Functions:
  - Guardian: Access control functions that protect other operations
  - Checkpoint: Functions that modify critical state
  - EscapeHatch: Emergency functions (pause, emergency withdraw)
  - EntryPoint: Public/external functions that can initiate state changes
  - Internal: Internal helper functions

- State Variables:
  - StateAnchor: Variables used in guards/access control
  - CriticalState: User-facing balances and critical financial state
  - ConfigState: Admin-configurable parameters
  - InternalState: Internal bookkeeping state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class FunctionRole(Enum):
    """Semantic roles for functions."""
    GUARDIAN = "Guardian"           # Access control functions
    CHECKPOINT = "Checkpoint"       # Critical state modification
    ESCAPE_HATCH = "EscapeHatch"   # Emergency functions
    ENTRY_POINT = "EntryPoint"     # Public state-changing functions
    INTERNAL = "Internal"          # Internal helper functions
    VIEW = "View"                  # Read-only functions


class StateVariableRole(Enum):
    """Semantic roles for state variables."""
    STATE_ANCHOR = "StateAnchor"     # Used in guards
    CRITICAL_STATE = "CriticalState" # User balances, critical financial state
    CONFIG_STATE = "ConfigState"     # Admin-configurable
    INTERNAL_STATE = "InternalState" # Internal bookkeeping


@dataclass
class AtomicBlock:
    """Represents an atomic block around an external call.

    An atomic block captures the pre/post regions around an external call,
    enabling detection of CEI violations and reentrancy risks.
    """
    function_id: str
    call_site_line: Optional[int]
    call_type: str  # "call", "delegatecall", "staticcall", "high_level"
    pre_state_reads: list[str] = field(default_factory=list)
    pre_state_writes: list[str] = field(default_factory=list)
    post_state_reads: list[str] = field(default_factory=list)
    post_state_writes: list[str] = field(default_factory=list)
    cei_violation: bool = False
    risk_level: str = "low"  # "low", "medium", "high", "critical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "function_id": self.function_id,
            "call_site_line": self.call_site_line,
            "call_type": self.call_type,
            "pre_state_reads": self.pre_state_reads,
            "pre_state_writes": self.pre_state_writes,
            "post_state_reads": self.post_state_reads,
            "post_state_writes": self.post_state_writes,
            "cei_violation": self.cei_violation,
            "risk_level": self.risk_level,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AtomicBlock":
        return AtomicBlock(
            function_id=str(data.get("function_id", "")),
            call_site_line=data.get("call_site_line"),
            call_type=str(data.get("call_type", "call")),
            pre_state_reads=list(data.get("pre_state_reads", [])),
            pre_state_writes=list(data.get("pre_state_writes", [])),
            post_state_reads=list(data.get("post_state_reads", [])),
            post_state_writes=list(data.get("post_state_writes", [])),
            cei_violation=bool(data.get("cei_violation", False)),
            risk_level=str(data.get("risk_level", "low")),
        )


class NodeClassifier:
    """Classifies nodes into semantic roles based on their properties."""

    # Keywords indicating guardian/access control functions
    GUARDIAN_KEYWORDS = {
        "only", "require", "auth", "access", "check", "verify",
        "permission", "role", "allowed", "restricted"
    }

    # Keywords indicating emergency/escape hatch functions
    EMERGENCY_KEYWORDS = {
        "emergency", "pause", "unpause", "stop", "kill", "shutdown",
        "recover", "rescue", "withdraw", "sweep"
    }

    # Keywords indicating checkpoint/critical functions
    CHECKPOINT_KEYWORDS = {
        "set", "update", "change", "transfer", "owner", "admin",
        "upgrade", "migrate", "initialize"
    }

    # Keywords for critical state variables
    CRITICAL_STATE_KEYWORDS = {
        "balance", "amount", "deposit", "stake", "share",
        "total", "supply", "reserve", "collateral"
    }

    # Keywords for config state variables
    CONFIG_STATE_KEYWORDS = {
        "fee", "rate", "threshold", "limit", "max", "min",
        "delay", "period", "config", "setting", "param"
    }

    # Keywords for anchor state variables (used in guards)
    ANCHOR_STATE_KEYWORDS = {
        "owner", "admin", "role", "paused", "initialized",
        "locked", "active", "enabled", "whitelist", "blacklist"
    }

    def classify_function(self, fn_node: Any) -> FunctionRole:
        """Classify a function node into a semantic role.

        Args:
            fn_node: Function node from the knowledge graph

        Returns:
            FunctionRole enum value
        """
        props = fn_node.properties if hasattr(fn_node, 'properties') else fn_node
        label = (fn_node.label if hasattr(fn_node, 'label') else props.get('label', '')).lower()

        # Check if it's a view function
        if props.get('is_view') or props.get('state_mutability') in ['view', 'pure']:
            return FunctionRole.VIEW

        # Check for guardian (access control) function
        if self._is_guardian(props, label):
            return FunctionRole.GUARDIAN

        # Check for escape hatch (emergency) function
        if self._is_escape_hatch(props, label):
            return FunctionRole.ESCAPE_HATCH

        # Check for checkpoint (critical state modification)
        if self._is_checkpoint(props, label):
            return FunctionRole.CHECKPOINT

        # Check for entry point (public/external state-changing)
        visibility = props.get('visibility', '')
        writes_state = props.get('writes_state', False)
        if visibility in ['public', 'external'] and writes_state:
            return FunctionRole.ENTRY_POINT

        return FunctionRole.INTERNAL

    def _is_guardian(self, props: dict, label: str) -> bool:
        """Check if function is an access control guardian."""
        # Has access control modifier or gate
        if props.get('has_access_gate') or props.get('has_access_modifier'):
            # Check if it's primarily an access control function
            modifiers = props.get('modifiers', [])
            if any('only' in m.lower() or 'auth' in m.lower() for m in modifiers):
                # This uses access control, but is it a guardian itself?
                # Guardians typically don't write much state
                if not props.get('writes_state'):
                    return True

        # Function name suggests access control
        if any(keyword in label for keyword in self.GUARDIAN_KEYWORDS):
            if not props.get('writes_state') or props.get('has_access_modifier'):
                return True

        return False

    def _is_escape_hatch(self, props: dict, label: str) -> bool:
        """Check if function is an emergency/escape hatch."""
        # Check for emergency keywords
        if any(keyword in label for keyword in self.EMERGENCY_KEYWORDS):
            return True

        # Check properties
        if props.get('is_emergency_function'):
            return True

        # Has pause check and can toggle pause state
        if props.get('has_pause_check') and 'pause' in label:
            return True

        return False

    def _is_checkpoint(self, props: dict, label: str) -> bool:
        """Check if function modifies critical state."""
        # Modifies privileged state
        if props.get('writes_privileged_state'):
            return True

        # Check for checkpoint keywords
        if any(keyword in label for keyword in self.CHECKPOINT_KEYWORDS):
            if props.get('writes_state'):
                return True

        # Modifies owner/admin
        if props.get('modifies_roles') or 'owner' in label or 'admin' in label:
            return True

        # Upgrade function
        if props.get('is_upgrade_function') or 'upgrade' in label:
            return True

        return False

    def classify_state_variable(self, var_node: Any) -> StateVariableRole:
        """Classify a state variable node into a semantic role.

        Args:
            var_node: StateVariable node from the knowledge graph

        Returns:
            StateVariableRole enum value
        """
        props = var_node.properties if hasattr(var_node, 'properties') else var_node
        label = (var_node.label if hasattr(var_node, 'label') else props.get('label', '')).lower()
        security_tags = props.get('security_tags', [])

        # Check for state anchor (used in guards)
        if self._is_state_anchor(props, label, security_tags):
            return StateVariableRole.STATE_ANCHOR

        # Check for critical state (user balances)
        if self._is_critical_state(props, label, security_tags):
            return StateVariableRole.CRITICAL_STATE

        # Check for config state (admin parameters)
        if self._is_config_state(props, label, security_tags):
            return StateVariableRole.CONFIG_STATE

        return StateVariableRole.INTERNAL_STATE

    def _is_state_anchor(self, props: dict, label: str, security_tags: list) -> bool:
        """Check if variable is used as a state anchor in guards."""
        # Check security tags
        if any(tag in ['owner', 'admin', 'role', 'access'] for tag in security_tags):
            return True

        # Check name patterns
        if any(keyword in label for keyword in self.ANCHOR_STATE_KEYWORDS):
            return True

        return False

    def _is_critical_state(self, props: dict, label: str, security_tags: list) -> bool:
        """Check if variable represents critical financial state."""
        # Check security tags
        if any(tag in ['balance', 'treasury', 'reserve'] for tag in security_tags):
            return True

        # Check name patterns
        if any(keyword in label for keyword in self.CRITICAL_STATE_KEYWORDS):
            return True

        # Mapping type with common balance patterns
        var_type = props.get('type', '')
        if 'mapping' in var_type.lower() and any(k in label for k in ['balance', 'deposit', 'stake']):
            return True

        return False

    def _is_config_state(self, props: dict, label: str, security_tags: list) -> bool:
        """Check if variable is admin-configurable state."""
        # Check security tags
        if any(tag in ['fee', 'config', 'setting'] for tag in security_tags):
            return True

        # Check name patterns
        if any(keyword in label for keyword in self.CONFIG_STATE_KEYWORDS):
            return True

        return False


def classify_function_role(fn_node: Any) -> str:
    """Convenience function to classify a function node.

    Args:
        fn_node: Function node from the knowledge graph

    Returns:
        String value of the role
    """
    classifier = NodeClassifier()
    return classifier.classify_function(fn_node).value


def classify_state_variable_role(var_node: Any) -> str:
    """Convenience function to classify a state variable node.

    Args:
        var_node: StateVariable node from the knowledge graph

    Returns:
        String value of the role
    """
    classifier = NodeClassifier()
    return classifier.classify_state_variable(var_node).value


def detect_atomic_blocks(fn_node: Any) -> list[AtomicBlock]:
    """Detect atomic blocks around external calls in a function.

    An atomic block captures state reads/writes before and after an external call,
    enabling detection of CEI (Checks-Effects-Interactions) violations.

    Args:
        fn_node: Function node from the knowledge graph

    Returns:
        List of AtomicBlock objects
    """
    props = fn_node.properties if hasattr(fn_node, 'properties') else fn_node
    blocks = []

    # Check if function has external calls
    has_external = props.get('has_external_calls', False)
    has_low_level = props.get('has_low_level_calls', False)

    if not has_external and not has_low_level:
        return blocks

    # Get state variable access info
    state_read = props.get('state_variables_read_names', [])
    state_written = props.get('state_variables_written_names', [])
    write_after_call = props.get('state_write_after_external_call', False)
    write_before_call = props.get('state_write_before_external_call', False)

    # Determine call type
    call_type = "high_level"
    if props.get('uses_delegatecall'):
        call_type = "delegatecall"
    elif has_low_level:
        call_type = "call"

    # Determine risk level
    if write_after_call:
        if props.get('has_reentrancy_guard'):
            risk_level = "low"
        elif call_type == "delegatecall":
            risk_level = "critical"
        else:
            risk_level = "high"
    else:
        risk_level = "low"

    # Create atomic block
    fn_id = fn_node.id if hasattr(fn_node, 'id') else props.get('id', '')
    line = props.get('line_start')

    block = AtomicBlock(
        function_id=fn_id,
        call_site_line=line,
        call_type=call_type,
        pre_state_reads=list(state_read) if write_before_call else [],
        pre_state_writes=list(state_written) if write_before_call else [],
        post_state_reads=list(state_read) if write_after_call else [],
        post_state_writes=list(state_written) if write_after_call else [],
        cei_violation=write_after_call and not props.get('has_reentrancy_guard', False),
        risk_level=risk_level,
    )

    blocks.append(block)
    return blocks


def get_semantic_role_summary(graph: Any) -> dict[str, Any]:
    """Get a summary of semantic roles in the graph.

    Args:
        graph: KnowledgeGraph

    Returns:
        Dictionary with role counts and high-risk findings
    """
    classifier = NodeClassifier()

    function_roles: dict[str, int] = {}
    var_roles: dict[str, int] = {}
    atomic_blocks: list[dict] = []
    high_risk_nodes: list[str] = []

    for node in graph.nodes.values():
        if node.type == "Function":
            role = classifier.classify_function(node)
            function_roles[role.value] = function_roles.get(role.value, 0) + 1

            # Detect atomic blocks
            blocks = detect_atomic_blocks(node)
            for block in blocks:
                if block.cei_violation:
                    high_risk_nodes.append(node.id)
                    atomic_blocks.append(block.to_dict())

        elif node.type == "StateVariable":
            role = classifier.classify_state_variable(node)
            var_roles[role.value] = var_roles.get(role.value, 0) + 1

    return {
        "function_roles": function_roles,
        "state_variable_roles": var_roles,
        "atomic_blocks": atomic_blocks,
        "high_risk_nodes": high_risk_nodes,
        "total_functions": sum(function_roles.values()),
        "total_state_variables": sum(var_roles.values()),
    }
