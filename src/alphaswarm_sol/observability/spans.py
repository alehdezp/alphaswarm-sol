"""Span creators for agents, tools, handoffs, and guardrails.

This module provides context manager functions for creating spans following
GenAI semantic conventions v1.37+.
"""

from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .tracer import get_tracer


@contextmanager
def create_agent_span(
    agent_name: str,
    pool_id: str,
    bead_id: Optional[str] = None,
    model: Optional[str] = None,
    operation: str = "chat",
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Create span for agent invocation with GenAI semantic conventions.

    Args:
        agent_name: Name of the agent (e.g., "vrs-attacker")
        pool_id: Pool identifier
        bead_id: Bead identifier (optional)
        model: Model identifier (e.g., "claude-opus-4")
        operation: GenAI operation name (default: "chat")
        attributes: Additional span attributes

    Yields:
        Active span

    Example:
        >>> with create_agent_span("vrs-attacker", "pool-123", model="claude-opus-4") as span:
        ...     # Agent logic here
        ...     span.set_attribute("gen_ai.usage.input_tokens", 1500)
    """
    tracer = get_tracer()
    span_name = f"{agent_name}.{operation}"

    # Build attributes following GenAI semantic conventions
    span_attrs: Dict[str, Any] = {
        "gen_ai.system": _extract_system_from_model(model) if model else "unknown",
        "gen_ai.operation.name": operation,
        "alphaswarm.agent.name": agent_name,
        "alphaswarm.pool.id": pool_id,
    }

    if model:
        span_attrs["gen_ai.request.model"] = model

    if bead_id:
        span_attrs["alphaswarm.bead.id"] = bead_id

    if attributes:
        span_attrs.update(attributes)

    with tracer.start_as_current_span(span_name, attributes=span_attrs) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def create_tool_span(
    tool_name: str,
    pool_id: str,
    bead_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Create span for tool invocation.

    Args:
        tool_name: Name of the tool (e.g., "slither", "mythril")
        pool_id: Pool identifier
        bead_id: Bead identifier (optional)
        attributes: Additional span attributes

    Yields:
        Active span

    Example:
        >>> with create_tool_span("slither", "pool-123") as span:
        ...     # Tool execution logic
        ...     span.set_attribute("tool.exit_code", 0)
    """
    tracer = get_tracer("alphaswarm.tools")
    span_name = f"tool.{tool_name}"

    span_attrs: Dict[str, Any] = {
        "alphaswarm.tool.name": tool_name,
        "alphaswarm.pool.id": pool_id,
    }

    if bead_id:
        span_attrs["alphaswarm.bead.id"] = bead_id

    if attributes:
        span_attrs.update(attributes)

    with tracer.start_as_current_span(span_name, attributes=span_attrs) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def create_handoff_span(
    from_agent: str,
    to_agent: str,
    pool_id: str,
    bead_id: Optional[str] = None,
    handoff_reason: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Create span for agent-to-agent handoff.

    Args:
        from_agent: Source agent name
        to_agent: Target agent name
        pool_id: Pool identifier
        bead_id: Bead identifier (optional)
        handoff_reason: Reason for handoff (optional)
        attributes: Additional span attributes

    Yields:
        Active span

    Example:
        >>> with create_handoff_span("vrs-attacker", "vrs-defender", "pool-123") as span:
        ...     # Handoff logic
        ...     span.set_attribute("handoff.context_size", 2500)
    """
    tracer = get_tracer()
    span_name = f"handoff.{from_agent}_to_{to_agent}"

    span_attrs: Dict[str, Any] = {
        "alphaswarm.handoff.from": from_agent,
        "alphaswarm.handoff.to": to_agent,
        "alphaswarm.pool.id": pool_id,
    }

    if bead_id:
        span_attrs["alphaswarm.bead.id"] = bead_id

    if handoff_reason:
        span_attrs["alphaswarm.handoff.reason"] = handoff_reason

    if attributes:
        span_attrs.update(attributes)

    with tracer.start_as_current_span(span_name, attributes=span_attrs) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@contextmanager
def create_guardrail_span(
    guardrail_type: str,
    agent_name: str,
    pool_id: str,
    bead_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[trace.Span, None, None]:
    """Create span for guardrail execution.

    Args:
        guardrail_type: Type of guardrail (e.g., "input_validation", "cost_limit")
        agent_name: Name of the agent being guarded
        pool_id: Pool identifier
        bead_id: Bead identifier (optional)
        attributes: Additional span attributes

    Yields:
        Active span

    Example:
        >>> with create_guardrail_span("cost_limit", "vrs-attacker", "pool-123") as span:
        ...     # Guardrail check
        ...     span.set_attribute("guardrail.passed", True)
    """
    tracer = get_tracer()
    span_name = f"guardrail.{guardrail_type}"

    span_attrs: Dict[str, Any] = {
        "alphaswarm.guardrail.type": guardrail_type,
        "alphaswarm.agent.name": agent_name,
        "alphaswarm.pool.id": pool_id,
    }

    if bead_id:
        span_attrs["alphaswarm.bead.id"] = bead_id

    if attributes:
        span_attrs.update(attributes)

    with tracer.start_as_current_span(span_name, attributes=span_attrs) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def _extract_system_from_model(model: str) -> str:
    """Extract GenAI system from model identifier.

    Args:
        model: Model identifier (e.g., "claude-opus-4", "gpt-4o")

    Returns:
        System identifier (e.g., "anthropic", "openai")
    """
    model_lower = model.lower()
    if "claude" in model_lower:
        return "anthropic"
    elif "gpt" in model_lower or "o1" in model_lower:
        return "openai"
    elif "gemini" in model_lower:
        return "google"
    else:
        return "unknown"
