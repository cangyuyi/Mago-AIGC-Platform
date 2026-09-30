# 🧙 Mago Agent 创意平台

> 已有Mago生图/生视频聚合平台的**上游AI创意大脑** — 模糊想法输入 → 专业提示词包输出，一键生成爆款视频。
> 长耗时的视频分析和热点抓取由 Redis/ARQ 队列交给独立 `agent-worker` 执行。

---

## ✨ 核心价值

**10分钟，从0想法到可直接生成的专业提示词包：**

1. **热点情报**：自动抓取抖音/小红书/B站/快手热点，发现爆款选题
2. **灵感发散**：AI生成10个差异化创意方向，AI可行性评分
3. **脚本创作**：8个Agent协作（创意总监→钩子专家→编剧→分镜师→评审→合规→节奏优化→裁判），自动生成专业短视频脚本
4. **角色&风格**：自定义角色人设+视觉风格，统一品牌调性
5. **提示词引擎**：自动生成12个主流AIGC模型的专业提示词（Midjourney/SDXL/DALL-E 3/Sora/Runway/Pika/可灵/即梦/Vidu/CogVideoX/海螺/通义万相）
6. **提示词包导出**：每个镜头的正向/负向提示词 + 可直接照抄的参数（宽高比、时长、seed、`--ar`/`--no` 语法），支持按镜头复制或整包导出 Markdown / CSV / JSON / 纯文本，粘贴到对应平台即可生成

---

## 🛠 技术栈

| 层 | 选型 |
|:---|:---|
| **前端** | Next.js 15.5.24 (App Router) + React 18 + TypeScript + TailwindCSS + shadcn/ui + React Flow + framer-motion + TanStack Query |
| **API网关** | Go 1.22 + Gin + GORM + JWT |
| **Agent服务** | Python 3.11 + FastAPI + LangGraph + LiteLLM（支持200+LLM） |
| **数据层** | PostgreSQL 16 + Redis 7 + Milvus向量库 + MinIO对象存储 |
| **可观测** | OpenTelemetry + Langfuse(LLM可观测) + Grafana + Prometheus + Loki + Tempo |
| **容器化** | Docker Compose（开发/小规模生产）；Kubernetes 迁移说明见部署文档 |

---

## 🚀 快速开始

### 前置要求

