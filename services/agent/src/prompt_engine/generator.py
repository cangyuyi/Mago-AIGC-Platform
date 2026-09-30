"""Prompt Engine - Core module for generating model-specific prompts.

Takes a ScriptPackage (script + storyboard + characters + style) and generates
optimized prompts for each target model.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from src.prompt_engine import normalize as nz

_CONFIG_PATH = Path(__file__).parent / "model_configs.json"


def load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


CONFIG = load_config()
MODELS = {m["model_id"]: m for m in CONFIG["models"]}
SHOT_SIZES = CONFIG["shot_sizes"]
CAMERA_ANGLES = CONFIG["camera_angles"]
CAMERA_MOVEMENTS = CONFIG["camera_movements"]
LIGHTING_TYPES = CONFIG["lighting_types"]


def _vocab(section: str, raw: Any, lang: str, *, fallback_key: str = "") -> str:
    """Resolve one storyboard vocabulary field into display text.

    Unrecognised values are kept verbatim instead of being dropped: an author
    who wrote "crash zoom" still expects that information in the prompt.
    """
    text = str(raw if raw is not None else "").strip()
    if not text:
        return nz.label(section, fallback_key, lang) if fallback_key else ""
    key = nz.resolve(section, text)
    if key:
        return nz.label(section, key, lang)
    return text


def translate_shot(shot: dict[str, Any], lang: str = "zh", include_movement: bool = True) -> str:
    """Translate shot fields into descriptive text.

    ``include_movement`` is switched off for video models, which state camera
    motion in their own clause; repeating it produced "镜头缓缓推近" twice.
    """
    parts: list[str] = [
        _vocab("shot_size", shot.get("shot_size"), lang, fallback_key="medium"),
        _vocab("camera_angle", shot.get("camera_angle"), lang, fallback_key="eye_level"),
    ]
    # A locked frame is already implied by the shot, so keep "static" out of the
    # composite framing clause; video models state motion separately.
    raw_move = shot.get("camera_movement")
    move_key = nz.resolve("camera_movement", raw_move)
    if not include_movement:
        move_key = None
        raw_move = ""
    if move_key and move_key != "static":
        parts.append(nz.label("camera_movement", move_key, lang))
    elif not move_key and str(raw_move or "").strip():
        parts.append(str(raw_move).strip())
    return (", " if lang == "en" else "，").join([part for part in parts if part])


def translate_lighting(lighting_key: str, lang: str = "zh") -> str:
    return _vocab("lighting", lighting_key, lang, fallback_key="natural")


_ASPECT_SIZES: dict[str, str] = {
    "9:16": "1024x1792",
    "16:9": "1792x1024",
    "1:1": "1024x1024",
    "4:5": "1024x1280",
    "3:2": "1536x1024",
    "2:3": "1024x1536",
}

_ASPECT_PIXELS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1024, 1024),
    "4:5": (1080, 1350),
    "3:2": (1536, 1024),
    "2:3": (1024, 1536),
}


def _apply_aspect_ratio(params: dict[str, Any], aspect_ratio: str, notes: list[str]) -> None:
    """Push the storyboard aspect ratio into whichever key this model uses."""
    aspect = str(aspect_ratio or "").strip()
    if not aspect:
        return
    if "aspect_ratio" in params:
        params["aspect_ratio"] = aspect
    elif "ar" in params:
        params["ar"] = aspect
    elif "size" in params and aspect in _ASPECT_SIZES:
        params["size"] = _ASPECT_SIZES[aspect]
    elif "width" in params and "height" in params and aspect in _ASPECT_PIXELS:
        params["width"], params["height"] = _ASPECT_PIXELS[aspect]
    else:
        notes.append(f"该模型没有通用宽高比参数，竖屏比例 {aspect} 需在生成界面手动选择")


def _contains_cjk(text: str) -> bool:
    """True when any CJK character survives inside an English-target prompt."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def generate_prompt_for_shot(
    shot: dict[str, Any],
    model_id: str,
    script: dict[str, Any] | None = None,
    characters: list[dict[str, Any]] | None = None,
    style: dict[str, Any] | None = None,
    global_params: dict[str, Any] | None = None,
    aspect_ratio: str | None = None,
) -> dict[str, Any]:
    """Generate a complete prompt for one shot + one model."""
    if model_id not in MODELS:
        return {"error": f"unknown model: {model_id}"}
    model = MODELS[model_id]
    lang = model.get("language", "en")

    # Build character fragment
    char_frag = ""
    if characters:
        char_descs = [
            c.get("prompt_fragment", c.get("face_description", ""))
            for c in characters
            if c.get("prompt_fragment") or c.get("face_description")
        ]
        char_frag = "，".join(char_descs) if lang == "zh" else ", ".join(char_descs)

    # Build style fragment
    style_frag = ""
    style_negative = ""
    if style:
        if lang == "zh":
            style_frag = style.get("positive_fragment", "")
        else:
            style_frag = style.get("positive_fragment", "")
        style_negative = style.get("negative_fragment", "")

    # Build subject/scene
    subject = shot.get("subject_description", "人物")
    scene = shot.get("scene_description", "")
    visual = shot.get("visual_description", "")
    action = shot.get("action_description", "")
    lighting = translate_lighting(shot.get("lighting", "natural"), lang)
    color_tone = nz.color_tone_label(shot.get("color_tone", ""), lang)
    is_video = model.get("prompt_type") == "video"
    shot_desc = translate_shot(shot, lang, include_movement=not is_video)
    transition = nz.transition_label(shot.get("transition", ""), lang) if is_video else ""
    quality = model.get("quality_booster", "")
    negative = model.get("universal_negative", "")
    if style_negative:
        negative = (negative + "，" + style_negative) if lang == "zh" else (negative + ", " + style_negative)

    # Motion description (video models)
    motion = ""
    move_key = nz.resolve("camera_movement", shot.get("camera_movement"))
    if is_video:
        if move_key:
            motion = nz.label("camera_movement", move_key, lang)
        elif str(shot.get("camera_movement") or "").strip():
            motion = str(shot["camera_movement"]).strip()
        elif str(shot.get("camera_movement") or "").strip() == "":
            motion = nz.label("camera_movement", "static", lang)
        # Add subtle motion details
        if lang == "zh":
            motion += "，自然流畅动作，画面平稳" if motion else "自然流畅动作"
        else:
            motion += ", natural smooth motion, steady frame" if motion else "natural smooth motion"

    # Compose
    if lang == "zh":
        parts = [visual]
        if char_frag:
            parts.append(f"人物特征：{char_frag}")
        if action and action not in visual:
            parts.append(f"动作：{action}")
        parts.append(f"镜头：{shot_desc}")
        parts.append(f"光线：{lighting}")
        if color_tone:
            parts.append(f"色调：{color_tone}")
        if style_frag:
            parts.append(f"风格：{style_frag}")
        if motion:
            parts.append(f"运动：{motion}")
        if transition:
            parts.append(f"转场：{transition}")
        parts.append(quality)
        positive = "；".join([p for p in parts if p])
    else:
        parts = [visual if visual else f"{subject} in {scene}"]
        if char_frag:
            parts.append(f"character features: {char_frag}")
        if action and action not in visual:
            parts.append(action)
        parts.append(shot_desc)
        parts.append(f"{lighting}")
        if color_tone:
            parts.append(color_tone)
        if style_frag:
            parts.append(style_frag)
        if motion:
            parts.append(motion)
        if transition:
            parts.append(transition)
        parts.append(quality)
        positive = ", ".join([p for p in parts if p])

    # Parameters
    params = dict(model.get("default_parameters", {}))
    if global_params:
        params.update(global_params)
    seed = random.randint(10000, 999999)
    params["seed"] = seed

    notes: list[str] = []
    _apply_aspect_ratio(params, aspect_ratio or "", notes)

    # Shot length beats a one-size-fits-all default: the storyboard already
    # knows how long the shot is, and video models bill by duration.
    shot_duration = shot.get("duration_sec", shot.get("duration"))
    if is_video and "duration" in params and isinstance(shot_duration, (int, float)):
        wanted = max(1, min(10, int(round(float(shot_duration)))))
        if params.get("duration") != wanted:
            notes.append(f"duration 已按镜头时长 {shot_duration}s 取整为 {wanted}s，请确认模型支持的档位（如可灵 5s/10s）")
        params["duration"] = wanted

    if lang == "en" and _contains_cjk(positive):
        notes.append("提示词含中文，而该模型建议正向英文提示词：投放前请先将中文部分翻译成英文")

    # Build reference images list
    ref_images = []
    if characters:
        for c in characters:
            if c.get("reference_image_url"):
                ref_images.append(
                    {"url": c["reference_image_url"], "role": "face", "weight": c.get("faceid_weight", 0.8)}
                )

    return {
        "model_id": model_id,
        "model_name": model["display_name"],
        "prompt_type": model["prompt_type"],
        "positive_prompt": positive,
        "negative_prompt": negative if model.get("supports_negative") else "",
        "parameters": params,
        "reference_images": ref_images,
        "seed_value": seed,
        "language": lang,
        "aspect_ratio": str(params.get("aspect_ratio") or params.get("ar") or params.get("size") or ""),
        "duration_sec": shot_duration if isinstance(shot_duration, (int, float)) else None,
        "transition": transition,
        "warnings": notes,
        "quality_notes": " ".join(
            [f"Generated for {model['display_name']}.", str(model.get("notes", "")), *notes]
        ).strip(),
    }


