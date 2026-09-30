# 指令 08：平台底座集成、可观测性与部署

## 角色设定

你是一名**DevOps工程师+SRE+后端架构师**，负责将所有板块集成联通、搭建完整的CI/CD、日志监控、告警、安全防护体系，并给出生产环境部署方案。你熟悉Docker/K8s/Terraform/OpenTelemetry/Prometheus/Grafana/Loki/Grafana Tempo生态。

## 前置依赖

必须先完成 `01-project-bootstrap.md` + `02`~`07`所有板块（各模块独立开发完成后做集成）。

## 任务目标

1. 所有模块端到端集成联调
2. Agent编排LangGraph总流程图串联所有Agent
3. 统一可观测体系（日志/指标/追踪/LLM调用链）
4. 安全加固（CORS/限流/SSRF/输入校验/Secret管理）
5. 生产环境部署配置（Docker/K8s/CDN/HTTPS）
6. 性能优化（缓存/批处理/异步任务/数据库索引）
7. Mago平台正式对接打通

## 执行步骤

### Step 1：调研GitHub与云原生最佳实践（必须）

记录到 `docs/research/08-platform-foundation.md`：

1. **LLM可观测性**：
   - 搜索关键词：`LLM observability open source`, `langfuse`, `helicone`, `langsmith alternative`, `openlit`, `phoenix arize`
   - 参考：`langfuse/langfuse`(⭐开源LLM可观测平台), `Helicone/helicone`(LLM网关+监控), `Arize-ai/phoenix`(LLM tracing+eval), `openlit/openlit`
   - 决策：对比自建vs开源。**推荐集成Langfuse（开源、可自建、支持LangChain/LangGraph/LiteLLM原生集成）**，自建部分业务指标

2. **OpenTelemetry集成**：
   - 参考：`open-telemetry/opentelemetry-go`, `open-telemetry/opentelemetry-python-contrib`
   - 决策：Go和Python都接入OTel SDK，Trace/Metric/Log三件套统一上报

3. **Grafana Stack部署**：
   - 参考：Grafana官方docker-compose（Grafana + Prometheus + Loki + Tempo）
   - 决策：用Grafana统一展示metrics(Prometheus) + logs(Loki) + traces(Tempo)

4. **API网关选型**：
   - 搜索：`kong vs apisix vs traefik`, `cloudnative api gateway`
   - 参考：`apache/apisix`(性能强、插件多), `kong/kong`, `traefik/traefik`(云原生), `envoyproxy/envoy`
   - 决策：MVP阶段用Nginx足够（01已配），生产考虑APISIX或Traefik，有明确的升级路径

### Step 2：LangGraph总流程图集成

在 `services/agent/src/core/graph.py` 中构建完整的端到端工作流，串联所有Agent：

