"""
Trend Analysis Agent.
Analyzes collected trend topics, detects lifecycle stages,
clusters related trends, and generates insights.
"""

from __future__ import annotations

import json
from typing import Any

from src.common.logger import get_logger
from src.schemas.trend import LifecycleStage, TrendTopicSchema

logger = get_logger(__name__)


class TrendAnalyzerAgent:
    """
    Analyzes trend data to detect emerging opportunities,
    lifecycle transitions, and cross-platform trend correlations.
    """

    def __init__(self, llm_gateway=None):
        self.llm_gateway = llm_gateway

    async def analyze(self, query: str = "") -> str:
        """Crawl the enabled platforms and return a compact trend summary.

        The graph used to call ``analyze`` even though this class only exposed
        lower-level helpers.  Keeping the crawl orchestration here makes the
        graph and the HTTP trend-insights endpoint use the same analysis
        semantics.  ``query`` is intentionally accepted for graph
        compatibility; category/keyword extraction belongs to the topic
        recommender and should not change the raw crawl results.
        """
        del query  # Reserved for future category/keyword-aware analysis.
        from src.crawlers.pipeline import CrawlerPipeline

        pipeline = CrawlerPipeline()
        results = await pipeline.crawl_all_platforms()
        trends_by_platform = {platform: result.topics for platform, result in results.items()}
        trends = pipeline.get_all_topics(results)
        alerts = self.get_rising_alerts(trends)
        cross_platform = self.get_cross_platform_trends(trends_by_platform)
        summary = await self.generate_trend_summary(trends, alerts)

        if cross_platform:
            summary = f"{summary} 跨平台共振话题：{cross_platform[0]['title']}。"
        return summary

    def detect_lifecycle_transitions(
        self, current: list[TrendTopicSchema], previous: list[TrendTopicSchema]
    ) -> list[dict[str, Any]]:
        """
        Compare current trends with previous snapshot to detect lifecycle changes.
        Returns list of trend transitions with stage changes.
        """
        prev_map = {t.title: t for t in previous}
        transitions = []

        for topic in current:
            prev = prev_map.get(topic.title)
            if not prev:
                transitions.append(
                    {
                        "title": topic.title,
                        "platform": topic.platform,
                        "change": "new",
                        "current_stage": LifecycleStage.EMERGING.value,
                        "growth": topic.hot_value_growth,
                        "hot_value": topic.hot_value,
                        "action": "monitor",  # emerging trends to watch
                    }
                )
                continue

            current_growth = topic.hot_value_growth or 0
            prev_growth = prev.hot_value_growth or 0

            if current_growth > 1.0 and prev_growth < 0.5:
                change = "entering_rising"
                action = "alert"  # important: rising trend
            elif current_growth < -0.3 and prev_growth > 0:
                change = "entering_declining"
                action = "avoid"
            elif current_growth > 0 and prev_growth > 0:
                change = "sustained_growth"
                action = "consider"
            elif current_growth < -0.5:
                change = "rapid_decline"
                action = "avoid"
            else:
                change = "stable"
                action = "monitor"

            transitions.append(
                {
                    "title": topic.title,
                    "platform": topic.platform,
                    "category": topic.category,
                    "change": change,
                    "current_stage": topic.extra.get("lifecycle_stage", "unknown"),
                    "growth": current_growth,
                    "hot_value": topic.hot_value,
                    "action": action,
                }
            )

        return transitions

    def get_cross_platform_trends(self, trends_by_platform: dict[str, list[TrendTopicSchema]]) -> list[dict]:
        """
        Identify trends appearing across multiple platforms (strong signal).
        """
        title_platforms: dict[str, list[str]] = {}
        title_topics: dict[str, list[TrendTopicSchema]] = {}

        for platform, trends in trends_by_platform.items():
            for t in trends:
                # Normalize title for matching (simplified)
                normalized = t.title.strip().lower()
                if normalized not in title_platforms:
                    title_platforms[normalized] = []
                    title_topics[normalized] = []
                title_platforms[normalized].append(platform)
                title_topics[normalized].append(t)

        cross_platform: list[dict[str, Any]] = []
        for title, platforms in title_platforms.items():
            if len(platforms) >= 2:
                topics = title_topics[title]
                data = topics[0]
                cross_platform.append(
                    {
                        "title": data.title,
                        "platforms": platforms,
                        "platform_count": len(platforms),
                        "category": data.category,
                        "max_hot_value": max((t.hot_value or 0) for t in topics),
                        "avg_growth": sum(t.hot_value_growth or 0 for t in topics) / len(topics),
                        "signal_strength": min(1.0, len(platforms) / 5.0),
                    }
                )

        cross_platform.sort(key=lambda x: x["signal_strength"], reverse=True)
        return cross_platform

    def get_rising_alerts(self, trends: list[TrendTopicSchema], growth_threshold: float = 0.8) -> list[dict]:
        """Get high-priority rising trend alerts."""
        alerts: list[dict[str, Any]] = []
        for t in trends:
            growth = t.hot_value_growth or 0
            if growth >= growth_threshold:
                alerts.append(
                    {
                        "title": t.title,
                        "platform": t.platform,
                        "category": t.category,
                        "growth_rate": growth,
                        "hot_value": t.hot_value,
                        "urgency": "high" if growth > 1.5 else "medium",
                        "recommended_action": "立即跟进" if growth > 1.5 else "密切关注",
                    }
                )
        alerts.sort(key=lambda x: x["growth_rate"], reverse=True)
        return alerts

    async def generate_trend_summary(self, trends: list[TrendTopicSchema], alerts: list[dict]) -> str:
        """Generate a natural-language summary of current trends using LLM."""
        if self.llm_gateway:
            try:
                top_trends = sorted(trends, key=lambda t: t.hot_value_growth or 0, reverse=True)[:15]
                trend_text = "\n".join(
                    f"- [{t.platform}] {t.title} (热度:{t.hot_value}, 增长:{(t.hot_value_growth or 0):.0%}, 分类:{t.category})"
                    for t in top_trends
                )
                _prompt = f"""你是一位短视频趋势分析师。请根据以下当前热点数据，生成一段100字以内的趋势洞察摘要，重点指出：
1. 哪些方向的内容正在爆发
2. 创作者应该抓住什么机会
3. 哪些趋势已经过时需要避开

热点数据：
{trend_text}

高增长预警：
{json.dumps(alerts[:5], ensure_ascii=False, indent=2)}

请用中文回复，语言简洁专业。"""
                response = await self.llm_gateway.chat(
                    messages=[
                        {"role": "system", "content": "你是短视频趋势分析师。"},
                        {"role": "user", "content": _prompt},
                    ],
                    temperature=0.3,
                    max_tokens=300,
                )
                content = response.choices[0].message.content
                if isinstance(content, str) and content.strip():
                    return content.strip()
            except Exception as e:
                logger.error(f"Trend summary generation failed: {e}")

        # Fallback summary
        if alerts:
            return f"当前有{len(alerts)}个快速上升热点，重点关注{alerts[0]['title']}等高增长方向。"
        return "当前热点整体平稳，建议持续监控上升期话题。"
