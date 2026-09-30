"""Script Studio data schemas (Pydantic models).

Defines structured outputs for all Script Studio agents.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Creative Brief ──────────────────────────────────────────────


class CreativeBrief(BaseModel):
    """Output of CreativeBriefAgent - crystallizes the creative direction."""

    angle_title: str = Field(description="一句话创意角度标题")
    core_concept: str = Field(description="核心创意概念描述，3-5句话")
    hook_strategy: str = Field(description="钩子策略选择和理由")
    target_emotion: str = Field(description="目标情绪基调")
    structure_type: str = Field(description="选用的叙事结构ID")
    target_duration_sec: int = Field(ge=10, le=600, description="目标时长秒数")
    target_platform: str = Field(description="目标平台")
    vertical: str = Field(description="垂类ID")
    key_elements: list[str] = Field(default_factory=list, description="必须包含的关键元素")
    reference_videos: list[str] = Field(default_factory=list, description="参考视频ID")
    tone_guide: str = Field(description="语调/风格指引")
    differentiators: list[str] = Field(default_factory=list, description="与同类内容的差异化点")


# ── Script Beats ────────────────────────────────────────────────


class ScriptBeat(BaseModel):
    """A beat/moment within the script."""

    id: str = ""
    index: int = Field(ge=0, description="Beat序号")
    phase: str = Field(description="阶段: hook/body/twist/climax/cta")
    duration_sec: float = Field(gt=0, description="本beat时长秒")
    content: str = Field(description="台词/旁白文字")
    visual_note: str = Field(description="画面提示/视觉建议")
    emotion: str = Field(description="本beat情绪值")
    sound_design: str = Field(default="", description="音效/BGM提示")


class HookVariant(BaseModel):
    """A single hook candidate from HookSpecialist."""

    id: str = ""
    hook_type: str = Field(description="钩子类型ID")
    text: str = Field(description="钩子文案（3秒内能说完）")
    word_count: int = Field(description="字数")
    estimated_attention_score: float = Field(ge=0, le=10, description="预估抓注意力分数")
    rationale: str = Field(description="为什么这个钩子有效")


# ── Script Output ───────────────────────────────────────────────


class Script(BaseModel):
    """Complete script output from StorytellerAgent."""

    id: str = ""
    title: str = Field(description="脚本标题")
    script_type: str = Field(default="oral_story", description="脚本类型")
    structure_id: str = Field(description="使用的叙事结构ID")
    hook: str = Field(description="最终选定的钩子文案")
    hook_type: str = Field(default="", description="钩子类型")
    hook_variants: list[HookVariant] = Field(default_factory=list, description="3个钩子候选")
    beats: list[ScriptBeat] = Field(default_factory=list, description="脚本节拍列表")
    body_text: str = Field(default="", description="正文完整文案")
    cta: str = Field(description="CTA文案")
    cta_type: str = Field(default="", description="CTA类型")
    target_duration_sec: int = Field(gt=0, description="目标总时长")
    actual_duration_sec: float = Field(default=0, description="实际估算时长")
    emotion_curve_id: str = Field(default="", description="情绪曲线ID")
    rhythm_pattern_id: str = Field(default="", description="节奏模式ID")
    tags: list[str] = Field(default_factory=list, description="标签")
    key_message: str = Field(default="", description="核心想传达的信息")
    word_count: int = Field(default=0, description="总字数")


# ── Storyboard ──────────────────────────────────────────────────


class StoryboardShot(BaseModel):
    """A single shot in the storyboard."""

    id: str = ""
    index: int = Field(ge=0, description="镜号(1-based)")
    duration_sec: float = Field(gt=0, description="时长秒")
    shot_size: str = Field(description="景别: extreme_close_up/close_up/medium/wide/extreme_wide")
    camera_angle: str = Field(default="eye_level", description="机位角度")
    camera_movement: str = Field(default="static", description="运镜: static/pan/tilt/dolly/zoom/tracking/handheld")
    scene_description: str = Field(description="场景/环境描述（具体可执行）")
    subject_description: str = Field(description="主体/人物描述（具体）")
    action_description: str = Field(description="动作描述")
    visual_description: str = Field(description="完整画面描述：场景+人物+动作+光线+色调（无抽象形容词）")
    dialogue: str = Field(default="", description="台词/旁白文字")
    emotion: str = Field(default="neutral", description="情绪")
    lighting: str = Field(default="natural", description="光线类型")
    color_tone: str = Field(default="natural", description="色调")
    transition: str = Field(default="cut", description="转场方式: cut/dissolve/fade/wipe/slide/zoom")
    props: list[str] = Field(default_factory=list, description="道具列表")
    ai_generation_difficulty: float = Field(default=5.0, ge=0, le=10, description="AI生成难度")
    ai_warnings: list[str] = Field(default_factory=list, description="AI难度警告")
    visual_keywords: list[str] = Field(default_factory=list, description="画面关键词(用于提示词生成)")


class Storyboard(BaseModel):
    """Complete storyboard output from StoryboardAgent."""

    id: str = ""
    script_id: str = Field(default="")
    title: str = Field(default="")
    aspect_ratio: str = Field(default="9:16")
    shots: list[StoryboardShot] = Field(default_factory=list)
    total_duration_sec: float = Field(default=0)
    shot_count: int = Field(default=0)
    visual_style_notes: str = Field(default="", description="整体视觉风格说明")
    color_palette: list[str] = Field(default_factory=list, description="建议色板")
    location_notes: str = Field(default="", description="场景/场地说明")


# ── Evaluation & Compliance ─────────────────────────────────────


class QualityScore(BaseModel):
    """Quality evaluation scores from EvaluatorAgent."""

    hook_strength: float = Field(ge=0, le=10, description="钩子吸引力")
    structure_clarity: float = Field(ge=0, le=10, description="结构清晰度")
    emotional_impact: float = Field(ge=0, le=10, description="情绪冲击力")
    pacing: float = Field(ge=0, le=10, description="节奏合理性")
    cta_effectiveness: float = Field(ge=0, le=10, description="CTA有效度")
    originality: float = Field(ge=0, le=10, description="原创性/差异度")
    ai_feasibility: float = Field(ge=0, le=10, description="AI可生成性")
    overall: float = Field(ge=0, le=10, description="综合评分")


class ScriptEvaluation(BaseModel):
    """Complete evaluation result."""

    scores: QualityScore
    strengths: list[str] = Field(default_factory=list, description="优点")
    weaknesses: list[str] = Field(default_factory=list, description="不足")
    improvement_suggestions: list[str] = Field(default_factory=list, description="具体改进建议")
    iteration_notes: str = Field(default="", description="迭代说明")


class ComplianceFlag(BaseModel):
    """A single compliance issue."""

    severity: Literal["low", "medium", "high"] = Field(description="严重程度")
    category: str = Field(description="违规类别: 极限词/医疗宣称/版权/虚假宣传/低俗/...")
    flagged_text: str = Field(description="被标记的文字")
    reason: str = Field(description="为什么违规")
    suggestion: str = Field(description="建议修改为")


class ComplianceReport(BaseModel):
    """Compliance check result."""

    is_compliant: bool = Field(default=True)
    flags: list[ComplianceFlag] = Field(default_factory=list)
    overall_risk: Literal["low", "medium", "high"] = Field(default="low")


# ── Script Package (output to 05 Prompt Engine) ────────────────


class ScriptPackage(BaseModel):
    """Final package that gets passed to the Prompt Engine (05)."""

    script: Script
    storyboard: Storyboard
    evaluation: ScriptEvaluation | None = None
    compliance: ComplianceReport | None = None
    creative_brief: CreativeBrief | None = None
    character_ids: list[str] = Field(default_factory=list)
    style_preset_ids: list[str] = Field(default_factory=list)
    target_models: list[str] = Field(default_factory=list, description="目标AIGC模型: sora/kling/runway/midjourney/...")
