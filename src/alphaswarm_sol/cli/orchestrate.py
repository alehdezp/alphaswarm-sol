"""CLI commands for pool orchestration management.

CLI interface for managing audit pools, starting audits, resuming from
checkpoints, and viewing pool status.

Philosophy: "All verdicts require human review" per PHILOSOPHY.md.
The CLI provides commands for:
- Starting new audits
- Resuming from checkpoints
- Viewing pool status
- Listing all pools
- Managing beads within pools
- Running multi-agent SDK orchestration (SDK-08 parity)
- Runtime selection (--runtime flag)
- Model rankings display (--show-rankings flag)

Implements SDK-08: CLI + SDK drive same artifact contract.
Implements 05.3-09: CLI runtime selection and rankings display.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import structlog
import typer

from alphaswarm_sol.agents.runtime.factory import (
    RuntimeType,
    create_runtime,
    get_available_runtimes,
)

from alphaswarm_sol.orchestration import (
    Pool,
    PoolManager,
    PoolStatus,
    Scope,
    ExecutionLoop,
    LoopConfig,
    create_default_handlers,
    RouteAction,
)

orchestrate_app = typer.Typer(help="Pool orchestration management for audits")
logger = structlog.get_logger()


# =============================================================================
# Runtime Selection Helper
# =============================================================================


class RuntimeChoice(str, Enum):
    """Runtime choices for CLI selection."""

    OPENCODE = "opencode"
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    API = "api"
    AUTO = "auto"


def _normalize_runtime(choice: RuntimeChoice) -> RuntimeType:
    """Convert CLI runtime choice to RuntimeType.

    Args:
        choice: CLI runtime choice

    Returns:
        RuntimeType enum value
    """
    mapping = {
        RuntimeChoice.OPENCODE: RuntimeType.OPENCODE,
        RuntimeChoice.CLAUDE_CODE: RuntimeType.CLAUDE_CODE,
        RuntimeChoice.CODEX: RuntimeType.CODEX,
        RuntimeChoice.API: RuntimeType.ANTHROPIC,  # API defaults to Anthropic
        RuntimeChoice.AUTO: RuntimeType.AUTO,
    }
    return mapping.get(choice, RuntimeType.AUTO)


def _display_rankings(store_path: Optional[Path] = None) -> None:
    """Display current model rankings.

    Loads rankings from the store and displays them in a formatted table.

    Args:
        store_path: Optional custom path to rankings store
    """
    from alphaswarm_sol.agents.ranking import RankingsStore

    store = RankingsStore(path=store_path)

    if not store.exists():
        typer.echo("No rankings found. Run benchmarks to generate rankings.")
        typer.echo("  Use: alphaswarm benchmark run --all-models")
        return

    # Load and display rankings
    rankings_data = store.load()

    if not rankings_data:
        typer.echo("Rankings file exists but contains no data.")
        return

    typer.echo("\n" + "=" * 70)
    typer.echo("MODEL RANKINGS")
    typer.echo("=" * 70)

    for task_type, model_rankings in sorted(rankings_data.items()):
        typer.echo(f"\n## {task_type.upper()}")
        typer.echo("-" * 70)
        typer.echo(
            f"{'Rank':<5} {'Model':<35} {'Score':<8} {'Quality':<8} {'Cost':<10}"
        )
        typer.echo("-" * 70)

        # Sort by composite score
        sorted_rankings = sorted(
            model_rankings.values(),
            key=lambda r: r.score(),
            reverse=True,
        )

        for rank, ranking in enumerate(sorted_rankings[:5], 1):
            model_short = ranking.model_id[:33] + ".." if len(ranking.model_id) > 35 else ranking.model_id
            score = f"{ranking.score():.3f}"
            quality = f"{ranking.quality_score:.2f}"
            cost = f"${ranking.cost_per_task:.4f}"
            typer.echo(f"{rank:<5} {model_short:<35} {score:<8} {quality:<8} {cost:<10}")

    typer.echo("\n" + "=" * 70)
    stats = store.get_stats()
    typer.echo(f"Total rankings: {stats['total_rankings']}")
    typer.echo(f"Task types: {len(stats['task_types'])}")
    typer.echo("=" * 70 + "\n")


def _reset_rankings(store_path: Optional[Path] = None) -> None:
    """Reset all model rankings.

    Args:
        store_path: Optional custom path to rankings store
    """
    from alphaswarm_sol.agents.ranking import RankingsStore

    store = RankingsStore(path=store_path)
    store.reset()
    typer.echo("Rankings have been reset.")
    typer.echo("Run benchmarks to regenerate rankings:")
    typer.echo("  alphaswarm benchmark run --all-models")


# =============================================================================
# Constants
# =============================================================================

DEFAULT_POOL_DIR = Path(".vrs/pools")


# =============================================================================
# Enums
# =============================================================================


class OutputFormat(str, Enum):
    """Output format options for CLI commands."""

    TABLE = "table"
    JSON = "json"
    COMPACT = "compact"


# =============================================================================
# Helper Functions
# =============================================================================


def _get_manager(vkg_dir: Optional[Path] = None) -> PoolManager:
    """Get pool manager instance.

    Args:
        vkg_dir: Optional custom directory for pool storage

    Returns:
        PoolManager instance
    """
    if vkg_dir is None:
        vkg_dir = Path.cwd() / ".vrs" / "pools"
    return PoolManager(vkg_dir)


def _print_pool_summary(pool: Pool) -> None:
    """Print pool summary in human-readable format.

    Args:
        pool: Pool to display
    """
    typer.echo(f"\n{'='*60}")
    typer.echo(f"POOL: {pool.id}")
    typer.echo(f"{'='*60}")

    typer.echo(f"\n## Status")
    typer.echo(f"  Status:       {pool.status.value.upper()}")
    typer.echo(f"  Created:      {pool.created_at}")
    typer.echo(f"  Updated:      {pool.updated_at}")
    typer.echo(f"  Initiated by: {pool.initiated_by or 'N/A'}")

    typer.echo(f"\n## Scope")
    typer.echo(f"  Files:        {len(pool.scope.files)}")
    for f in pool.scope.files[:5]:  # Show first 5
        typer.echo(f"    - {f}")
    if len(pool.scope.files) > 5:
        typer.echo(f"    ... and {len(pool.scope.files) - 5} more")

    if pool.scope.contracts:
        typer.echo(f"  Contracts:    {len(pool.scope.contracts)}")
        for c in pool.scope.contracts[:5]:
            typer.echo(f"    - {c}")
        if len(pool.scope.contracts) > 5:
            typer.echo(f"    ... and {len(pool.scope.contracts) - 5} more")

    if pool.scope.focus_areas:
        typer.echo(f"  Focus Areas:  {', '.join(pool.scope.focus_areas)}")

    typer.echo(f"\n## Progress")
    typer.echo(f"  Beads:        {len(pool.bead_ids)}")
    typer.echo(f"  Verdicts:     {len(pool.verdicts)}")
    typer.echo(f"  Pending:      {len(pool.pending_beads)}")
    typer.echo(f"  Vulnerable:   {pool.vulnerable_count}")

    if pool.metadata:
        typer.echo(f"\n## Metadata")
        for key, value in pool.metadata.items():
            if key != "paused_from_status":  # Skip internal keys
                typer.echo(f"  {key}: {value}")

    typer.echo(f"\n{'='*60}\n")


def _status_color(status: PoolStatus) -> str:
    """Get display indicator for status.

    Args:
        status: Pool status

    Returns:
        Status indicator string
    """
    indicators = {
        PoolStatus.INTAKE: "[*]",
        PoolStatus.CONTEXT: "[.]",
        PoolStatus.BEADS: "[.]",
        PoolStatus.EXECUTE: "[>]",
        PoolStatus.VERIFY: "[?]",
        PoolStatus.INTEGRATE: "[+]",
        PoolStatus.COMPLETE: "[OK]",
        PoolStatus.FAILED: "[X]",
        PoolStatus.PAUSED: "[||]",
    }
    return indicators.get(status, "[ ]")


# =============================================================================
# CLI Commands
# =============================================================================


@orchestrate_app.command("list")
def list_pools(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (intake, context, beads, execute, verify, integrate, complete, failed, paused)",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """List all pools, optionally filtered by status.

    Examples:
        vkg orchestrate list
        vkg orchestrate list --status execute
        vkg orchestrate list --format json
    """
    manager = _get_manager(vkg_dir)
    pools = manager.storage.list_pools()

    # Apply status filter
    if status:
        try:
            status_enum = PoolStatus.from_string(status)
            pools = [p for p in pools if p.status == status_enum]
        except ValueError:
            typer.echo(f"Invalid status: {status}", err=True)
            typer.echo(
                "Valid: intake, context, beads, execute, verify, integrate, complete, failed, paused",
                err=True,
            )
            raise typer.Exit(code=1)

    if not pools:
        typer.echo("No pools found matching criteria.")
        return

    if fmt == OutputFormat.JSON:
        typer.echo(json.dumps([p.to_dict() for p in pools], indent=2, default=str))
        return

    if fmt == OutputFormat.COMPACT:
        for pool in pools:
            typer.echo(
                f"{pool.id} | {pool.status.value} | "
                f"{len(pool.bead_ids)} beads | {len(pool.verdicts)} verdicts"
            )
    else:  # table
        typer.echo(
            f"{'ID':<30} {'Status':<12} {'Beads':<8} {'Verdicts':<10} {'Created':<20}"
        )
        typer.echo("-" * 85)
        for pool in pools:
            created = str(pool.created_at)[:19] if pool.created_at else "N/A"
            ind = _status_color(pool.status)
            typer.echo(
                f"{pool.id:<30} {ind} {pool.status.value:<8} "
                f"{len(pool.bead_ids):<8} {len(pool.verdicts):<10} {created:<20}"
            )

    typer.echo(f"\nTotal: {len(pools)} pools")


@orchestrate_app.command("status")
def pool_status(
    pool_id: str = typer.Argument(..., help="Pool ID to show status for"),
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Show status of a specific pool.

    Examples:
        vkg orchestrate status pool-abc123
        vkg orchestrate status pool-abc123 --format json
    """
    manager = _get_manager(vkg_dir)
    pool = manager.get_pool(pool_id)

    if pool is None:
        typer.echo(f"Error: Pool {pool_id} not found", err=True)
        raise typer.Exit(code=1)

    if fmt == OutputFormat.JSON:
        typer.echo(json.dumps(pool.to_dict(), indent=2, default=str))
        return

    _print_pool_summary(pool)


