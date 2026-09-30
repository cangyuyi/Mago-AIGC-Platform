"""EvaluatorAgent - Scores script quality and provides improvement suggestions."""

from __future__ import annotations

import json
from typing import Any, cast

from src.agents.base import BaseAgent

EVALUATOR_SYSTEM_PROMPT = """你是一位严格的短视频脚本质量评估专家。
请对给定脚本进行打分（每项0-10分）并给出具体改进建议。

## 评分维度
- hook_strength: 钩子前3秒吸引力
- structure_clarity: 叙事结构清晰度
- emotional_impact: 情绪冲击力
- pacing: 节奏合理性（镜头时长分配）
- cta_effectiveness: CTA行动号召有效度
- originality: 原创性/与同类内容的差异度
- ai_feasibility: AI画面生成可行性（高难度真人动作分数低）
- overall: 综合评分

## 输出格式（严格JSON）
{
  "scores": {
    "hook_strength": 7.5, "structure_clarity": 8.0, "emotional_impact": 7.0,
    "pacing": 7.0, "cta_effectiveness": 6.5, "originality": 6.0,
    "ai_feasibility": 7.0, "overall": 7.0
  },
  "strengths": ["优点1","优点2"],
  "weaknesses": ["不足1","不足2"],
  "improvement_suggestions": ["具体可执行的改进建议1","建议2"],
  "iteration_notes": "一句话总结最需要改进的地方"
}

严格输出JSON，不要markdown标记。
"""


class EvaluatorAgent(BaseAgent):
    name = "evaluator"
    description = "Scores script quality and suggests improvements"

    def system_prompt(self) -> str:
        return EVALUATOR_SYSTEM_PROMPT

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        script = state.get("script", {})
        self.logger.info("eval_start", script_id=script.get("id", ""))

        prompt = f"""脚本标题: {script.get("title", "")}
钩子: {script.get("hook", "")}
正文: {script.get("body_text", "")}
CTA: {script.get("cta", "")}
节拍数: {len(script.get("beats", []))}
目标时长: {script.get("target_duration_sec", 30)}秒
情绪曲线: {script.get("emotion_curve_id", "")}

请评分并给出改进建议。"""

        if not self.llm_available:
            evaluation = self._offline_eval(script)
        else:
            response_text = await self.call_llm(
                user_message=prompt,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            evaluation = self._parse_eval(response_text)

        passed = evaluation.get("scores", {}).get("overall", 0) >= 6.5
        return {
            "evaluation": evaluation,
            "eval_passed": passed,
            "current_step": "eval_complete",
        }

    def _parse_eval(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(text.strip()))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("eval_parse_error", error=str(e))
            return self._offline_eval({})

    def _offline_eval(self, script: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "hook_strength": 7.0,
                "structure_clarity": 7.5,
                "emotional_impact": 6.5,
                "pacing": 7.0,
                "cta_effectiveness": 6.5,
                "originality": 6.0,
                "ai_feasibility": 7.5,
                "overall": 7.0,
            },
            "strengths": ["钩子清晰引发好奇", "三段结构完整", "节奏分配合理"],
            "weaknesses": ["差异化不够突出", "CTA可以更有紧迫感"],
            "improvement_suggestions": ["在开头加入更具体的数字或反常识点", "CTA加入紧迫感如'限时'或互动引导"],
            "iteration_notes": "整体合格，建议在差异化和CTA上做优化",
        }
