"""Tests for vulndocs centralized resolution module.

Plan 3.1c.1-01 Task 5: Unit and integration tests for vulndocs_read_path(),
vulndocs_write_path(), _assert_single_vulndocs_root(), and callsite migrations.
"""

from __future__ import annotations

import logging
import os
import tempfile
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest

from alphaswarm_sol.vulndocs.resolution import (
    VulndocsConfigError,
    VulndocsPathConflict,
    _assert_single_vulndocs_root,
    _BUNDLED_DATA_SUBPATH,
    vulndocs_read_path,
    vulndocs_write_path,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensure resolution env vars are clean for every test."""
    monkeypatch.delenv("ALPHASWARM_VULNDOCS_DIR", raising=False)
    monkeypatch.delenv("ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK", raising=False)
    yield


@pytest.fixture
def tmp_vulndocs(tmp_path: Path) -> Path:
    """Create a temporary vulndocs directory with YAML content."""
    vd = tmp_path / "vulndocs"
    patterns_dir = vd / "reentrancy" / "classic" / "patterns"
    patterns_dir.mkdir(parents=True)
    (patterns_dir / "re-001.yaml").write_text(
        "id: re-001\ntitle: Classic Reentrancy\ntier: A\n"
    )
    return vd


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Create an empty directory."""
    d = tmp_path / "empty"
    d.mkdir()
    return d


# ──────────────────────────────────────────────
# Unit tests: vulndocs_read_path
# ──────────────────────────────────────────────


class TestReadPath:
    def test_read_path_returns_traversable(self) -> None:
        """vulndocs_read_path() returns a Traversable (may also be Path)."""
        result = vulndocs_read_path()
        assert isinstance(result, Traversable), (
            f"Expected Traversable, got {type(result).__name__}"
        )

    def test_read_path_from_non_project_cwd(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """vulndocs_read_path() works even when cwd is /tmp (non-project dir)."""
        monkeypatch.chdir(tempfile.gettempdir())
        result = vulndocs_read_path()
        assert isinstance(result, Traversable)
        # Should have some content (categories or data)
        children = list(result.iterdir())
        assert len(children) > 0, "vulndocs should have content from non-project cwd"

    def test_read_path_navigates_categories(self) -> None:
        """The returned Traversable can navigate vulndocs categories."""
        result = vulndocs_read_path()
        children = list(result.iterdir())
        child_names = [c.name for c in children]
        # Should contain at least some known categories
        assert "reentrancy" in child_names or len(children) > 5, (
            f"Expected vulndocs categories, got: {child_names[:10]}"
        )


# ──────────────────────────────────────────────
# Unit tests: vulndocs_write_path
# ──────────────────────────────────────────────


class TestWritePath:
    def test_write_path_returns_path(self) -> None:
        """vulndocs_write_path() returns a concrete Path, not just Traversable."""
        result = vulndocs_write_path()
        assert isinstance(result, Path), (
            f"Expected Path, got {type(result).__name__}"
        )

    def test_write_path_is_under_writable_directory(self) -> None:
        """The write path's parent directory is writable."""
        result = vulndocs_write_path()
        parent = result.parent
        assert parent.exists(), f"Parent directory doesn't exist: {parent}"
        assert os.access(parent, os.W_OK), f"Parent not writable: {parent}"


# ──────────────────────────────────────────────
# Unit tests: ALPHASWARM_VULNDOCS_DIR override
# ──────────────────────────────────────────────


class TestEnvOverride:
    def test_env_override_read(
        self, monkeypatch: pytest.MonkeyPatch, tmp_vulndocs: Path
    ) -> None:
        """ALPHASWARM_VULNDOCS_DIR overrides vulndocs_read_path()."""
        monkeypatch.setenv("ALPHASWARM_VULNDOCS_DIR", str(tmp_vulndocs))
        result = vulndocs_read_path()
        assert isinstance(result, Path)
        assert result == tmp_vulndocs

    def test_env_override_write(
        self, monkeypatch: pytest.MonkeyPatch, tmp_vulndocs: Path
    ) -> None:
        """ALPHASWARM_VULNDOCS_DIR overrides vulndocs_write_path()."""
        monkeypatch.setenv("ALPHASWARM_VULNDOCS_DIR", str(tmp_vulndocs))
        result = vulndocs_write_path()
        assert isinstance(result, Path)
        assert result == tmp_vulndocs

    def test_env_override_nonexistent_raises(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """ALPHASWARM_VULNDOCS_DIR pointing to nonexistent path raises VulndocsConfigError."""
        nonexistent = tmp_path / "does_not_exist"
        monkeypatch.setenv("ALPHASWARM_VULNDOCS_DIR", str(nonexistent))
        with pytest.raises(VulndocsConfigError, match="does not exist"):
            vulndocs_read_path()

    def test_env_override_not_directory_raises(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """ALPHASWARM_VULNDOCS_DIR pointing to a file raises VulndocsConfigError."""
        a_file = tmp_path / "not_a_dir.txt"
        a_file.write_text("I am a file")
        monkeypatch.setenv("ALPHASWARM_VULNDOCS_DIR", str(a_file))
        with pytest.raises(VulndocsConfigError, match="not a directory"):
            vulndocs_read_path()

    def test_env_override_empty_dir_warns(
        self,
        monkeypatch: pytest.MonkeyPatch,
        empty_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """ALPHASWARM_VULNDOCS_DIR pointing to empty dir logs WARNING."""
        monkeypatch.setenv("ALPHASWARM_VULNDOCS_DIR", str(empty_dir))
        with caplog.at_level(logging.WARNING):
            result = vulndocs_read_path()
        assert result == empty_dir
        assert "no YAML files" in caplog.text


# ──────────────────────────────────────────────
# Unit tests: Dual-root conflict detection
# ──────────────────────────────────────────────


class TestDualRoot:
    def test_dual_root_detection(
        self, monkeypatch: pytest.MonkeyPatch, tmp_vulndocs: Path
    ) -> None:
        """Dual roots with different paths and YAML files raises VulndocsPathConflict."""
        # Simulate: importlib.resources returns tmp_vulndocs,
        # __file__-relative returns a DIFFERENT path with YAMLs
        other_root = tmp_vulndocs.parent / "other_vulndocs"
        other_patterns = other_root / "access-control" / "patterns"
        other_patterns.mkdir(parents=True)
        (other_patterns / "ac-001.yaml").write_text("id: ac-001\n")

        monkeypatch.delenv("ALPHASWARM_VULNDOCS_DIR", raising=False)
        monkeypatch.delenv("ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK", raising=False)

        with patch(
            "alphaswarm_sol.vulndocs.resolution._traversable_has_yamls",
            return_value=True,
        ), patch(
            "alphaswarm_sol.vulndocs.resolution.importlib.resources.files",
        ) as mock_files, patch(
            "alphaswarm_sol.vulndocs.resolution._file_relative_vulndocs",
            return_value=other_root,
        ):
            # Make importlib return a Path different from _file_relative
            mock_files.return_value.joinpath.return_value = tmp_vulndocs

            with pytest.raises(VulndocsPathConflict, match="Dual vulndocs roots"):
                _assert_single_vulndocs_root()

    def test_dual_root_suppression(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK=1 suppresses the check."""
        monkeypatch.setenv("ALPHASWARM_SKIP_VULNDOCS_CONFLICT_CHECK", "1")
        # Should not raise regardless of state
        _assert_single_vulndocs_root()


# ──────────────────────────────────────────────
# Unit tests: Traversable API contract
# ──────────────────────────────────────────────


class TestTraversableContract:
    def test_traversable_mock_rejects_fspath(self) -> None:
        """A Traversable mock that raises TypeError on __fspath__ still works
        with _walk_pattern_files, proving no implicit Path cast occurs."""
        from alphaswarm_sol.queries.patterns import _walk_pattern_files

        class MockTraversable:
            """Traversable that rejects __fspath__ (like zip-backed resources)."""

            def __init__(self, name: str, children: list | None = None) -> None:
                self.name = name
                self._children = children or []

            def __fspath__(self) -> str:
                raise TypeError("Cannot convert Traversable to filesystem path")

            def iterdir(self) -> Iterator:
                return iter(self._children)

            def is_dir(self) -> bool:
                return bool(self._children)

            def is_file(self) -> bool:
                return not self._children

            def read_text(self, encoding: str = "utf-8") -> str:
                return "id: mock-001\ntitle: Mock Pattern\ntier: A\n"

            def open(self, mode: str = "r", *args, **kwargs):
                raise TypeError("Cannot open Traversable as file")

            def joinpath(self, *args):
                return self

        # Build a mock tree: root -> reentrancy -> classic -> patterns -> re-001.yaml
        yaml_file = MockTraversable("re-001.yaml")
        patterns_dir = MockTraversable("patterns", [yaml_file])
        classic_dir = MockTraversable("classic", [patterns_dir])
        reentrancy_dir = MockTraversable("reentrancy", [classic_dir])
        root = MockTraversable("vulndocs", [reentrancy_dir])

        # This should work using only Traversable API
        results = _walk_pattern_files(root)
        assert len(results) == 1
        assert results[0].name == "re-001.yaml"

        # Verify that __fspath__ would fail if called
        with pytest.raises(TypeError, match="Cannot convert"):
            os.fspath(root)


# ──────────────────────────────────────────────
# Integration tests
# ──────────────────────────────────────────────


class TestIntegration:
    def test_get_patterns_from_non_project_cwd(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_patterns() succeeds when cwd is /tmp (the Plan 12 Batch 1 failure scenario)."""
        monkeypatch.chdir(tempfile.gettempdir())
        from alphaswarm_sol.queries.patterns import get_patterns

        patterns = get_patterns()
        assert len(patterns) > 0, "Should load patterns from non-project cwd"

    def test_patterns_count_unchanged(self) -> None:
        """Pattern count matches what we'd get from the project root vulndocs/."""
        from alphaswarm_sol.queries.patterns import get_patterns, PatternStore

        # Load via centralized resolution
        resolved_patterns = get_patterns()

        # Load directly from project root for comparison
        project_vulndocs = Path(__file__).parent.parent / "vulndocs"
        if project_vulndocs.is_dir():
            direct_patterns = PatternStore.load_vulndocs_patterns(project_vulndocs)
            assert len(resolved_patterns) == len(direct_patterns), (
                f"Pattern count mismatch: resolved={len(resolved_patterns)}, "
                f"direct={len(direct_patterns)}"
            )
        else:
            # If running from a non-standard location, just verify we got patterns
            assert len(resolved_patterns) > 100, (
                f"Expected 100+ patterns, got {len(resolved_patterns)}"
            )
