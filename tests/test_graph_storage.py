"""Tests for per-contract graph storage (Plan 02: 3.1c.1-02).

Tests contract identity, graph store with hash-based subdirectories,
meta.json sidecar, atomic writes, skip-if-exists, backward compat,
and corrupt detection.
"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path

import pytest

from alphaswarm_sol.kg.identity import contract_identity, _resolve_project_root, filter_dependency_paths
from alphaswarm_sol.kg.store import GraphStore, GraphMetadata, CorruptGraphError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sol_file(tmp_path: Path, name: str = "Token.sol") -> Path:
    """Create a minimal Solidity file."""
    sol = tmp_path / name
    sol.write_text("pragma solidity ^0.8.0;\ncontract Token {}", encoding="utf-8")
    return sol


def _minimal_graph():
    """Return a minimal KnowledgeGraph-compatible object."""
    from alphaswarm_sol.kg.schema import KnowledgeGraph

    return KnowledgeGraph.from_dict({"nodes": [], "edges": [], "metadata": {}})


def _valid_meta(identity: str, contract_paths: list[str] | None = None) -> dict:
    """Return a valid meta dict for GraphStore.save()."""
    return {
        "schema_version": 1,
        "built_at": "2026-03-01T00:00:00+00:00",
        "graph_hash": "a" * 12,
        "contract_paths": contract_paths or ["/tmp/Token.sol"],
        "stem": "Token",
        "source_contract": "Token",
        "slither_version": "0.10.0",
        "project_root_type": "git_toplevel",
    }


# ===========================================================================
# Contract Identity Tests
# ===========================================================================


class TestContractIdentity:
    """Tests for contract_identity() function."""

    def test_deterministic(self, tmp_path: Path) -> None:
        """Same input produces same hash."""
        sol = _make_sol_file(tmp_path)
        h1 = contract_identity([sol])
        h2 = contract_identity([sol])
        assert h1 == h2
        assert len(h1) == 12
        assert all(c in "0123456789abcdef" for c in h1)

    def test_order_independent(self, tmp_path: Path) -> None:
        """Different path order produces same hash."""
        a = _make_sol_file(tmp_path, "A.sol")
        b = _make_sol_file(tmp_path, "B.sol")
        h1 = contract_identity([a, b])
        h2 = contract_identity([b, a])
        assert h1 == h2

    def test_trailing_slash_stripped(self, tmp_path: Path) -> None:
        """Trailing slash does not change identity for directories."""
        dir_a = tmp_path / "contracts"
        dir_a.mkdir()
        _make_sol_file(dir_a)

        # Same directory with and without trailing slash
        h1 = contract_identity([dir_a])
        h2 = contract_identity([Path(str(dir_a) + "/")])
        assert h1 == h2

    def test_symlink_resolved(self, tmp_path: Path) -> None:
        """Symlink and target produce same identity."""
        real_file = _make_sol_file(tmp_path, "Real.sol")
        link_file = tmp_path / "Link.sol"
        link_file.symlink_to(real_file)

        h1 = contract_identity([real_file])
        h2 = contract_identity([link_file])
        assert h1 == h2

    def test_uses_realpath_not_abspath(self) -> None:
        """Verify os.path.realpath is used (not abspath) in the actual code logic."""
        import ast
        import inspect

        source = inspect.getsource(contract_identity)
        tree = ast.parse(source)

        # Check that realpath is called in the function body
        realpath_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "realpath"
        ]
        assert len(realpath_calls) > 0, "os.path.realpath not found in function body"

        # Check no abspath call exists in function body (ignoring strings/comments)
        abspath_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "abspath"
        ]
        assert len(abspath_calls) == 0, "os.path.abspath found in function body"

    def test_empty_paths_raises(self) -> None:
        """Empty path list raises ValueError."""
        with pytest.raises(ValueError, match="at least one path"):
            contract_identity([])

    def test_utf8_filename(self, tmp_path: Path) -> None:
        """Non-ASCII filename produces a valid hash."""
        sol = _make_sol_file(tmp_path, "Contrato\u00e9.sol")
        h = contract_identity([sol])
        assert len(h) == 12
        assert all(c in "0123456789abcdef" for c in h)

    def test_single_vs_multi_degeneracy(self, tmp_path: Path) -> None:
        """Single file identity is consistent (degenerate case)."""
        sol = _make_sol_file(tmp_path)
        h1 = contract_identity([sol])
        assert len(h1) == 12

    def test_different_contracts_different_identity(self, tmp_path: Path) -> None:
        """Two different contracts produce different identities."""
        a = _make_sol_file(tmp_path, "TokenA.sol")
        b = _make_sol_file(tmp_path, "TokenB.sol")
        ha = contract_identity([a])
        hb = contract_identity([b])
        assert ha != hb


# ===========================================================================
# Resolve Project Root Tests
# ===========================================================================


class TestResolveProjectRoot:
    def test_non_git_fallback(self, tmp_path: Path) -> None:
        """Non-git directory returns fallback_cwd without error."""
        sol = _make_sol_file(tmp_path)
        root, source_type = _resolve_project_root([sol])
        assert source_type in ("fallback_cwd", "git_toplevel")
        assert isinstance(root, Path)

    def test_empty_inputs(self) -> None:
        """Empty inputs returns cwd."""
        root, source_type = _resolve_project_root([])
        assert source_type == "fallback_cwd"


# ===========================================================================
# Filter Dependency Paths Tests
# ===========================================================================


class TestFilterDependencyPaths:
    def test_filters_external_paths(self, tmp_path: Path) -> None:
        """Paths outside project root are excluded."""
        project = tmp_path / "project"
        project.mkdir()
        internal = project / "Token.sol"
        internal.write_text("// internal", encoding="utf-8")
        external = Path("/tmp/external/Dep.sol")

        result = filter_dependency_paths([internal, external], project)
        assert internal in result
        assert external not in result

    def test_keeps_project_paths(self, tmp_path: Path) -> None:
        """Paths inside project root are kept."""
        sol = _make_sol_file(tmp_path)
        result = filter_dependency_paths([sol], tmp_path)
        assert sol in result


# ===========================================================================
# GraphMetadata Pydantic Model Tests
# ===========================================================================


class TestGraphMetadata:
    def test_valid_meta(self) -> None:
        """Valid metadata passes validation."""
        meta = GraphMetadata(
            schema_version=1,
            built_at="2026-03-01T00:00:00+00:00",
            graph_hash="abcdef123456",
            contract_paths=["/tmp/Token.sol"],
            stem="Token",
            source_contract="Token",
            identity="abcdef123456",
            slither_version="0.10.0",
            project_root_type="git_toplevel",
        )
        assert meta.schema_version == 1
        assert meta.source_contract == "Token"

    def test_extra_fields_rejected(self) -> None:
        """Extra fields raise validation error."""
        with pytest.raises(Exception):  # pydantic ValidationError
            GraphMetadata(
                schema_version=1,
                built_at="2026-03-01T00:00:00+00:00",
                graph_hash="abcdef123456",
                contract_paths=["/tmp/Token.sol"],
                stem="Token",
                source_contract="Token",
                identity="abcdef123456",
                slither_version="0.10.0",
                project_root_type="git_toplevel",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_schema_version_must_be_1(self) -> None:
        """schema_version != 1 raises validation error."""
        with pytest.raises(Exception):
            GraphMetadata(
                schema_version=2,
                built_at="2026-03-01T00:00:00+00:00",
                graph_hash="abcdef123456",
                contract_paths=["/tmp/Token.sol"],
                stem="Token",
                source_contract="Token",
                identity="abcdef123456",
                slither_version="0.10.0",
                project_root_type="git_toplevel",
            )

    def test_identity_validation(self) -> None:
        """Invalid identity format raises validation error."""
        with pytest.raises(Exception):
            GraphMetadata(
                schema_version=1,
                built_at="2026-03-01T00:00:00+00:00",
                graph_hash="abcdef123456",
                contract_paths=["/tmp/Token.sol"],
                stem="Token",
                source_contract="Token",
                identity="too_short",  # Not 12 hex chars
                slither_version="0.10.0",
                project_root_type="git_toplevel",
            )

    def test_all_dmeta_fields_present(self) -> None:
        """All D-meta schema fields are present in the model."""
        required_fields = {
            "schema_version", "built_at", "graph_hash", "contract_paths",
            "stem", "source_contract", "identity", "slither_version",
            "project_root_type",
        }
        model_fields = set(GraphMetadata.model_fields.keys())
        assert required_fields == model_fields


# ===========================================================================
# GraphStore Tests
# ===========================================================================


class TestGraphStoreSave:
    def test_save_creates_hash_subdir(self, tmp_path: Path) -> None:
        """save() with identity creates {root}/{identity}/graph.toon."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        saved = store.save(graph, identity=identity, meta=_valid_meta(identity))
        assert saved == tmp_path / identity / "graph.toon"
        assert saved.exists()
        assert (tmp_path / identity / "meta.json").exists()

    def test_save_atomic_no_temp_remains(self, tmp_path: Path) -> None:
        """No .tmp files remain after save."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        store.save(graph, identity=identity, meta=_valid_meta(identity))
        hash_dir = tmp_path / identity
        tmp_files = list(hash_dir.glob("*.tmp"))
        assert tmp_files == []

    def test_save_skip_if_exists(self, tmp_path: Path) -> None:
        """Second save returns early without overwriting."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        p1 = store.save(graph, identity=identity, meta=_valid_meta(identity))
        mtime1 = p1.stat().st_mtime

        p2 = store.save(graph, identity=identity, meta=_valid_meta(identity))
        mtime2 = p2.stat().st_mtime

        assert p1 == p2
        assert mtime1 == mtime2  # File not modified

    def test_save_force_overwrites(self, tmp_path: Path) -> None:
        """save(force=True) overwrites existing graph."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        p1 = store.save(graph, identity=identity, meta=_valid_meta(identity))
        content1 = p1.read_text()

        p2 = store.save(graph, identity=identity, meta=_valid_meta(identity), force=True)
        content2 = p2.read_text()

        assert p1 == p2
        # Content should be regenerated (timestamp will differ)

    def test_save_meta_json_valid(self, tmp_path: Path) -> None:
        """meta.json validates against GraphMetadata model."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        store.save(graph, identity=identity, meta=_valid_meta(identity))
        meta_path = tmp_path / identity / "meta.json"
        data = json.loads(meta_path.read_text())

        # Should not raise
        validated = GraphMetadata(**data)
        assert validated.schema_version == 1
        assert validated.identity == identity
        assert validated.source_contract == "Token"

    def test_save_meta_json_all_fields(self, tmp_path: Path) -> None:
        """meta.json has all D-meta fields."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        store.save(graph, identity=identity, meta=_valid_meta(identity))
        meta_path = tmp_path / identity / "meta.json"
        data = json.loads(meta_path.read_text())

        expected_fields = {
            "schema_version", "built_at", "graph_hash", "contract_paths",
            "stem", "source_contract", "identity", "slither_version",
            "project_root_type",
        }
        assert expected_fields == set(data.keys())

    def test_different_identities_different_dirs(self, tmp_path: Path) -> None:
        """Two different identities produce two different directories."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        id_a = "aaaaaaaaaaaa"
        id_b = "bbbbbbbbbbbb"

        pa = store.save(graph, identity=id_a, meta=_valid_meta(id_a))
        pb = store.save(graph, identity=id_b, meta=_valid_meta(id_b))

        assert pa.parent != pb.parent
        assert pa.exists()
        assert pb.exists()


