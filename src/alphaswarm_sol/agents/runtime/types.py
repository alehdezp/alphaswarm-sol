"""Task Types and Model Pricing for OpenCode SDK Runtime.

This module provides:
- TaskType: Enumeration of task categories for model routing
- MODEL_PRICING: Cost information for cost tracking
- MODEL_CONTEXT_LIMITS: Context window sizes
- DEFAULT_MODELS: Task-type to model mapping

Per 05.3-CONTEXT.md, models are selected based on task requirements:
- VERIFY/SUMMARIZE/CONTEXT: Free models for cost optimization
- REASONING/REASONING_HEAVY: Paid models for quality
- CODE: Subscription models (GLM-4.7)
- CRITICAL/REVIEW: CLI-based (Claude Code, Codex)

Usage:
    from alphaswarm_sol.agents.runtime.types import (
        TaskType,
        MODEL_PRICING,
        calculate_model_cost,
        DEFAULT_MODELS,
    )

    model = DEFAULT_MODELS[TaskType.VERIFY]
    cost = calculate_model_cost(model, input_tokens=1000, output_tokens=500)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Tuple


class TaskType(str, Enum):
    """Task type categories for model routing.

    Each task type maps to optimal models based on cost/quality tradeoffs.
    Per 05.3-CONTEXT.md decision matrix:

    - VERIFY: Validation, double-checks -> free models
    - SUMMARIZE: Context compression -> free models
    - CONTEXT: Quick context gathering -> Grok Code Fast 1 (FREE)
    - CODE: Code generation, tests -> GLM-4.7 (subscription)
    - REASONING: Deep reasoning -> DeepSeek V3.2
    - REASONING_HEAVY: Complex reasoning -> Gemini 3 Pro
    - HEAVY: Large context processing -> Gemini 3 Flash
    - ANALYZE: General analysis -> default model
    - REVIEW: Reviews, discussion -> Codex CLI
    - CRITICAL: Critical analysis -> Claude Code CLI
    """
    VERIFY = "verify"
    SUMMARIZE = "summarize"
    CONTEXT = "context"
    CODE = "code"
    REASONING = "reasoning"
    REASONING_HEAVY = "reasoning_heavy"
    HEAVY = "heavy"
    ANALYZE = "analyze"
    REVIEW = "review"
    CRITICAL = "critical"


# Model pricing per million tokens: (input_price, output_price)
# Per 05.3-CONTEXT.md model cost table
MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # Free tier models
    "x-ai/grok-code-fast-1": (0.0, 0.002),  # Minimal output cost
    "minimax/minimax-m2:free": (0.0, 0.0),
    "bigpickle/bigpickle:free": (0.0, 0.0),
    "qwen/qwen-2.5-72b-instruct:free": (0.0, 0.0),

    # Paid models via OpenRouter
    "deepseek/deepseek-v3.2": (0.25, 0.38),
    "google/gemini-3-flash-preview": (0.50, 3.0),
    "google/gemini-3-pro-preview": (2.0, 12.0),

    # Subscription models (treated as zero marginal cost)
    "zhipu/glm-4.7": (0.0, 0.0),  # $6/month subscription

    # Fallback for unknown models - conservative estimate
    "default": (2.0, 10.0),
}


# Model context window limits (max tokens)
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    "x-ai/grok-code-fast-1": 256_000,
    "minimax/minimax-m2:free": 204_000,
    "bigpickle/bigpickle:free": 200_000,
    "qwen/qwen-2.5-72b-instruct:free": 32_768,  # Smaller context
    "deepseek/deepseek-v3.2": 164_000,
    "google/gemini-3-flash-preview": 1_000_000,
    "google/gemini-3-pro-preview": 1_000_000,
    "zhipu/glm-4.7": 128_000,
    "default": 100_000,  # Conservative default
}


# Default models per task type
# Per 05.3-CONTEXT.md model selection strategy
DEFAULT_MODELS: Dict[TaskType, str] = {
    TaskType.VERIFY: "minimax/minimax-m2:free",
    TaskType.SUMMARIZE: "minimax/minimax-m2:free",
    TaskType.CONTEXT: "x-ai/grok-code-fast-1",
    TaskType.CODE: "zhipu/glm-4.7",
    TaskType.REASONING: "deepseek/deepseek-v3.2",
    TaskType.REASONING_HEAVY: "google/gemini-3-pro-preview",
    TaskType.HEAVY: "google/gemini-3-flash-preview",
    TaskType.ANALYZE: "google/gemini-3-flash-preview",  # Default
    TaskType.REVIEW: "codex",  # Codex CLI - handled specially
    TaskType.CRITICAL: "claude",  # Claude Code CLI - handled specially
}


def calculate_model_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate cost in USD for token usage.

    Args:
        model_id: Model identifier (e.g., "deepseek/deepseek-v3.2")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD

    Example:
        >>> calculate_model_cost("deepseek/deepseek-v3.2", 1000, 500)
        0.00044  # $0.25/M * 1000 + $0.38/M * 500
    """
    pricing = MODEL_PRICING.get(model_id, MODEL_PRICING["default"])
    input_price, output_price = pricing

    input_cost = (input_tokens * input_price) / 1_000_000
    output_cost = (output_tokens * output_price) / 1_000_000

    return input_cost + output_cost


def get_context_limit(model_id: str) -> int:
    """Get the context window limit for a model.

    Args:
        model_id: Model identifier

    Returns:
        Maximum context window size in tokens
    """
    return MODEL_CONTEXT_LIMITS.get(model_id, MODEL_CONTEXT_LIMITS["default"])


def is_free_model(model_id: str) -> bool:
    """Check if a model is free (zero cost).

    Args:
        model_id: Model identifier

    Returns:
        True if the model has zero input and output cost
    """
    pricing = MODEL_PRICING.get(model_id, MODEL_PRICING["default"])
    return pricing[0] == 0.0 and pricing[1] == 0.0


__all__ = [
    "TaskType",
    "MODEL_PRICING",
    "MODEL_CONTEXT_LIMITS",
    "DEFAULT_MODELS",
    "calculate_model_cost",
    "get_context_limit",
    "is_free_model",
]
