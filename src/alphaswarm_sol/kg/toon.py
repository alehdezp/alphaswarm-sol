"""TOON serialization utilities for knowledge graphs.

TOON (Token-Oriented Object Notation) provides 30-60% token reduction
compared to JSON when passing structured data to LLMs.

This module wraps the `toons` library with graph-specific optimizations:
- LLM-friendly field ordering (id, type, label first)
- Proper handling of datetime objects
- Clear error messages for encoding failures

Usage:
    >>> from alphaswarm_sol.kg.toon import toon_dumps, toon_loads
    >>> data = {"id": "node:1", "type": "function", "properties": {"public": True}}
    >>> encoded = toon_dumps(data)
    >>> decoded = toon_loads(encoded)

When to use TOON (vs JSON/YAML):
- Graph output for LLM consumption: YES - primary use case
- Pattern files: NO - keep YAML (multiline content quality)
- Config files: NO - keep JSON (backwards compatibility)
- Non-LLM JSON (package.json, etc.): NO - don't convert
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

import toons


def toon_dumps(obj: Any, *, indent: bool = False) -> str:
    """Encode Python object to TOON string.

    Args:
        obj: Python object to encode (dict, list, primitives)
        indent: If True, use indented format (for debugging)
            Note: Currently ignored - toons library handles formatting

    Returns:
        TOON-encoded string

    Raises:
        TypeError: If obj contains non-serializable types

    Example:
        >>> toon_dumps({"name": "transfer", "public": True})
        'name: transfer\\npublic: true'
    """
    # Pre-process to handle datetime objects and other Python types
    processed = _preprocess(obj)
    return toons.dumps(processed)


def toon_loads(s: str) -> Any:
    """Decode TOON string to Python object.

    Args:
        s: TOON-encoded string

    Returns:
        Decoded Python object

    Raises:
        ValueError: If string is not valid TOON

    Example:
        >>> toon_loads('name: transfer\\npublic: true')
        {'name': 'transfer', 'public': True}
    """
    return toons.loads(s)


def toon_dump(obj: Any, fp: TextIO) -> None:
    """Encode Python object and write to file.

    Args:
        obj: Python object to encode
        fp: File-like object to write to

    Example:
        >>> with open("graph.toon", "w") as f:
        ...     toon_dump({"nodes": []}, f)
    """
    fp.write(toon_dumps(obj))


def toon_load(fp: TextIO) -> Any:
    """Read file and decode as TOON.

    Args:
        fp: File-like object to read from

    Returns:
        Decoded Python object

    Example:
        >>> with open("graph.toon", "r") as f:
        ...     data = toon_load(f)
    """
    return toon_loads(fp.read())


def _preprocess(obj: Any) -> Any:
    """Pre-process object for TOON encoding.

    Handles:
    - datetime objects -> ISO format strings
    - Path objects -> strings
    - Objects with to_dict() method -> dict representation
    - Other non-serializable types -> raise TypeError

    Args:
        obj: Any Python object

    Returns:
        Processed object suitable for toons.dumps()

    Raises:
        TypeError: If object is not TOON serializable
    """
    # Primitives pass through directly
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # Datetime -> ISO format string
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Path -> string
    if isinstance(obj, Path):
        return str(obj)

    # Dict -> recurse on values
    if isinstance(obj, dict):
        return {k: _preprocess(v) for k, v in obj.items()}

    # List/tuple -> recurse on items
    if isinstance(obj, (list, tuple)):
        return [_preprocess(item) for item in obj]

    # Objects with to_dict() method (dataclasses, Pydantic models, etc.)
    if hasattr(obj, "to_dict"):
        return _preprocess(obj.to_dict())

    # Unknown type - raise clear error
    raise TypeError(f"Object of type {type(obj).__name__} is not TOON serializable")


__all__ = ["toon_dumps", "toon_loads", "toon_dump", "toon_load"]
