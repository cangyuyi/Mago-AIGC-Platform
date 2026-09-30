"""
Douyin (抖音) hot list crawler.
Uses public hot list API endpoints.
"""

from __future__ import annotations

from src.config import get_settings
from src.crawlers.base import BaseCrawler
from src.schemas.trend import Platform, TrendTopicSchema

logger = __import__("src.common.logger", fromlist=["get_logger"]).get_logger(__name__)


class DouyinCrawler(BaseCrawler):
    PLATFORM = "douyin"
    BASE_URL = "https://www.douyin.com"

    # Douyin hot board (public)
    HOT_LIST_URL = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
    HOT_VIDEO_URL = "https://www.douyin.com/aweme/v1/web/hot/search/video/"

    async def crawl_hot_list(self, category: str | None = None) -> list[TrendTopicSchema]:
        """Crawl Douyin hot search list."""
        topics: list[TrendTopicSchema] = []
        try:
            headers = {"Referer": "https://www.douyin.com/hot"}
            cookie = get_settings().douyin_cookie.strip()
            if cookie:
                headers["Cookie"] = cookie
            data = await self._get_json(self.HOT_LIST_URL, headers=headers)
            word_list = data.get("data", {}).get("word_list", [])

            for i, item in enumerate(word_list):
                word = item.get("word", "")
                if not word:
                    continue
                hot_value = item.get("hot_value", 0)
                event_time = item.get("event_time", 0)
                topics.append(
                    TrendTopicSchema(
                        platform=Platform.DOUYIN,
                        topic_id=str(item.get("sentence_tag", {}).get("sentence_id", "")),
                        title=word,
                        category=category or item.get("word_type", {}).get("name", "热点"),
                        hot_value=int(hot_value) if hot_value else None,
                        rank_position=i + 1,
                        url=f"https://www.douyin.com/hot/{item.get('sentence_id', '')}",
                        cover_url=item.get("word_cover", {}).get("url_list", [None])[0]
                        if item.get("word_cover")
                        else None,
                        tags=[t.get("name", "") for t in item.get("related_words", []) if t.get("name")],
                        extra={
                            "event_time": event_time,
                            "hot_label": item.get("label", ""),
                            "video_count": item.get("video_count", 0),
                        },
                    )
                )
            logger.info(f"[douyin] Crawled {len(topics)} hot topics")
        except Exception as e:
            logger.error(f"[douyin] Failed to crawl hot list: {e}")
            if self.allow_sample_data:
                logger.warning("[douyin] Live crawl failed; returning explicitly enabled sample data")
            topics = self._get_sample_data() if self.allow_sample_data else []
        return topics

    def _get_sample_data(self) -> list[TrendTopicSchema]:
        """Sample data for development/testing when live crawling fails."""
        samples = [
            ("国庆出行攻略", "旅游", 9854321, 0.85),
            ("秋日氛围感穿搭", "时尚", 8765432, 0.92),
            ("3分钟快手早餐", "美食", 7654321, 0.45),
            ("AI工具效率提升10倍", "科技", 6543210, 1.2),
            ("普通人逆袭副业", "知识", 5432109, 0.33),
            ("秋季护肤误区", "美妆", 4321098, 0.78),
            ("手机摄影隐藏技巧", "3C", 3210987, 0.56),
            ("租房改造百元预算", "生活", 2109876, 0.21),
        ]
        return [
            TrendTopicSchema(
                platform=Platform.DOUYIN,
                title=title,
                category=cat,
                hot_value=hv,
                hot_value_growth=growth,
                rank_position=i + 1,
                tags=[cat],
                extra={"source": "sample_data"},
            )
            for i, (title, cat, hv, growth) in enumerate(samples)
        ]
