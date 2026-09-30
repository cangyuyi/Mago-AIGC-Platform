# `shared-protos`（预留，当前为空）

这个目录**尚未接入构建流程**，留在这里是为了说明「前后端类型怎么统一」这条路径，避免每个人自己发明一套。

## 现状

- Go API 没有输出 OpenAPI 文件（`services/api-gateway` 未引入 swaggo/`/swagger`）。
- Python Agent 由 FastAPI 自动生成 schema：Agent 运行时访问 `http://localhost:8000/openapi.json`，交互式文档在 `/docs`。这是**目前唯一真实可导出的契约**。
- 前端类型手写在 `apps/web/src/lib/`（`agent-output.ts`、`api.ts`、`prompt-pack.ts`），并与 `packages/shared-types` 有部分重复。

## 计划的用法（欢迎按这个方向提 PR）

1. Go 侧用 swaggo 注解补齐 `docs/swagger.json`，或在 CI 里从路由表导出 OpenAPI；
2. 统一产物落到本目录：`shared-protos/openapi.yaml`（Go）+ `shared-protos/agent.openapi.json`（由 `curl localhost:8000/openapi.json` 生成）；
3. 用 `openapi-typescript` 生成 `packages/shared-types/src/generated/`，前端改为消费生成结果；
4. CI 增加一步「重新生成 + 无 diff」校验，防止契约悄悄漂移。

```bash
# 生成 Agent 契约（需要 Agent 已启动）
curl -sS http://localhost:8000/openapi.json > packages/shared-protos/agent.openapi.json

# 生成前端类型（需要先安装 openapi-typescript 到 devDependencies）
npx openapi-typescript packages/shared-protos/agent.openapi.json \
  -o packages/shared-types/src/generated/agent.ts
```

在此之前，请把 `packages/shared-types` 当作**手写参考**而不是真相来源：它以 API 网关的 Go 模型为准，字段与前端实际解析的 Agent SSE 负载并不完全一致。
