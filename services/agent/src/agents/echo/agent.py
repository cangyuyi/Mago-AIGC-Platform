"""Echo agent for testing the LLM chain end-to-end.

Simply echoes input with a greeting - validates that the LLM call chain works.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent


class EchoAgent(BaseAgent):
    name = "echo"
    description = "Test agent that echoes input with a greeting"

    def system_prompt(self) -> str:
        return (
            "You are 芒果(Mago)创意助手，一个专业的短视频AI创意伙伴。"
            "用中文回复，语气友好热情。"
            "收到用户消息后，用一句简短亲切的话回应用户，"
            "然后告诉用户你可以帮他做：灵感发散、脚本写作、分镜设计、提示词生成。"
        )

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("current_input", "")
        self.logger.info("echo_agent_run", input_length=len(user_input))

        # If no API key is configured, return a friendly offline message
        if not self.llm_available:
            response_text = (
                f"你好！👋 我是Mago创意助手。收到你的消息："
                f"「{user_input}」\n\n"
                "LLM API Key尚未配置，所以我目前只能回复这条测试消息。"
                "请在 .env 中配置 OPENAI_API_KEY 或其他LLM API Key后，"
                "我就可以帮你做灵感发散、脚本写作、分镜设计、提示词生成啦！"
            )
        else:
            response_text = await self.call_llm(
                user_message=user_input,
                temperature=0.8,
            )

        messages = state.get("messages", [])
        messages.append({"role": "assistant", "content": response_text})

        return {
            "messages": messages,
            "current_step": "echo_done",
            "steps_completed": state.get("steps_completed", []) + ["echo"],
        }
