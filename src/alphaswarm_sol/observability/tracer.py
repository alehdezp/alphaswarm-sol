"""OpenTelemetry tracer setup with GenAI semantic conventions.

This module provides tracer initialization and configuration following
OpenTelemetry GenAI semantic conventions v1.37+.
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from alphaswarm_sol import __version__


def setup_tracing(
    service_name: str = "alphaswarm",
    endpoint: Optional[str] = None,
    environment: Optional[str] = None,
) -> trace.Tracer:
    """Initialize OpenTelemetry tracing with GenAI semantic conventions.

    Args:
        service_name: Name of the service (default: "alphaswarm")
        endpoint: OTLP endpoint URL (e.g., "http://localhost:4318/v1/traces").
                 If None, uses ConsoleSpanExporter for development.
        environment: Deployment environment (default: reads from DEPLOYMENT_ENV or "development")

    Returns:
        Configured Tracer instance

    Example:
        >>> tracer = setup_tracing()
        >>> tracer = setup_tracing(endpoint="http://localhost:4318/v1/traces", environment="production")
    """
    # Determine environment
    if environment is None:
        environment = os.getenv("DEPLOYMENT_ENV", "development")

    # Create resource with service metadata
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": __version__,
            "deployment.environment": environment,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporter based on endpoint
    if endpoint:
        # Production: OTLP exporter
        exporter = OTLPSpanExporter(endpoint=endpoint)
    else:
        # Development: console exporter
        exporter = ConsoleSpanExporter()

    # Use BatchSpanProcessor for efficiency
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Return tracer instance
    return get_tracer()


def get_tracer(name: str = "alphaswarm.orchestration") -> trace.Tracer:
    """Get tracer from global provider.

    Args:
        name: Tracer name (default: "alphaswarm.orchestration")

    Returns:
        Tracer instance

    Example:
        >>> tracer = get_tracer()
        >>> tracer = get_tracer("alphaswarm.tools")
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """Force flush and shutdown tracer provider.

    Call this before application exit to ensure all spans are exported.

    Example:
        >>> shutdown_tracing()
    """
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
