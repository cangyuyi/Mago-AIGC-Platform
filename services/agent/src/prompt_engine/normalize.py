"""Normalise storyboard vocabulary onto the prompt-engine config keys.

Storyboard shots are produced by an LLM (and by older builds of this app), so
field values are not guaranteed to be one of the canonical keys in
``model_configs.json``. Before this module existed, any value that did not
match exactly was dropped silently, which is how a shot like
``camera_movement: "slow_push_in"`` ended up in the exported prompt with no
camera information at all.

Resolution order for every field: exact config key -> alias table -> the
config's own ``cn``/``en`` labels read backwards. Anything that still fails is
returned as ``None`` and the caller keeps the raw text instead of losing it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).parent / "model_configs.json"

SHOT_SIZES: dict[str, dict[str, str]] = {}
CAMERA_ANGLES: dict[str, dict[str, str]] = {}
CAMERA_MOVEMENTS: dict[str, dict[str, str]] = {}
LIGHTING_TYPES: dict[str, dict[str, str]] = {}


def _load() -> None:
    global SHOT_SIZES, CAMERA_ANGLES, CAMERA_MOVEMENTS, LIGHTING_TYPES
    with _CONFIG_PATH.open(encoding="utf-8") as fh:
        cfg = json.load(fh)
    SHOT_SIZES = cfg["shot_sizes"]
    CAMERA_ANGLES = cfg["camera_angles"]
    CAMERA_MOVEMENTS = cfg["camera_movements"]
    LIGHTING_TYPES = cfg["lighting_types"]


_load()

# Surface forms seen in real storyboard output (LLM variants, Chinese film
# terms, abbreviations, and the vocabulary the storyboard prompt used to ask
# for). Values are canonical keys of model_configs.json.
_ALIASES: dict[str, dict[str, str]] = {
    "shot_size": {
        "ecu": "extreme_close_up",
        "big_close_up": "extreme_close_up",
        "macro": "extreme_close_up",
        "cu": "close_up",
        "closeup": "close_up",
        "close": "close_up",
        "mcu": "medium_close_up",
        "ms": "medium",
        "medium_shot": "medium",
        "mls": "medium_wide",
        "ws": "wide",
        "full_body": "wide",
        " establishing": "wide",
        "ews": "extreme_wide",
        "establishing_shot": "extreme_wide",
        "extreme_close": "extreme_close_up",
        "特写": "close_up",
        "大特写": "extreme_close_up",
        "极特写": "extreme_close_up",
        "微距": "extreme_close_up",
        "近景": "medium_close_up",
        "中近景": "medium_close_up",
        "中景": "medium",
        "半身": "medium",
        "中远景": "medium_wide",
        "全景": "wide",
        "全身": "wide",
        "远景": "extreme_wide",
        "大全景": "extreme_wide",
        "空镜": "extreme_wide",
    },
    "camera_angle": {
        "level": "eye_level",
        "neutral": "eye_level",
        "front": "eye_level",
        "low": "low_angle",
        "up": "low_angle",
        "looking_up": "low_angle",
        "high": "high_angle",
        "looking_down": "high_angle",
        "top_down": "birds_eye",
        "overhead": "birds_eye",
        "bird_s_eye": "birds_eye",
        "birds_eye_view": "birds_eye",
        "dutch": "dutch_angle",
        "tilted": "dutch_angle",
        "ots": "over_shoulder",
        "shoulder": "over_shoulder",
        "平视": "eye_level",
        "正面": "eye_level",
        "仰拍": "low_angle",
        "仰视": "low_angle",
        "俯拍": "high_angle",
        "俯视": "high_angle",
        "鸟瞰": "birds_eye",
        "顶视": "birds_eye",
        "过肩": "over_shoulder",
        "荷兰角": "dutch_angle",
        "倾斜": "dutch_angle",
    },
    "camera_movement": {
        "dolly_in": "push_in",
        "dollyin": "push_in",
        "slow_push_in": "push_in",
        "push": "push_in",
        "pushing_in": "push_in",
        "in": "push_in",
        "advance": "push_in",
        "慢推": "push_in",
        "推": "push_in",
        "推镜": "push_in",
        "推近": "push_in",
        "dolly_out": "pull_out",
        "slow_pull_out": "pull_out",
        "pull_back": "pull_out",
        "pull": "pull_out",
        "out": "pull_out",
        "retreat": "pull_out",
        "拉远": "pull_out",
        "拉镜": "pull_out",
        "zoom_out": "pull_out",
        "zoomin": "zoom_in",
        "quick_zoom_in": "zoom_in",
        "急推": "zoom_in",
        "放大": "zoom_in",
        "pan": "pan_right",
        "slow_pan": "pan_right",
        "panning": "pan_right",
        "摇镜": "pan_right",
        "右摇": "pan_right",
        "左摇": "pan_left",
        "paning_left": "pan_left",
        "tilt": "tilt_up",
        "up": "tilt_up",
        "tiltdown": "tilt_down",
        "下摇": "tilt_down",
        "上摇": "tilt_up",
        "升": "tilt_up",
        "降": "tilt_down",
        "follow": "tracking",
        "follow_shot": "tracking",
        "tracking_shot": "tracking",
        "follow_pan": "tracking",
        "dolly": "tracking",
        "跟镜": "tracking",
        "跟拍": "tracking",
        "移镜": "tracking",
        "handheld_follow": "handheld",
        "handheld_camera": "handheld",
        "shake": "handheld",
        "手持": "handheld",
        "晃动": "handheld",
        "orbit_360": "orbit",
        "rotate": "orbit",
        "circle": "orbit",
        "环绕": "orbit",
        "旋转": "orbit",
        "static_shot": "static",
        "locked": "static",
        "fixed": "static",
        "none": "static",
        "静止": "static",
        "固定": "static",
        "固定机位": "static",
        "慢动作": "slow_motion",
        "slowmo": "slow_motion",
        # Transitions are not camera moves: resolve to None so the caller does
        # not invent camera behaviour that the shot does not have.
        "match_cut": "",
        "cut": "",
        "dissolve": "",
        "fade_in": "",
        "fade_out": "",
        "wipe": "",
        "slide_left": "",
        "zoom_transition": "",
    },
    "lighting": {
        "soft": "soft_studio",
        "studio": "soft_studio",
        "soft_light": "soft_studio",
        "soft_warm": "tungsten_warm",
        "soft_morning_natural": "natural",
        "morning": "natural",
        "morning_light": "natural",
        "morning_natural": "natural",
        "daylight": "natural",
        "sunlight": "natural",
        "window": "natural",
        "window_light": "natural",
        "outdoor": "natural",
        "ring_light": "soft_studio",
        "dramatic": "dramatic_contrast",
        "contrast": "dramatic_contrast",
        "hard": "dramatic_contrast",
        "low_key": "dramatic_contrast",
        "backlit": "backlit_silhouette",
        "silhouette": "backlit_silhouette",
        "rim": "backlit_silhouette",
        "neon": "neon_cool",
        "cool": "neon_cool",
        "blue": "neon_cool",
        "bright": "bright_even",
        "even": "bright_even",
        "flat": "bright_even",
        "warm": "tungsten_warm",
        "tungsten": "tungsten_warm",
        "candle": "tungsten_warm",
        "sunset": "golden_hour",
        "dusk": "golden_hour",
        "自然光": "natural",
        "晨光": "natural",
        "日光": "natural",
        "窗光": "natural",
        "柔光": "soft_studio",
        "影棚光": "soft_studio",
        "环形灯": "soft_studio",
        "戏剧光": "dramatic_contrast",
        "硬光": "dramatic_contrast",
        "逆光": "backlit_silhouette",
        "剪影": "backlit_silhouette",
        "霓虹": "neon_cool",
        "冷光": "neon_cool",
        "暖光": "tungsten_warm",
        "钨丝灯": "tungsten_warm",
        "黄金时刻": "golden_hour",
        "夕阳": "golden_hour",
        "均匀布光": "bright_even",
    },
}

# colour_tone has no config section, so keep its own bilingual label table.
COLOR_TONES: dict[str, tuple[str, str]] = {
    "warm": ("暖色调", "warm color grade"),
    "cool": ("冷色调", "cool color grade"),
    "neutral": ("中性色调", "neutral color grade"),
    "monochrome": ("黑白", "monochrome, black and white"),
    "high_contrast": ("高对比", "high contrast color grade"),
    "pastel": ("粉彩低饱和", "soft pastel color palette"),
    "warm_neutral": ("暖中性色调", "warm neutral color grade"),
    "teal_orange": ("青橙色调", "teal and orange color grade"),
    "desaturated": ("低饱和", "desaturated muted colors"),
    "vivid": ("高饱和鲜艳", "vivid saturated colors"),
}

TRANSITIONS: dict[str, tuple[str, str]] = {
    "cut": ("硬切", "hard cut"),
    "dissolve": ("叠化", "dissolve"),
    "fade_in": ("淡入", "fade in"),
    "fade_out": ("淡出", "fade out"),
    "wipe": ("划像", "wipe"),
    "slide_left": ("左滑转场", "slide left"),
    "zoom_transition": ("变焦转场", "zoom transition"),
    "match_cut": ("匹配剪辑", "match cut"),
}

_INDEX: dict[str, dict[str, str]] = {}


def _canon(value: Any) -> str:
    text = str(value if value is not None else "").strip().lower()
    for ch in (" ", "-", "'", ".", "/"):
        text = text.replace(ch, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _build_index() -> None:
    """Alias table + a backwards index over the config's own cn/en labels."""
    sections = {
        "shot_size": SHOT_SIZES,
        "camera_angle": CAMERA_ANGLES,
        "camera_movement": CAMERA_MOVEMENTS,
        "lighting": LIGHTING_TYPES,
    }
    for name, table in sections.items():
        index: dict[str, str] = {}
        for key, labels in table.items():
            index[_canon(key)] = key
            for text in labels.values():
                # "extreme close-up shot, ECU" -> both halves are usable keys.
                normalized = str(text).replace("（", "(").replace("）", ")")
                for piece in normalized.split(","):
                    token = _canon(piece.strip(" ()"))
                    if token and token not in index:
                        index[token] = key
                # Chinese labels are often slashed synonyms: "远景/大全景(EWS)".
                for piece in str(labels.get("cn", "")).replace("）", ")").replace("（", "(").split("/"):
                    token = piece.strip("()").strip()
                    if token:
                        index.setdefault(_canon(token.replace("(", "_").replace(")", "")), key)
                        index.setdefault(token, key)
        index.update({k: v for k, v in _ALIASES[name].items()})
        _INDEX[name] = index


