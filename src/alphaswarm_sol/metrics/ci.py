"""CI integration for metrics.

Task 8.7: Functions for CI pipeline integration.

Provides programmatic access to metric checking for CI systems,
with proper exit codes and machine-readable output.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from pathlib import Path

from .alerting import Alert, AlertChecker, AlertLevel, check_alerts
from .storage import HistoryStore
from .tracker import MetricsTracker
from .types import MetricSnapshot, MetricStatus


class ExitCode(IntEnum):
    """CI exit codes for metrics checks."""

    SUCCESS = 0
    CRITICAL_ALERT = 1
    WARNING_ALERT = 2
    REGRESSION_DETECTED = 3
    BASELINE_NOT_FOUND = 4
    INVALID_CONFIG = 5


@dataclass
class CIResult:
    """Result of a CI metrics check."""

    exit_code: ExitCode
    alerts: list[Alert]
    snapshot: MetricSnapshot
    baseline: MetricSnapshot | None
    message: str
    regression_detected: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "exit_code": self.exit_code.value,
            "exit_code_name": self.exit_code.name,
            "message": self.message,
            "regression_detected": self.regression_detected,
            "alert_count": len(self.alerts),
            "alerts": [a.to_dict() for a in self.alerts],
            "snapshot": self.snapshot.to_dict(),
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "timestamp": datetime.now().isoformat(),
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def check_metrics_gate(
    storage_path: Path | str | None = None,
    baseline_path: Path | str | None = None,
    days: int = 7,
    fail_on_warning: bool = False,
    regression_threshold: float = 0.05,
) -> CIResult:
    """Run metrics gate check for CI.

    Args:
        storage_path: Path to metrics storage (default: .vrs/metrics)
        baseline_path: Path to baseline snapshot file for comparison
        days: Days of events to include in calculation
        fail_on_warning: If True, warnings also cause failure
        regression_threshold: Threshold for regression detection (default 5%)

    Returns:
        CIResult with exit code, alerts, and details
    """
    tracker = MetricsTracker(Path(storage_path) if storage_path else None)
    snapshot = tracker.calculate_metrics(days=days)

    # Load baseline if provided
    baseline: MetricSnapshot | None = None
    if baseline_path:
        path = Path(baseline_path)
        if not path.exists():
            return CIResult(
                exit_code=ExitCode.BASELINE_NOT_FOUND,
                alerts=[],
                snapshot=snapshot,
                baseline=None,
                message=f"Baseline file not found: {baseline_path}",
            )
        with open(path) as f:
            data = json.load(f)
        baseline = MetricSnapshot.from_dict(data)

    # Check alerts
    alerts = check_alerts(snapshot, baseline, regression_threshold)
    checker = AlertChecker(regression_threshold)

    # Determine exit code
    regression_detected = any(
        a for a in alerts if a.message and "regression" in a.message.lower()
    )

    if checker.has_critical(alerts):
        return CIResult(
            exit_code=ExitCode.CRITICAL_ALERT,
            alerts=alerts,
            snapshot=snapshot,
            baseline=baseline,
            message=f"Critical alert(s) found: {len([a for a in alerts if a.level == AlertLevel.CRITICAL])} critical",
            regression_detected=regression_detected,
        )

    if regression_detected:
        return CIResult(
            exit_code=ExitCode.REGRESSION_DETECTED,
            alerts=alerts,
            snapshot=snapshot,
            baseline=baseline,
            message="Metric regression detected compared to baseline",
            regression_detected=True,
        )

    warning_alerts = [a for a in alerts if a.level == AlertLevel.WARNING]
    if fail_on_warning and warning_alerts:
        return CIResult(
            exit_code=ExitCode.WARNING_ALERT,
            alerts=alerts,
            snapshot=snapshot,
            baseline=baseline,
            message=f"Warning alert(s) found: {len(warning_alerts)} warnings",
            regression_detected=regression_detected,
        )

    return CIResult(
        exit_code=ExitCode.SUCCESS,
        alerts=alerts,
        snapshot=snapshot,
        baseline=baseline,
        message="All metrics within acceptable thresholds",
        regression_detected=False,
    )


def save_baseline(
    output_path: Path | str,
    storage_path: Path | str | None = None,
    days: int = 7,
) -> Path:
    """Save current metrics as baseline for future comparisons.

    Args:
        output_path: Where to save the baseline file
        storage_path: Path to metrics storage
        days: Days of events to include

    Returns:
        Path to saved baseline file
    """
    tracker = MetricsTracker(Path(storage_path) if storage_path else None)
    snapshot = tracker.calculate_metrics(days=days)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        json.dump(snapshot.to_dict(), f, indent=2)

    return output


def compare_snapshots(
    current_path: Path | str,
    baseline_path: Path | str,
    regression_threshold: float = 0.05,
) -> CIResult:
    """Compare two snapshot files for regression.

    Args:
        current_path: Path to current snapshot
        baseline_path: Path to baseline snapshot
        regression_threshold: Threshold for regression detection

    Returns:
        CIResult with comparison results
    """
    with open(current_path) as f:
        current = MetricSnapshot.from_dict(json.load(f))

    with open(baseline_path) as f:
        baseline = MetricSnapshot.from_dict(json.load(f))

    alerts = check_alerts(current, baseline, regression_threshold)
    checker = AlertChecker(regression_threshold)

    regression_detected = any(
        a for a in alerts if a.message and "regression" in a.message.lower()
    )

    if checker.has_critical(alerts):
        exit_code = ExitCode.CRITICAL_ALERT
        message = f"Critical alerts: {len([a for a in alerts if a.level == AlertLevel.CRITICAL])}"
    elif regression_detected:
        exit_code = ExitCode.REGRESSION_DETECTED
        message = "Regression detected"
    elif alerts:
        exit_code = ExitCode.WARNING_ALERT
        message = f"Warnings: {len(alerts)}"
    else:
        exit_code = ExitCode.SUCCESS
        message = "No regression detected"

    return CIResult(
        exit_code=exit_code,
        alerts=alerts,
        snapshot=current,
        baseline=baseline,
        message=message,
        regression_detected=regression_detected,
    )


def format_ci_summary(result: CIResult) -> str:
    """Format CI result as human-readable summary.

    Args:
        result: CIResult to format

    Returns:
        Formatted summary string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("AlphaSwarm Metrics CI Gate")
    lines.append("=" * 60)
    lines.append("")

    # Status
    status_emoji = {
        ExitCode.SUCCESS: "\u2705",
        ExitCode.CRITICAL_ALERT: "\u274C",
        ExitCode.WARNING_ALERT: "\u26A0\uFE0F",
        ExitCode.REGRESSION_DETECTED: "\u2B07\uFE0F",
        ExitCode.BASELINE_NOT_FOUND: "\u2753",
        ExitCode.INVALID_CONFIG: "\u274C",
    }.get(result.exit_code, "\u2753")

    lines.append(f"Status: {status_emoji} {result.exit_code.name}")
    lines.append(f"Message: {result.message}")
    lines.append("")

    # Metric summary
    summary = result.snapshot.get_status_summary()
    lines.append(f"Metrics: {summary[MetricStatus.OK]} OK, "
                 f"{summary[MetricStatus.WARNING]} Warning, "
                 f"{summary[MetricStatus.CRITICAL]} Critical")
    lines.append("")

    # Alerts
    if result.alerts:
        lines.append(f"Alerts ({len(result.alerts)}):")
        lines.append("-" * 40)
        for alert in result.alerts:
            level_emoji = {
                AlertLevel.CRITICAL: "\u274C",
                AlertLevel.WARNING: "\u26A0\uFE0F",
                AlertLevel.INFO: "\u2139\uFE0F",
            }.get(alert.level, "")
            lines.append(f"  {level_emoji} [{alert.level.value}] {alert.metric_name.value}")
            lines.append(f"     {alert.message}")
    else:
        lines.append("No alerts")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> int:
    """CLI entry point for CI metrics check.

    Returns:
        Exit code for CI
    """
    import argparse

    parser = argparse.ArgumentParser(description="AlphaSwarm Metrics CI Gate")
    parser.add_argument("--storage", help="Metrics storage path")
    parser.add_argument("--baseline", help="Baseline snapshot file")
    parser.add_argument("--days", type=int, default=7, help="Days of events")
    parser.add_argument(
        "--fail-on-warning", action="store_true", help="Fail on warnings too"
    )
    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=0.05,
        help="Regression threshold (default 0.05)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--save-baseline", help="Save current metrics as baseline to this path"
    )

    args = parser.parse_args()

    # If saving baseline
    if args.save_baseline:
        path = save_baseline(args.save_baseline, args.storage, args.days)
        print(f"Baseline saved to: {path}")
        return ExitCode.SUCCESS

    # Run check
    result = check_metrics_gate(
        storage_path=args.storage,
        baseline_path=args.baseline,
        days=args.days,
        fail_on_warning=args.fail_on_warning,
        regression_threshold=args.regression_threshold,
    )

    if args.json:
        print(result.to_json())
    else:
        print(format_ci_summary(result))

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
