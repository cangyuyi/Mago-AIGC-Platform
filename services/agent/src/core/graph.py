"""LangGraph workflow graph definition.

Provides graphs for:
- echo_graph: Simple echo test
- ideation_graph: Ideation only
- script_studio_graph: Script studio pipeline (ideation -> brief -> hooks -> script -> storyboard)
- trend_research_graph: Trend research + ideation
- full_graph: End-to-end pipeline with trend/ideation/brief/character/style/hooks/script/eval/compliance/rhythm/storyboard/prompt
              Supports checkpointing for resume and interrupts for HITL.
"""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

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
from src.core.checkpoint import get_checkpointer
from src.core.state import AgentState

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# HITL checkpointer
# ---------------------------------------------------------------------------
#
# Paused runs are persisted here. ``get_checkpointer()`` selects Postgres/Redis/
# SQLite when configured and falls back to an in-process MemorySaver otherwise;
# see ``src/core/checkpoint.py`` for the resolution order.
#
# An earlier version of this module returned ``END`` from a conditional edge to
# "pause" for human review. That ended the run instead of suspending it: the
# user's next message restarted the graph from START and advanced a single node,
# so a multi-stage approval flow needed one round-trip per node and the stored
# checkpoint was never reused. The graphs below use LangGraph's ``interrupt()``
# plus ``Command(resume=...)`` instead, which suspends mid-node and continues
# from the same position on resume.

#: Gate identifiers surfaced to the client so the UI knows what to ask for next,
#: mapped to the boolean state key that marks the gate as satisfied. The idea
#: gate is satisfied by ``selected_idea_id`` (a selection, not a boolean) and is
#: therefore handled separately.
HITL_GATES: dict[str, str] = {
    "brief_review": "brief_approved",
    "script_review": "script_approved",
    "storyboard_review": "storyboard_approved",
}


def _should_pause(state: AgentState, approval_key: str) -> bool:
    """Whether the workflow must stop for a human decision at this gate.

    ``quick`` mode is fully autonomous and ``approved`` (or an explicit
    selection on the incoming request) satisfies the gate, so both continue
    without interrupting.
    """
    if state.get("mode") == "quick":
        return False
    return not bool(state.get(approval_key))


def _gate(state: AgentState, gate: str, prompt: str, payload: dict[str, Any] | None = None) -> Any:
    """Suspend the run for a human decision and return their response.

    On the first pass this raises LangGraph's interrupt, which persists the
    checkpoint and returns control to the caller. When the caller later invokes
    the graph with ``Command(resume=value)`` this same call returns ``value``
    and the node continues in place.
    """
    decision = interrupt(
        {
            "gate": gate,
            "prompt": prompt,
            "mode": "approval",
            "payload": payload or {},
        }
    )
    return decision


def _apply_gate_decision(state: AgentState, gate: str, decision: Any) -> dict[str, Any]:
    """Translate a resumed HITL decision into state updates.

    Clients may resume with a bare ``True`` approval, a selection id string, or
    a structured object carrying edits/feedback. All three are normalised here
    so individual nodes stay simple.
    """
    updates: dict[str, Any] = {"hitl_node": gate, "hitl_required": False}

    # Record the approval on the gate we just cleared so the run does not
    # immediately re-pause on the same gate. The idea gate is satisfied by the
    # selected id below rather than a boolean.
    approval_key = HITL_GATES.get(gate)

    if isinstance(decision, dict):
        if decision.get("approved") is False:
            updates["hitl_required"] = True
        elif approval_key:
            updates[approval_key] = True
        for key in ("selected_idea_id", "feedback", "hitl_feedback"):
            value = decision.get(key)
            if value:
                updates[key] = value
        if decision.get("edits"):
            updates["user_modifications"] = str(decision["edits"])
        updates["_gate_decision"] = decision
        return updates

    if isinstance(decision, str) and decision:
        if gate == "idea_selection":
            updates["selected_idea_id"] = decision
        else:
            updates["hitl_feedback"] = decision
            updates["user_modifications"] = decision
        if approval_key:
            updates[approval_key] = True
        updates["_gate_decision"] = decision
        return updates

    updates["_gate_decision"] = decision
    return updates


