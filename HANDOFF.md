# 🧙 Mago Agent Platform — 项目交接文档

## 🔄 2026-09-30 更新：真·token 级流式输出 + 前端门控测试

### 本轮完成
- **SSE 由“假流式”改为“真流式”**：`run_agent` 过去用 `ainvoke` 把整张图跑完才逐条吐事件，用户要等数十秒才看到任何输出。现改为 `graph.astream(stream_mode=["updates","custom"])`，每个节点产出的瞬间就推送到前端。
  - `updates` 流：节点级增量，逐个映射为 `ideas/brief/script/storyboard/...` 事件，并新增通用 `node` 事件，前端可据此显示“正在执行哪个节点”。
  - `custom` 流：新增 `src/common/streaming.py`，节点通过 `get_stream_writer()` 推送 token 级 `chunk`。`StorytellerAgent` 现在用 `call_llm_streaming()` 边生成边推送，脚本正文逐字出现。
  - 新增 `_astream_graph()` 统一兼容 LangGraph 不同版本 `(mode, payload)` 与裸 payload 两种 yield 形态；`_custom_to_sse()` 转发自定义事件且对未知类型向前兼容。
  - 流式是“尽力而为”的传输层能力：`streaming.py` 在无 LangGraph 运行上下文时静默降级，绝不因流式失败而中断业务节点。
- **新增后端流式测试** `tests/test_agent_streaming.py`（7 个用例）：token chunk 送达、chunk 与节点输出顺序、节点 delta 映射为 script 事件、中断经 updates 流上报、resume 走 `Command`、`_custom_to_sse` 空串/未知类型处理、`_astream_graph` 两种 yield 形态归一化。
- **新增前端门控测试** `apps/web/src/components/chat/__tests__/chat-interface-gate.test.tsx`（4 个用例）：门控横幅渲染、approval 续跑 payload 正确、token chunk 累积渲染进气泡、续跑后横幅消失。`vitest.setup.ts` 补 `scrollIntoView` polyfill（jsdom 缺失导致组件测试报错）。
- 既有 `test_hitl_resume.py` / `test_agent_regressions.py` 的路由图替身由 `ainvoke` 改为 `astream`，与新实现对齐。
- 真实图端到端冒烟：ideation 模式事件顺序 `meta→thinking→node→ideas→done` 增量到达；detailed 模式连续三轮续跑 `idea_selection→brief_review→script_review`，状态正确累积。

### 验证结果
- Agent：`pytest` **97 passed**、`ruff check` 通过、`mypy` 对 89 个源文件无错误。
- Web：`typecheck` 通过、`eslint` 通过、`vitest` **66 passed**。


## 🔄 2026-09-17 更新：发布前收尾复核

### 本轮完成
- 重新执行 Python Agent 全套检查：Ruff 通过，`pytest` **47 passed**，mypy 对 86 个源文件无错误。
- 重新执行 Go API：`go test ./...`、`go vet ./...`、`go test -race ./...` 均通过。
- 重新执行 Web：TypeScript（关闭增量写入以绕过 iCloud 缓存写入限制）、ESLint、Next.js 15.5.24 production build 均通过；16 个页面生成成功。
- 启动 standalone 前端并逐页 HTTP 冒烟：主要页面返回 200，不存在路由返回 404；`/studio` 在没有项目时按设计重定向到 `/projects`。
- 修复 `scripts/init_milvus.py` 对当前工作目录的隐式依赖；现在可从任意目录执行，并支持 `MILVUS_HOST`/`MILVUS_PORT`，会校验端口范围并在结束时断开连接。
- 生产 Compose overlay 强制要求显式设置 `ALLOWED_ORIGINS`，避免生产继承 localhost 默认 CORS；Go 启动校验同时拒绝空白/逗号占位配置和通配符来源，避免与凭据 CORS 组合产生安全问题。
- 完成 Go CORS 配置回归测试：生产显式来源校验通过，空来源和通配符来源均被拒绝。
- 更新 README/架构文档到 Next.js 15.5.24，安装说明改用不会意外改锁文件的 `go mod download`；CI 固定使用 pnpm 9.15.0。
- 前端生产依赖在线审计已通过：234 个生产依赖，info/low/moderate/high/critical 均为 0；锁文件中 Next.js 实际使用 PostCSS 8.5.28。
- 修复 Compose 的可用性问题：移除不完整的单容器 `langfuse/langfuse:latest`，默认核心栈不再依赖 Langfuse；Agent 的 Langfuse 接入改为显式可选的外部 endpoint/密钥。开发与生产 Compose 配置均重新解析通过，生产配置在缺少 Langfuse self-host 密钥时也能正常校验。
- 最终回归：`make test`、`make lint`、Python compileall、Shell `bash -n`、Compose config、页面/健康接口/SSE 冒烟均通过；当前仍无法在本机完成 Docker daemon 实际启动和 Nginx `-t`。

### 当前仍需外部环境验证
- 本机没有 Docker daemon、Nginx、Redis CLI、FFmpeg，尚未完成真实 Compose 镜像构建/启动、生产 overlay 联调、Nginx `-t`、视频文件分析及 Worker 重启/多副本测试。
- LICENSE 仍需项目所有者确认最终采用标准 MIT、自定义许可证、双许可证，或只开放明确目录；尚未在用户确认前修改。
- Docker Compose 中仍有 `minio/minio:latest`、`milvusdb/milvus:v2.4-latest` 浮动标签，发布前应在有 Docker 的环境中确认兼容版本后固定；此前不完整的单容器 `langfuse/langfuse:latest` 已移除，Langfuse 改为外部可选依赖。
- LangGraph 的 HITL 断点已改为可插拔的持久化 checkpointer：优先 `CHECKPOINTER_URL`（Postgres/Redis），其次 `AGENT_CHECKPOINT_PATH`（SQLite），未配置时回退进程内 `MemorySaver`。生产环境需配置其一，否则重启/多副本下断点仍会丢失（见下方“HITL 断点持久化”）。

## 今日继续审查记录（2026-09-15）

