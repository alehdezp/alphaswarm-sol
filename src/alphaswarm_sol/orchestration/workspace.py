"""Workspace Manager for Agent Isolation.

Phase 07.3.1.9: Provides Jujutsu workspace management so parallel agents
can operate safely without file conflicts.

Per PHILOSOPHY.md and 07.1.1-CONTEXT.md:
- Parallel agents must have isolated working directories
- Each agent gets a fresh workspace with no shared writes
- Workspaces are tracked, cleaned up, and changes can be merged back

Usage:
    from alphaswarm_sol.orchestration.workspace import WorkspaceManager

    manager = WorkspaceManager()

    # Allocate workspace for an agent
    workspace_path = manager.allocate(
        pool_id="audit-001",
        agent_id="attacker-1",
    )

    # ... agent runs in workspace_path ...

    # Release when done
    manager.release(pool_id="audit-001", agent_id="attacker-1")

    # Cleanup all workspaces for a pool
    manager.cleanup_pool("audit-001")

    # Cleanup old workspaces
    manager.cleanup_stale(max_age_hours=24)
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Default workspace root under .vrs directory
DEFAULT_WORKSPACE_ROOT = ".vrs/workspaces"


@dataclass
class WorkspaceMetadata:
    """Metadata for a workspace.

    Attributes:
        pool_id: Pool ID this workspace belongs to
        agent_id: Agent ID this workspace is assigned to
        base_ref: Jujutsu revision the workspace is based on (commit or @)
        workspace_path: Absolute path to the workspace
        created_at: When the workspace was created
        status: Current status (active, released, error)
        workspace_name: Name of the jj workspace created
    """

    pool_id: str
    agent_id: str
    base_ref: str
    workspace_path: str
    created_at: datetime
    status: str = "active"
    workspace_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pool_id": self.pool_id,
            "agent_id": self.agent_id,
            "base_ref": self.base_ref,
            "workspace_path": self.workspace_path,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "workspace_name": self.workspace_name,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceMetadata":
        """Create from dictionary."""
        return cls(
            pool_id=data["pool_id"],
            agent_id=data["agent_id"],
            base_ref=data["base_ref"],
            workspace_path=data["workspace_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=data.get("status", "active"),
            workspace_name=data.get("workspace_name", ""),
            metadata=data.get("metadata", {}),
        )


class WorkspaceError(Exception):
    """Error during workspace operations."""

    pass


class WorkspaceManager:
    """Manages Jujutsu workspaces for isolated agent execution.

    Per Phase 07.3.1.9:
    - Allocate workspace paths under .vrs/workspaces/{pool_id}/{agent_id}
    - Use `jj workspace add` to create isolated workspaces
    - Track workspace metadata in JSON
    - Provide release() and cleanup() helpers

    Workspace Layout:
        .vrs/
        workspaces/
            {pool_id}/
                {agent_id}/
                    ... workspace files ...
            metadata.json  # Tracks all workspaces

    Attributes:
        repo_root: Root of the Jujutsu repository
        workspace_root: Directory for workspaces (default: .vrs/workspaces)
        metadata_file: Path to metadata JSON file
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
    ):
        """Initialize workspace manager.

        Args:
            repo_root: Root of the jj repository (auto-detected if None)
            workspace_root: Root directory for workspaces

        Raises:
            WorkspaceError: If jj is unavailable or not in a jj repo
        """
        self.repo_root = repo_root or self._find_repo_root()
        self.workspace_root = workspace_root or (self.repo_root / DEFAULT_WORKSPACE_ROOT)
        self.metadata_file = self.workspace_root / "metadata.json"

        # Validate jj is available
        self._validate_jj()

        # Ensure workspace root exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Load or initialize metadata
        self._metadata: Dict[str, WorkspaceMetadata] = {}
        self._load_metadata()

    def _find_repo_root(self) -> Path:
        """Find the root of the current Jujutsu repository.

        Returns:
            Path to repository root

        Raises:
            WorkspaceError: If not in a jj repository
        """
        try:
            result = subprocess.run(
                ["jj", "root"],
                capture_output=True,
                text=True,
                check=True,
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            raise WorkspaceError("Not in a jj repository")
        except FileNotFoundError:
            raise WorkspaceError("jj command not found")

    def _validate_jj(self) -> None:
        """Validate jj is available and configured.

        Raises:
            WorkspaceError: If jj is unavailable or misconfigured
        """
        try:
            result = subprocess.run(
                ["jj", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.debug(f"Jujutsu version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise WorkspaceError("jj command not found - install jujutsu first")
        except subprocess.CalledProcessError as e:
            raise WorkspaceError(f"jj error: {e.stderr}")

    def _load_metadata(self) -> None:
        """Load workspace metadata from disk."""
        if not self.metadata_file.exists():
            return

        try:
            with open(self.metadata_file) as f:
                data = json.load(f)
                for key, entry in data.items():
                    self._metadata[key] = WorkspaceMetadata.from_dict(entry)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load workspace metadata: {e}")

    def _save_metadata(self) -> None:
        """Save workspace metadata to disk."""
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        data = {key: ws.to_dict() for key, ws in self._metadata.items()}
        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)

    def _make_key(self, pool_id: str, agent_id: str) -> str:
        """Create metadata key from pool and agent ID."""
        return f"{pool_id}/{agent_id}"

    def _get_current_ref(self) -> str:
        """Get current jj working copy revision.

        Returns:
            Current commit ID or @ as fallback
        """
        try:
            result = subprocess.run(
                ["jj", "log", "-r", "@", "--no-graph", "-T", "commit_id"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "@"  # Jujutsu's default working copy reference

    def allocate(
        self,
        pool_id: str,
        agent_id: str,
        base_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Allocate a workspace for an agent.

        Creates a new jj workspace under .vrs/workspaces/{pool_id}/{agent_id}.
        The workspace is created from the specified base_ref or current @.

        Args:
            pool_id: ID of the pool this agent belongs to
            agent_id: Unique agent identifier
            base_ref: Jujutsu revision to base workspace on (default: @)
            metadata: Optional additional metadata to track

        Returns:
            Path to the allocated workspace

        Raises:
            WorkspaceError: If allocation fails
        """
        key = self._make_key(pool_id, agent_id)

        # Check if already allocated
        if key in self._metadata and self._metadata[key].status == "active":
            existing = self._metadata[key]
            workspace_path = Path(existing.workspace_path)
            if workspace_path.exists():
                logger.info(f"Workspace already exists for {key}")
                return workspace_path

        # Determine base ref
        base_ref = base_ref or self._get_current_ref()

        # Create workspace path
        workspace_path = self.workspace_root / pool_id / agent_id
        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove if exists but orphaned
        if workspace_path.exists():
            self._remove_workspace_dir(workspace_path)

        # Create unique workspace name
        workspace_name = f"vrs-{pool_id[:8]}-{agent_id[:8]}-{uuid.uuid4().hex[:6]}"

        try:
            # Create workspace with jj workspace add
            subprocess.run(
                [
                    "jj", "workspace", "add",
                    str(workspace_path),
                    "--name", workspace_name,
                    "-r", base_ref,
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info(f"Created workspace at {workspace_path} from {base_ref}")

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            raise WorkspaceError(f"Failed to create workspace: {error_msg}")

        # Track metadata
        ws_meta = WorkspaceMetadata(
            pool_id=pool_id,
            agent_id=agent_id,
            base_ref=base_ref,
            workspace_path=str(workspace_path.absolute()),
            created_at=datetime.now(),
            status="active",
            workspace_name=workspace_name,
            metadata=metadata or {},
        )
        self._metadata[key] = ws_meta
        self._save_metadata()

        return workspace_path

    def get_workspace(self, pool_id: str, agent_id: str) -> Optional[Path]:
        """Get path to an allocated workspace.

        Args:
            pool_id: Pool ID
            agent_id: Agent ID

        Returns:
            Path to workspace if exists and active, None otherwise
        """
        key = self._make_key(pool_id, agent_id)
        ws = self._metadata.get(key)

        if ws and ws.status == "active":
            path = Path(ws.workspace_path)
            if path.exists():
                return path

        return None

    def get_metadata(self, pool_id: str, agent_id: str) -> Optional[WorkspaceMetadata]:
        """Get metadata for a workspace.

        Args:
            pool_id: Pool ID
            agent_id: Agent ID

        Returns:
            WorkspaceMetadata if exists, None otherwise
        """
        key = self._make_key(pool_id, agent_id)
        return self._metadata.get(key)

    def release(self, pool_id: str, agent_id: str) -> bool:
        """Release a workspace after agent completion.

        Marks the workspace as released but does not remove it yet.
        Use cleanup_pool() or cleanup_stale() to actually remove.

        Args:
            pool_id: Pool ID
            agent_id: Agent ID

        Returns:
            True if released, False if not found
        """
        key = self._make_key(pool_id, agent_id)
        ws = self._metadata.get(key)

        if not ws:
            return False

        ws.status = "released"
        self._save_metadata()
        logger.info(f"Released workspace {key}")

        return True

    def _remove_workspace_dir(self, path: Path) -> None:
        """Remove a workspace directory.

        Args:
            path: Path to workspace directory
        """
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def _remove_workspace(self, workspace_path: Path, workspace_name: str) -> None:
        """Remove a workspace via jj and cleanup.

        Args:
            workspace_path: Path to workspace
            workspace_name: Workspace name to forget
        """
        # Forget the workspace from jj tracking
        if workspace_name:
            try:
                subprocess.run(
                    ["jj", "workspace", "forget", workspace_name],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,  # Don't fail if already gone
                )
            except Exception as e:
                logger.debug(f"jj workspace forget failed (may be ok): {e}")

        # Remove the workspace directory
        self._remove_workspace_dir(workspace_path)

    def cleanup_pool(self, pool_id: str) -> int:
        """Cleanup all workspaces for a pool.

        Removes all workspaces associated with a pool, regardless of status.

        Args:
            pool_id: Pool ID to cleanup

        Returns:
            Number of workspaces removed
        """
        removed = 0
        to_remove = []

        for key, ws in self._metadata.items():
            if ws.pool_id == pool_id:
                to_remove.append(key)
                self._remove_workspace(Path(ws.workspace_path), ws.workspace_name)
                removed += 1

        for key in to_remove:
            del self._metadata[key]

        # Remove pool directory if empty
        pool_dir = self.workspace_root / pool_id
        if pool_dir.exists():
            try:
                pool_dir.rmdir()
            except OSError:
                pass  # Not empty

        self._save_metadata()
        logger.info(f"Cleaned up {removed} workspaces for pool {pool_id}")

        return removed

    def cleanup_stale(self, max_age_hours: int = 24) -> int:
        """Cleanup workspaces older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of workspaces removed
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = 0
        to_remove = []

        for key, ws in self._metadata.items():
            if ws.created_at < cutoff and ws.status != "active":
                to_remove.append(key)
                self._remove_workspace(Path(ws.workspace_path), ws.workspace_name)
                removed += 1

        for key in to_remove:
            del self._metadata[key]

        self._save_metadata()

        if removed > 0:
            logger.info(f"Cleaned up {removed} stale workspaces")

        return removed

    def cleanup(self) -> int:
        """Cleanup all managed workspaces.

        Returns:
            Number of workspaces removed
        """
        removed = 0

        for key, ws in list(self._metadata.items()):
            self._remove_workspace(Path(ws.workspace_path), ws.workspace_name)
            removed += 1

        self._metadata.clear()
        self._save_metadata()

        # Remove workspace root if empty
        if self.workspace_root.exists():
            try:
                shutil.rmtree(self.workspace_root)
            except OSError:
                pass

        logger.info(f"Cleaned up {removed} workspaces")

        return removed

    def _prune_workspaces(self) -> None:
        """Jujutsu automatically handles stale workspace references.

        Note: Unlike git worktrees, jj workspaces don't need explicit pruning.
        This method is kept for API compatibility but is a no-op.
        """
        # No equivalent needed in jj - workspaces are cleaned up via forget
        pass

    def list_workspaces(self, pool_id: Optional[str] = None) -> List[WorkspaceMetadata]:
        """List all tracked workspaces.

        Args:
            pool_id: Optional pool ID to filter by

        Returns:
            List of WorkspaceMetadata
        """
        workspaces = list(self._metadata.values())

        if pool_id:
            workspaces = [ws for ws in workspaces if ws.pool_id == pool_id]

        return workspaces

    def get_active_count(self, pool_id: Optional[str] = None) -> int:
        """Get count of active workspaces.

        Args:
            pool_id: Optional pool ID to filter by

        Returns:
            Number of active workspaces
        """
        workspaces = self.list_workspaces(pool_id)
        return sum(1 for ws in workspaces if ws.status == "active")


# Backward compatibility aliases
WorktreeMetadata = WorkspaceMetadata
WorktreeError = WorkspaceError
WorktreeManager = WorkspaceManager
DEFAULT_WORKTREE_ROOT = DEFAULT_WORKSPACE_ROOT


__all__ = [
    # New names
    "WorkspaceMetadata",
    "WorkspaceError",
    "WorkspaceManager",
    "DEFAULT_WORKSPACE_ROOT",
    # Backward compatibility
    "WorktreeMetadata",
    "WorktreeError",
    "WorktreeManager",
    "DEFAULT_WORKTREE_ROOT",
]
