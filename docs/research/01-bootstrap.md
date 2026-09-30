# 01-项目初始化 GitHub调研结论

## 调研时间：2026-09-07

---

## 1. Monorepo管理方案

### 评估候选

| 方案 | Stars | 适用场景 | 评估 |
|:---|:---|:---|:---|
| **pnpm workspace** | 30k+ | 轻量、Node生态原生 | ✅ **选择** - 前端用pnpm workspace管理，Go/Python各自管理，根目录Makefile统一调度。简单够用，无需额外学习成本 |
| Turborepo | 26k+ | 大型Monorepo构建缓存 | ⚪ 可选 - 后续项目大了引入，初期pnpm workspace足够 |
| Nx | 24k+ | 企业级Monorepo，插件丰富 | ❌ 过重 - 功能太多学习曲线陡，我们是混合栈(Go/Python/TS)，Nx主要服务JS/TS |

**决策**：pnpm workspace管理前端workspace包，Go和Python各用自己的模块管理（go.mod / pyproject.toml），根目录Makefile提供统一命令入口。

### 参考项目
- `pnpm/pnpm` 官方workspace文档
- `vercel/turborepo/examples/basic` - 参考其pnpm workspace配置方式
- `belgattitude/nextjs-monorepo-example` (8k+ stars) - 参考其tsconfig和eslint配置

---

## 2. Next.js + shadcn/ui + Tailwind 初始化

### 评估候选

| 方案 | Stars | 评估 |
|:---|:---|:---|
| **shadcn/ui + Next App Router** | 80k+ | ✅ **选择** - 2026年企业级SaaS标配，组件可直接复制到项目中定制，不锁定版本 |
| ixartz/SaaS-Boilerplate | 5.8k+ | 参考其landing/dashboard布局设计，不直接fork（依赖太重） |
| shadcn-ui/taxonomy | 参考阅读体验设计，不直接使用 |
| next-auth/next-auth-example | 参考Auth集成方式 |

### 关键决策
- Next.js 14 App Router + Server Components + Client Components合理分离
- TailwindCSS v3 + shadcn/ui (最新版) + lucide-react图标
- 暗色模式用 next-themes
- 表单：react-hook-form + zod
- 数据请求：@tanstack/react-query
- 状态管理：zustand（轻量，避免Redux复杂性）
- 流程图：reactflow（xyflow/react）
- Markdown渲染：react-markdown + remark-gfm + rehype-highlight

---

## 3. Go + Gin 企业脚手架

### 评估候选

| 组件 | 选型 | Stars | 理由 |
|:---|:---|:---|:---|
| Web框架 | **Gin** | 77k+ | 生态最成熟、性能优秀、中间件丰富、Mago团队已有经验 |
| ORM | **GORM** | 36k+ | 开发效率高、关联查询方便、自动迁移，适合初期快速迭代 |
| 数据库迁移 | **goose** | 5.8k+ | SQL原生、支持up/down、CLI简单、不绑定ORM |
| 配置管理 | **viper** | 28k+ | 支持多格式、环境变量覆盖、热重载 |
| 日志 | **zap** | 21k+ | 高性能结构化日志、uber出品 |
| JWT | **golang-jwt/jwt/v5** | 20k+ | 标准JWT库 |
| 参数校验 | **go-playground/validator** | 17k+ | Gin生态默认 |
| 项目布局 | **golang-standards/project-layout** | 48k+ | 社区标准 |

**不选Fiber的理由**：虽然Fiber性能略高但Gin生态更成熟、文档更多、团队更熟悉，性能差异在我们的场景（不是超高QPS API网关）不重要。

**不选sqlc的理由**：sqlc类型安全但开发速度慢，初期优先开发速度选GORM，后续性能热点再迁移。

### 目录结构（遵循Standard Go Project Layout + Clean Architecture）
```
services/api-gateway/
├── cmd/server/main.go       # 入口
├── internal/                # 私有代码（不可被外部导入）
│   ├── config/              # 配置
│   ├── handler/             # HTTP handlers (controller层)
│   ├── middleware/           # Gin中间件
│   ├── model/               # GORM models/请求响应DTO
│   ├── repository/           # 数据访问层
│   ├── service/              # 业务逻辑层
│   ├── router/               # 路由注册
│   └── pkg/                  # 内部公共包
├── migrations/               # SQL迁移文件
├── api/                      # OpenAPI/Swagger
└── go.mod
```

