"""Agent interaction endpoints with SSE streaming.

Supports all pipeline modes:
- echo: Simple test echo
- ideation: Only generate creative ideas
- script_studio/quick/detailed: Ideation -> script -> storyboard pipeline
- full: Complete end-to-end pipeline (trend -> ideation -> brief -> character -> style -> hooks -> script -> eval -> compliance -> rhythm -> storyboard -> prompt -> export)
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any, Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.agents.character.agent import CharacterAgent
from src.agents.echo import EchoAgent
from src.agents.ideation import IdeationAgent
from src.agents.prompt.prompt_engine_agent import PromptEngineAgent
from src.agents.script import (
    ComplianceAgent,
    CreativeBriefAgent,
    EvaluatorAgent,
    HookSpecialistAgent,
    RhythmOptimizerAgent,
    StoryboardAgent,
    StorytellerAgent,
)
from src.agents.style.agent import StyleAgent
from src.agents.topic_recommender.agent import TopicRecommenderAgent
from src.agents.trend_analyzer.agent import TrendAnalyzerAgent
from src.common.logger import get_logger
from src.config import get_settings
from src.core.graph import (
    build_echo_graph,
    build_full_graph,
    build_ideation_graph,
    build_script_studio_graph,
)
from src.llm.gateway import LLMGateway, get_llm_gateway
from src.prompt_engine.generator import generate_package, get_model_list

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])
logger = get_logger(__name__)


@router.get("/health")
async def agent_health():
    """Return a lightweight health response for the agent API namespace."""
    return {"agent": "running"}


class ChatRequest(BaseModel):
    """A chat turn, optionally resuming a paused human-in-the-loop run.

    When a run paused at an ``interrupt``, the client answers by sending the
    same ``project_id``/``mode`` and setting ``resume`` (or ``approved`` /
    ``selected_idea_id`` / ``feedback``, which are folded into a resume value).
    The server then continues the stored checkpoint instead of starting over.
    """

    message: str = Field("", description="User message text")
    project_id: str | None = None
    mode: Literal["echo", "ideation", "script", "quick", "detailed", "full"] = Field(
        default="ideation", description="echo/ideation/script/quick/detailed/full"
    )
    action: str | None = None
    selected_idea_id: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    style_ids: list[str] = Field(default_factory=list)
    target_models: list[str] = Field(default_factory=list)
    approved: bool = False
    feedback: str | None = None
    resume: Any | None = Field(
        default=None,
        description="Explicit resume value for a paused run (bool, id, or object).",
    )
    resume_from: str | None = Field(default=None, description="Gate name to resume, for clients that track it.")
    rejected: bool = Field(default=False, description="Set when the human declines the pending step.")
    history: list[dict[str, Any]] = Field(default_factory=list)

    def resume_value(self) -> Any | None:
        """Collapse the shorthand fields into a single HITL resume value.

        Returns ``None`` when this turn is not a resume (i.e. a fresh run).
        """
        if self.resume is not None:
            return self.resume
        if self.rejected:
            return {"approved": False, "gate": self.resume_from}
        if self.approved:
            return {"approved": True, "gate": self.resume_from}
        if self.selected_idea_id:
            return {"selected_idea_id": self.selected_idea_id, "gate": self.resume_from}
        if self.feedback:
            return {"feedback": self.feedback, "approved": True, "gate": self.resume_from}
        return None

    def is_resume(self) -> bool:
        return self.resume_value() is not None


def _provenance(llm: LLMGateway) -> dict[str, Any]:
    """Describe what actually produced an answer.

    Without this the UI cannot tell a real model generation from the offline
    template fallback, so users would paste template copy into production.
    """
    configured = bool(getattr(llm, "is_configured", False))
    settings = getattr(llm, "settings", None)
    model = str(getattr(settings, "default_model", "") or "") if configured else ""
    return {"llm_configured": configured, "model": model}


def _sse(event: str, data: dict[str, Any]) -> str:
    """Format Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _validate_project_access(request: Request, project_id: str | None) -> None:
    """Validate that the authenticated user owns the requested project.

    The web app can reach this service directly through a Next.js rewrite, so
    relying only on the Go gateway's project checks would leave a production
    bypass. In local/demo mode authentication is intentionally disabled; in
    authenticated mode the same bearer token is checked by the gateway.
    """
    if not project_id:
        return

    settings = get_settings()
    if not settings.agent_auth_enabled:
        # Development mode has no verified identity or gateway token to use.
        # Production deployments must enable AGENT_AUTH_ENABLED.
        return

    from uuid import UUID

    try:
        UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid project_id") from exc

    authorization = request.headers.get("Authorization", "")
    if not getattr(request.state, "user_id", None) or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication is required for project-scoped runs")

    base_url = settings.mago_api_url.rstrip("/")
    headers = {"Authorization": authorization}
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        headers["X-Request-ID"] = request_id

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/v1/projects/{project_id}", headers=headers)
    except httpx.HTTPError as exc:
        logger.error("project_access_validation_unavailable", project_id=project_id, error=str(exc))
        raise HTTPException(status_code=503, detail="project access validation is unavailable") from exc

    if response.status_code in {401, 403, 404}:
        # Do not disclose whether an inaccessible project exists.
        raise HTTPException(status_code=404, detail="project not found")
    if response.status_code >= 500:
        logger.error(
            "project_access_validation_failed",
            project_id=project_id,
            status_code=response.status_code,
        )
        raise HTTPException(status_code=503, detail="project access validation failed")
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="project access validation rejected the request")


