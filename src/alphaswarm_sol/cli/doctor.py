"""
VKG Doctor Command

Diagnoses VKG installation and project state.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class Diagnosis:
    """Result of a diagnostic check."""

    category: str
    check: str
    status: str  # "ok", "warning", "error"
    message: str
    fix_command: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "check": self.check,
            "status": self.status,
            "message": self.message,
            "fix_command": self.fix_command,
        }


class Doctor:
    """Diagnoses VKG issues."""

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self.vkg_dir = self.project_dir / ".vrs"
        self.diagnoses: List[Diagnosis] = []

    def run_all(self) -> List[Diagnosis]:
        """Run all diagnostic checks."""
        self.diagnoses = []

        # Installation checks
        self._check_installation()

        # Project checks
        self._check_project()

        # State checks
        self._check_state()

        return self.diagnoses

    def _check_installation(self):
        """Check VKG installation."""
        from alphaswarm_sol.core.tiers import DEPENDENCIES, Tier

        # Check core dependencies
        for name, dep in DEPENDENCIES.items():
            if dep.tier == Tier.CORE:
                is_available = dep.is_available()
                self.diagnoses.append(
                    Diagnosis(
                        category="Installation",
                        check=f"{name}",
                        status="ok" if is_available else "error",
                        message=dep.get_version() if is_available else "Not installed",
                        fix_command=dep.install_hint if not is_available else None,
                    )
                )

    def _check_project(self):
        """Check project configuration."""
        # Check .vrs directory
        if self.vkg_dir.exists():
            self.diagnoses.append(
                Diagnosis(
                    category="Project",
                    check=".vrs directory",
                    status="ok",
                    message="Exists",
                )
            )
        else:
            self.diagnoses.append(
                Diagnosis(
                    category="Project",
                    check=".vrs directory",
                    status="warning",
                    message="Not found. Run 'vkg build-kg' first.",
                    fix_command="vkg build-kg .",
                )
            )
            return  # Can't check more without .vrs

        # Check for graph files (identity-based subdirs or legacy flat file)
        from alphaswarm_sol.kg.store import GraphStore

        graphs_dir = self.vkg_dir / "graphs"
        if graphs_dir.exists():
            store = GraphStore(graphs_dir)
            identities = store.list_identities()
            if identities:
                self.diagnoses.append(
                    Diagnosis(
                        category="Project",
                        check="graphs",
                        status="ok",
                        message=f"{len(identities)} per-contract graph(s) found",
                    )
                )
            else:
                # Check legacy flat files
                flat_toon = graphs_dir / "graph.toon"
                flat_json = graphs_dir / "graph.json"
                if flat_toon.exists() or flat_json.exists():
                    self.diagnoses.append(
                        Diagnosis(
                            category="Project",
                            check="graphs",
                            status="warning",
                            message="Legacy flat graph found. Rebuild with 'alphaswarm build-kg' for per-contract isolation.",
                            fix_command="alphaswarm build-kg . --force",
                        )
                    )
                else:
                    self.diagnoses.append(
                        Diagnosis(
                            category="Project",
                            check="graphs",
                            status="warning",
                            message="No graphs found",
                            fix_command="alphaswarm build-kg .",
                        )
                    )
        else:
            self.diagnoses.append(
                Diagnosis(
                    category="Project",
                    check="graphs",
                    status="warning",
                    message="No .vrs/graphs directory",
                    fix_command="alphaswarm build-kg .",
                )
            )

    def _check_state(self):
        """Check state consistency."""
        if not self.vkg_dir.exists():
            return

        # Check versions directory
        versions_dir = self.vkg_dir / "versions"
        if versions_dir.exists():
            version_count = len(list(versions_dir.glob("*.json")))
            self.diagnoses.append(
                Diagnosis(
                    category="State",
                    check="Version tracking",
                    status="ok" if version_count > 0 else "warning",
                    message=f"{version_count} versions tracked"
                    if version_count > 0
                    else "No versions tracked",
                    fix_command="vkg build-kg . --overwrite" if version_count == 0 else None,
                )
            )

        # Check current version file
        current_version_file = self.vkg_dir / "current_version.json"
        if current_version_file.exists():
            try:
                data = json.loads(current_version_file.read_text())
                version_id = data.get("current")
                if version_id:
                    self.diagnoses.append(
                        Diagnosis(
                            category="State",
                            check="Current version",
                            status="ok",
                            message=f"v{version_id[:8]}...",
                        )
                    )
                else:
                    self.diagnoses.append(
                        Diagnosis(
                            category="State",
                            check="Current version",
                            status="warning",
                            message="No current version set",
                        )
                    )
            except json.JSONDecodeError:
                self.diagnoses.append(
                    Diagnosis(
                        category="State",
                        check="Current version",
                        status="error",
                        message="Corrupted version file",
                        fix_command="vkg repair",
                    )
                )

        # Check findings freshness if findings exist
        findings_dir = self.vkg_dir / "findings"
        if findings_dir.exists():
            findings_count = len(list(findings_dir.glob("*.json")))
            self.diagnoses.append(
                Diagnosis(
                    category="State",
                    check="Findings",
                    status="ok" if findings_count > 0 else "info",
                    message=f"{findings_count} findings stored"
                    if findings_count > 0
                    else "No findings yet",
                )
            )

    def get_summary(self) -> dict:
        """Get summary of diagnoses."""
        errors = [d for d in self.diagnoses if d.status == "error"]
        warnings = [d for d in self.diagnoses if d.status == "warning"]
        ok = [d for d in self.diagnoses if d.status == "ok"]

        return {
            "total_checks": len(self.diagnoses),
            "errors": len(errors),
            "warnings": len(warnings),
            "ok": len(ok),
            "healthy": len(errors) == 0,
        }


doctor_app = typer.Typer(help="Diagnose VKG issues")


@doctor_app.callback(invoke_without_command=True)
def doctor(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all checks"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """
    Diagnose VKG installation and project issues.

    Checks:
    - Core dependencies (Python, Slither)
    - Enhancement tools (Aderyn, Foundry)
    - Project configuration (.vrs)
    - State consistency (versions, findings)

    Example:
        vkg doctor
        vkg doctor --verbose
        vkg doctor --json
    """
    project_dir = Path(project) if project else Path.cwd()
    doc = Doctor(project_dir)
    diagnoses = doc.run_all()

    if json_output:
        output = {
            "diagnoses": [d.to_dict() for d in diagnoses],
            "summary": doc.get_summary(),
        }
        typer.echo(json.dumps(output, indent=2))
        return

    # Rich output
    table = Table(title="VKG Doctor")
    table.add_column("Category", style="cyan")
    table.add_column("Check", style="white")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    for d in diagnoses:
        if not verbose and d.status == "ok":
            continue

        status_icon = {
            "ok": "[green]OK[/green]",
            "warning": "[yellow]![/yellow]",
            "error": "[red]X[/red]",
            "info": "[blue]i[/blue]",
        }.get(d.status, "?")

        table.add_row(d.category, d.check, status_icon, d.message)

    console.print(table)

    # Summary
    summary = doc.get_summary()
    console.print()
    if summary["errors"] > 0:
        console.print(f"[red]Found {summary['errors']} error(s)[/red]")
    if summary["warnings"] > 0:
        console.print(f"[yellow]Found {summary['warnings']} warning(s)[/yellow]")
    if summary["healthy"]:
        console.print("[green]VKG is healthy![/green]")

    # Show fixes
    fixes = [d for d in diagnoses if d.fix_command and d.status != "ok"]
    if fixes:
        console.print("\n[bold]Suggested fixes:[/bold]")
        for d in fixes:
            console.print(f"  {d.fix_command}")
