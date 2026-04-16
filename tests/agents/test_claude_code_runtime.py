"""Tests for Claude Code CLI Runtime.

Comprehensive tests for ClaudeCodeRuntime covering:
- Configuration defaults and customization
- Role-to-model mapping (critical roles get opus)
- Command building (--print, --output-format, --model, --resume)
- Prompt building from config and messages
- Response parsing with subscription pricing
- Session management
- Error handling (auth, subscription limits, session not found)
- Usage tracking
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse, AgentRole
from alphaswarm_sol.agents.runtime.claude_code import (
    ClaudeCodeConfig,
    ClaudeCodeRuntime,
    CRITICAL_ROLES,
    DEFAULT_SESSION_DIR,
)


# =============================================================================
# Test ClaudeCodeConfig
# =============================================================================

class TestClaudeCodeConfig:
    """Tests for ClaudeCodeConfig dataclass."""

    def test_default_model_is_sonnet(self):
        """Default model is claude-sonnet-4."""
        config = ClaudeCodeConfig()
        assert config.model == "claude-sonnet-4-20250514"

    def test_opus_model_default(self):
        """Opus model is claude-opus-4."""
        config = ClaudeCodeConfig()
        assert config.opus_model == "claude-opus-4-20250514"

    def test_timeout_default_is_300(self):
        """Default timeout is 300 seconds (5 minutes)."""
        config = ClaudeCodeConfig()
        assert config.timeout_seconds == 300

    def test_max_tokens_default(self):
        """Default max_tokens is 8192."""
        config = ClaudeCodeConfig()
        assert config.max_tokens == 8192

    def test_session_dir_defaults_to_home(self):
        """Session dir defaults to ~/.claude-code-sessions."""
        config = ClaudeCodeConfig()
        assert config.session_dir == DEFAULT_SESSION_DIR

    def test_print_mode_default_true(self):
        """Print mode is enabled by default."""
        config = ClaudeCodeConfig()
        assert config.print_mode is True

    def test_max_retries_default(self):
        """Default max_retries is 2."""
        config = ClaudeCodeConfig()
        assert config.max_retries == 2

    def test_custom_model_values(self):
        """Config accepts custom model values."""
        config = ClaudeCodeConfig(
            model="custom-sonnet",
            opus_model="custom-opus",
            timeout_seconds=600,
        )
        assert config.model == "custom-sonnet"
        assert config.opus_model == "custom-opus"
        assert config.timeout_seconds == 600

    def test_custom_session_dir(self):
        """Config accepts custom session directory."""
        custom_dir = Path("/tmp/custom-sessions")
        config = ClaudeCodeConfig(session_dir=custom_dir)
        assert config.session_dir == custom_dir


# =============================================================================
# Test Role-to-Model Mapping
# =============================================================================

class TestRoleToModelMapping:
    """Tests for role-to-model mapping."""

    def test_attacker_gets_opus(self):
        """ATTACKER role maps to opus model."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        model = runtime.get_model_for_role(AgentRole.ATTACKER)
        assert model == "claude-opus-4-20250514"

    def test_verifier_gets_opus(self):
        """VERIFIER role maps to opus model."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        model = runtime.get_model_for_role(AgentRole.VERIFIER)
        assert model == "claude-opus-4-20250514"

    def test_defender_gets_sonnet(self):
        """DEFENDER role maps to sonnet model."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        model = runtime.get_model_for_role(AgentRole.DEFENDER)
        assert model == "claude-sonnet-4-20250514"

    def test_test_builder_gets_sonnet(self):
        """TEST_BUILDER role maps to sonnet model."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        model = runtime.get_model_for_role(AgentRole.TEST_BUILDER)
        assert model == "claude-sonnet-4-20250514"

    def test_supervisor_gets_sonnet(self):
        """SUPERVISOR role maps to sonnet model."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        model = runtime.get_model_for_role(AgentRole.SUPERVISOR)
        assert model == "claude-sonnet-4-20250514"

    def test_integrator_gets_sonnet(self):
        """INTEGRATOR role maps to sonnet model."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        model = runtime.get_model_for_role(AgentRole.INTEGRATOR)
        assert model == "claude-sonnet-4-20250514"

    def test_critical_roles_set_correct(self):
        """CRITICAL_ROLES contains ATTACKER and VERIFIER."""
        assert AgentRole.ATTACKER in CRITICAL_ROLES
        assert AgentRole.VERIFIER in CRITICAL_ROLES
        assert AgentRole.DEFENDER not in CRITICAL_ROLES
        assert AgentRole.TEST_BUILDER not in CRITICAL_ROLES

    def test_custom_model_used_for_role(self):
        """Custom model configuration used for role mapping."""
        config = ClaudeCodeConfig(
            model="custom-sonnet",
            opus_model="custom-opus",
        )
        runtime = ClaudeCodeRuntime(config)

        assert runtime.get_model_for_role(AgentRole.ATTACKER) == "custom-opus"
        assert runtime.get_model_for_role(AgentRole.DEFENDER) == "custom-sonnet"


# =============================================================================
# Test Command Building
# =============================================================================

class TestCommandBuilding:
    """Tests for CLI command building."""

    def test_basic_command_structure(self):
        """Basic command has correct structure."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test prompt",
            model="claude-sonnet-4",
        )

        assert cmd[0] == "claude"
        assert "--print" in cmd
        assert "-p" in cmd
        assert "Test prompt" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd
        assert "--model" in cmd
        assert "claude-sonnet-4" in cmd

    def test_print_flag_present(self):
        """--print flag present for non-interactive mode."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-sonnet-4",
        )

        assert "--print" in cmd

    def test_print_flag_can_be_disabled(self):
        """--print flag absent when print_mode=False."""
        config = ClaudeCodeConfig(print_mode=False)
        runtime = ClaudeCodeRuntime(config)
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-sonnet-4",
        )

        assert "--print" not in cmd

    def test_output_format_json(self):
        """--output-format json always present."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-sonnet-4",
        )

        assert "--output-format" in cmd
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "json"

    def test_model_flag_set(self):
        """--model flag set to correct model."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-opus-4",
        )

        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-opus-4"

    def test_resume_flag_with_session(self):
        """--resume flag present with session ID."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-sonnet-4",
            session_id="my-session-123",
        )

        assert "--resume" in cmd
        idx = cmd.index("--resume")
        assert cmd[idx + 1] == "my-session-123"

    def test_no_resume_without_session(self):
        """--resume flag absent without session ID."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        cmd = runtime._build_command(
            prompt="Test",
            model="claude-sonnet-4",
            session_id=None,
        )

        assert "--resume" not in cmd

    def test_prompt_preserved(self):
        """Prompt string preserved in command."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        prompt = 'Test with "quotes" and $special chars'
        cmd = runtime._build_command(
            prompt=prompt,
            model="claude-sonnet-4",
        )

        assert prompt in cmd


