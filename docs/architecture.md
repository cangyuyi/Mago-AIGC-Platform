# Mago Agent Platform - 技术架构文档

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js 前端 (apps/web)                                     │
│  · App Router + React Server Components                      │
│  · React Flow (工作流可视化)  · Chat UI (SSE流式)             │
│  · TanStack Query · Zustand · shadcn/ui · Tailwind           │
├─────────────────────────────────────────────────────────────┤
│  Nginx 反向代理 (deploy/nginx)                                │
│  /      → Next.js:3000                                        │
│  /api/ → Go API Gateway:8080                                  │
│  /api/agent/ → Python Agent Service:8000                     │
├─────────────────────────────────────────────────────────────┤
│  Go API Gateway (services/api-gateway)                       │
│  · Gin + GORM + JWT认证 + RBAC                                │
│  · 用户/项目/脚本/分镜/提示词CRUD                              │
│  · 热点/趋势数据管理                                          │
├─────────────────────────────────────────────────────────────┤
│  Python Agent Service (services/agent)                        │
│  · FastAPI + LangGraph 编排                                   │
│  · 8个核心Agent：                                              │
│    - 灵感发散/创意总监/钩子专家/叙事编剧                        │
│    - 文案撰稿/转化专家/分镜师/提示词工程师                      │
│    - 优化师/合规审查/评估Agent                                 │
│  · LiteLLM统一接入多模型                                      │
│  · SSE流式输出                                                │
├─────────────────────────────────────────────────────────────┤
│  基础设施 (docker-compose)                                    │
│  · PostgreSQL 16  · Redis 7  · MinIO                          │
│  · Milvus (向量库) · Langfuse (LLM可观测)                     │
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
Mago-AIGC-Platform/
├── apps/web/                    # Next.js前端
│   └── src/
│       ├── app/                 # 页面路由
│       ├── components/          # 组件
│       └── lib/                 # API客户端/工具函数
├── services/
│   ├── api-gateway/             # Go API网关
│   │   ├── cmd/server/          # 入口
│   │   ├── internal/
│   │   │   ├── config/
│   │   │   ├── handler/
│   │   │   ├── middleware/
│   │   │   ├── model/
│   │   │   ├── repository/
│   │   │   ├── service/
│   │   │   ├── router/
│   │   │   └── pkg/
│   │   └── migrations/          # SQL迁移
│   └── agent/                   # Python Agent服务
│       └── src/
│           ├── api/routes/      # FastAPI路由
│           ├── agents/          # 各Agent实现
│           ├── core/            # LangGraph编排
│           ├── llm/             # LLM网关
│           └── common/
├── packages/shared-types/       # TS共享类型
├── deploy/                      # Docker/Nginx/可观测性配置
├── docs/                        # 文档
└── scripts/                     # 工具脚本
```

## 核心技术选型

### 前端
- **框架**: Next.js 15.5.24 App Router
- **UI**: TailwindCSS + shadcn/ui
- **状态**: Zustand + TanStack Query
- **工作流**: React Flow (@xyflow/react)
- **动效**: Framer Motion
- **Markdown**: react-markdown + remark-gfm

### 后端 - API网关
- **语言**: Go 1.22
- **框架**: Gin
- **ORM**: GORM
- **迁移**: pressly/goose
- **认证**: JWT (golang-jwt/jwt/v5) + bcrypt

### 后端 - Agent服务
- **语言**: Python 3.11+
- **框架**: FastAPI + Uvicorn
- **编排**: LangGraph
- **LLM接入**: LiteLLM (支持OpenAI/Anthropic/Gemini/DeepSeek等)
- **数据校验**: Pydantic v2
- **包管理**: uv

### 基础设施
- **容器**: Docker + Docker Compose（开发及小规模生产）；中大型生产可按本文档和 Compose 配置迁移到 Kubernetes（仓库未提供现成 K8s manifests）
- **数据库**: PostgreSQL 16
- **缓存**: Redis 7
- **对象存储**: MinIO (S3兼容)
- **向量数据库**: Milvus
- **LLM可观测**: Langfuse
- **日志**: Zap (Go) + structlog (Python)
- **监控**: Prometheus + Grafana + OpenTelemetry

## Agent工作流

### 快速模式（一键出片）
```
用户输入 → Ideation(自动选最优) → Script → Storyboard → Prompts → 输出
```

### 精细模式（每个节点人工审核）
```
用户输入 → Ideation → [HITL: 选创意] → CreativeBrief → [HITL: 确认方向]
→ HookDesign → Narrative → Copywriting → CTA → Compliance → Eval
→ [HITL: 审核脚本] → Storyboard → [HITL: 逐镜修改]
→ PromptGeneration → QA → [HITL: 最终确认] → 推送到Mago
```
