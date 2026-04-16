"""Compact output format for LLM consumption.

Task 9.3/9.8: Token-optimized serialization.

Provides 30-40% token reduction vs JSON while remaining readable.
Uses YAML with key abbreviations and detail level filtering.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, Optional, Set

import yaml

from .abbreviations import abbreviate_keys, expand_keys


class DetailLevel(Enum):
    """Output detail levels for context control.

    SUMMARY: Minimal - id, severity, location only (~60% reduction)
    DETAILED: Standard - includes description, evidence (~30% reduction)
    FULL: Everything included (baseline)
    """

    SUMMARY = "summary"
    DETAILED = "detailed"
    FULL = "full"


# Fields to include in SUMMARY mode
SUMMARY_FIELDS: Set[str] = {
    "finding_id",
    "fid",
    "pattern_id",
    "pid",
    "severity",
    "sev",
    "confidence",
    "conf",
    "contract",
    "c",
    "function",
    "fn",
    "line_number",
    "ln",
    "findings",  # Keep findings list
    "items",  # Keep items list
}

# Fields to EXCLUDE in DETAILED mode (verbose)
VERBOSE_FIELDS: Set[str] = {
    "raw_source",
    "ast_dump",
    "slither_output",
    "full_trace",
    "debug_info",
    "source_code",
    "bytecode",
}


class CompactEncoder:
    """Encode VKG data in compact YAML format.

    Token Reduction:
        - Key abbreviations: ~15% reduction
        - YAML vs JSON: ~10% reduction
        - Detail filtering: ~10-20% reduction
        - Total: ~30-40% reduction

    Usage:
        encoder = CompactEncoder(detail=DetailLevel.DETAILED)
        compact = encoder.encode(finding_dict)
        # compact is a YAML string
    """

    def __init__(self, detail: DetailLevel = DetailLevel.DETAILED):
        """Initialize encoder.

        Args:
            detail: Level of detail to include in output
        """
        self.detail = detail

    def encode(self, data: Dict[str, Any]) -> str:
        """Encode data as compact YAML.

        Args:
            data: Dictionary to encode

        Returns:
            Compact YAML string
        """
        # Filter by detail level
        filtered = self._filter_detail(data)

        # Abbreviate keys
        abbreviated = abbreviate_keys(filtered)

        # Convert to YAML
        return yaml.dump(
            abbreviated,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,  # Longer lines = fewer tokens
        )

    def encode_json(self, data: Dict[str, Any]) -> str:
        """Encode as compact JSON (minified with abbreviations).

        Args:
            data: Dictionary to encode

        Returns:
            Minified JSON string with abbreviated keys
        """
        filtered = self._filter_detail(data)
        abbreviated = abbreviate_keys(filtered)
        return json.dumps(abbreviated, separators=(",", ":"))

    def _filter_detail(self, data: Any) -> Any:
        """Filter data based on detail level.

        Args:
            data: Data to filter

        Returns:
            Filtered data
        """
        if self.detail == DetailLevel.FULL:
            return data

        if self.detail == DetailLevel.SUMMARY:
            return self._extract_summary(data)

        # DETAILED: remove verbose fields
        return self._extract_detailed(data)

    def _extract_summary(self, data: Any) -> Any:
        """Extract summary fields only.

        Args:
            data: Data to filter

        Returns:
            Data with only summary fields
        """
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if k in SUMMARY_FIELDS:
                    result[k] = self._extract_summary(v)
            return result
        elif isinstance(data, list):
            return [self._extract_summary(item) for item in data]
        else:
            return data

    def _extract_detailed(self, data: Any) -> Any:
        """Extract detailed fields (exclude verbose).

        Args:
            data: Data to filter

        Returns:
            Data without verbose fields
        """
        if isinstance(data, dict):
            return {
                k: self._extract_detailed(v)
                for k, v in data.items()
                if k not in VERBOSE_FIELDS
            }
        elif isinstance(data, list):
            return [self._extract_detailed(item) for item in data]
        else:
            return data


class CompactDecoder:
    """Decode compact format back to standard dicts."""

    def decode(self, compact_str: str) -> Dict[str, Any]:
        """Decode compact YAML to dictionary.

        Args:
            compact_str: Compact YAML string

        Returns:
            Dictionary with expanded keys
        """
        data = yaml.safe_load(compact_str)
        if data is None:
            return {}
        return expand_keys(data)

    def decode_json(self, compact_str: str) -> Dict[str, Any]:
        """Decode compact JSON to dictionary.

        Args:
            compact_str: Compact JSON string

        Returns:
            Dictionary with expanded keys
        """
        data = json.loads(compact_str)
        return expand_keys(data)


def encode_finding(
    finding: Dict[str, Any],
    detail: DetailLevel = DetailLevel.DETAILED,
) -> str:
    """Convenience function to encode a finding.

    Args:
        finding: Finding dictionary to encode
        detail: Level of detail to include

    Returns:
        Compact YAML string
    """
    return CompactEncoder(detail=detail).encode(finding)


def decode_finding(compact_str: str) -> Dict[str, Any]:
    """Convenience function to decode a finding.

    Args:
        compact_str: Compact YAML string

    Returns:
        Finding dictionary with expanded keys
    """
    return CompactDecoder().decode(compact_str)


def compare_token_counts(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compare token counts between formats.

    Uses approximate token counting (chars/4 is a rough estimate
    for GPT-style tokenization).

    Args:
        data: Dictionary to compare

    Returns:
        Dict with token counts for each format
    """
    json_str = json.dumps(data, indent=2)
    json_min = json.dumps(data, separators=(",", ":"))
    compact_str = CompactEncoder(detail=DetailLevel.DETAILED).encode(data)
    summary_str = CompactEncoder(detail=DetailLevel.SUMMARY).encode(data)

    json_chars = len(json_str)
    compact_chars = len(compact_str)

    reduction = 0
    if json_chars > 0:
        reduction = round((1 - compact_chars / json_chars) * 100, 1)

    return {
        "json_pretty_chars": json_chars,
        "json_minified_chars": len(json_min),
        "compact_chars": compact_chars,
        "summary_chars": len(summary_str),
        "json_tokens_approx": json_chars // 4,
        "compact_tokens_approx": compact_chars // 4,
        "reduction_percent": reduction,
    }


def format_context(
    context_dict: Dict[str, Any],
    detail: DetailLevel = DetailLevel.DETAILED,
    format_type: str = "yaml",
) -> str:
    """Format context for LLM consumption.

    Args:
        context_dict: Context dictionary to format
        detail: Level of detail
        format_type: "yaml" or "json"

    Returns:
        Formatted string
    """
    encoder = CompactEncoder(detail=detail)

    if format_type == "json":
        return encoder.encode_json(context_dict)

    return encoder.encode(context_dict)
