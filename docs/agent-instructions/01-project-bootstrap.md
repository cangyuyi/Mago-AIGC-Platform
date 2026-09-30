# 指令 01：项目初始化与基础设施搭建

## 角色设定

你是一名**全栈高级工程师兼DevOps**，擅长从零搭建企业级TypeScript/Go/Python混合技术栈的Monorepo项目。你熟悉Next.js、Go(Gin)、FastAPI、PostgreSQL、Redis、Docker生态。

## 任务目标

在 `<repo-root>/` 目录下搭建一个**生产可用的Monorepo项目骨架**，包含前端(Next.js)、后端(Go)、Agent服务(Python)、基础设施(PostgreSQL/Redis/MinIO/Milvus)四大部分，完成CI/CD、代码规范、数据库迁移、认证系统的搭建。

## 产品背景（必读）

本项目是 **Mago AIGC 创意 Agent 平台**，作为已有 Mago 生图/生视频平台（已在生产运行，技术栈Go+React）的上游"AI创意大脑"。核心功能是：热点发现 → 选题策划 → 脚本分镜 → 角色/风格管理 → 文生图/文生视频专业提示词生成 → 一键推送到Mago平台执行生成。

参考文档（你必须先阅读）：
- `docs/05-agent-platform-execution-plan.md`（完整执行计划，了解整体架构）
- `README.md`（了解Mago已有产品和技术栈）
- `docs/02-prompt-iteration-sop.md`（了解Prompt工程SOP）
- `docs/agent-instructions/00-README.md`（本指令集规范）

## 项目结构要求（最终产物的目录结构）

```
Mago-AIGC-Platform/
├── README.md                           # 项目总README（更新）
├── docker-compose.yml                  # 本地开发环境一键启动
├── docker-compose.prod.yml             # 生产环境参考
├── Makefile                            # 常用命令聚合
├── .env.example                        # 环境变量模板
├── .github/
│   └── workflows/
│       ├── ci.yml                      # CI：lint+test+build
│       └── docker-build.yml            # 镜像构建
├── docs/
│   ├── architecture.md                 # 架构文档（含Mermaid架构图）
│   ├── api-design.md                   # API设计规范
│   ├── dependencies.md                 # 第三方依赖登记（按00-README要求）
│   └── ...（已有文档保留）
├── packages/
│   ├── shared-types/                   # 共享TypeScript类型定义
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/index.ts
│   └── shared-protos/                  # 共享API类型/OpenAPI生成产物
│       └── openapi.yaml
├── apps/
│   ├── web/                            # Next.js前端
│   │   ├── package.json
│   │   ├── next.config.mjs
│   │   ├── tsconfig.json
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.mjs
│   │   ├── .eslintrc.json
│   │   ├── public/
│   │   └── src/
│   │       ├── app/
│   │       │   ├── layout.tsx
│   │       │   ├── page.tsx            # 首页/Landing
│   │       │   ├── login/
│   │       │   ├── dashboard/
│   │       │   ├── projects/
│   │       │   └── api/                # Next.js API routes (BFF)
│   │       ├── components/
│   │       │   ├── ui/                 # shadcn/ui 组件
│   │       │   ├── chat/               # 对话组件
│   │       │   ├── project/            # 项目相关组件
│   │       │   └── layout/             # 布局组件
│   │       ├── lib/
│   │       │   ├── api.ts              # API调用封装
│   │       │   ├── auth.ts             # 认证逻辑
│   │       │   └── utils.ts
│   │       ├── hooks/
│   │       └── styles/
│   │           └── globals.css
│   └── admin/                          # 管理后台（简化版，Phase 2使用，先留壳）
│       └── ...
├── services/
│   ├── api-gateway/                    # Go API网关+业务服务
│   │   ├── go.mod
│   │   ├── go.sum
│   │   ├── Makefile
│   │   ├── cmd/server/main.go
│   │   ├── internal/
│   │   │   ├── config/                 # 配置加载
│   │   │   ├── handler/                # HTTP handlers
│   │   │   ├── middleware/             # 中间件(auth/cors/logging/ratelimit)
│   │   │   ├── model/                  # DB models
│   │   │   ├── repository/             # 数据访问层
│   │   │   ├── service/                # 业务逻辑层
│   │   │   ├── router/                 # 路由注册
│   │   │   └── pkg/                    # 内部公共包
│   │   │       ├── jwt/
│   │   │       ├── hash/
│   │   │       ├── response/
│   │   │       └── logger/
│   │   ├── migrations/                 # 数据库迁移文件
│   │   │   ├── 000001_init_schema.up.sql
│   │   │   └── 000001_init_schema.down.sql
│   │   └── api/openapi.yaml            # OpenAPI规格
│   └── agent/                          # Python Agent服务
│       ├── pyproject.toml              # 用uv或poetry管理
│       ├── Dockerfile
│       ├── Makefile
│       ├── src/
│       │   ├── main.py                 # FastAPI入口
│       │   ├── config.py               # 配置(pydantic-settings)
│       │   ├── api/                    # HTTP路由
│       │   │   └── routes/
│       │   ├── agents/                 # Agent实现（后续填充）
│       │   │   └── base.py
│       │   ├── core/                   # Agent编排核心
│       │   │   ├── graph.py            # LangGraph StateGraph定义
│       │   │   ├── state.py            # Agent状态定义
│       │   │   └── nodes.py            # 节点基类
│       │   ├── llm/                    # LLM网关
│       │   │   ├── gateway.py          # LiteLLM封装
│       │   │   └── prompts/            # Prompt模板目录
│       │   ├── tools/                  # Agent可用工具
│       │   └── common/                 # 公共模块
│       │       ├── logger.py
│       │       └── exceptions.py
│       ├── tests/
│       └── scripts/
├── deploy/
│   ├── docker/
│   │   ├── api-gateway.Dockerfile
│   │   ├── agent.Dockerfile
│   │   └── web.Dockerfile
│   └── nginx/
│       └── default.conf
└── scripts/
    ├── dev.sh                          # 本地开发启动脚本
    ├── setup.sh                        # 初始化环境脚本
    └── seed-db.sh                      # 数据库种子数据脚本
```

