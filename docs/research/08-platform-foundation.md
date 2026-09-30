# 08板块调研：平台底座集成、可观测性与部署

## 调研时间：2026-09-09

---

## 1. LLM可观测性方案选型

### 候选方案对比

| 方案 | Stars | License | 特点 | LangGraph/LiteLLM集成 | 部署方式 |
|:---|:---|:---|:---|:---|:---|
| **Langfuse** | ⭐7.8k | MIT | 开源LLM可观测平台，支持trace/eval/datasets/prompt管理 | ✅ 原生集成（langfuse-langchain, litellm回调） | Docker/Cloud/Self-hosted |
| Helicone | ⭐3.2k | Apache 2.0 | LLM网关+监控，主打成本优化和缓存 | ✅ LiteLLM代理模式 | Cloud/Self-hosted |
| Arize Phoenix | ⭐4.5k | Elastic License 2.0 | LLM tracing+eval， Colab友好 | ✅ OpenInference标准 | Docker/Pip |
| OpenLIT | ⭐2.1k | Apache 2.0 | OpenTelemetry原生LLM可观测 | ✅ OTel自动埋点 | Docker |
| LangSmith | - | 商业 | LangChain官方，闭源SaaS | ✅ 最佳 | 仅Cloud |

### 决策：**Langfuse**
理由：
1. MIT协议完全开源，可自建无限制
2. 对LangChain/LangGraph/LiteLLM都有原生集成支持
3. 功能完整：Trace查看、Token/Cost统计、Prompt版本管理、Eval评估、数据集管理
4. 社区活跃，更新频繁
5. 提供Python SDK和REST API，可扩展自定义指标

**集成方式**：
- Python Agent服务：通过LiteLLM回调+Langfuse LangChain集成自动捕获所有LLM调用
- 业务自定义Trace：使用Langfuse Python SDK手动埋点关键业务步骤
- Go API网关：通过OpenTelemetry将API请求trace发送到Langfuse（或直接用REST API上报）

---

## 2. OpenTelemetry集成方案

### 选型结论
- **Go服务**：使用`go.opentelemetry.io/otel`官方SDK + OTLP exporter
- **Python服务**：使用`opentelemetry-python`官方SDK + OTLP exporter + FastAPI自动埋点
- **前端**：使用`@opentelemetry/api`基础SDK，手动埋点关键用户操作

### 采集信号
1. **Traces**：全链路追踪（前端→Nginx→Go网关→Python Agent→LLM API→DB/Redis）
2. **Metrics**：
   - Go: QPS、延迟P50/P95/P99、错误率、goroutine数、GC
   - Python: QPS、延迟、LLM调用次数/token数/成本、Agent执行时长
   - 业务: 创意生成成功率、脚本通过率、提示词质量评分
3. **Logs**：结构化日志统一通过OTel发送到Loki

### 后端接收
- **Collector**：OpenTelemetry Collector作为统一接收端，做tail-based采样、属性处理、路由
- 路由规则：
  - Traces → Tempo
  - Metrics → Prometheus
  - Logs → Loki
  - LLM traces → Langfuse（额外导出）

---

## 3. Grafana监控栈部署

### 组件选型（官方推荐云原生观测栈）
| 组件 | 版本 | 用途 | 端口 |
|:---|:---|:---|:---|
| Grafana | 10.4.x | 统一可视化入口 | 3000 |
| Prometheus | 2.51.x | Metrics存储+告警 | 9090 |
| Loki | 2.9.x | 日志聚合存储 | 3100 |
| Tempo | 2.4.x | 分布式Trace后端 | 3200 |
| OTel Collector | 0.97.x | 统一遥测数据收集 | 4317(OTLP gRPC), 4318(OTLP HTTP) |
| Node Exporter | 1.8.x | 主机指标采集 | 9100 |
| cAdvisor | 0.49.x | 容器指标采集 | 8080 |
| Promtail | 2.9.x | 日志采集（DaemonSet模式） | - |

