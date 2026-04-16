"""Bead-Aware Checkpointer for LangGraph Persistence.

Provides deterministic replay capability by storing graph state alongside
bead state. Enables recovery from failures and investigation resumption.

Key Features:
- Checkpoint state maps to VulnerabilityBead lifecycle
- Replay chain reconstruction for deterministic history
- Validation of bead integrity across checkpoints
- JSONL storage format for git-friendly history
- Integration with BeadStorage for unified persistence

Architecture:
    CheckpointState: Checkpoint metadata and serialized state
    BeadCheckpointer: Bead-aware persistence with replay chains
    LangGraph Checkpointer Protocol: Compatible with langgraph.checkpoint

Storage Format:
    {storage_path}/
        {bead_id}/
            checkpoints.jsonl  # Append-only checkpoint log
            latest.json        # Latest checkpoint for fast access

Usage:
    from alphaswarm_sol.adapters.checkpointer import BeadCheckpointer

    # Create checkpointer
    checkpointer = BeadCheckpointer(Path(".langgraph_checkpoints"))

    # Save checkpoint
    checkpoint_id = checkpointer.save(state, "attacker")

    # Load checkpoint
    state = checkpointer.load(checkpoint_id)

    # Get replay chain
    chain = checkpointer.get_replay_chain(checkpoint_id)

    # Cleanup old checkpoints
    removed = checkpointer.cleanup_old_checkpoints(max_age_hours=24)

Phase: 07.1.4-03 LangGraph Adapter with Persistence
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.beads.storage import BeadStorage

# Lazy import for langgraph checkpoint protocol
try:
    from langgraph.checkpoint import (
        BaseCheckpointSaver,
        Checkpoint,
        CheckpointTuple,
    )
    from langchain_core.runnables import RunnableConfig

    HAS_LANGGRAPH_CHECKPOINT = True
except ImportError:
    HAS_LANGGRAPH_CHECKPOINT = False
    BaseCheckpointSaver = object  # type: ignore
    Checkpoint = Dict[str, Any]  # type: ignore
    CheckpointTuple = tuple  # type: ignore
    RunnableConfig = Dict[str, Any]  # type: ignore


@dataclass
class CheckpointState:
    """Checkpoint state for bead replay.

    Attributes:
        checkpoint_id: Unique checkpoint identifier
        bead_id: Associated VulnerabilityBead ID
        graph_state: Serialized VrsState from LangGraph
        timestamp: ISO timestamp of checkpoint creation
        node_executed: Last graph node that executed
        parent_checkpoint_id: Parent checkpoint for replay chain
        bead_hash: Hash of bead state at checkpoint (for validation)

    Example:
        state = CheckpointState(
            checkpoint_id="ckpt-abc123",
            bead_id="VKG-001",
            graph_state={"bead": {...}, "messages": [...]},
            timestamp="2024-01-29T14:00:00Z",
            node_executed="attacker",
            parent_checkpoint_id="ckpt-xyz789",
            bead_hash="abc123...",
        )
    """

    checkpoint_id: str
    bead_id: str
    graph_state: Dict[str, Any]
    timestamp: str
    node_executed: str
    parent_checkpoint_id: Optional[str] = None
    bead_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "bead_id": self.bead_id,
            "graph_state": self.graph_state,
            "timestamp": self.timestamp,
            "node_executed": self.node_executed,
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "bead_hash": self.bead_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointState":
        """Create CheckpointState from dictionary."""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            bead_id=data["bead_id"],
            graph_state=data["graph_state"],
            timestamp=data["timestamp"],
            node_executed=data["node_executed"],
            parent_checkpoint_id=data.get("parent_checkpoint_id"),
            bead_hash=data.get("bead_hash", ""),
        )

    def to_jsonl(self) -> str:
        """Convert to JSONL format (single line)."""
        return json.dumps(self.to_dict(), separators=(",", ":"))


class BeadCheckpointer:
    """Bead-aware checkpointer for LangGraph persistence.

    Stores graph state alongside bead state for deterministic replay.
    Maintains replay chains for investigation history reconstruction.

    Storage Structure:
        {storage_path}/
            {bead_id}/
                checkpoints.jsonl  # Append-only checkpoint log
                latest.json        # Latest checkpoint cache

    Example:
        checkpointer = BeadCheckpointer(Path(".langgraph_checkpoints"))

        # Save checkpoint
        checkpoint_id = checkpointer.save(state, "attacker")

        # Load checkpoint
        state = checkpointer.load(checkpoint_id)

        # Get replay chain
        chain = checkpointer.get_replay_chain(checkpoint_id)
    """

    def __init__(
        self,
        storage_path: Path,
        bead_storage: Optional["BeadStorage"] = None,
    ):
        """Initialize checkpointer.

        Args:
            storage_path: Directory for checkpoint storage
            bead_storage: Optional BeadStorage for bead state validation
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.bead_storage = bead_storage

        # Track latest checkpoint per bead
        self._latest_checkpoints: Dict[str, str] = {}

    def save(self, state: Dict[str, Any], node: str) -> str:
        """Save checkpoint for current state.

        Args:
            state: VrsState to checkpoint
            node: Graph node that was executed

        Returns:
            Checkpoint ID
        """
        # Extract bead ID from state
        bead_id = state.get("bead", {}).get("id", "unknown")

        # Generate checkpoint ID
        checkpoint_id = f"ckpt-{uuid.uuid4().hex[:12]}"

        # Get parent checkpoint
        parent_checkpoint_id = self._latest_checkpoints.get(bead_id)

        # Compute bead hash for validation
        bead_hash = self._compute_bead_hash(state.get("bead", {}))

        # Create checkpoint state
        checkpoint_state = CheckpointState(
            checkpoint_id=checkpoint_id,
            bead_id=bead_id,
            graph_state=state,
            timestamp=datetime.utcnow().isoformat(),
            node_executed=node,
            parent_checkpoint_id=parent_checkpoint_id,
            bead_hash=bead_hash,
        )

        # Save to storage
        self._write_checkpoint(checkpoint_state)

        # Update latest checkpoint
        self._latest_checkpoints[bead_id] = checkpoint_id

        return checkpoint_id

    def load(self, checkpoint_id: str) -> CheckpointState:
        """Load checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint ID to load

        Returns:
            CheckpointState

        Raises:
            FileNotFoundError: If checkpoint not found
            ValueError: If checkpoint validation fails
        """
        # Find checkpoint in storage
        checkpoint_state = self._read_checkpoint(checkpoint_id)

        # Validate bead still exists
        if self.bead_storage:
            bead = self.bead_storage.get_bead(checkpoint_state.bead_id)
            if not bead:
                raise ValueError(
                    f"Bead {checkpoint_state.bead_id} not found for checkpoint {checkpoint_id}"
                )

        # Validate checkpoint
        if not self.validate_checkpoint(checkpoint_state):
            raise ValueError(f"Checkpoint {checkpoint_id} validation failed")

        return checkpoint_state

    def list_checkpoints(self, bead_id: str) -> List[CheckpointState]:
        """List all checkpoints for a bead.

        Args:
            bead_id: VulnerabilityBead ID

        Returns:
            List of CheckpointState ordered by timestamp (newest first)
        """
        bead_dir = self.storage_path / bead_id
        if not bead_dir.exists():
            return []

        checkpoint_file = bead_dir / "checkpoints.jsonl"
        if not checkpoint_file.exists():
            return []

        # Read all checkpoints from JSONL
        checkpoints = []
        with checkpoint_file.open("r") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    checkpoints.append(CheckpointState.from_dict(data))

        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)

        return checkpoints

    def get_replay_chain(self, checkpoint_id: str) -> List[CheckpointState]:
        """Build replay chain from initial checkpoint to given checkpoint.

        Args:
            checkpoint_id: Target checkpoint ID

        Returns:
            List of CheckpointState from initial to target (chronological order)

        Example:
            chain = checkpointer.get_replay_chain("ckpt-xyz789")
            # Returns: [ckpt-abc123, ckpt-def456, ckpt-xyz789]
        """
        # Load target checkpoint
        target = self.load(checkpoint_id)

        # Build chain by following parent links
        chain = [target]
        current = target

        while current.parent_checkpoint_id:
            parent = self.load(current.parent_checkpoint_id)
            chain.insert(0, parent)
            current = parent

        return chain

    def cleanup_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """Remove checkpoints older than max_age.

        Args:
            max_age_hours: Maximum checkpoint age in hours

        Returns:
            Number of checkpoints removed
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed_count = 0

        # Scan all bead directories
        for bead_dir in self.storage_path.iterdir():
            if not bead_dir.is_dir():
                continue

            checkpoint_file = bead_dir / "checkpoints.jsonl"
            if not checkpoint_file.exists():
                continue

            # Read and filter checkpoints
            kept_checkpoints = []
            with checkpoint_file.open("r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        checkpoint_time = datetime.fromisoformat(data["timestamp"])

                        if checkpoint_time >= cutoff_time:
                            kept_checkpoints.append(line)
                        else:
                            removed_count += 1

            # Rewrite checkpoint file with kept checkpoints
            with checkpoint_file.open("w") as f:
                f.writelines(kept_checkpoints)

        return removed_count

    def validate_checkpoint(self, state: CheckpointState) -> bool:
        """Validate checkpoint integrity.

        Args:
            state: CheckpointState to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not state.checkpoint_id or not state.bead_id:
            return False

        # Validate graph state structure
        if not isinstance(state.graph_state, dict):
            return False

        required_keys = ["bead", "messages", "current_agent", "evidence"]
        if not all(key in state.graph_state for key in required_keys):
            return False

        # Validate bead hash if available
        if state.bead_hash:
            current_hash = self._compute_bead_hash(state.graph_state.get("bead", {}))
            if current_hash != state.bead_hash:
                return False

        return True

    def _compute_bead_hash(self, bead_data: Dict[str, Any]) -> str:
        """Compute hash of bead data for validation.

        Args:
            bead_data: Serialized bead dictionary

        Returns:
            SHA256 hash hex string
        """
        bead_json = json.dumps(bead_data, sort_keys=True)
        return hashlib.sha256(bead_json.encode()).hexdigest()

    def _write_checkpoint(self, state: CheckpointState) -> None:
        """Write checkpoint to storage.

        Args:
            state: CheckpointState to write
        """
        bead_dir = self.storage_path / state.bead_id
        bead_dir.mkdir(parents=True, exist_ok=True)

        # Append to JSONL log
        checkpoint_file = bead_dir / "checkpoints.jsonl"
        with checkpoint_file.open("a") as f:
            f.write(state.to_jsonl() + "\n")

        # Update latest cache
        latest_file = bead_dir / "latest.json"
        with latest_file.open("w") as f:
            json.dump(state.to_dict(), f, indent=2)

    def _read_checkpoint(self, checkpoint_id: str) -> CheckpointState:
        """Read checkpoint from storage.

        Args:
            checkpoint_id: Checkpoint ID to read

        Returns:
            CheckpointState

        Raises:
            FileNotFoundError: If checkpoint not found
        """
        # Search all bead directories for checkpoint
        for bead_dir in self.storage_path.iterdir():
            if not bead_dir.is_dir():
                continue

            checkpoint_file = bead_dir / "checkpoints.jsonl"
            if not checkpoint_file.exists():
                continue

            # Scan JSONL for matching checkpoint
            with checkpoint_file.open("r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data["checkpoint_id"] == checkpoint_id:
                            return CheckpointState.from_dict(data)

        raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")


# LangGraph Checkpointer Protocol Implementation
# (Optional - only if langgraph.checkpoint is available)

if HAS_LANGGRAPH_CHECKPOINT:

    class LangGraphBeadCheckpointer(BaseCheckpointSaver):
        """LangGraph-compatible checkpointer using BeadCheckpointer.

        Implements the langgraph.checkpoint.BaseCheckpointSaver protocol
        for seamless integration with LangGraph graphs.

        Example:
            checkpointer = LangGraphBeadCheckpointer(Path(".checkpoints"))
            graph = StateGraph(...).compile(checkpointer=checkpointer)
        """

        def __init__(self, storage_path: Path):
            """Initialize LangGraph checkpointer.

            Args:
                storage_path: Directory for checkpoint storage
            """
            super().__init__()
            self.bead_checkpointer = BeadCheckpointer(storage_path)

        def get(
            self, config: RunnableConfig
        ) -> Optional[CheckpointTuple]:  # type: ignore
            """Get checkpoint for config.

            Args:
                config: Runnable configuration with checkpoint ID

            Returns:
                CheckpointTuple or None if not found
            """
            checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
            if not checkpoint_id:
                return None

            try:
                state = self.bead_checkpointer.load(checkpoint_id)
                checkpoint: Checkpoint = {
                    "v": 1,
                    "id": state.checkpoint_id,
                    "ts": state.timestamp,
                    "channel_values": state.graph_state,
                }
                return CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata={"node": state.node_executed},
                )
            except FileNotFoundError:
                return None

        def put(
            self, config: RunnableConfig, checkpoint: Checkpoint
        ) -> RunnableConfig:  # type: ignore
            """Save checkpoint.

            Args:
                config: Runnable configuration
                checkpoint: Checkpoint to save

            Returns:
                Updated configuration with checkpoint ID
            """
            node = config.get("configurable", {}).get("node", "unknown")
            state = checkpoint.get("channel_values", {})

            checkpoint_id = self.bead_checkpointer.save(state, node)

            # Update config with checkpoint ID
            updated_config = config.copy()
            if "configurable" not in updated_config:
                updated_config["configurable"] = {}
            updated_config["configurable"]["checkpoint_id"] = checkpoint_id

            return updated_config

        def list(self, config: RunnableConfig) -> Iterator[CheckpointTuple]:  # type: ignore
            """List checkpoints for config.

            Args:
                config: Runnable configuration with bead ID

            Yields:
                CheckpointTuple for each checkpoint
            """
            bead_id = config.get("configurable", {}).get("bead_id")
            if not bead_id:
                return

            checkpoints = self.bead_checkpointer.list_checkpoints(bead_id)

            for state in checkpoints:
                checkpoint: Checkpoint = {
                    "v": 1,
                    "id": state.checkpoint_id,
                    "ts": state.timestamp,
                    "channel_values": state.graph_state,
                }
                yield CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata={"node": state.node_executed},
                )
