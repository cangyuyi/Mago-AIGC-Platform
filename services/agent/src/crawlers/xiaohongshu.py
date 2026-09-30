"""
Xiaohongshu (小红书/RED) hot topics crawler.
"""

from __future__ import annotations

from src.crawlers.base import BaseCrawler
from src.schemas.trend import Platform, TrendTopicSchema

logger = __import__("src.common.logger", fromlist=["get_logger"]).get_logger(__name__)


class XiaohongshuCrawler(BaseCrawler):
    PLATFORM = "xiaohongshu"
    BASE_URL = "https://www.xiaohongshu.com"
    HOT_LIST_URL = "https://edith.xiaohongshu.com/api/sns/v1/search/hot_list"

    async def crawl_hot_list(self, category: str | None = None) -> list[TrendTopicSchema]:
        topics: list[TrendTopicSchema] = []
        try:
            headers = {
                "Referer": "https://www.xiaohongshu.com/explore",
                "Origin": "https://www.xiaohongshu.com",
            }
            data = await self._get_json(self.HOT_LIST_URL, headers=headers)
            items = data.get("data", {}).get("items", [])
            for i, item in enumerate(items):
                note = item if isinstance(item, dict) else {}
                title = note.get("query", note.get("name", ""))
                if not title:
                    continue
                topics.append(
                    TrendTopicSchema(
                        platform=Platform.XIAOHONGSHU,
                        title=title,
                        category=category or note.get("category", "生活"),
                        hot_value=int(note.get("hot_score") or note.get("score") or 0),
                        rank_position=i + 1,
                        url=f"https://www.xiaohongshu.com/search_result?keyword={title}",
                        cover_url=note.get("image", {}).get("url") if isinstance(note.get("image"), dict) else None,
                        tags=[note.get("style", "")] if note.get("style") else [],
                        extra={"note_count": note.get("note_count", 0)},
                    )
                )
            logger.info(f"[xiaohongshu] Crawled {len(topics)} hot topics")
        except Exception as e:
            logger.error(f"[xiaohongshu] Failed to crawl hot list: {e}")
            topics = self._get_sample_data() if self.allow_sample_data else []
        return topics

    def _get_sample_data(self) -> list[TrendTopicSchema]:
        samples = [
            ("早C晚A正确顺序", "美妆", 9123456, 1.35),
            ("秋日氛围感拍照", "摄影", 8012345, 0.98),
            ("一周减脂餐食谱", "美食", 7901234, 0.65),
            ("平价好物分享", "购物", 6789012, 0.45),
            ("租房改造ins风", "家居", 5678901, 0.87),
            ("通勤穿搭公式", "时尚", 4567890, 1.1),
            ("旅行小众目的地", "旅游", 3456789, 0.56),
        ]
        return [
            TrendTopicSchema(
                platform=Platform.XIAOHONGSHU,
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
