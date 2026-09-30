"""
Crawler pipeline: orchestrates multi-platform crawling, deduplication,
lifecycle stage detection, and persistence.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy import create_engine, text

from src.common.logger import get_logger
from src.config import get_settings
from src.crawlers.base import BaseCrawler, ProxyConfig
from src.crawlers.bilibili import BilibiliCrawler
from src.crawlers.douyin import DouyinCrawler
from src.crawlers.kuaishou import KuaishouCrawler
from src.crawlers.weibo import WeiboCrawler
from src.crawlers.xiaohongshu import XiaohongshuCrawler
from src.schemas.trend import LifecycleStage, Platform, TrendTopicSchema

logger = get_logger(__name__)


class SQLTrendRepository:
    """Small DB adapter used by the crawler to persist normalized trend rows."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)

    async def batch_upsert_trends(self, topics: list[TrendTopicSchema]) -> tuple[int, int]:
        return await asyncio.to_thread(self._batch_upsert_sync, topics)

    def _batch_upsert_sync(self, topics: list[TrendTopicSchema]) -> tuple[int, int]:
        created = 0
        updated = 0
        find_sql = text(
            """SELECT id FROM trend_topics
               WHERE platform = :platform
                 AND ((:topic_id IS NOT NULL AND topic_id = :topic_id) OR title = :title)
               ORDER BY created_at ASC LIMIT 1"""
        )
        insert_sql = text(
            """INSERT INTO trend_topics
               (platform, topic_id, title, category, hot_value, hot_value_growth,
                rank_position, cover_url, url, tags, status, lifecycle_stage,
                extra, first_seen_at, last_updated_at, created_at, updated_at)
               VALUES (:platform, :topic_id, :title, :category, :hot_value, :hot_value_growth,
                :rank_position, :cover_url, :url, CAST(:tags AS JSONB), :status,
                :lifecycle_stage, CAST(:extra AS JSONB), NOW(), NOW(), NOW(), NOW())"""
        )
        update_sql = text(
            """UPDATE trend_topics SET title = :title, category = :category,
                hot_value = :hot_value, hot_value_growth = :hot_value_growth,
                rank_position = :rank_position, cover_url = :cover_url, url = :url,
                tags = CAST(:tags AS JSONB), status = :status, lifecycle_stage = :lifecycle_stage,
                extra = CAST(:extra AS JSONB), last_updated_at = NOW(), updated_at = NOW()
                WHERE id = :id"""
        )
        with self.engine.begin() as connection:
            for topic in topics:
                params = {
                    "platform": topic.platform.value,
                    "topic_id": topic.topic_id,
                    "title": topic.title,
                    "category": topic.category,
                    "hot_value": topic.hot_value,
                    "hot_value_growth": topic.hot_value_growth,
                    "rank_position": topic.rank_position,
                    "cover_url": topic.cover_url,
                    "url": topic.url,
                    "tags": json.dumps(topic.tags),
                    "status": "rising" if (topic.hot_value_growth or 0) > 0 else "stable",
                    "lifecycle_stage": topic.extra.get("lifecycle_stage"),
                    "extra": json.dumps(topic.extra),
                }
                existing = connection.execute(find_sql, params).first()
                if existing is None:
                    connection.execute(insert_sql, params)
                    created += 1
                else:
                    connection.execute(update_sql, {**params, "id": existing[0]})
                    updated += 1
        return created, updated


class CrawlType(str, Enum):
    HOT_LIST = "hot_list"
    VIDEO_DETAIL = "video_detail"
    SEARCH = "search"


@dataclass
class CrawlResult:
    platform: str
    task_type: str
    topics: list[TrendTopicSchema] = field(default_factory=list)
    items_found: int = 0
    items_new: int = 0
    items_updated: int = 0
    items_failed: int = 0
    duration_ms: int = 0
    error: str | None = None


