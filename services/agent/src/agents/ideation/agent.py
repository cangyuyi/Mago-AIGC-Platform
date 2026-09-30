"""Ideation Agent - generates creative directions from user input.

Phase 1 implementation: takes user's vague description and returns multiple
creative ideas using the LLM. Will be enhanced with knowledge base retrieval
and hot trend data in later phases.
"""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from src.agents.base import BaseAgent

IDEATION_SYSTEM_PROMPT = """你是一位顶级短视频创意总监，擅长帮助创作者找到爆款方向。

用户会给你一个模糊的视频创作想法（可能只有一句话、一个赛道，甚至一个词）。
你的任务是给出【10个差异度足够大的创意方向】，不是10个大同小异的方案。

## 创意发散规则

使用以下创意激发方法（每个想法可组合多种）：
1. 跨界移植法：把其他领域的爆款结构搬到本赛道
2. 反转法：把常规做法反过来（"不要买"代替"推荐买"）
3. 极端化法：把某元素推到极致
4. 代入法：代入特定身份/场景
5. 热梗嫁接法：结合当前热门BGM/挑战/梗
6. 冲突法：制造对立/矛盾/争议
7. 时间压缩/延展法：一秒变装/30天变化/10分钟讲百年
8. 第四面墙法：打破第四面墙直接和观众对话

## 输出格式（严格JSON，不要多余文字）

```json
{
  "ideas": [
    {
      "title": "创意标题（一句话，有吸引力）",
      "description": "核心思路描述（2-3句话说清楚这个创意的角度）",
      "hook_direction": "钩子方向：用什么类型钩子、大概内容",
      "emotion_tone": "情绪基调（搞笑/感动/震撼/愤怒/治愈/干货/悬疑/共鸣…）",
      "differentiation": "差异化：为什么这个方向能火，和同类内容有何不同",
      "ai_feasibility_score": 7,
      "difficulty": "low/medium/high",
      "estimated_duration": 30,
      "tags": ["标签1", "标签2"],
      "is_hot_trend": false
    }
  ]
}
```

## 重要约束
- 10个想法必须在情绪基调、钩子类型、叙事结构上有明显差异
- 每个创意要有具体可执行的钩子方向，不能泛泛而谈
- ai_feasibility_score要诚实：需要大量真人出镜/复杂物理交互的分数低
- 所有内容用中文
- 严格输出JSON，不要markdown代码块标记，不要额外解释
"""


