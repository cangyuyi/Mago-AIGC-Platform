"""StoryboardAgent - Converts a script into a detailed shot-by-shot storyboard."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

from src.agents.base import BaseAgent

STORYBOARD_SYSTEM_PROMPT = """你是一位专业的影视分镜师，擅长把文字脚本转化为可执行的分镜表。

## 输出格式（严格JSON）
{
  "title": "分镜标题",
  "aspect_ratio": "9:16",
  "visual_style_notes": "整体视觉风格说明（光线/色调/质感）",
  "color_palette": ["#hex1","#hex2","#hex3"],
  "location_notes": "场景说明",
  "shots": [
    {
      "index": 1,
      "duration_sec": 3.0,
      "shot_size": "extreme_close_up/medium_close_up/close_up/medium/medium_wide/wide/extreme_wide",
      "camera_angle": "eye_level/low_angle/high_angle/birds_eye/dutch_angle/over_shoulder",
      "camera_movement": "static/push_in/pull_out/pan_left/pan_right/tilt_up/tilt_down/tracking/zoom_in/orbit/handheld/slow_motion",
      "scene_description": "场景环境描述（具体，有视觉元素）",
      "subject_description": "主体/人物描述（具体服装/表情/动作）",
      "action_description": "动作描述（具体动作步骤）",
      "visual_description": "完整画面：场景+人物+动作+光线+色调。必须具体可执行，不能出现抽象形容词如'很美''很震撼''很有感觉'",
      "dialogue": "对应台词/旁白",
      "emotion": "情绪",
      "lighting": "natural/soft_studio/dramatic_contrast/backlit_silhouette/neon_cool/golden_hour/bright_even/tungsten_warm",
      "color_tone": "warm/cool/neutral/monochrome/high_contrast/pastel",
      "transition": "cut/dissolve/fade_in/fade_out/wipe/slide_left/zoom_transition/match_cut",
      "props": ["道具1"],
      "ai_generation_difficulty": 5.0,
      "ai_warnings": [],
      "visual_keywords": ["关键词1","关键词2"]
    }
  ]
}

## 硬约束
0. shot_size / camera_angle / camera_movement / lighting / color_tone / transition 必须逐字使用上面 JSON 中列出的枚举值，禁止自造同义词（例如禁止 dolly_in、slow_push_in、soft、studio）：提示词引擎按这些键查表，写入未知值会导致镜头信息在导出提示词里丢失。
1. visual_description 中**禁止出现抽象形容词**：不能写"很美""很震撼""很有感觉""非常漂亮"。必须写具体的视觉元素：什么光线、什么颜色、什么动作、什么角度、什么物体。
2. 每个shot的index从1开始递增，不能跳号。
3. 所有shot的duration_sec之和必须约等于总目标时长。
4. shot_size必须有变化：不能所有镜头都是close_up或都是medium。
5. ai_generation_difficulty：需要真人出镜/复杂物理交互/文字精准渲染的分数高(>7)，纯画面生成的分数低(<5)。
6. 高难度镜头（>7分）必须在ai_warnings中说明原因。
7. 严格输出JSON，不要markdown标记。
"""

# Shot size durations for rhythm reference
SHOT_SIZES = ["extreme_close_up", "close_up", "medium", "medium_close_up", "wide", "extreme_wide"]
CAMERA_ANGLES = ["eye_level", "low_angle", "high_angle", "over_shoulder", "dutch_angle"]
CAMERA_MOVEMENTS = ["static", "slow_zoom_in", "pan_left", "pan_right", "tilt_up", "dolly_in", "tracking", "handheld"]
LIGHTING_TYPES = [
    "natural",
    "soft_studio",
    "dramatic_contrast",
    "backlit_silhouette",
    "golden_hour",
    "neon_cool",
    "bright_even",
]
COLOR_TONES = ["warm_peach", "cool_blue", "neutral_natural", "high_contrast_dark", "pastel_soft", "vivid_saturated"]
TRANSITIONS = ["cut", "dissolve", "fade_in", "zoom_transition", "slide_right"]


class StoryboardAgent(BaseAgent):
    name = "storyboard"
    description = "Converts scripts into detailed shot-by-shot storyboards"

    def system_prompt(self) -> str:
        return STORYBOARD_SYSTEM_PROMPT

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        script = state.get("script", {})
        brief = state.get("creative_brief", {})
        self.logger.info("storyboard_start", script_title=script.get("title", ""))

        beats = script.get("beats", [])
        beats_summary = "\n".join(
            f"Beat {b.get('index', 0)} [{b.get('phase', '')}, {b.get('duration_sec', 3)}s]: {b.get('content', '')} | 画面: {b.get('visual_note', '')}"
            for b in beats
        )

        prompt = f"""脚本标题: {script.get("title", "")}