```python
from langgraph.graph import StateGraph, END
from agents.trend.viral_analyzer import viral_analyzer_node
from agents.trend.topic_recommender import recommend_topics_node
from agents.script.ideation_agent import ideation_node
from agents.script.creative_director import creative_brief_node
from agents.script.hook_specialist import hook_design_node
from agents.script.storyteller import narrative_node
from agents.script.copywriter import copywriting_node
from agents.script.conversion_expert import cta_design_node
from agents.script.compliance_agent import compliance_check_node
from agents.script.script_evaluator import script_eval_node
from agents.script.storyboard_agent import storyboard_node
from agents.character.character_designer import character_design_node
from agents.style.style_director import style_director_node
from agents.prompt.assembler import prompt_generation_node
from agents.prompt.reviewer import prompt_qa_node
from agents.prompt.optimizer import prompt_optimize_node
from core.hitl import human_review_node, should_wait_for_human

def build_full_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # 添加所有节点
    g.add_node("clarify", clarify_needs_node)
    g.add_node("trend_research", trend_research_node)        # 可选：研究热点
    g.add_node("ideation", ideation_node)
    g.add_node("ideation_review", human_review_node("ideation"))  # HITL选择创意
    g.add_node("creative_brief", creative_brief_node)
    g.add_node("brief_review", human_review_node("brief"))
    g.add_node("character_design", character_design_node)    # 可选
    g.add_node("style_design", style_director_node)          # 可选
    g.add_node("hook_design", hook_design_node)
    g.add_node("narrative", narrative_node)
    g.add_node("copywriting", copywriting_node)
    g.add_node("cta_design", cta_design_node)
    g.add_node("compliance", compliance_check_node)
    g.add_node("script_eval", script_eval_node)
    g.add_node("script_review", human_review_node("script"))
    g.add_node("storyboard", storyboard_node)
    g.add_node("storyboard_eval", storyboard_eval_node)
    g.add_node("storyboard_review", human_review_node("storyboard"))
    g.add_node("prompt_generation", prompt_generation_node)
    g.add_node("prompt_qa", prompt_qa_node)
    g.add_node("prompt_optimize", prompt_optimize_node)
    g.add_node("prompt_review", human_review_node("prompt"))
    g.add_node("export_ready", export_ready_node)

    # 定义边（精细模式）
    g.set_entry_point("clarify")

    g.add_conditional_edges("clarify", needs_trend_research, {
        True: "trend_research",
        False: "ideation"
    })
    g.add_edge("trend_research", "ideation")
    g.add_edge("ideation", "ideation_review")  # HITL
    g.add_edge("ideation_review", "creative_brief")
    g.add_edge("creative_brief", "brief_review")  # HITL
    g.add_edge("brief_review", "character_design")
    g.add_edge("character_design", "style_design")
    g.add_edge("style_design", "hook_design")
    g.add_edge("hook_design", "narrative")
    g.add_edge("narrative", "copywriting")
    g.add_edge("copywriting", "cta_design")
    g.add_edge("cta_design", "compliance")
    g.add_edge("compliance", "script_eval")
    g.add_conditional_edges("script_eval", script_needs_revision, {
        "hook": "hook_design",
        "narrative": "narrative",
        "compliance": "compliance",
        "pass": "script_review"
    })
    g.add_edge("script_review", "storyboard")
    g.add_edge("storyboard", "storyboard_eval")
    g.add_conditional_edges("storyboard_eval", storyboard_needs_revision, {
        True: "storyboard",
        False: "storyboard_review"
    })
    g.add_edge("storyboard_review", "prompt_generation")
    g.add_edge("prompt_generation", "prompt_qa")
    g.add_conditional_edges("prompt_qa", prompt_needs_optimization, {
        True: "prompt_optimize",
        False: "prompt_review"
    })
    g.add_edge("prompt_optimize", "prompt_qa")
    g.add_edge("prompt_review", "export_ready")
    g.add_edge("export_ready", END)

    # 编译（带checkpointer实现断点续跑）
    return g.compile(
        checkpointer=PostgresCheckpointer(conn_string=DB_URL),
        interrupt_before=HITL_NODES,  # 所有human_review节点作为中断点
    )
```

同时编译一个快速模式graph（跳过所有HITL节点，Agent自动决策）：

```python
def build_quick_graph() -> StateGraph:
    """快速模式：一键生成，Agent自动决策，无人工节点"""
    # ... 类似结构但去掉所有human_review节点，creative_director自动选最优方案
```

要求：
- **状态持久化**：使用LangGraph的PostgresCheckpointer，将Agent执行状态持久化到PostgreSQL，服务器重启/用户关闭页面后可断点续跑
- **每个节点输出流式事件**：通过SSE推送给前端
- **并行执行**：无依赖关系的节点（如hook_design/copywriting/cta_design）用Send API并行执行
- **错误处理**：每个节点wrap try/except，失败时支持重试（带指数退避），超过3次标记节点失败并通知用户
- **超时控制**：每个节点有超时（LLM调用60s，复杂任务300s），超时降级

### Step 3：服务间通信架构

确定API Gateway模式：
- 前端统一访问Nginx反向代理，路径路由：
  - `/` → Next.js前端
  - `/api/v1/*` → Go API Gateway（业务CRUD、鉴权、聚合）
  - `/api/agent/*` → Python Agent服务（Agent执行、流式输出）
  - `/ws/*` → WebSocket（Go或Python服务统一接入点）
- Go API Gateway需要聚合Agent服务的API（前端不直接访问Agent服务），但SSE/WebSocket流式响应直接透传
- 服务间内部调用用HTTP + 服务发现（初期用Docker network DNS，生产用Consul/K8s Service）
- 异步任务（视频分析、提示词批量生成）走消息队列（arq/Redis Stream）

### Step 4：可观测体系搭建

#### 4.1 Langfuse LLM可观测性（必须集成）

- 在docker-compose中增加 `langfuse` 服务（langfuse/langfuse镜像 + PostgreSQL依赖）
- LiteLLM初始化时配置Langfuse callback：
  ```python
  litellm.success_callback = ["langfuse"]
  litellm.failure_callback = ["langfuse"]
  ```
