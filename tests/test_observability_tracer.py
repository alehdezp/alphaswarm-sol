"""Tests for observability tracer and span creators.

This test suite verifies that the OpenTelemetry integration produces
spans with correct GenAI semantic convention attributes.

Note: These tests disable xdist parallelization due to global TracerProvider state.
"""

import pytest
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from alphaswarm_sol.observability import (
    create_agent_span,
    create_guardrail_span,
    create_handoff_span,
    create_tool_span,
    get_tracer,
    record_error_event,
    record_input_event,
    record_llm_usage,
    record_output_event,
    setup_tracing,
    shutdown_tracing,
)

# Disable xdist for this module due to global TracerProvider state
pytestmark = pytest.mark.xdist_group(name="observability")


@pytest.fixture(scope="function")
def fresh_tracer():
    """Create a fresh tracer provider for each test.

    This fixture ensures clean state by creating a new provider
    and properly cleaning up after each test.
    """
    # Save original provider
    original_provider = trace_api._TRACER_PROVIDER

    # Create new exporter and provider
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Force set new provider
    trace_api._TRACER_PROVIDER = provider

    # Return both for test use
    yield provider, exporter

    # Cleanup
    provider.force_flush()
    provider.shutdown()

    # Restore original
    trace_api._TRACER_PROVIDER = original_provider


def test_tracer_setup_returns_valid_tracer():
    """Test that tracer setup returns a valid OTel Tracer instance."""
    tracer = setup_tracing(service_name="test-service")
    assert tracer is not None
    assert hasattr(tracer, "start_span")
    shutdown_tracing()


def test_get_tracer_returns_tracer():
    """Test that get_tracer returns a tracer from global provider."""
    setup_tracing()
    tracer = get_tracer("test.module")
    assert tracer is not None
    assert hasattr(tracer, "start_span")
    shutdown_tracing()


def test_agent_span_has_genai_attributes(fresh_tracer):
    """Test that agent spans have GenAI semantic convention attributes."""
    provider, exporter = fresh_tracer

    with create_agent_span(
        agent_name="vrs-attacker",
        pool_id="pool-123",
        bead_id="bead-456",
        model="claude-opus-4",
        operation="chat",
    ) as span:
        assert span is not None

    # Force flush to get finished spans
    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.name == "vrs-attacker.chat"

    # Check GenAI semantic conventions v1.37+
    attrs = dict(span.attributes)
    assert attrs["gen_ai.system"] == "anthropic"
    assert attrs["gen_ai.operation.name"] == "chat"
    assert attrs["gen_ai.request.model"] == "claude-opus-4"
    assert attrs["alphaswarm.agent.name"] == "vrs-attacker"
    assert attrs["alphaswarm.pool.id"] == "pool-123"
    assert attrs["alphaswarm.bead.id"] == "bead-456"


def test_agent_span_system_extraction(fresh_tracer):
    """Test that agent span correctly extracts system from model name."""
    provider, exporter = fresh_tracer

    test_cases = [
        ("claude-sonnet-4.5", "anthropic"),
        ("gpt-4o", "openai"),
        ("o1-preview", "openai"),
        ("gemini-2.0-flash", "google"),
        ("unknown-model", "unknown"),
    ]

    for model, expected_system in test_cases:
        exporter.clear()
        with create_agent_span("test", "pool-1", model=model):
            pass
        provider.force_flush()
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        attrs = dict(spans[0].attributes)
        assert attrs["gen_ai.system"] == expected_system, f"Failed for model {model}"


def test_tool_span_has_correct_attributes(fresh_tracer):
    """Test that tool spans have correct attributes."""
    provider, exporter = fresh_tracer

    with create_tool_span(
        tool_name="slither", pool_id="pool-123", bead_id="bead-456"
    ):
        pass

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.name == "tool.slither"

    attrs = dict(span.attributes)
    assert attrs["alphaswarm.tool.name"] == "slither"
    assert attrs["alphaswarm.pool.id"] == "pool-123"
    assert attrs["alphaswarm.bead.id"] == "bead-456"


def test_handoff_span_has_correct_attributes(fresh_tracer):
    """Test that handoff spans have correct attributes."""
    provider, exporter = fresh_tracer

    with create_handoff_span(
        from_agent="vrs-attacker",
        to_agent="vrs-defender",
        pool_id="pool-123",
        bead_id="bead-456",
        handoff_reason="found_vulnerability",
    ):
        pass

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.name == "handoff.vrs-attacker_to_vrs-defender"

    attrs = dict(span.attributes)
    assert attrs["alphaswarm.handoff.from"] == "vrs-attacker"
    assert attrs["alphaswarm.handoff.to"] == "vrs-defender"
    assert attrs["alphaswarm.pool.id"] == "pool-123"
    assert attrs["alphaswarm.bead.id"] == "bead-456"
    assert attrs["alphaswarm.handoff.reason"] == "found_vulnerability"