# ---------------------------------------------------------------------------
# Simple graphs
# ---------------------------------------------------------------------------


def build_echo_graph(echo_agent: EchoAgent) -> Any:
    g = StateGraph(AgentState)
    g.add_node("echo", cast(Any, echo_agent.run))
    g.add_edge(START, "echo")
    g.add_edge("echo", END)
    return g.compile(checkpointer=get_checkpointer())


def build_ideation_graph(ideation_agent: IdeationAgent | None = None) -> Any:
    agent = ideation_agent or IdeationAgent()
    g = StateGraph(AgentState)
    g.add_node("ideation", cast(Any, agent.run))
    g.add_edge(START, "ideation")
    g.add_edge("ideation", END)
    return g.compile(checkpointer=get_checkpointer())


# ---------------------------------------------------------------------------
# Script Studio graph (03)
# ---------------------------------------------------------------------------


def build_script_studio_graph(**deps: Any) -> Any:
    """Three-layer creative funnel: ideation -> brief -> hooks -> script -> storyboard."""
    ideation = deps.get("ideation_agent") or IdeationAgent()
    brief = deps.get("brief_agent") or CreativeBriefAgent()
    hooks = deps.get("hooks_agent") or HookSpecialistAgent()
    storyteller = deps.get("storyteller_agent") or StorytellerAgent()
    storyboard = deps.get("storyboard_agent") or StoryboardAgent()
    evaluator = deps.get("evaluator_agent") or EvaluatorAgent()
    compliance = deps.get("compliance_agent") or ComplianceAgent()
    rhythm = deps.get("rhythm_agent") or RhythmOptimizerAgent()

    # --- HITL gate nodes -------------------------------------------------
    # Each gate suspends the run with interrupt() and, on resume, folds the
    # human decision back into state before routing onward. Because interrupt()
    # suspends in place, one approval message continues the pipeline instead of
    # restarting the graph and advancing a single node.

    async def idea_gate(state: AgentState) -> dict:
        if _should_pause(state, "selected_idea_id"):
            decision = _gate(
                state,
                "idea_selection",
                "请选择一个创意方向继续",
                {"ideas": state.get("creative_ideas", [])},
            )
            updates = _apply_gate_decision(state, "idea_selection", decision)
            updates["selected_idea_id"] = updates.get("selected_idea_id") or state.get("selected_idea_id", "")
            return updates
        return {}

    async def brief_gate(state: AgentState) -> dict:
        if _should_pause(state, "brief_approved"):
            decision = _gate(state, "brief_review", "请确认创意简报后继续", {"brief": state.get("creative_brief", {})})
            return _apply_gate_decision(state, "brief_review", decision)
        return {}

    async def script_gate(state: AgentState) -> dict:
        if _should_pause(state, "script_approved"):
            decision = _gate(state, "script_review", "请确认脚本后继续生成分镜", {"script": state.get("script", {})})
            return _apply_gate_decision(state, "script_review", decision)
        return {}

    async def select_idea_node(state: AgentState) -> dict:
        """Resolve the chosen idea (auto-picking the first in quick mode)."""
        ideas = state.get("creative_ideas", [])
        chosen_id = state.get("selected_idea_id", "")
        chosen: dict[str, Any] = state.get("selected_idea", {}) or {}
        if chosen_id:
            chosen = next((i for i in ideas if str(i.get("id")) == str(chosen_id)), chosen)
        if not chosen and ideas:
            chosen = ideas[0]
            chosen_id = str(chosen.get("id", ""))
        return {
            "selected_idea": chosen,
            "selected_idea_id": chosen_id,
            "steps_completed": state.get("steps_completed", []) + ["idea_selected"],
        }

    def _after_idea_gate(state: AgentState) -> str:
        return "select_idea"

    def _after_eval(state: AgentState) -> str:
        if state.get("eval_passed") or state.get("mode") == "quick":
            return "compliance"
        if state.get("eval_iteration_count", 0) >= 2:
            logger.info("eval_max_iterations_reached, proceeding to compliance")
            return "compliance"
        state["eval_iteration_count"] = state.get("eval_iteration_count", 0) + 1
        state["user_modifications"] = state.get("evaluation", {}).get("iteration_notes", "")
        return "script"

    g = StateGraph(AgentState)
    g.add_node("ideation", ideation.run)
    g.add_node("idea_gate", idea_gate)
    g.add_node("select_idea", select_idea_node)
    g.add_node("brief", brief.run)
    g.add_node("brief_gate", brief_gate)
    g.add_node("hooks", hooks.run)
    g.add_node("script", storyteller.run)
    g.add_node("script_gate", script_gate)
    g.add_node("storyboard", storyboard.run)
    g.add_node("evaluate", evaluator.run)
    g.add_node("compliance", compliance.run)
    g.add_node("rhythm", rhythm.run)
    g.add_edge(START, "ideation")
    g.add_edge("ideation", "idea_gate")
    g.add_edge("idea_gate", "select_idea")
    g.add_edge("select_idea", "brief")
    g.add_edge("brief", "brief_gate")
    g.add_edge("brief_gate", "hooks")
    g.add_edge("hooks", "script")
    g.add_edge("script", "script_gate")
    g.add_edge("script_gate", "storyboard")
    g.add_edge("storyboard", "evaluate")
    g.add_conditional_edges("evaluate", _after_eval, {"script": "script", "compliance": "compliance"})
    g.add_edge("compliance", "rhythm")
    g.add_edge("rhythm", END)
    return g.compile(checkpointer=get_checkpointer())


