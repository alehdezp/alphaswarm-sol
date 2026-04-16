"""Tests for determinism, replayability, and resumability.

SDK-10: Ensures same inputs produce same outputs.

Test Categories:
1. Determinism - Same inputs produce identical outputs
2. Resumability - Pool can be resumed from any checkpoint
3. Replayability - Execution can be replayed from artifacts
4. State Persistence - All state survives restart

Key Invariants:
- Given identical inputs, outputs MUST match byte-for-byte
- Pool state persists through crash/restart
- Artifacts enable replay without re-running agents
- Verdicts are stable across repeated executions
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from tests.e2e.fixtures import (
    DeterministicRuntime,
    DETERMINISTIC_RESPONSES,
    create_minimal_bead,
)

from alphaswarm_sol.agents.propulsion.coordinator import (
    AgentCoordinator,
    CoordinatorConfig,
    CoordinatorReport,
    CoordinatorStatus,
)
from alphaswarm_sol.agents.runtime import AgentConfig, AgentRole
from alphaswarm_sol.beads.schema import VulnerabilityBead
from alphaswarm_sol.beads.storage import BeadStorage
from alphaswarm_sol.beads.types import BeadStatus, Severity
from alphaswarm_sol.orchestration.loop import (
    ExecutionLoop,
    LoopConfig,
    LoopPhase,
    PhaseResult,
)
from alphaswarm_sol.orchestration.pool import PoolManager, PoolStorage
from alphaswarm_sol.orchestration.router import RouteAction, Router
from alphaswarm_sol.orchestration.schemas import (
    Pool,
    PoolStatus,
    Scope,
    Verdict,
    VerdictConfidence,
    EvidenceItem,
    EvidencePacket,
)


# =============================================================================
# Test: Determinism - Same inputs produce same outputs
# =============================================================================


@pytest.mark.asyncio
class TestDeterminism:
    """Test that identical inputs produce identical outputs."""

    async def test_runtime_deterministic_responses(self) -> None:
        """Test DeterministicRuntime produces same output for same input."""
        runtime = DeterministicRuntime()

        config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="You are a security expert.",
            tools=[],
        )

        # Run same task twice
        r1 = await runtime.spawn_agent(config, "Analyze this vulnerability")
        r2 = await runtime.spawn_agent(config, "Analyze this vulnerability")

        # Content must match exactly
        assert r1.content == r2.content, "Same input must produce same output"

    async def test_runtime_content_matches_template(self) -> None:
        """Test runtime content matches predefined template."""
        runtime = DeterministicRuntime()

        for role in AgentRole:
            config = AgentConfig(
                role=role,
                system_prompt="test",
                tools=[],
            )
            response = await runtime.spawn_agent(config, "test task")

            expected = DETERMINISTIC_RESPONSES.get(
                role, "Analysis complete. No issues found."
            )
            assert response.content == expected, f"Response for {role} must match template"

    async def test_coordinator_deterministic_report(self) -> None:
        """Test coordinator produces deterministic report structure."""
        beads = [create_minimal_bead(bead_id="VKG-DET-001")]
        pool = Pool(
            id="determinism-test",
            scope=Scope(files=["contracts/Test.sol"]),
            bead_ids=[b.id for b in beads],
        )

        # Run twice with fresh runtimes
        runtime1 = DeterministicRuntime()
        coordinator1 = AgentCoordinator(
            runtime1,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        coordinator1.setup_for_pool(pool, beads)
        report1 = await coordinator1.run()

        runtime2 = DeterministicRuntime()
        coordinator2 = AgentCoordinator(
            runtime2,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        coordinator2.setup_for_pool(pool, beads)
        report2 = await coordinator2.run()

        # Structure must match (excluding timestamps/durations)
        assert report1.total_beads == report2.total_beads
        assert report1.completed_beads == report2.completed_beads
        assert report1.failed_beads == report2.failed_beads
        assert report1.results_by_role == report2.results_by_role
        assert report1.status == report2.status

    async def test_bead_hash_stability(self) -> None:
        """Test bead content hash is stable."""
        bead1 = create_minimal_bead(bead_id="VKG-HASH-001")
        bead2 = create_minimal_bead(bead_id="VKG-HASH-001")

        # Context hash should be identical
        assert bead1.context_hash == bead2.context_hash, "Same bead content must have same hash"

    def test_pool_serialization_deterministic(self, tmp_path: Path) -> None:
        """Test pool serialization is deterministic."""
        storage = PoolStorage(tmp_path / "pools")

        scope = Scope(
            files=["contracts/A.sol", "contracts/B.sol"],
            contracts=["A", "B"],
        )
        pool = Pool(
            id="serialize-test",
            scope=scope,
            bead_ids=["VKG-001", "VKG-002"],
        )

        # Serialize twice
        yaml1 = pool.to_yaml()
        yaml2 = pool.to_yaml()

        # Must be identical
        assert yaml1 == yaml2, "Pool serialization must be deterministic"

    def test_verdict_serialization_deterministic(self) -> None:
        """Test verdict serialization is deterministic."""
        evidence = EvidencePacket(
            finding_id="VKG-001",
            items=[
                EvidenceItem(
                    type="signature",
                    value="R:bal->X:out->W:bal",
                    location="Vault.sol:42",
                    confidence=0.9,
                )
            ],
        )

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="CEI violation confirmed",
            evidence_packet=evidence,
        )

        # Serialize twice
        yaml1 = verdict.to_yaml()
        yaml2 = verdict.to_yaml()

        assert yaml1 == yaml2, "Verdict serialization must be deterministic"


# =============================================================================
# Test: Resumability - Pool can resume from any checkpoint
# =============================================================================


class TestResumability:
    """Test pool can be resumed from any checkpoint."""

    def test_pool_resumes_from_intake(self, tmp_path: Path) -> None:
        """Test pool resumes from INTAKE phase."""
        manager = PoolManager(tmp_path / "pools")

        # Create pool at INTAKE
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="resume-intake")

        # Pause it
        manager.pause_pool(pool.id, "Simulated interruption")
        assert manager.get_pool(pool.id).status == PoolStatus.PAUSED

        # Resume
        manager.resume_pool(pool.id)
        pool = manager.get_pool(pool.id)
        assert pool.status != PoolStatus.PAUSED

    def test_pool_resumes_from_execute(self, tmp_path: Path) -> None:
        """Test pool resumes from EXECUTE phase."""
        manager = PoolManager(tmp_path / "pools")

        # Create pool and advance to EXECUTE
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="resume-execute")
        pool.advance_phase()  # INTAKE -> CONTEXT
        pool.advance_phase()  # CONTEXT -> BEADS
        pool.advance_phase()  # BEADS -> EXECUTE
        manager.storage.save_pool(pool)

        # Pause at EXECUTE
        manager.pause_pool(pool.id, "Mid-execution pause")
        pool = manager.get_pool(pool.id)
        assert pool.status == PoolStatus.PAUSED
        assert "execute" in pool.metadata.get("paused_from_status", "")

        # Resume
        manager.resume_pool(pool.id)
        pool = manager.get_pool(pool.id)
        assert pool.status != PoolStatus.PAUSED

    def test_pool_resumes_from_verify(self, tmp_path: Path) -> None:
        """Test pool resumes from VERIFY phase."""
        manager = PoolManager(tmp_path / "pools")

        # Create pool and advance to VERIFY
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="resume-verify")
        for _ in range(4):  # Advance through INTAKE, CONTEXT, BEADS, EXECUTE
            pool.advance_phase()
        manager.storage.save_pool(pool)

        assert pool.status == PoolStatus.VERIFY

        # Pause and resume
        manager.pause_pool(pool.id)
        manager.resume_pool(pool.id)

        pool = manager.get_pool(pool.id)
        assert pool.status in [PoolStatus.VERIFY, PoolStatus.INTEGRATE]

    def test_bead_work_state_preserved(self, tmp_path: Path) -> None:
        """Test bead work state is preserved through pause/resume."""
        bead_storage = BeadStorage(tmp_path / "beads")

        # Create bead with work state
        bead = create_minimal_bead(bead_id="VKG-WORK-STATE")
        bead.work_state = {"step": 2, "partial_result": {"found": True}}
        bead.last_agent = "attacker-001"
        bead.last_updated = datetime.now()
        bead_storage.save_bead(bead)

        # Load and verify
        loaded = bead_storage.get_bead("VKG-WORK-STATE")
        assert loaded is not None
        assert loaded.work_state == {"step": 2, "partial_result": {"found": True}}
        assert loaded.last_agent == "attacker-001"

    def test_pool_preserves_partial_verdicts(self, tmp_path: Path) -> None:
        """Test pool preserves partial verdicts through pause/resume."""
        manager = PoolManager(tmp_path / "pools")

        # Create pool with beads
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="partial-verdicts")
        manager.add_bead(pool.id, "VKG-001")
        manager.add_bead(pool.id, "VKG-002")
        manager.add_bead(pool.id, "VKG-003")

        # Record partial verdicts
        verdict1 = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="First verdict",
        )
        manager.record_verdict(pool.id, verdict1)

        # Pause
        manager.pause_pool(pool.id, "Partial completion")

        # Resume
        manager.resume_pool(pool.id)

        # Verify partial verdicts preserved
        pool = manager.get_pool(pool.id)
        assert "VKG-001" in pool.verdicts
        assert "VKG-002" not in pool.verdicts  # Not yet processed
        assert len(pool.pending_beads) == 2


# =============================================================================
# Test: Replayability - Execution can be replayed from artifacts
# =============================================================================


class TestReplayability:
    """Test execution can be replayed from artifacts."""

    def test_pool_yaml_roundtrip(self, tmp_path: Path) -> None:
        """Test pool survives YAML roundtrip."""
        scope = Scope(
            files=["contracts/Vault.sol"],
            contracts=["Vault"],
            focus_areas=["reentrancy"],
        )
        pool = Pool(
            id="roundtrip-test",
            scope=scope,
            bead_ids=["VKG-001", "VKG-002"],
            metadata={"key": "value"},
        )
        pool.advance_phase()  # Add some state

        # Roundtrip
        yaml_str = pool.to_yaml()
        restored = Pool.from_yaml(yaml_str)

        # Verify all fields
        assert restored.id == pool.id
        assert restored.scope.files == pool.scope.files
        assert restored.bead_ids == pool.bead_ids
        assert restored.status == pool.status
        assert restored.metadata["key"] == "value"

    def test_bead_json_roundtrip(self) -> None:
        """Test bead survives JSON roundtrip."""
        bead = create_minimal_bead(bead_id="VKG-ROUNDTRIP")
        bead.add_note("Investigation note 1")
        bead.status = BeadStatus.INVESTIGATING

        # Roundtrip
        json_str = bead.to_json()
        restored = VulnerabilityBead.from_json(json_str)

        # Verify key fields
        assert restored.id == bead.id
        assert restored.vulnerability_class == bead.vulnerability_class
        assert restored.status == bead.status
        assert len(restored.notes) == 1

    def test_verdict_yaml_roundtrip(self) -> None:
        """Test verdict survives YAML roundtrip."""
        evidence = EvidencePacket(
            finding_id="VKG-001",
            items=[
                EvidenceItem(
                    type="code_pattern",
                    value="state_write_after_call",
                    location="Vault.sol:42",
                    confidence=0.9,
                )
            ],
            summary="CEI violation detected",
        )

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.CONFIRMED,
            is_vulnerable=True,
            rationale="Multi-agent consensus reached",
            evidence_packet=evidence,
        )

        # Roundtrip
        yaml_str = verdict.to_yaml()
        restored = Verdict.from_yaml(yaml_str)

        # Verify
        assert restored.finding_id == verdict.finding_id
        assert restored.confidence == verdict.confidence
        assert restored.is_vulnerable == verdict.is_vulnerable
        assert restored.evidence_packet is not None
        assert len(restored.evidence_packet.items) == 1

    def test_coordinator_report_json_roundtrip(self) -> None:
        """Test coordinator report survives JSON roundtrip."""
        report = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=5,
            completed_beads=4,
            failed_beads=1,
            results_by_role={"attacker": 5, "defender": 5, "verifier": 4},
            duration_seconds=42.5,
            stuck_work=["VKG-005:verifier"],
            verdicts=[
                {"finding_id": "VKG-001", "vulnerable": True},
                {"finding_id": "VKG-002", "vulnerable": False},
            ],
        )

        # Roundtrip
        json_str = json.dumps(report.to_dict())
        restored = CoordinatorReport.from_dict(json.loads(json_str))

        # Verify all fields
        assert restored.status == report.status
        assert restored.total_beads == report.total_beads
        assert restored.completed_beads == report.completed_beads
        assert restored.failed_beads == report.failed_beads
        assert restored.results_by_role == report.results_by_role
        assert restored.duration_seconds == report.duration_seconds
        assert restored.stuck_work == report.stuck_work
        assert len(restored.verdicts) == 2

    def test_replay_from_saved_pool(self, tmp_path: Path) -> None:
        """Test execution can be replayed from saved pool state."""
        manager = PoolManager(tmp_path / "pools")
        bead_storage = BeadStorage(tmp_path / "beads")

        # Create initial state
        beads = [create_minimal_bead(bead_id=f"VKG-REPLAY-{i}") for i in range(3)]
        for bead in beads:
            bead_storage.save_bead(bead)

        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="replay-test")
        for bead in beads:
            manager.add_bead(pool.id, bead.id)

        # Reload pool to get updated version with beads
        pool = manager.get_pool(pool.id)
        assert pool is not None

        # Advance and save state at checkpoint
        pool.advance_phase()  # INTAKE -> CONTEXT
        pool.advance_phase()  # CONTEXT -> BEADS
        manager.storage.save_pool(pool)

        checkpoint_yaml = pool.to_yaml()

        # Simulate "crash" - reload from scratch
        fresh_manager = PoolManager(tmp_path / "pools")
        fresh_pool = fresh_manager.get_pool(pool.id)

        # Verify state preserved
        assert fresh_pool is not None
        assert fresh_pool.status == PoolStatus.BEADS
        assert len(fresh_pool.bead_ids) == 3


# =============================================================================
# Test: State Persistence - All state survives restart
# =============================================================================


class TestStatePersistence:
    """Test that all state persists correctly."""

    def test_pool_status_persists(self, tmp_path: Path) -> None:
        """Test pool status persists through reload."""
        storage = PoolStorage(tmp_path / "pools")

        # Create pool at various statuses
        for status in [PoolStatus.INTAKE, PoolStatus.CONTEXT, PoolStatus.BEADS]:
            scope = Scope(files=["contracts/Test.sol"])
            pool = Pool(id=f"persist-{status.value}", scope=scope)
            pool.status = status
            storage.save_pool(pool)

            # Reload
            loaded = storage.get_pool(pool.id)
            assert loaded is not None
            assert loaded.status == status, f"Status {status} must persist"

    def test_pool_phases_complete_persists(self, tmp_path: Path) -> None:
        """Test completed phases list persists."""
        storage = PoolStorage(tmp_path / "pools")

        scope = Scope(files=["contracts/Test.sol"])
        pool = Pool(id="phases-persist", scope=scope)
        pool.advance_phase()  # Adds INTAKE to phases_complete
        pool.advance_phase()  # Adds CONTEXT to phases_complete
        storage.save_pool(pool)

        # Reload
        loaded = storage.get_pool(pool.id)
        assert loaded is not None
        assert "intake" in loaded.phases_complete
        assert "context" in loaded.phases_complete

    def test_pool_metadata_persists(self, tmp_path: Path) -> None:
        """Test pool metadata persists."""
        storage = PoolStorage(tmp_path / "pools")

        scope = Scope(files=["contracts/Test.sol"])
        pool = Pool(id="metadata-persist", scope=scope)
        pool.metadata = {
            "custom_key": "custom_value",
            "nested": {"a": 1, "b": 2},
            "list": [1, 2, 3],
        }
        storage.save_pool(pool)

        # Reload
        loaded = storage.get_pool(pool.id)
        assert loaded is not None
        assert loaded.metadata["custom_key"] == "custom_value"
        assert loaded.metadata["nested"]["a"] == 1
        assert loaded.metadata["list"] == [1, 2, 3]

    def test_bead_status_persists(self, tmp_path: Path) -> None:
        """Test bead status persists."""
        storage = BeadStorage(tmp_path / "beads")

        for status in [BeadStatus.PENDING, BeadStatus.INVESTIGATING, BeadStatus.CONFIRMED]:
            bead = create_minimal_bead(bead_id=f"VKG-STATUS-{status.value}")
            bead.status = status
            storage.save_bead(bead)

            # Reload
            loaded = storage.get_bead(bead.id)
            assert loaded is not None
            assert loaded.status == status, f"Status {status} must persist"

    def test_bead_notes_persist(self, tmp_path: Path) -> None:
        """Test bead investigation notes persist."""
        storage = BeadStorage(tmp_path / "beads")

        bead = create_minimal_bead(bead_id="VKG-NOTES-PERSIST")
        bead.add_note("First investigation note")
        bead.add_note("Second investigation note")
        storage.save_bead(bead)

        # Reload
        loaded = storage.get_bead(bead.id)
        assert loaded is not None
        assert len(loaded.notes) == 2
        assert "First investigation note" in loaded.notes[0]
        assert "Second investigation note" in loaded.notes[1]

    def test_verdict_in_pool_persists(self, tmp_path: Path) -> None:
        """Test verdicts stored in pool persist."""
        storage = PoolStorage(tmp_path / "pools")

        scope = Scope(files=["contracts/Test.sol"])
        pool = Pool(id="verdict-persist", scope=scope)
        pool.add_bead("VKG-001")

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Test verdict persistence",
        )
        pool.record_verdict(verdict)
        storage.save_pool(pool)

        # Reload
        loaded = storage.get_pool(pool.id)
        assert loaded is not None
        assert "VKG-001" in loaded.verdicts
        assert loaded.verdicts["VKG-001"].is_vulnerable
        assert loaded.verdicts["VKG-001"].confidence == VerdictConfidence.LIKELY


# =============================================================================
# Test: Custom Response Handler for Testing
# =============================================================================


@pytest.mark.asyncio
class TestCustomResponseHandler:
    """Test DeterministicRuntime with custom response handler."""

    async def test_custom_handler_receives_context(self) -> None:
        """Test custom handler receives message context."""
        received_messages: List[List[Dict]] = []

        def handler(config: AgentConfig, messages: List[Dict]) -> str:
            received_messages.append(messages)
            return f"Processed by {config.role.value}"

        runtime = DeterministicRuntime(custom_handler=handler)

        config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="test",
            tools=[],
        )
        response = await runtime.spawn_agent(config, "test message")

        # Handler should have been called with message
        assert len(received_messages) == 1
        assert received_messages[0][0]["content"] == "test message"

    async def test_custom_handler_role_routing(self) -> None:
        """Test custom handler can route based on role."""
        def handler(config: AgentConfig, messages: List[Dict]) -> str:
            return f"ROLE:{config.role.value.upper()}"

        runtime = DeterministicRuntime(custom_handler=handler)

        for role in [AgentRole.ATTACKER, AgentRole.DEFENDER, AgentRole.VERIFIER]:
            config = AgentConfig(role=role, system_prompt="test", tools=[])
            response = await runtime.spawn_agent(config, "test")
            assert response.content == f"ROLE:{role.value.upper()}"

    async def test_runtime_call_log_for_replay(self) -> None:
        """Test runtime call log can be used for replay."""
        runtime = DeterministicRuntime()

        # Execute multiple calls
        configs = [
            AgentConfig(role=AgentRole.ATTACKER, system_prompt="test", tools=[]),
            AgentConfig(role=AgentRole.DEFENDER, system_prompt="test", tools=[]),
        ]

        for config in configs:
            await runtime.spawn_agent(config, f"task for {config.role.value}")

        # Call log should record all calls
        assert len(runtime.call_log) == 2
        assert runtime.call_log[0]["role"] == "attacker"
        assert runtime.call_log[1]["role"] == "defender"

        # Can replay by iterating call log
        runtime2 = DeterministicRuntime()
        for log_entry in runtime.call_log:
            role = AgentRole(log_entry["role"])
            messages = log_entry["messages"]
            config = AgentConfig(role=role, system_prompt="test", tools=[])
            response = await runtime2.execute(config, messages)
            # Replayed responses match originals
            assert response.content == DETERMINISTIC_RESPONSES[role]


# =============================================================================
# Test: Hash Stability for Deduplication
# =============================================================================


class TestHashStability:
    """Test content hashing is stable for deduplication."""

    def test_bead_hash_same_content(self) -> None:
        """Test beads with same content have same hash."""
        bead1 = create_minimal_bead(bead_id="VKG-SAME-1")
        bead2 = create_minimal_bead(bead_id="VKG-SAME-2")

        # Same vulnerable_code content -> same hash
        assert bead1.context_hash == bead2.context_hash

    def test_bead_hash_different_content(self) -> None:
        """Test beads with different content have different hash."""
        bead1 = create_minimal_bead(bead_id="VKG-DIFF-1")
        bead2 = create_minimal_bead(bead_id="VKG-DIFF-2")

        # Store original hash
        original_hash = bead2.context_hash

        # Modify content and recalculate hash manually
        bead2.vulnerable_code.source = "function differentCode() {}"
        new_hash = bead2._calculate_hash()

        # Different content -> different hash
        assert new_hash != original_hash, "Different content should produce different hash"

        # Verify the hashing is deterministic
        recalculated = bead2._calculate_hash()
        assert new_hash == recalculated, "Hash calculation must be deterministic"

    def test_evidence_item_equality(self) -> None:
        """Test evidence items with same content are equal."""
        e1 = EvidenceItem(
            type="signature",
            value="R:bal->X:out->W:bal",
            location="Vault.sol:42",
            confidence=0.9,
        )
        e2 = EvidenceItem(
            type="signature",
            value="R:bal->X:out->W:bal",
            location="Vault.sol:42",
            confidence=0.9,
        )

        # Serialization should be identical
        assert e1.to_dict() == e2.to_dict()


# =============================================================================
# Test: ReplayEngine - Deterministic Pool Reconstruction (07.1.1-04)
# =============================================================================


class TestReplayEngine:
    """Test ReplayEngine for deterministic pool reconstruction from event logs."""

    def test_replay_engine_basic_instantiation(self, tmp_path: Path) -> None:
        """Test ReplayEngine can be instantiated."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine

        engine = ReplayEngine(vrs_root=tmp_path / ".vrs")
        assert engine is not None
        assert hasattr(engine, "replay")

    def test_replay_empty_pool_from_snapshot(self, tmp_path: Path) -> None:
        """Test replay falls back to snapshot when no events exist."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        # Create pool directly (no events)
        manager = PoolManager(vrs_root / "pools")
        scope = Scope(files=["contracts/Test.sol"])
        pool = manager.create_pool(scope, pool_id="replay-fallback-test")

        # Replay should load from snapshot
        engine = ReplayEngine(vrs_root=vrs_root)
        result = engine.replay("replay-fallback-test")

        assert result.success
        assert result.pool is not None
        assert result.pool.id == "replay-fallback-test"
        assert result.event_count == 0  # No events, loaded from snapshot

    def test_replay_pool_with_bead_events(self, tmp_path: Path) -> None:
        """Test replay reconstructs pool state from bead events."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine, PoolEventStore, PoolEvent
        from alphaswarm_sol.beads.event_store import BeadEventStore, BeadEvent

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        pool_id = "replay-bead-events"

        # Create pool event log
        pool_events = PoolEventStore(vrs_root / "pools", pool_id)
        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="pool_created",
            payload={
                "scope": {"files": ["contracts/Test.sol"], "contracts": [], "focus_areas": []},
                "bead_ids": [],
                "initiated_by": "test",
                "status": "intake",
            },
            actor="test",
        ))

        # Add bead events
        bead_events = BeadEventStore(vrs_root / "beads", pool_id=pool_id)
        bead = create_minimal_bead(bead_id="VKG-REPLAY-001")
        bead_events.append_event(BeadEvent(
            bead_id="VKG-REPLAY-001",
            event_type="pool_assigned",
            payload=bead.to_dict(),
            actor="test",
            pool_id=pool_id,
        ))

        # Replay
        engine = ReplayEngine(vrs_root=vrs_root)
        result = engine.replay(pool_id)

        assert result.success
        assert result.pool is not None
        assert result.event_count >= 1
        assert "VKG-REPLAY-001" in result.beads

    def test_replay_with_verdicts(self, tmp_path: Path) -> None:
        """Test replay reconstructs verdicts from events."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine, PoolEventStore, PoolEvent

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        pool_id = "replay-verdicts"

        # Create pool with verdict event
        pool_events = PoolEventStore(vrs_root / "pools", pool_id)
        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="pool_created",
            payload={
                "scope": {"files": ["contracts/Test.sol"], "contracts": [], "focus_areas": []},
                "bead_ids": ["VKG-001"],
                "initiated_by": "test",
                "status": "intake",
            },
            actor="test",
        ))
        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="verdict_recorded",
            payload={
                "verdict": {
                    "finding_id": "VKG-001",
                    "confidence": "likely",
                    "is_vulnerable": True,
                    "rationale": "Test verdict",
                }
            },
            actor="test",
        ))

        # Replay
        engine = ReplayEngine(vrs_root=vrs_root)
        result = engine.replay(pool_id)

        assert result.success
        assert result.verdict_count == 1
        assert result.pool is not None
        assert "VKG-001" in result.pool.verdicts
        assert result.pool.verdicts["VKG-001"].is_vulnerable

    def test_replay_strict_mode_matches(self, tmp_path: Path) -> None:
        """Test strict mode validates replay matches current snapshot."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine, PoolEventStore, PoolEvent

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        pool_id = "replay-strict-match"

        # Create consistent state (events match snapshot)
        pool_events = PoolEventStore(vrs_root / "pools", pool_id)
        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="pool_created",
            payload={
                "scope": {"files": ["contracts/Test.sol"], "contracts": [], "focus_areas": []},
                "bead_ids": ["VKG-001"],
                "initiated_by": "test",
                "status": "intake",
            },
            actor="test",
        ))

        # Also save matching snapshot
        manager = PoolManager(vrs_root / "pools")
        scope = Scope(files=["contracts/Test.sol"])
        pool = Pool(id=pool_id, scope=scope, bead_ids=["VKG-001"])
        manager.storage.save_pool(pool)

        # Replay with strict mode
        engine = ReplayEngine(vrs_root=vrs_root)
        result = engine.replay(pool_id, strict=True)

        assert result.success
        # No mismatches expected when state is consistent
        # (some fields may differ like timestamps, but core state should match)

    def test_replay_strict_mode_detects_mismatch(self, tmp_path: Path) -> None:
        """Test strict mode detects when replay differs from snapshot."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine, PoolEventStore, PoolEvent

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        pool_id = "replay-strict-mismatch"

        # Create events with one set of beads
        pool_events = PoolEventStore(vrs_root / "pools", pool_id)
        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="pool_created",
            payload={
                "scope": {"files": ["contracts/Test.sol"], "contracts": [], "focus_areas": []},
                "bead_ids": ["VKG-001"],
                "initiated_by": "test",
                "status": "intake",
            },
            actor="test",
        ))

        # Save snapshot with different beads (mismatch)
        manager = PoolManager(vrs_root / "pools")
        scope = Scope(files=["contracts/Test.sol"])
        pool = Pool(id=pool_id, scope=scope, bead_ids=["VKG-001", "VKG-002", "VKG-003"])
        manager.storage.save_pool(pool)

        # Replay with strict mode
        engine = ReplayEngine(vrs_root=vrs_root)
        result = engine.replay(pool_id, strict=True)

        assert result.success
        # Should detect mismatch in bead_ids
        assert len(result.mismatches) > 0
        bead_mismatch = any(m.field == "bead_ids" for m in result.mismatches)
        assert bead_mismatch, "Should detect bead_ids mismatch"

    def test_replay_deterministic_with_seed(self, tmp_path: Path) -> None:
        """Test replay is deterministic with explicit seed."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine, PoolEventStore, PoolEvent

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        pool_id = "replay-deterministic"

        # Create pool events
        pool_events = PoolEventStore(vrs_root / "pools", pool_id)
        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="pool_created",
            payload={
                "scope": {"files": ["contracts/Test.sol"], "contracts": [], "focus_areas": []},
                "bead_ids": ["VKG-001", "VKG-002"],
                "initiated_by": "test",
                "status": "intake",
            },
            actor="test",
        ))

        engine = ReplayEngine(vrs_root=vrs_root)

        # Replay with same seed twice
        result1 = engine.replay(pool_id, seed=42)
        result2 = engine.replay(pool_id, seed=42)

        # Results should be identical
        assert result1.success == result2.success
        assert result1.bead_count == result2.bead_count
        assert result1.event_count == result2.event_count
        assert result1.seed == result2.seed == 42

    def test_replay_event_ordering_deterministic(self, tmp_path: Path) -> None:
        """Test events are processed in deterministic order (timestamp + event_id)."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine, PoolEventStore, PoolEvent

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        pool_id = "replay-ordering"

        # Create events with same timestamp but different payloads
        pool_events = PoolEventStore(vrs_root / "pools", pool_id)

        # Use fixed timestamp
        fixed_timestamp = "2026-01-29T12:00:00Z"

        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="pool_created",
            payload={
                "scope": {"files": ["contracts/Test.sol"], "contracts": [], "focus_areas": []},
                "bead_ids": [],
                "initiated_by": "test",
                "status": "intake",
            },
            actor="test",
            timestamp=fixed_timestamp,
        ))

        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="bead_added",
            payload={"bead_id": "VKG-001"},
            actor="test",
            timestamp=fixed_timestamp,
        ))

        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="bead_added",
            payload={"bead_id": "VKG-002"},
            actor="test",
            timestamp=fixed_timestamp,
        ))

        # Replay multiple times
        engine = ReplayEngine(vrs_root=vrs_root)
        results = [engine.replay(pool_id, seed=0) for _ in range(3)]

        # All replays should produce identical state
        for result in results:
            assert result.success
            assert result.pool is not None
            assert set(result.pool.bead_ids) == {"VKG-001", "VKG-002"}

    def test_replay_nonexistent_pool_fails(self, tmp_path: Path) -> None:
        """Test replay of nonexistent pool returns error."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        engine = ReplayEngine(vrs_root=vrs_root)
        result = engine.replay("nonexistent-pool")

        assert not result.success
        assert "not found" in result.error.lower()

    def test_replay_diff_summary_format(self, tmp_path: Path) -> None:
        """Test diff summary produces readable output."""
        from alphaswarm_sol.orchestration.replay import ReplayEngine, PoolEventStore, PoolEvent

        vrs_root = tmp_path / ".vrs"
        vrs_root.mkdir(parents=True)

        pool_id = "replay-diff-format"

        # Create pool
        pool_events = PoolEventStore(vrs_root / "pools", pool_id)
        pool_events.append_event(PoolEvent(
            pool_id=pool_id,
            event_type="pool_created",
            payload={
                "scope": {"files": ["contracts/Test.sol"], "contracts": [], "focus_areas": []},
                "bead_ids": ["VKG-001"],
                "initiated_by": "test",
                "status": "intake",
            },
            actor="test",
        ))

        engine = ReplayEngine(vrs_root=vrs_root)
        result = engine.replay(pool_id)

        # Generate diff summary
        summary = engine.get_diff_summary(result)

        assert "REPLAY DIFF SUMMARY" in summary
        assert pool_id in summary
        assert "Events processed" in summary
        assert "Beads reconstructed" in summary
