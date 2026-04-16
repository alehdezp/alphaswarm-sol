"""Tool Description Compression (Phase 7.1.3-05).

This module provides compression utilities for tool descriptions before
inclusion in LLM context. Compresses verbose sections, dedupes schema
content, and shortens examples to reduce token usage.

Key features:
- Trim verbose sections (long descriptions, detailed examples)
- Dedupe repeated schema patterns
- Shorten common phrases and boilerplate
- Preserve required fields (name, binary, install_hint)
- Configurable compression level

Usage:
    from alphaswarm_sol.tools.description_compress import (
        compress_tool_description,
        compress_tool_descriptions,
        ToolDescriptionCompressor,
    )

    # Quick compression
    compressed = compress_tool_description(tool_info)

    # Batch compression for context
    compressed_batch = compress_tool_descriptions(tool_list, max_tokens=500)

    # Custom compressor
    compressor = ToolDescriptionCompressor(aggressive=True)
    compressed = compressor.compress(tool_info)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Common phrases to abbreviate
PHRASE_ABBREVIATIONS: Dict[str, str] = {
    "Static analyzer for Solidity": "Solidity static analyzer",
    "primary VKG data source": "VKG core",
    "Rust-based Solidity analyzer with custom detectors": "Rust analyzer",
    "Symbolic execution for vulnerability detection": "Symbolic exec",
    "Property-based fuzzer for smart contracts": "Fuzzer",
    "Fast testing framework and toolkit": "Testing toolkit",
    "Pattern-based code analysis": "Pattern analysis",
    "Symbolic bounded model checker": "SMT checker",
    "Parallel fuzzer based on go-ethereum": "Go fuzzer",
    "Solidity compiler": "Compiler",
    "Compilation framework supporting multiple build systems": "Build framework",
    "Download from GitHub releases or": "GitHub or",
    "Install package dependencies": "Install deps",
    "Tool importance tiers": "Tiers",
    "Health status of a tool": "Health info",
    "Static information about a tool": "Tool info",
}

# Schema patterns to dedupe
SCHEMA_DEDUP_PATTERNS = [
    # Remove repeated type declarations
    (r'"type":\s*"string",?\s*', ""),
    (r'"type":\s*"object",?\s*', ""),
    (r'"type":\s*"array",?\s*', ""),
    (r'"type":\s*"number",?\s*', ""),
    (r'"type":\s*"boolean",?\s*', ""),
    # Simplify properties
    (r'"properties":\s*\{\s*\}', "{}"),
    (r'"required":\s*\[\]', ""),
    # Remove descriptions from schema
    (r'"description":\s*"[^"]*",?\s*', ""),
]

# Fields that must be preserved
REQUIRED_FIELDS = {"name", "binary", "install_hint", "install_method", "tier"}

# Fields to trim aggressively
VERBOSE_FIELDS = {"description", "homepage", "examples", "detailed_usage"}


@dataclass
class CompressionStats:
    """Statistics about compression.

    Attributes:
        original_chars: Original character count.
        compressed_chars: Compressed character count.
        savings_percent: Percentage saved.
        phrases_replaced: Number of phrases replaced.
        fields_trimmed: List of fields that were trimmed.
    """

    original_chars: int = 0
    compressed_chars: int = 0
    savings_percent: float = 0.0
    phrases_replaced: int = 0
    fields_trimmed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_chars": self.original_chars,
            "compressed_chars": self.compressed_chars,
            "savings_percent": round(self.savings_percent, 1),
            "phrases_replaced": self.phrases_replaced,
            "fields_trimmed": self.fields_trimmed,
        }


class ToolDescriptionCompressor:
    """Compress tool descriptions for LLM context.

    Applies various compression strategies to reduce token usage while
    preserving essential information.

    Example:
        compressor = ToolDescriptionCompressor()
        compressed = compressor.compress(tool_info_dict)
        print(compressor.last_stats)
    """

    # Approximate chars per token
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        aggressive: bool = False,
        max_description_chars: int = 80,
        max_example_chars: int = 100,
        preserve_fields: Optional[set] = None,
    ):
        """Initialize compressor.

        Args:
            aggressive: Apply aggressive compression (remove more content).
            max_description_chars: Max chars for description fields.
            max_example_chars: Max chars for example content.
            preserve_fields: Additional fields to preserve (beyond REQUIRED_FIELDS).
        """
        self._aggressive = aggressive
        self._max_description = max_description_chars
        self._max_example = max_example_chars
        self._preserve_fields = (preserve_fields or set()) | REQUIRED_FIELDS
        self._last_stats: Optional[CompressionStats] = None

    @property
    def last_stats(self) -> Optional[CompressionStats]:
        """Statistics from last compression."""
        return self._last_stats

    def compress(self, tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a single tool description.

        Args:
            tool_info: Tool information dictionary with fields like:
                - name: Tool name (required)
                - binary: Executable name (required)
                - description: Tool description (will be trimmed)
                - install_hint: Install command (required)
                - homepage: URL (removed in aggressive mode)
                - examples: Usage examples (trimmed)

        Returns:
            Compressed dictionary with same structure.
        """
        if not tool_info:
            return tool_info

        original = str(tool_info)
        original_chars = len(original)

        result: Dict[str, Any] = {}
        phrases_replaced = 0
        fields_trimmed: List[str] = []

        for key, value in tool_info.items():
            # Skip None values
            if value is None:
                continue

            # Always preserve required fields
            if key in self._preserve_fields:
                result[key] = self._compress_value(key, value)
                continue

            # Skip verbose fields in aggressive mode
            if self._aggressive and key in VERBOSE_FIELDS:
                if key == "description":
                    # Keep very short description
                    result[key] = self._truncate(str(value), 50)
                    fields_trimmed.append(key)
                continue

            # Process other fields
            compressed_value = self._compress_value(key, value)
            if compressed_value != value:
                phrases_replaced += 1
            result[key] = compressed_value

        # Calculate stats
        compressed_str = str(result)
        compressed_chars = len(compressed_str)
        savings = (
            ((original_chars - compressed_chars) / original_chars * 100)
            if original_chars > 0
            else 0.0
        )

        self._last_stats = CompressionStats(
            original_chars=original_chars,
            compressed_chars=compressed_chars,
            savings_percent=savings,
            phrases_replaced=phrases_replaced,
            fields_trimmed=fields_trimmed,
        )

        return result

    def _compress_value(self, key: str, value: Any) -> Any:
        """Compress a single field value.

        Args:
            key: Field name.
            value: Field value.

        Returns:
            Compressed value.
        """
        if isinstance(value, str):
            return self._compress_string(key, value)
        elif isinstance(value, dict):
            return self._compress_dict(value)
        elif isinstance(value, list):
            return self._compress_list(key, value)
        return value

    def _compress_string(self, key: str, value: str) -> str:
        """Compress a string value.

        Args:
            key: Field name.
            value: String value.

        Returns:
            Compressed string.
        """
        result = value

        # Apply phrase abbreviations
        for phrase, abbrev in PHRASE_ABBREVIATIONS.items():
            result = result.replace(phrase, abbrev)

        # Truncate based on field type
        if key in ("description", "detailed_description"):
            result = self._truncate(result, self._max_description)
        elif key in ("examples", "usage_example"):
            result = self._truncate(result, self._max_example)
        elif key == "homepage" and self._aggressive:
            # Shorten URLs
            result = self._shorten_url(result)

        return result

    def _compress_dict(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a nested dictionary.

        Args:
            value: Dictionary to compress.

        Returns:
            Compressed dictionary.
        """
        result: Dict[str, Any] = {}
        for k, v in value.items():
            compressed = self._compress_value(k, v)
            if compressed is not None:
                result[k] = compressed
        return result

    def _compress_list(self, key: str, value: List[Any]) -> List[Any]:
        """Compress a list value.

        Args:
            key: Field name.
            value: List value.

        Returns:
            Compressed list.
        """
        if not value:
            return value

        # Limit list length in aggressive mode
        if self._aggressive and len(value) > 3:
            return [self._compress_value(key, v) for v in value[:3]]

        return [self._compress_value(key, v) for v in value]

    def _truncate(self, text: str, max_chars: int) -> str:
        """Truncate text to max chars.

        Args:
            text: Text to truncate.
            max_chars: Maximum characters.

        Returns:
            Truncated text with ellipsis if needed.
        """
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    def _shorten_url(self, url: str) -> str:
        """Shorten a URL.

        Args:
            url: URL to shorten.

        Returns:
            Shortened URL.
        """
        # Remove protocol and www
        shortened = re.sub(r"^https?://(www\.)?", "", url)
        # Take just domain and first path segment
        parts = shortened.split("/")
        if len(parts) > 2:
            return parts[0] + "/" + parts[1]
        return shortened


def compress_tool_description(
    tool_info: Dict[str, Any],
    aggressive: bool = False,
) -> Dict[str, Any]:
    """Compress a single tool description.

    This is the main entry point for tool description compression.
    Applies compression strategies to reduce token usage while
    preserving required fields.

    Args:
        tool_info: Tool information dictionary.
        aggressive: Apply aggressive compression.

    Returns:
        Compressed dictionary.

    Example:
        tool = {"name": "slither", "description": "Static analyzer for Solidity..."}
        compressed = compress_tool_description(tool)
    """
    compressor = ToolDescriptionCompressor(aggressive=aggressive)
    return compressor.compress(tool_info)


def compress_tool_descriptions(
    tools: List[Dict[str, Any]],
    max_tokens: Optional[int] = None,
    aggressive: bool = False,
) -> List[Dict[str, Any]]:
    """Compress multiple tool descriptions for context.

    Compresses a list of tool descriptions. If max_tokens is specified,
    applies increasingly aggressive compression until under budget.

    Args:
        tools: List of tool information dictionaries.
        max_tokens: Maximum tokens for total output (optional).
        aggressive: Start with aggressive compression.

    Returns:
        List of compressed dictionaries.

    Example:
        tools = [{"name": "slither", ...}, {"name": "aderyn", ...}]
        compressed = compress_tool_descriptions(tools, max_tokens=500)
    """
    if not tools:
        return tools

    compressor = ToolDescriptionCompressor(aggressive=aggressive)
    result = [compressor.compress(tool) for tool in tools]

    # If no budget, return as-is
    if max_tokens is None:
        return result

    # Check if under budget
    total_chars = sum(len(str(t)) for t in result)
    estimated_tokens = total_chars // ToolDescriptionCompressor.CHARS_PER_TOKEN

    # If over budget and not already aggressive, try aggressive
    if estimated_tokens > max_tokens and not aggressive:
        compressor = ToolDescriptionCompressor(aggressive=True)
        result = [compressor.compress(tool) for tool in tools]

    # If still over budget, remove non-essential tools
    total_chars = sum(len(str(t)) for t in result)
    estimated_tokens = total_chars // ToolDescriptionCompressor.CHARS_PER_TOKEN

    if estimated_tokens > max_tokens and len(result) > 1:
        # Keep only essential info per tool
        minimal_result = []
        for tool in result:
            minimal = {
                "name": tool.get("name"),
                "binary": tool.get("binary"),
                "install_hint": tool.get("install_hint"),
            }
            minimal_result.append(minimal)
        result = minimal_result

    return result


def compress_for_context(
    tools: List[Dict[str, Any]],
    max_chars: int = 2000,
) -> str:
    """Compress tools into a compact context string.

    Creates a minimal context string suitable for LLM prompts.

    Args:
        tools: List of tool information dictionaries.
        max_chars: Maximum characters for output.

    Returns:
        Compact string representation of tools.

    Example:
        context = compress_for_context(tools, max_chars=1000)
        # Returns: "Tools: slither(pip), aderyn(cargo), mythril(pip)"
    """
    if not tools:
        return "Tools: none"

    # Create compact representation
    parts = []
    for tool in tools:
        name = tool.get("name", "?")
        method = tool.get("install_method", "")
        if method:
            parts.append(f"{name}({method})")
        else:
            parts.append(name)

    result = "Tools: " + ", ".join(parts)

    if len(result) > max_chars:
        # Truncate to fit
        result = result[: max_chars - 3] + "..."

    return result


def estimate_tool_tokens(tool_info: Dict[str, Any]) -> int:
    """Estimate token count for a tool description.

    Args:
        tool_info: Tool information dictionary.

    Returns:
        Estimated token count.
    """
    chars = len(str(tool_info))
    return chars // ToolDescriptionCompressor.CHARS_PER_TOKEN


def get_compression_stats(
    original: Dict[str, Any],
    compressed: Dict[str, Any],
) -> CompressionStats:
    """Calculate compression statistics.

    Args:
        original: Original tool info.
        compressed: Compressed tool info.

    Returns:
        CompressionStats with savings info.
    """
    orig_chars = len(str(original))
    comp_chars = len(str(compressed))
    savings = ((orig_chars - comp_chars) / orig_chars * 100) if orig_chars > 0 else 0.0

    return CompressionStats(
        original_chars=orig_chars,
        compressed_chars=comp_chars,
        savings_percent=savings,
    )
