"""OpenTelemetry tracing setup.

Gracefully degrades if opentelemetry packages are not installed.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_tracer = None
_initialized = False


def setup_tracing(
    service_name: str = "mago-agent",
    otlp_endpoint: str | None = None,
    sample_rate: float = 1.0,
) -> Any | None:
    """Initialize OpenTelemetry tracing if packages are available."""
    global _tracer, _initialized
    if _initialized:
        return _tracer

    enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    if not enabled:
        _initialized = True
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.namespace": "mago-platform",
                "deployment.environment": os.getenv("APP_ENV", "development"),
                "service.version": os.getenv("APP_VERSION", "0.1.0"),
            }
        )

        provider = TracerProvider(resource=resource)
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        logger.info("OpenTelemetry tracing initialized")
    except ImportError:
        logger.info("opentelemetry packages not installed, tracing disabled")
        _tracer = None
    except Exception as e:
        logger.warning(f"OpenTelemetry initialization failed: {e}")
        _tracer = None

    _initialized = True
    return _tracer


def get_tracer(name: str | None = None) -> Any | None:
    global _tracer
    if _tracer is None and not _initialized:
        _tracer = setup_tracing()
    if _tracer is None:
        return None
    if name:
        try:
            from opentelemetry import trace

            return trace.get_tracer(name)
        except Exception:
            return _tracer
    return _tracer


def trace_agent_step(step_name: str, attributes: dict[str, Any] | None = None):
    """Context manager to trace an agent step (no-op if tracing not initialized)."""
    tracer = get_tracer()
    if tracer is None:

        class NoopSpan:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def set_attribute(self, *args):
                pass

        return NoopSpan()
    return tracer.start_as_current_span(f"agent.{step_name}", attributes=attributes or {})
