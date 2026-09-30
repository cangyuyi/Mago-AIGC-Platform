# 指令 02：热点情报中心（Trend Intelligence）

## 角色设定

你是一名**数据工程师+爬虫工程师+多模态算法工程师**，擅长构建大规模数据采集、清洗、分析流水线，以及视频内容的AI多模态理解系统。你熟悉Python爬虫生态、FFmpeg视频处理、多模态LLM应用。

## 前置依赖

必须先完成 `01-project-bootstrap.md` 的所有内容，项目骨架、数据库、Agent框架、前端项目已经搭建完成。

## 任务目标

实现**热点情报中心**模块，包含：
1. 多平台热点话题实时爬取系统
2. 爆款视频内容AI多模态拆解引擎（输入视频URL → 输出结构化拆解报告）
3. 热点趋势分析与选题推荐Agent
4. 前端热点看板、爆款详情页、选题推荐UI

## 产品边界

✅ **做**：爬取公开热点数据、下载公开视频、调用多模态LLM分析视频、存储分析结果、提供检索和推荐API、前端展示  
❌ **不做**：破解付费内容、绕过平台反爬做违法操作、视频剪辑/转码发布（只做分析）

## 数据合规要求

- 严格遵守各平台robots.txt和服务条款
- 爬取频率受限，加入随机延迟和UA轮换
- 所有下载视频仅用于分析处理，分析完成后原视频文件可删除（仅保留结构化分析结果和关键帧缩略图）
- 提供robots.txt检查机制和爬取频率配置开关
- 用户主动提交URL进行分析的场景下，由用户承担版权责任，平台仅提供分析工具

## 执行步骤

### Step 1：调研GitHub开源方案（必须）

在写代码之前，**必须**搜索并评估以下类别的开源项目，在 `docs/research/02-trend-intelligence.md` 中记录结论：

1. **短视频平台爬虫**：
   - 搜索关键词：`douyin crawler github python`, `tiktok scraper open source`, `bilibili crawler python`, `xiaohongshu crawler 2024`
   - 候选参考：
     - `NanmiCoder/MediaCrawler`（⭐小红书/抖音/快手/B站/微博多平台爬虫，star必看，评估是否直接复用）
     - `JoeanAmier/TikTokDownloader`（抖音/TikTok下载）
     - `SocialSisterYi/bilibili-API-collect`（B站API合集）
     - `Evil0ctal/Douyin_TikTok_Download_API`（抖音TikTok解析API）
   - 决策：如果MediaCrawler满足需求，直接作为git submodule或独立服务集成；不满足则借鉴其接口设计自行实现核心爬取逻辑

2. **视频场景分割**：
   - 搜索关键词：`video scene detection python`, `TransNetV2 shot detection`, `PySceneDetect tutorial`
   - 候选参考：`Breakthrough/PySceneDetect`, `soCzech/TransNetV2`（基于深度学习的镜头边界检测，精度高）
   - 决策：必须支持两种模式——PySceneDetect（轻量，阈值法）+ TransNetV2（深度模型，高精度），按需要切换

3. **视频ASR（语音转文字）**：
   - 搜索关键词：`chinese speech recognition funasr`, `whisper large v3 chinese`, `offline asr python`
   - 候选参考：`modelscope/FunASR`（阿里开源，中文SOTA）, `openai/whisper`, `linto-ai/whisper-timestamped`（带时间戳）
   - 决策：中文优先用FunASR（paraformer-zh模型），多语言用Whisper-large-v3，必须支持字级时间戳以便对齐镜头

4. **音频节拍/BPM检测**：
   - 搜索关键词：`python audio beat detection librosa`, `bpm detection python`, `music emotion classification`
   - 参考：librosa官方文档, `tyiannak/pyAudioAnalysis`（音频分析库）
   - 决策：用librosa实现BPM和onset检测；情绪分类初版用规则+BPM映射（快BPM=紧张/激动，慢BPM=舒缓），后续可训练模型

5. **异步任务队列**：
   - 搜索关键词：`python async task queue redis`, `celery vs arq vs rq`, `fastapi background task alternative`
   - 候选参考：`celery/celery`（重但成熟）, `samuelcolvin/arq`（轻量，基于asyncio/redis）, `hibiken/asynq`(Go)
   - 决策：视频分析是长任务，必须用独立worker。优先在Python Agent服务内用arq（asyncio+redis，和FastAPI生态最搭），或在Go端用asynq。根据栈选择后实施。

