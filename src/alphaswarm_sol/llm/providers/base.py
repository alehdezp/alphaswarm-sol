"""
Base LLM Provider

Abstract base class for all LLM providers with:
- Unified response format
- Token tracking
- Cost calculation
- Health checks
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


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

    # Tool calls (for tool-calling responses)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "tokens": {"input": self.input_tokens, "output": self.output_tokens},
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
        }
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result


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
