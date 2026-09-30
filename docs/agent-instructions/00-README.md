# 🤖 Mago Agent 平台 — Agent 执行指令集

## 这是什么

本目录包含一套**工程化的Agent执行指令**（Agent Instructions），每一份指令都是一份可直接投喂给通用AI编码Agent（Codex/Cursor/Claude Code/GPT-4o Engineer/Gemini CLI等）执行的"任务合同"。

收到指令的Agent会按照指令要求：
1. **主动调研GitHub**：搜索、阅读、评估开源项目和模块
2. **复用优秀轮子**：能直接用的直接下载/集成/二次开发，不重复造轮子
3. **产出企业级代码**：遵循架构规范、代码规范、测试规范、文档规范
4. **自检验收**：交付前按验收标准自行验证

## 指令清单

| 文件 | 板块 | 依赖 |
|:---|:---|:---|
| [`01-project-bootstrap.md`](./01-project-bootstrap.md) | Phase 0 - 项目初始化与基础设施 | 无 |
| [`02-trend-intelligence.md`](./02-trend-intelligence.md) | 板块一 - 热点情报中心 | 01 |
| [`03-script-studio.md`](./03-script-studio.md) | 板块二 - 脚本创作中心 | 01 |
| [`04-character-style.md`](./04-character-style.md) | 板块三 - 角色与风格管理 | 01,03 |
| [`05-prompt-engine.md`](./05-prompt-engine.md) | 板块四 - 提示词生成引擎（核心） | 01,03,04 |
| [`06-knowledge-base.md`](./06-knowledge-base.md) | 板块五 - 知识与资产底座 | 01 |
| [`07-hitl-workflow.md`](./07-hitl-workflow.md) | 板块六 - 人机协作与交互 | 01,03,04,05 |
| [`08-platform-foundation.md`](./08-platform-foundation.md) | 板块七 - 平台底座（集成/可观测/部署） | 01-07 |
| [`09-orchestrator.md`](./09-orchestrator.md) | 🎯 总聚合调度指令 | 按顺序调度全部 |

## 使用方法

### 给单个Agent（如Codex）执行单个板块
直接把对应的 `.md` 文件内容粘贴/上传给Agent，并告诉它项目根目录路径。Agent会自动完成该板块的所有工作。

```bash
# 示例：让Codex执行项目初始化
cat docs/agent-instructions/01-project-bootstrap.md | pbcopy
# 粘贴给Agent，然后说："按照指令执行，项目根目录是当前目录"
```

### 给多个Agent并行执行
多个Agent可以并行处理无依赖的板块：
- Agent A 执行 `01-project-bootstrap.md`（必须最先完成）
- Agent B 在01完成后执行 `06-knowledge-base.md`（独立板块）
- Agent C 在01完成后执行 `02-trend-intelligence.md`（独立板块）
- Agent D 在01+03+04完成后执行 `05-prompt-engine.md`（有依赖）
- 最后由Orchestrator Agent执行 `09-orchestrator.md` 做集成联调

### 给Orchestrator Agent一次性执行全部
直接把 `09-orchestrator.md` 喂给一个强能力的Agent（推荐GPT-4o/Claude 3.5 Sonnet/Gemini 2.5 Pro级别），它会按照依赖关系依次调度/执行所有板块，并在最后完成集成联调。

## 所有指令通用约定

每份指令都遵循以下统一规范：

1. **角色设定**：明确Agent扮演的角色和能力要求
2. **任务边界**：明确做什么/不做什么
3. **执行步骤**：编号步骤，含GitHub调研环节
4. **GitHub调研要求**：必须搜索关键词、至少评估3个候选方案、选型有书面理由
5. **复用规则**：npm/pip包直接引；优秀脚手架直接fork；单文件工具直接拷贝（注明来源License）；大而全框架谨慎评估后裁剪
6. **代码规范**：ESLint/Black/Ruff/gofmt等语言标准规范，必须有类型标注，必须有docstring/注释
7. **测试要求**：核心逻辑必须有单元测试，API必须有集成测试
8. **文档要求**：每个模块必须有README.md，含架构图、启动命令、API文档
9. **验收标准**：可执行的验收checklist，Agent交付前必须逐项自检通过
10. **禁止闭门造车**：任何非trivial的功能模块，必须先调研GitHub开源方案，优先复用，不允许从零手写

## 技术栈硬约束（所有指令必须遵守）

| 项 | 选型 | 理由 |
|:---|:---|:---|
| 前端 | Next.js 14+ (App Router) + React 18 + TypeScript + TailwindCSS + shadcn/ui | 与Mago主站技术栈统一 |
| 前端流程图 | React Flow | 节点式工作流 |
| 后端主服务 | Go (Gin/Fiber) | 高性能，与Mago技术栈一致 |
| Agent服务 | Python 3.11+ (FastAPI) | LLM生态最成熟 |
| Agent编排 | LangGraph | DAG/状态机/HITL/持久化 |
| LLM统一接口 | LiteLLM (Python) / 自研(Go) | 接入200+模型 |
| 主数据库 | PostgreSQL 16 | 可靠 |
| 缓存 | Redis 7 | 多用途 |
| 向量库 | Milvus / Qdrant | 高性能检索 |
| 对象存储 | MinIO / S3兼容 | 与Mago共享 |
| 视频分析 | FFmpeg + PySceneDetect + OpenCV + Librosa | 成熟工具链 |
| ASR | FunASR / Whisper-large-v3 | 中文最优 |
| 容器化 | Docker + docker-compose (dev) / K8s (prod) | 标准 |
| API风格 | RESTful + OpenAPI 3.0 (Swagger) | 标准 |
| 代码规范 | ESLint+Prettier(前端) / golangci-lint(Go) / Ruff+Black+mypy(Python) | 企业级 |
| 提交规范 | Conventional Commits | 标准 |

## 关键原则

> **不重复造轮子，但也不盲目引入依赖。**
> - 一个功能如果有成熟的、Stars>5k、最近6个月有更新、License友好的开源方案 → 优先复用
> - 一个功能如果只有重量级全家桶框架实现（如需要引入Django只是为了一个CRUD）→ 找轻量替代或自己写
> - 一个功能如果开源方案质量差/年久失修/不符合架构 → 自己实现但参考开源的设计思路
> - 任何引入的第三方依赖必须在 `docs/dependencies.md` 登记，注明用途、Stars数、License、最后更新时间
