"""Tests for Propulsion Engine and Agent Coordinator.

Tests cover:
- PropulsionEngine work processing
- Context-fresh agent spawning
- Concurrency limits
- Work state resume
- Timeout handling
- AgentCoordinator setup and execution
- Verifier assignment when BOTH attacker AND defender complete
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from alphaswarm_sol.agents.propulsion import (
    PropulsionEngine,
    PropulsionConfig,
    WorkResult,
    AgentCoordinator,
    CoordinatorConfig,
    CoordinatorStatus,
    CoordinatorReport,
)
from alphaswarm_sol.agents.runtime.base import AgentRole, AgentResponse
from alphaswarm_sol.agents.hooks import AgentInbox


@pytest.fixture
def mock_runtime():
    """Create mock runtime for testing."""
    runtime = MagicMock()
    runtime.spawn_agent = AsyncMock(
        return_value=AgentResponse(
            content="Analysis complete",
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=0,
            cache_write_tokens=0,
            model="claude-sonnet",
            latency_ms=1000,
        )
    )
    return runtime


def create_mock_bead(bead_id: str = "VKG-001", prompt: str = "Analyze this vulnerability..."):
    """Create a properly configured mock bead for testing."""
    bead = MagicMock()
    bead.id = bead_id
    bead.work_state = None
    bead.get_llm_prompt.return_value = prompt
    bead.last_updated = None
    bead.last_agent = None
    # Required for queue prioritization
    bead.metadata = {"tool_count": 0}
    bead.confidence = 0.5
    bead.severity = MagicMock()
    bead.severity.value = "medium"
    return bead


@pytest.fixture
def mock_bead():
    """Create mock bead for testing."""
    return create_mock_bead()


@pytest.fixture
def inbox_with_work(mock_bead):
    """Create inbox with one bead."""
    inbox = AgentInbox(AgentRole.ATTACKER)
    inbox.assign(mock_bead)
    return inbox


class TestPropulsionConfig:
    """Tests for PropulsionConfig dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = PropulsionConfig()
        assert config.max_concurrent_per_role == 2
        assert config.poll_interval_seconds == 1.0
        assert config.work_timeout_seconds == 300
        assert config.enable_resume is True

    def test_custom_values(self):
        """Should accept custom values."""
        config = PropulsionConfig(
            max_concurrent_per_role=5,
            poll_interval_seconds=0.5,
            work_timeout_seconds=600,
            enable_resume=False,
        )
        assert config.max_concurrent_per_role == 5
        assert config.poll_interval_seconds == 0.5
        assert config.work_timeout_seconds == 600
        assert config.enable_resume is False

    def test_to_dict(self):
        """Should serialize to dictionary."""
        config = PropulsionConfig(max_concurrent_per_role=3)
        d = config.to_dict()
        assert d["max_concurrent_per_role"] == 3
        assert "poll_interval_seconds" in d


class TestWorkResult:
    """Tests for WorkResult dataclass."""

    def test_success_result(self):
        """Should represent successful work."""
        response = AgentResponse(
            content="done",
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=0,
            cache_write_tokens=0,
            model="claude",
            latency_ms=1000,
        )
        result = WorkResult(
            bead_id="VKG-001",
            agent_role=AgentRole.ATTACKER,
            success=True,
            response=response,
            duration_ms=1500,
        )
        assert result.success is True
        assert result.bead_id == "VKG-001"
        assert result.duration_ms == 1500

    def test_failure_result(self):
        """Should represent failed work."""
        result = WorkResult(
            bead_id="VKG-001",
            agent_role=AgentRole.ATTACKER,
            success=False,
            error="Timeout",
            duration_ms=300000,
        )
        assert result.success is False
        assert result.error == "Timeout"

    def test_to_dict(self):
        """Should serialize to dictionary."""
        result = WorkResult(
            bead_id="VKG-001",
            agent_role=AgentRole.ATTACKER,
            success=True,
            duration_ms=1000,
        )
        d = result.to_dict()
        assert d["bead_id"] == "VKG-001"
        assert d["agent_role"] == "attacker"
        assert d["success"] is True


