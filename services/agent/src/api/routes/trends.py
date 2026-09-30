"""
Trend Intelligence API routes.
Provides endpoints for:
- Triggering crawls
- Getting trend data
- Submitting video analysis
- Getting topic recommendations
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl

from src.agents.topic_recommender.agent import TopicRecommenderAgent
from src.agents.trend_analyzer.agent import TrendAnalyzerAgent
from src.agents.viral_analyzer.agent import ViralAnalyzerAgent
from src.api.auth import require_roles
from src.common.cache import CacheClient
from src.common.logger import get_logger
from src.config import get_settings
from src.crawlers.pipeline import CrawlerPipeline
from src.llm.gateway import get_llm_gateway
from src.schemas.trend import (
    Platform,
    TopicRecommendRequest,
    ViralVideoSubmit,
)

router = APIRouter(prefix="/api/v1", tags=["trend-intelligence"])
logger = get_logger(__name__)

# Redis is used when available; the bounded in-memory map keeps local/offline
# development usable when Redis is not running.
_tasks: dict[str, dict] = {}
_crawl_cache: dict[str, Any] = {}
_MAX_MEMORY_TASKS = 1000
_TASK_TTL_SECONDS = 24 * 60 * 60


def _task_cache(request: Request) -> CacheClient | None:
    cache = getattr(request.app.state, "cache", None)
    return cache if isinstance(cache, CacheClient) else None


async def _save_task(task_id: str, cache: CacheClient | None, **updates: Any) -> dict:
    task = _tasks.setdefault(task_id, {"id": task_id})
    task.update(updates)
    if len(_tasks) > _MAX_MEMORY_TASKS:
        finished = [key for key, value in _tasks.items() if value.get("status") in {"completed", "failed"}]
        for key in finished[: max(1, len(_tasks) - _MAX_MEMORY_TASKS)]:
            _tasks.pop(key, None)
    if cache is not None:
        await cache.set(f"mago:task:{task_id}", task, ttl=_TASK_TTL_SECONDS)
    return task


def _request_user_id(request: Request) -> str | None:
    user_id = getattr(request.state, "user_id", None)
    return str(user_id) if user_id else None


def _public_task(task: dict) -> dict:
    public = dict(task)
    public.pop("owner_user_id", None)
    return public


async def _get_task(task_id: str, cache: CacheClient | None, request: Request) -> dict | None:
    task: dict | None = None
    if cache is not None:
        cached = await cache.get(f"mago:task:{task_id}")
        if isinstance(cached, dict):
            _tasks[task_id] = cached
            task = cached
    if task is None:
        task = _tasks.get(task_id)
    if task is None:
        return None

    owner = task.get("owner_user_id")
    current_user = _request_user_id(request)
    # In production every task has an owner. Keep anonymous development mode
    # compatible with older in-memory tasks that have no owner field.
    if owner is not None and owner != current_user:
        return None
    return _public_task(task)


async def _enqueue_task(
    request: Request,
    queue_job_id: str,
    function_name: str,
    *args: Any,
    **kwargs: Any,
) -> bool:
    """Enqueue a durable ARQ job, or report that local fallback is allowed.

    FastAPI ``BackgroundTasks`` is intentionally limited to development/test
    mode. It runs inside the API process and would silently lose long-running
    work during a restart or when multiple replicas are used.
    """
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is not None:
        try:
            job = await pool.enqueue_job(function_name, *args, _job_id=queue_job_id, **kwargs)
            if job is None:
                raise RuntimeError(f"ARQ rejected duplicate or expired job: {queue_job_id}")
            return True
        except Exception as exc:
            logger.error("task_enqueue_failed task_id=%s function=%s error=%s", queue_job_id, function_name, exc)
            settings = get_settings()
            if settings.environment.lower() not in {"development", "dev", "test"} and not settings.debug:
                raise HTTPException(status_code=503, detail="background task queue is unavailable") from exc
            return False

    settings = get_settings()
    if settings.environment.lower() in {"development", "dev", "test"} or settings.debug:
        logger.warning("task_queue_unavailable_using_dev_fallback task_id=%s", queue_job_id)
        return False
    raise HTTPException(status_code=503, detail="background task queue is unavailable")


class CrawlNowRequest(BaseModel):
    platform: Platform | Literal["all"] | None = Field(default=None, description="Platform to crawl, null=all")
    category: str | None = None


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    platform: Platform | None = None
    category: str | None = None
    analysis_mode: Literal["fast", "accurate"] = Field(default="fast", description="fast or accurate")
    extract_patterns: bool = True


class TopicRequest(BaseModel):
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    reference_video_urls: list[str] = Field(default_factory=list)
    count: int = Field(default=10, ge=1, le=30)
    target_platform: str | None = None


@router.post("/trends/crawl-now")
async def trigger_crawl(req: CrawlNowRequest, background_tasks: BackgroundTasks, request: Request):
    """Trigger an immediate crawl (runs in background)."""
    require_roles(request, "owner", "admin")
    task_id = f"crawl_{uuid.uuid4().hex[:12]}"
    cache = _task_cache(request)
    await _save_task(
        task_id,
        cache,
        type="crawl",
        owner_user_id=_request_user_id(request),
        platform=req.platform,
        status="queued",
        progress=0,
        started_at=datetime.now(UTC).isoformat(),
    )

    async def _do_crawl():
        try:
            await _save_task(task_id, cache, status="running")
            pipeline = CrawlerPipeline()
            if req.platform and req.platform != "all":
                from src.schemas.trend import Platform

                platform = req.platform if isinstance(req.platform, Platform) else Platform(req.platform)
                result = await pipeline.crawl_platform(platform, category=req.category)
                await _save_task(
                    task_id,
                    cache,
                    status="completed",
                    progress=100,
                    items_found=result.items_found,
                    items_new=result.items_new,
                )
            else:
                results = await pipeline.crawl_all_platforms(category=req.category)
                await _save_task(
                    task_id,
                    cache,
                    status="completed",
                    progress=100,
                    total_found=sum(r.items_found for r in results.values()),
                    total_new=sum(r.items_new for r in results.values()),
                    platforms=list(results.keys()),
                )
        except Exception as e:
            await _save_task(task_id, cache, status="failed", error="task failed")
            logger.error(f"Crawl task {task_id} failed: {e}")

    queued = await _enqueue_task(
        request,
        task_id,
        "crawl_hot_list_task",
        task_id=task_id,
        owner_user_id=_request_user_id(request),
        platform=(req.platform.value if isinstance(req.platform, Platform) else req.platform)
        if req.platform != "all"
        else None,
        category=req.category,
    )
    if not queued:
        background_tasks.add_task(_do_crawl)
    return {"task_id": task_id, "status": "queued", "platform": req.platform}


@router.get("/trends/task/{task_id}")
async def get_task_status(task_id: str, request: Request):
    """Get task status by ID."""
    task = await _get_task(task_id, _task_cache(request), request)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/viral-videos/analyze")
async def analyze_video(req: AnalyzeRequest, background_tasks: BackgroundTasks, request: Request):
    """Submit a video URL for analysis (async, returns task_id)."""
    task_id = f"analyze_{uuid.uuid4().hex[:12]}"
    cache = _task_cache(request)
    await _save_task(
        task_id,
        cache,
        type="analysis",
        owner_user_id=_request_user_id(request),
        url=str(req.url),
        status="queued",
        progress=0,
        result=None,
    )

    async def _do_analysis():
        progress_updates: list[asyncio.Task[dict]] = []
        try:
            await _save_task(task_id, cache, status="running")
            # Keep the development fallback aligned with the ARQ worker: use
            # the configured LLM gateway instead of silently running the
            # video analyzer without one.
            agent = ViralAnalyzerAgent(llm_gateway=get_llm_gateway())
            submit = ViralVideoSubmit(
                url=req.url,
                platform=req.platform,
                category=req.category,
                analysis_mode=req.analysis_mode,
                extract_patterns=req.extract_patterns,
            )

            def _on_progress(pct: float, stage: str, msg: str) -> None:
                # The analyzer emits a synchronous callback from the running
                # event loop. Persist progress asynchronously so Redis-backed
                # status remains useful when the next poll hits another
                # Agent replica. Do not index _tasks directly: bounded cleanup
                # may evict completed entries.
                progress_updates.append(
                    asyncio.create_task(
                        _save_task(
                            task_id,
                            cache,
                            progress=max(0, min(100, int(pct * 100))),
                            stage=stage,
                            message=msg,
                        )
                    )
                )

            result = await agent.analyze(submit, on_progress=_on_progress)
            if progress_updates:
                await asyncio.gather(*progress_updates, return_exceptions=True)
            await _save_task(
                task_id,
                cache,
                status="completed",
                progress=100,
                result=result.model_dump(),
            )
        except Exception as e:
            await _save_task(task_id, cache, status="failed", error="task failed")
            logger.error(f"Analysis task {task_id} failed: {e}")

    queued = await _enqueue_task(
        request,
        task_id,
        "analyze_video_task",
        task_id=task_id,
        owner_user_id=_request_user_id(request),
        url=str(req.url),
        platform=req.platform.value if req.platform else None,
        category=req.category,
        analysis_mode=req.analysis_mode,
        extract_patterns=req.extract_patterns,
    )
    if not queued:
        background_tasks.add_task(_do_analysis)
    return {"task_id": task_id, "status": "queued", "url": str(req.url)}


@router.get("/viral-videos/analyze/{task_id}")
async def get_analysis_result(task_id: str, request: Request):
    """Get analysis task result."""
    task = await _get_task(task_id, _task_cache(request), request)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/topic-recommendations/generate")
async def generate_topics(req: TopicRequest):
    """Generate topic recommendations (synchronous for MVP, takes 2-5s)."""
    # Reuse the configured gateway so this endpoint benefits from the same
    # provider/model settings as the main Agent pipeline.
    agent = TopicRecommenderAgent(llm_gateway=get_llm_gateway())
    request = TopicRecommendRequest(
        category=req.category,
        keywords=req.keywords,
        reference_video_urls=req.reference_video_urls,
        count=req.count,
        target_platform=req.target_platform,
    )
    response = await agent.recommend(request)
    return response.model_dump()


@router.get("/trends/insights")
async def get_trend_insights(platform: str | None = None, category: str | None = None):
    """Get trend insights without allowing an upstream crawler to hang the UI.

    This endpoint is called directly while the trends page is loading. Platform
    sites can be slow or unreachable, so the dashboard-facing request gets a
    bounded timeout and returns a useful empty/partial response instead of
    keeping the browser spinner forever. Full crawls remain available through
    the queued ``/trends/crawl-now`` endpoint.
    """
    settings = get_settings()
    timeout_seconds = max(0.1, settings.trend_insights_timeout_seconds)
    pipeline = CrawlerPipeline()
    timed_out = False
    crawl_errors: dict[str, str] = {}

    try:
        if platform and platform != "all":
            from src.schemas.trend import Platform

            try:
                selected_platform = Platform(platform)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"unsupported platform: {platform}") from exc
            result = await asyncio.wait_for(
                pipeline.crawl_platform(selected_platform, category=category),
                timeout=timeout_seconds,
            )
            all_topics = result.topics
            results_by_platform = {selected_platform.value: result.topics}
            if result.error:
                crawl_errors[selected_platform.value] = result.error
        else:
            results = await asyncio.wait_for(
                pipeline.crawl_all_platforms(category=category),
                timeout=timeout_seconds,
            )
            all_topics = pipeline.get_all_topics(results)
            results_by_platform = {p: r.topics for p, r in results.items()}
            crawl_errors = {p: r.error for p, r in results.items() if r.error}
    except TimeoutError:
        timed_out = True
        all_topics = []
        results_by_platform = {}
        logger.warning(
            "trend_insights_crawl_timeout platform=%s timeout_seconds=%s",
            platform or "all",
            timeout_seconds,
        )

    analyzer = TrendAnalyzerAgent()
    alerts = analyzer.get_rising_alerts(all_topics)
    cross_platform = analyzer.get_cross_platform_trends(results_by_platform)
    summary = await analyzer.generate_trend_summary(all_topics, alerts)

    return {
        "summary": summary,
        "total_topics": len(all_topics),
        "rising_alerts": alerts[:10],
        "cross_platform_trends": cross_platform[:10],
        "trends": [t.model_dump() for t in all_topics[:50]],
        "timed_out": timed_out,
        "errors": crawl_errors,
    }