6. **代理池**：
   - 搜索关键词：`python proxy pool open source`, `free proxy pool github`
   - 候选参考：`jhao104/proxy_pool`(经典), `hermanschaaf/proxy-pool`
   - 决策：实现可插拔的代理提供器，默认支持手动配置代理列表，可选集成开源代理池

### Step 2：数据库表设计

在Go服务的migrations中新增以下表（用DDL编写迁移文件）：

```sql
-- 热点话题表
CREATE TABLE trend_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,        -- douyin/kuaishou/xiaohongshu/bilibili/weibo/tiktok/youtube
    topic_id VARCHAR(255),                 -- 平台话题ID（如抖音热榜词ID）
    title VARCHAR(512) NOT NULL,           -- 话题/热词标题
    category VARCHAR(64),                  -- 分类：娱乐/科技/美食/时尚/...
    hot_value BIGINT,                      -- 热度值
    hot_value_growth FLOAT,                -- 热度增长率（用于判断上升期）
    rank_position INT,                     -- 当前排名
    cover_url TEXT,                        -- 封面图URL
    url TEXT,                              -- 话题页URL
    tags TEXT[],                           -- 标签数组
    status VARCHAR(20) DEFAULT 'rising',   -- rising/peak/declining
    lifecycle_stage VARCHAR(20),           -- 上升期/爆发期/衰退期
    related_videos_count INT DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_trend_topics_platform ON trend_topics(platform);
CREATE INDEX idx_trend_topics_status ON trend_topics(status);
CREATE INDEX idx_trend_topics_last_updated ON trend_topics(last_updated_at);
CREATE UNIQUE INDEX idx_trend_unique_platform_topic ON trend_topics(platform, topic_id) WHERE topic_id IS NOT NULL;

-- 爆款视频表
CREATE TABLE viral_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    video_id VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    author_id VARCHAR(255),
    author_name VARCHAR(255),
    author_followers INT,
    title VARCHAR(512),
    description TEXT,
    tags TEXT[],
    category VARCHAR(64),
    duration FLOAT,                         -- 秒
    width INT,
    height INT,
    aspect_ratio VARCHAR(16),               -- "9:16"/"16:9"/"1:1"
    -- 数据指标
    metrics JSONB DEFAULT '{}',             -- {likes, comments, shares, views, collects...}
    completion_rate_est FLOAT,              -- 完播率估算
    trend_score FLOAT,                      -- 综合热度分
    -- 分析状态
    analysis_status VARCHAR(20) DEFAULT 'pending',  -- pending/downloading/analyzing/completed/failed
    analysis_error TEXT,
    video_path TEXT,                         -- 本地存储路径（分析后可删）
    keyframes_dir TEXT,                      -- 关键帧存储目录
    thumbnail_url TEXT,
    bgm_name VARCHAR(255),
    bgm_bpm FLOAT,
    bgm_emotion VARCHAR(64),
    -- 分析结果（JSON）
    analysis JSONB DEFAULT '{}',
    -- embedding用于检索
    clip_embedding vector(512),              -- 用pgvector或Milvus
    text_embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_viral_videos_platform ON viral_videos(platform);
CREATE INDEX idx_viral_videos_category ON viral_videos(category);
CREATE INDEX idx_viral_videos_status ON viral_videos(analysis_status);
CREATE INDEX idx_viral_videos_created ON viral_videos(created_at);
CREATE UNIQUE INDEX idx_viral_unique_platform_vid ON viral_videos(platform, video_id);

-- 视频镜头表（拆解后每个镜头）
CREATE TABLE video_shots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES viral_videos(id) ON DELETE CASCADE,
    shot_index INT NOT NULL,
    start_time FLOAT NOT NULL,              -- 秒
    end_time FLOAT NOT NULL,
    duration FLOAT NOT NULL,
    keyframe_path TEXT,                      -- 关键帧图片路径
    keyframe_url TEXT,
    -- 视觉分析
    shot_type VARCHAR(32),                   -- close-up/medium/wide/extreme-wide
    camera_movement VARCHAR(64),             -- static/push/pull/pan/tilt/tracking/handheld/zoom
    composition VARCHAR(64),                 -- 构图描述
    lighting VARCHAR(64),                    -- 光线描述
    color_tone VARCHAR(64),                  -- 色调
    subject TEXT,                            -- 主体描述
    scene TEXT,                              -- 场景描述
    text_detected TEXT,                      -- OCR文字
    -- 音频
    speech_text TEXT,                        -- 该镜头对应的ASR文本
    speech_start FLOAT,
    speech_end FLOAT,
    emotion VARCHAR(32),                     -- 情绪标签
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_video_shots_video ON video_shots(video_id, shot_index);

-- 爆款公式/模式库
CREATE TABLE viral_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,              -- 如"反常识钩子+痛点放大+解决方案"
    pattern_type VARCHAR(64) NOT NULL,       -- hook/narrative/cta/transition/rhythm
    description TEXT,
    formula_template TEXT,                   -- 可复用模板
    tags TEXT[],
    category VARCHAR(64),
    source_video_ids UUID[],
    success_count INT DEFAULT 0,             -- 被多少视频验证
    avg_metrics JSONB,                       -- 采用该公式的视频平均指标
    example_text TEXT,                       -- 示例文案
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 爬虫任务日志
CREATE TABLE crawl_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(32) NOT NULL,
    task_type VARCHAR(32) NOT NULL,          -- trending/video_detail/video_analysis
    target_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

注意：`vector` 类型需要安装 `pgvector` 扩展（在migration最开头加 `CREATE EXTENSION IF NOT EXISTS vector;`），或者直接用Milvus存embedding，PG里只存外键。根据调研决策，建议用Milvus专门存向量（已在docker-compose中）。

### Step 3：热点爬取服务

在 `services/agent/src/crawlers/` 下实现爬取模块：

```
crawlers/
├── __init__.py
├── base.py                # BaseCrawler抽象基类
├── registry.py            # Crawler注册表
├── config.py              # 爬取配置（间隔/UA/代理）
├── douyin.py              # 抖音热榜
├── kuaishou.py            # 快手热榜
├── xiaohongshu.py         # 小红书热门
├── bilibili.py            # B站热门
├── weibo.py               # 微博热搜
├── tiktok.py              # TikTok Trending（可选）
└── pipeline.py            # 数据清洗/去重/入库Pipeline
```

设计要求：
- `BaseCrawler` 定义统一接口：`async def fetch_trending() -> List[TrendTopic]`
- 每个平台爬虫独立实现，通过registry装饰器注册
- 爬取流程：爬取 → 标准化字段 → 去重（按platform+topic_id或标题语义相似度）→ 计算热度变化 → 判定生命周期阶段（上升/爆发/衰退）→ 入库
- 使用 `httpx.AsyncClient` + 随机UA + 代理轮换 + 指数退避重试
- 爬取频率：核心平台每15分钟，次要每60分钟，通过配置可调
- 用 `APScheduler` 或 `arq cron` 做定时调度
- 新话题首次发现时标记为`rising`，2小时内热度增长>100%标记为爆发预警
- 每个爬取任务记录到crawl_tasks表，方便监控

### Step 4：视频下载服务

在 `services/agent/src/video_tools/` 下实现：

```
video_tools/
├── __init__.py
├── downloader.py          # 视频下载（基于yt-dlp + 平台特定解析）
├── scene_detect.py        # 镜头分割（PySceneDetect + TransNetV2）
├── keyframe_extractor.py  # 关键帧提取
├── asr.py                 # ASR语音转文字（FunASR + Whisper）
├── audio_analysis.py      # BPM/节拍/情绪分析
├── ocr.py                 # 视频帧OCR（可选，用PaddleOCR或easyocr）
└── pipeline.py            # 完整视频分析Pipeline编排
```

要求：
- `downloader.py`：优先用 `yt-dlp` 做视频下载（支持1000+网站），特殊平台（小红书等）用专用解析逻辑；下载到MinIO临时目录
- `scene_detect.py`：
  - ContentDetector（PySceneDetect阈值法）作为快速模式
  - TransNetV2作为精确模式（需要下载模型权重到本地models目录）
  - 输出：每个镜头的start_time, end_time, confidence
- `keyframe_extractor.py`：每个镜头取中间帧作为关键帧，用OpenCV抽取，保存为webp格式（小体积），上传到MinIO
- `asr.py`：
  - FunASR用paraformer-zh模型做中文ASR，输出带时间戳的字幕（SRT格式和JSON格式）
  - Whisper-large-v3做多语言兜底
  - 必须支持word-level timestamp
  - 提供模型首次启动时自动下载权重（到models目录，配置镜像源加速）
- `audio_analysis.py`：用librosa提取BPM、onset_strength（节奏强度曲线）、频谱特征；简单情绪映射规则：BPM>140=紧张/激动，BPM<80=舒缓/伤感，中间=平稳/愉悦
- `ocr.py`（可选）：用PaddleOCR提取关键帧中的文字（如字幕/贴纸/标题），注意安装paddleocr依赖较重，做成可选模块

### Step 5：爆款视频多模态拆解Agent

这是本板块最核心的Agent，实现在 `services/agent/src/agents/trend/viral_analyzer.py`

输入：视频URL或viral_video_id  
输出：结构化的视频拆解报告（存入analysis JSONB字段）

工作流程（LangGraph实现）：

1. **Download节点**：调用下载器下载视频 → 更新状态为downloading
2. **AudioExtract节点**：用FFmpeg抽取音频轨
3. **ASR节点**：调用ASR服务获取完整文字稿+时间戳
4. **SceneDetect节点**：调用镜头分割
5. **KeyframeExtract节点**：抽取关键帧（每个镜头1帧，关键帧太多时按时间均匀采样到不超过30帧，避免token爆炸）
6. **AudioAnalysis节点**：BPM/节拍/情绪
7. **MultimodalAnalyze节点**（核心）：
   - 将关键帧（base64或MinIO临时URL）+ ASR文本 + 基础元数据 发送给多模态LLM（Gemini 2.5 Pro 或 GPT-4o）
   - Prompt要求模型逐镜头分析：景别/运镜/光影/色调/主体/场景/情绪，并整体分析钩子类型、叙事结构、CTA策略、爆款可复用公式
   - Prompt必须有严格的JSON输出schema（用Pydantic定义ViralAnalysisResult，用LLM的structured_output/function_calling保证格式）
   - Prompt要求模型总结该视频的**爆款公式**（如"前3秒提出反常识观点→用3个快速镜头展示痛点→结尾给出解决方案+CTA"）
8. **PatternExtract节点**：将拆解出的爆款公式与已有viral_patterns库做相似度匹配（用text embedding），若发现新模式则入库
9. **Embedding节点**：生成clip_embedding（关键帧CLIP embedding平均池化）和text_embedding（标题+描述+脚本文本embedding），存入Milvus
10. **Cleanup节点**：删除原始视频文件保留关键帧和结构化数据（可配置保留策略）
11. **Persist节点**：所有结果入库，更新analysis_status为completed

关键Prompt框架（写在 `services/agent/src/llm/prompts/viral_analysis.py`）：
```
你是一位专业的短视频内容分析师，擅长拆解爆款视频的底层逻辑。

