"""Regression tests for pattern loading architecture.

Prevents the silent-failure bug where PatternStore returned []
for nonexistent directories, causing 891 tests to test nothing.

These tests act as a permanent safety net. If anyone reintroduces
silent pattern loading or references the old broken directory path,
these tests will catch it immediately.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from alphaswarm_sol.queries.errors import (
    EmptyPatternStoreError,
    PatternDirectoryNotFoundError,
    PatternLoadError,
)
from alphaswarm_sol.queries.patterns import PatternStore, get_patterns
from tests.pattern_loader import _MIN_EXPECTED_PATTERNS


class TestPatternDiscovery:
    """Verify the canonical pattern loading path works."""

    def test_vulndocs_directory_exists(self) -> None:
        assert Path("vulndocs").exists(), "vulndocs/ directory must exist in project root"

    def test_get_patterns_returns_non_empty(self) -> None:
        patterns = get_patterns()
        assert len(patterns) >= _MIN_EXPECTED_PATTERNS, (
            f"Expected >= {_MIN_EXPECTED_PATTERNS} patterns, got {len(patterns)}"
        )

    def test_get_patterns_default_matches_explicit(self) -> None:
        default = get_patterns()
        explicit = get_patterns(Path("vulndocs"))
        assert len(default) == len(explicit)


class TestLoudFailure:
    """Verify pattern loading raises on bad paths -- never silently returns []."""

    def test_get_patterns_raises_on_missing_dir(self) -> None:
        with pytest.raises(PatternDirectoryNotFoundError) as exc_info:
            get_patterns(Path("nonexistent_dir"))
        assert exc_info.value.path == Path("nonexistent_dir")

    def test_load_vulndocs_patterns_raises_on_missing_dir(self) -> None:
        with pytest.raises(PatternDirectoryNotFoundError):
            PatternStore.load_vulndocs_patterns(Path("nonexistent_dir"))

    def test_pattern_store_load_raises_on_missing_dir(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with pytest.raises(PatternDirectoryNotFoundError):
                PatternStore(Path("nonexistent_dir")).load()

    def test_exception_hierarchy(self) -> None:
        """All pattern exceptions inherit from PatternLoadError."""
        with pytest.raises(PatternLoadError):
            get_patterns(Path("nonexistent_dir"))

    def test_pattern_store_rejects_non_path(self) -> None:
        with pytest.raises(TypeError):
            PatternStore("not_a_path")  # type: ignore[arg-type]


class TestNoLegacyPaths:
    """Ensure no code references the old 'patterns' directory."""

    # Build the forbidden patterns dynamically to avoid this file triggering itself.
    _LEGACY_DOUBLE = 'Path("' + 'patterns")'
    _LEGACY_SINGLE = "Path('" + "patterns')"

    def test_no_legacy_patterns_path_in_tests(self) -> None:
        """No test file should reference the old broken 'patterns' directory path."""
        violations: list[str] = []
        for test_file in sorted(Path("tests").glob("test_*.py")):
            if test_file.name == "test_pattern_loading_regression.py":
                continue  # skip self
            source = test_file.read_text()
            if self._LEGACY_DOUBLE in source or self._LEGACY_SINGLE in source:
                violations.append(test_file.name)
        assert not violations, f"Legacy patterns path found in: {violations}"

    def test_no_legacy_patterns_path_in_source(self) -> None:
        """No source file should default to the old broken 'patterns' directory path."""
        violations: list[str] = []
        for src_file in sorted(Path("src").rglob("*.py")):
            source = src_file.read_text()
            if self._LEGACY_DOUBLE in source or self._LEGACY_SINGLE in source:
                violations.append(str(src_file))
        assert not violations, f"Legacy patterns path found in: {violations}"
