"""Unified LLM gateway using LiteLLM.

Provides a single interface for calling any supported model with
automatic fallback, cost tracking, and structured output support.
"""

from collections.abc import AsyncIterator
from typing import Any

import litellm
from litellm import acompletion, aembedding
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    RateLimitError,
    Timeout,
)

from src.common.exceptions import LLMError
from src.common.logger import get_logger
from src.config import Settings, get_settings

logger = get_logger(__name__)

# Configure litellm
litellm.drop_params = True  # silently drop unsupported params
litellm.set_verbose = False


class LLMGateway:
    """Central LLM gateway with fallback and cost tracking."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._configure_keys()

    @property
    def is_configured(self) -> bool:
        """Whether at least one provider credential is configured.

        Keeping this check on the gateway lets callers distinguish an injected
        gateway object from a gateway that can actually make an upstream LLM
        request.  This is especially important for the offline/demo mode,
        where the gateway is still constructed so the rest of the app can use
        one dependency shape.
        """
        return any(
            (
                self.settings.openai_api_key,
                self.settings.anthropic_api_key,
                self.settings.google_api_key,
                self.settings.deepseek_api_key,
                self.settings.zhipu_api_key,
                self.settings.dashscope_api_key,
            )
        )

    def _configure_keys(self) -> None:
        """Set API keys from settings."""
        import os

        if self.settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
        if self.settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key
        if self.settings.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.settings.google_api_key
        if self.settings.deepseek_api_key:
            os.environ["DEEPSEEK_API_KEY"] = self.settings.deepseek_api_key

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        response_format: dict | None = None,
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a chat completion request.

        Args:
            messages: List of {role, content} message dicts.
            model: Model identifier (defaults to settings.default_model).
            temperature: Sampling temperature (0-2).
            max_tokens: Max response tokens.
            stream: Whether to stream the response.
            response_format: Structured output format (e.g. {"type":"json_object"}).
            tools: Function calling tool definitions.

        Returns:
            The completion response object.
        """
        model = model or self.settings.default_model

        params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        if response_format:
            params["response_format"] = response_format
        if tools:
            params["tools"] = tools
            params["tool_choice"] = kwargs.pop("tool_choice", "auto")
        params.update(kwargs)

        try:
            response = await acompletion(**params)
            return response
        except (APIConnectionError, Timeout) as e:
            logger.error("llm_connection_error", model=model, error=str(e))
            raise LLMError(f"Connection error to {model}: {e}", model=model)
        except RateLimitError as e:
            logger.error("llm_rate_limit", model=model, error=str(e))
            raise LLMError(f"Rate limit hit for {model}: {e}", model=model)
        except APIError as e:
            logger.error("llm_api_error", model=model, error=str(e))
            raise LLMError(f"API error from {model}: {e}", model=model)
        except Exception as e:
            logger.error("llm_unexpected_error", model=model, error=str(e))
            raise LLMError(f"Unexpected error calling {model}: {e}", model=model)

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion, yielding text chunks."""
        model = model or self.settings.default_model
        response = await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Get embeddings for a list of texts."""
        model = model or self.settings.embedding_model
        try:
            response = await aembedding(model=model, input=texts)
            return [d["embedding"] for d in response.data]
        except Exception as e:
            logger.error("embedding_error", model=model, error=str(e))
            raise LLMError(f"Embedding failed: {e}", model=model)

    def get_system_message(self, content: str) -> dict[str, str]:
        """Helper to create a system message."""
        return {"role": "system", "content": content}

    def get_user_message(self, content: str) -> dict[str, str]:
        """Helper to create a user message."""
        return {"role": "user", "content": content}

    def get_assistant_message(self, content: str) -> dict[str, str]:
        """Helper to create an assistant message."""
        return {"role": "assistant", "content": content}


# Singleton instance
_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    """Get or create the singleton LLM gateway."""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
