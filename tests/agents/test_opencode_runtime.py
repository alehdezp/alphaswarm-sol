"""Tests for OpenCode SDK Runtime.

Comprehensive tests for OpenCodeRuntime covering:
- Configuration and defaults
- Model selection (task-type and role-based)
- Command building
- Prompt building
- Cost calculation
- Response parsing
- Error handling
- Loop prevention
- Usage tracking
"""

from __future__ import annotations

import asyncio
import json
import hashlib
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse, AgentRole
from alphaswarm_sol.agents.runtime.opencode import (
    OpenCodeConfig,
    OpenCodeRuntime,
    LoopState,
    MAX_ITERATIONS,
    MAX_REPEATED_OUTPUTS,
    TOKEN_CEILING,
)
from alphaswarm_sol.agents.runtime.types import (
    TaskType,
    MODEL_PRICING,
    calculate_model_cost,
    get_context_limit,
    is_free_model,
)


# =============================================================================
# Test OpenCodeConfig
# =============================================================================

class TestOpenCodeConfig:
    """Tests for OpenCodeConfig dataclass."""

    def test_default_values(self):
        """All model fields have default values."""
        config = OpenCodeConfig()

        assert config.default_model == "google/gemini-3-flash-preview"
        assert config.verify_model == "minimax/minimax-m2:free"
        assert config.summarize_model == "minimax/minimax-m2:free"
        assert config.context_model == "x-ai/grok-code-fast-1"
        assert config.code_model == "zhipu/glm-4.7"
        assert config.reasoning_model == "deepseek/deepseek-v3.2"
        assert config.reasoning_heavy_model == "google/gemini-3-pro-preview"
        assert config.heavy_model == "google/gemini-3-flash-preview"
        assert config.fallback_model == "qwen/qwen-2.5-72b-instruct:free"
        assert config.timeout_seconds == 120
        assert config.max_retries == 3

    def test_custom_values(self):
        """Config accepts custom model values."""
        config = OpenCodeConfig(
            default_model="custom/model",
            timeout_seconds=60,
            max_retries=5,
        )

        assert config.default_model == "custom/model"
        assert config.timeout_seconds == 60
        assert config.max_retries == 5

    def test_get_model_for_task_type(self):
        """get_model_for_task_type returns correct models."""
        config = OpenCodeConfig()

        assert config.get_model_for_task_type(TaskType.VERIFY) == "minimax/minimax-m2:free"
        assert config.get_model_for_task_type(TaskType.REASONING) == "deepseek/deepseek-v3.2"
        assert config.get_model_for_task_type(TaskType.CODE) == "zhipu/glm-4.7"
        assert config.get_model_for_task_type(TaskType.HEAVY) == "google/gemini-3-flash-preview"


# =============================================================================
# Test Model Selection
# =============================================================================

class TestModelSelection:
    """Tests for model selection logic."""

    def test_select_model_verify_returns_free_model(self):
        """Verify task type returns free model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.VERIFY, None)
        assert model == "minimax/minimax-m2:free"

    def test_select_model_reasoning_returns_deepseek(self):
        """Reasoning task type returns DeepSeek."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model(TaskType.REASONING, None)
        assert model == "deepseek/deepseek-v3.2"

    def test_select_model_string_task_type(self):
        """Model selection works with string task type."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model("verify", None)
        assert model == "minimax/minimax-m2:free"

    def test_select_model_unknown_task_type_falls_back(self):
        """Unknown task type falls back to default model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime._select_model("unknown_type", None)
        assert model == "google/gemini-3-flash-preview"

    def test_rankings_override_defaults(self):
        """Rankings override default model selection."""
        rankings = {
            "verify": [{"model": "custom/ranked-model", "score": 0.95}],
        }
        runtime = OpenCodeRuntime(OpenCodeConfig(), rankings_store=rankings)
        model = runtime._select_model(TaskType.VERIFY, None)
        assert model == "custom/ranked-model"

    def test_rankings_list_format(self):
        """Rankings in simple list format work."""
        rankings = {
            "verify": ["simple/model", "backup/model"],
        }
        runtime = OpenCodeRuntime(OpenCodeConfig(), rankings_store=rankings)
        model = runtime._select_model(TaskType.VERIFY, None)
        assert model == "simple/model"

    def test_get_model_for_role_attacker(self):
        """ATTACKER role maps to reasoning model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime.get_model_for_role(AgentRole.ATTACKER)
        assert model == "deepseek/deepseek-v3.2"

    def test_get_model_for_role_verifier(self):
        """VERIFIER role maps to verify model (free)."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime.get_model_for_role(AgentRole.VERIFIER)
        assert model == "minimax/minimax-m2:free"

    def test_get_model_for_role_test_builder(self):
        """TEST_BUILDER role maps to code model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        model = runtime.get_model_for_role(AgentRole.TEST_BUILDER)
        assert model == "zhipu/glm-4.7"


# =============================================================================
# Test Command Building
# =============================================================================

class TestCommandBuilding:
    """Tests for subprocess command building."""

    def test_build_command_basic(self):
        """Basic command has correct structure."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        cmd = runtime._build_command("test/model", "Hello world")

        assert cmd[0] == "opencode"
        assert "-p" in cmd
        assert cmd[cmd.index("-p") + 1] == "Hello world"
        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1] == "test/model"
        assert "-f" in cmd
        assert "json" in cmd
        assert "-q" in cmd

    def test_build_command_special_characters(self):
        """Command handles special characters in prompt."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        prompt = 'Test with "quotes" and $variables and `backticks`'
        cmd = runtime._build_command("test/model", prompt)

        assert prompt in cmd

    def test_build_command_multiline_prompt(self):
        """Command handles multiline prompts."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        prompt = "Line 1\nLine 2\nLine 3"
        cmd = runtime._build_command("test/model", prompt)

        assert prompt in cmd