- LangChain/LangGraph配置Langfuse tracer（`from langfuse.callback import CallbackHandler`）
- 每个Agent调用LLM时传入 `config={"callbacks": [langfuse_handler]}`，自动记录：
  - 每次LLM调用的Prompt/Response/Tokens/Latency/Cost
  - Trace ID和Span ID与OpenTelemetry对接
  - 用户反馈（👍👎）关联到具体Trace
  - 版本标记（Prompt版本、Agent版本）

#### 4.2 OpenTelemetry全链路追踪

Go服务：
- 集成 `go.opentelemetry.io/otel` + `otelgin`（Gin middleware）
- 每个HTTP请求创建Span，Context跨服务传递（W3C TraceContext）
- 数据库调用创建子Span
- 调用Agent服务/LLM API时传播trace header

Python服务：
- 集成 `opentelemetry-sdk` + FastAPI middleware + `opentelemetry-instrumentation-*`（requests/redis/httpx等自动instrumentation）
- LangGraph节点执行创建Span
- LLM调用创建Span（包含model/prompt tokens等attributes）

前端：
- 集成Web端OTel SDK（`@opentelemetry/sdk-trace-web`），前端页面加载、API调用、关键交互都有Span
- 通过OTLP/HTTP上报到Tempo/Grafana

#### 4.3 Metrics指标

**业务指标**（Prometheus Counter/Gauge/Histogram）：
- 用户注册/登录/活跃数
- 项目创建数
- Agent执行次数（按Agent类型）
- Agent执行成功率/失败率
- Agent执行耗时分布（P50/P95/P99）
- 提示词生成数
- Mago推送任务数/成功率/平均耗时
- LLM Token消耗（分模型/Agent/用户）
- LLM成本（按美元/人民币）
- 热点爬取成功率/视频分析成功率
- 用户反馈（👍/👎比率）

**技术指标**：
- API QPS/延迟分布/错误率
- WebSocket连接数
- 数据库连接池/慢查询数
- Redis命中率/内存使用
- Milvus查询延迟
- MinIO存储使用量
- GPU/CPU/内存/磁盘（基础资源）

#### 4.4 日志

- 所有服务使用结构化日志（JSON格式），统一字段：`timestamp, level, service, trace_id, span_id, user_id, project_id, msg, error, latency_ms, ...`
- 日志输出到stdout/stderr（容器最佳实践）
- Promtail/Fluentd采集日志→Loki存储→Grafana查看
- 敏感信息（API Key/用户密码/Token）禁止打日志（中间件统一脱敏）

#### 4.5 Grafana Dashboard

必须创建以下看板：
1. **总览看板**：全局QPS、错误率、P95延迟、在线用户数、今日项目/脚本/提示词生成数、今日LLM成本
2. **Agent看板**：每个Agent的调用次数/成功率/耗时/Token消耗，实时运行中的Agent任务列表
3. **LLM看板**：分模型调用量/延迟/错误率/Cost，Top用户Token消耗，Langfuse跳转链接
4. **业务看板**：注册/转化/留存漏斗，Mago推送成功率，用户满意度
5. **基础设施看板**：各服务CPU/内存/磁盘，数据库连接池，Redis/Milvus/MinIO健康
6. **爬虫/视频分析看板**：爬取任务成功率、队列堆积、视频分析耗时分布

#### 4.6 告警规则

配置Prometheus AlertManager告警：
- **P0（立即处理）**：服务宕机、错误率>5%持续5分钟、数据库不可用
- **P1（30分钟内）**：P95延迟>3s持续5分钟、LLM API连续失败、Mago推送成功率<90%
- **P2（2小时内）**：队列堆积>100任务、磁盘使用率>80%、单用户日成本超阈值
- **P3（工作日处理）**：磁盘>70%、某Agent失败率上升但不影响全局、证书即将过期

告警渠道：邮件/企业微信/飞书/Telegram（按优先级分渠道）

### Step 5：安全加固

1. **认证与授权**：
   - JWT access token（短过期，15分钟）+ refresh token（7天，httpOnly cookie存储）
   - RBAC权限：每个API检查用户对project/asset的权限
   - API Key（给开发者/第三方集成）：可生成/吊销，有权限范围限制
   - 企业SSO：实现OIDC/SAML（Phase 2，预留接口）

2. **传输安全**：
   - 生产全HTTPS（Let's Encrypt自动续期）
   - WebSocket使用WSS
   - HSTS头启用
   - 内部服务间mTLS（Phase 2）