def generate_package(
    storyboard: dict[str, Any],
    script: dict[str, Any] | None = None,
    characters: list[dict[str, Any]] | None = None,
    style: dict[str, Any] | None = None,
    target_models: list[str] | None = None,
    global_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a complete prompt package for all shots × all selected models."""
    if target_models is None:
        target_models = ["kling-v3", "midjourney-v7", "sora-turbo"]
    shots = storyboard.get("shots", [])
    aspect = ""
    if global_params:
        aspect = str(global_params.get("aspect_ratio") or "")
    if not aspect:
        # This product ships vertical short video, so a storyboard with no
        # declared ratio still gets the same ratio the model defaults use.
        aspect = str(storyboard.get("aspect_ratio") or "9:16")
    package = {
        "id": str(uuid4())[:8],
        "storyboard_id": storyboard.get("id", ""),
        "name": script.get("title", "脚本提示词包") if script else "提示词包",
        "total_shots": len(shots),
        "selected_models": target_models,
        "aspect_ratio": aspect,
        "prompts": [],
    }
    base_seed = random.randint(10000, 99999)
    for i, shot in enumerate(shots):
        for model_id in target_models:
            result = generate_prompt_for_shot(
                shot, model_id, script, characters, style, global_params, aspect_ratio=aspect
            )
            if "error" in result:
                continue
            result["shot_index"] = shot.get("index", i + 1)
            result["package_id"] = package["id"]
            # Seed locking for consistency: same seed range per scene
            result["seed_value"] = base_seed + shot.get("index", i) * 7
            result["parameters"]["seed"] = result["seed_value"]
            package["prompts"].append(result)
    return package


def get_model_list() -> list[dict[str, Any]]:
    """Return list of available models for UI."""
    return [
        {
            "model_id": m["model_id"],
            "display_name": m["display_name"],
            "vendor": m["vendor"],
            "prompt_type": m["prompt_type"],
            "language": m.get("language", "en"),
            "supports_negative": m["supports_negative"],
            "aspect_ratios": m.get("aspect_ratios", []),
        }
        for m in CONFIG["models"]
    ]
