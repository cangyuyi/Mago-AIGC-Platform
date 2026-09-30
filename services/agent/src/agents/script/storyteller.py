"""StorytellerAgent - Writes the full script with beats, body, and CTA."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

from src.agents.base import BaseAgent
from src.common.streaming import emit_thinking

STORYTELLER_SYSTEM_PROMPT = """你是一位顶级短视频编剧，擅长写抖音/快手/小红书爆款短视频脚本。

用户给你一份创意简报+选定的钩子，你要输出完整脚本。

## 输出格式（严格JSON）
{
  "title": "脚本标题",
  "structure_id": "叙事结构ID",
  "hook": "最终钩子文案",
  "hook_type": "钩子类型",
  "body_text": "正文完整文案（纯文字，包含所有旁白/台词）",
  "cta": "CTA文案（结尾号召行动）",
  "cta_type": "CTA类型",
  "beats": [
    {
      "index": 0,
      "phase": "hook/body/twist/climax/cta",
      "duration_sec": 3.0,
      "content": "本段旁白/台词文字",
      "visual_note": "画面提示",
      "emotion": "情绪描述",
      "sound_design": "音效提示"
    }
  ],
  "emotion_curve_id": "情绪曲线ID",
  "rhythm_pattern_id": "节奏模式ID",
  "key_message": "核心想传达的一句话",
  "tags": ["标签1","标签2"]
}

## 约束
- beats必须按时间顺序排列，duration_sec之和等于target_duration_sec
- hook beat 必须在前3秒
- 最后一个beat必须是CTA
- body_text是完整的旁白/台词文字（所有beat的content合并），口播速度约4字/秒
- 节奏必须有变化，不能从头到尾一个语速
- 严格输出JSON，不要markdown标记
"""


class StorytellerAgent(BaseAgent):
    name = "storyteller"
    description = "Writes complete video scripts with beats"

    def system_prompt(self) -> str:
        return STORYTELLER_SYSTEM_PROMPT

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief = state.get("creative_brief", {})
        hook_result = state.get("hook_result", {})
        hooks = hook_result.get("hook_variants", [])
        rec_idx = hook_result.get("recommended_index", 0)
        selected_hook = hooks[rec_idx] if hooks and rec_idx < len(hooks) else {}
        user_modifications = state.get("user_modifications", "")

        self.logger.info("storyteller_start", title=brief.get("angle_title", ""))
        emit_thinking(self.name, "正在撰写完整脚本…")

        prompt = f"""创意简报:
标题: {brief.get("angle_title", "")}
核心概念: {brief.get("core_concept", "")}
目标情绪: {brief.get("target_emotion", "")}
目标时长: {brief.get("target_duration_sec", 30)}秒
平台: {brief.get("target_platform", "douyin")}
语调指引: {brief.get("tone_guide", "")}
关键元素: {", ".join(brief.get("key_elements", []))}

选定钩子: {selected_hook.get("text", "")} (类型: {selected_hook.get("hook_type", "")})

{f"用户修改要求: {user_modifications}" if user_modifications else ""}

请输出完整脚本JSON。"""

        if not self.llm_available:
            script = self._offline_script(brief, selected_hook)
        else:
            # Stream the script as it is written so the UI shows progress instead
            # of freezing until the whole JSON object is finished.
            response_text = await self.call_llm_streaming(user_message=prompt, temperature=0.75)
            script = self._parse_script(response_text)

        script["id"] = str(uuid4())[:8]
        script["word_count"] = len(script.get("body_text", ""))
        total_dur = sum(b.get("duration_sec", 0) for b in script.get("beats", []))
        script["actual_duration_sec"] = total_dur
        script["target_duration_sec"] = brief.get("target_duration_sec", 30)
        script["script_type"] = "oral_story"

        return {
            "script": script,
            "current_step": "script_complete",
            "steps_completed": state.get("steps_completed", []) + ["script"],
            "hitl_required": True,
            "hitl_node": "script_review",
        }

    def _parse_script(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(text.strip()))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("script_parse_error", error=str(e))
            return self._offline_script({}, {})

    def _offline_script(self, brief: dict[str, Any], hook: dict[str, Any]) -> dict[str, Any]:
        title = brief.get("angle_title", "短视频")
        elements = [str(item) for item in brief.get("key_elements", []) if item]
        topic = elements[0] if elements else title[:18]
        hook_text = hook.get("text", f"{topic}怎么拍，才能有这种质感？")
        cta = f"把{topic}的成片发在评论区，告诉我你最喜欢哪个镜头。"
        beats = [
            ("hook", 3.0, hook_text, f"{topic}成品特写，先给结果再快速切回起点", "好奇", "轻微提示音"),
            ("body", 6.0, f"先准备好{topic}，把环境收拾干净，留出一束自然光。", f"环境建立镜头，交代{topic}、桌面和清晨光线", "期待", "环境底噪"),
            ("body", 8.0, "拍摄过程中只抓三个细节：动作、声音，以及光线落下来的位置。", f"手部和过程特写，跟随{topic}的关键步骤移动", "专注", "节奏轻快的BGM"),
            ("climax", 8.0, "把过程镜头按由慢到快的节奏剪起来，再用一个成品特写收住画面。", "过程与成片前后对照，画面节奏逐渐加快", "满足", "BGM进入高潮"),
            ("cta", 5.0, cta, "回到成品全景，叠加简洁文字CTA", "温暖", "BGM渐弱"),
        ]
        body_text = "".join(item[2] for item in beats)
        return {
            "title": title,
            "structure_id": brief.get("structure_type", "struct_hook_body_cta"),
            "hook": hook_text,
            "hook_type": hook.get("hook_type", "question"),
            "body_text": body_text,
            "cta": cta,
            "cta_type": "action",
            "beats": [
                {
                    "index": index,
                    "phase": phase,
                    "duration_sec": duration,
                    "content": content,
                    "visual_note": visual_note,
                    "emotion": emotion,
                    "sound_design": sound,
                }
                for index, (phase, duration, content, visual_note, emotion, sound) in enumerate(beats)
            ],
            "emotion_curve_id": "emotion_staircase_up",
            "rhythm_pattern_id": "rhythm_medium",
            "key_message": f"用镜头讲清楚{topic}从过程到成片的变化",
            "tags": brief.get("key_elements", [topic, "过程记录"]),
        }
