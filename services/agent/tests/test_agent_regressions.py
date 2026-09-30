"""Regression tests for the end-to-end agent wiring."""

from types import SimpleNamespace

import pytest
from fastapi import Request

from src.agents.style.agent import StyleAgent
from src.agents.topic_recommender.agent import TopicRecommenderAgent
from src.agents.trend_analyzer.agent import TrendAnalyzerAgent
from src.agents.viral_analyzer.agent import ViralAnalyzerAgent
from src.api.routes import agent as agent_route
from src.schemas.trend import TopicRecommendRequest


class FakeLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict] = []

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


def test_full_pipeline_uses_legacy_trend_agent_constructor_names() -> None:
    gateway = object()
    assert TrendAnalyzerAgent(llm_gateway=gateway).llm_gateway is gateway
    assert TopicRecommenderAgent(llm_gateway=gateway).llm_gateway is gateway


@pytest.mark.asyncio
async def test_viral_analyzer_propagates_failures_to_task_runner() -> None:
    class FailingPipeline:
        async def analyze(self, **_kwargs):
            raise RuntimeError("download failed")

    with pytest.raises(RuntimeError, match="download failed"):
        await ViralAnalyzerAgent(pipeline=FailingPipeline()).analyze(
            type("Request", (), {"url": "https://example.com/video", "extract_patterns": True, "platform": None, "category": None})()
        )


@pytest.mark.asyncio
async def test_viral_analyzer_treats_download_error_result_as_failure() -> None:
    class FailedDownloadPipeline:
        async def analyze(self, **_kwargs):
            from src.schemas.trend import ViralAnalysisResult

            return ViralAnalysisResult(
                url="https://example.com/video",
                model_info={"download_error": "network unavailable"},
                analysis_version="v2",
            )

    with pytest.raises(RuntimeError, match="network unavailable"):
        await ViralAnalyzerAgent(pipeline=FailedDownloadPipeline()).analyze(
            type("Request", (), {"url": "https://example.com/video", "extract_patterns": True, "platform": None, "category": None})()
        )


@pytest.mark.asyncio
async def test_style_agent_runs_with_string_llm_input_and_json_response() -> None:
    llm = FakeLLM('{"style_name": "Test Style", "tags": ["test"]}')
    result = await StyleAgent(llm=llm).run(
        {
            "creative_brief": {"title": "Test project"},
            "script": {"logline": "A short test story"},
            "steps_completed": [],
        }
    )

    assert result["style"]["style_name"] == "Test Style"
    assert result["steps_completed"] == ["style_design"]
    assert isinstance(llm.calls[0]["messages"][-1]["content"], str)
    assert llm.calls[0]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_full_route_wires_trend_and_topic_gateways(monkeypatch) -> None:
    captured: dict = {}
    gateway = object()

    def fake_build_full_graph(**deps):
        captured.update(deps)
        return object()

    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: gateway)
    monkeypatch.setattr(agent_route, "build_full_graph", fake_build_full_graph)

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/agent/run"})
    response = await agent_route.run_agent(
        agent_route.ChatRequest(message="test", mode="full"),
        request,
    )

    assert response.media_type == "text/event-stream"
    assert captured["trend_agent"].llm_gateway is gateway
    assert captured["topic_agent"].llm_gateway is gateway


@pytest.mark.asyncio
async def test_agent_run_propagates_authenticated_user_id(monkeypatch) -> None:
    captured: dict = {}

    class FakeGraph:
        async def ainvoke(self, state, config=None):
            captured["state"] = state
            captured["config"] = config
            return {"steps_completed": [], "current_step": "done"}

    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_echo_graph", lambda agent: FakeGraph())

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/agent/run"})
    request.state.user_id = "user-123"
    response = await agent_route.run_agent(
        agent_route.ChatRequest(message="test", mode="echo"),
        request,
    )

    async for _chunk in response.body_iterator:
        pass

    assert captured["state"]["user_id"] == "user-123"
    assert captured["config"]["configurable"]["thread_id"].startswith("user-123:")
    assert captured["config"]["configurable"]["thread_id"] != "anonymous"


@pytest.mark.asyncio
async def test_agent_threads_are_scoped_to_authenticated_user(monkeypatch) -> None:
    captured: dict = {}

    class FakeGraph:
        async def ainvoke(self, state, config=None):
            captured["config"] = config
            return {"steps_completed": [], "current_step": "done"}

    monkeypatch.setattr(agent_route, "get_llm_gateway", lambda: object())
    monkeypatch.setattr(agent_route, "build_echo_graph", lambda agent: FakeGraph())

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/agent/run"})
    request.state.user_id = "user-456"
    response = await agent_route.run_agent(
        agent_route.ChatRequest(message="test", mode="echo", project_id="project-1"),
        request,
    )

    async for _chunk in response.body_iterator:
        pass

    assert captured["config"]["configurable"]["thread_id"] == "user-456:project-1"


def test_version_manager_scopes_versions_by_owner() -> None:
    from src.agents.hitl.version_manager import VersionManager

    manager = VersionManager()
    assert manager.save_version("entity-1", {"value": "alice"}, owner_id="alice") == "v1"
    assert manager.save_version("entity-1", {"value": "bob"}, owner_id="bob") == "v1"

    assert manager.list_versions("entity-1", owner_id="alice")[0]["version_id"] == "v1"
    assert manager.rollback("entity-1", "v1", owner_id="alice") == {"value": "alice"}
    assert manager.rollback("entity-1", "v1", owner_id="bob") == {"value": "bob"}
    assert manager.rollback("entity-1", "v1", owner_id="mallory") is None

@pytest.mark.asyncio
async def test_project_scoped_run_rejects_non_uuid_project_id(monkeypatch) -> None:
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/agent/run"})
    request.state.user_id = "user-123"
    monkeypatch.setattr(
        agent_route,
        "get_settings",
        lambda: type("Settings", (), {"agent_auth_enabled": True})(),
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        await agent_route._validate_project_access(request, "not-a-uuid")

    assert error.value.status_code == 400


def test_agent_settings_accept_compose_host_and_port_names() -> None:
    from src.config import Settings

    settings = Settings(APP_HOST="127.0.0.1", APP_PORT=8123)
    assert settings.host == "127.0.0.1"
    assert settings.port == 8123

@pytest.mark.asyncio
async def test_topic_recommendations_fill_requested_count_for_every_category() -> None:
    agent = TopicRecommenderAgent()
    categories = [None, "美妆", "美食", "时尚", "3C", "剧情", "知识", "生活", "旅游", "未知"]

    for category in categories:
        result = await agent.recommend(TopicRecommendRequest(category=category, count=30))
        titles = [topic.title for topic in result.topics]
        assert len(titles) == 30, category
        assert len(set(titles)) == 30, category
        assert result.model_info["engine"] == "template+pattern+trend"


def test_llm_gateway_reports_configuration_state() -> None:
    from src.config import Settings
    from src.llm.gateway import LLMGateway

    assert LLMGateway(settings=Settings()).is_configured is False
    assert LLMGateway(settings=Settings(openai_api_key="test-key")).is_configured is True