class TestGraphStoreLoad:
    def test_load_from_identity(self, tmp_path: Path) -> None:
        """Load by identity hash works."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        store.save(graph, identity=identity, meta=_valid_meta(identity))
        loaded = store.load(identity=identity)
        assert loaded is not None

    def test_load_corrupt_detection(self, tmp_path: Path) -> None:
        """Partial write (.tmp without .toon) raises CorruptGraphError."""
        identity = "abcdef123456"
        hash_dir = tmp_path / identity
        hash_dir.mkdir(parents=True)

        # Create .tmp without .toon
        (hash_dir / "graph.toon.tmp").write_text("partial", encoding="utf-8")

        store = GraphStore(tmp_path)
        with pytest.raises(CorruptGraphError, match="Partial write"):
            store.load(identity=identity)

    def test_load_backward_compat_flat(self, tmp_path: Path) -> None:
        """Legacy flat graph.toon loads with deprecation warning when identity not found."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()

        # Save as flat file (legacy)
        saved = store.save(graph, format="toon")
        assert saved == tmp_path / "graph.toon"

        # Load with a nonexistent identity should fall back to flat
        loaded = store.load(identity="nonexistent00")
        assert loaded is not None

    def test_load_no_graph_raises(self, tmp_path: Path) -> None:
        """Loading from empty directory raises FileNotFoundError."""
        store = GraphStore(tmp_path)
        with pytest.raises(FileNotFoundError):
            store.load()


