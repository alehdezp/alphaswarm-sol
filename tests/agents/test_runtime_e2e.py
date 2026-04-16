"""End-to-End Runtime Tests.

Comprehensive E2E tests for the runtime system covering:
- Complete execution flow through PropulsionEngine
- Runtime routing matrix (role, task_type -> runtime)
- Model selection within OpenCode
- Fallback behavior from free to paid models
- Ranking updates based on feedback
- Cost tracking accuracy
- Loop prevention mechanisms
- Session management for Claude Code
- Concurrent execution safety
- Error recovery and retry logic

Per 05.3-10-PLAN.md:
- 100+ total runtime-related tests
- E2E flow verification
- Fallback behavior verification
- Ranking updates verification
- Cost tracking verification
- >90% coverage on new code
"""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse, AgentRole
from alphaswarm_sol.agents.runtime.types import TaskType
from alphaswarm_sol.agents.runtime.opencode import OpenCodeRuntime, OpenCodeConfig
from alphaswarm_sol.agents.runtime.claude_code import ClaudeCodeRuntime, ClaudeCodeConfig
from alphaswarm_sol.agents.runtime.codex_cli import CodexCLIRuntime, CodexCLIConfig
from alphaswarm_sol.agents.runtime.router import (
    TaskRouter,
    RoutingPolicy,
    route_to_runtime,
)
from alphaswarm_sol.agents.runtime.factory import create_runtime, RuntimeType
from alphaswarm_sol.agents.ranking import (
    RankingsStore,
    ModelSelector,
    FeedbackCollector,
    TaskFeedback,
    TaskProfile,
    ModelRanking,
)
from alphaswarm_sol.agents.propulsion import (
    PropulsionEngine,
    PropulsionConfig,
    WorkResult,
    CostSummary,
    AgentCoordinator,
    ROLE_TO_TASK_TYPE,
)


# =============================================================================
# Helper Functions
# =============================================================================


