# 安全策略

## 报告漏洞

**不要公开提 Issue。** 请使用 GitHub 的 [Private vulnerability reporting](https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)（仓库首页 → Security → Report a vulnerability），或发邮件给维护者（邮箱见仓库主页）。

我们会在 3 个工作日内确认，并在 30 天内给出修复计划或说明拒绝理由。欢迎随报告附上复现命令/请求包。

## 支持版本

| 版本 | 支持状态 |
|:---|:---|
| `main`（未发布） | ✅ 安全修复在此分支 |
| `< 0.1.0` | ❌ 不再单独回溯修复 |

## 已落地的防护措施

**传输与入口**
- 全局安全响应头（`X-Content-Type-Options`、`X-Frame-Options`/CSP frame-ancestors、Referrer-Policy 等）· Gin 中间件
- CORS 白名单：`ALLOWED_ORIGINS` 必填且校验，生产 Compose 拒绝通配符、空白与逗号占位
- 请求体大小上限 10 MB（`internal/middleware/request_size.go`）
- 分层限流：登录/注册按 IP+账号防爆破，其余写接口按用户限流（`internal/middleware/rate_limiter.go`）
- Nginx 开发/生产配置覆盖所有 Agent API 根路径，Agent 在 Compose 内部网络不直接对外发布

**认证与授权**
- JWT access + refresh（`JWT_ACCESS_TTL_MINUTES` / `JWT_REFRESH_TTL_DAYS`），生产要求 `JWT_SECRET` ≥32 位随机
- 所有按 ID 访问的读写走 `*Owned` 仓储方法校验属主；不存在与无权统一返回 404，避免资源枚举
- Agent 侧带 `project_id` 的请求在认证模式下回查 Go API 校验项目归属

**注入与外联**
- 数据库全部走 GORM 参数化，无字符串拼接 SQL
- 视频下载器在调用 yt-dlp 前拒绝解析到内网/非公网地址（SSRF 防护）；日志只保留主机名，不记录凭据、query 参数和签名 URL
- 提示词包请求限制镜头数量上限（200），越界返回 422

**数据与密钥**
- 密钥只从环境变量读取；`.env` 已进 `.gitignore`，`.env.example` 不含真实值
- 导出/下载链路不返回带签名的长期 URL

## 当前已知限制（部署前必须读）

1. **默认配置是不安全的，只适用于本机开发**：`AGENT_AUTH_ENABLED=false`、`JWT_SECRET=change_this_...`、Postgres/MinIO 使用示例口令。任何能被他人访问的部署都必须改，`docker-compose.prod.yml` 已强制其中一部分。
2. **LangGraph HITL 状态存在进程内存**（`MemorySaver`）：Agent 重启会丢失断点，多副本会互相看不见状态。需要跨进程断点续跑请接入 Postgres/Redis checkpointer。
3. **单实例限流计数器不共享**：多副本部署时每个进程各算各的，需要换成 Redis 计数。
4. **无对象存储加密与访问策略**：MinIO 桶默认私有但没有 SSE 与预签名 URL 有效期审计。
5. **依赖容器镜像仍有浮动标签**（`minio/minio:latest`、`milvusdb/milvus:v2.4-latest`）：生产前请固定 digest。
6. **未做外部渗透测试与模糊测试**，也没有 SOC2/等保类认证。当作「自建工具」使用，不要当作「合规即服务」。

## 生产部署最小检查清单

```bash
# 1. 密钥与口令全部更换
grep -E '^(JWT_SECRET|POSTGRES_PASSWORD|MINIO_ROOT_PASSWORD|AGENT_AUTH_ENABLED|ALLOWED_ORIGINS)=' .env
# 2. 生产 overlay 启动（会拒绝不合规配置）
docker compose -f docker-compose.yml -f docker-compose.prod.yml config -q
# 3. 确认没有端口被意外发布到公网
docker compose -f docker-compose.yml -f docker-compose.prod.yml port <service> <port>
# 4. 依赖审计（前端 + Python）
./scripts/pnpm.sh --dir apps/web audit --prod
cd services/agent && uv pip list --outdated
# 5. 备份已演练过恢复，而不只是备份
bash scripts/backup/restore-pg.sh /backups/postgres/mago_XXXX.sql.gz mago_restore   # 恢复到临时库
```
