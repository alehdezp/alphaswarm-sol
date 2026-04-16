"""Pattern loading exceptions.

Exception hierarchy:
    PatternLoadError (base)
    ├── PatternDirectoryNotFoundError  — path doesn't exist
    └── EmptyPatternStoreError         — path exists, no patterns found
"""
from __future__ import annotations

from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Union


class PatternLoadError(Exception):
    """Base exception for all pattern loading failures."""


class PatternDirectoryNotFoundError(PatternLoadError):
    """Pattern directory does not exist on disk."""

    def __init__(self, path: Union[Path, Traversable]) -> None:
        self.path = path
        super().__init__(
            f"Pattern directory not found: {path}. "
            f"Expected vulndocs/ in project root or installed package."
        )


class EmptyPatternStoreError(PatternLoadError):
    """Valid directory exists but contains no loadable patterns."""

    def __init__(self, path: Union[Path, Traversable], glob_pattern: str = "**/patterns/*.yaml") -> None:
        self.path = path
        self.glob_pattern = glob_pattern
        super().__init__(f"No patterns matching '{glob_pattern}' found in {path}")
