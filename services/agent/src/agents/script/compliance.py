"""ComplianceAgent - Checks scripts for advertising law / platform rule violations."""

from __future__ import annotations

import json
from typing import Any, cast

from src.agents.base import BaseAgent

COMPLIANCE_SYSTEM_PROMPT = """你是一位短视频内容合规审查专家，熟悉中国广告法和各平台内容规则。

请审查以下脚本内容是否存在违规问题，检查类别：
1. 极限词：最/第一/顶级/国家级/绝对/唯一/100%/永久/永不/万能/特效等
2. 医疗宣称：涉及治病/疗效/药效/处方/药物/根治/治愈/医学认证等
3. 虚假宣传：夸张效果/数据造假/无法证实的承诺
4. 低俗色情：性暗示/低俗用语/暴露描写
5. 暴力危险：鼓励危险行为/暴力展示
6. 贬低竞品：直接贬低其他品牌/产品
7. 诱导消费：虚假紧迫感/误导性价格宣传
8. 侵权风险：未经授权的品牌/IP/音乐/人物

## 输出格式（严格JSON）
{
  "is_compliant": true/false,
  "overall_risk": "low/medium/high",
  "flags": [
    {
      "severity": "low/medium/high",
      "category": "违规类别",
      "flagged_text": "被标记的文字",
      "reason": "违规原因",
      "suggestion": "建议修改为"
    }
  ]
}

没有问题时flags为空数组，is_compliant为true。
严格输出JSON，不要markdown标记。
"""

# Built-in pattern checks for offline mode
EXTREME_WORDS = [
    "最好",
    "最佳",
    "最强",
    "最优",
    "第一",
    "顶级",
    "国家级",
    "绝对",
    "唯一",
    "100%",
    "永久",
    "永不",
    "万能",
    "特效",
    "极致",
    "史上最",
    "全球第一",
    "绝无仅有",
    "独一无二",
    "前无古人",
    "包治百病",
    "药到病除",
]
MEDICAL_WORDS = [
    "治疗",
    "治愈",
    "根治",
    "疗效",
    "药效",
    "处方",
    "医用",
    "医学认证",
    "包治",
    "药到病除",
    "无副作用",
    "临床验证",
]
DANGEROUS_WORDS = ["试试跳楼", "自杀方法", "自残教程"]


class ComplianceAgent(BaseAgent):
    name = "compliance"
    description = "Checks scripts for compliance issues"

    def system_prompt(self) -> str:
        return COMPLIANCE_SYSTEM_PROMPT

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        script = state.get("script", {})
        storyboard = state.get("storyboard", {})
        self.logger.info("compliance_check", script_id=script.get("id", ""))

        full_text = " ".join([script.get("hook", ""), script.get("body_text", ""), script.get("cta", "")])
        for beat in script.get("beats", []):
            full_text += " " + beat.get("content", "")
        for shot in storyboard.get("shots", []):
            full_text += " " + shot.get("dialogue", "")

        prompt = f"请审查以下短视频脚本文案：\n\n{full_text}\n\n输出合规审查JSON。"

        if not self.llm_available:
            report = self._rule_based_check(full_text)
        else:
            response_text = await self.call_llm(
                user_message=prompt,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            report = self._parse_report(response_text)
            rule_based = self._rule_based_check(full_text)
            if rule_based["flags"]:
                report["flags"].extend(rule_based["flags"])
                report["is_compliant"] = report["is_compliant"] and rule_based["is_compliant"]
                if report["overall_risk"] == "low" and not rule_based["is_compliant"]:
                    report["overall_risk"] = "medium"

        return {
            "compliance": report,
            "current_step": "compliance_complete",
        }

    def _parse_report(self, text: str) -> dict[str, Any]:
        try:
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            return cast(dict[str, Any], json.loads(text.strip()))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("compliance_parse_error", error=str(e))
            return {"is_compliant": True, "overall_risk": "low", "flags": []}

    def _rule_based_check(self, text: str) -> dict[str, Any]:
        flags = []
        for word in EXTREME_WORDS:
            if word in text:
                flags.append(
                    {
                        "severity": "medium",
                        "category": "极限词",
                        "flagged_text": word,
                        "reason": f"「{word}」属于广告法禁止使用的极限词",
                        "suggestion": "替换为更客观的表述如'非常''很''推荐'",
                    }
                )
        for word in MEDICAL_WORDS:
            if word in text:
                flags.append(
                    {
                        "severity": "high",
                        "category": "医疗宣称",
                        "flagged_text": word,
                        "reason": f"「{word}」涉及医疗宣称，非医疗认证账号禁止使用",
                        "suggestion": "删除医疗相关词汇，改为个人体验描述",
                    }
                )
        return {
            "is_compliant": len(flags) == 0,
            "overall_risk": "high" if any(f["severity"] == "high" for f in flags) else ("medium" if flags else "low"),
            "flags": flags,
        }
