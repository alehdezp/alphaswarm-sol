"""Tests for query routing, --graph flag, stdout contract, and exit codes.

Plan 3.1c.1-03: Query Routing Fix + --graph Flag.
Tests validate outcomes (exit codes, stdout content, stderr content),
not implementation details.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from alphaswarm_sol.kg.store import (
    EXPECTED_SCHEMA_VERSION,
    GraphInfo,
    GraphMetadata,
    SchemaVersionMismatchError,
    list_available_graphs,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_graph_dir(
    root: Path,
    identity: str,
    *,
    stem: str = "Token",
    source_contract: str = "Token.sol",
    contract_paths: list[str] | None = None,
    schema_version: int = 1,
    graph_format: str = "json",
    corrupt: bool = False,
    no_meta: bool = False,
    bad_meta_json: bool = False,
) -> Path:
    """Create a mock graph subdirectory with graph file and meta.json."""
    hash_dir = root / identity
    hash_dir.mkdir(parents=True, exist_ok=True)

    if not corrupt:
        # Write a minimal graph file
        ext = ".toon" if graph_format == "toon" else ".json"
        graph_file = hash_dir / f"graph{ext}"
        if graph_format == "json":
            graph_file.write_text(
                json.dumps({
                    "format": "alphaswarm-kg-v1",
                    "saved_at": "2026-01-01T00:00:00Z",
                    "graph": {"nodes": {}, "edges": {}},
                }),
                encoding="utf-8",
            )
        else:
            # Minimal toon: just write JSON for test simplicity
            graph_file.write_text(
                json.dumps({
                    "format": "alphaswarm-kg-v1",
                    "saved_at": "2026-01-01T00:00:00Z",
                    "graph": {"nodes": {}, "edges": {}},
                }),
                encoding="utf-8",
            )
    else:
        # Corrupt: .tmp file without completed graph
        tmp_file = hash_dir / "graph.json.tmp"
        tmp_file.write_text("{}", encoding="utf-8")

    if not no_meta and not bad_meta_json:
        meta = {
            "schema_version": schema_version,
            "built_at": "2026-01-01T00:00:00Z",
            "graph_hash": "abc123",
            "contract_paths": contract_paths or [f"contracts/{source_contract}"],
            "stem": stem,
            "source_contract": source_contract,
            "identity": identity,
            "slither_version": "0.10.0",
            "project_root_type": "git_toplevel",
        }
        (hash_dir / "meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
    elif bad_meta_json:
        (hash_dir / "meta.json").write_text("not valid json", encoding="utf-8")

    return hash_dir


@pytest.fixture
def graphs_root(tmp_path: Path) -> Path:
    """Return an empty graphs root directory."""
    root = tmp_path / ".vrs" / "graphs"
    root.mkdir(parents=True)
    return root


@pytest.fixture
def single_graph(graphs_root: Path) -> Path:
    """Create a single valid graph."""
    _make_graph_dir(graphs_root, "aabbccddeeff", stem="Token", source_contract="Token.sol")
    return graphs_root


@pytest.fixture
def two_graphs(graphs_root: Path) -> Path:
    """Create two valid graphs with different stems."""
    _make_graph_dir(graphs_root, "aabbccddeeff", stem="Token", source_contract="Token.sol")
    _make_graph_dir(
        graphs_root,
        "112233445566",
        stem="Vault",
        source_contract="Vault.sol",
        contract_paths=["contracts/Vault.sol"],
    )
    return graphs_root


@pytest.fixture
def ambiguous_stem_graphs(graphs_root: Path) -> Path:
    """Create two graphs with same stem (collision)."""
    _make_graph_dir(
        graphs_root,
        "aabbccddeeff",
        stem="Token",
        source_contract="Token.sol",
        contract_paths=["contracts/v1/Token.sol"],
    )
    _make_graph_dir(
        graphs_root,
        "112233445566",
        stem="Token",
        source_contract="Token.sol",
        contract_paths=["contracts/v2/Token.sol"],
    )
    return graphs_root


# ---------------------------------------------------------------------------
# list_available_graphs tests
# ---------------------------------------------------------------------------


class TestListAvailableGraphs:
    def test_empty_root(self, graphs_root: Path) -> None:
        result = list_available_graphs(graphs_root)
        assert result == []

    def test_nonexistent_root(self, tmp_path: Path) -> None:
        result = list_available_graphs(tmp_path / "nonexistent")
        assert result == []

    def test_single_graph(self, single_graph: Path) -> None:
        result = list_available_graphs(single_graph)
        assert len(result) == 1
        assert result[0].identity == "aabbccddeeff"
        assert result[0].stem == "Token"
        assert result[0].source_contract == "Token.sol"
        assert isinstance(result[0].meta, GraphMetadata)

    def test_two_graphs(self, two_graphs: Path) -> None:
        result = list_available_graphs(two_graphs)
        assert len(result) == 2
        stems = {g.stem for g in result}
        assert stems == {"Token", "Vault"}

    def test_skips_no_meta(self, graphs_root: Path) -> None:
        _make_graph_dir(graphs_root, "aabbccddeeff", no_meta=True)
        result = list_available_graphs(graphs_root)
        assert len(result) == 0

    def test_skips_bad_meta_json(self, graphs_root: Path) -> None:
        _make_graph_dir(graphs_root, "aabbccddeeff", bad_meta_json=True)
        result = list_available_graphs(graphs_root)
        assert len(result) == 0

    def test_schema_version_mismatch_raises(self, graphs_root: Path) -> None:
        _make_graph_dir(
            graphs_root,
            "aabbccddeeff",
            schema_version=99,
        )
        with pytest.raises(SchemaVersionMismatchError) as exc_info:
            list_available_graphs(graphs_root)
        assert "schema version mismatch" in str(exc_info.value)
        assert exc_info.value.found == 99
        assert exc_info.value.expected == EXPECTED_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Graph resolution tests (via graph_resolution module)
# ---------------------------------------------------------------------------


class TestGraphResolution:
    """Test resolve_and_load_graph() which is the shared entry point."""

    def test_no_graphs_exit_2(self, graphs_root: Path) -> None:
        """Zero graphs -> exit 2 with 'no graphs found' message."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph(None, graphs_root=graphs_root)
        assert exc_info.value.exit_code == 2

    def test_single_graph_auto_select(self, single_graph: Path) -> None:
        """One graph -> auto-selected successfully."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, info = resolve_and_load_graph(None, graphs_root=single_graph)
        assert graph_obj is not None
        assert info is not None
        assert info.stem == "Token"

    def test_multiple_graphs_no_flag_exit_1(self, two_graphs: Path) -> None:
        """2+ graphs without --graph -> exit 1 with available stems."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph(None, graphs_root=two_graphs)
        assert exc_info.value.exit_code == 1


