"""PromptEngineAgent - Orchestrates prompt generation across all shots and models."""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.prompt_engine.generator import generate_package, get_model_list


class PromptEngineAgent(BaseAgent):
    name = "prompt_engine"
    description = "Generates model-specific prompts for all shots in a storyboard"

    def system_prompt(self) -> str:
        return "You are a prompt engineering expert who generates optimal prompts for AI video/image generation models."

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        storyboard = state.get("storyboard", {})
        script = state.get("script")
        characters = state.get("characters", [])
        style = state.get("style")
        target_models = state.get("target_models", ["kling-v3", "midjourney-v7", "sora-turbo"])
        self.logger.info("prompt_engine_start", shots=len(storyboard.get("shots", [])), models=target_models)
        package = generate_package(storyboard, script, characters, style, target_models)
        return {
            "prompt_package": package,
            "current_step": "prompts_complete",
            "steps_completed": state.get("steps_completed", []) + ["prompts"],
        }

    def get_available_models(self) -> list[dict[str, Any]]:
        return get_model_list()