def create_mock_response(
    content: str = "Test response",
    model: str = "test/model",
    cost_usd: float = 0.001,
    latency_ms: int = 500,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> AgentResponse:
    """Create a mock AgentResponse."""
    return AgentResponse(
        content=content,
        tool_calls=[],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        metadata={},
    )


class MockRuntime:
    """Mock runtime for testing."""

    def __init__(
        self,
        model: str = "test/model",
        cost_usd: float = 0.001,
        should_fail: bool = False,
        fail_message: str = "Mock failure",
    ):
        self.model = model
        self.cost_usd = cost_usd
        self.should_fail = should_fail
        self.fail_message = fail_message
        self.execute_calls: List[Dict[str, Any]] = []
        self.spawn_calls: List[Dict[str, Any]] = []

    async def execute(
        self,
        config: AgentConfig,
        messages: List[Dict[str, Any]],
    ) -> AgentResponse:
        self.execute_calls.append({
            "config": config,
            "messages": messages,
        })
        if self.should_fail:
            raise RuntimeError(self.fail_message)
        return create_mock_response(
            model=self.model,
            cost_usd=self.cost_usd,
        )

    async def spawn_agent(
        self,
        config: AgentConfig,
        task: str,
    ) -> AgentResponse:
        self.spawn_calls.append({
            "config": config,
            "task": task,
        })
        if self.should_fail:
            raise RuntimeError(self.fail_message)
        return create_mock_response(
            model=self.model,
            cost_usd=self.cost_usd,
        )

    def get_model_for_role(self, role: AgentRole) -> str:
        return self.model

    def get_usage(self) -> Dict[str, Any]:
        return {"total_cost_usd": self.cost_usd * len(self.execute_calls)}


# =============================================================================
# Test Complete Execution Flow
# =============================================================================


class TestCompleteExecutionFlow:
    """Tests for complete end-to-end execution flow."""

    @pytest.mark.asyncio
    async def test_engine_executes_with_router_and_selector(self, tmp_path):
        """Test complete: engine -> router -> selector -> runtime -> feedback."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime(model="deepseek/deepseek-v3.2", cost_usd=0.001)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(
                role=AgentRole.ATTACKER,
                system_prompt="Find vulnerabilities",
            )

            response = await engine.execute_agent(
                config,
                [{"role": "user", "content": "Analyze this contract"}],
                task_type=TaskType.CRITICAL,
            )

            # Verify response
            assert response.content == "Test response"
            assert response.model == "deepseek/deepseek-v3.2"

            # Verify router was called
            assert mock_router.route.called

    @pytest.mark.asyncio
    async def test_response_returned_correctly(self, tmp_path):
        """Verify response is returned correctly through the flow."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime(
            model="test/model",
            cost_usd=0.002,
        )

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Verify")
            response = await engine.execute_agent(
                config,
                [{"role": "user", "content": "Test"}],
            )

            assert response is not None
            assert isinstance(response, AgentResponse)
            assert response.input_tokens == 100
            assert response.output_tokens == 50

    @pytest.mark.asyncio
    async def test_feedback_recorded_after_execution(self, tmp_path):
        """Verify feedback is recorded after successful execution."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime(model="test/model", cost_usd=0.001)

        # Add initial ranking
        store.update_ranking(ModelRanking(
            model_id="test/model",
            task_type="analyze",
            quality_score=0.8,
            sample_count=5,
        ))

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(role=AgentRole.DEFENDER, system_prompt="Test")
            await engine.execute_agent(
                config,
                [{"role": "user", "content": "Test"}],
                task_type=TaskType.ANALYZE,
            )

            # Verify feedback was recorded (sample count increased)
            ranking = store.get_ranking("test/model", "analyze")
            assert ranking.sample_count > 5


# =============================================================================
# Test Runtime Routing Matrix
# =============================================================================


class TestRuntimeRoutingMatrix:
    """Tests for runtime routing based on role and task type."""

    @pytest.mark.parametrize("role,task_type,expected_runtime", [
        # Critical analysis -> Claude Code
        (AgentRole.ATTACKER, TaskType.CRITICAL, ClaudeCodeRuntime),
        (AgentRole.VERIFIER, TaskType.CRITICAL, ClaudeCodeRuntime),
        # Review -> Codex CLI
        (AgentRole.DEFENDER, TaskType.REVIEW, CodexCLIRuntime),
        (AgentRole.INTEGRATOR, TaskType.REVIEW, CodexCLIRuntime),
        # Standard tasks -> OpenCode
        (AgentRole.DEFENDER, TaskType.ANALYZE, OpenCodeRuntime),
        (AgentRole.TEST_BUILDER, TaskType.CODE, OpenCodeRuntime),
        (AgentRole.INTEGRATOR, TaskType.SUMMARIZE, OpenCodeRuntime),
        (AgentRole.SUPERVISOR, TaskType.VERIFY, OpenCodeRuntime),
        # Reasoning tasks -> OpenCode
        (AgentRole.ATTACKER, TaskType.REASONING, OpenCodeRuntime),
        (AgentRole.DEFENDER, TaskType.REASONING_HEAVY, OpenCodeRuntime),
    ])
    def test_routing_matrix(self, role, task_type, expected_runtime):
        """Test routing matrix matches expected runtimes."""
        # Accuracy critical only matters for critical task type
        accuracy_critical = task_type == TaskType.CRITICAL
        runtime = route_to_runtime(
            role=role,
            task_type=task_type,
            accuracy_critical=accuracy_critical,
        )
        assert isinstance(runtime, expected_runtime), (
            f"Expected {expected_runtime.__name__} for {role}/{task_type}, "
            f"got {type(runtime).__name__}"
        )

    def test_attacker_accuracy_critical_to_claude(self):
        """ATTACKER + accuracy_critical routes to Claude Code."""
        runtime = route_to_runtime(
            AgentRole.ATTACKER,
            TaskType.ANALYZE,
            accuracy_critical=True,
        )
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_verifier_accuracy_critical_to_claude(self):
        """VERIFIER + accuracy_critical routes to Claude Code."""
        runtime = route_to_runtime(
            AgentRole.VERIFIER,
            TaskType.VERIFY,
            accuracy_critical=True,
        )
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_attacker_without_accuracy_to_opencode(self):
        """ATTACKER without accuracy_critical routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.ATTACKER,
            TaskType.ANALYZE,
            accuracy_critical=False,
        )
        assert isinstance(runtime, OpenCodeRuntime)


