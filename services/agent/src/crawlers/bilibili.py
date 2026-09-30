"""
Bilibili (B站) hot/ranking crawler.
Uses the public ranking API.
"""

from __future__ import annotations

from src.crawlers.base import BaseCrawler
from src.schemas.trend import Platform, TrendTopicSchema

logger = __import__("src.common.logger", fromlist=["get_logger"]).get_logger(__name__)


class BilibiliCrawler(BaseCrawler):
    PLATFORM = "bilibili"
    BASE_URL = "https://www.bilibili.com"
    HOT_SEARCH_URL = "https://app.bilibili.com/x/v2/search/hot"
    RANKING_URL = "https://api.bilibili.com/x/web-interface/ranking/v2"

    async def crawl_hot_list(self, category: str | None = None) -> list[TrendTopicSchema]:
        topics: list[TrendTopicSchema] = []
        try:
            data = await self._get_json(self.HOT_SEARCH_URL, headers={"Referer": "https://www.bilibili.com/"})
            items = data.get("data", {}).get("list", [])
            for i, item in enumerate(items):
                title = item.get("keyword", "")
                if not title:
                    continue
                topics.append(
                    TrendTopicSchema(
                        platform=Platform.BILIBILI,
                        title=title,
                        category=category or item.get("category_type", "综合"),
                        hot_value=int(item.get("hot_id", 0)),
                        hot_value_growth=float(item.get("heat_score", 0)) / 100 if item.get("heat_score") else None,
                        rank_position=i + 1,
                        url=f"https://search.bilibili.com/all?keyword={title}",
                        cover_url=item.get("icon", ""),
                        tags=item.get("comprehensive_review", "").split(",")
                        if item.get("comprehensive_review")
                        else [],
                        extra={"resource_id": item.get("resource_id", 0)},
                    )
                )
            logger.info(f"[bilibili] Crawled {len(topics)} hot topics")
        except Exception as e:
            logger.error(f"[bilibili] Failed to crawl hot list: {e}")
            topics = self._get_sample_data() if self.allow_sample_data else []
        return topics

    def _get_sample_data(self) -> list[TrendTopicSchema]:
        samples = [
            ("AI绘画新玩法教程", "科技", 8765432, 1.5),
            ("原神新角色深度解析", "游戏", 7654321, 0.89),
            ("程序员转行经验", "知识", 6543210, 0.67),
            ("鬼畜视频最新素材", "娱乐", 5432109, 1.0),
            ("考研400分经验", "学习", 4321098, 0.34),
            ("日系治愈系Vlog", "生活", 3210987, 0.45),
        ]
        return [
            TrendTopicSchema(
                platform=Platform.BILIBILI,
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
