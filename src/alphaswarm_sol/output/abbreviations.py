"""Key abbreviations for compact output.

Task 9.3/9.8: Token-optimized serialization abbreviations.

These abbreviations reduce token count while remaining readable.
The mapping is bidirectional - keys can be abbreviated and expanded.
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

# Full key -> abbreviated key
KEY_ABBREVIATIONS: Dict[str, str] = {
    # Identifiers
    "finding_id": "fid",
    "pattern_id": "pid",
    "contract": "c",
    "function": "fn",
    "function_id": "fnid",
    # Metadata
    "severity": "sev",
    "confidence": "conf",
    "line_number": "ln",
    "column_number": "col",
    "file_path": "fp",
    "timestamp": "ts",
    # Content
    "description": "desc",
    "recommendation": "rec",
    "evidence": "ev",
    "properties": "props",
    "metadata": "meta",
    # Types
    "external_call": "xcall",
    "state_variable": "svar",
    "state_read": "sr",
    "state_write": "sw",
    "modifier": "mod",
    "visibility": "vis",
    # Graph elements
    "callers": "clrs",
    "callees": "cles",
    "call_type": "ct",
    "target_id": "tid",
    # Analysis
    "operations": "ops",
    "risk_score": "risk",
    "category": "cat",
    "subcategory": "sub",
    # Context
    "items_included": "incl",
    "items_filtered": "filt",
    "bytes_sent": "bytes",
    "policy_level": "plvl",
}

# Abbreviated -> full key (reverse mapping)
KEY_EXPANSIONS: Dict[str, str] = {v: k for k, v in KEY_ABBREVIATIONS.items()}

# Common value abbreviations (severity, visibility, etc.)
VALUE_ABBREVIATIONS: Dict[str, str] = {
    # Severity levels
    "critical": "CRIT",
    "high": "HIGH",
    "medium": "MED",
    "low": "LOW",
    "informational": "INFO",
    # Visibility
    "public": "pub",
    "external": "ext",
    "internal": "int",
    "private": "priv",
    # Status
    "pending": "pend",
    "complete": "done",
    "in_progress": "prog",
    # Boolean-like
    "true": "T",
    "false": "F",
    # Call types
    "external_call": "xcall",
    "delegate_call": "dcall",
    "static_call": "scall",
}

# Reverse mapping for values
VALUE_EXPANSIONS: Dict[str, str] = {v: k for k, v in VALUE_ABBREVIATIONS.items()}


def abbreviate_keys(data: Any) -> Any:
    """Recursively abbreviate keys in a dictionary.

    Also abbreviates known string values.

    Args:
        data: Dictionary, list, or value to process

    Returns:
        Data with abbreviated keys and values

    Example:
        >>> abbreviate_keys({"severity": "critical"})
        {"sev": "CRIT"}
    """
    if isinstance(data, dict):
        return {
            KEY_ABBREVIATIONS.get(k, k): abbreviate_keys(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [abbreviate_keys(item) for item in data]
    elif isinstance(data, str):
        return VALUE_ABBREVIATIONS.get(data, data)
    else:
        return data


def expand_keys(data: Any) -> Any:
    """Recursively expand abbreviated keys back to full names.

    Also expands known abbreviated values.

    Args:
        data: Dictionary, list, or value to process

    Returns:
        Data with expanded keys and values

    Example:
        >>> expand_keys({"sev": "CRIT"})
        {"severity": "critical"}
    """
    if isinstance(data, dict):
        return {
            KEY_EXPANSIONS.get(k, k): expand_keys(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [expand_keys(item) for item in data]
    elif isinstance(data, str):
        return VALUE_EXPANSIONS.get(data, data)
    else:
        return data


def abbreviate_value(value: str) -> str:
    """Abbreviate a single value.

    Args:
        value: Value to abbreviate

    Returns:
        Abbreviated value or original if not in mapping
    """
    return VALUE_ABBREVIATIONS.get(value, value)


def expand_value(value: str) -> str:
    """Expand a single abbreviated value.

    Args:
        value: Abbreviated value to expand

    Returns:
        Expanded value or original if not in mapping
    """
    return VALUE_EXPANSIONS.get(value, value)


def get_abbreviation(key: str) -> str:
    """Get abbreviation for a key.

    Args:
        key: Full key name

    Returns:
        Abbreviated key or original if not in mapping
    """
    return KEY_ABBREVIATIONS.get(key, key)


def get_expansion(key: str) -> str:
    """Get full name for an abbreviated key.

    Args:
        key: Abbreviated key

    Returns:
        Full key name or original if not in mapping
    """
    return KEY_EXPANSIONS.get(key, key)
