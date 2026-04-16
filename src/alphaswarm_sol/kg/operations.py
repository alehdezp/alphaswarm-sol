"""Semantic Operations for True VKG.

This module provides name-agnostic detection of what Solidity functions DO,
rather than relying on function names. This enables detection of vulnerabilities
even when code uses non-standard naming conventions.

Key concepts:
- SemanticOperation: Enum of 20 operations describing function behavior
- OperationOccurrence: Records where an operation occurs in CFG order
- Behavioral Signature: Compact notation like "R:bal→X:out→W:bal"

Registry Integration (Phase 5.9):
- All operation names can be resolved through the taxonomy registry
- Legacy aliases and SARIF-normalized names are supported with deprecation warnings
- Use resolve_operation_name() for registry-backed resolution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.kg.taxonomy import OpsTaxonomyRegistry


class SemanticOperation(Enum):
    """Semantic operations that describe what code does, not what it's named."""

    # Value Movement (4) - Operations related to ETH/token transfers
    TRANSFERS_VALUE_OUT = auto()  # ETH or token transfers out (transfer, send, call{value:})
    RECEIVES_VALUE_IN = auto()  # Payable functions, token receipts
    READS_USER_BALANCE = auto()  # balances[user], balanceOf(user)
    WRITES_USER_BALANCE = auto()  # balances[user] = x, balance modifications

    # Access Control (3) - Permission and authorization operations
    CHECKS_PERMISSION = auto()  # require(msg.sender == owner), onlyOwner
    MODIFIES_OWNER = auto()  # owner = newOwner, ownership transfers
    MODIFIES_ROLES = auto()  # Role assignments, AccessControl changes

    # External Interaction (3) - Cross-contract operations
    CALLS_EXTERNAL = auto()  # Any external call (high-level or low-level)
    CALLS_UNTRUSTED = auto()  # Calls to user-supplied addresses
    READS_EXTERNAL_VALUE = auto()  # Reading from external contracts (oracles, DEX)

    # State Management (3) - Critical state operations
    MODIFIES_CRITICAL_STATE = auto()  # Writes to privileged state (owner, roles, fees)
    INITIALIZES_STATE = auto()  # Initializer patterns, constructor-like setups
    READS_ORACLE = auto()  # Chainlink, Uniswap oracle reads

    # Control Flow (3) - Flow control with security implications
    LOOPS_OVER_ARRAY = auto()  # for/while over arrays (DoS risk)
    USES_TIMESTAMP = auto()  # block.timestamp access
    USES_BLOCK_DATA = auto()  # block.number, blockhash, prevrandao

    # Arithmetic (2) - Potentially risky arithmetic
    PERFORMS_DIVISION = auto()  # Division operations (precision loss, div-by-zero)
    PERFORMS_MULTIPLICATION = auto()  # Multiplication operations (overflow risk)

    # Validation (2) - Input validation and logging
    VALIDATES_INPUT = auto()  # require/assert on parameters
    EMITS_EVENT = auto()  # Event emissions


@dataclass
class OperationOccurrence:
    """Records where a semantic operation occurs in the CFG."""

    operation: SemanticOperation
    cfg_order: int  # Position in CFG traversal (0-indexed)
    line_number: int  # Source line number
    detail: Optional[str] = None  # Additional context (e.g., target address, function name)


# Short codes for behavioral signatures - compact notation for pattern matching
OP_CODES: Dict[SemanticOperation, str] = {
    SemanticOperation.TRANSFERS_VALUE_OUT: "X:out",
    SemanticOperation.RECEIVES_VALUE_IN: "X:in",
    SemanticOperation.READS_USER_BALANCE: "R:bal",
    SemanticOperation.WRITES_USER_BALANCE: "W:bal",
    SemanticOperation.CHECKS_PERMISSION: "C:auth",
    SemanticOperation.MODIFIES_OWNER: "M:own",
    SemanticOperation.MODIFIES_ROLES: "M:role",
    SemanticOperation.CALLS_EXTERNAL: "X:call",
    SemanticOperation.CALLS_UNTRUSTED: "X:unk",
    SemanticOperation.READS_EXTERNAL_VALUE: "R:ext",
    SemanticOperation.MODIFIES_CRITICAL_STATE: "M:crit",
    SemanticOperation.INITIALIZES_STATE: "I:init",
    SemanticOperation.READS_ORACLE: "R:orc",
    SemanticOperation.LOOPS_OVER_ARRAY: "L:arr",
    SemanticOperation.USES_TIMESTAMP: "U:time",
    SemanticOperation.USES_BLOCK_DATA: "U:blk",
    SemanticOperation.PERFORMS_DIVISION: "A:div",
    SemanticOperation.PERFORMS_MULTIPLICATION: "A:mul",
    SemanticOperation.VALIDATES_INPUT: "V:in",
    SemanticOperation.EMITS_EVENT: "E:evt",
}