3. **输入安全**：
   - 所有用户输入在后端做校验（zod/validator），禁止信任前端
   - SQL注入防护：使用ORM参数化查询（已有GORM）
   - XSS防护：React默认+Markdown渲染时sanitize（用DOMPurify）
   - CSRF：SameSite cookie + CSRF token
   - SSRF防护：用户提交URL做域名白名单/黑名单（爬虫场景），禁止访问内网地址
   - 文件上传：验证文件类型/大小/内容（MIME sniffing），上传到MinIO时用随机文件名，不执行用户上传的文件

4. **速率限制**：
   - API限流：按用户+IP（滑窗算法，普通用户60次/分钟，企业客户单独配置）
   - LLM调用限流：按用户+Agent类型限流，防止Token消耗爆炸
   - 登录/注册限流：防暴力破解（5次/分钟/IP）
   - 文件上传限流和大小限制

5. **Secret管理**：
   - 所有密钥（DB密码/API Key/JWT Secret）通过环境变量注入，不硬编码
   - 生产环境用Vault或K8s Secrets管理
   - `.env.example`只放模板，真实密钥不入库
   - LLM API Key加密存储（AES-256-GCM），使用时解密

6. **数据安全**：
   - 用户数据隔离：API层强制过滤（WHERE owner_id = current_user），向量库按owner_id分区
   - 个人信息脱敏：日志中邮箱/手机号脱敏显示
   - 数据备份：PostgreSQL每日全量备份+WAL持续归档，保留30天
   - 删除用户时级联删除所有数据（GDPR合规）

7. **内容安全**：
   - 合规审查Agent前置拦截违规内容（板块03已有）
   - 敏感词库持续更新
   - 用户上传图片/视频做内容安全审核（可对接阿里云/腾讯云内容安全API，Phase 2）

### Step 6：性能优化

1. **缓存策略**：
   - Redis缓存热点数据：热点榜单、预置知识库（角色/风格/场景/创意理论）、查询结果
   - LLM响应缓存：相同prompt+model+temperature的请求缓存（有TTL），用prompt hash做key
   - 多级缓存：内存缓存(ttl 60s) → Redis缓存(ttl 10min) → DB
   - 缓存失效：写操作时主动失效相关缓存

2. **数据库优化**：
   - 检查所有表的索引（为WHERE/JOIN/ORDER BY字段加索引）
   - 慢查询监控：>100ms的query记录，定期优化
   - 连接池配置合理（Go sql.DB SetMaxOpenConns等）
   - 热点行/表考虑读写分离（Phase 2）

3. **异步处理**：
   - 视频分析、批量提示词生成、非实时查询全部走异步队列
   - 前端用轮询/WebSocket等待结果
   - 任务状态持久化，Worker重启后可恢复

4. **LLM成本优化**：
   - 模型路由：简单任务（分类/抽取/格式转换）用GPT-4o-mini/Claude Haiku/DeepSeek，复杂创意任务才用GPT-4o/Claude Sonnet/Gemini Pro
   - 缓存：相同/相似请求直接返回缓存
   - Prompt压缩：历史对话/知识库上下文压缩（LLMLingua或相似压缩）
   - Token计数：实时监控每次调用的token用量，超阈值告警
   - 批处理：可批处理的请求合并（Embedding批处理）

5. **CDN与静态资源**：
   - 前端静态资源（JS/CSS/图片）上传CDN
   - 用户上传的参考图/关键帧用CDN加速
   - 视频文件不上传本地，只存MinIO+CDN分发

### Step 7：Mago正式集成对接

与Mago主站打通：
1. **SSO单点登录**：Mago用户免登录进入Agent平台（JWT共享或OAuth2授权）
2. **用户/组织/计费体系打通**：复用Mago的用户/组织/余额体系
3. **API正式对接**：
   - 获取Mago的模型列表（动态拉取，不硬编码）
   - 推送提示词包到Mago批量创建任务（使用Mago任务API）
   - Webhook接收Mago任务状态回调
   - 获取Mago已有的LoRA/风格/数字人列表供选择
4. **数据统计回传**：Agent平台生成的提示词→Mago生成→效果数据（成功率/用户满意度/后续使用）回流Agent平台用于优化
5. **统一导航入口**：Mago主导航增加"AI创意助手"入口跳转Agent平台

### Step 8：生产部署配置

#### 8.1 Docker镜像优化

- 所有Dockerfile用多阶段构建
- Go服务：builder阶段(golang:alpine) + runtime阶段(alpine)，最终镜像<30MB
- Python服务：builder阶段(uv同步依赖) + runtime阶段(python:slim)，清理pip缓存
- Next.js：standalone输出，最终镜像<200MB
- 基础镜像固定版本tag（不用latest），定期安全扫描（Trivy）

#### 8.2 docker-compose.prod.yml

