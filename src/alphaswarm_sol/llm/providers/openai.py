"""
OpenAI GPT Provider

Supports GPT-4o-mini and other OpenAI models.
"""

import openai
from .base import LLMProvider, LLMResponse
from ..config import ProviderConfig
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
        """Use tiktoken for accurate token counting."""
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(self.config.model)
            return len(enc.encode(text))
        except Exception:
            # Fallback to rough estimate
            return len(text) // 4

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        return (
            input_tokens * self.config.cost_per_1m_input / 1_000_000 +
            output_tokens * self.config.cost_per_1m_output / 1_000_000
        )
