"""Shared graph resolution for all graph-consuming CLI commands.

Implements:
- Error-when-ambiguous default (refuses to guess among multiple graphs)
- --graph flag with both direct path and stem-based lookup
- Agent-actionable error messages with embedded recovery commands
- Exit code semantics: 0=success, 1=routing/argument error, 2=graph load failure
- schema_version validation at load time

Decision references: D-3 (query graph targeting), D-meta (meta.json schema).
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.kg.store import (
    CorruptGraphError,
    GraphInfo,
    GraphStore,
    SchemaVersionMismatchError,
    list_available_graphs,
)

DEFAULT_GRAPHS_ROOT = Path(".vrs/graphs")


def resolve_and_load_graph(
    graph_flag: str | None,
    *,
    graphs_root: Path = DEFAULT_GRAPHS_ROOT,
) -> tuple[KnowledgeGraph, GraphInfo | None]:
    """Resolve and load a graph, enforcing error-when-ambiguous.

    This is the single entry point for all graph-consuming CLI commands.

    Args:
        graph_flag: Value of --graph flag (path or stem), or None.
        graphs_root: Root directory for graph storage.

    Returns:
        Tuple of (loaded KnowledgeGraph, GraphInfo or None for legacy/direct path).

    Raises:
        typer.Exit: With code 1 for routing errors, code 2 for graph load errors.
    """
    # Case 1: --graph given as direct path
    if graph_flag and _looks_like_path(graph_flag):
        return _load_from_direct_path(Path(graph_flag)), None

    # Discover available graphs
    try:
        available = list_available_graphs(graphs_root)
    except SchemaVersionMismatchError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=2) from exc

    # Case 2: --graph given as stem
    if graph_flag:
        return _resolve_by_stem(graph_flag, available)

    # Case 3: No --graph flag — apply error-when-ambiguous
    return _resolve_auto(available, graphs_root)


def _looks_like_path(value: str) -> bool:
    """Check if --graph value looks like a file path rather than a stem."""
    return "/" in value or value.startswith(".")


def _load_from_direct_path(path: Path) -> KnowledgeGraph:
    """Load graph from a direct path."""
    if not path.exists():
        print(
            f"Error: graph path not found: {path}. "
            f"Run 'alphaswarm build-kg <path>' first.",
            file=sys.stderr,
        )
        raise typer.Exit(code=2)

    # If path is a directory, look for graph.toon/graph.json inside
    if path.is_dir():
        store = GraphStore(path.parent if path.name != "graphs" else path)
        toon_path = path / "graph.toon"
        json_path = path / "graph.json"
        if toon_path.exists():
            graph_file = toon_path
        elif json_path.exists():
            graph_file = json_path
        else:
            print(
                f"Error: no graph file in {path}. "
                f"Run 'alphaswarm build-kg <path>' to build.",
                file=sys.stderr,
            )
            raise typer.Exit(code=2)
        store = GraphStore(path)
        return store.load(path=graph_file)

    # Direct file path
    try:
        store = GraphStore(path.parent)
        return store.load(path=path)
    except CorruptGraphError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        print(
            f"Error: could not load graph from {path}: {exc}",
            file=sys.stderr,
        )
        raise typer.Exit(code=2) from exc


def _resolve_by_stem(
    stem: str, available: list[GraphInfo]
) -> tuple[KnowledgeGraph, GraphInfo]:
    """Resolve --graph stem against meta.json source_contract fields."""
    matches = [g for g in available if g.stem == stem]

    if len(matches) == 1:
        info = matches[0]
        return _load_graph_info(info), info

    if len(matches) > 1:
        # Stem collision — show full contract paths for disambiguation
        paths_list = ", ".join(
            g.meta.contract_paths[0] if g.meta.contract_paths else g.identity
            for g in matches
        )
        print(
            f"Error: ambiguous --graph '{stem}' matches multiple graphs "
            f"-- use full path: {paths_list}",
            file=sys.stderr,
        )
        raise typer.Exit(code=1)

    # 0 matches — show available and suggest build
    _print_available_stems(available)
    print(
        f"Error: no graph found for '--graph {stem}'. "
        f"Run 'alphaswarm build-kg contracts/{stem}.sol' to build.",
        file=sys.stderr,
    )
    raise typer.Exit(code=1)


def _resolve_auto(
    available: list[GraphInfo], graphs_root: Path
) -> tuple[KnowledgeGraph, GraphInfo | None]:
    """Auto-resolve when --graph is not specified."""
    if len(available) == 0:
        # Check for legacy flat file
        store = GraphStore(graphs_root)
        for ext in ("graph.toon", "graph.json"):
            if (graphs_root / ext).exists():
                return store.load(path=graphs_root / ext), None

        print(
            "Error: no graphs found. Run 'alphaswarm build-kg <path>' first.",
            file=sys.stderr,
        )
        raise typer.Exit(code=2)

    if len(available) == 1:
        info = available[0]
        return _load_graph_info(info), info

    # 2+ graphs — error-when-ambiguous (NEVER auto-select)
    stems = [g.stem for g in available]
    stems_str = ", ".join(stems[:20])
    if len(stems) > 20:
        stems_str += f" ... and {len(stems) - 20} more"
    print(
        f"Error: {len(available)} graphs found. Specify --graph <stem>.",
        file=sys.stderr,
    )
    print(f"Available: {stems_str}", file=sys.stderr)
    raise typer.Exit(code=1)


def _load_graph_info(info: GraphInfo) -> KnowledgeGraph:
    """Load a KnowledgeGraph from a GraphInfo entry."""
    store = GraphStore(info.dir_path.parent)
    try:
        return store.load(identity=info.identity)
    except CorruptGraphError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        print(
            f"Error: could not load graph {info.identity}: {exc}",
            file=sys.stderr,
        )
        raise typer.Exit(code=2) from exc


def _print_available_stems(available: list[GraphInfo]) -> None:
    """Print available graph stems to stderr."""
    if not available:
        return
    stems = [g.stem for g in available]
    stems_str = ", ".join(stems[:20])
    if len(stems) > 20:
        stems_str += f" ... and {len(stems) - 20} more"
    print(f"Available: {stems_str}", file=sys.stderr)
