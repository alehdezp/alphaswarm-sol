"""Tests for Agent Runtime Abstraction.

Tests the multi-SDK agent runtime layer including:
- AgentConfig creation and validation
- AgentRole enumeration
- ROLE_MODEL_MAP access
- RuntimeConfig validation
- Tool conversion between SDK formats
- Mock tests for both runtimes (no API calls)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from alphaswarm_sol.agents.runtime import (
    AgentRole,
    AgentConfig,
    AgentResponse,
    AgentRuntime,
    UsageTracker,
    ROLE_MODEL_MAP,
    MODEL_PRICING,
    RuntimeConfig,
    calculate_cost,
    AnthropicRuntime,
    OpenAIAgentsRuntime,
    create_runtime,
)


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_all_roles_defined(self):
        """All expected roles are defined."""
        expected_roles = [
            "attacker",
            "defender",
            "verifier",
            "test_builder",
            "supervisor",
            "integrator",
        ]
        actual_roles = [role.value for role in AgentRole]
        assert set(expected_roles) == set(actual_roles)

    def test_role_string_values(self):
        """Roles have correct string values."""
        assert AgentRole.ATTACKER.value == "attacker"
        assert AgentRole.DEFENDER.value == "defender"
        assert AgentRole.VERIFIER.value == "verifier"
        assert AgentRole.TEST_BUILDER.value == "test_builder"
        assert AgentRole.SUPERVISOR.value == "supervisor"
        assert AgentRole.INTEGRATOR.value == "integrator"

    def test_role_is_string_enum(self):
        """Roles can be used as strings."""
        assert AgentRole.ATTACKER == "attacker"
        assert AgentRole.ATTACKER.value == "attacker"


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_minimal_config(self):
        """Config can be created with minimal required fields."""
        config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="You are a security expert.",
        )
        assert config.role == AgentRole.ATTACKER
        assert config.system_prompt == "You are a security expert."
        assert config.tools == []
        assert config.max_tokens == 8192
        assert config.temperature == 0.1
        assert config.timeout_seconds == 300

    def test_full_config(self):
        """Config can be created with all fields."""
        tools = [{"name": "test_tool", "description": "A test tool"}]
        config = AgentConfig(
            role=AgentRole.DEFENDER,
            system_prompt="Defend the protocol.",
            tools=tools,
            max_tokens=4096,
            temperature=0.5,
            timeout_seconds=120,
            metadata={"task": "guard_detection"},
        )
        assert config.role == AgentRole.DEFENDER
        assert config.tools == tools
        assert config.max_tokens == 4096
        assert config.temperature == 0.5
        assert config.timeout_seconds == 120
        assert config.metadata == {"task": "guard_detection"}

    def test_config_serialization(self):
        """Config can be serialized to dict."""
        config = AgentConfig(
            role=AgentRole.VERIFIER,
            system_prompt="Verify evidence.",
        )
        data = config.to_dict()
        assert data["role"] == "verifier"
        assert data["system_prompt"] == "Verify evidence."
        assert data["tools"] == []

    def test_config_deserialization(self):
        """Config can be deserialized from dict."""
        data = {
            "role": "test_builder",
            "system_prompt": "Build tests.",
            "max_tokens": 2048,
        }
        config = AgentConfig.from_dict(data)
        assert config.role == AgentRole.TEST_BUILDER
        assert config.system_prompt == "Build tests."
        assert config.max_tokens == 2048


class TestAgentResponse:
    """Tests for AgentResponse dataclass."""

    def test_response_creation(self):
        """Response can be created with all fields."""
        response = AgentResponse(
            content="Found vulnerability in transfer function.",
            tool_calls=[{"name": "analyze", "input": {"file": "token.sol"}}],
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=800,
            cache_write_tokens=0,
            model="claude-opus-4-20250514",
            latency_ms=2500,
            cost_usd=0.05,
        )
        assert response.content == "Found vulnerability in transfer function."
        assert len(response.tool_calls) == 1
        assert response.input_tokens == 1000
        assert response.output_tokens == 500
        assert response.cache_read_tokens == 800

    def test_response_total_tokens(self):
        """Total tokens calculated correctly."""
        response = AgentResponse(
            content="",
            tool_calls=[],
            input_tokens=1000,
            output_tokens=500,
        )
        assert response.total_tokens == 1500

    def test_response_cache_hit_ratio(self):
        """Cache hit ratio calculated correctly."""
        response = AgentResponse(
            content="",
            tool_calls=[],
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=800,
        )
        assert response.cache_hit_ratio == 0.8

    def test_response_cache_hit_ratio_zero_input(self):
        """Cache hit ratio is 0 when no input tokens."""
        response = AgentResponse(
            content="",
            tool_calls=[],
            input_tokens=0,
            output_tokens=100,
        )
        assert response.cache_hit_ratio == 0.0

    def test_response_serialization(self):
        """Response can be serialized to dict."""
        response = AgentResponse(
            content="Test",
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            model="test-model",
        )
        data = response.to_dict()
        assert data["content"] == "Test"
        assert data["model"] == "test-model"
        assert data["input_tokens"] == 100


class TestUsageTracker:
    """Tests for UsageTracker."""

    def test_track_single_response(self):
        """Tracker accumulates single response."""
        tracker = UsageTracker()
        response = AgentResponse(
            content="",
            tool_calls=[],
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=200,
            model="claude-opus-4-20250514",
            cost_usd=0.05,
        )
        tracker.track(response)
        summary = tracker.get_summary()
        assert summary["total_input_tokens"] == 1000
        assert summary["total_output_tokens"] == 500
        assert summary["total_cache_read_tokens"] == 200
        assert summary["total_cost_usd"] == 0.05
        assert summary["request_count"] == 1

    def test_track_multiple_responses(self):
        """Tracker accumulates multiple responses."""
        tracker = UsageTracker()
        for i in range(3):
            response = AgentResponse(
                content="",
                tool_calls=[],
                input_tokens=100,
                output_tokens=50,
                model="claude-sonnet-4-20250514",
                cost_usd=0.01,
            )
            tracker.track(response)
        summary = tracker.get_summary()
        assert summary["total_input_tokens"] == 300
        assert summary["total_output_tokens"] == 150
        assert summary["request_count"] == 3

    def test_track_per_model(self):
        """Tracker tracks per-model usage."""
        tracker = UsageTracker()
        tracker.track(AgentResponse(
            content="", tool_calls=[], input_tokens=100, output_tokens=50,
            model="claude-opus-4-20250514", cost_usd=0.05,
        ))
        tracker.track(AgentResponse(
            content="", tool_calls=[], input_tokens=200, output_tokens=100,
            model="claude-sonnet-4-20250514", cost_usd=0.02,
        ))
        summary = tracker.get_summary()
        assert "claude-opus-4-20250514" in summary["by_model"]
        assert "claude-sonnet-4-20250514" in summary["by_model"]
        assert summary["by_model"]["claude-opus-4-20250514"]["count"] == 1
        assert summary["by_model"]["claude-sonnet-4-20250514"]["count"] == 1

    def test_tracker_reset(self):
        """Tracker can be reset."""
        tracker = UsageTracker()
        tracker.track(AgentResponse(
            content="", tool_calls=[], input_tokens=100, output_tokens=50,
        ))
        tracker.reset()
        summary = tracker.get_summary()
        assert summary["total_input_tokens"] == 0
        assert summary["request_count"] == 0


class TestRoleModelMap:
    """Tests for ROLE_MODEL_MAP."""

    def test_all_roles_mapped(self):
        """All roles have mappings."""
        for role in AgentRole:
            assert role in ROLE_MODEL_MAP
            assert "anthropic" in ROLE_MODEL_MAP[role]
            assert "openai" in ROLE_MODEL_MAP[role]

    def test_attacker_uses_opus(self):
        """Attacker uses Opus for deep reasoning."""
        assert "opus" in ROLE_MODEL_MAP[AgentRole.ATTACKER]["anthropic"].lower()

    def test_defender_uses_sonnet(self):
        """Defender uses Sonnet for fast guard detection."""
        assert "sonnet" in ROLE_MODEL_MAP[AgentRole.DEFENDER]["anthropic"].lower()

    def test_verifier_uses_opus(self):
        """Verifier uses Opus for critical accuracy."""
        assert "opus" in ROLE_MODEL_MAP[AgentRole.VERIFIER]["anthropic"].lower()


class TestRuntimeConfig:
    """Tests for RuntimeConfig."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = RuntimeConfig()
        assert config.preferred_sdk == "anthropic"
        assert config.enable_prompt_caching is True
        assert config.enable_cost_tracking is True
        assert config.max_retries == 3
        assert config.retry_backoff_base == 2.0

    def test_openai_sdk_config(self):
        """Config can be set for OpenAI SDK."""
        config = RuntimeConfig(preferred_sdk="openai")
        assert config.preferred_sdk == "openai"

    def test_invalid_sdk_raises(self):
        """Invalid SDK raises ValueError."""
        with pytest.raises(ValueError):
            RuntimeConfig(preferred_sdk="invalid")

    def test_negative_retries_raises(self):
        """Negative retries raises ValueError."""
        with pytest.raises(ValueError):
            RuntimeConfig(max_retries=-1)

    def test_zero_backoff_raises(self):
        """Zero backoff raises ValueError."""
        with pytest.raises(ValueError):
            RuntimeConfig(retry_backoff_base=0)

    def test_get_model_for_role(self):
        """Config returns correct model for role."""
        config = RuntimeConfig(preferred_sdk="anthropic")
        model = config.get_model_for_role(AgentRole.ATTACKER)
        assert "opus" in model.lower()

    def test_custom_model_override(self):
        """Custom model map overrides default."""
        config = RuntimeConfig(
            preferred_sdk="anthropic",
            custom_model_map={AgentRole.ATTACKER: "claude-sonnet-4-20250514"},
        )
        model = config.get_model_for_role(AgentRole.ATTACKER)
        assert "sonnet" in model.lower()

    def test_config_serialization(self):
        """Config can be serialized to dict."""
        config = RuntimeConfig(
            preferred_sdk="openai",
            max_retries=5,
        )
        data = config.to_dict()
        assert data["preferred_sdk"] == "openai"
        assert data["max_retries"] == 5

    def test_config_deserialization(self):
        """Config can be deserialized from dict."""
        data = {
            "preferred_sdk": "openai",
            "max_retries": 5,
            "enable_prompt_caching": False,
        }
        config = RuntimeConfig.from_dict(data)
        assert config.preferred_sdk == "openai"
        assert config.max_retries == 5
        assert config.enable_prompt_caching is False


