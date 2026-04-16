"""Phase 19: Incremental Build Support.

This module provides functionality for detecting changes and
performing incremental builds of the knowledge graph.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class FileState:
    """State of a file for change detection.

    Attributes:
        path: File path
        hash: Content hash
        mtime: Modification time
        size: File size
    """
    path: str
    hash: str
    mtime: float
    size: int

    @classmethod
    def from_path(cls, path: Path) -> "FileState":
        """Create FileState from path.

        Args:
            path: Path to file

        Returns:
            FileState
        """
        stat = path.stat()
        with open(path, 'rb') as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()

        return cls(
            path=str(path),
            hash=content_hash,
            mtime=stat.st_mtime,
            size=stat.st_size,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "hash": self.hash,
            "mtime": self.mtime,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileState":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            hash=data["hash"],
            mtime=data["mtime"],
            size=data["size"],
        )


@dataclass
class ChangeSet:
    """Set of detected changes.

    Attributes:
        added: Newly added files
        modified: Modified files
        deleted: Deleted files
        unchanged: Unchanged files
    """
    added: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.modified or self.deleted)

    @property
    def changed_files(self) -> List[str]:
        """Get all changed files (added + modified)."""
        return self.added + self.modified

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.added) + len(self.modified) + len(self.deleted)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "unchanged": self.unchanged,
            "has_changes": self.has_changes,
            "total_changes": self.total_changes,
        }


class ChangeDetector:
    """Detects changes in source files.

    Compares current file states against stored baseline to
    identify added, modified, and deleted files.
    """

    def __init__(self, extensions: Optional[List[str]] = None):
        """Initialize detector.

        Args:
            extensions: File extensions to track (default: .sol)
        """
        self.extensions = extensions or [".sol"]
        self._baseline: Dict[str, FileState] = {}

    def scan_directory(self, directory: Path) -> Dict[str, FileState]:
        """Scan directory for source files.

        Args:
            directory: Directory to scan

        Returns:
            Dict mapping path to FileState
        """
        states: Dict[str, FileState] = {}

        for ext in self.extensions:
            for path in directory.rglob(f"*{ext}"):
                if path.is_file():
                    state = FileState.from_path(path)
                    states[state.path] = state

        return states

    def set_baseline(self, states: Dict[str, FileState]) -> None:
        """Set baseline for change detection.

        Args:
            states: File states to use as baseline
        """
        self._baseline = states

    def detect_changes(self, current: Dict[str, FileState]) -> ChangeSet:
        """Detect changes from baseline.

        Args:
            current: Current file states

        Returns:
            ChangeSet with detected changes
        """
        changeset = ChangeSet()

        baseline_paths = set(self._baseline.keys())
        current_paths = set(current.keys())

        # Added files
        for path in current_paths - baseline_paths:
            changeset.added.append(path)

        # Deleted files
        for path in baseline_paths - current_paths:
            changeset.deleted.append(path)

        # Modified or unchanged
        for path in baseline_paths & current_paths:
            baseline_state = self._baseline[path]
            current_state = current[path]

            if baseline_state.hash != current_state.hash:
                changeset.modified.append(path)
            else:
                changeset.unchanged.append(path)

        return changeset

    def detect_changes_in_directory(self, directory: Path) -> ChangeSet:
        """Convenience method to detect changes in directory.

        Args:
            directory: Directory to check

        Returns:
            ChangeSet with detected changes
        """
        current = self.scan_directory(directory)
        return self.detect_changes(current)

    def save_baseline(self, path: Path) -> None:
        """Save baseline to file.

        Args:
            path: Path to save baseline
        """
        import json
        data = {k: v.to_dict() for k, v in self._baseline.items()}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_baseline(self, path: Path) -> bool:
        """Load baseline from file.

        Args:
            path: Path to load baseline from

        Returns:
            True if baseline was loaded
        """
        import json
        if not path.exists():
            return False

        try:
            with open(path) as f:
                data = json.load(f)
            self._baseline = {
                k: FileState.from_dict(v) for k, v in data.items()
            }
            return True
        except (json.JSONDecodeError, KeyError):
            return False


@dataclass
class IncrementalBuildResult:
    """Result of an incremental build.

    Attributes:
        full_rebuild: Whether a full rebuild was performed
        files_processed: Files that were processed
        files_skipped: Files that were skipped
        time_saved_ms: Estimated time saved
    """
    full_rebuild: bool = False
    files_processed: List[str] = field(default_factory=list)
    files_skipped: List[str] = field(default_factory=list)
    time_saved_ms: float = 0.0

    @property
    def total_files(self) -> int:
        return len(self.files_processed) + len(self.files_skipped)

    @property
    def skip_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return len(self.files_skipped) / self.total_files


class IncrementalBuilder:
    """Performs incremental builds of the knowledge graph.

    Only processes changed files, reusing cached results for
    unchanged files.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        force_full_rebuild: bool = False,
    ):
        """Initialize builder.

        Args:
            cache_dir: Directory for caching
            force_full_rebuild: Whether to force full rebuild
        """
        self.cache_dir = cache_dir
        self.force_full_rebuild = force_full_rebuild
        self._detector = ChangeDetector()

        # Load baseline if available
        if cache_dir:
            baseline_path = cache_dir / "baseline.json"
            self._detector.load_baseline(baseline_path)

    def should_rebuild_file(
        self,
        file_path: str,
        changeset: ChangeSet,
    ) -> bool:
        """Check if a file needs to be rebuilt.

        Args:
            file_path: File to check
            changeset: Detected changes

        Returns:
            True if file needs rebuild
        """
        if self.force_full_rebuild:
            return True

        return file_path in changeset.changed_files

    def plan_build(
        self,
        directory: Path,
    ) -> Tuple[ChangeSet, IncrementalBuildResult]:
        """Plan an incremental build.

        Args:
            directory: Directory to build

        Returns:
            Tuple of (changeset, build result plan)
        """
        # Detect changes
        current = self._detector.scan_directory(directory)
        changeset = self._detector.detect_changes(current)

        # Plan build
        result = IncrementalBuildResult()

        if self.force_full_rebuild or not self._detector._baseline:
            result.full_rebuild = True
            result.files_processed = list(current.keys())
        else:
            result.files_processed = changeset.changed_files
            result.files_skipped = changeset.unchanged

            # Estimate time saved (rough: 50ms per skipped file)
            result.time_saved_ms = len(result.files_skipped) * 50

        return changeset, result

    def update_baseline(self, directory: Path) -> None:
        """Update baseline after successful build.

        Args:
            directory: Directory that was built
        """
        current = self._detector.scan_directory(directory)
        self._detector.set_baseline(current)

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            baseline_path = self.cache_dir / "baseline.json"
            self._detector.save_baseline(baseline_path)


def detect_changes(
    directory: Path,
    extensions: Optional[List[str]] = None,
) -> ChangeSet:
    """Detect changes in a directory.

    Convenience function for quick change detection.

    Args:
        directory: Directory to check
        extensions: File extensions to track

    Returns:
        ChangeSet with detected changes
    """
    detector = ChangeDetector(extensions)
    current = detector.scan_directory(directory)

    # No baseline = all files are "added"
    changeset = ChangeSet()
    changeset.added = list(current.keys())

    return changeset


__all__ = [
    "FileState",
    "ChangeSet",
    "ChangeDetector",
    "IncrementalBuildResult",
    "IncrementalBuilder",
    "detect_changes",
]