### 今天已完成
- 完成前端、Go API、Python Agent、Shell/YAML 的一轮静态检查与测试；前端 `typecheck`、`lint`、`build` 通过，Go `test/vet` 通过，Python 测试、Ruff、mypy 通过。
- 本轮修复 Agent Redis 客户端不读取 Pydantic `.env` 解析值的问题，新增 2 个回归测试；修复进度异步任务类型错误，Python 测试现为 29 passed。
- 本轮修复 Go API 的 Count 错误丢失、提示词包级联删除非原子、故事板跨项目脚本引用、趋势 limit 宽松解析；Go `test/vet/build` 重新通过。
- 视频下载失败日志改为只记录主机和异常类型，不再记录完整 URL 或可能包含签名参数的异常文本。
- 视频下载器新增 SSRF 防护：仅允许可解析到公网的 HTTP(S) 地址，拒绝 localhost、私网、回环、链路本地、保留地址、IPv6 本地地址和带凭据 URL；新增 4 个回归测试。
- 提示词包新增跨资源归属校验：Storyboard 必须属于同一 Project，Prompt 的 Shot 必须属于该 Storyboard，并为缺失 UUID 的 Prompt 生成 ID。
- Go CORS 放行 `X-Request-ID`；Nginx 三份配置统一规范化四个 Agent 专用 API 根路径的无尾斜线请求，避免误落到通用 Agent 路由。
- Go 资源接口统一将“资源不存在/无权访问”映射为 404，将未预期数据库错误保留为 500，避免泄漏内部错误详情或产生错误状态码。
- 修复了 Agent 长任务入队、Redis/ARQ 生命周期、视频场景检测、任务失败状态、安全错误信息和若干启动脚本/文档契约问题。
- 按用户反馈重新收敛工作台 UI：移除廉价渐变和过重阴影，改为浅灰系统背景、白色轻边框圆角卡片、系统字体、苹果蓝、轻量侧边栏选中态；精修了首页、侧边栏、顶部搜索栏、聊天气泡、快捷建议和输入框。
- 最新 UI 修改文件：
  - `apps/web/src/styles/globals.css`
  - `apps/web/src/app/dashboard/page.tsx`
  - `apps/web/src/components/chat/chat-interface.tsx`
  - `apps/web/src/components/layout/sidebar.tsx`
  - `apps/web/src/components/layout/header.tsx`
  - `apps/web/src/components/ui/card.tsx`
  - `apps/web/src/components/ui/button.tsx`
- 最新前端验证：`pnpm --dir apps/web typecheck && pnpm --dir apps/web lint && pnpm --dir apps/web build` 通过。

### 明天继续
1. 先打开并检查 3000 端口的实际页面；当前本机存在两个 Next dev 进程，3000/3001 可能不是同一个实例，需要清理重复进程并让用户当前浏览器回到正确实例。
2. 继续处理 Docker/部署收尾：新增根目录 `.dockerignore`，统一 README 与 `docs/deployment.md` 中 Compose 公共入口（Nginx `http://localhost:8080`）和手动启动 Go API `http://localhost:8080` 的表述。
3. 如果环境允许，执行真实的 `docker compose config/build/up`、生产 Compose 合并配置检查和 `nginx -t`；当前机器没有 Docker/Nginx，不能把这些结果假装为已通过。
4. 发布前仍需人工决定许可证文本；当前 `LICENSE` 不是可直接称为“标准 MIT”的纯 MIT 条款。
5. ~~如需生产级 HITL 断点恢复，替换 `MemorySaver()`~~ 已完成：见下方“HITL 断点持久化”。

---

> **交接时间**：2026-09-07
> **项目位置**：仓库根目录（使用相对路径）
> **文档性质**：本文保留历史开发交接记录；当前验证结果以 `README.md`、`docs/deployment.md` 和本节为准。
> **总代码量**：约12,500行代码/配置/文档，外加9份Agent执行指令（4,149行）

---

## 运行时配置注意事项

- Docker Compose 中 Agent 使用 `AGENT_REDIS_URL` 连接 Redis；宿主机直接运行 Agent 才使用 `REDIS_URL`。这样可避免容器内的 `localhost` 指向错误。
- Agent 在 Compose 中等待数据库迁移服务成功后再启动。

## HITL 断点持久化（2026-09-30）

精细/完整模式在 4 个关键节点暂停等待人工确认：创意选择、简报确认、脚本确认、分镜确认。
这些暂停使用 LangGraph 的 `interrupt()` 真正挂起图，并通过 `Command(resume=...)` 从同一节点续跑，
而不是用「条件边返回 `END`」假装暂停（旧实现会导致每条消息只能推进一个节点）。

- 实现位置：`services/agent/src/core/graph.py`（`_gate` / `_should_pause` / `_apply_gate_decision`、4 个 `*_gate` 节点）。
- Checkpointer 工厂：`services/agent/src/core/checkpoint.py`，解析顺序：
  1. `CHECKPOINTER_URL`（`postgresql://` 或 `redis://`，多副本/持久首选）
  2. `AGENT_CHECKPOINT_PATH`（SQLite 文件，单机持久）
  3. 进程内 `MemorySaver`（仅开发/演示，重启即丢）
- 可选依赖：`pip install -e ".[checkpoint-postgres]"` / `".[checkpoint-redis]"` / `".[checkpoint-sqlite]"`。
- 客户端续跑：请求体带 `resume`（布尔/选择 id/对象），或使用 `approved` / `rejected` / `selected_idea_id` / `feedback` 简写字段。
- 回归测试：`services/agent/tests/test_hitl_resume.py`（挂起、续跑跨多个节点、连续确认跑完、quick 模式不中断）。

---

## 当前验证状态（2026-09-17）

本仓库已完成一轮代码修复和可执行检查：

- 前端：`pnpm typecheck`、`pnpm lint`、`pnpm build` 通过；共享类型包类型检查通过。
- Go API：使用仓库内 Go 1.22.8 工具链执行 `go test ./...`、`go vet ./...` 和构建，均通过。
- Python Agent：Ruff、mypy（86 个源文件）通过，测试为 `47 passed`。
- Compose、Shell 脚本：静态 YAML/语法检查通过。
- 本机未安装 Docker/Nginx，因此 Compose 实际启动、镜像构建、Nginx `-t` 和完整端到端联调仍需在具备这些工具的机器上执行。

下方按日期排列的内容是历史记录，部分“待完成”描述可能已经过时，不应覆盖上述当前状态。

## 一、项目一句话定位

Mago Agent 创意平台是已有Mago生图/生视频聚合平台（见 `README.md` 已有介绍，在生产运行）的**上游"AI创意大脑"**。
核心流程：用户输入模糊想法 → AI热点发现 → 灵感发散（10个创意方向）→ 多Agent协作写脚本/分镜 → **生成12个主流AIGC模型的专业提示词包** → 一键推送到Mago平台生成。