---

## 4. FastAPI + LangGraph 项目结构

### 评估候选

| 组件 | 选型 | Stars | 理由 |
|:---|:---|:---|:---|
| Web框架 | **FastAPI** | 78k+ | 异步支持、自动文档、Pydantic集成 |
| Agent编排 | **LangGraph** | 10k+ | 状态图/DAG/HITL/持久化/断点续跑，最适合生产Agent编排 |
| LLM统一接口 | **LiteLLM** | 18k+ | 200+模型统一调用、Cost追踪、FallBack、支持Langfuse |
| 依赖管理 | **uv** | 30k+ | Rust写的极速Python包管理器，比pip/poetry快10-100倍 |
| 配置 | pydantic-settings | - | Pydantic v2官方配置库 |

**不选CrewAI/AutoGen的理由**：
- CrewAI适合快速原型但生产级可控性差，调试困难
- AutoGen更偏向研究和多Agent对话，不适合线性DAG工作流
- LangGraph的StateGraph + Checkpointer + Interrupt机制是生产级Agent编排的最佳选择

### 关键设计
- LangGraph StateGraph 用 PostgreSQL 做 checkpointer（持久化+断点续跑）
- 流式输出用 SSE (Server-Sent Events)，比WebSocket简单且兼容HTTP生态
- Agent之间通过依赖注入共享LLM Gateway、Knowledge Retriever等服务
- 每个Agent节点是独立的async函数，接收State返回State update

---

## 5. Docker Compose 本地开发

### 服务清单
| 服务 | 镜像 | 端口 | 说明 |
|:---|:---|:---|:---|
| postgres | postgres:16-alpine | 5432 | 关系数据库+pgvector |
| redis | redis:7-alpine | 6379 | 缓存/会话/消息队列 |
| minio | minio/minio | 9000/9001 | 对象存储（S3兼容） |
| milvus | milvusdb/milvus (standalone) | 19530 | 向量数据库（依赖etcd+minio） |
| etcd | quay.io/coreos/etcd | 2379 | Milvus依赖 |
| langfuse | langfuse/langfuse | 3000 | LLM可观测性（Phase 0可选） |
| api-gateway | 本地build | 8080 | Go服务 |
| agent | 本地build | 8000 | Python服务 |
| web | 本地build | 3000 | Next.js前端 |
| nginx | nginx:alpine | 80 | 反向代理 |

Milvus standalone需要注意：v2.4+ standalone已经内嵌etcd和minio，配置简化。

---

## 6. 前端依赖清单（确定）

```json
{
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "@radix-ui/react-*": "shadcn按需",
    "lucide-react": "^0.400.0",
    "next-themes": "^0.3.0",
    "react-hook-form": "^7.52.0",
    "@hookform/resolvers": "^3.9.0",
    "zod": "^3.23.0",
    "@tanstack/react-query": "^5.50.0",
    "zustand": "^4.5.0",
    "@xyflow/react": "^12.0.0",
    "framer-motion": "^11.3.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "rehype-highlight": "^7.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.4.0",
    "class-variance-authority": "^0.7.0"
  },
  "devDependencies": {
    "@types/node": "^20.14.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "eslint": "^8.57.0",
    "eslint-config-next": "^14.2.0",
    "prettier": "^3.3.0",
    "prettier-plugin-tailwindcss": "^0.6.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

## 7. Go依赖清单（确定）

```
github.com/gin-gonic/gin v1.10.0
gorm.io/gorm v1.25.0
gorm.io/driver/postgres v1.5.0
github.com/spf13/viper v1.19.0
go.uber.org/zap v1.27.0
github.com/golang-jwt/jwt/v5 v5.2.0
github.com/go-playground/validator/v10 v10.22.0
github.com/pressly/goose/v3 v3.22.0
github.com/gin-contrib/cors v1.7.0
golang.org/x/crypto v0.25.0 (bcrypt)
github.com/google/uuid v1.6.0
```

## 8. Python依赖清单（确定）

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-anthropic>=0.2.0
litellm[proxy]>=1.50.0
pydantic>=2.9.0
pydantic-settings>=2.6.0
python-dotenv>=1.0.0
httpx>=0.27.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
jinja2>=3.1.0
python-multipart>=0.0.9
```
