"""
Pydantic schemas for trend intelligence module.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class Platform(str, Enum):
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"
    WEIBO = "weibo"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class LifecycleStage(str, Enum):
    EMERGING = "emerging"  # 刚出现，0-6小时
    RISING = "rising"  # 快速上升，6-24小时
    PEAK = "peak"  # 峰值，24-72小时
    DECLINING = "declining"  # 下降期
    STALE = "stale"  # 过时


class TrendTopicSchema(BaseModel):
    """Normalized trend topic across platforms."""

    platform: Platform
    topic_id: str | None = None
    title: str
    category: str | None = None
    hot_value: int | None = None
    hot_value_growth: float | None = None
    rank_position: int | None = None
    cover_url: str | None = None
    url: str | None = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class ViralVideoSubmit(BaseModel):
    """Request to analyze a video URL."""

    url: HttpUrl
    platform: Platform | None = None
    category: str | None = None
    analysis_mode: Literal["fast", "accurate"] = Field(default="fast", description="fast or accurate")
    extract_patterns: bool = Field(default=True, description="whether to extract viral patterns")


class ShotData(BaseModel):
    """Structured shot data from video analysis."""

    shot_index: int
    start_time: float
    end_time: float
    duration: float
    keyframe_path: str | None = None
    keyframe_url: str | None = None
    transcript: str | None = None
    transcript_words: list[dict[str, Any]] = Field(default_factory=list)
    visual_description: str | None = None
    visual_tags: list[str] = Field(default_factory=list)
    camera_movement: str | None = None
    camera_angle: str | None = None
    lighting: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    emotion_tag: str | None = None
    text_ocr: str | None = None
    transition_type: str | None = None
    has_face: bool = False
    face_count: int = 0
    motion_intensity: float = 0.0
    audio_type: str | None = None
    onset_strength: float = 0.0


class HookAnalysis(BaseModel):
    """Analysis of the video's opening hook."""

    hook_text: str
    hook_type: str  # question/shock/contrast/story/number/demo/curiosity/pain_point
    hook_end_time: float  # seconds until hook ends
    engagement_score: float = Field(ge=0, le=1)
    techniques_used: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class NarrativeStructure(BaseModel):
    """Narrative structure analysis."""

    structure_type: str  # hook-body-cta / problem-solution / countdown / story / tutorial / reaction
    total_duration: float
    hook_duration: float
    body_duration: float
    cta_duration: float
    act_breakpoints: list[float] = Field(default_factory=list)
    pacing_type: str  # fast_cut / medium / slow_build
    tension_curve: list[float] = Field(default_factory=list)  # per-second tension 0-1


class VisualLanguage(BaseModel):
    """Visual cinematography analysis."""

    dominant_style: str
    color_grading: str
    lighting_setup: str
    camera_movements: list[str] = Field(default_factory=list)
    composition_rules: list[str] = Field(default_factory=list)
    shot_types_used: dict[str, float] = Field(default_factory=dict)  # close_up:0.3, medium:0.5
    average_shot_duration: float
    key_visual_motifs: list[str] = Field(default_factory=list)
    subtitle_style: str | None = None


class AudioAnalysis(BaseModel):
    """Audio/music analysis."""

    bpm: float
    bpm_category: str  # slow/medium/fast/very_fast
    music_genre: str | None = None
    emotion: str  # calm/happy/tense/energetic/dramatic/nostalgic
    onset_curve: list[float] = Field(default_factory=list)
    speech_to_music_ratio: float = 0.0
    has_voiceover: bool = True
    sound_effects: list[str] = Field(default_factory=list)
    key_phrases: list[str] = Field(default_factory=list)


class ViralPatternSchema(BaseModel):
    """Extracted viral pattern/formula."""

    name: str
    pattern_type: str  # hook/narrative/editing/audio/visual/structure
    category: str | None = None
    description: str
    formula_template: str | None = None
    key_phrases: list[str] = Field(default_factory=list)
    trigger_conditions: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)


class ViralAnalysisResult(BaseModel):
    """Complete viral video analysis result."""

    video_id: str | None = None
    platform: str | None = None
    url: str
    title: str | None = None
    description: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    aspect_ratio: str | None = None

    # Analysis components
    transcript: str | None = None
    shots: list[ShotData] = Field(default_factory=list)
    hook: HookAnalysis | None = None
    narrative: NarrativeStructure | None = None
    visual: VisualLanguage | None = None
    audio: AudioAnalysis | None = None
    patterns: list[ViralPatternSchema] = Field(default_factory=list)
    emotion_curve: list[dict[str, Any]] = Field(default_factory=list)
    rhythm_curve: list[dict[str, Any]] = Field(default_factory=list)
    viral_score: float = Field(default=0.0, ge=0, le=100)
    viral_score_breakdown: dict[str, float] = Field(default_factory=dict)
    keyframe_paths: list[str] = Field(default_factory=list)
    summary: str | None = None

    # Metadata
    analysis_version: str = "v2"
    analyzed_at: datetime = Field(default_factory=datetime.now)
    model_info: dict[str, Any] = Field(default_factory=dict)


class TopicCard(BaseModel):
    """A single topic recommendation card."""

    title: str
    hook_suggestion: str
    content_direction: str
    target_platform: list[str] = Field(default_factory=list)
    target_duration: str
    estimated_viral_potential: float = Field(default=50.0, ge=0, le=100)
    supporting_trends: list[str] = Field(default_factory=list)
    reference_patterns: list[str] = Field(default_factory=list)
    key_selling_points: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    script_outline: str | None = None
    visual_concept: str | None = None
    tags: list[str] = Field(default_factory=list)


class TopicRecommendRequest(BaseModel):
    """Request for topic recommendations."""

    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    reference_video_urls: list[str] = Field(default_factory=list)
    count: int = Field(default=10, ge=1, le=30)
    target_platform: str | None = None


class TopicRecommendResponse(BaseModel):
    """Response with topic cards."""

    topics: list[TopicCard] = Field(default_factory=list)
    trend_summary: str | None = None
    model_info: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)


class CrawlTaskStatus(BaseModel):
    """Status of a crawl task."""

    task_id: str
    platform: str
    task_type: str
    status: str = "pending"
    progress: float = 0.0
    items_found: int = 0
    items_new: int = 0
    error: str | None = None
