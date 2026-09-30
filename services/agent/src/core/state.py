"""Agent state definition for LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class CreativeIdea(BaseModel):
    """A creative idea/direction."""

    id: str = ""
    title: str
    description: str
    hook_direction: str = ""
    emotion_tone: str = "neutral"
    differentiation: str = ""
    ai_feasibility_score: float = Field(default=7.0, ge=0, le=10)
    difficulty: str = "medium"  # low/medium/high
    estimated_duration: int = 30
    reference_video_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_hot_trend: bool = False


class AgentMessage(BaseModel):
    """A message in the agent conversation."""

    role: str  # user/assistant/system
    content: str
    timestamp: str = ""


class AgentState(TypedDict, total=False):
    """LangGraph state passed between nodes.

    All fields are optional to support incremental state building.
    """

    # Identity
    project_id: str
    user_id: str
    run_id: str
    mode: str  # quick/detailed

    # Conversation
    messages: list[dict[str, Any]]
    current_input: str

    # Workflow tracking
    current_step: str
    steps_completed: list[str]

    # Trend research output
    trend_summary: str
    topic_recommendations: list[dict[str, Any]]
    viral_patterns: list[dict[str, Any]]

    # Ideation output
    creative_ideas: list[dict[str, Any]]
    selected_idea_id: str
    selected_idea: dict[str, Any]

    # Brief output
    creative_brief: dict[str, Any]
    brief_approved: bool

    # Character & Style output
    characters: list[dict[str, Any]]
    character_ids: list[str]
    style: dict[str, Any]
    style_ids: list[str]

    # Script output
    script: dict[str, Any]
    script_approved: bool

    # Evaluation
    evaluation: dict[str, Any]
    eval_passed: bool
    eval_iteration_count: int
    eval_feedback: str
    user_modifications: str

    # Storyboard output
    storyboard: dict[str, Any]
    storyboard_approved: bool
    storyboard_eval: dict[str, Any]

    # Compliance & Rhythm
    compliance_result: dict[str, Any]
    rhythm_result: dict[str, Any]

    # Prompt output
    target_models: list[str]
    prompt_package: dict[str, Any]
    prompt_qa_result: dict[str, Any]
    prompt_optimized: bool
    prompt_retry_count: int

    # HITL
    hitl_required: bool
    hitl_node: str
    hitl_feedback: str
    versions: list[dict[str, Any]]

    # Export
    export_ready: bool
    export_data: dict[str, Any]

    # Errors
    error: str | None

    # Streaming events
    events: list[dict[str, Any]]
