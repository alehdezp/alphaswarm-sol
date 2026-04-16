"""
Ollama Local LLM Provider

Supports local models via Ollama.
"""

import httpx
from .base import LLMProvider, LLMResponse
from ..config import ProviderConfig
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
        """Rough estimate: ~4 chars per token."""
        return len(text) // 4
