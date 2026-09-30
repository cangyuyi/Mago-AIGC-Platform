"""ARQ worker for durable, long-running Agent tasks.

Run from ``services/agent`` with::

    arq src.worker.WorkerSettings

The API enqueues jobs into Redis and the worker owns execution. Each task
updates ``mago:task:<task_id>`` so status polling works across API replicas.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from pydantic import HttpUrl, TypeAdapter

from src.common.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)
_TASK_TTL_SECONDS = 24 * 60 * 60


async def _update_task(ctx: dict[str, Any], task_id: str | None, **updates: Any) -> None:
    """Merge task updates into the Redis JSON status document."""
    if not task_id:
        return
    redis = ctx.get("redis")
    if redis is None:
        logger.warning("task_status_skipped_without_redis task_id=%s", task_id)
        return

    key = f"mago:task:{task_id}"
    try:
        raw = await redis.get(key)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        task = json.loads(raw) if raw else {"id": task_id}
        if not isinstance(task, dict):
            task = {"id": task_id}
        task.update(updates)
        await redis.set(key, json.dumps(task, default=str), ex=_TASK_TTL_SECONDS)
    except Exception:
        logger.exception("task_status_update_failed task_id=%s", task_id)


async def startup(ctx: dict[str, Any]) -> None:
    """Initialize shared worker resources."""
    settings = get_settings()
    ctx["settings"] = settings
    logger.info("worker_starting redis_url=%s", settings.redis_url.split("@")[-1])

    from src.crawlers.pipeline import CrawlerPipeline
    from src.llm.gateway import LLMGateway

    ctx["crawler_pipeline"] = CrawlerPipeline()
    ctx["llm_gateway"] = LLMGateway()
    logger.info("worker_ready")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Release worker-owned resources."""
    logger.info("worker_shutting_down")


async def analyze_video_task(
    ctx: dict[str, Any],
    url: str,
    platform: str | None = None,
    category: str | None = None,
    analysis_mode: Literal["fast", "accurate"] = "fast",
    extract_patterns: bool = True,
    task_id: str | None = None,
    owner_user_id: str | None = None,
) -> dict[str, Any]:
    """Analyze one video and persist running/progress/completed status."""
    from src.agents.viral_analyzer.agent import ViralAnalyzerAgent
    from src.schemas.trend import Platform, ViralVideoSubmit
    from src.video_tools.pipeline import VideoAnalysisPipeline

    del owner_user_id  # ownership is already stored in the task document
    await _update_task(ctx, task_id, status="running", progress=0, stage="starting")
    progress_updates: list[asyncio.Task[None]] = []

    def on_progress(progress: Any) -> None:
        message = getattr(progress, "message", "")
        stage = getattr(progress, "stage", "processing")
        pct = float(getattr(progress, "progress", 0))
        logger.info("task_progress task_id=%s stage=%s progress=%.0f%%", task_id, stage, pct * 100)
        if task_id:
            progress_updates.append(
                asyncio.create_task(
                    _update_task(
                        ctx,
                        task_id,
                        progress=max(0, min(100, int(pct * 100))),
                        stage=stage,
                        message=message,
                    )
                )
            )

    settings = ctx.get("settings")
    pipeline = VideoAnalysisPipeline(
        asr_engine=getattr(settings, "asr_engine", "whisper"),
        scene_mode=analysis_mode,
        on_progress=on_progress,
    )
    agent = ViralAnalyzerAgent(pipeline=pipeline, llm_gateway=ctx.get("llm_gateway"))

    try:
        request = ViralVideoSubmit(
            url=TypeAdapter(HttpUrl).validate_python(url),
            platform=Platform(platform) if platform else None,
            category=category,
            analysis_mode=analysis_mode,
            extract_patterns=extract_patterns,
        )
        result = await agent.analyze(
            request,
            on_progress=lambda pct, stage, msg: on_progress(
                type("Progress", (), {"progress": pct, "stage": stage, "message": msg})()
            ),
        )
        if progress_updates:
            await asyncio.gather(*progress_updates, return_exceptions=True)
        payload = result.model_dump()
        await _update_task(ctx, task_id, status="completed", progress=100, result=payload)
        logger.info("video_analysis_completed task_id=%s", task_id)
        return payload
    except Exception:
        await _update_task(ctx, task_id, status="failed", error="task failed")
        logger.exception("video_analysis_failed task_id=%s", task_id)
        raise


async def crawl_hot_list_task(
    ctx: dict[str, Any],
    platform: str | None = None,
    category: str | None = None,
    task_id: str | None = None,
    owner_user_id: str | None = None,
) -> dict[str, Any]:
    """Crawl one platform or all configured platforms."""
    from src.schemas.trend import Platform

    del owner_user_id
    await _update_task(ctx, task_id, status="running", progress=0, stage="crawling")
    try:
        pipeline = ctx.get("crawler_pipeline")
        if pipeline is None:
            from src.crawlers.pipeline import CrawlerPipeline

            pipeline = CrawlerPipeline()
        if platform:
            result = await pipeline.crawl_platform(Platform(platform), category=category)
            payload = {
                "platform": getattr(result.platform, "value", result.platform),
                "items_found": result.items_found,
                "items_new": result.items_new,
                "duration_ms": result.duration_ms,
                "error": result.error,
            }
        else:
            results = await pipeline.crawl_all_platforms(category=category)
            payload = {
                "platforms": list(results.keys()),
                "total_found": sum(r.items_found for r in results.values()),
                "total_new": sum(r.items_new for r in results.values()),
                "errors": {p: r.error for p, r in results.items() if r.error},
            }
        await _update_task(ctx, task_id, status="completed", progress=100, result=payload, **payload)
        return payload
    except Exception:
        await _update_task(ctx, task_id, status="failed", error="task failed")
        logger.exception("crawl_task_failed task_id=%s", task_id)
        raise


async def generate_topic_recommendations_task(
    ctx: dict[str, Any],
    category: str | None = None,
    keywords: list[str] | None = None,
    reference_urls: list[str] | None = None,
    count: int = 10,
    task_id: str | None = None,
    owner_user_id: str | None = None,
) -> dict[str, Any]:
    """Generate topic recommendations and persist task status."""
    from src.agents.topic_recommender.agent import TopicRecommenderAgent
    from src.schemas.trend import TopicRecommendRequest

    del owner_user_id
    await _update_task(ctx, task_id, status="running", progress=0, stage="generating")
    try:
        agent = TopicRecommenderAgent(llm_gateway=ctx.get("llm_gateway"))
        request = TopicRecommendRequest(
            category=category,
            keywords=keywords or [],
            reference_video_urls=reference_urls or [],
            count=count,
        )
        response = await agent.recommend(request)
        payload = response.model_dump()
        await _update_task(ctx, task_id, status="completed", progress=100, result=payload)
        return payload
    except Exception:
        await _update_task(ctx, task_id, status="failed", error="task failed")
        logger.exception("topic_recommendation_failed task_id=%s", task_id)
        raise


def _redis_settings():
    from arq.connections import RedisSettings

    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    """ARQ settings loaded by the ``arq`` CLI."""

    redis_settings = _redis_settings()
    functions = [
        analyze_video_task,
        crawl_hot_list_task,
        generate_topic_recommendations_task,
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    keep_result = 3600
    job_timeout = 600