# =============================================================================
# Test Session Management
# =============================================================================

class TestSessionManagement:
    """Tests for session management."""

    def test_session_file_path_generated(self):
        """Session file path generated from session ID."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        path = runtime._get_session_file("my-session-123")

        assert path.name.startswith("session_")
        assert path.suffix == ".json"
        assert path.parent == DEFAULT_SESSION_DIR

    def test_session_id_hashed(self):
        """Session ID is hashed for filesystem safety."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        path = runtime._get_session_file("test/session:with:special/chars!")

        # Should be a safe hex string
        session_part = path.stem.replace("session_", "")
        assert session_part.isalnum()

    def test_different_session_ids_different_paths(self):
        """Different session IDs produce different paths."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        path1 = runtime._get_session_file("session-a")
        path2 = runtime._get_session_file("session-b")

        assert path1 != path2

    def test_same_session_id_same_path(self):
        """Same session ID produces same path."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        path1 = runtime._get_session_file("session-x")
        path2 = runtime._get_session_file("session-x")

        assert path1 == path2


# =============================================================================
# Test Response Parsing
# =============================================================================

class TestResponseParsing:
    """Tests for response parsing."""

    def test_basic_response_parsed(self):
        """Basic JSON response parsed correctly."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        result = {
            "content": "Analysis complete",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }

        response = runtime._parse_response(result, "claude-sonnet-4", 1000)

        assert response.content == "Analysis complete"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.model == "claude-sonnet-4"
        assert response.latency_ms == 1000

    def test_cost_is_zero_subscription(self):
        """cost_usd is 0.0 for subscription pricing."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        result = {
            "content": "Test",
            "usage": {"input_tokens": 10000, "output_tokens": 5000},
        }

        response = runtime._parse_response(result, "claude-opus-4", 500)

        assert response.cost_usd == 0.0

    def test_alternative_usage_keys(self):
        """Alternative usage keys (prompt_tokens, completion_tokens) work."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        result = {
            "content": "Test",
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
            },
        }

        response = runtime._parse_response(result, "claude-sonnet-4", 500)

        assert response.input_tokens == 200
        assert response.output_tokens == 100

    def test_tool_calls_extracted(self):
        """Tool calls extracted from response."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        result = {
            "content": "Using tool...",
            "tool_calls": [{"name": "Read", "arguments": {"path": "/test"}}],
            "usage": {},
        }

        response = runtime._parse_response(result, "claude-sonnet-4", 100)

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "Read"

    def test_tool_use_key_also_works(self):
        """tool_use key (alternative to tool_calls) also works."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        result = {
            "content": "Using tool...",
            "tool_use": [{"name": "Write", "arguments": {}}],
            "usage": {},
        }

        response = runtime._parse_response(result, "claude-sonnet-4", 100)

        assert len(response.tool_calls) == 1

    def test_empty_response_handled(self):
        """Empty response handled gracefully."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        result = {}

        response = runtime._parse_response(result, "claude-sonnet-4", 50)

        assert response.content == ""
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.cost_usd == 0.0

    def test_cache_tokens_extracted(self):
        """Cache tokens extracted from usage."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        result = {
            "content": "Test",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_tokens": 80,
                "cache_write_tokens": 20,
            },
        }

        response = runtime._parse_response(result, "claude-sonnet-4", 100)

        assert response.cache_read_tokens == 80
        assert response.cache_write_tokens == 20


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """Timeout raises TimeoutError."""
        config = ClaudeCodeConfig(timeout_seconds=1, max_retries=0)
        runtime = ClaudeCodeRuntime(config)

        with patch.object(runtime, "_run_subprocess") as mock_run:
            mock_run.side_effect = TimeoutError("Timed out")

            config_agent = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(TimeoutError):
                await runtime.execute(config_agent, messages)

    @pytest.mark.asyncio
    async def test_auth_error_fails_fast(self):
        """Authentication error fails immediately without retries."""
        config = ClaudeCodeConfig(max_retries=3)
        runtime = ClaudeCodeRuntime(config)

        with patch.object(runtime, "_run_subprocess") as mock_run:
            mock_run.side_effect = RuntimeError("Authentication error: Not logged in")

            config_agent = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RuntimeError, match="Authentication error"):
                await runtime.execute(config_agent, messages)

            # Should only be called once (no retries for auth)
            assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_subscription_limit_error_fails_fast(self):
        """Subscription limit error fails immediately."""
        config = ClaudeCodeConfig(max_retries=3)
        runtime = ClaudeCodeRuntime(config)

        with patch.object(runtime, "_run_subprocess") as mock_run:
            mock_run.side_effect = RuntimeError("Subscription limit error: rate limit")

            config_agent = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(RuntimeError, match="Subscription limit"):
                await runtime.execute(config_agent, messages)

            assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_session_not_found_recovers(self):
        """Session not found triggers retry without session."""
        config = ClaudeCodeConfig(max_retries=1)
        runtime = ClaudeCodeRuntime(config)

        call_count = 0

        async def mock_run(cmd, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and "--resume" in cmd:
                return {"content": "", "session_not_found": True}
            return {"content": "Success", "usage": {"input_tokens": 10, "output_tokens": 5}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config_agent = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            response = await runtime.execute(config_agent, messages, session_id="old-session")

            assert response.content == "Success"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Retries on transient errors then succeeds."""
        config = ClaudeCodeConfig(max_retries=2)
        runtime = ClaudeCodeRuntime(config)

        call_count = 0

        async def mock_run(cmd, timeout):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary error")
            return {"content": "Success", "usage": {"input_tokens": 10, "output_tokens": 5}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config_agent = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Test"}]

            response = await runtime.execute(config_agent, messages)

            assert response.content == "Success"
            assert call_count == 2


# =============================================================================
# Test Prompt Building
# =============================================================================

class TestPromptBuilding:
    """Tests for prompt building from config and messages."""

    def test_system_prompt_wrapped(self):
        """System prompt wrapped in <system> tags."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        config = AgentConfig(
            role=AgentRole.VERIFIER,
            system_prompt="You are a security expert.",
        )
        messages = []

        prompt = runtime._build_prompt(config, messages)

        assert "<system>" in prompt
        assert "You are a security expert." in prompt
        assert "</system>" in prompt

    def test_user_message_wrapped(self):
        """User message wrapped in <user> tags."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="")
        messages = [{"role": "user", "content": "Analyze this"}]

        prompt = runtime._build_prompt(config, messages)

        assert "<user>" in prompt
        assert "Analyze this" in prompt
        assert "</user>" in prompt

    def test_assistant_message_wrapped(self):
        """Assistant message wrapped in <assistant> tags."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="")
        messages = [{"role": "assistant", "content": "Response here"}]

        prompt = runtime._build_prompt(config, messages)

        assert "<assistant>" in prompt
        assert "Response here" in prompt
        assert "</assistant>" in prompt

    def test_message_order_preserved(self):
        """Message order preserved in prompt."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="System")
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
        ]

        prompt = runtime._build_prompt(config, messages)

        assert prompt.index("System") < prompt.index("First")
        assert prompt.index("First") < prompt.index("Second")
        assert prompt.index("Second") < prompt.index("Third")


