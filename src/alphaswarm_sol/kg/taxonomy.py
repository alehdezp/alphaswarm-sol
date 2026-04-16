"""Ops Taxonomy Registry for True VKG (Phase 5.9).

This module provides a canonical registry for semantic operations, edge types,
and pattern tags with versioned deprecations and migration rules.

The registry serves as the single source of truth for:
- SemanticOperation names and their metadata
- EdgeType mappings and risk levels
- Pattern tags for vulnerability detection
- Legacy aliases (with warnings) for backward compatibility
- Deprecation metadata with versioning and sunset policy
- SARIF-normalized operation names for tool output compatibility

Usage:
    from alphaswarm_sol.kg.taxonomy import ops_registry

    # Resolve canonical name from any alias
    canonical = ops_registry.resolve("TRANSFERS_ETH")  # -> "TRANSFERS_VALUE_OUT"

    # Check if an operation is deprecated
    if ops_registry.is_deprecated("OLD_OP"):
        migration = ops_registry.get_migration("OLD_OP")

    # Get all canonical operations
    for op in ops_registry.canonical_ops():
        print(op)
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from alphaswarm_sol.kg.operations import SemanticOperation


# =============================================================================
# Version Tracking
# =============================================================================

TAXONOMY_VERSION = "2.0.0"  # Phase 5.9 introduces v2
TAXONOMY_INTRODUCED = "0.5.0"  # First version with ops taxonomy


class DeprecationStatus(str, Enum):
    """Status of a deprecated operation or edge type."""

    ACTIVE = "active"  # In use, not deprecated
    DEPRECATED = "deprecated"  # Deprecated, migration available
    SUNSET = "sunset"  # Will be removed in future version
    REMOVED = "removed"  # No longer supported


@dataclass(frozen=True)
class DeprecationInfo:
    """Deprecation metadata for an operation or edge type.

    Attributes:
        status: Current deprecation status
        deprecated_in: Version when deprecated
        sunset_in: Version when it will be removed (optional)
        replacement: Canonical replacement name (optional)
        migration_rule: Description of how to migrate
        reason: Why this was deprecated
    """

    status: DeprecationStatus
    deprecated_in: str
    sunset_in: Optional[str] = None
    replacement: Optional[str] = None
    migration_rule: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "deprecated_in": self.deprecated_in,
            "sunset_in": self.sunset_in,
            "replacement": self.replacement,
            "migration_rule": self.migration_rule,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class OpDefinition:
    """Definition of a semantic operation in the taxonomy.

    Attributes:
        canonical_name: The canonical operation name (enum name)
        category: Operation category (value_movement, access_control, etc.)
        short_code: Short code for behavioral signatures (e.g., "X:out")
        description: Human-readable description
        risk_base: Base risk score (0-10)
        aliases: Alternative names that resolve to this operation
        sarif_aliases: SARIF/tool-normalized names
        pattern_tags: Associated pattern tags
        edge_types: Related edge types
        deprecation: Deprecation info if deprecated
    """

    canonical_name: str
    category: str
    short_code: str
    description: str
    risk_base: float = 0.0
    aliases: FrozenSet[str] = field(default_factory=frozenset)
    sarif_aliases: FrozenSet[str] = field(default_factory=frozenset)
    pattern_tags: FrozenSet[str] = field(default_factory=frozenset)
    edge_types: FrozenSet[str] = field(default_factory=frozenset)
    deprecation: Optional[DeprecationInfo] = None

    def is_deprecated(self) -> bool:
        """Check if this operation is deprecated."""
        return self.deprecation is not None and self.deprecation.status != DeprecationStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "canonical_name": self.canonical_name,
            "category": self.category,
            "short_code": self.short_code,
            "description": self.description,
            "risk_base": self.risk_base,
            "aliases": list(self.aliases),
            "sarif_aliases": list(self.sarif_aliases),
            "pattern_tags": list(self.pattern_tags),
            "edge_types": list(self.edge_types),
        }
        if self.deprecation:
            result["deprecation"] = self.deprecation.to_dict()
        return result


@dataclass(frozen=True)
class EdgeDefinition:
    """Definition of an edge type in the taxonomy.

    Attributes:
        canonical_name: The canonical edge type name
        category: Edge category (state, external, value, containment, taint, meta)
        risk_base: Base risk score (0-10)
        description: Human-readable description
        aliases: Alternative names that resolve to this edge type
        operations: Related semantic operations
        deprecation: Deprecation info if deprecated
    """

    canonical_name: str
    category: str
    risk_base: float
    description: str
    aliases: FrozenSet[str] = field(default_factory=frozenset)
    operations: FrozenSet[str] = field(default_factory=frozenset)
    deprecation: Optional[DeprecationInfo] = None

    def is_deprecated(self) -> bool:
        """Check if this edge type is deprecated."""
        return self.deprecation is not None and self.deprecation.status != DeprecationStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result: Dict[str, Any] = {
            "canonical_name": self.canonical_name,
            "category": self.category,
            "risk_base": self.risk_base,
            "description": self.description,
            "aliases": list(self.aliases),
            "operations": list(self.operations),
        }
        if self.deprecation:
            result["deprecation"] = self.deprecation.to_dict()
        return result


# =============================================================================
# Canonical Operation Definitions
# =============================================================================

# Operation categories
OP_CATEGORY_VALUE_MOVEMENT = "value_movement"
OP_CATEGORY_ACCESS_CONTROL = "access_control"
OP_CATEGORY_EXTERNAL = "external_interaction"
OP_CATEGORY_STATE = "state_management"
OP_CATEGORY_CONTROL_FLOW = "control_flow"
OP_CATEGORY_ARITHMETIC = "arithmetic"
OP_CATEGORY_VALIDATION = "validation"


CANONICAL_OPERATIONS: Dict[str, OpDefinition] = {
    # Value Movement (4)
    "TRANSFERS_VALUE_OUT": OpDefinition(
        canonical_name="TRANSFERS_VALUE_OUT",
        category=OP_CATEGORY_VALUE_MOVEMENT,
        short_code="X:out",
        description="ETH or token transfers out (transfer, send, call{value:})",
        risk_base=7.0,
        aliases=frozenset({"TRANSFER_OUT", "VALUE_OUT", "SENDS_VALUE"}),
        sarif_aliases=frozenset({"TRANSFERS_ETH", "TRANSFERS_TOKEN", "transfers-eth", "transfers-token"}),
        pattern_tags=frozenset({"reentrancy", "value_movement", "cei_violation"}),
        edge_types=frozenset({"TRANSFERS_ETH", "TRANSFERS_TOKEN"}),
    ),
    "RECEIVES_VALUE_IN": OpDefinition(
        canonical_name="RECEIVES_VALUE_IN",
        category=OP_CATEGORY_VALUE_MOVEMENT,
        short_code="X:in",
        description="Payable functions, token receipts",
        risk_base=3.0,
        aliases=frozenset({"RECEIVE_VALUE", "VALUE_IN", "ACCEPTS_PAYMENT"}),
        sarif_aliases=frozenset({"receives-eth", "receives-token"}),
        pattern_tags=frozenset({"value_movement"}),
        edge_types=frozenset(),
    ),
    "READS_USER_BALANCE": OpDefinition(
        canonical_name="READS_USER_BALANCE",
        category=OP_CATEGORY_VALUE_MOVEMENT,
        short_code="R:bal",
        description="balances[user], balanceOf(user)",
        risk_base=2.0,
        aliases=frozenset({"READ_BALANCE", "BALANCE_READ"}),
        sarif_aliases=frozenset({"reads-balance", "balance-read"}),
        pattern_tags=frozenset({"reentrancy", "balance_check"}),
        edge_types=frozenset({"READS_BALANCE"}),
    ),
    "WRITES_USER_BALANCE": OpDefinition(
        canonical_name="WRITES_USER_BALANCE",
        category=OP_CATEGORY_VALUE_MOVEMENT,
        short_code="W:bal",
        description="balances[user] = x, balance modifications",
        risk_base=6.0,
        aliases=frozenset({"WRITE_BALANCE", "BALANCE_WRITE", "UPDATES_BALANCE"}),
        sarif_aliases=frozenset({"writes-balance", "balance-write"}),
        pattern_tags=frozenset({"reentrancy", "cei_violation", "balance_update"}),
        edge_types=frozenset({"WRITES_BALANCE"}),
    ),
    # Access Control (3)
    "CHECKS_PERMISSION": OpDefinition(
        canonical_name="CHECKS_PERMISSION",
        category=OP_CATEGORY_ACCESS_CONTROL,
        short_code="C:auth",
        description="require(msg.sender == owner), onlyOwner",
        risk_base=0.0,  # Guards reduce risk
        aliases=frozenset({"AUTH_CHECK", "PERMISSION_CHECK", "ACCESS_CHECK"}),
        sarif_aliases=frozenset({"checks-auth", "access-control-check"}),
        pattern_tags=frozenset({"access_control", "guard"}),
        edge_types=frozenset(),
    ),
    "MODIFIES_OWNER": OpDefinition(
        canonical_name="MODIFIES_OWNER",
        category=OP_CATEGORY_ACCESS_CONTROL,
        short_code="M:own",
        description="owner = newOwner, ownership transfers",
        risk_base=8.0,
        aliases=frozenset({"OWNER_CHANGE", "OWNERSHIP_TRANSFER"}),
        sarif_aliases=frozenset({"modifies-owner", "ownership-change"}),
        pattern_tags=frozenset({"access_control", "ownership", "critical_state"}),
        edge_types=frozenset({"WRITES_CRITICAL_STATE"}),
    ),
    "MODIFIES_ROLES": OpDefinition(
        canonical_name="MODIFIES_ROLES",
        category=OP_CATEGORY_ACCESS_CONTROL,
        short_code="M:role",
        description="Role assignments, AccessControl changes",
        risk_base=7.0,
        aliases=frozenset({"ROLE_CHANGE", "ROLE_ASSIGNMENT"}),
        sarif_aliases=frozenset({"modifies-roles", "role-change"}),
        pattern_tags=frozenset({"access_control", "role_management", "critical_state"}),
        edge_types=frozenset({"WRITES_CRITICAL_STATE"}),
    ),
    # External Interaction (3)
    "CALLS_EXTERNAL": OpDefinition(
        canonical_name="CALLS_EXTERNAL",
        category=OP_CATEGORY_EXTERNAL,
        short_code="X:call",
        description="Any external contract call (high-level or low-level)",
        risk_base=5.0,
        aliases=frozenset({"EXTERNAL_CALL", "CONTRACT_CALL"}),
        sarif_aliases=frozenset({"calls-external", "external-call"}),
        pattern_tags=frozenset({"reentrancy", "external_call"}),
        edge_types=frozenset({"CALLS_EXTERNAL"}),
    ),
    "CALLS_UNTRUSTED": OpDefinition(
        canonical_name="CALLS_UNTRUSTED",
        category=OP_CATEGORY_EXTERNAL,
        short_code="X:unk",
        description="Calls to user-supplied addresses",
        risk_base=8.0,
        aliases=frozenset({"UNTRUSTED_CALL", "USER_CONTROLLED_CALL"}),
        sarif_aliases=frozenset({"calls-untrusted", "untrusted-call"}),
        pattern_tags=frozenset({"reentrancy", "untrusted_call", "arbitrary_call"}),
        edge_types=frozenset({"CALLS_UNTRUSTED"}),
    ),
    "READS_EXTERNAL_VALUE": OpDefinition(
        canonical_name="READS_EXTERNAL_VALUE",
        category=OP_CATEGORY_EXTERNAL,
        short_code="R:ext",
        description="Reading from external contracts (oracles, DEX)",
        risk_base=4.0,
        aliases=frozenset({"EXTERNAL_READ", "CONTRACT_READ"}),
        sarif_aliases=frozenset({"reads-external", "external-read"}),
        pattern_tags=frozenset({"oracle_dependency", "external_data"}),
        edge_types=frozenset({"READS_ORACLE"}),
    ),
    # State Management (3)
    "MODIFIES_CRITICAL_STATE": OpDefinition(
        canonical_name="MODIFIES_CRITICAL_STATE",
        category=OP_CATEGORY_STATE,
        short_code="M:crit",
        description="Writes to privileged state (owner, roles, fees)",
        risk_base=7.0,
        aliases=frozenset({"CRITICAL_STATE_WRITE", "PRIVILEGED_WRITE"}),
        sarif_aliases=frozenset({"modifies-critical-state", "critical-write"}),
        pattern_tags=frozenset({"critical_state", "privileged_operation"}),
        edge_types=frozenset({"WRITES_CRITICAL_STATE"}),
    ),
    "INITIALIZES_STATE": OpDefinition(
        canonical_name="INITIALIZES_STATE",
        category=OP_CATEGORY_STATE,
        short_code="I:init",
        description="Initializer patterns, constructor-like setups",
        risk_base=5.0,
        aliases=frozenset({"STATE_INIT", "INITIALIZATION"}),
        sarif_aliases=frozenset({"initializes-state", "state-init"}),
        pattern_tags=frozenset({"initialization", "proxy_pattern"}),
        edge_types=frozenset({"WRITES_STATE"}),
    ),
    "READS_ORACLE": OpDefinition(
        canonical_name="READS_ORACLE",
        category=OP_CATEGORY_STATE,
        short_code="R:orc",
        description="Chainlink, Uniswap oracle reads",
        risk_base=4.0,
        aliases=frozenset({"ORACLE_READ", "PRICE_READ"}),
        sarif_aliases=frozenset({"reads-oracle", "oracle-read", "price-read"}),
        pattern_tags=frozenset({"oracle_dependency", "price_manipulation"}),
        edge_types=frozenset({"READS_ORACLE"}),
    ),
    # Control Flow (3)
    "LOOPS_OVER_ARRAY": OpDefinition(
        canonical_name="LOOPS_OVER_ARRAY",
        category=OP_CATEGORY_CONTROL_FLOW,
        short_code="L:arr",
        description="for/while over arrays (DoS risk)",
        risk_base=4.0,
        aliases=frozenset({"ARRAY_LOOP", "UNBOUNDED_LOOP"}),
        sarif_aliases=frozenset({"loops-array", "unbounded-loop"}),
        pattern_tags=frozenset({"dos", "gas_limit", "unbounded_operation"}),
        edge_types=frozenset({"FUNCTION_HAS_LOOP"}),
    ),
    "USES_TIMESTAMP": OpDefinition(
        canonical_name="USES_TIMESTAMP",
        category=OP_CATEGORY_CONTROL_FLOW,
        short_code="U:time",
        description="block.timestamp access",
        risk_base=2.0,
        aliases=frozenset({"TIMESTAMP_USE", "TIME_DEPENDENCY"}),
        sarif_aliases=frozenset({"uses-timestamp", "timestamp-dependency"}),
        pattern_tags=frozenset({"timestamp_dependency", "miner_manipulation"}),
        edge_types=frozenset(),
    ),
    "USES_BLOCK_DATA": OpDefinition(
        canonical_name="USES_BLOCK_DATA",
        category=OP_CATEGORY_CONTROL_FLOW,
        short_code="U:blk",
        description="block.number, blockhash, prevrandao",
        risk_base=3.0,
        aliases=frozenset({"BLOCK_DATA_USE", "BLOCK_DEPENDENCY"}),
        sarif_aliases=frozenset({"uses-block-data", "block-dependency"}),
        pattern_tags=frozenset({"block_dependency", "randomness"}),
        edge_types=frozenset(),
    ),
    # Arithmetic (2)
    "PERFORMS_DIVISION": OpDefinition(
        canonical_name="PERFORMS_DIVISION",
        category=OP_CATEGORY_ARITHMETIC,
        short_code="A:div",
        description="Division operations (precision loss, div-by-zero)",
        risk_base=3.0,
        aliases=frozenset({"DIVISION", "DIV_OP"}),
        sarif_aliases=frozenset({"performs-division", "division-operation"}),
        pattern_tags=frozenset({"arithmetic", "precision_loss", "division_by_zero"}),
        edge_types=frozenset(),
    ),
    "PERFORMS_MULTIPLICATION": OpDefinition(
        canonical_name="PERFORMS_MULTIPLICATION",
        category=OP_CATEGORY_ARITHMETIC,
        short_code="A:mul",
        description="Multiplication operations (overflow risk)",
        risk_base=2.0,
        aliases=frozenset({"MULTIPLICATION", "MUL_OP"}),
        sarif_aliases=frozenset({"performs-multiplication", "multiplication-operation"}),
        pattern_tags=frozenset({"arithmetic", "overflow"}),
        edge_types=frozenset(),
    ),
    # Validation (2)
    "VALIDATES_INPUT": OpDefinition(
        canonical_name="VALIDATES_INPUT",
        category=OP_CATEGORY_VALIDATION,
        short_code="V:in",
        description="require/assert on parameters",
        risk_base=0.0,  # Validation reduces risk
        aliases=frozenset({"INPUT_VALIDATION", "PARAM_CHECK"}),
        sarif_aliases=frozenset({"validates-input", "input-validation"}),
        pattern_tags=frozenset({"input_validation", "guard"}),
        edge_types=frozenset(),
    ),
    "EMITS_EVENT": OpDefinition(
        canonical_name="EMITS_EVENT",
        category=OP_CATEGORY_VALIDATION,
        short_code="E:evt",
        description="Event emissions",
        risk_base=0.0,
        aliases=frozenset({"EVENT_EMISSION", "EMIT_LOG"}),
        sarif_aliases=frozenset({"emits-event", "event-emission"}),
        pattern_tags=frozenset({"event", "logging"}),
        edge_types=frozenset({"CONTAINS_EVENT"}),
    ),
}


# =============================================================================
# Canonical Edge Type Definitions
# =============================================================================

EDGE_CATEGORY_STATE = "state"
EDGE_CATEGORY_EXTERNAL = "external"
EDGE_CATEGORY_VALUE = "value"
EDGE_CATEGORY_CONTAINMENT = "containment"
EDGE_CATEGORY_TAINT = "taint"
EDGE_CATEGORY_META = "meta"


CANONICAL_EDGES: Dict[str, EdgeDefinition] = {
    # State modification edges
    "WRITES_STATE": EdgeDefinition(
        canonical_name="WRITES_STATE",
        category=EDGE_CATEGORY_STATE,
        risk_base=3.0,
        description="Writes any state variable",
        aliases=frozenset({"STATE_WRITE", "MODIFIES_STATE"}),
        operations=frozenset({"INITIALIZES_STATE"}),
    ),
    "WRITES_CRITICAL_STATE": EdgeDefinition(
        canonical_name="WRITES_CRITICAL_STATE",
        category=EDGE_CATEGORY_STATE,
        risk_base=7.0,
        description="Writes owner/admin/role vars",
        aliases=frozenset({"CRITICAL_STATE_WRITE"}),
        operations=frozenset({"MODIFIES_OWNER", "MODIFIES_ROLES", "MODIFIES_CRITICAL_STATE"}),
    ),
    "WRITES_BALANCE": EdgeDefinition(
        canonical_name="WRITES_BALANCE",
        category=EDGE_CATEGORY_STATE,
        risk_base=6.0,
        description="Writes balance-related state",
        aliases=frozenset({"BALANCE_WRITE"}),
        operations=frozenset({"WRITES_USER_BALANCE"}),
    ),
    # State reading edges
    "READS_STATE": EdgeDefinition(
        canonical_name="READS_STATE",
        category=EDGE_CATEGORY_STATE,
        risk_base=1.0,
        description="Reads any state variable",
        aliases=frozenset({"STATE_READ"}),
        operations=frozenset(),
    ),
    "READS_BALANCE": EdgeDefinition(
        canonical_name="READS_BALANCE",
        category=EDGE_CATEGORY_STATE,
        risk_base=2.0,
        description="Reads balance-related state",
        aliases=frozenset({"BALANCE_READ"}),
        operations=frozenset({"READS_USER_BALANCE"}),
    ),
    "READS_ORACLE": EdgeDefinition(
        canonical_name="READS_ORACLE",
        category=EDGE_CATEGORY_STATE,
        risk_base=3.0,
        description="Reads from oracle contract",
        aliases=frozenset({"ORACLE_READ"}),
        operations=frozenset({"READS_ORACLE", "READS_EXTERNAL_VALUE"}),
    ),
    # External call edges
    "CALLS_EXTERNAL": EdgeDefinition(
        canonical_name="CALLS_EXTERNAL",
        category=EDGE_CATEGORY_EXTERNAL,
        risk_base=5.0,
        description="Any external contract call",
        aliases=frozenset({"EXTERNAL_CALL"}),
        operations=frozenset({"CALLS_EXTERNAL"}),
    ),
    "CALLS_UNTRUSTED": EdgeDefinition(
        canonical_name="CALLS_UNTRUSTED",
        category=EDGE_CATEGORY_EXTERNAL,
        risk_base=8.0,
        description="Call to untrusted address",
        aliases=frozenset({"UNTRUSTED_CALL"}),
        operations=frozenset({"CALLS_UNTRUSTED"}),
    ),
    "DELEGATECALL": EdgeDefinition(
        canonical_name="DELEGATECALL",
        category=EDGE_CATEGORY_EXTERNAL,
        risk_base=9.0,
        description="delegatecall operation",
        aliases=frozenset({"DELEGATE_CALL"}),
        operations=frozenset({"CALLS_EXTERNAL"}),
    ),
    "STATICCALL": EdgeDefinition(
        canonical_name="STATICCALL",
        category=EDGE_CATEGORY_EXTERNAL,
        risk_base=2.0,
        description="staticcall operation",
        aliases=frozenset({"STATIC_CALL"}),
        operations=frozenset({"CALLS_EXTERNAL"}),
    ),
    # Value transfer edges
    "TRANSFERS_ETH": EdgeDefinition(
        canonical_name="TRANSFERS_ETH",
        category=EDGE_CATEGORY_VALUE,
        risk_base=7.0,
        description="Transfers native ETH",
        aliases=frozenset({"ETH_TRANSFER", "SEND_ETH"}),
        operations=frozenset({"TRANSFERS_VALUE_OUT"}),
    ),
    "TRANSFERS_TOKEN": EdgeDefinition(
        canonical_name="TRANSFERS_TOKEN",
        category=EDGE_CATEGORY_VALUE,
        risk_base=6.0,
        description="Transfers ERC20/721 tokens",
        aliases=frozenset({"TOKEN_TRANSFER", "SEND_TOKEN"}),
        operations=frozenset({"TRANSFERS_VALUE_OUT"}),
    ),
    # Containment edges (structural)
    "CONTAINS_FUNCTION": EdgeDefinition(
        canonical_name="CONTAINS_FUNCTION",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=0.0,
        description="Contract contains function",
        aliases=frozenset({"HAS_FUNCTION"}),
        operations=frozenset(),
    ),
    "CONTAINS_STATE": EdgeDefinition(
        canonical_name="CONTAINS_STATE",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=0.0,
        description="Contract contains state var",
        aliases=frozenset({"HAS_STATE"}),
        operations=frozenset(),
    ),
    "CONTAINS_EVENT": EdgeDefinition(
        canonical_name="CONTAINS_EVENT",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=0.0,
        description="Contract contains event",
        aliases=frozenset({"HAS_EVENT"}),
        operations=frozenset({"EMITS_EVENT"}),
    ),
    "CONTAINS_MODIFIER": EdgeDefinition(
        canonical_name="CONTAINS_MODIFIER",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=0.0,
        description="Contract contains modifier",
        aliases=frozenset({"HAS_MODIFIER"}),
        operations=frozenset(),
    ),
    "FUNCTION_HAS_INPUT": EdgeDefinition(
        canonical_name="FUNCTION_HAS_INPUT",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=0.0,
        description="Function has parameter",
        aliases=frozenset({"HAS_INPUT", "HAS_PARAM"}),
        operations=frozenset(),
    ),
    "FUNCTION_HAS_LOOP": EdgeDefinition(
        canonical_name="FUNCTION_HAS_LOOP",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=2.0,
        description="Function has loop construct",
        aliases=frozenset({"HAS_LOOP"}),
        operations=frozenset({"LOOPS_OVER_ARRAY"}),
    ),
    # Function relationships
    "CALLS_INTERNAL": EdgeDefinition(
        canonical_name="CALLS_INTERNAL",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=0.0,
        description="Internal function call",
        aliases=frozenset({"INTERNAL_CALL"}),
        operations=frozenset(),
    ),
    "USES_MODIFIER": EdgeDefinition(
        canonical_name="USES_MODIFIER",
        category=EDGE_CATEGORY_CONTAINMENT,
        risk_base=0.0,
        description="Function uses modifier",
        aliases=frozenset({"HAS_MODIFIER_USE"}),
        operations=frozenset({"CHECKS_PERMISSION"}),
    ),
    # Taint propagation edges
    "INPUT_TAINTS_STATE": EdgeDefinition(
        canonical_name="INPUT_TAINTS_STATE",
        category=EDGE_CATEGORY_TAINT,
        risk_base=4.0,
        description="User input flows to state",
        aliases=frozenset({"USER_TAINT"}),
        operations=frozenset(),
    ),
    "EXTERNAL_TAINTS": EdgeDefinition(
        canonical_name="EXTERNAL_TAINTS",
        category=EDGE_CATEGORY_TAINT,
        risk_base=5.0,
        description="External data taints state",
        aliases=frozenset({"EXT_TAINT"}),
        operations=frozenset(),
    ),
    # Meta-edges (graph intelligence)
    "SIMILAR_TO": EdgeDefinition(
        canonical_name="SIMILAR_TO",
        category=EDGE_CATEGORY_META,
        risk_base=0.0,
        description="Similar code pattern detected",
        aliases=frozenset(),
        operations=frozenset(),
    ),
    "BUGGY_PATTERN_MATCH": EdgeDefinition(
        canonical_name="BUGGY_PATTERN_MATCH",
        category=EDGE_CATEGORY_META,
        risk_base=0.0,
        description="Matches known bug pattern",
        aliases=frozenset(),
        operations=frozenset(),
    ),
    "REFACTOR_CANDIDATE": EdgeDefinition(
        canonical_name="REFACTOR_CANDIDATE",
        category=EDGE_CATEGORY_META,
        risk_base=0.0,
        description="Code could be refactored",
        aliases=frozenset(),
        operations=frozenset(),
    ),
}


# =============================================================================
# Deprecated Operations and Migration Rules
# =============================================================================

DEPRECATED_ALIASES: Dict[str, DeprecationInfo] = {
    # Legacy tool output aliases (from external tools)
    "TRANSFERS_ETH": DeprecationInfo(
        status=DeprecationStatus.DEPRECATED,
        deprecated_in="2.0.0",
        sunset_in="3.0.0",
        replacement="TRANSFERS_VALUE_OUT",
        migration_rule="Use TRANSFERS_VALUE_OUT for all value transfers (ETH and tokens)",
        reason="Unified value transfer operation",
    ),
    "TRANSFERS_TOKEN": DeprecationInfo(
        status=DeprecationStatus.DEPRECATED,
        deprecated_in="2.0.0",
        sunset_in="3.0.0",
        replacement="TRANSFERS_VALUE_OUT",
        migration_rule="Use TRANSFERS_VALUE_OUT for all value transfers (ETH and tokens)",
        reason="Unified value transfer operation",
    ),
    # Old naming conventions
    "TRANSFER_OUT": DeprecationInfo(
        status=DeprecationStatus.DEPRECATED,
        deprecated_in="2.0.0",
        sunset_in="3.0.0",
        replacement="TRANSFERS_VALUE_OUT",
        migration_rule="Rename to TRANSFERS_VALUE_OUT",
        reason="Standardized naming",
    ),
    "OWNER_CHANGE": DeprecationInfo(
        status=DeprecationStatus.DEPRECATED,
        deprecated_in="2.0.0",
        sunset_in="3.0.0",
        replacement="MODIFIES_OWNER",
        migration_rule="Rename to MODIFIES_OWNER",
        reason="Standardized naming",
    ),
}


# =============================================================================
# Ops Taxonomy Registry
# =============================================================================


class OpsTaxonomyRegistry:
    """Central registry for semantic operations and edge types.

    Provides resolution of aliases to canonical names, deprecation checking,
    and migration guidance.

    Thread-safe for reads; modifications should be done at initialization only.
    """

    def __init__(self) -> None:
        """Initialize the registry with canonical definitions."""
        self._operations = dict(CANONICAL_OPERATIONS)
        self._edges = dict(CANONICAL_EDGES)
        self._deprecated = dict(DEPRECATED_ALIASES)

        # Build reverse lookup indexes
        self._op_alias_index: Dict[str, str] = {}
        self._edge_alias_index: Dict[str, str] = {}
        self._sarif_alias_index: Dict[str, str] = {}
        self._short_code_index: Dict[str, str] = {}

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build reverse lookup indexes for fast resolution."""
        # Operation aliases
        for canonical, op_def in self._operations.items():
            # Canonical name points to itself
            self._op_alias_index[canonical] = canonical
            self._op_alias_index[canonical.lower()] = canonical

            # All aliases point to canonical
            for alias in op_def.aliases:
                self._op_alias_index[alias] = canonical
                self._op_alias_index[alias.lower()] = canonical

            # SARIF aliases
            for sarif_alias in op_def.sarif_aliases:
                self._sarif_alias_index[sarif_alias] = canonical
                self._sarif_alias_index[sarif_alias.lower()] = canonical

            # Short codes
            self._short_code_index[op_def.short_code] = canonical

        # Edge aliases
        for canonical, edge_def in self._edges.items():
            self._edge_alias_index[canonical] = canonical
            self._edge_alias_index[canonical.lower()] = canonical

            for alias in edge_def.aliases:
                self._edge_alias_index[alias] = canonical
                self._edge_alias_index[alias.lower()] = canonical

    @property
    def version(self) -> str:
        """Get taxonomy version."""
        return TAXONOMY_VERSION

    # =========================================================================
    # Operation Resolution
    # =========================================================================

    def resolve_operation(self, name: str, warn_on_deprecated: bool = True) -> Optional[str]:
        """Resolve an operation name to its canonical form.

        Args:
            name: Operation name (canonical, alias, or SARIF format)
            warn_on_deprecated: Whether to emit deprecation warnings

        Returns:
            Canonical operation name or None if not found
        """
        # Try direct lookup first
        canonical = self._op_alias_index.get(name)
        if canonical is None:
            canonical = self._op_alias_index.get(name.lower())
        if canonical is None:
            canonical = self._sarif_alias_index.get(name)
        if canonical is None:
            canonical = self._sarif_alias_index.get(name.lower())

        # Check deprecation
        if canonical is not None and warn_on_deprecated:
            self._check_deprecation(name)

        return canonical

    def resolve(self, name: str) -> Optional[str]:
        """Alias for resolve_operation."""
        return self.resolve_operation(name)

    def resolve_sarif_operation(self, sarif_name: str) -> Optional[str]:
        """Resolve a SARIF-normalized operation name to canonical form.

        Args:
            sarif_name: SARIF operation name (e.g., "transfers-eth")

        Returns:
            Canonical operation name or None if not found
        """
        return self._sarif_alias_index.get(sarif_name) or self._sarif_alias_index.get(sarif_name.lower())

    def resolve_short_code(self, short_code: str) -> Optional[str]:
        """Resolve a short code to canonical operation name.

        Args:
            short_code: Short code (e.g., "X:out")

        Returns:
            Canonical operation name or None if not found
        """
        return self._short_code_index.get(short_code)

    # =========================================================================
    # Edge Resolution
    # =========================================================================

    def resolve_edge(self, name: str, warn_on_deprecated: bool = True) -> Optional[str]:
        """Resolve an edge type name to its canonical form.

        Args:
            name: Edge type name (canonical or alias)
            warn_on_deprecated: Whether to emit deprecation warnings

        Returns:
            Canonical edge type name or None if not found
        """
        canonical = self._edge_alias_index.get(name)
        if canonical is None:
            canonical = self._edge_alias_index.get(name.lower())

        return canonical

    # =========================================================================
    # Deprecation Checking
    # =========================================================================

    def is_deprecated(self, name: str) -> bool:
        """Check if an operation or alias is deprecated.

        Args:
            name: Operation name to check

        Returns:
            True if deprecated
        """
        if name in self._deprecated:
            return True

        # Check if canonical op is deprecated
        canonical = self.resolve_operation(name, warn_on_deprecated=False)
        if canonical and canonical in self._operations:
            return self._operations[canonical].is_deprecated()

        return False

    def get_deprecation_info(self, name: str) -> Optional[DeprecationInfo]:
        """Get deprecation information for an operation or alias.

        Args:
            name: Operation name

        Returns:
            DeprecationInfo if deprecated, None otherwise
        """
        # Check direct deprecated aliases first
        if name in self._deprecated:
            return self._deprecated[name]

        # Check canonical operation
        canonical = self.resolve_operation(name, warn_on_deprecated=False)
        if canonical and canonical in self._operations:
            return self._operations[canonical].deprecation

        return None

    def get_migration(self, name: str) -> Optional[str]:
        """Get migration replacement for a deprecated operation.

        Args:
            name: Deprecated operation name

        Returns:
            Replacement operation name or None
        """
        info = self.get_deprecation_info(name)
        return info.replacement if info else None

    def _check_deprecation(self, name: str) -> None:
        """Emit deprecation warning if operation is deprecated."""
        info = self.get_deprecation_info(name)
        if info and info.status != DeprecationStatus.ACTIVE:
            msg = f"Operation '{name}' is deprecated"
            if info.replacement:
                msg += f", use '{info.replacement}' instead"
            if info.migration_rule:
                msg += f". Migration: {info.migration_rule}"
            warnings.warn(msg, DeprecationWarning, stacklevel=4)

    # =========================================================================
    # Enumeration
    # =========================================================================

    def canonical_ops(self) -> List[str]:
        """Get all canonical operation names.

        Returns:
            List of canonical operation names
        """
        return list(self._operations.keys())

    def canonical_edges(self) -> List[str]:
        """Get all canonical edge type names.

        Returns:
            List of canonical edge type names
        """
        return list(self._edges.keys())

    def get_operation(self, name: str) -> Optional[OpDefinition]:
        """Get operation definition.

        Args:
            name: Operation name (canonical or alias)

        Returns:
            OpDefinition or None
        """
        canonical = self.resolve_operation(name, warn_on_deprecated=False)
        if canonical:
            return self._operations.get(canonical)
        return None

    def get_edge(self, name: str) -> Optional[EdgeDefinition]:
        """Get edge type definition.

        Args:
            name: Edge type name (canonical or alias)

        Returns:
            EdgeDefinition or None
        """
        canonical = self.resolve_edge(name, warn_on_deprecated=False)
        if canonical:
            return self._edges.get(canonical)
        return None

    def get_ops_by_category(self, category: str) -> List[OpDefinition]:
        """Get all operations in a category.

        Args:
            category: Category name

        Returns:
            List of operation definitions
        """
        return [op for op in self._operations.values() if op.category == category]

    def get_edges_by_category(self, category: str) -> List[EdgeDefinition]:
        """Get all edge types in a category.

        Args:
            category: Category name

        Returns:
            List of edge definitions
        """
        return [edge for edge in self._edges.values() if edge.category == category]

    def get_pattern_tags(self, name: str) -> FrozenSet[str]:
        """Get pattern tags for an operation.

        Args:
            name: Operation name

        Returns:
            Set of pattern tags
        """
        op = self.get_operation(name)
        return op.pattern_tags if op else frozenset()

    def get_risk_base(self, name: str) -> float:
        """Get base risk score for an operation or edge.

        Args:
            name: Operation or edge name

        Returns:
            Base risk score (0-10)
        """
        op = self.get_operation(name)
        if op:
            return op.risk_base

        edge = self.get_edge(name)
        if edge:
            return edge.risk_base

        return 0.0

    # =========================================================================
    # Validation
    # =========================================================================

    def is_valid_operation(self, name: str) -> bool:
        """Check if a name resolves to a valid operation.

        Args:
            name: Operation name to check

        Returns:
            True if valid
        """
        return self.resolve_operation(name, warn_on_deprecated=False) is not None

    def is_valid_edge(self, name: str) -> bool:
        """Check if a name resolves to a valid edge type.

        Args:
            name: Edge type name to check

        Returns:
            True if valid
        """
        return self.resolve_edge(name, warn_on_deprecated=False) is not None

    def validate_pattern_ops(self, ops: List[str]) -> Tuple[List[str], List[str]]:
        """Validate operations used in a pattern.

        Args:
            ops: List of operation names

        Returns:
            Tuple of (valid_ops, invalid_ops)
        """
        valid = []
        invalid = []
        for op in ops:
            if self.is_valid_operation(op):
                valid.append(op)
            else:
                invalid.append(op)
        return valid, invalid

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Export registry as dictionary.

        Returns:
            Dictionary representation of the registry
        """
        return {
            "version": TAXONOMY_VERSION,
            "operations": {k: v.to_dict() for k, v in self._operations.items()},
            "edges": {k: v.to_dict() for k, v in self._edges.items()},
            "deprecated": {k: v.to_dict() for k, v in self._deprecated.items()},
        }


# =============================================================================
# Module-level Registry Instance
# =============================================================================

# Singleton registry instance
ops_registry = OpsTaxonomyRegistry()


# Convenience functions
def resolve_operation(name: str) -> Optional[str]:
    """Resolve operation name to canonical form."""
    return ops_registry.resolve_operation(name)


def resolve_edge(name: str) -> Optional[str]:
    """Resolve edge type to canonical form."""
    return ops_registry.resolve_edge(name)


def is_deprecated(name: str) -> bool:
    """Check if operation is deprecated."""
    return ops_registry.is_deprecated(name)


def get_migration(name: str) -> Optional[str]:
    """Get migration for deprecated operation."""
    return ops_registry.get_migration(name)


def validate_pattern_ops(ops: List[str]) -> Tuple[List[str], List[str]]:
    """Validate pattern operations."""
    return ops_registry.validate_pattern_ops(ops)


__all__ = [
    # Version
    "TAXONOMY_VERSION",
    # Enums
    "DeprecationStatus",
    # Dataclasses
    "DeprecationInfo",
    "OpDefinition",
    "EdgeDefinition",
    # Constants
    "CANONICAL_OPERATIONS",
    "CANONICAL_EDGES",
    "DEPRECATED_ALIASES",
    # Categories
    "OP_CATEGORY_VALUE_MOVEMENT",
    "OP_CATEGORY_ACCESS_CONTROL",
    "OP_CATEGORY_EXTERNAL",
    "OP_CATEGORY_STATE",
    "OP_CATEGORY_CONTROL_FLOW",
    "OP_CATEGORY_ARITHMETIC",
    "OP_CATEGORY_VALIDATION",
    "EDGE_CATEGORY_STATE",
    "EDGE_CATEGORY_EXTERNAL",
    "EDGE_CATEGORY_VALUE",
    "EDGE_CATEGORY_CONTAINMENT",
    "EDGE_CATEGORY_TAINT",
    "EDGE_CATEGORY_META",
    # Registry
    "OpsTaxonomyRegistry",
    "ops_registry",
    # Convenience functions
    "resolve_operation",
    "resolve_edge",
    "is_deprecated",
    "get_migration",
    "validate_pattern_ops",
]
