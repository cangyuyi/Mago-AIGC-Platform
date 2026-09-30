"""Creative knowledge base loader for Script Studio.

Loads and provides access to hooks, story structures, CTAs, emotion curves,
vertical specs, and rhythm patterns from JSON data files.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any, cast

_DATA_DIR = Path(__file__).parent / "data"


@functools.lru_cache(maxsize=1)
def load_json(filename: str) -> Any:
    """Load and cache a JSON file from the data directory."""
    path = _DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_hooks() -> dict[str, Any]:
    return cast(dict[str, Any], load_json("hooks.json"))


def get_story_structures() -> dict[str, Any]:
    return cast(dict[str, Any], load_json("story_structures.json"))


def get_ctas() -> dict[str, Any]:
    return cast(dict[str, Any], load_json("ctas.json"))


def get_emotion_curves() -> dict[str, Any]:
    return cast(dict[str, Any], load_json("emotion_curves.json"))


def get_vertical_specs() -> dict[str, Any]:
    return cast(dict[str, Any], load_json("vertical_specs.json"))


def get_rhythm_patterns() -> dict[str, Any]:
    return cast(dict[str, Any], load_json("rhythm_patterns.json"))


def get_hooks_by_type(hook_type: str) -> list[dict[str, Any]]:
    """Get hook templates filtered by category type."""
    data = get_hooks()
    for cat in data.get("categories", []):
        if cat.get("type") == hook_type:
            return cast(list[dict[str, Any]], cat.get("templates", []))
    return []


def get_structure_by_id(struct_id: str) -> dict[str, Any] | None:
    data = get_story_structures()
    for s in data.get("structures", []):
        if s.get("id") == struct_id:
            return cast(dict[str, Any], s)
    return None


def get_vertical_by_id(vertical_id: str) -> dict[str, Any] | None:
    data = get_vertical_specs()
    for v in data.get("verticals", []):
        if v.get("id") == vertical_id:
            return cast(dict[str, Any], v)
    return None


def get_cta_by_type(cta_type: str) -> list[dict[str, Any]]:
    data = get_ctas()
    return cast(list[dict[str, Any]], [c for c in data.get("strategies", []) if c.get("type") == cta_type])


def get_emotion_curve_by_id(curve_id: str) -> dict[str, Any] | None:
    data = get_emotion_curves()
    for c in data.get("curves", []):
        if c.get("id") == curve_id:
            return cast(dict[str, Any], c)
    return None


def get_knowledge_summary() -> dict[str, Any]:
    """Return counts of all knowledge entries."""
    hooks = get_hooks()
    hook_count = sum(len(cat.get("templates", [])) for cat in hooks.get("categories", []))
    return {
        "hooks": hook_count,
        "story_structures": len(get_story_structures().get("structures", [])),
        "ctas": len(get_ctas().get("strategies", [])),
        "emotion_curves": len(get_emotion_curves().get("curves", [])),
        "vertical_specs": len(get_vertical_specs().get("verticals", [])),
        "rhythm_patterns": len(get_rhythm_patterns().get("patterns", [])),
    }