# State variable name patterns for classification
# ENHANCED: Semantic balance detection - recognizes ALL common balance-tracking names
BALANCE_PATTERNS = frozenset({
    # Standard "balance" naming
    "balance", "balances", "_balance", "_balances",
    "userbalance", "userbalances", "accountbalance",
    # Alternative naming conventions (funds, shares, deposits, etc.)
    "fund", "funds", "_fund", "_funds", "userfunds", "accountfunds",
    "share", "shares", "_share", "_shares", "usershares", "accountshares",
    "deposit", "deposits", "_deposit", "_deposits", "userdeposits", "accountdeposits",
    "credit", "credits", "_credit", "_credits", "usercredits", "accountcredits",
    "stake", "stakes", "_stake", "_stakes", "userstakes", "accountstakes",
    "amount", "amounts", "_amount", "_amounts", "useramounts", "accountamounts",
    "position", "positions", "_position", "_positions", "userpositions",
    "holding", "holdings", "_holding", "_holdings", "userholdings",
    "reserve", "reserves", "_reserve", "_reserves", "userreserves",
    "liquidity", "liquidities", "_liquidity", "userliquidity",
    "supply", "supplies", "_supply", "_supplies", "usersupply",
    "debt", "debts", "_debt", "_debts", "userdebts", "accountdebts",
    "owed", "_owed", "userowed", "accountowed",
    "claim", "claims", "_claim", "_claims", "userclaims",
    "withdrawal", "withdrawals", "_withdrawal", "_withdrawals",
    "token", "tokens", "_token", "_tokens", "usertokens", "accounttokens",
})
OWNER_PATTERNS = frozenset({
    "owner", "_owner", "admin", "_admin",
    "governance", "controller", "authority",
})
ROLE_PATTERNS = frozenset({
    "role", "roles", "_roles", "minter", "pauser",
    "operator", "operators", "whitelist", "blacklist",
})
PRIVILEGED_PATTERNS = OWNER_PATTERNS | ROLE_PATTERNS | frozenset({
    "fee", "fees", "treasury", "vault", "implementation",
    "pendingowner", "pendinggov", "guardian",
})

# Oracle function name patterns
ORACLE_FUNCTIONS = frozenset({
    "latestanswer", "latestrounddata", "getprice", "getunderlyingprice",
    "consult", "observe", "getamountout", "getreserves", "slot0",
    "gettwap", "getpricecumulativelast",
})

# Token transfer functions
TOKEN_TRANSFER_FUNCTIONS = frozenset({
    "transfer", "transferfrom", "safetransfer", "safetransferfrom",
    "send", "sendvalue", "call",
})

# Auth modifier patterns
AUTH_MODIFIER_PATTERNS = frozenset({
    "onlyowner", "onlyadmin", "onlygov", "onlygovernance",
    "onlyauthorized", "onlyoperator", "onlyminter", "onlypauser",
    "onlyrole", "requiresauth", "auth", "restricted",
})


def _get_line_number(node: Any) -> int:
    """Extract line number from a Slither node."""
    if hasattr(node, "source_mapping") and node.source_mapping:
        mapping = node.source_mapping
        if hasattr(mapping, "lines") and mapping.lines:
            return mapping.lines[0]
        if hasattr(mapping, "start"):
            return mapping.start
    return 0


def _normalize_name(name: str) -> str:
    """Normalize a name for pattern matching."""
    return name.lower().replace("_", "")


def _is_balance_var(var_name: str) -> bool:
    """Check if a variable name suggests it's a balance."""
    normalized = _normalize_name(var_name)
    return any(pattern in normalized for pattern in BALANCE_PATTERNS)


def _is_privileged_var(var_name: str) -> bool:
    """Check if a variable name suggests privileged state."""
    normalized = _normalize_name(var_name)
    return any(pattern in normalized for pattern in PRIVILEGED_PATTERNS)


def _is_owner_var(var_name: str) -> bool:
    """Check if a variable name suggests ownership."""
    normalized = _normalize_name(var_name)
    return any(pattern in normalized for pattern in OWNER_PATTERNS)


def _is_role_var(var_name: str) -> bool:
    """Check if a variable name suggests role management."""
    normalized = _normalize_name(var_name)
    return any(pattern in normalized for pattern in ROLE_PATTERNS)


# =============================================================================
# Value Movement Detectors (P1-T2)
# =============================================================================


