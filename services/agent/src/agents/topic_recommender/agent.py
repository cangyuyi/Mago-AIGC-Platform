"""
Topic Recommendation Agent (创意选题推荐).
Core agent for helping creators without inspiration find direction.

Combines:
- Real-time trend data
- Viral video patterns
- Category-specific knowledge
- Cross-platform correlation signals
To produce actionable topic cards with hooks, outlines, and visual concepts.
"""

from __future__ import annotations

import random

from src.common.logger import get_logger
from src.schemas.trend import (
    TopicCard,
    TopicRecommendRequest,
    TopicRecommendResponse,
    TrendTopicSchema,
    ViralPatternSchema,
)

logger = get_logger(__name__)


class TopicRecommenderAgent:
    """
    AI-powered topic recommendation engine.
    The most important agent for creators seeking inspiration.
    Generates 10-30 actionable topic cards based on:
    - Current hot trends + lifecycle position
    - Extracted viral patterns/formulas
    - Category-specific best practices
    - User keywords and reference videos
    """

    # Category-specific topic templates (knowledge base)
    CATEGORY_TEMPLATES: dict[str, list[dict]] = {
        "美妆": [
            {
                "hook_type": "contrast",
                "template": "我用{method}之前vs之后，{effect}差别也太大了",
                "visual": "before/after对比镜头",
            },
            {
                "hook_type": "number",
                "template": "{number}个{group}必知的{technique}，第{n}个99%的人不知道",
                "visual": "快节奏产品展示",
            },
            {
                "hook_type": "pain_point",
                "template": "为什么你涂{product}总是{problem}？因为你少了这一步",
                "visual": "特写错误/正确手法",
            },
            {
                "hook_type": "demo",
                "template": "挑战{time}分钟{look}妆容，手残党也能学会",
                "visual": "加速教程+成果展示",
            },
            {
                "hook_type": "shock",
                "template": "{price}块钱的{product}居然比{expensive}的还好用？",
                "visual": "产品对比+测评",
            },
        ],
        "美食": [
            {"hook_type": "curiosity", "template": "{food}的神仙吃法，我居然才知道", "visual": "食物特写+制作过程"},
            {
                "hook_type": "number",
                "template": "{number}道{time}分钟搞定的{meal}，上班族必收藏",
                "visual": "快切烹饪过程",
            },
            {
                "hook_type": "shock",
                "template": "用{ingredient}做{food}？结果居然是这样的",
                "visual": "惊喜反应+成果展示",
            },
            {
                "hook_type": "pain_point",
                "template": "为什么你做的{dish}总是{problem}？秘诀在这里",
                "visual": "错误vs正确对比",
            },
            {"hook_type": "demo", "template": "挑战{budget}元做{meal}，比外卖强10倍", "visual": "食材购买+烹饪+品尝"},
        ],
        "时尚": [
            {
                "hook_type": "contrast",
                "template": "同一件{cloth}，{groupA}穿vs{groupB}穿差别太大了",
                "visual": "不同风格穿搭对比",
            },
            {"hook_type": "number", "template": "{number}个秋季必入单品，每件不超{price}", "visual": "换装快剪"},
            {
                "hook_type": "curiosity",
                "template": "今年最火的{style}风，到底怎么穿才不显{bad}",
                "visual": "街拍+穿搭细节",
            },
            {
                "hook_type": "story",
                "template": "从{bad_look}到{good_look}，我花了{time}总结的穿搭公式",
                "visual": "个人变化对比",
            },
        ],
        "3C": [
            {
                "hook_type": "shock",
                "template": "{product}隐藏功能大揭秘，{percent}%的人不知道",
                "visual": "手机/产品操作特写",
            },
            {"hook_type": "number", "template": "{number}个APP让你的{device}好用10倍", "visual": "屏幕录制+效果展示"},
            {
                "hook_type": "pain_point",
                "template": "为什么你的{product}总是{problem}？一招解决",
                "visual": "问题展示+解决方案",
            },
            {
                "hook_type": "contrast",
                "template": "{price1}的{product1} vs {price2}的{product2}，差别居然是...",
                "visual": "产品对比测试",
            },
        ],
        "剧情": [
            {
                "hook_type": "story",
                "template": "当{character}发现{twist}，结局万万没想到",
                "visual": "角色特写+反转镜头",
            },
            {"hook_type": "shock", "template": "{behavior}的人，其实{truth}", "visual": "情感场景+表演"},
            {"hook_type": "curiosity", "template": "如果{scenario}，你会{choice}吗？", "visual": "沉浸式视角"},
        ],
        "知识": [
            {"hook_type": "question", "template": "为什么{phenomenon}？{n}个理由颠覆认知", "visual": "动画+实景讲解"},
            {"hook_type": "number", "template": "{number}个{field}冷知识，知道{n}个算我输", "visual": "快节奏知识卡片"},
            {"hook_type": "shock", "template": "你以为{common_belief}？其实完全搞反了", "visual": "反差画面+证据"},
        ],
        "生活": [
            {"hook_type": "demo", "template": "{problem}一招解决，{effect}", "visual": "前后对比+操作演示"},
            {"hook_type": "number", "template": "{number}个居家神器，租房党必备", "visual": "产品展示+使用场景"},
            {
                "hook_type": "story",
                "template": "花{budget}改造{space}，朋友以为花了{big_budget}",
                "visual": "改造前后对比",
            },
        ],
        "旅游": [
            {
                "hook_type": "curiosity",
                "template": "{place}最被低估的{n}个地方，99%的人不知道",
                "visual": "航拍/风景+文字标注",
            },
            {"hook_type": "number", "template": "{budget}元玩转{city}{n}天，详细攻略", "visual": "行程快剪+费用明细"},
        ],
    }

    # Hook type effectiveness by platform
    PLATFORM_HOOK_PREFERENCE = {
        "douyin": ["curiosity", "shock", "number", "demo", "pain_point"],
        "kuaishou": ["story", "demo", "shock", "question"],
        "xiaohongshu": ["pain_point", "number", "curiosity", "contrast", "demo"],
        "bilibili": ["question", "story", "curiosity", "number"],
        "weibo": ["shock", "question", "story"],
    }

    def __init__(self, llm_gateway=None):
        self.llm_gateway = llm_gateway

    async def recommend(
        self,
        request: TopicRecommendRequest,
        current_trends: list[TrendTopicSchema] | None = None,
        viral_patterns: list[ViralPatternSchema] | None = None,
    ) -> TopicRecommendResponse:
        """
        Generate topic recommendations.

        Strategy:
        1. If category is provided, use category templates
        2. Mix in current rising trends as topic angles
        3. Apply viral patterns as formula structures
        4. Add user keywords as custom angles
        5. Generate 10-30 unique topic cards
        6. Score each card for viral potential
        """
        current_trends = current_trends or []
        viral_patterns = viral_patterns or []

        topics: list[TopicCard] = []

        # Get relevant templates
        category = request.category or "综合"
        templates = self.CATEGORY_TEMPLATES.get(category, self._get_general_templates())

        # Get relevant rising trends
        rising_trends = [
            t
            for t in current_trends
            if t.hot_value_growth
            and t.hot_value_growth > 0.3
            and (category in (t.category or "") or not request.category)
        ]
        rising_trends.sort(key=lambda t: t.hot_value_growth or 0, reverse=True)

        # Get relevant patterns
        relevant_patterns = [p for p in viral_patterns if not category or not p.category or p.category == category]

        # Track used titles to avoid duplicates
        used_titles = set()

        # Strategy 1: Trend-driven topics (50% of output)
        for trend in rising_trends[: max(3, request.count // 3)]:
            for template in random.sample(templates, min(2, len(templates))):
                card = self._create_trend_topic(trend, template, request.target_platform, category)
                if card and card.title not in used_titles:
                    topics.append(card)
                    used_titles.add(card.title)
                    if len(topics) >= request.count:
                        break
            if len(topics) >= request.count:
                break

        # Strategy 2: Pattern-driven topics (30% of output)
        for pattern in relevant_patterns[: max(2, request.count // 4)]:
            card = self._create_pattern_topic(pattern, templates, category, request.target_platform)
            if card and card.title not in used_titles:
                topics.append(card)
                used_titles.add(card.title)
                if len(topics) >= request.count:
                    break

        # Strategy 3: Template-based topics (remaining).
        # The catalog is intentionally compact, but the API contract allows up
        # to 30 cards. Use deterministic variation slots instead of stopping
        # after three passes, otherwise categories with four or five templates
        # silently return fewer cards than requested.
        template_count = 0
        max_template_attempts = max(request.count * 2, len(templates) * 3)
        while len(topics) < request.count and template_count < max_template_attempts:
            template = templates[template_count % len(templates)]
            card = self._create_template_topic(
                template,
                category,
                request.keywords,
                request.target_platform,
                variation_index=template_count + 1,
            )
            if card and card.title not in used_titles:
                topics.append(card)
                used_titles.add(card.title)
            template_count += 1

        # Strategy 4: If LLM is available, enhance with AI-generated topics
        if self._llm_is_available() and len(topics) < request.count:
            try:
                ai_topics = await self._generate_ai_topics(request, rising_trends[:5], relevant_patterns[:3])
                for card in ai_topics:
                    if card.title not in used_titles:
                        topics.append(card)
                        used_titles.add(card.title)
                        if len(topics) >= request.count:
                            break
            except Exception as e:
                logger.warning(f"AI topic generation failed: {e}")

        # Score and sort by viral potential
        for card in topics:
            card.estimated_viral_potential = self._score_topic(card, rising_trends, relevant_patterns)
        topics.sort(key=lambda c: c.estimated_viral_potential, reverse=True)

        # Generate trend summary
        trend_summary = await self._generate_summary(rising_trends, category)

        return TopicRecommendResponse(
            topics=topics[: request.count],
            trend_summary=trend_summary,
            model_info={
                "engine": "template+pattern+trend" + ("+llm" if self._llm_is_available() else ""),
                "trends_used": len(rising_trends),
                "patterns_used": len(relevant_patterns),
                "category": category,
            },
        )

    def _create_trend_topic(
        self, trend: TrendTopicSchema, template: dict, platform: str | None, category: str
    ) -> TopicCard | None:
        """Create a topic card based on a trending topic + hook template."""
        title = trend.title
        hook_type = template["hook_type"]

        # Generate hook based on hook type
        hook_suggestions = {
            "question": f"关于{title}，你是不是也一直搞错了？",
            "shock": f"{title}背后的真相，90%的人都不知道！",
            "curiosity": f"当所有人都在讨论{title}时，我发现了一个秘密",
            "number": f"关于{title}的{random.randint(3, 7)}个关键点，最后一个最关键",
            "contrast": f"普通人做{title}vs高手做{title}，差距就在这",
            "pain_point": f"追{title}热点总是慢一步？这个方法帮你抢流量",
            "demo": f"手把手教你蹭{title}热点，这条视频可能会被删",
            "story": f"我因为{title}发生了一件意想不到的事",
        }
        hook = hook_suggestions.get(hook_type, f"关于{title}你必须知道的事")

        return TopicCard(
            title=f"【热点】{title} - {self._get_hook_label(hook_type)}创意",
            hook_suggestion=hook,
            content_direction=f"结合{title}热点，用{template['visual']}的方式呈现{self._get_category_content(category)}，快速切入热点流量。",
            target_platform=self._get_platforms(platform),
            target_duration=f"{random.randint(15, 60)}秒",
            supporting_trends=[title],
            reference_patterns=[],
            key_selling_points=[
                f"紧扣{title}热点",
                f"{self._get_hook_label(hook_type)}开头提升完播率",
                "时效性强，首发优势明显",
            ],
            risk_factors=[
                "热点消退快，需48小时内发布",
                "同质化内容多，需差异化切入",
            ],
            script_outline=f"开头({hook})→ 核心内容(结合{title}展开{self._get_category_content(category)})→ 结尾引导(互动/关注/保存)",
            visual_concept=template["visual"],
            tags=[trend.category or category, title, "热点", "流量密码"],
        )

    def _create_pattern_topic(
        self, pattern, templates: list[dict], category: str, platform: str | None
    ) -> TopicCard | None:
        """Create a topic card based on a viral pattern/formula."""
        template = random.choice(templates) if templates else {"hook_type": "curiosity", "visual": "快节奏剪辑"}
        return TopicCard(
            title=f"【公式】{pattern.name} - 可复用爆款结构",
            hook_suggestion=pattern.key_phrases[0] if pattern.key_phrases else f"用{pattern.name}的方法，结果惊人",
            content_direction=f"运用'{pattern.name}'爆款公式：{pattern.description}。{pattern.formula_template or ''}",
            target_platform=self._get_platforms(platform),
            target_duration=f"{random.randint(20, 90)}秒",
            reference_patterns=[pattern.name],
            key_selling_points=[
                f"已验证的{pattern.pattern_type}公式",
                f"平均爆款分{pattern.avg_viral_score:.0f}",
                "结构可复用，降低试错成本",
            ],
            risk_factors=[
                "公式化内容需要加入个人特色",
                "过度使用同一公式会导致审美疲劳",
            ],
            script_outline=f"按照{pattern.name}结构：开头钩子→铺垫→转折→高潮→CTA",
            visual_concept=template.get("visual", "特写+快切+节奏感"),
            tags=[category, pattern.pattern_type, "爆款公式", "可复用"],
        )

    def _create_template_topic(
        self,
        template: dict,
        category: str,
        keywords: list[str],
        platform: str | None,
        variation_index: int = 1,
    ) -> TopicCard:
        """Create a topic card from a template with unique variation.

        ``variation_index`` is optional to preserve compatibility for callers
        that use this helper directly.
        """
        hook_type = template["hook_type"]
        # Keep the template catalog extensible: a newly added template should
        # not take the whole recommendation endpoint down just because it uses
        # one more placeholder than the built-in examples.  The previous direct
        # ``str.format`` call raised ``KeyError: topic`` for the generic
        # curiosity/number templates, which made the offline/demo endpoint
        # return HTTP 500 when no LLM key was configured.
        context = {
            "method": "正确方法",
            "effect": "效果",
            "number": 3 + (variation_index % 5),
            "group": ["女生", "上班族", "新手", "学生", "懒人"][variation_index % 5],
            "technique": "技巧",
            "n": 2 + (variation_index % 4),
            "topic": self._get_random_keyword(category, variation_index, keywords),
            "product": "护肤品",
            "problem": "卡粉/脱妆",
            "time": 3 + (variation_index % 8),
            "look": ["日常", "通勤", "约会", "懒人", "清透"][variation_index % 5],
            "price": 9 + ((variation_index * 17) % 91),
            "price1": 99 + ((variation_index * 37) % 401),
            "price2": 599 + ((variation_index * 61) % 1401),
            "product1": "入门款",
            "product2": "旗舰款",
            "expensive": "大牌",
            "food": "食材",
            "ingredient": "意外食材",
            "dish": "菜",
            "meal": "一餐",
            "cloth": "衣服",
            "groupA": "普通人",
            "groupB": "博主",
            "style": "风格",
            "bad_look": "土气",
            "good_look": "高级",
            "bad": "胖/矮",
            "time_learn": "一年",
            "product_tech": "手机",
            "percent": 90,
            "device": "手机",
            "character": "主角",
            "twist": "真相",
            "behavior": "表面现象",
            "truth": "另有隐情",
            "scenario": "这种情况",
            "choice": "怎么选",
            "phenomenon": "现象",
            "field": "领域",
            "common": "常识",
            "common_belief": "常识",
            "bad_thing": "错误做法",
            "place": "目的地",
            "city": "城市",
            "budget": 500 + ((variation_index * 257) % 2501),
            "big_budget": f"{2 + (variation_index % 9)}倍",
            "space": "房间",
            "n_days": 3,
            "n_spots": 5,
        }
        # Placeholder defaults are category-aware so a 3C recommendation does
        # not accidentally talk about skincare, and the other categories stay
        # equally coherent when the same template is reused.
        category_context = {
            "美妆": {
                "method": "三明治底妆", "effect": "毛孔和持妆", "group": "新手",
                "technique": "底妆技巧", "product": "粉底液", "problem": "斑驳脱妆",
                "look": "通勤", "expensive": "大牌粉底", "field": "护肤",
            },
            "美食": {
                "food": "鸡蛋", "meal": "一人食", "ingredient": "空气炸锅",
                "dish": "家常菜", "problem": "不入味", "field": "饮食",
            },
            "时尚": {
                "cloth": "西装外套", "groupA": "小个子", "groupB": "高个子",
                "style": "法式", "bad": "显臃肿", "bad_look": "普通", "good_look": "高级",
            },
            "3C": {
                "product": "手机", "device": "电脑", "problem": "发烫/卡顿",
                "product1": "入门款手机", "product2": "旗舰款手机", "field": "数码",
                "common_belief": "参数越高就一定越好",
            },
            "剧情": {
                "character": "女主", "twist": "他才是幕后真凶", "behavior": "看似冷漠",
                "truth": "其实一直在保护你", "scenario": "朋友隐瞒了一个秘密", "choice": "原谅他",
            },
            "知识": {
                "phenomenon": "人为什么会越忙越拖延", "field": "心理学",
                "common_belief": "熬夜只要补觉就能恢复", "common": "努力就一定有效",
            },
            "生活": {
                "problem": "小户型收纳", "effect": "空间立刻变大", "space": "出租屋",
                "field": "居家",
            },
            "旅游": {
                "place": "云南", "city": "成都", "field": "旅行",
            },
        }
        context.update(category_context.get(category, {}))
        context["topic"] = self._get_random_keyword(category, variation_index, keywords)

        class _MissingPlaceholder(dict):
            def __missing__(self, key: str) -> str:
                logger.warning("unknown_topic_template_placeholder placeholder=%s", key)
                return f"{key}"

        hook = template["template"].format_map(_MissingPlaceholder(context))
        # Keep the visible title useful while guaranteeing uniqueness when a
        # small template catalog is reused for larger ``count`` values.
        title = f"【{self._get_hook_label(hook_type)}】{hook[:24]}·角度{variation_index}"

        return TopicCard(
            title=title,
            hook_suggestion=hook,
            content_direction=f"{self._get_category_content(category)}方向，使用{template['visual']}形式呈现。",
            target_platform=self._get_platforms(platform),
            target_duration=f"{random.randint(15, 60)}秒",
            key_selling_points=[
                f"{self._get_hook_label(hook_type)}开头",
                "结构清晰，完播率高",
                "适合新手创作者",
            ],
            risk_factors=["需要找到差异化角度"],
            script_outline=f"开头({hook})→ {self._get_category_content(category)}内容展开→ 引导互动",
            visual_concept=template["visual"],
            tags=[category, hook_type, "创作灵感"] + keywords[:3],
        )

    async def _generate_ai_topics(
        self, request: TopicRecommendRequest, trends: list, patterns: list
    ) -> list[TopicCard]:
        """Generate additional topics using LLM for higher creativity."""
        try:
            trend_text = (
                "\n".join(f"- {t.title} (增长{t.hot_value_growth:.0%})" for t in trends[:5])
                if trends
                else "暂无实时热点"
            )
            pattern_text = (
                "\n".join(f"- {p.name}: {p.description}" for p in patterns[:3]) if patterns else "暂无爆款公式"
            )
            keywords_text = ", ".join(request.keywords) if request.keywords else "无"

            _prompt = f"""你是一位短视频创意总监，擅长为创作者挖掘爆款选题。请基于以下信息生成{max(3, request.count // 3)}个创意选题卡片。

分类：{request.category or "综合"}
关键词：{keywords_text}
当前热点：
{trend_text}
爆款公式：
{pattern_text}

每个选题输出JSON：
{{"title":"选题标题(吸引眼球)","hook_suggestion":"开头钩子文案","content_direction":"内容方向描述(100字内)","script_outline":"脚本大纲(开头→内容→结尾)","visual_concept":"视觉概念","key_selling_points":["爆点1","爆点2"],"estimated_viral_potential":85,"tags":["标签1","标签2"]}}

返回JSON数组，不要其他文字。"""

            # response = await self.llm_gateway.agenerate(prompt)
            # parsed = json.loads(response)
            # return [TopicCard(**item) for item in parsed]
            logger.info("AI topic generation called (LLM integration pending)")
            return []
        except Exception as e:
            logger.error(f"AI topic generation failed: {e}")
            return []

    def _score_topic(self, card: TopicCard, trends: list, patterns: list) -> float:
        """Score topic card viral potential 0-100."""
        score = 50.0  # base
        # Trend-backed topics score higher
        if card.supporting_trends:
            score += min(25, len(card.supporting_trends) * 10)
        # Pattern-backed topics score higher
        if card.reference_patterns:
            score += min(15, len(card.reference_patterns) * 8)
        # More selling points = better
        score += min(10, len(card.key_selling_points) * 2)
        # Risk factors reduce score
        score -= min(10, len(card.risk_factors) * 3)
        return round(min(100, max(0, score)), 1)

    async def _generate_summary(self, trends: list, category: str) -> str:
        if trends:
            top = trends[:3]
            return f"当前{category or '全平台'}热点上升趋势明显，建议优先关注：{', '.join(t.title for t in top)}。结合爆款公式快速产出内容，抢占流量窗口。"
        return f"建议围绕{category or '通用'}领域的经典痛点+新角度切入，配合高完播率开头公式提升表现。"

    def _get_platforms(self, platform: str | None) -> list[str]:
        if platform:
            return [platform]
        return ["douyin", "xiaohongshu"]

    def _get_hook_label(self, hook_type: str) -> str:
        labels = {
            "question": "提问式",
            "shock": "震惊式",
            "curiosity": "好奇式",
            "number": "数字式",
            "contrast": "对比式",
            "pain_point": "痛点式",
            "demo": "演示式",
            "story": "故事式",
        }
        return labels.get(hook_type, "创意")

    def _get_category_content(self, category: str) -> str:
        contents = {
            "美妆": "妆教/产品测评/护肤分享",
            "美食": "教程/探店/开箱试吃",
            "时尚": "穿搭/单品推荐/风格解析",
            "3C": "数码测评/技巧分享/产品对比",
            "剧情": "情感故事/反转/共鸣场景",
            "知识": "科普/冷知识/干货分享",
            "生活": "好物/技巧/日常Vlog",
            "旅游": "攻略/景点/旅行Vlog",
        }
        return contents.get(category, "干货/分享/教程")

    def _llm_is_available(self) -> bool:
        """Return true only when the injected gateway has usable credentials.

        Test doubles and custom gateways without an ``is_configured``
        attribute are treated as available for backwards compatibility.
        """
        if not self.llm_gateway:
            return False
        configured = getattr(self.llm_gateway, "is_configured", None)
        return True if configured is None else bool(configured)

    def _get_random_keyword(
        self, category: str, variation_index: int = 0, user_keywords: list[str] | None = None
    ) -> str:
        keywords = {
            "美妆": ["底妆", "口红", "眼影", "护肤", "防晒", "卸妆"],
            "美食": ["早餐", "便当", "甜品", "火锅", "烧烤", "面食"],
            "时尚": ["外套", "配饰", "鞋", "包", "穿搭公式"],
            "3C": ["手机", "电脑", "耳机", "APP", "摄影"],
            "剧情": ["恋爱", "职场", "友情", "家庭", "逆袭"],
            "知识": ["心理", "历史", "科学", "经济", "健康"],
            "生活": ["收纳", "清洁", "做饭", "运动", "早起"],
            "旅游": ["海岛", "古城", "美食之旅", "小众目的地"],
        }
        if user_keywords:
            return user_keywords[variation_index % len(user_keywords)]
        cats = keywords.get(category, ["好物", "技巧", "分享", "干货"])
        return cats[variation_index % len(cats)]

    def _get_general_templates(self) -> list[dict]:
        return [
            {"hook_type": "curiosity", "template": "{topic}的秘密，{group}都在偷偷用", "visual": "开头悬念+逐步揭秘"},
            {"hook_type": "number", "template": "{number}个{topic}技巧，第{n}个太绝了", "visual": "快切展示+文字标注"},
            {"hook_type": "shock", "template": "你以为{common}？真相是{truth}", "visual": "反差画面+证据展示"},
            {
                "hook_type": "pain_point",
                "template": "{problem}怎么办？{method}一步解决",
                "visual": "问题+解决方案+效果",
            },
            {
                "hook_type": "question",
                "template": "为什么{group}都在{behavior}？原因找到了",
                "visual": "场景还原+分析讲解",
            },
        ]
