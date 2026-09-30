"""StyleAgent - Directs visual style, cinematography, and color grading for the project."""

from __future__ import annotations

import json
from typing import Any

from src.agents.base import BaseAgent

STYLE_PROMPT = """你是一位资深电影视觉风格指导，擅长为短视频/广告/短剧项目确定整体视觉风格。

根据创意简报和脚本内容，你需要输出：
- 整体视觉风格定义（电影感/写实/赛博朋克/日系清新/复古港风等）
- 色调方案（主色/辅色/肤色处理/对比度/饱和度）
- 光影风格（光线类型/光比/色温/光源方向）
- 镜头语言偏好（焦段/运镜/构图风格）
- 参考影片/导演/摄影指导
- 适合AI生成的style_prompt_fragment（英文，可拼接进各镜头prompt）
- 负面风格词（避免的视觉效果）

## 输出格式（严格JSON）
{
  "style_name": "风格名称",
  "style_category": "cinematic/realistic/cyberpunk/japanese_fresh/retro_hk/anime/film_noir/minimalist/vintage/futuristic",
  "color_palette": {
    "primary_colors": ["主色1"],
    "secondary_colors": ["辅色1"],
    "skin_tone_handling": "肤色处理方式",
    "contrast": "high/medium/low",
    "saturation": "high/medium/low",
    "color_temperature": "warm/neutral/cool"
  },
  "lighting": {
    "style": "光线风格",
    "ratio": "光比描述",
    "source_direction": "光源方向",
    "quality": "hard/soft/diffused"
  },
  "cinematography": {
    "preferred_lenses": ["焦段偏好"],
    "camera_movement": "运镜偏好",
    "composition": "构图风格",
    "aspect_ratio": "9:16/16:9/1:1/2.35:1"
  },
  "references": ["参考影片/导演"],
  "style_prompt_fragment": "英文风格描述段，直接拼接入各镜头prompt",
  "negative_fragment": "负面风格词（英文）",
  "grading_notes": "调色备注",
  "tags": ["标签1"]
}
严格输出JSON，用中文描述，但style_prompt_fragment和negative_fragment用英文。
"""


class StyleAgent(BaseAgent):
    name = "style_director"
    description = "Determines visual style, cinematography, and color direction"

    def system_prompt(self) -> str:
        return STYLE_PROMPT

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        brief = state.get("creative_brief", {})
        script = state.get("script", {})
        self.logger.info("style_director_start", brief_title=brief.get("title", ""))

        brief_text = (
            f"项目标题: {brief.get('title', '')}\n"
            f"品牌/产品: {brief.get('brand_product', '')}\n"
            f"目标受众: {brief.get('target_audience', '')}\n"
            f"情感基调: {brief.get('emotion_tone', '')}\n"
            f"核心卖点: {brief.get('core_selling_points', '')}\n"
            f"参考风格: {brief.get('visual_reference', '')}\n"
        )
        script_text = f"脚本概述: {script.get('logline', script.get('summary', ''))}" if script else ""

        result = await self.call_llm(
            user_message=f"请为以下项目设计视觉风格：\n{brief_text}\n{script_text}",
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        style = self._parse_style(result)
        if not style:
            style = self._default_style(brief)

        return {
            "style": style,
            "current_step": "style_complete",
            "steps_completed": state.get("steps_completed", []) + ["style_design"],
        }

    def _parse_style(self, text: str) -> dict[str, Any]:
        """Parse the model response while tolerating fenced JSON output."""
        try:
            value = text.strip()
            if value.startswith("```"):
                value = value.split("\n", 1)[1]
            if value.endswith("```"):
                value = value.rsplit("```", 1)[0]
            parsed = json.loads(value.strip())
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError, ValueError, IndexError) as exc:
            self.logger.error("style_parse_error", error=str(exc))
            return {}

    def _default_style(self, brief: dict[str, Any]) -> dict[str, Any]:
        return {
            "style_name": "Cinematic Clean",
            "style_category": "cinematic",
            "color_palette": {
                "primary_colors": ["teal", "orange"],
                "secondary_colors": ["warm white"],
                "skin_tone_handling": "natural warm",
                "contrast": "medium",
                "saturation": "medium",
                "color_temperature": "warm",
            },
            "lighting": {
                "style": "soft key + rim light",
                "ratio": "3:1",
                "source_direction": "45 degree key",
                "quality": "soft",
            },
            "cinematography": {
                "preferred_lenses": ["35mm", "50mm"],
                "camera_movement": "smooth gimbal",
                "composition": "rule of thirds",
                "aspect_ratio": "9:16",
            },
            "references": [],
            "style_prompt_fragment": "cinematic lighting, shallow depth of field, teal and orange color grading, film grain",
            "negative_fragment": "flat lighting, oversaturated, blurry, watermark",
            "grading_notes": "slight teal shadows, warm highlights",
            "tags": ["cinematic", "commercial"],
        }
