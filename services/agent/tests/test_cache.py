"""Regression tests for Redis cache configuration."""

from __future__ import annotations

from src.common import cache as cache_module


def test_get_cache_uses_resolved_settings_url(monkeypatch) -> None:
    monkeypatch.setattr(cache_module, "_cache", None)

    cache = cache_module.get_cache("redis://:secret@example.test:6380/2")

    assert cache._redis_url == "redis://:secret@example.test:6380/2"


def test_get_cache_reinitializes_when_settings_url_changes(monkeypatch) -> None:
    monkeypatch.setattr(cache_module, "_cache", None)

    first = cache_module.get_cache("redis://localhost:6379/0")
    second = cache_module.get_cache("redis://redis.example.test:6379/4")

    assert second is not first
    assert second._redis_url == "redis://redis.example.test:6379/4"