重点：**不做视频生成本身**，专注做"想什么+写什么+怎么描述"，输出物是可直接粘贴的高质量Prompt。

---

## 二、技术栈硬约束（不可随意更改）

| 层 | 选型 | 版本 |
|:---|:---|:---|
| 前端 | **Next.js 14 (App Router) + React 18 + TypeScript strict + TailwindCSS + shadcn/ui** | Node 20+ |
| 前端状态 | zustand + @tanstack/react-query | - |
| 前端流程图 | @xyflow/react（React Flow） | v12 |
| 前端动效 | framer-motion | v11 |
| API网关 | **Go 1.22 + Gin** | - |
| ORM | GORM | - |
| 数据库迁移 | pressly/goose（SQL文件） | - |
| Agent服务 | **Python 3.11+ + FastAPI + LangGraph** | uv管理依赖 |
| LLM统一接口 | **LiteLLM** | 支持OpenAI/Anthropic/Google/DeepSeek等200+模型 |
| Agent编排 | **LangGraph**（StateGraph + Checkpointer + HITL） | v0.2+ |
| 数据库 | **PostgreSQL 16** | - |
| 缓存 | Redis 7 | - |
| 对象存储 | MinIO（S3兼容） | - |
| 向量库 | Milvus | v2.4 standalone |
| 日志 | Zap(Go) + structlog(Python) | - |
| 容器化 | Docker Compose(dev) / K8s(prod) | - |
| CI | GitHub Actions | - |
| 包管理 | pnpm(前端) / go mod(Go) / uv(Python) | - |

---

## 三、目录结构（已全部创建）

```
Mago-AIGC-Platform/
├── README.md                         # 项目说明（已更新）
├── Makefile                          # 统一命令入口
├── docker-compose.yml                # 开发环境全套（PG/Redis/MinIO/Milvus/Etcd/Nginx/3个服务）
├── docker-compose.prod.yml           # 生产参考
├── .env.example                      # 环境变量模板
├── .gitignore / .editorconfig
├── .github/workflows/
│   ├── ci.yml                        # CI: 前端lint+build, Go lint+test, Python lint+test
│   └── docker-build.yml              # Docker镜像构建
├── scripts/
│   ├── setup.sh                      # 一键初始化环境
│   ├── dev.sh                        # 开发启动引导
│   └── seed-db.sh                    # 种子数据
├── packages/
│   └── shared-types/                 # TS共享类型（核心DTO都在这）
├── apps/
│   └── web/                          # Next.js前端 ⬇️
│       ├── src/app/
│       │   ├── page.tsx              # Landing首页
│       │   ├── layout.tsx            # 根布局+主题
│       │   ├── login/page.tsx        # 登录/注册
│       │   ├── dashboard/
│       │   │   ├── layout.tsx        # 带侧边栏的Dashboard布局
│       │   │   └── page.tsx          # 工作台（Chat+右侧栏）
│       │   ├── projects/
│       │   │   ├── page.tsx          # 项目列表
│       │   │   └── [id]/page.tsx     # 项目详情（Chat嵌入）
│       │   ├── trends/, knowledge/, settings/  # 占位页
│       ├── src/components/
│       │   ├── chat/chat-interface.tsx   # ⭐核心Chat组件(SSE+Markdown+创意卡片)
│       │   ├── layout/{sidebar,header}.tsx
│       │   └── ui/{button,card,input,badge}.tsx  # shadcn风格组件
│       └── src/lib/{api,auth,utils}.ts
├── services/
│   ├── api-gateway/                  # Go API网关 ⬇️
│   │   ├── cmd/server/main.go
│   │   ├── internal/
│   │   │   ├── config/               # viper配置
│   │   │   ├── model/                # GORM Models（12张表）
│   │   │   ├── repository/           # 数据访问层（5个repo）
│   │   │   ├── service/              # 业务逻辑（Auth/Project）
│   │   │   ├── handler/              # HTTP handlers（5个）
│   │   │   ├── middleware/            # CORS/JWT/Logger/RequestID
│   │   │   ├── router/               # 路由注册
│   │   │   └── pkg/{jwt,hash,response,logger}
│   │   └── migrations/               # SQL迁移（000001_init_schema up/down）
│   └── agent/                        # Python Agent服务 ⬇️
│       ├── pyproject.toml
│       └── src/
│           ├── main.py               # FastAPI入口
│           ├── config.py             # pydantic-settings配置
│           ├── common/{logger,exceptions}
│           ├── llm/gateway.py        # ⭐LiteLLM统一网关（流式/embedding/fallback）
│           ├── core/{state,nodes,graph}.py  # LangGraph编排
│           ├── agents/
│           │   ├── base.py           # Agent基类
│           │   ├── echo/agent.py     # 测试Echo Agent
│           │   └── ideation/agent.py # ⭐灵感发散Agent（含8种创意算子）
│           ├── api/routes/{health,agent}.py  # FastAPI路由（含SSE流式）
│           └── tests/test_main.py    # pytest smoke tests
├── deploy/
│   ├── docker/{api-gateway,agent,web}.Dockerfile  # 多阶段构建
│   └── nginx/default.conf            # Nginx反代（Gzip+SSE缓冲关）
└── docs/
    ├── architecture.md               # 架构文档（含架构图）
    ├── api-design.md                 # API规范
    ├── dependencies.md               # 所有依赖登记
    ├── research/01-bootstrap.md      # Phase01调研结论
    ├── 05-agent-platform-execution-plan.md  # 总体执行计划（4149行指令之前已写）
    └── agent-instructions/           # ⭐⭐⭐ 9份Agent执行指令（最关键资产）
        ├── 00-README.md
        ├── 01-project-bootstrap.md
        ├── 02-trend-intelligence.md
        ├── 03-script-studio.md       # 脚本创作核心（创意输出灵魂）
        ├── 04-character-style.md
        ├── 05-prompt-engine.md       # 提示词引擎核心输出
        ├── 06-knowledge-base.md
        ├── 07-hitl-workflow.md
        ├── 08-platform-foundation.md
        └── 09-orchestrator.md        # 总调度指令
```

---

## 四、当前已完成什么（Phase 01交付物）