# =============================================================================
# Test Usage Tracking
# =============================================================================

class TestUsageTracking:
    """Tests for usage tracking."""

    def test_get_usage_empty_initially(self):
        """Initial usage is empty."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())
        usage = runtime.get_usage()

        assert usage["total_tokens"] == 0
        assert usage["total_cost"] == 0.0
        assert usage["request_count"] == 0
        assert usage["by_model"] == {}

    def test_usage_cost_always_zero(self):
        """Usage cost is always 0.0 (subscription)."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())

        # Simulate tracking
        response = AgentResponse(
            content="Test",
            tool_calls=[],
            input_tokens=10000,
            output_tokens=5000,
            model="claude-opus-4",
            cost_usd=0.0,  # Subscription
        )
        runtime._usage_tracker.track(response)

        usage = runtime.get_usage()

        assert usage["total_cost"] == 0.0
        assert usage["by_model"]["claude-opus-4"]["cost"] == 0.0

    @pytest.mark.asyncio
    async def test_usage_aggregates_across_calls(self):
        """Usage aggregates across multiple execute calls."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())

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

    def test_reset_usage(self):
        """reset_usage clears all tracking."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())

        # Track some usage
        response = AgentResponse(
            content="Test",
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            model="claude-sonnet-4",
            cost_usd=0.0,
        )
        runtime._usage_tracker.track(response)

        assert runtime.get_usage()["request_count"] == 1

        runtime.reset_usage()

        assert runtime.get_usage()["request_count"] == 0