class TestCalculateCost:
    """Tests for calculate_cost function."""

    def test_known_model_cost(self):
        """Cost calculated for known model."""
        cost = calculate_cost(
            model="claude-opus-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )
        # Opus: $15/M input, $75/M output
        expected = (1000 * 15.0 + 500 * 75.0) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_cache_cost_reduction(self):
        """Cached reads reduce cost."""
        cost_no_cache = calculate_cost(
            model="claude-opus-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )
        cost_with_cache = calculate_cost(
            model="claude-opus-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=800,
        )
        # Cache reads should reduce cost
        assert cost_with_cache < cost_no_cache

    def test_unknown_model_fallback(self):
        """Unknown model uses fallback pricing."""
        cost = calculate_cost(
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )
        # Should return some positive value
        assert cost > 0


class TestCreateRuntime:
    """Tests for create_runtime factory."""

    @pytest.mark.xfail(reason="Stale code: Agent runtime create API changed")
    def test_create_anthropic_runtime(self):
        """Creates Anthropic runtime by default."""
        runtime = create_runtime()
        assert isinstance(runtime, AnthropicRuntime)

    @pytest.mark.xfail(reason="Stale code: Agent runtime create API changed")
    def test_create_openai_runtime(self):
        """Creates OpenAI runtime when specified."""
        config = RuntimeConfig(preferred_sdk="openai")
        runtime = create_runtime(config)
        assert isinstance(runtime, OpenAIAgentsRuntime)


class TestAnthropicRuntime:
    """Tests for AnthropicRuntime (mocked)."""

    def test_get_model_for_role(self):
        """Returns correct model for role."""
        config = RuntimeConfig(preferred_sdk="anthropic")
        runtime = AnthropicRuntime(config)
        model = runtime.get_model_for_role(AgentRole.ATTACKER)
        assert "opus" in model.lower()

    def test_build_cached_system(self):
        """Builds cached system content when enabled."""
        config = RuntimeConfig(enable_prompt_caching=True)
        runtime = AnthropicRuntime(config)
        system = runtime._build_cached_system("Test prompt")
        assert len(system) == 1
        assert system[0]["text"] == "Test prompt"
        assert "cache_control" in system[0]

    def test_build_uncached_system(self):
        """Builds uncached system content when disabled."""
        config = RuntimeConfig(enable_prompt_caching=False)
        runtime = AnthropicRuntime(config)
        system = runtime._build_cached_system("Test prompt")
        assert len(system) == 1
        assert system[0]["text"] == "Test prompt"
        assert "cache_control" not in system[0]

    def test_build_cached_tools(self):
        """Builds cached tools with cache_control on last."""
        config = RuntimeConfig(enable_prompt_caching=True)
        runtime = AnthropicRuntime(config)
        tools = [
            {"name": "tool1", "description": "First"},
            {"name": "tool2", "description": "Second"},
        ]
        cached = runtime._build_cached_tools(tools)
        assert "cache_control" not in cached[0]
        assert "cache_control" in cached[1]


class TestOpenAIAgentsRuntime:
    """Tests for OpenAIAgentsRuntime (mocked)."""

    def test_get_model_for_role(self):
        """Returns correct model for role."""
        config = RuntimeConfig(preferred_sdk="openai")
        runtime = OpenAIAgentsRuntime(config)
        model = runtime.get_model_for_role(AgentRole.ATTACKER)
        assert model == "o3"

    def test_convert_tools_empty(self):
        """Converts empty tools list."""
        config = RuntimeConfig(preferred_sdk="openai")
        runtime = OpenAIAgentsRuntime(config)
        converted = runtime._convert_tools([])
        assert converted == []

    def test_convert_tools_anthropic_format(self):
        """Converts tools from Anthropic format."""
        config = RuntimeConfig(preferred_sdk="openai")
        runtime = OpenAIAgentsRuntime(config)
        tools = [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
            }
        ]
        converted = runtime._convert_tools(tools)
        assert len(converted) == 1
        assert converted[0].name == "get_weather"
        assert converted[0].description == "Get weather for a location"

    def test_extract_input_from_messages(self):
        """Extracts input from messages."""
        config = RuntimeConfig(preferred_sdk="openai")
        runtime = OpenAIAgentsRuntime(config)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        input_text = runtime._extract_input_from_messages(messages)
        assert "Hello" in input_text
        assert "How are you?" in input_text
        assert "Hi there" not in input_text

    def test_extract_input_from_content_blocks(self):
        """Extracts input from content blocks."""
        config = RuntimeConfig(preferred_sdk="openai")
        runtime = OpenAIAgentsRuntime(config)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "First part"},
                    {"type": "text", "text": "Second part"},
                ],
            }
        ]
        input_text = runtime._extract_input_from_messages(messages)
        assert "First part" in input_text
        assert "Second part" in input_text


