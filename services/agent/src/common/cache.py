"""Redis cache client with JSON serialization and TTL support."""

from __future__ import annotations

import json
import os
from typing import Any

import redis.asyncio as redis

from src.common.logger import get_logger

logger = get_logger(__name__)


class CacheClient:
    """Async Redis cache client."""

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl: int = 3600,
    ):
        self._redis_url = redis_url or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
        self._default_ttl = default_ttl
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._client

    async def ping(self) -> bool:
        try:
            client = await self._get_client()
            return bool(await client.ping())
        except Exception as e:
            logger.warning(f"cache_ping_failed: {e}")
            return False

    async def get(self, key: str) -> Any | None:
        """Get a value from cache, auto-deserializing JSON."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"cache_get_failed key={key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set a value in cache, auto-serializing to JSON."""
        try:
            client = await self._get_client()
            serialized = json.dumps(value, default=str)
            await client.set(key, serialized, ex=ttl or self._default_ttl)
            return True
        except Exception as e:
            logger.warning(f"cache_set_failed key={key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            client = await self._get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"cache_delete_failed key={key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern (e.g., 'knowledge:*')."""
        try:
            client = await self._get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return int(await client.delete(*keys))
            return 0
        except Exception as e:
            logger.warning(f"cache_invalidate_failed pattern={pattern}: {e}")
            return 0

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


# Singleton
_cache: CacheClient | None = None


def get_cache(redis_url: str | None = None) -> CacheClient:
    """Return the process-wide cache client configured for the application.

    ``Settings`` reads values from ``.env`` without populating ``os.environ``.
    Accepting the resolved URL here keeps native launches and Compose launches
    on the same Redis instance instead of silently falling back to localhost.
    """
    global _cache
    if _cache is None:
        _cache = CacheClient(redis_url=redis_url)
    elif redis_url and _cache._redis_url != redis_url:
        # Do not log Redis URLs: they may contain passwords.
        logger.warning("cache_config_changed_reinitializing")
        # The cache client is lazily connected, so replacing an unneeded
        # instance is safe here. The application lifespan closes the active
        # instance during shutdown.
        _cache = CacheClient(redis_url=redis_url)
    return _cache
