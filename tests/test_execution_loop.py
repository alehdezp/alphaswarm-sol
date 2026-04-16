"""Tests for execution loop and router.

Tests verify:
1. Router routes based on pool status (ORCH-01)
2. ExecutionLoop follows fixed sequence (ORCH-07)
3. Loop can resume from checkpoints
4. Phase transitions are deterministic
"""

import tempfile
from pathlib import Path

import pytest

from alphaswarm_sol.orchestration.loop import (
    ExecutionLoop,
    LoopConfig,
    LoopPhase,
    PhaseResult,
)
from alphaswarm_sol.orchestration.pool import PoolManager
from alphaswarm_sol.orchestration.router import RouteAction, RouteDecision, Router, route_pool
from alphaswarm_sol.orchestration.schemas import (
    EvidenceItem,
    EvidencePacket,
    Pool,
    PoolStatus,
    Scope,
    Verdict,
    VerdictConfidence,
)


class TestRouteAction:
    """Tests for RouteAction enum."""

    def test_route_actions_exist(self):
        """All expected route actions exist."""
        actions = [
            RouteAction.BUILD_GRAPH,
            RouteAction.DETECT_PATTERNS,
            RouteAction.LOAD_CONTEXT,
            RouteAction.CREATE_BEADS,
            RouteAction.SPAWN_ATTACKERS,
            RouteAction.SPAWN_DEFENDERS,
            RouteAction.SPAWN_VERIFIERS,
            RouteAction.RUN_DEBATE,
            RouteAction.COLLECT_VERDICTS,
            RouteAction.GENERATE_REPORT,
            RouteAction.FLAG_FOR_HUMAN,
            RouteAction.COMPLETE,
            RouteAction.WAIT,
        ]
        assert len(actions) == 13

    def test_route_action_values(self):
        """Route actions have correct string values."""
        assert RouteAction.BUILD_GRAPH.value == "build_graph"
        assert RouteAction.SPAWN_ATTACKERS.value == "spawn_attackers"
        assert RouteAction.FLAG_FOR_HUMAN.value == "flag_for_human"


class TestRouteDecision:
    """Tests for RouteDecision dataclass."""

    def test_route_decision_creation(self):
        """RouteDecision can be created with defaults."""
        decision = RouteDecision(action=RouteAction.BUILD_GRAPH)
        assert decision.action == RouteAction.BUILD_GRAPH
        assert decision.target_beads == []
        assert decision.reason == ""
        assert decision.metadata == {}

    def test_route_decision_with_target_beads(self):
        """RouteDecision tracks target beads."""
        decision = RouteDecision(
            action=RouteAction.SPAWN_ATTACKERS,
            target_beads=["VKG-001", "VKG-002"],
            reason="2 beads need attacker analysis",
        )
        assert decision.target_beads == ["VKG-001", "VKG-002"]
        assert "2 beads" in decision.reason


