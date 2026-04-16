"""Output formatting modules for VKG.

Task 9.3/9.8: Token-optimized serialization.

This module provides compact output formats for LLM consumption,
achieving 30-40% token reduction while maintaining readability.
"""

from .abbreviations import (
    KEY_ABBREVIATIONS,
    KEY_EXPANSIONS,
    VALUE_ABBREVIATIONS,
    VALUE_EXPANSIONS,
    abbreviate_keys,
    abbreviate_value,
    expand_keys,
    expand_value,
    get_abbreviation,
    get_expansion,
)
from .compact import (
    CompactDecoder,
    CompactEncoder,
    DetailLevel,
    compare_token_counts,
    decode_finding,
    encode_finding,
    format_context,
)

__all__ = [
    # Abbreviations
    "KEY_ABBREVIATIONS",
    "KEY_EXPANSIONS",
    "VALUE_ABBREVIATIONS",
    "VALUE_EXPANSIONS",
    "abbreviate_keys",
    "abbreviate_value",
    "expand_keys",
    "expand_value",
    "get_abbreviation",
    "get_expansion",
    # Compact encoder/decoder
    "CompactEncoder",
    "CompactDecoder",
    "DetailLevel",
    "encode_finding",
    "decode_finding",
    "compare_token_counts",
    "format_context",
]