def detect_transfers_value_out(fn: Any) -> List[OperationOccurrence]:
    """Detect ETH or token transfers out of the contract.

    Detects:
    - ETH: transfer(), send(), call{value:}
    - Tokens: transfer(), transferFrom(), safeTransfer(), safeTransferFrom()
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        found = False
        detail = None

        # Check IR for Transfer, Send, LowLevelCall with value
        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__

            # ETH transfers via Transfer or Send IR
            if ir_type in ("Transfer", "Send"):
                found = True
                detail = f"ETH via {ir_type.lower()}"
                break

            # Low-level call with value
            if ir_type == "LowLevelCall":
                if getattr(ir, "call_value", None):
                    found = True
                    detail = "ETH via call{value:}"
                    break

            # High-level token transfer calls
            if ir_type == "HighLevelCall":
                func_name = str(getattr(ir, "function_name", "") or "").lower()
                if func_name in TOKEN_TRANSFER_FUNCTIONS:
                    found = True
                    detail = f"Token via {func_name}"
                    break

        if found:
            occurrences.append(OperationOccurrence(
                operation=SemanticOperation.TRANSFERS_VALUE_OUT,
                cfg_order=cfg_order,
                line_number=_get_line_number(node),
                detail=detail,
            ))
        cfg_order += 1

    return occurrences


def detect_receives_value_in(fn: Any) -> List[OperationOccurrence]:
    """Detect if function receives ETH or tokens.

    Detects:
    - Payable functions
    - Token receipt patterns (transferFrom where contract is recipient)
    """
    occurrences: List[OperationOccurrence] = []

    # Check if function is payable
    if getattr(fn, "payable", False):
        occurrences.append(OperationOccurrence(
            operation=SemanticOperation.RECEIVES_VALUE_IN,
            cfg_order=0,
            line_number=_get_line_number(fn),
            detail="payable function",
        ))

    return occurrences


def detect_reads_user_balance(fn: Any) -> List[OperationOccurrence]:
    """Detect reads from user balance state with CFG ordering.

    Detects:
    - balances[user] reads at each CFG node
    - balanceOf() calls
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    # Get balance variable names for this contract
    balance_vars = set()
    for var in getattr(fn, "state_variables_read", []) or []:
        var_name = getattr(var, "name", "") or ""
        if _is_balance_var(var_name):
            balance_vars.add(var_name)

    # Traverse CFG nodes to find reads in order
    for node in getattr(fn, "nodes", []) or []:
        found = False

        # Check for state variable reads at this node
        node_vars_read = getattr(node, "state_variables_read", []) or []
        for var in node_vars_read:
            var_name = getattr(var, "name", "") or ""
            if _is_balance_var(var_name):
                occurrences.append(OperationOccurrence(
                    operation=SemanticOperation.READS_USER_BALANCE,
                    cfg_order=cfg_order,
                    line_number=_get_line_number(node),
                    detail=f"read {var_name}",
                ))
                found = True
                break

        # Also check for balanceOf() calls in IR
        if not found:
            for ir in getattr(node, "irs", []) or []:
                if type(ir).__name__ == "HighLevelCall":
                    func_name = str(getattr(ir, "function_name", "") or "").lower()
                    if func_name == "balanceof":
                        occurrences.append(OperationOccurrence(
                            operation=SemanticOperation.READS_USER_BALANCE,
                            cfg_order=cfg_order,
                            line_number=_get_line_number(node),
                            detail="balanceOf() call",
                        ))
                        break

        cfg_order += 1

    return occurrences


def detect_writes_user_balance(fn: Any) -> List[OperationOccurrence]:
    """Detect writes to user balance state with CFG ordering.

    Detects:
    - balances[user] = x at each CFG node
    - _balances modifications
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    # Traverse CFG nodes to find writes in order
    for node in getattr(fn, "nodes", []) or []:
        # Check for state variable writes at this node
        node_vars_written = getattr(node, "state_variables_written", []) or []
        for var in node_vars_written:
            var_name = getattr(var, "name", "") or ""
            if _is_balance_var(var_name):
                occurrences.append(OperationOccurrence(
                    operation=SemanticOperation.WRITES_USER_BALANCE,
                    cfg_order=cfg_order,
                    line_number=_get_line_number(node),
                    detail=f"write {var_name}",
                ))
                break  # One per node

        cfg_order += 1

    return occurrences


# =============================================================================
# Access Control Detectors (P1-T3)
# =============================================================================


def detect_checks_permission(fn: Any) -> List[OperationOccurrence]:
    """Detect permission checks.

    Detects:
    - Auth modifiers (onlyOwner, etc.)
    - require(msg.sender == owner)
    - Role-based checks
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    # Check for auth modifiers
    for mod in getattr(fn, "modifiers", []) or []:
        mod_name = _normalize_name(getattr(mod, "name", "") or "")
        if any(pattern in mod_name for pattern in AUTH_MODIFIER_PATTERNS):
            occurrences.append(OperationOccurrence(
                operation=SemanticOperation.CHECKS_PERMISSION,
                cfg_order=0,
                line_number=_get_line_number(fn),
                detail=f"modifier {mod.name}",
            ))

    # Check for require/assert with msg.sender
    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__
            if ir_type == "SolidityCall":
                func = getattr(ir, "function", None)
                func_name = str(getattr(func, "name", "") or "").lower() if func else ""
                if func_name in ("require", "assert"):
                    # Check if condition involves msg.sender comparison
                    args = getattr(ir, "arguments", []) or []
                    for arg in args:
                        arg_str = str(arg).lower()
                        if "msg.sender" in arg_str and ("==" in arg_str or "owner" in arg_str):
                            occurrences.append(OperationOccurrence(
                                operation=SemanticOperation.CHECKS_PERMISSION,
                                cfg_order=cfg_order,
                                line_number=_get_line_number(node),
                                detail="require msg.sender check",
                            ))
                            break
        cfg_order += 1

    return occurrences


def detect_modifies_owner(fn: Any) -> List[OperationOccurrence]:
    """Detect modifications to ownership.

    Detects:
    - owner = newOwner
    - _owner modifications
    - transferOwnership patterns
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for var in getattr(fn, "state_variables_written", []) or []:
        var_name = getattr(var, "name", "") or ""
        if _is_owner_var(var_name):
            occurrences.append(OperationOccurrence(
                operation=SemanticOperation.MODIFIES_OWNER,
                cfg_order=cfg_order,
                line_number=_get_line_number(fn),
                detail=f"write {var_name}",
            ))
            cfg_order += 1

    return occurrences


def detect_modifies_roles(fn: Any) -> List[OperationOccurrence]:
    """Detect modifications to roles.

    Detects:
    - Role assignments
    - AccessControl changes
    - Whitelist/blacklist modifications
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for var in getattr(fn, "state_variables_written", []) or []:
        var_name = getattr(var, "name", "") or ""
        if _is_role_var(var_name):
            occurrences.append(OperationOccurrence(
                operation=SemanticOperation.MODIFIES_ROLES,
                cfg_order=cfg_order,
                line_number=_get_line_number(fn),
                detail=f"write {var_name}",
            ))
            cfg_order += 1

    return occurrences