## 执行步骤

### Step 1：调研GitHub优秀Monorepo脚手架（必须）

在动手写代码之前，**必须**搜索和评估以下内容，在 `docs/architecture.md` 中记录调研结论和选型理由：

1. **Monorepo管理方案**：搜索对比 Turborepo vs Nx vs pnpm workspace，选择最适合Next.js+Go+Python混合栈的方案（建议pnpm workspace管理前端，Go/Python各管各，统一在根目录Makefile调度）。
   - 搜索关键词：`monorepo nextjs golang python`, `pnpm workspace monorepo`, `turborepo polyglot`
   - 参考项目：`vercel/turborepo/examples`, `belgattitude/nextjs-monorepo-example` (8k+ stars)

2. **Next.js + shadcn/ui + Tailwind 初始化方案**：
   - 搜索关键词：`next.js 14 shadcn tailwind boilerplate enterprise`, `shadcn ui next 14 app router starter`
   - 参考项目：`shadcn-ui/taxonomy` (⭐参考设计), `ixartz/SaaS-Boilerplate` (⭐企业级SaaS模板), `nextauthjs/next-auth-example`
   - 要求：使用App Router、Server Components/Client Components合理分离、支持暗色模式

3. **Go + Gin 企业脚手架**：
   - 搜索关键词：`golang gin enterprise boilerplate`, `go clean architecture gin`, `golang project layout production`
   - 参考项目：`golang-standards/project-layout` (⭐标准项目布局), `gin-gonic/examples`, `go-gorm/gorm`（ORM选型）, `pressly/goose`（迁移工具）
   - 要求：遵循clean architecture分层（handler/service/repository/model）、使用GORM或sqlc、JWT认证、配置管理用viper或yaml

