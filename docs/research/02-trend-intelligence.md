# 02 热点情报中心 — GitHub调研与技术选型报告

> 调研日期：2026-09-08
> 调研目标：为短视频AIGC平台的热点情报中心模块选型开源组件

---

## 1. 短视频平台爬虫

### 1.1 候选项目评估

| 项目 | Stars(约) | 支持平台 | 语言 | 活跃度 | 评估结论 |
|------|----------|---------|------|--------|---------|
| **NanmiCoder/MediaCrawler** | ⭐50k+ | 小红书/抖音/快手/B站/微博/百度 | Python | 极高，持续更新 | **首选**：多平台统一接口、Cookie池/代理/登录态管理完善、数据结构标准 |
| JoeanAmier/TikTokDownloader | ⭐12k+ | 抖音/TikTok | Python | 高 | 抖音专用，功能细但单一平台 |
| SocialSisterYi/bilibili-API-collect | ⭐14k+ | B站 | 文档/API | 高 | B站API参考手册，非爬虫框架 |
| Evil0ctal/Douyin_TikTok_Download_API | ⭐8k+ | 抖音/TikTok | Python/FastAPI | 中 | 提供API服务形式，但解析接口容易失效 |

### 1.2 决策

**采用 MediaCrawler 作为核心爬虫引擎**，理由：
- 统一支持5+平台（抖音、快手、小红书、B站、微博），与我们需求完全匹配
- 内置Cookie池、代理轮换、Slider验证码处理、数据持久化
- 代码结构清晰（base_crawler → platform_crawler），可独立作为服务调用
- 活跃维护，社区大，遇到问题有解决方案

**集成方式**：作为git submodule引入 `services/agent/third_party/MediaCrawler/`，通过Python `import` 直接调用其核心爬取函数，外层封装我们自己的 `crawlers/` 适配层（统一数据格式、定时调度、去重、入库）。热点榜单爬取部分（热榜API通常无需登录）我们自行实现轻量版本，因为热榜页面结构相对简单且变化少。

---

## 2. 视频场景分割（Shot Detection）

### 2.1 候选项目评估

| 项目/方案 | 类型 | 精度 | 速度 | 依赖 | 评估 |
|-----------|------|------|------|------|------|
| **PySceneDetect** | 阈值/内容检测（传统CV） | 中等 | 极快（CPU实时） | OpenCV, FFmpeg | **基础方案**：轻量、无需GPU、安装简单、适合快速分割 |
| **TransNetV2** | 深度学习（CNN+Transformer） | 极高（F1≈0.95） | 快（GPU实时/CPU较慢） | TensorFlow/PyTorch | **高精度方案**：电影级镜头检测，适合需要精确分镜的场景 |
| scenedetect + PySceneDetect CLI | 命令行工具 | 中等 | 快 | FFmpeg | 适合批处理脚本 |

### 2.2 决策

**双模式支持**：
- 默认模式：PySceneDetect（content detector, threshold=27-30），快速完成镜头分割
- 高精度模式：TransNetV2（需PyTorch），在需要精确分析（爆款拆解）时切换
- 实现统一接口 `SceneDetector.detect(video_path, mode='fast'|'accurate') → List[Shot]`

---

## 3. 视频ASR（语音转文字）

### 3.1 候选项目评估

| 项目 | 语言支持 | 中文精度 | 时间戳 | 模型大小 | 部署 |
|------|---------|---------|--------|---------|------|
| **FunASR (paraformer-zh)** | 中文为主 | SOTA（>95%） | ✅ 字级 | ~200MB | 本地/服务端 |
| **Whisper-large-v3** | 99种语言 | 中文优秀（~92%） | ✅ (需whisper-timestamped) | ~3GB | 本地/服务端 |
| faster-whisper | 同Whisper | 同Whisper | ✅ | ~3GB(量化后更小) | CTranslate2加速 |
| linto-ai/whisper-timestamped | Whisper增强 | 同Whisper | ✅ 字级（更精确） | ~3GB | 本地 |

### 3.2 决策

**双引擎策略**：
- 中文音频：FunASR paraformer-zh + punc_ct（标点恢复）+ spk（说话人分离可选），字级时间戳
- 其他语言/中英混合：faster-whisper large-v3（CTranslate2加速，4-bit量化，CPU可用）
- 统一接口 `ASREngine.transcribe(audio_path, language='auto') → List[Word]` (含start/end time)

---

## 4. 音频节拍/情绪分析

### 4.1 方案评估

