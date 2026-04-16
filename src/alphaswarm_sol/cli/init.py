"""VRS initialization command for target projects."""

import json
import shutil
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from alphaswarm_sol.skills import get_shipped_skills_path
from alphaswarm_sol.shipping import get_shipped_agents_path
from alphaswarm_sol.cli import bead

app = typer.Typer(help="AlphaSwarm VRS commands")
console = Console()

# Add bead subcommand
app.add_typer(bead.app, name="bead")

VRS_VERSION = "0.5.0"


@app.command("init")
def init_alphaswarm(
    target: Path = typer.Argument(
        Path("."),
        help="Target project directory",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite existing installation",
    ),
    skip_health_check: bool = typer.Option(
        False,
        "--skip-health-check",
        help="Skip automatic health check after installation",
    ),
) -> None:
    """Initialize VRS in a target project.

    Copies VRS skills to .claude/vrs/ and creates .beads/ directory.
    Does NOT modify existing .claude/ files or settings.

    Example:
        alphaswarm init ./my-defi-project
        alphaswarm init . --force
    """
    vrs_dir = target / ".claude" / "vrs"
    beads_dir = target / ".beads"

    # Check existing installation
    if vrs_dir.exists() and not force:
        console.print(
            "[yellow]VRS already installed in this project.[/yellow]"
        )
        console.print(
            "[dim]Use --force to reinstall, or run `alphaswarm health-check`[/dim]"
        )
        raise typer.Exit(1)

    # Create directories
    console.print(f"[blue]Initializing VRS in {target.absolute()}[/blue]")

    vrs_dir.mkdir(parents=True, exist_ok=True)
    beads_dir.mkdir(parents=True, exist_ok=True)

    # Copy skills from package
    skills_source = get_shipped_skills_path()
    skills_copied = 0

    for skill_file in skills_source.glob("*.md"):
        if skill_file.name == "README.md":
            continue  # Skip README in root
        shutil.copy(skill_file, vrs_dir / skill_file.name)
        skills_copied += 1
        console.print(f"  [green]+[/green] {skill_file.name}")

    # Copy agents subdirectory if exists
    agents_source = get_shipped_agents_path()
    if agents_source.exists():
        agents_dest = vrs_dir / "agents"
        agents_dest.mkdir(exist_ok=True)
        for agent_file in agents_source.glob("*.md"):
            shutil.copy(agent_file, agents_dest / agent_file.name)
            skills_copied += 1
            console.print(f"  [green]+[/green] agents/{agent_file.name}")

    # Copy README to vrs directory
    readme_source = skills_source / "README.md"
    if readme_source.exists():
        shutil.copy(readme_source, vrs_dir / "README.md")
        console.print(f"  [green]+[/green] README.md")

    # Create beads index
    beads_index = beads_dir / "index.jsonl"
    if not beads_index.exists():
        beads_index.touch()
        console.print("  [green]+[/green] .beads/index.jsonl")

    # Create cache directory with gitignore
    cache_dir = vrs_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    gitignore = cache_dir / ".gitignore"
    gitignore.write_text("*\n!.gitignore\n")
    console.print("  [green]+[/green] cache/.gitignore")

    # Record installation metadata
    meta = vrs_dir / ".vrs-meta.json"
    meta.write_text(json.dumps({
        "version": VRS_VERSION,
        "installed_at": datetime.now().isoformat(),
        "skills_count": skills_copied,
    }, indent=2))

    console.print(f"\n[green]VRS installed successfully![/green]")
    console.print(f"  Skills: {skills_copied} files in .claude/vrs/")
    console.print(f"  Beads:  .beads/ directory ready")

    # Run health check unless skipped
    if not skip_health_check:
        console.print("\n[blue]Running health check...[/blue]")
        run_health_check(target)


def run_health_check(target: Path) -> None:
    """Run health check on VRS installation.

    Args:
        target: Project directory to check
    """
    vrs_dir = target / ".claude" / "vrs"
    beads_dir = target / ".beads"

    issues = []

    # Check .claude/vrs/ exists
    if not vrs_dir.exists():
        issues.append(".claude/vrs/ directory missing")

    # Check .beads/ exists
    if not beads_dir.exists():
        issues.append(".beads/ directory missing")

    # Check beads index exists
    beads_index = beads_dir / "index.jsonl"
    if not beads_index.exists():
        issues.append(".beads/index.jsonl missing")

    # Check for skills
    if vrs_dir.exists():
        skill_files = list(vrs_dir.glob("*.md"))
        if len(skill_files) < 5:
            issues.append(f"Only {len(skill_files)} skill files found (expected at least 5)")

    # Check for metadata
    meta_file = vrs_dir / ".vrs-meta.json"
    if not meta_file.exists():
        issues.append("Installation metadata missing")
    else:
        try:
            meta = json.loads(meta_file.read_text())
            console.print(f"  Version: {meta.get('version', 'unknown')}")
            console.print(f"  Installed: {meta.get('installed_at', 'unknown')}")
        except Exception as e:
            issues.append(f"Metadata corrupted: {e}")

    if issues:
        console.print("\n[yellow]Issues found:[/yellow]")
        for issue in issues:
            console.print(f"  [red]✗[/red] {issue}")
        raise typer.Exit(1)
    else:
        console.print("\n[green]✓ Installation healthy[/green]")


@app.command("health-check")
def health_check_command(
    target: Path = typer.Argument(
        Path("."),
        help="Target project directory",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
) -> None:
    """Run health check on VRS installation.

    Verifies that VRS is properly installed and configured.

    Example:
        alphaswarm health-check
        alphaswarm health-check ./my-defi-project
    """
    console.print(f"[blue]Running VRS health check for {target.absolute()}[/blue]\n")
    run_health_check(target)