# =============================================================================
# External Interaction Detectors (P1-T4)
# =============================================================================


def detect_calls_external(fn: Any) -> List[OperationOccurrence]:
    """Detect any external calls.

    Detects:
    - High-level external calls
    - Low-level calls (call, delegatecall, staticcall)
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__
            if ir_type in ("HighLevelCall", "LowLevelCall", "ExternalCall"):
                detail = ir_type
                if ir_type == "HighLevelCall":
                    func_name = getattr(ir, "function_name", None)
                    if func_name:
                        detail = f"call {func_name}"
                occurrences.append(OperationOccurrence(
                    operation=SemanticOperation.CALLS_EXTERNAL,
                    cfg_order=cfg_order,
                    line_number=_get_line_number(node),
                    detail=detail,
                ))
                break  # One occurrence per node
        cfg_order += 1

    return occurrences


def detect_calls_untrusted(fn: Any) -> List[OperationOccurrence]:
    """Detect calls to untrusted/user-supplied addresses.

    Detects:
    - Calls where target comes from parameter or storage
    - Calls to non-constant addresses
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    # Get parameter names for untrusted detection
    param_names = {
        _normalize_name(getattr(p, "name", "") or "")
        for p in getattr(fn, "parameters", []) or []
    }

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__
            if ir_type in ("HighLevelCall", "LowLevelCall"):
                # Check if destination is from parameter or looks untrusted
                dest = getattr(ir, "destination", None)
                dest_str = _normalize_name(str(dest) if dest else "")

                # Consider untrusted if destination is a parameter
                if any(param in dest_str for param in param_names if param):
                    occurrences.append(OperationOccurrence(
                        operation=SemanticOperation.CALLS_UNTRUSTED,
                        cfg_order=cfg_order,
                        line_number=_get_line_number(node),
                        detail=f"call to param {dest}",
                    ))
                    break
        cfg_order += 1

    return occurrences


def detect_reads_external_value(fn: Any) -> List[OperationOccurrence]:
    """Detect reads from external contracts.

    Detects:
    - Oracle reads (Chainlink, Uniswap)
    - DEX reserve reads
    - Any external call that returns a value used in computation
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            if type(ir).__name__ == "HighLevelCall":
                func_name = _normalize_name(str(getattr(ir, "function_name", "") or ""))
                # Check if it's an oracle-like read
                if func_name in ORACLE_FUNCTIONS or "get" in func_name or "read" in func_name:
                    # Check if return value is used
                    lvalue = getattr(ir, "lvalue", None)
                    if lvalue:
                        occurrences.append(OperationOccurrence(
                            operation=SemanticOperation.READS_EXTERNAL_VALUE,
                            cfg_order=cfg_order,
                            line_number=_get_line_number(node),
                            detail=f"external read {func_name}",
                        ))
                        break
        cfg_order += 1

    return occurrences


# =============================================================================
# State Management Detectors (P1-T5)
# =============================================================================


def detect_modifies_critical_state(fn: Any) -> List[OperationOccurrence]:
    """Detect writes to privileged/critical state.

    Detects:
    - Writes to owner, roles, fees, treasury
    - Implementation address changes
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for var in getattr(fn, "state_variables_written", []) or []:
        var_name = getattr(var, "name", "") or ""
        if _is_privileged_var(var_name):
            occurrences.append(OperationOccurrence(
                operation=SemanticOperation.MODIFIES_CRITICAL_STATE,
                cfg_order=cfg_order,
                line_number=_get_line_number(fn),
                detail=f"write {var_name}",
            ))
            cfg_order += 1

    return occurrences


def detect_initializes_state(fn: Any) -> List[OperationOccurrence]:
    """Detect initializer patterns.

    Detects:
    - Functions with initializer modifiers
    - Constructor-like initialization patterns
    """
    occurrences: List[OperationOccurrence] = []

    # Check for initializer modifiers
    for mod in getattr(fn, "modifiers", []) or []:
        mod_name = _normalize_name(getattr(mod, "name", "") or "")
        if "initializer" in mod_name or "init" in mod_name:
            occurrences.append(OperationOccurrence(
                operation=SemanticOperation.INITIALIZES_STATE,
                cfg_order=0,
                line_number=_get_line_number(fn),
                detail=f"modifier {mod.name}",
            ))

    # Check if it's a constructor
    if getattr(fn, "is_constructor", False):
        occurrences.append(OperationOccurrence(
            operation=SemanticOperation.INITIALIZES_STATE,
            cfg_order=0,
            line_number=_get_line_number(fn),
            detail="constructor",
        ))

    return occurrences