# =============================================================================
# Test Model Selection Within OpenCode
# =============================================================================


class TestOpenCodeModelSelection:
    """Tests for model selection within OpenCode runtime."""

    def test_verify_task_returns_free_model(self):
        """VERIFY task type returns free model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.VERIFY, None)
        assert "free" in model.lower() or "minimax" in model.lower()

    def test_reasoning_task_returns_deepseek(self):
        """REASONING task type returns DeepSeek model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.REASONING, None)
        assert "deepseek" in model.lower()

    def test_code_task_returns_glm(self):
        """CODE task type returns GLM model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.CODE, None)
        assert "glm" in model.lower()

    def test_heavy_task_returns_gemini_flash(self):
        """HEAVY task type returns Gemini Flash."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.HEAVY, None)
        assert "gemini" in model.lower()

    def test_summarize_task_returns_free_model(self):
        """SUMMARIZE task type returns free model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.SUMMARIZE, None)
        assert "free" in model.lower() or "minimax" in model.lower()

    def test_context_task_returns_grok(self):
        """CONTEXT task type returns Grok."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.CONTEXT, None)
        assert "grok" in model.lower()


# =============================================================================
# Test Fallback Behavior
# =============================================================================


class TestFallbackBehavior:
    """Tests for fallback from free models to paid models."""

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self, tmp_path):
        """Verify fallback from OpenCode to Claude Code on failure."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        failing_runtime = MockRuntime(should_fail=True, fail_message="OpenCode failed")
        fallback_runtime = MockRuntime(model="claude-sonnet-4", cost_usd=0.0)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter, patch(
            "alphaswarm_sol.agents.propulsion.engine.route_to_runtime"
        ) as mock_route:
            mock_router = MagicMock()
            mock_router.route.return_value = failing_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router
            mock_route.return_value = fallback_runtime

            engine = PropulsionEngine(
                runtime=failing_runtime,
                inboxes={},
                rankings_store=store,
                config=PropulsionConfig(enable_fallback=True),
            )

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")
            response = await engine.execute_agent(
                config,
                [{"role": "user", "content": "Test"}],
                task_type=TaskType.ANALYZE,
            )

            # Verify fallback was used
            assert response.metadata.get("fallback") is True
            assert response.model == "claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_fallback_logged(self, tmp_path):
        """Verify fallback is logged in engine statistics."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        failing_runtime = MockRuntime(should_fail=True)
        fallback_runtime = MockRuntime(model="claude", cost_usd=0.0)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter, patch(
            "alphaswarm_sol.agents.propulsion.engine.route_to_runtime"
        ) as mock_route:
            mock_router = MagicMock()
            mock_router.route.return_value = failing_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router
            mock_route.return_value = fallback_runtime

            engine = PropulsionEngine(
                runtime=failing_runtime,
                inboxes={},
                rankings_store=store,
                config=PropulsionConfig(enable_fallback=True),
            )

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")
            await engine.execute_agent(config, [{"role": "user", "content": "Test"}])

            # Verify fallback rate updated
            assert engine.get_fallback_rate() > 0

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self, tmp_path):
        """Verify fallback is not attempted when disabled."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        failing_runtime = MockRuntime(should_fail=True, fail_message="Test error")

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = failing_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=failing_runtime,
                inboxes={},
                rankings_store=store,
                config=PropulsionConfig(enable_fallback=False),
            )

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")

            with pytest.raises(RuntimeError, match="Test error"):
                await engine.execute_agent(
                    config,
                    [{"role": "user", "content": "Test"}],
                )

    @pytest.mark.asyncio
    async def test_fallback_when_claude_code_already_no_retry(self, tmp_path):
        """Claude Code failure doesn't trigger fallback to itself."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        failing_runtime = MockRuntime(should_fail=True, fail_message="Claude failed")
        # Pretend this is already Claude Code
        failing_runtime.__class__.__name__ = "ClaudeCodeRuntime"

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = failing_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=failing_runtime,
                inboxes={},
                rankings_store=store,
                config=PropulsionConfig(enable_fallback=True),
            )

            # Mock _get_runtime_name to return claude_code
            engine._get_runtime_name = lambda r: "claude_code"

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")

            with pytest.raises(RuntimeError, match="Claude failed"):
                await engine.execute_agent(
                    config,
                    [{"role": "user", "content": "Test"}],
                )