class TestRuntimeInterfaceCompatibility:
    """Tests that both runtimes have compatible interfaces."""

    def test_both_runtimes_have_execute(self):
        """Both runtimes have execute method."""
        anthropic = AnthropicRuntime()
        openai = OpenAIAgentsRuntime()
        assert hasattr(anthropic, "execute")
        assert hasattr(openai, "execute")

    def test_both_runtimes_have_spawn_agent(self):
        """Both runtimes have spawn_agent method."""
        anthropic = AnthropicRuntime()
        openai = OpenAIAgentsRuntime()
        assert hasattr(anthropic, "spawn_agent")
        assert hasattr(openai, "spawn_agent")

    def test_both_runtimes_have_get_model_for_role(self):
        """Both runtimes have get_model_for_role method."""
        anthropic = AnthropicRuntime()
        openai = OpenAIAgentsRuntime()
        assert hasattr(anthropic, "get_model_for_role")
        assert hasattr(openai, "get_model_for_role")

    def test_both_runtimes_have_get_usage(self):
        """Both runtimes have get_usage method."""
        anthropic = AnthropicRuntime()
        openai = OpenAIAgentsRuntime()
        assert hasattr(anthropic, "get_usage")
        assert hasattr(openai, "get_usage")


class TestModelPricing:
    """Tests for MODEL_PRICING data."""

    def test_all_mapped_models_have_pricing(self):
        """All models in ROLE_MODEL_MAP have pricing."""
        for role in AgentRole:
            anthropic_model = ROLE_MODEL_MAP[role]["anthropic"]
            openai_model = ROLE_MODEL_MAP[role]["openai"]
            assert anthropic_model in MODEL_PRICING, f"Missing pricing for {anthropic_model}"
            assert openai_model in MODEL_PRICING, f"Missing pricing for {openai_model}"

    def test_pricing_has_required_fields(self):
        """All pricing entries have input and output."""
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"Missing input price for {model}"
            assert "output" in pricing, f"Missing output price for {model}"
