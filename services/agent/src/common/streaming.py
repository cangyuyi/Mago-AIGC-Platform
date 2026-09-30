"""Helpers for pushing token-level progress out of LangGraph nodes.

LangGraph exposes ``get_stream_writer()`` inside a running node: anything the
node writes appears on the graph's ``custom`` stream. The agent API consumes
that stream and turns each payload into an SSE frame, so a node can report
progress (or partial model output) the moment it happens instead of buffering
the whole node result.

The helpers are deliberately fail-safe: calling them outside a LangGraph run
(e.g. in a unit test that invokes an agent directly) must never raise, because
streaming is a transport concern and must not break the business logic.
"""

from __future__ import annotations

from typing import Any

from src.common.logger import get_logger

logger = get_logger(__name__)


def _writer() -> Any | None:
    """Return the active LangGraph stream writer, or ``None`` outside a run."""
    try:  # Imported lazily so the module stays importable on older LangGraph.
        from langgraph.config import get_stream_writer
    except Exception:  # pragma: no cover - dependency missing
        return None
    try:
        return get_stream_writer()
    except Exception:
        # get_stream_writer() raises when there is no active run context.
        return None


def emit(payload: dict[str, Any]) -> None:
    """Write one custom payload to the active graph stream, if any."""
    writer = _writer()
    if writer is None:
        return
    try:
        writer(payload)
    except Exception:  # pragma: no cover - transport errors must not abort a node
        logger.debug("stream_emit_failed", payload_type=payload.get("type"))


def emit_chunk(node: str, text: str) -> None:
    """Forward a slice of model output as it is produced."""
    if not text:
        return
    emit({"type": "chunk", "node": node, "text": text})


def emit_thinking(node: str, text: str) -> None:
    """Publish a short progress/status line for the UI."""
    if not text:
        return
    emit({"type": "thinking", "node": node, "text": text})