class IdeationAgent(BaseAgent):
    name = "ideation"
    description = "Generates multiple creative directions from user input"

    def system_prompt(self) -> str:
        return IDEATION_SYSTEM_PROMPT

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("current_input", "")
        self.logger.info("ideation_run", input_length=len(user_input))

        if not self.llm_available:
            # Offline mode: return starter ideas
            ideas = self._offline_ideas(user_input)
        else:
            response_text = await self.call_llm(
                user_message=user_input,
                temperature=0.9,  # High temperature for creativity
                response_format={"type": "json_object"},
            )
            ideas = self._parse_ideas(response_text)

        # Assign IDs
        for idea in ideas:
            if not idea.get("id"):
                idea["id"] = str(uuid4())[:8]

        messages = state.get("messages", [])
        messages.append(
            {
                "role": "assistant",
                "content": f"我为你想到了{len(ideas)}个创意方向，你看看哪个感兴趣？可以选一个，也可以组合几个方向。",
            }
        )

        return {
            "messages": messages,
            "creative_ideas": ideas,
            "current_step": "ideation_complete",
            "steps_completed": state.get("steps_completed", []) + ["ideation"],
            "hitl_required": True,
            "hitl_node": "ideation_review",
        }

    def _parse_ideas(self, text: str) -> list[dict[str, Any]]:
        """Parse JSON response into list of idea dicts."""
        try:
            # Strip any markdown code block markers
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            data = json.loads(text.strip())
            ideas = data.get("ideas", data.get("creative_ideas", []))
            # Validate each idea has required fields
            valid_ideas = []
            for i in ideas:
                if isinstance(i, dict) and "title" in i:
                    valid_ideas.append(i)
            return valid_ideas[:10]  # Cap at 10
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error("ideation_parse_error", error=str(e))
            return self._offline_ideas("")

    @staticmethod
    def _topic_from_input(user_input: str) -> str:
        """Extract a concise creative topic for the deterministic demo mode.

        The offline path must remain useful without an LLM. In particular, do not
        paste a full instruction such as ``帮我设计一个30秒短视频：...`` into a
        title or hook, because that produces visibly broken copy in the workbench.

        This also covers the follow-up the workbench sends when the creator picks
        a direction ("我选这个方向：<title>。<description> 请帮我写…"): that sentence
        must collapse back to the bare topic, otherwise every shot description —
        and therefore every exported prompt — repeats the chat instruction.
        """
        text = re.sub(r"\s+", " ", (user_input or "").strip())
        # A trailing instruction clause always starts a new sentence.
        text = re.split(r"[。.!！]", text, maxsplit=1)[0]
        # "我选这个方向：…" / "就用第二个：…" — keep what follows the lead-in.
        text = re.sub(
            r"^(?:我|你)?(?:就|还是)?(?:选|用|要|做|拍|来)(?:了)?(?:这个|这一?个|第[一二三四五六七八九十\d]+个)?(?:方向|选题?|点子|创意|方案|思路)?[：:，,\s]*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^(?:请|帮我|请帮我|我想(?:要)?|想要)?(?:设计|制作|创作|生成|做)"
            r"(?:一个|一条|一支)?(?:\d+\s*(?:秒|分钟|min|s))?"
            r"(?:短视频|视频|内容)?[：:，,\s]*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        # Templates below prepend their own framing ("第一视角记录…"), so a
        # trailing instruction clause and any duplicated framing residue both
        # have to go: with the clause dropped, "第一视角记录口红测评" and
        # "口红测评，第一视角，30秒" must both collapse to "口红测评".
        text = re.sub(r"[，,。；;：:！!？?].*$", "", text).strip(" ：:，,。.!！")
        # Drop framing / format tokens wherever they appear (lead, middle or
        # tail) plus bare durations such as "30秒" / "1分钟".
        framing = r"(?:第一视角记录|第一视角|沉浸式记录|沉浸式|前后对比|过程记录|ASMR|asmr|Vlog|vlog|开箱|测评视频)"
        text = re.sub(framing, " ", text)
        text = re.sub(r"\d+\s*(?:秒|分钟|min|s)", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" ：:，,。.!！-—·")
        if not text:
            # The input was *only* framing (e.g. "第一视角"): keep it rather than
            # fabricating a topic, so the title still reads as the creator wrote.
            return "第一视角"
        return text[:32].rstrip(" ：:，,。.!！")

    def _offline_ideas(self, user_input: str) -> list[dict[str, Any]]:
        """Return useful, input-aware starter ideas when no LLM is available."""
        topic = self._topic_from_input(user_input)
        return [
            {
                "id": "idea001",
                "title": f"第一视角记录{topic}：从开始到成片",
                "description": f"用第一视角完整记录{topic}的关键过程，开头用一个最有质感的瞬间吸引观众，中段用快速剪辑交代步骤，结尾给出成片回看。",
                "hook_direction": f"视觉钩子：先展示{topic}最有冲击力的成品瞬间，再倒叙过程。",
                "emotion_tone": "沉浸/专注",
                "differentiation": "把过程和成片结果放在同一条叙事线上，观众既能获得方法也能获得沉浸感。",
                "ai_feasibility_score": 8,
                "difficulty": "low",
                "estimated_duration": 30,
                "tags": [topic, "第一视角", "过程记录"],
                "is_hot_trend": False,
            },
            {
                "id": "idea002",
                "title": f"前后对比：{topic}的质感如何被拍出来",
                "description": f"先展示普通视角下的{topic}，再切换到光线、构图和节奏都更好的成片版本，用前后对比突出创作方法。",
                "hook_direction": f"对比式：同一个{topic}，为什么成片质感差这么多？",
                "emotion_tone": "惊喜/向往",
                "differentiation": "用可感知的画面对比解释创作选择，不依赖夸张承诺，适合展示制作能力。",
                "ai_feasibility_score": 9,
                "difficulty": "low",
                "estimated_duration": 25,
                "tags": [topic, "前后对比", "视觉冲击"],
                "is_hot_trend": False,
            },
            {
                "id": "idea003",
                "title": f"沉浸式ASMR：{topic}的专注时刻",
                "description": f"弱化旁白，放大{topic}过程中的细节声音、手部动作和光影变化，让观众像坐在现场一样体验完整过程。",
                "hook_direction": f"沉浸式开场：直接从{topic}最细腻的声音和特写开始，前3秒不说话。",
                "emotion_tone": "治愈/放松",
                "differentiation": "以声音和细节代替堆砌信息，能和讲解型内容形成明显区分。",
                "ai_feasibility_score": 7,
                "difficulty": "medium",
                "estimated_duration": 45,
                "tags": [topic, "沉浸式", "ASMR"],
                "is_hot_trend": False,
            },
        ]
