"""Langfuse LLM observability setup.

Gracefully degrades if langfuse is not installed.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_langfuse = None
_initialized = False


def setup_langfuse() -> Any | None:
    """Initialize Langfuse client and register LiteLLM callback if available."""
    global _langfuse, _initialized
    if _initialized:
        return _langfuse

    enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if not enabled:
        _initialized = True
        return None

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3030")

    if not public_key or not secret_key:
        logger.warning("Langfuse enabled but keys not configured, skipping initialization")
        _initialized = True
        return None

    try:
        from langfuse import Langfuse

        _langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            release=os.getenv("APP_VERSION", "0.1.0"),
        )

        # Register LiteLLM callback
        try:
            import litellm

            litellm.success_callback = getattr(litellm, "success_callback", [])
            litellm.failure_callback = getattr(litellm, "failure_callback", [])
            if "langfuse" not in litellm.success_callback:
                litellm.success_callback.append("langfuse")
            if "langfuse" not in litellm.failure_callback:
                litellm.failure_callback.append("langfuse")
        except Exception as e:
            logger.warning(f"Failed to register Langfuse LiteLLM callback: {e}")

        logger.info("Langfuse initialized successfully")
    except ImportError:
        logger.info("langfuse package not installed, LLM observability disabled")
        _langfuse = None
    except Exception as e:
        logger.warning(f"Langfuse initialization failed: {e}")
        _langfuse = None

    _initialized = True
    return _langfuse


def langfuse_client() -> Any | None:
    if not _initialized:
        return setup_langfuse()
    return _langfuse


def get_langfuse_callback() -> Any | None:
    if not _initialized:
        setup_langfuse()
    if _langfuse is None:
        return None
    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler()
    except Exception:
        return None


def flush_langfuse() -> None:
    if _langfuse is not None:
        try:
            _langfuse.flush()
        except Exception:
            pass
