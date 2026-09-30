# `@mago/shared-types`

手写的 API 契约类型（登录/项目/脚本/分镜/镜头/提示词包/热点），以 **Go API 网关的 `internal/model`** 为准。

- 只有 `typecheck`，没有构建产物，`main` 直接指向 `src/index.ts`。
- `apps/web/src/lib/api.ts` 直接复用本包的项目、角色、提示词包与提示词实体，以及项目/角色创建和项目更新请求类型；Agent SSE 负载和提示词包仍由 `apps/web/src/lib/agent-output.ts`、`prompt-pack.ts` 等前端模块定义。
- 想要自动生成的契约类型，见 [`../shared-protos/README.md`](../shared-protos/README.md)。

改 Go 模型字段时，请同步这里和前端类型，并检查导出链路（`apps/web/src/lib/export-formats.ts`、`artifacts.ts`）里的字段名是否一致——历史上就出过「Agent 输出 `scene_description`、前端只读 `scene_environment`」导致表格永远空白的问题。