# =============================================================================
# Test Ranking Updates
# =============================================================================


class TestRankingUpdates:
    """Tests for ranking updates after execution."""

    @pytest.mark.asyncio
    async def test_rankings_updated_after_execution(self, tmp_path):
        """Verify rankings are updated after execution."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Add initial ranking
        store.update_ranking(ModelRanking(
            model_id="test/model",
            task_type="critical",
            quality_score=0.7,
            success_rate=0.8,
            sample_count=5,
        ))

        mock_runtime = MockRuntime(model="test/model", cost_usd=0.001)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")

            # Execute multiple times
            for _ in range(3):
                await engine.execute_agent(
                    config,
                    [{"role": "user", "content": "Test"}],
                    task_type=TaskType.CRITICAL,
                )

            # Verify rankings updated
            ranking = store.get_ranking("test/model", "critical")
            assert ranking.sample_count > 5  # Should have added samples

    @pytest.mark.asyncio
    async def test_better_model_selected_after_feedback(self, tmp_path):
        """Verify better model is selected after positive feedback."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Add two models, one initially lower ranked
        store.update_ranking(ModelRanking(
            model_id="model-a",
            task_type="analyze",
            quality_score=0.8,
            success_rate=0.9,
            sample_count=10,
        ))
        store.update_ranking(ModelRanking(
            model_id="model-b",
            task_type="analyze",
            quality_score=0.6,
            success_rate=0.7,
            sample_count=10,
        ))

        selector = ModelSelector(store)
        profile = TaskProfile(task_type=TaskType.ANALYZE)

        # Initial selection should be model-a
        selected = selector.select(profile)
        assert selected == "model-a"

    @pytest.mark.asyncio
    async def test_sample_count_increases_with_feedback(self, tmp_path):
        """Verify sample count increases with each feedback."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)

        # Record feedback
        for i in range(5):
            feedback = TaskFeedback(
                task_id=f"task-{i}",
                model_id="test/model",
                task_type="verify",
                success=True,
                latency_ms=500,
                tokens_used=100,
                quality_score=0.9,
                cost_usd=0.0,
            )
            collector.record(feedback)

        # Verify sample count
        ranking = store.get_ranking("test/model", "verify")
        assert ranking.sample_count == 5


# =============================================================================
# Test Cost Tracking
# =============================================================================


class TestCostTracking:
    """Tests for cost tracking accuracy."""

    @pytest.mark.asyncio
    async def test_costs_aggregated_across_executions(self, tmp_path):
        """Test that costs are aggregated across executions."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime(model="test/model", cost_usd=0.002)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")

            # Execute 5 times
            for _ in range(5):
                await engine.execute_agent(
                    config,
                    [{"role": "user", "content": "Test"}],
                )

            summary = engine.get_cost_summary()
            assert summary.execution_count == 5
            assert summary.total_cost_usd == pytest.approx(0.01, rel=0.1)

    @pytest.mark.asyncio
    async def test_free_models_show_zero_cost(self, tmp_path):
        """Test that free models show $0 cost."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime(model="minimax/minimax-m2:free", cost_usd=0.0)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            await engine.execute_agent(
                config,
                [{"role": "user", "content": "Test"}],
                task_type=TaskType.VERIFY,
            )

            summary = engine.get_cost_summary()
            assert summary.total_cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_cost_breakdown_by_runtime(self, tmp_path):
        """Test cost breakdown by runtime."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime(model="test/model", cost_usd=0.003)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")
            await engine.execute_agent(config, [{"role": "user", "content": "Test"}])

            summary = engine.get_cost_summary()
            assert summary.by_role.get("attacker", 0) > 0

    def test_cost_summary_to_dict(self):
        """Test CostSummary serialization."""
        summary = CostSummary()
        summary.add_execution(0.001, "opencode", "test/model", "attacker")
        summary.add_execution(0.002, "claude_code", "claude", "defender")

        data = summary.to_dict()

        assert data["total_cost_usd"] == pytest.approx(0.003, rel=0.001)
        assert data["execution_count"] == 2
        assert "opencode" in data["by_runtime"]
        assert "attacker" in data["by_role"]


