"""
xAI Grok Provider

Supports Grok-2 via xAI's OpenAI-compatible API.
"""

import httpx
from .base import LLMProvider, LLMResponse
from ..config import ProviderConfig
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
        """Rough estimate: ~4 chars per token."""
        return len(text) // 4

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        return (
            input_tokens * self.config.cost_per_1m_input / 1_000_000 +
            output_tokens * self.config.cost_per_1m_output / 1_000_000
        )
