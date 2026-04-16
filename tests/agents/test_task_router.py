"""Tests for Multi-Model Task Router.

Comprehensive tests for TaskRouter covering:
- Routing rules per 05.3-CONTEXT.md
- RoutingPolicy dataclass
- TaskRouter class methods
- route_to_runtime convenience function
- Context size handling
- Fallback behavior
- Statistics tracking
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

import pytest

from alphaswarm_sol.agents.runtime.router import (
    RoutingPolicy,
    TaskRouter,
    route_to_runtime,
    LARGE_CONTEXT_THRESHOLD,
    HEAVY_CONTEXT_THRESHOLD,
)
from alphaswarm_sol.agents.runtime.base import AgentRole
from alphaswarm_sol.agents.runtime.types import TaskType
from alphaswarm_sol.agents.runtime.opencode import OpenCodeRuntime
from alphaswarm_sol.agents.runtime.claude_code import ClaudeCodeRuntime
from alphaswarm_sol.agents.runtime.codex_cli import CodexCLIRuntime


# =============================================================================
# Test RoutingPolicy Dataclass
# =============================================================================

class TestRoutingPolicy:
    """Tests for RoutingPolicy dataclass."""

    def test_minimal_policy(self):
        """Policy with only required field works."""
        policy = RoutingPolicy(task_type=TaskType.ANALYZE)
        assert policy.task_type == TaskType.ANALYZE
        assert policy.role is None
        assert policy.accuracy_critical is False
        assert policy.latency_sensitive is False
        assert policy.context_size == 0
        assert policy.preferred_runtime is None
        assert policy.metadata == {}

    def test_full_policy(self):
        """Policy with all fields works."""
        policy = RoutingPolicy(
            task_type=TaskType.CRITICAL,
            role=AgentRole.ATTACKER,
            accuracy_critical=True,
            latency_sensitive=False,
            context_size=100_000,
            preferred_runtime="opencode",
            metadata={"custom": "value"},
        )
        assert policy.task_type == TaskType.CRITICAL
        assert policy.role == AgentRole.ATTACKER
        assert policy.accuracy_critical is True
        assert policy.latency_sensitive is False
        assert policy.context_size == 100_000
        assert policy.preferred_runtime == "opencode"
        assert policy.metadata == {"custom": "value"}

    def test_to_dict_minimal(self):
        """to_dict works with minimal policy."""
        policy = RoutingPolicy(task_type=TaskType.VERIFY)
        result = policy.to_dict()

        assert result["task_type"] == "verify"
        assert result["role"] is None
        assert result["accuracy_critical"] is False
        assert result["context_size"] == 0

    def test_to_dict_with_role(self):
        """to_dict correctly serializes role."""
        policy = RoutingPolicy(
            task_type=TaskType.CRITICAL,
            role=AgentRole.ATTACKER,
        )
        result = policy.to_dict()

        assert result["task_type"] == "critical"
        assert result["role"] == "attacker"

    def test_all_task_types_valid(self):
        """All TaskType values create valid policies."""
        for task_type in TaskType:
            policy = RoutingPolicy(task_type=task_type)
            assert policy.task_type == task_type

    def test_all_roles_valid(self):
        """All AgentRole values create valid policies."""
        for role in AgentRole:
            policy = RoutingPolicy(
                task_type=TaskType.ANALYZE,
                role=role,
            )
            assert policy.role == role


# =============================================================================
# Test TaskRouter - Critical Analysis Routing
# =============================================================================

class TestRouterCriticalAnalysis:
    """Tests for critical analysis routing to Claude Code."""

    def test_attacker_accuracy_critical_to_claude(self):
        """ATTACKER + accuracy_critical routes to Claude Code."""
        runtime = route_to_runtime(
            AgentRole.ATTACKER,
            TaskType.CRITICAL,
            accuracy_critical=True,
        )
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_verifier_accuracy_critical_to_claude(self):
        """VERIFIER + accuracy_critical routes to Claude Code."""
        runtime = route_to_runtime(
            AgentRole.VERIFIER,
            TaskType.ANALYZE,
            accuracy_critical=True,
        )
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_critical_task_type_to_claude(self):
        """CRITICAL task type routes to Claude Code."""
        runtime = route_to_runtime(
            AgentRole.DEFENDER,  # Not Attacker/Verifier
            TaskType.CRITICAL,
        )
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_attacker_without_accuracy_to_opencode(self):
        """ATTACKER without accuracy_critical routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.ATTACKER,
            TaskType.ANALYZE,  # Not CRITICAL
            accuracy_critical=False,
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_verifier_without_accuracy_to_opencode(self):
        """VERIFIER without accuracy_critical routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.VERIFIER,
            TaskType.VERIFY,  # Not CRITICAL
            accuracy_critical=False,
        )
        assert isinstance(runtime, OpenCodeRuntime)


# =============================================================================
# Test TaskRouter - Review Routing
# =============================================================================

class TestRouterReview:
    """Tests for review routing to Codex CLI."""

    def test_review_task_to_codex(self):
        """REVIEW task routes to Codex CLI."""
        runtime = route_to_runtime(
            AgentRole.DEFENDER,
            TaskType.REVIEW,
        )
        assert isinstance(runtime, CodexCLIRuntime)

    def test_review_any_role_to_codex(self):
        """REVIEW task routes to Codex regardless of role."""
        for role in AgentRole:
            runtime = route_to_runtime(role, TaskType.REVIEW)
            assert isinstance(runtime, CodexCLIRuntime), f"Failed for role {role}"


# =============================================================================
# Test TaskRouter - OpenCode Routing
# =============================================================================

class TestRouterOpenCode:
    """Tests for OpenCode routing (verification, summarization, code, etc.)."""

    def test_verify_task_to_opencode(self):
        """VERIFY task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.VERIFIER,
            TaskType.VERIFY,
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_summarize_task_to_opencode(self):
        """SUMMARIZE task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.SUMMARIZE,
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_code_task_to_opencode(self):
        """CODE task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.TEST_BUILDER,
            TaskType.CODE,
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_reasoning_task_to_opencode(self):
        """REASONING task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.DEFENDER,
            TaskType.REASONING,
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_reasoning_heavy_task_to_opencode(self):
        """REASONING_HEAVY task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.ATTACKER,
            TaskType.REASONING_HEAVY,
            accuracy_critical=False,  # Override to not go Claude
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_context_task_to_opencode(self):
        """CONTEXT task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.SUPERVISOR,
            TaskType.CONTEXT,
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_heavy_task_to_opencode(self):
        """HEAVY task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.HEAVY,
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_analyze_default_to_opencode(self):
        """ANALYZE (default) task routes to OpenCode."""
        runtime = route_to_runtime(
            AgentRole.SUPERVISOR,
            TaskType.ANALYZE,
        )
        assert isinstance(runtime, OpenCodeRuntime)