def test_guardrail_span_has_correct_attributes(fresh_tracer):
    """Test that guardrail spans have correct attributes."""
    provider, exporter = fresh_tracer

    with create_guardrail_span(
        guardrail_type="cost_limit",
        agent_name="vrs-attacker",
        pool_id="pool-123",
        bead_id="bead-456",
    ):
        pass

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    assert span.name == "guardrail.cost_limit"

    attrs = dict(span.attributes)
    assert attrs["alphaswarm.guardrail.type"] == "cost_limit"
    assert attrs["alphaswarm.agent.name"] == "vrs-attacker"
    assert attrs["alphaswarm.pool.id"] == "pool-123"
    assert attrs["alphaswarm.bead.id"] == "bead-456"


def test_record_input_event_adds_event(fresh_tracer):
    """Test that record_input_event adds event to span."""
    provider, exporter = fresh_tracer

    with create_agent_span("test-agent", "pool-123") as span:
        record_input_event(
            span, "bead_context", metadata={"token_count": 1500, "size_bytes": 8000}
        )

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    events = spans[0].events
    assert len(events) == 1

    event = events[0]
    assert event.name == "input_received"

    attrs = dict(event.attributes)
    assert attrs["event.type"] == "input"
    assert attrs["input.type"] == "bead_context"
    assert attrs["input.token_count"] == 1500
    assert attrs["input.size_bytes"] == 8000


def test_record_output_event_adds_event(fresh_tracer):
    """Test that record_output_event adds event to span."""
    provider, exporter = fresh_tracer

    with create_agent_span("test-agent", "pool-123") as span:
        record_output_event(
            span, "finding", metadata={"verdict": "confirmed", "token_count": 800}
        )

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    events = spans[0].events
    assert len(events) == 1

    event = events[0]
    assert event.name == "output_generated"

    attrs = dict(event.attributes)
    assert attrs["event.type"] == "output"
    assert attrs["output.type"] == "finding"
    assert attrs["output.verdict"] == "confirmed"
    assert attrs["output.token_count"] == 800


def test_record_error_event_adds_event(fresh_tracer):
    """Test that record_error_event adds event to span."""
    provider, exporter = fresh_tracer

    with create_agent_span("test-agent", "pool-123") as span:
        record_error_event(
            span,
            "llm_error",
            "Rate limit exceeded",
            metadata={"retry_count": 3, "backoff_ms": 5000},
        )

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    events = spans[0].events
    assert len(events) == 1

    event = events[0]
    assert event.name == "error_occurred"

    attrs = dict(event.attributes)
    assert attrs["event.type"] == "error"
    assert attrs["error.type"] == "llm_error"
    assert attrs["error.message"] == "Rate limit exceeded"
    assert attrs["error.retry_count"] == 3
    assert attrs["error.backoff_ms"] == 5000


def test_record_llm_usage_sets_attributes(fresh_tracer):
    """Test that record_llm_usage sets GenAI usage attributes."""
    provider, exporter = fresh_tracer

    with create_agent_span("test-agent", "pool-123") as span:
        record_llm_usage(span, input_tokens=1500, output_tokens=800, cost_usd=0.05)

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    attrs = dict(spans[0].attributes)
    assert attrs["gen_ai.usage.input_tokens"] == 1500
    assert attrs["gen_ai.usage.output_tokens"] == 800
    assert attrs["gen_ai.usage.total_tokens"] == 2300
    assert attrs["alphaswarm.usage.cost_usd"] == 0.05


def test_span_error_handling(fresh_tracer):
    """Test that spans properly record exceptions."""
    provider, exporter = fresh_tracer

    with pytest.raises(ValueError, match="Test error"):
        with create_agent_span("test-agent", "pool-123"):
            raise ValueError("Test error")

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    # Check span status is error
    assert span.status.status_code.name == "ERROR"
    assert "Test error" in span.status.description

    # Check exception event was recorded
    events = span.events
    assert len(events) > 0
    # OpenTelemetry records exceptions as events
    exception_events = [e for e in events if "exception" in e.name.lower()]
    assert len(exception_events) > 0


def test_nested_spans(fresh_tracer):
    """Test that nested spans maintain parent-child relationships."""
    provider, exporter = fresh_tracer

    with create_agent_span("test-agent", "pool-123"):
        with create_tool_span("slither", "pool-123"):
            pass

    provider.force_flush()

    spans = exporter.get_finished_spans()
    assert len(spans) == 2

    # Find parent and child
    agent_span = next(s for s in spans if "test-agent" in s.name)
    tool_span = next(s for s in spans if "slither" in s.name)

    # Verify parent-child relationship
    assert tool_span.parent is not None
    assert tool_span.parent.span_id == agent_span.context.span_id
