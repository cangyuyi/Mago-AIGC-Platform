# Mago Agent Platform - Dependencies

## 03-ScriptStudio 新增依赖

### Python (services/agent)
| Package | Version | Purpose |
|---------|---------|---------|
| (无新外部依赖) | - | 全部基于已有LangGraph/LiteLLM/Pydantic实现 |

### 知识库数据（services/agent/src/knowledge/data/）
| 文件 | 条目数 | 内容 |
|------|--------|------|
| hooks.json | 100种 | 钩子套路（10大类×10种） |
| story_structures.json | 32种 | 叙事结构模板 |
| ctas.json | 20种 | CTA行动号召策略 |
| emotion_curves.json | 15种 | 情绪曲线模板（含坐标点） |
| vertical_specs.json | 20个 | 垂类内容规范 |
| rhythm_patterns.json | 11种 | 节奏/镜头时长模式 |

### Frontend (apps/web)
| Package | Purpose |
|---------|---------|
| (无新外部依赖) | 使用已有React/Tailwind/Lucide，分镜使用原生HTML5 drag-and-drop |

---

## 02-TrendIntelligence 新增依赖

### Python (services/agent)
| Package | Purpose |
|---------|---------|
| yt-dlp | 视频下载（支持1000+平台） |
| opencv-python-headless | 视频帧提取、图像处理 |
| scenedetect>=0.6.0,<0.7.0 | 视频场景/镜头分割（配合 opencv-python-headless） |
| librosa | 音频BPM、节拍分析 |
| soundfile | 音频文件读写 |
| arq | 异步任务队列（Redis+asyncio） |
| apscheduler | 定时爬虫调度 |
| beautifulsoup4 | HTML解析 |
| lxml | HTML/XML解析器 |
| Pillow | 图像处理 |

### Python 可选依赖（生产环境）
| Package | Purpose |
|---------|---------|
| faster-whisper | 多语言ASR（large-v3） |
| FunASR | 中文ASR（paraformer-zh） |
| PaddleOCR | 视频画面文字识别 |
| torch | TransNetV2精确镜头分割 |
| paddlepaddle | PaddleOCR运行时 |

### Frontend
| Package | Purpose |
|---------|---------|
| recharts | 趋势图、节奏曲线可视化 |

### 系统依赖
| Tool | Purpose |
|------|---------|
| FFmpeg >=6.0 | 视频/音频转码、关键帧提取 |
| Redis >=7.0 | arq任务队列、缓存 |
| PostgreSQL >=15 | 数据存储 |
| pg_dump / psql | PostgreSQL 备份与恢复脚本 |
| aws CLI（可选） | 将备份上传到 S3/MinIO |

---

## 01-ProjectBootstrap 原有依赖

### Backend
- Go 1.22+ / Python 3.11+ / Node.js 20+ / pnpm 9+

### Go Packages
- gin-gonic/gin (HTTP框架)
- gorm.io/gorm + gorm.io/driver/postgres (ORM)
- golang-jwt/jwt/v5 (JWT认证)
- go.uber.org/zap (结构化日志)
- google/uuid (UUID生成)

### Python Packages
- fastapi + uvicorn (API服务)
- langgraph + langchain-core (Agent编排)
- litellm (多LLM统一接口)
- httpx (异步HTTP)
- sqlalchemy + psycopg2-binary (数据库)
- redis (Redis客户端)
- numpy (数值计算)
- structlog (结构化日志)
- pydantic + pydantic-settings (数据验证/配置)

### Frontend Packages
- next.js 14 (App Router)
- react 18 + react-dom
- tailwindcss
- lucide-react (图标)
- class-variance-authority + tailwind-merge
- react-hook-form + zod
- framer-motion (动效)
- @xyflow/react (React Flow流程图)
- zustand + @tanstack/react-query (状态管理)
- react-markdown + remark-gfm + rehype-highlight (Markdown渲染)
- next-themes (主题切换)