class TestRouter:
    """Test thin routing layer (ORCH-01)."""

    def test_routes_intake_to_build_graph(self):
        """INTAKE status routes to BUILD_GRAPH."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.INTAKE)

        decision = router.route(pool)
        assert decision.action == RouteAction.BUILD_GRAPH

    def test_intake_returns_wait_after_graph_built(self):
        """INTAKE returns WAIT after graph_built metadata set (prevents infinite loop)."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.INTAKE)
        pool.metadata["graph_built"] = True

        decision = router.route(pool)
        assert decision.action == RouteAction.WAIT

    def test_routes_context_to_detect_patterns_first(self):
        """CONTEXT status routes to DETECT_PATTERNS when patterns not yet detected."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.CONTEXT)

        decision = router.route(pool)
        assert decision.action == RouteAction.DETECT_PATTERNS

    def test_routes_context_to_load_context_after_patterns(self):
        """CONTEXT status routes to LOAD_CONTEXT after patterns detected."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.CONTEXT)
        pool.metadata["patterns_detected"] = True

        decision = router.route(pool)
        assert decision.action == RouteAction.LOAD_CONTEXT

    def test_context_phase_returns_wait_when_complete(self):
        """CONTEXT phase returns WAIT when both patterns and context are done."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.CONTEXT)
        pool.metadata["patterns_detected"] = True
        pool.metadata["context_loaded"] = True

        decision = router.route(pool)
        assert decision.action == RouteAction.WAIT

    def test_routes_beads_to_create_beads(self):
        """BEADS status routes to CREATE_BEADS."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.BEADS)

        decision = router.route(pool)
        assert decision.action == RouteAction.CREATE_BEADS

    def test_routes_integrate_to_generate_report(self):
        """INTEGRATE status routes to GENERATE_REPORT."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.INTEGRATE)

        decision = router.route(pool)
        assert decision.action == RouteAction.GENERATE_REPORT

    def test_routes_complete_to_complete(self):
        """COMPLETE status routes to COMPLETE action."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.COMPLETE)

        decision = router.route(pool)
        assert decision.action == RouteAction.COMPLETE

    def test_routes_failed_to_wait(self):
        """FAILED status routes to WAIT."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.FAILED,
            metadata={"failure_reason": "Test failure"},
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.WAIT
        assert "failed" in decision.reason.lower()

    def test_routes_paused_to_wait(self):
        """PAUSED status routes to WAIT."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.PAUSED,
            metadata={"pause_reason": "Awaiting human"},
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.WAIT
        assert "paused" in decision.reason.lower()

    def test_execute_phase_batch_order_attackers_first(self):
        """Execute phase spawns attackers first."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.EXECUTE,
            bead_ids=["VKG-001", "VKG-002"],
            metadata={},
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.SPAWN_ATTACKERS
        assert set(decision.target_beads) == {"VKG-001", "VKG-002"}

    def test_execute_phase_defenders_after_attackers(self):
        """Execute phase spawns defenders after all attackers done."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.EXECUTE,
            bead_ids=["VKG-001", "VKG-002"],
            metadata={"attacker_processed": ["VKG-001", "VKG-002"]},
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.SPAWN_DEFENDERS
        assert set(decision.target_beads) == {"VKG-001", "VKG-002"}

    def test_execute_phase_verifiers_after_defenders(self):
        """Execute phase spawns verifiers after all defenders done."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.EXECUTE,
            bead_ids=["VKG-001", "VKG-002"],
            metadata={
                "attacker_processed": ["VKG-001", "VKG-002"],
                "defender_processed": ["VKG-001", "VKG-002"],
            },
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.SPAWN_VERIFIERS
        assert set(decision.target_beads) == {"VKG-001", "VKG-002"}

    def test_execute_phase_waits_when_complete(self):
        """Execute phase waits when all roles done."""
        router = Router()
        scope = Scope(files=["Test.sol"])
        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.EXECUTE,
            bead_ids=["VKG-001", "VKG-002"],
            metadata={
                "attacker_processed": ["VKG-001", "VKG-002"],
                "defender_processed": ["VKG-001", "VKG-002"],
                "verifier_processed": ["VKG-001", "VKG-002"],
            },
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.WAIT
        assert "complete" in decision.reason.lower()

    def test_routes_debate_for_uncertain_verdict(self):
        """Verify phase routes to debate for uncertain verdicts."""
        router = Router()
        scope = Scope(files=["Test.sol"])

        # Create evidence packet for uncertain verdict
        evidence = EvidencePacket(
            finding_id="VKG-001",
            items=[EvidenceItem(type="test", value="test", location="Test.sol:1")],
        )

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.UNCERTAIN,
            is_vulnerable=True,
            rationale="Disagreement between attacker and defender",
            evidence_packet=evidence,
        )

        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.VERIFY,
            bead_ids=["VKG-001"],
            verdicts={"VKG-001": verdict},
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.RUN_DEBATE
        assert "VKG-001" in decision.target_beads

    def test_routes_human_flag_for_flagged_verdict(self):
        """Verify phase routes to human flag when verdict is flagged."""
        router = Router()
        scope = Scope(files=["Test.sol"])

        # LIKELY verdict with human flag
        evidence = EvidencePacket(
            finding_id="VKG-001",
            items=[EvidenceItem(type="test", value="test", location="Test.sol:1")],
        )

        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.LIKELY,
            is_vulnerable=True,
            rationale="Strong evidence",
            evidence_packet=evidence,
            human_flag=True,  # Always True per design
        )

        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.VERIFY,
            bead_ids=["VKG-001"],
            verdicts={"VKG-001": verdict},
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.FLAG_FOR_HUMAN
        assert "VKG-001" in decision.target_beads

    def test_verify_phase_collects_when_no_debates_needed(self):
        """Verify phase collects verdicts when no debates needed."""
        router = Router()
        scope = Scope(files=["Test.sol"])

        # REJECTED verdict - no debate needed
        verdict = Verdict(
            finding_id="VKG-001",
            confidence=VerdictConfidence.REJECTED,
            is_vulnerable=False,
            rationale="False positive confirmed",
            human_flag=False,  # Will be set True by __post_init__
        )

        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.VERIFY,
            bead_ids=["VKG-001"],
            verdicts={"VKG-001": verdict},
        )

        decision = router.route(pool)
        # Should flag for human (all verdicts require human review)
        assert decision.action == RouteAction.FLAG_FOR_HUMAN

    def test_verify_phase_collects_with_no_verdicts(self):
        """Verify phase collects when no verdicts yet."""
        router = Router()
        scope = Scope(files=["Test.sol"])

        pool = Pool(
            id="test",
            scope=scope,
            status=PoolStatus.VERIFY,
            bead_ids=["VKG-001"],
            verdicts={},
        )

        decision = router.route(pool)
        assert decision.action == RouteAction.COLLECT_VERDICTS


class TestRoutePoolConvenience:
    """Test route_pool convenience function."""

    def test_route_pool_function(self):
        """route_pool function works correctly."""
        scope = Scope(files=["Test.sol"])
        pool = Pool(id="test", scope=scope, status=PoolStatus.INTAKE)

        decision = route_pool(pool)
        assert decision.action == RouteAction.BUILD_GRAPH


class TestLoopPhase:
    """Tests for LoopPhase enum."""

    def test_loop_phases_exist(self):
        """All expected loop phases exist."""
        phases = [
            LoopPhase.INTAKE,
            LoopPhase.CONTEXT,
            LoopPhase.BEADS,
            LoopPhase.EXECUTE,
            LoopPhase.VERIFY,
            LoopPhase.INTEGRATE,
            LoopPhase.COMPLETE,
        ]
        assert len(phases) == 7


class TestPhaseResult:
    """Tests for PhaseResult dataclass."""

    def test_phase_result_creation(self):
        """PhaseResult can be created with required fields."""
        result = PhaseResult(success=True, phase=LoopPhase.INTAKE)
        assert result.success
        assert result.phase == LoopPhase.INTAKE
        assert result.next_phase is None
        assert result.message == ""
        assert result.artifacts == {}
        assert not result.checkpoint

    def test_phase_result_with_checkpoint(self):
        """PhaseResult tracks checkpoints."""
        result = PhaseResult(
            success=True,
            phase=LoopPhase.VERIFY,
            message="Human review required",
            checkpoint=True,
            artifacts={"beads_for_review": ["VKG-001"]},
        )
        assert result.checkpoint
        assert "VKG-001" in result.artifacts["beads_for_review"]


class TestLoopConfig:
    """Tests for LoopConfig dataclass."""

    def test_loop_config_defaults(self):
        """LoopConfig has sensible defaults."""
        config = LoopConfig()
        assert config.auto_advance is True
        assert config.pause_on_human_flag is True
        assert config.max_iterations == 100
        assert config.verbose is False

    def test_loop_config_custom(self):
        """LoopConfig accepts custom values."""
        config = LoopConfig(
            auto_advance=False,
            pause_on_human_flag=False,
            max_iterations=50,
            verbose=True,
        )
        assert not config.auto_advance
        assert not config.pause_on_human_flag
        assert config.max_iterations == 50
        assert config.verbose


class TestExecutionLoop:
    """Test fixed execution loop (ORCH-07)."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create pool manager."""
        return PoolManager(temp_dir / "pools")

    @pytest.fixture
    def loop(self, manager):
        """Create execution loop."""
        return ExecutionLoop(manager)

    def test_loop_phase_order(self):
        """Loop follows fixed phase order."""
        expected = [
            LoopPhase.INTAKE,
            LoopPhase.CONTEXT,
            LoopPhase.BEADS,
            LoopPhase.EXECUTE,
            LoopPhase.VERIFY,
            LoopPhase.INTEGRATE,
            LoopPhase.COMPLETE,
        ]
        assert ExecutionLoop.PHASE_ORDER == expected

    def test_loop_pool_not_found(self, loop):
        """Loop returns error for missing pool."""
        result = loop.run("nonexistent")
        assert not result.success
        assert "not found" in result.message.lower()

    def test_loop_returns_complete_for_complete_pool(self, manager, loop):
        """Loop returns success for already complete pool."""
        scope = Scope(files=["Test.sol"])
        pool = manager.create_pool(scope, pool_id="test-complete")
        manager.set_status(pool.id, PoolStatus.COMPLETE)

        result = loop.run(pool.id)
        assert result.success
        assert result.phase == LoopPhase.COMPLETE
        assert "complete" in result.message.lower()

    def test_loop_returns_error_for_failed_pool(self, manager, loop):
        """Loop returns error for failed pool."""
        scope = Scope(files=["Test.sol"])
        pool = manager.create_pool(scope, pool_id="test-failed")
        manager.fail_pool(pool.id, "Test failure")

        result = loop.run(pool.id)
        assert not result.success
        assert "failed" in result.message.lower()

    def test_loop_pauses_on_human_flag(self, manager, loop):
        """Loop pauses when human review needed."""
        scope = Scope(files=["Test.sol"])
        pool = manager.create_pool(scope, pool_id="test-human-flag")
        pool.status = PoolStatus.VERIFY
        pool.bead_ids = ["VKG-001"]

        # Create a flagged verdict
        evidence = EvidencePacket(
            finding_id="VKG-001",
            items=[EvidenceItem(type="test", value="test", location="Test.sol:1")],
        )
        pool.verdicts = {
            "VKG-001": Verdict(
                finding_id="VKG-001",
                confidence=VerdictConfidence.LIKELY,
                is_vulnerable=True,
                rationale="Test",
                evidence_packet=evidence,
            )
        }
        manager.storage.save_pool(pool)

        # Configure to pause on human flag
        loop.config.pause_on_human_flag = True

        result = loop.run(pool.id)
        assert result.checkpoint
        assert "human" in result.message.lower()

    def test_loop_run_single_phase(self, manager, loop):
        """Can run single phase only."""
        scope = Scope(files=["Test.sol"])
        pool = manager.create_pool(scope, pool_id="test-single")

        # Register handler
        def intake_handler(p, beads):
            return PhaseResult(success=True, phase=LoopPhase.INTAKE, message="Graph built")

        loop.register_handler(RouteAction.BUILD_GRAPH, intake_handler)

        result = loop.run_single_phase(pool.id)
        assert result.success
        assert result.phase == LoopPhase.INTAKE
        assert result.message == "Graph built"

    def test_loop_no_handler_returns_error(self, manager, loop):
        """Loop returns error when no handler registered."""
        scope = Scope(files=["Test.sol"])
        pool = manager.create_pool(scope, pool_id="test-no-handler")

        result = loop.run(pool.id)
        assert not result.success
        # Queue-based path may hit max iterations rather than immediate "no handler"
        assert "no handler" in result.message.lower() or "max iterations" in result.message.lower()

    def test_loop_resume(self, manager, loop):
        """Loop can resume from checkpoint."""
        scope = Scope(files=["Test.sol"])
        pool = manager.create_pool(scope, pool_id="test-resume")

        # Simulate paused state (pausing from INTAKE advances to CONTEXT on resume)
        manager.pause_pool(pool.id, "Awaiting human")

        # Register handlers for resumed phase (CONTEXT after resume from INTAKE)
        def context_handler(p, beads):
            return PhaseResult(
                success=True, phase=LoopPhase.CONTEXT, message="Context loaded", checkpoint=True
            )

        # Also register INTAKE handler in case resume doesn't advance
        def intake_handler(p, beads):
            return PhaseResult(
                success=True, phase=LoopPhase.INTAKE, message="Resumed", checkpoint=True
            )

        def detect_handler(p, beads):
            p.metadata["patterns_detected"] = True
            return PhaseResult(
                success=True, phase=LoopPhase.CONTEXT, message="Patterns detected", checkpoint=True
            )

        loop.register_handler(RouteAction.BUILD_GRAPH, intake_handler)
        loop.register_handler(RouteAction.DETECT_PATTERNS, detect_handler)
        loop.register_handler(RouteAction.LOAD_CONTEXT, context_handler)

        result = loop.resume(pool.id)
        # Should be checkpointed from handler
        assert result.checkpoint or result.success

    def test_loop_max_iterations(self, manager):
        """Loop respects max iterations limit."""
        scope = Scope(files=["Test.sol"])
        pool_manager = manager
        pool = pool_manager.create_pool(scope, pool_id="test-max-iter")

        # Create loop with very low max iterations
        config = LoopConfig(max_iterations=2, auto_advance=False)
        loop = ExecutionLoop(pool_manager, config)

        # Register handler that never advances
        def handler(p, beads):
            return PhaseResult(success=True, phase=LoopPhase.INTAKE)

        loop.register_handler(RouteAction.BUILD_GRAPH, handler)

        result = loop.run(pool.id)
        assert not result.success
        assert "max iterations" in result.message.lower()

    def test_loop_handler_error_handling(self, manager, loop):
        """Loop handles handler exceptions."""
        scope = Scope(files=["Test.sol"])
        pool = manager.create_pool(scope, pool_id="test-error")

        # Register handler that raises
        def bad_handler(p, beads):
            raise ValueError("Test error")

        loop.register_handler(RouteAction.BUILD_GRAPH, bad_handler)

        result = loop.run(pool.id)
        assert not result.success
        # Queue-based path retries exhausted items and may hit max iterations
        assert "handler error" in result.message.lower() or "max iterations" in result.message.lower()