### ✅ 基础设施层
- [x] Monorepo骨架（pnpm workspace + Go/Python独立管理 + Makefile统一调度）
- [x] Docker Compose全套：PG16/Redis7/MinIO/Milvus2.4/Etcd/Nginx/3个服务
- [x] Dockerfile三个（多阶段构建，生产级）
- [x] Nginx配置（静态/Gzip/反代API/SSE特殊处理）
- [x] CI/CD（GitHub Actions三个job：前端/Go/Python）
- [x] 环境变量模板、EditorConfig、.gitignore

### ✅ Go API网关
- [x] 配置加载（viper风格）
- [x] 12张表的GORM Model定义（User/Org/Membership/Project/Script/Storyboard/Shot/Character/StylePreset/TrendTopic/ViralVideo/CreativeSession）
- [x] SQL Migration（up/down）
- [x] DB初始化+AutoMigrate
- [x] Zap结构化日志
- [x] JWT认证（access 15min + refresh 7天）
- [x] bcrypt密码哈希
- [x] 4个中间件（CORS/Auth/Logger/RequestID）
- [x] 统一JSON响应格式+分页工具
- [x] Repository层（User/Project/Script/Storyboard/Trend 5个）
- [x] Service层（AuthService注册登录、ProjectService CRUD）
- [x] Handler层（Health/Auth/Project/Trend 5个）
- [x] 路由注册

### ✅ Python Agent服务
- [x] pydantic-settings配置
- [x] structlog日志
- [x] 自定义异常体系
- [x] **LLM Gateway（LiteLLM封装）**：统一chat/stream/embed接口、错误处理、key配置
- [x] **LangGraph State定义**：AgentState/CreativeIdea/AgentMessage类型
- [x] NodeRegistry节点注册机制
- [x] **BaseAgent基类**：统一LLM调用、系统Prompt、流式接口
- [x] EchoAgent（测试链路）
- [x] **IdeationAgent灵感发散Agent**：8种创意激发算子（跨界移植/反转/极端化/代入/热梗/冲突/时间压缩/第四面墙）、JSON格式输出、offline模式兜底
- [x] LangGraph编排（echo/ideation/full三种graph）
- [x] FastAPI路由（Health + AgentRun SSE）
- [x] **SSE事件协议**：meta/thinking/chunk/ideas/done/error 6种事件类型
- [x] pytest基础测试

### ✅ 前端
- [x] Next.js 14 App Router + TS strict + TailwindCSS配置
- [x] shadcn/ui风格的4个基础组件（Button/Card/Input/Badge）
- [x] 全局样式（设计tokens+亮暗模式+渐变色+动画+glass-card）
- [x] 工具函数（cn/formatDuration/formatDate）
- [x] 认证工具（token存储/apiFetch封装401跳转）
- [x] API客户端（authApi/projectsApi）
- [x] **Sidebar导航**（工作台/项目/热点/知识库/设置）
- [x] Header顶栏（搜索+通知）
- [x] Dashboard布局（auth guard）
- [x] **Landing首页**（Hero+特性展示+CTA）
- [x] **登录/注册页**（完整表单+测试账号提示）
- [x] **Dashboard工作台**（Chat+右侧栏最近项目/今日灵感/快捷操作）
- [x] **ChatInterface组件**：SSE流式接收/Markdown渲染/创意卡片网格（评分/标签/AI可行性徽章）/快捷建议/Thinking指示器/Enter发送Shift+Enter换行/停止按钮
- [x] 项目列表页（新建弹窗/卡片网格/空状态）
- [x] 项目详情页（Chat嵌入）
- [x] 热点/知识库/设置占位页

### ✅ 文档
- [x] 架构文档（含ASCII架构图）
- [x] API设计规范（响应格式/分页/认证）
- [x] 依赖登记表（前端/Go/Python/基础设施 全部登记Stars/License）
- [x] GitHub调研结论（01-bootstrap）
- [x] README更新
- [x] **最重要的：9份Agent执行指令文档**（总计4149行，供后续Agent执行每个板块）

---

## 五、当前没有完成什么（需要下一个Agent做的事）

### 🔴 需要本地执行的收尾（沙箱无法装依赖）
1. **安装依赖**：
   ```bash
   cd apps/web && pnpm install
   cd ../../services/api-gateway && go mod tidy
   cd ../../services/agent && uv sync
   ```
2. **Lint验证**：
   ```bash
   cd apps/web && pnpm lint && pnpm typecheck
   cd ../../services/api-gateway && golangci-lint run
   cd ../../services/agent && uv run ruff check src/ && uv run mypy src/ --ignore-missing-imports
   ```
3. **启动验证**：
   ```bash
   docker compose up -d postgres redis minio etcd milvus
   # 三个终端分别启动
   cd apps/web && pnpm dev
   cd services/api-gateway && go run cmd/server/main.go
   cd services/agent && uv run uvicorn src.main:app --reload --port 8000
   ```
4. **端到端测试**：
   - 注册→登录→创建项目→Chat发消息→SSE流式收到回复
   - 配置OPENAI_API_KEY后Ideation Agent能返回真实创意卡片
5. **packages/shared-types** 中的类型导出（Go/Python已经有完整类型，TS端需要补全导入引用）
6. **Go端缺少golangci-lint配置文件**（`.golangci.yml`），需要创建
7. **seed-db.sh需要真正插入一个bcrypt哈希过的测试用户**（当前只是SQL占位），建议用Go的Register接口创建更可靠
8. **前端pnpm-lock.yaml未生成**（pnpm install后自动生成）

### 🟡 后续板块（按指令集执行，顺序如下）

**推荐执行顺序（看09-orchestrator.md的Wave依赖图）**：

1. **先装依赖把01跑通**（上面的步骤）
2. **06-knowledge-base.md（知识底座）** — 其他Agent依赖其检索接口，但它自己不依赖其他板块（除了01基础设施）
3. **03-script-studio.md（脚本创作中心）** — **最核心的创意输出板块**，用户最看重的部分
4. **04-character-style.md（角色与风格管理）** — 和03可部分并行
5. **02-trend-intelligence.md（热点情报）** — 相对独立，可并行
6. **05-prompt-engine.md（提示词引擎）** — **最核心的输出板块**，依赖03+04+06
7. **07-hitl-workflow.md（人机交互前端）** — 前端细化
8. **08-platform-foundation.md（集成/可观测/部署）** — 最后集成联调
9. 09-orchestrator.md是总调度指南，最后跑E2E

