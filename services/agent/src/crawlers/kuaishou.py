"""
Kuaishou (快手) hot list crawler.
"""

from __future__ import annotations

from src.crawlers.base import BaseCrawler
from src.schemas.trend import Platform, TrendTopicSchema

logger = __import__("src.common.logger", fromlist=["get_logger"]).get_logger(__name__)


class KuaishouCrawler(BaseCrawler):
    PLATFORM = "kuaishou"
    BASE_URL = "https://www.kuaishou.com"
    HOT_LIST_URL = "https://www.kuaishou.com/graphql"

    async def crawl_hot_list(self, category: str | None = None) -> list[TrendTopicSchema]:
        topics: list[TrendTopicSchema] = []
        try:
            # Kuaishou uses GraphQL API for hot list
            payload = {
                "operationName": "hotListQuery",
                "query": "query hotListQuery { visionHotList { list { id name hotValue photoUrl } } }",
                "variables": {},
            }
            headers = {"Content-Type": "application/json", "Referer": "https://www.kuaishou.com/hot"}
            data = await self._get_json(self.HOT_LIST_URL, method="POST", headers=headers, json_data=payload)
            items = data.get("data", {}).get("visionHotList", {}).get("list", [])
            for i, item in enumerate(items):
                topics.append(
                    TrendTopicSchema(
                        platform=Platform.KUAISHOU,
                        topic_id=item.get("id", ""),
                        title=item.get("name", ""),
                        category=category or "热点",
                        hot_value=int(item.get("hotValue", 0)),
                        rank_position=i + 1,
                        cover_url=item.get("photoUrl"),
                        tags=[],
                    )
                )
            logger.info(f"[kuaishou] Crawled {len(topics)} hot topics")
        except Exception as e:
            logger.error(f"[kuaishou] Failed to crawl hot list: {e}")
            topics = self._get_sample_data() if self.allow_sample_data else []
        return topics

    def _get_sample_data(self) -> list[TrendTopicSchema]:
        samples = [
            ("农村美食大赏", "美食", 8234567, 0.67),
            ("搞笑段子合集", "搞笑", 7123456, 0.43),
            ("广场舞新玩法", "生活", 6012345, 0.89),
            ("手工DIY创意", "生活", 5901234, 0.55),
            ("二手车避坑指南", "汽车", 4790123, 0.34),
            ("快手美妆教程", "美妆", 3689012, 0.72),
        ]
        return [
            TrendTopicSchema(
                platform=Platform.KUAISHOU,
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