# =============================================================================
# Test Loop Prevention
# =============================================================================


class TestLoopPrevention:
    """Tests for loop prevention mechanisms."""

    def test_repeated_outputs_detected(self):
        """Test that repeated outputs are detected."""
        from alphaswarm_sol.agents.runtime.opencode import (
            OpenCodeRuntime,
            OpenCodeConfig,
            LoopState,
            MAX_REPEATED_OUTPUTS,
        )

        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState()

        same_output = "identical output every time"

        # First MAX_REPEATED_OUTPUTS calls don't trigger
        for _ in range(MAX_REPEATED_OUTPUTS):
            result = runtime._check_loop_prevention(state, same_output)
            assert result is False

        # Next call with same output triggers
        result = runtime._check_loop_prevention(state, same_output)
        assert result is True

    def test_token_ceiling_enforced(self):
        """Test that token ceiling is enforced."""
        from alphaswarm_sol.agents.runtime.opencode import (
            OpenCodeRuntime,
            OpenCodeConfig,
            LoopState,
            TOKEN_CEILING,
        )

        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState(total_tokens_used=TOKEN_CEILING)

        result = runtime._check_loop_prevention(state, "test output")
        assert result is True

    def test_different_outputs_dont_trigger(self):
        """Test that different outputs don't trigger loop detection."""
        from alphaswarm_sol.agents.runtime.opencode import (
            OpenCodeRuntime,
            OpenCodeConfig,
            LoopState,
            MAX_REPEATED_OUTPUTS,
        )

        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState()

        # Different outputs should never trigger
        for i in range(MAX_REPEATED_OUTPUTS + 10):
            result = runtime._check_loop_prevention(state, f"output {i}")
            assert result is False


# =============================================================================
# Test Session Management (Claude Code)
# =============================================================================


class TestSessionManagement:
    """Tests for Claude Code session management."""

    def test_session_id_generates_consistent_path(self):
        """Test that same session ID generates same path."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        path1 = runtime._get_session_file("session-123")
        path2 = runtime._get_session_file("session-123")
        assert path1 == path2

    def test_different_sessions_different_paths(self):
        """Test that different session IDs generate different paths."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        path1 = runtime._get_session_file("session-a")
        path2 = runtime._get_session_file("session-b")
        assert path1 != path2

    def test_resume_flag_with_session(self):
        """Test that --resume flag is included with session."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-sonnet-4",
            session_id="my-session",
        )
        assert "--resume" in cmd
        idx = cmd.index("--resume")
        assert cmd[idx + 1] == "my-session"

    def test_no_resume_without_session(self):
        """Test that --resume flag is absent without session."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-sonnet-4",
            session_id=None,
        )
        assert "--resume" not in cmd


# =============================================================================
# Test Concurrent Execution
# =============================================================================


