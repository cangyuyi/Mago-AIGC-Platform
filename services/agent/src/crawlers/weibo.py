"""
Weibo (微博) hot search crawler.
Uses the public mobile API.
"""

from __future__ import annotations

from src.crawlers.base import BaseCrawler
from src.schemas.trend import Platform, TrendTopicSchema

logger = __import__("src.common.logger", fromlist=["get_logger"]).get_logger(__name__)


class WeiboCrawler(BaseCrawler):
    PLATFORM = "weibo"
    BASE_URL = "https://weibo.com"
    HOT_SEARCH_URL = "https://weibo.com/ajax/side/hotSearch"

    async def crawl_hot_list(self, category: str | None = None) -> list[TrendTopicSchema]:
        topics: list[TrendTopicSchema] = []
        try:
            headers = {"Referer": "https://weibo.com/hot/search"}
            data = await self._get_json(self.HOT_SEARCH_URL, headers=headers)
            realtime = data.get("data", {}).get("realtime", [])
            for i, item in enumerate(realtime):
                word = item.get("word", "")
                if not word:
                    continue
                topics.append(
                    TrendTopicSchema(
                        platform=Platform.WEIBO,
                        topic_id=str(item.get("mid", "")),
                        title=word,
                        category=category or self._map_category(item.get("category", "")),
                        hot_value=int(item.get("num", 0)),
                        hot_value_growth=item.get("growth_rate", 0) / 100 if item.get("growth_rate") else None,
                        rank_position=item.get("rank", i + 1),
                        url=f"https://s.weibo.com/weibo?q=%23{word}%23",
                        cover_url=None,
                        tags=[t for t in [item.get("label_name", "")] if t],
                        extra={
                            "is_hot": item.get("is_hot", False),
                            "is_new": item.get("is_new", False),
                            "subject_label": item.get("subject_label", ""),
                        },
                    )
                )
            logger.info(f"[weibo] Crawled {len(topics)} hot topics")
        except Exception as e:
            logger.error(f"[weibo] Failed to crawl hot list: {e}")
            topics = self._get_sample_data() if self.allow_sample_data else []
        return topics

    def _map_category(self, cat: str) -> str:
        mapping = {"1": "社会", "2": "娱乐", "3": "时尚", "4": "体育", "5": "财经", "6": "科技"}
        return mapping.get(cat, "社会")

    def _get_sample_data(self) -> list[TrendTopicSchema]:
        samples = [
            ("2026国庆档电影", "娱乐", 9999999, 0.76),
            ("AI大模型最新进展", "科技", 8888888, 1.2),
            ("秋季养生食谱", "健康", 7777777, 0.55),
            ("明星穿搭同款", "时尚", 6666666, 0.34),
            ("国足最新比赛", "体育", 5555555, 0.98),
            ("高考改革新政策", "教育", 4444444, 2.3),
        ]
        return [
            TrendTopicSchema(
                platform=Platform.WEIBO,
                title=t,
                category=c,
                hot_value=h,
                hot_value_growth=g,
                rank_position=i + 1,
                tags=[c],
                extra={"source": "sample"},
            )
            for i, (t, c, h, g) in enumerate(samples)
        ]
