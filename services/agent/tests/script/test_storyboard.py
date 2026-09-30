"""Tests for storyboard agent output quality."""

from __future__ import annotations

import pytest

from src.agents.script.storyboard_agent import StoryboardAgent

ABSTRACT_WORDS = ["很美", "很震撼", "非常漂亮", "很有感觉", "超级好看", "极其美丽", "无比惊艳"]


@pytest.mark.asyncio
async def test_offline_storyboard_has_shots():
    agent = StoryboardAgent()
    script = {
        "title": "测试脚本",
        "hook": "你知道吗",
        "beats": [{"index": 0, "phase": "hook", "duration_sec": 3.0, "content": "你知道吗", "visual_note": "特写"}],
        "target_duration_sec": 30,
        "structure_id": "struct_hook_body_cta",
    }
    state = {
        "script": script,
        "creative_brief": {"target_platform": "douyin", "vertical": "v_beauty", "tone_guide": "亲切"},
    }
    result = await agent.run(state)
    sb = result.get("storyboard", {})
    assert sb.get("shot_count", 0) >= 3, f"Should have at least 3 shots, got {sb.get('shot_count')}"
    assert sb.get("total_duration_sec", 0) > 0


@pytest.mark.asyncio
async def test_offline_shots_have_concrete_descriptions():
    agent = StoryboardAgent()
    script = {"title": "测试", "beats": [], "target_duration_sec": 30, "structure_id": "struct_hook_body_cta"}
    state = {"script": script, "creative_brief": {"target_platform": "douyin", "vertical": "v_beauty"}}
    result = await agent.run(state)
    sb = result.get("storyboard", {})
    for shot in sb.get("shots", []):
        desc = shot.get("visual_description", "")
        assert len(desc) > 20, f"Shot {shot.get('index')} description too short: {desc}"
        for word in ABSTRACT_WORDS:
            assert word not in desc, f"Shot {shot.get('index')} contains abstract word '{word}': {desc}"


@pytest.mark.asyncio
async def test_storyboard_shot_sizes_vary():
    agent = StoryboardAgent()
    script = {"title": "测试", "beats": [], "target_duration_sec": 30, "structure_id": "struct_hook_body_cta"}
    state = {"script": script, "creative_brief": {"target_platform": "douyin", "vertical": "v_beauty"}}
    result = await agent.run(state)
    sb = result.get("storyboard", {})
    sizes = set(s.get("shot_size") for s in sb.get("shots", []))
    assert len(sizes) >= 2, f"Shot sizes should vary, got only: {sizes}"
