"""DebateJudgeAgent - Mediates between multiple agent outputs to select best option.

When multiple agents (or multiple generations of the same agent) produce
conflicting outputs, the judge selects the best option based on criteria.
"""

from __future__ import annotations

import json
from typing import Any, cast

from src.agents.base import BaseAgent

JUDGE_SYSTEM_PROMPT = """你是一位创意辩论裁判（Debate Judge）。
当有多个候选方案时，你需要基于以下标准选择最优方案：
1. 钩子吸引力（最重要）
2. 目标受众匹配度
3. 执行可行性（AI生成难度）
4. 原创性/差异度
5. 情绪冲击力

## 输出格式（严格JSON）
{
  "selected_index": 0,
  "reasoning": "选择理由（2-3句话）",
  "improvement_note": "在选定方案基础上的改进建议"
}

严格输出JSON，不要markdown标记。
"""


class DebateJudgeAgent(BaseAgent):
    name = "debate_judge"
    description = "Selects best option from multiple candidates"

    def system_prompt(self) -> str:
        return JUDGE_SYSTEM_PROMPT

    async def judge_hooks(self, variants: list[dict[str, Any]], context: str) -> dict[str, Any]:
        """Select best hook variant."""
        if len(variants) <= 1:
            return {"selected_index": 0, "reasoning": "Only one option", "improvement_note": ""}

        hooks_text = "\n".join(
            f"候选{i}: {v.get('text', '')} (类型:{v.get('hook_type', '')}, 评分:{v.get('estimated_attention_score', 0)})"
            for i, v in enumerate(variants)
        )
        prompt = f"上下文: {context}\n\n候选钩子:\n{hooks_text}\n\n请选择最优钩子。"

        if not self.llm_available:
            best_idx = max(range(len(variants)), key=lambda i: variants[i].get("estimated_attention_score", 0))
            return {"selected_index": best_idx, "reasoning": "选择预估分数最高的", "improvement_note": ""}

        response_text = await self.call_llm(
            user_message=prompt,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return self._parse(response_text)

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"current_step": "judge_complete"}

    def _parse(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(text.strip()))
        except (json.JSONDecodeError, KeyError, TypeError):
            return {"selected_index": 0, "reasoning": "默认选择第一个", "improvement_note": ""}
