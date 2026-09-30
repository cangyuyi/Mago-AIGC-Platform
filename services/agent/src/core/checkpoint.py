"""LangGraph checkpointer factory.

Workflow graphs pause at human-in-the-loop checkpoints and later resume from
the exact node where they stopped. That only works when the checkpointer
outlives the request that created the pause, so production deployments must
back it with a durable store.

Resolution order (most durable first):

1. ``CHECKPOINTER_URL`` — a ``postgresql://`` or ``redis://`` DSN. Both
   backends keep checkpoints outside the process, so a paused run survives a
   restart, a rolling deploy, or a second API replica.
2. ``AGENT_CHECKPOINT_PATH`` — a SQLite file. Single-node durability, which is
   a good fit for local development and small self-hosted deployments.
3. In-memory ``MemorySaver`` — process-local. Every paused run is lost when the
   process exits, so this is acceptable only for tests and demos.

The selected backend is logged at startup so an operator can tell whether a
restart would drop in-flight human approvals.
"""

from __future__ import annotations

import threading
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from src.common.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)

_lock = threading.Lock()
_cached: Any = None
_cached_identity: str | None = None


def _build_postgres(url: str) -> Any:
    from langgraph.checkpoint.postgres import PostgresSaver

    # ``from_conn_string`` returns a context manager; enter it and keep the
    # saver alive for the lifetime of the process.
    ctx = PostgresSaver.from_conn_string(url)
    saver = ctx.__enter__()
    saver.setup()
    logger.info("checkpointer_ready", backend="postgres")
    return saver


def _build_redis(url: str) -> Any:
    from langgraph.checkpoint.redis import RedisSaver

    ctx = RedisSaver.from_conn_string(url)
    saver = ctx.__enter__()
    try:
        # RedisSaver.setup() creates the RediSearch indices. A server without
        # the RedisJSON/Search modules still stores plain keys, so a missing
        # setup is not fatal for single-instance use.
        saver.setup()
    except Exception:  # pragma: no cover - depends on server capabilities
        logger.warning("checkpointer_redis_setup_skipped")
    logger.info("checkpointer_ready", backend="redis")
    return saver


def _build_sqlite(path: str) -> Any:
    from langgraph.checkpoint.sqlite import SqliteSaver

    ctx = SqliteSaver.from_conn_string(path)
    saver = ctx.__enter__()
    saver.setup()
    logger.info("checkpointer_ready", backend="sqlite", path=path)
    return saver


def build_checkpointer() -> Any:
    """Return a checkpointer for the configured backend.

    Falls back to ``MemorySaver`` when nothing durable is configured or when
    the optional backend package is not installed, and reports that in the logs.
    """
    settings = get_settings()
    dsn = (getattr(settings, "checkpointer_url", "") or "").strip()
    sqlite_path = (getattr(settings, "agent_checkpoint_path", "") or "").strip()

    if dsn:
        try:
            if dsn.startswith(("postgres://", "postgresql://")):
                return _build_postgres(dsn)
            if dsn.startswith(("redis://", "rediss://")):
                return _build_redis(dsn)
            logger.warning("checkpointer_url_unsupported_scheme", dsn_scheme=dsn.split(":", 1)[0])
        except ImportError as exc:
            logger.warning(
                "checkpointer_backend_package_missing",
                error=str(exc),
                hint="install langgraph-checkpoint-postgres / -redis / -sqlite",
            )
        except Exception as exc:
            logger.error("checkpointer_backend_init_failed", error=str(exc))

    if sqlite_path:
        try:
            return _build_sqlite(sqlite_path)
        except ImportError as exc:
            logger.warning("checkpointer_sqlite_package_missing", error=str(exc))
        except Exception as exc:
            logger.error("checkpointer_sqlite_init_failed", error=str(exc))

    logger.warning(
        "checkpointer_in_memory",
        detail="HITL pauses are process-local and will be lost on restart; "
        "set CHECKPOINTER_URL or AGENT_CHECKPOINT_PATH for durable runs.",
    )
    return MemorySaver()


def get_checkpointer() -> Any:
    """Return the process-wide checkpointer, creating it on first use."""
    global _cached, _cached_identity

    settings = get_settings()
    identity = f"{getattr(settings, 'checkpointer_url', '')}|{getattr(settings, 'agent_checkpoint_path', '')}"

    with _lock:
        if _cached is None or _cached_identity != identity:
            _cached = build_checkpointer()
            _cached_identity = identity
        return _cached


def reset_checkpointer_cache() -> None:
    """Drop the cached checkpointer (used by tests that swap configuration)."""
    global _cached, _cached_identity
    with _lock:
        _cached = None
        _cached_identity = None