# =============================================================================
# Test Prompt Building
# =============================================================================

class TestPromptBuilding:
    """Tests for prompt building from config and messages."""

    def test_system_prompt_comes_first(self):
        """System prompt appears first in built prompt."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        config = AgentConfig(
            role=AgentRole.VERIFIER,
            system_prompt="You are a security expert.",
        )
        messages = [{"role": "user", "content": "Analyze this code."}]

        prompt = runtime._build_prompt(config, messages)

        assert prompt.index("<system>") < prompt.index("<user>")
        assert "You are a security expert." in prompt

    def test_user_messages_formatted(self):
        """User messages are correctly formatted."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="")
        messages = [{"role": "user", "content": "Test message"}]

        prompt = runtime._build_prompt(config, messages)

        assert "<user>" in prompt
        assert "Test message" in prompt
        assert "</user>" in prompt

    def test_multiple_messages_concatenated(self):
        """Multiple messages are concatenated."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="")
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Second message"},
        ]

        prompt = runtime._build_prompt(config, messages)

        assert "First message" in prompt
        assert "Response" in prompt
        assert "Second message" in prompt
        assert prompt.index("First message") < prompt.index("Response")
        assert prompt.index("Response") < prompt.index("Second message")


# =============================================================================
# Test Cost Calculation
# =============================================================================

class TestCostCalculation:
    """Tests for cost calculation."""

    def test_free_models_return_zero(self):
        """Free models return 0.0 cost."""
        cost = calculate_model_cost("minimax/minimax-m2:free", 1000, 1000)
        assert cost == 0.0

    def test_paid_models_calculate_correctly(self):
        """Paid models calculate cost correctly."""
        # DeepSeek: $0.25/M in, $0.38/M out
        cost = calculate_model_cost("deepseek/deepseek-v3.2", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.25 + 0.38, rel=0.01)

    def test_unknown_models_use_default_pricing(self):
        """Unknown models use default pricing."""
        cost = calculate_model_cost("unknown/model", 1_000_000, 1_000_000)
        # Default: $2.0/M in, $10.0/M out
        assert cost == pytest.approx(2.0 + 10.0, rel=0.01)

    def test_grok_free_input_minimal_output(self):
        """Grok has free input but minimal output cost."""
        cost = calculate_model_cost("x-ai/grok-code-fast-1", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.002, rel=0.01)


# =============================================================================
# Test Response Parsing
# =============================================================================

class TestResponseParsing:
    """Tests for response parsing."""

    def test_json_response_parsed(self):
        """JSON response is parsed to AgentResponse."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        result = {
            "content": "Analysis complete",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        response = runtime._parse_response(result, "test/model", 1000)

        assert response.content == "Analysis complete"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.model == "test/model"
        assert response.latency_ms == 1000

    def test_token_counts_extracted(self):
        """Token counts extracted from response."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        result = {
            "content": "Test",
            "usage": {
                "prompt_tokens": 200,  # Alternative key
                "completion_tokens": 100,  # Alternative key
            },
        }

        response = runtime._parse_response(result, "test/model", 500)

        assert response.input_tokens == 200
        assert response.output_tokens == 100

    def test_tool_calls_extracted(self):
        """Tool calls extracted if present."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        result = {
            "content": "Using tool...",
            "tool_calls": [{"name": "search", "arguments": {"query": "test"}}],
            "usage": {},
        }

        response = runtime._parse_response(result, "test/model", 100)

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "search"

    def test_empty_response_handled(self):
        """Empty response handled gracefully."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        result = {}

        response = runtime._parse_response(result, "test/model", 50)

        assert response.content == ""
        assert response.input_tokens == 0
        assert response.output_tokens == 0


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """Timeout returns appropriate error."""
        runtime = OpenCodeRuntime(OpenCodeConfig(timeout_seconds=1, max_retries=0))

        with patch.object(runtime, "_run_subprocess") as mock_run:
            mock_run.side_effect = TimeoutError("Timed out")

            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(TimeoutError):
                await runtime.execute(config, messages)

    @pytest.mark.asyncio
    async def test_auth_error_fails_fast(self):
        """Authentication error fails immediately without retries."""
        runtime = OpenCodeRuntime(OpenCodeConfig(max_retries=3))

        with patch.object(runtime, "_run_subprocess") as mock_run:
            mock_run.side_effect = RuntimeError("Authentication error: Invalid API key")

            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RuntimeError, match="Authentication error"):
                await runtime.execute(config, messages)

            # Should only be called once (no retries for auth)
            assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Retries on transient errors then succeeds."""
        runtime = OpenCodeRuntime(OpenCodeConfig(max_retries=2))

        call_count = 0

        async def mock_run(cmd, timeout):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary error")
            return {"content": "Success", "usage": {"input_tokens": 10, "output_tokens": 5}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            response = await runtime.execute(config, messages)

            assert response.content == "Success"
            assert call_count == 2


# =============================================================================
# Test Loop Prevention
# =============================================================================

class TestLoopPrevention:
    """Tests for loop prevention mechanisms."""

    def test_iteration_count_limit(self):
        """Iteration count limit triggers abort."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState(iteration_count=MAX_ITERATIONS)

        # At limit - should trigger
        result = runtime._check_loop_prevention(state, "test output")
        assert result is True

    def test_iteration_count_below_limit(self):
        """Below iteration limit allows continuation."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState(iteration_count=MAX_ITERATIONS - 1)

        result = runtime._check_loop_prevention(state, "test output")
        assert result is False

    def test_output_hash_deduplication_triggers(self):
        """Repeated outputs trigger after threshold."""
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

    def test_different_outputs_dont_trigger(self):
        """Different outputs don't trigger deduplication."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState()

        for i in range(MAX_REPEATED_OUTPUTS + 5):
            result = runtime._check_loop_prevention(state, f"output {i}")
            assert result is False

    def test_token_ceiling_triggers(self):
        """Token ceiling triggers abort."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState(total_tokens_used=TOKEN_CEILING)

        result = runtime._check_loop_prevention(state, "test")
        assert result is True

    def test_token_ceiling_below_allows(self):
        """Below token ceiling allows continuation."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        state = LoopState(total_tokens_used=TOKEN_CEILING - 1)

        result = runtime._check_loop_prevention(state, "test")
        assert result is False


# =============================================================================
# Test Usage Tracking
# =============================================================================

class TestUsageTracking:
    """Tests for usage tracking."""

    def test_get_usage_empty_initially(self):
        """Initial usage is empty."""
        runtime = OpenCodeRuntime(OpenCodeConfig())
        usage = runtime.get_usage()

        assert usage["total_tokens"] == 0
        assert usage["total_cost"] == 0.0
        assert usage["request_count"] == 0
        assert usage["by_model"] == {}

    @pytest.mark.asyncio
    async def test_get_usage_aggregates(self):
        """Usage aggregates across multiple calls."""
        runtime = OpenCodeRuntime(OpenCodeConfig())

        async def mock_run(cmd, timeout):
            return {"content": "Test", "usage": {"input_tokens": 100, "output_tokens": 50}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            await runtime.execute(config, messages)
            await runtime.execute(config, messages)

            usage = runtime.get_usage()

            assert usage["total_tokens"] == 300  # 2 * (100 + 50)
            assert usage["request_count"] == 2

    def test_by_model_breakdown_accurate(self):
        """By-model breakdown is accurate."""
        runtime = OpenCodeRuntime(OpenCodeConfig())

        # Simulate tracking
        response = AgentResponse(
            content="Test",
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            model="test/model",
            cost_usd=0.01,
        )
        runtime._usage_tracker.track(response)
        runtime._usage_tracker.track(response)

        usage = runtime.get_usage()

        assert "test/model" in usage["by_model"]
        assert usage["by_model"]["test/model"]["tokens"] == 300
        assert usage["by_model"]["test/model"]["requests"] == 2


# =============================================================================
# Test Types Module
# =============================================================================

class TestTypesModule:
    """Tests for types.py module."""

    def test_task_type_enum_values(self):
        """TaskType has all expected values."""
        assert TaskType.VERIFY.value == "verify"
        assert TaskType.SUMMARIZE.value == "summarize"
        assert TaskType.CONTEXT.value == "context"
        assert TaskType.CODE.value == "code"
        assert TaskType.REASONING.value == "reasoning"
        assert TaskType.REASONING_HEAVY.value == "reasoning_heavy"
        assert TaskType.HEAVY.value == "heavy"
        assert TaskType.ANALYZE.value == "analyze"
        assert TaskType.REVIEW.value == "review"
        assert TaskType.CRITICAL.value == "critical"

    def test_model_pricing_has_expected_models(self):
        """MODEL_PRICING has expected models."""
        assert "x-ai/grok-code-fast-1" in MODEL_PRICING
        assert "deepseek/deepseek-v3.2" in MODEL_PRICING
        assert "google/gemini-3-flash-preview" in MODEL_PRICING
        assert "google/gemini-3-pro-preview" in MODEL_PRICING

    def test_get_context_limit(self):
        """get_context_limit returns correct limits."""
        assert get_context_limit("google/gemini-3-flash-preview") == 1_000_000
        assert get_context_limit("deepseek/deepseek-v3.2") == 164_000
        assert get_context_limit("unknown/model") == 100_000  # Default

    def test_is_free_model(self):
        """is_free_model correctly identifies free models."""
        assert is_free_model("minimax/minimax-m2:free") is True
        assert is_free_model("bigpickle/bigpickle:free") is True
        assert is_free_model("deepseek/deepseek-v3.2") is False
        assert is_free_model("google/gemini-3-flash-preview") is False


# =============================================================================
# Test Rankings Persistence
# =============================================================================

class TestRankingsPersistence:
    """Tests for rankings persistence."""

    def test_rankings_loaded_from_store(self):
        """Rankings loaded from provided store."""
        rankings = {"verify": [{"model": "test/model"}]}
        runtime = OpenCodeRuntime(OpenCodeConfig(), rankings_store=rankings)

        assert runtime.get_rankings() == rankings

    def test_rankings_not_mutated(self):
        """get_rankings returns copy, not original."""
        rankings = {"verify": [{"model": "test/model"}]}
        runtime = OpenCodeRuntime(OpenCodeConfig(), rankings_store=rankings)

        result = runtime.get_rankings()
        result["new_key"] = "value"

        assert "new_key" not in runtime.get_rankings()

    def test_save_rankings_creates_directory(self, tmp_path):
        """save_rankings creates parent directories."""
        rankings_path = tmp_path / "rankings" / "rankings.yaml"
        config = OpenCodeConfig(rankings_path=rankings_path)
        runtime = OpenCodeRuntime(config)

        runtime._rankings = {"verify": [{"model": "test"}]}
        runtime._save_rankings()

        assert rankings_path.exists()

    def test_load_rankings_from_file(self, tmp_path):
        """Rankings loaded from YAML file."""
        rankings_path = tmp_path / "rankings.yaml"
        rankings_path.write_text("verify:\n  - model: test/model\n")

        config = OpenCodeConfig(rankings_path=rankings_path)
        runtime = OpenCodeRuntime(config)

        assert "verify" in runtime.get_rankings()


# =============================================================================
# Test spawn_agent
# =============================================================================

class TestSpawnAgent:
    """Tests for spawn_agent method."""

    @pytest.mark.asyncio
    async def test_spawn_agent_uses_correct_task_type(self):
        """spawn_agent maps role to task type."""
        runtime = OpenCodeRuntime(OpenCodeConfig())

        async def mock_run(cmd, timeout):
            return {"content": "Test", "usage": {"input_tokens": 10, "output_tokens": 5}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")

            response = await runtime.spawn_agent(config, "Verify this code")

            assert response.content == "Test"
            # Should use verify model (free)
            assert response.model == "minimax/minimax-m2:free"

    @pytest.mark.asyncio
    async def test_spawn_agent_attacker_uses_reasoning(self):
        """ATTACKER role uses reasoning model."""
        runtime = OpenCodeRuntime(OpenCodeConfig())

        async def mock_run(cmd, timeout):
            return {"content": "Exploit found", "usage": {"input_tokens": 10, "output_tokens": 5}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Find exploits")

            response = await runtime.spawn_agent(config, "Attack this contract")

            assert response.model == "deepseek/deepseek-v3.2"