# =============================================================================
# Test TaskRouter - Context Size Handling
# =============================================================================

class TestRouterContextSize:
    """Tests for context size-based routing."""

    def test_large_context_to_opencode_flash(self):
        """Large context (>200K) routes to OpenCode with Gemini Flash."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.SUMMARIZE,
            context_size=300_000,  # 300K tokens
        )
        assert isinstance(runtime, OpenCodeRuntime)
        # Verify model selection
        assert runtime.config.default_model == "google/gemini-3-flash-preview"

    def test_heavy_context_to_opencode_flash(self):
        """Heavy context (>500K) routes to OpenCode with Gemini Flash."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.ANALYZE,
            context_size=600_000,  # 600K tokens
        )
        assert isinstance(runtime, OpenCodeRuntime)
        assert runtime.config.default_model == "google/gemini-3-flash-preview"

    def test_normal_context_uses_task_default_model(self):
        """Normal context uses task-type default model."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.VERIFY,
            context_size=50_000,  # 50K tokens - normal
        )
        assert isinstance(runtime, OpenCodeRuntime)
        # VERIFY should use free model per DEFAULT_MODELS
        assert "minimax" in runtime.config.default_model.lower()

    def test_context_threshold_boundary(self):
        """Context at exactly LARGE_CONTEXT_THRESHOLD triggers large handling."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.SUMMARIZE,
            context_size=LARGE_CONTEXT_THRESHOLD,  # Exactly 200K
        )
        assert isinstance(runtime, OpenCodeRuntime)
        assert runtime.config.default_model == "google/gemini-3-flash-preview"

    def test_below_threshold_uses_default(self):
        """Context below threshold uses task default."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.SUMMARIZE,
            context_size=LARGE_CONTEXT_THRESHOLD - 1,  # Just under 200K
        )
        assert isinstance(runtime, OpenCodeRuntime)
        # Should use task-type default, not large context model


# =============================================================================
# Test TaskRouter - Preferred Runtime Override
# =============================================================================

class TestRouterPreferredOverride:
    """Tests for preferred_runtime override."""

    def test_preferred_opencode_overrides_claude(self):
        """preferred_runtime='opencode' overrides Claude routing."""
        runtime = route_to_runtime(
            AgentRole.ATTACKER,
            TaskType.CRITICAL,
            accuracy_critical=True,
            preferred_runtime="opencode",  # Override
        )
        assert isinstance(runtime, OpenCodeRuntime)

    def test_preferred_codex_overrides_opencode(self):
        """preferred_runtime='codex' overrides OpenCode routing."""
        runtime = route_to_runtime(
            AgentRole.INTEGRATOR,
            TaskType.SUMMARIZE,
            preferred_runtime="codex",  # Override
        )
        assert isinstance(runtime, CodexCLIRuntime)

    def test_preferred_claude_code_overrides_opencode(self):
        """preferred_runtime='claude_code' overrides OpenCode routing."""
        runtime = route_to_runtime(
            AgentRole.TEST_BUILDER,
            TaskType.CODE,
            preferred_runtime="claude_code",  # Override
        )
        assert isinstance(runtime, ClaudeCodeRuntime)


# =============================================================================
# Test TaskRouter Class Methods
# =============================================================================

class TestTaskRouterClass:
    """Tests for TaskRouter class methods."""

    def test_init_defaults(self):
        """TaskRouter initializes with defaults."""
        router = TaskRouter()
        assert router.rankings_store is None
        assert router._rankings is None
        assert router._route_count["opencode"] == 0
        assert router._route_count["claude_code"] == 0
        assert router._route_count["codex"] == 0

    def test_init_with_rankings_store(self):
        """TaskRouter accepts rankings_store path."""
        store_path = Path("/tmp/rankings.yaml")
        router = TaskRouter(rankings_store=store_path)
        assert router.rankings_store == store_path

    def test_route_tracks_statistics(self):
        """route() updates statistics."""
        router = TaskRouter()

        # Route multiple tasks
        policy = RoutingPolicy(task_type=TaskType.VERIFY)
        router.route(policy)
        router.route(policy)
        router.route(policy)

        stats = router.get_route_statistics()
        assert stats["opencode"] == 3

    def test_route_claude_updates_statistics(self):
        """Routing to Claude updates claude_code statistics."""
        router = TaskRouter()

        policy = RoutingPolicy(
            task_type=TaskType.CRITICAL,
            role=AgentRole.ATTACKER,
            accuracy_critical=True,
        )
        router.route(policy)

        stats = router.get_route_statistics()
        assert stats["claude_code"] == 1

    def test_route_codex_updates_statistics(self):
        """Routing to Codex updates codex statistics."""
        router = TaskRouter()

        policy = RoutingPolicy(task_type=TaskType.REVIEW)
        router.route(policy)

        stats = router.get_route_statistics()
        assert stats["codex"] == 1

    def test_get_route_statistics_returns_copy(self):
        """get_route_statistics returns a copy."""
        router = TaskRouter()
        stats = router.get_route_statistics()
        stats["opencode"] = 999  # Modify

        # Original should be unchanged
        assert router._route_count["opencode"] == 0

    def test_reset_statistics(self):
        """reset_statistics clears all counters."""
        router = TaskRouter()

        # Route some tasks
        policy = RoutingPolicy(task_type=TaskType.VERIFY)
        router.route(policy)
        router.route(policy)

        # Reset
        router.reset_statistics()

        stats = router.get_route_statistics()
        assert stats["opencode"] == 0
        assert stats["claude_code"] == 0
        assert stats["codex"] == 0

    def test_get_recommended_runtime_verify(self):
        """get_recommended_runtime returns correct name for VERIFY."""
        router = TaskRouter()
        name = router.get_recommended_runtime(TaskType.VERIFY)
        assert name == "opencode"

    def test_get_recommended_runtime_critical(self):
        """get_recommended_runtime returns correct name for CRITICAL."""
        router = TaskRouter()
        name = router.get_recommended_runtime(
            TaskType.CRITICAL,
            AgentRole.ATTACKER,
        )
        # Note: get_recommended_runtime doesn't have accuracy_critical param
        # CRITICAL task type alone should route to claude_code
        assert name == "claude_code"

    def test_get_recommended_runtime_review(self):
        """get_recommended_runtime returns correct name for REVIEW."""
        router = TaskRouter()
        name = router.get_recommended_runtime(TaskType.REVIEW)
        assert name == "codex"


# =============================================================================
# Test Rankings Loading
# =============================================================================

class TestRankingsLoading:
    """Tests for rankings YAML loading."""

    def test_load_rankings_no_file(self):
        """No rankings file returns empty dict."""
        router = TaskRouter(rankings_store=Path("/nonexistent/path.yaml"))
        rankings = router._load_rankings()
        assert rankings == {}

    def test_load_rankings_caches_result(self):
        """Rankings are cached after first load."""
        router = TaskRouter()
        router._rankings = {"cached": True}

        # Should return cached value
        rankings = router._load_rankings()
        assert rankings == {"cached": True}

    def test_load_rankings_from_file(self):
        """Rankings loaded from YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("verify:\n  - minimax\n  - deepseek\n")
            f.flush()
            rankings_path = Path(f.name)

        try:
            router = TaskRouter(rankings_store=rankings_path)
            rankings = router._load_rankings()

            assert "verify" in rankings
            assert rankings["verify"] == ["minimax", "deepseek"]
        finally:
            rankings_path.unlink()


