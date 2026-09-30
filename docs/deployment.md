# Mago Agent Platform 部署文档

## 快速开始（开发环境）

### 前置要求
- Docker Desktop 4.20+ (生产叠加配置需要 Docker Compose v2.24+，用于清空开发端口映射)
- Node.js 20+（通过 Corepack 使用项目固定的 pnpm 9.15.0）
- Go 1.22+
- Python 3.11+ + FFmpeg（原生启动 Agent 时需要）
- uv 包管理器

### 1. 一键启动开发环境
```bash
# 复制环境变量
cp .env.example .env
# 编辑.env填入你的OPENAI_API_KEY
# Python Agent 使用 DATABASE_URL；Goose 使用 POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB

# 启动基础设施（PG/Redis/MinIO/Milvus/可观测栈）
docker compose up -d postgres redis minio etcd milvus otel-collector prometheus loki tempo grafana

# 等待服务就绪
make wait-db

# 运行数据库迁移
make migrate-up

# 启动四个进程（Go API、Agent API、Agent Worker、前端；新开终端，或用下面的脚本）
./🚀启动Mago.command

# 或分别启动：
cd services/agent && uv run python -m src.main
cd services/agent && uv run arq src.worker.WorkerSettings
cd services/api-gateway && go run ./cmd/server
cd apps/web && ../../scripts/pnpm.sh dev
```

### 访问地址
| 服务 | 地址 | 默认账号/密码 |
|:---|:---|:---|
| 前端（手动启动或 Compose 直连） | http://localhost:3000 | - |
| 开发 Compose 公共入口（Nginx） | http://localhost:8080 | 前端、Go API 和 Agent 的统一入口 |
| Go API 容器内部地址 | http://api-gateway:8080 | 仅 Compose 网络可用；手动启动时才直接使用宿主机 8080 |
| Python Agent（仅手动开发启动） | http://localhost:8000/docs | Compose 默认不暴露该端口；生产通过 Nginx 访问受保护 API |
| Grafana监控 | http://localhost:3001 | admin / mago_grafana |
| Langfuse可观测 | 外部 Langfuse Cloud / 自行部署地址 | 需在 `.env` 配置后启用 |
| MinIO控制台 | http://localhost:9001 | mago / mago_secret123 |
| Prometheus | http://localhost:9090 | - |

---

## 生产环境部署

### Docker Compose 生产部署

生产叠加配置会拒绝未设置的关键密钥。至少需要在 `.env` 中设置：

- `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`；如果数据库密码包含 `@:/?#%`、空格等 URL 保留字符，还需设置 `POSTGRES_PASSWORD_URLENCODED` 为密码组件的百分号编码值，并将同一编码值用于原生 Agent 的 `DATABASE_URL`。Go API 使用原始密码，Compose Agent/Goose 和 `make migrate-up` 使用编码值；可用 Python `urllib.parse.quote(password, safe="")` 生成。
- `REDIS_PASSWORD`、`AGENT_REDIS_URL`（例如 `redis://:密码@redis:6379/0`；密码中的特殊字符必须 URL 编码；这是 Docker 网络内 Agent 使用的地址）
- 如果在宿主机直接运行 Agent，再设置 `REDIS_URL=redis://localhost:6379/0`；不要把宿主机的 `localhost` 地址填入 `AGENT_REDIS_URL`。
- `MINIO_ROOT_USER`、`MINIO_ROOT_PASSWORD`
- `GRAFANA_ADMIN_USER`、`GRAFANA_ADMIN_PASSWORD`
- `NEXTAUTH_SECRET`、`NEXTAUTH_URL`、`LANGFUSE_SALT`：仅在你单独部署 Langfuse 时需要；核心 Compose 不再启动单容器 Langfuse。
- `JWT_SECRET`（至少 32 个字符的随机值）

不要把生产密码提交到仓库。

生产叠加配置会关闭数据库、缓存和监控组件的宿主机端口，仅由内部网络访问；公网入口是 Nginx。

先准备 TLS 证书（文件名必须匹配）：

```bash
mkdir -p deploy/ssl deploy/certbot
# 将证书复制为以下两个文件：
# deploy/ssl/fullchain.pem
# deploy/ssl/privkey.pem

# 使用生产 compose 文件
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 服务扩容（不要给带 container_name 的基础设施扩容）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d \
  --scale api-gateway=3 --scale web=2
```

如果尚未配置证书，请先使用开发 Compose 的 `http://localhost:8080`；生产 Nginx 会在证书缺失时拒绝启动，而不是静默降级为不安全的 HTTP。

生产 Nginx 同时挂载 `deploy/certbot` 到 `/var/www/certbot`，用于 Let's Encrypt HTTP-01 challenge。当前 Compose 不会自动签发或续期证书；如果使用 certbot，请让 certbot 将 challenge 文件写入 `deploy/certbot`，并在续期后替换 `deploy/ssl/fullchain.pem` 与 `deploy/ssl/privkey.pem`，再 reload Nginx。

### 安全配置
1. **必须修改所有默认密码**：
   - PostgreSQL密码
   - Redis密码（生产开启密码认证）
   - MinIO root用户密码
   - JWT_SECRET 改为长度32+的随机字符串
   - Grafana admin密码
   - 如果单独 self-host Langfuse，再修改其 NEXTAUTH_SECRET/SALT；核心 Compose 不使用这两个变量