我会给你一段视频的：
1. 基本信息（标题/描述/标签/时长/平台）
2. 完整的语音文字稿（带时间戳）
3. 按镜头切分的关键帧图片（共N张，按时间顺序排列）

请按以下JSON schema输出分析结果（必须严格符合，不要输出多余内容）：
{
  "hook_analysis": {
    "hook_text": "前3秒的具体文字/画面内容",
    "hook_type": "悬念式/冲突式/反常识式/痛点式/数字式/提问式/对比式/视觉冲击式/情感共鸣式",
    "hook_mechanism": "为什么这个钩子能吸引注意力（心理学/认知机制）",
    "hook_strength_score": 1-10
  },
  "narrative_structure": {
    "structure_type": "总分总/问题-方案/对比反转/时间线/清单并列/故事线",
    "acts": [
      {"act_name": "开场/钩子", "time_range": "0-3s", "purpose": "...", "content_summary": "...", "emotion": "..."},
      {"act_name": "主体", "time_range": "3-25s", ...},
      {"act_name": "结尾/CTA", "time_range": "25-30s", ...}
    ],
    "emotion_curve": ["好奇", "紧张", "惊喜", "满足"],
    "information_density": "high/medium/low",
    "pacing_assessment": "节奏评价"
  },
  "visual_language": {
    "dominant_shot_types": ["close-up", "medium"],
    "dominant_camera_movements": ["static", "quick-cut"],
    "color_grading": "色调描述，如暖黄复古/冷蓝赛博朋克/明亮清新",
    "lighting_style": "光线风格，如自然光/伦勃朗光/霓虹光",
    "composition_style": "构图风格",
    "editing_rhythm": "剪辑节奏描述（快切/长镜头/混合），平均镜头时长",
    "transition_types": ["硬切","跳切","转场特效"],
    "visual_consistency_score": 1-10
  },
  "audio_analysis": {
    "speech_style": "口播风格（激情/亲切/严肃/幽默）",
    "voice_tone": "音色描述",
    "speech_pace": "语速（字/分钟估算）",
    "bgm_role": "BGM作用（烘托/节奏/情绪/记忆点）",
    "sound_effects_used": ["类型1","类型2"],
    "audio_visual_sync_score": 1-10
  },
  "content_elements": {
    "key_messages": ["核心信息点1","核心信息点2"],
    "selling_points"：["卖点1"]（若是带货视频）,
    "pain_points_addressed": ["痛点1"],
    "cta_type": "关注/点赞/购买/评论/收藏/转发/无明确CTA",
    "cta_text": "具体CTA文字",
    "cta_position": "结尾/开头/贯穿"
  },
  "viral_formula": {
    "formula_name": "给这个爆款模式起一个简洁的名字",
    "formula_description": "详细描述可复用的公式/模板",
    "reusable_template": "可以直接套用的模板（括号中是需要填充的变量）",
    "applicable_scenarios": ["适合的垂类/场景"],
    "key_success_factors": ["成功的关键因素"]
  },
  "tags": ["标签1","标签2"],
  "target_audience": "目标受众描述",
  "overall_viral_score": 1-10,
  "strengths": ["优点1","优点2"],
  "weaknesses": ["可改进点1"],
  "replicable_score": 1-10  // AI生成内容可复刻的程度（需要大量真人出镜/特殊场景=低分）
}
```

### Step 6：热点趋势分析服务

在 `services/agent/src/agents/trend/` 下新增：
- `trend_analyzer.py`：定时分析热点数据，计算：
  - 话题热度生命周期：基于历史热度数据（time series）用简单规则判定阶段（连续N次爬取热度增长>阈值=rising，峰值=peak，下降=declining）
  - 上升期话题自动标记并推送到前端通知（WebSocket）
  - 话题分类聚类：用embedding对热点标题做聚类（sklearn KMeans或DBSCAN），自动归到预定义的20个垂类
- `topic_recommender.py`：选题推荐Agent
  - 输入：用户指定的赛道/垂类/关键词/账号风格描述/参考视频
  - 逻辑：
    1. 检索当前上升期热点（status=rising，匹配用户垂类）
    2. 检索爆款库中相似赛道的高viral_score视频（向量相似度检索）
    3. 用LLM综合热点+爆款模式+用户需求，生成10-20个选题卡片
    4. 每个选题卡片包含：选题名、一句话钩子、核心卖点、目标受众、建议时长、建议形式、参考爆款链接、热度预估、AI生成可行性评分
  - 输出：`List[TopicCard]`（Pydantic模型）

### Step 7：RESTful API实现

在Go后端新增handler/service/repository（或Python Agent服务直接暴露，推荐Go做聚合），实现：

| 方法 | 路径 | 功能 |
|:---|:---|:---|
| GET | `/api/v1/trends` | 热点话题列表（分页、按平台/分类/状态筛选、排序） |
| GET | `/api/v1/trends/:id` | 热点话题详情（含关联视频列表） |
| POST | `/api/v1/trends/crawl-now` | 触发立即爬取（管理员） |
| GET | `/api/v1/viral-videos` | 爆款视频列表（分页、按平台/垂类/评分/公式类型筛选） |
| GET | `/api/v1/viral-videos/:id` | 爆款视频详情（含完整拆解报告） |
| POST | `/api/v1/viral-videos/analyze` | 提交视频URL进行分析（异步，返回task_id） |
| GET | `/api/v1/viral-videos/analyze/:task_id` | 查询分析任务状态和结果 |
| GET | `/api/v1/viral-patterns` | 爆款公式库列表 |
| GET | `/api/v1/viral-patterns/:id` | 公式详情 |
| POST | `/api/v1/topic-recommendations` | 选题推荐（参数：垂类/关键词/参考视频URL/数量） |
| GET | `/api/v1/viral-videos/search` | 爆款搜索（关键词+语义向量混合检索） |

API要求：
- 支持分页：`?page=1&page_size=20`，返回 `{"items":[...], "total": N, "page": 1, "page_size": 20}`
- 异步任务用轮询或WebSocket通知进度
- 所有列表支持按字段排序（`?sort=trend_score&order=desc`）

### Step 8：前端页面实现

在 `apps/web/src/app/` 下新增：

```
app/
├── trends/
│   ├── page.tsx                  # 热点看板首页
│   ├── [platform]/page.tsx       # 按平台筛选
│   └── components/
│       ├── trend-card.tsx        # 热点话题卡片（热度值/趋势箭头/分类标签）
│       ├── trend-list.tsx        # 热点列表（支持切换平台tab/分类筛选）
│       ├── trending-chart.tsx    # 热度趋势折线图（用recharts）
│       └── rising-alert.tsx      # 上升期热点预警横幅
├── viral/
│   ├── page.tsx                  # 爆款库浏览页
│   ├── [id]/page.tsx             # 爆款拆解详情页
│   └── components/
│       ├── viral-card.tsx
│       ├── video-player.tsx      # 视频播放器
│       ├── analysis-report.tsx   # 结构化拆解报告展示
│       ├── shot-timeline.tsx     # 镜头时间线（可点击跳转到对应镜头）
│       ├── rhythm-chart.tsx      # 节奏曲线可视化
│       ├── emotion-curve.tsx     # 情绪曲线可视化
│       ├── formula-card.tsx      # 爆款公式卡片
│       └── analyze-form.tsx      # URL输入表单，提交分析
└── topics/
    └── page.tsx                  # 选题推荐页
        └── components/
            ├── topic-preference-form.tsx  # 偏好设置（垂类/关键词/参考视频）
            ├── topic-card.tsx             # 选题卡片
            └── topic-generate-btn.tsx     # 生成选题按钮
