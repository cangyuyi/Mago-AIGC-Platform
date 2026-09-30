"""Base agent class that all agents inherit from."""

from __future__ import annotations

from typing import Any

from src.common.logger import get_logger
from src.common.streaming import emit_chunk, emit_thinking
from src.config import Settings, get_settings
from src.llm.gateway import LLMGateway, get_llm_gateway

logger = get_logger(__name__)


class BaseAgent:
    """Base class for all agent implementations."""

    name: str = "base"
    description: str = ""

    def __init__(
        self,
        llm: LLMGateway | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm or get_llm_gateway()
        self.settings = settings or get_settings()
        self.logger = get_logger(f"agent.{self.name}")

    @property
    def llm_available(self) -> bool:
        """Return whether the injected gateway has usable provider credentials."""
        return bool(getattr(self.llm, "is_configured", False))

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent and return state updates.

        Subclasses must implement this method.
        """
        raise NotImplementedError

    def system_prompt(self) -> str:
        """Return the system prompt for this agent. Override in subclasses."""
        return f"You are {self.name}, a helpful AI assistant."

    def _msg(self, role: str, content: str) -> dict[str, str]:
        return {"role": role, "content": content}

    async def call_llm(
        self,
        user_message: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        history: list[dict[str, str]] | None = None,
        response_format: dict | None = None,
    ) -> str:
        """Call LLM with the agent's system prompt and return response text."""
        messages = []
        messages.append(self._msg("system", system_prompt or self.system_prompt()))
        if history:
            messages.extend(history)
        messages.append(self._msg("user", user_message))

        resp = await self.llm.chat(
            messages=messages,
            model=model or self.settings.default_model,
            temperature=temperature,
            response_format=response_format,
        )
        return resp.choices[0].message.content or ""

    async def stream_llm(
        self,
        user_message: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        history: list[dict[str, str]] | None = None,
    ):
        """Stream LLM response chunks."""
        messages = []
        messages.append(self._msg("system", system_prompt or self.system_prompt()))
        if history:
            messages.extend(history)
        messages.append(self._msg("user", user_message))

        async for chunk in self.llm.chat_stream(
            messages=messages,
            model=model or self.settings.default_model,
            temperature=temperature,
        ):
            yield chunk

    async def call_llm_streaming(
        self,
        user_message: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Stream an LLM answer while forwarding each token to the SSE client.

        The returned string is the full concatenated answer, so callers can keep
        parsing structured output exactly as they do with ``call_llm``. Without a
        configured provider this falls back to a single non-streamed call, which
        keeps offline/demo runs working.
        """
        if not self.llm_available:
            return ""

        accumulated: list[str] = []
        async for chunk in self.stream_llm(
            user_message=user_message,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            history=history,
        ):
            accumulated.append(chunk)
            emit_chunk(self.name, chunk)
        return "".join(accumulated)

    def emit_progress(self, text: str) -> None:
        """Publish a human-readable progress line to the SSE stream."""
        emit_thinking(self.name, text)