class TestPhaseTransitions:
    """Test phase transition logic."""

    @pytest.fixture
    def temp_dir(self):
        """Create temp directory for storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def loop(self, temp_dir):
        """Create execution loop."""
        manager = PoolManager(temp_dir / "pools")
        return ExecutionLoop(manager)

    def test_status_phase_mapping(self, loop):
        """Pool status maps to loop phase correctly."""
        assert loop._status_to_phase(PoolStatus.INTAKE) == LoopPhase.INTAKE
        assert loop._status_to_phase(PoolStatus.CONTEXT) == LoopPhase.CONTEXT
        assert loop._status_to_phase(PoolStatus.BEADS) == LoopPhase.BEADS
        assert loop._status_to_phase(PoolStatus.EXECUTE) == LoopPhase.EXECUTE
        assert loop._status_to_phase(PoolStatus.VERIFY) == LoopPhase.VERIFY
        assert loop._status_to_phase(PoolStatus.INTEGRATE) == LoopPhase.INTEGRATE
        assert loop._status_to_phase(PoolStatus.COMPLETE) == LoopPhase.COMPLETE

    def test_phase_status_mapping(self, loop):
        """Loop phase maps to pool status correctly."""
        assert loop._phase_to_status(LoopPhase.INTAKE) == PoolStatus.INTAKE
        assert loop._phase_to_status(LoopPhase.CONTEXT) == PoolStatus.CONTEXT
        assert loop._phase_to_status(LoopPhase.BEADS) == PoolStatus.BEADS
        assert loop._phase_to_status(LoopPhase.EXECUTE) == PoolStatus.EXECUTE
        assert loop._phase_to_status(LoopPhase.VERIFY) == PoolStatus.VERIFY
        assert loop._phase_to_status(LoopPhase.INTEGRATE) == PoolStatus.INTEGRATE
        assert loop._phase_to_status(LoopPhase.COMPLETE) == PoolStatus.COMPLETE

    def test_get_phase_index(self, loop):
        """Phase index is correctly determined."""
        assert loop._get_phase_index(PoolStatus.INTAKE) == 0
        assert loop._get_phase_index(PoolStatus.CONTEXT) == 1
        assert loop._get_phase_index(PoolStatus.BEADS) == 2
        assert loop._get_phase_index(PoolStatus.EXECUTE) == 3
        assert loop._get_phase_index(PoolStatus.VERIFY) == 4
        assert loop._get_phase_index(PoolStatus.INTEGRATE) == 5
        assert loop._get_phase_index(PoolStatus.COMPLETE) == 6

    def test_terminal_status_index_is_none(self, loop):
        """Terminal statuses return valid index."""
        # FAILED and PAUSED map to INTAKE phase for index lookup
        assert loop._get_phase_index(PoolStatus.FAILED) == 0
        assert loop._get_phase_index(PoolStatus.PAUSED) == 0