### 预定义看板
1. **全局总览看板**：QPS、延迟、错误率、在线用户数、系统资源
2. **Go API网关看板**：API维度QPS/延迟、JWT验证成功率、DB连接池
3. **Python Agent看板**：Agent执行次数/时长、LLM调用统计、Token消耗、成本估算
4. **LLM调用看板**：按模型/Agent/项目维度统计调用量、成功率、成本、P95延迟
5. **数据库看板**：PG QPS、连接数、慢查询、锁等待、缓存命中率
6. **业务看板**：创意生成数、脚本完成数、提示词包导出数、各阶段转化率

### 告警规则（分级）
- **P0（立即电话）**：核心服务宕机、错误率>10%持续5分钟、DB不可用
- **P1（15分钟内响应）**：LLM API大面积失败、Agent执行失败率>30%、磁盘>90%
- **P2（1小时内响应）**：P95延迟>1s、Redis不可用、队列堆积>1000
- **P3（工作日处理）**：证书即将过期、磁盘>80%、非核心API错误率上升

---

## 4. API网关与安全加固

### 当前状态
- 已有Go Gin框架 + CORS中间件 + JWT中间件 + Logger中间件
- Nginx反向代理已配置基础路由

### 需要补充的安全措施
1. **限流**：使用`golang.org/x/time/rate`实现令牌桶限流，按IP/用户ID多维度限流
2. **输入校验**：所有请求DTO加validator标签，统一参数校验中间件
3. **SSRF防护**：禁止访问内网IP（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8）
4. **请求大小限制**：限制请求体大小（默认10MB）
5. **安全头**：添加X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, HSTS
6. **SQL注入防护**：GORM参数化查询已默认，额外添加慢查询监控
7. **Secret管理**：开发用.env，生产用K8s Secret或Vault，禁止硬编码密钥
8. **CORS精细化配置**：生产环境严格限制允许的Origin，不使用*
9. **RBAC权限控制**：角色分为admin/user/guest，API级别权限校验
10. **审计日志**：所有敏感操作（登录/修改密码/导出/删除）记录审计日志

---

## 5. 性能优化方案

### 缓存策略（Redis）
1. **热点接口缓存**：
   - 知识库查询：缓存1小时，更新时失效
   - 模型列表/风格/角色列表：缓存24小时
   - 热点趋势数据：缓存30分钟
2. **LLM响应缓存**：
   - 相同Prompt+模型参数缓存24小时（可配置）
   - 创意发散结果缓存
3. **HTTP缓存头**：静态资源设置Cache-Control，前端长期缓存

### 数据库优化
1. **索引优化**：
   - users: email(unique), created_at
   - projects: user_id, created_at, updated_at
   - scripts: project_id, created_at
   - storyboards: script_id
   - prompts: script_id, project_id
   - llm_call_logs: created_at, user_id, model
2. **连接池配置**：GORM设置MaxOpenConns/MaxIdleConns/ConnMaxLifetime合理值
3. **分页优化**：所有列表接口使用keyset分页（基于created_at+id），避免offset深分页
4. **软删除**：使用GORM DeletedAt进行软删除，定期归档历史数据

### LLM成本优化
1. **模型路由**：简单任务用便宜模型（创意发散用DeepSeek/GPT-4o-mini，质量检查用小模型，最终生成用高端模型）
2. **Prompt压缩**：长对话历史自动摘要压缩，减少token消耗
3. **缓存命中**：相同/相似Prompt命中缓存直接返回
4. **超时控制**：LLM调用设置合理超时，避免挂起消耗资源
5. **批处理**：非实时任务（批量评估、批量生成）批处理调用

---

## 6. 容器化与部署方案