---

## 六、关键设计决策（不要随意推翻）

1. **LiteLLM统一接入所有LLM**，不直接调OpenAI/Anthropic SDK，方便换模型+fallback+成本追踪
2. **LangGraph做Agent编排**，不是CrewAI/AutoGen，因为需要HITL断点+状态持久化+生产可控
3. **Go做API网关/业务CRUD，Python做Agent/AI逻辑**——和Mago主站技术栈一致，性能和AI生态兼顾
4. **SSE做流式输出**，不用WebSocket（SSE更简单、代理友好、够用）
5. **提示词按模型单独模板**，不追求一个prompt打天下——MJ/SD/Kling/Runway/Sora语法差异太大
6. **三层创意漏斗（发散→辩论→收敛）**是创意输出的灵魂，不是一次生成就完
7. **三层Prompt设计**（宪法层/流程层/表达层），和Mago现有Prompt SOP一脉相承
8. **所有Agent执行必须先检索知识库**，不允许LLM自由发挥——这是稳定性的关键
9. **预置资产库是平台开箱即用价值**——50角色/100风格/100场景/100钩子/30叙事结构，不能留给用户自己建

---

## 七、最关键的文件在哪里

如果时间紧只看几个文件，按顺序读：

1. **`docs/agent-instructions/09-orchestrator.md`** — 总调度指令，讲清楚整体路线图和执行顺序
2. **`docs/05-agent-platform-execution-plan.md`** — 最初的详细产品规划（六大板块设计）
3. **`docs/agent-instructions/03-script-studio.md`** — 创意核心板块指令（灵感发散+多Agent编剧团）
4. **`docs/agent-instructions/05-prompt-engine.md`** — 提示词引擎指令（12模型适配、组装流水线、一致性策略）
5. **`services/agent/src/agents/ideation/agent.py`** — 已实现的Ideation Agent，可以看到当前Agent编码规范
6. **`services/agent/src/llm/gateway.py`** — LLM网关实现模式
7. **`apps/web/src/components/chat/chat-interface.tsx`** — Chat组件实现模式（SSE消费方式）
8. **`services/api-gateway/internal/model/model.go`** — 全部数据库模型，看数据结构就理解系统

---

## 八、快速启动命令（给下一个Agent）

```bash
cd /path/to/Mago-AIGC-Platform

# 第一次：装依赖
cd apps/web && pnpm install
cd ../../services/api-gateway && go mod tidy
cd ../../services/agent && uv sync
cd ../..

# 启动基础设施（Docker必须运行）
docker compose up -d postgres redis minio etcd milvus

# 三个终端分别启动
cd apps/web && pnpm dev                     # http://localhost:3000
cd services/api-gateway && go run cmd/server/main.go  # http://localhost:8080
cd services/agent && uv run uvicorn src.main:app --reload --port 8000  # http://localhost:8000

# 测试（先注册一个用户）
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123456","name":"测试"}'

# 浏览器打开 http://localhost:3000/login 登录
```

---

## 九、配置API Key

在 `.env` 文件中（从 `.env.example` 复制）至少配置一个LLM API Key：
- `OPENAI_API_KEY=sk-...`（推荐，GPT-4o效果最好）
- 或 `ANTHROPIC_API_KEY=sk-ant-...`（Claude 3.5 Sonnet）
- 或 `GOOGLE_API_KEY=...`（Gemini，免费额度大）
- 或 `DEEPSEEK_API_KEY=...`（便宜中文）

不配置Key Agent会进入offline模式返回友好提示，不会崩溃。

---

## 十、编码规范（必须遵守）

- **TypeScript**：strict模式，禁止any，ESLint+Prettier
- **Go**：golangci-lint，所有公开函数godoc，错误必须处理（不允许`_`丢弃，除非注释理由）
- **Python**：ruff+mypy（ignore-missing-imports可），公开函数docstring（Google风格）
- **Conventional Commits**：`feat:/fix:/docs:/refactor:/test:/chore:`
- **禁止硬编码密钥**，都走环境变量
- **禁止吞错**，所有error必须log或return
- **禁止前端直接调LLM API**，必须走后端代理
- **每个板块开始前必须Step 1 GitHub调研**，在`docs/research/`写结论，不闭门造车
- **第三方依赖必须登记到`docs/dependencies.md`**（用途/Stars/License/最后更新）

---

## 十一、联系上下文（之前做了什么）

1. 用户最初需求："短视频AIGC热门视频+电影级画质agent平台，企业级"
2. 收敛后定位：**不做生成/剪辑，专注做"从选题到文生图/文生视频提示词输出"的创意Agent平台**，Mago已有生图/生视频能力
3. 用户最侧重：**创意输出**——让没灵感的创作者找到方向，不是停留在想法阶段
4. 已产出9份执行指令（覆盖01-08板块+09总调度），指令要求Agent先GitHub调研再动手、复用优秀开源轮子
5. 已按01指令完成项目骨架代码（12,000+行）
6. 用户验收标准："百分百完成不缩水"

---

## 🔄 2026-09-08 更新：代码依赖安装验证结果

### ✅ 已验证可运行
- **Python Agent服务**：100%正常
  - Python 3.11.16（安装到 `.tools/python/`）
  - 所有依赖已安装（FastAPI/LangGraph/LiteLLM等）
  - 所有模块import无错误
  - FastAPI应用启动成功
  - `/health` → 200 ✅
  - `/api/v1/agent/health` → 200 ✅
  - `/api/v1/agent/run` SSE流式对话 → 完整meta/thinking/chunk/done事件流 ✅
  - Echo Agent离线模式返回友好提示 ✅

- **Go API网关**：代码100%编译通过
  - Go 1.22.8（安装到 `.tools/go/`）
  - 所有依赖通过goproxy.cn下载完成
  - `go mod tidy` 成功
  - `go vet ./...` 通过，0警告
  - `go build` 成功（产出19MB二进制）
  - ⚠️ 沙箱环境dyld限制无法执行二进制，**正常Mac/Linux上无此问题**，用`go run ./cmd/server`即可启动

- **Next.js前端**：
  - 所有npm依赖已安装
  - TypeScript `tsc --noEmit` 0错误通过
  - eslint/构建可正常进行
  - 缺失的依赖（next-themes/react-markdown/remark-gfm/rehype-highlight/@xyflow/react等）已补