4. **FastAPI + LangGraph 项目结构**：
   - 搜索关键词：`fastapi langgraph production template`, `langgraph fastapi boilerplate`, `langserve template`
   - 参考项目：`langchain-ai/langgraph` 官方examples, `langchain-ai/langserve`
   - 要求：使用LangGraph的StateGraph、支持SSE流式输出、有Pydantic v2模型、LiteLLM统一接入

5. **Docker Compose 本地开发全套**：
   - 参考项目：`docker/awesome-compose` 中postgres/redis/minio/milvus的标准配置

### Step 2：根目录初始化

创建根目录文件：
- `pnpm-workspace.yaml`（若用pnpm管理前端）
- `Makefile`：包含 `make dev`, `make build`, `make test`, `make lint`, `make migrate-up`, `make migrate-down`, `make seed` 等常用命令
- `.env.example`：包含所有必要环境变量模板（DB_URL, REDIS_URL, MINIO_*, JWT_SECRET, OPENAI_API_KEY等）
- `.gitignore`：涵盖node_modules, .env, dist, bin, __pycache__, *.pyc, .next, coverage等
- `.editorconfig`

### Step 3：前端项目初始化（apps/web）

要求：
- Next.js 14+ (App Router, TypeScript, TailwindCSS)
- 集成 shadcn/ui（执行 `npx shadcn-ui@latest init`，配置正确的路径别名）
- 安装基础依赖：`lucide-react`(图标), `next-themes`(暗色模式), `react-hook-form`+`zod`(表单校验), `@tanstack/react-query`(数据请求), `zustand`(轻量状态管理), `react-flow`(工作流画布)
- 安装 `@packages/shared-types` 作为workspace依赖
- 实现基础布局：顶部导航栏、侧边栏、主内容区
- 实现登录页（UI先行，对接Go后端API）
- 实现Dashboard首页（占位，显示项目列表空状态）
- 封装好 `lib/api.ts` 提供统一的fetch封装（自动带JWT、错误处理、类型推断）
- 封装好 `components/chat/chat-interface.tsx`：一个基础的Chat UI组件（消息列表+输入框+流式输出支持，后续板块要用）

### Step 4：Go API网关初始化（services/api-gateway）

要求：
- 使用 Go 1.21+，Go Modules
- Web框架用 Gin 或 Fiber（调研后选一个，建议Gin生态更成熟）
- 分层架构：`handler → service → repository → model`
- 配置管理：用 `viper` 或 `spf13/viper` 读取.env/yaml
- 日志：`uber-go/zap` 或 `rs/zerolog`（结构化日志）
- ORM：`gorm/gorm`（开发快）或 `sqlc-dev/sqlc`（类型安全），二选一
- 数据库迁移：`pressly/goose` 或 `golang-migrate/migrate`
- JWT认证：`golang-jwt/jwt` 实现access token + refresh token
- 密码哈希：`golang.org/x/crypto/bcrypt`
- 中间件：CORS、RequestID、Logger、Recovery、Auth（JWT解析）、RateLimit（`golang.org/x/time/rate` 或 `ulule/limiter`）
- 统一响应格式：`{"code": 0, "message": "ok", "data": {...}}` 成功；`{"code": 10001, "message": "error msg"}` 错误
- 必须实现的API：
  - `POST /api/v1/auth/register` - 用户注册
  - `POST /api/v1/auth/login` - 用户登录（返回JWT）
  - `POST /api/v1/auth/refresh` - 刷新token
  - `GET  /api/v1/auth/me` - 获取当前用户
  - `GET  /api/v1/projects` - 项目列表（分页）
  - `POST /api/v1/projects` - 创建项目
  - `GET  /api/v1/projects/:id` - 项目详情
  - `PUT  /api/v1/projects/:id` - 更新项目
  - `DELETE /api/v1/projects/:id` - 删除项目
  - `GET  /api/v1/health` - 健康检查