生产环境compose（或作为K8s部署参考）：
- 所有服务指定资源限制（CPU/内存）
- PostgreSQL配置持久化volume、定期备份cron
- Redis配置持久化AOF
- MinIO配置纠删码模式（4驱动器）
- Milvus生产模式（集群版可选，初期standalone够）
- Nginx配置HTTPS证书、gzip/brotli压缩、HTTP/2、静态资源缓存头
- 副本数：Web/API可多副本，Agent服务按GPU/CPU资源配置

#### 8.3 K8s部署清单（生产推荐）

在 `deploy/k8s/` 下提供：
- Namespace
- Deployment/StatefulSet（各服务）
- Service（ClusterIP/LoadBalancer/Ingress）
- ConfigMap/Secret
- HPA（水平自动扩缩容）
- Ingress（Nginx Ingress Controller + cert-manager自动HTTPS）
- PersistentVolumeClaim（PG/Redis/Milvus/MinIO数据持久化）
- PodDisruptionBudget
- ResourceQuota/LimitRange

#### 8.4 数据库备份与灾难恢复

- PG每日自动备份（pg_dump到S3/MinIO），保留30天
- WAL归档支持PITR（Point-in-Time Recovery）
- Redis AOF每秒钟fsync
- Milvus元数据备份
- 恢复演练Runbook（文档化，每季度演练一次）

### Step 9：测试体系完善

在现有单元测试基础上补充：
1. **集成测试**：每个服务启动后测试主要API流程（用testcontainers或docker-compose启动依赖）
2. **端到端测试**：用Playwright写关键流程E2E测试（注册→创建项目→灵感→脚本→分镜→提示词→导出）
3. **Agent评估测试**：建立固定测试集（20+case），每次Prompt更新后自动跑，输出各维度分数对比报告
4. **负载测试**：用k6对核心API做压测，确保500并发下P95<500ms
5. **混沌测试**（Phase 2）：模拟LLM API超时/失败、Redis宕机等场景，验证降级

### Step 10：文档完善

- 更新根README：架构图、快速开始、部署文档、API链接
- `docs/deployment.md`：生产部署指南（环境要求/Docker/K8s步骤/配置项清单/备份恢复/扩容）
- `docs/troubleshooting.md`：常见问题排查手册
- `docs/api/`：SwaggerUI部署（/swagger路径可访问）
- `docs/architecture.md`：更新为最终架构（含所有板块集成后的完整架构图）
- `docs/security.md`：安全说明
- `CHANGELOG.md`：每个版本的更新记录

### Step 11：数据初始化与Demo数据

- 种子数据脚本 `scripts/seed-db.sh` 完成：
  - 默认管理员账号
  - 5个示例项目（覆盖不同类型：美妆带货/知识口播/短剧/好物推荐/风景）
  - 预置角色50+、风格100+、场景100+、道具80+
  - 预置知识全部入库
  - 12个模型配置初始化
- Demo模式：新用户注册后可选"创建示例项目"快速体验全流程

## 验收标准

- [ ] 完整的端到端Happy Path走通：用户注册→灵感→脚本→分镜→提示词→推送到Mago→查看结果→优化重生成
- [ ] LangGraph精细模式和快速模式都能正常执行，HITL节点等待/通过/重跑正常
- [ ] 断点续跑：关闭浏览器后重新打开能继续上次的任务
- [ ] Langfuse LLM可观测部署完成，能看到每次LLM调用的trace/token/cost
- [ ] OpenTelemetry全链路追踪串联Go/Python/前端，Grafana Tempo可查Trace
- [ ] Grafana 6个看板全部完成，关键指标正常显示
- [ ] 告警规则配置完成（P0/P1/P2/P3）
- [ ] 安全加固项全部通过：HTTPS/JWT/RBAC/限流/输入校验/SSRF防护/Secret管理
- [ ] 缓存策略生效，热点接口响应<50ms
- [ ] LLM成本优化生效（路由/缓存/压缩有数据验证成本下降）
- [ ] Mago SSO/API/回调/数据回流全部打通（可在Mago测试环境验证）
- [ ] Docker生产镜像构建完成，docker-compose.prod.yml可启动生产栈
- [ ] K8s部署清单可用（或明确提供升级路径）
- [ ] 数据库备份脚本可用，恢复流程文档化
- [ ] Playwright E2E测试覆盖核心流程，通过率100%
- [ ] 负载测试核心API在500并发P95<500ms
- [ ] 所有文档齐全（部署/排错/API/架构/安全）
- [ ] Demo数据初始化可用，新用户可快速体验
