"""Persistent storage for vulnerability beads.

This module provides file-based storage for VulnerabilityBead objects,
allowing beads to persist between CLI invocations.

Supports both standalone storage and pool-integrated storage:
- Standalone: .vrs/beads/{bead_id}.json
- Pool-aware: .vrs/pools/{pool_id}/beads/{bead_id}.yaml

Event Sourcing (Phase 7.1.1):
All mutations emit events to an append-only log for auditing and replay.
Events are stored in JSONL format for git-friendly history.

Usage:
    from alphaswarm_sol.beads.storage import BeadStorage

    # Create storage instance
    storage = BeadStorage(Path(".vrs/beads"))

    # Save a bead (emits bead_created event)
    storage.save_bead(bead)

    # Load a bead
    bead = storage.get_bead("VKG-0001-abc123")

    # List all beads
    all_beads = storage.list_beads()

    # Pool-aware operations (ORCH-04/08)
    storage.save_to_pool(bead, "audit-vault-2026-01-20")
    beads = storage.list_pool_beads("audit-vault-2026-01-20")
    resumable = storage.get_resumable_beads("audit-vault-2026-01-20")

    # Replay beads from event log
    replayed = storage.replay_beads()
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING

import yaml

from .schema import VulnerabilityBead
from .types import BeadStatus, Severity

if TYPE_CHECKING:
    from .event_store import BeadEventStore


class BeadStorage:
    """File-based storage for vulnerability beads.

    Stores beads as JSON files in a directory structure.
    Each bead is saved as {bead_id}.json.

    Event sourcing: All mutations emit events to an append-only log
    for auditing, debugging, and state reconstruction.

    Example:
        storage = BeadStorage(Path(".vrs/beads"))
        storage.save_bead(bead)
        loaded = storage.get_bead(bead.id)

        # Replay from event log
        replayed = storage.replay_beads()
    """

    def __init__(
        self,
        path: Path,
        event_store: Optional["BeadEventStore"] = None,
        enable_events: bool = True,
    ):
        """Initialize storage.

        Args:
            path: Directory path for storing beads.
                  Will be created if it doesn't exist.
            event_store: Optional event store for event sourcing.
                        If None and enable_events=True, creates default.
            enable_events: Whether to emit events (default True).
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._enable_events = enable_events

        # Initialize event store
        if event_store is not None:
            self.event_store = event_store
        elif enable_events:
            from .event_store import BeadEventStore

            self.event_store = BeadEventStore(self.path)
        else:
            self.event_store = None  # type: ignore

    def _record_event(
        self,
        bead_id: str,
        event_type: str,
        payload: Dict[str, Any],
        actor: str = "system",
        pool_id: Optional[str] = None,
    ) -> None:
        """Record an event to the event store.

        Args:
            bead_id: Bead identifier
            event_type: Type of event
            payload: Event payload
            actor: Who/what caused the event
            pool_id: Optional pool association
        """
        if not self._enable_events or self.event_store is None:
            return

        from .event_store import BeadEvent

        event = BeadEvent(
            bead_id=bead_id,
            event_type=event_type,
            payload=payload,
            actor=actor,
            pool_id=pool_id,
        )
        self.event_store.append_event(event)

    def save_bead(
        self, bead: VulnerabilityBead, actor: str = "system"
    ) -> Path:
        """Save a bead to storage.

        Args:
            bead: VulnerabilityBead to save
            actor: Who/what is saving the bead (for event logging)

        Returns:
            Path to saved file
        """
        bead_path = self.path / f"{bead.id}.json"
        is_update = bead_path.exists()

        with open(bead_path, "w", encoding="utf-8") as f:
            json.dump(bead.to_dict(), f, indent=2)

        # Record event
        event_type = "bead_updated" if is_update else "bead_created"
        self._record_event(
            bead_id=bead.id,
            event_type=event_type,
            payload=bead.to_dict(),
            actor=actor,
            pool_id=bead.pool_id,
        )

        return bead_path

    def get_bead(self, bead_id: str) -> Optional[VulnerabilityBead]:
        """Load a bead by ID.

        Args:
            bead_id: Unique bead identifier

        Returns:
            VulnerabilityBead if found, None otherwise
        """
        bead_path = self.path / f"{bead_id}.json"
        if not bead_path.exists():
            return None

        with open(bead_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return VulnerabilityBead.from_dict(data)

    def list_beads(self) -> List[VulnerabilityBead]:
        """List all beads in storage.

        Returns:
            List of all VulnerabilityBead objects
        """
        beads = []
        for path in sorted(self.path.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                beads.append(VulnerabilityBead.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                # Skip corrupted files
                import sys

                print(f"Warning: Skipping corrupted bead file {path}: {e}", file=sys.stderr)
        return beads

    def list_beads_by_status(self, status: BeadStatus) -> List[VulnerabilityBead]:
        """List beads filtered by status.

        Args:
            status: BeadStatus to filter by

        Returns:
            List of matching VulnerabilityBead objects
        """
        all_beads = self.list_beads()
        return [b for b in all_beads if b.status == status]

    def list_beads_by_severity(self, severity: Severity) -> List[VulnerabilityBead]:
        """List beads filtered by severity.

        Args:
            severity: Severity to filter by

        Returns:
            List of matching VulnerabilityBead objects
        """
        all_beads = self.list_beads()
        return [b for b in all_beads if b.severity == severity]

    def list_beads_by_class(self, vulnerability_class: str) -> List[VulnerabilityBead]:
        """List beads filtered by vulnerability class.

        Args:
            vulnerability_class: Class name (e.g., "reentrancy")

        Returns:
            List of matching VulnerabilityBead objects
        """
        all_beads = self.list_beads()
        return [b for b in all_beads if b.vulnerability_class == vulnerability_class]

    def delete_bead(self, bead_id: str, actor: str = "system") -> bool:
        """Delete a bead from storage.

        Args:
            bead_id: Unique bead identifier
            actor: Who/what is deleting the bead (for event logging)

        Returns:
            True if deleted, False if not found
        """
        bead_path = self.path / f"{bead_id}.json"
        if bead_path.exists():
            bead_path.unlink()

            # Record deletion event
            self._record_event(
                bead_id=bead_id,
                event_type="bead_deleted",
                payload={},
                actor=actor,
            )
            return True
        return False

    def clear(self) -> int:
        """Clear all beads from storage.

        Returns:
            Count of beads deleted
        """
        count = 0
        for path in self.path.glob("*.json"):
            path.unlink()
            count += 1
        return count

    def count(self) -> int:
        """Count beads in storage.

        Returns:
            Total number of beads
        """
        return len(list(self.path.glob("*.json")))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics.

        Returns:
            Dict with counts by status, severity, and class
        """
        beads = self.list_beads()

        by_status: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_class: Dict[str, int] = {}

        for bead in beads:
            # Count by status
            status = bead.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # Count by severity
            severity = bead.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

            # Count by class
            vuln_class = bead.vulnerability_class
            by_class[vuln_class] = by_class.get(vuln_class, 0) + 1

        return {
            "total": len(beads),
            "by_status": by_status,
            "by_severity": by_severity,
            "by_class": by_class,
        }

    def exists(self, bead_id: str) -> bool:
        """Check if a bead exists.

        Args:
            bead_id: Unique bead identifier

        Returns:
            True if bead exists
        """
        bead_path = self.path / f"{bead_id}.json"
        return bead_path.exists()

    # =========================================================================
    # POOL-AWARE OPERATIONS (ORCH-04/08)
    # =========================================================================

    def _get_pool_beads_dir(self, pool_id: str) -> Path:
        """Get the beads directory for a pool.

        Pool beads are stored at: .vrs/pools/{pool_id}/beads/

        Args:
            pool_id: Pool identifier

        Returns:
            Path to pool's beads directory
        """
        # Navigate from .vrs/beads to .vrs/pools/{pool_id}/beads
        vkg_root = self.path.parent  # .vkg
        return vkg_root / "pools" / pool_id / "beads"

    def save_to_pool(
        self,
        bead: VulnerabilityBead,
        pool_id: str,
        use_yaml: bool = True,
        actor: str = "system",
    ) -> Path:
        """Save a bead to a pool's beads directory.

        Saves the bead in minimal YAML format for human readability,
        and updates the bead's pool_id association.

        Args:
            bead: VulnerabilityBead to save
            pool_id: Pool identifier to associate with
            use_yaml: Use YAML format (default True, more human-readable)
            actor: Who/what is saving the bead (for event logging)

        Returns:
            Path to saved file

        Usage:
            storage.save_to_pool(bead, "audit-vault-2026-01-20")
            # Saves to .vrs/pools/audit-vault-2026-01-20/beads/VKG-001.yaml
        """
        pool_beads_dir = self._get_pool_beads_dir(pool_id)
        pool_beads_dir.mkdir(parents=True, exist_ok=True)

        # Update bead's pool association
        bead.pool_id = pool_id
        bead.last_updated = datetime.now()

        if use_yaml:
            bead_path = pool_beads_dir / f"{bead.id}.yaml"
            with open(bead_path, "w", encoding="utf-8") as f:
                f.write(bead.to_minimal_yaml())
        else:
            bead_path = pool_beads_dir / f"{bead.id}.json"
            with open(bead_path, "w", encoding="utf-8") as f:
                json.dump(bead.to_dict(), f, indent=2)

        # Record pool assignment event
        self._record_event(
            bead_id=bead.id,
            event_type="pool_assigned",
            payload=bead.to_dict(),
            actor=actor,
            pool_id=pool_id,
        )

        return bead_path

    def load_from_pool(
        self, bead_id: str, pool_id: str
    ) -> Optional[VulnerabilityBead]:
        """Load a bead from a pool's beads directory.

        Args:
            bead_id: Unique bead identifier
            pool_id: Pool identifier

        Returns:
            VulnerabilityBead if found, None otherwise

        Usage:
            bead = storage.load_from_pool("VKG-001", "audit-vault-2026-01-20")
        """
        pool_beads_dir = self._get_pool_beads_dir(pool_id)

        # Try YAML first (preferred format)
        yaml_path = pool_beads_dir / f"{bead_id}.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return self._bead_from_minimal_yaml(data, bead_id)

        # Fall back to JSON
        json_path = pool_beads_dir / f"{bead_id}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return VulnerabilityBead.from_dict(data)

        return None

    def _bead_from_minimal_yaml(
        self, data: Dict[str, Any], bead_id: str
    ) -> VulnerabilityBead:
        """Reconstruct bead from minimal YAML data.

        The minimal YAML format doesn't include all fields, so we need
        to reconstruct with defaults. For full data, load from main storage.

        Args:
            data: Parsed YAML data
            bead_id: Bead ID for lookup in main storage

        Returns:
            VulnerabilityBead (may have partial data)
        """
        # Try to load full bead from main storage first
        full_bead = self.get_bead(bead_id)
        if full_bead:
            # Update with pool data
            full_bead.pool_id = data.get("pool_id")
            full_bead.human_flag = data.get("human_flag", False)
            full_bead.status = BeadStatus(data.get("status", "pending"))

            # Update debate fields if present
            debate = data.get("debate", {})
            if debate:
                full_bead.debate_summary = debate.get("summary")
                full_bead.attacker_claim = debate.get("attacker_claim")
                full_bead.defender_claim = debate.get("defender_claim")
                full_bead.verifier_verdict = debate.get("verifier_verdict")

            # Update work state if present
            work = data.get("work_state", {})
            if work:
                full_bead.work_state = work.get("state")
                full_bead.last_agent = work.get("last_agent")
                if work.get("last_updated"):
                    full_bead.last_updated = datetime.fromisoformat(
                        work["last_updated"]
                    )

            return full_bead

        # No full bead found - create minimal placeholder
        from .schema import (
            CodeSnippet,
            PatternContext,
            InvestigationGuide,
            TestContext,
        )

        location = data.get("location", {})
        return VulnerabilityBead(
            id=data.get("id", bead_id),
            vulnerability_class=data.get("vulnerability_class", "unknown"),
            pattern_id=data.get("pattern_id", ""),
            severity=Severity(data.get("severity", "medium")),
            confidence=data.get("confidence", 0.0),
            status=BeadStatus(data.get("status", "pending")),
            vulnerable_code=CodeSnippet(
                source="",
                file_path=location.get("file", ""),
                start_line=int(location.get("lines", "0-0").split("-")[0]),
                end_line=int(location.get("lines", "0-0").split("-")[-1]),
                function_name=location.get("function"),
                contract_name=location.get("contract"),
            ),
            related_code=[],
            full_contract=None,
            inheritance_chain=[],
            pattern_context=PatternContext(
                pattern_name="",
                pattern_description="",
                why_flagged=data.get("why_flagged", ""),
                matched_properties=[],
                evidence_lines=[],
            ),
            investigation_guide=InvestigationGuide(
                steps=[],
                questions_to_answer=[],
                common_false_positives=[],
                key_indicators=[],
                safe_patterns=[],
            ),
            test_context=TestContext(
                scaffold_code="",
                attack_scenario="",
                setup_requirements=[],
                expected_outcome="",
            ),
            similar_exploits=[],
            fix_recommendations=[],
            pool_id=data.get("pool_id"),
            human_flag=data.get("human_flag", False),
        )

    def list_pool_beads(self, pool_id: str) -> List[VulnerabilityBead]:
        """List all beads in a pool's beads directory.

        Args:
            pool_id: Pool identifier

        Returns:
            List of VulnerabilityBead objects

        Usage:
            beads = storage.list_pool_beads("audit-vault-2026-01-20")
        """
        pool_beads_dir = self._get_pool_beads_dir(pool_id)
        if not pool_beads_dir.exists():
            return []

        beads = []

        # Load YAML beads
        for path in sorted(pool_beads_dir.glob("*.yaml")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                bead_id = path.stem
                beads.append(self._bead_from_minimal_yaml(data, bead_id))
            except (yaml.YAMLError, KeyError) as e:
                import sys
                print(
                    f"Warning: Skipping corrupted pool bead file {path}: {e}",
                    file=sys.stderr,
                )

        # Load JSON beads (fallback format)
        for path in sorted(pool_beads_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                beads.append(VulnerabilityBead.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                import sys
                print(
                    f"Warning: Skipping corrupted pool bead file {path}: {e}",
                    file=sys.stderr,
                )

        return beads

    def update_work_state(
        self,
        bead_id: str,
        pool_id: str,
        work_state: Dict[str, Any],
        agent_id: str,
    ) -> bool:
        """Update work state for a bead (for agent resumption).

        This is used by agents to persist their state so they can
        resume work on a bead if interrupted (ORCH-08).

        Args:
            bead_id: Bead identifier
            pool_id: Pool identifier
            work_state: State dictionary for agent resumption
            agent_id: Identifier of the agent updating state

        Returns:
            True if updated, False if bead not found

        Usage:
            storage.update_work_state(
                "VKG-001",
                "audit-vault-2026-01-20",
                {"step": 2, "findings": [...], "incomplete": True},
                "attacker-agent-001"
            )
        """
        bead = self.load_from_pool(bead_id, pool_id)
        if not bead:
            return False

        bead.work_state = work_state
        bead.last_agent = agent_id
        bead.last_updated = datetime.now()

        # Save without emitting pool_assigned (use _save_to_pool_internal)
        # to avoid duplicate events
        self._save_to_pool_internal(bead, pool_id)

        # Record work state update event
        self._record_event(
            bead_id=bead_id,
            event_type="work_state_updated",
            payload={
                "work_state": work_state,
                "last_agent": agent_id,
            },
            actor=agent_id,
            pool_id=pool_id,
        )

        return True

    def _save_to_pool_internal(
        self, bead: VulnerabilityBead, pool_id: str, use_yaml: bool = True
    ) -> Path:
        """Internal save to pool without emitting events.

        Used by update_work_state to avoid duplicate events.
        """
        pool_beads_dir = self._get_pool_beads_dir(pool_id)
        pool_beads_dir.mkdir(parents=True, exist_ok=True)

        if use_yaml:
            bead_path = pool_beads_dir / f"{bead.id}.yaml"
            with open(bead_path, "w", encoding="utf-8") as f:
                f.write(bead.to_minimal_yaml())
        else:
            bead_path = pool_beads_dir / f"{bead.id}.json"
            with open(bead_path, "w", encoding="utf-8") as f:
                json.dump(bead.to_dict(), f, indent=2)

        return bead_path

    def get_resumable_beads(self, pool_id: str) -> List[VulnerabilityBead]:
        """Get beads with incomplete work state (for agent resumption).

        Returns beads that have work_state set and are in an
        intermediate status (INVESTIGATING).

        Args:
            pool_id: Pool identifier

        Returns:
            List of beads that can be resumed

        Usage:
            resumable = storage.get_resumable_beads("audit-vault-2026-01-20")
            for bead in resumable:
                print(f"{bead.id}: last worked on by {bead.last_agent}")
        """
        all_beads = self.list_pool_beads(pool_id)
        return [
            b
            for b in all_beads
            if b.work_state is not None
            and b.status == BeadStatus.INVESTIGATING
        ]

    def list_flagged_for_human(self, pool_id: str) -> List[VulnerabilityBead]:
        """Get beads flagged for human review in a pool.

        These are beads where debate outcome was inconclusive
        and requires human judgment (ORCH-08).

        Args:
            pool_id: Pool identifier

        Returns:
            List of beads needing human review

        Usage:
            flagged = storage.list_flagged_for_human("audit-vault-2026-01-20")
            print(f"{len(flagged)} beads need human review")
        """
        all_beads = self.list_pool_beads(pool_id)
        return [
            b
            for b in all_beads
            if b.human_flag or b.status == BeadStatus.FLAGGED_FOR_HUMAN
        ]

    def list_pools_with_beads(self) -> List[str]:
        """List all pools that have beads stored.

        Returns:
            List of pool IDs with beads

        Usage:
            pools = storage.list_pools_with_beads()
            for pool_id in pools:
                count = len(storage.list_pool_beads(pool_id))
                print(f"{pool_id}: {count} beads")
        """
        vkg_root = self.path.parent
        pools_dir = vkg_root / "pools"
        if not pools_dir.exists():
            return []

        pools = []
        for pool_dir in sorted(pools_dir.iterdir()):
            if pool_dir.is_dir():
                beads_dir = pool_dir / "beads"
                if beads_dir.exists() and any(beads_dir.iterdir()):
                    pools.append(pool_dir.name)

        return pools

    # =========================================================================
    # EVENT SOURCING (Phase 7.1.1)
    # =========================================================================

    def replay_beads(
        self,
        pool_id: Optional[str] = None,
        bead_id: Optional[str] = None,
    ) -> Dict[str, VulnerabilityBead]:
        """Replay bead state from event log.

        Reconstructs bead state by replaying all events in order.
        Useful for audits, recovery, and debugging.

        Args:
            pool_id: Optional pool ID to use pool-specific event store
            bead_id: Optional filter to replay only a specific bead

        Returns:
            Dictionary mapping bead_id to reconstructed VulnerabilityBead

        Usage:
            # Replay all beads
            beads = storage.replay_beads()

            # Replay specific bead
            beads = storage.replay_beads(bead_id="VKG-001")

            # Replay from pool event store
            beads = storage.replay_beads(pool_id="audit-2026-01-20")
        """
        if not self._enable_events or self.event_store is None:
            return {}

        if pool_id:
            # Use pool-specific event store
            from .event_store import BeadEventStore

            pool_store = BeadEventStore(self.path, pool_id=pool_id)
            return pool_store.replay(bead_id=bead_id)
        else:
            return self.event_store.replay(bead_id=bead_id)

    def get_event_history(
        self,
        bead_id: Optional[str] = None,
        pool_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get event history for beads.

        Args:
            bead_id: Optional filter by bead ID
            pool_id: Optional pool ID to use pool-specific event store

        Returns:
            List of event dictionaries in chronological order
        """
        if not self._enable_events or self.event_store is None:
            return []

        if pool_id:
            from .event_store import BeadEventStore

            pool_store = BeadEventStore(self.path, pool_id=pool_id)
            events = pool_store.list_events(bead_id=bead_id)
        else:
            events = self.event_store.list_events(bead_id=bead_id)

        return [e.to_dict() for e in events]


# Export for module
__all__ = ["BeadStorage"]
