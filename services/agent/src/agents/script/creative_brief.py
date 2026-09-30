"""CreativeBriefAgent - Crystallizes a chosen creative idea into a concrete brief."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

from src.agents.base import BaseAgent

BRIEF_SYSTEM_PROMPT = """你是一位资深短视频创意策划师。
用户已经选定了一个创意方向，你的任务是把它深化成一份可执行的「创意简报」(Creative Brief)。

## 输出要求（严格JSON）
{
  "angle_title": "一句话创意角度标题，如：'反常识冷知识：你以为正确的化妆顺序其实是错的'",
  "core_concept": "核心创意概念，3-5句话说清楚这个视频做什么、怎么做、为什么能火",
  "hook_strategy": "钩子策略：用什么类型钩子、前3秒说什么、为什么这个钩子能抓住人",
  "target_emotion": "目标情绪基调（一个词+描述）",
  "structure_type": "选用的叙事结构ID",
  "target_duration_sec": 30,
  "target_platform": "douyin/xiaohongshu/bilibili",
  "vertical": "垂类ID（如v_beauty）",
  "key_elements": ["必须包含的关键元素1", "关键元素2"],
  "reference_videos": [],
  "tone_guide": "语调指引：如'闺蜜式亲切/专业但不端着/幽默自嘲'",
  "differentiators": ["与同类内容的差异化点1", "差异化点2"]
}

## 约束
- structure_type 从以下选择：{structure_ids}
- target_duration_sec 必须在垂类规范的ideal_duration范围内
- 所有内容用中文
- 严格输出JSON，不要markdown代码块标记
"""


class CreativeBriefAgent(BaseAgent):
    name = "creative_brief"
    description = "Crystallizes a chosen idea into a concrete creative brief"

    def system_prompt(self) -> str:
        from src.knowledge.loader import get_story_structures

        structures = get_story_structures()
        ids = [s["id"] for s in structures.get("structures", [])]
        return BRIEF_SYSTEM_PROMPT.format(structure_ids=", ".join(ids))

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        idea = state.get("selected_idea") or {}
        # Quick/full automatic runs may not persist the conditional router's
        # in-place selection back into the graph state. Fall back to the first
        # generated idea so the brief is based on the idea, not the raw prompt.
        if not idea and state.get("mode") == "quick":
            ideas = state.get("creative_ideas") or []
            if ideas and isinstance(ideas[0], dict):
                idea = ideas[0]
        user_input = state.get("current_input", "")
        self.logger.info("brief_start", idea_title=idea.get("title", ""))

        prompt_context = f"""用户原始输入: {user_input}

选定的创意方向:
标题: {idea.get("title", "")}
描述: {idea.get("description", "")}
钩子方向: {idea.get("hook_direction", "")}
情绪基调: {idea.get("emotion_tone", "")}
预估时长: {idea.get("estimated_duration", 30)}秒
标签: {", ".join(idea.get("tags", []))}

请基于以上创意方向，输出创意简报JSON。"""

        if not self.llm_available:
            brief = self._offline_brief(idea, user_input)
        else:
            response_text = await self.call_llm(
                user_message=prompt_context,
                temperature=0.6,
                response_format={"type": "json_object"},
            )
            brief = self._parse_brief(response_text)

        brief["id"] = str(uuid4())[:8]

        return {
            "creative_brief": brief,
            "current_step": "brief_complete",
            "steps_completed": state.get("steps_completed", []) + ["brief"],
            "hitl_required": True,
            "hitl_node": "brief_review",
        }

    def _parse_brief(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            data = cast(dict[str, Any], json.loads(text.strip()))
            return data
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("brief_parse_error", error=str(e))
            return self._offline_brief({}, "")

    def _offline_brief(self, idea: dict[str, Any], user_input: str) -> dict[str, Any]:
        tags = [str(tag) for tag in idea.get("tags", []) if tag]
        topic = tags[0] if tags else (user_input.strip()[:24] or "日常主题")
        topic_lower = topic.lower()
        vertical = "v_food" if any(word in topic_lower for word in ("咖啡", "美食", "饮品", "料理", "烘焙")) else "v_home"
        return {
            "angle_title": idea.get("title") or f"{topic}创意",
            "core_concept": idea.get("description") or f"围绕{topic}记录一个从过程到成片的短视频。",
            "hook_strategy": idea.get("hook_direction") or f"先展示{topic}最有质感的成品瞬间，再回到制作过程。",
            "target_emotion": idea.get("emotion_tone", "沉浸/专注"),
            "structure_type": "struct_hook_body_cta",
            "target_duration_sec": idea.get("estimated_duration", 30),
            "target_platform": "douyin",
            "vertical": vertical,
            "key_elements": [topic, "过程细节", "成片回看"],
            "reference_videos": [],
            "tone_guide": "克制、沉浸、像朋友一样分享创作过程",
            "differentiators": ["过程真实可执行", "用细节而不是夸张承诺制造记忆点"],
        }