# =============================================================================
# Test Package Imports
# =============================================================================

class TestPackageImports:
    """Tests for package-level imports."""

    def test_route_to_runtime_importable(self):
        """route_to_runtime importable from package."""
        from alphaswarm_sol.agents.runtime import route_to_runtime
        assert callable(route_to_runtime)

    def test_task_router_importable(self):
        """TaskRouter importable from package."""
        from alphaswarm_sol.agents.runtime import TaskRouter
        assert TaskRouter is not None

    def test_routing_policy_importable(self):
        """RoutingPolicy importable from package."""
        from alphaswarm_sol.agents.runtime import RoutingPolicy
        assert RoutingPolicy is not None

    def test_threshold_constants_importable(self):
        """Threshold constants importable from package."""
        from alphaswarm_sol.agents.runtime import (
            LARGE_CONTEXT_THRESHOLD,
            HEAVY_CONTEXT_THRESHOLD,
        )
        assert LARGE_CONTEXT_THRESHOLD == 200_000
        assert HEAVY_CONTEXT_THRESHOLD == 500_000


# =============================================================================
# Test Default Routing Behavior
# =============================================================================

class TestDefaultRouting:
    """Tests for default routing behavior."""

    def test_unknown_role_no_crash(self):
        """Unknown scenarios don't crash."""
        # All roles should work with default task type
        for role in AgentRole:
            runtime = route_to_runtime(role)
            assert runtime is not None

    def test_default_task_type_is_analyze(self):
        """Default task_type parameter is ANALYZE."""
        runtime = route_to_runtime(AgentRole.SUPERVISOR)
        assert isinstance(runtime, OpenCodeRuntime)

    def test_latency_sensitive_no_effect_currently(self):
        """latency_sensitive doesn't change routing (future feature)."""
        runtime1 = route_to_runtime(
            AgentRole.DEFENDER,
            TaskType.VERIFY,
            latency_sensitive=False,
        )
        runtime2 = route_to_runtime(
            AgentRole.DEFENDER,
            TaskType.VERIFY,
            latency_sensitive=True,
        )
        # Both should be same type (latency not implemented)
        assert type(runtime1) == type(runtime2)


