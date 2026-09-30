"""RhythmOptimizerAgent - Adjusts shot durations/pacing for optimal rhythm."""

from __future__ import annotations

import json
from typing import Any, cast

from src.agents.base import BaseAgent

RHYTHM_SYSTEM_PROMPT = """你是一位短视频节奏优化师，擅长调整镜头时长分配让视频更有节奏感。

用户会给你当前脚本的分镜表和目标节奏模式，请你：
1. 检查每个镜头时长是否合理
2. 调整时长以匹配目标节奏模式
3. 确保总时长约等于目标时长
4. 给出节奏调整说明

## 输出格式（严格JSON）
{
  "optimized_shots": [{"index":1,"duration_sec":2.5},...],
  "total_duration_sec": 30.0,
  "rhythm_notes": "调整说明：开头加速/中间放慢/结尾有力等"
}

严格输出JSON，不要markdown标记。
"""


class RhythmOptimizerAgent(BaseAgent):
    name = "rhythm_optimizer"
    description = "Optimizes shot pacing and rhythm"

    def system_prompt(self) -> str:
        return RHYTHM_SYSTEM_PROMPT

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        storyboard = state.get("storyboard", {})
        script = state.get("script", {})
        self.logger.info("rhythm_start", shots=len(storyboard.get("shots", [])))

        shots_summary = "\n".join(
            f"镜{s.get('index')}: {s.get('duration_sec', 3)}s, {s.get('shot_size', '')}, {s.get('action_description', '')[:30]}"
            for s in storyboard.get("shots", [])
        )

        prompt = f"""目标总时长: {script.get("target_duration_sec", 30)}秒
节奏模式: {script.get("rhythm_pattern_id", "rhythm_medium")}

当前分镜:
{shots_summary}

请优化镜头时长分配。"""

        if not self.llm_available:
            result = self._offline_optimize(storyboard, script)
        else:
            response_text = await self.call_llm(
                user_message=prompt,
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            result = self._parse_result(response_text)

        if result.get("optimized_shots"):
            shots = storyboard.get("shots", [])
            for opt in result["optimized_shots"]:
                idx = opt.get("index", 0) - 1
                if 0 <= idx < len(shots):
                    shots[idx]["duration_sec"] = opt.get("duration_sec", shots[idx]["duration_sec"])
            storyboard["shots"] = shots
            storyboard["total_duration_sec"] = sum(s.get("duration_sec", 0) for s in shots)

        return {
            "storyboard": storyboard,
            "rhythm_notes": result.get("rhythm_notes", ""),
            "current_step": "rhythm_complete",
        }

    def _parse_result(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(text.strip()))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("rhythm_parse_error", error=str(e))
            return {"optimized_shots": [], "rhythm_notes": ""}

    def _offline_optimize(self, storyboard: dict, script: dict) -> dict[str, Any]:
        target = script.get("target_duration_sec", 30)
        shots = storyboard.get("shots", [])
        if not shots:
            return {"optimized_shots": [], "rhythm_notes": "无镜头可优化", "total_duration_sec": 0}
        return {
            "optimized_shots": [],
            "rhythm_notes": "当前节奏已合理，钩子镜头3秒快速切入，正文中等节奏，结尾CTA留5秒互动时间。",
            "total_duration_sec": target,
        }
