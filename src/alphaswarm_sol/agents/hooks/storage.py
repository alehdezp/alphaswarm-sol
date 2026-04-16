"""Hook state persistence for session continuity.

This module provides YAML-based persistence for hook system state,
enabling work state to persist across sessions per PHILOSOPHY.md.

Usage:
    from alphaswarm_sol.agents.hooks import HookStorage, AgentInbox, AgentRole

    storage = HookStorage(Path(".vrs/hooks"))

    # Save inbox state
    storage.save_inbox(inbox, "pool-abc123")

    # Load inbox state (requires bead loader)
    inbox = storage.load_inbox("pool-abc123", AgentRole.ATTACKER, bead_loader)

    # List saved inboxes
    for role in storage.list_inboxes("pool-abc123"):
        print(f"Found inbox for {role}")
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from alphaswarm_sol.agents.hooks import AgentRole
    from alphaswarm_sol.agents.hooks.inbox import AgentInbox, InboxConfig, WorkClaim
    from alphaswarm_sol.beads.schema import VulnerabilityBead


class HookStorage:
    """Persistence for hook system state.

    Provides YAML-based storage for inbox state, enabling session
    continuity. Each pool has a separate hooks directory with
    per-role inbox files.

    Directory structure:
        base_path/
            {pool_id}/
                hooks/
                    attacker_inbox.yaml
                    defender_inbox.yaml
                    verifier_inbox.yaml

    Attributes:
        base_path: Base directory for hook storage

    Usage:
        storage = HookStorage(Path(".vrs/hooks"))

        # Save state
        storage.save_inbox(inbox, "pool-abc")

        # Load state
        def load_bead(bead_id: str) -> VulnerabilityBead:
            return bead_storage.load(bead_id)

        inbox = storage.load_inbox("pool-abc", AgentRole.ATTACKER, load_bead)
    """

    def __init__(self, base_path: Path) -> None:
        """Initialize storage with base path.

        Args:
            base_path: Base directory for hook storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_inbox(self, inbox: "AgentInbox", pool_id: str) -> Path:
        """Save inbox state to YAML.

        Saves the inbox state including:
        - Configuration
        - Pending bead IDs (queue)
        - In-progress work claims
        - Failure counts
        - Completed bead IDs

        Args:
            inbox: AgentInbox to save
            pool_id: ID of the pool

        Returns:
            Path where inbox was saved

        Usage:
            path = storage.save_inbox(inbox, "pool-abc")
            print(f"Saved to {path}")
        """
        path = self._inbox_path(pool_id, inbox.agent_role)
        path.parent.mkdir(parents=True, exist_ok=True)

        state = inbox.to_dict()
        state["saved_at"] = datetime.now().isoformat()
        state["pool_id"] = pool_id

        with open(path, "w") as f:
            yaml.dump(state, f, default_flow_style=False, sort_keys=False)

        return path

    def load_inbox(
        self,
        pool_id: str,
        role: "AgentRole",
        bead_loader: Callable[[str], Optional["VulnerabilityBead"]],
    ) -> Optional["AgentInbox"]:
        """Load inbox state from YAML.

        Reconstructs an AgentInbox from saved state. Requires a bead_loader
        function to resolve bead IDs to VulnerabilityBead objects.

        Args:
            pool_id: ID of the pool
            role: Agent role to load inbox for
            bead_loader: Function that loads a bead by ID

        Returns:
            Reconstructed AgentInbox, or None if not found

        Usage:
            def load_bead(bead_id: str) -> VulnerabilityBead:
                return bead_storage.load(bead_id)

            inbox = storage.load_inbox("pool-abc", AgentRole.ATTACKER, load_bead)
        """
        from alphaswarm_sol.agents.hooks.inbox import AgentInbox, InboxConfig, WorkClaim

        role_value = role.value if hasattr(role, "value") else str(role)
        path = self._inbox_path(pool_id, role_value)

        if not path.exists():
            return None

        with open(path) as f:
            state = yaml.safe_load(f)

        if not state:
            return None

        # Reconstruct config
        config_data = state.get("config", {})
        config = InboxConfig.from_dict(config_data)

        # Create inbox
        inbox = AgentInbox(role, config)

        # Restore failure counts
        inbox._failure_counts = state.get("failure_counts", {})

        # Restore completed history
        inbox._completed = state.get("completed", [])

        # Load and enqueue pending beads
        pending_ids = state.get("pending_bead_ids", [])
        for bead_id in pending_ids:
            bead = bead_loader(bead_id)
            if bead:
                inbox._queue.push(bead)

        # Restore in-progress claims
        in_progress_data = state.get("in_progress", {})
        for bead_id, claim_data in in_progress_data.items():
            bead = bead_loader(bead_id)
            if bead:
                claimed_at = claim_data.get("claimed_at")
                if isinstance(claimed_at, str):
                    claimed_at = datetime.fromisoformat(claimed_at)
                else:
                    claimed_at = datetime.now()

                claim = WorkClaim(
                    bead=bead,
                    agent_role=claim_data.get("agent_role", role_value),
                    claimed_at=claimed_at,
                    attempt=int(claim_data.get("attempt", 1)),
                )
                inbox._in_progress[bead_id] = claim

        return inbox

    def delete_inbox(self, pool_id: str, role: "AgentRole") -> bool:
        """Delete saved inbox state.

        Args:
            pool_id: ID of the pool
            role: Agent role

        Returns:
            True if deleted, False if not found

        Usage:
            storage.delete_inbox("pool-abc", AgentRole.ATTACKER)
        """
        role_value = role.value if hasattr(role, "value") else str(role)
        path = self._inbox_path(pool_id, role_value)

        if path.exists():
            path.unlink()
            return True
        return False

    def delete_pool_hooks(self, pool_id: str) -> int:
        """Delete all hook state for a pool.

        Args:
            pool_id: ID of the pool

        Returns:
            Number of files deleted

        Usage:
            count = storage.delete_pool_hooks("pool-abc")
            print(f"Deleted {count} inbox files")
        """
        hooks_dir = self.base_path / pool_id / "hooks"
        if not hooks_dir.exists():
            return 0

        count = 0
        for file in hooks_dir.glob("*_inbox.yaml"):
            file.unlink()
            count += 1

        # Remove empty directories
        if hooks_dir.exists() and not any(hooks_dir.iterdir()):
            hooks_dir.rmdir()
            pool_dir = self.base_path / pool_id
            if pool_dir.exists() and not any(pool_dir.iterdir()):
                pool_dir.rmdir()

        return count

    def list_inboxes(self, pool_id: str) -> List[str]:
        """List saved inbox roles for a pool.

        Args:
            pool_id: ID of the pool

        Returns:
            List of role names with saved inboxes

        Usage:
            for role in storage.list_inboxes("pool-abc"):
                print(f"Found inbox for {role}")
        """
        hooks_dir = self.base_path / pool_id / "hooks"
        if not hooks_dir.exists():
            return []

        roles = []
        for file in hooks_dir.glob("*_inbox.yaml"):
            role = file.stem.replace("_inbox", "")
            roles.append(role)
        return roles

    def list_pools(self) -> List[str]:
        """List all pools with hook state.

        Returns:
            List of pool IDs

        Usage:
            for pool_id in storage.list_pools():
                print(f"Pool: {pool_id}")
        """
        pools = []
        for item in self.base_path.iterdir():
            if item.is_dir():
                hooks_dir = item / "hooks"
                if hooks_dir.exists() and any(hooks_dir.glob("*_inbox.yaml")):
                    pools.append(item.name)
        return pools

    def inbox_exists(self, pool_id: str, role: "AgentRole") -> bool:
        """Check if inbox state exists.

        Args:
            pool_id: ID of the pool
            role: Agent role

        Returns:
            True if inbox state file exists
        """
        role_value = role.value if hasattr(role, "value") else str(role)
        return self._inbox_path(pool_id, role_value).exists()

    def get_inbox_metadata(self, pool_id: str, role: "AgentRole") -> Optional[Dict[str, Any]]:
        """Get metadata from saved inbox without full load.

        Useful for getting summary info without loading all beads.

        Args:
            pool_id: ID of the pool
            role: Agent role

        Returns:
            Dictionary with metadata, or None if not found

        Usage:
            meta = storage.get_inbox_metadata("pool-abc", AgentRole.ATTACKER)
            if meta:
                print(f"Pending: {len(meta.get('pending_bead_ids', []))}")
        """
        role_value = role.value if hasattr(role, "value") else str(role)
        path = self._inbox_path(pool_id, role_value)

        if not path.exists():
            return None

        with open(path) as f:
            state = yaml.safe_load(f)

        if not state:
            return None

        return {
            "agent_role": state.get("agent_role"),
            "pool_id": state.get("pool_id"),
            "saved_at": state.get("saved_at"),
            "pending_count": len(state.get("pending_bead_ids", [])),
            "in_progress_count": len(state.get("in_progress", {})),
            "completed_count": len(state.get("completed", [])),
            "failure_count": len(state.get("failure_counts", {})),
        }

    def _inbox_path(self, pool_id: str, role: str) -> Path:
        """Get path to inbox YAML file.

        Args:
            pool_id: ID of the pool
            role: Agent role (string)

        Returns:
            Path to inbox file
        """
        return self.base_path / pool_id / "hooks" / f"{role}_inbox.yaml"


# Export all public types
__all__ = [
    "HookStorage",
]
