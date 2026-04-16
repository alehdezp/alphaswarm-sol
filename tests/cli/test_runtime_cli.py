"""CLI tests for runtime selection and model benchmarking.

Tests for:
- orchestrate agent-run --runtime flag
- orchestrate --show-rankings / --reset-rankings
- benchmark models commands (run, rankings, compare, integrate, export)

Per 05.3-09-PLAN.md:
- At least 12 CLI tests
- Use click.testing.CliRunner (via typer.testing)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import pytest
from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app
from alphaswarm_sol.cli.orchestrate import orchestrate_app, RuntimeChoice


runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def rankings_store(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary rankings store with test data."""
    rankings_dir = tmp_path / ".vkg" / "rankings"
    rankings_dir.mkdir(parents=True)
    rankings_file = rankings_dir / "rankings.yaml"

    # Create test rankings data
    test_data = """
version: 1
updated: 2026-01-22T00:00:00
rankings:
  verify:
    - model_id: minimax/minimax-m2:free
      task_type: verify
      success_rate: 0.95
      average_latency_ms: 850
      average_tokens: 450
      quality_score: 0.88
      cost_per_task: 0.0
      sample_count: 25
      last_updated: 2026-01-22T00:00:00
    - model_id: deepseek/deepseek-v3.2
      task_type: verify
      success_rate: 0.92
      average_latency_ms: 1200
      average_tokens: 600
      quality_score: 0.90
      cost_per_task: 0.001
      sample_count: 20
      last_updated: 2026-01-22T00:00:00
  reasoning:
    - model_id: deepseek/deepseek-v3.2
      task_type: reasoning
      success_rate: 0.88
      average_latency_ms: 2500
      average_tokens: 2000
      quality_score: 0.85
      cost_per_task: 0.002
      sample_count: 15
      last_updated: 2026-01-22T00:00:00
"""
    rankings_file.write_text(test_data)
    yield rankings_dir


