"""Regression tests for the human-in-the-loop (HITL) pause/resume contract.

An earlier implementation "paused" by returning ``END`` from a conditional
edge. That terminated the graph instead of suspending it: the follow-up message
restarted the run from ``START`` and advanced exactly one node, so a detailed
run needed one round-trip per gate and the checkpoint was never reused.

The graphs now suspend with LangGraph's ``interrupt()`` and continue from the
same node through ``Command(resume=...)``. These tests lock in that behaviour.

Every pipeline agent is stubbed so the tests exercise the *graph* (pause/resume
and checkpoint wiring) rather than any LLM provider.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.types import Command

from src.core.checkpoint import reset_checkpointer_cache
from src.core.graph import build_full_graph, build_script_studio_graph


class _StubAgent:
    """Minimal agent returning a fixed state fragment (optionally dynamic)."""

    def __init__(self, updates: dict[str, Any] | None = None, *, fn: Any = None) -> None:
        self._updates = updates or {}
        self._fn = fn

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        if self._fn is not None:
            return self._fn(state)
        return dict(self._updates)


def _steps(*names: str) -> dict[str, Any]:
    return {"steps_completed": list(names)}


def _stub_deps() -> dict[str, Any]:
    """Agents that return just enough state for the graph to run to export."""

    def brief(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "creative_brief": {"topic": "口红测评", "needs_character": False},
            "steps_completed": state.get("steps_completed", []) + ["brief"],
        }

    def style(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "style": {"style_name": "test"},
            "steps_completed": state.get("steps_completed", []) + ["style"],
        }

    def hooks(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "hooks": [{"text": "hook"}],
            "steps_completed": state.get("steps_completed", []) + ["hooks"],
        }

    def script(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "script": {"shots": [{"text": "shot"}], "content": "script"},
            "steps_completed": state.get("steps_completed", []) + ["script"],
        }

    def evaluate(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "evaluation": {"overall_score": 9.0, "iteration_notes": ""},
            "eval_passed": True,
            "steps_completed": state.get("steps_completed", []) + ["evaluate"],
        }

    def compliance(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "compliance_result": {"passed": True},
            "steps_completed": state.get("steps_completed", []) + ["compliance"],
        }

    def rhythm(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "rhythm_notes": "ok",
            "steps_completed": state.get("steps_completed", []) + ["rhythm"],
        }

    def storyboard(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "storyboard": {
                "shots": [
                    {"shot_type": "close-up", "text": "s1"},
                    {"shot_type": "wide", "text": "s2"},
                    {"shot_type": "medium", "text": "s3"},
                ]
            },
            "steps_completed": state.get("steps_completed", []) + ["storyboard"],
        }

    def prompt(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "prompt_package": {
                "shots": [
                    {"prompts": {"midjourney": "a sufficiently long prompt for validation purposes"}},
                    {"prompts": {"midjourney": "another sufficiently long prompt for validation purposes"}},
                ]
            },
            "steps_completed": state.get("steps_completed", []) + ["prompt_generation"],
        }

    return {
        "brief_agent": _StubAgent(fn=brief),
        "style_agent": _StubAgent(fn=style),
        "hooks_agent": _StubAgent(fn=hooks),
        "storyteller_agent": _StubAgent(fn=script),
        "evaluator_agent": _StubAgent(fn=evaluate),
        "compliance_agent": _StubAgent(fn=compliance),
        "rhythm_agent": _StubAgent(fn=rhythm),
        "storyboard_agent": _StubAgent(fn=storyboard),
        "prompt_agent": _StubAgent(fn=prompt),
    }


def _fresh_graph():
    """Build a stubbed graph on a clean checkpointer (no thread leakage)."""
    reset_checkpointer_cache()
    return build_full_graph(**_stub_deps())


def _initial_state(mode: str) -> dict[str, Any]:
    return {
        "project_id": "hitl-test",
        "user_id": "tester",
        "run_id": "run-1",
        "mode": mode,
        "messages": [],
        "current_input": "口红测评",
        "current_step": "starting",
        "steps_completed": [],
        "events": [],
    }


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


@pytest.mark.asyncio
async def test_detailed_mode_pauses_at_idea_gate() -> None:
    """The first detailed turn must suspend with an interrupt, not finish."""
    graph = _fresh_graph()
    cfg = _config("detail-pause")

    result = await graph.ainvoke(_initial_state("detailed"), config=cfg)

    interrupts = result.get("__interrupt__")
    assert interrupts, "detailed mode should pause at the idea-selection gate"
    gate = interrupts[0].value
    assert gate["gate"] == "idea_selection"
    assert gate["payload"]["ideas"], "the pause must carry the candidate ideas"

    # The checkpoint must remember where it stopped so a resume is possible.
    assert graph.get_state(cfg).next, "a paused run must have a pending node"


@pytest.mark.asyncio
async def test_resume_advances_past_the_gate_and_keeps_going() -> None:
    """Resuming with a choice continues the pipeline beyond the gate.

    The old END-based pause advanced exactly one node per message; a resume must
    instead carry the run forward (ideation -> brief -> style -> ...).
    """
    graph = _fresh_graph()
    cfg = _config("detail-resume")

    paused = await graph.ainvoke(_initial_state("detailed"), config=cfg)
    ideas = paused["__interrupt__"][0].value["payload"]["ideas"]
    chosen_id = ideas[0]["id"]

    resumed = await graph.ainvoke(
        Command(resume={"selected_idea_id": chosen_id, "approved": True}),
        config=cfg,
    )

    steps = set(resumed.get("steps_completed", []))
    # The run must progress past idea selection and through the brief in a
    # single resume, then pause at the next review gate.
    assert "idea_selected" in steps, f"resume should select an idea, got {sorted(steps)}"
    assert "brief" in steps, f"resume should reach the brief step, got {sorted(steps)}"
    assert resumed["__interrupt__"][0].value["gate"] == "brief_review"


@pytest.mark.asyncio
async def test_idea_approval_advances_to_the_next_gate() -> None:
    """One resume carries the run to the *next* gate, not one node further.

    This is the core regression: the old END-based pause restarted the graph and
    advanced a single node, so reaching the brief gate from ideation needed
    several messages. Resuming at the idea gate must instead advance the run all
    the way to the brief gate in one shot.
    """
    graph = _fresh_graph()
    cfg = _config("detail-next-gate")

    paused = await graph.ainvoke(_initial_state("detailed"), config=cfg)
    chosen_id = paused["__interrupt__"][0].value["payload"]["ideas"][0]["id"]

    resumed = await graph.ainvoke(
        Command(resume={"selected_idea_id": chosen_id}),
        config=cfg,
    )

    steps = set(resumed.get("steps_completed", []))
    # ideation + idea_selected + brief all happened, then it paused at brief_review.
    assert {"idea_selected", "brief"} <= steps, f"expected to reach the brief gate, got {sorted(steps)}"
    interrupts = resumed.get("__interrupt__")
    assert interrupts, "the run should pause at the next gate (brief review)"
    assert interrupts[0].value["gate"] == "brief_review"
    assert graph.get_state(cfg).next, "the run is paused, not finished"


@pytest.mark.asyncio
async def test_repeated_approvals_finish_the_run() -> None:
    """Approving each gate in turn drives the detailed run to export."""
    graph = _fresh_graph()
    cfg = _config("detail-complete")
    state = _initial_state("detailed")

    result = await graph.ainvoke(state, config=cfg)
    assert result["__interrupt__"][0].value["gate"] == "idea_selection"
    chosen_id = result["__interrupt__"][0].value["payload"]["ideas"][0]["id"]

    # Approve the idea gate, then each subsequent review gate until finished.
    result = await graph.ainvoke(Command(resume={"selected_idea_id": chosen_id}), config=cfg)
    for _ in range(6):
        interrupts = result.get("__interrupt__")
        if not interrupts:
            break
        result = await graph.ainvoke(Command(resume={"approved": True}), config=cfg)

    assert "export_ready" in result.get("steps_completed", []), "the run should finish after approvals"
    assert not graph.get_state(cfg).next, "a completed run must have no pending node"


@pytest.mark.asyncio
async def test_quick_mode_never_interrupts() -> None:
    """Quick mode is autonomous: it must run to completion without a pause."""
    graph = _fresh_graph()
    cfg = _config("quick-run")

    result = await graph.ainvoke(_initial_state("quick"), config=cfg)

    assert not result.get("__interrupt__"), "quick mode must not pause for approval"
    assert not graph.get_state(cfg).next, "a finished quick run has no pending node"


@pytest.mark.asyncio
async def test_script_studio_graph_pauses_for_idea_selection() -> None:
    """The lighter Script Studio funnel pauses the same way."""
    reset_checkpointer_cache()
    graph = build_script_studio_graph(**_stub_deps())
    cfg = _config("studio-pause")

    result = await graph.ainvoke(_initial_state("detailed"), config=cfg)

    interrupts = result.get("__interrupt__")
    assert interrupts, "script studio should pause at the idea gate"
    assert interrupts[0].value["gate"] == "idea_selection"


# ---------------------------------------------------------------------------
# Route-level integration: the SSE endpoint must surface and consume gates.
# ---------------------------------------------------------------------------


async def _collect_sse(response) -> list[tuple[str, dict]]:
    """Parse an SSE response body into (event, data) tuples."""
    events: list[tuple[str, dict]] = []
    raw = b""
    async for chunk in response.body_iterator:
        raw += chunk if isinstance(chunk, bytes) else chunk.encode()
    for record in raw.decode().split("\n\n"):
        event, data = None, None
        for line in record.splitlines():
            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data = line[len("data:") :].strip()
        if event and data:
            import json as _json

            events.append((event, _json.loads(data)))
    return events


class _FakeRouteGraph:
    """A graph double that records how the route invoked it.

    The route now drives the graph with ``astream(stream_mode=[...])`` rather
    than ``ainvoke``, so the double yields ``(mode, payload)`` pairs the same way
    LangGraph does.
    """

    def __init__(self, *, interrupts: list | None = None, chunks: list[str] | None = None) -> None:
        self._interrupts = interrupts
        self._chunks = chunks or []
        self.invocations: list[object] = []

    def get_state(self, _config):
        from types import SimpleNamespace

        return SimpleNamespace(next=("idea_gate",))

    async def astream(self, payload, config=None, stream_mode=None):
        self.invocations.append(payload)
        for chunk in self._chunks:
            yield "custom", {"type": "chunk", "node": "storyteller", "text": chunk}
        delta: dict = {
            "steps_completed": ["ideation"],
            "current_step": "awaiting_idea",
            "creative_ideas": [{"id": "idea001", "title": "t", "description": "d"}],
        }
        if self._interrupts:
            yield "updates", {"__interrupt__": self._interrupts}
        yield "updates", {"ideation": delta}


@pytest.mark.asyncio
async def test_route_reports_pending_gate_on_done(monkeypatch) -> None:
    """A paused detailed run must surface hitl_required + the gate name."""
    from fastapi import Request
    from langgraph.types import Interrupt

    from src.api.routes import agent as agent_route

    interrupt = Interrupt(
        value={
            "gate": "idea_selection",
            "prompt": "请选择一个创意方向继续",
            "mode": "approval",
            "payload": {"ideas": [{"id": "idea001"}]},
        }
    )
    fake = _FakeRouteGraph(interrupts=[interrupt])
    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_script_studio_graph", lambda **_deps: fake)

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/agent/run"})
    response = await agent_route.run_agent(
        agent_route.ChatRequest(message="口红测评", mode="detailed", project_id="p1"),
        request,
    )
    events = await _collect_sse(response)

    done = next(data for event, data in events if event == "done")
    assert done["state"]["hitl_required"] is True
    assert done["state"]["hitl_node"] == "idea_selection"
    assert done["state"]["hitl_prompt"]


@pytest.mark.asyncio
async def test_route_resumes_with_command(monkeypatch) -> None:
    """A resume request must invoke the graph with a Command(resume=...)."""
    from fastapi import Request
    from langgraph.types import Command

    from src.api.routes import agent as agent_route

    fake = _FakeRouteGraph()
    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_script_studio_graph", lambda **_deps: fake)

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/agent/run"})
    response = await agent_route.run_agent(
        agent_route.ChatRequest(
            message="就用第一个",
            mode="detailed",
            project_id="p1",
            resume={"selected_idea_id": "idea001"},
        ),
        request,
    )
    await _collect_sse(response)

    assert fake.invocations, "the graph should have been invoked"
    first = fake.invocations[0]
    assert isinstance(first, Command), f"expected a Command resume, got {type(first)}"