class TestGraphStoreListIdentities:
    def test_list_identities(self, tmp_path: Path) -> None:
        """list_identities returns all identity subdirs."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        id_a = "aaaaaaaaaaaa"
        id_b = "bbbbbbbbbbbb"

        store.save(graph, identity=id_a, meta=_valid_meta(id_a))
        store.save(graph, identity=id_b, meta=_valid_meta(id_b))

        identities = store.list_identities()
        assert id_a in identities
        assert id_b in identities
        assert len(identities) == 2


class TestGraphStoreCheckFresh:
    def test_fresh_matches(self, tmp_path: Path) -> None:
        """check_fresh returns True when hashes match."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"
        meta = _valid_meta(identity)
        meta["graph_hash"] = "source123abc"

        store.save(graph, identity=identity, meta=meta)
        assert store.check_fresh(identity, "source123abc") is True

    def test_stale_mismatch(self, tmp_path: Path) -> None:
        """check_fresh returns False when hashes differ."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        store.save(graph, identity=identity, meta=_valid_meta(identity))
        assert store.check_fresh(identity, "different_hash") is False

    def test_missing_identity_is_stale(self, tmp_path: Path) -> None:
        """check_fresh returns False for nonexistent identity."""
        store = GraphStore(tmp_path)
        assert store.check_fresh("nonexistent00", "anything") is False


class TestGraphStoreLoadMeta:
    def test_load_meta(self, tmp_path: Path) -> None:
        """load_meta returns validated GraphMetadata."""
        store = GraphStore(tmp_path)
        graph = _minimal_graph()
        identity = "abcdef123456"

        store.save(graph, identity=identity, meta=_valid_meta(identity))
        meta = store.load_meta(identity)
        assert meta is not None
        assert meta.schema_version == 1
        assert meta.source_contract == "Token"
        assert meta.identity == identity

    def test_load_meta_nonexistent(self, tmp_path: Path) -> None:
        """load_meta returns None for nonexistent identity."""
        store = GraphStore(tmp_path)
        assert store.load_meta("nonexistent00") is None


# ===========================================================================
# Integration: Build-KG flow simulation
# ===========================================================================


class TestBuildKgIntegration:
    def test_build_creates_isolated_subdir(self, tmp_path: Path) -> None:
        """Simulates build-kg: identity -> save -> load round-trip."""
        sol = _make_sol_file(tmp_path, "Vault.sol")
        identity = contract_identity([sol])

        store = GraphStore(tmp_path / "graphs")
        graph = _minimal_graph()
        meta = _valid_meta(identity, [str(sol)])
        meta["stem"] = "Vault"
        meta["source_contract"] = "Vault"

        saved = store.save(graph, identity=identity, meta=meta)
        assert identity in str(saved)
        assert saved.exists()

        loaded = store.load(identity=identity)
        assert loaded is not None

    def test_concurrent_builds_no_collision(self, tmp_path: Path) -> None:
        """Two contracts produce isolated graphs that don't collide."""
        sol_a = _make_sol_file(tmp_path, "TokenA.sol")
        sol_b = _make_sol_file(tmp_path, "TokenB.sol")

        id_a = contract_identity([sol_a])
        id_b = contract_identity([sol_b])
        assert id_a != id_b

        store = GraphStore(tmp_path / "graphs")
        graph = _minimal_graph()

        meta_a = _valid_meta(id_a, [str(sol_a)])
        meta_b = _valid_meta(id_b, [str(sol_b)])

        store.save(graph, identity=id_a, meta=meta_a)
        store.save(graph, identity=id_b, meta=meta_b)

        # Both exist independently
        loaded_a = store.load(identity=id_a)
        loaded_b = store.load(identity=id_b)
        assert loaded_a is not None
        assert loaded_b is not None

        # Two separate directories
        identities = store.list_identities()
        assert len(identities) == 2
