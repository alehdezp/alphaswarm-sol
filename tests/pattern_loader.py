"""Shared pattern loader for all tests.

Uses @lru_cache to load patterns once per process (same pattern as graph_cache.py).
Dogfoods get_patterns() -- the canonical API -- instead of bypassing it.
Works with unittest.TestCase (no pytest fixture dependency).
"""
from __future__ import annotations

from functools import lru_cache

from alphaswarm_sol.queries.patterns import PatternDefinition, get_patterns


# Minimum expected pattern count. As of 2026-02, vulndocs/ contains 466 patterns.
# This threshold catches catastrophic loading failures (wrong directory, broken glob)
# while allowing normal pattern additions/removals.
_MIN_EXPECTED_PATTERNS = 400


@lru_cache(maxsize=1)
def load_all_patterns() -> tuple[PatternDefinition, ...]:
    """Load all vulndocs patterns with caching and validation.

    Returns tuple (not list) for lru_cache hashability.
    Asserts >= _MIN_EXPECTED_PATTERNS patterns on first load as smoke check.
    """
    patterns = get_patterns()  # Uses canonical API -- fails loud on bad path
    assert len(patterns) >= _MIN_EXPECTED_PATTERNS, (
        f"Expected >= {_MIN_EXPECTED_PATTERNS} patterns, got {len(patterns)}. "
        f"Pattern loading may be broken."
    )
    return tuple(patterns)
