"""CharacterAgent - Manages character profiles and ensures cross-shot consistency."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

from src.agents.base import BaseAgent

CHARACTER_PROMPT = """你是一位AI角色设计师，擅长根据文字描述或参考图创建角色卡。

用户会描述一个角色，你需要输出：
- 结构化的角色视觉特征（面部/发型/体型/服装/肤色/标志性特征）
- 适合AI生成的prompt_fragment（嵌入每个镜头prompt的固定描述段）
- AI参数建议（FaceID权重/IP-Adapter参数）

## 输出格式（严格JSON）
{
  "name": "角色名称",
  "gender": "male/female/non-binary/unknown",
  "age_appearance": "child/teen/young_adult/adult/middle_aged/senior",
  "ethnicity": "asian/white/black/latino/middle_eastern/south_asian/mixed",
  "face_description": "面部详细描述（脸型/五官/眼睛/鼻子/嘴唇）",
  "hair_description": "发型发色详细描述",
  "body_description": "体型描述",
  "clothing_default": "默认服装描述",
  "skin_details": "肤色/皮肤特征",
  "distinctive_features": ["标志性特征1"],
  "personality_vibe": "气质关键词",
  "faceid_weight": 0.8,
  "ip_adapter_scale": 0.7,
  "reference_strategy": "faceid/instantid/description_only",
  "prompt_fragment": "自动生成的角色描述段，用于每个镜头的prompt（英文逗号分隔，可直接拼接入prompt）",
  "negative_fragment": "负向词（不需要的特征）",
  "tags": ["标签1"]
}
严格输出JSON，用中文描述，但prompt_fragment用英文。
"""


class CharacterAgent(BaseAgent):
    name = "character_designer"
    description = "Creates and manages character profiles for cross-shot consistency"

    def system_prompt(self) -> str:
        return CHARACTER_PROMPT

    async def create_character(self, description: str, ref_images: list[str] | None = None) -> dict[str, Any]:
        if not self.llm_available:
            return self._offline_character(description)
        resp = await self.call_llm(user_message=description, temperature=0.5, response_format={"type": "json_object"})
        return self._parse(resp)

    async def generate_prompt_fragment(self, char: dict[str, Any]) -> str:
        frag_parts = []
        for field in ["face_description", "hair_description", "body_description", "clothing_default", "skin_details"]:
            if char.get(field):
                frag_parts.append(str(char[field]))
        if char.get("distinctive_features"):
            frag_parts.append(", ".join(char["distinctive_features"]))
        return ", ".join(frag_parts)

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return state

    def _parse(self, text: str) -> dict[str, Any]:
        try:
            t = text.strip()
            if t.startswith("```"):
                t = t.split("\n", 1)[1]
            if t.endswith("```"):
                t = t.rsplit("```", 1)[0]
            data = json.loads(t.strip())
            data["id"] = str(uuid4())[:8]
            return cast(dict[str, Any], data)
        except Exception as e:
            self.logger.error("char_parse_error", error=str(e))
            return self._offline_character("")

    def _offline_character(self, desc: str) -> dict[str, Any]:
        return {
            "id": str(uuid4())[:8],
            "name": "主角",
            "gender": "female",
            "age_appearance": "young_adult",
            "ethnicity": "asian",
            "face_description": "oval face, bright eyes, natural makeup",
            "hair_description": "long dark hair, soft waves",
            "body_description": "slim build",
            "clothing_default": "white casual top",
            "skin_details": "fair skin, natural complexion",
            "distinctive_features": ["small mole near eye"],
            "personality_vibe": "friendly and warm",
            "faceid_weight": 0.8,
            "ip_adapter_scale": 0.7,
            "reference_strategy": "faceid",
            "prompt_fragment": "young asian woman, oval face, bright eyes, long dark wavy hair, slim build, white casual top, fair skin",
            "negative_fragment": "masculine features, old face",
            "tags": ["female", "young", "asian"],
        }


STYLE_AGENT_PROMPT = """你是一位视觉风格专家，擅长把视觉风格描述转化为AI可识别的风格提示词。

输出格式（严格JSON）：
{
  "name": "风格名称",
  "category": "visual_style/lighting/color_grading/lens/director/cinematography",
  "description": "风格描述",
  "positive_fragment": "英文正向风格词（逗号分隔）",
  "negative_fragment": "英文负向词（逗号分隔）",
  "dominant_colors": ["#hex1","#hex2"],
  "lighting_style": "光线类型",
  "color_tone": "色调",
  "lens_and_camera": "镜头/相机/焦距",
  "parameter_hints": {"cfg_scale":7, "steps":30}
}
严格输出JSON。
"""


class StyleAgent(BaseAgent):
    name = "style_designer"
    description = "Creates visual style presets for consistent aesthetic"

    def system_prompt(self) -> str:
        return STYLE_AGENT_PROMPT

    async def create_style(self, description: str, category: str = "visual_style") -> dict[str, Any]:
        if not self.llm_available:
            return self._offline_style(description, category)
        prompt = f"风格类别: {category}\n描述: {description}"
        resp = await self.call_llm(user_message=prompt, temperature=0.5, response_format={"type": "json_object"})
        return self._parse(resp)

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return state

    def _parse(self, text: str) -> dict[str, Any]:
        try:
            t = text.strip()
            if t.startswith("```"):
                t = t.split("\n", 1)[1]
            if t.endswith("```"):
                t = t.rsplit("```", 1)[0]
            data = json.loads(t.strip())
            data["id"] = str(uuid4())[:8]
            return cast(dict[str, Any], data)
        except Exception:
            return self._offline_style("", "visual_style")

    def _offline_style(self, desc: str, category: str) -> dict[str, Any]:
        presets = {
            "cinematic": {
                "positive_fragment": "cinematic lighting, film grain, anamorphic lens, shallow depth of field, color graded, teal and orange",
                "dominant_colors": ["#FF8C00", "#008080", "#1A1A2E"],
            },
            "warm_cozy": {
                "positive_fragment": "warm golden light, soft bokeh, cozy atmosphere, pastel tones, natural lighting",
                "dominant_colors": ["#FFDAB9", "#FFF5E6", "#FFB347"],
            },
            "cool_tech": {
                "positive_fragment": "cool blue lighting, neon accents, high contrast, futuristic, clean lines",
                "dominant_colors": ["#00BFFF", "#1A1A2E", "#333333"],
            },
        }
        preset = presets["cinematic"]
        return {
            "id": str(uuid4())[:8],
            "name": "电影感风格",
            "category": category,
            "description": "电影级画质，青橙色调",
            "positive_fragment": preset["positive_fragment"],
            "negative_fragment": "flat lighting, overexposed, amateur",
            "dominant_colors": preset["dominant_colors"],
            "lighting_style": "dramatic side lighting",
            "color_tone": "teal_orange",
            "lens_and_camera": "35mm anamorphic lens, f/1.8",
            "parameter_hints": {"cfg_scale": 7, "steps": 30},
        }
