"""Observability module: Langfuse LLM tracing + OpenTelemetry.

Gracefully degrades if optional dependencies are not installed.
"""

from __future__ import annotations

from typing import Any

# Tracing (OpenTelemetry) - optional dependency
try:
    from .tracing import get_tracer, setup_tracing
except ImportError:

    def setup_tracing(
        service_name: str = "mago-agent-service",
        otlp_endpoint: str | None = None,
        sample_rate: float = 1.0,
    ) -> Any | None:
        return None

    def get_tracer(name: str | None = None) -> Any | None:
        return None


# Langfuse - optional dependency
try:
    from .langfuse_setup import flush_langfuse, get_langfuse_callback, langfuse_client, setup_langfuse
except ImportError:

    def setup_langfuse() -> Any | None:
        return None

    def langfuse_client() -> Any | None:
        return None

    def get_langfuse_callback() -> Any | None:
        return None

    def flush_langfuse() -> None:
        return None


__all__ = [
    "setup_tracing",
    "get_tracer",
    "setup_langfuse",
    "langfuse_client",
    "get_langfuse_callback",
    "flush_langfuse",
]
