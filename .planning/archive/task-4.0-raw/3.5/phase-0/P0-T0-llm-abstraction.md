# [P0-T0] LLM Provider Abstraction

**Phase**: 0 - Knowledge Foundation (Pre-requisite)
**Task ID**: P0-T0
**Status**: NOT_STARTED
**Priority**: CRITICAL (Blocks all LLM-dependent tasks)
**Estimated Effort**: 2-3 days
**Actual Effort**: -

---

## Executive Summary

Create a **unified LLM provider abstraction** that allows BSKG 3.5 to use any LLM provider (Anthropic, OpenAI, Google, xAI, local) with automatic fallback, cost tracking, and caching. This is a **prerequisite** for all LLM-dependent tasks.

**Key Requirements**:
- Support multiple providers with consistent interface
- Automatic fallback when a provider fails or hits rate limits
- Cost tracking with budget enforcement
- Response caching to minimize API calls
- Research capability via Exa Search integration

---

## Supported Providers

| Provider | Model | Use Case | Cost (1M tokens) |
|----------|-------|----------|------------------|
| **Anthropic** | claude-3-5-haiku | Fast analysis, intent | ~$0.25 in / $1.25 out |
| **Google** | gemini-2.0-flash | Fast, cheap reasoning | ~$0.10 in / $0.40 out |
| **OpenAI** | gpt-4o-mini | Balanced speed/quality | ~$0.15 in / $0.60 out |
| **xAI** | grok-2 | Code-focused | TBD |
| **Ollama** | llama3.2 / codellama | Local dev, no cost | Free |
| **Mock** | - | Unit tests | Free |

### Provider Priority (Default Fallback Order)
1. **gemini-2.0-flash** - Fastest, cheapest for bulk work
2. **claude-3-5-haiku** - Quality fallback
3. **gpt-4o-mini** - Second fallback
4. **ollama** - Offline fallback

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM PROVIDER ABSTRACTION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          LLMClient (Facade)                             │ │
│  │                                                                         │ │
│  │  Methods:                                                               │ │
│  │  • analyze(prompt, system) → str                                        │ │
│  │  • analyze_json(prompt, schema) → dict                                  │ │
│  │  • research(query) → SearchResults  (via Exa)                          │ │
│  │  • get_usage() → UsageStats                                            │ │
│  │  • set_budget(max_usd)                                                  │ │
│  │                                                                         │ │
│  └─────────────────────────────┬──────────────────────────────────────────┘ │
│                                │                                             │
│              ┌─────────────────┼─────────────────┐                          │
│              │                 │                 │                          │
│              ▼                 ▼                 ▼                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │ProviderRouter │  │  CacheLayer   │  │ CostTracker   │                   │
│  │               │  │               │  │               │                   │
│  │• select_best()│  │• check_cache()│  │• track_usage()│                   │
│  │• fallback()   │  │• store()      │  │• check_budget()│                  │
│  │• health_check()│ │• invalidate() │  │• get_report() │                   │
│  └───────┬───────┘  └───────────────┘  └───────────────┘                   │
│          │                                                                   │
│          ├──────────────┬──────────────┬──────────────┬─────────────┐       │
│          ▼              ▼              ▼              ▼             ▼       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐  │
│  │ Anthropic  │ │  Google    │ │  OpenAI    │ │    xAI     │ │  Ollama  │  │
│  │  Provider  │ │  Provider  │ │  Provider  │ │  Provider  │ │ Provider │  │
│  │            │ │            │ │            │ │            │ │          │  │
│  │ haiku/opus │ │flash/pro   │ │ gpt-4o-mini│ │  grok-2    │ │ local    │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         Exa Search Integration                          │ │
│  │                                                                         │ │
│  │  • Web search for vulnerability research                                │ │
│  │  • Code context search                                                  │ │
│  │  • Documentation lookup                                                 │ │
│  │  • CVE/exploit research                                                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Design

### Configuration

```python
# src/true_vkg/llm/config.py

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import os


class Provider(Enum):
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
        model="gemini-2.0-flash",
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
    cache_dir: str = ".true_vkg/llm_cache"

    # Request settings
    default_max_tokens: int = 4096
    default_temperature: float = 0.1
    timeout_seconds: int = 60
    max_retries: int = 3

    # Exa Search
    exa_api_key_env: str = "EXA_API_KEY"
    research_enabled: bool = True
```

### Provider Base Class

```python
# src/true_vkg/llm/providers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import time


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str

    # Token counts
    input_tokens: int
    output_tokens: int

    # Cost
    cost_usd: float

    # Metadata
    latency_ms: int
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "tokens": {"input": self.input_tokens, "output": self.output_tokens},
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: "ProviderConfig"):
        self.config = config
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost = 0.0
        self._request_count = 0

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        pass

    def get_usage(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_cost_usd": self._total_cost,
            "request_count": self._request_count,
        }

    def _track_usage(self, input_tokens: int, output_tokens: int):
        """Track token usage and cost."""
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_cost += (
            input_tokens * self.config.cost_per_1m_input / 1_000_000 +
            output_tokens * self.config.cost_per_1m_output / 1_000_000
        )
        self._request_count += 1

    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        try:
            response = await self.generate("Say 'ok'", max_tokens=10)
            return len(response.content) > 0
        except Exception:
            return False
```

