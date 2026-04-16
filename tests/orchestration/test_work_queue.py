"""Tests for work queue with concurrency limits and backpressure.

Phase 07.1.1-03: Production Orchestration Hardening - Work Queue
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

import pytest

from alphaswarm_sol.orchestration.queue import (
    WorkQueue,
    WorkItem,
    WorkItemStatus,
    QueueLimits,
    BackpressureError,
)
from alphaswarm_sol.orchestration.loop import ExecutionLoop, LoopConfig, PhaseResult, LoopPhase
from alphaswarm_sol.orchestration.router import RouteAction, RouteDecision
from alphaswarm_sol.orchestration.pool import PoolManager
from alphaswarm_sol.orchestration.schemas import Pool, Scope, PoolStatus


# ============================================================================
# WorkQueue Unit Tests
# ============================================================================


class TestWorkQueueBasics:
    """Test basic WorkQueue operations."""

    def test_empty_queue_snapshot(self, tmp_path: Path):
        """Empty queue returns zero counts."""
        queue = WorkQueue(tmp_path / "test-pool")
        snap = queue.snapshot()

        assert snap["queued"] == 0
        assert snap["reserved"] == 0
        assert snap["completed"] == 0
        assert snap["total"] == 0
        assert snap["backpressure"] is False

    def test_enqueue_single_item(self, tmp_path: Path):
        """Single item can be enqueued."""
        queue = WorkQueue(tmp_path / "test-pool")
        item = WorkItem(pool_id="test", bead_id="b1", action="spawn_attacker")

        result = queue.enqueue(item)

        assert result is True
        snap = queue.snapshot()
        assert snap["queued"] == 1
        assert snap["total"] == 1

    def test_enqueue_duplicate_ignored(self, tmp_path: Path):
        """Duplicate items are ignored."""
        queue = WorkQueue(tmp_path / "test-pool")
        item1 = WorkItem(pool_id="test", bead_id="b1", action="spawn_attacker")
        queue.enqueue(item1)

        # Same item again
        item2 = WorkItem(
            pool_id=item1.pool_id,
            bead_id=item1.bead_id,
            action=item1.action,
            item_id=item1.item_id,  # Same ID
        )
        result = queue.enqueue(item2)

        assert result is False
        snap = queue.snapshot()
        assert snap["queued"] == 1


class TestFIFOOrdering:
    """Test FIFO ordering with deterministic tie-breakers."""

    def test_fifo_ordering(self, tmp_path: Path):
        """Items are reserved in FIFO order."""
        queue = WorkQueue(tmp_path / "test-pool")

        # Enqueue in order
        items = []
        for i in range(5):
            item = WorkItem(pool_id="test", bead_id=f"b{i}", action="test")
            queue.enqueue(item)
            items.append(item)

        # Reserve should return in same order
        reserved = queue.reserve(max_items=5)
        assert len(reserved) == 5

        for i, reserved_item in enumerate(reserved):
            assert reserved_item.bead_id == f"b{i}", f"Expected b{i}, got {reserved_item.bead_id}"

    def test_deterministic_tiebreaker(self, tmp_path: Path):
        """Same enqueue time uses item_id as tie-breaker."""
        queue = WorkQueue(tmp_path / "test-pool")

        # Enqueue with same timestamp (forced)
        items = []
        timestamp = "2024-01-01T00:00:00+00:00"
        for i in range(3):
            item = WorkItem(
                pool_id="test",
                bead_id=f"b{i}",
                action="test",
                enqueued_at=timestamp,
            )
            queue.enqueue(item)
            items.append(item)

        # Sort by item_id for expected order
        items.sort(key=lambda x: x.item_id)

        reserved = queue.reserve(max_items=3)
        for i, reserved_item in enumerate(reserved):
            assert reserved_item.item_id == items[i].item_id


class TestMaxInFlightEnforcement:
    """Test max_in_flight concurrency limit enforcement."""

    def test_max_in_flight_respected(self, tmp_path: Path):
        """Reserve respects max_in_flight limit."""
        limits = QueueLimits(max_in_flight=2, max_queue_depth=10)
        queue = WorkQueue(tmp_path / "test-pool", limits)

        # Enqueue 5 items
        for i in range(5):
            queue.enqueue(WorkItem(pool_id="test", bead_id=f"b{i}", action="test"))

        # First reserve returns up to max_in_flight
        reserved1 = queue.reserve()
        assert len(reserved1) == 2

        # Second reserve returns nothing (at capacity)
        reserved2 = queue.reserve()
        assert len(reserved2) == 0

        snap = queue.snapshot()
        assert snap["at_capacity"] is True

    def test_reserve_after_ack_allows_more(self, tmp_path: Path):
        """After ack, more items can be reserved."""
        limits = QueueLimits(max_in_flight=2, max_queue_depth=10)
        queue = WorkQueue(tmp_path / "test-pool", limits)

        for i in range(5):
            queue.enqueue(WorkItem(pool_id="test", bead_id=f"b{i}", action="test"))

        # Reserve 2
        reserved = queue.reserve()
        assert len(reserved) == 2

        # Ack one
        queue.ack(reserved[0].item_id)

        # Now can reserve one more
        more = queue.reserve()
        assert len(more) == 1

    def test_per_action_limits(self, tmp_path: Path):
        """Per-action limits are enforced."""
        limits = QueueLimits(
            max_in_flight=10,
            max_queue_depth=100,
            per_action_limits={"spawn_attacker": 2, "spawn_defender": 1},
        )
        queue = WorkQueue(tmp_path / "test-pool", limits)

        # Enqueue 5 attackers
        for i in range(5):
            queue.enqueue(WorkItem(pool_id="test", bead_id=f"att{i}", action="spawn_attacker"))

        # Enqueue 3 defenders
        for i in range(3):
            queue.enqueue(WorkItem(pool_id="test", bead_id=f"def{i}", action="spawn_defender"))

        # Reserve all - should be limited by per-action limits
        reserved = queue.reserve()

        attackers = [r for r in reserved if r.action == "spawn_attacker"]
        defenders = [r for r in reserved if r.action == "spawn_defender"]

        assert len(attackers) == 2  # per_action_limit
        assert len(defenders) == 1  # per_action_limit


class TestBackpressure:
    """Test backpressure behavior when queue is full."""

    def test_backpressure_on_queue_full(self, tmp_path: Path):
        """Enqueue raises BackpressureError when at max_queue_depth."""
        limits = QueueLimits(max_in_flight=10, max_queue_depth=3)
        queue = WorkQueue(tmp_path / "test-pool", limits)

        # Fill queue
        for i in range(3):
            queue.enqueue(WorkItem(pool_id="test", bead_id=f"b{i}", action="test"))

        snap = queue.snapshot()
        assert snap["backpressure"] is True

        # Next enqueue should raise
        with pytest.raises(BackpressureError):
            queue.enqueue(WorkItem(pool_id="test", bead_id="overflow", action="test"))

    def test_backpressure_force_bypass(self, tmp_path: Path):
        """Force flag bypasses backpressure check."""
        limits = QueueLimits(max_in_flight=10, max_queue_depth=2)
        queue = WorkQueue(tmp_path / "test-pool", limits)

        # Fill queue
        queue.enqueue(WorkItem(pool_id="test", bead_id="b1", action="test"))
        queue.enqueue(WorkItem(pool_id="test", bead_id="b2", action="test"))

        # Force enqueue works
        result = queue.enqueue(
            WorkItem(pool_id="test", bead_id="forced", action="test"),
            force=True,
        )
        assert result is True

        snap = queue.snapshot()
        assert snap["queued"] == 3  # Over limit

    def test_backpressure_clears_after_processing(self, tmp_path: Path):
        """Backpressure clears when items are processed."""
        limits = QueueLimits(max_in_flight=2, max_queue_depth=3)
        queue = WorkQueue(tmp_path / "test-pool", limits)

        # Fill queue
        for i in range(3):
            queue.enqueue(WorkItem(pool_id="test", bead_id=f"b{i}", action="test"))

        assert queue.snapshot()["backpressure"] is True

        # Process some items
        reserved = queue.reserve()
        for item in reserved:
            queue.ack(item.item_id)

        # Now should have room
        snap = queue.snapshot()
        assert snap["backpressure"] is False


class TestQueuePersistence:
    """Test queue state persists across restarts."""

    def test_queue_survives_reload(self, tmp_path: Path):
        """Queue state survives reload from JSONL."""
        pool_path = tmp_path / "test-pool"

        # Create and populate queue
        queue1 = WorkQueue(pool_path)
        queue1.enqueue(WorkItem(pool_id="test", bead_id="b1", action="test"))
        queue1.enqueue(WorkItem(pool_id="test", bead_id="b2", action="test"))

        reserved = queue1.reserve(max_items=1)
        queue1.ack(reserved[0].item_id)

        # Reload from disk
        queue2 = WorkQueue(pool_path)

        snap = queue2.snapshot()
        assert snap["queued"] == 1
        assert snap["completed"] == 1
        assert snap["total"] == 2

    def test_reserved_survives_reload(self, tmp_path: Path):
        """Reserved items remain reserved after reload."""
        pool_path = tmp_path / "test-pool"

        queue1 = WorkQueue(pool_path)
        queue1.enqueue(WorkItem(pool_id="test", bead_id="b1", action="test"))
        reserved = queue1.reserve()

        # Reload
        queue2 = WorkQueue(pool_path)

        snap = queue2.snapshot()
        assert snap["reserved"] == 1
        assert snap["queued"] == 0

    def test_compact_reduces_file_size(self, tmp_path: Path):
        """Compact rewrites JSONL with current state only."""
        pool_path = tmp_path / "test-pool"
        queue = WorkQueue(pool_path)

        # Create many state changes
        for i in range(100):
            item = WorkItem(pool_id="test", bead_id=f"b{i}", action="test")
            queue.enqueue(item)

        # Reserve and ack all
        while True:
            reserved = queue.reserve(max_items=10)
            if not reserved:
                break
            for item in reserved:
                queue.ack(item.item_id)

        # File should be large from all state transitions
        jsonl_path = pool_path / "queue.jsonl"
        size_before = jsonl_path.stat().st_size

        # Compact
        saved = queue.compact()

        size_after = jsonl_path.stat().st_size
        assert saved > 0
        assert size_after < size_before


class TestNackAndRetry:
    """Test negative acknowledgment and retry behavior."""

    def test_nack_requeues_for_retry(self, tmp_path: Path):
        """Nack with retry=True requeues the item."""
        limits = QueueLimits(max_retries=3)
        queue = WorkQueue(tmp_path / "test-pool", limits)

        item = WorkItem(pool_id="test", bead_id="b1", action="test")
        queue.enqueue(item)

        # Reserve and nack
        reserved = queue.reserve()
        queue.nack(reserved[0].item_id, retry=True)

        snap = queue.snapshot()
        assert snap["queued"] == 1
        assert snap["reserved"] == 0

    def test_nack_exhausts_retries(self, tmp_path: Path):
        """Item becomes dead after exhausting retries."""
        limits = QueueLimits(max_retries=2)
        queue = WorkQueue(tmp_path / "test-pool", limits)

        item = WorkItem(pool_id="test", bead_id="b1", action="test")
        queue.enqueue(item)

        # Retry loop
        for i in range(3):
            reserved = queue.reserve()
            if reserved:
                queue.nack(reserved[0].item_id, retry=True)

        snap = queue.snapshot()
        assert snap["dead"] == 1

    def test_nack_no_retry_fails(self, tmp_path: Path):
        """Nack with retry=False marks as failed."""
        queue = WorkQueue(tmp_path / "test-pool")

        item = WorkItem(pool_id="test", bead_id="b1", action="test")
        queue.enqueue(item)

        reserved = queue.reserve()
        queue.nack(reserved[0].item_id, retry=False)

        snap = queue.snapshot()
        assert snap["failed"] == 1


# ============================================================================
# ExecutionLoop + WorkQueue Integration Tests
# ============================================================================


class TestLoopQueueIntegration:
    """Test ExecutionLoop integration with WorkQueue."""

    def test_loop_uses_queue_by_default(self, tmp_path: Path):
        """ExecutionLoop uses queue when use_queue=True (default)."""
        storage_path = tmp_path / "pools"
        manager = PoolManager(storage_path)

        config = LoopConfig(use_queue=True)
        loop = ExecutionLoop(manager, config=config)

        # Create pool
        scope = Scope(files=["test.sol"])
        pool = manager.create_pool(scope, pool_id="test-pool")

        # Get queue snapshot
        snap = loop.get_queue_snapshot(pool.id)
        # Snapshot should have queue stats if queue is enabled
        assert "queued" in snap
        assert snap["queued"] == 0  # Empty queue initially

    def test_loop_respects_max_in_flight(self, tmp_path: Path):
        """Loop respects queue max_in_flight limits."""
        storage_path = tmp_path / "pools"
        manager = PoolManager(storage_path)

        limits = QueueLimits(max_in_flight=1, max_queue_depth=10)
        config = LoopConfig(use_queue=True, queue_limits=limits)
        loop = ExecutionLoop(manager, config=config)

        # Create pool
        scope = Scope(files=["test.sol"])
        pool = manager.create_pool(scope, pool_id="test-pool")

        # Register a counting handler
        call_count = 0

        def counting_handler(pool: Pool, beads: List[str]) -> PhaseResult:
            nonlocal call_count
            call_count += 1
            return PhaseResult(success=True, phase=LoopPhase.INTAKE)

        loop.register_handler(RouteAction.BUILD_GRAPH, counting_handler)

        # Enqueue multiple items
        for i in range(5):
            decision = RouteDecision(
                action=RouteAction.BUILD_GRAPH,
                target_beads=[f"b{i}"],
            )
            loop.enqueue(pool.id, decision)

        # Process queue once
        results = loop._process_queue(pool.id)

        # Should only process max_in_flight items
        assert len(results) <= 1

    def test_backpressure_pauses_pool(self, tmp_path: Path):
        """Backpressure causes pool to be paused."""
        storage_path = tmp_path / "pools"
        manager = PoolManager(storage_path)

        # Very small queue
        limits = QueueLimits(max_in_flight=1, max_queue_depth=1)
        config = LoopConfig(use_queue=True, queue_limits=limits)
        loop = ExecutionLoop(manager, config=config)

        # Create pool
        scope = Scope(files=["test.sol"])
        pool = manager.create_pool(scope, pool_id="test-pool")

        # Fill queue
        decision1 = RouteDecision(action=RouteAction.BUILD_GRAPH, target_beads=["b1"])
        loop.enqueue(pool.id, decision1)

        # Try to enqueue more - should trigger backpressure
        decision2 = RouteDecision(action=RouteAction.BUILD_GRAPH, target_beads=["b2"])
        result = loop.enqueue(pool.id, decision2)

        assert result is False

        # Pool should be paused
        pool = manager.get_pool(pool.id)
        assert pool.status == PoolStatus.PAUSED
        assert pool.metadata.get("backpressure") is True
        assert pool.metadata.get("pause_reason") == "backpressure"


class TestRouteDecisionPayloadHash:
    """Test RouteDecision payload hash generation."""

    def test_payload_hash_deterministic(self):
        """Same decision produces same hash."""
        decision1 = RouteDecision(
            action=RouteAction.SPAWN_ATTACKERS,
            target_beads=["b1", "b2", "b3"],
        )
        decision2 = RouteDecision(
            action=RouteAction.SPAWN_ATTACKERS,
            target_beads=["b1", "b2", "b3"],
        )

        assert decision1.payload_hash == decision2.payload_hash

    def test_payload_hash_order_independent(self):
        """Bead order doesn't affect hash (sorted internally)."""
        decision1 = RouteDecision(
            action=RouteAction.SPAWN_ATTACKERS,
            target_beads=["b3", "b1", "b2"],
        )
        decision2 = RouteDecision(
            action=RouteAction.SPAWN_ATTACKERS,
            target_beads=["b1", "b2", "b3"],
        )

        assert decision1.payload_hash == decision2.payload_hash

    def test_payload_hash_different_for_different_actions(self):
        """Different actions produce different hashes."""
        decision1 = RouteDecision(
            action=RouteAction.SPAWN_ATTACKERS,
            target_beads=["b1"],
        )
        decision2 = RouteDecision(
            action=RouteAction.SPAWN_DEFENDERS,
            target_beads=["b1"],
        )

        assert decision1.payload_hash != decision2.payload_hash