def detect_reads_oracle(fn: Any) -> List[OperationOccurrence]:
    """Detect oracle reads.

    Detects:
    - Chainlink latestRoundData, latestAnswer
    - Uniswap getReserves, slot0
    - TWAP oracle reads
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            if type(ir).__name__ == "HighLevelCall":
                func_name = _normalize_name(str(getattr(ir, "function_name", "") or ""))
                if func_name in ORACLE_FUNCTIONS:
                    occurrences.append(OperationOccurrence(
                        operation=SemanticOperation.READS_ORACLE,
                        cfg_order=cfg_order,
                        line_number=_get_line_number(node),
                        detail=f"oracle {func_name}",
                    ))
                    break
        cfg_order += 1

    return occurrences


# =============================================================================
# Control Flow Detectors (P1-T6)
# =============================================================================


def detect_loops_over_array(fn: Any) -> List[OperationOccurrence]:
    """Detect loops that iterate over arrays.

    Detects:
    - for loops with array length conditions
    - while loops over dynamic data
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        node_type = str(getattr(node, "type", ""))
        # Check for loop nodes
        if "LOOP" in node_type.upper() or "FOR" in node_type.upper():
            occurrences.append(OperationOccurrence(
                operation=SemanticOperation.LOOPS_OVER_ARRAY,
                cfg_order=cfg_order,
                line_number=_get_line_number(node),
                detail="array loop",
            ))
        cfg_order += 1

    return occurrences


def detect_uses_timestamp(fn: Any) -> List[OperationOccurrence]:
    """Detect block.timestamp usage.

    Detects:
    - block.timestamp reads
    - now (deprecated alias)
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_str = str(ir).lower()
            if "block.timestamp" in ir_str or "now" in ir_str:
                occurrences.append(OperationOccurrence(
                    operation=SemanticOperation.USES_TIMESTAMP,
                    cfg_order=cfg_order,
                    line_number=_get_line_number(node),
                    detail="block.timestamp",
                ))
                break
        cfg_order += 1

    return occurrences


def detect_uses_block_data(fn: Any) -> List[OperationOccurrence]:
    """Detect block.number, blockhash, prevrandao usage.

    Detects:
    - block.number reads
    - blockhash() calls
    - block.prevrandao (formerly block.difficulty)
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_str = str(ir).lower()
            if any(term in ir_str for term in ["block.number", "blockhash", "prevrandao", "block.difficulty"]):
                occurrences.append(OperationOccurrence(
                    operation=SemanticOperation.USES_BLOCK_DATA,
                    cfg_order=cfg_order,
                    line_number=_get_line_number(node),
                    detail="block data",
                ))
                break
        cfg_order += 1

    return occurrences


# =============================================================================
# Arithmetic & Validation Detectors (P1-T7)
# =============================================================================


def detect_performs_division(fn: Any) -> List[OperationOccurrence]:
    """Detect division operations.

    Detects:
    - / operator
    - div() calls
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__
            if ir_type == "Binary":
                op = getattr(ir, "type", None)
                op_str = str(op).lower() if op else ""
                if "div" in op_str or "/" in str(ir):
                    occurrences.append(OperationOccurrence(
                        operation=SemanticOperation.PERFORMS_DIVISION,
                        cfg_order=cfg_order,
                        line_number=_get_line_number(node),
                        detail="division",
                    ))
                    break
        cfg_order += 1

    return occurrences


def detect_performs_multiplication(fn: Any) -> List[OperationOccurrence]:
    """Detect multiplication operations.

    Detects:
    - * operator
    - mul() calls
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__
            if ir_type == "Binary":
                op = getattr(ir, "type", None)
                op_str = str(op).lower() if op else ""
                if "mul" in op_str or "*" in str(ir):
                    occurrences.append(OperationOccurrence(
                        operation=SemanticOperation.PERFORMS_MULTIPLICATION,
                        cfg_order=cfg_order,
                        line_number=_get_line_number(node),
                        detail="multiplication",
                    ))
                    break
        cfg_order += 1

    return occurrences


