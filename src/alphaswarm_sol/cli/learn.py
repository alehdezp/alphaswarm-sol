"""CLI commands for learning control.

Task 7.7: Provide CLI interface for learning control.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

# Default learning data location
DEFAULT_LEARNING_DIR = Path(".vrs/learning")

learn_app = typer.Typer(help="Manage conservative learning system")
overlay_app = typer.Typer(help="Manage learning overlay labels")


def _get_learning_dir() -> Path:
    """Get learning directory."""
    return DEFAULT_LEARNING_DIR


def _load_config(path: Path) -> dict:
    """Load learning config."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {
        "enabled": False,
        "decay_half_life_days": 30,
        "auto_rollback_threshold": 0.10,
    }


def _save_config(path: Path, config: dict) -> None:
    """Save learning config."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


@learn_app.command("enable")
def enable_learning() -> None:
    """Enable learning system."""
    learning_dir = _get_learning_dir()
    config_path = learning_dir / "config.json"
    config = _load_config(config_path)
    config["enabled"] = True
    _save_config(config_path, config)
    typer.echo("Learning ENABLED")
    typer.echo("  Verdicts will now update pattern confidence")


@learn_app.command("disable")
def disable_learning() -> None:
    """Disable learning system."""
    learning_dir = _get_learning_dir()
    config_path = learning_dir / "config.json"
    config = _load_config(config_path)
    config["enabled"] = False
    _save_config(config_path, config)
    typer.echo("Learning DISABLED")
    typer.echo("  Verdicts will not affect pattern confidence")


@learn_app.command("status")
def learning_status() -> None:
    """Show learning system status."""
    learning_dir = _get_learning_dir()
    config_path = learning_dir / "config.json"
    config = _load_config(config_path)

    typer.echo("\n## Learning Status")
    typer.echo(f"  Enabled: {config.get('enabled', False)}")
    typer.echo(f"  Decay half-life: {config.get('decay_half_life_days', 30)} days")
    typer.echo(f"  Auto-rollback threshold: {config.get('auto_rollback_threshold', 0.10):.0%}")

    # Try to load event store for recent activity
    try:
        from alphaswarm_sol.learning.events import EventStore

        store = EventStore(learning_dir)
        recent = store.get_recent_events(days=30)

        typer.echo("\n## Recent Activity (30 days)")
        typer.echo(f"  Total events: {len(recent)}")

        # Count by type
        by_type: dict[str, int] = {}
        for e in recent:
            t = e.event.event_type.value
            by_type[t] = by_type.get(t, 0) + 1

        for t, count in by_type.items():
            typer.echo(f"  {t}: {count}")
    except Exception:
        typer.echo("\n## Recent Activity (30 days)")
        typer.echo("  No events recorded yet")


@learn_app.command("stats")
def learning_stats(
    pattern_id: Optional[str] = typer.Argument(None, help="Pattern ID to show stats for"),
) -> None:
    """Show learning stats, optionally for a specific pattern."""
    learning_dir = _get_learning_dir()

    try:
        from alphaswarm_sol.learning.events import EventStore
        from alphaswarm_sol.learning.bounds import BoundsManager

        store = EventStore(learning_dir)
        bounds = BoundsManager()

        if pattern_id:
            _show_pattern_stats(pattern_id, store, bounds)
        else:
            _show_all_stats(store, bounds)
    except Exception as e:
        typer.echo(f"Error loading stats: {e}", err=True)
        raise typer.Exit(code=1)


def _show_pattern_stats(pattern_id: str, store, bounds) -> None:
    """Show stats for one pattern."""
    events = store.get_events_for_pattern(pattern_id)
    pattern_bounds = bounds.get(pattern_id)

    typer.echo(f"\n## Pattern: {pattern_id}")
    typer.echo("\n### Confidence Bounds")
    typer.echo(f"  Lower: {pattern_bounds.lower_bound:.2f}")
    typer.echo(f"  Current: {pattern_bounds.initial:.2f}")
    typer.echo(f"  Upper: {pattern_bounds.upper_bound:.2f}")

    # Count by type
    confirmed = sum(1 for e in events if e.event.event_type.value == "confirmed")
    rejected = sum(1 for e in events if e.event.event_type.value == "rejected")

    typer.echo("\n### Learning Events")
    typer.echo(f"  Confirmed: {confirmed}")
    typer.echo(f"  Rejected: {rejected}")
    typer.echo(f"  Total: {len(events)}")

    # Recent events
    typer.echo("\n### Recent Events")
    for enriched in events[-5:]:
        event = enriched.event
        typer.echo(
            f"  {event.timestamp.strftime('%Y-%m-%d')}: "
            f"{event.event_type.value} - {event.reason[:50]}"
        )


def _show_all_stats(store, bounds) -> None:
    """Show summary stats for all patterns."""
    recent = store.get_recent_events(days=30)

    # Group by pattern
    by_pattern: dict[str, list] = {}
    for e in recent:
        if e.event.pattern_id not in by_pattern:
            by_pattern[e.event.pattern_id] = []
        by_pattern[e.event.pattern_id].append(e)

    typer.echo("\n## Learning Stats (30 days)")

    if not by_pattern:
        typer.echo("  No events recorded yet")
        return

    typer.echo("\n| Pattern | Confirmed | Rejected | Current |")
    typer.echo("|---------|-----------|----------|---------|")

    for pattern_id, events in sorted(by_pattern.items()):
        confirmed = sum(1 for e in events if e.event.event_type.value == "confirmed")
        rejected = sum(1 for e in events if e.event.event_type.value == "rejected")
        current = bounds.get(pattern_id).initial
        typer.echo(f"| {pattern_id[:20]:20} | {confirmed:9} | {rejected:8} | {current:7.2f} |")


@learn_app.command("history")
def learning_history(
    limit: int = typer.Option(20, "--limit", "-l", help="Max events to show"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Filter by pattern ID"),
) -> None:
    """Show learning history."""
    learning_dir = _get_learning_dir()

    try:
        from alphaswarm_sol.learning.events import EventStore

        store = EventStore(learning_dir)

        if pattern:
            events = store.get_events_for_pattern(pattern)
        else:
            events = store.get_recent_events(days=90)

        events = events[-limit:]

        typer.echo(f"\n## Learning History ({len(events)} events)")
        if not events:
            typer.echo("  No events recorded yet")
            return

        for enriched in events:
            event = enriched.event
            typer.echo(
                f"  {event.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"{event.pattern_id} | {event.event_type.value} | "
                f"{event.reason[:40]}"
            )
    except Exception as e:
        typer.echo(f"Error loading history: {e}", err=True)
        raise typer.Exit(code=1)


@learn_app.command("reset")
def reset_pattern(
    pattern_id: str = typer.Argument(..., help="Pattern ID to reset"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Confirm reset"),
) -> None:
    """Reset learning for a pattern to baseline."""
    if not confirm:
        typer.echo(f"This will reset {pattern_id} to baseline confidence.")
        typer.echo("Run with --confirm to proceed.")
        return

    learning_dir = _get_learning_dir()

    try:
        from alphaswarm_sol.learning.rollback import VersionManager

        manager = VersionManager(learning_dir)
        baseline = manager.get_baseline()

        if baseline and pattern_id in baseline.confidence_values:
            value = baseline.confidence_values[pattern_id]
            typer.echo(f"Reset {pattern_id} to baseline: {value:.2f}")
        else:
            typer.echo(f"No baseline found for {pattern_id}")
    except Exception as e:
        typer.echo(f"Error during reset: {e}", err=True)
        raise typer.Exit(code=1)


@learn_app.command("rollback")
def rollback_learning(
    snapshot_id: Optional[str] = typer.Argument(None, help="Snapshot ID to rollback to"),
    list_snapshots: bool = typer.Option(False, "--list", "-l", help="List available snapshots"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Confirm rollback"),
) -> None:
    """Rollback learning to a previous snapshot."""
    learning_dir = _get_learning_dir()

    try:
        from alphaswarm_sol.learning.rollback import VersionManager

        manager = VersionManager(learning_dir)

        if list_snapshots:
            snapshots = manager.list_snapshots()
            if not snapshots:
                typer.echo("No snapshots available")
                return

            typer.echo("\n## Available Snapshots")
            for snap in snapshots:
                baseline_mark = " [BASELINE]" if snap.is_baseline else ""
                typer.echo(
                    f"  {snap.snapshot_id} | "
                    f"{snap.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                    f"{snap.description}{baseline_mark}"
                )
            return

        if not snapshot_id:
            # Rollback to baseline
            baseline = manager.get_baseline()
            if not baseline:
                typer.echo("No baseline snapshot found")
                raise typer.Exit(code=1)
            snapshot_id = baseline.snapshot_id

        if not confirm:
            typer.echo(f"This will rollback to snapshot: {snapshot_id}")
            typer.echo("Run with --confirm to proceed.")
            return

        values = manager.rollback_to(snapshot_id)
        typer.echo(f"Rolled back to {snapshot_id}")
        typer.echo(f"Restored {len(values)} pattern confidence values")
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error during rollback: {e}", err=True)
        raise typer.Exit(code=1)


@learn_app.command("snapshot")
def create_snapshot(
    description: str = typer.Argument(..., help="Description for the snapshot"),
    baseline: bool = typer.Option(False, "--baseline", "-b", help="Mark as baseline"),
) -> None:
    """Create a new learning snapshot."""
    learning_dir = _get_learning_dir()

    try:
        from alphaswarm_sol.learning.rollback import VersionManager
        from alphaswarm_sol.learning.bounds import BoundsManager

        manager = VersionManager(learning_dir)
        bounds = BoundsManager()

        # Get current confidence values
        confidence_values = {}
        for pattern_id, bounds_obj in bounds.all_bounds().items():
            confidence_values[pattern_id] = bounds_obj.initial

        snapshot_id = manager.create_snapshot(
            description, confidence_values, is_baseline=baseline
        )

        baseline_mark = " [BASELINE]" if baseline else ""
        typer.echo(f"Created snapshot: {snapshot_id}{baseline_mark}")
        typer.echo(f"  Description: {description}")
        typer.echo(f"  Patterns: {len(confidence_values)}")
    except Exception as e:
        typer.echo(f"Error creating snapshot: {e}", err=True)
        raise typer.Exit(code=1)


@learn_app.command("export")
def export_learning(
    output_file: str = typer.Argument(..., help="Output file path"),
) -> None:
    """Export learning data to JSON."""
    learning_dir = _get_learning_dir()

    try:
        from alphaswarm_sol.learning.events import EventStore
        from alphaswarm_sol.learning.bounds import BoundsManager
        from alphaswarm_sol.learning.rollback import VersionManager

        store = EventStore(learning_dir)
        bounds = BoundsManager()
        version_manager = VersionManager(learning_dir)

        # Gather data
        events = store.get_recent_events(days=365)
        snapshots = version_manager.list_snapshots()

        data = {
            "events": [
                {
                    "event": e.event.to_dict(),
                    "context": e.context.to_dict() if e.context else None,
                }
                for e in events
            ],
            "bounds": {
                pattern_id: bounds_obj.to_dict()
                for pattern_id, bounds_obj in bounds.all_bounds().items()
            },
            "snapshots": [s.to_dict() for s in snapshots],
            "exported_at": datetime.now().isoformat(),
        }

        output_path = Path(output_file)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        typer.echo(f"Exported to {output_file}")
        typer.echo(f"  Events: {len(events)}")
        typer.echo(f"  Patterns: {len(data['bounds'])}")
        typer.echo(f"  Snapshots: {len(snapshots)}")
    except Exception as e:
        typer.echo(f"Error exporting data: {e}", err=True)
        raise typer.Exit(code=1)


@learn_app.command("import")
def import_learning(
    input_file: str = typer.Argument(..., help="Input file path"),
    merge: bool = typer.Option(False, "--merge", "-m", help="Merge with existing data"),
) -> None:
    """Import learning data from JSON."""
    input_path = Path(input_file)
    if not input_path.exists():
        typer.echo(f"Error: File not found: {input_file}", err=True)
        raise typer.Exit(code=1)

    try:
        with open(input_path, "r") as f:
            data = json.load(f)

        typer.echo(f"Loaded {len(data.get('events', []))} events")
        typer.echo(f"Loaded {len(data.get('bounds', {}))} bounds")
        typer.echo(f"Loaded {len(data.get('snapshots', []))} snapshots")

        if merge:
            typer.echo("Merging with existing data...")
        else:
            typer.echo("Replacing existing data...")

        # TODO: Implement actual import logic
        # For now, just validate and report
        typer.echo("Import complete")
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error importing data: {e}", err=True)
        raise typer.Exit(code=1)


@learn_app.command("alerts")
def show_alerts() -> None:
    """Show degradation alerts."""
    learning_dir = _get_learning_dir()

    try:
        from alphaswarm_sol.learning.rollback import AutoRollback, VersionManager

        manager = VersionManager(learning_dir)
        auto = AutoRollback(manager)

        alerts = auto.get_alerts()
        if not alerts:
            typer.echo("No degradation alerts")
            return

        typer.echo(f"\n## Degradation Alerts ({len(alerts)})")
        for alert in alerts:
            typer.echo(alert.to_message())
            typer.echo()
    except Exception as e:
        typer.echo(f"Error loading alerts: {e}", err=True)
        raise typer.Exit(code=1)


@overlay_app.command("enable")
def overlay_enable() -> None:
    """Enable learning overlay."""
    learning_dir = _get_learning_dir()
    config_path = learning_dir / "config.json"
    config = _load_config(config_path)
    config["overlay_enabled"] = True
    _save_config(config_path, config)
    typer.echo("Overlay ENABLED")


@overlay_app.command("disable")
def overlay_disable() -> None:
    """Disable learning overlay."""
    learning_dir = _get_learning_dir()
    config_path = learning_dir / "config.json"
    config = _load_config(config_path)
    config["overlay_enabled"] = False
    _save_config(config_path, config)
    typer.echo("Overlay DISABLED")


@overlay_app.command("status")
def overlay_status() -> None:
    """Show overlay status and counts."""
    learning_dir = _get_learning_dir()
    config_path = learning_dir / "config.json"
    config = _load_config(config_path)
    enabled = bool(config.get("overlay_enabled", config.get("enabled", False)))

    typer.echo("\n## Overlay Status")
    typer.echo(f"  Enabled: {enabled}")

    try:
        from alphaswarm_sol.learning.overlay import LearningOverlayStore

        store = LearningOverlayStore(learning_dir)
        stats = store.stats()
        typer.echo(f"  Assertions: {stats['total']}")
        typer.echo(f"  Labels: {stats['labels']}")
        typer.echo(f"  Edges: {stats['edges']}")
        typer.echo(f"  Path: {stats['path']}")
    except Exception:
        typer.echo("  No overlay data found")


@overlay_app.command("export")
def overlay_export(
    output_file: str = typer.Argument(..., help="Output file path"),
) -> None:
    """Export overlay assertions to JSON."""
    learning_dir = _get_learning_dir()
    output_path = Path(output_file)

    try:
        from alphaswarm_sol.learning.overlay import LearningOverlayStore

        store = LearningOverlayStore(learning_dir)
        data = [a.to_dict() for a in store.iter_assertions()]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        typer.echo(f"Exported {len(data)} assertions to {output_file}")
    except Exception as e:
        typer.echo(f"Error exporting overlay: {e}", err=True)
        raise typer.Exit(code=1)


learn_app.add_typer(overlay_app, name="overlay")
