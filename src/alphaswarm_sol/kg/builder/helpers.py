"""Shared helper functions for VKG builder modules.

This module provides pure utility functions used across builder modules.
All functions are stateless and take explicit parameters instead of using self.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from alphaswarm_sol.kg.schema import Evidence


def source_location(obj: Any) -> tuple[str | None, int | None, int | None]:
    """Extract source location from a Slither object.

    Args:
        obj: Slither object with source_mapping attribute.

    Returns:
        Tuple of (file_path, line_start, line_end). Returns (None, None, None)
        if source mapping is unavailable.
    """
    source_mapping = getattr(obj, "source_mapping", None)
    if not source_mapping:
        return None, None, None

    filename = (
        getattr(source_mapping, "filename_absolute", None)
        or getattr(source_mapping, "filename", None)
        or None
    )

    if filename is None:
        return None, None, None

    # Handle different filename types from Slither
    if hasattr(filename, "absolute"):
        filename = getattr(filename, "absolute")
    elif hasattr(filename, "used"):
        filename = getattr(filename, "used")

    file_path = str(filename) if filename else None

    lines = getattr(source_mapping, "lines", None)
    if not lines:
        return file_path, None, None

    return file_path, min(lines), max(lines)


def relpath(filename: str, project_root: Path) -> str:
    """Convert absolute path to relative path from project root.

    Args:
        filename: The absolute or relative file path.
        project_root: The project root directory.

    Returns:
        Relative path string from project_root, or original filename if
        conversion fails.
    """
    try:
        return str(Path(filename).resolve().relative_to(project_root.resolve()))
    except (ValueError, RuntimeError):
        return str(filename)


def evidence_from_location(
    file_path: str | None,
    line_start: int | None,
    line_end: int | None,
) -> list[Evidence]:
    """Create Evidence list from source location.

    Args:
        file_path: Source file path.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed).

    Returns:
        List containing a single Evidence object, or empty list if file_path
        is None or "unknown".
    """
    if not file_path or file_path == "unknown":
        return []
    return [Evidence(file=file_path, line_start=line_start, line_end=line_end)]


def function_label(fn: Any) -> str:
    """Get function label (full_name, name, or fallback).

    Args:
        fn: Slither function object.

    Returns:
        Function label string, defaulting to "function" if not available.
    """
    return getattr(fn, "full_name", None) or getattr(fn, "name", None) or "function"


def is_access_gate(modifier_name: str) -> bool:
    """Check if modifier name indicates access control.

    Args:
        modifier_name: Name of the modifier.

    Returns:
        True if the modifier name contains access control keywords.
    """
    lowered = modifier_name.lower()
    keywords = ("only", "auth", "role", "admin", "owner", "guardian", "governor")
    return any(key in lowered for key in keywords)


def uses_var_name(variables: list[Any], name: str) -> bool:
    """Check if a variable name is used in a list of variables.

    Args:
        variables: List of Slither variable objects.
        name: Variable name to search for.

    Returns:
        True if the name is found in the variables list.
    """
    for var in variables:
        var_name = getattr(var, "name", None)
        if var_name == name:
            return True
        if name in str(var):
            return True
    return False


def strip_comments(text: str) -> str:
    """Remove comments from Solidity source text.

    Removes both block comments (/* ... */) and line comments (//).

    Args:
        text: Source text to process.

    Returns:
        Text with comments removed.
    """
    # Remove block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Remove line comments
    text = re.sub(r"//.*", "", text)
    return text


def node_expression(node: Any) -> str:
    """Get expression string from a CFG node.

    Args:
        node: Slither CFG node.

    Returns:
        String representation of the node's expression, or empty string
        if not available.
    """
    expression = getattr(node, "expression", None)
    if expression is None:
        return ""
    return str(expression)


def callsite_data_expression(call: Any) -> str:
    """Get the data expression from a call site.

    Extracts the call data, arguments, or expression from various
    call site representations.

    Args:
        call: Slither call site object.

    Returns:
        String representation of the call data or expression.
    """
    for attr in ("call_data", "data", "arguments", "args"):
        value = getattr(call, attr, None)
        if value is not None:
            if isinstance(value, list):
                names = []
                for item in value:
                    name = getattr(item, "name", None)
                    if name:
                        names.append(name)
                if names:
                    return " ".join(names)
            return str(value)
    expression = getattr(call, "expression", None)
    if expression is not None:
        return str(expression)
    return str(call)


def callsite_destination(call: Any) -> str | None:
    """Get the destination address/contract from a call site.

    Args:
        call: Slither call site object.

    Returns:
        String representation of the call destination, or None if not available.
    """
    for attr in ("destination", "called", "to", "expression"):
        value = getattr(call, attr, None)
        if value is not None:
            return str(value)
    return None


def node_id_hash(kind: str, name: str, file_path: str | None, line_start: int | None) -> str:
    """Generate a stable, deterministic node ID using SHA1 hash.

    Args:
        kind: Node kind (e.g., 'function', 'contract', 'state_var').
        name: Entity name.
        file_path: Source file path.
        line_start: Starting line number.

    Returns:
        A hash-based node ID in format "{kind}:{hash[:12]}".
    """
    raw = f"{kind}:{name}:{file_path}:{line_start}"
    return f"{kind}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def edge_id_hash(edge_type: str, source: str, target: str) -> str:
    """Generate a stable, deterministic edge ID using SHA1 hash.

    Args:
        edge_type: Type of edge (e.g., 'CALLS', 'READS', 'WRITES').
        source: Source node ID.
        target: Target node ID.

    Returns:
        A hash-based edge ID in format "edge:{hash[:12]}".
    """
    raw = f"{edge_type}:{source}:{target}"
    return f"edge:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def is_user_controlled_destination(destination: str, parameter_names: list[str]) -> bool:
    """Check if a call destination is user controlled.

    Args:
        destination: String representation of call destination.
        parameter_names: List of function parameter names.

    Returns:
        True if destination appears to be controlled by user input.
    """
    lowered = destination.lower()
    if "msg.sender" in lowered or "tx.origin" in lowered:
        return True
    return any(name.lower() == lowered or name.lower() in lowered for name in parameter_names)


def is_user_controlled_expression(
    expression: Any,
    parameter_names: list[str],
    *,
    allow_msg_value: bool = False,
) -> bool:
    """Check if an expression is user controlled.

    Args:
        expression: Expression to analyze (can be Any type from Slither).
        parameter_names: List of function parameter names.
        allow_msg_value: Whether msg.value counts as user controlled.

    Returns:
        True if expression appears to be controlled by user input.
    """
    if isinstance(expression, list):
        for item in expression:
            name = getattr(item, "name", None)
            if name and any(param.lower() == name.lower() for param in parameter_names):
                return True
        text = " ".join(str(item) for item in expression).lower()
    else:
        text = str(expression).lower()

    if allow_msg_value and "msg.value" in text:
        return True
    if "msg.sender" in text or "tx.origin" in text:
        return True
    return any(name.lower() in text for name in parameter_names)


def get_source_lines(file_path: str, project_root: Path, cache: dict[str, list[str]]) -> list[str]:
    """Get source lines for a file with caching.

    Args:
        file_path: Path to source file.
        project_root: Project root directory.
        cache: Dictionary to use for caching results.

    Returns:
        List of source lines, or empty list if file cannot be read.
    """
    cached = cache.get(file_path)
    if cached is not None:
        return cached

    path = Path(file_path)
    if not path.is_absolute():
        path = project_root / file_path
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        cache[file_path] = []
        return []

    lines = text.splitlines()
    cache[file_path] = lines
    return lines


def get_source_slice(
    file_path: str | None,
    line_start: int | None,
    line_end: int | None,
    project_root: Path,
    cache: dict[str, list[str]],
) -> str:
    """Get a slice of source code from a file.

    Args:
        file_path: Path to source file.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed, inclusive).
        project_root: Project root directory.
        cache: Dictionary to use for line caching.

    Returns:
        Source code slice as a string, or empty string if unavailable.
    """
    if not file_path or line_start is None or line_end is None:
        return ""

    lines = get_source_lines(file_path, project_root, cache)
    if not lines:
        return ""

    # Convert to 0-indexed
    start = max(line_start - 1, 0)
    end = min(line_end, len(lines))
    return "\n".join(lines[start:end])


def is_hardcoded_gas(gas_value: Any) -> bool:
    """Check if a gas value is hardcoded (literal number).

    Args:
        gas_value: Gas value from Slither.

    Returns:
        True if the gas value is a hardcoded numeric literal.
    """
    text = str(gas_value).strip().lower()
    return bool(re.fullmatch(r"0x[0-9a-f]+|\d+", text))


def normalize_state_mutability(fn: Any) -> str:
    """Normalize function state mutability to standard values.

    Args:
        fn: Slither function object.

    Returns:
        Normalized state mutability string: 'view', 'pure', 'payable', or 'nonpayable'.
    """
    raw = getattr(fn, "state_mutability", None) or getattr(fn, "mutability", None)
    if raw is None:
        return "nonpayable"

    raw_str = str(raw).lower()
    if raw_str in ("view", "pure", "payable"):
        return raw_str
    if raw_str == "nonpayable" or raw_str == "non_payable":
        return "nonpayable"
    return "nonpayable"


def classify_parameter_types(parameters: list[Any]) -> dict[str, list[str]]:
    """Classify parameters into categories by type.

    Args:
        parameters: List of Slither parameter objects.

    Returns:
        Dictionary with keys: 'address', 'array', 'amount', 'bytes', 'threshold',
        'pagination', 'nonce', 'string', each containing list of parameter names.
    """
    result: dict[str, list[str]] = {
        "address": [],
        "array": [],
        "amount": [],
        "bytes": [],
        "threshold": [],
        "pagination": [],
        "nonce": [],
        "string": [],
    }

    for param in parameters:
        name = getattr(param, "name", None)
        if not name:
            continue

        param_type = str(getattr(param, "type", "") or "").lower()
        name_lower = name.lower()

        # Type-based classification
        if "address" in param_type:
            result["address"].append(name)
        if "[]" in param_type or "array" in param_type:
            result["array"].append(name)
        if "bytes" in param_type:
            result["bytes"].append(name)
        if "string" in param_type:
            result["string"].append(name)

        # Name-based classification
        if any(token in name_lower for token in ("amount", "value", "amt", "qty", "quantity")):
            result["amount"].append(name)
        if any(token in name_lower for token in ("threshold", "quorum", "mincount")):
            result["threshold"].append(name)
        if any(token in name_lower for token in ("offset", "limit", "page", "cursor", "skip")):
            result["pagination"].append(name)
        if any(token in name_lower for token in ("nonce", "counter", "sequence", "index", "txid")):
            result["nonce"].append(name)

    return result


def node_type_name(node: Any) -> str:
    """Get the lowercase type name of a CFG node.

    Args:
        node: Slither CFG node.

    Returns:
        Lowercase string representing the node type.
    """
    node_type = getattr(node, "type", None)
    name = getattr(node_type, "name", None)
    if name:
        return str(name).lower()
    return str(node_type).lower()


def is_loop_start(node: Any) -> bool:
    """Check if a CFG node is a loop start.

    Args:
        node: Slither CFG node.

    Returns:
        True if the node represents a loop start.
    """
    name = node_type_name(node)
    return "startloop" in name or "loopstart" in name


def is_loop_end(node: Any) -> bool:
    """Check if a CFG node is a loop end.

    Args:
        node: Slither CFG node.

    Returns:
        True if the node represents a loop end.
    """
    name = node_type_name(node)
    return "endloop" in name or "loopend" in name


def node_has_external_call(node: Any) -> bool:
    """Check if a CFG node contains an external call.

    Args:
        node: Slither CFG node.

    Returns:
        True if the node contains an external call IR.
    """
    for ir in getattr(node, "irs", []) or []:
        name = type(ir).__name__
        if name in {"LowLevelCall", "HighLevelCall", "ExternalCall"}:
            return True
    return False


def node_has_delete(node: Any) -> bool:
    """Check if a CFG node contains a delete operation.

    Args:
        node: Slither CFG node.

    Returns:
        True if the node contains a delete operation.
    """
    expression = node_expression(node)
    if "delete" in expression.lower():
        return True
    for ir in getattr(node, "irs", []) or []:
        ir_name = type(ir).__name__.lower()
        if "delete" in ir_name or "delete" in str(ir).lower():
            return True
    return False


__all__ = [
    # Source location helpers
    "source_location",
    "relpath",
    "evidence_from_location",
    "get_source_lines",
    "get_source_slice",
    # Function/node helpers
    "function_label",
    "is_access_gate",
    "uses_var_name",
    "strip_comments",
    "node_expression",
    "callsite_data_expression",
    "callsite_destination",
    "normalize_state_mutability",
    # ID generation
    "node_id_hash",
    "edge_id_hash",
    # Control flow helpers
    "is_user_controlled_destination",
    "is_user_controlled_expression",
    "is_hardcoded_gas",
    # Parameter classification
    "classify_parameter_types",
    # CFG node helpers
    "node_type_name",
    "is_loop_start",
    "is_loop_end",
    "node_has_external_call",
    "node_has_delete",
]
