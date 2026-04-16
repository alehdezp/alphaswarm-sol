"""Tests for bead event store and event sourcing.

Tests validate:
- Event log is append-only (no rewrites)
- Event count increases on mutations
- Replay reconstructs bead state equivalent to stored beads
- Pool-specific event log paths work correctly
- Event ordering is deterministic

Phase 7.1.1: Production Orchestration Hardening
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from alphaswarm_sol.beads.event_store import BeadEvent, BeadEventStore, get_pool_event_store
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.storage import BeadStorage
from alphaswarm_sol.beads.types import BeadStatus, CodeSnippet, Severity


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_vrs_dir(tmp_path: Path) -> Path:
    """Create a temporary .vrs directory structure."""
    vrs = tmp_path / ".vrs"
    vrs.mkdir()
    (vrs / "beads").mkdir()
    return vrs


@pytest.fixture
def event_store(temp_vrs_dir: Path) -> BeadEventStore:
    """Create an event store rooted at temp .vrs/beads."""
    return BeadEventStore(temp_vrs_dir / "beads")


@pytest.fixture
def storage(temp_vrs_dir: Path) -> BeadStorage:
    """Create a BeadStorage with event sourcing enabled."""
    return BeadStorage(temp_vrs_dir / "beads", enable_events=True)


@pytest.fixture
def sample_bead() -> VulnerabilityBead:
    """Create a sample bead for testing."""
    return VulnerabilityBead(
        id="VKG-TEST-001",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        severity=Severity.CRITICAL,
        confidence=0.95,
        vulnerable_code=CodeSnippet(
            source="function withdraw() { ... }",
            file_path="contracts/Vault.sol",
            start_line=10,
            end_line=20,
            function_name="withdraw",
            contract_name="Vault",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=PatternContext(
            pattern_name="Classic Reentrancy",
            pattern_description="External call before state update",
            why_flagged="State update after external call",
            matched_properties=["state_write_after_external_call"],
            evidence_lines=[15, 16],
        ),
        investigation_guide=InvestigationGuide(
            steps=[],
            questions_to_answer=["Is the external call target user-controlled?"],
            common_false_positives=["nonReentrant modifier present"],
            key_indicators=["State update after external call"],
            safe_patterns=["CEI pattern"],
        ),
        test_context=TestContext(
            scaffold_code="",
            attack_scenario="",
            setup_requirements=[],
            expected_outcome="",
        ),
        similar_exploits=[],
        fix_recommendations=["Use CEI pattern"],
    )


# ============================================================================
# BeadEvent Tests
# ============================================================================


class TestBeadEvent:
    """Tests for BeadEvent dataclass."""

    def test_event_id_computed_from_content(self) -> None:
        """Event ID is computed deterministically from content."""
        event1 = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"test": "data"},
            actor="system",
            timestamp="2026-01-29T12:00:00Z",
        )
        event2 = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"test": "data"},
            actor="system",
            timestamp="2026-01-29T12:00:00Z",
        )
        # Same content = same event_id
        assert event1.event_id == event2.event_id
        assert len(event1.event_id) == 16  # SHA-256 truncated to 16 chars

    def test_payload_hash_computed(self) -> None:
        """Payload hash is computed from payload content."""
        event = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"key": "value"},
            actor="system",
        )
        assert len(event.payload_hash) == 32  # SHA-256 truncated to 32 chars

    def test_different_payloads_different_hashes(self) -> None:
        """Different payloads produce different hashes."""
        event1 = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"key": "value1"},
            actor="system",
        )
        event2 = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"key": "value2"},
            actor="system",
        )
        assert event1.payload_hash != event2.payload_hash

    def test_to_dict_includes_all_fields(self) -> None:
        """to_dict() includes all event fields."""
        event = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"test": "data"},
            actor="agent-001",
            pool_id="audit-pool",
        )
        d = event.to_dict()

        assert d["bead_id"] == "VKG-001"
        assert d["event_type"] == "bead_created"
        assert d["payload"] == {"test": "data"}
        assert d["actor"] == "agent-001"
        assert d["pool_id"] == "audit-pool"
        assert "event_id" in d
        assert "payload_hash" in d
        assert "timestamp" in d

    def test_from_dict_roundtrip(self) -> None:
        """Event can be serialized and deserialized."""
        event = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"test": "data"},
            actor="system",
        )
        d = event.to_dict()
        restored = BeadEvent.from_dict(d)

        assert restored.bead_id == event.bead_id
        assert restored.event_type == event.event_type
        assert restored.payload == event.payload
        assert restored.event_id == event.event_id
        assert restored.payload_hash == event.payload_hash


# ============================================================================
# BeadEventStore Tests
# ============================================================================


class TestBeadEventStore:
    """Tests for BeadEventStore."""

    def test_empty_store_has_no_events(self, event_store: BeadEventStore) -> None:
        """New event store has no events."""
        assert event_store.list_events() == []
        assert event_store.count_events() == 0

    def test_append_event_increases_count(self, event_store: BeadEventStore) -> None:
        """Appending an event increases the event count."""
        event = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"id": "VKG-001"},
            actor="system",
        )

        assert event_store.count_events() == 0
        event_store.append_event(event)
        assert event_store.count_events() == 1

    def test_append_multiple_events(self, event_store: BeadEventStore) -> None:
        """Multiple events can be appended."""
        for i in range(5):
            event = BeadEvent(
                bead_id=f"VKG-{i:03d}",
                event_type="bead_created",
                payload={"id": f"VKG-{i:03d}"},
                actor="system",
            )
            event_store.append_event(event)

        assert event_store.count_events() == 5
        events = event_store.list_events()
        assert len(events) == 5

    def test_events_stored_in_jsonl_format(
        self, event_store: BeadEventStore
    ) -> None:
        """Events are stored as JSONL (one JSON per line)."""
        event = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"id": "VKG-001"},
            actor="system",
        )
        event_store.append_event(event)

        # Read the raw file
        with open(event_store.events_path, "r") as f:
            lines = f.readlines()

        assert len(lines) == 1
        # Should be valid JSON
        data = json.loads(lines[0])
        assert data["bead_id"] == "VKG-001"

    def test_list_events_filters_by_bead_id(
        self, event_store: BeadEventStore
    ) -> None:
        """list_events can filter by bead_id."""
        event_store.append_event(
            BeadEvent(bead_id="VKG-001", event_type="bead_created", payload={}, actor="system")
        )
        event_store.append_event(
            BeadEvent(bead_id="VKG-002", event_type="bead_created", payload={}, actor="system")
        )

        events = event_store.list_events(bead_id="VKG-001")
        assert len(events) == 1
        assert events[0].bead_id == "VKG-001"

    def test_list_events_filters_by_event_type(
        self, event_store: BeadEventStore
    ) -> None:
        """list_events can filter by event_type."""
        event_store.append_event(
            BeadEvent(bead_id="VKG-001", event_type="bead_created", payload={}, actor="system")
        )
        event_store.append_event(
            BeadEvent(bead_id="VKG-001", event_type="bead_updated", payload={}, actor="system")
        )

        events = event_store.list_events(event_type="bead_created")
        assert len(events) == 1
        assert events[0].event_type == "bead_created"

    def test_events_sorted_by_timestamp(self, event_store: BeadEventStore) -> None:
        """Events are returned sorted by timestamp."""
        # Add events with explicit timestamps out of order
        event_store.append_event(
            BeadEvent(
                bead_id="VKG-002",
                event_type="bead_created",
                payload={},
                actor="system",
                timestamp="2026-01-29T12:02:00Z",
            )
        )
        event_store.append_event(
            BeadEvent(
                bead_id="VKG-001",
                event_type="bead_created",
                payload={},
                actor="system",
                timestamp="2026-01-29T12:01:00Z",
            )
        )

        events = event_store.list_events()
        assert events[0].timestamp < events[1].timestamp

    def test_get_event_by_id(self, event_store: BeadEventStore) -> None:
        """Can retrieve specific event by ID."""
        event = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"test": "data"},
            actor="system",
        )
        event_store.append_event(event)

        found = event_store.get_event_by_id(event.event_id)
        assert found is not None
        assert found.bead_id == "VKG-001"

    def test_get_event_by_id_not_found(self, event_store: BeadEventStore) -> None:
        """Returns None for non-existent event ID."""
        assert event_store.get_event_by_id("nonexistent") is None


# ============================================================================
# Replay Tests
# ============================================================================


class TestReplay:
    """Tests for event replay functionality."""

    def test_replay_empty_store(self, event_store: BeadEventStore) -> None:
        """Replaying empty store returns empty dict."""
        beads = event_store.replay()
        assert beads == {}

    def test_replay_creates_bead_from_bead_created_event(
        self, event_store: BeadEventStore, sample_bead: VulnerabilityBead
    ) -> None:
        """bead_created event creates bead in replay."""
        event = BeadEvent(
            bead_id=sample_bead.id,
            event_type="bead_created",
            payload=sample_bead.to_dict(),
            actor="system",
        )
        event_store.append_event(event)

        beads = event_store.replay()
        assert sample_bead.id in beads
        assert beads[sample_bead.id].vulnerability_class == "reentrancy"

    def test_replay_updates_bead_from_bead_updated_event(
        self, event_store: BeadEventStore, sample_bead: VulnerabilityBead
    ) -> None:
        """bead_updated event updates bead in replay."""
        # Create
        event_store.append_event(
            BeadEvent(
                bead_id=sample_bead.id,
                event_type="bead_created",
                payload=sample_bead.to_dict(),
                actor="system",
            )
        )

        # Update
        sample_bead.confidence = 0.99
        event_store.append_event(
            BeadEvent(
                bead_id=sample_bead.id,
                event_type="bead_updated",
                payload=sample_bead.to_dict(),
                actor="agent-001",
            )
        )

        beads = event_store.replay()
        assert beads[sample_bead.id].confidence == 0.99

    def test_replay_removes_bead_from_bead_deleted_event(
        self, event_store: BeadEventStore, sample_bead: VulnerabilityBead
    ) -> None:
        """bead_deleted event removes bead from replay."""
        # Create
        event_store.append_event(
            BeadEvent(
                bead_id=sample_bead.id,
                event_type="bead_created",
                payload=sample_bead.to_dict(),
                actor="system",
            )
        )

        # Delete
        event_store.append_event(
            BeadEvent(
                bead_id=sample_bead.id,
                event_type="bead_deleted",
                payload={},
                actor="system",
            )
        )

        beads = event_store.replay()
        assert sample_bead.id not in beads

    def test_replay_with_bead_id_filter(
        self, event_store: BeadEventStore, sample_bead: VulnerabilityBead
    ) -> None:
        """Can replay only specific bead."""
        # Create two beads
        event_store.append_event(
            BeadEvent(
                bead_id="VKG-001",
                event_type="bead_created",
                payload=sample_bead.to_dict(),
                actor="system",
            )
        )
        other_bead = sample_bead.to_dict()
        other_bead["id"] = "VKG-002"
        event_store.append_event(
            BeadEvent(
                bead_id="VKG-002",
                event_type="bead_created",
                payload=other_bead,
                actor="system",
            )
        )

        beads = event_store.replay(bead_id="VKG-001")
        assert "VKG-001" in beads
        assert "VKG-002" not in beads


# ============================================================================
# BeadStorage Integration Tests
# ============================================================================


class TestStorageEventIntegration:
    """Tests for BeadStorage event sourcing integration."""

    def test_save_bead_emits_bead_created_event(
        self, storage: BeadStorage, sample_bead: VulnerabilityBead
    ) -> None:
        """save_bead emits bead_created event."""
        storage.save_bead(sample_bead)

        events = storage.event_store.list_events()
        assert len(events) == 1
        assert events[0].event_type == "bead_created"
        assert events[0].bead_id == sample_bead.id

    def test_save_existing_bead_emits_bead_updated_event(
        self, storage: BeadStorage, sample_bead: VulnerabilityBead
    ) -> None:
        """Saving existing bead emits bead_updated event."""
        storage.save_bead(sample_bead)
        sample_bead.confidence = 0.99
        storage.save_bead(sample_bead)

        events = storage.event_store.list_events()
        assert len(events) == 2
        assert events[0].event_type == "bead_created"
        assert events[1].event_type == "bead_updated"

    def test_delete_bead_emits_bead_deleted_event(
        self, storage: BeadStorage, sample_bead: VulnerabilityBead
    ) -> None:
        """delete_bead emits bead_deleted event."""
        storage.save_bead(sample_bead)
        storage.delete_bead(sample_bead.id)

        events = storage.event_store.list_events()
        assert len(events) == 2
        assert events[1].event_type == "bead_deleted"

    def test_replay_matches_stored_bead(
        self, storage: BeadStorage, sample_bead: VulnerabilityBead
    ) -> None:
        """Replayed bead matches stored bead."""
        storage.save_bead(sample_bead)

        # Load from file
        stored = storage.get_bead(sample_bead.id)

        # Replay from event log
        replayed = storage.replay_beads()

        assert stored is not None
        assert sample_bead.id in replayed

        # Compare key fields
        assert stored.id == replayed[sample_bead.id].id
        assert stored.vulnerability_class == replayed[sample_bead.id].vulnerability_class
        assert stored.confidence == replayed[sample_bead.id].confidence
        assert stored.severity == replayed[sample_bead.id].severity

    def test_storage_with_events_disabled(
        self, temp_vrs_dir: Path, sample_bead: VulnerabilityBead
    ) -> None:
        """Storage works with event sourcing disabled."""
        storage = BeadStorage(temp_vrs_dir / "beads", enable_events=False)
        storage.save_bead(sample_bead)

        # Bead should be saved
        assert storage.get_bead(sample_bead.id) is not None

        # But no events
        assert storage.event_store is None
        assert storage.replay_beads() == {}


# ============================================================================
# Pool-Specific Event Store Tests
# ============================================================================


class TestPoolEventStore:
    """Tests for pool-specific event stores."""

    def test_pool_event_store_path(self, temp_vrs_dir: Path) -> None:
        """Pool event store uses correct path."""
        store = get_pool_event_store(temp_vrs_dir, "audit-2026-01-29")
        expected = temp_vrs_dir / "pools" / "audit-2026-01-29" / "events" / "beads.jsonl"
        assert store.events_path == expected

    def test_pool_events_isolated(self, temp_vrs_dir: Path) -> None:
        """Events in different pools are isolated."""
        store1 = get_pool_event_store(temp_vrs_dir, "pool-1")
        store2 = get_pool_event_store(temp_vrs_dir, "pool-2")

        store1.append_event(
            BeadEvent(bead_id="VKG-001", event_type="bead_created", payload={}, actor="system")
        )

        assert store1.count_events() == 1
        assert store2.count_events() == 0

    def test_save_to_pool_emits_pool_assigned_event(
        self, storage: BeadStorage, sample_bead: VulnerabilityBead
    ) -> None:
        """save_to_pool emits pool_assigned event."""
        storage.save_to_pool(sample_bead, "audit-pool")

        events = storage.event_store.list_events()
        assert len(events) == 1
        assert events[0].event_type == "pool_assigned"
        assert events[0].pool_id == "audit-pool"

    def test_update_work_state_emits_work_state_updated_event(
        self, storage: BeadStorage, sample_bead: VulnerabilityBead
    ) -> None:
        """update_work_state emits work_state_updated event."""
        storage.save_to_pool(sample_bead, "audit-pool")
        storage.update_work_state(
            sample_bead.id,
            "audit-pool",
            {"step": 2, "findings": []},
            "attacker-agent",
        )

        events = storage.event_store.list_events()
        # pool_assigned + work_state_updated
        assert len(events) == 2
        assert events[1].event_type == "work_state_updated"
        assert events[1].actor == "attacker-agent"


# ============================================================================
# Event Log Integrity Tests
# ============================================================================


class TestEventLogIntegrity:
    """Tests for event log integrity and append-only behavior."""

    def test_events_are_append_only(self, event_store: BeadEventStore) -> None:
        """Events are never modified after being written."""
        event1 = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={"version": 1},
            actor="system",
        )
        event_store.append_event(event1)

        # Read the file content
        with open(event_store.events_path, "r") as f:
            original_content = f.read()

        # Add another event
        event2 = BeadEvent(
            bead_id="VKG-002",
            event_type="bead_created",
            payload={"version": 2},
            actor="system",
        )
        event_store.append_event(event2)

        # Original content should still be at the beginning
        with open(event_store.events_path, "r") as f:
            new_content = f.read()

        assert new_content.startswith(original_content)

    def test_event_order_is_deterministic(
        self, event_store: BeadEventStore
    ) -> None:
        """Events are always returned in deterministic order."""
        # Add events with same timestamp
        base_timestamp = "2026-01-29T12:00:00Z"

        for i in range(10):
            event = BeadEvent(
                bead_id=f"VKG-{i:03d}",
                event_type="bead_created",
                payload={"index": i},
                actor="system",
                timestamp=base_timestamp,
            )
            event_store.append_event(event)

        # Multiple reads should return same order
        events1 = event_store.list_events()
        events2 = event_store.list_events()

        assert len(events1) == len(events2)
        for e1, e2 in zip(events1, events2):
            assert e1.event_id == e2.event_id

    def test_corrupted_line_skipped(self, event_store: BeadEventStore) -> None:
        """Corrupted JSONL lines are skipped without error."""
        # Write a valid event
        event = BeadEvent(
            bead_id="VKG-001",
            event_type="bead_created",
            payload={},
            actor="system",
        )
        event_store.append_event(event)

        # Manually append corrupted line
        with open(event_store.events_path, "a") as f:
            f.write("not valid json\n")

        # Write another valid event
        event2 = BeadEvent(
            bead_id="VKG-002",
            event_type="bead_created",
            payload={},
            actor="system",
        )
        event_store.append_event(event2)

        # Should get 2 valid events (corrupted line skipped)
        events = event_store.list_events()
        assert len(events) == 2