# =============================================================================
# Test spawn_agent
# =============================================================================

class TestSpawnAgent:
    """Tests for spawn_agent method."""

    @pytest.mark.asyncio
    async def test_spawn_agent_no_session(self):
        """spawn_agent creates context-fresh agent (no session)."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())

        async def mock_run(cmd, timeout):
            # Verify no --resume in command
            assert "--resume" not in cmd
            return {"content": "Fresh response", "usage": {"input_tokens": 10, "output_tokens": 5}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")

            response = await runtime.spawn_agent(config, "Verify this code")

            assert response.content == "Fresh response"

    @pytest.mark.asyncio
    async def test_spawn_agent_attacker_uses_opus(self):
        """ATTACKER role uses opus model in spawn_agent."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())

        async def mock_run(cmd, timeout):
            # Verify opus model used
            model_idx = cmd.index("--model")
            assert "opus" in cmd[model_idx + 1]
            return {"content": "Exploit found", "usage": {}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config = AgentConfig(role=AgentRole.ATTACKER, system_prompt="Find exploits")

            response = await runtime.spawn_agent(config, "Attack this contract")

            assert response.model == "claude-opus-4-20250514"


# =============================================================================
# Test execute_with_session
# =============================================================================

class TestExecuteWithSession:
    """Tests for execute_with_session method."""

    @pytest.mark.asyncio
    async def test_execute_with_session_includes_resume(self):
        """execute_with_session includes --resume flag."""
        runtime = ClaudeCodeRuntime(ClaudeCodeConfig())

        async def mock_run(cmd, timeout):
            assert "--resume" in cmd
            resume_idx = cmd.index("--resume")
            assert cmd[resume_idx + 1] == "session-abc"
            return {"content": "Continued", "usage": {}}

        with patch.object(runtime, "_run_subprocess", side_effect=mock_run):
            config = AgentConfig(role=AgentRole.VERIFIER, system_prompt="Test")
            messages = [{"role": "user", "content": "Continue"}]

            response = await runtime.execute_with_session(config, messages, "session-abc")

            assert response.content == "Continued"
