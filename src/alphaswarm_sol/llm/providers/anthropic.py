"""
Anthropic Claude Provider

Supports Claude models via Anthropic API with tool calling support.
"""

import time
from typing import Any, Dict, List, Optional

import anthropic

from .base import LLMProvider, LLMResponse
from ..config import ProviderConfig


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with tool calling support."""

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

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        tool_choice: Optional[Dict[str, Any]] = None,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> LLMResponse:
        """Generate response with tool calling.

        Uses Claude's tool calling feature for structured outputs with
        guaranteed schema compliance via the structured-outputs beta.

        Args:
            prompt: User prompt
            tools: List of tool definitions with JSON Schema
            tool_choice: Optional tool choice constraint
                         (e.g., {"type": "tool", "name": "apply_labels_batch"})
            system: System prompt
            max_tokens: Maximum output tokens
            temperature: Sampling temperature

        Returns:
            LLMResponse with tool_calls populated if tools were used
        """
        start = time.perf_counter()

        messages = [{"role": "user", "content": prompt}]

        # Build request kwargs
        kwargs: Dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            "tools": tools,
        }

        if system:
            kwargs["system"] = system

        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        # Add structured outputs header for guaranteed schema compliance
        response = await self.client.messages.create(
            **kwargs,
            extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"}
        )

        latency = int((time.perf_counter() - start) * 1000)

        # Extract tool calls from response
        tool_calls: List[Dict[str, Any]] = []
        content = ""
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
            elif block.type == "text":
                content = block.text

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        self._track_usage(input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            model=self.config.model,
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
            tool_calls=tool_calls,
        )

    def count_tokens(self, text: str) -> int:
        """Use Anthropic's tokenizer."""
        return self.client.count_tokens(text)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        return (
            input_tokens * self.config.cost_per_1m_input / 1_000_000 +
            output_tokens * self.config.cost_per_1m_output / 1_000_000
        )


def extract_labels_from_response(response: LLMResponse) -> List[Dict[str, Any]]:
    """Extract label assignments from tool call response.

    Helper function to extract labels from any tool calls in the response.

    Args:
        response: LLMResponse with potential tool_calls

    Returns:
        List of label assignment dicts with function_id, label, confidence, reasoning
    """
    labels: List[Dict[str, Any]] = []

    for tool_call in response.tool_calls:
        if tool_call["name"] == "apply_label":
            labels.append(tool_call["input"])
        elif tool_call["name"] == "apply_labels_batch":
            labels.extend(tool_call["input"].get("labels", []))

    return labels