- 每个接口必须有请求/响应结构体、参数校验（`go-playground/validator`）
- Swagger/OpenAPI文档：用 `swaggo/swag` 自动生成或手写openapi.yaml
- 数据库迁移：创建初始migration，包含 users表、organizations表、memberships表、projects表的Schema（字段设计合理：id uuid主键、created_at/updated_at/deleted_at软删除、外键约束、必要索引）

### Step 5：Python Agent服务初始化（services/agent）

要求：
- Python 3.11+，用 `uv` 或 `poetry` 管理依赖（推荐uv，速度快）
- 核心依赖：`fastapi`, `uvicorn`, `langgraph`, `langchain`, `langchain-openai`, `langchain-anthropic`, `litellm`, `pydantic>=2.0`, `pydantic-settings`, `python-dotenv`, `httpx`, `sqlalchemy`(可选，或直接调用Go API)
- FastAPI应用结构：
  - `main.py`：创建FastAPI实例、注册路由、CORS配置、全局异常处理
  - `config.py`：`pydantic-settings` 管理所有配置（LLM API keys、DB连接、服务地址等）
  - `api/routes/`：路由模块，初始实现 `GET /health` 和 `POST /api/v1/agent/run`（占位，调用一个echo Agent测试联通）
  - `agents/base.py`：Agent基类，定义统一的 `arun(input) -> output` 接口
  - `core/graph.py`：初始化一个LangGraph StateGraph，包含一个占位的echo节点
  - `core/state.py`：定义AgentState（Pydantic Model，包含messages、project_id、current_step等基础字段）
  - `llm/gateway.py`：封装LiteLLM，提供 `acompletion()`、`astream()` 统一方法，支持自动fallback、token计数、cost追踪
- 实现流式输出：Agent的思考/输出必须支持SSE (Server-Sent Events) 流式返回给前端
- 实现一个echo测试Agent：收到什么回什么+调用LLM加一句"你好，我是Mago Agent"，验证LLM链路联通

### Step 6：共享基础设施

- 实现 `packages/shared-types`：定义前后端共享的TypeScript类型（User, Project, Script, StoryboardShot, PromptPackage等，初版先定义核心的几个）
- 生成 `packages/shared-protos/openapi.yaml`：从Go后端Swagger生成或手写，前端基于这个生成API client（可用 `openapi-typescript` 或 `openapi-typescript-codegen`）

### Step 7：Docker & 本地开发环境

- 编写 `docker-compose.yml`，一键启动以下服务：
  - `postgres`: postgres:16-alpine，端口5432，带volume持久化
  - `redis`: redis:7-alpine，端口6379
  - `minio`: minio/minio，端口9000(API)/9001(Console)
  - `milvus`: milvusdb/milvus (standalone模式)，端口19530，依赖etcd+minio
  - `api-gateway`: 本地build，端口8080，依赖上面三个服务
  - `agent`: 本地build，端口8000，依赖LLM API（外部）
  - `web`: 本地build，端口3000
  - `nginx`: nginx:alpine，端口80，反向代理web/api/agent
- 编写各Dockerfile（多阶段构建，生产镜像alpine基础，减小体积）
- 编写 `scripts/setup.sh`：检查依赖（node/pnpm/go/python3/uv/docker）、复制.env.example、安装依赖、准备数据库
- 编写 `scripts/dev.sh`：启动开发模式（前端next dev + Go air热重载 + Python uvicorn --reload）
- 确保 `docker-compose up` 可以一键启动所有服务

### Step 8：CI/CD

- 编写 `.github/workflows/ci.yml`：
  - 触发条件：push PR到main
  - Job 1 (frontend lint+test+build)：pnpm install → pnpm lint → pnpm test → pnpm build
  - Job 2 (go lint+test+build)：golangci-lint run → go test → go build
  - Job 3 (python lint+test)：ruff check → mypy → pytest
