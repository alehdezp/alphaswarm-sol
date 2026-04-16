"""CLI commands for protocol context pack management.

CLI interface for generating, displaying, and managing protocol context packs.
Context packs capture protocol-level information (roles, assumptions, invariants,
off-chain inputs) for LLM-driven vulnerability detection.

Per 03-CONTEXT.md: "Both: auto-generate during `build-kg` AND standalone
`alphaswarm generate-context` command"

Philosophy: "LLM-generated, not human-authored" with confidence tracking.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Optional

import structlog
import typer

from alphaswarm_sol.context import (
    ContextPackBuilder,
    BuildConfig,
    ContextPackStorage,
    ProtocolContextPack,
    Confidence,
)

context_app = typer.Typer(help="Protocol context pack management")
logger = structlog.get_logger()


# =============================================================================
# Constants
# =============================================================================

DEFAULT_CONTEXT_DIR = Path(".vrs/context")


# =============================================================================
# Helper Functions
# =============================================================================


def _get_storage(path: Path) -> ContextPackStorage:
    """Get context pack storage instance.

    Args:
        path: Project path to derive storage location from

    Returns:
        ContextPackStorage instance
    """
    context_dir = path / ".vrs" / "context"
    return ContextPackStorage(context_dir)


def _format_confidence(confidence: Confidence) -> str:
    """Format confidence for display.

    Args:
        confidence: Confidence level

    Returns:
        Formatted string with indicator
    """
    indicators = {
        Confidence.CERTAIN: "[+]",
        Confidence.INFERRED: "[?]",
        Confidence.UNKNOWN: "[ ]",
    }
    return f"{indicators.get(confidence, '[ ]')} {confidence.value}"


def _print_pack_summary(pack: ProtocolContextPack) -> None:
    """Print context pack summary.

    Args:
        pack: ProtocolContextPack to display
    """
    typer.echo(f"\n{'='*60}")
    typer.echo(f"Protocol: {pack.protocol_name}")
    typer.echo(f"Type: {pack.protocol_type or 'Unknown'}")
    typer.echo(f"Version: {pack.version}")
    typer.echo(f"Generated: {pack.generated_at}")
    typer.echo(f"Auto-generated: {pack.auto_generated}")
    typer.echo(f"Reviewed: {pack.reviewed}")
    typer.echo(f"{'='*60}")

    # Counts
    typer.echo(f"\n## Summary")
    typer.echo(f"  Roles:           {len(pack.roles)}")
    typer.echo(f"  Assumptions:     {len(pack.assumptions)}")
    typer.echo(f"  Invariants:      {len(pack.invariants)}")
    typer.echo(f"  Off-chain:       {len(pack.offchain_inputs)}")
    typer.echo(f"  Value Flows:     {len(pack.value_flows)}")
    typer.echo(f"  Critical Funcs:  {len(pack.critical_functions)}")
    typer.echo(f"  Accepted Risks:  {len(pack.accepted_risks)}")
    typer.echo(f"  Sources:         {len(pack.sources)}")

    # Confidence breakdown
    summary = pack.confidence_summary()
    typer.echo(f"\n## Confidence Breakdown")
    for section, counts in summary.items():
        certain = counts.get("certain", 0)
        inferred = counts.get("inferred", 0)
        unknown = counts.get("unknown", 0)
        total = certain + inferred + unknown
        if total > 0:
            typer.echo(f"  {section}: {certain} certain, {inferred} inferred, {unknown} unknown")

    # Token estimate
    typer.echo(f"\n## Token Estimate: ~{pack.token_estimate():,} tokens")


def _print_roles_section(pack: ProtocolContextPack) -> None:
    """Print roles section.

    Args:
        pack: ProtocolContextPack to display roles from
    """
    typer.echo(f"\n## Roles ({len(pack.roles)})")
    typer.echo("-" * 40)

    for role in pack.roles:
        conf = _format_confidence(role.confidence)
        typer.echo(f"\n### {role.name} {conf}")
        if role.description:
            typer.echo(f"    {role.description}")
        typer.echo(f"    Capabilities:")
        for cap in role.capabilities:
            typer.echo(f"      - {cap}")
        if role.trust_assumptions:
            typer.echo(f"    Trust Assumptions:")
            for ta in role.trust_assumptions:
                typer.echo(f"      - {ta}")


def _print_assumptions_section(pack: ProtocolContextPack) -> None:
    """Print assumptions section.

    Args:
        pack: ProtocolContextPack to display assumptions from
    """
    typer.echo(f"\n## Assumptions ({len(pack.assumptions)})")
    typer.echo("-" * 40)

    for i, assumption in enumerate(pack.assumptions, 1):
        conf = _format_confidence(assumption.confidence)
        typer.echo(f"\n{i}. {conf} [{assumption.category}]")
        typer.echo(f"   {assumption.description}")
        if assumption.affects_functions:
            typer.echo(f"   Affects: {', '.join(assumption.affects_functions)}")
        if assumption.source:
            typer.echo(f"   Source: {assumption.source}")


def _print_invariants_section(pack: ProtocolContextPack) -> None:
    """Print invariants section.

    Args:
        pack: ProtocolContextPack to display invariants from
    """
    typer.echo(f"\n## Invariants ({len(pack.invariants)})")
    typer.echo("-" * 40)

    for i, inv in enumerate(pack.invariants, 1):
        conf = _format_confidence(inv.confidence)
        critical = "[CRITICAL]" if inv.critical else ""
        typer.echo(f"\n{i}. {conf} {critical}")
        typer.echo(f"   {inv.natural_language}")
        if inv.formal:
            typer.echo(f"   Formal: {inv.formal}")
        if inv.category:
            typer.echo(f"   Category: {inv.category}")


def _print_offchain_section(pack: ProtocolContextPack) -> None:
    """Print off-chain inputs section.

    Args:
        pack: ProtocolContextPack to display off-chain inputs from
    """
    typer.echo(f"\n## Off-chain Inputs ({len(pack.offchain_inputs)})")
    typer.echo("-" * 40)

    for inp in pack.offchain_inputs:
        conf = _format_confidence(inp.confidence)
        typer.echo(f"\n### {inp.name} ({inp.input_type}) {conf}")
        if inp.description:
            typer.echo(f"    {inp.description}")
        if inp.trust_assumptions:
            typer.echo(f"    Trust Assumptions:")
            for ta in inp.trust_assumptions:
                typer.echo(f"      - {ta}")
        if inp.affects_functions:
            typer.echo(f"    Affects: {', '.join(inp.affects_functions)}")


def _print_value_flows_section(pack: ProtocolContextPack) -> None:
    """Print value flows section.

    Args:
        pack: ProtocolContextPack to display value flows from
    """
    typer.echo(f"\n## Value Flows ({len(pack.value_flows)})")
    typer.echo("-" * 40)

    for flow in pack.value_flows:
        conf = _format_confidence(flow.confidence)
        typer.echo(f"\n### {flow.name} {conf}")
        typer.echo(f"    {flow.from_role} -> {flow.to_role} [{flow.asset}]")
        if flow.conditions:
            typer.echo(f"    Conditions:")
            for cond in flow.conditions:
                typer.echo(f"      - {cond}")


def _print_accepted_risks_section(pack: ProtocolContextPack) -> None:
    """Print accepted risks section.

    Args:
        pack: ProtocolContextPack to display accepted risks from
    """
    typer.echo(f"\n## Accepted Risks ({len(pack.accepted_risks)})")
    typer.echo("-" * 40)

    for i, risk in enumerate(pack.accepted_risks, 1):
        typer.echo(f"\n{i}. [{risk.severity}] {risk.description}")
        typer.echo(f"   Reason: {risk.reason}")
        if risk.affects_functions:
            typer.echo(f"   Affects: {', '.join(risk.affects_functions)}")
        typer.echo(f"   Documented in: {risk.documented_in}")


def _print_security_section(pack: ProtocolContextPack) -> None:
    """Print security section.

    Args:
        pack: ProtocolContextPack to display security info from
    """
    typer.echo(f"\n## Security Model")
    typer.echo("-" * 40)

    if pack.security_model:
        for key, value in pack.security_model.items():
            typer.echo(f"  {key}: {value}")
    else:
        typer.echo("  No security model defined")

    typer.echo(f"\n## Critical Functions ({len(pack.critical_functions)})")
    for func in pack.critical_functions:
        typer.echo(f"  - {func}")


# =============================================================================
# CLI Commands
# =============================================================================


@context_app.command("generate")
def generate_context(
    path: str = typer.Argument(".", help="Path to Solidity project"),
    docs: Optional[str] = typer.Option(
        None, "--docs", "-d", help="Path to documentation directory"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output path for context pack"
    ),
    sources: Optional[List[str]] = typer.Option(
        None, "--source", "-s", help="Additional doc sources (URLs or paths)"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Protocol name override"
    ),
    protocol_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Protocol type override (lending, dex, etc.)"
    ),
    no_code: bool = typer.Option(
        False, "--no-code", help="Skip code analysis (docs only)"
    ),
    no_docs: bool = typer.Option(
        False, "--no-docs", help="Skip doc parsing (code only)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing context pack"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output result as JSON"
    ),
) -> None:
    """Generate protocol context pack from code and documentation.

    Analyzes Solidity code via VKG and optionally parses documentation
    to create a unified protocol context pack with roles, assumptions,
    invariants, and other security-relevant context.

    Examples:
        # Auto-discover docs and analyze code
        uv run alphaswarm context generate ./src

        # Specify docs directory
        uv run alphaswarm context generate ./src --docs ./docs

        # Add external sources
        uv run alphaswarm context generate ./src --source https://docs.protocol.io

        # Override protocol name and type
        uv run alphaswarm context generate ./src --name "MyProtocol" --type lending

        # Skip code analysis (docs only)
        uv run alphaswarm context generate ./src --no-code --docs ./docs
    """
    try:
        project_path = Path(path).resolve()

        if not project_path.exists():
            typer.echo(f"Error: Path not found: {project_path}", err=True)
            raise typer.Exit(code=1)

        # Check if context pack already exists
        storage = _get_storage(project_path)
        pack_name = name or project_path.name

        if storage.exists(pack_name) and not force:
            typer.echo(
                f"Error: Context pack '{pack_name}' already exists. Use --force to overwrite.",
                err=True,
            )
            raise typer.Exit(code=1)

        # Build the knowledge graph first (if doing code analysis)
        graph = None
        if not no_code:
            from alphaswarm_sol.kg.builder import VKGBuilder

            typer.echo(f"Building knowledge graph for {project_path}...")
            try:
                builder = VKGBuilder(project_path)
                graph = builder.build(project_path)
                typer.echo(f"Graph built: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
            except Exception as e:
                typer.echo(f"Warning: Failed to build graph: {e}", err=True)
                if no_docs:
                    typer.echo("Error: Cannot proceed without code analysis or docs", err=True)
                    raise typer.Exit(code=1)

        # Require a graph for context building
        if graph is None:
            # Create a minimal graph to satisfy the builder
            from alphaswarm_sol.kg.schema import KnowledgeGraph

            graph = KnowledgeGraph()
            typer.echo("Note: No knowledge graph available, context will be limited")

        # Create build config
        additional_sources = list(sources) if sources else []
        if docs:
            additional_sources.append(docs)

        config = BuildConfig(
            protocol_name=pack_name,
            protocol_type=protocol_type or "",
            include_code_analysis=not no_code,
            include_doc_parsing=not no_docs,
            additional_doc_sources=additional_sources,
            infer_unstated_assumptions=True,
            cross_validate=True,
            generate_questions=True,
            auto_discover_docs=not no_docs,
        )

        typer.echo(f"\nGenerating context pack for '{pack_name}'...")
        typer.echo(f"  Code analysis: {'enabled' if not no_code else 'disabled'}")
        typer.echo(f"  Doc parsing: {'enabled' if not no_docs else 'disabled'}")

        # Build context pack (async method)
        context_builder = ContextPackBuilder(
            graph=graph,
            project_path=project_path,
            config=config,
        )

        result = asyncio.run(context_builder.build())
        pack = result.pack

        # Save the pack
        output_path = Path(output) if output else None
        if output_path:
            # Save to specified path as YAML
            import yaml

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(pack.to_dict(), f, default_flow_style=False, allow_unicode=True)
            typer.echo(f"\nContext pack saved to: {output_path}")
        else:
            # Save to standard storage
            saved_path = storage.save(pack, pack_name)
            typer.echo(f"\nContext pack saved to: {saved_path}")

        # Output result
        if json_output:
            typer.echo(json.dumps(result.to_dict(), indent=2))
        else:
            _print_pack_summary(pack)

            # Show warnings
            if result.warnings:
                typer.echo(f"\n## Warnings ({len(result.warnings)})")
                for warning in result.warnings:
                    typer.echo(f"  - {warning}")

            # Show conflicts
            if result.conflicts:
                typer.echo(f"\n## Conflicts ({len(result.conflicts)})")
                for conflict in result.conflicts:
                    typer.echo(f"  [{conflict.severity}] {conflict.description}")

            # Show questions
            if result.questions:
                typer.echo(f"\n## Investigation Questions ({len(result.questions)})")
                for q in result.questions:
                    typer.echo(f"  ? {q}")

            typer.echo(f"\nBuild time: {result.build_time:.2f}s")

        logger.info(
            "context_generated",
            pack_name=pack_name,
            roles=len(pack.roles),
            assumptions=len(pack.assumptions),
            build_time=result.build_time,
        )

    except typer.Exit:
        raise
    except Exception as exc:
        logger.error("context_generate_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("show")
def show_context(
    path: str = typer.Argument(".", help="Path to project with context pack"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Context pack name"
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Show specific section (roles, assumptions, invariants, offchain, flows, risks, security)",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Display context pack contents.

    Shows the full context pack or specific sections for targeted
    retrieval. Useful for reviewing generated context and for
    piping into other tools.

    Examples:
        # Show full context pack
        uv run alphaswarm context show ./src

        # Show specific section
        uv run alphaswarm context show ./src --section roles
        uv run alphaswarm context show ./src --section assumptions

        # Output as JSON
        uv run alphaswarm context show ./src --json
    """
    try:
        project_path = Path(path).resolve()

        if not project_path.exists():
            typer.echo(f"Error: Path not found: {project_path}", err=True)
            raise typer.Exit(code=1)

        storage = _get_storage(project_path)
        pack_name = name or project_path.name

        # Load the pack
        pack = storage.load(pack_name)
        if pack is None:
            typer.echo(f"Error: Context pack '{pack_name}' not found", err=True)
            typer.echo(f"Hint: Run 'uv run alphaswarm context generate {path}' first", err=True)
            raise typer.Exit(code=1)

        # JSON output
        if json_output:
            if section:
                section_data = pack.get_section(section)
                if section_data:
                    typer.echo(json.dumps(section_data, indent=2))
                else:
                    typer.echo(f"Error: Section '{section}' not found", err=True)
                    raise typer.Exit(code=1)
            else:
                typer.echo(json.dumps(pack.to_dict(), indent=2))
            return

        # Human-readable output
        if section:
            # Show specific section
            section_printers = {
                "roles": _print_roles_section,
                "assumptions": _print_assumptions_section,
                "invariants": _print_invariants_section,
                "offchain": _print_offchain_section,
                "offchain_inputs": _print_offchain_section,
                "flows": _print_value_flows_section,
                "value_flows": _print_value_flows_section,
                "risks": _print_accepted_risks_section,
                "accepted_risks": _print_accepted_risks_section,
                "security": _print_security_section,
            }

            printer = section_printers.get(section.lower())
            if printer:
                printer(pack)
            else:
                typer.echo(f"Error: Unknown section '{section}'", err=True)
                typer.echo(f"Available sections: {', '.join(section_printers.keys())}", err=True)
                raise typer.Exit(code=1)
        else:
            # Show full pack
            _print_pack_summary(pack)
            _print_roles_section(pack)
            _print_assumptions_section(pack)
            _print_invariants_section(pack)
            _print_offchain_section(pack)
            _print_value_flows_section(pack)
            _print_accepted_risks_section(pack)
            _print_security_section(pack)

            if pack.notes:
                typer.echo(f"\n## Notes")
                typer.echo(pack.notes)

    except typer.Exit:
        raise
    except Exception as exc:
        logger.error("context_show_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("update")
def update_context(
    path: str = typer.Argument(".", help="Path to project"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Context pack name to update"
    ),
    changed_files: Optional[List[str]] = typer.Option(
        None, "--changed", "-c", help="Specify changed files (for incremental update)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Update existing context pack with code changes.

    Performs incremental update when code changes, preserving
    human-verified content and adding new inferences.

    Examples:
        # Update after code changes
        uv run alphaswarm context update ./src

        # Specify changed files for targeted update
        uv run alphaswarm context update ./src --changed Token.sol --changed Vault.sol
    """
    try:
        project_path = Path(path).resolve()

        if not project_path.exists():
            typer.echo(f"Error: Path not found: {project_path}", err=True)
            raise typer.Exit(code=1)

        storage = _get_storage(project_path)
        pack_name = name or project_path.name

        # Load existing pack
        existing_pack = storage.load(pack_name)
        if existing_pack is None:
            typer.echo(f"Error: Context pack '{pack_name}' not found", err=True)
            typer.echo(f"Hint: Run 'uv run alphaswarm context generate {path}' first", err=True)
            raise typer.Exit(code=1)

        # Build the knowledge graph
        from alphaswarm_sol.kg.builder import VKGBuilder

        typer.echo(f"Rebuilding knowledge graph...")
        builder = VKGBuilder(project_path)
        graph = builder.build(project_path)
        typer.echo(f"Graph built: {len(graph.nodes)} nodes")

        # Create builder with existing config
        config = BuildConfig(
            protocol_name=pack_name,
            protocol_type=existing_pack.protocol_type,
            include_code_analysis=True,
            include_doc_parsing=True,
            infer_unstated_assumptions=True,
            cross_validate=True,
            generate_questions=True,
        )

        context_builder = ContextPackBuilder(
            graph=graph,
            project_path=project_path,
            config=config,
        )

        # Perform incremental update (async method)
        typer.echo(f"Updating context pack '{pack_name}'...")
        result = asyncio.run(context_builder.update(
            existing_pack=existing_pack,
            changed_files=list(changed_files) if changed_files else None,
        ))

        # Save updated pack
        saved_path = storage.save(result.pack, pack_name)
        typer.echo(f"Updated context pack saved to: {saved_path}")

        # Output
        if json_output:
            typer.echo(json.dumps(result.to_dict(), indent=2))
        else:
            _print_pack_summary(result.pack)

            if result.warnings:
                typer.echo(f"\n## Warnings")
                for warning in result.warnings:
                    typer.echo(f"  - {warning}")

            typer.echo(f"\nUpdate time: {result.build_time:.2f}s")

        logger.info(
            "context_updated",
            pack_name=pack_name,
            build_time=result.build_time,
        )

    except typer.Exit:
        raise
    except Exception as exc:
        logger.error("context_update_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("list")
def list_context(
    path: str = typer.Argument(".", help="Path to project"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all stored context packs.

    Examples:
        uv run alphaswarm context list
        uv run alphaswarm context list --json
    """
    try:
        project_path = Path(path).resolve()
        storage = _get_storage(project_path)

        summary = storage.get_summary()

        if json_output:
            typer.echo(json.dumps(summary, indent=2))
            return

        if summary["total"] == 0:
            typer.echo("No context packs found.")
            typer.echo(f"Hint: Run 'uv run alphaswarm context generate {path}' to create one")
            return

        typer.echo(f"\n## Context Packs ({summary['total']})")
        typer.echo("-" * 60)

        for pack in summary["packs"]:
            reviewed = "[reviewed]" if pack["reviewed"] else "[auto]"
            typer.echo(
                f"  {pack['name']:<20} {pack['protocol_type']:<10} "
                f"{pack['roles']}R {pack['assumptions']}A {pack['invariants']}I {reviewed}"
            )

    except Exception as exc:
        logger.error("context_list_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("delete")
def delete_context(
    path: str = typer.Argument(".", help="Path to project"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Context pack name to delete"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation prompt"
    ),
) -> None:
    """Delete a context pack.

    Examples:
        uv run alphaswarm context delete --name MyProtocol
        uv run alphaswarm context delete --name MyProtocol --force
    """
    try:
        project_path = Path(path).resolve()
        storage = _get_storage(project_path)
        pack_name = name or project_path.name

        if not storage.exists(pack_name):
            typer.echo(f"Error: Context pack '{pack_name}' not found", err=True)
            raise typer.Exit(code=1)

        if not force:
            confirm = typer.confirm(f"Delete context pack '{pack_name}'?")
            if not confirm:
                typer.echo("Cancelled.")
                return

        if storage.delete(pack_name):
            typer.echo(f"Deleted context pack '{pack_name}'")
        else:
            typer.echo(f"Failed to delete '{pack_name}'", err=True)
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as exc:
        logger.error("context_delete_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("export")
def export_context(
    path: str = typer.Argument(".", help="Path to project"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Context pack name"
    ),
    output: str = typer.Option(
        "context-pack.yaml", "--output", "-o", help="Output file path"
    ),
    format_type: str = typer.Option(
        "yaml", "--format", "-f", help="Output format (yaml or json)"
    ),
) -> None:
    """Export context pack to file.

    Examples:
        uv run alphaswarm context export --output my-context.yaml
        uv run alphaswarm context export --format json --output my-context.json
    """
    try:
        project_path = Path(path).resolve()
        storage = _get_storage(project_path)
        pack_name = name or project_path.name

        pack = storage.load(pack_name)
        if pack is None:
            typer.echo(f"Error: Context pack '{pack_name}' not found", err=True)
            raise typer.Exit(code=1)

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format_type.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(pack.to_dict(), f, indent=2)
        else:
            import yaml

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(pack.to_dict(), f, default_flow_style=False, allow_unicode=True)

        typer.echo(f"Exported to: {output_path}")

    except typer.Exit:
        raise
    except Exception as exc:
        logger.error("context_export_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


# =============================================================================
# Context-Merge Bead Commands (Phase 05.5-07)
# =============================================================================


@context_app.command("create-bead")
def create_bead(
    vuln_class: str = typer.Option(
        ..., "--vuln-class", help="Vulnerability class (e.g., reentrancy/classic)"
    ),
    protocol: str = typer.Option(..., "--protocol", help="Protocol name"),
    scope: str = typer.Option(
        ..., "--scope", help="Target scope as JSON array or single path"
    ),
    bundle_file: Path = typer.Option(
        ..., "--bundle-file", help="Path to YAML bundle file"
    ),
    verification_score: float = typer.Option(
        0.9, "--verification-score", help="Verification quality score"
    ),
    pool_id: Optional[str] = typer.Option(
        None, "--pool-id", help="Pool to associate bead with"
    ),
    output_format: str = typer.Option(
        "yaml", "--output-format", "-f", help="Output format (yaml, json)"
    ),
) -> None:
    """Create a context-merge bead from a verified context bundle.

    Used for manually creating context beads from pre-built bundles.
    Typically the orchestration flow creates these automatically.

    Examples:
        # Create bead from bundle file
        uv run alphaswarm context create-bead \\
            --vuln-class reentrancy/classic \\
            --protocol MyProtocol \\
            --scope '["contracts/"]' \\
            --bundle-file bundle.yaml \\
            --pool-id audit-2026-01
    """
    import yaml

    from alphaswarm_sol.agents.context import (
        ContextBeadFactory,
        ContextBundle,
        MergeResult,
        VerificationResult,
    )

    try:
        # Parse scope
        try:
            target_scope = json.loads(scope)
            if isinstance(target_scope, str):
                target_scope = [target_scope]
        except json.JSONDecodeError:
            target_scope = [scope]

        # Load bundle
        if not bundle_file.exists():
            typer.echo(f"Error: Bundle file not found: {bundle_file}", err=True)
            raise typer.Exit(code=1)

        with open(bundle_file) as f:
            bundle_data = yaml.safe_load(f)

        bundle = ContextBundle.from_dict(bundle_data)

        # Create factory
        factory = ContextBeadFactory()

        # Create mock merge/verification results for CLI usage
        merge_result = MergeResult(
            success=True,
            bundle=bundle,
            errors=[],
            warnings=[],
            token_count=0,
            trimmed=False,
            sources_used=["bundle_file"],
        )

        verification_result = VerificationResult(
            valid=True,
            errors=[],
            warnings=[],
            quality_score=verification_score,
            feedback_for_retry=None,
        )

        bead = factory.create_from_verified_merge(
            merge_result=merge_result,
            verification_result=verification_result,
            pool_id=pool_id,
        )
        bead_path = factory.save_bead(bead)

        # Output
        if output_format == "json":
            result = {"status": "success", "bead_id": bead.id, "bead_path": str(bead_path)}
            typer.echo(json.dumps(result, indent=2))
        else:
            typer.echo(f"Bead created: {bead.id}")
            typer.echo(f"  Path: {bead_path}")
            typer.echo(f"  Vuln class: {bead.vulnerability_class}")
            typer.echo(f"  Protocol: {bead.protocol_name}")
            typer.echo(f"  Status: {bead.status.value}")

        logger.info(
            "context_bead_created",
            bead_id=bead.id,
            vuln_class=vuln_class,
            pool_id=pool_id,
        )

    except typer.Exit:
        raise
    except Exception as exc:
        logger.error("create_bead_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("list-beads")
def list_beads(
    pool_id: Optional[str] = typer.Option(
        None, "--pool-id", help="Filter by pool"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", help="Filter by status (pending, in_progress, complete, failed)"
    ),
    output_format: str = typer.Option(
        "table", "--output-format", "-f", help="Output format (table, json)"
    ),
) -> None:
    """List context-merge beads.

    Shows all context beads, optionally filtered by pool or status.

    Examples:
        # List all beads
        uv run alphaswarm context list-beads

        # List beads in a pool
        uv run alphaswarm context list-beads --pool-id audit-2026-01

        # List pending beads
        uv run alphaswarm context list-beads --status pending

        # Output as JSON
        uv run alphaswarm context list-beads --output-format json
    """
    from alphaswarm_sol.agents.context import ContextBeadFactory
    from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus

    try:
        factory = ContextBeadFactory()

        # Get all beads from storage
        beads_dir = factory.beads_dir
        beads = []

        search_dirs = []
        if pool_id:
            pool_dir = beads_dir / pool_id
            if pool_dir.exists():
                search_dirs = [pool_dir]
        else:
            if beads_dir.exists():
                search_dirs = [d for d in beads_dir.iterdir() if d.is_dir()]

        for bead_dir in search_dirs:
            for bead_file in bead_dir.glob("CTX-*.yaml"):
                try:
                    bead = ContextMergeBead.from_yaml(bead_file.read_text())

                    # Filter by status if specified
                    if status and bead.status.value != status:
                        continue

                    beads.append(bead)
                except Exception as e:
                    logger.warning(f"Failed to load bead {bead_file}: {e}")

        if output_format == "json":
            typer.echo(json.dumps([b.to_dict() for b in beads], indent=2, default=str))
        else:
            if not beads:
                typer.echo("No context beads found.")
                return

            # Print table header
            typer.echo("")
            typer.echo(f"{'ID':<20} {'Vuln Class':<25} {'Protocol':<15} {'Status':<12} {'Score':<6} {'Findings'}")
            typer.echo("-" * 90)

            for bead in beads:
                typer.echo(
                    f"{bead.id:<20} "
                    f"{bead.vulnerability_class:<25} "
                    f"{bead.protocol_name:<15} "
                    f"{bead.status.value:<12} "
                    f"{bead.verification_score:.2f}  "
                    f"{len(bead.finding_bead_ids)}"
                )

            typer.echo("")
            typer.echo(f"Total: {len(beads)} beads")

    except Exception as exc:
        logger.error("list_beads_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("show-bead")
def show_bead(
    bead_id: str = typer.Argument(..., help="Bead ID to show"),
    pool_id: Optional[str] = typer.Option(
        None, "--pool-id", help="Pool containing bead"
    ),
    output_format: str = typer.Option(
        "yaml", "--output-format", "-f", help="Output format (yaml, json)"
    ),
) -> None:
    """Show details of a context bead.

    Displays full information about a context-merge bead, including
    the embedded context bundle.

    Examples:
        # Show bead details
        uv run alphaswarm context show-bead CTX-abc123

        # Show as JSON
        uv run alphaswarm context show-bead CTX-abc123 --output-format json
    """
    from alphaswarm_sol.agents.context import ContextBeadFactory

    try:
        factory = ContextBeadFactory()

        try:
            bead = factory.load_bead(bead_id, pool_id)
        except FileNotFoundError:
            typer.echo(f"Error: Bead not found: {bead_id}", err=True)
            raise typer.Exit(code=1)

        if output_format == "json":
            typer.echo(json.dumps(bead.to_dict(), indent=2, default=str))
        else:
            typer.echo(bead.to_yaml())

    except typer.Exit:
        raise
    except Exception as exc:
        logger.error("show_bead_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@context_app.command("run-discovery")
def run_discovery(
    pool_id: str = typer.Option(
        ..., "--pool-id", help="Pool to process"
    ),
    bead_ids: Optional[str] = typer.Option(
        None, "--bead-ids", help="Specific bead IDs (comma-separated)"
    ),
    graph_path: Optional[Path] = typer.Option(
        None, "--graph", help="Path to knowledge graph"
    ),
    max_parallel: int = typer.Option(
        5, "--max-parallel", help="Max parallel discovery agents"
    ),
) -> None:
    """Run vuln-discovery on pending context beads.

    Processes context beads through the vuln-discovery agent to
    produce finding beads with evidence chains.

    Examples:
        # Run discovery on all pending beads in pool
        uv run alphaswarm context run-discovery --pool-id audit-2026-01

        # Run on specific beads
        uv run alphaswarm context run-discovery \\
            --pool-id audit-2026-01 \\
            --bead-ids CTX-abc123,CTX-def456

        # With custom graph
        uv run alphaswarm context run-discovery \\
            --pool-id audit-2026-01 \\
            --graph .vrs/graphs/graph.json
    """
    from alphaswarm_sol.agents.orchestration import MainOrchestrator, OrchestrationConfig
    from alphaswarm_sol.context.schema import ProtocolContextPack

    try:
        # Parse bead IDs
        specific_beads = None
        if bead_ids:
            specific_beads = [b.strip() for b in bead_ids.split(",")]

        # Create minimal protocol pack (discovery doesn't need it)
        protocol_pack = ProtocolContextPack(protocol_name="", protocol_type="")

        config = OrchestrationConfig(max_parallel_discovery=max_parallel)

        orchestrator = MainOrchestrator(
            protocol_pack=protocol_pack,
            target_scope=[],
            vuln_classes=[],
            pool_id=pool_id,
            config=config,
            graph_path=graph_path,
        )

        typer.echo(f"Running vuln-discovery on pool: {pool_id}")
        if specific_beads:
            typer.echo(f"Processing beads: {', '.join(specific_beads)}")

        result = asyncio.run(orchestrator.run_discovery_only(specific_beads))

        # Output results
        typer.echo("")
        typer.echo("Discovery complete")
        typer.echo(f"  Discoveries completed: {result.discovery_completed}")
        typer.echo(f"  Discoveries failed: {result.discovery_failed}")
        typer.echo(f"  Findings created: {result.findings_created}")

        if result.errors:
            typer.echo("")
            typer.echo("Errors:")
            for category, errs in result.errors.items():
                for err in errs:
                    typer.echo(f"  - [{category}] {err}")

        logger.info(
            "discovery_complete",
            pool_id=pool_id,
            completed=result.discovery_completed,
            failed=result.discovery_failed,
            findings=result.findings_created,
        )

    except Exception as exc:
        logger.error("run_discovery_failed", error=str(exc))
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


# =============================================================================
# Module exports
# =============================================================================

__all__ = ["context_app"]
