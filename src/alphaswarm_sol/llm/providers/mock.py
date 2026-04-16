"""
Mock LLM Provider

Deterministic mock provider for testing without API calls.
Supports pattern-based responses for unit tests.
"""

from .base import LLMProvider, LLMResponse
from ..config import ProviderConfig
from typing import Dict
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
        """Estimate tokens (4 chars per token)."""
        return len(text) // 4
