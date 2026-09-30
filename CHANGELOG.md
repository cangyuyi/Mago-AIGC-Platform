# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> 说明：`0.1.0` 之前的历史提交没有拆分版本号，统一归入下面的条目；此后每次对外发布都应新增一个版本段落。

## [未发布]

### 新增 — 输出能力（本轮核心）

- **提示词包引擎上线到工作台**：分镜生成后可直接勾选目标模型（Sora / Runway / 可灵 / 即梦 / Vidu / Pika / CogVideoX / 海螺 / 通义万相 / Midjourney / SDXL / DALL·E 3 / Flux / 混元 等 14 个），一键产出每个镜头的**正向提示词 + 负向提示词 + 可直接照抄的参数**（宽高比、时长、seed、`--ar`/`--no` 语法）。
- `POST /api/v1/agent/prompt-pack`、`GET /api/v1/agent/prompt-models`：不依赖数据库、不消耗任何模型额度，纯本地模板引擎，离线可用。
- 前端 `PromptPackPanel`：按镜头分组折叠、逐条复制、整包导出为 **Markdown / CSV / JSON / 纯文本** 四种格式。
- 词表归一层 `src/prompt_engine/normalize.shot_size/camera_angle/...`：中英文标签、别名词、Agent 自由文本都能落到规范键；无法识别的值保留原文并给出 warning，不再静默丢弃。

### 修复

- 提示词引擎：取景描述在英文模板里被重复整句、视频模型重复运动描述、灯光/色调/转场字段中文泄漏到英文提示词、`duration` 恒为 0、宽高比从不落到参数、缺少 CJK 告警等 7 个真实缺陷。
- `LLMGateway` 在 Agent 路由中未导入即使用（运行到该分支必然 NameError）。
- 前端读取分镜场景字段时用了 `scene_environment`，而 Agent 输出的是 `scene_description`，导致场景列永远显示「未指定」；导出表格与镜头表同样受影响。
- 选题标题重复拼接（「第一视角记录第一视角记录口红测评…」）。
- `make test-api` 在 `CGO_ENABLED=0` 下带 `-race`，在没有 C 工具链的机器上必定失败；拆分为 `test-api` 与 `test-api-race`。
- `make test`（含 `test-web`）此前不运行任何前端测试，只跑 typecheck + lint；现改为真实执行 vitest。
- `.github/workflows/ci.yml` 前端 job 不跑单测；新增 `pnpm test`、数据库迁移可回滚校验、Dockerfile 构建冒烟。

### 新增 — 可自助部署

- `scripts/doctor.sh`（`make doctor`）：只读体检，逐条告诉你缺什么、怎么补，并区分「真阻塞」和「可绕过」。
- `scripts/demo.sh`（`make demo`）：无 Docker、无数据库，一条命令拉起 Agent + 前端跑通主链路。
- `docker-compose.min.yml` + `make docker-min`：只起 Postgres / Redis / MinIO，省掉 Milvus + etcd 约 4GB 内存。
- `make setup-env`：从 `.env.example` 生成 `.env`（已存在则不覆盖）。
- 文档：`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`packages/*/README.md`。

## [0.1.0] — 2026-09-17

### 首个可运行版本

- 三服务架构：Next.js 15 工作台 + Go 1.22 API 网关 + Python 3.11/FastAPI Agent 服务。
- LangGraph 17 节点创作流程：热点研究 → 创意发散 → 简报 → 钩子 → 脚本 → 质检回环 → 合规 → 节奏 → 分镜 → 分镜质检 → 提示词 → 导出（含人工确认断点）。
- Go API：认证（JWT + 刷新）、项目/脚本/分镜/镜头/提示词包 CRUD、限流、请求体大小限制、安全响应头、资源归属校验。
- 数据层：PostgreSQL 16 + Goose 迁移（6 组 up/down）、Redis 7 + ARQ 后台队列、MinIO 对象存储、Milvus 向量检索。
- 可观测：OpenTelemetry、Prometheus、Loki、Tempo、Grafana 预置看板。
- 离线演示模式：`NEXT_PUBLIC_DEMO_MODE=true` 时前端使用浏览器本地数据跑通全部页面。
