"""
Viral Video Analysis Agent.
LangGraph-based agent that orchestrates the full video analysis pipeline
and produces structured viral analysis reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from src.common.logger import get_logger
from src.schemas.trend import ViralAnalysisResult, ViralVideoSubmit

logger = get_logger(__name__)


class ViralAnalysisState(TypedDict, total=False):
    """State for the viral analysis LangGraph."""

    url: str
    platform: str | None
    category: str | None
    analysis_mode: str
    extract_patterns: bool
    # Pipeline results
    download_result: dict | None
    shots: list[dict] | None
    keyframes: list[dict] | None
    transcript: str | None
    audio_analysis: dict | None
    llm_analysis: dict | None
    viral_score: float | None
    patterns: list[dict] | None
    # Final result
    result: ViralAnalysisResult | None
    error: str | None
    progress: float
    stage: str


class ViralAnalyzerAgent:
    """
    Agent that analyzes viral videos using the video tools pipeline.
    Can be used directly (await agent.analyze(url)) or integrated into LangGraph.
    """

    def __init__(self, pipeline=None, llm_gateway=None):
        self.pipeline = pipeline
        self.llm_gateway = llm_gateway

    async def analyze(
        self,
        request: ViralVideoSubmit,
        on_progress=None,
    ) -> ViralAnalysisResult:
        """
        Full analysis of a video URL.

        Args:
            request: ViralVideoSubmit with url and options
            on_progress: Optional callback(progress_pct, stage, message)

        Returns:
            ViralAnalysisResult with complete structured analysis
        """
        from src.video_tools.pipeline import VideoAnalysisPipeline

        pipeline = self.pipeline or VideoAnalysisPipeline(
            asr_engine="whisper",
            scene_mode=request.analysis_mode,
            llm_gateway=self.llm_gateway,
            on_progress=lambda p: on_progress(p.progress, p.stage, p.message) if on_progress else None,
        )

        try:
            result = await pipeline.analyze(
                url=str(request.url),
                extract_patterns=request.extract_patterns,
            )
            # A failed download is represented as a result with an error field
            # by the pipeline rather than as an exception. Treat it as a real
            # task failure so ARQ does not report an unusable analysis as
            # ``completed`` and callers can retry it.
            download_error = result.model_info.get("download_error")
            if download_error:
                raise RuntimeError(f"video download failed: {download_error}")
            result.platform = request.platform or result.platform
            if request.category:
                result.model_info["category"] = request.category
            return result
        except Exception as e:
            logger.error(f"Viral analysis failed: {e}", exc_info=True)
            # Let the API/ARQ caller persist a failed task state. Returning an
            # error-shaped success result makes polling clients believe the
            # analysis completed successfully.
            raise

    def to_storage_dict(self, result: ViralAnalysisResult) -> dict[str, Any]:
        """Convert analysis result to database storage format."""
        return {
            "url": result.url,
            "platform": result.platform,
            "video_id": result.video_id,
            "title": result.title,
            "description": result.description,
            "duration": result.duration,
            "width": result.width,
            "height": result.height,
            "aspect_ratio": result.aspect_ratio,
            "transcript": result.transcript,
            "shot_count": len(result.shots),
            "avg_shot_duration": self._avg_shot_duration(result.shots),
            "hook_text": result.hook.hook_text if result.hook else None,
            "hook_type": result.hook.hook_type if result.hook else None,
            "hook_engagement_score": result.hook.engagement_score if result.hook else None,
            "narrative_structure": result.narrative.model_dump() if result.narrative else {},
            "visual_language": result.visual.model_dump() if result.visual else {},
            "rhythm_analysis": result.audio.model_dump() if result.audio else {},
            "emotion_curve": result.emotion_curve,
            "viral_score": result.viral_score,
            "analysis": result.viral_score_breakdown,
            # ``keyframe_paths`` is a list of local paths, not dictionaries.
            # Prefer a public URL when one exists on ShotData and fall back to
            # the local path so this conversion never raises ``AttributeError``.
            "keyframe_urls": [
                shot.keyframe_url or shot.keyframe_path
                for shot in result.shots
                if shot.keyframe_url or shot.keyframe_path
            ],
            "patterns": [p.model_dump() for p in result.patterns],
            "analyzed_at": datetime.now(),
            "analysis_version": result.analysis_version,
            "summary": result.summary,
        }

    def _avg_shot_duration(self, shots: list[Any]) -> float:
        if not shots:
            return 0
        return float(sum(float(s.duration) for s in shots) / len(shots))