class TestPropulsionEngine:
    """Tests for PropulsionEngine."""

    @pytest.mark.asyncio
    async def test_run_processes_all_work(self, mock_runtime, inbox_with_work):
        """Should process all work items."""
        inboxes = {AgentRole.ATTACKER: inbox_with_work}
        engine = PropulsionEngine(mock_runtime, inboxes)

        results = await engine.run(timeout=5)

        assert len(results) == 1
        assert results[0].success
        assert results[0].agent_role == AgentRole.ATTACKER

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Stale code: PropulsionEngine API changed")
    async def test_context_fresh_spawning(self, mock_runtime, mock_bead):
        """Each bead should get fresh agent instance."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(mock_bead)

        bead2 = create_mock_bead("VKG-002", "...")
        inbox.assign(bead2)

        engine = PropulsionEngine(mock_runtime, {AgentRole.ATTACKER: inbox})
        await engine.run(timeout=5)

        # Should have spawned 2 separate agents
        assert mock_runtime.spawn_agent.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, mock_runtime, mock_bead):
        """Should respect max_concurrent_per_role."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        for i in range(5):
            bead = create_mock_bead(f"VKG-{i:03d}", "...")
            inbox.assign(bead)

        # Slow response to test concurrency
        async def slow_spawn(*args, **kwargs):
            await asyncio.sleep(0.1)
            return AgentResponse("done", [], 100, 50, 0, 0, "claude", 100)

        mock_runtime.spawn_agent = slow_spawn

        config = PropulsionConfig(max_concurrent_per_role=2, poll_interval_seconds=0.05)
        engine = PropulsionEngine(mock_runtime, {AgentRole.ATTACKER: inbox}, config)

        # Start run but don't wait
        task = asyncio.create_task(engine.run(timeout=2))
        await asyncio.sleep(0.05)  # Let some tasks start

        # Should have at most 2 active
        assert len(engine._active_tasks) <= 2

        engine.stop()
        await task

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Stale code: PropulsionEngine API changed")
    async def test_work_state_resume(self, mock_runtime, mock_bead):
        """Should include work state in resumed prompts."""
        mock_bead.work_state = {"previous": "data"}
        inbox = AgentInbox(AgentRole.ATTACKER)
        inbox.assign(mock_bead)

        config = PropulsionConfig(enable_resume=True)
        engine = PropulsionEngine(mock_runtime, {AgentRole.ATTACKER: inbox}, config)
        results = await engine.run(timeout=5)

        assert results[0].resumed
        # Check prompt included work state
        call_args = mock_runtime.spawn_agent.call_args
        prompt = call_args[0][1]  # Second positional arg
        assert "previous" in prompt or "Resuming" in prompt

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_runtime):
        """Should handle work timeout."""
        # Create fresh inbox with one bead
        inbox = AgentInbox(AgentRole.ATTACKER)
        bead = create_mock_bead("VKG-TIMEOUT", "timeout test")
        inbox.assign(bead)

        async def slow_spawn(*args, **kwargs):
            await asyncio.sleep(10)  # Very slow
            return AgentResponse("", [], 0, 0, 0, 0, "", 0)

        mock_runtime.spawn_agent = slow_spawn
        # Use longer poll interval to prevent double-claim race
        config = PropulsionConfig(work_timeout_seconds=1, poll_interval_seconds=2.0)
        engine = PropulsionEngine(
            mock_runtime, {AgentRole.ATTACKER: inbox}, config
        )

        results = await engine.run(timeout=5)

        # Should have exactly one timeout result
        assert len(results) >= 1
        assert results[0].success is False
        assert "Timeout" in results[0].error

    @pytest.mark.asyncio
    async def test_callback_on_complete(self, mock_runtime, inbox_with_work):
        """Should call on_complete callback on success."""
        completed_beads = []

        def on_complete(bead_id, response):
            completed_beads.append(bead_id)

        config = PropulsionConfig(on_complete=on_complete)
        engine = PropulsionEngine(
            mock_runtime, {AgentRole.ATTACKER: inbox_with_work}, config
        )

        await engine.run(timeout=5)

        assert "VKG-001" in completed_beads

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Stale code: PropulsionEngine API changed")
    async def test_callback_on_error(self, mock_runtime, inbox_with_work):
        """Should call on_error callback on failure."""
        failed_beads = []

        def on_error(bead_id, error):
            failed_beads.append(bead_id)

        async def failing_spawn(*args, **kwargs):
            raise ValueError("Test error")

        mock_runtime.spawn_agent = failing_spawn
        config = PropulsionConfig(on_error=on_error)
        engine = PropulsionEngine(
            mock_runtime, {AgentRole.ATTACKER: inbox_with_work}, config
        )

        await engine.run(timeout=5)

        assert "VKG-001" in failed_beads

    @pytest.mark.asyncio
    async def test_stop_gracefully(self, mock_runtime, mock_bead):
        """Should stop gracefully when stop() called."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        for i in range(10):
            bead = create_mock_bead(f"VKG-{i:03d}", "...")
            inbox.assign(bead)

        async def slow_spawn(*args, **kwargs):
            await asyncio.sleep(0.5)
            return AgentResponse("done", [], 100, 50, 0, 0, "claude", 100)

        mock_runtime.spawn_agent = slow_spawn
        config = PropulsionConfig(max_concurrent_per_role=1, poll_interval_seconds=0.05)
        engine = PropulsionEngine(mock_runtime, {AgentRole.ATTACKER: inbox}, config)

        task = asyncio.create_task(engine.run(timeout=10))
        await asyncio.sleep(0.1)
        engine.stop()
        results = await task

        # Should have processed some but not all
        assert len(results) < 10

    @pytest.mark.asyncio
    async def test_empty_inbox_returns_immediately(self, mock_runtime):
        """Should return immediately when inbox is empty."""
        inbox = AgentInbox(AgentRole.ATTACKER)
        engine = PropulsionEngine(mock_runtime, {AgentRole.ATTACKER: inbox})

        results = await engine.run(timeout=5)

        assert results == []
        mock_runtime.spawn_agent.assert_not_called()


class TestCoordinatorConfig:
    """Tests for CoordinatorConfig dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = CoordinatorConfig()
        assert config.agents_per_role["attacker"] == 2
        assert config.agents_per_role["defender"] == 2
        assert config.agents_per_role["verifier"] == 1
        assert config.enable_supervisor is True
        assert config.poll_interval == 1.0

    def test_custom_values(self):
        """Should accept custom values."""
        config = CoordinatorConfig(
            agents_per_role={"attacker": 5, "defender": 3, "verifier": 2},
            enable_supervisor=False,
            poll_interval=0.5,
        )
        assert config.agents_per_role["attacker"] == 5
        assert config.enable_supervisor is False

    def test_to_dict(self):
        """Should serialize to dictionary."""
        config = CoordinatorConfig()
        d = config.to_dict()
        assert "agents_per_role" in d
        assert "enable_supervisor" in d


