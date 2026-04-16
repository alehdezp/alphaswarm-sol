"""Event definitions for input, output, and error logging.

This module provides functions for recording structured events on spans
without logging full prompt payloads to avoid PII/token bloat.
"""

from typing import Any, Dict, Optional

from opentelemetry import trace


def record_input_event(
    span: trace.Span,
    input_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record input event on span without full payload.

    Args:
        span: Active span to add event to
        input_type: Type of input (e.g., "user_query", "bead_context")
        metadata: Metadata about input (e.g., token count, size)

    Example:
        >>> with create_agent_span("vrs-attacker", "pool-123") as span:
        ...     record_input_event(span, "bead_context", {"token_count": 1500})
    """
    attributes: Dict[str, Any] = {
        "event.type": "input",
        "input.type": input_type,
    }

    if metadata:
        # Add metadata with "input." prefix
        for key, value in metadata.items():
            attributes[f"input.{key}"] = value

    span.add_event("input_received", attributes=attributes)


def record_output_event(
    span: trace.Span,
    output_type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record output event on span without full payload.

    Args:
        span: Active span to add event to
        output_type: Type of output (e.g., "finding", "verdict")
        metadata: Metadata about output (e.g., token count, verdict)

    Example:
        >>> with create_agent_span("vrs-attacker", "pool-123") as span:
        ...     record_output_event(span, "finding", {"verdict": "confirmed", "token_count": 800})
    """
    attributes: Dict[str, Any] = {
        "event.type": "output",
        "output.type": output_type,
    }

    if metadata:
        # Add metadata with "output." prefix
        for key, value in metadata.items():
            attributes[f"output.{key}"] = value

    span.add_event("output_generated", attributes=attributes)


def record_error_event(
    span: trace.Span,
    error_type: str,
    error_message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record error event on span.

    Args:
        span: Active span to add event to
        error_type: Type of error (e.g., "validation_error", "llm_error")
        error_message: Error message
        metadata: Additional error metadata

    Example:
        >>> with create_agent_span("vrs-attacker", "pool-123") as span:
        ...     record_error_event(span, "llm_error", "Rate limit exceeded", {"retry_count": 3})
    """
    attributes: Dict[str, Any] = {
        "event.type": "error",
        "error.type": error_type,
        "error.message": error_message,
    }

    if metadata:
        # Add metadata with "error." prefix
        for key, value in metadata.items():
            attributes[f"error.{key}"] = value

    span.add_event("error_occurred", attributes=attributes)


def record_llm_usage(
    span: trace.Span,
    input_tokens: int,
    output_tokens: int,
    cost_usd: Optional[float] = None,
) -> None:
    """Record LLM token usage and cost as span attributes.

    Args:
        span: Active span to add attributes to
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_usd: Cost in USD (optional)

    Example:
        >>> with create_agent_span("vrs-attacker", "pool-123") as span:
        ...     record_llm_usage(span, input_tokens=1500, output_tokens=800, cost_usd=0.05)
    """
    # Follow GenAI semantic conventions v1.37+
    span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", output_tokens)

    total_tokens = input_tokens + output_tokens
    span.set_attribute("gen_ai.usage.total_tokens", total_tokens)

    if cost_usd is not None:
        span.set_attribute("alphaswarm.usage.cost_usd", cost_usd)