class PromptPackRequest(BaseModel):
    """On-demand prompt-pack generation from an existing storyboard."""

    storyboard: dict[str, Any] = Field(..., description="Storyboard dict containing shots[]")
    script: dict[str, Any] | None = None
    characters: list[dict[str, Any]] = Field(default_factory=list)
    style: dict[str, Any] | None = None
    target_models: list[str] = Field(default_factory=list)
    project_id: str | None = None


MAX_PROMPT_PACK_SHOTS = 200


@router.get("/prompt-models")
async def list_prompt_models() -> dict[str, Any]:
    """Return the models the prompt engine can write prompts for."""
    return {"models": get_model_list()}


@router.post("/prompt-pack")
async def create_prompt_pack(req: PromptPackRequest, request: Request) -> dict[str, Any]:
    """Turn a storyboard into per-model generation prompts.

    The prompt engine is a deterministic template layer: it needs no LLM key
    and spends no model credit, so it is exposed as its own endpoint instead
    of being buried at the tail of the ``full`` pipeline where the UI cannot
    reach it.
    """
    await _validate_project_access(request, req.project_id)

    shots = req.storyboard.get("shots")
    if not isinstance(shots, list) or not shots:
        raise HTTPException(status_code=422, detail="分镜表为空，请先生成分镜表")
    if len(shots) > MAX_PROMPT_PACK_SHOTS:
        raise HTTPException(
            status_code=422,
            detail=f"分镜数量超过上限 {MAX_PROMPT_PACK_SHOTS}，当前 {len(shots)}",
        )

    unusable = [
        str(shot.get("index", position + 1))
        for position, shot in enumerate(shots)
        if not isinstance(shot, dict)
        or not (
            str(shot.get("visual_description") or "").strip()
            or (
                str(shot.get("subject_description") or "").strip()
                and str(shot.get("scene_description") or "").strip()
            )
        )
    ]
    if unusable:
        raise HTTPException(
            status_code=422,
            detail="第 " + ", ".join(unusable) + " 号镜头缺少画面描述，生成的提示词会是无意义占位文本，请补全分镜后重试",
        )

    known = [str(m["model_id"]) for m in get_model_list()]
    unknown = [m for m in req.target_models if m not in known]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail="不支持的模型: " + ", ".join(unknown) + "；可用模型: " + ", ".join(known),
        )
    target_models = req.target_models or known[:3]

    package = generate_package(
        storyboard=req.storyboard,
        script=req.script,
        characters=req.characters,
        style=req.style,
        target_models=target_models,
    )
    if not package.get("prompts"):
        raise HTTPException(
            status_code=422,
            detail="未能从分镜生成任何提示词，请检查分镜字段（画面描述/景别/运镜）是否完整",
        )

    logger.info(
        "prompt_pack_generated",
        shots=package.get("total_shots"),
        prompts=len(package["prompts"]),
        models=len(target_models),
    )
    return {
        "package": package,
        "generated_by": "prompt_engine_template",
        "available_models": known,
        "llm_configured": False,
    }