### Docker镜像优化
所有服务采用多阶段构建：
- **Go API网关**：builder(golang:1.22-alpine) → runtime(alpine:3.19)，最终镜像~25MB
- **Python Agent**：builder(python:3.11-slim + uv) → runtime(python:3.11-slim)，清理系统缓存，最终镜像~350MB
- **Next.js前端**：builder(node:20-alpine + pnpm) → runner(node:20-alpine, standalone输出)，最终镜像~180MB
- **Nginx**：nginx:1.25-alpine基础上添加配置和前端静态文件，~40MB

### 生产Docker Compose
所有服务配置：
- 资源限制（CPU/内存）
- restart: always
- 健康检查（healthcheck）
- 非root用户运行
- 只读文件系统（可写目录挂载volume）
- depends_on健康检查依赖

### K8s部署清单
提供生产级K8s配置：
- Namespace: mago-platform
- Deployment: web/api-gateway多副本，agent服务按队列配置
- StatefulSet: postgres/redis/minio/milvus等有状态服务
- Service: ClusterIP内部服务，Ingress暴露外部
- ConfigMap: 非敏感配置
- Secret: 敏感信息（API Key/DB密码等）
- HPA: CPU/内存/QPS驱动自动扩缩容
- Ingress: Nginx Ingress + cert-manager自动HTTPS
- PVC: 持久化存储
- PDB: Pod中断预算保证可用性

---

## 7. Mago平台对接方案

### 对接内容
1. **SSO单点登录**：Mago作为IdP，Agent平台通过OIDC/JWT对接，用户免登录
2. **模型列表同步**：调用Mago API动态获取已启用的AIGC模型列表（12+模型）
3. **风格/LoRA/数字人同步**：同步Mago上已有的资产供用户选择
4. **提示词包推送**：生成的提示词包一键推送到Mago创建批量生成任务
5. **Webhook回调**：Mago生成完成后回调Agent平台更新任务状态
6. **数据回流**：生成结果（图片/视频URL、成功率、用户评分）回传Agent平台用于Prompt优化

### 接口规范
- 所有接口使用JWT认证
- 请求/响应统一JSON格式
- 幂等性保证：使用request_id避免重复提交
- 速率限制：按应用维度限流

---

## 8. 备份与灾难恢复

### 备份策略
| 数据 | 方式 | 频率 | 保留时间 | 存储位置 |
|:---|:---|:---|:---|:---|
| PostgreSQL | pg_dump全量 + WAL归档PITR | 每日0点全量，实时WAL | 全量30天，WAL7天 | S3/MinIO |
| Redis | RDB+AOF | RDB每小时，AOF每秒fsync | 7天 | 本地持久化volume |
| MinIO对象 | 版本控制+跨区域复制 | 实时 | 90天 | 多AZ |
| Milvus向量数据 | milvus-backup | 每日 | 30天 | S3/MinIO |

### 恢复Runbook
1. **PG恢复**：停止服务 → 恢复最新全量备份 → 回放WAL到指定时间点 → 启动服务 → 验证数据
2. **全集群故障**：基础设施重建 → 恢复各服务数据 → 启动服务 → DNS切换 → 验证
3. **数据误删**：使用PITR恢复到删除前时间点，导出需要的数据回写到生产库

---

## 最终技术选型总结

| 模块 | 选型 |
|:---|:---|
| LLM可观测 | Langfuse (self-hosted) |
| 遥测SDK | OpenTelemetry (Go/Python/JS官方SDK) |
| 遥测Collector | OpenTelemetry Collector |
| Metrics存储 | Prometheus |
| Logs存储 | Grafana Loki |
| Traces存储 | Grafana Tempo |
| 可视化 | Grafana |
| 限流 | golang.org/x/time/rate (令牌桶) |
| 参数校验 | go-playground/validator |
| 缓存 | Redis 7 + go-redis |
| 反向代理 | Nginx (MVP) → APISIX (生产升级路径) |
| 镜像构建 | Docker多阶段构建 |
| 编排 | Docker Compose (dev/小生产) → K8s (中大型生产) |
| HTTPS | Let's Encrypt + cert-manager |
| 备份 | pg_dump + WAL-E/WAL-G → S3/MinIO |