2. **配置HTTPS**：
   - 使用Nginx反向代理 + Let's Encrypt证书
   - 或者K8s环境使用cert-manager自动签发
3. **开启防火墙**：只开放80/443端口，数据库/缓存等端口不对外暴露

### 资源配置建议
| 服务 | CPU | 内存 | 副本数 |
|:---|:---|:---|:---|
| Nginx | 0.5核 | 512MB | 2 |
| Web (Next.js) | 1核 | 1GB | 2+ |
| API Gateway (Go) | 1核 | 1GB | 2+ |
| Agent API (Python) | 2核 | 4GB | 按并发量 |
| Agent Worker (Python/ARQ) | 2核 | 4GB | 按视频分析并发量 |
| PostgreSQL | 2核 | 4GB | 1（主从可选） |
| Redis | 0.5核 | 1GB | 1（哨兵可选） |
| MinIO | 2核 | 4GB | 4节点纠删码（生产） |
| Milvus | 2核 | 8GB | 1 standalone |
| Grafana/Prometheus等 | 1核 | 2GB | 1 |

---

## 备份与恢复

### 自动备份配置
添加cron任务每天凌晨2点执行备份。备份/恢复脚本要求显式设置 `PG_PASSWORD`，不会使用仓库内置的默认数据库密码。不要把密码直接写进 crontab；可使用仅 root 可读的 secret 文件和包装脚本：

```bash
# /usr/local/sbin/mago-backup（root 所有，权限 700）
#!/bin/sh
set -eu
PG_PASSWORD="$(cat /run/secrets/mago_pg_password)"
export PG_PASSWORD
exec /path/to/scripts/backup/backup-pg.sh
```

以 root 身份安装该包装脚本后，配置 cron：
```cron
0 2 * * * /usr/local/sbin/mago-backup >> /var/log/mago-backup.log 2>&1
```

备份文件默认保留30天，可配置上传到S3/MinIO。备份脚本会先验证 gzip 完整性，再发布备份文件；恢复脚本也会在导入前验证归档。执行恢复前，请通过同等安全的方式设置并导出 `PG_PASSWORD`。

### 恢复流程
```bash
# 1. 停止应用服务
docker compose stop api-gateway agent web

# 2. 执行恢复
export PG_PASSWORD="$(cat /run/secrets/mago_pg_password)"  # 从受限权限的 secret 文件读取
./scripts/backup/restore-pg.sh /backups/postgres/mago_20260101_000000.sql.gz

# 3. 启动服务验证
docker compose up -d api-gateway agent web
```

---

## Kubernetes 迁移说明（中大型生产）

本仓库当前**不包含现成的 `deploy/k8s/` manifests**。Docker Compose 生产配置是可直接运行的参考实现；迁移到 Kubernetes 时，请将以下组件分别映射为 Deployment/Service 或托管服务：

- `web`、`api-gateway`、`agent`、`agent-worker`、`nginx`：Deployment + Service（`agent-worker` 只需要 Deployment，不需要公网 Service）；
- PostgreSQL、Redis、MinIO、Milvus：优先使用云厂商托管服务，或单独维护 StatefulSet/PersistentVolume；
- `.env` 中的密钥：使用 Kubernetes Secret/Vault，不要写入 ConfigMap；
- HTTPS：使用 Ingress + cert-manager；
- 迁移任务：使用 Job 执行 Goose migrations，并在应用 Deployment 前完成；
- 扩缩容：先为 `api-gateway`/`web` 配置 HPA，Agent 需要根据 LLM 并发和视频处理资源单独评估。

在没有 Kubernetes manifests 之前，不要执行 `kubectl apply -f deploy/k8s/`；该路径不存在。

---

## 可观测性
接入后可以在Grafana看到：
1. 全局总览看板：QPS/延迟/错误率/资源使用率
2. API网关看板：接口维度指标
3. Agent服务看板：LLM调用次数/token消耗/成本/执行时长
4. 业务看板：各阶段转化率/创意生成数/导出数

配置外部 Langfuse 后，可以看到每一次 LLM 调用的完整 trace、输入输出、token 数和成本；未配置时 Agent 仍可正常运行。

---

## 故障排查
见 [troubleshooting.md](./troubleshooting.md)


### 前端离线演示
没有完整基础设施时，可以在 `apps/web/.env.local` 设置 `NEXT_PUBLIC_DEMO_MODE=true`。该模式只在浏览器端提供可清空的示例数据和本地 SSE，不会调用真实后端；生产部署必须保持为 `false` 或不设置。

### 生产安全必配项

- `JWT_SECRET`：至少 32 个字符的随机值，Go API 与 Agent 必须一致。
- `AGENT_AUTH_ENABLED=true`：生产 Agent JWT 校验由 `docker-compose.prod.yml` 自动开启。
- `CRAWL_USE_SAMPLE_DATA=false`：默认关闭样例热点数据；只有离线演示才显式开启。
- `TREND_INSIGHTS_TIMEOUT_SECONDS=15`：工作台同步读取热点洞察的最长等待时间；超时会返回空/部分结果，完整抓取应使用队列接口。
- `DOUYIN_COOKIE`：如需抖音接口访问，通过环境变量注入，不要提交到仓库。
