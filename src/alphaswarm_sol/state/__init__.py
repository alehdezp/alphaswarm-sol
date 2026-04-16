"""
State Management Module

Provides version tracking, staleness detection, and state persistence
for VKG knowledge graphs and findings.
"""

from alphaswarm_sol.state.versioning import (
    GraphVersion,
    VersionGenerator,
    VersionStore,
)
from alphaswarm_sol.state.staleness import (
    StalenessResult,
    StalenessChecker,
    format_staleness_warning,
)


__all__ = [
    # Versioning
    "GraphVersion",
    "VersionGenerator",
    "VersionStore",
    # Staleness
    "StalenessResult",
    "StalenessChecker",
    "format_staleness_warning",
]
