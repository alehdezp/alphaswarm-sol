"""
Tests for P0-T0: LLM Provider Abstraction

Validates:
- All provider implementations
- Automatic fallback
- Response caching
- Cost tracking
- Budget enforcement
"""

import pytest
import os
from pathlib import Path
import json

from alphaswarm_sol.llm import (
    LLMClient,
    LLMConfig,
    Provider,
    UsageStats,
)
from alphaswarm_sol.llm.providers.mock import MockProvider


class TestLLMClient:
    """Test LLM client functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mock provider only."""
        config = LLMConfig(
            provider_priority=[Provider.MOCK],
            cache_enabled=False,
        )
        return LLMClient(config)

    @pytest.mark.asyncio
    async def test_basic_generation(self, mock_client):
        """Test basic text generation."""
        response = await mock_client.analyze("Hello")
        assert len(response) > 0
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_json_generation(self, mock_client):
        """Test JSON mode generation."""
        # Set up mock response
        mock_provider = mock_client._providers[Provider.MOCK]
        mock_provider.set_default('{"intent": "test", "confidence": 0.9}')

        data = await mock_client.analyze_json("Extract intent")
        assert "intent" in data
        assert data["intent"] == "test"

    @pytest.mark.asyncio
    async def test_caching(self, tmp_path):
        """Test response caching."""
        config = LLMConfig(
            provider_priority=[Provider.MOCK],
            cache_enabled=True,
            cache_dir=str(tmp_path / "llm_cache"),
        )
        client = LLMClient(config)

        # First request
        await client.analyze("Test prompt")
        stats1 = client.get_usage()

        # Second request (should be cached)
        await client.analyze("Test prompt")
        stats2 = client.get_usage()

        assert stats2.cache_hits == 1
        assert stats2.total_requests == 1  # Only first request counted

    @pytest.mark.asyncio
    async def test_budget_enforcement(self):
        """Test budget limit stops requests."""
        config = LLMConfig(
            provider_priority=[Provider.MOCK],
            max_budget_usd=0.0001,  # Very low budget
        )
        client = LLMClient(config)

        # Artificially set high cost
        client._usage.total_cost_usd = 0.001

        with pytest.raises(RuntimeError, match="budget exceeded"):
            await client.analyze("Test")

    def test_available_providers(self, mock_client):
        """Test provider availability check."""
        available = mock_client.available_providers()
        assert available["mock"] is True

    @pytest.mark.asyncio
    async def test_usage_tracking(self, mock_client):
        """Test usage statistics."""
        await mock_client.analyze("Test 1")
        await mock_client.analyze("Test 2")

        stats = mock_client.get_usage()
        assert stats.total_requests == 2
        assert stats.total_input_tokens > 0
        assert isinstance(stats.to_dict(), dict)

    @pytest.mark.asyncio
    async def test_cache_clear(self, tmp_path):
        """Test cache clearing."""
        config = LLMConfig(
            provider_priority=[Provider.MOCK],
            cache_enabled=True,
            cache_dir=str(tmp_path / "llm_cache"),
        )
        client = LLMClient(config)

        await client.analyze("Test")
        assert len(client._cache) > 0

        client.clear_cache()
        assert len(client._cache) == 0


class TestProviderFallback:
    """Test automatic provider fallback."""

    @pytest.mark.asyncio
    async def test_fallback_to_mock(self):
        """Test fallback to mock when no providers available."""
        # Create config with providers that aren't available
        config = LLMConfig(
            provider_priority=[Provider.XAI, Provider.MOCK],
            cache_enabled=False,
        )
        client = LLMClient(config)

        # Should fallback to mock
        response = await client.analyze("Test")
        assert len(response) > 0