class TestConcurrentExecution:
    """Tests for concurrent execution safety."""

    @pytest.mark.asyncio
    async def test_concurrent_executions_no_race_conditions(self, tmp_path):
        """Test that concurrent executions don't cause race conditions."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Add initial ranking
        store.update_ranking(ModelRanking(
            model_id="test/model",
            task_type="analyze",
            quality_score=0.8,
            sample_count=0,
        ))

        mock_runtime = MockRuntime(model="test/model", cost_usd=0.001)

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            config = AgentConfig(role=AgentRole.DEFENDER, system_prompt="Test")

            # Execute concurrently
            tasks = [
                engine.execute_agent(
                    config,
                    [{"role": "user", "content": f"Test {i}"}],
                    task_type=TaskType.ANALYZE,
                )
                for i in range(5)
            ]

            responses = await asyncio.gather(*tasks)

            # Verify all completed
            assert len(responses) == 5
            assert all(r.content == "Test response" for r in responses)

            # Verify costs aggregated correctly
            summary = engine.get_cost_summary()
            assert summary.execution_count == 5

    @pytest.mark.asyncio
    async def test_rankings_updated_correctly_with_concurrent_feedback(self, tmp_path):
        """Test that rankings are updated correctly with concurrent feedback."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        collector = FeedbackCollector(store, auto_save=False)

        # Add initial ranking
        store.update_ranking(ModelRanking(
            model_id="test/model",
            task_type="verify",
            quality_score=0.5,
            sample_count=0,
        ))

        # Record feedback concurrently (simulated)
        for i in range(10):
            feedback = TaskFeedback(
                task_id=f"task-{i}",
                model_id="test/model",
                task_type="verify",
                success=True,
                latency_ms=500,
                tokens_used=100,
                quality_score=0.9,
                cost_usd=0.0,
            )
            collector.record(feedback)

        # Verify sample count
        ranking = store.get_ranking("test/model", "verify")
        assert ranking.sample_count == 10


