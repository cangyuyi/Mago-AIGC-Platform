"""Regression tests for durable Agent task submission and status updates."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.api.routes import trends
from src.worker import _update_task


def _request(*, pool=None) -> Request:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/test",
            "app": SimpleNamespace(state=SimpleNamespace(arq_pool=pool)),
        }
    )
    return request


class FakePool:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def enqueue_job(self, function: str, *args, **kwargs):
        self.calls.append((function, args, kwargs))
        return object()


@pytest.mark.asyncio
async def test_enqueue_task_uses_arq_and_preserves_task_id(monkeypatch) -> None:
    pool = FakePool()
    monkeypatch.setattr(
        trends,
        "get_settings",
        lambda: SimpleNamespace(environment="production", debug=False),
    )

    queued = await trends._enqueue_task(
        _request(pool=pool),
        "analyze_abc",
        "analyze_video_task",
        task_id="analyze_abc",
        owner_user_id="user-1",
        url="https://example.com/video",
    )

    assert queued is True
    assert pool.calls == [
        (
            "analyze_video_task",
            (),
            {
                "_job_id": "analyze_abc",
                "task_id": "analyze_abc",
                "owner_user_id": "user-1",
                "url": "https://example.com/video",
            },
        )
    ]


@pytest.mark.asyncio
async def test_enqueue_task_does_not_fallback_in_production(monkeypatch) -> None:
    monkeypatch.setattr(
        trends,
        "get_settings",
        lambda: SimpleNamespace(environment="production", debug=False),
    )

    with pytest.raises(HTTPException) as error:
        await trends._enqueue_task(_request(), "crawl_abc", "crawl_hot_list_task")

    assert error.value.status_code == 503


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {
            "mago:task:task-1": json.dumps({"id": "task-1", "status": "queued", "owner_user_id": "user-1"})
        }

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int):
        self.values[key] = value
        assert ex > 0
        return True


@pytest.mark.asyncio
async def test_worker_task_status_update_merges_existing_owner() -> None:
    redis = FakeRedis()
    await _update_task({"redis": redis}, "task-1", status="running", progress=10)

    task = json.loads(redis.values["mago:task:task-1"])
    assert task == {"id": "task-1", "status": "running", "owner_user_id": "user-1", "progress": 10}