_build_index()


def resolve(section: str, value: Any) -> str | None:
    """Return the canonical key for ``value`` or ``None`` when unknown."""
    raw = value if isinstance(value, str) else ""
    if not raw.strip():
        return None
    index = _INDEX.get(section, {})
    canon = _canon(raw)
    if canon in index:
        key = index[canon]
        return key or None
    # Chinese terms are not touched by lowercasing; try the raw form as-is.
    if raw in index:
        key = index[raw]
        return key or None
    # last resort: a canonical key embedded in a longer phrase
    for token, key in index.items():
        if token and len(token) > 3 and token in canon:
            return key or None
    return None


def label(section: str, key: str | None, lang: str) -> str:
    table = {"shot_size": SHOT_SIZES, "camera_angle": CAMERA_ANGLES, "camera_movement": CAMERA_MOVEMENTS, "lighting": LIGHTING_TYPES}[section]
    if not key or key not in table:
        return ""
    field = "cn" if lang == "zh" else "en"
    return table[key].get(field, "")


def color_tone_label(value: Any, lang: str) -> str:
    """Translate a colour tone key, falling back to the raw author text."""
    raw = str(value if value is not None else "").strip()
    if not raw:
        return ""
    key = _canon(raw)
    if key in COLOR_TONES:
        return COLOR_TONES[key][0] if lang == "zh" else COLOR_TONES[key][1]
    return raw


def transition_label(value: Any, lang: str) -> str:
    raw = _canon(value)
    if raw in TRANSITIONS:
        return TRANSITIONS[raw][0] if lang == "zh" else TRANSITIONS[raw][1]
    return str(value or "").strip()


def unmapped(section: str, value: Any) -> str:
    """Human-readable note for a field the engine could not interpret."""
    key = _canon(value)
    if key in _ALIASES.get(section, {}):
        return ""
    return str(value or "").strip()
