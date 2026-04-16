"""Framework pre-validation for Plan 3.1c.1-04 CLI Isolation Smoke Tests.

Validates that testing infrastructure works BEFORE spawning agents.
Each test targets a specific component: WorkspaceManager, TeamManager,
EvaluationRunner, and session binary freshness.

If ANY pre-validation test fails, agent spawning (Tasks 3-5) must NOT proceed.
Failure messages identify WHICH component failed for unambiguous diagnosis.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.workflow_harness.lib.workspace import WorkspaceManager
from tests.workflow_harness.lib.team_manager import TeamManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_CONTRACTS = PROJECT_ROOT / "tests" / "contracts"


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Create a minimal temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    # Copy a small contract for workspace testing
    src = TEST_CONTRACTS / "CrossFunctionReentrancy.sol"
    if src.exists():
        contracts_dir = ws / "contracts"
        contracts_dir.mkdir()
        shutil.copy2(src, contracts_dir / "CrossFunctionReentrancy.sol")
    return ws


# ---------------------------------------------------------------------------
# (a) WorkspaceManager validation
# ---------------------------------------------------------------------------


class TestWorkspaceManagerPreValidation:
    """Verify WorkspaceManager can create/verify/destroy workspaces."""

    def test_workspace_setup_creates_observation_dir(self, tmp_workspace: Path) -> None:
        """WorkspaceManager.setup() creates .vrs/observations/ directory."""
        mgr = WorkspaceManager(tmp_workspace)
        ws = mgr.setup(tmp_workspace)

        obs_dir = ws / ".vrs" / "observations"
        assert obs_dir.is_dir(), (
            f"COMPONENT FAILURE: WorkspaceManager — "
            f".vrs/observations/ not created at {obs_dir}"
        )

    def test_workspace_setup_creates_hooks(self, tmp_workspace: Path) -> None:
        """WorkspaceManager.setup() installs .claude/settings.json."""
        mgr = WorkspaceManager(tmp_workspace)
        ws = mgr.setup(tmp_workspace)

        settings_path = ws / ".claude" / "settings.json"
        assert settings_path.exists(), (
            "COMPONENT FAILURE: WorkspaceManager — "
            ".claude/settings.json not created"
        )
        data = json.loads(settings_path.read_text())
        assert "hooks" in data, (
            "COMPONENT FAILURE: WorkspaceManager — "
            "settings.json missing 'hooks' key"
        )

    def test_workspace_cleanup_removes_testing_dir(self, tmp_workspace: Path) -> None:
        """WorkspaceManager.cleanup() removes .vrs/testing/ artifacts."""
        mgr = WorkspaceManager(tmp_workspace)
        ws = mgr.setup(tmp_workspace)

        # Create .vrs/testing/ with dummy data
        testing_dir = ws / ".vrs" / "testing"
        testing_dir.mkdir(parents=True, exist_ok=True)
        (testing_dir / "session.json").write_text("{}")

        mgr.cleanup(ws)
        assert not testing_dir.exists(), (
            "COMPONENT FAILURE: WorkspaceManager — "
            ".vrs/testing/ not cleaned up"
        )

    @pytest.mark.skipif(
        not shutil.which("jj"),
        reason="jj not installed — reduced isolation (git worktree fallback)",
    )
    def test_jj_workspace_create_and_forget(self) -> None:
        """WorkspaceManager can create and forget a Jujutsu workspace."""
        mgr = WorkspaceManager(PROJECT_ROOT)
        workspace_name = "prevalidation-smoke"

        try:
            ws_path = mgr.create_workspace(workspace_name, source_dir=PROJECT_ROOT)
            assert ws_path.exists(), (
                f"COMPONENT FAILURE: WorkspaceManager — "
                f"Jujutsu workspace not created at {ws_path}"
            )
        finally:
            mgr.forget_workspace(workspace_name)
            # Clean up the workspace directory
            ws_dir = PROJECT_ROOT / workspace_name
            if ws_dir.exists():
                shutil.rmtree(ws_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# (b) TeamManager validation
# ---------------------------------------------------------------------------


class TestTeamManagerPreValidation:
    """Verify TeamManager lifecycle: create, spawn, observe, destroy."""

    def test_team_create_and_delete(self, tmp_workspace: Path) -> None:
        """TeamManager creates and deletes a team cleanly."""
        with TeamManager(tmp_workspace, "prevalidation-team") as tm:
            team_name = tm.create_team("Pre-validation smoke test")
            assert tm.active, (
                "COMPONENT FAILURE: TeamManager — "
                "team not active after create_team()"
            )
            assert team_name == "prevalidation-team"
        # After context manager exit, team should be inactive
        assert not tm.active, (
            "COMPONENT FAILURE: TeamManager — "
            "team still active after context manager exit"
        )

    def test_team_spawn_and_observe(self, tmp_workspace: Path) -> None:
        """TeamManager spawns teammate and builds observation."""
        with TeamManager(tmp_workspace, "prevalidation-obs") as tm:
            tm.create_team("Observation test")
            agent_id = tm.spawn_teammate("echo-agent", "general-purpose", "Test echo")

            assert agent_id, (
                "COMPONENT FAILURE: TeamManager — "
                "spawn_teammate returned empty agent_id"
            )

            tm.send_message("echo-agent", "ping")
            obs = tm.get_team_observation()

            assert obs is not None, (
                "COMPONENT FAILURE: TeamManager — "
                "get_team_observation() returned None"
            )
            assert len(obs.agents) == 1, (
                "COMPONENT FAILURE: TeamManager — "
                f"expected 1 agent in observation, got {len(obs.agents)}"
            )

    def test_team_duplicate_spawn_rejected(self, tmp_workspace: Path) -> None:
        """TeamManager rejects duplicate teammate names."""
        with TeamManager(tmp_workspace, "prevalidation-dup") as tm:
            tm.create_team("Duplicate test")
            tm.spawn_teammate("agent-a", "general-purpose", "First agent")

            with pytest.raises(ValueError, match="already exists"):
                tm.spawn_teammate("agent-a", "general-purpose", "Duplicate")


# ---------------------------------------------------------------------------
# (c) EvaluationRunner validation
# ---------------------------------------------------------------------------


class TestEvaluationRunnerPreValidation:
    """Verify EvaluationRunner pipeline completes on synthetic input."""

    def test_pipeline_completes_on_synthetic_input(self, tmp_path: Path) -> None:
        """EvaluationRunner runs pipeline without error on minimal input."""
        from alphaswarm_sol.testing.evaluation.models import RunMode
        from tests.workflow_harness.lib.evaluation_runner import (
            EvaluationRunner,
            JSONFileStore,
        )

        store = JSONFileStore(tmp_path / "eval_store")
        runner = EvaluationRunner(
            store=store,
            run_mode=RunMode.SIMULATED,
        )

        # Minimal synthetic input — enough to exercise the pipeline
        from tests.workflow_harness.lib.output_collector import CollectedOutput

        synthetic = CollectedOutput(
            scenario_name="prevalidation-synthetic",
            run_id="prevalidation-001",
            tool_sequence=["Bash", "Bash"],
        )

        result = runner.run(
            scenario_name="prevalidation-synthetic",
            workflow_id="prevalidation",
            collected_output=synthetic,
        )

        assert result is not None, (
            "COMPONENT FAILURE: EvaluationRunner — "
            "run() returned None"
        )
        assert result.scenario_name == "prevalidation-synthetic", (
            "COMPONENT FAILURE: EvaluationRunner — "
            f"scenario_name mismatch: {result.scenario_name}"
        )

    def test_pipeline_health_stages(self, tmp_path: Path) -> None:
        """EvaluationRunner pipeline health tracks completed stages."""
        from alphaswarm_sol.testing.evaluation.models import RunMode
        from tests.workflow_harness.lib.evaluation_runner import (
            EvaluationRunner,
            JSONFileStore,
        )

        store = JSONFileStore(tmp_path / "eval_store")
        runner = EvaluationRunner(store=store, run_mode=RunMode.SIMULATED)

        from tests.workflow_harness.lib.output_collector import CollectedOutput

        synthetic = CollectedOutput(
            scenario_name="health-check",
            run_id="health-001",
            tool_sequence=[],
        )

        result = runner.run(
            scenario_name="health-check",
            workflow_id="prevalidation",
            collected_output=synthetic,
        )

        assert result.pipeline_health is not None, (
            "COMPONENT FAILURE: EvaluationRunner — "
            "pipeline_health is None"
        )
        assert len(result.pipeline_health.stages_completed) > 0, (
            "COMPONENT FAILURE: EvaluationRunner — "
            "no pipeline stages completed"
        )


# ---------------------------------------------------------------------------
# (d) Session binary freshness
# ---------------------------------------------------------------------------


class TestSessionBinaryFreshness:
    """Verify Claude Code session binary exists (per TESTING-FRAMEWORK.md F1)."""

    def test_claude_binary_exists(self) -> None:
        """Claude Code binary is on PATH."""
        claude_path = shutil.which("claude")
        assert claude_path is not None, (
            "COMPONENT FAILURE: Session Binary — "
            "claude not found on PATH. Is Claude Code installed?"
        )

    def test_session_binary_version_directory(self) -> None:
        """Claude Code versions directory has at least one version."""
        if platform.system() != "Darwin":
            pytest.skip("macOS-specific path check")

        versions_dir = Path.home() / ".local" / "share" / "claude" / "versions"
        if not versions_dir.exists():
            pytest.skip("Claude Code versions directory not found")

        versions = list(versions_dir.iterdir())
        assert len(versions) > 0, (
            "COMPONENT FAILURE: Session Binary — "
            f"no versions found in {versions_dir}. "
            "STALE SESSION — restart required."
        )

    def test_claude_binary_responds(self) -> None:
        """Claude Code binary executes and returns version."""
        claude_bin = shutil.which("claude")
        if not claude_bin:
            pytest.skip("claude not on PATH")

        result = subprocess.run(
            [claude_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            "COMPONENT FAILURE: Session Binary — "
            f"claude --version failed with exit {result.returncode}: "
            f"{result.stderr.strip()}"
        )
        assert result.stdout.strip(), (
            "COMPONENT FAILURE: Session Binary — "
            "claude --version returned empty output"
        )
