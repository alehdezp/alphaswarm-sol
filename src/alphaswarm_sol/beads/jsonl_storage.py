"""JSONL storage for beads following steveyegge pattern.

Beads are stored in .beads/index.jsonl as append-only JSONL.
Each line is a complete bead state (not a diff).
This is git-friendly and optimized for AI workflows.

Usage:
    storage = BeadJSONLStorage(Path(".beads"))
    bead_id = storage.create(title="Check reentrancy", severity="high")
    storage.update(bead_id, status="in_progress")
    beads = storage.list(status="open")
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BeadEntry:
    """A single bead entry for storage.

    Following steveyegge pattern:
    - Hash-based IDs (bd-{hash[:8]})
    - Status tracking for workflow
    - Blockers for dependency management
    - Work state for resumption
    """
    id: str
    title: str
    status: str = "open"  # open, in_progress, complete, blocked
    severity: str = "medium"  # critical, high, medium, low
    priority: int = 0  # 0 = highest
    pattern_id: Optional[str] = None
    location: Optional[str] = None  # file:function
    parent_id: Optional[str] = None
    blockers: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    agent_id: Optional[str] = None
    work_state: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None

    def to_jsonl(self) -> str:
        """Serialize to JSONL line."""
        return json.dumps(asdict(self))

    @classmethod
    def from_jsonl(cls, line: str) -> "BeadEntry":
        """Deserialize from JSONL line."""
        data = json.loads(line)
        return cls(**data)


class BeadJSONLStorage:
    """JSONL-based bead storage.

    Stores beads in .beads/index.jsonl as append-only log.
    Maintains in-memory index of latest state per bead.
    """

    def __init__(self, beads_dir: Path):
        """Initialize storage.

        Args:
            beads_dir: Directory for beads (typically .beads/)
        """
        self.beads_dir = beads_dir
        self.index_file = beads_dir / "index.jsonl"
        self._beads: Dict[str, BeadEntry] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load all beads from index file."""
        self.beads_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            self.index_file.touch()
            return

        with open(self.index_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    bead = BeadEntry.from_jsonl(line)
                    self._beads[bead.id] = bead

    def _generate_id(self, title: str) -> str:
        """Generate hash-based bead ID."""
        timestamp = datetime.now().isoformat()
        content = f"{title}:{timestamp}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
        return f"bd-{hash_val}"

    def _append_to_index(self, bead: BeadEntry) -> None:
        """Append bead to index file."""
        with open(self.index_file, "a") as f:
            f.write(bead.to_jsonl() + "\n")

    def create(
        self,
        title: str,
        severity: str = "medium",
        pattern_id: Optional[str] = None,
        location: Optional[str] = None,
        priority: int = 0,
        parent_id: Optional[str] = None,
    ) -> str:
        """Create a new bead.

        Args:
            title: Brief description of investigation
            severity: critical/high/medium/low
            pattern_id: Optional pattern that triggered this
            location: Optional file:function location
            priority: Priority (0 = highest)
            parent_id: Optional parent bead for hierarchy

        Returns:
            Bead ID (bd-{hash})
        """
        bead_id = self._generate_id(title)
        bead = BeadEntry(
            id=bead_id,
            title=title,
            severity=severity,
            pattern_id=pattern_id,
            location=location,
            priority=priority,
            parent_id=parent_id,
        )
        self._beads[bead_id] = bead
        self._append_to_index(bead)
        return bead_id

    def update(
        self,
        bead_id: str,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        agent_id: Optional[str] = None,
        work_state: Optional[Dict[str, Any]] = None,
        blocked_by: Optional[str] = None,
    ) -> BeadEntry:
        """Update a bead's state.

        Args:
            bead_id: ID of bead to update
            status: New status (open/in_progress/complete/blocked)
            notes: Additional notes
            agent_id: ID of agent working on this
            work_state: State for resumption
            blocked_by: ID of blocking bead

        Returns:
            Updated bead entry
        """
        if bead_id not in self._beads:
            raise ValueError(f"Bead not found: {bead_id}")

        bead = self._beads[bead_id]

        if status:
            bead.status = status
        if notes:
            bead.notes = notes
        if agent_id:
            bead.agent_id = agent_id
        if work_state:
            bead.work_state = work_state
        if blocked_by and blocked_by not in bead.blockers:
            bead.blockers.append(blocked_by)

        bead.updated_at = datetime.now().isoformat()
        self._append_to_index(bead)
        return bead

    def get(self, bead_id: str) -> Optional[BeadEntry]:
        """Get a bead by ID."""
        return self._beads.get(bead_id)

    def list(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> List[BeadEntry]:
        """List beads with optional filtering.

        Args:
            status: Filter by status
            severity: Filter by severity
            parent_id: Filter by parent

        Returns:
            List of matching beads, sorted by priority
        """
        beads = list(self._beads.values())

        if status:
            beads = [b for b in beads if b.status == status]
        if severity:
            beads = [b for b in beads if b.severity == severity]
        if parent_id:
            beads = [b for b in beads if b.parent_id == parent_id]

        # Sort by priority (lower = higher priority), then by created_at
        return sorted(beads, key=lambda b: (b.priority, b.created_at))

    def get_ready(self) -> List[BeadEntry]:
        """Get beads ready for work (open, not blocked)."""
        ready = []
        for bead in self._beads.values():
            if bead.status == "open" and not bead.blockers:
                ready.append(bead)
            elif bead.status == "open" and bead.blockers:
                # Check if all blockers are complete
                all_clear = all(
                    self._beads.get(b, BeadEntry(id="", title="")).status == "complete"
                    for b in bead.blockers
                )
                if all_clear:
                    ready.append(bead)
        return sorted(ready, key=lambda b: (b.priority, b.created_at))