目标时长: {script.get("target_duration_sec", 30)}秒
钩子: {script.get("hook", "")}
叙事结构: {script.get("structure_id", "")}
平台: {brief.get("target_platform", "douyin")}
垂类: {brief.get("vertical", "")}
视觉风格指引: {brief.get("tone_guide", "")}

脚本节拍:
{beats_summary}

请将以上脚本转化为详细分镜表JSON。注意：
- 根据节拍和时长合理分配镜头
- 每个beat可能对应1-3个镜头
- 景别要有变化
- visual_description必须具体，不能有抽象形容词
"""

        if not self.llm_available:
            storyboard = self._offline_storyboard(script, brief)
        else:
            response_text = await self.call_llm(
                user_message=prompt,
                temperature=0.6,
                response_format={"type": "json_object"},
            )
            storyboard = self._parse_storyboard(response_text)

        storyboard["id"] = str(uuid4())[:8]
        storyboard["script_id"] = script.get("id", "")
        total_dur = sum(s.get("duration_sec", 0) for s in storyboard.get("shots", []))
        storyboard["total_duration_sec"] = total_dur
        storyboard["shot_count"] = len(storyboard.get("shots", []))

        return {
            "storyboard": storyboard,
            "current_step": "storyboard_complete",
            "steps_completed": state.get("steps_completed", []) + ["storyboard"],
            "hitl_required": True,
            "hitl_node": "storyboard_review",
        }

    def _parse_storyboard(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(text.strip()))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("storyboard_parse_error", error=str(e))
            return self._offline_storyboard({}, {})

    def _offline_storyboard(self, script: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
        """Build an input-aware storyboard when no image/text model is configured."""
        title = script.get("title", "短视频")
        elements = [str(item) for item in brief.get("key_elements", []) if item]
        topic = elements[0] if elements else title[:18]
        beat_contents = [
            str(beat.get("content", ""))
            for beat in script.get("beats", [])
            if isinstance(beat, dict)
        ]
        dialogues = beat_contents + [
            script.get("hook", f"{topic}怎么拍？"),
            f"先准备好{topic}，再用镜头记录过程。",
            f"抓住{topic}的动作、声音和光线细节。",
            "把过程剪成有节奏的成片。",
            script.get("cta", "欢迎在评论区分享你的成片。"),
        ]
        shot_specs = [
            (3.0, "extreme_close_up", "slow_push_in", f"清晨自然光下的{topic}成品特写", f"{topic}的关键细节占满画面，背景柔和虚化，纹理清晰可见", "好奇", [topic]),
            (6.0, "wide", "slow_pan", f"干净的桌面与{topic}的环境建立镜头", f"从窗边光线扫到{topic}和主要道具，交代空间关系", "期待", [topic, "桌面", "自然光"]),
            (8.0, "close_up", "handheld_follow", f"手部正在完成{topic}的关键步骤", "镜头贴近动作，记录材质、声音和细小变化，浅景深", "专注", [topic, "手部动作"]),
            (8.0, "medium", "match_cut", f"{topic}从过程到成片的节奏化蒙太奇", "连续三个动作特写快速衔接，最后切到完成状态，与开场形成呼应", "满足", [topic, "过程剪辑", "成片"]),
            (5.0, "medium", "slow_pull_out", f"完成后的{topic}回到完整构图", "成品置于画面中心，保留清晨光影和环境留白，叠加简洁CTA", "温暖", [topic, "CTA"]),
        ]
        shots = []
        for index, (duration, shot_size, movement, scene, visual, emotion, props) in enumerate(shot_specs):
            shots.append(
                {
                    "index": index + 1,
                    "duration_sec": duration,
                    "shot_size": shot_size,
                    "camera_angle": "eye_level",
                    "camera_movement": movement,
                    "scene_description": scene,
                    "subject_description": f"{topic}及其制作过程中的关键细节",
                    "action_description": visual,
                    "visual_description": visual,
                    "dialogue": dialogues[index] if index < len(dialogues) else "",
                    "emotion": emotion,
                    "lighting": "soft_morning_natural",
                    "color_tone": "warm_neutral",
                    "transition": "cut" if index < 4 else "fade_out",
                    "props": props,
                    "ai_generation_difficulty": 4.0 if index in (0, 1, 4) else 5.0,
                    "ai_warnings": [],
                    "visual_keywords": [shot_size, "natural_light", "topic_detail", "clean_composition"],
                }
            )
        return {
            "title": f"{title} - 分镜表",
            "aspect_ratio": "9:16",
            "visual_style_notes": "清晨自然光、克制暖色、浅景深与干净构图，突出过程细节和真实质感",
            "color_palette": ["#F7F1E8", "#D8B08C", "#9C6B4E", "#5C4033", "#252525"],
            "location_notes": "靠窗的干净桌面或工作台，保留自然光方向和适度留白",
            "shots": shots,
        }
