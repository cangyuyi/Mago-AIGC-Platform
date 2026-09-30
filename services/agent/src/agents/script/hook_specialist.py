"""HookSpecialistAgent - Generates and selects the best hook variants."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

from src.agents.base import BaseAgent
from src.knowledge.loader import get_hooks

HOOK_SYSTEM_PROMPT = """你是一位顶级短视频钩子设计专家，精通100+种钩子套路。

你的任务是为给定的脚本创意设计【3个不同类型的候选钩子】，每个钩子必须：
1. 在3秒内能说完（中文≤25字）
2. 能立刻抓住观众注意力
3. 类型互不相同（不要3个都是提问式）

## 输出格式（严格JSON）
{
  "selected_hook_type": "最佳钩子类型",
  "hook_variants": [
    {
      "hook_type": "钩子类型ID",
      "text": "钩子文案（≤25字）",
      "word_count": 12,
      "estimated_attention_score": 8.5,
      "rationale": "为什么这个钩子能抓住人"
    }
  ],
  "recommended_index": 0
}

## 可选择的钩子类型（必须从中选择）
{hook_types}

## 约束
- 3个钩子必须来自不同的category type（如question/shock/curiosity/number/pain_point/story/demo/resonance/trend/authority）
- 每条文案字数必须在8-25字之间
- estimated_attention_score 0-10分，诚实评估
- 严格输出JSON，不要markdown标记
"""


class HookSpecialistAgent(BaseAgent):
    name = "hook_specialist"
    description = "Designs and selects optimal hook variants"

    def system_prompt(self) -> str:
        hooks_data = get_hooks()
        types = []
        for cat in hooks_data.get("categories", []):
            types.append(f"  - {cat['type']}: {cat['name']}（{len(cat.get('templates', []))}种模板）")
        return HOOK_SYSTEM_PROMPT.format(hook_types="\n".join(types))

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief = state.get("creative_brief", {})
        self.logger.info("hook_start", angle=brief.get("angle_title", ""))

        prompt = f"""创意简报:
标题: {brief.get("angle_title", "")}
核心概念: {brief.get("core_concept", "")}
钩子策略: {brief.get("hook_strategy", "")}
目标情绪: {brief.get("target_emotion", "")}
目标时长: {brief.get("target_duration_sec", 30)}秒
平台: {brief.get("target_platform", "douyin")}

请设计3个候选钩子。"""

        if not self.llm_available:
            result = self._offline_hooks(brief)
        else:
            response_text = await self.call_llm(
                user_message=prompt,
                temperature=0.8,
                response_format={"type": "json_object"},
            )
            result = self._parse_hooks(response_text)

        for v in result.get("hook_variants", []):
            if not v.get("id"):
                v["id"] = str(uuid4())[:8]

        return {
            "hook_result": result,
            "current_step": "hooks_complete",
        }

    def _parse_hooks(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(text.strip()))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("hook_parse_error", error=str(e))
            return self._offline_hooks({})

    def _offline_hooks(self, brief: dict[str, Any]) -> dict[str, Any]:
        title = brief.get("angle_title", "这个视频")
        elements = [str(item) for item in brief.get("key_elements", []) if item]
        topic = elements[0] if elements else title[:18]
        return {
            "selected_hook_type": "question",
            "hook_variants": [
                {
                    "id": str(uuid4())[:8],
                    "hook_type": "question",
                    "text": f"{topic}怎么拍，才能有这种清晨专注感？",
                    "word_count": 16,
                    "estimated_attention_score": 7.8,
                    "rationale": "把用户主题和明确结果绑定，直接建立观看期待。",
                },
                {
                    "id": str(uuid4())[:8],
                    "hook_type": "visual",
                    "text": f"先看成片：{topic}的质感，来自这三个瞬间。",
                    "word_count": 15,
                    "estimated_attention_score": 8.2,
                    "rationale": "先展示结果再倒叙过程，适合短视频前三秒留人。",
                },
                {
                    "id": str(uuid4())[:8],
                    "hook_type": "process",
                    "text": f"从第一步到成片，{topic}只需要抓住这几个细节。",
                    "word_count": 17,
                    "estimated_attention_score": 7.4,
                    "rationale": "承诺清晰的过程拆解，适合教程和幕后记录。",
                },
            ],
            "recommended_index": 1,
        }
