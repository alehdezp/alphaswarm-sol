"""CLI commands for metrics and observability.

Task 8.5: CLI interface for metrics module.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import typer

from alphaswarm_sol.metrics import (
    MetricName,
    MetricStatus,
    MetricsTracker,
    HistoryStore,
    AlertChecker,
    check_alerts,
    get_definition,
    get_all_definitions,
    check_metrics_gate,
    save_baseline,
    compare_snapshots,
    format_ci_summary,
    ExitCode,
)

metrics_app = typer.Typer(help="Metrics and observability commands")


def _get_tracker(storage_path: str | None = None) -> MetricsTracker:
    """Get MetricsTracker instance."""
    path = Path(storage_path) if storage_path else None
    return MetricsTracker(path)


def _status_emoji(status: MetricStatus) -> str:
    """Return emoji for status."""
    return {
        MetricStatus.OK: "\u2705",  # green check
        MetricStatus.WARNING: "\u26A0\uFE0F",  # warning
        MetricStatus.CRITICAL: "\u274C",  # red X
        MetricStatus.UNKNOWN: "\u2753",  # question mark
    }.get(status, "\u2753")


def _format_value(value: float, name: MetricName) -> str:
    """Format value based on metric type."""
    if name in (MetricName.TOKEN_EFFICIENCY,):
        return f"{value:.0f} tokens"
    elif name in (MetricName.TIME_TO_DETECTION,):
        return f"{value:.1f}s"
    else:
        return f"{value:.1%}"


@metrics_app.command("show")
def show(
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    days: int = typer.Option(7, "--days", help="Days of events to include"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
) -> None:
    """Show current metric values.

    Calculates metrics from recent events and displays them.
    """
    tracker = _get_tracker(storage)
    snapshot = tracker.calculate_metrics(days=days)

    if format == "json":
        typer.echo(json.dumps(snapshot.to_dict(), indent=2))
        return

    # Human-readable output
    typer.echo("VKG Metrics")
    typer.echo("=" * 60)
    typer.echo(f"Timestamp: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    typer.echo(f"Version:   {snapshot.version}")
    typer.echo(f"Events:    Last {days} days")
    typer.echo("")

    # Group by status
    critical = []
    warning = []
    ok = []
    unknown = []

    for name, metric in sorted(snapshot.metrics.items(), key=lambda x: x[0].value):
        status = metric.evaluate_status()
        entry = (name, metric, status)

        if status == MetricStatus.CRITICAL:
            critical.append(entry)
        elif status == MetricStatus.WARNING:
            warning.append(entry)
        elif status == MetricStatus.OK:
            ok.append(entry)
        else:
            unknown.append(entry)

    # Print in order of severity
    for entries, header in [
        (critical, "CRITICAL"),
        (warning, "WARNING"),
        (ok, "OK"),
        (unknown, "UNKNOWN"),
    ]:
        if entries:
            typer.echo(f"\n{header}")
            typer.echo("-" * 40)
            for name, metric, status in entries:
                emoji = _status_emoji(status)
                value_str = _format_value(metric.value, name)
                target_str = _format_value(metric.target, name)
                typer.echo(f"  {emoji} {name.value}: {value_str} (target: {target_str})")

    typer.echo("")
    typer.echo("-" * 60)
    summary = snapshot.get_status_summary()
    typer.echo(
        f"Summary: {summary[MetricStatus.OK]} OK, "
        f"{summary[MetricStatus.WARNING]} Warning, "
        f"{summary[MetricStatus.CRITICAL]} Critical"
    )


@metrics_app.command("history")
def history(
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    days: int = typer.Option(30, "--days", help="Days of history to show"),
    metric: str | None = typer.Option(None, "--metric", "-m", help="Filter to specific metric"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max snapshots to show"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
) -> None:
    """Show historical metric values.

    Displays metric snapshots from the history store.
    """
    tracker = _get_tracker(storage)
    snapshots = tracker.get_history(days=days, limit=limit)

    if format == "json":
        output = [s.to_dict() for s in snapshots]
        typer.echo(json.dumps(output, indent=2))
        return

    if not snapshots:
        typer.echo(f"No history found for the last {days} days.")
        return

    typer.echo(f"Metric History (last {days} days, showing {len(snapshots)} snapshots)")
    typer.echo("=" * 70)
    typer.echo("")

    if metric:
        # Show trend for single metric
        try:
            metric_name = MetricName(metric)
        except ValueError:
            typer.echo(f"Unknown metric: {metric}", err=True)
            typer.echo(f"Valid metrics: {', '.join(m.value for m in MetricName)}", err=True)
            raise typer.Exit(code=1)

        typer.echo(f"Trend for: {metric_name.value}")
        typer.echo("-" * 40)

        for snapshot in snapshots:
            if metric_name in snapshot.metrics:
                m = snapshot.metrics[metric_name]
                status = m.evaluate_status()
                emoji = _status_emoji(status)
                value_str = _format_value(m.value, metric_name)
                ts = snapshot.timestamp.strftime("%Y-%m-%d %H:%M")
                typer.echo(f"  {ts}  {emoji} {value_str}")
            else:
                ts = snapshot.timestamp.strftime("%Y-%m-%d %H:%M")
                typer.echo(f"  {ts}  -- no data --")
    else:
        # Show all snapshots
        for snapshot in snapshots:
            ts = snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            typer.echo(f"\n{ts}")
            typer.echo("-" * 40)

            for name, m in sorted(snapshot.metrics.items(), key=lambda x: x[0].value):
                status = m.evaluate_status()
                emoji = _status_emoji(status)
                value_str = _format_value(m.value, name)
                typer.echo(f"  {emoji} {name.value}: {value_str}")


@metrics_app.command("alerts")
def alerts(
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    days: int = typer.Option(7, "--days", help="Days of events to include"),
    baseline: str | None = typer.Option(None, "--baseline", help="Compare against baseline snapshot file"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
    fail_on_critical: bool = typer.Option(False, "--fail-on-critical", help="Exit with code 1 if critical alerts"),
) -> None:
    """Check for metric alerts.

    Evaluates current metrics against thresholds and optionally
    against a baseline for regression detection.
    """
    tracker = _get_tracker(storage)
    snapshot = tracker.calculate_metrics(days=days)

    # Load baseline if provided
    baseline_snapshot = None
    if baseline:
        baseline_path = Path(baseline)
        if not baseline_path.exists():
            typer.echo(f"Baseline file not found: {baseline}", err=True)
            raise typer.Exit(code=1)

        with open(baseline_path) as f:
            data = json.load(f)
        from alphaswarm_sol.metrics import MetricSnapshot

        baseline_snapshot = MetricSnapshot.from_dict(data)

    # Check alerts
    alert_list = check_alerts(snapshot, baseline_snapshot)

    if format == "json":
        output = [a.to_dict() for a in alert_list]
        typer.echo(json.dumps(output, indent=2))
    else:
        if not alert_list:
            typer.echo("\u2705 No alerts - all metrics within thresholds")
        else:
            typer.echo(f"Found {len(alert_list)} alert(s)")
            typer.echo("=" * 60)
            typer.echo("")

            for alert in alert_list:
                level_emoji = {
                    "critical": "\u274C",
                    "warning": "\u26A0\uFE0F",
                    "info": "\u2139\uFE0F",
                }.get(alert.level.value, "\u2753")

                typer.echo(f"{level_emoji} [{alert.level.value.upper()}] {alert.metric_name.value}")
                typer.echo(f"   {alert.message}")
                typer.echo("")

    # Exit with error if critical and flag set
    if fail_on_critical:
        checker = AlertChecker()
        if checker.has_critical(alert_list):
            raise typer.Exit(code=1)


@metrics_app.command("save")
def save(
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    days: int = typer.Option(7, "--days", help="Days of events to include"),
) -> None:
    """Save current metrics snapshot to history.

    Calculates current metrics and persists them to the history store
    for trend analysis.
    """
    tracker = _get_tracker(storage)
    snapshot = tracker.calculate_metrics(days=days)
    filepath = tracker.save_snapshot(snapshot)

    typer.echo(f"Snapshot saved to: {filepath}")
    typer.echo(f"Timestamp: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    # Show summary
    summary = snapshot.get_status_summary()
    typer.echo(
        f"Metrics: {summary[MetricStatus.OK]} OK, "
        f"{summary[MetricStatus.WARNING]} Warning, "
        f"{summary[MetricStatus.CRITICAL]} Critical"
    )


@metrics_app.command("definitions")
def definitions(
    metric: str | None = typer.Option(None, "--metric", "-m", help="Show specific metric definition"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
) -> None:
    """Show metric definitions with thresholds.

    Displays all metric definitions including formulas, thresholds,
    and data sources.
    """
    if metric:
        try:
            metric_name = MetricName(metric)
        except ValueError:
            typer.echo(f"Unknown metric: {metric}", err=True)
            typer.echo(f"Valid metrics: {', '.join(m.value for m in MetricName)}", err=True)
            raise typer.Exit(code=1)

        defn = get_definition(metric_name)
        definitions = {metric_name: defn}
    else:
        definitions = get_all_definitions()

    if format == "json":
        output = {}
        for name, defn in definitions.items():
            output[name.value] = {
                "formula": defn.formula,
                "description": defn.description,
                "target": defn.target,
                "threshold_warning": defn.threshold_warning,
                "threshold_critical": defn.threshold_critical,
                "unit": defn.unit,
                "higher_is_better": defn.higher_is_better,
                "data_sources": defn.data_sources,
                "dependencies": defn.dependencies,
            }
        typer.echo(json.dumps(output, indent=2))
        return

    # Human-readable
    typer.echo("VKG Metric Definitions")
    typer.echo("=" * 70)
    typer.echo("")

    for name, defn in sorted(definitions.items(), key=lambda x: x[0].value):
        typer.echo(f"\u2022 {name.value}")
        typer.echo(f"  Description: {defn.description}")
        typer.echo(f"  Formula:     {defn.formula}")
        typer.echo(f"  Target:      {_format_value(defn.target, name)}")
        typer.echo(f"  Warning:     {_format_value(defn.threshold_warning, name)}")
        typer.echo(f"  Critical:    {_format_value(defn.threshold_critical, name)}")
        typer.echo(f"  Direction:   {'Higher is better' if defn.higher_is_better else 'Lower is better'}")
        if defn.dependencies:
            typer.echo(f"  Requires:    {', '.join(defn.dependencies)}")
        typer.echo("")


@metrics_app.command("cleanup")
def cleanup(
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    retention_days: int = typer.Option(90, "--retention", "-r", help="Keep snapshots from last N days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted"),
) -> None:
    """Clean up old metric snapshots.

    Removes snapshots older than the retention period to manage storage.
    """
    tracker = _get_tracker(storage)

    if dry_run:
        # Count what would be deleted
        all_snapshots = tracker.history.get_history(days=9999)  # Get all
        cutoff = datetime.now() - timedelta(days=retention_days)
        would_delete = [s for s in all_snapshots if s.timestamp < cutoff]

        typer.echo(f"Would delete {len(would_delete)} snapshots older than {retention_days} days")
        for s in would_delete[:5]:
            typer.echo(f"  - {s.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if len(would_delete) > 5:
            typer.echo(f"  ... and {len(would_delete) - 5} more")
    else:
        removed = tracker.cleanup_history(retention_days)
        typer.echo(f"Removed {removed} snapshots older than {retention_days} days")


@metrics_app.command("stats")
def stats(
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    metric: str = typer.Option(..., "--metric", "-m", help="Metric to analyze"),
    days: int = typer.Option(30, "--days", help="Days of history to analyze"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
) -> None:
    """Show statistics for a metric over time.

    Calculates min, max, average, and trend for a specific metric.
    """
    try:
        metric_name = MetricName(metric)
    except ValueError:
        typer.echo(f"Unknown metric: {metric}", err=True)
        typer.echo(f"Valid metrics: {', '.join(m.value for m in MetricName)}", err=True)
        raise typer.Exit(code=1)

    tracker = _get_tracker(storage)
    stats = tracker.get_metric_statistics(metric_name, days=days)

    if stats is None:
        typer.echo(f"No data available for {metric_name.value} in the last {days} days")
        return

    if format == "json":
        typer.echo(json.dumps(stats, indent=2))
        return

    typer.echo(f"Statistics for: {metric_name.value}")
    typer.echo(f"Period: Last {days} days ({stats['count']} data points)")
    typer.echo("=" * 50)
    typer.echo(f"  Min:     {_format_value(stats['min'], metric_name)}")
    typer.echo(f"  Max:     {_format_value(stats['max'], metric_name)}")
    typer.echo(f"  Average: {_format_value(stats['avg'], metric_name)}")
    typer.echo(f"  Latest:  {_format_value(stats['latest'], metric_name)}")

    # Show trend direction
    if stats['count'] >= 2:
        defn = get_definition(metric_name)
        if defn.higher_is_better:
            trend = "improving" if stats['latest'] > stats['avg'] else "declining"
        else:
            trend = "improving" if stats['latest'] < stats['avg'] else "declining"
        typer.echo(f"  Trend:   {trend}")


@metrics_app.command("ci-check")
def ci_check(
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    baseline: str | None = typer.Option(None, "--baseline", "-b", help="Baseline snapshot file for comparison"),
    days: int = typer.Option(7, "--days", help="Days of events to include"),
    fail_on_warning: bool = typer.Option(False, "--fail-on-warning", help="Also fail on warning-level alerts"),
    regression_threshold: float = typer.Option(0.05, "--regression-threshold", help="Threshold for regression detection (default 5%)"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
) -> None:
    """Run CI gate check on metrics.

    Evaluates metrics against thresholds and optionally against a baseline.
    Returns appropriate exit codes for CI integration.

    Exit codes:
    - 0: Success - all metrics within thresholds
    - 1: Critical alert - at least one metric in critical state
    - 2: Warning alert (with --fail-on-warning)
    - 3: Regression detected compared to baseline
    - 4: Baseline file not found
    """
    result = check_metrics_gate(
        storage_path=storage,
        baseline_path=baseline,
        days=days,
        fail_on_warning=fail_on_warning,
        regression_threshold=regression_threshold,
    )

    if format == "json":
        typer.echo(result.to_json())
    else:
        typer.echo(format_ci_summary(result))

    if result.exit_code != ExitCode.SUCCESS:
        raise typer.Exit(code=result.exit_code.value)


@metrics_app.command("save-baseline")
def save_baseline_cmd(
    output: str = typer.Argument(..., help="Path to save baseline file"),
    storage: str | None = typer.Option(None, "--storage", help="Storage path override"),
    days: int = typer.Option(7, "--days", help="Days of events to include"),
) -> None:
    """Save current metrics as baseline for CI comparisons.

    Creates a snapshot file that can be used with --baseline in ci-check
    to detect metric regressions.
    """
    path = save_baseline(output, storage, days)
    typer.echo(f"Baseline saved to: {path}")


@metrics_app.command("compare")
def compare_cmd(
    current: str = typer.Argument(..., help="Path to current snapshot file"),
    baseline: str = typer.Argument(..., help="Path to baseline snapshot file"),
    regression_threshold: float = typer.Option(0.05, "--regression-threshold", help="Threshold for regression detection"),
    format: str = typer.Option("human", "--format", "-f", help="Output format: human or json"),
) -> None:
    """Compare two metric snapshots for regression.

    Compares a current snapshot against a baseline to detect
    metric regressions or improvements.
    """
    from pathlib import Path as P

    current_path = P(current)
    baseline_path = P(baseline)

    if not current_path.exists():
        typer.echo(f"Current snapshot not found: {current}", err=True)
        raise typer.Exit(code=1)

    if not baseline_path.exists():
        typer.echo(f"Baseline snapshot not found: {baseline}", err=True)
        raise typer.Exit(code=1)

    result = compare_snapshots(current_path, baseline_path, regression_threshold)

    if format == "json":
        typer.echo(result.to_json())
    else:
        typer.echo(format_ci_summary(result))

    if result.exit_code != ExitCode.SUCCESS:
        raise typer.Exit(code=result.exit_code.value)
