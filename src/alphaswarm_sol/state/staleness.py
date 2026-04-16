"""
Staleness Detection

Detects when findings or other artifacts reference outdated graph versions.

Staleness Severity Levels:
- critical: Source code has changed, findings may be completely invalid
- warning: Graph rebuilt but code unchanged (findings likely valid)
- info: Minor version differences, generally safe to ignore
- ok: Finding is up-to-date
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict
from enum import Enum
import logging

from alphaswarm_sol.state.versioning import GraphVersion

logger = logging.getLogger(__name__)


class StalenessSeverity(Enum):
    """Severity levels for staleness."""

    OK = "ok"  # Not stale
    INFO = "info"  # Minor, likely safe
    WARNING = "warning"  # Should investigate
    CRITICAL = "critical"  # Source changed, findings may be invalid


@dataclass
class StalenessResult:
    """
    Result of a staleness check.

    Attributes:
        stale: Whether the finding is stale
        finding_version: Version ID the finding references
        current_version: Current graph version ID
        age: Time since finding was created
        code_changed: Whether source code has changed
        recommendation: User-friendly action recommendation
        details: Additional details about the staleness
    """

    stale: bool
    finding_version: Optional[str] = None
    current_version: Optional[str] = None
    age: Optional[timedelta] = None
    code_changed: bool = False
    recommendation: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def severity(self) -> StalenessSeverity:
        """
        Get staleness severity level.

        Returns:
            StalenessSeverity enum value
        """
        if not self.stale:
            return StalenessSeverity.OK

        # Code changed = critical
        if self.code_changed:
            return StalenessSeverity.CRITICAL

        # Very old = warning
        if self.age and self.age > timedelta(days=7):
            return StalenessSeverity.WARNING

        # Just version mismatch = info
        return StalenessSeverity.INFO

    @property
    def severity_str(self) -> str:
        """Get severity as string."""
        return self.severity.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stale": self.stale,
            "finding_version": self.finding_version,
            "current_version": self.current_version,
            "age_seconds": self.age.total_seconds() if self.age else None,
            "age_human": self._format_age() if self.age else None,
            "code_changed": self.code_changed,
            "severity": self.severity_str,
            "recommendation": self.recommendation,
            "details": self.details,
        }

    def _format_age(self) -> str:
        """Format age as human-readable string."""
        if not self.age:
            return "unknown"

        total_seconds = int(self.age.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds} seconds"
        elif total_seconds < 3600:
            return f"{total_seconds // 60} minutes"
        elif total_seconds < 86400:
            return f"{total_seconds // 3600} hours"
        else:
            return f"{total_seconds // 86400} days"


class StalenessChecker:
    """
    Checks findings for staleness against current graph version.

    Usage:
        checker = StalenessChecker(current_version)
        result = checker.check(finding.graph_version, finding.code_hash)
        if result.stale:
            print(format_staleness_warning(result))
    """

    def __init__(self, current_version: GraphVersion):
        """
        Initialize checker with current graph version.

        Args:
            current_version: The current graph version to check against
        """
        self.current_version = current_version

    def check(
        self,
        finding_version: Optional[str],
        finding_code_hash: Optional[str] = None,
        finding_created_at: Optional[datetime] = None,
    ) -> StalenessResult:
        """
        Check if a finding is stale.

        Args:
            finding_version: Version ID from the finding
            finding_code_hash: Code hash from the finding
            finding_created_at: When the finding was created

        Returns:
            StalenessResult with staleness information
        """
        # No version = definitely stale
        if finding_version is None:
            return StalenessResult(
                stale=True,
                current_version=self.current_version.version_id,
                recommendation="Finding has no version. Run: vkg findings refresh",
                details={"reason": "no_version"},
            )

        # Same version = not stale
        if finding_version == self.current_version.version_id:
            return StalenessResult(stale=False)

        # Different version - check if code changed
        code_changed = (
            finding_code_hash is not None
            and finding_code_hash != self.current_version.code_hash
        )

        # Calculate age if we have creation time
        age = None
        if finding_created_at:
            age = datetime.now() - finding_created_at

        return StalenessResult(
            stale=True,
            finding_version=finding_version,
            current_version=self.current_version.version_id,
            age=age,
            code_changed=code_changed,
            recommendation=self._get_recommendation(code_changed),
            details={
                "reason": "version_mismatch",
                "code_changed": code_changed,
            },
        )

    def _get_recommendation(self, code_changed: bool) -> str:
        """Get user-friendly recommendation based on staleness."""
        if code_changed:
            return (
                "Source code has changed. Findings may be invalid.\n"
                "Options:\n"
                "  vkg findings refresh   # Re-validate against current graph\n"
                "  vkg findings reset     # Regenerate all findings"
            )
        return (
            "Graph rebuilt but source unchanged. Findings likely still valid.\n"
            "Run: vkg findings refresh"
        )

    def check_all(
        self,
        findings: List[Any],
        version_attr: str = "graph_version",
        code_hash_attr: str = "code_hash",
        created_at_attr: str = "created_at",
    ) -> List[StalenessResult]:
        """
        Check multiple findings for staleness.

        Args:
            findings: List of finding objects
            version_attr: Attribute name for version ID
            code_hash_attr: Attribute name for code hash
            created_at_attr: Attribute name for creation time

        Returns:
            List of StalenessResult, one per finding
        """
        results = []

        for finding in findings:
            # Extract attributes (handle both objects and dicts)
            if isinstance(finding, dict):
                version = finding.get(version_attr)
                code_hash = finding.get(code_hash_attr)
                created_at = finding.get(created_at_attr)
            else:
                version = getattr(finding, version_attr, None)
                code_hash = getattr(finding, code_hash_attr, None)
                created_at = getattr(finding, created_at_attr, None)

            results.append(self.check(version, code_hash, created_at))

        return results

    def get_summary(self, findings: List[Any]) -> Dict[str, Any]:
        """
        Get summary of staleness for a list of findings.

        Args:
            findings: List of finding objects

        Returns:
            Summary dictionary with counts and recommendations
        """
        results = self.check_all(findings)

        # Count by severity
        counts = {severity.value: 0 for severity in StalenessSeverity}
        for result in results:
            counts[result.severity_str] += 1

        stale_count = sum(1 for r in results if r.stale)
        code_changed_count = sum(1 for r in results if r.code_changed)

        return {
            "total": len(findings),
            "stale": stale_count,
            "fresh": len(findings) - stale_count,
            "code_changed": code_changed_count,
            "by_severity": counts,
            "needs_action": counts["critical"] > 0 or counts["warning"] > 0,
            "current_version": self.current_version.version_id,
        }


def format_staleness_warning(result: StalenessResult, verbose: bool = False) -> str:
    """
    Format staleness result as user-friendly warning.

    Args:
        result: StalenessResult to format
        verbose: Include more details if True

    Returns:
        Formatted warning string (empty if not stale)
    """
    if not result.stale:
        return ""

    # Icon based on severity
    icons = {
        "critical": "[!] CRITICAL",
        "warning": "[!] WARNING",
        "info": "[i] INFO",
        "ok": "",
    }
    icon = icons.get(result.severity_str, "[?]")

    lines = [f"{icon}: Graph has changed since findings were created"]

    # Version info
    if result.current_version:
        lines.append(f"  Current graph version: {result.current_version}")
    if result.finding_version:
        lines.append(f"  Findings reference: {result.finding_version}")

    # Code change status
    if result.code_changed:
        lines.append("  Source code: CHANGED (findings may be invalid)")
    else:
        lines.append("  Source code: unchanged (findings likely valid)")

    # Age
    if result.age:
        lines.append(f"  Age: {result._format_age()}")

    # Recommendation
    if result.recommendation:
        lines.append("")
        # Indent recommendation lines
        for line in result.recommendation.split("\n"):
            lines.append(f"  {line}")

    # Extra details if verbose
    if verbose and result.details:
        lines.append("")
        lines.append("  Details:")
        for key, value in result.details.items():
            lines.append(f"    {key}: {value}")

    return "\n".join(lines)


def check_finding_staleness(
    finding: Any,
    current_version: GraphVersion,
) -> StalenessResult:
    """
    Convenience function to check a single finding.

    Args:
        finding: Finding object or dict
        current_version: Current graph version

    Returns:
        StalenessResult
    """
    checker = StalenessChecker(current_version)

    if isinstance(finding, dict):
        return checker.check(
            finding.get("graph_version"),
            finding.get("code_hash"),
            finding.get("created_at"),
        )
    else:
        return checker.check(
            getattr(finding, "graph_version", None),
            getattr(finding, "code_hash", None),
            getattr(finding, "created_at", None),
        )


def summarize_staleness(
    findings: List[Any],
    current_version: GraphVersion,
) -> str:
    """
    Generate human-readable staleness summary.

    Args:
        findings: List of findings
        current_version: Current graph version

    Returns:
        Formatted summary string
    """
    checker = StalenessChecker(current_version)
    summary = checker.get_summary(findings)

    lines = [
        "Staleness Summary",
        "=" * 40,
        f"Total findings: {summary['total']}",
        f"Fresh: {summary['fresh']}",
        f"Stale: {summary['stale']}",
    ]

    if summary["code_changed"] > 0:
        lines.append(f"Code changed: {summary['code_changed']} (findings may be invalid)")

    lines.append("")
    lines.append("By severity:")
    for severity, count in summary["by_severity"].items():
        if count > 0:
            lines.append(f"  {severity}: {count}")

    if summary["needs_action"]:
        lines.append("")
        lines.append("Action needed: Run 'vkg findings refresh' or 'vkg findings reset'")

    return "\n".join(lines)
