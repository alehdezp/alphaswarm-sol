"""
Availability Checker

Runtime checks for VKG component availability and graceful degradation.
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from alphaswarm_sol.core.tiers import (
    Tier,
    Dependency,
    DEPENDENCIES,
    get_tier_dependencies,
    get_degradation_message,
    format_dependency_status,
)


@dataclass
class AvailabilityReport:
    """
    Report of component availability for a single tier.

    Attributes:
        tier: The tier being reported on
        available: List of available dependency names
        unavailable: List of unavailable dependency names
        degraded: True if any dependencies are unavailable
        message: Human-readable status message
        checked_at: Timestamp of the check
    """

    tier: Tier
    available: List[str]
    unavailable: List[str]
    degraded: bool
    message: str
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tier": self.tier.name,
            "tier_value": self.tier.value,
            "available": self.available,
            "unavailable": self.unavailable,
            "degraded": self.degraded,
            "message": self.message,
            "checked_at": self.checked_at.isoformat(),
        }

    @property
    def is_critical(self) -> bool:
        """True if this is a critical (CORE) tier degradation."""
        return self.tier == Tier.CORE and self.degraded


@dataclass
class SystemStatus:
    """
    Overall system availability status.

    Attributes:
        effective_tier: The current effective operating tier
        reports: List of availability reports per tier
        can_run: True if VKG can operate (CORE tier available)
        warnings: List of warning messages
    """

    effective_tier: Tier
    reports: List[AvailabilityReport]
    can_run: bool
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "effective_tier": self.effective_tier.name,
            "can_run": self.can_run,
            "warnings": self.warnings,
            "reports": [r.to_dict() for r in self.reports],
        }


class AvailabilityChecker:
    """
    Checks VKG component availability with caching.

    Usage:
        checker = AvailabilityChecker()
        reports = checker.check_all()
        tier = checker.get_effective_tier()
    """

    def __init__(self):
        self._cache: Dict[str, bool] = {}
        self._last_check: Optional[datetime] = None
        self._cache_ttl_seconds: int = 60  # Cache for 1 minute

    def check_all(self, force: bool = False) -> List[AvailabilityReport]:
        """
        Check all dependencies by tier.

        Args:
            force: If True, bypass cache

        Returns:
            List of AvailabilityReport, one per tier
        """
        if force:
            self.clear_cache()

        reports = []

        for tier in Tier:
            tier_deps = get_tier_dependencies(tier)
            available = []
            unavailable = []

            for dep in tier_deps:
                if self._check_dependency(dep):
                    available.append(dep.name)
                else:
                    unavailable.append(dep.name)

            degraded = len(unavailable) > 0

            if tier == Tier.CORE and degraded:
                message = f"FATAL: Core dependencies missing: {', '.join(unavailable)}"
            elif degraded:
                message = f"Degraded: Missing {', '.join(unavailable)}"
            else:
                message = "All available"

            reports.append(
                AvailabilityReport(
                    tier=tier,
                    available=available,
                    unavailable=unavailable,
                    degraded=degraded,
                    message=message,
                )
            )

        self._last_check = datetime.now()
        return reports

    def _check_dependency(self, dep: Dependency) -> bool:
        """Check single dependency with caching."""
        # Check if cache is valid
        if dep.name in self._cache and self._is_cache_valid():
            return self._cache[dep.name]

        result = dep.is_available()
        self._cache[dep.name] = result
        return result

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid (within TTL)."""
        if self._last_check is None:
            return False

        elapsed = (datetime.now() - self._last_check).total_seconds()
        return elapsed < self._cache_ttl_seconds

    def get_effective_tier(self, raise_on_critical: bool = True) -> Tier:
        """
        Get the effective operation tier based on availability.

        Args:
            raise_on_critical: If True, raise RuntimeError when CORE is degraded

        Returns:
            The highest tier where all dependencies are available

        Raises:
            RuntimeError: If CORE tier is degraded and raise_on_critical is True
        """
        reports = self.check_all()

        # Check if core is degraded
        core_report = next(r for r in reports if r.tier == Tier.CORE)
        if core_report.degraded:
            if raise_on_critical:
                raise RuntimeError(
                    f"Cannot run VKG: {core_report.message}\n"
                    f"{get_degradation_message(Tier.CORE)}"
                )
            return Tier.CORE

        # Find lowest (most capable) non-degraded tier
        # Note: Lower tier value = more critical = more capabilities
        for report in sorted(reports, key=lambda r: r.tier.value):
            if not report.degraded:
                continue

        # All tiers available
        return Tier.OPTIONAL

    def get_system_status(self) -> SystemStatus:
        """
        Get comprehensive system status.

        Returns:
            SystemStatus with full availability information
        """
        reports = self.check_all()
        warnings = []

        # Check core tier
        core_report = next(r for r in reports if r.tier == Tier.CORE)
        can_run = not core_report.degraded

        # Determine effective tier
        if not can_run:
            effective_tier = Tier.CORE
        else:
            # Find highest (least critical) available tier
            effective_tier = Tier.CORE
            for report in reports:
                if not report.degraded:
                    effective_tier = report.tier

        # Collect warnings for degraded tiers
        for report in reports:
            if report.degraded and report.tier != Tier.CORE:
                warnings.append(get_degradation_message(report.tier))

        return SystemStatus(
            effective_tier=effective_tier,
            reports=reports,
            can_run=can_run,
            warnings=warnings,
        )

    def check_dependency(self, name: str) -> bool:
        """
        Check a specific dependency by name.

        Args:
            name: Dependency name

        Returns:
            True if available
        """
        dep = DEPENDENCIES.get(name)
        if not dep:
            return False
        return self._check_dependency(dep)

    def clear_cache(self) -> None:
        """Clear availability cache (useful for testing or after installations)."""
        self._cache.clear()
        self._last_check = None

    def format_report(self, verbose: bool = False) -> str:
        """
        Format availability report for display.

        Args:
            verbose: If True, include installation hints

        Returns:
            Formatted report string
        """
        reports = self.check_all()
        lines = ["VKG Dependency Status", "=" * 40]

        for report in reports:
            tier_name = report.tier.name
            status = "DEGRADED" if report.degraded else "OK"
            lines.append(f"\n{tier_name} Tier [{status}]")
            lines.append("-" * 30)

            tier_deps = get_tier_dependencies(report.tier)
            for dep in tier_deps:
                if verbose:
                    lines.append(format_dependency_status(dep))
                else:
                    available = dep.name in report.available
                    symbol = "[OK]" if available else "[X]"
                    lines.append(f"  {symbol} {dep.name}")

        return "\n".join(lines)


