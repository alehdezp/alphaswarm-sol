"""Integration tests for alphaswarm build-kg CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app
from alphaswarm_sol.kg.toon import toon_loads

runner = CliRunner()

# Path to test contracts
CONTRACTS_DIR = Path(__file__).parent / "contracts"


def _find_graph_file(root: Path, ext: str = ".toon") -> Path | None:
    """Find graph file in identity-based subdir or flat root."""
    # Check identity subdirs first
    for entry in sorted(root.iterdir()) if root.exists() else []:
        if entry.is_dir() and len(entry.name) == 12:
            candidate = entry / f"graph{ext}"
            if candidate.exists():
                return candidate
    # Flat fallback
    flat = root / f"graph{ext}"
    return flat if flat.exists() else None


class TestBuildKgFormat:
    """Test --format flag for build-kg command."""

    def test_default_format_produces_toon(self, tmp_path: Path) -> None:
        """Default format produces .toon file in identity subdir."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path)]
        )

        assert result.exit_code == 0
        toon_file = _find_graph_file(tmp_path, ".toon")
        assert toon_file is not None, f"No graph.toon found under {tmp_path}"
        json_file = _find_graph_file(tmp_path, ".json")
        assert json_file is None

    def test_explicit_format_toon(self, tmp_path: Path) -> None:
        """Explicit --format toon produces .toon file."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app,
            ["build-kg", str(contract), "--out", str(tmp_path), "--format", "toon"],
        )

        assert result.exit_code == 0
        toon_file = _find_graph_file(tmp_path, ".toon")
        assert toon_file is not None

    def test_format_json_produces_json(self, tmp_path: Path) -> None:
        """--format json produces .json file."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app,
            ["build-kg", str(contract), "--out", str(tmp_path), "--format", "json"],
        )

        assert result.exit_code == 0
        json_file = _find_graph_file(tmp_path, ".json")
        assert json_file is not None
        toon_file = _find_graph_file(tmp_path, ".toon")
        assert toon_file is None

    def test_json_file_is_valid_json(self, tmp_path: Path) -> None:
        """JSON output is valid JSON."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        runner.invoke(
            app,
            ["build-kg", str(contract), "--out", str(tmp_path), "--format", "json"],
        )

        json_file = _find_graph_file(tmp_path, ".json")
        assert json_file is not None
        content = json_file.read_text()
        data = json.loads(content)  # Should not raise

        assert "format" in data
        assert "graph" in data

    def test_toon_file_is_valid_toon(self, tmp_path: Path) -> None:
        """TOON output is valid TOON."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        runner.invoke(
            app,
            ["build-kg", str(contract), "--out", str(tmp_path), "--format", "toon"],
        )

        toon_file = _find_graph_file(tmp_path, ".toon")
        assert toon_file is not None
        content = toon_file.read_text()
        data = toon_loads(content)  # Should not raise

        assert "format" in data
        assert "graph_json" in data  # Graph stored as JSON string

    def test_invalid_format_value(self, tmp_path: Path) -> None:
        """Invalid format value shows error."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app,
            ["build-kg", str(contract), "--out", str(tmp_path), "--format", "xml"],
        )

        # Should fail with non-zero exit code
        assert result.exit_code != 0


class TestBuildKgOutput:
    """Test build-kg command output."""

    def test_output_shows_format_in_message(self, tmp_path: Path) -> None:
        """Output message shows format used."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path)]
        )

        assert "toon" in result.stdout.lower() or "graph.toon" in result.stdout

    def test_output_shows_json_format(self, tmp_path: Path) -> None:
        """Output message shows JSON format when used."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app,
            ["build-kg", str(contract), "--out", str(tmp_path), "--format", "json"],
        )

        assert "json" in result.stdout.lower() or "graph.json" in result.stdout

    def test_output_shows_identity(self, tmp_path: Path) -> None:
        """Output message shows identity hash."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path)]
        )

        assert result.exit_code == 0
        assert "identity:" in result.stdout


class TestBuildKgOverwrite:
    """Test build-kg --overwrite/--force with different formats."""

    def test_overwrite_toon(self, tmp_path: Path) -> None:
        """--overwrite replaces existing .toon file."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"

        # First build
        result1 = runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path), "--format", "toon"]
        )
        assert result1.exit_code == 0

        # Second build with overwrite (skips via skip-if-exists by default)
        result2 = runner.invoke(
            app,
            [
                "build-kg",
                str(contract),
                "--out",
                str(tmp_path),
                "--format",
                "toon",
                "--overwrite",
            ],
        )

        assert result2.exit_code == 0

    def test_no_overwrite_skips_existing(self, tmp_path: Path) -> None:
        """Without --overwrite, skip-if-exists returns same path."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"

        # First build
        result1 = runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path), "--format", "toon"]
        )
        assert result1.exit_code == 0

        # Second build without overwrite - should skip (identity-based caching)
        result2 = runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path), "--format", "toon"]
        )
        assert result2.exit_code == 0


class TestBuildKgMetaJson:
    """Test meta.json sidecar creation."""

    def test_meta_json_created(self, tmp_path: Path) -> None:
        """build-kg creates meta.json sidecar in identity subdir."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        result = runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path)]
        )
        assert result.exit_code == 0

        # Find meta.json in identity subdir
        meta_files = list(tmp_path.rglob("meta.json"))
        assert len(meta_files) == 1

        data = json.loads(meta_files[0].read_text())
        assert data["schema_version"] == 1
        assert data["source_contract"] is not None
        assert len(data["identity"]) == 12

    def test_meta_json_has_all_fields(self, tmp_path: Path) -> None:
        """meta.json contains all D-meta fields."""
        contract = CONTRACTS_DIR / "NoAccessGate.sol"
        runner.invoke(
            app, ["build-kg", str(contract), "--out", str(tmp_path)]
        )

        meta_files = list(tmp_path.rglob("meta.json"))
        assert len(meta_files) == 1

        data = json.loads(meta_files[0].read_text())
        expected_fields = {
            "schema_version", "built_at", "graph_hash", "contract_paths",
            "stem", "source_contract", "identity", "slither_version",
            "project_root_type",
        }
        assert expected_fields == set(data.keys())
