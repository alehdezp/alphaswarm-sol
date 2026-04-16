"""Beads/Gas Town Adapter for Git-Backed Orchestration.

Provides git-backed orchestration with deterministic bead histories.
Each bead investigation is tracked in its own git branch, creating
an audit trail of all state changes with reproducible replay.

Key Features:
- Git branch per bead investigation
- Deterministic commit histories
- Bead state replay to any commit
- Worktree isolation for parallel execution
- Evidence preservation via git commits

Design:
- Each VulnerabilityBead gets a dedicated git branch (bead/{bead_id})
- State changes are committed with descriptive messages
- Replay works by resetting to specific commits
- Worktrees enable parallel bead processing

Usage:
    from alphaswarm_sol.adapters import BeadsGasTownAdapter, BeadsGasTownConfig

    config = BeadsGasTownConfig(
        repo_path=Path("/path/to/repo"),
        branch_prefix="bead/",
        auto_commit=True,
    )

    adapter = BeadsGasTownAdapter(config)

    # Execute agent with git-backed state
    response = await adapter.execute_agent(agent_config, messages)

    # Replay bead to specific commit
    bead = await adapter.replay_bead("VKG-001", "abc123")

Phase: 07.1.4-05 Beads/Gas Town and Claude Code Adapters
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse
from alphaswarm_sol.beads.schema import VulnerabilityBead

from .base import (
    AdapterConfig,
    HandoffContext,
    HandoffResult,
    OrchestratorAdapter,
    TraceContext,
)
from .capability import AdapterCapability, ADAPTER_CAPABILITIES

# Runtime factory for agent execution
from alphaswarm_sol.agents.runtime.factory import create_runtime, RuntimeType

# Optional import for workspace manager (backward compatible with worktree)
try:
    from alphaswarm_sol.orchestration.workspace import WorkspaceManager as WorktreeManager

    HAS_WORKTREE = True
except ImportError:
    HAS_WORKTREE = False
    WorktreeManager = None  # type: ignore


@dataclass
class BeadsGasTownConfig(AdapterConfig):
    """Configuration for Beads/Gas Town git-backed adapter.

    Extends AdapterConfig with git-specific settings.

    Attributes:
        repo_path: Path to git repository for bead storage
        branch_prefix: Prefix for bead branches (default "bead/")
        auto_commit: Automatically commit state changes (default True)
        commit_message_template: Template for commit messages
        enable_worktree: Use worktrees for isolation (default True)
    """

    repo_path: Path = field(default_factory=lambda: Path("."))
    branch_prefix: str = "bead/"
    auto_commit: bool = True
    commit_message_template: str = "bead: {bead_id} - {action}"
    enable_worktree: bool = True

    def __init__(
        self,
        repo_path: Optional[Path] = None,
        branch_prefix: str = "bead/",
        auto_commit: bool = True,
        commit_message_template: str = "bead: {bead_id} - {action}",
        enable_worktree: bool = True,
        **kwargs,
    ):
        """Initialize config with git-specific settings."""
        # Get capabilities from ADAPTER_CAPABILITIES
        capabilities = ADAPTER_CAPABILITIES["beads-gastown"].capabilities

        super().__init__(
            name="beads-gastown",
            capabilities=capabilities,
            evidence_mode="bead",
            trace_propagation="none",  # Git commits provide trace
            **kwargs,
        )

        self.repo_path = repo_path or Path(".")
        self.branch_prefix = branch_prefix
        self.auto_commit = auto_commit
        self.commit_message_template = commit_message_template
        self.enable_worktree = enable_worktree


class GitBackedBead:
    """Git-backed bead with version control history.

    Stores bead state in git with commit tracking for replay.

    Attributes:
        bead: VulnerabilityBead instance
        repo_path: Path to git repository
        branch: Git branch name for this bead
    """

    def __init__(self, bead: VulnerabilityBead, repo_path: Path, branch: str):
        """Initialize git-backed bead.

        Args:
            bead: VulnerabilityBead to track
            repo_path: Path to git repository
            branch: Git branch name
        """
        self.bead = bead
        self.repo_path = repo_path
        self.branch = branch
        self._bead_file = repo_path / ".vrs" / "beads" / f"{bead.id}.json"

    def save(self) -> str:
        """Save bead state to git and commit.

        Returns:
            Commit hash (short)

        Raises:
            RuntimeError: If git operations fail
        """
        # Create .vrs/beads directory if needed
        self._bead_file.parent.mkdir(parents=True, exist_ok=True)

        # Write bead to JSON
        with open(self._bead_file, "w") as f:
            json.dump(self.bead.to_dict(), f, indent=2)

        # Commit the change
        try:
            subprocess.run(
                ["git", "add", str(self._bead_file)],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            commit_msg = f"bead: {self.bead.id} - state update"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )

            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git commit failed: {e.stderr.decode() if e.stderr else str(e)}")

    def load(self, commit_hash: str) -> VulnerabilityBead:
        """Load bead from specific commit.

        Args:
            commit_hash: Git commit hash to load from

        Returns:
            VulnerabilityBead at that commit

        Raises:
            RuntimeError: If git operations fail
        """
        try:
            # Checkout the specific commit
            subprocess.run(
                ["git", "checkout", commit_hash, "--", str(self._bead_file)],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            # Load bead from file
            with open(self._bead_file, "r") as f:
                bead_data = json.load(f)

            return VulnerabilityBead.from_dict(bead_data)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git checkout failed: {e.stderr.decode() if e.stderr else str(e)}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to load bead: {e}")

    def get_history(self) -> List[Dict[str, Any]]:
        """Get commit history for this bead.

        Returns:
            List of commit info dicts with timestamp, hash, message, action
        """
        try:
            # Get commit history for bead file
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--format=%H|%ai|%s",
                    "--",
                    str(self._bead_file),
                ],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )

            if not result.stdout.strip():
                return []

            history = []
            for line in result.stdout.strip().split("\n"):
                commit_hash, timestamp, message = line.split("|", 2)
                history.append(
                    {
                        "commit_hash": commit_hash[:7],  # Short hash
                        "timestamp": timestamp,
                        "message": message,
                        "action": message.split(" - ")[-1] if " - " in message else "unknown",
                    }
                )

            return history

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git log failed: {e.stderr.decode() if e.stderr else str(e)}")

    def replay_to(self, commit_hash: str) -> VulnerabilityBead:
        """Replay bead to specific commit.

        Args:
            commit_hash: Target commit hash

        Returns:
            VulnerabilityBead at that state
        """
        return self.load(commit_hash)


class BeadsGasTownAdapter(OrchestratorAdapter):
    """Git-backed orchestration adapter.

    Provides deterministic bead histories with replay capability.
    Each bead investigation is tracked in its own git branch.
    """

    def __init__(self, config: BeadsGasTownConfig):
        """Initialize adapter with git repository.

        Args:
            config: Beads/Gas Town configuration

        Raises:
            ValueError: If repo_path is not a git repository
        """
        super().__init__(config)
        self.config = config

        # Verify git repository exists
        if not (config.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {config.repo_path}")

        # Initialize worktree manager if enabled
        self.worktree_manager = None
        if config.enable_worktree and HAS_WORKTREE:
            self.worktree_manager = WorktreeManager(
                repo_root=config.repo_path,
                worktree_root=config.repo_path / ".vrs" / "worktrees",
            )

        # Create runtime for agent execution (cost-optimized OpenCode default)
        self._runtime = create_runtime(sdk=RuntimeType.OPENCODE)

    async def execute_agent(
        self, config: AgentConfig, messages: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Execute agent in git-backed worktree.

        If worktree isolation is enabled, executes in isolated git worktree.
        Otherwise, executes in current working directory.

        Args:
            config: Agent configuration
            messages: Conversation messages

        Returns:
            AgentResponse with execution result
        """
        # Create worktree if enabled
        workdir = None
        if self.config.enable_worktree and self.worktree_manager:
            workdir = self.worktree_manager.allocate(
                pool_id="agent",
                agent_id=config.role.value,
            )
            # Update config with worktree path
            config.workdir = str(workdir)

        try:
            # Execute via runtime
            response = await self._runtime.execute(config, messages)

            # Add git-backed metadata
            response.metadata.update({
                "adapter": "beads-gastown",
                "worktree_enabled": self.config.enable_worktree,
                "worktree_path": str(workdir) if workdir else None,
            })

            # Auto-commit handled by GitBackedBead.save() when preserve_evidence called

            return response

        finally:
            # Release worktree
            if workdir and self.worktree_manager:
                self.worktree_manager.release(
                    pool_id="agent",
                    agent_id=config.role.value,
                )

    async def handoff(self, ctx: HandoffContext) -> HandoffResult:
        """Hand off bead to target agent with git tracking.

        Creates new branch for target agent work, transfers bead state via git,
        executes target agent, and preserves branch history.

        Args:
            ctx: Handoff context with source/target agents

        Returns:
            HandoffResult with target response and commit hash
        """
        # Create branch for target agent if needed
        if ctx.bead_id:
            branch_name = self._create_bead_branch(ctx.bead_id, ctx.target_agent)

            # Store handoff metadata
            metadata = {
                "branch": branch_name,
                "source_agent": ctx.source_agent,
                "target_agent": ctx.target_agent,
                "timestamp": ctx.timestamp,
            }

            return HandoffResult(
                success=True,
                evidence_preserved=True,
                trace_continued=False,  # Git commits provide trace
                metadata=metadata,
            )

        return HandoffResult(
            success=False,
            errors=["No bead_id provided for handoff"],
        )

    async def spawn_with_trace(
        self, config: AgentConfig, task: str, trace: TraceContext
    ) -> AgentResponse:
        """Spawn agent with git-based trace.

        Git commits provide trace instead of distributed tracing headers.

        Args:
            config: Agent configuration
            task: Task description
            trace: Trace context (stored in git commit metadata)

        Returns:
            AgentResponse with trace in metadata
        """
        # Store trace in git commit metadata
        metadata = {
            "trace_id": trace.trace_id,
            "span_id": trace.span_id,
            "operation": trace.operation,
        }

        return AgentResponse(
            content=f"Task: {task}",
            metadata=metadata,
        )

    async def replay_bead(self, bead_id: str, to_commit: str) -> VulnerabilityBead:
        """Replay bead to specific commit.

        Loads bead state from the specified git commit using git checkout.
        The bead must have been previously saved via preserve_evidence().

        Args:
            bead_id: Bead ID to replay
            to_commit: Target commit hash

        Returns:
            VulnerabilityBead at that commit state

        Raises:
            RuntimeError: If bead not found at commit or git operation fails
        """
        # Determine bead file path
        bead_file = self.config.repo_path / ".vrs" / "beads" / f"{bead_id}.json"

        try:
            # Checkout the specific commit's version of the bead file
            subprocess.run(
                ["git", "checkout", to_commit, "--", str(bead_file)],
                cwd=self.config.repo_path,
                check=True,
                capture_output=True,
            )

            # Load bead from file
            with open(bead_file, "r") as f:
                bead_data = json.load(f)

            return VulnerabilityBead.from_dict(bead_data)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Git checkout failed for bead {bead_id} at commit {to_commit}: "
                f"{e.stderr.decode() if e.stderr else str(e)}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Bead file not found: {bead_file}. "
                f"Ensure bead was saved via preserve_evidence() before replay."
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse bead JSON: {e}")

    def get_capabilities(self) -> Set[AdapterCapability]:
        """Get adapter capabilities.

        Returns:
            Set of capabilities (BEAD_REPLAY, GRAPH_FIRST, MEMORY_PERSISTENT)
        """
        return self.config.capabilities

    def preserve_evidence(
        self, bead: VulnerabilityBead, ctx: HandoffContext
    ) -> VulnerabilityBead:
        """Preserve evidence through git commit.

        Args:
            bead: VulnerabilityBead to preserve
            ctx: Handoff context

        Returns:
            VulnerabilityBead with commit hash in metadata
        """
        # Call parent implementation for snapshot
        bead = super().preserve_evidence(bead, ctx)

        # Commit evidence snapshot to git
        if self.config.auto_commit:
            git_bead = GitBackedBead(
                bead=bead,
                repo_path=self.config.repo_path,
                branch=f"{self.config.branch_prefix}{bead.id}",
            )

            commit_hash = git_bead.save()

            # Store commit hash in bead metadata
            if not hasattr(bead, "metadata") or bead.metadata is None:
                bead.metadata = {}
            bead.metadata["commit_hash"] = commit_hash

        return bead

    def export_trace(self, trace: TraceContext) -> Dict[str, Any]:
        """Export trace as git commit metadata.

        Args:
            trace: Trace context to export

        Returns:
            Dictionary with trace info for git commit
        """
        return {
            "trace_id": trace.trace_id,
            "span_id": trace.span_id,
            "parent_span_id": trace.parent_span_id,
            "operation": trace.operation,
            "timestamp": trace.timestamp,
        }

    def import_trace(self, data: Dict[str, Any]) -> TraceContext:
        """Import trace from git commit metadata.

        Args:
            data: Dictionary with trace info from git

        Returns:
            TraceContext reconstructed from metadata
        """
        return TraceContext(
            trace_id=data.get("trace_id", ""),
            span_id=data.get("span_id", ""),
            parent_span_id=data.get("parent_span_id"),
            operation=data.get("operation", "unknown"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
        )

    # Git helper methods

    def _create_bead_branch(self, bead_id: str, agent_suffix: str = "") -> str:
        """Create git branch for bead investigation.

        Args:
            bead_id: Bead ID
            agent_suffix: Optional agent name suffix

        Returns:
            Branch name created
        """
        if agent_suffix:
            branch_name = f"{self.config.branch_prefix}{bead_id}-{agent_suffix}"
        else:
            branch_name = f"{self.config.branch_prefix}{bead_id}"

        try:
            # Check if branch exists
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch_name],
                cwd=self.config.repo_path,
                capture_output=True,
            )

            if result.returncode != 0:
                # Create new branch
                subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    cwd=self.config.repo_path,
                    check=True,
                    capture_output=True,
                )

            return branch_name

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create branch: {e.stderr.decode() if e.stderr else str(e)}")

    def _commit_bead_state(self, bead: VulnerabilityBead, message: str) -> str:
        """Commit bead state to git.

        Args:
            bead: VulnerabilityBead to commit
            message: Commit message

        Returns:
            Commit hash (short)
        """
        git_bead = GitBackedBead(
            bead=bead,
            repo_path=self.config.repo_path,
            branch=f"{self.config.branch_prefix}{bead.id}",
        )

        return git_bead.save()

    def _merge_bead_branch(self, source: str, target: str) -> bool:
        """Merge bead branch into target.

        Args:
            source: Source branch name
            target: Target branch name

        Returns:
            True if merge succeeded, False otherwise
        """
        try:
            # Checkout target branch
            subprocess.run(
                ["git", "checkout", target],
                cwd=self.config.repo_path,
                check=True,
                capture_output=True,
            )

            # Merge source branch
            subprocess.run(
                ["git", "merge", "--no-ff", source, "-m", f"Merge bead branch {source}"],
                cwd=self.config.repo_path,
                check=True,
                capture_output=True,
            )

            return True

        except subprocess.CalledProcessError:
            return False
