"""Observability module for AlphaSwarm multi-agent orchestration.

This module provides unified tracing using OpenTelemetry with GenAI semantic
conventions for end-to-end visibility of agent invocations, tool calls, and handoffs.
"""

from .events import (
    record_error_event,
    record_input_event,
    record_llm_usage,
    record_output_event,
)
from .spans import (
    create_agent_span,
    create_guardrail_span,
    create_handoff_span,
    create_tool_span,
)
from .tracer import get_tracer, setup_tracing, shutdown_tracing

__all__ = [
    # Tracer setup
    "setup_tracing",
    "get_tracer",
    "shutdown_tracing",
    # Span creators
    "create_agent_span",
    "create_tool_span",
    "create_handoff_span",
    "create_guardrail_span",
    # Event recorders
    "record_input_event",
    "record_output_event",
    "record_error_event",
    "record_llm_usage",
]
