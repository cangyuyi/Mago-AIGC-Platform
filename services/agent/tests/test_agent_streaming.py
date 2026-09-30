"""Tests for genuine token-level SSE streaming from the agent endpoint.

The endpoint used to buffer: it ran the graph to completion with ``ainvoke``
and only then emitted every frame. That made the "streaming" response arrive in
one burst, so the UI could not show progress or partial output.

The route now drives the graph with ``astream(stream_mode=["updates","custom"])``
and forwards each node delta (and each agent-emitted token chunk) as it lands.
These tests pin that behaviour down at the route and helper level.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import Request

from src.api.routes import agent as agent_route


class _StreamingGraph:
    """Graph double yielding interleaved custom chunks and node updates."""

    def __init__(self, *, interrupt: bool = False) -> None:
        self.interrupt = interrupt
        self.invocations: list[Any] = []

    def get_state(self, _config):
        from types import SimpleNamespace

        return SimpleNamespace(next=("brief_gate",))

    async def astream(self, payload, config=None, stream_mode=None):
        self.invocations.append(payload)
        # Two token chunks, exactly what a streaming storyteller would emit.
        yield "custom", {"type": "chunk", "node": "storyteller", "text": "第一段"}
        yield "custom", {"type": "chunk", "node": "storyteller", "text": "第二段"}
        yield "custom", {"type": "thinking", "node": "storyteller", "text": "正在撰写"}
        script = {
            "title": "口红测评脚本",
            "body_text": "第一段第二段",
            "beats": [{"index": 0, "content": "第一段", "duration_sec": 3.0}],
        }
        yield "updates", {"storyteller": {"script": script, "current_step": "script_complete"}}
        if self.interrupt:
            yield "updates", {
                "__interrupt__": [
                    _make_interrupt(
                        {
                            "gate": "brief_review",
                            "prompt": "请确认创意简报",
                            "payload": {"brief": {"topic": "口红"}},
                        }
                    )
                ]
            }


def _make_interrupt(value: dict) -> Any:
    from langgraph.types import Interrupt

    return Interrupt(value=value)


async def _collect_sse(response) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    raw = b""
    async for chunk in response.body_iterator:
        raw += chunk if isinstance(chunk, bytes) else chunk.encode()
    for record in raw.decode().split("\n\n"):
        if not record.strip():
            continue
        event, data = None, None
        for line in record.splitlines():
            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = line[len("data:") :].strip()
        if event and data is not None:
            if data == "[DONE]":
                continue
            events.append((event, json.loads(data)))
    return events


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/api/v1/agent/run"})


@pytest.mark.asyncio
async def test_route_emits_token_chunks(monkeypatch) -> None:
    """Token chunks from the graph's custom stream must reach the client."""
    fake = _StreamingGraph()
    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_script_studio_graph", lambda **_deps: fake)

    response = await agent_route.run_agent(
        agent_route.ChatRequest(message="口红测评", mode="detailed", project_id="p1"),
        _request(),
    )
    events = await _collect_sse(response)

    chunks = [data["text"] for event, data in events if event == "chunk"]
    assert chunks == ["第一段", "第二段"], f"unexpected chunks: {chunks}"

    # The stream must be ordered: chunks arrive before the node's final output.
    names = [event for event, _ in events]
    assert names.index("chunk") < names.index("script")


@pytest.mark.asyncio
async def test_route_emits_script_from_node_delta(monkeypatch) -> None:
    """A script produced by a node update must be forwarded as a script event."""
    fake = _StreamingGraph()
    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_script_studio_graph", lambda **_deps: fake)

    response = await agent_route.run_agent(
        agent_route.ChatRequest(message="口红测评", mode="quick", project_id="p1"),
        _request(),
    )
    events = await _collect_sse(response)

    script_events = [data for event, data in events if event == "script"]
    assert script_events, "expected a script event"
    assert script_events[0]["script"]["title"] == "口红测评脚本"
    # Provenance travels with generated content so the UI can flag template output.
    assert "llm_configured" in script_events[0]


@pytest.mark.asyncio
async def test_route_reports_interrupt_from_stream(monkeypatch) -> None:
    """An interrupt in the update stream must surface on the done event."""
    fake = _StreamingGraph(interrupt=True)
    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_script_studio_graph", lambda **_deps: fake)

    response = await agent_route.run_agent(
        agent_route.ChatRequest(message="口红测评", mode="detailed", project_id="p1"),
        _request(),
    )
    events = await _collect_sse(response)

    done = next(data for event, data in events if event == "done")
    assert done["state"]["hitl_required"] is True
    assert done["state"]["hitl_node"] == "brief_review"


@pytest.mark.asyncio
async def test_resume_drives_graph_with_command(monkeypatch) -> None:
    """A resume turn must feed a Command into the streaming graph."""
    from langgraph.types import Command

    fake = _StreamingGraph()
    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_script_studio_graph", lambda **_deps: fake)

    response = await agent_route.run_agent(
        agent_route.ChatRequest(
            message="确认",
            mode="detailed",
            project_id="p1",
            resume={"approved": True},
        ),
        _request(),
    )
    await _collect_sse(response)

    assert fake.invocations, "graph should have been invoked"
    assert isinstance(fake.invocations[0], Command)


@pytest.mark.asyncio
async def test_custom_to_sse_ignores_empty_and_forwards_unknown() -> None:
    """Custom payload handling must drop empty chunks but keep unknown types."""
    assert agent_route._custom_to_sse({"type": "chunk", "text": ""}) == []

    forwarded = agent_route._custom_to_sse({"type": "progress", "value": 3})
    assert len(forwarded) == 1
    assert "event: progress" in forwarded[0]

    chunk = agent_route._custom_to_sse({"type": "chunk", "node": "n", "text": "hi"})
    assert "event: chunk" in chunk[0] and "hi" in chunk[0]


@pytest.mark.asyncio
async def test_astream_graph_normalises_pair_and_bare_payload() -> None:
    """The stream normaliser must accept both LangGraph yield shapes."""

    class _PairGraph:
        async def astream(self, *_a, **_k):
            yield ("updates", {"a": 1})

    class _BareGraph:
        async def astream(self, *_a, **_k):
            yield {"b": 2}

    pairs = [item async for item in agent_route._astream_graph(_PairGraph(), {}, {})]
    assert pairs == [("updates", {"a": 1})]

    bare = [item async for item in agent_route._astream_graph(_BareGraph(), {}, {})]
    assert bare == [("updates", {"b": 2})]