```

UI/UX要求：
- 热点看板：平台tab切换（抖音/快手/小红书/B站/微博/全部），卡片展示热度值+上升/下降箭头，上升期热点用红色🔥标记，支持按分类筛选
- 爆款详情页：左侧视频播放器，右侧结构化分析tab（钩子分析/叙事结构/视觉语言/音频分析/爆款公式），底部镜头时间线（点击镜头显示该镜头关键帧和文字）
- 节奏曲线：用recharts画折线图，x轴时间，y轴onset_strength/镜头切换频率，峰值处标注
- 选题推荐页：用户先选垂类（美妆/美食/3C/剧情/知识/...）+ 输入关键词或粘贴参考视频URL → 点生成 → 返回10-20张选题卡片，每张卡片支持"一键以此创建项目"按钮

### Step 9：集成到Agent编排层

将热点/选题能力集成到LangGraph，作为上游节点：
- 用户输入"帮我找现在最火的美妆选题" → Trend Agent调用热点+推荐 → 输出选题卡片 → 用户选择 → 进入脚本创作环节
- 在 `services/agent/src/core/graph.py` 中新增 `trend_research` 和 `topic_recommend` 节点
- 前端Chat UI中增加快捷按钮："🔥查看今日热点"、"💡给我推荐选题"

## 验收标准

- [ ] docker-compose启动后，爬虫定时任务能正常运行，热点数据能持续入库
- [ ] 至少支持5个平台热点爬取（抖音/快手/小红书/B站/微博）
- [ ] 提交一个公开视频URL（30秒-3分钟），10分钟内产出完整拆解报告（钩子/叙事/镜头/音频/公式）
- [ ] ASR转写准确率中文≥90%（普通话清晰音频）
- [ ] 镜头分割准确率≥85%（与人工标注对比）
- [ ] 爆款公式能自动提取并入库，相似视频能匹配到同一公式
- [ ] 选题推荐Agent能基于热点+爆款库给出10+个可用选题卡片
- [ ] 前端热点看板正常展示，热度趋势图表可交互
- [ ] 爆款详情页能播放视频+查看完整拆解报告+镜头时间线
- [ ] 语义搜索能用自然语言搜到相关爆款视频（如"快切节奏的美妆种草"）
- [ ] 所有API有正确的分页/排序/筛选/错误处理
- [ ] `make lint && make test` 通过
- [ ] `docs/research/02-trend-intelligence.md` 有完整的GitHub调研结论和选型理由
- [ ] `docs/dependencies.md` 已更新本次新增的所有依赖