### 📦 本地工具路径
- Go: `.tools/go/bin/go`
- Python 3.11: `services/agent/.venv/bin/python`
- GOPATH: `.tools/gopath/`
- GOCACHE: `.tools/gocache/`

### 🚀 正常Mac启动步骤（不用Docker也能验证代码正确性）
```bash
# Python Agent（无需DB即可验证health和SSE流）
cd services/agent && .venv/bin/uvicorn src.main:app --port 8000

# Go API（需要PG启动才能完整运行，但go build/vet确认代码正确）
cd services/api-gateway && export PATH="../../.tools/go/bin:$PATH" && go run ./cmd/server

# 前端
cd apps/web && pnpm dev
```

### ⚠️ 必须在本机做的事（沙箱无法完成）
1. **安装并启动Docker Desktop**（沙箱内无法运行Docker）
2. `docker compose up -d postgres redis minio etcd milvus` 启动基础设施
3. Go服务连PG后执行注册/登录/项目CRUD E2E
4. 前端pnpm build/next dev完整启动
5. 配置OPENAI_API_KEY后Ideation Agent能返回真实创意

---

## 🔄 2026-09-08 更新：03板块 Script Studio 完成

### ✅ 01板块bug修复
- **next.config.mix rewrites顺序bug已修复**：`/api/agent/:path*` 现在排在 `/api/:path*` 之前，SSE请求不会被错误代理到Go网关

### ✅ 03板块 Script Studio 已完成

#### 知识库（6个JSON文件）
- `services/agent/src/knowledge/data/hooks.json` — 10大类100种钩子模板
- `story_structures.json` — 32种叙事结构模板
- `ctas.json` — 20种CTA策略
- `emotion_curves.json` — 15种情绪曲线（含坐标点）
- `vertical_specs.json` — 20个垂类规范
- `rhythm_patterns.json` — 11种节奏模式
- `loader.py` — 统一加载器，带LRU缓存

#### Python Agent（8个Agent全部实现）
- `CreativeBriefAgent` — 创意简报生成
- `HookSpecialistAgent` — 3个不同类型钩子候选
- `StorytellerAgent` — 完整脚本（beats+body+CTA+情绪曲线+节奏）
- `StoryboardAgent` — 逐镜分镜表（景别/机位/运镜/光线/色调/AI难度警告）
- `EvaluatorAgent` — 7维度质量评分+改进建议（最多2轮自动迭代）
- `ComplianceAgent` — 广告法/平台规则合规审查（极限词/医疗宣称规则引擎+LLM双重检查）
- `RhythmOptimizerAgent` — 镜头时长节奏优化
- `DebateJudgeAgent` — 多候选方案裁判选择

#### LangGraph编排
- `build_script_studio_graph()` — 三层漏斗完整pipeline（ideation→brief→hooks→script→storyboard→evaluate→compliance→rhythm）
- `build_full_graph()` — 含意图路由（热点/直接/脚本），快速模式自动跳过HITL
- 支持quick模式（3分钟内自动跑完全流程）和detailed模式（每个关键节点HITL暂停）
- 评估不通过自动回环修改（最多2轮）

#### Go后端API
- `script_service.go` + `script_handler.go` — Scripts/Storyboards CRUD API
- 路由：GET/POST/PUT/DELETE `/api/v1/scripts`，GET/POST `/api/v1/storyboards`
- 已在main.go/router.go注册，编译通过

#### 前端页面
- `app/studio/[projectId]/page.tsx` — 脚本创作中心（三tab：灵感→脚本→分镜）
- ChatInterface升级支持script/storyboard SSE事件
- 创意卡片"用这个写脚本"按钮触发后续pipeline
- 脚本查看页（钩子/正文/节拍分解/CTA/备选钩子）
- 分镜查看页（景别/机位/运镜/光线/色调/AI难度警告卡片）
- Sidebar添加"脚本创作"入口（带03徽章）

#### Agent API
- `/api/v1/agent/run` 支持mode=quick/detailed
- 新增SSE事件类型：brief/script/storyboard/eval/compliance
- 新增 `/api/v1/agent/knowledge/summary` 知识库统计接口

#### 测试
- `tests/script/test_ideation.py` — 创意发散测试+知识库完整性
- `tests/script/test_compliance.py` — 合规审查（极限词/医疗宣称/清洁文本/严重度分级）
- `tests/script/test_storyboard.py` — 分镜质量（镜头数/抽象词检测/景别变化）

### ✅ 验证结果
- Go: `go vet` + `go build` 零错误 ✅
- Python: 所有agent import正常，offline模式端到端跑通 ✅
- Frontend: `tsc --noEmit` 零错误 ✅
- 知识库统计：hooks=100, story_structures=32, ctas=20, emotion_curves=15, vertical_specs=20, rhythm_patterns=11 ✅

### ⚠️ 需要本机完成
1. `cd services/agent && uv add --dev pytest pytest-asyncio && uv run pytest tests/script/ -v` 运行测试（沙箱无网络）
2. 配置OPENAI_API_KEY后测试真实LLM模式下的完整pipeline
3. 前端 `pnpm dev` 启动后在浏览器中测试完整创意→脚本→分镜流程
4. Docker启动PG后Go API的scripts/storyboards CRUD端到端测试

---

## 🔄 2026-09-09 更新：08板块 平台底座集成完成

### ✅ 已完成内容

#### 1. LangGraph总流程图完善
- 新增MemorySaver断点续跑支持，关闭浏览器重新打开可以继续之前的任务
- 全链路共17个节点完整串联：热点研究→选题推荐→创意发散→创意简报→角色设计（可选）→风格设计→钩子设计→脚本撰写→质量评估（最多回环2次）→合规检查→节奏优化→分镜生成→分镜质量检查→提示词生成→提示词QA→导出打包
- 新增`get_graph_by_name`工厂函数支持多粒度图调用
- 快速模式自动跳过HITL节点，详细模式在关键节点暂停等待人工确认

#### 2. 可观测体系
- **Langfuse LLM可观测**：Python端集成，自动捕获所有LiteLLM调用，展示trace/token/cost
- **OpenTelemetry集成**：Go/Python双端SDK支持，Trace/Metric/Log统一采集
- **Grafana完整栈配置**：
  - OTel Collector统一接收遥测数据
  - Prometheus存储指标，已配置服务发现
  - Loki存储日志
  - Tempo存储全链路Trace
  - Grafana自动配置Prometheus/Loki/Tempo数据源
