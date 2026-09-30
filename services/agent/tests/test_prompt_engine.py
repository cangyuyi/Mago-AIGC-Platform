"""Prompt-engine vocabulary and prompt-pack endpoint tests.

These lock the bug where storyboard fields that were not exact
model_configs.json keys were dropped from the exported prompt, which is what
made the exported prompt packs unusable.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.prompt_engine import normalize as nz
from src.prompt_engine.generator import (
    generate_package,
    generate_prompt_for_shot,
    get_model_list,
    translate_shot,
)

SHOT = {
    "index": 1,
    "duration_sec": 7.4,
    "shot_size": "特写",
    "camera_angle": "overhead",
    "camera_movement": "slow_push_in",
    "visual_description": "口红膏体旋出",
    "action_description": "口红膏体旋出",
    "scene_description": "梳妆台",
    "subject_description": "手",
    "lighting": "soft_warm",
    "color_tone": "warm_neutral",
    "transition": "match_cut",
}


# --------------------------------------------------------------------- vocab
def test_legacy_camera_movement_resolves_to_config_key() -> None:
    assert nz.resolve("camera_movement", "slow_push_in") == "push_in"
    assert nz.resolve("camera_movement", "dolly_in") == "push_in"
    assert nz.resolve("camera_movement", "handheld_follow") == "handheld"
    assert nz.resolve("camera_movement", "zoom_out") == "pull_out"


def test_chinese_film_terms_resolve_in_both_directions() -> None:
    assert nz.resolve("shot_size", "特写") == "close_up"
    assert nz.label("shot_size", "close_up", "en") == "close-up shot, CU"
    assert nz.resolve("camera_movement", "跟拍") == "tracking"
    assert nz.label("camera_movement", "tracking", "zh") == "跟随拍摄"


def test_transition_is_not_treated_as_camera_movement() -> None:
    assert nz.resolve("camera_movement", "match_cut") is None


def test_unknown_value_returns_none_instead_of_guessing() -> None:
    assert nz.resolve("lighting", "totally_made_up_light") is None
    assert nz.resolve("shot_size", "") is None


def test_lighting_synonyms_from_storyboard_prompt_resolve() -> None:
    for raw, expected in [("soft", "soft_studio"), ("dramatic", "dramatic_contrast"),
                          ("backlit", "backlit_silhouette"), ("neon", "neon_cool"),
                          ("studio", "soft_studio"), ("soft_morning_natural", "natural")]:
        assert nz.resolve("lighting", raw) == expected, raw


# -------------------------------------------------------------------- framing
def test_video_framing_does_not_repeat_camera_motion() -> None:
    framing = translate_shot(SHOT, "zh", include_movement=False)
    assert "推近" not in framing
    assert "特写" in framing and "顶视" in framing


def test_image_framing_keeps_motion_hint() -> None:
    framing = translate_shot(SHOT, "en", include_movement=True)
    assert "slow push in" in framing


def test_unmappable_value_is_preserved_not_dropped() -> None:
    shot = dict(SHOT, camera_movement="crash zoom")
    assert "crash zoom" in translate_shot(shot, "en")


# ------------------------------------------------------------------- prompts
def test_zh_video_prompt_carries_lighting_tone_and_transition() -> None:
    result = generate_prompt_for_shot(SHOT, "kling-v3", aspect_ratio="9:16")
    prompt = result["positive_prompt"]
    assert "光线：暖黄钨丝灯" in prompt
    assert "色调：暖中性色调" in prompt
    assert "转场：匹配剪辑" in prompt
    assert prompt.count("镜头缓缓推近") == 1


def test_image_prompt_omits_transition() -> None:
    result = generate_prompt_for_shot(SHOT, "midjourney-v7", aspect_ratio="9:16")
    assert "match cut" not in result["positive_prompt"]


def test_english_model_flags_untranslated_chinese() -> None:
    result = generate_prompt_for_shot(SHOT, "midjourney-v7", aspect_ratio="9:16")
    assert any("英文" in w for w in result["warnings"])


def test_duration_follows_the_shot_and_is_capped() -> None:
    assert generate_prompt_for_shot(SHOT, "kling-v3")["parameters"]["duration"] == 7
    assert generate_prompt_for_shot(dict(SHOT, duration_sec=99), "kling-v3")["parameters"]["duration"] == 10


def test_aspect_ratio_uses_each_models_own_parameter_name() -> None:
    assert generate_prompt_for_shot(SHOT, "midjourney-v7", aspect_ratio="1:1")["parameters"]["ar"] == "1:1"
    assert generate_prompt_for_shot(SHOT, "dalle-3", aspect_ratio="9:16")["parameters"]["size"] == "1024x1792"
    flux = generate_prompt_for_shot(SHOT, "flux-dev", aspect_ratio="16:9")["parameters"]
    assert (flux["width"], flux["height"]) == (1920, 1080)


def test_duplicate_action_text_is_not_repeated_for_english_models() -> None:
    prompt = generate_prompt_for_shot(SHOT, "flux-dev", aspect_ratio="1:1")["positive_prompt"]
    assert prompt.count("口红膏体旋出") == 1


def test_unknown_model_reports_error() -> None:
    assert "error" in generate_prompt_for_shot(SHOT, "not-a-model")


# ------------------------------------------------------------------- package
def test_package_seeds_lock_across_models_of_one_shot() -> None:
    package = generate_package({"id": "sb", "aspect_ratio": "9:16", "shots": [SHOT]},
                              {"title": "T"}, [], None, ["kling-v3", "midjourney-v7"])
    assert len(package["prompts"]) == 2
    assert package["prompts"][0]["seed_value"] == package["prompts"][1]["seed_value"]
    assert package["aspect_ratio"] == "9:16"


def test_package_with_no_usable_shots_returns_no_prompts() -> None:
    assert generate_package({"shots": []}, None, None, None, ["kling-v3"])["prompts"] == []


def test_model_list_exposes_ui_fields() -> None:
    models = get_model_list()
    assert len(models) >= 10
    for entry in models:
        assert entry["model_id"] and entry["display_name"] and entry["prompt_type"] in {"image", "video"}


# ------------------------------------------------------------------ endpoint
def _agent_client() -> TestClient:
    from fastapi import FastAPI

    from src.api.routes import agent as agent_module

    app = FastAPI()
    app.include_router(agent_module.router)
    return TestClient(app)


def test_prompt_models_endpoint_lists_every_model() -> None:
    body = _agent_client().get("/api/v1/agent/prompt-models").json()
    assert len(body["models"]) >= 10
    assert {"model_id", "display_name", "prompt_type"} <= set(body["models"][0])


def test_prompt_pack_endpoint_returns_prompts() -> None:
    response = _agent_client().post(
        "/api/v1/agent/prompt-pack",
        json={"storyboard": {"id": "sb", "aspect_ratio": "9:16", "shots": [SHOT]},
              "script": {"title": "口红测评"}, "target_models": ["kling-v3"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generated_by"] == "prompt_engine_template"
    assert body["llm_configured"] is False
    assert len(body["package"]["prompts"]) == 1
    assert "暖黄钨丝灯" in body["package"]["prompts"][0]["positive_prompt"]


def test_prompt_pack_rejects_empty_storyboard() -> None:
    response = _agent_client().post("/api/v1/agent/prompt-pack", json={"storyboard": {"shots": []}})
    assert response.status_code == 422
    assert "分镜表为空" in response.json()["detail"]


def test_prompt_pack_rejects_unknown_model_and_lists_options() -> None:
    response = _agent_client().post(
        "/api/v1/agent/prompt-pack",
        json={"storyboard": {"shots": [SHOT]}, "target_models": ["nope-v9"]},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "nope-v9" in detail and "kling-v3" in detail


def test_prompt_pack_caps_shot_count() -> None:
    from src.api.routes.agent import MAX_PROMPT_PACK_SHOTS

    shots = [dict(SHOT, index=i) for i in range(MAX_PROMPT_PACK_SHOTS + 1)]
    response = _agent_client().post("/api/v1/agent/prompt-pack", json={"storyboard": {"shots": shots}})
    assert response.status_code == 422
    assert "上限" in response.json()["detail"]


def test_prompt_pack_defaults_to_three_models() -> None:
    body = _agent_client().post(
        "/api/v1/agent/prompt-pack", json={"storyboard": {"shots": [SHOT]}}
    ).json()
    assert len(body["package"]["selected_models"]) == 3


@pytest.mark.asyncio
async def test_project_access_is_required_when_auth_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prompt pack is project data: it must not bypass the auth gate."""
    from src.api.routes import agent as agent_module

    monkeypatch.setattr(
        agent_module, "get_settings", lambda: SimpleNamespace(agent_auth_enabled=True, mago_api_url="http://gateway")
    )
    request = SimpleNamespace(headers={}, state=SimpleNamespace(user_id=None))
    with pytest.raises(HTTPException) as excinfo:
        await agent_module._validate_project_access(request, "11111111-1111-1111-1111-111111111111")
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_prompt_pack_route_enforces_project_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.api.routes import agent as agent_module

    called: list[object] = []

    async def _guard(_request, project_id):
        called.append(project_id)

    monkeypatch.setattr(agent_module, "_validate_project_access", _guard)
    await agent_module.create_prompt_pack(
        agent_module.PromptPackRequest(
            storyboard={"shots": [SHOT]}, project_id="proj-1"
        ),
        SimpleNamespace(headers={}, state=SimpleNamespace(user_id=None)),
    )
    assert called == ["proj-1"]


@pytest.mark.asyncio
async def test_prompt_pack_route_rejects_unusable_shots_before_calling_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.api.routes import agent as agent_module

    async def _no_project_check(_request, _project_id):
        return None

    monkeypatch.setattr(agent_module, "_validate_project_access", _no_project_check)
    with pytest.raises(HTTPException) as excinfo:
        await agent_module.create_prompt_pack(
            agent_module.PromptPackRequest(storyboard={"shots": [{"index": 1}]}),
            SimpleNamespace(headers={}, state=SimpleNamespace(user_id=None)),
        )
    assert excinfo.value.status_code == 422