# ---------------------------------------------------------------------------
# Trend Research graph (02)
# ---------------------------------------------------------------------------


def build_trend_research_graph(**deps: Any) -> Any:
    """Trend analysis + topic recommendation pipeline."""
    from src.agents.topic_recommender.agent import TopicRecommenderAgent
    from src.agents.trend_analyzer.agent import TrendAnalyzerAgent

    trend_agent = deps.get("trend_agent") or TrendAnalyzerAgent()
    topic_agent = deps.get("topic_agent") or TopicRecommenderAgent()

    async def trend_research_node(state: AgentState) -> dict:
        try:
            result = await trend_agent.analyze(state.get("current_input", ""))
            return {
                "current_step": "trend_research_done",
                "steps_completed": state.get("steps_completed", []) + ["trend_research"],
                "trend_summary": result if isinstance(result, str) else str(result),
            }
        except Exception as e:
            logger.warning("trend_research_failed", error=str(e))
            return {
                "current_step": "trend_research_done",
                "steps_completed": state.get("steps_completed", []) + ["trend_research"],
            }

    async def topic_recommend_node(state: AgentState) -> dict:
        try:
            from src.schemas.trend import TopicRecommendRequest

            message = state.get("current_input", "")
            request = TopicRecommendRequest(
                category=_extract_category(message),
                keywords=_extract_keywords(message),
                count=10,
            )
            response = await topic_agent.recommend(request)
            return {
                "current_step": "topic_recommend_done",
                "steps_completed": state.get("steps_completed", []) + ["topic_recommend"],
                "topic_recommendations": [t.model_dump() for t in response.topics],
                "trend_summary": response.trend_summary,
            }
        except Exception as e:
            logger.warning("topic_recommend_failed", error=str(e))
            return {
                "current_step": "topic_recommend_done",
                "steps_completed": state.get("steps_completed", []) + ["topic_recommend"],
                "topic_recommendations": [],
            }

    g = StateGraph(AgentState)
    g.add_node("trend_research", trend_research_node)
    g.add_node("topic_recommend", topic_recommend_node)
    g.add_node("ideation", (deps.get("ideation_agent") or IdeationAgent()).run)
    g.add_edge(START, "trend_research")
    g.add_edge("trend_research", "topic_recommend")
    g.add_edge("topic_recommend", "ideation")
    g.add_edge("ideation", END)
    return g.compile(checkpointer=get_checkpointer())


# ---------------------------------------------------------------------------
# Full end-to-end production graph (08 - 集成所有板块)
# ---------------------------------------------------------------------------