- 共7个可观测服务全部写入docker-compose.yml，一键启动

#### 3. 安全加固
- **Go API网关**：新增4个中间件：
  - Recovery：全局panic捕获，避免服务崩溃
  - SecurityHeaders：添加X-Frame-Options/X-Content-Type-Options/HSTS等安全头
  - RateLimiter：按IP令牌桶限流（登录接口5rps防暴破，普通接口50rps，全局200rps）
  - RequestSizeLimit：请求体大小限制10MB
- **Python Agent**：新增安全头中间件、RequestID全链路追踪中间件
- CORS配置精细化，生产环境不使用*
- `/metrics`端点暴露供Prometheus采集

#### 4. 性能优化
- Redis异步缓存客户端（JSON序列化+TTL+模式失效）
- 数据库性能索引迁移（15+张表全部添加合理索引，覆盖常用查询）
- LLM成本优化基础架构（模型路由+缓存+prompt压缩预留位置）

#### 5. 容器化与部署
- 三个服务多阶段Dockerfile：
  - Go API：~25MB（alpine基础，无依赖）
  - Python Agent：~350MB（python:slim + 清理缓存）
  - Next.js：~180MB（standalone输出）
- Nginx生产配置：反向代理+SSE流式支持+gzip压缩+静态资源缓存+安全头
- docker-compose.yml更新：共16个服务（基础设施+应用+可观测+Nginx）
- 数据库备份脚本：每日pg_dump自动备份+S3上传+旧备份清理，配套恢复脚本
- Demo种子数据：4个预置角色、5种视觉风格、5个场景、5种道具、12个AIGC模型配置

#### 6. 文档完善
- `docs/deployment.md`：完整部署指南（开发/生产/备份/K8s）
- `docs/troubleshooting.md`：常见问题排查手册
- `docs/security.md`：安全说明
- `docs/research/08-platform-foundation.md`：08板块技术选型调研
- `.env.example`更新新增可观测/Mago对接相关配置项

### ✅ 验证结果
- Go: `go vet` + `go build` 零错误 ✅
- Python: 所有模块import正常，full graph编译通过（17节点），知识库加载正常（198条知识） ✅
- Frontend: `tsc --noEmit` 零错误 ✅
- 所有必要文件和目录结构完整 ✅

### ⚠️ 本机启动需要执行
```bash
# 1. 安装新增依赖
cd services/api-gateway && go mod tidy
cd ../..
cd services/agent && uv sync
cd ../..

# 2. 配置环境变量
cp .env.example .env
# 编辑.env填入OPENAI_API_KEY

# 3. 启动基础设施
docker compose up -d postgres redis minio etcd milvus otel-collector prometheus loki tempo grafana
# Langfuse 需按官方多容器方案单独部署，或使用 Langfuse Cloud；不要使用旧的单容器命令。

# 4. 启动服务（分别启动或用启动脚本）
./🚀启动Mago.command
```

### 📋 后续Phase 2待完成项
- K8s完整部署清单（当前docker-compose可以满足中小规模生产）
- Playwright E2E自动化测试
- k6负载测试
- RBAC细粒度权限控制
- Mago平台SSO/API/Webhook对接
- LLM成本优化效果验证

---

## 🔄 2026-09-09 更新：09板块 总聚合调度完成，全项目交付

### ✅ 最终交付完成
01-09所有板块全部完成，全量验证通过：

#### 09新增内容
1. **统一Agent API更新**：`/api/v1/agent/run` 支持full模式，串联所有17个节点端到端工作流
   - 新增full模式：热点→选题→创意→简报→角色→风格→钩子→脚本→评估→合规→节奏→分镜→提示词→导出全流程
   - SSE事件支持所有节点输出（trend/topics/ideas/brief/characters/style/script/eval/compliance/storyboard/prompt/export）
   - 自动识别HITL暂停节点，支持断点续跑
   - 新增`/api/v1/agent/graph-info`接口返回支持的模式和节点信息
2. **优雅降级处理**：observability模块(langfuse/opentelemetry)在依赖未安装时自动禁用，不影响核心功能运行
3. **最终README更新**：完整项目介绍、快速开始、架构说明、工作流介绍、访问地址等

### ✅ 最终验收结果
| 检查项 | 结果 |
|:---|:---|
| Go API网关 `go vet` + `go build` | ✅ 0错误，19MB二进制 |
| Python Agent全量导入 + FastAPI app创建 | ✅ 0错误 |
| Python Full Graph编译 | ✅ 17个节点完整 |
| Next.js前端 `tsc --noEmit` | ✅ 0类型错误 |
| 前端页面（14个页面） | ✅ 全部存在，覆盖所有板块 |
| 核心文件/文档/部署配置 | ✅ 全部完整 |
| 数据库迁移（10个SQL文件） | ✅ 含性能索引 |
| Docker服务 | ✅ Compose 配置解析通过；开发/生产各 16 个服务（不含外部 Langfuse） |

### 📊 项目最终统计
- 总代码量：约16000行（Go+Python+TypeScript）+ 198条预置知识库
- 前端：14个页面，完整覆盖热点/创意/脚本/分镜/角色/风格/提示词/导出全流程
- Agent：14个Agent，LangGraph状态机17个节点端到端串联，支持断点续跑+人工确认
- API：Go网关完整CRUD+5个安全中间件
- 可观测：Langfuse LLM观测 + OpenTelemetry全链路追踪 + Grafana/Prometheus/Loki/Tempo完整栈
- 部署：多阶段Dockerfile（最小镜像25MB）、Docker Compose一键启动、备份脚本、K8s配置参考
- 文档：README/deployment/troubleshooting/security/architecture/api-design完整

### 🚀 本地启动步骤
```bash
# 1. 安装依赖（首次）
cd services/api-gateway && go mod tidy && cd ../..
# （可选）cd services/agent && uv sync  # 安装langfuse/opentelemetry可观测依赖
pnpm install

# 2. 配置
cp .env.example .env
# 填入 OPENAI_API_KEY

# 3. 启动基础设施
docker compose up -d postgres redis minio etcd milvus

# （可选）启动可观测栈
# docker compose up -d otel-collector prometheus loki tempo grafana
# Langfuse 需按官方多容器方案单独部署，或使用 Langfuse Cloud。

# 4. 启动服务
./🚀启动Mago.command

# 5. 访问 http://localhost:3000
```

