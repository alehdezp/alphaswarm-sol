"""
LLM Provider Configuration

Defines configuration for all supported LLM providers including:
- Provider enumeration
- Per-provider settings (API keys, costs, rate limits)
- Global LLM configuration (fallback order, budget, caching)
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import os


class Provider(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"
    XAI = "xai"
    OLLAMA = "ollama"
    MOCK = "mock"


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""
    provider: Provider
    model: str
    api_key_env: str  # Environment variable name for API key
    base_url: Optional[str] = None

    # Cost per 1M tokens (for budget tracking)
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 100_000

    # Capabilities
    supports_json_mode: bool = True
    supports_system_prompt: bool = True
    max_context_tokens: int = 128_000

    def get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        return os.getenv(self.api_key_env)

    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        if self.provider == Provider.MOCK:
            return True
        if self.provider == Provider.OLLAMA:
            # Check if Ollama is running locally
            return self._check_ollama()
        return self.get_api_key() is not None

    def _check_ollama(self) -> bool:
        """Check if Ollama is running on localhost."""
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False


# Pre-configured providers
PROVIDER_CONFIGS = {
    Provider.ANTHROPIC: ProviderConfig(
        provider=Provider.ANTHROPIC,
        model="claude-3-5-haiku-latest",
        api_key_env="ANTHROPIC_API_KEY",
        cost_per_1m_input=0.25,
        cost_per_1m_output=1.25,
        max_context_tokens=200_000,
    ),
    Provider.GOOGLE: ProviderConfig(
        provider=Provider.GOOGLE,
        model="gemini-2.0-flash-exp",
        api_key_env="GEMINI_API_KEY",
        cost_per_1m_input=0.10,
        cost_per_1m_output=0.40,
        max_context_tokens=1_000_000,
    ),
    Provider.OPENAI: ProviderConfig(
        provider=Provider.OPENAI,
        model="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        max_context_tokens=128_000,
    ),
    Provider.XAI: ProviderConfig(
        provider=Provider.XAI,
        model="grok-2",
        api_key_env="XAI_API_KEY",
        base_url="https://api.x.ai/v1",
        cost_per_1m_input=2.0,  # Estimate
        cost_per_1m_output=10.0,
        max_context_tokens=131_072,
    ),
    Provider.OLLAMA: ProviderConfig(
        provider=Provider.OLLAMA,
        model="llama3.2",
        api_key_env="",  # No API key needed
        base_url="http://localhost:11434",
        cost_per_1m_input=0.0,
        cost_per_1m_output=0.0,
        max_context_tokens=128_000,
    ),
    Provider.MOCK: ProviderConfig(
        provider=Provider.MOCK,
        model="mock",
        api_key_env="",
        cost_per_1m_input=0.0,
        cost_per_1m_output=0.0,
    ),
}


@dataclass
class LLMConfig:
    """Global LLM configuration."""
    # Provider priority (fallback order)
    provider_priority: List[Provider] = field(default_factory=lambda: [
        Provider.GOOGLE,      # Cheapest, fastest
        Provider.ANTHROPIC,   # Quality fallback
        Provider.OPENAI,      # Second fallback
        Provider.XAI,         # Third fallback
        Provider.OLLAMA,      # Offline fallback
    ])

    # Cost controls
    max_budget_usd: Optional[float] = None  # None = unlimited
    warn_at_usd: float = 1.0

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600 * 24  # 24 hours
    cache_dir: str = ".vrs/llm_cache"

    # Request settings
    default_max_tokens: int = 4096
    default_temperature: float = 0.1
    timeout_seconds: int = 60
    max_retries: int = 3

    # Exa Search
    exa_api_key_env: str = "EXA_API_KEY"
    research_enabled: bool = True
