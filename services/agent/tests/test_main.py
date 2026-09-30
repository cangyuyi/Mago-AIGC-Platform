"""Basic smoke tests for the agent service."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_agent_health_endpoint(client):
    response = client.get("/api/v1/agent/health")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "running"


def test_agent_run_rejects_unknown_mode(client):
    response = client.post(
        "/api/v1/agent/run",
        json={"message": "你好", "mode": "not-a-real-mode"},
    )
    assert response.status_code == 422


def test_echo_run_returns_sse(client):
    """Test that the agent run endpoint returns SSE format."""
    with client.stream(
        "POST",
        "/api/v1/agent/run",
        json={"message": "你好", "mode": "echo"},
    ) as response:
        assert response.status_code == 200
        content = response.read().decode("utf-8")
        # Should have SSE events
        assert "event: meta" in content
        assert "event:" in content
        assert "[DONE]" in content


def test_trend_insights_returns_bounded_response_when_crawler_hangs(client, monkeypatch):
    """The dashboard must not spin forever when a trend provider is unavailable."""
    import asyncio
    from types import SimpleNamespace

    from src.api.routes import trends as trends_route

    class SlowPipeline:
        async def crawl_all_platforms(self, category=None):
            del category
            await asyncio.sleep(0.2)
            return {}

        def get_all_topics(self, results):
            del results
            return []

    monkeypatch.setattr(trends_route, "CrawlerPipeline", SlowPipeline)
    monkeypatch.setattr(
        trends_route,
        "get_settings",
        lambda: SimpleNamespace(trend_insights_timeout_seconds=0.1),
    )

    response = client.get("/api/v1/trends/insights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["timed_out"] is True
    assert payload["total_topics"] == 0
    assert payload["trends"] == []

def test_topic_recommendations_work_without_llm_keys(client):
    """Offline/demo mode must still produce usable topic cards."""
    response = client.post(
        "/api/v1/topic-recommendations/generate",
        json={"category": "知识", "count": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["topics"]) == 3
    assert all(topic["title"] for topic in payload["topics"])
    assert payload["model_info"]["engine"].startswith("template")


def test_video_analysis_rejects_unknown_analysis_mode(client):
    response = client.post(
        "/api/v1/viral-videos/analyze",
        json={"url": "https://example.com/video", "analysis_mode": "turbo"},
    )
    assert response.status_code == 422


def test_video_analysis_defaults_to_fast_mode(client, monkeypatch):
    captured = {}

    async def fake_enqueue(*args, **kwargs):
        captured.update(kwargs)
        return True

    # The endpoint only needs to validate and enqueue the request for this
    # contract test; no downloader or LLM should be touched.
    monkeypatch.setattr("src.api.routes.trends._enqueue_task", fake_enqueue)
    response = client.post(
        "/api/v1/viral-videos/analyze",
        json={"url": "https://example.com/video"},
    )
    assert response.status_code == 200
    assert captured["analysis_mode"] == "fast"