- 编写 `.github/workflows/docker-build.yml`：tag推送时构建三个镜像push到registry

### Step 9：认证系统联调

- 前端登录页对接Go后端 `/auth/login` API
- 登录成功后JWT存localStorage（或httpOnly cookie，更安全）
- 前端所有API请求自动带 `Authorization: Bearer <token>` 头
- 后端Auth中间件校验JWT，注入user_id到context
- 前端添加未登录重定向逻辑
- 测试完整流程：注册→登录→访问受保护页面→创建项目

### Step 10：种子数据与文档

- 编写 `scripts/seed-db.sh`：创建测试用户（test@example.com / test123456）、示例项目、示例数据
- 更新根 `README.md`：项目简介、架构图（用Mermaid）、快速开始命令、技术栈说明
- 创建 `docs/architecture.md`：包含架构图、技术选型理由（基于Step 1的调研结论）、模块说明
- 创建 `docs/api-design.md`：API设计规范（URL命名、错误码、分页格式、认证方式）
- 创建 `docs/dependencies.md`：登记所有第三方依赖（按00-README要求，含用途/Stars/License/更新日期）

## 代码质量硬性要求

1. **TypeScript**：strict模式开启，禁止any，所有API调用有完整类型
2. **Go**：`golangci-lint run` 必须零警告，所有公开函数有godoc注释，错误必须处理不允许`_`丢弃（除了特殊情况加注释说明）
3. **Python**：`ruff check` 零错误，`mypy --strict` 通过（第三方库无stub的可局部ignore），所有公开函数有docstring（Google风格）
4. **测试**：
   - Go核心service层单元测试覆盖率≥60%
   - Python核心LLM封装层有mock测试
   - 前端工具函数有单元测试（vitest）
5. **配置**：所有硬编码的配置项必须走环境变量/pydantic-settings/viper，不允许代码中出现硬编码的密钥/URL/端口
6. **日志**：所有HTTP请求/Agent执行有结构化日志，包含trace_id，方便排查
7. **错误处理**：错误信息要清晰、有上下文，禁止吞错

## 禁止事项

- ❌ 禁止不调研就直接写（Step 1必须完成并记录结论）
- ❌ 禁止把所有代码塞到一个文件/一个main函数里
- ❌ 禁止使用 `any` 类型（TS）或 `interface{}`（Go）偷懒
- ❌ 禁止在代码中硬编码API Key或密钥
- ❌ 禁止用 `print()` / `fmt.Println` 做日志（必须用结构化日志库）
- ❌ 禁止不写错误处理
- ❌ 禁止前端直接调用LLM API（必须走后端/Agent服务代理）

## 验收标准（交付前必须全部通过）

- [ ] `scripts/setup.sh` 在一个全新macOS/Linux环境下能正常执行（假设已有node/pnpm/go/python/uv/docker）
- [ ] `docker-compose up` 能成功启动所有服务，无报错
- [ ] 访问 http://localhost 能看到前端页面
- [ ] 访问 http://localhost/api/v1/health 返回 `{"code":0,"message":"ok"}`
- [ ] 访问 http://localhost/api/v1/agent/health 返回OK
- [ ] 能完成：注册新用户 → 登录 → 创建一个项目 → 项目列表显示该项目
- [ ] 前端Chat UI能和Agent服务联通，发送消息能收到流式回复（echo测试）
- [ ] `make lint` 三个服务（web/go/python）全部通过
- [ ] `make test` 所有测试通过
- [ ] CI workflow在push时能成功运行
- [ ] 所有文档（architecture.md, api-design.md, dependencies.md）齐全，architecture.md中有GitHub调研结论和选型理由
- [ ] 所有初始数据库表已创建（users/organizations/memberships/projects），迁移可up可down
- [ ] 种子数据脚本可运行，测试账号可登录