@router.post("/run")
async def run_agent(req: ChatRequest, request: Request):
    """SSE streaming endpoint for all agent interactions.

    Events: meta, thinking, node, idea, brief, characters, style, hooks, script,
            eval, compliance, rhythm, storyboard, prompt, export, done, error

    The graph is driven with ``astream(stream_mode=["updates","custom"])`` so
    every node's output is pushed to the client the moment it finishes instead
    of being buffered until the whole run completes. ``custom`` mode carries the
    token-level chunks emitted by agents through ``get_stream_writer()``.
    """
    run_id = str(uuid4())
    await _validate_project_access(request, req.project_id)
    logger.info("agent_run_started", run_id=run_id, mode=req.mode, project_id=req.project_id)

    llm = get_llm_gateway()

    # Build appropriate graph based on mode
    if req.mode == "echo":
        graph = build_echo_graph(EchoAgent(llm=llm))
    elif req.mode == "full":
        graph = build_full_graph(
            ideation_agent=IdeationAgent(llm=llm),
            trend_agent=TrendAnalyzerAgent(llm_gateway=llm),
            topic_agent=TopicRecommenderAgent(llm_gateway=llm),
            brief_agent=CreativeBriefAgent(llm=llm),
            character_agent=CharacterAgent(llm=llm),
            style_agent=StyleAgent(llm=llm),
            hooks_agent=HookSpecialistAgent(llm=llm),
            storyteller_agent=StorytellerAgent(llm=llm),
            storyboard_agent=StoryboardAgent(llm=llm),
            evaluator_agent=EvaluatorAgent(llm=llm),
            compliance_agent=ComplianceAgent(llm=llm),
            rhythm_agent=RhythmOptimizerAgent(llm=llm),
            prompt_agent=PromptEngineAgent(llm=llm),
        )
    elif req.mode in ("quick", "detailed", "script"):
        graph = build_script_studio_graph(
            ideation_agent=IdeationAgent(llm=llm),
            brief_agent=CreativeBriefAgent(llm=llm),
            hooks_agent=HookSpecialistAgent(llm=llm),
            storyteller_agent=StorytellerAgent(llm=llm),
            storyboard_agent=StoryboardAgent(llm=llm),
            evaluator_agent=EvaluatorAgent(llm=llm),
            compliance_agent=ComplianceAgent(llm=llm),
            rhythm_agent=RhythmOptimizerAgent(llm=llm),
        )
    else:  # ideation (default)
        graph = build_ideation_graph(IdeationAgent(llm=llm))

    async def event_generator():
        provenance = _provenance(llm)
        yield _sse("meta", {"run_id": run_id, "mode": req.mode, "timestamp": time.time(), **provenance})

        try:
            initial_state: dict[str, Any] = {
                "project_id": req.project_id or "",
                "user_id": str(getattr(request.state, "user_id", None) or "anonymous"),
                "run_id": run_id,
                "mode": req.mode,
                "messages": req.history,
                "current_input": req.message,
                "current_step": "starting",
                "steps_completed": [],
                "events": [],
            }

            # Non-gate inputs that apply to both fresh runs and resumes.
            if req.character_ids:
                initial_state["character_ids"] = req.character_ids
            if req.style_ids:
                initial_state["style_ids"] = req.style_ids
            if req.target_models:
                initial_state["target_models"] = req.target_models

            # Scope checkpoints by both authenticated user and project. Using only
            # project_id lets two users who know the same ID share a checkpointer
            # thread, which can leak prior workflow state across accounts.
            thread_subject = str(getattr(request.state, "user_id", None) or "anonymous")
            thread_id = f"{thread_subject}:{req.project_id or run_id}"
            config = {"configurable": {"thread_id": thread_id}}

            resume_value = req.resume_value()
            is_resume = resume_value is not None
            if is_resume:
                paused = graph.get_state(config)
                if not paused.next:
                    # Nothing to resume: no checkpoint for this thread, or the
                    # run already finished. Fall back to a fresh run rather than
                    # silently replaying an old answer.
                    logger.info("resume_without_pending_checkpoint", run_id=run_id)
                    is_resume = False

            if is_resume:
                # A bare approval also satisfies the downstream review gates, so
                # the pipeline can finish without one round-trip per gate.
                if isinstance(resume_value, dict) and resume_value.get("approved") is True:
                    initial_state["brief_approved"] = True
                    initial_state["script_approved"] = True
                    initial_state["storyboard_approved"] = True
                yield _sse("thinking", {"node": "resume", "text": "正在继续上一次创作流程..."})
                graph_input: Any = Command(resume=resume_value)
            else:
                # Fresh run: honour explicit approvals/selection sent up front.
                if req.approved:
                    initial_state["brief_approved"] = True
                    initial_state["script_approved"] = True
                    initial_state["storyboard_approved"] = True
                if req.selected_idea_id:
                    initial_state["selected_idea_id"] = req.selected_idea_id
                if req.feedback:
                    initial_state["user_modifications"] = req.feedback

                yield _sse("thinking", {"node": "start", "text": "正在启动创意工作流..."})
                graph_input = initial_state

            # --- Drive the graph and forward each node's output as it lands ---
            emitted: set[str] = set()
            final_state: dict[str, Any] = {}
            pending_gate: dict[str, Any] | None = None
            step_count = 0

            async for stream_mode, payload in _astream_graph(graph, graph_input, config):
                if stream_mode == "custom":
                    # Token-level chunks forwarded by agents via the stream writer.
                    if isinstance(payload, dict):
                        for event in _custom_to_sse(payload):
                            yield event
                    continue

                # stream_mode == "updates": payload is {node_name: state_delta}
                if not isinstance(payload, dict):
                    continue
                if "__interrupt__" in payload:
                    pending_gate = _pending_gate(payload.get("__interrupt__"))
                    continue
                for node, delta in payload.items():
                    if not isinstance(delta, dict):
                        continue
                    final_state.update(delta)
                    step_count += 1
                    async for event in _forward_node_output(node, delta, emitted, provenance):
                        yield event

            result = final_state
            yield _sse("thinking", {"node": "graph", "text": f"工作流完成，共执行 {step_count} 个节点"})

            # A pause surfaces as "__interrupt__" in the update stream. Report
            # the pending gate so the client can render the right prompt.
            if pending_gate is None and resume_value is None:
                pending_gate = _pending_gate_from_state(result)

            steps = result.get("steps_completed", [])
            yield _sse(
                "done",
                {
                    "run_id": run_id,
                    "state": {
                        "current_step": result.get("current_step", "done"),
                        "steps_completed": steps,
                        "hitl_required": pending_gate is not None,
                        "hitl_node": (pending_gate or {}).get("gate", ""),
                        "hitl_prompt": (pending_gate or {}).get("prompt", ""),
                        "hitl_payload": (pending_gate or {}).get("payload", {}),
                        "has_trend": bool(result.get("trend_summary")),
                        "has_ideas": bool(result.get("creative_ideas")),
                        "has_brief": bool(result.get("creative_brief")),
                        "has_characters": bool(result.get("characters")),
                        "has_style": bool(result.get("style")),
                        "has_script": bool(result.get("script")),
                        "has_storyboard": bool(result.get("storyboard")),
                        "has_prompt": bool(result.get("prompt_package")),
                        "export_ready": result.get("export_ready", False),
                    },
                },
            )
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            logger.info("agent_run_cancelled", run_id=run_id)
            yield _sse("error", {"error": "cancelled", "message": "请求被取消"})
        except Exception as e:
            logger.error("agent_run_error", run_id=run_id, error=str(e), exc_info=True)
            yield _sse("error", {"error": "agent_failed", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _astream_graph(graph: Any, graph_input: Any, config: dict[str, Any]) -> AsyncIterator[tuple[str, Any]]:
    """Yield ``(stream_mode, payload)`` pairs from a graph run.

    ``stream_mode=["updates", "custom"]`` gives us node-level deltas *and* the
    custom chunks agents emit through ``get_stream_writer()``. Some LangGraph
    versions yield a single list/tuple per step instead of a pair, so both
    shapes are normalised here.
    """
    async for item in graph.astream(graph_input, config=config, stream_mode=["updates", "custom"]):
        if isinstance(item, (tuple, list)) and len(item) == 2:
            mode, payload = item[0], item[1]
        else:
            mode, payload = "updates", item
        yield str(mode), payload


def _custom_to_sse(payload: dict[str, Any]) -> list[str]:
    """Convert an agent-emitted custom chunk into one or more SSE frames."""
    kind = payload.get("type")
    if kind == "chunk":
        text = payload.get("text") or ""
        if not text:
            return []
        return [_sse("chunk", {"text": text, "node": payload.get("node", "")})]
    if kind == "thinking":
        return [_sse("thinking", {"node": payload.get("node", ""), "text": payload.get("text", "")})]
    # Unknown custom payloads are still forwarded so future agents can extend
    # the protocol without a server change.
    return [_sse(str(kind or "custom"), payload)]


async def _forward_node_output(
    node: str,
    delta: dict[str, Any],
    emitted: set[str],
    provenance: dict[str, Any],
) -> AsyncIterator[str]:
    """Translate one node's state delta into SSE frames.

    Only keys that have not been emitted yet are sent, so a node that preserves
    an earlier field does not spam the client with duplicates.
    """

    def take(key: str) -> Any | None:
        if key in delta and delta[key] and key not in emitted:
            emitted.add(key)
            return delta[key]
        return None

    yield _sse("node", {"node": node})

    trend_summary = take("trend_summary")
    if trend_summary:
        yield _sse("thinking", {"node": "trend", "text": "热点研究完成"})
    topics = take("topic_recommendations")
    if topics:
        yield _sse("topics", {"topics": topics})

    ideas = take("creative_ideas")
    if ideas:
        yield _sse("thinking", {"node": "ideation", "text": f"创意发散完成，为你生成了{len(ideas)}个方向"})
        yield _sse("ideas", {"ideas": ideas})

    brief = take("creative_brief")
    if brief:
        yield _sse("brief", {"brief": brief})
        yield _sse("thinking", {"node": "brief", "text": "创意简报已生成"})

    characters = take("characters")
    if characters:
        yield _sse("characters", {"characters": characters})
        yield _sse("thinking", {"node": "character", "text": f"角色设计完成，{len(characters)}个角色"})

    style = take("style")
    if style:
        yield _sse("style", {"style": style})
        yield _sse("thinking", {"node": "style", "text": "风格设定完成"})

    script = take("script")
    if script:
        yield _sse("script", {"script": script, **provenance})
        yield _sse("thinking", {"node": "script", "text": "脚本初稿完成"})

    evaluation = take("evaluation")
    if evaluation:
        yield _sse("eval", {"evaluation": evaluation})

    compliance = take("compliance_result")
    if compliance:
        yield _sse("compliance", {"compliance": compliance})

    rhythm = take("rhythm_result")
    if rhythm:
        yield _sse("thinking", {"node": "rhythm", "text": "节奏优化完成"})

    storyboard = take("storyboard")
    if storyboard:
        yield _sse("storyboard", {"storyboard": storyboard, **provenance})
        shot_count = storyboard.get("shot_count", len(storyboard.get("shots", [])))
        yield _sse("thinking", {"node": "storyboard", "text": f"分镜表完成，共{shot_count}个镜头"})

    prompt_pkg = take("prompt_package")
    if prompt_pkg:
        yield _sse("prompt", {"prompt_package": prompt_pkg})
        shots_count = len(prompt_pkg.get("shots", [])) if isinstance(prompt_pkg, dict) else 0
        yield _sse("thinking", {"node": "prompt", "text": f"提示词包生成完成，{shots_count}个镜头"})

    export_data = take("export_data")
    if export_data:
        yield _sse("export", {"export": export_data})


def _pending_gate_from_state(result: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort recovery of a pending gate carried on the final state.

    ``astream`` normally surfaces interrupts through the ``updates`` stream, but
    when a graph ends on a gate the writer may also leave ``hitl_required`` and
    ``hitl_node`` set on the state. This keeps the done event accurate in that
    case.
    """
    if not result.get("hitl_required"):
        return None
    gate = result.get("hitl_node")
    if not gate:
        return None
    return {"gate": gate, "prompt": result.get("hitl_prompt", ""), "payload": {}}


def _pending_gate(interrupts: Any) -> dict[str, Any] | None:
    """Extract the pending HITL gate from a graph result's interrupts.

    LangGraph returns a tuple of ``Interrupt`` objects on the state (under the
    ``__interrupt__`` key) when a run suspends. The value carried by the
    interrupt is the dict built in ``core.graph._gate``.
    """
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", None)
    if value is None and isinstance(first, dict):
        value = first.get("value")
    if isinstance(value, dict):
        return value
    return {"gate": str(value), "prompt": "", "payload": {}}


@router.get("/graph-info")
async def get_graph_info():
    """Get information about available pipeline modes and nodes."""
    return {
        "modes": [
            {"key": "echo", "name": "测试回声", "description": "简单测试用"},
            {"key": "ideation", "name": "创意发散", "description": "只生成创意方向"},
            {"key": "quick", "name": "快速模式", "description": "3分钟自动完成脚本+分镜，自动选择最优方案"},
            {"key": "detailed", "name": "精细模式", "description": "每个关键节点暂停等待人工确认，可修改调整"},
            {"key": "full", "name": "完整流程", "description": "热点→创意→脚本→分镜→提示词包一键生成"},
        ],
        "nodes": [
            "trend_research",
            "topic_recommend",
            "ideation",
            "creative_brief",
            "character_design",
            "style_design",
            "hook_design",
            "script_writing",
            "evaluation",
            "compliance_check",
            "rhythm_optimization",
            "storyboard",
            "prompt_generation",
            "prompt_qa",
            "export",
        ],
    }