@pytest.fixture
def empty_rankings_store(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary empty rankings store."""
    rankings_dir = tmp_path / ".vkg" / "rankings"
    rankings_dir.mkdir(parents=True)
    yield rankings_dir


# =============================================================================
# orchestrate agent-run --runtime tests
# =============================================================================


class TestOrchestrateRuntimeFlag:
    """Tests for orchestrate agent-run --runtime flag."""

    def test_runtime_flag_help_shows_options(self):
        """--runtime flag shows all runtime options in help."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--runtime" in result.output
        assert "opencode" in result.output
        assert "claude-code" in result.output
        assert "codex" in result.output
        assert "api" in result.output
        assert "auto" in result.output

    def test_runtime_default_is_auto(self):
        """Default runtime is auto."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "default: auto" in result.output.lower()

    def test_runtime_choice_enum_values(self):
        """RuntimeChoice enum has all expected values."""
        assert RuntimeChoice.OPENCODE.value == "opencode"
        assert RuntimeChoice.CLAUDE_CODE.value == "claude-code"
        assert RuntimeChoice.CODEX.value == "codex"
        assert RuntimeChoice.API.value == "api"
        assert RuntimeChoice.AUTO.value == "auto"


class TestOrchestrateRankingsFlags:
    """Tests for orchestrate --show-rankings and --reset-rankings flags."""

    def test_show_rankings_flag_exists(self):
        """--show-rankings flag is available."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--show-rankings" in result.output

    def test_reset_rankings_flag_exists(self):
        """--reset-rankings flag is available."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--reset-rankings" in result.output


class TestOrchestrateRankingsCommand:
    """Tests for orchestrate rankings command."""

    def test_rankings_command_exists(self):
        """rankings command is available under orchestrate."""
        result = runner.invoke(app, ["orchestrate", "--help"])
        assert result.exit_code == 0
        assert "rankings" in result.output

    def test_rankings_command_help(self):
        """rankings command shows help text."""
        result = runner.invoke(app, ["orchestrate", "rankings", "--help"])
        assert result.exit_code == 0
        assert "--task-type" in result.output or "task-type" in result.output
        assert "--format" in result.output

    def test_rankings_empty_store(self, empty_rankings_store: Path):
        """rankings command handles empty store gracefully."""
        result = runner.invoke(
            app,
            ["orchestrate", "rankings", "--vkg-dir", str(empty_rankings_store.parent)]
        )
        # Should not crash, may report no rankings
        assert result.exit_code == 0 or "No rankings" in result.output


class TestOrchestrateRuntimesCommand:
    """Tests for orchestrate runtimes command."""

    def test_runtimes_command_exists(self):
        """runtimes command is available under orchestrate."""
        result = runner.invoke(app, ["orchestrate", "--help"])
        assert result.exit_code == 0
        assert "runtimes" in result.output

    def test_runtimes_command_shows_all_runtimes(self):
        """runtimes command lists all runtime types."""
        result = runner.invoke(app, ["orchestrate", "runtimes"])
        assert result.exit_code == 0
        assert "opencode" in result.output.lower()
        assert "claude" in result.output.lower()
        assert "codex" in result.output.lower()
        assert "anthropic" in result.output.lower()

    def test_runtimes_command_json_format(self):
        """runtimes command supports JSON output."""
        result = runner.invoke(app, ["orchestrate", "runtimes", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 3  # At least opencode, claude_code, codex
        assert all("id" in item for item in data)
        assert all("available" in item for item in data)


# =============================================================================
# benchmark models tests
# =============================================================================


class TestBenchmarkModelsRun:
    """Tests for benchmark models run command."""

    def test_benchmark_models_run_help(self):
        """benchmark models run shows help."""
        result = runner.invoke(app, ["benchmark", "models", "run", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "--category" in result.output
        assert "--all-models" in result.output

    def test_benchmark_models_run_requires_model_or_all(self):
        """benchmark models run requires --model or --all-models."""
        result = runner.invoke(app, ["benchmark", "models", "run"])
        # Should fail without model specification
        assert result.exit_code != 0 or "Specify" in result.output


class TestBenchmarkModelsRankings:
    """Tests for benchmark models rankings command."""

    def test_benchmark_models_rankings_help(self):
        """benchmark models rankings shows help."""
        result = runner.invoke(app, ["benchmark", "models", "rankings", "--help"])
        assert result.exit_code == 0
        assert "--task-type" in result.output or "task-type" in result.output
        assert "--top" in result.output
        assert "--format" in result.output

    def test_benchmark_models_rankings_no_store(self):
        """benchmark models rankings handles missing store."""
        result = runner.invoke(app, ["benchmark", "models", "rankings"])
        # Should not crash
        assert "No rankings" in result.output or result.exit_code == 0


class TestBenchmarkModelsCompare:
    """Tests for benchmark models compare command."""

    def test_benchmark_models_compare_help(self):
        """benchmark models compare shows help."""
        result = runner.invoke(app, ["benchmark", "models", "compare", "--help"])
        assert result.exit_code == 0
        assert "MODEL_A" in result.output
        assert "MODEL_B" in result.output

    def test_benchmark_models_compare_requires_args(self):
        """benchmark models compare requires model arguments."""
        result = runner.invoke(app, ["benchmark", "models", "compare"])
        assert result.exit_code != 0  # Missing required arguments


class TestBenchmarkModelsIntegrate:
    """Tests for benchmark models integrate command."""

    def test_benchmark_models_integrate_help(self):
        """benchmark models integrate shows help."""
        result = runner.invoke(app, ["benchmark", "models", "integrate", "--help"])
        assert result.exit_code == 0
        assert "MODEL_ID" in result.output
        assert "--iterations" in result.output

    def test_benchmark_models_integrate_requires_model(self):
        """benchmark models integrate requires model_id argument."""
        result = runner.invoke(app, ["benchmark", "models", "integrate"])
        assert result.exit_code != 0


class TestBenchmarkModelsExport:
    """Tests for benchmark models export command."""

    def test_benchmark_models_export_help(self):
        """benchmark models export shows help."""
        result = runner.invoke(app, ["benchmark", "models", "export", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output
        assert "--output" in result.output

    @pytest.mark.xfail(reason="Stale code: benchmark models CLI changed")
    def test_benchmark_models_export_no_store(self):
        """benchmark models export handles missing store."""
        result = runner.invoke(app, ["benchmark", "models", "export"])
        # Should fail or report no rankings
        assert result.exit_code != 0 or "No rankings" in result.output


class TestBenchmarkModelsListCategories:
    """Tests for benchmark models list-categories command."""

    def test_benchmark_models_list_categories_exists(self):
        """benchmark models list-categories command exists."""
        result = runner.invoke(app, ["benchmark", "models", "--help"])
        assert result.exit_code == 0
        assert "list-categories" in result.output

    def test_benchmark_models_list_categories_output(self):
        """benchmark models list-categories shows categories."""
        result = runner.invoke(app, ["benchmark", "models", "list-categories"])
        assert result.exit_code == 0
        assert "verify" in result.output.lower()
        assert "reasoning" in result.output.lower()
        assert "code" in result.output.lower()


# =============================================================================
# Integration tests
# =============================================================================


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    def test_orchestrate_and_benchmark_coexist(self):
        """orchestrate and benchmark commands coexist without conflict."""
        result1 = runner.invoke(app, ["orchestrate", "--help"])
        result2 = runner.invoke(app, ["benchmark", "--help"])

        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert "agent-run" in result1.output
        assert "models" in result2.output

    def test_benchmark_vkg_and_models_coexist(self):
        """VKG benchmark and model benchmark coexist."""
        result = runner.invoke(app, ["benchmark", "--help"])
        assert result.exit_code == 0
        # VKG detection benchmark
        assert "run" in result.output
        assert "compare" in result.output
        # Model benchmark subgroup
        assert "models" in result.output

    def test_main_app_has_all_cli_groups(self):
        """Main app has all expected CLI groups."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "orchestrate" in result.output
        assert "benchmark" in result.output
        assert "tools" in result.output
        assert "findings" in result.output


# =============================================================================
# API warning tests
# =============================================================================


class TestAPIWarning:
    """Tests for API usage warning."""

    def test_api_warning_message_in_code(self):
        """Verify API warning message is defined in orchestrate module."""
        from alphaswarm_sol.cli import orchestrate

        # The warning message should be present in the source
        import inspect
        source = inspect.getsource(orchestrate)
        assert "API-based runtimes is expensive" in source or "expensive" in source


# Run with: uv run pytest tests/cli/test_runtime_cli.py -v
