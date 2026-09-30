"""
Video analysis pipeline.
Orchestrates: Download → SceneDetect → KeyframeExtract → ASR → AudioAnalysis → OCR
→ Multimodal LLM Analysis → Pattern Extraction → Persistence
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.common.logger import get_logger
from src.schemas.trend import (
    AudioAnalysis,
    HookAnalysis,
    NarrativeStructure,
    ShotData,
    ViralAnalysisResult,
    ViralPatternSchema,
    VisualLanguage,
)
from src.video_tools.asr import ASREngine
from src.video_tools.audio_analysis import AudioAnalysisResult, AudioAnalyzer
from src.video_tools.downloader import VideoDownloader
from src.video_tools.keyframe_extractor import KeyframeExtractor
from src.video_tools.ocr import OCREngine
from src.video_tools.scene_detect import SceneDetector, Shot

logger = get_logger(__name__)


@dataclass
class PipelineProgress:
    stage: str
    progress: float  # 0-1
    message: str
    data: dict = field(default_factory=dict)


ProgressCallback = Callable[[PipelineProgress], None]


class VideoAnalysisPipeline:
    """
    Complete video analysis pipeline that coordinates all video processing tools
    and produces a structured ViralAnalysisResult.
    """

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        work_dir: str = "/tmp/mago_analysis",
        asr_engine: str = "whisper",
        scene_mode: str = "fast",
        on_progress: ProgressCallback | None = None,
        llm_gateway: Any | None = None,
    ):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.downloader = VideoDownloader(output_dir=str(self.work_dir / "videos"), ffmpeg_path=ffmpeg_path)
        self.scene_detector = SceneDetector(mode=scene_mode)
        self.keyframe_extractor = KeyframeExtractor(
            output_dir=str(self.work_dir / "keyframes"), ffmpeg_path=ffmpeg_path
        )
        self.asr = ASREngine(engine=asr_engine, model_size="base")
        self.audio_analyzer = AudioAnalyzer()
        self.ocr = OCREngine()
        self.llm_gateway = llm_gateway
        self.on_progress = on_progress

    async def analyze(
        self,
        url: str,
        extract_patterns: bool = True,
        max_duration: int = 300,
    ) -> ViralAnalysisResult:
        """
        Run full analysis pipeline on a video URL.

        Stages:
        1. Download video + audio
        2. Scene detection
        3. Keyframe extraction
        4. ASR transcription
        5. Audio analysis (BPM, rhythm)
        6. OCR on keyframes
        7. Multimodal LLM visual analysis
        8. Hook analysis
        9. Narrative structure
        10. Pattern extraction
        11. Viral score calculation
        12. Cleanup
        """
        start_time = time.time()
        video_id = f"vid_{int(time.time())}"

        result = ViralAnalysisResult(url=url, analysis_version="v2")

        def _progress(stage: str, pct: float, msg: str, **extra):
            logger.info(f"[pipeline] {stage} ({pct * 100:.0f}%): {msg}")
            if self.on_progress:
                self.on_progress(PipelineProgress(stage=stage, progress=pct, message=msg, data=extra))

        # Stage 1: Download
        _progress("download", 0.0, "Starting download")
        dl = await self.downloader.download(url, extract_audio=True, max_duration=max_duration)
        if not dl.success:
            result.model_info["download_error"] = dl.error
            return result
        _progress("download", 0.1, f"Downloaded: {dl.title} ({dl.duration}s)")

        result.video_id = dl.video_id
        result.platform = dl.platform
        result.title = dl.title
        result.description = dl.description
        result.duration = dl.duration
        result.width = dl.width
        result.height = dl.height
        if dl.width and dl.height:
            ratio = dl.width / dl.height
            if 0.5 < ratio < 0.7:
                result.aspect_ratio = "9:16"
            elif 0.8 < ratio < 1.2:
                result.aspect_ratio = "1:1"
            else:
                result.aspect_ratio = "16:9"

        # Stage 2: Scene detection
        _progress("scene_detect", 0.15, "Detecting scenes...")
        shots = []
        if dl.video_path and os.path.exists(dl.video_path):
            shots = await self.scene_detector.detect(dl.video_path)
        result.keyframe_paths = []
        _progress("scene_detect", 0.25, f"Detected {len(shots)} shots")

        # Stage 3: Keyframe extraction
        _progress("keyframes", 0.25, "Extracting keyframes...")
        keyframes = []
        if dl.video_path and os.path.exists(dl.video_path):
            keyframes = await self.keyframe_extractor.extract_keyframes(
                dl.video_path, shots, video_id=dl.video_id or video_id
            )
            result.keyframe_paths = [kf["path"] for kf in keyframes]
        _progress("keyframes", 0.35, f"Extracted {len(keyframes)} keyframes")

        # Stage 4: ASR
        _progress("asr", 0.35, "Running speech recognition...")
        transcript_text = ""
        transcript_words = []
        if dl.audio_path and os.path.exists(dl.audio_path):
            asr_result = await self.asr.transcribe(dl.audio_path)
            transcript_text = asr_result.text
            transcript_words = [
                {"word": w.word, "start": w.start, "end": w.end, "confidence": w.confidence} for w in asr_result.words
            ]
            result.transcript = transcript_text
        _progress("asr", 0.5, f"Transcribed {len(transcript_words)} words")

        # Stage 5: Audio analysis
        _progress("audio", 0.5, "Analyzing audio...")
        audio_result = AudioAnalysisResult()
        if dl.audio_path and os.path.exists(dl.audio_path):
            audio_result = await self.audio_analyzer.analyze(dl.audio_path)
            result.audio = AudioAnalysis(
                bpm=audio_result.bpm,
                bpm_category=audio_result.bpm_category,
                emotion=audio_result.emotion,
                onset_curve=audio_result.onset_curve[:300],  # limit points
                speech_to_music_ratio=audio_result.speech_ratio,
                has_voiceover=audio_result.speech_ratio > 0.3,
            )
        _progress("audio", 0.6, f"Audio analyzed: BPM={audio_result.bpm:.0f}")

        # Stage 6: Build shot data
        _progress("shots", 0.6, "Assembling shot data...")
        shot_data_list = await self._build_shot_data(shots, keyframes, transcript_words, dl.video_path)
        result.shots = shot_data_list

        # Stage 7: Multimodal LLM analysis
        _progress("multimodal", 0.7, "Running multimodal analysis...")
        if self.llm_gateway and keyframes:
            try:
                llm_analysis = await self._run_multimodal_analysis(
                    keyframes[:8],  # Analyze first 8 keyframes max (cost control)
                    transcript_text,
                    audio_result,
                    shots,
                    result.duration or 0,
                )
                result.hook = llm_analysis.get("hook")
                result.narrative = llm_analysis.get("narrative")
                result.visual = llm_analysis.get("visual")
                result.summary = llm_analysis.get("summary")
                result.patterns = llm_analysis.get("patterns", [])
                result.emotion_curve = llm_analysis.get("emotion_curve", [])
            except Exception as e:
                logger.error(f"Multimodal analysis failed: {e}")
                result.model_info["multimodal_error"] = str(e)

        # Fallback: compute hook/narrative from data if LLM failed
        if not result.hook and transcript_words:
            result.hook = self._extract_hook_basic(transcript_text, transcript_words, shots, audio_result)
        if not result.narrative and shots:
            avg_dur = self.scene_detector.get_average_shot_duration(shots)
            result.narrative = NarrativeStructure(
                structure_type="hook-body-cta",
                total_duration=result.duration or sum(s.duration for s in shots),
                hook_duration=min(3.0, sum(s.duration for s in shots[:3])),
                body_duration=result.duration or 0,
                cta_duration=2.0,
                pacing_type=self.scene_detector.get_pacing_type(avg_dur),
            )
        if not result.visual and shots:
            avg_dur = self.scene_detector.get_average_shot_duration(shots)
            result.visual = VisualLanguage(
                dominant_style="待分析",
                color_grading="待分析",
                lighting_setup="待分析",
                average_shot_duration=avg_dur,
            )

        # Stage 8: Rhythm curve
        result.rhythm_curve = self._build_rhythm_curve(shots, audio_result, result.duration or 0)

        # Stage 9: Viral score
        result.viral_score, result.viral_score_breakdown = self._calculate_viral_score(result, shots, audio_result)

        # Stage 10: Pattern extraction (rule-based fallback)
        if not result.patterns:
            result.patterns = self._extract_patterns_basic(result, shots, audio_result)

        # Update result metadata
        result.model_info = {
            "asr_engine": "whisper",
            "scene_mode": self.scene_detector.mode,
            "total_duration_sec": result.duration or 0,
            "shot_count": len(shots),
            "processing_time_sec": time.time() - start_time,
        }

        # Stage 11: Cleanup
        _progress("cleanup", 0.95, "Cleaning up temporary files...")
        await self.downloader.cleanup(dl.video_path or "", dl.audio_path or "")

        _progress(
            "done", 1.0, f"Analysis complete in {time.time() - start_time:.1f}s, viral score: {result.viral_score:.0f}"
        )
        return result

    async def _build_shot_data(
        self,
        shots: list[Shot],
        keyframes: list[dict],
        transcript_words: list[dict],
        video_path: str | None,
    ) -> list[ShotData]:
        """Build structured shot data combining detection results."""
        kf_map = {kf["shot_index"]: kf for kf in keyframes}
        shot_data = []

        for shot in shots:
            # Words in this shot's time range
            shot_words = [
                w for w in transcript_words if w["start"] >= shot.start_time and w["end"] <= shot.end_time + 0.3
            ]
            shot_transcript = "".join(w["word"] for w in shot_words)

            # Motion intensity estimation (simple frame diff for keyframes, fallback 0)
            motion = 0.3  # default
            kf = kf_map.get(shot.index)

            # Detect if audio is speech/music at this time
            audio_type = "speech" if shot_words else "music"

            sd = ShotData(
                shot_index=shot.index,
                start_time=round(shot.start_time, 2),
                end_time=round(shot.end_time, 2),
                duration=round(shot.duration, 2),
                keyframe_path=kf["path"] if kf else None,
                transcript=shot_transcript or None,
                transcript_words=shot_words,
                transition_type=shot.transition_type,
                audio_type=audio_type,
                motion_intensity=motion,
            )
            shot_data.append(sd)

        return shot_data

    def _extract_hook_basic(
        self, transcript: str, words: list[dict], shots: list[Shot], audio: AudioAnalysisResult
    ) -> HookAnalysis:
        """Rule-based hook extraction when LLM is not available."""
        hook_text = ""
        hook_type = "curiosity"
        hook_end = 3.0  # first 3 seconds default

        if words:
            # Get words in first 5 seconds
            early_words = [w for w in words if w["start"] < 5.0]
            hook_text = "".join(w["word"] for w in early_words)
            if not hook_text and words:
                hook_text = "".join(w["word"] for w in words[:20])

            # Detect hook type from text
            text_lower = hook_text
            if "?" in text_lower or "？" in text_lower or "怎么" in text_lower or "为什么" in text_lower:
                hook_type = "question"
            elif "!" in text_lower or "！" in text_lower or "震惊" in text_lower or "绝了" in text_lower:
                hook_type = "shock"
            elif "我" in text_lower and ("发现" in text_lower or "终于" in text_lower or "教你" in text_lower):
                hook_type = "story"
            elif any(c.isdigit() for c in text_lower):
                hook_type = "number"

        # Hook engagement based on audio energy in first 3 seconds
        engagement = min(1.0, 0.5 + (audio.avg_onset_strength * 0.5))

        # Detect first cut point as hook end
        if len(shots) > 1:
            hook_end = min(shots[0].end_time, 5.0)

        return HookAnalysis(
            hook_text=hook_text[:200] if hook_text else "（未检测到语音）",
            hook_type=hook_type,
            hook_end_time=hook_end,
            engagement_score=round(engagement, 2),
            techniques_used=[f"开场{hook_type}"],
        )

    def _build_rhythm_curve(self, shots: list[Shot], audio: AudioAnalysisResult, duration: float) -> list[dict]:
        """Build combined rhythm curve from shots and audio onset."""
        curve: list[dict[str, float]] = []
        if not shots:
            return curve
        # Create per-second rhythm intensity
        n_points = max(30, int(duration))
        if duration <= 0:
            return curve
        for i in range(n_points):
            t = (i / max(n_points - 1, 1)) * duration
            # Shot density (how many shot cuts near this time)
            cut_density = sum(1 for s in shots if abs(s.start_time - t) < 1.0) / 3.0
            # Audio onset
            onset_idx = min(int((t / max(duration, 1)) * len(audio.onset_curve)), len(audio.onset_curve) - 1)
            onset = audio.onset_curve[onset_idx] if audio.onset_curve and onset_idx >= 0 else 0
            curve.append(
                {
                    "time": round(t, 1),
                    "shot_cut_intensity": min(1.0, cut_density),
                    "audio_onset": float(onset),
                    "combined_rhythm": min(1.0, (cut_density * 0.4 + float(onset) * 0.6)),
                }
            )
        return curve

    def _calculate_viral_score(
        self, result: ViralAnalysisResult, shots: list[Shot], audio: AudioAnalysisResult
    ) -> tuple[float, dict]:
        """Calculate viral potential score (0-100) based on multiple signals."""
        scores: dict[str, float] = {}

        # Hook quality (0-25)
        hook_score = 0.0
        if result.hook:
            hook_score = result.hook.engagement_score * 25
        scores["hook_quality"] = round(hook_score, 1)

        # Pacing (0-20): fast cuts often correlate with short-video virality
        avg_dur = self.scene_detector.get_average_shot_duration(shots) if shots else 5
        if avg_dur < 1.5:
            pacing_score = 20
        elif avg_dur < 2.5:
            pacing_score = 16
        elif avg_dur < 4:
            pacing_score = 12
        else:
            pacing_score = 6
        scores["pacing"] = pacing_score

        # Audio engagement (0-20): high BPM/onset = more engaging
        audio_score = min(20, 10 + audio.avg_onset_strength * 20)
        scores["audio_engagement"] = round(audio_score, 1)

        # Narrative clarity (0-15)
        narr_score = 10.0  # default
        if result.narrative and result.narrative.structure_type != "unknown":
            narr_score = 13
        if result.transcript and len(result.transcript) > 50:
            narr_score += 2
        scores["narrative_clarity"] = narr_score

        # Visual quality (0-20)
        vis_score = 12.0  # default
        if result.visual and result.visual.dominant_style != "待分析":
            vis_score = 16
        if len(shots) > 5:
            vis_score += 2
        scores["visual_quality"] = min(20, vis_score)

        total = sum(scores.values())
        return round(min(100, total), 1), scores

    def _extract_patterns_basic(
        self, result: ViralAnalysisResult, shots: list[Shot], audio: AudioAnalysisResult
    ) -> list[ViralPatternSchema]:
        """Rule-based pattern extraction when LLM is unavailable."""
        patterns = []
        avg_dur = self.scene_detector.get_average_shot_duration(shots) if shots else 5

        # Fast cut pattern
        if avg_dur < 1.8 and len(shots) >= 8:
            patterns.append(
                ViralPatternSchema(
                    name="快切节奏型",
                    pattern_type="editing",
                    description=f"平均镜头时长{avg_dur:.1f}秒，快速切换保持注意力",
                    confidence=0.7,
                    key_phrases=[],
                )
            )

        # Question hook pattern
        if result.hook and result.hook.hook_type == "question":
            patterns.append(
                ViralPatternSchema(
                    name="提问式开头",
                    pattern_type="hook",
                    description="以问题开场引发好奇，提升完播率",
                    confidence=0.8,
                    key_phrases=[result.hook.hook_text[:30]],
                )
            )

        # High BGM pattern
        if audio.bpm > 120:
            patterns.append(
                ViralPatternSchema(
                    name="高BGM节奏",
                    pattern_type="audio",
                    description=f"BPM={audio.bpm:.0f}的{audio.emotion}背景音乐，提升情绪感染力",
                    confidence=0.6,
                )
            )

        return patterns

    async def _run_multimodal_analysis(
        self,
        keyframes: list[dict],
        transcript: str,
        audio: AudioAnalysisResult,
        shots: list[Shot],
        duration: float,
    ) -> dict:
        """Run multimodal LLM analysis on keyframes + transcript.
        In production, calls GPT-4o/Claude/Qwen-VL with image inputs.
        Returns structured analysis dict."""
        # This requires the LLM gateway to support multimodal inputs
        # For MVP, return a structured analysis prompt template that can be filled in
        if not self.llm_gateway:
            return {}

        try:
            # Build analysis prompt
            self._build_analysis_prompt(keyframes, transcript, audio, shots, duration)
            # Call LLM (implementation depends on llm_gateway)
            # response = await self.llm_gateway.agenerate(prompt, images=[kf["path"] for kf in keyframes])
            # parsed = json.loads(response)
            # return self._parse_llm_response(parsed)
            logger.info("Multimodal LLM analysis called (gateway integration pending)")
            return {}
        except Exception as e:
            logger.error(f"Multimodal LLM call failed: {e}")
            return {}

    def _build_analysis_prompt(self, keyframes, transcript, audio, shots, duration) -> str:
        """Build structured prompt for multimodal video analysis."""
        return f"""你是一位专业的短视频内容分析师。请分析以下视频的完整内容，输出结构化的爆款分析报告。