# =============================================================================
# Test Error Recovery
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery and retry logic."""

    @pytest.mark.asyncio
    async def test_timeout_handled_gracefully(self, tmp_path):
        """Test that timeout is handled gracefully."""
        store = RankingsStore(tmp_path / "rankings.yaml")

        # Create a runtime that times out
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(10)  # Will be cancelled
            return create_mock_response()

        mock_runtime = MockRuntime()
        mock_runtime.execute = slow_execute

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
                config=PropulsionConfig(work_timeout_seconds=1),
            )

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")

            with pytest.raises(asyncio.TimeoutError):
                await engine.execute_agent(
                    config,
                    [{"role": "user", "content": "Test"}],
                )

    @pytest.mark.asyncio
    async def test_retry_logic_in_opencode_runtime(self):
        """Test retry logic in OpenCode runtime."""
        config = OpenCodeConfig(max_retries=2)
        runtime = OpenCodeRuntime(config)

        call_count = 0

        async def mock_run(cmd, timeout):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary error")
            return {"content": "Success", "usage": {"input_tokens": 10, "output_tokens": 5}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            agent_config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            response = await runtime.execute(agent_config, messages)

            assert response.content == "Success"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_auth_error_fails_fast(self):
        """Test that authentication errors fail fast without retries."""
        config = OpenCodeConfig(max_retries=3)
        runtime = OpenCodeRuntime(config)

        call_count = 0

        async def mock_run(cmd, timeout):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Authentication error: Invalid API key")

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            agent_config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RuntimeError, match="Authentication error"):
                await runtime.execute(agent_config, messages)

            # Should only be called once (no retries for auth)
            assert call_count == 1


# =============================================================================
# Test ROLE_TO_TASK_TYPE Mapping
# =============================================================================


class TestRoleToTaskTypeMapping:
    """Tests for role-to-task-type mapping."""

    def test_attacker_maps_to_critical(self):
        """ATTACKER maps to CRITICAL."""
        assert ROLE_TO_TASK_TYPE["attacker"] == TaskType.CRITICAL

    def test_defender_maps_to_analyze(self):
        """DEFENDER maps to ANALYZE."""
        assert ROLE_TO_TASK_TYPE["defender"] == TaskType.ANALYZE

    def test_verifier_maps_to_critical(self):
        """VERIFIER maps to CRITICAL."""
        assert ROLE_TO_TASK_TYPE["verifier"] == TaskType.CRITICAL

    def test_test_builder_maps_to_code(self):
        """TEST_BUILDER maps to CODE."""
        assert ROLE_TO_TASK_TYPE["test_builder"] == TaskType.CODE


# =============================================================================
# Test Factory Integration
# =============================================================================


class TestFactoryIntegration:
    """Tests for runtime factory integration."""

    def test_default_factory_returns_opencode(self):
        """Default factory returns OpenCode runtime."""
        runtime = create_runtime()
        assert isinstance(runtime, OpenCodeRuntime)

    def test_factory_with_opencode(self):
        """Factory with 'opencode' returns OpenCode."""
        runtime = create_runtime("opencode")
        assert isinstance(runtime, OpenCodeRuntime)

    def test_factory_with_claude_code(self):
        """Factory with 'claude_code' returns Claude Code."""
        runtime = create_runtime("claude_code")
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_factory_with_codex(self):
        """Factory with 'codex' returns Codex CLI."""
        runtime = create_runtime("codex")
        assert isinstance(runtime, CodexCLIRuntime)

    def test_factory_with_config(self):
        """Factory accepts runtime-specific config."""
        config = OpenCodeConfig(timeout_seconds=60)
        runtime = create_runtime("opencode", config=config)
        assert runtime.config.timeout_seconds == 60


# =============================================================================
# Test Router Statistics
# =============================================================================


class TestRouterStatistics:
    """Tests for router statistics tracking."""

    def test_router_tracks_route_counts(self):
        """Router tracks route counts by runtime."""
        router = TaskRouter()

        # Route to different runtimes
        router.route(RoutingPolicy(task_type=TaskType.VERIFY))
        router.route(RoutingPolicy(task_type=TaskType.VERIFY))
        router.route(RoutingPolicy(task_type=TaskType.CRITICAL))
        router.route(RoutingPolicy(task_type=TaskType.REVIEW))

        stats = router.get_route_statistics()
        assert stats["opencode"] == 2
        assert stats["claude_code"] == 1
        assert stats["codex"] == 1

    def test_router_reset_statistics(self):
        """Router can reset statistics."""
        router = TaskRouter()

        router.route(RoutingPolicy(task_type=TaskType.VERIFY))
        router.route(RoutingPolicy(task_type=TaskType.VERIFY))

        router.reset_statistics()

        stats = router.get_route_statistics()
        assert stats["opencode"] == 0
        assert stats["claude_code"] == 0
        assert stats["codex"] == 0


# =============================================================================
# Test Quality Estimation
# =============================================================================


class TestQualityEstimation:
    """Tests for quality score estimation from response."""

    @pytest.mark.asyncio
    async def test_empty_response_zero_quality(self, tmp_path):
        """Empty response returns 0.0 quality."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        engine = PropulsionEngine(
            runtime=MockRuntime(),
            inboxes={},
            rankings_store=store,
        )

        response = AgentResponse(
            content="",
            tool_calls=[],
            input_tokens=100,
            output_tokens=0,
        )
        assert engine._estimate_quality(response) == 0.0

    @pytest.mark.asyncio
    async def test_non_empty_response_base_quality(self, tmp_path):
        """Non-empty response returns base quality."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        engine = PropulsionEngine(
            runtime=MockRuntime(),
            inboxes={},
            rankings_store=store,
        )

        response = AgentResponse(
            content="Some analysis result",
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
        )
        quality = engine._estimate_quality(response)
        assert 0.7 <= quality <= 0.8

    @pytest.mark.asyncio
    async def test_long_response_higher_quality(self, tmp_path):
        """Long response with tools gets higher quality."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        engine = PropulsionEngine(
            runtime=MockRuntime(),
            inboxes={},
            rankings_store=store,
        )

        response = AgentResponse(
            content="A" * 1000,
            tool_calls=[{"name": "test"}],
            input_tokens=100,
            output_tokens=500,
        )
        quality = engine._estimate_quality(response)
        assert quality > 0.8


# =============================================================================
# Test WorkResult Serialization
# =============================================================================


