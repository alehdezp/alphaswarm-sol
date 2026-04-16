"""CLI commands for querying evaluation session data.

Simple SQLite queries formatted for terminal output. Zero AI cost.

Usage:
    uv run alphaswarm eval timeline <session-id>
    uv run alphaswarm eval search "build-kg"
    uv run alphaswarm eval violations --last 10
    uv run alphaswarm eval tasks <session-id>
    uv run alphaswarm eval patterns --workflow audit-full
    uv run alphaswarm eval sessions
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

eval_app = typer.Typer(help="Query evaluation session recordings")

DEFAULT_DB = ".vrs/evaluations/sessions.db"


def _get_recorder(db_path: str = DEFAULT_DB):  # type: ignore[no-untyped-def]
    """Get a SessionRecorder instance, or exit if DB doesn't exist."""
    path = Path(db_path)
    if not path.exists():
        typer.echo(f"No session database found at {db_path}")
        typer.echo("Record an evaluation session first.")
        raise typer.Exit(1)
    from alphaswarm_sol.testing.evaluation.session_recorder import SessionRecorder

    return SessionRecorder(db_path=db_path)


@eval_app.command("sessions")
def list_sessions(
    workflow: Optional[str] = typer.Option(None, "--workflow", "-w", help="Filter by workflow ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max sessions to show"),
    db: str = typer.Option(DEFAULT_DB, "--db", help="Database path"),
) -> None:
    """List recorded evaluation sessions."""
    recorder = _get_recorder(db)
    sessions = recorder.list_sessions(workflow_id=workflow, limit=limit)
    recorder.close()

    if not sessions:
        typer.echo("No sessions recorded.")
        return

    typer.echo(f"{'ID':<38} {'Verdict':<10} {'Contract':<25} {'Score':>6} {'Duration':>8}")
    typer.echo("-" * 90)
    for s in sessions:
        sid = s["id"][:36]
        verdict = s.get("verdict", "?")
        contract = (s.get("contract") or "?")[:24]
        score = s.get("overall_score")
        score_str = f"{score:.1f}" if score is not None else "-"
        duration = s.get("duration_seconds") or 0
        dur_str = f"{duration:.0f}s"
        typer.echo(f"{sid:<38} {verdict:<10} {contract:<25} {score_str:>6} {dur_str:>8}")


@eval_app.command("timeline")
def show_timeline(
    session_id: str = typer.Argument(help="Session ID to show timeline for"),
    db: str = typer.Option(DEFAULT_DB, "--db", help="Database path"),
) -> None:
    """Show chronological timeline of all events in a session."""
    recorder = _get_recorder(db)
    events = recorder.get_session_timeline(session_id)
    recorder.close()

    if not events:
        typer.echo(f"No events found for session {session_id}")
        return

    typer.echo(f"Timeline for session {session_id[:36]}")
    typer.echo(f"{'#':>4} {'Type':<15} {'Summary'}")
    typer.echo("-" * 70)
    for i, e in enumerate(events, 1):
        event_type = e.event_type
        summary = e.summary[:60]
        typer.echo(f"{i:>4} {event_type:<15} {summary}")


@eval_app.command("search")
def search_sessions(
    query: str = typer.Argument(help="FTS5 search query"),
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Limit to session"),
    db: str = typer.Option(DEFAULT_DB, "--db", help="Database path"),
) -> None:
    """Full-text search across tool calls and task actions."""
    recorder = _get_recorder(db)
    results = recorder.search(query, session_id=session_id)
    recorder.close()

    if not results:
        typer.echo(f"No results for '{query}'")
        return

    typer.echo(f"Found {len(results)} results for '{query}'")
    typer.echo(f"{'Table':<15} {'Session':<38} {'Snippet'}")
    typer.echo("-" * 80)
    for r in results[:50]:
        sid = r.session_id[:36]
        snippet = r.snippet.replace("\n", " ")[:60]
        typer.echo(f"{r.table_name:<15} {sid:<38} {snippet}")


