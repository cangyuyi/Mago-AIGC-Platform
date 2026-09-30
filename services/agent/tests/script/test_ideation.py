"""Tests for ideation agent producing diverse creative ideas."""

from __future__ import annotations

import json

import pytest

from src.agents.ideation.agent import IdeationAgent
from src.knowledge.loader import get_knowledge_summary


@pytest.mark.asyncio
async def test_ideation_offline_returns_ideas():
    agent = IdeationAgent()
    state = {
        "current_input": "美妆口红种草",
        "messages": [],
        "steps_completed": [],
    }
    result = await agent.run(state)
    ideas = result.get("creative_ideas", [])
    assert len(ideas) >= 3
    for idea in ideas:
        assert "title" in idea
        assert "description" in idea
        assert "id" in idea


@pytest.mark.asyncio
async def test_offline_ideas_have_required_fields():
    agent = IdeationAgent()
    ideas = agent._offline_ideas("美妆")
    for idea in ideas:
        assert idea["title"], "idea must have title"
        assert idea["description"], "idea must have description"
        assert isinstance(idea.get("ai_feasibility_score", 0), (int, float))
        assert 0 <= idea.get("ai_feasibility_score", 0) <= 10


def test_knowledge_base_complete():
    summary = get_knowledge_summary()
    assert summary["hooks"] >= 100
    assert summary["story_structures"] >= 30
    assert summary["ctas"] >= 20
    assert summary["emotion_curves"] >= 15
    assert summary["vertical_specs"] >= 20
    assert summary["rhythm_patterns"] >= 10

class TestTopicFromInput:
    """The offline demo must not paste the whole instruction into copy."""

    def test_drops_trailing_instruction_clause(self) -> None:
        from src.agents.ideation.agent import IdeationAgent

        assert IdeationAgent._topic_from_input("口红测评，从开盖到上嘴，30秒") == "口红测评"

    def test_does_not_duplicate_the_template_lead_in(self) -> None:
        from src.agents.ideation.agent import IdeationAgent

        assert IdeationAgent._topic_from_input("第一视角记录口红测评") == "口红测评"

    def test_keeps_a_bare_phrase_that_only_looks_like_a_lead_in(self) -> None:
        from src.agents.ideation.agent import IdeationAgent

        assert IdeationAgent._topic_from_input("第一视角") == "第一视角"

    def test_collapses_the_workbench_selection_sentence(self) -> None:
        """Picking a direction sends prose; the topic must stay a topic.

        Regression: the follow-up sentence used to become the topic itself, so
        every hook, shot description and exported prompt repeated
        "我选这个方向：…" verbatim.
        """
        follow_up = (
            "我选这个方向：第一视角记录口红测评：从开始到成片。用第一视角完整记录口红测评的关键过程，"
            "开头用一个最有质感的瞬间吸引观众。 请帮我写创意简报、设计钩子、写完整脚本。"
        )
        assert IdeationAgent._topic_from_input(follow_up) == "口红测评"

    def test_idea_copy_never_contains_chat_instructions(self) -> None:
        ideas = IdeationAgent()._offline_ideas(
            "我选这个方向：第一视角记录咖啡拉花：从开始到成片。请帮我写脚本。"
        )
        blob = json.dumps(ideas, ensure_ascii=False)
        for banned in ("我选这个方向", "请帮我", "：从开始到成片：从开始到成片"):
            assert banned not in blob, banned

    def test_offline_title_reads_as_one_sentence(self) -> None:
        from src.agents.ideation.agent import IdeationAgent

        ideas = IdeationAgent()._offline_ideas("第一视角记录口红测评，从开盖到上嘴，30秒")
        assert ideas[0]["title"] == "第一视角记录口红测评：从开始到成片"