### Provider Implementations

```python
# src/true_vkg/llm/providers/anthropic.py

import anthropic
from .base import LLMProvider, LLMResponse, ProviderConfig
import time


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(
            api_key=config.get_api_key()
        )

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> LLMResponse:
        start = time.perf_counter()

        messages = [{"role": "user", "content": prompt}]

        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system if system else None,
            messages=messages,
        )

        latency = int((time.perf_counter() - start) * 1000)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        self._track_usage(input_tokens, output_tokens)

        return LLMResponse(
            content=response.content[0].text,
            model=self.config.model,
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
        )

    def count_tokens(self, text: str) -> int:
        # Use Anthropic's tokenizer
        return self.client.count_tokens(text)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.config.cost_per_1m_input / 1_000_000 +
            output_tokens * self.config.cost_per_1m_output / 1_000_000
        )


# src/true_vkg/llm/providers/google.py

import google.generativeai as genai
from .base import LLMProvider, LLMResponse, ProviderConfig
import time


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        genai.configure(api_key=config.get_api_key())
        self.model = genai.GenerativeModel(config.model)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> LLMResponse:
        start = time.perf_counter()

        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        generation_config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        if json_mode:
            generation_config.response_mime_type = "application/json"

        response = await self.model.generate_content_async(
            full_prompt,
            generation_config=generation_config,
        )

        latency = int((time.perf_counter() - start) * 1000)

        # Estimate tokens (Gemini doesn't always return exact counts)
        input_tokens = self.count_tokens(full_prompt)
        output_tokens = self.count_tokens(response.text)
        self._track_usage(input_tokens, output_tokens)

        return LLMResponse(
            content=response.text,
            model=self.config.model,
            provider="google",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
        )

    def count_tokens(self, text: str) -> int:
        # Rough estimate: ~4 chars per token
        return len(text) // 4


# src/true_vkg/llm/providers/openai.py

import openai
from .base import LLMProvider, LLMResponse, ProviderConfig
import time


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = openai.AsyncOpenAI(api_key=config.get_api_key())

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> LLMResponse:
        start = time.perf_counter()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)

        latency = int((time.perf_counter() - start) * 1000)

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        self._track_usage(input_tokens, output_tokens)

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.config.model,
            provider="openai",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
        )

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.encoding_for_model(self.config.model)
        return len(enc.encode(text))


# src/true_vkg/llm/providers/xai.py

import httpx
from .base import LLMProvider, LLMResponse, ProviderConfig
import time


class XAIProvider(LLMProvider):
    """xAI Grok provider (OpenAI-compatible API)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(
            base_url=config.base_url or "https://api.x.ai/v1",
            headers={"Authorization": f"Bearer {config.get_api_key()}"},
            timeout=60,
        )

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> LLMResponse:
        start = time.perf_counter()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        latency = int((time.perf_counter() - start) * 1000)

        input_tokens = data["usage"]["prompt_tokens"]
        output_tokens = data["usage"]["completion_tokens"]
        self._track_usage(input_tokens, output_tokens)

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=self.config.model,
            provider="xai",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // 4  # Rough estimate


# src/true_vkg/llm/providers/ollama.py

import httpx
from .base import LLMProvider, LLMResponse, ProviderConfig
import time


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> LLMResponse:
        start = time.perf_counter()

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        if json_mode:
            payload["format"] = "json"

        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()

        latency = int((time.perf_counter() - start) * 1000)

        # Ollama provides token counts
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return LLMResponse(
            content=data["response"],
            model=self.config.model,
            provider="ollama",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,  # Local = free
            latency_ms=latency,
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // 4


# src/true_vkg/llm/providers/mock.py

from .base import LLMProvider, LLMResponse, ProviderConfig
from typing import Dict, Callable
import re


class MockProvider(LLMProvider):
    """Mock provider for testing with deterministic responses."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._responses: Dict[str, str] = {}
        self._default_response = '{"result": "mock_response"}'

    def set_response(self, pattern: str, response: str):
        """Set a response for prompts matching pattern."""
        self._responses[pattern] = response

    def set_default(self, response: str):
        """Set default response."""
        self._default_response = response

    async def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> LLMResponse:
        # Find matching response
        response_text = self._default_response
        for pattern, resp in self._responses.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                response_text = resp
                break

        input_tokens = self.count_tokens(prompt + system)
        output_tokens = self.count_tokens(response_text)

        return LLMResponse(
            content=response_text,
            model="mock",
            provider="mock",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
            latency_ms=1,
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
```

### LLM Client (Main Interface)

