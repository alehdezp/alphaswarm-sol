"""
Pragma Compatibility Check (Task 4.4)

Validates Solidity pragma version compatibility between test files
and the contracts they test.

Philosophy:
- Conservative matching: when in doubt, report UNKNOWN
- Support common patterns: ^, >=, <, range
- Never claim compatibility we can't verify
- Provide helpful suggestions for mismatches
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from alphaswarm_sol.testing.remappings import extract_pragma_from_source


class CompatibilityStatus(Enum):
    """Result of pragma compatibility check."""

    COMPATIBLE = "compatible"          # Versions overlap
    INCOMPATIBLE = "incompatible"      # Versions don't overlap
    UNKNOWN = "unknown"                # Cannot determine
    MISSING = "missing"                # One or both pragmas missing


@dataclass
class SemVer:
    """
    Semantic version representation.

    Only supports major.minor.patch format (no pre-release or build).
    """

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> Optional["SemVer"]:
        """
        Parse version string to SemVer.

        Args:
            version_str: Version like "0.8.20", "0.8", "0"

        Returns:
            SemVer instance or None if parse fails
        """
        # Remove leading zeros and common prefixes
        version_str = version_str.strip().lstrip("v")

        # Match version pattern
        match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?$", version_str)
        if not match:
            return None

        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        patch = int(match.group(3)) if match.group(3) else 0

        return cls(major=major, minor=minor, patch=patch)

    def __lt__(self, other: "SemVer") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "SemVer") -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "SemVer") -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "SemVer") -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump_minor(self) -> "SemVer":
        """Return version with incremented minor and zeroed patch."""
        return SemVer(self.major, self.minor + 1, 0)


@dataclass
class VersionRange:
    """
    A range of Solidity versions.

    Represents constraints like ^0.8.0, >=0.8.0 <0.9.0, etc.
    """

    min_version: Optional[SemVer]
    max_version: Optional[SemVer]
    min_inclusive: bool = True
    max_inclusive: bool = False

    def contains(self, version: SemVer) -> bool:
        """Check if a version is within this range."""
        if self.min_version is not None:
            if self.min_inclusive:
                if version < self.min_version:
                    return False
            else:
                if version <= self.min_version:
                    return False

        if self.max_version is not None:
            if self.max_inclusive:
                if version > self.max_version:
                    return False
            else:
                if version >= self.max_version:
                    return False

        return True

    def overlaps(self, other: "VersionRange") -> bool:
        """
        Check if two ranges have any overlap.

        Conservative: returns True if unsure.
        """
        # If either has unbounded sides, assume overlap possible
        if self.min_version is None or self.max_version is None:
            return True
        if other.min_version is None or other.max_version is None:
            return True

        # Check for non-overlap conditions
        # self is entirely before other
        if self.max_version < other.min_version:
            return False
        if self.max_version == other.min_version:
            if not self.max_inclusive or not other.min_inclusive:
                return False

        # self is entirely after other
        if self.min_version > other.max_version:
            return False
        if self.min_version == other.max_version:
            if not self.min_inclusive or not other.max_inclusive:
                return False

        return True


def parse_pragma(pragma_str: str) -> Optional[VersionRange]:
    """
    Parse a Solidity pragma string to a VersionRange.

    Handles:
    - ^0.8.0 -> [0.8.0, 0.9.0)
    - >=0.8.0 <0.9.0 -> [0.8.0, 0.9.0)
    - 0.8.20 (exact) -> [0.8.20, 0.8.21)
    - >=0.8.0 -> [0.8.0, inf)
    - <0.9.0 -> [0, 0.9.0)

    Args:
        pragma_str: The pragma version constraint

    Returns:
        VersionRange or None if cannot parse
    """
    pragma_str = pragma_str.strip()

    # Handle caret version: ^0.8.0
    caret_match = re.match(r"^\^(\d+\.\d+(?:\.\d+)?)", pragma_str)
    if caret_match:
        version = SemVer.parse(caret_match.group(1))
        if version:
            # Caret allows changes that do not modify left-most non-zero
            # For Solidity (0.x.y), ^0.8.0 means >=0.8.0 <0.9.0
            max_version = version.bump_minor()
            return VersionRange(
                min_version=version,
                max_version=max_version,
                min_inclusive=True,
                max_inclusive=False,
            )

    # Handle range: >=0.8.0 <0.9.0 or >=0.8.0 <=0.9.0
    range_match = re.match(
        r"^(>=?)\s*(\d+\.\d+(?:\.\d+)?)\s+(<=?)\s*(\d+\.\d+(?:\.\d+)?)$",
        pragma_str
    )
    if range_match:
        min_op, min_ver, max_op, max_ver = range_match.groups()
        min_version = SemVer.parse(min_ver)
        max_version = SemVer.parse(max_ver)
        if min_version and max_version:
            return VersionRange(
                min_version=min_version,
                max_version=max_version,
                min_inclusive=(min_op == ">="),
                max_inclusive=(max_op == "<="),
            )

    # Handle single constraint: >=0.8.0 or <0.9.0
    single_match = re.match(r"^(>=?|<=?)\s*(\d+\.\d+(?:\.\d+)?)$", pragma_str)
    if single_match:
        op, ver = single_match.groups()
        version = SemVer.parse(ver)
        if version:
            if op == ">=":
                return VersionRange(min_version=version, max_version=None, min_inclusive=True)
            elif op == ">":
                return VersionRange(min_version=version, max_version=None, min_inclusive=False)
            elif op == "<=":
                return VersionRange(min_version=None, max_version=version, max_inclusive=True)
            elif op == "<":
                return VersionRange(min_version=None, max_version=version, max_inclusive=False)

    # Handle exact version: 0.8.20
    exact_match = re.match(r"^(\d+\.\d+(?:\.\d+)?)$", pragma_str)
    if exact_match:
        version = SemVer.parse(exact_match.group(1))
        if version:
            # Exact version is just that version
            return VersionRange(
                min_version=version,
                max_version=version,
                min_inclusive=True,
                max_inclusive=True,
            )

    return None


@dataclass
class CompatibilityResult:
    """
    Result of pragma compatibility check.

    Attributes:
        status: Whether versions are compatible
        test_pragma: The test file's pragma
        contract_pragma: The contract's pragma
        message: Human-readable explanation
        suggestion: Suggested fix if incompatible
    """

    status: CompatibilityStatus
    test_pragma: Optional[str]
    contract_pragma: Optional[str]
    message: str
    suggestion: Optional[str] = None


def check_pragma_compatibility(
    test_pragma: Optional[str],
    contract_pragma: Optional[str],
) -> CompatibilityResult:
    """
    Check if test pragma is compatible with contract pragma.

    Args:
        test_pragma: Pragma from test file (e.g., "^0.8.20")
        contract_pragma: Pragma from contract file

    Returns:
        CompatibilityResult with status and explanation
    """
    # Handle missing pragmas
    if test_pragma is None and contract_pragma is None:
        return CompatibilityResult(
            status=CompatibilityStatus.MISSING,
            test_pragma=None,
            contract_pragma=None,
            message="Both test and contract are missing pragma statements",
            suggestion="Add pragma solidity ^0.8.20; to both files",
        )

    if test_pragma is None:
        return CompatibilityResult(
            status=CompatibilityStatus.MISSING,
            test_pragma=None,
            contract_pragma=contract_pragma,
            message="Test file is missing pragma statement",
            suggestion=f"Add pragma solidity {contract_pragma}; to test file",
        )

    if contract_pragma is None:
        return CompatibilityResult(
            status=CompatibilityStatus.MISSING,
            test_pragma=test_pragma,
            contract_pragma=None,
            message="Contract is missing pragma statement",
            suggestion=None,  # Can't suggest fix for contract
        )

    # Parse both pragmas
    test_range = parse_pragma(test_pragma)
    contract_range = parse_pragma(contract_pragma)

    if test_range is None or contract_range is None:
        return CompatibilityResult(
            status=CompatibilityStatus.UNKNOWN,
            test_pragma=test_pragma,
            contract_pragma=contract_pragma,
            message="Cannot parse one or both pragma constraints",
            suggestion=None,
        )

    # Check for overlap
    if test_range.overlaps(contract_range):
        return CompatibilityResult(
            status=CompatibilityStatus.COMPATIBLE,
            test_pragma=test_pragma,
            contract_pragma=contract_pragma,
            message=f"Pragma versions are compatible: test ({test_pragma}) overlaps contract ({contract_pragma})",
            suggestion=None,
        )
    else:
        return CompatibilityResult(
            status=CompatibilityStatus.INCOMPATIBLE,
            test_pragma=test_pragma,
            contract_pragma=contract_pragma,
            message=f"Pragma versions are incompatible: test ({test_pragma}) does not overlap contract ({contract_pragma})",
            suggestion=f"Change test pragma to: pragma solidity {contract_pragma};",
        )


def suggest_test_pragma(contract_pragma: Optional[str]) -> str:
    """
    Suggest a test pragma based on contract pragma.

    Aims for maximum compatibility while respecting contract constraints.

    Args:
        contract_pragma: The contract's pragma string

    Returns:
        Suggested pragma string for test file
    """
    if contract_pragma is None:
        # Default to recent stable version
        return "^0.8.20"

    # Try to parse and use same constraint
    contract_range = parse_pragma(contract_pragma)
    if contract_range is None:
        return contract_pragma  # Use as-is if can't parse

    # If it's already a caret or range, use it
    if contract_pragma.startswith("^"):
        return contract_pragma

    if ">=" in contract_pragma:
        return contract_pragma

    # For exact versions, add caret to allow patch updates
    exact_match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", contract_pragma)
    if exact_match:
        major = exact_match.group(1)
        minor = exact_match.group(2)
        return f"^{major}.{minor}.0"

    return contract_pragma


def get_pragma_from_file(file_path: Path) -> Optional[str]:
    """
    Extract pragma from a Solidity file.

    Args:
        file_path: Path to .sol file

    Returns:
        Pragma version string or None
    """
    try:
        source = file_path.read_text()
        return extract_pragma_from_source(source)
    except OSError:
        return None


def find_common_pragma(pragmas: List[str]) -> Optional[str]:
    """
    Find a pragma that satisfies all given constraints.

    Useful when test needs to import multiple contracts.

    Args:
        pragmas: List of pragma strings from various files

    Returns:
        A pragma string that overlaps all, or None if no overlap
    """
    if not pragmas:
        return None

    if len(pragmas) == 1:
        return pragmas[0]

    # Parse all pragmas
    ranges = []
    for p in pragmas:
        r = parse_pragma(p)
        if r is None:
            return None  # Can't determine if one is unparseable
        ranges.append(r)

    # Find intersection
    # Start with first range and narrow down
    min_ver: Optional[SemVer] = None
    max_ver: Optional[SemVer] = None
    min_inclusive = True
    max_inclusive = True

    for r in ranges:
        # Update minimum
        if r.min_version is not None:
            if min_ver is None or r.min_version > min_ver:
                min_ver = r.min_version
                min_inclusive = r.min_inclusive
            elif r.min_version == min_ver and not r.min_inclusive:
                min_inclusive = False

        # Update maximum
        if r.max_version is not None:
            if max_ver is None or r.max_version < max_ver:
                max_ver = r.max_version
                max_inclusive = r.max_inclusive
            elif r.max_version == max_ver and not r.max_inclusive:
                max_inclusive = False

    # Check if intersection is valid
    if min_ver is not None and max_ver is not None:
        if min_ver > max_ver:
            return None
        if min_ver == max_ver and (not min_inclusive or not max_inclusive):
            return None

    # Build pragma string
    if min_ver is not None and max_ver is not None:
        min_op = ">=" if min_inclusive else ">"
        max_op = "<=" if max_inclusive else "<"
        return f"{min_op}{min_ver} {max_op}{max_ver}"
    elif min_ver is not None:
        return f">={min_ver}" if min_inclusive else f">{min_ver}"
    elif max_ver is not None:
        return f"<={max_ver}" if max_inclusive else f"<{max_ver}"
    else:
        return ">=0.0.0"  # No constraints
