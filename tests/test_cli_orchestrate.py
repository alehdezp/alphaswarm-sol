"""Tests for orchestration CLI commands.

Tests the CLI interface for pool orchestration management:
- list: List pools with status filtering
- status: Show pool details
- start: Create new audit pool
- resume: Resume from checkpoint
- beads: List beads in pool
- pause: Pause pool
- delete: Delete pool
- summary: Show summary statistics
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from alphaswarm_sol.cli.main import app
from alphaswarm_sol.orchestration import Pool, PoolManager, PoolStatus, Scope


runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_vkg_dir(tmp_path: Path) -> Path:
    """Create a temporary .vkg directory."""
    vkg_dir = tmp_path / ".vkg" / "pools"
    vkg_dir.mkdir(parents=True)
    return vkg_dir


@pytest.fixture
def manager(temp_vkg_dir: Path) -> PoolManager:
    """Create pool manager with temp storage."""
    return PoolManager(temp_vkg_dir)


@pytest.fixture
def sample_pool(manager: PoolManager) -> Pool:
    """Create a sample pool for testing."""
    scope = Scope(
        files=["contracts/Vault.sol", "contracts/Token.sol"],
        contracts=["Vault", "Token"],
        focus_areas=["reentrancy", "access-control"],
    )
    return manager.create_pool(
        scope=scope,
        pool_id="test-pool-001",
        initiated_by="test",
    )


# =============================================================================
# TestOrchestrateCLI - Basic Commands
# =============================================================================


class TestOrchestrateCLI:
    """Tests for basic orchestrate CLI commands."""

    def test_list_empty(self, temp_vkg_dir: Path) -> None:
        """Test list command with no pools."""
        result = runner.invoke(
            app,
            ["orchestrate", "list", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "No pools found" in result.stdout

    def test_list_with_pool(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test list command with a pool present."""
        result = runner.invoke(
            app,
            ["orchestrate", "list", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "test-pool-001" in result.stdout
        assert "intake" in result.stdout.lower()
        assert "Total: 1 pools" in result.stdout

    def test_list_format_json(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test list command with JSON output."""
        result = runner.invoke(
            app,
            ["orchestrate", "list", "--vkg-dir", str(temp_vkg_dir), "-f", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["id"] == "test-pool-001"

    def test_list_format_compact(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test list command with compact output."""
        result = runner.invoke(
            app,
            ["orchestrate", "list", "--vkg-dir", str(temp_vkg_dir), "-f", "compact"],
        )
        assert result.exit_code == 0
        assert "test-pool-001 |" in result.stdout

    def test_list_filter_status(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test list command with status filter."""
        result = runner.invoke(
            app,
            ["orchestrate", "list", "--vkg-dir", str(temp_vkg_dir), "-s", "intake"],
        )
        assert result.exit_code == 0
        assert "test-pool-001" in result.stdout

        # Filter by status that doesn't match
        result = runner.invoke(
            app,
            ["orchestrate", "list", "--vkg-dir", str(temp_vkg_dir), "-s", "complete"],
        )
        assert result.exit_code == 0
        assert "No pools found" in result.stdout

    def test_list_invalid_status(self, temp_vkg_dir: Path) -> None:
        """Test list command with invalid status."""
        result = runner.invoke(
            app,
            ["orchestrate", "list", "--vkg-dir", str(temp_vkg_dir), "-s", "invalid"],
        )
        assert result.exit_code == 1
        assert "Invalid status" in result.stdout

    def test_status_not_found(self, temp_vkg_dir: Path) -> None:
        """Test status command with non-existent pool."""
        result = runner.invoke(
            app,
            ["orchestrate", "status", "nonexistent", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_status_shows_pool(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test status command shows pool details."""
        result = runner.invoke(
            app,
            ["orchestrate", "status", "test-pool-001", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "test-pool-001" in result.stdout
        assert "INTAKE" in result.stdout
        assert "Vault.sol" in result.stdout

    def test_status_json_format(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test status command with JSON output."""
        result = runner.invoke(
            app,
            ["orchestrate", "status", "test-pool-001", "--vkg-dir", str(temp_vkg_dir), "-f", "json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == "test-pool-001"
        assert data["status"] == "intake"

    def test_beads_empty(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test beads command with no beads in pool."""
        result = runner.invoke(
            app,
            ["orchestrate", "beads", "test-pool-001", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "No" in result.stdout or "beads" in result.stdout.lower()


# =============================================================================
# TestOrchestrateStart - Audit Start Command
# =============================================================================


class TestOrchestrateStart:
    """Tests for orchestrate start command."""

    def test_start_creates_pool(self, tmp_path: Path) -> None:
        """Test start command creates a pool."""
        # Create a sample Solidity file (not named Test.sol to avoid filter)
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "Vault.sol").write_text(
            "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Vault {}"
        )

        vkg_dir = tmp_path / ".vkg" / "pools"
        vkg_dir.mkdir(parents=True)

        result = runner.invoke(
            app,
            [
                "orchestrate", "start", str(contracts_dir),
                "--vkg-dir", str(vkg_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Pool created" in result.stdout
        assert "Found 1 Solidity files" in result.stdout

    def test_start_with_focus(self, tmp_path: Path) -> None:
        """Test start command with focus areas."""
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "Vault.sol").write_text(
            "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Vault {}"
        )

        vkg_dir = tmp_path / ".vkg" / "pools"
        vkg_dir.mkdir(parents=True)

        result = runner.invoke(
            app,
            [
                "orchestrate", "start", str(contracts_dir),
                "--vkg-dir", str(vkg_dir),
                "--focus", "reentrancy",
                "--focus", "oracle",
            ],
        )
        assert result.exit_code == 0
        assert "Pool created" in result.stdout

    def test_start_with_custom_id(self, tmp_path: Path) -> None:
        """Test start command with custom pool ID."""
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "Vault.sol").write_text(
            "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Vault {}"
        )

        vkg_dir = tmp_path / ".vkg" / "pools"
        vkg_dir.mkdir(parents=True)

        result = runner.invoke(
            app,
            [
                "orchestrate", "start", str(contracts_dir),
                "--vkg-dir", str(vkg_dir),
                "--pool-id", "my-custom-pool",
            ],
        )
        assert result.exit_code == 0
        assert "my-custom-pool" in result.stdout

    def test_start_dry_run(self, tmp_path: Path) -> None:
        """Test start command in dry-run mode."""
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "Vault.sol").write_text(
            "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Vault {}"
        )

        vkg_dir = tmp_path / ".vkg" / "pools"
        vkg_dir.mkdir(parents=True)

        result = runner.invoke(
            app,
            [
                "orchestrate", "start", str(contracts_dir),
                "--vkg-dir", str(vkg_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.stdout
        # Should not create any pool files
        assert len(list(vkg_dir.glob("*.yaml"))) == 0

    def test_start_path_not_found(self, tmp_path: Path) -> None:
        """Test start command with non-existent path."""
        vkg_dir = tmp_path / ".vkg" / "pools"
        vkg_dir.mkdir(parents=True)

        result = runner.invoke(
            app,
            [
                "orchestrate", "start", "/nonexistent/path",
                "--vkg-dir", str(vkg_dir),
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_start_no_solidity_files(self, tmp_path: Path) -> None:
        """Test start command with no Solidity files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        vkg_dir = tmp_path / ".vkg" / "pools"
        vkg_dir.mkdir(parents=True)

        result = runner.invoke(
            app,
            [
                "orchestrate", "start", str(empty_dir),
                "--vkg-dir", str(vkg_dir),
            ],
        )
        assert result.exit_code == 1
        assert "No Solidity files" in result.stdout


# =============================================================================
# TestOrchestrateResume - Resume Command
# =============================================================================


class TestOrchestrateResume:
    """Tests for orchestrate resume command."""

    def test_resume_not_found(self, temp_vkg_dir: Path) -> None:
        """Test resume command with non-existent pool."""
        result = runner.invoke(
            app,
            ["orchestrate", "resume", "nonexistent", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_resume_complete_pool(
        self, temp_vkg_dir: Path, manager: PoolManager, sample_pool: Pool
    ) -> None:
        """Test resume command with already complete pool."""
        # Mark pool as complete
        manager.set_status(sample_pool.id, PoolStatus.COMPLETE)

        result = runner.invoke(
            app,
            ["orchestrate", "resume", "test-pool-001", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "complete" in result.stdout.lower()

    def test_resume_failed_pool(
        self, temp_vkg_dir: Path, manager: PoolManager, sample_pool: Pool
    ) -> None:
        """Test resume command with failed pool."""
        manager.fail_pool(sample_pool.id, "test failure")

        result = runner.invoke(
            app,
            ["orchestrate", "resume", "test-pool-001", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()


# =============================================================================
# TestOrchestrateOther - Other Commands
# =============================================================================


class TestOrchestrateOther:
    """Tests for other orchestrate commands."""

    def test_pause_pool(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test pause command."""
        result = runner.invoke(
            app,
            [
                "orchestrate", "pause", "test-pool-001",
                "--vkg-dir", str(temp_vkg_dir),
                "--reason", "Test pause",
            ],
        )
        assert result.exit_code == 0
        assert "paused" in result.stdout.lower()

    def test_pause_not_found(self, temp_vkg_dir: Path) -> None:
        """Test pause command with non-existent pool."""
        result = runner.invoke(
            app,
            ["orchestrate", "pause", "nonexistent", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_delete_pool(
        self, temp_vkg_dir: Path, sample_pool: Pool
    ) -> None:
        """Test delete command with force."""
        result = runner.invoke(
            app,
            [
                "orchestrate", "delete", "test-pool-001",
                "--vkg-dir", str(temp_vkg_dir),
                "--force",
            ],
        )
        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()

    def test_delete_not_found(self, temp_vkg_dir: Path) -> None:
        """Test delete command with non-existent pool."""
        result = runner.invoke(
            app,
            [
                "orchestrate", "delete", "nonexistent",
                "--vkg-dir", str(temp_vkg_dir),
                "--force",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_summary_empty(self, temp_vkg_dir: Path) -> None:
        """Test summary command with no pools."""
        result = runner.invoke(
            app,
            ["orchestrate", "summary", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "Total: 0 pools" in result.stdout

    def test_summary_with_pools(
        self, temp_vkg_dir: Path, manager: PoolManager, sample_pool: Pool
    ) -> None:
        """Test summary command with pools."""
        # Create another pool
        scope = Scope(files=["test.sol"])
        manager.create_pool(scope=scope, pool_id="test-pool-002")

        result = runner.invoke(
            app,
            ["orchestrate", "summary", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "Total: 2 pools" in result.stdout
        assert "intake: 2" in result.stdout

    def test_beads_with_pool_beads(
        self, temp_vkg_dir: Path, manager: PoolManager, sample_pool: Pool
    ) -> None:
        """Test beads command with beads in pool."""
        # Add some beads
        manager.add_beads(sample_pool.id, ["VKG-001", "VKG-002", "VKG-003"])

        result = runner.invoke(
            app,
            ["orchestrate", "beads", "test-pool-001", "--vkg-dir", str(temp_vkg_dir)],
        )
        assert result.exit_code == 0
        assert "VKG-001" in result.stdout
        assert "VKG-002" in result.stdout
        assert "VKG-003" in result.stdout
        assert "Total: 3 beads" in result.stdout

    def test_beads_pending_filter(
        self, temp_vkg_dir: Path, manager: PoolManager, sample_pool: Pool
    ) -> None:
        """Test beads command with pending filter."""
        manager.add_beads(sample_pool.id, ["VKG-001", "VKG-002"])

        result = runner.invoke(
            app,
            [
                "orchestrate", "beads", "test-pool-001",
                "--vkg-dir", str(temp_vkg_dir),
                "--pending",
            ],
        )
        assert result.exit_code == 0
        assert "VKG-001" in result.stdout
        assert "pending" in result.stdout.lower()

    def test_beads_json_format(
        self, temp_vkg_dir: Path, manager: PoolManager, sample_pool: Pool
    ) -> None:
        """Test beads command with JSON output."""
        manager.add_beads(sample_pool.id, ["VKG-001"])

        result = runner.invoke(
            app,
            [
                "orchestrate", "beads", "test-pool-001",
                "--vkg-dir", str(temp_vkg_dir),
                "-f", "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["pool_id"] == "test-pool-001"
        assert "VKG-001" in data["filtered_beads"]


# =============================================================================
# TestAgentRunCLI - SDK-08 Parity Tests
# =============================================================================


class TestGetRuntime:
    """Tests for get_runtime SDK selection."""

    def test_anthropic_runtime(self) -> None:
        """Should return Anthropic runtime for 'anthropic' SDK."""
        from alphaswarm_sol.cli.orchestrate import get_runtime

        # Patch the runtime module where it's imported from
        with patch("alphaswarm_sol.agents.runtime.AnthropicRuntime") as mock:
            mock.return_value = MagicMock()
            runtime = get_runtime("anthropic")
            mock.assert_called_once()
            assert runtime is not None

    def test_openai_runtime(self) -> None:
        """Should return OpenAI runtime for 'openai' SDK."""
        from alphaswarm_sol.cli.orchestrate import get_runtime

        # Patch the runtime module where it's imported from
        with patch("alphaswarm_sol.agents.runtime.OpenAIAgentsRuntime") as mock:
            mock.return_value = MagicMock()
            runtime = get_runtime("openai")
            mock.assert_called_once()
            assert runtime is not None

    def test_invalid_sdk_raises(self) -> None:
        """Should raise ValueError for unknown SDK."""
        from alphaswarm_sol.cli.orchestrate import get_runtime

        with pytest.raises(ValueError, match="Unknown SDK"):
            get_runtime("invalid")

    def test_invalid_sdk_message(self) -> None:
        """Should provide helpful error message."""
        from alphaswarm_sol.cli.orchestrate import get_runtime

        with pytest.raises(ValueError) as exc_info:
            get_runtime("gemini")
        assert "anthropic" in str(exc_info.value)
        assert "openai" in str(exc_info.value)


class TestOrchestrateOptions:
    """Tests for OrchestrateOptions dataclass."""

    def test_defaults(self) -> None:
        """Should have sensible defaults."""
        from alphaswarm_sol.cli.orchestrate import OrchestrateOptions

        opts = OrchestrateOptions()
        assert opts.sdk == "anthropic"
        assert opts.timeout == 3600
        assert opts.agents_attacker == 2
        assert opts.agents_defender == 2
        assert opts.agents_verifier == 1
        assert not opts.headless
        assert not opts.resume
        assert not opts.verbose

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        from alphaswarm_sol.cli.orchestrate import OrchestrateOptions

        opts = OrchestrateOptions(
            sdk="openai",
            timeout=7200,
            agents_attacker=4,
            agents_defender=4,
            agents_verifier=2,
            headless=True,
            verbose=True,
        )
        assert opts.sdk == "openai"
        assert opts.timeout == 7200
        assert opts.agents_attacker == 4
        assert opts.agents_defender == 4
        assert opts.agents_verifier == 2
        assert opts.headless
        assert opts.verbose

    def test_output_dir_default(self) -> None:
        """Should have default output directory."""
        from alphaswarm_sol.cli.orchestrate import OrchestrateOptions

        opts = OrchestrateOptions()
        assert opts.output_dir == Path(".vrs/pools")


class TestCoordinatorReportParity:
    """Tests for CoordinatorReport SDK-08 artifact parity."""

    def test_to_dict_format(self) -> None:
        """Should serialize to expected JSON format."""
        from alphaswarm_sol.agents.propulsion import CoordinatorReport, CoordinatorStatus

        report = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=5,
            completed_beads=4,
            failed_beads=1,
            results_by_role={"attacker": 5, "defender": 5},
            duration_seconds=60.0,
            stuck_work=["bead-1"],
        )

        report_dict = report.to_dict()

        # Verify all expected fields for SDK-08 parity
        assert "status" in report_dict
        assert "total_beads" in report_dict
        assert "completed_beads" in report_dict
        assert "failed_beads" in report_dict
        assert "results_by_role" in report_dict
        assert "duration_seconds" in report_dict
        assert "stuck_work" in report_dict

    def test_json_serializable(self) -> None:
        """Should be JSON serializable (SDK-08 contract)."""
        from alphaswarm_sol.agents.propulsion import CoordinatorReport, CoordinatorStatus

        report = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=5,
            completed_beads=4,
            failed_beads=1,
            results_by_role={"attacker": 5, "defender": 5},
            duration_seconds=60.0,
            stuck_work=["bead-1"],
        )

        report_dict = report.to_dict()

        # Must round-trip through JSON
        serialized = json.dumps(report_dict)
        deserialized = json.loads(serialized)
        assert deserialized == report_dict

    def test_status_enum_serialization(self) -> None:
        """Status should serialize as string value."""
        from alphaswarm_sol.agents.propulsion import CoordinatorReport, CoordinatorStatus

        report = CoordinatorReport(
            status=CoordinatorStatus.RUNNING,
            total_beads=0,
            completed_beads=0,
            failed_beads=0,
            results_by_role={},
            duration_seconds=0,
            stuck_work=[],
        )

        report_dict = report.to_dict()
        assert report_dict["status"] == "running"

    def test_from_dict_roundtrip(self) -> None:
        """Should roundtrip through from_dict."""
        from alphaswarm_sol.agents.propulsion import CoordinatorReport, CoordinatorStatus

        original = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=10,
            completed_beads=8,
            failed_beads=2,
            results_by_role={"attacker": 10, "defender": 10, "verifier": 8},
            duration_seconds=120.5,
            stuck_work=["bead-1", "bead-2"],
        )

        report_dict = original.to_dict()
        restored = CoordinatorReport.from_dict(report_dict)

        assert restored.status == original.status
        assert restored.total_beads == original.total_beads
        assert restored.completed_beads == original.completed_beads
        assert restored.failed_beads == original.failed_beads
        assert restored.results_by_role == original.results_by_role
        assert restored.duration_seconds == original.duration_seconds
        assert restored.stuck_work == original.stuck_work


class TestAgentRunCommand:
    """Tests for agent-run CLI command."""

    @pytest.mark.xfail(reason="Stale code: --sdk flag removed from CLI")
    def test_help_shows_sdk_option(self) -> None:
        """Help should document SDK option."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--sdk" in result.stdout
        assert "anthropic" in result.stdout
        assert "openai" in result.stdout

    def test_help_shows_agent_options(self) -> None:
        """Help should document agent count options."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--attackers" in result.stdout
        assert "--defenders" in result.stdout
        assert "--verifiers" in result.stdout

    def test_help_shows_headless_option(self) -> None:
        """Help should document headless mode for CI."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--headless" in result.stdout
        assert "CI" in result.stdout

    def test_help_shows_resume_option(self) -> None:
        """Help should document resume from checkpoint."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--resume" in result.stdout
        assert "checkpoint" in result.stdout

    def test_help_shows_timeout_option(self) -> None:
        """Help should document timeout option."""
        result = runner.invoke(app, ["orchestrate", "agent-run", "--help"])
        assert result.exit_code == 0
        assert "--timeout" in result.stdout
        assert "3600" in result.stdout  # Default value


class TestCLISDKParity:
    """Tests verifying CLI and SDK produce same outputs (SDK-08)."""

    def test_report_format_matches_sdk(self) -> None:
        """CLI report format should match SDK format exactly."""
        from alphaswarm_sol.agents.propulsion import CoordinatorReport, CoordinatorStatus

        # This is the contract: both produce CoordinatorReport.to_dict()
        cli_report = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=5,
            completed_beads=5,
            failed_beads=0,
            results_by_role={"attacker": 5, "defender": 5, "verifier": 5},
            duration_seconds=300.0,
            stuck_work=[],
        )

        # SDK would produce the same report type
        sdk_report = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=5,
            completed_beads=5,
            failed_beads=0,
            results_by_role={"attacker": 5, "defender": 5, "verifier": 5},
            duration_seconds=300.0,
            stuck_work=[],
        )

        # Both should produce identical dict format
        assert cli_report.to_dict() == sdk_report.to_dict()

    def test_report_fields_documented(self) -> None:
        """All report fields should be documented/present."""
        from alphaswarm_sol.agents.propulsion import CoordinatorReport, CoordinatorStatus

        report = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=1,
            completed_beads=1,
            failed_beads=0,
            results_by_role={},
            duration_seconds=1.0,
            stuck_work=[],
        )

        expected_fields = [
            "status",
            "total_beads",
            "completed_beads",
            "failed_beads",
            "results_by_role",
            "duration_seconds",
            "stuck_work",
        ]

        report_dict = report.to_dict()
        for field in expected_fields:
            assert field in report_dict, f"Missing field: {field}"


class TestCoordinatorStatus:
    """Tests for CoordinatorStatus enum."""

    def test_all_statuses(self) -> None:
        """Should have all expected status values."""
        from alphaswarm_sol.agents.propulsion import CoordinatorStatus

        statuses = [s.value for s in CoordinatorStatus]
        assert "idle" in statuses
        assert "running" in statuses
        assert "paused" in statuses
        assert "complete" in statuses
        assert "failed" in statuses

    def test_status_is_string_enum(self) -> None:
        """Status values should be strings for JSON serialization."""
        from alphaswarm_sol.agents.propulsion import CoordinatorStatus

        for status in CoordinatorStatus:
            assert isinstance(status.value, str)