**只想先看一眼能干什么**：只需要 Node.js 20+ 和 Python（或 [uv](https://docs.astral.sh/uv/)）——见下面「路径 C」。

| 依赖 | 何时必须 | 版本 |
|:---|:---|:---|
| Node.js | 始终（前端） | 20+，自带 Corepack，固定 pnpm 9.15.0 |
| Python / uv | 始终（Agent 服务） | 3.11+；装了 uv 会自动准备解释器 |
| Docker Desktop | 只有要真实数据库/团队账号时 | 4.20+，完整栈请分配 ≥8GB RAM |
| Go | 只有要跑 API 网关时 | 1.22+ |
| FFmpeg | 只有要下载/分析参考视频时 | 任意近期版本 |
| LLM API Key | 可选 | OpenAI / Anthropic / DeepSeek 任一；**没有 Key 时脚本与提示词包仍能出结果**（走内置模板引擎，不消耗额度） |

先体检，缺什么会逐条告诉你怎么补：

```bash
make doctor
```

### 四种启动方式

| 路径 | 命令 | 需要 | 能用到什么程度 |
|:---|:---|:---|:---|
| **A 完整栈（全容器）** | `make docker-up`，入口 http://localhost:8080 | Docker ≥8GB | 全部功能：账号体系、持久化、热点抓取、向量检索、可观测面板 |
| **A2 完整栈（本地热重载）** | `bash scripts/setup.sh` 后 `make dev-web / dev-api / dev-agent` | Docker + Go | 同上，但改代码即时生效；`setup.sh` 会起基础设施、装三端依赖并跑迁移 |
| **B 轻量栈** | `make docker-min` → `docker compose -f docker-compose.min.yml run --rm migrate` → `make dev-api` / `dev-agent` / `dev-web` | Docker（只起 Postgres/Redis/MinIO） | 除热点趋势 RAG 外全部功能，省约 4GB 内存 |
| **C 零依赖演示** | `make demo` | 只有 Node + Python | 脚本 → 分镜 → 提示词包 → 导出全链路；数据存在你自己的浏览器 localStorage |

### 1. 克隆&初始化
```bash
cd /path/to/Mago-AIGC-Platform

# 复制环境变量配置（已存在则不会覆盖）
make setup-env
# 编辑 .env，填入你的 OPENAI_API_KEY（没有 Key 也可以先试内置模板引擎）
```

### 2. 启动基础设施
```bash
# 启动数据库/缓存/对象存储/向量库/可观测栈
docker compose up -d postgres redis minio etcd milvus \
  otel-collector prometheus loki tempo grafana
# Langfuse 不再随 Compose 单容器启动；如需 LLM trace，请使用 Langfuse Cloud
# 或按官方多容器部署单独部署，并在 .env 中设置 LANGFUSE_ENABLED/HOST/KEY。

# 等待服务健康检查通过（约30秒）
docker compose ps
```

### 3. 安装依赖
```bash
# 安装前端依赖
./scripts/pnpm.sh install

# 安装Go依赖
cd services/api-gateway && go mod download && cd ../..

# 安装Python依赖
cd services/agent && uv sync && cd ../..
```

### 4. 启动应用服务
使用一键启动脚本：
```bash
chmod +x 🚀启动Mago.command
./🚀启动Mago.command
```

或分别启动四个终端：
```bash
# 终端1：Python Agent API服务 (端口8000)
cd services/agent && source .venv/bin/activate && uvicorn src.main:app --port 8000 --reload

# 终端2：Agent Worker（执行视频分析/热点抓取长任务）
cd services/agent && source .venv/bin/activate && arq src.worker.WorkerSettings

# 终端3：Go API网关（直连宿主机端口 8080）
cd services/api-gateway && go run ./cmd/server

# 终端4：Next.js前端（端口 3000）
cd apps/web && ../../scripts/pnpm.sh dev
```

### 离线演示模式
如果暂时没有 PostgreSQL/Redis/MinIO 或 LLM Key，可以仅启动前端并在 `apps/web/.env.local` 中设置：

```bash
NEXT_PUBLIC_DEMO_MODE=true
```

演示模式使用浏览器本地数据，覆盖登录、Dashboard、项目、选题、热点、爆款拆解、角色、知识库、提示词和 Agent 流式创作流程；不会伪装真实生产数据。接入完整后端时请改回 `false`，真实 API 错误会直接显示在页面上。

`make demo` 走的是这条路径，但**同时把 Python Agent 也起起来**：脚本、分镜和提示词包由真实的服务端引擎生成（只是不需要数据库和 LLM Key），因此能拿到可以直接复制使用的产出物，而不只是一个界面。数据仍然只保存在浏览器本地。

### 安全与数据源说明

- 生产环境请设置长度至少 32 个字符的随机 `JWT_SECRET`；`docker-compose.prod.yml` 会在未设置时拒绝启动。
- 生产 Compose 默认启用 Agent JWT 校验（`AGENT_AUTH_ENABLED=true`），Agent 只通过 Nginx 内部网络访问。
- 热点爬虫默认不返回样例数据；如需离线演示，显式设置 `CRAWL_USE_SAMPLE_DATA=true`，页面中的数据会标记为样例来源。抖音 Cookie 请通过 `DOUYIN_COOKIE` 注入，不要写入代码。

### 5. 开始使用
如果使用上面的四终端方式，直接打开前端 `http://localhost:3000`；如果使用 Docker Compose 启动 `web`、`api-gateway`、`agent` 和 `nginx`，统一通过 Nginx 公共入口 `http://localhost:8080` 访问。Compose 中的 Go API 和 Agent 只在容器网络内使用 `api-gateway:8080` 与 `agent:8000`，不会直接发布到宿主机。

打开浏览器访问：
| 服务 | 地址 | 默认账号 |
|:---|:---|:---|
| 🎨 **主应用（手动启动前端）** | http://localhost:3000 | 注册新账号 |
| 🌐 **开发 Compose 公共入口（Nginx）** | http://localhost:8080 | 通过 Nginx 访问前端和 `/api/` |
| 📊 **Grafana监控** | http://localhost:3001 | admin / mago_grafana |
| 🔍 **Langfuse LLM观测** | 外部 Langfuse Cloud / 自行部署地址 | 需在 `.env` 配置后启用 |
| 📦 **MinIO控制台** | http://localhost:9001 | mago / mago_secret123 |
| 📈 **Prometheus** | http://localhost:9090 | - |
| 📚 **Agent API文档（手动启动 Agent 时）** | http://localhost:8000/docs | 仅开发调试；Compose 默认不对外暴露 Agent 端口 |

---

## 📁 项目结构

```
Mago-AIGC-Platform/
├── apps/
│   └── web/                    # Next.js前端
│       └── src/app/            # 所有页面（登录/Dashboard/热点/脚本/角色/风格/提示词等）
├── services/
│   ├── api-gateway/            # Go API网关（认证/项目/CRUD）
│   │   ├── internal/           # handler/middleware/service/repository/model
│   │   └── migrations/         # 数据库迁移（含性能索引）
│   └── agent/                  # Python Agent服务（LangGraph编排）
│       └── src/
│           ├── agents/         # 所有Agent实现
│           │   ├── trend_analyzer/    # 热点分析
│           │   ├── topic_recommender/ # 选题推荐
│           │   ├── ideation/          # 创意发散
│           │   ├── script/            # 8个脚本创作Agent
│           │   ├── character/         # 角色设计
│           │   ├── style/             # 风格设计
│           │   └── prompt/            # 提示词生成
│           ├── core/            # LangGraph总流程图（21个节点端到端串联，含4个人工确认门）
│           ├── knowledge/       # 预置知识库（100钩子/32叙事结构/20CTA等共198条）
│           ├── observability/   # Langfuse + OpenTelemetry集成
│           ├── llm/             # LLM统一网关（LiteLLM接入200+模型）
│           └── crawlers/        # 多平台热点爬虫
├── packages/
│   ├── shared-types/           # 手写共享类型（当前未被前端 import，见其 README）
│   └── shared-protos/          # OpenAPI 契约（预留目录，规划见其 README）
├── deploy/
│   ├── nginx/                  # Nginx开发/生产配置
│   └── observability/          # OTel/Prometheus/Grafana/Loki/Tempo配置
├── scripts/
│   ├── backup/                 # 数据库备份/恢复脚本
│   ├── doctor.sh               # 只读环境体检（make doctor）
│   ├── demo.sh                 # 无 Docker 启动 Agent + 前端（make demo）
│   ├── pnpm.sh                 # 固定 pnpm 版本的包装脚本
│   └── seed-db.sh              # Demo数据初始化
├── docs/                       # 文档（部署/排错/安全/架构）
├── docker-compose.yml          # 完整栈（含可观测栈与 Milvus）
├── docker-compose.min.yml      # 轻量栈：只有 Postgres + Redis + MinIO
└── docker-compose.prod.yml     # 生产 overlay
```

---

## 🎯 工作流模式

| 模式 | 适用场景 | 耗时 | 人工介入 |
|:---|:---|:---|:---|
| 快速模式(quick) | 快速出Demo/草稿 | ~3分钟 | 无，自动选最优方案 |
| 精细模式(detailed) | 专业生产 | ~10分钟+ | 创意/简报/脚本/分镜4个人工确认点，可修改调整 |
| 完整流程(full) | 从热点到提示词端到端 | ~5分钟/快速 ~15分钟/精细 | 可选角色风格定制 |

---

## 🧠 Agent架构

采用LangGraph状态机编排，共21个节点（含4个 `interrupt()` 人工确认门）：

```
START → 路由意图
  ↓
[热点研究→选题推荐]  (可选，用户问"有什么热点/没灵感"时触发)
  ↓
创意发散 → 🔍人工选创意（精细模式暂停）
  ↓
创意简报 → 🔍人工确认简报
  ↓
[角色设计?] → 风格设定  (角色可选，需要人设时启用)
  ↓
钩子设计 → 脚本撰写
  ↓
质量评估 → ❌不通过回环修改（最多2次）
  ↓
合规检查 → 节奏优化
  ↓
分镜生成 → 分镜质检 → 🔍人工确认分镜
  ↓
提示词生成 → 提示词QA → ❌失败重试1次
  ↓
导出打包 → END
```

支持断点续跑：关闭浏览器重新打开可以继续之前的任务。

---

## 🔍 可观测性

接入完整企业级可观测体系：
- **LLM调用追踪**：Langfuse查看每次LLM调用的输入/输出/token/成本/延迟
- **全链路Trace**：OpenTelemetry串联前端→Nginx→Go→Python→LLM→数据库
- **指标监控**：Prometheus采集QPS/延迟/错误率/Token消耗/成本
- **日志聚合**：Loki统一收集所有服务日志
- **Grafana看板**：预置全局总览/API/Agent/LLM/数据库/业务6个看板
- **分级告警**：P0（电话）/P1（15分钟）/P2（1小时）/P3（工作日）

---

## 🔒 安全措施

- JWT认证 + 权限校验
- 分层限流（防暴力破解/防刷）
- 安全响应头 + CORS精细化配置
- 请求大小限制
- SQL注入防护（GORM参数化）
- 敏感信息全部走环境变量，无硬编码密钥
- Panic全局捕获，避免服务崩溃

---

## 📚 文档

- [贡献指南](CONTRIBUTING.md) - 环境、make 目标、代码规范、如何加模型/加 Agent
- [更新日志](CHANGELOG.md) - 每个版本改了什么
- [安全策略](SECURITY.md) - 漏洞私密报告、已落地防护、已知限制、上线检查清单
- [开源发布清单](docs/opensource-release.md) - 当前可发布性结论与阻塞项
- [部署文档](docs/deployment.md) - 开发/生产部署、备份恢复、Kubernetes迁移说明
- [故障排查](docs/troubleshooting.md) - 常见问题解决
- [安全说明](docs/security.md) - 安全配置说明
- [架构文档](docs/architecture.md) - 系统架构说明
- [API设计](docs/api-design.md) - API接口规范
- [执行计划](docs/05-agent-platform-execution-plan.md) - 完整产品&技术规划

---

## 📊 代码统计

| 语言 | 文件数 | 代码量 |
|:---|:---|:---|
| TypeScript/TSX（前端 + 共享类型） | 46 | ~6,500 行 |
| Go（API 网关） | 59 | ~5,200 行 |
| Python（Agent 服务 src） | 87 | ~10,000 行 |
| SQL 迁移（6 组 up/down） | 12 | ~720 行 |
| 预置知识库 | 7 个 JSON | 钩子/情绪曲线/节奏/结构/风格/平台规范模板 |

> 统计口径：`find` + `wc -l`，不含 `node_modules`、`.venv`、文档与配置。测试代码另计（Agent `tests/` + 前端 `__tests__/`）。

---

## 🎬 下一步

1. 配置好API Key，启动服务
2. 注册账号，创建第一个项目
3. 输入："帮我做一个美妆新品带货的短视频创意"
4. 选择快速模式，3分钟后拿到完整脚本+分镜+12个模型的提示词包
5. 复制提示词包到对应模型平台生成视频 🚀（**自动推送到 Mago 平台的链路尚未实现**，见 [开源发布清单](docs/opensource-release.md)）

---

## License

当前仓库的 `LICENSE` 文件同时包含标准 MIT 授权条款和额外的中文限制性说明，两者的授权范围存在冲突，因此在法律条款确认前，不应把本项目宣传为“无条件 MIT”。开源发布前请先按照 [开源发布清单](./docs/opensource-release.md) 选定并重写为一种明确的许可证。
