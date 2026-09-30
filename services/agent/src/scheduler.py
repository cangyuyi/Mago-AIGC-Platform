"""
APScheduler-based crawl scheduler.
Runs periodic hot list crawls for all configured platforms.
"""

from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.common.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)


class CrawlScheduler:
    """Manages scheduled crawling of platform hot lists."""

    def __init__(self, crawler_pipeline=None, arq_pool=None):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.pipeline = crawler_pipeline
        self.arq_pool = arq_pool
        self._running = False

    def start(self):
        """Start the scheduler with configured intervals."""
        if self._running:
            return
        if self.pipeline is None and self.arq_pool is None:
            logger.warning("[scheduler] Disabled: no crawler pipeline or ARQ queue available")
            return

        # Schedule platform crawls
        interval_min = self.settings.crawl_interval_minutes
        platforms = [p.strip() for p in self.settings.crawl_enabled_platforms.split(",") if p.strip()]

        for platform in platforms:
            self.scheduler.add_job(
                self._crawl_platform_job,
                trigger=IntervalTrigger(minutes=interval_min),
                args=[platform],
                id=f"crawl_{platform}",
                name=f"Crawl {platform} hot list",
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300,
            )
            logger.info(f"[scheduler] Scheduled {platform} crawl every {interval_min} min")

        # Schedule a comprehensive crawl at startup (after 30s delay)
        self.scheduler.add_job(
            self._crawl_all_job,
            trigger="date",  # run once
            id="crawl_all_startup",
            name="Initial crawl of all platforms",
            replace_existing=True,
        )

        self.scheduler.start()
        self._running = True
        logger.info(f"[scheduler] Started with {len(platforms)} platform crawlers, interval={interval_min}min")

    def shutdown(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("[scheduler] Stopped")

    async def _crawl_platform_job(self, platform: str):
        """Job to crawl a single platform."""
        logger.info(f"[scheduler] Starting scheduled crawl for {platform}")
        try:
            if self.pipeline:
                from src.schemas.trend import Platform

                result = await self.pipeline.crawl_platform(Platform(platform))
                logger.info(f"[scheduler] {platform} crawl done: {result.items_found} topics, {result.duration_ms}ms")
            elif self.arq_pool:
                await self.arq_pool.enqueue_job("crawl_hot_list_task", platform)
                logger.info(f"[scheduler] {platform} crawl job enqueued")
        except asyncio.CancelledError:
            logger.info(f"[scheduler] {platform} crawl cancelled during shutdown")
        except Exception as e:
            logger.error(f"[scheduler] {platform} crawl failed: {e}")

    async def _crawl_all_job(self):
        """Job to crawl all platforms at startup."""
        logger.info("[scheduler] Running initial crawl of all platforms...")
        await asyncio.sleep(30)  # Wait for services to be ready
        try:
            if self.pipeline:
                results = await self.pipeline.crawl_all_platforms()
                total = sum(r.items_found for r in results.values())
                logger.info(f"[scheduler] Initial crawl complete: {total} topics found")
            elif self.arq_pool:
                await self.arq_pool.enqueue_job("crawl_hot_list_task", None)
        except asyncio.CancelledError:
            logger.info("[scheduler] Initial crawl cancelled during shutdown")
        except Exception as e:
            logger.error(f"[scheduler] Initial crawl failed: {e}")

    def trigger_crawl_now(self, platform: str | None = None) -> str:
        """Manually trigger a crawl."""
        import uuid

        job_id = f"manual_{uuid.uuid4().hex[:8]}"
        self.scheduler.add_job(
            self._crawl_platform_job if platform else self._crawl_all_job,
            args=[platform] if platform else [],
            id=job_id,
            name=f"Manual crawl {platform or 'all'}",
            replace_existing=False,
        )
        return job_id
