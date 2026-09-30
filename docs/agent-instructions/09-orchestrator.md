# 指令 09：🎯 总聚合调度指令（Orchestrator Master Plan）

## 角色设定

你是一个**首席架构师+技术负责人（Tech Lead）**，收到本指令意味着你要负责**整体交付Mago Agent创意平台**。你的职责是：
1. 理解全局架构和所有板块的依赖关系
2. 按正确的顺序调度执行各板块指令（01~08）
3. 在每个板块完成后做验收检查，不通过则返工
4. 解决板块间的集成问题
5. 最终交付一个可运行、可演示、企业级质量的完整产品

## 项目根目录

```
<repo-root>/
```

你必须在该目录下工作，已有的README.md/docs/screenshots保留。

## 全局技术栈约束（所有板块必须遵守）

- **前端**：Next.js 14+ (App Router) + React 18 + TypeScript strict + TailwindCSS + shadcn/ui + React Flow + framer-motion + TanStack Query + Zustand
- **API网关**：Go 1.21+ with Gin/Fiber + GORM + go-redis
- **Agent服务**：Python 3.11+ with FastAPI + LangGraph + LiteLLM + Pydantic v2 + uvicorn
- **数据库**：PostgreSQL 16 + Redis 7 + Milvus (向量) + MinIO (对象存储)
- **消息队列**：arq（基于Redis，适合Python/asyncio）或 asynq（Go端）
- **可观测**：OpenTelemetry + Prometheus + Grafana + Loki + Tempo + Langfuse（LLM可观测）
- **容器化**：Docker + docker-compose（开发）+ K8s（生产）
- **CI/CD**：GitHub Actions
- **代码规范**：ESLint+Prettier(前端) / golangci-lint(Go) / Ruff+mypy(Python)
- **提交规范**：Conventional Commits

## 执行总路线图

各板块依赖关系：

```
01-项目初始化 ─────┬──→ 02-热点情报 ────┐
                  ├──→ 03-脚本创作（创意核心）──┬──→ 05-提示词引擎（输出核心）──┐
                  ├──→ 04-角色风格 ────────────┤                            │
                  └──→ 06-知识底座 ────────────┴────────────────────────────┤
                                                                             │
                  ─────────────────────────────→ 07-人机交互前端 ─────────────┤
                                                                             │
                  所有板块完成 ────→ 08-平台集成 ─────────────────────────────┘
```

**并行化建议**：
- **Wave 1（必须先完成）**：01-项目初始化
- **Wave 2（01完成后并行）**：02/03/04/06 四个板块可并行（分配4个Agent，每个负责一个板块）
  - 03-脚本创作和04-角色风格有类型定义依赖，提前在01中定义好共享类型
  - 06-知识底座是其他板块依赖的检索服务，优先完成基础Embedding和检索接口
- **Wave 3（03+04+06完成后）**：05-提示词引擎（依赖分镜数据/角色卡/风格卡/知识库）
- **Wave 4（Wave 2+3并行进行）**：07-前端（可先用mock数据开发，后端完成后联调）
- **Wave 5（所有板块功能完成）**：08-平台集成、联调、可观测、部署、测试、文档

## 执行步骤

### Step 0：项目准备

在动手做任何板块之前：

1. **通读所有指令文档**：
   - `docs/05-agent-platform-execution-plan.md`（完整执行计划）
   - `docs/agent-instructions/00-README.md`（指令集规范）
   - `docs/agent-instructions/01-project-bootstrap.md` ~ `08-platform-foundation.md`（所有板块指令）
   - 现有项目代码：`README.md`, `docs/*.md`, `.github/` 等，理解已有Mago平台的产品定位和技术风格

2. **确认环境**：
   - 检查本地开发环境：Node 20+, pnpm 9+, Go 1.21+, Python 3.11+, uv, Docker/Docker Desktop
   - 确认Git状态，当前在哪个分支（创建 `feature/agent-platform` 分支进行开发）
   - 检查Docker资源分配（至少8GB RAM用于Milvus+PG+Redis+MinIO+Langfuse）

3. **创建基础分支**：
   ```bash
   cd <repo-root>
   git checkout -b feature/agent-platform
   ```

### Step 1：执行 01-项目初始化