# ---------------------------------------------------------------------------
# --graph flag tests
# ---------------------------------------------------------------------------


class TestGraphFlag:
    def test_graph_direct_path(self, single_graph: Path) -> None:
        """--graph with hash dir path -> loads correct graph."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        dir_path = str(single_graph / "aabbccddeeff")
        graph_obj, _ = resolve_and_load_graph(dir_path, graphs_root=single_graph)
        assert graph_obj is not None

    def test_graph_stem_unique(self, two_graphs: Path) -> None:
        """--graph with unique stem -> loads correct graph."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        graph_obj, info = resolve_and_load_graph("Token", graphs_root=two_graphs)
        assert graph_obj is not None
        assert info is not None
        assert info.stem == "Token"

    def test_graph_stem_ambiguous(self, ambiguous_stem_graphs: Path) -> None:
        """--graph with colliding stem -> exit 1 with disambiguation paths."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph("Token", graphs_root=ambiguous_stem_graphs)
        assert exc_info.value.exit_code == 1

    def test_graph_stem_nonexistent(self, two_graphs: Path) -> None:
        """--graph with unknown stem -> exit 1 with available graph list."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph("NonExistent", graphs_root=two_graphs)
        assert exc_info.value.exit_code == 1

    def test_graph_schema_version_mismatch(self, graphs_root: Path) -> None:
        """Wrong schema_version -> fail fast with error."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        _make_graph_dir(graphs_root, "aabbccddeeff", schema_version=99)

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph("Token", graphs_root=graphs_root)
        # SchemaVersionMismatchError causes exit 2 (graph infrastructure error)
        assert exc_info.value.exit_code == 2


# ---------------------------------------------------------------------------
# Stderr message content tests
# ---------------------------------------------------------------------------


class TestErrorMessages:
    """Verify error messages contain agent-actionable recovery commands."""

    def test_no_graphs_message(self, graphs_root: Path, capsys: pytest.CaptureFixture) -> None:
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit):
            resolve_and_load_graph(None, graphs_root=graphs_root)
        captured = capsys.readouterr()
        assert "no graphs found" in captured.err.lower()
        assert "alphaswarm build-kg" in captured.err

    def test_multiple_graphs_shows_stems(self, two_graphs: Path, capsys: pytest.CaptureFixture) -> None:
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit):
            resolve_and_load_graph(None, graphs_root=two_graphs)
        captured = capsys.readouterr()
        assert "Available:" in captured.err
        assert "Token" in captured.err
        assert "Vault" in captured.err

    def test_nonexistent_stem_shows_available(self, two_graphs: Path, capsys: pytest.CaptureFixture) -> None:
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit):
            resolve_and_load_graph("NonExistent", graphs_root=two_graphs)
        captured = capsys.readouterr()
        assert "no graph found for '--graph NonExistent'" in captured.err
        assert "alphaswarm build-kg" in captured.err
        assert "Available:" in captured.err

    def test_ambiguous_stem_shows_paths(
        self, ambiguous_stem_graphs: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit):
            resolve_and_load_graph("Token", graphs_root=ambiguous_stem_graphs)
        captured = capsys.readouterr()
        assert "ambiguous" in captured.err.lower()
        # Must include actual contract paths from meta.json for disambiguation
        assert "contracts/v1/Token.sol" in captured.err
        assert "contracts/v2/Token.sol" in captured.err


# ---------------------------------------------------------------------------
# Intent cli_mode tests (no silent degradation to "nodes")
# ---------------------------------------------------------------------------


class TestNoSilentDegradation:
    def test_cli_mode_default_is_pattern(self) -> None:
        """In cli_mode, query_kind defaults to 'pattern', not 'nodes'."""
        from alphaswarm_sol.queries.intent import parse_intent

        # A generic query with no explicit tokens
        intent = parse_intent("show me everything", cli_mode=True)
        # In cli_mode, when nothing specific matches, default is "pattern"
        # (preventing silent degradation to "nodes")
        assert intent.query_kind != "nodes"

    def test_api_mode_default_is_nodes(self) -> None:
        """Without cli_mode, query_kind still defaults to 'nodes' for API compat."""
        from alphaswarm_sol.queries.intent import parse_intent

        # Use a query that won't match VQL grammar or specific tokens
        intent = parse_intent("some random text here xyzzy", cli_mode=False)
        assert intent.query_kind == "nodes"

    def test_explicit_edge_query_works(self) -> None:
        """Edge queries still work in cli_mode."""
        from alphaswarm_sol.queries.intent import parse_intent

        # Use JSON input to explicitly set query_kind to "edges"
        intent = parse_intent('{"query_kind": "edges", "edge_types": ["CALLS"]}', cli_mode=True)
        assert intent.query_kind == "edges"

    def test_explicit_pattern_query_works(self) -> None:
        """Pattern queries work in cli_mode."""
        from alphaswarm_sol.queries.intent import parse_intent

        intent = parse_intent("pattern:reentrancy-001", cli_mode=True)
        assert intent.query_kind == "pattern"


# ---------------------------------------------------------------------------
# Stdout contract tests
# ---------------------------------------------------------------------------

RESULT_HEADER_REGEX = re.compile(r"^# result: graph_nodes=\d+ matches=\d+$")


class TestStdoutContract:
    """Test the structured stdout output contract for query command."""

    def test_result_header_regex(self) -> None:
        """Verify the regex matches valid headers."""
        assert RESULT_HEADER_REGEX.match("# result: graph_nodes=42 matches=0")
        assert RESULT_HEADER_REGEX.match("# result: graph_nodes=0 matches=0")
        assert RESULT_HEADER_REGEX.match("# result: graph_nodes=1234 matches=567")
        assert not RESULT_HEADER_REGEX.match("# result: graph_nodes=abc matches=0")
        assert not RESULT_HEADER_REGEX.match("# Result: graph_nodes=42 matches=0")
        assert not RESULT_HEADER_REGEX.match("result: graph_nodes=42 matches=0")


# ---------------------------------------------------------------------------
# Exit code semantics tests
# ---------------------------------------------------------------------------


class TestExitCodes:
    """Test exit code semantics: 0=success, 1=routing error, 2=graph error."""

    def test_exit_2_no_graphs(self, graphs_root: Path) -> None:
        """No graphs -> exit 2 (graph infrastructure error)."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph(None, graphs_root=graphs_root)
        assert exc_info.value.exit_code == 2

    def test_exit_1_ambiguous(self, two_graphs: Path) -> None:
        """Ambiguous (2+ graphs, no --graph) -> exit 1 (routing error)."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph(None, graphs_root=two_graphs)
        assert exc_info.value.exit_code == 1

    def test_exit_1_nonexistent_stem(self, two_graphs: Path) -> None:
        """Non-existent stem -> exit 1 (routing error)."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph("Bogus", graphs_root=two_graphs)
        assert exc_info.value.exit_code == 1

    def test_exit_2_corrupt_graph_path(self, graphs_root: Path) -> None:
        """Direct path to non-existent file -> exit 2 (graph error)."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            resolve_and_load_graph(
                str(graphs_root / "nonexistent" / "graph.json"),
                graphs_root=graphs_root,
            )
        assert exc_info.value.exit_code == 2

    def test_exit_0_success(self, single_graph: Path) -> None:
        """Successful resolution -> no exit (returns normally)."""
        from alphaswarm_sol.cli.graph_resolution import resolve_and_load_graph

        # Should not raise
        graph_obj, info = resolve_and_load_graph(None, graphs_root=single_graph)
        assert graph_obj is not None


# ---------------------------------------------------------------------------
# GraphInfo dataclass tests
# ---------------------------------------------------------------------------


class TestGraphInfo:
    def test_graph_info_fields(self) -> None:
        meta = GraphMetadata(
            schema_version=1,
            built_at="2026-01-01T00:00:00Z",
            graph_hash="abc",
            contract_paths=["contracts/Token.sol"],
            stem="Token",
            source_contract="Token.sol",
            identity="aabbccddeeff",
            slither_version="0.10.0",
            project_root_type="git_toplevel",
        )
        info = GraphInfo(
            identity="aabbccddeeff",
            stem="Token",
            source_contract="Token.sol",
            dir_path=Path("/tmp/graphs/aabbccddeeff"),
            meta=meta,
        )
        assert info.identity == "aabbccddeeff"
        assert info.stem == "Token"
        assert info.source_contract == "Token.sol"


# ---------------------------------------------------------------------------
# SchemaVersionMismatchError tests
# ---------------------------------------------------------------------------


class TestSchemaVersionMismatchError:
    def test_error_message(self) -> None:
        err = SchemaVersionMismatchError(
            identity="aabbccddeeff", found=99, expected=1
        )
        assert "schema version mismatch" in str(err)
        assert "aabbccddeeff" in str(err)
        assert "99" in str(err)
        assert "1" in str(err)

    def test_attributes(self) -> None:
        err = SchemaVersionMismatchError(
            identity="aabbccddeeff", found=2, expected=1
        )
        assert err.identity == "aabbccddeeff"
        assert err.found == 2
        assert err.expected == 1