@orchestrate_app.command("start")
def start_audit(
    path: str = typer.Argument(..., help="Path to Solidity project"),
    focus: Optional[List[str]] = typer.Option(
        None,
        "--focus",
        "-f",
        help="Focus areas for audit (repeatable: reentrancy, access-control, oracle, etc.)",
    ),
    pool_id: Optional[str] = typer.Option(
        None,
        "--pool-id",
        help="Custom pool ID (auto-generated if not provided)",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be created without executing",
    ),
) -> None:
    """Start a new audit and create a pool.

    Creates a new pool with the given scope and initiates the
    audit workflow. The pool will progress through phases:
    intake -> context -> beads -> execute -> verify -> integrate -> complete

    Examples:
        vkg orchestrate start ./contracts
        vkg orchestrate start ./contracts --focus reentrancy --focus oracle
        vkg orchestrate start ./contracts --pool-id my-audit-001
    """
    project_path = Path(path).resolve()

    if not project_path.exists():
        typer.echo(f"Error: Path not found: {project_path}", err=True)
        raise typer.Exit(code=1)

    # Collect Solidity files
    if project_path.is_file():
        files = [str(project_path)]
    else:
        sol_files = list(project_path.rglob("*.sol"))
        # Exclude test files and mocks (check relative path from project root)
        files = []
        for f in sol_files:
            try:
                relative_path = str(f.relative_to(project_path)).lower()
            except ValueError:
                relative_path = f.name.lower()
            if not any(
                x in relative_path
                for x in ["test", "mock", "node_modules", "lib/", "dependencies/"]
            ):
                files.append(str(f))

    if not files:
        typer.echo("Error: No Solidity files found in path", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Found {len(files)} Solidity files")

    if dry_run:
        typer.echo("\n[DRY RUN] Would create pool with:")
        typer.echo(f"  Files: {len(files)}")
        for f in files[:5]:
            typer.echo(f"    - {f}")
        if len(files) > 5:
            typer.echo(f"    ... and {len(files) - 5} more")
        if focus:
            typer.echo(f"  Focus areas: {', '.join(focus)}")
        return

    # Create scope
    scope = Scope(
        files=files,
        focus_areas=focus or [],
    )

    # Create pool
    manager = _get_manager(vkg_dir)
    pool = manager.create_pool(
        scope=scope,
        pool_id=pool_id,
        initiated_by="cli:orchestrate:start",
        metadata={"project_path": str(project_path)},
    )

    typer.echo(f"\nPool created: {pool.id}")
    typer.echo(f"Status: {pool.status.value}")
    typer.echo(f"Files in scope: {len(files)}")

    logger.info(
        "pool_created",
        pool_id=pool.id,
        file_count=len(files),
        focus_areas=focus,
    )

    typer.echo(f"\nNext: Run 'vkg orchestrate resume {pool.id}' to start processing")


@orchestrate_app.command("resume")
def resume_audit(
    pool_id: str = typer.Argument(..., help="Pool ID to resume"),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
    step: bool = typer.Option(
        False,
        "--step",
        help="Run single phase only (step mode)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """Resume an audit from checkpoint.

    Continues processing a pool from its current state.
    If the pool is paused, it will be resumed first.

    Examples:
        vkg orchestrate resume pool-abc123
        vkg orchestrate resume pool-abc123 --step  # Single phase only
    """
    manager = _get_manager(vkg_dir)
    pool = manager.get_pool(pool_id)

    if pool is None:
        typer.echo(f"Error: Pool {pool_id} not found", err=True)
        raise typer.Exit(code=1)

    if pool.status == PoolStatus.COMPLETE:
        typer.echo(f"Pool {pool_id} is already complete.")
        return

    if pool.status == PoolStatus.FAILED:
        typer.echo(f"Pool {pool_id} has failed. Use 'vkg orchestrate status' to check reason.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Resuming pool {pool_id} from {pool.status.value}...")

    # Create execution loop with default handlers
    config = LoopConfig(
        auto_advance=True,
        pause_on_human_flag=True,
        verbose=verbose,
    )
    loop = ExecutionLoop(manager, config=config)

    # Register default handlers
    handlers = create_default_handlers(manager)
    for action, handler in handlers.items():
        loop.register_handler(action, handler)

    # Run loop
    if step:
        result = loop.run_single_phase(pool_id)
    else:
        result = loop.resume(pool_id)

    # Report result
    if result.success:
        if result.checkpoint:
            typer.echo(f"\nCheckpoint reached: {result.message}")
            typer.echo("Human review required before continuing.")
            if result.artifacts.get("beads_for_review"):
                typer.echo(f"Beads to review: {', '.join(result.artifacts['beads_for_review'])}")
        else:
            typer.echo(f"\nPhase complete: {result.phase.value}")
            typer.echo(result.message)
    else:
        typer.echo(f"\nError: {result.message}", err=True)
        raise typer.Exit(code=1)

    logger.info(
        "pool_resumed",
        pool_id=pool_id,
        phase=result.phase.value,
        success=result.success,
        checkpoint=result.checkpoint,
    )


@orchestrate_app.command("beads")
def list_beads(
    pool_id: str = typer.Argument(..., help="Pool ID to list beads from"),
    pending: bool = typer.Option(
        False,
        "--pending",
        "-p",
        help="Show only pending beads (without verdicts)",
    ),
    human_flagged: bool = typer.Option(
        False,
        "--human-flagged",
        "-h",
        help="Show only human-flagged beads",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """List beads in a pool.

    Shows all beads associated with a pool, with optional filtering
    for pending (no verdict) or human-flagged beads.

    Examples:
        vkg orchestrate beads pool-abc123
        vkg orchestrate beads pool-abc123 --pending
        vkg orchestrate beads pool-abc123 --human-flagged
    """
    manager = _get_manager(vkg_dir)
    pool = manager.get_pool(pool_id)

    if pool is None:
        typer.echo(f"Error: Pool {pool_id} not found", err=True)
        raise typer.Exit(code=1)

    # Get bead IDs
    bead_ids = pool.bead_ids

    if pending:
        bead_ids = pool.pending_beads

    if not bead_ids:
        criteria = "pending " if pending else ""
        typer.echo(f"No {criteria}beads in pool {pool_id}.")
        return

    if fmt == OutputFormat.JSON:
        result = {
            "pool_id": pool_id,
            "total_beads": len(pool.bead_ids),
            "pending_beads": len(pool.pending_beads),
            "filtered_beads": bead_ids,
        }
        typer.echo(json.dumps(result, indent=2))
        return

    # Get verdicts for bead info
    verdicts_by_bead = {v.finding_id: v for v in pool.verdicts}

    if fmt == OutputFormat.COMPACT:
        for bead_id in bead_ids:
            verdict = verdicts_by_bead.get(bead_id)
            status = verdict.confidence.value if verdict else "pending"
            typer.echo(f"{bead_id} | {status}")
    else:  # table
        typer.echo(f"Beads in pool: {pool_id}")
        typer.echo("-" * 60)
        typer.echo(f"{'Bead ID':<30} {'Verdict':<12} {'Vulnerable':<10}")
        typer.echo("-" * 60)

        for bead_id in bead_ids:
            verdict = verdicts_by_bead.get(bead_id)
            if verdict:
                conf = verdict.confidence.value
                vuln = "Yes" if verdict.is_vulnerable else "No"
            else:
                conf = "pending"
                vuln = "N/A"
            typer.echo(f"{bead_id:<30} {conf:<12} {vuln:<10}")

    typer.echo(f"\nTotal: {len(bead_ids)} beads")
    if pending:
        typer.echo(f"(Showing pending only)")


@orchestrate_app.command("pause")
def pause_pool(
    pool_id: str = typer.Argument(..., help="Pool ID to pause"),
    reason: str = typer.Option(
        "manual_pause",
        "--reason",
        "-r",
        help="Reason for pausing",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Pause a pool for human review.

    Examples:
        vkg orchestrate pause pool-abc123
        vkg orchestrate pause pool-abc123 --reason "Need expert review"
    """
    manager = _get_manager(vkg_dir)

    if not manager.pause_pool(pool_id, reason):
        typer.echo(f"Error: Pool {pool_id} not found", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Pool {pool_id} paused: {reason}")


@orchestrate_app.command("delete")
def delete_pool(
    pool_id: str = typer.Argument(..., help="Pool ID to delete"),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Delete a pool.

    Examples:
        vkg orchestrate delete pool-abc123
        vkg orchestrate delete pool-abc123 --force
    """
    manager = _get_manager(vkg_dir)
    pool = manager.get_pool(pool_id)

    if pool is None:
        typer.echo(f"Error: Pool {pool_id} not found", err=True)
        raise typer.Exit(code=1)

    if not force:
        typer.echo(f"Pool: {pool_id}")
        typer.echo(f"Status: {pool.status.value}")
        typer.echo(f"Beads: {len(pool.bead_ids)}")
        typer.echo(f"Verdicts: {len(pool.verdicts)}")
        confirm = typer.confirm("Delete this pool? This cannot be undone.")
        if not confirm:
            typer.echo("Cancelled.")
            return

    if manager.delete_pool(pool_id):
        typer.echo(f"Pool {pool_id} deleted.")
    else:
        typer.echo(f"Error: Failed to delete pool {pool_id}", err=True)
        raise typer.Exit(code=1)


@orchestrate_app.command("summary")
def pool_summary(
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Show summary statistics for all pools.

    Examples:
        vkg orchestrate summary
    """
    manager = _get_manager(vkg_dir)
    summary = manager.storage.get_summary()

    typer.echo("\n## POOL SUMMARY")
    typer.echo(f"Total: {summary['total_pools']} pools")

    if summary["total_pools"] == 0:
        typer.echo("\nNo pools found. Run 'vkg orchestrate start <path>' to create a pool.")
        return

    typer.echo("\n### By Status")
    for status, count in summary["by_status"].items():
        typer.echo(f"  {status}: {count}")

    typer.echo("\n### Aggregate Metrics")
    typer.echo(f"  Total beads:      {summary['total_beads']}")
    typer.echo(f"  Total verdicts:   {summary['total_verdicts']}")
    typer.echo(f"  Vulnerable count: {summary['vulnerable_count']}")


@orchestrate_app.command("replay")
def replay_pool(
    pool_id: str = typer.Argument(..., help="Pool ID to replay"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Validate replayed state against current snapshot",
    ),
    seed: int = typer.Option(
        0,
        "--seed",
        "-s",
        help="Random seed for deterministic replay",
    ),
    diff: bool = typer.Option(
        False,
        "--diff",
        "-d",
        help="Print diff summary vs current pool",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Replay pool from event logs for deterministic reconstruction.

    Reconstructs pool state by replaying all recorded events. Useful for:
    - Auditing: Verify pool state matches recorded history
    - Debugging: Reconstruct state at any point in time
    - Regression testing: Compare replay output across versions

    Examples:
        alphaswarm orchestrate replay pool-abc123
        alphaswarm orchestrate replay pool-abc123 --strict
        alphaswarm orchestrate replay pool-abc123 --diff
        alphaswarm orchestrate replay pool-abc123 --seed 42 --strict
    """
    from alphaswarm_sol.orchestration.replay import ReplayEngine

    # Determine VRS root
    if vkg_dir:
        vrs_root = vkg_dir
    else:
        vrs_root = Path.cwd() / ".vrs"

    # Create replay engine
    engine = ReplayEngine(vrs_root=vrs_root)

    # Run replay
    typer.echo(f"Replaying pool {pool_id}...")
    result = engine.replay(pool_id, strict=strict, seed=seed)

    if not result.success:
        typer.echo(f"Error: Replay failed - {result.error}", err=True)
        raise typer.Exit(code=1)

    # JSON output
    if fmt == OutputFormat.JSON:
        output = {
            "pool_id": result.pool.id if result.pool else pool_id,
            "success": result.success,
            "event_count": result.event_count,
            "bead_count": result.bead_count,
            "verdict_count": result.verdict_count,
            "seed": result.seed,
            "mismatches": [
                {
                    "field": m.field,
                    "expected": m.expected,
                    "actual": m.actual,
                    "message": m.message,
                }
                for m in result.mismatches
            ] if result.mismatches else [],
        }
        typer.echo(json.dumps(output, indent=2, default=str))
        return

    # Print diff summary if requested
    if diff:
        summary = engine.get_diff_summary(result)
        typer.echo(summary)
        return

    # Table output (default)
    typer.echo("\n" + "=" * 60)
    typer.echo("REPLAY RESULT")
    typer.echo("=" * 60)

    if result.pool:
        typer.echo(f"Pool ID:      {result.pool.id}")
        typer.echo(f"Status:       {result.pool.status.value}")
    typer.echo(f"Events:       {result.event_count}")
    typer.echo(f"Beads:        {result.bead_count}")
    typer.echo(f"Verdicts:     {result.verdict_count}")
    typer.echo(f"Seed:         {result.seed}")

    if strict:
        typer.echo("\n## Validation (strict mode)")
        if result.mismatches:
            typer.echo(f"MISMATCHES: {len(result.mismatches)}")
            for m in result.mismatches:
                typer.echo(f"  - {m.message}")
        else:
            typer.echo("OK - Replay matches current snapshot")

    typer.echo("=" * 60 + "\n")

    logger.info(
        "pool_replayed",
        pool_id=pool_id,
        event_count=result.event_count,
        bead_count=result.bead_count,
        verdict_count=result.verdict_count,
        mismatch_count=len(result.mismatches),
        strict=strict,
    )


# =============================================================================
# Agent Run Command (SDK-08 Parity)
# =============================================================================


@dataclass
class OrchestrateOptions:
    """Options for agent orchestration command.

    Used by both CLI and SDK for consistent configuration.
    """

    sdk: str = "anthropic"  # "anthropic" or "openai"
    output_dir: Path = Path(".vrs/pools")
    timeout: int = 3600  # 1 hour default
    agents_attacker: int = 2
    agents_defender: int = 2
    agents_verifier: int = 1
    verbose: bool = False
    resume: bool = False
    headless: bool = False


def get_runtime(sdk: str, config=None):
    """Get agent runtime based on SDK choice.

    Ensures CLI and SDK use same runtime implementations.

    Args:
        sdk: SDK to use ("anthropic" or "openai")
        config: Optional RuntimeConfig

    Returns:
        AgentRuntime instance

    Raises:
        ValueError: If unknown SDK specified
    """
    from alphaswarm_sol.agents.runtime import (
        AnthropicRuntime,
        OpenAIAgentsRuntime,
        RuntimeConfig,
    )

    config = config or RuntimeConfig()

    if sdk == "anthropic":
        return AnthropicRuntime(config)
    elif sdk == "openai":
        return OpenAIAgentsRuntime(config)
    else:
        raise ValueError(f"Unknown SDK: {sdk}. Use 'anthropic' or 'openai'")


async def _run_agent_orchestration(
    target: Path,
    options: OrchestrateOptions,
):
    """Run full agent orchestration pipeline.

    Implements SDK-08: Same artifact outputs from CLI and SDK.

    Args:
        target: Path to contracts or existing pool
        options: Orchestration options

    Returns:
        CoordinatorReport with results
    """
    from alphaswarm_sol.agents.propulsion import (
        AgentCoordinator,
        CoordinatorConfig,
        CoordinatorReport,
        CoordinatorStatus,
    )
    from alphaswarm_sol.beads.storage import BeadStorage

    # 1. Setup output directories
    options.output_dir.mkdir(parents=True, exist_ok=True)
    pool_manager = PoolManager(options.output_dir)
    bead_storage = BeadStorage(options.output_dir / "beads")

    # 2. Check for resume
    if options.resume:
        # Load existing pool
        pools = list(options.output_dir.glob("*/pool.yaml"))
        if not pools:
            typer.echo("No existing pools found to resume", err=True)
            raise typer.Exit(1)

        # Load most recent
        pool = pool_manager.get_pool(pools[-1].parent.name)
        if pool is None:
            typer.echo(f"Failed to load pool from {pools[-1]}", err=True)
            raise typer.Exit(1)

        # Load beads
        beads = []
        for bid in pool.bead_ids:
            try:
                bead = bead_storage.load(bid)
                beads.append(bead)
            except Exception:
                pass  # Skip missing beads
        typer.echo(f"Resuming pool {pool.id} with {len(beads)} beads")
    else:
        # Create new pool from contracts
        typer.echo(f"Building knowledge graph from {target}...")
        pool, beads = await _create_pool_from_contracts(
            target, pool_manager, bead_storage, options
        )
        typer.echo(f"Created pool {pool.id} with {len(beads)} beads")

    # 3. Get runtime
    typer.echo(f"Using {options.sdk} SDK")
    runtime = get_runtime(options.sdk)

    # 4. Configure coordinator
    config = CoordinatorConfig(
        agents_per_role={
            "attacker": options.agents_attacker,
            "defender": options.agents_defender,
            "verifier": options.agents_verifier,
            "test_builder": 1,
        },
        enable_supervisor=True,
    )

    # 5. Run coordination
    typer.echo("Starting agent orchestration...")
    coordinator = AgentCoordinator(runtime, config)
    coordinator.setup_for_pool(pool, beads)

    if not options.headless:
        typer.echo("Press Ctrl+C to stop early")

    try:
        report = await coordinator.run(timeout=options.timeout)
    except KeyboardInterrupt:
        typer.echo("\nStopping orchestration...")
        coordinator.stop()
        report = CoordinatorReport(
            status=CoordinatorStatus.PAUSED,
            total_beads=len(beads),
            completed_beads=0,
            failed_beads=0,
            results_by_role={},
            duration_seconds=0,
            stuck_work=[],
        )

    # 6. Save results
    _save_agent_results(pool, report, options)

    return report


async def _create_pool_from_contracts(
    target: Path,
    pool_manager: PoolManager,
    bead_storage,
    options: OrchestrateOptions,
):
    """Create pool from contracts directory.

    Pipeline:
    1. Build VKG from contracts
    2. Run pattern detection
    3. Create beads from findings
    4. Create pool with bead IDs

    Args:
        target: Path to contracts
        pool_manager: Pool manager instance
        bead_storage: Bead storage instance
        options: Orchestration options

    Returns:
        Tuple of (pool, beads)
    """
    from alphaswarm_sol.kg.builder import VKGBuilder
    from alphaswarm_sol.queries.executor import QueryExecutor
    from alphaswarm_sol.beads.factory import BeadFactory

    # Build graph
    builder = VKGBuilder(target if target.is_dir() else target.parent)
    graph = builder.build(target)

    # Detect patterns
    executor = QueryExecutor()
    findings = executor.detect_all_patterns(graph)

    # Create beads
    factory = BeadFactory(graph)
    beads = []
    for finding in findings:
        bead = factory.create_from_finding(finding)
        bead_storage.save(bead)
        beads.append(bead)

    # Create pool
    scope = Scope(
        files=[str(f) for f in target.glob("**/*.sol") if target.is_dir()] or [str(target)],
        contracts=list(graph.contracts.keys()) if hasattr(graph, 'contracts') else [],
        focus_areas=[],
    )
    pool = pool_manager.create_pool(
        scope=scope,
        bead_ids=[b.id for b in beads],
        initiated_by="cli:orchestrate:agent-run",
    )

    return pool, beads


def _save_agent_results(pool: Pool, report, options: OrchestrateOptions) -> None:
    """Save orchestration results.

    Same artifact format whether called from CLI or SDK.
    Ensures SDK-08 parity.

    Args:
        pool: Pool that was processed
        report: CoordinatorReport with results
        options: Orchestration options
    """
    report_path = options.output_dir / pool.id / "agent-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    typer.echo(f"Report saved to {report_path}")


def _print_agent_report(report, options: OrchestrateOptions) -> None:
    """Print human-readable agent report.

    Args:
        report: CoordinatorReport
        options: Orchestration options
    """
    typer.echo("\n" + "=" * 60)
    typer.echo("AGENT ORCHESTRATION REPORT")
    typer.echo("=" * 60)

    typer.echo(f"Status: {report.status.value}")
    typer.echo(f"Duration: {report.duration_seconds:.1f}s")
    typer.echo(f"Total beads: {report.total_beads}")
    typer.echo(f"Completed: {report.completed_beads}")
    typer.echo(f"Failed: {report.failed_beads}")

    if report.results_by_role:
        typer.echo("\nResults by role:")
        for role, count in report.results_by_role.items():
            typer.echo(f"  {role}: {count}")

    if report.stuck_work:
        typer.echo(f"\nStuck work: {len(report.stuck_work)} items")
        if options.verbose:
            for item in report.stuck_work:
                typer.echo(f"  - {item}")

    typer.echo("=" * 60)


@orchestrate_app.command("agent-run")
def agent_run(
    target: Path = typer.Argument(
        ...,
        help="Path to contracts directory or existing pool",
        exists=True,
    ),
    output: Path = typer.Option(
        Path(".vrs/pools"),
        "--output",
        "-o",
        help="Output directory for pool artifacts",
    ),
    runtime: RuntimeChoice = typer.Option(
        RuntimeChoice.AUTO,
        "--runtime",
        "-r",
        help="Runtime to use (default: auto, which uses opencode for cost optimization)",
    ),
    sdk: Optional[str] = typer.Option(
        None,
        "--sdk",
        help="[DEPRECATED] Use --runtime instead. SDK to use: anthropic or openai",
        hidden=True,  # Hide from help, still works for backward compat
    ),
    show_rankings: bool = typer.Option(
        False,
        "--show-rankings",
        help="Display current model rankings before execution",
    ),
    reset_rankings: bool = typer.Option(
        False,
        "--reset-rankings",
        help="Clear existing rankings and start fresh",
    ),
    timeout: int = typer.Option(
        3600,
        "--timeout",
        "-t",
        help="Timeout in seconds (default 1 hour)",
    ),
    agents_attacker: int = typer.Option(
        2,
        "--attackers",
        help="Number of attacker agents",
    ),
    agents_defender: int = typer.Option(
        2,
        "--defenders",
        help="Number of defender agents",
    ),
    agents_verifier: int = typer.Option(
        1,
        "--verifiers",
        help="Number of verifier agents",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Resume existing pool from checkpoint",
    ),
    headless: bool = typer.Option(
        False,
        "--headless",
        help="Run without interactive prompts (for CI)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output",
    ),
) -> None:
    """Run multi-agent orchestration on contracts.

    Builds knowledge graph, detects patterns, creates beads,
    and runs attacker/defender/verifier agents to produce verdicts.

    Implements SDK-08: CLI and SDK produce same artifact outputs.

    Runtime Options:
        - opencode: Cost-optimized, uses OpenRouter free/cheap models (default)
        - claude-code: Claude Code CLI, subscription-based
        - codex: Codex CLI, subscription-based
        - api: Direct API access (expensive, use with caution)
        - auto: Smart selection, defaults to opencode

    Examples:
        alphaswarm orchestrate agent-run ./contracts/
        alphaswarm orchestrate agent-run ./contracts/ --runtime opencode
        alphaswarm orchestrate agent-run ./contracts/ --runtime claude-code
        alphaswarm orchestrate agent-run ./contracts/ --show-rankings
        alphaswarm orchestrate agent-run .vrs/pools/audit-001 --resume
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Handle reset rankings
    if reset_rankings:
        _reset_rankings()
        if not typer.confirm("Continue with execution?"):
            return

    # Handle show rankings
    if show_rankings:
        _display_rankings()

    # Determine SDK from runtime or legacy --sdk flag
    if sdk is not None:
        # Legacy --sdk flag used - emit deprecation warning
        typer.echo(
            typer.style("WARNING: ", fg=typer.colors.YELLOW, bold=True)
            + "--sdk is deprecated. Use --runtime instead."
        )
        effective_sdk = sdk
    else:
        # Use --runtime flag (new preferred method)
        runtime_type = _normalize_runtime(runtime)
        effective_sdk = runtime_type.value

    # Warn about API usage (expensive)
    if runtime == RuntimeChoice.API or effective_sdk in ("anthropic", "openai"):
        typer.echo(
            typer.style("WARNING: ", fg=typer.colors.YELLOW, bold=True)
            + "Using API-based runtimes is expensive. "
            "Consider using 'opencode' or 'claude-code' for cost savings."
        )
        if not headless:
            if not typer.confirm("Continue with API runtime?"):
                typer.echo("Aborted. Use --runtime opencode for cost-optimized execution.")
                raise typer.Exit(code=0)

    # Display runtime info
    typer.echo(f"Runtime: {effective_sdk}")
    available = get_available_runtimes()
    if effective_sdk not in available and effective_sdk != "auto":
        typer.echo(
            typer.style("WARNING: ", fg=typer.colors.YELLOW, bold=True)
            + f"Runtime '{effective_sdk}' may not be available. "
            f"Available runtimes: {', '.join(available)}"
        )

    options = OrchestrateOptions(
        sdk=effective_sdk,
        output_dir=output,
        timeout=timeout,
        agents_attacker=agents_attacker,
        agents_defender=agents_defender,
        agents_verifier=agents_verifier,
        verbose=verbose,
        resume=resume,
        headless=headless,
    )

    # Run async orchestration
    try:
        report = asyncio.run(_run_agent_orchestration(target, options))
        _print_agent_report(report, options)

        # Display cost summary at end
        if hasattr(report, 'total_cost_usd') and report.total_cost_usd > 0:
            typer.echo(f"\nTotal cost: ${report.total_cost_usd:.4f}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@orchestrate_app.command("rankings")
def rankings_cmd(
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Reset all rankings",
    ),
    task_type: Optional[str] = typer.Option(
        None,
        "--task-type",
        "-t",
        help="Filter by task type (verify, reasoning, code, etc.)",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
    vkg_dir: Optional[Path] = typer.Option(
        None,
        "--vkg-dir",
        help="Path to .vrs directory",
    ),
) -> None:
    """Display or manage model rankings.

    Shows current model rankings per task type, sorted by composite score.
    Rankings are updated automatically during agent execution.

    Examples:
        alphaswarm orchestrate rankings
        alphaswarm orchestrate rankings --task-type verify
        alphaswarm orchestrate rankings --format json
        alphaswarm orchestrate rankings --reset
    """
    from alphaswarm_sol.agents.ranking import RankingsStore

    # Determine store path
    store_path = None
    if vkg_dir:
        store_path = vkg_dir / "rankings" / "rankings.yaml"

    if reset:
        _reset_rankings(store_path)
        return

    store = RankingsStore(path=store_path)

    if not store.exists():
        typer.echo("No rankings found. Run benchmarks or agent-run to generate rankings.")
        return

    rankings_data = store.load()

    if not rankings_data:
        typer.echo("Rankings file exists but contains no data.")
        return

    # Filter by task type if specified
    if task_type:
        if task_type not in rankings_data:
            typer.echo(f"No rankings for task type: {task_type}")
            typer.echo(f"Available task types: {', '.join(rankings_data.keys())}")
            return
        rankings_data = {task_type: rankings_data[task_type]}

    # JSON output
    if fmt == OutputFormat.JSON:
        output = {}
        for tt, model_rankings in rankings_data.items():
            output[tt] = [r.to_dict() for r in model_rankings.values()]
        typer.echo(json.dumps(output, indent=2, default=str))
        return

    # Table output
    _display_rankings(store_path)


@orchestrate_app.command("runtimes")
def runtimes_cmd(
    fmt: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format",
        "-f",
        help="Output format",
    ),
) -> None:
    """List available runtimes.

    Shows which runtimes are available on the current system.

    Examples:
        alphaswarm orchestrate runtimes
        alphaswarm orchestrate runtimes --format json
    """
    from alphaswarm_sol.agents.runtime.factory import is_runtime_available

    runtimes = {
        "opencode": {
            "name": "OpenCode",
            "description": "Multi-model via OpenRouter (cost-optimized, default)",
            "cost": "Free-$3/1M tokens",
        },
        "claude_code": {
            "name": "Claude Code",
            "description": "Claude Code CLI (subscription-based)",
            "cost": "$20-100/month",
        },
        "codex": {
            "name": "Codex",
            "description": "Codex CLI (ChatGPT Plus)",
            "cost": "$20/month",
        },
        "anthropic": {
            "name": "Anthropic API",
            "description": "Direct Anthropic API (expensive)",
            "cost": "$3-75/1M tokens",
        },
        "openai": {
            "name": "OpenAI API",
            "description": "Direct OpenAI API (expensive)",
            "cost": "$2.5-40/1M tokens",
        },
    }

    available = get_available_runtimes()

    if fmt == OutputFormat.JSON:
        output = []
        for rt_id, info in runtimes.items():
            output.append({
                "id": rt_id,
                "name": info["name"],
                "description": info["description"],
                "cost": info["cost"],
                "available": rt_id in available,
            })
        typer.echo(json.dumps(output, indent=2))
        return

    # Table format
    typer.echo("\n" + "=" * 75)
    typer.echo("AVAILABLE RUNTIMES")
    typer.echo("=" * 75)
    typer.echo(f"{'Status':<10} {'ID':<15} {'Name':<15} {'Cost':<20}")
    typer.echo("-" * 75)

    for rt_id, info in runtimes.items():
        status = "[OK]" if rt_id in available else "[--]"
        typer.echo(f"{status:<10} {rt_id:<15} {info['name']:<15} {info['cost']:<20}")

    typer.echo("-" * 75)
    typer.echo(f"\nAvailable: {len(available)}/{len(runtimes)}")
    typer.echo("\nRecommended: opencode (cost-optimized, uses free/cheap models)")
    typer.echo("For critical analysis: claude-code (subscription required)")
    typer.echo("=" * 75 + "\n")


# Export for module
__all__ = [
    "orchestrate_app",
    "OrchestrateOptions",
    "get_runtime",
    "RuntimeChoice",
]