# -----------------------------------------------------------------------------
# Convenience Functions
# -----------------------------------------------------------------------------


def check_all_dependencies(force: bool = False) -> List[AvailabilityReport]:
    """
    Check all dependencies and return reports.

    Args:
        force: If True, bypass cache

    Returns:
        List of AvailabilityReport
    """
    checker = AvailabilityChecker()
    return checker.check_all(force=force)


def get_effective_tier() -> Tier:
    """
    Get the current effective tier.

    Returns:
        Tier value

    Raises:
        RuntimeError: If CORE dependencies are missing
    """
    checker = AvailabilityChecker()
    return checker.get_effective_tier()


def is_tier_available(tier: Tier) -> bool:
    """
    Check if a specific tier is fully available.

    Args:
        tier: Tier to check

    Returns:
        True if all dependencies for the tier are available
    """
    checker = AvailabilityChecker()
    reports = checker.check_all()

    for report in reports:
        if report.tier == tier:
            return not report.degraded

    return False


def require_tier(tier: Tier) -> None:
    """
    Raise error if required tier is not available.

    Args:
        tier: Required tier

    Raises:
        RuntimeError: If tier is not available
    """
    if not is_tier_available(tier):
        raise RuntimeError(
            f"Operation requires {tier.name} tier, but it's not available.\n"
            f"{get_degradation_message(tier)}"
        )


