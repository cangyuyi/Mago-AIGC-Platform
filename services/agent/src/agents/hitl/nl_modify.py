"""Natural Language Modification Agent - applies user feedback to scripts/storyboards.

Interprets commands like:
- "钩子改得更幽默点"
- "缩短到30秒"
- "第3镜换成特写"
- "整体色调改成暖色"
- "CTA换成引导关注"

Returns incremental modifications rather than regenerating from scratch.
"""

from __future__ import annotations

import json
from typing import Any, cast

from src.agents.base import BaseAgent

NL_MODIFY_PROMPT = """你是一位脚本修改助手。用户会用自然语言提出修改要求，你要把它转化为对脚本/分镜的具体修改。

## 输出格式（严格JSON）
{
  "modifications": [
    {
      "target": "hook|body|cta|beat|shot|structure|duration|emotion|tone|all",
      "target_index": null,
      "field": "要修改的字段名或'content'",
      "action": "replace|append|prepend|delete|reorder|adjust_duration|change_shot_size|change_angle|change_movement|change_lighting|change_color",
      "old_value": "修改前的内容（用于diff展示，可空）",
      "new_value": "修改后的内容",
      "reason": "为什么这样改"
    }
  ],
  "explanation": "一句话解释这次改了什么",
  "requires_regeneration": false
}

## 常见修改模式
- "钩子更幽默" → target=hook, action=replace, new_value=更幽默的钩子文案
- "缩短到30秒" → target=all, action=adjust_duration, 调整各镜时长
- "第3镜换特写" → target=shot, target_index=3, field=shot_size, action=change_shot_size
- "加一个反转" → target=beat, action=append, 在body段加入反转beat
- "色调改暖色" → target=shot或all, field=color_tone
- "CTA改成关注我" → target=cta, action=replace

严格输出JSON。
"""

# Common keyword patterns for offline rule-based modification
MODIFICATION_PATTERNS = [
    {"keywords": ["缩短", "压到", "时长", "秒"], "target": "duration", "action": "adjust_duration"},
    {"keywords": ["幽默", "搞笑", "有趣"], "target": "tone", "action": "adjust_tone"},
    {"keywords": ["特写", "近景", "中景", "全景", "远景"], "target": "shot", "action": "change_shot_size"},
    {"keywords": ["钩子", "开头"], "target": "hook", "action": "modify"},
    {"keywords": ["结尾", "cta", "关注", "点赞", "收藏", "评论"], "target": "cta", "action": "replace"},
    {"keywords": ["暖", "冷", "色调", "颜色"], "target": "color", "action": "change_color"},
    {"keywords": ["反转", "加一个", "加入"], "target": "beat", "action": "append"},
    {"keywords": ["删除", "去掉", "不要"], "target": "beat", "action": "delete"},
]


class NLModifyAgent(BaseAgent):
    name = "nl_modifier"
    description = "Applies natural language modifications to scripts and storyboards"

    def system_prompt(self) -> str:
        return NL_MODIFY_PROMPT

    async def modify(
        self, feedback: str, script: dict[str, Any] | None = None, storyboard: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Parse user feedback and produce structured modifications."""
        if not self.llm_available:
            return self._rule_based_modify(feedback, script, storyboard)
        context = f"用户反馈: {feedback}\n\n当前脚本: {json.dumps(script or {}, ensure_ascii=False)[:2000]}"
        resp = await self.call_llm(user_message=context, temperature=0.3, response_format={"type": "json_object"})
        return self._parse(resp)

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        feedback = state.get("user_modifications", "")
        if not feedback:
            return state
        result = await self.modify(feedback, state.get("script"), state.get("storyboard"))
        modifications = result.get("modifications", [])
        return {
            "modifications": modifications,
            "modification_explanation": result.get("explanation", ""),
            "requires_regeneration": result.get("requires_regeneration", False),
            "current_step": "modifications_applied",
            "steps_completed": state.get("steps_completed", []) + ["nl_modify"],
        }

    def _parse(self, text: str) -> dict[str, Any]:
        try:
            t = text.strip()
            if t.startswith("```"):
                t = t.split("\n", 1)[1]
            if t.endswith("```"):
                t = t.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(t.strip()))
        except Exception as e:
            self.logger.error("nlmod_parse_error", error=str(e))
            return {"modifications": [], "explanation": "", "requires_regeneration": True}

    def _rule_based_modify(self, feedback: str, script: dict | None, storyboard: dict | None) -> dict[str, Any]:
        """Simple keyword-based modification detection for offline mode."""
        mods = []
        for pat in MODIFICATION_PATTERNS:
            for kw in pat["keywords"]:
                if kw in feedback:
                    mods.append(
                        {
                            "target": pat["target"],
                            "action": pat["action"],
                            "new_value": feedback,
                            "reason": f"用户要求{kw}",
                        }
                    )
                    break
        if not mods:
            mods.append(
                {
                    "target": "script",
                    "action": "regenerate",
                    "new_value": feedback,
                    "reason": "需要重新生成以满足修改要求",
                }
            )
        return {
            "modifications": mods,
            "explanation": f"根据「{feedback}」进行修改",
            "requires_regeneration": any(m["action"] == "regenerate" for m in mods),
        }

    def apply_modifications_to_script(self, script: dict[str, Any], mods: list[dict]) -> dict[str, Any]:
        """Apply modifications to a script dict (MVP: handles hook/cta/body replace)."""
        import copy

        s = copy.deepcopy(script)
        s["version"] = s.get("version", 1) + 1
        for m in mods:
            if m["target"] == "hook" and m.get("new_value"):
                s["hook"] = m["new_value"]
            elif m["target"] == "cta" and m.get("new_value"):
                s["cta"] = m["new_value"]
            elif m["target"] == "duration" and m.get("new_value"):
                import re

                nums = re.findall(r"\d+", str(m["new_value"]))
                if nums:
                    s["target_duration_sec"] = int(nums[0])
        return s

    def apply_modifications_to_storyboard(self, storyboard: dict[str, Any], mods: list[dict]) -> dict[str, Any]:
        import copy

        sb = copy.deepcopy(storyboard)
        for m in mods:
            if m["target"] == "shot" and m.get("target_index") is not None:
                idx = m["target_index"] - 1
                if 0 <= idx < len(sb.get("shots", [])):
                    shot = sb["shots"][idx]
                    if m["action"] == "change_shot_size" and m.get("new_value"):
                        shot["shot_size"] = m["new_value"]
            elif m["target"] == "color":
                for shot in sb.get("shots", []):
                    if m.get("new_value"):
                        shot["color_tone"] = m["new_value"]
        return sb