视频信息：
- 时长：{duration:.1f}秒
- 镜头数：{len(shots)}个
- 平均镜头时长：{self.scene_detector.get_average_shot_duration(shots):.2f}秒
- 背景音乐BPM：{audio.bpm:.0f}
- 音频情绪：{audio.emotion}
- ASR转写文本：{transcript[:2000]}

请按以下JSON结构输出分析结果：
{{
  "hook": {{
    "hook_text": "开头钩子文字",
    "hook_type": "question/shock/contrast/story/number/demo/curiosity/pain_point",
    "hook_end_time": 3.5,
    "engagement_score": 0.85,
    "techniques_used": ["技巧1", "技巧2"],
    "improvement_suggestions": ["建议1"]
  }},
  "narrative": {{
    "structure_type": "hook-body-cta/problem-solution/countdown/story/tutorial/reaction",
    "total_duration": {duration},
    "hook_duration": 3.0,
    "body_duration": {duration - 5},
    "cta_duration": 2.0,
    "pacing_type": "fast_cut/medium/slow_build",
    "tension_curve": []
  }},
  "visual": {{
    "dominant_style": "视觉风格描述",
    "color_grading": "色彩风格",
    "lighting_setup": "布光方式",
    "camera_movements": [],
    "composition_rules": [],
    "shot_types_used": {{"close_up": 0.3}},
    "average_shot_duration": 2.1,
    "key_visual_motifs": [],
    "subtitle_style": "字幕风格"
  }},
  "patterns": [
    {{
      "name": "模式名称",
      "pattern_type": "hook/narrative/editing/audio/visual/structure",
      "description": "模式描述",
      "formula_template": "可复用模板",
      "confidence": 0.8,
      "key_phrases": []
    }}
  ],
  "emotion_curve": [{{"time": 0, "emotion": "curious", "intensity": 0.7}}],
  "summary": "一句话总结视频为什么可能爆款"
}}"""
