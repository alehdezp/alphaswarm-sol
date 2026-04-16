"""
LLM Client - Main Interface

Unified LLM client with:
- Automatic provider fallback
- Response caching (memory + disk)
- Cost tracking and budget enforcement
- Multi-provider support
"""

from typing import Optional, Dict, Any, Type
from dataclasses import dataclass, field
import hashlib
import json
import asyncio
from pathlib import Path

from .config import LLMConfig, Provider, PROVIDER_CONFIGS, ProviderConfig
from .providers.base import LLMProvider, LLMResponse
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.openai import OpenAIProvider
from .providers.xai import XAIProvider
from .providers.ollama import OllamaProvider
from .providers.mock import MockProvider


PROVIDER_CLASSES: Dict[Provider, Type[LLMProvider]] = {
    Provider.ANTHROPIC: AnthropicProvider,
    Provider.GOOGLE: GoogleProvider,
    Provider.OPENAI: OpenAIProvider,
    Provider.XAI: XAIProvider,
    Provider.OLLAMA: OllamaProvider,
    Provider.MOCK: MockProvider,
}


@dataclass
class UsageStats:
    """Aggregated usage statistics across all providers."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_requests: int = 0
    cache_hits: int = 0
    provider_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        total_interactions = self.total_requests + self.cache_hits
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (
                self.cache_hits / total_interactions
                if total_interactions > 0 else 0
            ),
            "providers": self.provider_breakdown,
        }


class LLMClient:
    """
    Unified LLM client with automatic fallback, caching, and cost tracking.

    Usage:
        client = LLMClient()  # Uses default config

        # Simple generation
        response = await client.analyze("Explain this code: ...")

        # JSON mode
        data = await client.analyze_json("Extract intent...", schema=IntentSchema)

        # Research via Exa
        results = await client.research("Chainlink oracle vulnerabilities 2024")

        # Check usage
        stats = client.get_usage()
        print(f"Total cost: ${stats.total_cost_usd:.4f}")
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._providers: Dict[Provider, LLMProvider] = {}
        self._cache: Dict[str, LLMResponse] = {}
        self._usage = UsageStats()
        self._cache_dir = Path(self.config.cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize available providers
        self._init_providers()

    def _init_providers(self):
        """Initialize available providers in priority order."""
        for provider in self.config.provider_priority:
            provider_config = PROVIDER_CONFIGS.get(provider)
            if provider_config and provider_config.is_available():
                provider_class = PROVIDER_CLASSES.get(provider)
                if provider_class:
                    self._providers[provider] = provider_class(provider_config)
                    self._usage.provider_breakdown[provider.value] = {}

        if not self._providers:
            # Fallback to mock if nothing available
            mock_config = PROVIDER_CONFIGS[Provider.MOCK]
            self._providers[Provider.MOCK] = MockProvider(mock_config)

    def _get_cache_key(self, prompt: str, system: str, json_mode: bool) -> str:
        """Generate cache key for request."""
        content = f"{prompt}|{system}|{json_mode}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _check_cache(self, key: str) -> Optional[LLMResponse]:
        """Check in-memory and disk cache."""
        # Memory cache
        if key in self._cache:
            return self._cache[key]

        # Disk cache
        cache_file = self._cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                response = LLMResponse(**data)
                response.cached = True
                self._cache[key] = response
                return response
            except Exception:
                pass

        return None

    def _store_cache(self, key: str, response: LLMResponse):
        """Store response in cache."""
        self._cache[key] = response

        # Disk cache
        cache_file = self._cache_dir / f"{key}.json"
        try:
            cache_file.write_text(json.dumps(response.to_dict()))
        except Exception:
            pass

    async def analyze(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = None,
        temperature: float = None,
        provider: Optional[Provider] = None,
        skip_cache: bool = False,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            max_tokens: Max output tokens (default from config)
            temperature: Temperature (default from config)
            provider: Force specific provider (otherwise auto-select)
            skip_cache: Skip cache lookup

        Returns:
            Generated text response
        """
        response = await self._generate(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens or self.config.default_max_tokens,
            temperature=temperature or self.config.default_temperature,
            json_mode=False,
            provider=provider,
            skip_cache=skip_cache,
        )
        return response.content

    async def analyze_json(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = None,
        provider: Optional[Provider] = None,
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from the LLM.

        Returns:
            Parsed JSON dictionary
        """
        response = await self._generate(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens or self.config.default_max_tokens,
            temperature=0.0,  # Low temp for structured output
            json_mode=True,
            provider=provider,
            skip_cache=False,
        )
        return json.loads(response.content)

    async def _generate(
        self,
        prompt: str,
        system: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
        provider: Optional[Provider],
        skip_cache: bool,
    ) -> LLMResponse:
        """Internal generation with fallback and caching."""

        # Check budget
        if self.config.max_budget_usd and self._usage.total_cost_usd >= self.config.max_budget_usd:
            raise RuntimeError(f"LLM budget exceeded: ${self._usage.total_cost_usd:.4f}")

        # Check cache
        cache_key = self._get_cache_key(prompt, system, json_mode)
        if self.config.cache_enabled and not skip_cache:
            cached = self._check_cache(cache_key)
            if cached:
                self._usage.cache_hits += 1
                return cached

        # Select provider(s) to try
        providers_to_try = (
            [self._providers[provider]] if provider and provider in self._providers
            else list(self._providers.values())
        )

        last_error = None
        for llm_provider in providers_to_try:
            try:
                response = await llm_provider.generate(
                    prompt=prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                )

                # Update usage
                self._usage.total_input_tokens += response.input_tokens
                self._usage.total_output_tokens += response.output_tokens
                self._usage.total_cost_usd += response.cost_usd
                self._usage.total_requests += 1

                # Store in cache
                if self.config.cache_enabled:
                    self._store_cache(cache_key, response)

                # Warn if approaching budget
                if (
                    self.config.max_budget_usd and
                    self._usage.total_cost_usd >= self.config.warn_at_usd
                ):
                    print(f"⚠️ LLM cost warning: ${self._usage.total_cost_usd:.4f}")

                return response

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def research(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Research a topic using Exa Search.

        Args:
            query: Research query
            num_results: Number of results to return

        Returns:
            Search results from Exa
        """
        if not self.config.research_enabled:
            return {"error": "Research disabled"}

        # This integrates with Exa MCP tool
        # In practice, this would call the exa-search MCP tool
        # For now, return a placeholder
        return {
            "query": query,
            "note": "Use mcp__exa-search__web_search_exa tool for actual research",
        }

    def get_usage(self) -> UsageStats:
        """Get aggregated usage statistics."""
        # Update provider breakdown
        for provider, llm_provider in self._providers.items():
            self._usage.provider_breakdown[provider.value] = llm_provider.get_usage()

        return self._usage

    def set_budget(self, max_usd: float):
        """Set maximum budget for this session."""
        self.config.max_budget_usd = max_usd

    def clear_cache(self):
        """Clear the response cache."""
        self._cache.clear()
        for f in self._cache_dir.glob("*.json"):
            f.unlink()

    def available_providers(self) -> Dict[str, bool]:
        """Return which providers are available."""
        return {
            provider.value: provider in self._providers
            for provider in Provider
        }