| 工具 | 功能 | 成熟度 |
|------|------|--------|
| **librosa** | BPM检测、onset强度、频谱特征、MFCC | 行业标准，文档丰富 |
| pyAudioAnalysis | 音频分类、情绪识别、 segmentation | 学术项目，功能全但维护一般 |
| essentia | 高级音频分析（键/BPM/风格） | 功能强大但C++依赖重 |

### 4.2 决策

- **BPM检测**：librosa `beat.beat_track()` + `onset.onset_strength()`
- **节奏曲线**：librosa onset_envelope 作为视频节奏特征，用于可视化节奏峰
- **情绪初版映射**：BPM区间映射（<80舒缓/80-120平稳/120-160活跃/>160紧张）+ 频谱质心加权
- **后续升级**：可接入音频情绪分类模型（如基于Wav2Vec2的emotion recognition）

---

## 5. 异步任务队列

### 5.1 候选项目评估

| 项目 | 语言 | 复杂度 | Redis依赖 | Async支持 | 适合场景 |
|------|------|--------|----------|----------|---------|
| **arq** | Python | 极简 | ✅ | ✅ 原生asyncio | FastAPI生态最佳搭档，轻量 |
| Celery | Python | 重 | ✅/RabbitMQ | ❌ 需eventlet | 成熟但配置复杂，对asyncio不友好 |
| RQ | Python | 简单 | ✅ | ❌ | 极简但功能少 |
| asynq | Go | 中等 | ✅ | ✅ | Go生态，若worker在Go端可用 |

### 5.2 决策

**选用 arq**：
- Python Agent服务原生asyncio，arq与FastAPI/Httpx/LangGraph的async模型完美契合
- 配置极简：一个 `WorkerSettings` 类即可启动worker
- 支持任务取消、重试、超时、任务结果持久化
- 视频分析任务（下载→转码→ASR→场景检测→LLM分析）天然适合async pipeline
- 启动方式：`arq services.agent.src.worker.WorkerSettings`

---

## 6. 代理池

### 6.1 候选项目评估

| 项目 | Stars | 功能 | 集成难度 |
|------|-------|------|---------|
| jhao104/proxy_pool | ⭐20k+ | 免费代理爬取+验证+API | 低（REST API） |
| hermanschaaf/proxy-pool | ⭐1k+ | 简单代理池 | 低 |
| 手动配置代理列表 | - | 企业级付费代理 | 极低 |

### 6.2 决策

- **设计可插拔代理提供器接口** `ProxyProvider.get_proxy(platform) → ProxyConfig`
- 默认实现：`StaticProxyProvider`（从环境变量/配置文件读取代理列表，轮换使用）
- 可选集成：`ProxyPoolProvider`（对接jhao104/proxy_pool的REST API）
- 生产建议：使用企业级付费代理（如快代理、芝麻代理），通过 `StaticProxyProvider` 配置

---

## 7. OCR（视频文字识别）

### 7.1 方案

- **首选**：PaddleOCR（中文识别精度高、支持竖排文字、轻量模型可选）
- 备用：EasyOCR（多语言、安装简单）
- 用途：识别视频中的字幕、弹幕、标题文字，辅助理解视频内容

---

## 8. 关键帧提取

- 使用 FFmpeg 基于场景检测结果提取关键帧（每个shot取中间帧或I帧）
- 辅助用 OpenCV 做帧质量筛选（模糊检测、暗帧过滤）
- 关键帧用于：多模态LLM视觉分析、缩略图生成、镜头时间线展示

---

## 技术栈总结

| 模块 | 选型 | 版本要求 |
|------|------|---------|
| 爬虫框架 | MediaCrawler (submodule) + 自研热榜爬虫 | latest |
| 视频下载 | yt-dlp | >=2024.01.01 |
| 视频处理 | FFmpeg | >=6.0 |
| 场景检测-快速 | PySceneDetect | >=0.6.0,<0.7.0 |
| 场景检测-精确 | TransNetV2 (PyTorch) | >=1.0 |
| ASR-中文 | FunASR (paraformer-zh) | >=1.0 |
| ASR-多语言 | faster-whisper (large-v3) | >=1.0 |
| 音频分析 | librosa | >=0.10.0 |
| OCR | PaddleOCR (paddlepaddle) | >=2.7 |
| 任务队列 | arq | >=0.9.0 |
| HTTP客户端 | httpx | >=0.27 |
| 调度器 | APScheduler | >=3.10 |
| 多模态LLM | 通过litellm调用(GPT-4o/Claude3.5/Qwen2.5-VL) | - |
| 向量嵌入 | text-embedding-3-small / BGE-M3 | - |
