"""
Google Gemini Provider

Supports Gemini 2.0 Flash and Pro models.
"""

from __future__ import annotations

from .base import LLMProvider, LLMResponse
from ..config import ProviderConfig
import time


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        import google.generativeai as genai  # Lazy import to avoid FutureWarning on every CLI command

        genai.configure(api_key=config.get_api_key())
        self._genai = genai
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

        generation_config = self._genai.GenerationConfig(
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
        """Rough estimate: ~4 chars per token."""
        return len(text) // 4

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        return (
            input_tokens * self.config.cost_per_1m_input / 1_000_000 +
            output_tokens * self.config.cost_per_1m_output / 1_000_000
        )