按 `docs/agent-instructions/01-project-bootstrap.md` 严格执行：

1. 先完成Step 1调研（pnpm/Turborepo/Go脚手架/FastAPI+LangGraph调研），将结论写入 `docs/research/01-bootstrap.md`
2. 按目录结构创建Monorepo骨架
3. 初始化前端（Next.js+shadcn+Tailwind）
4. 初始化Go API Gateway（Gin+GORM+JWT+migrations）
5. 初始化Python Agent服务（FastAPI+LangGraph+LiteLLM）
6. 启动docker-compose，确保PG/Redis/MinIO/Milvus全部启动
7. 实现用户认证+项目CRUD基础API
8. 前端登录页+Dashboard+Chat UI基础版
9. CI/CD配置
10. 跑通基础E2E：注册→登录→创建项目→Chat对话（echo测试Agent）

**01验收Checklist**（逐项验证通过才进入下一步）：
- [ ] `docker-compose up` 所有服务healthy
- [ ] `make dev` 三个服务（web/api/agent）启动无报错
- [ ] `http://localhost` 能看到前端首页
- [ ] `http://localhost/api/v1/health` 返回 `{"code":0}`
- [ ] 能注册、登录、创建项目
- [ ] Chat UI发消息能收到Agent流式回复
- [ ] `make lint` 三个服务lint全过
- [ ] `make test` 已有测试全部通过
- [ ] `docs/architecture.md` 和 `docs/dependencies.md` 存在且内容完整
- [ ] `docs/research/01-bootstrap.md` 调研结论存在

### Step 2：并行执行Wave 2（02/03/04/06）

**建议方式**：如果只有一个Agent执行，则按以下顺序：06(知识底座) → 03(脚本) → 04(角色风格) → 02(热点情报)。如果可以启动多个Agent并行，按以下分配：

- **Agent A → 06-知识底座**（最先启动，其他板块依赖其检索接口）
- **Agent B → 03-脚本创作中心**（创意核心，工作量最大）
- **Agent C → 04-角色与风格**
- **Agent D → 02-热点情报中心**

每个Agent执行对应指令文件（从Step 1调研开始，按文档步骤执行）。

**并行开发注意事项**：
- 共享的Pydantic/TypeScript类型定义先在01中定义好（在`packages/shared-types`和Python的`src/common/types.py`中），避免冲突
- 各服务通过REST API解耦，不直接跨服务import
- 数据库migration文件命名加前缀（如 `000010_create_trend_topics.up.sql`），避免版本号冲突
- 每天合并/同步主分支，解决冲突

**每个板块验收通过后**，在本文件末尾的"进度看板"中标记完成。

### Step 3：执行 05-提示词引擎（核心输出）

等03+04+06完成后执行05：

1. 先做调研（Step 1），重点是每个模型的官方文档和社区最佳实践
2. 创建数据库表和Milvus的prompt_knowledge集合
3. 构建专业术语词典（300+条）
4. 编写12个模型的配置文件和模板
5. 实现提示词组装核心引擎（7步组装流水线）
6. 实现一致性策略
7. 实现质量评分+优化Agent
8. 实现导出+Mago推送
9. 完成前端提示词工作台（在07的基础上对接）
10. 测试！测试！测试！尤其是真人抽检环节

**05特别强调**：这是平台的**最终交付物**，提示词质量决定用户是否真的能用。必须花时间打磨每条prompt模板、每个negative词、每个参数建议。**不要让这个板块沦为"套模板拼字符串"的垃圾代码**——要达到"资深Prompt工程师手工调优"的水准。

### Step 4：执行 07-人机交互与前端

可以在Wave 2进行中并行开发前端（用mock数据），等05完成后做真实API联调：

1. 先完成设计系统和基础组件库
2. 实现Chat对话引擎（最高优先级，因为是核心交互）
3. 实现工作流可视化画布（React Flow）
4. 实现各业务页面（灵感/脚本/分镜/提示词/角色/风格/知识库）
5. WebSocket实时通知
6. HITL审核面板
7. 快捷键/命令面板
8. 动效和微交互
9. 错误处理/空状态/加载状态
10. 响应式和暗色模式

