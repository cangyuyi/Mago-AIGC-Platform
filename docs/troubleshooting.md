# 常见问题排查手册

## 服务启动问题
### Agent服务启动失败，提示无法连接Redis
- 检查Redis是否启动：`docker compose ps redis`
- 检查REDIS_URL配置是否正确
- Redis默认无密码，如果配置了密码需要在URL中指定

### Go API无法连接PostgreSQL
- 检查PG是否启动健康检查通过：`docker compose ps postgres`
- 检查DB_DSN配置格式：`host=localhost port=5432 user=mago password=xxx dbname=mago sslmode=disable`
- 手动连接测试：`psql $DATABASE_URL`

### LLM调用失败
- 检查OPENAI_API_KEY是否正确配置
- 检查网络是否能访问OpenAI/Anthropic/DeepSeek等API
- 离线模式下只能运行测试，无法生成真实内容

## 性能问题
### Agent执行很慢
- 检查LLM API响应延迟（Langfuse中可以看到）
- 如果是复杂任务（详细模式）属于正常现象，可使用quick模式快速出结果
- 检查是否开启了缓存，相同Prompt会直接返回缓存结果

### API P95延迟高
- 检查数据库慢查询日志
- 确认所有索引都已创建（执行000002_add_indexes迁移）
- 增加API网关副本数水平扩容

## 可观测问题
### Grafana看不到指标
- 检查Prometheus targets是否全部UP
- 检查OTel Collector是否正常运行
- 确认服务OTEL_ENABLED设置为true

### Langfuse没有 trace 数据
- 确认已单独部署 Langfuse Cloud 或官方多容器 self-hosted stack；核心 Compose 不提供单容器 Langfuse。
- 确认 `LANGFUSE_ENABLED=true`、`LANGFUSE_HOST`、`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY` 配置正确。
- 先用 `curl -fsS "$LANGFUSE_HOST/api/public/health"` 检查 endpoint 是否可达，再查看 Agent 日志。
