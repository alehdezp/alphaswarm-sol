"""
VKG Repair Command

Fixes common issues automatically.
"""

import json
import shutil
from pathlib import Path
from typing import Optional, List, Callable
from dataclasses import dataclass

import typer
from rich.console import Console

console = Console()


@dataclass
class RepairAction:
    """Describes a repair action to take."""

    issue: str
    action: str
    command: Callable[[], None]
    followup: Optional[str] = None

    def execute(self, dry_run: bool = False) -> bool:
        """Execute the repair action.

        Returns True if the action was executed (or would be in dry run).
        """
        console.print(f"\n[yellow]Issue:[/yellow] {self.issue}")
        console.print(f"[cyan]Action:[/cyan] {self.action}")

        if dry_run:
            console.print("[dim](dry run - no changes made)[/dim]")
            return False

        try:
            self.command()
            console.print("[green]Fixed![/green]")
            if self.followup:
                console.print(f"[dim]Next: {self.followup}[/dim]")
            return True
        except Exception as e:
            console.print(f"[red]Failed: {e}[/red]")
            return False


class Repairer:
    """Repairs VKG state issues."""

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self.vkg_dir = self.project_dir / ".vrs"
        self.repairs: List[RepairAction] = []

    def scan(self) -> List[RepairAction]:
        """Scan for issues and build repair list."""
        self.repairs = []

        if not self.vkg_dir.exists():
            return self.repairs

        # Check graph files
        self._check_graph_files()

        # Check cache
        self._check_cache()

        # Check versions
        self._check_versions()

        return self.repairs

    def _check_graph_files(self):
        """Check and plan graph file repairs."""
        from alphaswarm_sol.kg.store import GraphStore, CorruptGraphError

        graphs_dir = self.vkg_dir / "graphs"
        if not graphs_dir.exists():
            return

        store = GraphStore(graphs_dir)

        # Check identity-based subdirectories for corruption
        for identity in store.list_identities():
            hash_dir = graphs_dir / identity
            try:
                store._check_corrupt(hash_dir)
            except CorruptGraphError as e:
                self.repairs.append(
                    RepairAction(
                        issue=f"Corrupt graph in {identity}: {e}",
                        action=f"Remove .tmp artifacts in {identity}",
                        command=lambda d=hash_dir: [f.unlink() for f in d.glob("*.tmp")] or None,
                        followup=f"Run: alphaswarm build-kg . --force",
                    )
                )

        # Check legacy flat files
        for flat_name in ("graph.json", "graph.toon"):
            flat_path = graphs_dir / flat_name
            if flat_path.exists() and flat_name.endswith(".json"):
                try:
                    json.loads(flat_path.read_text())
                except json.JSONDecodeError:
                    self.repairs.append(
                        RepairAction(
                            issue=f"Corrupted {flat_name}",
                            action="Remove corrupted file",
                            command=lambda p=flat_path: p.unlink(),
                            followup="Run: alphaswarm build-kg .",
                        )
                    )

    def _check_cache(self):
        """Check and plan cache repairs."""
        cache_dir = self.vkg_dir / "cache"
        if cache_dir.exists():
            corrupted = False
            for cache_file in cache_dir.glob("*.json"):
                try:
                    json.loads(cache_file.read_text())
                except json.JSONDecodeError:
                    corrupted = True
                    break

            if corrupted:
                self.repairs.append(
                    RepairAction(
                        issue="Corrupted cache files",
                        action="Clear cache directory",
                        command=lambda d=cache_dir: shutil.rmtree(d),
                    )
                )

    def _check_versions(self):
        """Check and plan version repairs."""
        current_version_file = self.vkg_dir / "current_version.json"
        if current_version_file.exists():
            try:
                data = json.loads(current_version_file.read_text())
                version_id = data.get("current")
                if version_id:
                    version_file = self.vkg_dir / "versions" / f"{version_id}.json"
                    if not version_file.exists():
                        self.repairs.append(
                            RepairAction(
                                issue=f"Current version references missing file: {version_id}",
                                action="Remove stale version reference",
                                command=lambda f=current_version_file: f.unlink(),
                                followup="Run: vkg build-kg . --overwrite",
                            )
                        )
            except json.JSONDecodeError:
                self.repairs.append(
                    RepairAction(
                        issue="Corrupted current_version.json",
                        action="Remove corrupted version file",
                        command=lambda f=current_version_file: f.unlink(),
                    )
                )

    def execute_all(self, dry_run: bool = False) -> int:
        """Execute all repairs.

        Returns number of successful repairs.
        """
        success_count = 0
        for repair in self.repairs:
            if repair.execute(dry_run):
                success_count += 1
        return success_count


repair_app = typer.Typer(help="Repair VKG issues")


@repair_app.callback(invoke_without_command=True)
def repair(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """
    Automatically fix common VKG issues.

    Repairs:
    - Corrupted graph.json (removes and suggests rebuild)
    - Stale findings (refreshes version references)
    - Invalid cache entries (clears cache)

    Example:
        vkg repair
        vkg repair --dry-run
    """
    project_dir = Path(project) if project else Path.cwd()
    vkg_dir = project_dir / ".vrs"

    if not vkg_dir.exists():
        console.print("[yellow]No .vrs directory found. Nothing to repair.[/yellow]")
        return

    repairer = Repairer(project_dir)
    repairs = repairer.scan()

    if not repairs:
        console.print("[green]No issues found. VKG is healthy![/green]")
        return

    console.print(f"[yellow]Found {len(repairs)} issue(s) to repair[/yellow]")

    success_count = repairer.execute_all(dry_run)

    if not dry_run:
        console.print(f"\n[green]Fixed {success_count}/{len(repairs)} issues[/green]")


@repair_app.command("cache")
def repair_cache(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """Clear VKG cache."""
    project_dir = Path(project) if project else Path.cwd()
    cache_dir = project_dir / ".vrs" / "cache"

    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        console.print("[green]Cache cleared.[/green]")
    else:
        console.print("[dim]No cache found.[/dim]")


@repair_app.command("findings")
def repair_findings(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """Refresh stale findings."""
    console.print("[yellow]Not implemented yet. Run: vkg findings refresh[/yellow]")


@repair_app.command("versions")
def repair_versions(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """Clean up orphaned version files."""
    project_dir = Path(project) if project else Path.cwd()
    vkg_dir = project_dir / ".vrs"
    versions_dir = vkg_dir / "versions"

    if not versions_dir.exists():
        console.print("[dim]No versions directory found.[/dim]")
        return

    # Find orphaned versions (no current reference)
    current_file = vkg_dir / "current_version.json"
    current_id = None
    if current_file.exists():
        try:
            data = json.loads(current_file.read_text())
            current_id = data.get("current")
        except json.JSONDecodeError:
            pass

    orphaned = []
    for version_file in versions_dir.glob("*.json"):
        version_id = version_file.stem
        if version_id != current_id:
            orphaned.append(version_file)

    if not orphaned:
        console.print("[green]No orphaned versions found.[/green]")
        return

    console.print(f"Found {len(orphaned)} orphaned version(s)")
    for f in orphaned:
        f.unlink()
        console.print(f"  Removed: {f.name}")

    console.print("[green]Cleanup complete.[/green]")
