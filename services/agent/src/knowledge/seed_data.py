"""Seed demo data: characters, styles, scenes, props, and model configurations."""

from __future__ import annotations

DEMO_CHARACTERS = [
    {
        "name": "专业美妆博主",
        "type": "influencer",
        "description": "25岁左右女性，专业美妆测评风格，语气亲切有说服力",
        "appearance": "精致妆容，时尚穿搭，工作室背景",
        "voice_tone": "亲切专业，有说服力，带点闺蜜推荐感",
        "tags": ["美妆", "带货", "测评", "女性向"],
    },
    {
        "name": "数码测评达人",
        "type": "reviewer",
        "description": "28岁左右男性，科技感十足，客观理性测评数码产品",
        "appearance": "休闲穿搭，简约工作室背景，产品特写",
        "voice_tone": "客观理性，数据说话，通俗易懂",
        "tags": ["数码", "3C", "测评", "科技"],
    },
    {
        "name": "美食探店博主",
        "type": "foodie",
        "description": "24岁左右，活泼开朗，真实反应美食体验",
        "appearance": "休闲日常，餐厅/厨房背景",
        "voice_tone": "活泼有感染力，真实评价，充满食欲感",
        "tags": ["美食", "探店", "吃播", "生活"],
    },
    {
        "name": "知识分享讲师",
        "type": "educator",
        "description": "30岁左右专业人士，清晰有条理分享知识干货",
        "appearance": "商务休闲，书房/办公室背景，专业灯光",
        "voice_tone": "清晰有条理，深入浅出，专业可信",
        "tags": ["知识", "教育", "职场", "干货"],
    },
]

DEMO_STYLES = [
    {
        "name": "电影感",
        "category": "visual",
        "description": "宽画幅，电影级调色，浅景深，氛围感强",
        "keywords": ["cinematic", "2.39:1", "shallow depth of field", "film grain"],
    },
    {
        "name": "日系清新",
        "category": "visual",
        "description": "明亮柔和，低饱和，自然光，生活感",
        "keywords": ["japanese style", "soft light", "low saturation", "natural"],
    },
    {
        "name": "赛博朋克",
        "category": "visual",
        "description": "霓虹灯光，高对比，蓝紫色调，未来感",
        "keywords": ["cyberpunk", "neon", "high contrast", "futuristic"],
    },
    {
        "name": "国风复古",
        "category": "visual",
        "description": "中国风元素，暖色调，古典质感",
        "keywords": ["chinese style", "vintage", "warm tone", "traditional"],
    },
    {
        "name": "极简高级",
        "category": "visual",
        "description": "大面积留白，低饱和，干净简洁，高级感",
        "keywords": ["minimalist", "clean", "monochrome", "luxury"],
    },
]

DEMO_SCENES = [
    {"name": "现代工作室", "category": "indoor", "description": "简约现代办公/直播工作室，自然光"},
    {"name": "居家客厅", "category": "indoor", "description": "温馨家庭客厅，沙发，暖光"},
    {"name": "咖啡馆", "category": "indoor", "description": "文艺咖啡馆，窗边座位，咖啡香气"},
    {"name": "城市街头", "category": "outdoor", "description": "繁华都市街道，人流，霓虹灯"},
    {"name": "自然风景", "category": "outdoor", "description": "山川湖海，自然风光，日出日落"},
]

DEMO_PROPS = [
    {"name": "手机", "category": "tech"},
    {"name": "笔记本电脑", "category": "tech"},
    {"name": "化妆品套装", "category": "beauty"},
    {"name": "咖啡杯", "category": "daily"},
    {"name": "书籍", "category": "daily"},
]

DEMO_MODELS = [
    {"key": "sdxl", "name": "Stable Diffusion XL", "type": "image", "resolution": "1024x1024"},
    {"key": "midjourney", "name": "Midjourney v6", "type": "image", "resolution": "1024x1024"},
    {"key": "dalle3", "name": "DALL-E 3", "type": "image", "resolution": "1024x1024, 1792x1024"},
    {"key": "wanx", "name": "通义万相", "type": "image", "resolution": "1024x1024"},
    {"key": "sora", "name": "OpenAI Sora", "type": "video", "duration": "10s-60s"},
    {"key": "runway", "name": "Runway Gen-3", "type": "video", "duration": "5s-10s"},
    {"key": "pika", "name": "Pika 3.0", "type": "video", "duration": "3s-10s"},
    {"key": "kling", "name": "可灵AI", "type": "video", "duration": "5s-120s"},
    {"key": "jimeng", "name": "即梦AI", "type": "video", "duration": "3s-60s"},
    {"key": "vidu", "name": "Vidu", "type": "video", "duration": "4s-16s"},
    {"key": "cogvideox", "name": "CogVideoX", "type": "video", "duration": "6s"},
    {"key": "hailuo", "name": "海螺AI", "type": "video", "duration": "5s-10s"},
]


def get_seed_data() -> dict:
    return {
        "characters": DEMO_CHARACTERS,
        "styles": DEMO_STYLES,
        "scenes": DEMO_SCENES,
        "props": DEMO_PROPS,
        "models": DEMO_MODELS,
    }