```python
# src/true_vkg/llm/client.py

from typing import Optional, Dict, Any, Type
from dataclasses import dataclass
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
    provider_breakdown: Dict[str, Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (
                self.cache_hits / (self.total_requests + self.cache_hits)
                if (self.total_requests + self.cache_hits) > 0 else 0
            ),
            "providers": self.provider_breakdown or {},
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
        self._usage = UsageStats(provider_breakdown={})
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
```

### Exa Search Integration

```python
# src/true_vkg/llm/research.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    score: float


@dataclass
class ResearchResults:
    """Collection of research results."""
    query: str
    results: List[SearchResult]
    total_found: int

    def to_context(self, max_chars: int = 10000) -> str:
        """Convert to LLM-friendly context string."""
        lines = [f"Research: {self.query}\n"]
        char_count = len(lines[0])

        for r in self.results:
            entry = f"\n## {r.title}\nURL: {r.url}\n{r.snippet}\n"
            if char_count + len(entry) > max_chars:
                break
            lines.append(entry)
            char_count += len(entry)

        return "".join(lines)


class ResearchClient:
    """
    Research client using Exa Search.

    Integrates with the exa-search MCP tools for:
    - Vulnerability research
    - CVE lookups
    - Documentation search
    - Code pattern search
    """

    async def search_vulnerabilities(
        self,
        topic: str,
        year: Optional[int] = None,
    ) -> ResearchResults:
        """Search for vulnerability information."""
        query = f"{topic} vulnerability exploit"
        if year:
            query += f" {year}"

        # Would call mcp__exa-search__web_search_exa
        # This is a placeholder for the integration
        return ResearchResults(
            query=query,
            results=[],
            total_found=0,
        )

    async def search_code_patterns(
        self,
        pattern: str,
        language: str = "solidity",
    ) -> ResearchResults:
        """Search for code patterns using Exa Code Search."""
        # Would call mcp__exa-search__get_code_context_exa
        return ResearchResults(
            query=f"{language} {pattern}",
            results=[],
            total_found=0,
        )

    async def search_documentation(
        self,
        topic: str,
        domains: Optional[List[str]] = None,
    ) -> ResearchResults:
        """Search for documentation."""
        domains = domains or ["docs.openzeppelin.com", "ethereum.org", "solidity.readthedocs.io"]
        # Would filter search to these domains
        return ResearchResults(
            query=topic,
            results=[],
            total_found=0,
        )
```

---

## Success Criteria

- [ ] All 5 providers implemented and tested
- [ ] Automatic fallback when provider fails
- [ ] Response caching reduces API calls by 90%+
- [ ] Cost tracking accurate to 0.1%
- [ ] Budget enforcement stops requests when exceeded
- [ ] Mock provider enables deterministic unit tests
- [ ] Exa Search integration for research queries
- [ ] Clear usage reporting

---

## Validation Tests

```python
import pytest
from true_vkg.llm.client import LLMClient
from true_vkg.llm.config import LLMConfig, Provider
from true_vkg.llm.providers.mock import MockProvider


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

    @pytest.mark.asyncio
    async def test_json_generation(self, mock_client):
        """Test JSON mode generation."""
        # Set up mock response
        mock_provider = mock_client._providers[Provider.MOCK]
        mock_provider.set_default('{"intent": "test"}')

        data = await mock_client.analyze_json("Extract intent")
        assert "intent" in data

    @pytest.mark.asyncio
    async def test_caching(self):
        """Test response caching."""
        config = LLMConfig(
            provider_priority=[Provider.MOCK],
            cache_enabled=True,
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
        assert available["mock"] == True

    @pytest.mark.asyncio
    async def test_usage_tracking(self, mock_client):
        """Test usage statistics."""
        await mock_client.analyze("Test 1")
        await mock_client.analyze("Test 2")

        stats = mock_client.get_usage()
        assert stats.total_requests == 2
        assert stats.total_input_tokens > 0


class TestProviderFallback:
    """Test automatic provider fallback."""

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """Test fallback to next provider when one fails."""
        # This would require mocking provider failures
        pass


class TestRealProviders:
    """Integration tests with real providers (skip if no API keys)."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="No Gemini API key")
    async def test_google_provider(self):
        """Test Google Gemini provider."""
        config = LLMConfig(provider_priority=[Provider.GOOGLE])
        client = LLMClient(config)

        response = await client.analyze("Say 'hello' and nothing else")
        assert "hello" in response.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No Anthropic API key")
    async def test_anthropic_provider(self):
        """Test Anthropic Claude provider."""
        config = LLMConfig(provider_priority=[Provider.ANTHROPIC])
        client = LLMClient(config)

        response = await client.analyze("Say 'hello' and nothing else")
        assert "hello" in response.lower()
```

---

## Integration with Other Tasks

This task **MUST BE COMPLETED BEFORE**:
- P1-T2 (LLM Intent Annotator) - Uses LLMClient
- P2-T2 (Attacker Agent) - Uses LLMClient
- P2-T3 (Defender Agent) - Uses LLMClient
- P2-T4 (LLMDFA Verifier) - Uses LLMClient
- P3-T1 (Iterative Engine) - Uses LLMClient

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-03 | Created as prerequisite task | Claude |