def build_full_graph(**deps: Any) -> Any:
    """Full end-to-end production graph.

    Pipeline:
      START -> route_intent -> [trend_research -> topic_recommend] -> ideation ->
      brief -> [character_design?] -> style_design -> hooks -> script ->
      evaluate -> (loop back to script up to 2x) -> compliance -> rhythm ->
      storyboard -> storyboard_eval -> prompt_generation -> prompt_qa -> export_ready -> END

    Conditional routing:
      - Quick mode auto-approves HITL checkpoints (idea/brief/script/storyboard selection)
      - Detailed mode returns END at HITL checkpoints to wait for human input (checkpointed)
      - Eval failure loops back to script for revision (max 2 iterations)
      - Character design is optional (skipped if no character_ids specified or quick mode)
      - Prompt QA failure triggers one more generation attempt
    """
    ideation_agent = deps.get("ideation_agent") or IdeationAgent()
    trend_agent = deps.get("trend_agent") or TrendAnalyzerAgent()
    topic_agent = deps.get("topic_agent") or TopicRecommenderAgent()
    brief_agent = deps.get("brief_agent") or CreativeBriefAgent()
    character_agent = deps.get("character_agent") or CharacterAgent()
    style_agent = deps.get("style_agent") or StyleAgent()
    hooks_agent = deps.get("hooks_agent") or HookSpecialistAgent()
    storyteller_agent = deps.get("storyteller_agent") or StorytellerAgent()
    storyboard_agent = deps.get("storyboard_agent") or StoryboardAgent()
    evaluator_agent = deps.get("evaluator_agent") or EvaluatorAgent()
    compliance_agent = deps.get("compliance_agent") or ComplianceAgent()
    rhythm_agent = deps.get("rhythm_agent") or RhythmOptimizerAgent()
    prompt_agent = deps.get("prompt_agent") or PromptEngineAgent()

    # --- Trend nodes ---
    async def trend_research_node(state: AgentState) -> dict:
        try:
            result = await trend_agent.analyze(state.get("current_input", ""))
            return {
                "current_step": "trend_research_done",
                "steps_completed": state.get("steps_completed", []) + ["trend_research"],
                "trend_summary": result if isinstance(result, str) else str(result),
            }
        except Exception as e:
            logger.warning("trend_research_failed", error=str(e))
            return {
                "current_step": "trend_research_done",
                "steps_completed": state.get("steps_completed", []) + ["trend_research"],
            }

    async def topic_recommend_node(state: AgentState) -> dict:
        try:
            from src.schemas.trend import TopicRecommendRequest

            message = state.get("current_input", "")
            request = TopicRecommendRequest(
                category=_extract_category(message),
                keywords=_extract_keywords(message),
                count=10,
            )
            response = await topic_agent.recommend(request)
            return {
                "current_step": "topic_recommend_done",
                "steps_completed": state.get("steps_completed", []) + ["topic_recommend"],
                "topic_recommendations": [t.model_dump() for t in response.topics],
                "trend_summary": response.trend_summary,
            }
        except Exception as e:
            logger.warning("topic_recommend_failed", error=str(e))
            return {
                "current_step": "topic_recommend_done",
                "steps_completed": state.get("steps_completed", []) + ["topic_recommend"],
                "topic_recommendations": [],
            }

    # --- Character design (optional) ---
    async def character_design_node(state: AgentState) -> dict:
        char_ids = state.get("character_ids", [])
        if not char_ids and state.get("mode") == "quick":
            return {
                "characters": [],
                "steps_completed": state.get("steps_completed", []) + ["character_design"],
            }
        result = await character_agent.run(cast(dict[str, Any], state))
        return result

    # --- Storyboard evaluation node ---
    async def storyboard_eval_node(state: AgentState) -> dict:
        storyboard = state.get("storyboard", {})
        shots = storyboard.get("shots", []) if isinstance(storyboard, dict) else []
        issues = []
        score = 10.0

        if len(shots) < 3:
            issues.append("too_few_shots")
            score -= 3
        if len(shots) > 20:
            issues.append("too_many_shots")
            score -= 2

        # Check for shot variety
        shot_types = set()
        for shot in shots:
            if isinstance(shot, dict):
                shot_type = shot.get("shot_type", "")
                if shot_type:
                    shot_types.add(shot_type)
        if len(shot_types) < 2 and len(shots) > 3:
            issues.append("lack_of_shot_variety")
            score -= 1

        return {
            "current_step": "storyboard_eval_done",
            "steps_completed": state.get("steps_completed", []) + ["storyboard_eval"],
            "storyboard_eval": {
                "score": max(0, score),
                "issues": issues,
                "passed": score >= 6.0,
            },
        }

    # --- Prompt QA node ---
    async def prompt_qa_node(state: AgentState) -> dict:
        pkg = state.get("prompt_package", {})
        shots = pkg.get("shots", []) if isinstance(pkg, dict) else []
        issues: list[str] = []
        if not shots:
            issues.append("no_shots_generated")
        for i, shot in enumerate(shots):
            if isinstance(shot, dict):
                for model_key, prompt_text in shot.get("prompts", {}).items():
                    if not prompt_text or len(str(prompt_text)) < 20:
                        issues.append(f"shot_{i}_model_{model_key}_prompt_too_short")
        qa_passed = len(issues) == 0
        qa_result = {
            "passed": qa_passed,
            "issues": issues,
            "score": 10.0 - len(issues) * 1.5,
        }
        return {
            "current_step": "prompt_qa_done",
            "steps_completed": state.get("steps_completed", []) + ["prompt_qa"],
            "prompt_qa_result": qa_result,
        }

    # --- Export ready node ---
    async def export_ready_node(state: AgentState) -> dict:
        from datetime import UTC, datetime

        pkg = state.get("prompt_package", {})
        export = {
            "exported_at": datetime.now(UTC).isoformat(),
            "project_id": state.get("project_id"),
            "selected_idea": state.get("selected_idea"),
            "creative_brief": state.get("creative_brief"),
            "script": state.get("script"),
            "storyboard": state.get("storyboard"),
            "prompt_package": pkg,
            "compliance_passed": state.get("compliance_result", {}).get("passed", True),
            "metadata": {
                "mode": state.get("mode"),
                "eval_score": state.get("evaluation", {}).get("overall_score"),
                "prompt_qa_score": state.get("prompt_qa_result", {}).get("score"),
            },
        }
        return {
            "current_step": "export_ready",
            "steps_completed": state.get("steps_completed", []) + ["export_ready"],
            "export_ready": True,
            "export_data": export,
        }

    # --- Conditional routing functions ---
    def route_by_intent(state: AgentState) -> str:
        msg = state.get("current_input", "").lower()
        trend_keywords = [
            "热点",
            "趋势",
            "选题",
            "灵感",
            "方向",
            "不知道拍什么",
            "没灵感",
            "热门",
            "爆款",
            "推荐选题",
            "找方向",
        ]
        for kw in trend_keywords:
            if kw in msg:
                return "trend"
        script_keywords = ["写脚本", "脚本", "分镜", "剧本"]
        for kw in script_keywords:
            if kw in msg:
                return "script"
        return "direct"

    def needs_character(state: AgentState) -> str:
        if state.get("character_ids"):
            return "character_design"
        if state.get("mode") == "quick":
            return "style_design"
        brief = state.get("creative_brief", {})
        if isinstance(brief, dict) and brief.get("needs_character"):
            return "character_design"
        return "style_design"

    def after_character(state: AgentState) -> str:
        return "style_design"

    def after_style(state: AgentState) -> str:
        return "hooks"

    # --- HITL gate nodes -------------------------------------------------
    # See the note above HITL_GATES: these use interrupt() so a single human
    # response resumes the pipeline in place rather than restarting it.

    async def idea_gate(state: AgentState) -> dict:
        if _should_pause(state, "selected_idea_id"):
            decision = _gate(
                state,
                "idea_selection",
                "请选择一个创意方向继续",
                {"ideas": state.get("creative_ideas", [])},
            )
            return _apply_gate_decision(state, "idea_selection", decision)
        return {}

    async def select_idea_node(state: AgentState) -> dict:
        ideas = state.get("creative_ideas", [])
        chosen_id = state.get("selected_idea_id", "")
        chosen: dict[str, Any] = state.get("selected_idea", {}) or {}
        if chosen_id:
            chosen = next((i for i in ideas if str(i.get("id")) == str(chosen_id)), chosen)
        if not chosen and ideas:
            chosen = ideas[0]
            chosen_id = str(chosen.get("id", ""))
        return {
            "selected_idea": chosen,
            "selected_idea_id": chosen_id,
            "steps_completed": state.get("steps_completed", []) + ["idea_selected"],
        }

    async def brief_gate(state: AgentState) -> dict:
        if _should_pause(state, "brief_approved"):
            decision = _gate(state, "brief_review", "请确认创意简报后继续", {"brief": state.get("creative_brief", {})})
            return _apply_gate_decision(state, "brief_review", decision)
        return {}

    async def script_gate(state: AgentState) -> dict:
        if _should_pause(state, "script_approved"):
            decision = _gate(state, "script_review", "请确认脚本后继续生成分镜", {"script": state.get("script", {})})
            return _apply_gate_decision(state, "script_review", decision)
        return {}

    async def storyboard_gate(state: AgentState) -> dict:
        if _should_pause(state, "storyboard_approved"):
            decision = _gate(
                state,
                "storyboard_review",
                "请确认分镜后可生成提示词包",
                {"storyboard": state.get("storyboard", {})},
            )
            return _apply_gate_decision(state, "storyboard_review", decision)
        return {}

    def _after_idea_gate(state: AgentState) -> str:
        return "select_idea"

    def _after_brief_gate(state: AgentState) -> str:
        return needs_character(state)

    def after_eval(state: AgentState) -> str:
        if state.get("eval_passed") or state.get("mode") == "quick":
            return "compliance"
        if state.get("eval_iteration_count", 0) >= 2:
            logger.info("eval_max_iterations_reached, proceeding to compliance")
            return "compliance"
        state["eval_iteration_count"] = state.get("eval_iteration_count", 0) + 1
        state["user_modifications"] = state.get("evaluation", {}).get("iteration_notes", "")
        return "script"

    def after_compliance(state: AgentState) -> str:
        return "rhythm"

    def after_rhythm(state: AgentState) -> str:
        return "storyboard"

    def after_storyboard(state: AgentState) -> str:
        return "storyboard_eval"

    def after_storyboard_eval(state: AgentState) -> str:
        """Send failed storyboards to human review; pass clean ones straight on."""
        eval_result = state.get("storyboard_eval", {})
        if state.get("mode") == "quick" or eval_result.get("passed", True):
            return "prompt_generation"
        return "storyboard_gate"

    def after_prompt_qa(state: AgentState) -> str:
        qa = state.get("prompt_qa_result", {})
        if qa.get("passed") or state.get("mode") == "quick":
            return "export_ready"
        if state.get("prompt_retry_count", 0) >= 1:
            logger.warning("prompt_qa_failed_max_retries, proceeding to export")
            return "export_ready"
        state["prompt_retry_count"] = state.get("prompt_retry_count", 0) + 1
        return "prompt_generation"  # Retry prompt generation once

    # --- Build graph ---
    g = StateGraph(AgentState)

    # Add all nodes
    g.add_node("trend_research", trend_research_node)
    g.add_node("topic_recommend", topic_recommend_node)
    g.add_node("ideation", ideation_agent.run)
    g.add_node("idea_gate", idea_gate)
    g.add_node("select_idea", select_idea_node)
    g.add_node("brief", brief_agent.run)
    g.add_node("brief_gate", brief_gate)
    g.add_node("script_gate", script_gate)
    g.add_node("storyboard_gate", storyboard_gate)
    g.add_node("character_design", character_design_node)
    g.add_node("style_design", style_agent.run)
    g.add_node("hooks", hooks_agent.run)
    g.add_node("script", storyteller_agent.run)
    g.add_node("evaluate", evaluator_agent.run)
    g.add_node("compliance", compliance_agent.run)
    g.add_node("rhythm", rhythm_agent.run)
    g.add_node("storyboard", storyboard_agent.run)
    g.add_node("storyboard_eval", storyboard_eval_node)
    g.add_node("prompt_generation", prompt_agent.run)
    g.add_node("prompt_qa", prompt_qa_node)
    g.add_node("export_ready", export_ready_node)

    # Entry point: route by intent
    g.add_conditional_edges(
        START,
        route_by_intent,
        {
            "trend": "trend_research",
            "direct": "ideation",
            "script": "ideation",
        },
    )

    # Trend path
    g.add_edge("trend_research", "topic_recommend")
    g.add_edge("topic_recommend", "ideation")

    # Ideation -> (gate) -> choose idea -> Brief
    g.add_edge("ideation", "idea_gate")
    g.add_edge("idea_gate", "select_idea")
    g.add_edge("select_idea", "brief")

    # Brief -> (gate) -> optional character -> Style
    g.add_edge("brief", "brief_gate")
    g.add_conditional_edges(
        "brief_gate",
        _after_brief_gate,
        {
            "character_design": "character_design",
            "style_design": "style_design",
        },
    )
    g.add_edge("character_design", "style_design")

    # Style -> Hooks -> Script -> (gate) -> Eval loop
    g.add_edge("style_design", "hooks")
    g.add_edge("hooks", "script")
    g.add_edge("script", "script_gate")
    g.add_edge("script_gate", "evaluate")
    g.add_conditional_edges("evaluate", after_eval, {"script": "script", "compliance": "compliance"})

    # Compliance -> Rhythm -> Storyboard -> Storyboard Eval -> (gate) -> Prompt
    g.add_edge("compliance", "rhythm")
    g.add_edge("rhythm", "storyboard")
    g.add_edge("storyboard", "storyboard_eval")
    g.add_conditional_edges(
        "storyboard_eval",
        after_storyboard_eval,
        {"prompt_generation": "prompt_generation", "storyboard_gate": "storyboard_gate"},
    )
    g.add_edge("storyboard_gate", "prompt_generation")

    # Prompt generation -> QA -> Export
    g.add_edge("prompt_generation", "prompt_qa")
    g.add_conditional_edges(
        "prompt_qa",
        after_prompt_qa,
        {
            "export_ready": "export_ready",
            "prompt_generation": "prompt_generation",
        },
    )
    g.add_edge("export_ready", END)

    return g.compile(checkpointer=get_checkpointer())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route_by_intent(state: AgentState) -> str:
    msg = state.get("current_input", "").lower()
    trend_keywords = [
        "热点",
        "趋势",
        "选题",
        "灵感",
        "方向",
        "不知道拍什么",
        "没灵感",
        "热门",
        "爆款",
        "推荐选题",
        "找方向",
    ]
    for kw in trend_keywords:
        if kw in msg:
            return "trend"
    script_keywords = ["写脚本", "脚本", "分镜", "剧本"]
    for kw in script_keywords:
        if kw in msg:
            return "script"
    return "direct"


def _extract_category(message: str) -> str | None:
    categories = ["美妆", "美食", "时尚", "3C", "数码", "剧情", "知识", "生活", "旅游", "游戏", "教育"]
    for cat in categories:
        if cat in message:
            return cat
    return None


def _extract_keywords(message: str) -> list[str]:
    import re

    words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", message)
    stopwords = {"帮我", "给我", "想", "做", "关于", "推荐", "一下", "一个", "什么", "怎么", "视频", "内容"}
    return [w for w in words if w not in stopwords and len(w) >= 2][:5]


def get_graph_by_name(name: str, **deps: Any) -> Any:
    """Get a compiled graph by name."""
    graphs = {
        "echo": lambda: build_echo_graph(deps.get("echo_agent") or EchoAgent()),
        "ideation": lambda: build_ideation_graph(deps.get("ideation_agent")),
        "script_studio": lambda: build_script_studio_graph(**deps),
        "trend": lambda: build_trend_research_graph(**deps),
        "full": lambda: build_full_graph(**deps),
    }
    if name not in graphs:
        raise ValueError(f"Unknown graph: {name}. Available: {list(graphs.keys())}")
    return graphs[name]()