**前端验收重点**：
- 交互流畅不卡顿
- 流式输出无闪烁无跳动
- 所有AI输出有清晰的loading/error/empty状态
- 自然语言修改功能真正能用（不是摆设）
- 提示词卡片的Mago闭环（推送→进度→结果→优化）完整

### Step 5：执行 08-平台集成与部署

所有功能模块完成后进入集成阶段：

1. 串联LangGraph总流程图（精细模式+快速模式）
2. 打通服务间通信
3. 部署可观测栈（Langfuse+OTel+Prometheus+Grafana+Loki+Tempo）
4. 安全加固
5. 性能优化（缓存/异步/模型路由/CDN）
6. Mago正式集成（SSO+API+回调+数据回流）
7. 完善测试（单元+集成+E2E+负载）
8. 生产Docker/K8s配置
9. 备份与恢复
10. 文档完善

### Step 6：端到端验收与交付

所有板块完成后，执行完整的验收流程：

1. **全新环境部署验证**：在一台干净的机器/虚拟机上跑 `scripts/setup.sh`，验证从零到运行无人工干预
2. **Happy Path全流程走通**（至少5个不同垂类的测试用例）：
   - 用例1：用户输入"想做个美妆口红种草视频，目标30秒，抖音9:16"
   - 用例2：用户直接粘贴一条爆款URL"帮我分析并模仿这条视频做一条类似的"
   - 用例3：快速模式："帮我做一个iPhone开箱评测视频，60秒，B站风格"
   - 用例4：用户有明确角色"用我创建的'小美'这个角色，做一个职场穿搭分享"
   - 用例5：多模型输出"这个分镜帮我适配MJ+Kling+Runway三个版本"
3. **提示词真人评审**：随机抽20条产出的提示词，按A/B/C/D评级，要求A≥60%, A+B≥90%, 无D
4. **性能测试**：k6压测500并发核心API达标
5. **故障演练**：手动停掉LLM API/Redis，验证降级和错误处理
6. **Bug Bash**：组织2-3小时集中测试，记录bug并修复P0/P1
7. **演示视频/截图**：录一段3-5分钟完整产品demo视频，更新README.md

### Step 7：交付产物清单

交付时必须包含：

```
Mago-AIGC-Platform/
├── README.md                        # 更新后的README（含架构图、快速开始、截图）
├── docker-compose.yml               # 开发环境
├── docker-compose.prod.yml          # 生产环境
├── Makefile                         # 常用命令
├── .env.example                     # 环境变量模板
├── .github/workflows/ci.yml         # CI配置
├── CHANGELOG.md                     # 变更记录
├── docs/
│   ├── architecture.md              # 架构文档（含Mermaid图）
│   ├── api-design.md                # API规范
│   ├── deployment.md                # 部署文档
│   ├── troubleshooting.md           # 排错手册
│   ├── security.md                  # 安全说明
│   ├── dependencies.md              # 第三方依赖登记
│   ├── research/                    # 所有板块的GitHub调研报告
│   │   ├── 01-bootstrap.md
│   │   ├── 02-trend-intelligence.md
│   │   ├── 03-script-studio.md
│   │   ├── 04-character-style.md
│   │   ├── 05-prompt-engine.md
│   │   ├── 06-knowledge-base.md
│   │   ├── 07-hitl-workflow.md
│   │   └── 08-platform-foundation.md
│   └── agent-instructions/          # 本指令集
├── apps/
│   └── web/                         # Next.js前端（完整实现）
├── services/
│   ├── api-gateway/                 # Go API网关（完整实现）
│   │   ├── cmd/server/main.go
│   │   ├── internal/(handler/middleware/service/repository/config/model/pkg)
│   │   ├── migrations/              # 所有数据库迁移文件
│   │   └── api/openapi.yaml
│   └── agent/                       # Python Agent服务（完整实现）
│       ├── src/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── api/
│       │   ├── agents/              # 8个Agent完整实现
│       │   │   ├── trend/
│       │   │   ├── script/
│       │   │   ├── character/
│       │   │   ├── style/
│       │   │   └── prompt/
│       │   ├── core/                # LangGraph编排
│       │   ├── crawlers/            # 爬虫
│       │   ├── video_tools/         # 视频处理
│       │   ├── knowledge/           # 知识库
│       │   │   ├── ingestion/
│       │   │   ├── retrieval/
│       │   │   └── presets/         # 预置JSON知识（钩子/结构/角色/风格等）
│       │   ├── llm/                 # LLM网关/Prompt模板
│       │   ├── prompt_engine/       # 提示词组装引擎
│       │   └── common/
│       └── tests/                   # 测试
├── packages/
│   ├── shared-types/                # 共享TS类型
│   └── shared-protos/
├── deploy/
│   ├── docker/                      # 各服务Dockerfile
│   ├── k8s/                         # K8s部署清单（可选但推荐）
│   └── nginx/
└── scripts/
    ├── dev.sh
    ├── setup.sh
    ├── seed-db.sh
    ├── init_milvus.py
    ├── init_knowledge.py
    └── backup.sh
```

