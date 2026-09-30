"""Tests for compliance agent detecting violations."""

from __future__ import annotations

import pytest

from src.agents.script.compliance import ComplianceAgent


@pytest.mark.asyncio
async def test_compliance_detects_extreme_words():
    agent = ComplianceAgent()
    state = {
        "script": {"hook": "这是最好的口红", "body_text": "使用100%纯天然成分", "cta": "", "beats": []},
        "storyboard": {"shots": []},
    }
    result = await agent.run(state)
    report = result.get("compliance", {})
    flags = report.get("flags", [])
    extreme_flags = [f for f in flags if f["category"] == "极限词"]
    assert len(extreme_flags) >= 2, f"Should detect at least 2 extreme words, got {len(extreme_flags)}"


@pytest.mark.asyncio
async def test_compliance_detects_medical_claims():
    agent = ComplianceAgent()
    state = {
        "script": {"hook": "", "body_text": "这个产品能治疗痘痘，根治痘印", "cta": "", "beats": []},
        "storyboard": {"shots": []},
    }
    result = await agent.run(state)
    report = result.get("compliance", {})
    flags = report.get("flags", [])
    med_flags = [f for f in flags if f["category"] == "医疗宣称"]
    assert len(med_flags) >= 1, f"Should detect medical claims, got {len(med_flags)}"


@pytest.mark.asyncio
async def test_compliance_clean_text_passes():
    agent = ComplianceAgent()
    state = {
        "script": {"hook": "今天分享一支口红", "body_text": "颜色很适合日常使用", "cta": "喜欢可以试试", "beats": []},
        "storyboard": {"shots": []},
    }
    result = await agent.run(state)
    report = result.get("compliance", {})
    assert report.get("is_compliant", False), "Clean text should pass compliance"
    assert len(report.get("flags", [])) == 0


@pytest.mark.asyncio
async def test_compliance_severity_levels():
    agent = ComplianceAgent()
    state = {
        "script": {"hook": "最好的产品", "body_text": "包治百病永不复发", "cta": "", "beats": []},
        "storyboard": {"shots": []},
    }
    result = await agent.run(state)
    report = result.get("compliance", {})
    assert report.get("overall_risk") in ("medium", "high"), "Mixed violations should be medium or high risk"