# -----------------------------------------------------------------------------
# Tool Availability Checking (for health-check command)
# -----------------------------------------------------------------------------


@dataclass
class ToolStatus:
    """Status of a single tool."""
    name: str
    available: bool
    version: Optional[str] = None
    path: Optional[str] = None
    error: Optional[str] = None
    required: bool = False


REQUIRED_TOOLS = ["slither"]
OPTIONAL_TOOLS = ["aderyn", "mythril", "foundry", "echidna", "semgrep", "halmos"]


def check_tool_available(tool_name: str) -> ToolStatus:
    """Check if a tool is available and get its version.

    Args:
        tool_name: Name of the tool to check

    Returns:
        ToolStatus with availability info
    """
    # Map tool names to executables
    exe_map = {
        "slither": "slither",
        "aderyn": "aderyn",
        "mythril": "myth",
        "foundry": "forge",
        "echidna": "echidna-test",
        "semgrep": "semgrep",
        "halmos": "halmos",
    }

    exe = exe_map.get(tool_name, tool_name)
    path = shutil.which(exe)

    if not path:
        return ToolStatus(
            name=tool_name,
            available=False,
            error=f"Executable '{exe}' not found in PATH",
            required=tool_name in REQUIRED_TOOLS,
        )

    # Try to get version
    version_flags = {
        "slither": "--version",
        "aderyn": "--version",
        "mythril": "--version",
        "foundry": "--version",
        "echidna": "--version",
        "semgrep": "--version",
        "halmos": "--version",
    }

    version = None
    try:
        result = subprocess.run(
            [exe, version_flags.get(tool_name, "--version")],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
    except Exception:
        pass

    return ToolStatus(
        name=tool_name,
        available=True,
        version=version,
        path=path,
        required=tool_name in REQUIRED_TOOLS,
    )


def get_available_tools() -> Dict[str, ToolStatus]:
    """Check all known tools and return their status."""
    tools = {}
    for tool in REQUIRED_TOOLS + OPTIONAL_TOOLS:
        tools[tool] = check_tool_available(tool)
    return tools


def check_vulndocs_available() -> Tuple[bool, Optional[Path], Optional[str]]:
    """Check if vulndocs are installed.

    Uses the centralized vulndocs resolution module for cwd-independent resolution.

    Returns:
        Tuple of (available, path, error)
    """
    from alphaswarm_sol.vulndocs.resolution import vulndocs_read_path, vulndocs_read_path_as_path

    try:
        read_path = vulndocs_read_path()
        # Check if the resolved path has content via Traversable API
        has_content = False
        for child in read_path.iterdir():
            if child.is_dir() or child.name.endswith((".yaml", ".yml")):
                has_content = True
                break
        if has_content:
            # Return a concrete Path (this function's API contract requires Path)
            return True, vulndocs_read_path_as_path(), None
    except Exception:
        pass

    # Fallback to home directory locations
    locations = [
        Path.home() / ".vrs" / "vulndocs",
        Path.home() / ".vkg" / "vulndocs",
    ]

    for loc in locations:
        if loc.exists() and loc.is_dir():
            entries = list(loc.glob("*.yaml")) + list(loc.glob("*.yml"))
            if entries:
                return True, loc, None

    return False, None, "vulndocs not found in standard locations"


def check_skills_available(project_root: Path) -> Tuple[bool, int, Optional[str]]:
    """Check if VRS skills are installed in project.

    Args:
        project_root: Root of the project to check

    Returns:
        Tuple of (available, skill_count, error)
    """
    vrs_dir = project_root / ".claude" / "vrs"

    if not vrs_dir.exists():
        return False, 0, "VRS skills not installed. Run: alphaswarm init"

    skills = list(vrs_dir.glob("*.md"))
    if not skills:
        return False, 0, "No skill files found in .claude/vrs/"

    return True, len(skills), None