## 全局质量红线（所有板块必须遵守）

以下是**绝对不能妥协**的质量要求：

1. ❌ **禁止硬编码API Key或密钥**（全部走环境变量）
2. ❌ **禁止吞掉错误**（所有error必须处理或log）
3. ❌ **禁止用any类型**（TS strict模式，Go禁止interface{}）
4. ❌ **禁止在循环中发SQL/LLM请求**（用batch/批量接口）
5. ❌ **禁止裸println/print打日志**（必须用结构化日志）
6. ❌ **禁止前端直接调用LLM API**（必须走后端）
7. ❌ **禁止生成"看起来完整但实际不能用"的代码**（要写就写能跑的，写placeholder要明确标记TODO+负责人）
8. ❌ **禁止抄袭开源项目后不注明来源**（在docs/dependencies.md登记）
9. ❌ **禁止用LLM生成不验证的SQL/Docker/Shell命令**（必须实际运行验证）
10. ❌ **禁止Prompt模板写"生成一个高质量视频"这种废话**（每个Prompt必须有具体结构、术语、负面词、参数）
11. ✅ **每个公共函数必须有docstring/godoc/TSDoc**
12. ✅ **每个数据模型必须有明确的类型定义（Pydantic/TypeScript/Go struct）**
13. ✅ **每个模块必须有README说明其职责和用法**
14. ✅ **每个API必须有错误处理和参数校验**
15. ✅ **每次提交必须能通过lint**

## 进度看板

执行过程中在此处更新进度：

| 板块 | 状态 | 负责人 | 完成时间 | 备注 |
|:---|:---|:---|:---|:---|
| 00-指令集编写 | ✅ 完成 | Codex | 2026-09-07 | 9份指令文件共~5000行 |
| 01-项目初始化 | ⬜ 待开始 | - | - | |
| 02-热点情报 | ⬜ 待开始 | - | - | |
| 03-脚本创作（核心） | ⬜ 待开始 | - | - | |
| 04-角色风格 | ⬜ 待开始 | - | - | |
| 05-提示词引擎（核心） | ⬜ 待开始 | - | - | |
| 06-知识底座 | ⬜ 待开始 | - | - | |
| 07-人机交互前端 | ⬜ 待开始 | - | - | |
| 08-平台集成 | ⬜ 待开始 | - | - | |
| E2E验收 | ⬜ 待开始 | - | - | |

## 开始执行

现在，按以下顺序启动：

1. 先让第一个Agent（或你自己）执行 `01-project-bootstrap.md`
2. 01通过验收后，并行启动03/04/06三个板块（02可以稍后或并行，依赖最少）
3. 每完成一个板块，更新上面的进度看板，提交代码
4. 遇到阻塞问题（某板块前置依赖未完成/技术难点），记录阻塞原因，先做不阻塞的部分
5. 遇到所有指令未覆盖的决策点（如特定技术选型的分歧），遵循以下优先级：
   - 与Mago已有技术栈一致 → 优先
   - 企业级成熟度/社区活跃度 → 其次
   - 团队熟悉度/开发效率 → 再次
   - 新技术尝鲜 → 最低优先级（除非有明确收益）

**记住目标**：让一个没有灵感的创作者打开平台，10分钟内拿到一套可以直接生成爆款视频的专业提示词包。所有技术决策都围绕这个目标。

**祝建造顺利。** 🚀