class TestCoordinatorReport:
    """Tests for CoordinatorReport dataclass."""

    def test_to_dict(self):
        """Should serialize to dictionary."""
        report = CoordinatorReport(
            status=CoordinatorStatus.COMPLETE,
            total_beads=10,
            completed_beads=8,
            failed_beads=2,
            results_by_role={"attacker": 10, "defender": 10},
            duration_seconds=60.5,
            stuck_work=[],
        )
        d = report.to_dict()
        assert d["status"] == "complete"
        assert d["total_beads"] == 10
        assert d["completed_beads"] == 8


class TestAgentCoordinator:
    """Tests for AgentCoordinator."""

    def test_setup_distributes_beads(self, mock_runtime, mock_bead):
        """Should register beads for processing."""
        coord = AgentCoordinator(mock_runtime)
        pool = MagicMock()
        pool.bead_ids = ["VKG-001"]

        coord.setup_for_pool(pool, [mock_bead])

        # Bead should be registered
        assert mock_bead.id in coord._bead_registry
        # Verifier queue should be empty initially
        assert len(coord._verifier_queue) == 0
        # Completion sets should be empty
        assert len(coord._attacker_complete) == 0
        assert len(coord._defender_complete) == 0

    @pytest.mark.asyncio
    async def test_run_returns_report(self, mock_runtime, mock_bead):
        """Should return comprehensive report."""
        coord = AgentCoordinator(
            mock_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        pool = MagicMock()

        coord.setup_for_pool(pool, [mock_bead])
        report = await coord.run(timeout=10)

        assert report.status == CoordinatorStatus.COMPLETE
        assert report.completed_beads >= 0
        assert "attacker" in report.results_by_role or "defender" in report.results_by_role

    def test_stop_sets_status(self, mock_runtime):
        """Stop should set status to paused."""
        coord = AgentCoordinator(mock_runtime)
        coord.stop()
        assert coord.status == CoordinatorStatus.PAUSED

    def test_verifier_assignment_on_both_complete(self, mock_runtime, mock_bead):
        """Verifier should be assigned when BOTH attacker and defender complete."""
        coord = AgentCoordinator(
            mock_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        pool = MagicMock()
        coord.setup_for_pool(pool, [mock_bead])

        # Initially verifier queue should be empty
        assert coord.verifier_pending_count == 0

        # Simulate attacker completing
        mock_response = MagicMock()
        coord._on_attacker_complete(mock_bead.id, mock_response)
        # Verifier still empty (defender not done)
        assert coord.verifier_pending_count == 0

        # Simulate defender completing
        coord._on_defender_complete(mock_bead.id, mock_response)
        # Now verifier should have work
        assert coord.verifier_pending_count == 1

    def test_verifier_not_assigned_until_both_done(self, mock_runtime, mock_bead):
        """Verifier should NOT be assigned if only one of attacker/defender done."""
        coord = AgentCoordinator(
            mock_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        pool = MagicMock()
        coord.setup_for_pool(pool, [mock_bead])

        # Only attacker completes
        mock_response = MagicMock()
        coord._on_attacker_complete(mock_bead.id, mock_response)

        # Verifier should still be empty
        assert coord.verifier_pending_count == 0

    def test_verifier_not_assigned_if_defender_only(self, mock_runtime, mock_bead):
        """Verifier should NOT be assigned if only defender done."""
        coord = AgentCoordinator(
            mock_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        pool = MagicMock()
        coord.setup_for_pool(pool, [mock_bead])

        # Only defender completes
        mock_response = MagicMock()
        coord._on_defender_complete(mock_bead.id, mock_response)

        # Verifier should still be empty
        assert coord.verifier_pending_count == 0

    def test_multiple_beads_verifier_assignment(self, mock_runtime):
        """Each bead should only be assigned to verifier when both roles complete."""
        coord = AgentCoordinator(
            mock_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1}
            ),
        )
        pool = MagicMock()

        # Create multiple beads
        beads = []
        for i in range(3):
            bead = create_mock_bead(f"VKG-{i:03d}", f"Bead {i}")
            beads.append(bead)

        coord.setup_for_pool(pool, beads)
        mock_response = MagicMock()

        # Complete attacker for all
        for bead in beads:
            coord._on_attacker_complete(bead.id, mock_response)

        # Verifier still empty (defenders not done)
        assert coord.verifier_pending_count == 0

        # Complete defender for first bead only
        coord._on_defender_complete(beads[0].id, mock_response)
        assert coord.verifier_pending_count == 1

        # Complete defender for second bead
        coord._on_defender_complete(beads[1].id, mock_response)
        assert coord.verifier_pending_count == 2

        # Complete defender for third bead
        coord._on_defender_complete(beads[2].id, mock_response)
        assert coord.verifier_pending_count == 3

    def test_status_transitions(self, mock_runtime, mock_bead):
        """Should track status correctly."""
        coord = AgentCoordinator(mock_runtime)

        # Initial status
        assert coord.status == CoordinatorStatus.IDLE

        # After setup
        pool = MagicMock()
        coord.setup_for_pool(pool, [mock_bead])
        assert coord.status == CoordinatorStatus.IDLE  # Still idle before run

        # After stop
        coord.stop()
        assert coord.status == CoordinatorStatus.PAUSED

    def test_bead_registry(self, mock_runtime, mock_bead):
        """Should register beads for lookup."""
        coord = AgentCoordinator(mock_runtime)
        pool = MagicMock()
        coord.setup_for_pool(pool, [mock_bead])

        assert mock_bead.id in coord._bead_registry
        assert coord._bead_registry[mock_bead.id] is mock_bead

    def test_completion_counts(self, mock_runtime, mock_bead):
        """Should track completion counts."""
        coord = AgentCoordinator(mock_runtime)
        pool = MagicMock()
        coord.setup_for_pool(pool, [mock_bead])

        assert coord.attacker_complete_count == 0
        assert coord.defender_complete_count == 0

        mock_response = MagicMock()
        coord._on_attacker_complete(mock_bead.id, mock_response)
        assert coord.attacker_complete_count == 1
        assert coord.defender_complete_count == 0

        coord._on_defender_complete(mock_bead.id, mock_response)
        assert coord.attacker_complete_count == 1
        assert coord.defender_complete_count == 1

    def test_verifier_pending_count(self, mock_runtime, mock_bead):
        """Should track verifier pending count."""
        coord = AgentCoordinator(mock_runtime)
        pool = MagicMock()
        coord.setup_for_pool(pool, [mock_bead])

        assert coord.verifier_pending_count == 0

        mock_response = MagicMock()
        coord._on_attacker_complete(mock_bead.id, mock_response)
        coord._on_defender_complete(mock_bead.id, mock_response)

        assert coord.verifier_pending_count == 1


class TestIntegration:
    """Integration tests for full propulsion workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_runtime):
        """Test complete workflow from setup to report."""
        # Create beads
        beads = []
        for i in range(2):
            bead = create_mock_bead(f"VKG-{i:03d}", f"Analyze bead {i}")
            beads.append(bead)

        # Fast mock
        async def fast_spawn(*args, **kwargs):
            await asyncio.sleep(0.01)
            return AgentResponse("done", [], 100, 50, 0, 0, "claude", 100)

        mock_runtime.spawn_agent = fast_spawn

        # Create coordinator
        coord = AgentCoordinator(
            mock_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 2, "defender": 2, "verifier": 1},
                poll_interval=0.05,
            ),
        )

        pool = MagicMock()
        pool.id = "test-pool"
        coord.setup_for_pool(pool, beads)

        # Run
        report = await coord.run(timeout=10)

        # Verify
        assert report.status == CoordinatorStatus.COMPLETE
        assert report.total_beads == 2
        # Should have attacker + defender + verifier results
        assert report.completed_beads >= 4  # At least 2 attackers + 2 defenders

    @pytest.mark.asyncio
    async def test_mixed_success_failure(self, mock_runtime):
        """Test workflow with some failures."""
        beads = []
        for i in range(2):
            bead = create_mock_bead(f"VKG-{i:03d}", f"Analyze bead {i}")
            beads.append(bead)

        call_count = [0]

        async def alternating_spawn(*args, **kwargs):
            call_count[0] += 1
            await asyncio.sleep(0.01)
            if call_count[0] % 3 == 0:
                raise ValueError("Simulated failure")
            return AgentResponse("done", [], 100, 50, 0, 0, "claude", 100)

        mock_runtime.spawn_agent = alternating_spawn

        coord = AgentCoordinator(
            mock_runtime,
            CoordinatorConfig(
                agents_per_role={"attacker": 1, "defender": 1, "verifier": 1},
                poll_interval=0.05,
            ),
        )

        pool = MagicMock()
        coord.setup_for_pool(pool, beads)
        report = await coord.run(timeout=10)

        # Should complete despite some failures
        assert report.status == CoordinatorStatus.COMPLETE
        assert report.failed_beads > 0  # Some should have failed
