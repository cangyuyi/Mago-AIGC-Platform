# 开源发布清单

本文用于把 Mago Agent 工作台发布给其他人使用。它记录当前代码检查结果、已知限制和发布前必须完成的事项。

> 状态更新时间：2026-09-17

## 当前可发布性结论

代码层面的静态检查已经完成：

- Web：TypeScript、ESLint、Next.js standalone build 已通过。
- Go API：`go test ./...`、`go vet ./...`、`go build` 已通过。
- Python Agent：Ruff、mypy、pytest（当前 47 个测试）已通过；Redis `.env` 配置读取已补回归测试。
- Shell：启动、迁移、备份脚本已通过 `bash -n`。

仍不能宣称“完整生产验收通过”：当前验证机没有 Docker daemon 和 Nginx，因此 Docker Compose 实际启动、镜像构建、迁移容器执行、HTTPS/Nginx 反向代理以及完整多服务 E2E 尚未验证。

本轮继续审查还修复了：Go API 的分页 Count 错误传播、提示词包删除事务、故事板跨项目脚本引用校验、严格趋势 limit 解析；Agent 进度异步任务的 mypy 类型问题、Redis 客户端显式使用 Pydantic Settings 解析后的 `redis_url`，以及视频下载日志中的 URL/签名信息泄露。Milvus 初始化脚本现在不依赖当前工作目录，并支持通过 `MILVUS_HOST`/`MILVUS_PORT` 指定连接地址；生产 Compose overlay 现在强制要求显式配置 `ALLOWED_ORIGINS`，Go 启动校验还会拒绝空白/逗号占位和通配符来源。前端生产依赖在线审计通过，234 个生产依赖未报告漏洞。

## 最近一轮安全与可用性修复

- 提示词包创建和 Prompt 批量写入现在会验证 Project → Storyboard → Shot 的归属链，阻止跨项目资源引用。
- 视频下载器在调用 yt-dlp 前会拒绝解析到非公网地址的 URL，并且日志只保留主机名，不记录凭据、查询参数或签名 URL。
- Go API 已允许链路使用的 `X-Request-ID` CORS 请求头；资源不存在和无权访问统一按 404 处理，内部数据库错误按 500 处理。
- Nginx 开发、生产和遗留配置均覆盖 Agent 专用 API 根路径的无尾斜线形式。
- 本轮 Agent 回归测试为 47 个通过，Go `test/vet/build` 通过；Web 的 TypeScript、ESLint 和 Next.js 15.5.24 standalone build 已通过，生产依赖树已固定到 PostCSS 8.5.28。由于本机没有 Docker、Nginx、FFmpeg 和 Redis CLI，真实部署联调仍需在具备这些依赖的机器上完成。

## 发布阻塞项

### 1. 先确定许可证

根目录 `LICENSE` 目前包含：

- 标准 MIT 条款；
- 额外中文说明，试图排除商业服务端、业务逻辑、品牌和同类竞品使用。

这两部分不能被当作一个清晰、无冲突的标准 MIT 许可证。发布前必须由项目所有者选择并落实一种方案：

1. 对确实要开放的代码使用完整、标准的 MIT（删除冲突的附加限制）；
2. 只对明确的目录/文件采用 MIT，并把商业代码移出仓库；
3. 采用经过法律审核的自定义许可证；
4. 使用经过法律审核的双许可证。

在选择完成前，README 不应继续只写“MIT”。

### 2. 固定容器镜像版本

开发 Compose 仍包含 `minio/minio:latest` 和 `milvusdb/milvus:v2.4-latest`，这两个浮动标签在开源发布前应在具备 Docker 的环境中验证并固定为明确版本或 digest。此前的单容器 `langfuse/langfuse:latest` 已从 Compose 移除：当前 Langfuse self-hosted 需要按官方多容器方案单独部署，避免默认启动流程因不完整配置失败。

### 3. Agent 项目权限边界

带有 `project_id` 的 Agent 请求在认证模式下会使用原始 Bearer Token 回查 Go API 的项目详情，只有项目所有者才能继续执行。生产部署必须让 Agent 设置可访问 Go API 的 `MAGO_API_URL`，并与 Go API 使用同一 `JWT_SECRET`；开发模式关闭 Agent JWT 时，项目校验也不会提供生产级隔离。

### 4. 后台任务运行方式

趋势抓取和视频分析已经接入 Redis/ARQ 持久队列，开发 Compose 和生产 overlay 都包含独立的 `agent-worker` 服务。生产环境在 Redis/Worker 不可用时会返回 503，不会静默退回 API 进程内任务；只有开发/测试模式允许使用 FastAPI `BackgroundTasks` 作为离线回退。

仍需在具备 Docker 的机器上验证队列重启、重复提交、Worker 重启和多副本状态轮询，确认实际部署参数与 Redis ACL/密码配置一致。

### 5. LangGraph HITL 状态持久化限制

当前 LangGraph 使用进程内 `MemorySaver`，并通过 `user_id:project_id` 线程 ID 做用户/项目隔离。这能支持单进程开发和短期交互，但 Agent 进程重启后 HITL 断点会丢失，也不适合多副本共享状态。要承诺生产级断点续跑，需要接入 PostgreSQL/Redis checkpointer 并补充恢复测试；在此之前，生产部署应把该能力视为有限支持。

## 发布前检查

在一台安装 Docker Desktop、Nginx 和 FFmpeg 的干净机器上执行：

```bash
cp .env.example .env
# 编辑 .env，填写 LLM key、随机 JWT_SECRET 和生产密码

docker compose config
docker compose build
docker compose up -d
docker compose ps

# 如果使用生产 overlay
docker compose -f docker-compose.yml -f docker-compose.prod.yml config

# 在宿主机或 Nginx 容器中验证配置
nginx -t

# 应用级冒烟测试
# 1. 注册并登录
# 2. 创建项目并读取项目
# 3. 发起 Chat SSE 请求，确认流式结束事件和鉴权
# 4. 请求趋势、选题推荐和 viral analyze 接口
# 5. 重启 API/Agent，确认数据库数据和任务状态符合预期
```

## 密钥与仓库卫生

- 只提交 `.env.example`，不要提交 `.env`、Cookie、API key、JWT secret、证书私钥或生产日志。
- 发布前执行一次 secrets scan，并人工检查截图、示例 JSON、日志和历史提交。
- `DOUYIN_COOKIE` 只通过环境变量注入。
- 生产环境必须使用至少 32 个字符的随机 `JWT_SECRET`，并让 Go API 与 Agent 使用同一值。
- 修改默认 PostgreSQL、Redis、MinIO、Grafana 密码；不要直接复用示例密码。

## 第三方依赖

发布前需要为 Go、Python、Node、Docker 镜像和前端字体/图标等依赖生成许可证清单，并确认依赖许可证与最终选择的项目许可证兼容。对于平台抓取能力，还要确认各数据源的服务条款、版权和隐私要求；“代码开源”不等于可以任意抓取或再分发平台内容。

## 不能跳过的人工确认

- 许可证方案和商标/品牌使用范围；
- 是否公开商业服务端、计费逻辑和 Mago 平台集成凭据；
- Docker/Nginx/HTTPS 实机验证结果；
- 任务队列在重启、重复提交和多副本场景下的行为；
- 数据源抓取的合规边界。