class TestMockProvider:
    """Test mock provider functionality."""

    @pytest.mark.asyncio
    async def test_pattern_matching(self):
        """Test pattern-based responses."""
        from alphaswarm_sol.llm.config import PROVIDER_CONFIGS
        from alphaswarm_sol.llm.providers.mock import MockProvider

        config = PROVIDER_CONFIGS[Provider.MOCK]
        provider = MockProvider(config)

        provider.set_response("intent", '{"intent": "transfer"}')
        provider.set_response("security", '{"risk": "high"}')

        response1 = await provider.generate("extract intent")
        assert "transfer" in response1.content

        response2 = await provider.generate("analyze security")
        assert "high" in response2.content

    @pytest.mark.asyncio
    async def test_default_response(self):
        """Test default response when no pattern matches."""
        from alphaswarm_sol.llm.config import PROVIDER_CONFIGS
        from alphaswarm_sol.llm.providers.mock import MockProvider

        config = PROVIDER_CONFIGS[Provider.MOCK]
        provider = MockProvider(config)

        provider.set_default('{"status": "ok"}')

        response = await provider.generate("random prompt")
        assert "ok" in response.content


class TestRealProviders:
    """Integration tests with real providers (skip if no API keys)."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No Gemini API key")
    @pytest.mark.xfail(reason="Stale code: google.generativeai deprecated")
    async def test_google_provider(self):
        """Test Google Gemini provider."""
        config = LLMConfig(provider_priority=[Provider.GOOGLE])
        client = LLMClient(config)

        response = await client.analyze("Say 'hello' and nothing else", max_tokens=10)
        assert "hello" in response.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No Anthropic API key")
    async def test_anthropic_provider(self):
        """Test Anthropic Claude provider."""
        config = LLMConfig(provider_priority=[Provider.ANTHROPIC])
        client = LLMClient(config)

        response = await client.analyze("Say 'hello' and nothing else", max_tokens=10)
        assert "hello" in response.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
    async def test_openai_provider(self):
        """Test OpenAI GPT provider."""
        config = LLMConfig(provider_priority=[Provider.OPENAI])
        client = LLMClient(config)

        response = await client.analyze("Say 'hello' and nothing else", max_tokens=10)
        assert "hello" in response.lower()


class TestUsageStats:
    """Test usage statistics."""

    def test_usage_stats_creation(self):
        """Test UsageStats dataclass."""
        stats = UsageStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cost_usd=0.015,
            total_requests=5,
            cache_hits=2,
        )

        assert stats.total_input_tokens == 1000
        assert stats.total_output_tokens == 500

        data = stats.to_dict()
        assert "cache_hit_rate" in data
        assert data["cache_hit_rate"] > 0


class TestProviderConfig:
    """Test provider configuration."""

    def test_provider_enumeration(self):
        """Test all providers are defined."""
        from alphaswarm_sol.llm.config import Provider

        assert Provider.ANTHROPIC.value == "anthropic"
        assert Provider.GOOGLE.value == "google"
        assert Provider.OPENAI.value == "openai"
        assert Provider.XAI.value == "xai"
        assert Provider.OLLAMA.value == "ollama"
        assert Provider.MOCK.value == "mock"

    def test_provider_configs_exist(self):
        """Test all provider configs are defined."""
        from alphaswarm_sol.llm.config import PROVIDER_CONFIGS, Provider

        for provider in Provider:
            assert provider in PROVIDER_CONFIGS


class TestCostTracking:
    """Test cost tracking functionality."""

    @pytest.mark.asyncio
    async def test_cost_calculation(self):
        """Test that costs are calculated correctly."""
        config = LLMConfig(provider_priority=[Provider.MOCK])
        client = LLMClient(config)

        # Mock provider costs are 0, so this tests the tracking mechanism
        await client.analyze("Test prompt")

        stats = client.get_usage()
        assert stats.total_cost_usd >= 0
        assert "total_cost_usd" in stats.to_dict()

    def test_set_budget(self):
        """Test budget setting."""
        config = LLMConfig()
        client = LLMClient(config)

        client.set_budget(5.0)
        assert client.config.max_budget_usd == 5.0


class TestResearch:
    """Test research module."""

    @pytest.mark.asyncio
    async def test_research_placeholder(self):
        """Test research returns expected structure."""
        config = LLMConfig(research_enabled=True)
        client = LLMClient(config)

        result = await client.research("Chainlink oracle vulnerabilities")
        assert "query" in result

    @pytest.mark.asyncio
    async def test_research_disabled(self):
        """Test research when disabled."""
        config = LLMConfig(research_enabled=False)
        client = LLMClient(config)

        result = await client.research("test")
        assert "error" in result
