"""Tests for Workspace Isolation (Phase 07.3.1.9).

These tests verify:
1. WorkspaceManager can allocate/release/cleanup workspaces
2. AgentConfig supports workdir field
3. PropulsionEngine integrates workspace allocation
4. Runtimes respect workdir during execution

Tests do not require network or real jj pushes.
Migrated from git worktrees to jj workspaces.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentRole
from alphaswarm_sol.agents.runtime.codex_cli import CodexCLIRuntime, CodexCLIConfig
from alphaswarm_sol.orchestration.workspace import (
    WorkspaceManager,
    WorkspaceMetadata,
    WorkspaceError,
)
# Backward compatibility aliases for tests that still use old names
WorktreeManager = WorkspaceManager
WorktreeMetadata = WorkspaceMetadata
WorktreeError = WorkspaceError


# -------------------------------------------------------------------
# Test: AgentConfig supports workdir
# -------------------------------------------------------------------

class TestAgentConfigWorkdir:
    """Test AgentConfig workdir field."""

    def test_config_has_workdir_field(self):
        """AgentConfig should have optional workdir field."""
        config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="You are a security expert.",
        )
        assert hasattr(config, "workdir")
        assert config.workdir is None

    def test_config_workdir_can_be_set(self):
        """AgentConfig workdir can be set to a path."""
        config = AgentConfig(
            role=AgentRole.DEFENDER,
            system_prompt="You are a security expert.",
            workdir="/tmp/test-worktree",
        )
        assert config.workdir == "/tmp/test-worktree"

    def test_config_to_dict_includes_workdir(self):
        """AgentConfig.to_dict() should include workdir."""
        config = AgentConfig(
            role=AgentRole.VERIFIER,
            system_prompt="You are a security expert.",
            workdir="/tmp/another-worktree",
        )
        data = config.to_dict()
        assert "workdir" in data
        assert data["workdir"] == "/tmp/another-worktree"

    def test_config_from_dict_includes_workdir(self):
        """AgentConfig.from_dict() should parse workdir."""
        data = {
            "role": "attacker",
            "system_prompt": "Test prompt",
            "workdir": "/tmp/parsed-worktree",
        }
        config = AgentConfig.from_dict(data)
        assert config.workdir == "/tmp/parsed-worktree"


# -------------------------------------------------------------------
# Test: WorkspaceManager (for agent isolation)
# -------------------------------------------------------------------

class TestWorkspaceManager:
    """Test WorkspaceManager functionality for agent isolation."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary jj repository (colocated with git for compatibility)."""
        import subprocess

        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        # Initialize jj repo (colocated with git for compatibility)
        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=repo_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["jj", "config", "set", "--repo", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["jj", "config", "set", "--repo", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Create initial content and commit
        (repo_dir / "README.md").write_text("# Test Repo")
        subprocess.run(
            ["jj", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        yield repo_dir

        # Cleanup workspaces (jj automatically handles stale workspace references)
        try:
            # Forget all vrs-* workspaces
            result = subprocess.run(
                ["jj", "workspace", "list"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if 'vrs-' in line:
                        ws_name = line.split(':')[0].strip()
                        subprocess.run(
                            ["jj", "workspace", "forget", ws_name],
                            cwd=repo_dir,
                            capture_output=True,
                        )
        except Exception:
            pass

    def test_manager_creation(self, temp_repo):
        """WorkspaceManager can be created with a repo root."""
        manager = WorkspaceManager(repo_root=temp_repo)
        assert manager.repo_root == temp_repo
        assert manager.workspace_root.exists()

        # Cleanup
        manager.cleanup()

    def test_allocate_creates_workspace(self, temp_repo):
        """allocate() creates a new jj workspace."""
        manager = WorkspaceManager(repo_root=temp_repo)

        path = manager.allocate(
            pool_id="test-pool",
            agent_id="agent-1",
        )

        assert path.exists()
        assert path.is_dir()
        # Check it's a jj workspace (has .jj directory)
        assert (path / ".jj").exists()

        # Cleanup
        manager.cleanup()

    def test_allocate_tracks_metadata(self, temp_repo):
        """allocate() tracks workspace metadata."""
        manager = WorkspaceManager(repo_root=temp_repo)

        manager.allocate(
            pool_id="test-pool",
            agent_id="agent-1",
            metadata={"role": "attacker"},
        )

        meta = manager.get_metadata("test-pool", "agent-1")
        assert meta is not None
        assert meta.pool_id == "test-pool"
        assert meta.agent_id == "agent-1"
        assert meta.status == "active"
        assert meta.metadata.get("role") == "attacker"

        # Cleanup
        manager.cleanup()

    def test_allocate_idempotent(self, temp_repo):
        """allocate() returns existing workspace if already allocated."""
        manager = WorkspaceManager(repo_root=temp_repo)

        path1 = manager.allocate(pool_id="pool", agent_id="agent")
        path2 = manager.allocate(pool_id="pool", agent_id="agent")

        assert path1 == path2

        # Cleanup
        manager.cleanup()

    def test_get_workspace(self, temp_repo):
        """get_workspace() returns path if active."""
        manager = WorkspaceManager(repo_root=temp_repo)

        allocated = manager.allocate(pool_id="pool", agent_id="agent")
        retrieved = manager.get_workspace("pool", "agent")

        assert retrieved == allocated

        # Cleanup
        manager.cleanup()

    def test_release_marks_as_released(self, temp_repo):
        """release() marks workspace as released."""
        manager = WorkspaceManager(repo_root=temp_repo)

        manager.allocate(pool_id="pool", agent_id="agent")
        result = manager.release("pool", "agent")

        assert result is True
        meta = manager.get_metadata("pool", "agent")
        assert meta.status == "released"

        # Cleanup
        manager.cleanup()

    def test_cleanup_pool_removes_all(self, temp_repo):
        """cleanup_pool() removes all workspaces for a pool."""
        manager = WorkspaceManager(repo_root=temp_repo)

        # Create multiple workspaces
        p1 = manager.allocate(pool_id="pool-1", agent_id="agent-1")
        p2 = manager.allocate(pool_id="pool-1", agent_id="agent-2")
        p3 = manager.allocate(pool_id="pool-2", agent_id="agent-1")

        # Cleanup pool-1
        removed = manager.cleanup_pool("pool-1")

        assert removed == 2
        assert not p1.exists()
        assert not p2.exists()
        assert p3.exists()  # Different pool

        # Cleanup
        manager.cleanup()

    def test_list_workspaces(self, temp_repo):
        """list_workspaces() returns all tracked workspaces."""
        manager = WorkspaceManager(repo_root=temp_repo)

        manager.allocate(pool_id="pool-1", agent_id="agent-1")
        manager.allocate(pool_id="pool-1", agent_id="agent-2")
        manager.allocate(pool_id="pool-2", agent_id="agent-1")

        all_wss = manager.list_workspaces()
        assert len(all_wss) == 3

        pool1_wss = manager.list_workspaces(pool_id="pool-1")
        assert len(pool1_wss) == 2

        # Cleanup
        manager.cleanup()

    def test_get_active_count(self, temp_repo):
        """get_active_count() returns count of active workspaces."""
        manager = WorkspaceManager(repo_root=temp_repo)

        manager.allocate(pool_id="pool", agent_id="agent-1")
        manager.allocate(pool_id="pool", agent_id="agent-2")
        manager.release("pool", "agent-1")

        assert manager.get_active_count() == 1
        assert manager.get_active_count("pool") == 1

        # Cleanup
        manager.cleanup()


# Backward compatibility: alias for old test class name
TestWorktreeManager = TestWorkspaceManager


# -------------------------------------------------------------------
# Test: WorkspaceMetadata
# -------------------------------------------------------------------

class TestWorkspaceMetadata:
    """Test WorkspaceMetadata serialization."""

    def test_to_dict(self):
        """WorkspaceMetadata can be serialized to dict."""
        from datetime import datetime

        meta = WorkspaceMetadata(
            pool_id="pool-1",
            agent_id="agent-1",
            base_ref="abc123",
            workspace_path="/tmp/workspace",
            created_at=datetime(2026, 1, 29, 12, 0, 0),
            status="active",
            workspace_name="vrs-pool-1-agent-1-xyz",
            metadata={"role": "attacker"},
        )

        data = meta.to_dict()
        assert data["pool_id"] == "pool-1"
        assert data["agent_id"] == "agent-1"
        assert data["status"] == "active"
        assert data["metadata"]["role"] == "attacker"

    def test_from_dict(self):
        """WorkspaceMetadata can be deserialized from dict."""
        data = {
            "pool_id": "pool-1",
            "agent_id": "agent-1",
            "base_ref": "abc123",
            "workspace_path": "/tmp/workspace",
            "created_at": "2026-01-29T12:00:00",
            "status": "released",
            "workspace_name": "vrs-pool-1-agent-1-xyz",
            "metadata": {"role": "defender"},
        }

        meta = WorkspaceMetadata.from_dict(data)
        assert meta.pool_id == "pool-1"
        assert meta.status == "released"
        assert meta.metadata["role"] == "defender"


# Backward compatibility: alias for old test class name
TestWorktreeMetadata = TestWorkspaceMetadata


# -------------------------------------------------------------------
# Test: PropulsionEngine workspace integration
# -------------------------------------------------------------------

class TestPropulsionEngineWorkspaceIntegration:
    """Test PropulsionEngine workspace integration."""

    def test_propulsion_config_has_workspace_fields(self):
        """PropulsionConfig should have workspace isolation fields."""
        from alphaswarm_sol.agents.propulsion.engine import PropulsionConfig
        import warnings

        config = PropulsionConfig()
        assert hasattr(config, "enable_workspace_isolation")
        assert hasattr(config, "pool_id")
        assert config.enable_workspace_isolation is False

        # Test backward compatibility property (deprecated)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assert hasattr(config, "enable_worktree_isolation")
            deprecated_value = config.enable_worktree_isolation
            assert deprecated_value is False
            # Verify deprecation warning was issued
            assert len(w) >= 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "enable_worktree_isolation" in str(w[-1].message)

    def test_propulsion_config_with_isolation(self):
        """PropulsionConfig can enable workspace isolation."""
        from alphaswarm_sol.agents.propulsion.engine import PropulsionConfig

        config = PropulsionConfig(
            enable_workspace_isolation=True,
            pool_id="audit-001",
        )
        assert config.enable_workspace_isolation is True
        assert config.pool_id == "audit-001"

    def test_propulsion_config_to_dict_includes_workspace(self):
        """PropulsionConfig.to_dict() includes workspace fields."""
        from alphaswarm_sol.agents.propulsion.engine import PropulsionConfig

        config = PropulsionConfig(
            enable_workspace_isolation=True,
            pool_id="audit-002",
        )
        data = config.to_dict()
        assert data["enable_workspace_isolation"] is True
        assert data["pool_id"] == "audit-002"

    @patch("alphaswarm_sol.orchestration.workspace.WorkspaceManager")
    def test_engine_initializes_workspace_manager(self, mock_wm_class):
        """PropulsionEngine initializes WorkspaceManager when enabled."""
        from alphaswarm_sol.agents.propulsion.engine import (
            PropulsionEngine,
            PropulsionConfig,
        )

        mock_wm = MagicMock()
        mock_wm_class.return_value = mock_wm

        runtime = MagicMock()
        config = PropulsionConfig(
            enable_workspace_isolation=True,
            pool_id="test-pool",
        )

        engine = PropulsionEngine(runtime=runtime, inboxes={}, config=config)

        assert engine._workspace_manager is not None

    def test_engine_no_workspace_when_disabled(self):
        """PropulsionEngine does not create WorkspaceManager when disabled."""
        from alphaswarm_sol.agents.propulsion.engine import (
            PropulsionEngine,
            PropulsionConfig,
        )

        runtime = MagicMock()
        config = PropulsionConfig(enable_workspace_isolation=False)

        engine = PropulsionEngine(runtime=runtime, inboxes={}, config=config)

        assert engine._workspace_manager is None

    def test_engine_cleanup_workspaces(self):
        """PropulsionEngine.cleanup_workspaces() calls manager cleanup."""
        from alphaswarm_sol.agents.propulsion.engine import (
            PropulsionEngine,
            PropulsionConfig,
        )

        runtime = MagicMock()
        config = PropulsionConfig(
            enable_workspace_isolation=True,
            pool_id="test-pool",
        )

        with patch("alphaswarm_sol.orchestration.workspace.WorkspaceManager") as mock_wm_class:
            mock_wm = MagicMock()
            mock_wm.cleanup_pool.return_value = 3
            mock_wm_class.return_value = mock_wm

            engine = PropulsionEngine(runtime=runtime, inboxes={}, config=config)
            result = engine.cleanup_workspaces()

            assert result == 3
            mock_wm.cleanup_pool.assert_called_once_with("test-pool")


# Backward compatibility: alias for old test class name
TestPropulsionEngineWorktreeIntegration = TestPropulsionEngineWorkspaceIntegration


# -------------------------------------------------------------------
# Test: Parallel agents get unique workspaces
# -------------------------------------------------------------------

class TestParallelAgentWorkspaces:
    """Test parallel agents get unique workspace paths."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary jj repository (colocated with git for compatibility)."""
        import subprocess

        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["jj", "config", "set", "--repo", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["jj", "config", "set", "--repo", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        (repo_dir / "README.md").write_text("# Test Repo")
        subprocess.run(
            ["jj", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        yield repo_dir

        # Cleanup workspaces
        try:
            result = subprocess.run(
                ["jj", "workspace", "list"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if 'vrs-' in line:
                        ws_name = line.split(':')[0].strip()
                        subprocess.run(
                            ["jj", "workspace", "forget", ws_name],
                            cwd=repo_dir,
                            capture_output=True,
                        )
        except Exception:
            pass

    def test_parallel_agents_unique_paths(self, temp_repo):
        """Multiple agents get unique workspace paths."""
        manager = WorkspaceManager(repo_root=temp_repo)

        paths = []
        for i in range(3):
            path = manager.allocate(
                pool_id="pool",
                agent_id=f"agent-{i}",
            )
            paths.append(path)

        # All paths should be unique
        assert len(set(paths)) == 3

        # All paths should exist
        for p in paths:
            assert p.exists()

        # Cleanup
        manager.cleanup()

    def test_parallel_agents_no_shared_writes(self, temp_repo):
        """Changes in one workspace don't affect another."""
        manager = WorkspaceManager(repo_root=temp_repo)

        path1 = manager.allocate(pool_id="pool", agent_id="agent-1")
        path2 = manager.allocate(pool_id="pool", agent_id="agent-2")

        # Write different content to each
        (path1 / "agent1.txt").write_text("Agent 1 content")
        (path2 / "agent2.txt").write_text("Agent 2 content")

        # Verify isolation
        assert (path1 / "agent1.txt").exists()
        assert not (path1 / "agent2.txt").exists()
        assert (path2 / "agent2.txt").exists()
        assert not (path2 / "agent1.txt").exists()

        # Cleanup
        manager.cleanup()


# Backward compatibility: alias for old test class name
TestParallelAgentWorktrees = TestParallelAgentWorkspaces


# -------------------------------------------------------------------
# Test: Codex CLI Runtime honors workdir
# -------------------------------------------------------------------

class TestCodexCLIRuntimeWorkdir:
    """Test Codex CLI Runtime respects workdir."""

    def test_runtime_has_get_working_dir(self):
        """CodexCLIRuntime should have _get_working_dir method."""
        runtime = CodexCLIRuntime()
        assert hasattr(runtime, "_get_working_dir")

    def test_runtime_default_working_dir(self):
        """Runtime uses default working dir when no config workdir."""
        runtime = CodexCLIRuntime()
        config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="Test",
        )
        workdir = runtime._get_working_dir(config)
        assert workdir == runtime.default_working_dir

    def test_runtime_respects_config_workdir(self, tmp_path):
        """Runtime uses AgentConfig.workdir when set."""
        runtime = CodexCLIRuntime()
        config = AgentConfig(
            role=AgentRole.DEFENDER,
            system_prompt="Test",
            workdir=str(tmp_path),
        )
        workdir = runtime._get_working_dir(config)
        assert workdir == tmp_path

    def test_runtime_uses_constructor_working_dir(self, tmp_path):
        """Runtime uses constructor working_dir as default."""
        runtime = CodexCLIRuntime(working_dir=tmp_path)
        assert runtime.default_working_dir == tmp_path

        config = AgentConfig(
            role=AgentRole.VERIFIER,
            system_prompt="Test",
        )
        workdir = runtime._get_working_dir(config)
        assert workdir == tmp_path

    def test_config_workdir_overrides_default(self, tmp_path):
        """AgentConfig.workdir overrides runtime default."""
        default_dir = tmp_path / "default"
        default_dir.mkdir()
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        runtime = CodexCLIRuntime(working_dir=default_dir)
        config = AgentConfig(
            role=AgentRole.TEST_BUILDER,
            system_prompt="Test",
            workdir=str(config_dir),
        )

        workdir = runtime._get_working_dir(config)
        assert workdir == config_dir

    @pytest.mark.asyncio
    async def test_execute_passes_workdir_to_subprocess(self, tmp_path):
        """execute() should pass workdir to subprocess."""
        runtime = CodexCLIRuntime()
        config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="Test",
            workdir=str(tmp_path),
        )
        messages = [{"role": "user", "content": "Test prompt"}]

        # Mock the subprocess to verify cwd
        captured_cwd = None

        async def mock_run_subprocess(cmd, timeout, working_dir=None):
            nonlocal captured_cwd
            captured_cwd = working_dir
            return {"content": "Test response", "usage": {}}

        with patch.object(runtime, "_run_subprocess", mock_run_subprocess):
            await runtime.execute(config, messages)

        assert captured_cwd == tmp_path


# -------------------------------------------------------------------
# Test: Workspace cleanup after completion
# -------------------------------------------------------------------

class TestWorkspaceCleanup:
    """Test workspace cleanup scenarios."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary jj repository (colocated with git for compatibility)."""
        import subprocess

        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["jj", "config", "set", "--repo", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["jj", "config", "set", "--repo", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        (repo_dir / "README.md").write_text("# Test Repo")
        subprocess.run(
            ["jj", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        yield repo_dir

        try:
            result = subprocess.run(
                ["jj", "workspace", "list"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if 'vrs-' in line:
                        ws_name = line.split(':')[0].strip()
                        subprocess.run(
                            ["jj", "workspace", "forget", ws_name],
                            cwd=repo_dir,
                            capture_output=True,
                        )
        except Exception:
            pass

    def test_cleanup_removes_released_workspaces(self, temp_repo):
        """cleanup() removes all workspaces."""
        manager = WorkspaceManager(repo_root=temp_repo)

        p1 = manager.allocate(pool_id="pool", agent_id="agent-1")
        p2 = manager.allocate(pool_id="pool", agent_id="agent-2")
        manager.release("pool", "agent-1")

        removed = manager.cleanup()

        assert removed == 2
        assert not p1.exists()
        assert not p2.exists()

    def test_cleanup_stale_respects_age(self, temp_repo):
        """cleanup_stale() only removes old released workspaces."""
        from datetime import datetime, timedelta

        manager = WorkspaceManager(repo_root=temp_repo)

        manager.allocate(pool_id="pool", agent_id="agent-1")
        manager.release("pool", "agent-1")

        # Modify created_at to make it old
        key = "pool/agent-1"
        manager._metadata[key].created_at = datetime.now() - timedelta(hours=48)
        manager._save_metadata()

        # Reload to pick up changes
        manager._load_metadata()

        removed = manager.cleanup_stale(max_age_hours=24)

        assert removed == 1

    def test_released_workspace_not_returned_by_get(self, temp_repo):
        """get_workspace() returns None for released workspaces."""
        manager = WorkspaceManager(repo_root=temp_repo)

        manager.allocate(pool_id="pool", agent_id="agent")
        manager.release("pool", "agent")

        result = manager.get_workspace("pool", "agent")

        # Released workspaces are not "active"
        assert result is None

        # Cleanup
        manager.cleanup()


# Backward compatibility: alias for old test class name
TestWorktreeCleanup = TestWorkspaceCleanup