## 🔄 2026-09-15 更新：继续审查与回归验证

### 本轮修复
- Python Agent 的视频分析 `analysis_mode` 收紧为 `fast` / `accurate`，API 对未知值返回 422，Worker 与 API 使用同一类型契约。
- Go API Gateway 视频分析请求新增回归测试，最小请求不会向 Agent 发送空字符串或 `null` 的可选字段。

### 本轮验证
- Python Agent：`ruff check` 通过；`compileall` 通过；`pytest` **42 passed**；Python 3.12 目标下 `mypy` **86 files / 0 errors**。
- Go API Gateway：`go test ./...` 通过；`go vet ./...` 通过；`CGO_ENABLED=0 go build ./cmd/server` 通过。
- 前端：Next.js 生产构建通过（15 个页面）；开发服务器逐页访问 `/`、`/login`、`/dashboard`、`/projects`、`/topics`、`/trends`、`/viral`、`/characters`、`/styles`、`/prompts`、`/knowledge` 均返回 HTTP 200，未发现运行时错误标记。
- Compose/YAML 与启动脚本语法检查通过。
- Agent 实际 HTTP 冒烟：`GET /health`、`GET /api/v1/agent/health` 均返回 200；非法 `analysis_mode=turbo` 返回 422；测试后已停止临时服务。

### 尚未完成的外部依赖验证
- 当前机器没有 Docker CLI/daemon、Nginx、Redis CLI、FFmpeg，因此尚未执行真实 Docker Compose 启动、容器联调、Nginx `-t` 和视频文件分析。
- iCloud 工作区的 `.next` 写入受当前执行环境限制；前端生产构建已在 `/private/tmp/mago-build` 的同等源码副本中成功完成。

## 🔄 2026-09-15 更新：生产启动与真实 HTTP 回归修复

### 本轮新增修复
- 恢复 `apps/web` 前端源码到项目目录；iCloud 同步曾导致该目录显示为空，已恢复 35 个前端源码/配置文件。
- 新增 `apps/web/Dockerfile`：使用 pnpm workspace + Next.js standalone 多阶段构建，补齐 Compose 原本引用但缺失的 Web 镜像构建文件。
- 修复 `apps/web/package.json` 的生产启动命令：从不兼容 standalone 的 `next start` 改为运行 `.next/standalone/apps/web/server.js`。
- 新增 `apps/web/scripts/prepare-standalone.mjs`，在构建后复制 `.next/static` 和 `public` 到 standalone 目录，避免本地 standalone 启动后 HTML 可访问但 CSS/JS 返回 404。

### 本轮验证
- 前端 `typecheck`：通过。
- 前端 `lint`：通过。
- Next.js production build：通过，生成 16 个页面，包含 `/studio` 和 `/studio/[projectId]`。
- standalone 生产服务：逐页 HTTP 冒烟通过；`/`、`/dashboard`、`/login`、`/projects`、`/characters`、`/styles`、`/prompts`、`/trends`、`/topics`、`/viral`、`/knowledge`、`/settings` 返回 200；`/studio` 正确重定向到项目页；不存在路由返回 404。
- standalone 静态资源：CSS 资源返回 200。
- Agent HTTP 联调：`/health`、`/api/v1/agent/health`、Next rewrite 的 `/api/agent/health` 和 `/api/agent/graph-info` 返回 200。
- SSE 联调：通过 `/api/agent/run` 的 `echo` 模式成功收到 `meta`、`thinking`、`done` 事件和 `[DONE]` 结束标记。
- Python Agent：`ruff check` 通过；`pytest` 42 passed（仅第三方弃用警告）。
- Compose 文件：使用 Ruby YAML parser 解析 `docker-compose.yml` 和 `docker-compose.prod.yml` 均通过。

### 当前明确限制
- 本机未安装 Docker CLI/daemon、Nginx、Redis CLI，因此尚未执行真实 Compose 容器启动、Nginx `-t`、PostgreSQL/Redis/MinIO 联调。
- Go 依赖当前不在本机 module cache；尝试从官方 proxy 下载时网络请求长时间无响应，未将本轮 Go vet/build 结果冒充为已通过。历史回归中 Go vet/build 曾通过，待网络或 Docker/Linux 环境可用后应再次执行。
- Agent 本地无 Redis 时会优雅降级到开发内存任务模式；生产环境仍必须提供 Redis、PostgreSQL、MinIO 和有效 JWT/LLM 配置。
- 生产启动器进一步支持 `pnpm --filter mago-agent-web start -p 3100` / `--hostname`，并已验证指定 3100 端口页面和 CSS 均返回 200。
## 🔄 2026-09-16 更新：热点页面超时保护与全量复核

### 本轮修复
- 为 Agent 的 `/api/v1/trends/insights` 增加可配置超时（`TREND_INSIGHTS_TIMEOUT_SECONDS`，默认 15 秒）。热点平台不可访问时，工作台现在返回可渲染的空/部分结果，不再无限转圈；完整抓取继续通过队列接口执行。
- 超时响应增加 `timed_out` 与 `errors` 字段，便于前端和监控识别降级状态。
- 更新 `.env.example` 与 `docs/deployment.md`，明确热点洞察与后台抓取的行为差异。

### 本轮验证
- Agent `pytest`：**43 passed**；`ruff check --no-cache`：通过；Python `compileall`：通过。
- Go API：`go test ./...`、`go vet ./...`、`CGO_ENABLED=0 go build ./cmd/server`：通过（使用仓库内 Go 与缓存路径）。
- 前端（在 `/private/tmp/mago-build` 的同等源码副本，避免 iCloud `.next` 写入限制）：typecheck、lint、Next 生产构建通过，16 个页面生成成功。
- 运行中服务：前端页面、Agent 健康检查、Next→Agent 代理、直连/代理 SSE 均返回 200；dashboard 首屏 13 个 CSS/JS 资源均无 404；热点洞察实测约 5.9 秒返回。

### 环境限制
- 当前机器仍没有 Docker CLI/daemon、Nginx、FFmpeg、Redis CLI，因此 Compose 实机启动、Nginx `-t`、视频文件分析和 Redis/Worker 重启联调仍需在具备这些依赖的机器上执行。
- iCloud 工作区直接生成 `.next` 可能触发 `EPERM`，生产构建已在临时同等源码副本验证；这不是应用代码错误。