# =============================================================================
# Test Integration
# =============================================================================

class TestIntegration:
    """Integration tests for router with actual runtime creation."""

    def test_opencode_runtime_model_for_reasoning(self):
        """REASONING task gets DeepSeek model."""
        runtime = route_to_runtime(
            AgentRole.DEFENDER,
            TaskType.REASONING,
        )
        assert isinstance(runtime, OpenCodeRuntime)
        assert "deepseek" in runtime.config.default_model.lower()

    def test_opencode_runtime_model_for_code(self):
        """CODE task gets GLM-4.7 model."""
        runtime = route_to_runtime(
            AgentRole.TEST_BUILDER,
            TaskType.CODE,
        )
        assert isinstance(runtime, OpenCodeRuntime)
        assert "glm" in runtime.config.default_model.lower()

    def test_multiple_routes_same_router(self):
        """Single router can route multiple tasks."""
        router = TaskRouter()

        # Route different task types
        p1 = RoutingPolicy(task_type=TaskType.VERIFY)
        p2 = RoutingPolicy(task_type=TaskType.CRITICAL)
        p3 = RoutingPolicy(task_type=TaskType.REVIEW)

        r1 = router.route(p1)
        r2 = router.route(p2)
        r3 = router.route(p3)

        assert isinstance(r1, OpenCodeRuntime)
        assert isinstance(r2, ClaudeCodeRuntime)
        assert isinstance(r3, CodexCLIRuntime)

        # Check statistics
        stats = router.get_route_statistics()
        assert stats["opencode"] == 1
        assert stats["claude_code"] == 1
        assert stats["codex"] == 1