def detect_validates_input(fn: Any) -> List[OperationOccurrence]:
    """Detect input validation.

    Detects:
    - require() with parameter checks
    - assert() statements
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    # Get parameter names
    param_names = {
        _normalize_name(getattr(p, "name", "") or "")
        for p in getattr(fn, "parameters", []) or []
    }
    param_names.discard("")  # Remove empty strings

    for node in getattr(fn, "nodes", []) or []:
        found = False
        # Check node type for require/assert patterns
        node_type_str = str(getattr(node, "type", "")).upper()

        # Slither uses NodeType.IF for require/assert nodes
        if "IF" in node_type_str or "REQUIRE" in node_type_str or "ASSERT" in node_type_str:
            # Check if the node expression references parameters
            node_str = _normalize_name(str(node))

            # Look for parameter references in the node
            if any(param in node_str for param in param_names if param):
                occurrences.append(OperationOccurrence(
                    operation=SemanticOperation.VALIDATES_INPUT,
                    cfg_order=cfg_order,
                    line_number=_get_line_number(node),
                    detail="require/assert on parameter",
                ))
                found = True

        # Also check IR for SolidityCall with require/assert
        if not found:
            for ir in getattr(node, "irs", []) or []:
                ir_type = type(ir).__name__
                ir_str = _normalize_name(str(ir))

                # Check for require/assert in IR string representation
                if "require" in ir_str or "assert" in ir_str:
                    if any(param in ir_str for param in param_names if param):
                        occurrences.append(OperationOccurrence(
                            operation=SemanticOperation.VALIDATES_INPUT,
                            cfg_order=cfg_order,
                            line_number=_get_line_number(node),
                            detail="require/assert on parameter",
                        ))
                        found = True
                        break

                # Also check SolidityCall specifically
                if ir_type == "SolidityCall":
                    func = getattr(ir, "function", None)
                    func_name = str(getattr(func, "name", "") or "").lower() if func else ""
                    if not func_name:
                        # Try full_name or function string
                        func_name = _normalize_name(str(func) if func else "")

                    if "require" in func_name or "assert" in func_name:
                        # Check arguments for parameters
                        args = getattr(ir, "arguments", []) or []
                        args_str = _normalize_name(" ".join(str(a) for a in args))
                        if any(param in args_str for param in param_names if param):
                            occurrences.append(OperationOccurrence(
                                operation=SemanticOperation.VALIDATES_INPUT,
                                cfg_order=cfg_order,
                                line_number=_get_line_number(node),
                                detail="require/assert on parameter",
                            ))
                            found = True
                            break

        cfg_order += 1

    return occurrences


def detect_emits_event(fn: Any) -> List[OperationOccurrence]:
    """Detect event emissions.

    Detects:
    - emit EventName()
    """
    occurrences: List[OperationOccurrence] = []
    cfg_order = 0

    for node in getattr(fn, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__
            if ir_type == "EventCall":
                event_name = getattr(ir, "name", None)
                occurrences.append(OperationOccurrence(
                    operation=SemanticOperation.EMITS_EVENT,
                    cfg_order=cfg_order,
                    line_number=_get_line_number(node),
                    detail=f"emit {event_name}" if event_name else "emit event",
                ))
                break
        cfg_order += 1

    return occurrences


# =============================================================================
# Main API
# =============================================================================


def derive_all_operations(fn: Any) -> List[OperationOccurrence]:
    """Derive all semantic operations for a function.

    Args:
        fn: A Slither Function object

    Returns:
        List of OperationOccurrence objects, sorted by CFG order
    """
    all_ops: List[OperationOccurrence] = []

    # Value Movement
    all_ops.extend(detect_transfers_value_out(fn))
    all_ops.extend(detect_receives_value_in(fn))
    all_ops.extend(detect_reads_user_balance(fn))
    all_ops.extend(detect_writes_user_balance(fn))

    # Access Control
    all_ops.extend(detect_checks_permission(fn))
    all_ops.extend(detect_modifies_owner(fn))
    all_ops.extend(detect_modifies_roles(fn))

    # External Interaction
    all_ops.extend(detect_calls_external(fn))
    all_ops.extend(detect_calls_untrusted(fn))
    all_ops.extend(detect_reads_external_value(fn))

    # State Management
    all_ops.extend(detect_modifies_critical_state(fn))
    all_ops.extend(detect_initializes_state(fn))
    all_ops.extend(detect_reads_oracle(fn))

    # Control Flow
    all_ops.extend(detect_loops_over_array(fn))
    all_ops.extend(detect_uses_timestamp(fn))
    all_ops.extend(detect_uses_block_data(fn))

    # Arithmetic & Validation
    all_ops.extend(detect_performs_division(fn))
    all_ops.extend(detect_performs_multiplication(fn))
    all_ops.extend(detect_validates_input(fn))
    all_ops.extend(detect_emits_event(fn))

    # Sort by CFG order
    return sorted(all_ops, key=lambda x: x.cfg_order)


def compute_behavioral_signature(operations: List[OperationOccurrence]) -> str:
    """Compute a behavioral signature from operations.

    The signature is a compact notation showing the sequence of operations.
    Example: "R:bal→X:out→W:bal" (vulnerable reentrancy pattern)
             "R:bal→W:bal→X:out" (safe CEI pattern)

    Args:
        operations: List of OperationOccurrence, should be sorted by cfg_order

    Returns:
        Behavioral signature string
    """
    if not operations:
        return ""

    # Sort by CFG order and get unique operations in order
    sorted_ops = sorted(operations, key=lambda x: x.cfg_order)

    # Build signature from unique operations in order
    seen_at_order: Dict[int, Set[str]] = {}
    for op in sorted_ops:
        code = OP_CODES.get(op.operation)
        if code:
            if op.cfg_order not in seen_at_order:
                seen_at_order[op.cfg_order] = set()
            seen_at_order[op.cfg_order].add(code)

    # Flatten to signature
    codes: List[str] = []
    for order in sorted(seen_at_order.keys()):
        for code in sorted(seen_at_order[order]):
            if code not in codes:  # Avoid duplicates
                codes.append(code)

    return "→".join(codes)


def compute_ordering_pairs(operations: List[OperationOccurrence]) -> List[tuple[str, str]]:
    """Compute all ordering pairs from operations.

    For each pair of operations where op1 happens before op2,
    returns (op1.name, op2.name).

    Args:
        operations: List of OperationOccurrence

    Returns:
        List of (before_op, after_op) tuples
    """
    pairs: List[tuple[str, str]] = []
    sorted_ops = sorted(operations, key=lambda x: x.cfg_order)

    for i, op1 in enumerate(sorted_ops):
        for op2 in sorted_ops[i + 1:]:
            pairs.append((op1.operation.name, op2.operation.name))

    return pairs


# =============================================================================
# Registry-Backed Resolution (Phase 5.9)
# =============================================================================


def resolve_operation_name(
    name: str,
    warn_on_deprecated: bool = True,
) -> Optional[str]:
    """Resolve an operation name to its canonical form using the taxonomy registry.

    This function provides registry-backed resolution for operation names,
    supporting legacy aliases, SARIF-normalized names, and deprecation warnings.

    Args:
        name: Operation name (canonical, alias, or SARIF format)
        warn_on_deprecated: Whether to emit deprecation warnings

    Returns:
        Canonical operation name or None if not found

    Example:
        >>> resolve_operation_name("TRANSFERS_ETH")  # Deprecated alias
        'TRANSFERS_VALUE_OUT'
        >>> resolve_operation_name("transfers-token")  # SARIF format
        'TRANSFERS_VALUE_OUT'
        >>> resolve_operation_name("X:out")  # Short code
        'TRANSFERS_VALUE_OUT'
    """
    # Lazy import to avoid circular dependency
    from alphaswarm_sol.kg.taxonomy import ops_registry

    # Try as operation first
    result = ops_registry.resolve_operation(name, warn_on_deprecated=warn_on_deprecated)
    if result:
        return result

    # Try as short code
    result = ops_registry.resolve_short_code(name)
    if result:
        return result

    return None


def get_operation_from_name(name: str) -> Optional[SemanticOperation]:
    """Get SemanticOperation enum from a name using registry resolution.

    Args:
        name: Operation name (canonical, alias, short code, or SARIF format)

    Returns:
        SemanticOperation enum or None if not found
    """
    canonical = resolve_operation_name(name, warn_on_deprecated=False)
    if canonical:
        try:
            return SemanticOperation[canonical]
        except KeyError:
            return None
    return None


def validate_operation_names(names: List[str]) -> tuple[List[str], List[str]]:
    """Validate a list of operation names against the taxonomy registry.

    Args:
        names: List of operation names to validate

    Returns:
        Tuple of (valid_canonical_names, invalid_names)

    Example:
        >>> valid, invalid = validate_operation_names(
        ...     ["TRANSFERS_VALUE_OUT", "UNKNOWN_OP", "transfers-eth"]
        ... )
        >>> valid
        ['TRANSFERS_VALUE_OUT', 'TRANSFERS_VALUE_OUT']
        >>> invalid
        ['UNKNOWN_OP']
    """
    valid: List[str] = []
    invalid: List[str] = []

    for name in names:
        canonical = resolve_operation_name(name, warn_on_deprecated=False)
        if canonical:
            valid.append(canonical)
        else:
            invalid.append(name)

    return valid, invalid


def get_operation_pattern_tags(name: str) -> Set[str]:
    """Get pattern tags for an operation from the taxonomy registry.

    Args:
        name: Operation name

    Returns:
        Set of pattern tags
    """
    from alphaswarm_sol.kg.taxonomy import ops_registry

    tags = ops_registry.get_pattern_tags(name)
    return set(tags)


def get_operation_risk_base(name: str) -> float:
    """Get base risk score for an operation from the taxonomy registry.

    Args:
        name: Operation name

    Returns:
        Base risk score (0-10)
    """
    from alphaswarm_sol.kg.taxonomy import ops_registry

    return ops_registry.get_risk_base(name)


# =============================================================================
# Guard Dominance Classification (Phase 5.9)
# =============================================================================


def classify_guard_dominance(
    guard_node_id: int,
    sink_node_id: int,
    analyzer: Any,
) -> "GuardDominance":
    """Classify the dominance relationship of a guard to a sink.

    This function determines whether a guard (modifier check, require, etc.)
    properly protects a sink (external call, state write, etc.) based on
    dominance analysis.

    Args:
        guard_node_id: CFG node ID of the guard
        sink_node_id: CFG node ID of the sink to protect
        analyzer: DominanceAnalyzer instance

    Returns:
        GuardDominance classification:
        - DOMINATING: Guard dominates sink on all paths
        - BYPASSABLE: Guard exists but can be bypassed
        - PRESENT: Guard exists somewhere in function
        - UNKNOWN: Cannot determine dominance

    Example:
        >>> analyzer = create_analyzer_for_function(fn)
        >>> dominance = classify_guard_dominance(guard_id, sink_id, analyzer)
        >>> if dominance == GuardDominance.BYPASSABLE:
        ...     print("Warning: guard can be bypassed!")
    """
    from alphaswarm_sol.kg.dominance import GuardDominance

    # Handle missing analyzer
    if analyzer is None:
        return GuardDominance.UNKNOWN

    # Check if nodes exist in analyzer
    if not hasattr(analyzer, "_nodes"):
        return GuardDominance.UNKNOWN

    nodes = analyzer._nodes
    if guard_node_id not in nodes:
        return GuardDominance.UNKNOWN
    if sink_node_id not in nodes:
        return GuardDominance.UNKNOWN

    # Check dominance
    if analyzer.dominates(guard_node_id, sink_node_id):
        return GuardDominance.DOMINATING

    # Check reachability - guard exists and can reach sink
    if hasattr(analyzer, "_can_reach") and analyzer._can_reach(guard_node_id, sink_node_id):
        return GuardDominance.BYPASSABLE

    # Guard exists but doesn't reach sink
    return GuardDominance.PRESENT


def classify_modifier_guard_dominance(
    modifier: Any,
    sink_op: OperationOccurrence,
    fn: Any,
) -> "GuardDominance":
    """Classify dominance of a modifier guard to a sink operation.

    This function handles modifier-specific guard classification, accounting
    for modifier entry/exit semantics.

    Args:
        modifier: Slither Modifier object
        sink_op: The operation occurrence to protect
        fn: Slither Function object

    Returns:
        GuardDominance classification
    """
    from alphaswarm_sol.kg.dominance import GuardDominance, create_analyzer_for_function

    # Check if modifier body is available
    modifier_nodes = getattr(modifier, "nodes", []) or []
    if not modifier_nodes:
        return GuardDominance.UNKNOWN

    # Create analyzer for function
    analyzer = create_analyzer_for_function(fn)
    if analyzer is None:
        return GuardDominance.UNKNOWN

    # Modifier entry (node 0 typically) should dominate function body
    # Since modifiers wrap the function, their entry always dominates body
    # unless there's conditional logic in the modifier

    # Check for revert/require in modifier (guard behavior)
    has_guard_behavior = False
    for node in modifier_nodes:
        node_type = str(getattr(node, "type", "")).upper()
        if "THROW" in node_type or "REVERT" in node_type:
            has_guard_behavior = True
            break

        for ir in getattr(node, "irs", []) or []:
            ir_type = type(ir).__name__
            if ir_type == "SolidityCall":
                func = getattr(ir, "function", None)
                func_name = str(getattr(func, "name", "") or "").lower() if func else ""
                if func_name in ("require", "assert", "revert"):
                    has_guard_behavior = True
                    break

    if not has_guard_behavior:
        return GuardDominance.PRESENT

    # Modifier with guard behavior - assume dominating unless proven otherwise
    # In most well-written modifiers, the guard is at the start and dominates _
    return GuardDominance.DOMINATING


def classify_require_guard_dominance(
    require_node_id: int,
    sink_op: OperationOccurrence,
    fn: Any,
) -> "GuardDominance":
    """Classify dominance of a require/assert guard to a sink operation.

    This function handles inline require/assert guards.

    Args:
        require_node_id: CFG node ID of the require/assert
        sink_op: The operation occurrence to protect
        fn: Slither Function object

    Returns:
        GuardDominance classification
    """
    from alphaswarm_sol.kg.dominance import GuardDominance, create_analyzer_for_function

    analyzer = create_analyzer_for_function(fn)
    if analyzer is None:
        return GuardDominance.UNKNOWN

    return classify_guard_dominance(require_node_id, sink_op.cfg_order, analyzer)


def find_guards_for_sink(
    sink_op: OperationOccurrence,
    fn: Any,
) -> List[Dict[str, Any]]:
    """Find all guards that might protect a sink operation.

    This function identifies potential guards (modifiers, require/assert)
    that could protect a sink operation.

    Args:
        sink_op: The operation occurrence to find guards for
        fn: Slither Function object

    Returns:
        List of guard info dictionaries with:
        - type: "modifier" | "require" | "assert"
        - name: Guard name or condition
        - node_id: CFG node ID (if applicable)
        - dominance: GuardDominance classification
    """
    from alphaswarm_sol.kg.dominance import GuardDominance, create_analyzer_for_function

    guards: List[Dict[str, Any]] = []

    # Check modifiers
    for modifier in getattr(fn, "modifiers", []) or []:
        mod_name = getattr(modifier, "name", "") or "unknown"
        dominance = classify_modifier_guard_dominance(modifier, sink_op, fn)
        guards.append({
            "type": "modifier",
            "name": mod_name,
            "node_id": None,
            "dominance": dominance.value,
        })

    # Check require/assert statements
    analyzer = create_analyzer_for_function(fn)
    for idx, node in enumerate(getattr(fn, "nodes", []) or []):
        for ir in getattr(node, "irs", []) or []:
            if type(ir).__name__ == "SolidityCall":
                func = getattr(ir, "function", None)
                func_name = str(getattr(func, "name", "") or "").lower() if func else ""
                if func_name in ("require", "assert"):
                    # Get condition string
                    args = getattr(ir, "arguments", []) or []
                    condition = str(args[0]) if args else "unknown"

                    # Classify dominance
                    dominance = GuardDominance.UNKNOWN
                    if analyzer is not None:
                        dominance = classify_guard_dominance(idx, sink_op.cfg_order, analyzer)

                    guards.append({
                        "type": func_name,
                        "name": condition,
                        "node_id": idx,
                        "dominance": dominance.value,
                    })

    return guards


def get_dominating_guards_for_function(fn: Any) -> Dict[str, List[Dict[str, Any]]]:
    """Get all dominating guards for each sink operation in a function.

    This function builds a comprehensive map of guards protecting each
    potentially vulnerable operation in a function.

    Args:
        fn: Slither Function object

    Returns:
        Dictionary mapping operation name to list of dominating guards
    """
    from alphaswarm_sol.kg.dominance import GuardDominance

    # Sink operations that should be protected
    sink_ops = {
        "TRANSFERS_VALUE_OUT",
        "CALLS_EXTERNAL",
        "CALLS_UNTRUSTED",
        "WRITES_USER_BALANCE",
        "MODIFIES_CRITICAL_STATE",
        "MODIFIES_OWNER",
        "MODIFIES_ROLES",
    }

    result: Dict[str, List[Dict[str, Any]]] = {}
    operations = derive_all_operations(fn)

    for op in operations:
        if op.operation.name not in sink_ops:
            continue

        guards = find_guards_for_sink(op, fn)
        dominating = [
            g for g in guards
            if g["dominance"] == GuardDominance.DOMINATING.value
        ]

        if op.operation.name not in result:
            result[op.operation.name] = []
        result[op.operation.name].extend(dominating)

    return result