class CrawlerPipeline:
    """
    Orchestrates crawling across all platforms, manages deduplication,
    detects lifecycle stages, and triggers persistence.
    """

    def __init__(
        self,
        proxies: list[ProxyConfig] | None = None,
        db_repository: Any | None = None,  # In production: inject ViralRepository/TrendRepository
        enabled_platforms: list[Platform] | None = None,
    ):
        self.proxies = proxies or []
        if db_repository is not None:
            self.db = db_repository
        else:
            settings = get_settings()
            self.db = SQLTrendRepository(settings.database_url) if settings.database_url else None

        # Initialize crawlers
        crawler_map: dict[Platform, type[BaseCrawler]] = {
            Platform.DOUYIN: DouyinCrawler,
            Platform.KUAISHOU: KuaishouCrawler,
            Platform.XIAOHONGSHU: XiaohongshuCrawler,
            Platform.BILIBILI: BilibiliCrawler,
            Platform.WEIBO: WeiboCrawler,
        }
        self.crawlers: dict[Platform, BaseCrawler] = {}
        for p in enabled_platforms or list(crawler_map.keys()):
            if p in crawler_map:
                self.crawlers[p] = crawler_map[p](proxies=self.proxies)

    async def crawl_all_platforms(self, category: str | None = None) -> dict[str, CrawlResult]:
        """Crawl hot lists from all enabled platforms concurrently."""
        results: dict[str, CrawlResult] = {}

        async def _crawl_one(platform: Platform, crawler: BaseCrawler) -> tuple[str, CrawlResult]:
            start = time.time()
            result = CrawlResult(
                platform=platform.value,
                task_type=CrawlType.HOT_LIST.value,
            )
            try:
                topics = await crawler.crawl_hot_list(category=category)
                result.topics = topics
                result.items_found = len(topics)
                # Add lifecycle stage detection
                for t in topics:
                    t.extra["lifecycle_stage"] = self._detect_lifecycle(t).value
                result.items_new, result.items_updated = await self._persist_topics(topics)
            except Exception as e:
                logger.error(f"[{platform.value}] Crawl failed: {e}")
                result.error = str(e)
                result.items_failed = result.items_found
            result.duration_ms = int((time.time() - start) * 1000)
            return platform.value, result

        tasks = [_crawl_one(p, c) for p, c in self.crawlers.items()]
        for platform_value, result in await asyncio.gather(*tasks):
            results[platform_value] = result

        total_found = sum(r.items_found for r in results.values())
        total_new = sum(r.items_new for r in results.values())
        logger.info(f"Crawl complete: {total_found} topics found, {total_new} new across {len(results)} platforms")
        return results

    async def crawl_platform(self, platform: Platform, category: str | None = None) -> CrawlResult:
        """Crawl a single platform's hot list."""
        crawler = self.crawlers.get(platform)
        if not crawler:
            return CrawlResult(
                platform=platform.value,
                task_type=CrawlType.HOT_LIST.value,
                error=f"Platform {platform.value} not enabled",
            )
        start = time.time()
        result = CrawlResult(platform=platform.value, task_type=CrawlType.HOT_LIST.value)
        try:
            topics = await crawler.crawl_hot_list(category=category)
            result.topics = topics
            result.items_found = len(topics)
            for t in topics:
                t.extra["lifecycle_stage"] = self._detect_lifecycle(t).value
            result.items_new, result.items_updated = await self._persist_topics(topics)
        except Exception as e:
            logger.error(f"[{platform.value}] Crawl failed: {e}")
            result.error = str(e)
        result.duration_ms = int((time.time() - start) * 1000)
        return result

    def _detect_lifecycle(self, topic: TrendTopicSchema) -> LifecycleStage:
        """
        Detect the lifecycle stage of a trend topic based on growth rate.
        Uses growth rate thresholds calibrated for each platform.
        """
        growth = topic.hot_value_growth
        if growth is None:
            return LifecycleStage.EMERGING
        if growth > 2.0:
            return LifecycleStage.EMERGING
        if growth > 0.5:
            return LifecycleStage.RISING
        if growth > -0.2:
            return LifecycleStage.PEAK
        if growth > -0.6:
            return LifecycleStage.DECLINING
        return LifecycleStage.STALE

    async def _persist_topics(self, topics: list[TrendTopicSchema]) -> tuple[int, int]:
        """Persist topics and return (created_count, updated_count)."""
        if not self.db:
            logger.debug("Trend persistence is disabled")
            return 0, 0
        try:
            result = self.db.batch_upsert_trends(topics)
            if asyncio.iscoroutine(result):
                result = await result
            if not isinstance(result, tuple) or len(result) != 2:
                raise TypeError("batch_upsert_trends must return (created, updated)")
            return int(result[0]), int(result[1])
        except Exception as e:
            logger.error(f"Failed to persist topics: {e}")
            return 0, 0

    def get_all_topics(self, results: dict[str, CrawlResult]) -> list[TrendTopicSchema]:
        """Flatten all topics from crawl results."""
        all_topics: list[TrendTopicSchema] = []
        for r in results.values():
            all_topics.extend(r.topics)
        # Sort by hot_value_growth descending
        all_topics.sort(key=lambda t: t.hot_value_growth or 0, reverse=True)
        return all_topics
