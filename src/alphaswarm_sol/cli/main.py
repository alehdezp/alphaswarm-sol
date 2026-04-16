"""CLI entrypoints for AlphaSwarm.sol."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import structlog
import typer

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph
    from alphaswarm_sol.labels import LabelOverlay

from alphaswarm_sol.cli.batch import batch_app
from alphaswarm_sol.cli.beads import beads_app
from alphaswarm_sol.cli.context import context_app
from alphaswarm_sol.cli.dashboard_cmd import ops_app
from alphaswarm_sol.cli.doctor import doctor_app
from alphaswarm_sol.cli.eval_commands import eval_app
from alphaswarm_sol.cli.findings import findings_app
from alphaswarm_sol.cli.health import app as health_app
from alphaswarm_sol.cli.learn import learn_app
from alphaswarm_sol.cli.metrics import metrics_app
from alphaswarm_sol.cli.novel import novel_app
from alphaswarm_sol.cli.repair import repair_app
from alphaswarm_sol.cli.tools import tools_app
from alphaswarm_sol.cli.vulndocs import vulndocs_app
from alphaswarm_sol.cli.orchestrate import orchestrate_app
from alphaswarm_sol.config import configure_logging, load_settings
from alphaswarm_sol.enterprise.reports import Finding, Severity
from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.kg.store import GraphStore
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.intent import parse_intent
from alphaswarm_sol.queries.planner import QueryPlanner
from alphaswarm_sol.queries.report import build_lens_report
from alphaswarm_sol.queries.schema_snapshot import build_schema_snapshot

app = typer.Typer(help="AlphaSwarm.sol: AI-native smart contract security analysis")

# Add subcommand groups
app.add_typer(batch_app, name="batch")
app.add_typer(beads_app, name="beads")
app.add_typer(context_app, name="context")
app.add_typer(doctor_app, name="doctor")
app.add_typer(findings_app, name="findings")
app.add_typer(health_app, name="health-check")
app.add_typer(learn_app, name="learn")
app.add_typer(metrics_app, name="metrics")
app.add_typer(novel_app, name="novel")
app.add_typer(ops_app, name="ops")
app.add_typer(repair_app, name="repair")
app.add_typer(tools_app, name="tools")
app.add_typer(vulndocs_app, name="vulndocs")
app.add_typer(eval_app, name="eval")
app.add_typer(orchestrate_app, name="orchestrate")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from alphaswarm_sol import __version__
        typer.echo(f"AlphaSwarm.sol {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit."),
    log_level: str | None = typer.Option(None, "--log-level", help="Override log level."),
) -> None:
    """Initialize logging and settings for commands."""

    settings = load_settings()
    configure_logging(log_level or settings.log_level)
    ctx.obj = {"settings": settings}


def _handle_error(exc: Exception) -> None:
    logger = structlog.get_logger()
    logger.error("command_failed", error=str(exc))
    raise typer.Exit(code=1) from exc


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to project root."),
    opencode: bool = typer.Option(
        False,
        "--opencode",
        help="Generate opencode.json for OpenCode integration.",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing config files."
    ),
    skip_skills: bool = typer.Option(
        False, "--skip-skills", help="Skip copying Claude Code skills."
    ),
) -> None:
    """Initialize VKG configuration for a project.

    Creates the .vrs directory, copies Claude Code skills to .claude/skills/vrs/,
    and optionally generates integration configs for external tools.

    Examples:

        # Initialize VKG in current directory
        alphaswarm init

        # Initialize with OpenCode integration
        alphaswarm init --opencode

        # Initialize in a specific directory
        alphaswarm init /path/to/project
    """
    import shutil

    try:
        logger = structlog.get_logger()
        project_path = Path(path).resolve()

        if not project_path.exists():
            typer.echo(f"Error: Path not found: {project_path}", err=True)
            raise typer.Exit(code=1)

        # Create .vrs directory
        vkg_dir = project_path / ".vrs"
        vkg_dir.mkdir(parents=True, exist_ok=True)
        typer.echo(f"Created: {vkg_dir}")

        # Create graphs subdirectory
        graphs_dir = vkg_dir / "graphs"
        graphs_dir.mkdir(exist_ok=True)
        typer.echo(f"Created: {graphs_dir}")

        # Copy Claude Code skills unless skipped
        if not skip_skills:
            from alphaswarm_sol.skills import get_shipped_skills_path
            from alphaswarm_sol.skills.registry import list_registry

            # Only ship production skills (not validation/development/pattern-development)
            PRODUCTION_CATEGORIES = {
                "orchestration",
                "investigation",
                "tool-integration",
            }

            # Get list of production skill IDs from registry
            registry = list_registry()
            production_skills = {
                f"{entry['id']}.md"
                for entry in registry
                if entry.get("category") in PRODUCTION_CATEGORIES
                and entry.get("location", {}).get("shipped")
            }

            skills_source = get_shipped_skills_path()
            skills_dest = project_path / ".claude" / "skills"
            skills_dest.mkdir(parents=True, exist_ok=True)

            # Claude Code skills must be folders with SKILL.md inside
            # Structure: .claude/skills/<skill-name>/SKILL.md
            skills_copied = 0
            for skill_file in skills_source.glob("*.md"):
                if skill_file.name == "README.md":
                    continue
                # Only copy production skills
                if skill_file.name not in production_skills:
                    continue
                # Create folder with vrs- prefix (e.g., audit.md -> vrs-audit/SKILL.md)
                skill_name = f"vrs-{skill_file.stem}"  # e.g., "vrs-audit"
                skill_folder = skills_dest / skill_name
                skill_folder.mkdir(exist_ok=True)
                shutil.copy(skill_file, skill_folder / "SKILL.md")
                skills_copied += 1

            # Copy only production agents (core multi-agent system)
            # Agents also need folder structure: .claude/agents/<agent-name>/AGENT.md
            PRODUCTION_AGENTS = {
                "vrs-attacker.md",
                "vrs-defender.md",
                "vrs-verifier.md",
                "vrs-secure-reviewer.md",
                "vrs-integrator.md",
                "vrs-supervisor.md",
            }
            from alphaswarm_sol.shipping import get_shipped_agents_path
            agents_source = get_shipped_agents_path()
            agents_dest = project_path / ".claude" / "agents"
            if agents_source.exists():
                agents_dest.mkdir(exist_ok=True)
                for agent_file in agents_source.glob("*.md"):
                    if agent_file.name not in PRODUCTION_AGENTS:
                        continue
                    # Create folder structure: .claude/agents/<name>/AGENT.md
                    agent_name = agent_file.stem  # Already has vrs- prefix
                    agent_folder = agents_dest / agent_name
                    agent_folder.mkdir(exist_ok=True)
                    shutil.copy(agent_file, agent_folder / "AGENT.md")
                    skills_copied += 1

            typer.echo(f"Installed {skills_copied} skills/agents to: {project_path / '.claude'}")

        # Generate OpenCode configuration if requested
        if opencode:
            from alphaswarm_sol.templates.opencode import write_opencode_config

            try:
                output_path = write_opencode_config(
                    project_path,
                    overwrite=overwrite,
                )
                typer.echo(f"Created: {output_path}")
                typer.echo("")
                typer.echo("OpenCode integration enabled!")
                typer.echo("VKG tools will be available in OpenCode:")
                typer.echo("  - vkg_build_kg: Build knowledge graph")
                typer.echo("  - vkg_analyze: Run vulnerability analysis")
                typer.echo("  - vkg_query: Query the knowledge graph")
                typer.echo("  - vkg_findings_*: Manage findings workflow")
                typer.echo("  - vkg_report: Generate audit reports")
                typer.echo("")
                typer.echo("Start OpenCode with: opencode")
            except FileExistsError:
                typer.echo(
                    "opencode.json already exists. Use --overwrite to replace.",
                    err=True,
                )
                raise typer.Exit(code=1)

        logger.info(
            "init_complete",
            project_path=str(project_path),
            opencode=opencode,
        )
        typer.echo("")
        typer.echo("VKG initialized successfully!")
        typer.echo(f"Next: Run 'uv run alphaswarm build-kg {path}' to build the knowledge graph.")

    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover - defensive for CLI
        _handle_error(exc)


@app.command("build-kg")
def build_kg(
    path: str,
    out: str | None = typer.Option(None, "--out", help="Output directory for VKG artifacts."),
    format: str = typer.Option("toon", "--format", "-f", help="Output format: toon (default, LLM-optimized) or json (legacy)."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing graph file."),
    force: bool = typer.Option(False, "--force", help="Force rebuild even if graph exists for this contract."),
    check_fresh: bool = typer.Option(False, "--check-fresh", help="Check staleness and exit (0=fresh, 42=stale)."),
    with_labels: bool = typer.Option(False, "--with-labels", help="Run LLM semantic labeling after building graph."),
    skip_labels: bool = typer.Option(False, "--skip-labels", help="Skip labeling even if previously enabled."),
    label_output: str | None = typer.Option(None, "--label-output", help="Path to export labels (JSON or YAML)."),
    label_format: str = typer.Option("json", "--label-format", help="Label export format (json/yaml)."),
) -> None:
    """Build a dynamic VKG for a Solidity file or folder."""
    try:
        from alphaswarm_sol.kg.graph_hash import compute_source_hash
        from alphaswarm_sol.kg.identity import contract_identity, _resolve_project_root

        # Validate format
        if format not in ("toon", "json"):
            typer.echo(f"Error: --format must be 'toon' or 'json', got '{format}'", err=True)
            raise typer.Exit(code=1)

        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {target}")
        project_root = target if target.is_dir() else target.parent
        output_dir = Path(out) if out else project_root / ".vrs" / "graphs"

        # Compute contract identity for per-contract isolation
        if target.is_file():
            input_paths = [target]
        else:
            input_paths = sorted(target.rglob("*.sol"))
        identity = contract_identity(input_paths) if input_paths else None

        store = GraphStore(output_dir)

        # --check-fresh: compare source hash to stored meta.json
        if check_fresh and identity:
            source_hash = compute_source_hash(input_paths)
            stem = target.stem if target.is_file() else target.name
            if store.check_fresh(identity, source_hash):
                typer.echo(f"[graph-cache] skipped: {stem} (hash match)", err=True)
                raise typer.Exit(code=0)
            else:
                typer.echo(f"[WARNING] cache mismatch: {stem} has changed on disk", err=True)
                raise typer.Exit(code=42)

        builder = VKGBuilder(project_root)
        graph = builder.build(target)

        # Build meta.json sidecar data
        resolved_root, root_type = _resolve_project_root(input_paths)
        source_hash = compute_source_hash(input_paths) if input_paths else ""
        stem = target.stem if target.is_file() else target.name
        source_contract = stem

        meta = {
            "schema_version": 1,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "graph_hash": source_hash,
            "contract_paths": [str(p) for p in input_paths],
            "stem": stem,
            "source_contract": source_contract,
            "slither_version": graph.metadata.get("slither_version") or "unknown",
            "project_root_type": root_type,
        }

        effective_force = force or overwrite
        saved_path = store.save(
            graph,
            identity=identity,
            meta=meta if identity else None,
            format=format,  # type: ignore[arg-type]
            force=effective_force,
        )

        structlog.get_logger().info(
            "build_kg_complete",
            output=str(saved_path),
            identity=identity,
            nodes=len(graph.nodes),
            edges=len(graph.edges),
            solc_version=graph.metadata.get("solc_version_selected"),
        )
        typer.echo(f"VKG saved to: {saved_path} (format: {format})")
        if identity:
            typer.echo(f"identity: {identity}")
        if graph.metadata.get("solc_version_selected"):
            typer.echo(f"solc selected: {graph.metadata['solc_version_selected']}")

        # Run semantic labeling if requested
        if with_labels and not skip_labels:
            typer.echo("")
            typer.echo("Running semantic labeling...")
            label_path = Path(label_output) if label_output else None
            overlay = _run_labeling(graph, label_path, label_format)
            if overlay:
                label_count = _count_labels(overlay)
                typer.echo(f"Applied {label_count} labels to {len(overlay.labels)} functions")

    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover - defensive for CLI
        _handle_error(exc)


async def _run_labeling_async(
    graph: "KnowledgeGraph",
    output_path: Optional[Path],
    format: str,
) -> Optional["LabelOverlay"]:
    """Run semantic labeling on graph asynchronously.

    Args:
        graph: Knowledge graph to label
        output_path: Optional path to export labels
        format: Export format (json/yaml)

    Returns:
        LabelOverlay with applied labels, or None on failure
    """
    from alphaswarm_sol.labels import LLMLabeler, LabelingConfig, LabelOverlay
    from alphaswarm_sol.llm.providers.anthropic import AnthropicProvider
    from alphaswarm_sol.llm.config import LLMConfig

    try:
        # Create provider
        config = LLMConfig()
        provider = AnthropicProvider(config)

        # Configure labeler
        labeling_config = LabelingConfig(
            max_tokens_per_call=6000,
            max_functions_per_batch=5,
        )

        labeler = LLMLabeler(provider, labeling_config)

        # Get function node IDs
        function_ids = [
            node_id for node_id, node in graph.nodes.items()
            if node.type == "function"
        ]

        typer.echo(f"Labeling {len(function_ids)} functions...")

        # Run labeling
        result = await labeler.label_functions(graph, function_ids)

        typer.echo(f"  Tokens used: {result.total_tokens:,}")
        typer.echo(f"  Cost: ${result.total_cost_usd:.4f}")
        typer.echo(f"  Labels applied: {result.labels_applied}")

        # Get overlay
        overlay = labeler.get_overlay()

        # Export if path provided
        if output_path:
            if format.lower() == "yaml":
                overlay.export_yaml(output_path)
            else:
                overlay.export_json(output_path)
            typer.echo(f"Labels exported to: {output_path}")

        return overlay

    except Exception as e:
        typer.echo(f"Labeling failed: {e}", err=True)
        return None


def _run_labeling(
    graph: "KnowledgeGraph",
    output_path: Optional[Path],
    format: str,
) -> Optional["LabelOverlay"]:
    """Sync wrapper for async labeling.

    Args:
        graph: Knowledge graph to label
        output_path: Optional path to export labels
        format: Export format (json/yaml)

    Returns:
        LabelOverlay with applied labels, or None on failure
    """
    return asyncio.run(_run_labeling_async(graph, output_path, format))


def _count_labels(overlay: "LabelOverlay") -> int:
    """Count total labels in overlay.

    Args:
        overlay: Label overlay to count

    Returns:
        Total number of labels across all functions
    """
    return sum(len(ls.labels) for ls in overlay.labels.values())


@app.command()
def label(
    graph: Optional[str] = typer.Option(None, "--graph", help="Graph path or contract stem (e.g., 'Token')."),
    output: str = typer.Option("labels.json", "--output", "-o", help="Output path for labels"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json/yaml)"),
    functions: Optional[List[str]] = typer.Option(None, "--function", "-fn", help="Specific functions to label (can be repeated)"),
) -> None:
    """Run semantic labeling on an existing knowledge graph.

    Applies LLM-driven semantic labels to functions in a built VKG.
    Labels categorize function behavior (access control, value handling, etc.)

    Examples:
        # Label all functions (single graph auto-selected)
        uv run alphaswarm label

        # Label specific contract's graph
        uv run alphaswarm label --graph Token

        # Label specific functions
        uv run alphaswarm label --graph Token -fn "Vault.withdraw" -fn "Vault.deposit"

        # Export as YAML
        uv run alphaswarm label --graph Token -o labels.yaml -f yaml
    """
    try:
        from alphaswarm_sol.labels import LLMLabeler, LabelingConfig, LabelOverlay
        from alphaswarm_sol.llm.providers.anthropic import AnthropicProvider
        from alphaswarm_sol.llm.config import LLMConfig
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        # Load graph via shared resolution (error-when-ambiguous, --graph flag)
        graph_obj, _graph_info = resolve_and_load_graph(graph)

        typer.echo(f"Loaded graph: {len(graph_obj.nodes)} nodes, {len(graph_obj.edges)} edges")

        # Run labeling
        output_path = Path(output)
        overlay = _run_labeling(graph_obj, output_path, format)

        if overlay:
            typer.echo(f"Labeling complete: {_count_labels(overlay)} labels applied")
        else:
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


@app.command("label-export")
def label_export(
    input_path: str = typer.Argument(..., help="Path to label overlay (json/yaml)"),
    output_path: str = typer.Argument(..., help="Output path"),
    format: str = typer.Option("json", "--format", "-f", help="Output format (json/yaml)"),
) -> None:
    """Export labels to different format.

    Convert label overlays between JSON and YAML formats.

    Examples:
        # Convert JSON to YAML
        uv run alphaswarm label-export labels.json labels.yaml -f yaml

        # Convert YAML to JSON
        uv run alphaswarm label-export labels.yaml labels.json -f json
    """
    try:
        from alphaswarm_sol.labels import LabelOverlay

        in_path = Path(input_path)
        out_path = Path(output_path)

        # Load overlay
        if in_path.suffix.lower() in (".yaml", ".yml"):
            overlay = LabelOverlay.from_yaml(in_path)
        else:
            overlay = LabelOverlay.from_json(in_path)

        typer.echo(f"Loaded {_count_labels(overlay)} labels from {len(overlay.labels)} functions")

        # Export
        if format.lower() == "yaml":
            overlay.export_yaml(out_path)
        else:
            overlay.export_json(out_path)

        typer.echo(f"Exported to: {out_path}")

    except Exception as exc:
        _handle_error(exc)


@app.command("label-info")
def label_info(
    input_path: str = typer.Argument(..., help="Path to label overlay (json/yaml)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed label breakdown"),
) -> None:
    """Show information about a label overlay.

    Display statistics about labels in an overlay file.

    Examples:
        uv run alphaswarm label-info labels.json
        uv run alphaswarm label-info labels.yaml -v
    """
    try:
        from alphaswarm_sol.labels import LabelOverlay, LabelValidator

        in_path = Path(input_path)

        # Load overlay
        if in_path.suffix.lower() in (".yaml", ".yml"):
            overlay = LabelOverlay.from_yaml(in_path)
        else:
            overlay = LabelOverlay.from_json(in_path)

        # Calculate statistics
        total_labels = _count_labels(overlay)
        functions_count = len(overlay.labels)

        # Confidence distribution
        high_count = 0
        medium_count = 0
        low_count = 0
        categories: dict = {}

        for label_set in overlay.labels.values():
            for label in label_set.labels:
                if label.confidence.value == "high":
                    high_count += 1
                elif label.confidence.value == "medium":
                    medium_count += 1
                else:
                    low_count += 1

                cat = label.category
                categories[cat] = categories.get(cat, 0) + 1

        typer.echo("Label Overlay Statistics")
        typer.echo("=" * 40)
        typer.echo(f"Functions labeled: {functions_count}")
        typer.echo(f"Total labels: {total_labels}")
        typer.echo(f"  High confidence: {high_count}")
        typer.echo(f"  Medium confidence: {medium_count}")
        typer.echo(f"  Low confidence: {low_count}")
        typer.echo("")
        typer.echo("Labels by category:")
        for cat, count in sorted(categories.items()):
            typer.echo(f"  {cat}: {count}")

        if verbose:
            typer.echo("")
            typer.echo("Labels per function:")
            for func_id, label_set in overlay.labels.items():
                labels_str = ", ".join(l.label_id for l in label_set.labels)
                typer.echo(f"  {func_id}: {labels_str}")

    except Exception as exc:
        _handle_error(exc)


@app.command()
def query(
    query_text: str,
    graph: str | None = typer.Option(None, "--graph", help="Graph path or contract stem (e.g., 'Token')."),
    no_evidence: bool = typer.Option(False, "--no-evidence", help="Omit evidence from results."),
    compact: bool = typer.Option(False, "--compact", help="Return compact node/edge output."),
    pattern_dir: str | None = typer.Option(None, "--pattern-dir", help="Directory with pattern packs."),
    explain: bool = typer.Option(False, "--explain", help="Include match explanations."),
    show_intent: bool = typer.Option(False, "--show-intent", help="Print parsed intent and exit."),
    vql2: bool = typer.Option(False, "--vql2", help="Use VQL 2.0 parser (experimental)."),
    validate_only: bool = typer.Option(False, "--validate", help="Validate query without executing."),
) -> None:
    """Run a VKG query using safe NL or VQL 2.0.

    Uses --graph flag for explicit graph targeting. When multiple graphs exist,
    --graph is required (error-when-ambiguous). Structured output on stdout
    with # result: header, errors on stderr, exit codes 0/1/2.
    """
    import sys as _sys
    from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
    from alphaswarm_sol.queries.errors import PatternLoadError

    try:
        graph_obj, _graph_info = resolve_and_load_graph(graph)
    except typer.Exit:
        raise
    except Exception as exc:
        print(f"Error: could not load graph: {exc}", file=_sys.stderr)
        raise typer.Exit(code=2) from exc

    try:
        graph_nodes_count = len(graph_obj.nodes)

        # VQL 2.0 path (new experimental parser)
        if vql2 or query_text.strip().upper().startswith(("MATCH ", "FLOW FROM", "WITH ")):
            from alphaswarm_sol.vql2 import parse_vql2
            from alphaswarm_sol.vql2.executor import VQL2Executor
            from alphaswarm_sol.vql2.guidance import LLMGuidanceSystem

            # Validation only mode
            if validate_only:
                guidance = LLMGuidanceSystem()
                validation_result = guidance.validate({"query": query_text})
                print(json.dumps(validation_result, indent=2), file=_sys.stdout)
                return

            try:
                # Parse VQL 2.0
                ast = parse_vql2(query_text)

                if show_intent:
                    from alphaswarm_sol.vql2.ast import ASTPrinter
                    printer = ASTPrinter()
                    print("VQL 2.0 AST:", file=_sys.stderr)
                    print(printer.print_node(ast), file=_sys.stderr)
                    return

                # Execute
                vql2_executor = VQL2Executor(
                    graph_obj,
                    pattern_dir=Path(pattern_dir) if pattern_dir else None,
                    compact_mode=compact,
                    include_evidence=not no_evidence,
                    explain_mode=explain,
                )
                result = vql2_executor.execute(ast)

                # Emit structured header + JSON line on stdout
                matches = len(result.get("findings", result.get("nodes", [])))
                print(f"# result: graph_nodes={graph_nodes_count} matches={matches}", file=_sys.stdout)
                print(json.dumps(result), file=_sys.stdout)
                return

            except Exception as e:
                print(f"VQL 2.0 Error: {e}", file=_sys.stderr)
                print("Hint: Use --validate to check your query syntax", file=_sys.stderr)
                raise typer.Exit(code=1) from e

        # VQL 1.0 path — use cli_mode=True to prevent silent "nodes" degradation
        try:
            intent = parse_intent(
                query_text,
                pattern_dir=Path(pattern_dir) if pattern_dir else None,
                cli_mode=True,
            )
        except PatternLoadError as exc:
            print(
                f"Error: could not load vulnerability patterns. "
                f"Run 'alphaswarm build-kg' from project root or set ALPHASWARM_VULNDOCS_DIR.",
                file=_sys.stderr,
            )
            raise typer.Exit(code=1) from exc

        if no_evidence:
            intent.include_evidence = False
            intent.evidence_mode = "none"
        if compact:
            intent.compact_mode = True
        if explain:
            intent.explain_mode = True

        if show_intent:
            print(intent.model_dump_json(indent=2), file=_sys.stderr)
            return

        plan = QueryPlanner().build(intent)
        executor = QueryExecutor(
            pattern_dir=Path(pattern_dir) if pattern_dir else None,
            output_mode="v2",
            contract_strict=True,
        )
        result = executor.execute(graph_obj, plan, query_source=query_text)

        # Compute matches count from result
        findings = result.get("findings_raw", result.get("findings", []))
        matches_count = len(findings) if isinstance(findings, list) else 0

        # Structured stdout: header line then JSON data line
        print(f"# result: graph_nodes={graph_nodes_count} matches={matches_count}", file=_sys.stdout)
        print(json.dumps(result), file=_sys.stdout)

    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover - defensive for CLI
        _handle_error(exc)


@app.command("suggest")
def suggest(
    graph: str | None = typer.Option(None, "--graph", help="Graph path or contract stem (e.g., 'Token')."),
    focus: str = typer.Option("all", "--focus", help="Category to focus on (all, access_control, reentrancy, oracle, mev, token, dos, upgradeability)."),
    limit: int = typer.Option(5, "--limit", help="Maximum number of suggestions to return."),
    output_format: str = typer.Option("human", "--format", help="Output format: human or json."),
) -> None:
    """Suggest high-value queries based on contract analysis."""
    try:
        from alphaswarm_sol.assist import suggest_queries
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, _ = resolve_and_load_graph(graph)

        # Get suggestions
        result = suggest_queries(graph_obj, focus=focus, limit=limit)

        # Output
        if output_format == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            _print_suggestions_human(result)

    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover - defensive for CLI
        _handle_error(exc)


def _print_suggestions_human(result: dict) -> None:
    """Print suggestions in human-readable format."""
    analysis = result["contract_analysis"]
    suggestions = result["suggestions"]

    # Contract analysis summary
    typer.echo("📊 Contract Analysis")
    typer.echo("━" * 60)
    typer.echo(f"Functions: {analysis['functions']} ({analysis['external_functions']} external, {analysis['public_functions']} public)")
    typer.echo(f"State Variables: {analysis['state_variables']} ({analysis['privileged_state_vars']} privileged)")

    # Security features
    features = []
    if analysis['has_access_control']:
        features.append("✓ Access control")
    else:
        features.append("❌ No access control")

    if analysis['has_external_calls']:
        features.append("✓ External calls")

    if analysis['has_delegatecalls']:
        features.append("⚠️  Delegatecalls present")

    if analysis['has_oracle_reads']:
        features.append("📊 Oracle reads")

    if analysis['has_swap_operations']:
        features.append("🔄 Swap operations")

    if analysis['has_token_transfers']:
        features.append("💰 Token transfers")

    if analysis['has_unbounded_loops']:
        features.append("⚠️  Unbounded loops")

    typer.echo(f"Security: {', '.join(features)}")
    typer.echo(f"Complexity: {analysis['complexity'].title()}")
    typer.echo()

    # Suggestions
    if not suggestions:
        typer.echo("💡 No applicable vulnerability queries found for this contract.")
        typer.echo("The contract may not have patterns that match known vulnerability queries.")
        return

    typer.echo(f"🎯 Top {len(suggestions)} Vulnerability Queries")
    typer.echo("━" * 60)
    typer.echo()

    priority_emoji = {
        "CRITICAL": "🔴",
        "HIGH": "🟡",
        "MEDIUM": "🟠",
        "LOW": "🟢",
    }

    for s in suggestions:
        emoji = priority_emoji.get(s["priority"], "⚪")
        typer.echo(f"{s['rank']}. {emoji} {s['priority']} | {s['category'].title()}")
        typer.echo(f"   {s['title']}")
        typer.echo()
        typer.echo(f"   Query: {s['query']}")
        typer.echo()
        typer.echo(f"   Why: {s['why']}")
        typer.echo(f"   Expect: {s['expected_findings']}")
        typer.echo(f"   Effectiveness: {int(s['effectiveness'] * 100)}%")
        typer.echo(f"   Score: {s['final_score']}")
        typer.echo()
        typer.echo(f"   Run: {s['execute_with']}")
        typer.echo()

    typer.echo("━" * 60)
    typer.echo(f"💡 Tip: Copy and run the suggested queries to find vulnerabilities")
    typer.echo(f"📊 {result['metadata']['applicable_queries']} applicable queries out of {result['metadata']['total_candidates']} total")


@app.command("lens-report")
def lens_report(
    graph: str | None = typer.Option(None, "--graph", help="Graph path or contract stem (e.g., 'Token')."),
    lens: list[str] = typer.Option(
        None,
        "--lens",
        help="Lens to include (repeatable). Defaults to Ordering, Oracle, ExternalInfluence.",
    ),
    limit: int = typer.Option(50, "--limit", help="Max findings to include."),
    pattern_dir: str | None = typer.Option(None, "--pattern-dir", help="Directory with pattern packs."),
) -> None:
    """Aggregate lens findings into a per-contract report."""
    try:
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        graph_obj, _ = resolve_and_load_graph(graph)
        report = build_lens_report(
            graph_obj,
            lens or ["Ordering", "Oracle", "ExternalInfluence"],
            limit=limit,
            pattern_dir=Path(pattern_dir) if pattern_dir else None,
        )
        typer.echo(json.dumps(report, indent=2))
    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover - defensive for CLI
        _handle_error(exc)


@app.command("schema")
def schema(
    graph: str | None = typer.Option(None, "--graph", help="Graph path or contract stem (e.g., 'Token')."),
    pattern_dir: str | None = typer.Option(None, "--pattern-dir", help="Directory with pattern packs."),
) -> None:
    """Export a schema snapshot for autocomplete and validation."""
    try:
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        graph_obj = None
        if graph:
            graph_obj, _ = resolve_and_load_graph(graph)
        snapshot = build_schema_snapshot(
            graph_obj, pattern_dir=Path(pattern_dir) if pattern_dir else None
        )
        typer.echo(json.dumps(snapshot.to_dict(), indent=2))
    except typer.Exit:
        raise
    except Exception as exc:  # pragma: no cover - defensive for CLI
        _handle_error(exc)


# Scaffold subcommand group
scaffold_app = typer.Typer(help="Test scaffold generation for vulnerability verification")
app.add_typer(scaffold_app, name="scaffold")


@scaffold_app.command("generate")
def scaffold_generate(
    finding_id: str = typer.Argument(..., help="Finding ID (e.g., VKG-001)"),
    tier: int = typer.Option(2, "--tier", "-t", help="Target tier (1=template, 2=smart)"),
    project: str | None = typer.Option(None, "--project", "-p", help="Project root path"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing file"),
) -> None:
    """Generate a test scaffold for a finding."""
    try:
        from alphaswarm_sol.testing import (
            TestTier,
            generate_with_fallback,
            detect_project_structure,
            write_scaffold_to_file,
        )

        # Create a mock finding from ID
        # In real use, this would load from findings storage
        finding = Finding(
            id=finding_id,
            title=f"Finding {finding_id}",
            severity=Severity.HIGH,
            description="Generated scaffold for verification",
        )

        # Detect project structure if provided
        project_config = None
        if project:
            project_config = detect_project_structure(Path(project))

        # Map tier number to enum
        target_tier = TestTier.TIER_1_TEMPLATE if tier == 1 else TestTier.TIER_2_SMART

        # Generate scaffold
        scaffold = generate_with_fallback(
            finding,
            target_tier=target_tier,
            project_config=project_config,
        )

        # Output handling
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                typer.echo(f"Error: File exists: {output_path}", err=True)
                typer.echo("Use --force to overwrite", err=True)
                raise typer.Exit(code=1)
            write_scaffold_to_file(scaffold, output_path.parent)
            typer.echo(f"Scaffold written to: {output_path.parent / scaffold.filename}")
        else:
            # Print to stdout
            typer.echo(scaffold.content)

        # Log info
        structlog.get_logger().info(
            "scaffold_generated",
            finding_id=finding_id,
            tier=scaffold.tier,
            confidence=scaffold.confidence,
            filename=scaffold.filename,
        )

    except Exception as exc:
        _handle_error(exc)


@scaffold_app.command("batch")
def scaffold_batch(
    graph: str | None = typer.Option(None, "--graph", "-g", help="Graph path or contract stem (e.g., 'Token')."),
    tier: int = typer.Option(2, "--tier", "-t", help="Target tier (1=template, 2=smart)"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    pattern_dir: str | None = typer.Option(None, "--pattern-dir", help="Pattern directory"),
) -> None:
    """Generate scaffolds for all findings from a graph analysis."""
    try:
        from alphaswarm_sol.testing import (
            TestTier,
            batch_generate_with_quality,
            detect_project_structure,
            QualityTracker,
        )
        from alphaswarm_sol.queries.patterns import PatternEngine
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, graph_info = resolve_and_load_graph(graph)
        if graph_info:
            project_root = graph_info.dir_path.parent.parent
        else:
            project_root = Path.cwd()

        # Run pattern detection to get findings
        pdir = Path(pattern_dir) if pattern_dir else None
        engine = PatternEngine(pattern_dir=pdir)
        matches = engine.run_all_patterns(graph_obj)

        if not matches:
            typer.echo("No findings detected. Nothing to scaffold.")
            return

        # Convert matches to findings
        findings = []
        for i, match in enumerate(matches):
            finding = Finding(
                id=f"VKG-{i+1:03d}",
                title=match.get("pattern_id", "Unknown"),
                severity=Severity.HIGH,
                description=match.get("why_match", "Pattern match"),
                location=match.get("function", "Unknown"),
            )
            findings.append(finding)

        # Setup output
        out_dir = Path(output_dir) if output_dir else Path(".vrs/scaffolds")
        out_dir.mkdir(parents=True, exist_ok=True)

        # Track quality
        tracker = QualityTracker(storage_path=out_dir / "quality.json")
        project_config = detect_project_structure(project_root)

        # Map tier
        target_tier = TestTier.TIER_1_TEMPLATE if tier == 1 else TestTier.TIER_2_SMART

        # Generate all scaffolds
        scaffolds = batch_generate_with_quality(
            findings,
            target_tier=target_tier,
            project_config=project_config,
            tracker=tracker,
        )

        # Write scaffolds
        for scaffold in scaffolds:
            scaffold_path = out_dir / scaffold.filename
            scaffold_path.write_text(scaffold.content)

        # Summary
        typer.echo(f"Generated {len(scaffolds)} scaffolds in {out_dir}")
        metrics = tracker.get_metrics()
        typer.echo(f"  Tier 1: {metrics.tier1_generated}")
        typer.echo(f"  Tier 2: {metrics.tier2_generated}")
        if metrics.fallback_count:
            typer.echo(f"  Fallbacks: {metrics.fallback_count}")

    except Exception as exc:
        _handle_error(exc)


@scaffold_app.command("info")
def scaffold_info() -> None:
    """Show test scaffold tier information."""
    try:
        from alphaswarm_sol.testing import TIER_DEFINITIONS, format_tier_summary

        typer.echo("Test Scaffold Tiers")
        typer.echo("=" * 60)
        typer.echo()

        for tier in TIER_DEFINITIONS:
            typer.echo(format_tier_summary(tier))
            typer.echo()

        typer.echo("=" * 60)
        typer.echo("Tier 1: Always works, provides TODO markers")
        typer.echo("Tier 2: Smart templates, 30-40% compile rate target")
        typer.echo("Tier 3: Complete tests (aspirational, <10% success)")

    except Exception as exc:
        _handle_error(exc)


# Benchmark subcommand group
benchmark_app = typer.Typer(help="Benchmark commands for VKG detection and model performance")
app.add_typer(benchmark_app, name="benchmark")

# Add model benchmarking subcommands
from alphaswarm_sol.cli.benchmark import benchmark_cli as model_benchmark_cli
benchmark_app.add_typer(model_benchmark_cli, name="models")


@benchmark_app.command("run")
def benchmark_run(
    suite: str = typer.Option("dvd", "--suite", "-s", help="Benchmark suite to run (dvd, smartbugs)"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output path for results JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    pattern_dir: str | None = typer.Option(None, "--pattern-dir", help="Pattern directory"),
) -> None:
    """Run a benchmark suite against VKG."""
    try:
        from alphaswarm_sol.benchmark.runner import run_benchmark

        output_path = Path(output) if output else None
        pdir = Path(pattern_dir) if pattern_dir else None

        typer.echo(f"Running benchmark suite: {suite}")
        results = run_benchmark(
            suite_name=suite,
            project_root=Path.cwd(),
            pattern_dir=pdir,
            output_path=output_path,
            verbose=verbose,
        )

        # Print summary
        typer.echo("")
        typer.echo("=" * 60)
        typer.echo(f"Benchmark Results: {suite}")
        typer.echo("=" * 60)
        typer.echo(f"Detection Rate: {results.detection_rate:.1%} ({results.detected_count}/{results.total_challenges - results.skipped_count})")
        typer.echo(f"Average Recall: {results.average_recall:.1%}")
        typer.echo(f"False Positives: {results.total_false_positives}")
        typer.echo(f"Total Time: {results.total_time_ms:.0f}ms")
        typer.echo("")

        if output_path:
            typer.echo(f"Results saved to: {output_path}")

    except Exception as exc:
        _handle_error(exc)


@benchmark_app.command("compare")
def benchmark_compare(
    current: str = typer.Argument(..., help="Path to current results JSON"),
    baseline: str = typer.Argument(..., help="Path to baseline results JSON"),
) -> None:
    """Compare benchmark results against a baseline."""
    try:
        from alphaswarm_sol.benchmark.results import BenchmarkResults, compare_results

        current_results = BenchmarkResults.load(Path(current))
        baseline_results = BenchmarkResults.load(Path(baseline))

        comparison = compare_results(current_results, baseline_results)

        typer.echo("=" * 60)
        typer.echo("Benchmark Comparison")
        typer.echo("=" * 60)
        typer.echo(f"Current Rate:  {comparison['current_rate']:.1%}")
        typer.echo(f"Baseline Rate: {comparison['baseline_rate']:.1%}")
        typer.echo(f"Delta:         {comparison['rate_delta']:+.1%}")
        typer.echo("")

        if comparison["improved"]:
            typer.echo(f"✓ Improved: {', '.join(comparison['improved'])}")
        if comparison["regressed"]:
            typer.echo(f"✗ Regressed: {', '.join(comparison['regressed'])}")

        if comparison["has_regression"]:
            typer.echo("")
            typer.echo("⚠️  REGRESSION DETECTED - blocking merge")
            raise typer.Exit(code=1)
        else:
            typer.echo("")
            typer.echo("✓ No regressions detected")

    except Exception as exc:
        _handle_error(exc)


@benchmark_app.command("list")
def benchmark_list() -> None:
    """List available benchmark suites."""
    try:
        benchmarks_dir = Path(__file__).parent.parent.parent / "benchmarks"
        suites = []

        for d in benchmarks_dir.iterdir():
            if d.is_dir() and (d / "suite.yaml").exists():
                suites.append(d.name)

        typer.echo("Available benchmark suites:")
        for s in sorted(suites):
            typer.echo(f"  - {s}")

    except Exception as exc:
        _handle_error(exc)


# Orchestrator command (Phase 5 Task 5.8)
@app.command("orchestrate")
def orchestrate(
    path: str = typer.Argument(..., help="Path to Solidity project"),
    tools: str = typer.Option(
        "vkg,slither,aderyn",
        "--tools",
        "-t",
        help="Comma-separated list of tools to run",
    ),
    output: str = typer.Option(
        "orchestrator-report.json",
        "--output",
        "-o",
        help="Output file path",
    ),
    skip_missing: bool = typer.Option(
        True,
        "--skip-missing/--no-skip-missing",
        help="Skip tools that are not installed",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown",
        "-m",
        help="Generate Markdown report instead of JSON",
    ),
) -> None:
    """Run multiple analysis tools and combine results.

    Runs VKG, Slither, and Aderyn (if installed), deduplicates
    findings by location, and generates a combined report.

    Examples:

        # Run all available tools
        uv run alphaswarm orchestrate ./src

        # Run specific tools only
        uv run alphaswarm orchestrate ./src --tools vkg,slither

        # Generate Markdown report
        uv run alphaswarm orchestrate ./src --markdown -o report.md
    """
    try:
        from alphaswarm_sol.orchestration import (
            ToolRunner,
            deduplicate_findings,
            generate_report,
            format_report,
            format_markdown_report,
        )

        project_path = Path(path)
        if not project_path.exists():
            typer.echo(f"Error: Path not found: {project_path}", err=True)
            raise typer.Exit(code=1)

        # Parse tools list
        tool_list = [t.strip() for t in tools.split(",") if t.strip()]

        typer.echo(f"Orchestrating analysis on: {project_path}")
        typer.echo(f"Tools: {', '.join(tool_list)}")
        typer.echo("")

        # Run tools
        runner = ToolRunner(project_path)
        available = runner.get_available_tools()

        typer.echo("Available tools: " + ", ".join(available))
        typer.echo("")

        results = runner.run_all(tools=tool_list, skip_missing=skip_missing)

        # Show tool results
        for r in results:
            if r.status.value == "success":
                typer.echo(f"  ✓ {r.tool}: {len(r.findings)} findings ({r.execution_time:.1f}s)")
            else:
                typer.echo(f"  ✗ {r.tool}: {r.status.value} - {r.error}")

        typer.echo("")

        # Collect all findings
        all_findings = []
        for r in results:
            all_findings.extend(r.findings)

        typer.echo(f"Total raw findings: {len(all_findings)}")

        # Deduplicate
        deduped = deduplicate_findings(all_findings)
        typer.echo(f"After deduplication: {len(deduped)}")
        typer.echo("")

        # Generate report
        report = generate_report(str(project_path), results, deduped)

        # Output
        output_path = Path(output)
        if markdown:
            content = format_markdown_report(report)
            output_path.write_text(content)
            typer.echo(f"Markdown report saved to: {output_path}")
        else:
            report.save(output_path)
            typer.echo(f"JSON report saved to: {output_path}")

        # Print summary if verbose
        if verbose:
            typer.echo("")
            typer.echo(format_report(report, verbose=True))

    except Exception as exc:
        _handle_error(exc)


@app.command("validate")
def validate_cmd(
    project: str | None = typer.Option(None, "--project", "-p", help="Project directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all validation checks"),
) -> None:
    """Validate .vrs directory integrity.

    Checks:
    - Directory structure exists
    - JSON files are valid
    - Version tracking is consistent
    - Graph file has required fields

    Example:
        vkg validate
        vkg validate --project /path/to/project
        vkg validate --verbose
    """
    try:
        from alphaswarm_sol.core.validator import StateValidator

        project_dir = Path(project) if project else Path.cwd()
        vkg_dir = project_dir / ".vrs"

        if not vkg_dir.exists():
            typer.echo("No .vrs directory found.", err=True)
            typer.echo("Hint: Run 'vkg build-kg <path>' first", err=True)
            raise typer.Exit(code=1)

        validator = StateValidator(vkg_dir)
        results = validator.validate_all()

        invalid = [r for r in results if not r.valid]

        if verbose:
            typer.echo(f"Validated {len(results)} items:")
            for r in results:
                status = "[OK]" if r.valid else "[FAIL]"
                typer.echo(f"  {status} {r.path}")
                if r.issue:
                    typer.echo(f"         {r.issue}")
            typer.echo()

        if invalid:
            typer.echo(f"Found {len(invalid)} validation error(s):", err=True)
            for r in invalid:
                typer.echo(f"  [ERROR] {r.path}: {r.issue}", err=True)
            raise typer.Exit(code=1)
        else:
            typer.echo(f"Validated {len(results)} items. All OK.")

    except typer.Exit:
        raise
    except Exception as exc:
        _handle_error(exc)


@app.command("reset")
def reset_cmd(
    confirm: bool = typer.Option(False, "--confirm", help="Confirm reset (required)"),
    project: str | None = typer.Option(None, "--project", "-p", help="Project directory"),
) -> None:
    """Reset VKG state (DESTRUCTIVE).

    This command deletes the entire .vrs directory, removing:
    - Built knowledge graphs
    - Cached analysis results
    - Version history
    - Stored findings

    This is a last-resort option when repair fails.

    Example:
        vkg reset --confirm
        vkg reset --confirm --project /path/to/project
    """
    import shutil

    if not confirm:
        typer.echo("This will delete all VKG state. Use --confirm to proceed.", err=True)
        typer.echo()
        typer.echo("What will be deleted:", err=True)
        typer.echo("  - Built knowledge graphs", err=True)
        typer.echo("  - Cached analysis results", err=True)
        typer.echo("  - Version history", err=True)
        typer.echo("  - Stored findings", err=True)
        raise typer.Exit(code=1)

    project_dir = Path(project) if project else Path.cwd()
    vkg_dir = project_dir / ".vrs"

    if vkg_dir.exists():
        shutil.rmtree(vkg_dir)
        typer.echo("VKG state reset successfully.")
        typer.echo("Run 'vkg build-kg <path>' to rebuild.")
    else:
        typer.echo("No .vrs directory found. Nothing to reset.")