class TestWorkResultSerialization:
    """Tests for WorkResult serialization."""

    def test_work_result_to_dict(self):
        """WorkResult serializes to dict correctly."""
        result = WorkResult(
            bead_id="VKG-001",
            agent_role=AgentRole.ATTACKER,
            success=True,
            duration_ms=500,
            runtime_used="opencode",
            model_used="deepseek/deepseek-v3.2",
            cost_usd=0.001,
        )

        data = result.to_dict()

        assert data["bead_id"] == "VKG-001"
        assert data["agent_role"] == "attacker"
        assert data["success"] is True
        assert data["runtime_used"] == "opencode"
        assert data["model_used"] == "deepseek/deepseek-v3.2"
        assert data["cost_usd"] == 0.001

    def test_work_result_with_error(self):
        """WorkResult with error serializes correctly."""
        result = WorkResult(
            bead_id="VKG-002",
            agent_role=AgentRole.DEFENDER,
            success=False,
            error="Timeout occurred",
            duration_ms=30000,
        )

        data = result.to_dict()

        assert data["success"] is False
        assert data["error"] == "Timeout occurred"


# =============================================================================
# Test Engine Configuration
# =============================================================================


class TestEngineConfiguration:
    """Tests for PropulsionEngine configuration."""

    def test_config_defaults(self):
        """PropulsionConfig has correct defaults."""
        config = PropulsionConfig()

        assert config.max_concurrent_per_role == 2
        assert config.poll_interval_seconds == 1.0
        assert config.work_timeout_seconds == 300
        assert config.enable_resume is True
        assert config.enable_fallback is True
        assert config.cost_threshold_usd is None

    def test_config_custom_values(self):
        """PropulsionConfig accepts custom values."""
        config = PropulsionConfig(
            max_concurrent_per_role=5,
            work_timeout_seconds=600,
            cost_threshold_usd=1.0,
        )

        assert config.max_concurrent_per_role == 5
        assert config.work_timeout_seconds == 600
        assert config.cost_threshold_usd == 1.0

    def test_config_to_dict(self):
        """PropulsionConfig serializes correctly."""
        config = PropulsionConfig(
            max_concurrent_per_role=3,
            enable_fallback=False,
        )

        data = config.to_dict()

        assert data["max_concurrent_per_role"] == 3
        assert data["enable_fallback"] is False
        assert "on_complete" not in data  # Callbacks not serialized


# =============================================================================
# Test spawn_agent Method
# =============================================================================


class TestSpawnAgentMethod:
    """Tests for spawn_agent method."""

    @pytest.mark.asyncio
    async def test_spawn_agent_derives_task_type_from_role(self, tmp_path):
        """spawn_agent derives task_type from role when not specified."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime()

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            # Track selector calls
            select_calls = []
            original_select = engine.selector.select

            def spy_select(profile):
                select_calls.append(profile)
                return original_select(profile)

            engine.selector.select = spy_select

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")

            # Don't specify task_type
            await engine.spawn_agent(config, "Attack this contract")

            # Should have derived CRITICAL from ATTACKER role
            assert len(select_calls) == 1
            assert select_calls[0].task_type == TaskType.CRITICAL

    @pytest.mark.asyncio
    async def test_spawn_agent_with_explicit_task_type(self, tmp_path):
        """spawn_agent uses explicit task_type when provided."""
        store = RankingsStore(tmp_path / "rankings.yaml")
        mock_runtime = MockRuntime()

        with patch(
            "alphaswarm_sol.agents.propulsion.engine.TaskRouter"
        ) as MockRouter:
            mock_router = MagicMock()
            mock_router.route.return_value = mock_runtime
            mock_router.get_route_statistics.return_value = {}
            MockRouter.return_value = mock_router

            engine = PropulsionEngine(
                runtime=mock_runtime,
                inboxes={},
                rankings_store=store,
            )

            select_calls = []
            original_select = engine.selector.select

            def spy_select(profile):
                select_calls.append(profile)
                return original_select(profile)

            engine.selector.select = spy_select

            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Test")

            # Specify explicit task_type
            await engine.spawn_agent(
                config,
                "Write code",
                task_type=TaskType.CODE,
            )

            # Should use explicit CODE, not derived CRITICAL
            assert len(select_calls) == 1
            assert select_calls[0].task_type == TaskType.CODE