@eval_app.command("violations")
def show_violations(
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Limit to session"),
    last: int = typer.Option(10, "--last", "-n", help="Last N sessions to check"),
    db: str = typer.Option(DEFAULT_DB, "--db", help="Database path"),
) -> None:
    """Show violations across sessions."""
    recorder = _get_recorder(db)

    if session_id:
        violations = recorder.query_violations(session_id=session_id)
    else:
        # Get violations from recent sessions
        sessions = recorder.list_sessions(limit=last)
        violations = []
        for s in sessions:
            violations.extend(recorder.query_violations(session_id=s["id"]))
    recorder.close()

    if not violations:
        typer.echo("No violations found.")
        return

    typer.echo(f"Found {len(violations)} violations")
    typer.echo(f"{'Severity':<10} {'Type':<25} {'Evidence'}")
    typer.echo("-" * 80)
    for v in violations:
        evidence = v.evidence[:50].replace("\n", " ")
        typer.echo(f"{v.severity:<10} {v.violation_type:<25} {evidence}")


@eval_app.command("tasks")
def show_tasks(
    session_id: str = typer.Argument(help="Session ID"),
    db: str = typer.Option(DEFAULT_DB, "--db", help="Database path"),
) -> None:
    """Show task actions from a session (check subject quality)."""
    recorder = _get_recorder(db)
    actions = recorder.query_task_actions(session_id)
    recorder.close()

    if not actions:
        typer.echo(f"No task actions for session {session_id[:36]}")
        return

    typer.echo(f"Task actions for session {session_id[:36]}")
    typer.echo(f"{'Action':<10} {'Status':<12} {'Subject'}")
    typer.echo("-" * 70)
    for a in actions:
        subject = a.task_subject[:50] if a.task_subject else "(empty)"
        typer.echo(f"{a.action:<10} {a.task_status:<12} {subject}")


@eval_app.command("patterns")
def show_patterns(
    workflow: Optional[str] = typer.Option(None, "--workflow", "-w", help="Filter by workflow"),
    last: int = typer.Option(10, "--last", "-n", help="Last N sessions"),
    db: str = typer.Option(DEFAULT_DB, "--db", help="Database path"),
) -> None:
    """Show cross-session patterns (most common failures, tool distribution)."""
    recorder = _get_recorder(db)
    report = recorder.get_cross_session_patterns(workflow_id=workflow, last_n=last)
    recorder.close()

    if report.session_count == 0:
        typer.echo("No sessions to analyze.")
        return

    typer.echo(f"Pattern report across {report.session_count} sessions")
    typer.echo()

    # CLI success rate
    typer.echo(f"CLI Success Rate: {report.cli_success_rate:.0%} ({report.cli_successes}/{report.cli_total})")

    # Task subject quality
    if report.total_task_creates > 0:
        typer.echo(
            f"Task Subject Quality: {report.empty_task_subjects} empty "
            f"of {report.total_task_creates} creates"
        )

    # Top violations
    if report.most_common_violations:
        typer.echo()
        typer.echo("Most Common Violations:")
        for vtype, count in report.most_common_violations[:10]:
            typer.echo(f"  {count:>4}x  {vtype}")

    # Tool distribution
    if report.tool_usage_distribution:
        typer.echo()
        typer.echo("Tool Usage Distribution:")
        for tool, count in sorted(
            report.tool_usage_distribution.items(), key=lambda x: -x[1]
        )[:15]:
            typer.echo(f"  {count:>4}x  {tool}")


@eval_app.command("cli-attempts")
def show_cli(
    session_id: str = typer.Argument(help="Session ID"),
    db: str = typer.Option(DEFAULT_DB, "--db", help="Database path"),
) -> None:
    """Show CLI (build-kg, query) attempts for a session."""
    recorder = _get_recorder(db)
    attempts = recorder.query_cli_attempts(session_id)
    recorder.close()

    if not attempts:
        typer.echo(f"No CLI attempts for session {session_id[:36]}")
        return

    typer.echo(f"CLI attempts for session {session_id[:36]}")
    typer.echo(f"{'State':<22} {'Exit':<6} {'Command'}")
    typer.echo("-" * 70)
    for a in attempts:
        cmd = a.command[:50]
        exit_str = str(a.exit_code) if a.exit_code is not None else "?"
        typer.echo(f"{a.state:<22} {exit_str:<6} {cmd}")
