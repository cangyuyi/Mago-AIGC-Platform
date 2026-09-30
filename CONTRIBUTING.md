# 贡献指南

先说结论：**这是一个可以只靠 `make demo` 就跑起来改代码的项目**，不需要 Docker、不需要数据库、不需要任何 LLM Key。

## 1. 环境准备

| 必需 | 版本 | 说明 |
|:---|:---|:---|
| Node.js | 20+ | 自带 Corepack，前端依赖固定 pnpm 9.15.0 |
| Python | 3.11+ 或 [uv](https://docs.astral.sh/uv/) | 有 uv 时它会自动准备解释器 |
| Git | 任意 | — |

可选：Go 1.22（只跑 API 网关需要）、Docker（只跑完整栈需要）、FFmpeg（只跑视频下载需要）。

装好后先体检：

```bash
make doctor        # 只读检查：缺什么、哪个端口被占用、能不能跑
make setup-env     # 生成 .env（已存在则不动）
```

> 本仓库常放在 iCloud 同步目录等**含空格的路径**下。所有脚本都对路径加了引号，请保持这个习惯：新写 Makefile 行或 shell 脚本时，`"$(GO)"`、`"$PROJECT_DIR"` 这类引号不要去掉。
> 另外 iCloud 会拒绝部分写入：缓存类产物一律放 `/tmp`（`GOCACHE`、`UV_CACHE_DIR`、`COVERAGE_FILE`、pytest 的 `cache_dir` 都已如此设置）。

## 2. 跑起来

```bash
make install          # 前端 + Go + Agent 三端依赖
make demo             # 无 Docker：Agent(8000) + 前端(3000)，数据在浏览器本地
```

需要真实数据库和账号体系时：

```bash
make docker-min       # 只要 Postgres + Redis + MinIO（推荐，省 ~4GB 内存）
docker compose -f docker-compose.min.yml run --rm migrate
make dev-api          # Go 网关(8080)
make dev-agent        # Agent(8000)，带热重载
make dev-web          # 前端(3000)
```

完整栈（含 Milvus 与可观测面板）：`make docker-up`，然后 `bash scripts/setup.sh`。

## 3. 改代码前必跑的检查

```bash
make test            # = check-web(vitest) + test-api(go) + test-agent(pytest)
make lint            # eslint + go vet + ruff/mypy
make build           # next build + go build + agent import 冒烟
```

单端：

```bash
make check-web        # typecheck + eslint + vitest
make test-api-race    # Go race 检测（需要 C 工具链；CI 里默认开）
cd services/agent && .venv/bin/pytest tests -q -o cache_dir=/tmp/pytest-cache
cd apps/web && ../../scripts/pnpm.sh test
```

**依赖安装规则**：前端依赖只能通过 `./scripts/pnpm.sh --dir apps/web add -D <包名>` 安装，**不要在 `apps/web` 里直接 `npm i`**——会在 workspace 里生成第二份 lockfile，CI 的 `--frozen-lockfile` 随即失败。

## 4. 代码规范

- **前端**：Apple 风格的浅色圆角卡片体系（页面底色 `#f5f5f7`、白卡 `rounded-[18px]`、`border-black/[0.06]`、主色 `#007aff`、`shadow-apple-sm/md`）。禁止硬编码深色主题、禁止渐变堆装饰。文案一律中文，面向创作者而不是工程师。
- **Python**：`ruff` + `mypy --check-untyped-defs` 必须全绿。新增 Agent 节点请同时加 `tests/` 用例，提示词类改动必须断言「输出里没有中文泄漏到英文提示词」「同一描述不重复两次」。
- **Go**：`go vet` 必须全绿；新增写接口必须带资源归属校验（参考 `internal/service/*Owned`），否则视为越权漏洞。
- 提交信息用一句话说清「改了什么 + 为什么」，中英文都可以；一个 PR 只做一件事。

## 5. 加一个新模型 / 新提示词格式

1. 在 `services/agent/src/prompt_engine/models.py` 增加该模型的参数声明（支持的宽高比键名、时长上限、是否支持负向提示词、参数写法）。
2. 在 `services/agent/src/prompt_engine/normalize.py` 检查该模型需要的取值是否要归一（例如 `dolly_in` → `push_in`）。
3. 在 `services/agent/tests/test_prompt_engine.py` 补一条：给定同一个分镜，该模型的提示词 + 参数符合预期。
4. 前端不需要改动——模型列表来自 `GET /api/v1/agent/prompt-models`。

## 6. 加一个新的 Agent

`services/agent/src/agents/<域>/` 写实现 → 在 `src/core/` 的 LangGraph 图里挂节点 → 路由放 `src/api/routes/` → 前端在 `apps/web/src/lib/agent-stream.ts` 的事件类型里加对应 SSE 事件（注意：事件负载是**嵌套**的，例如 `event: storyboard` 的数据是 `{"storyboard": {...}}`）。
别忘了给前端 `apps/web/src/lib/__tests__/` 加对应的解析测试。

## 7. 提 PR

- 从 `main` 开分支，PR 描述里写清：动了哪些文件、为什么、怎么验证的（贴命令和结果）。
- 会改变用户可见行为时，同步更新 `README.md` 与 `CHANGELOG.md`。
- CI 五个 job（frontend / go / python / migrations / dockerfiles）必须全绿。
- **不要提交**：`.env`、`*.log`、`node_modules`、`.next`、`.venv`、`screenshots/` 里的真实产品截图、任何用户数据。检查方法：`git status --porcelain | grep -v '^??' ` 之外，还要看 `git add -n .` 的输出。

## 8. 行为准则

参与讨论与提交请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。发现安全问题请按 [SECURITY.md](SECURITY.md) 私密报告，不要直接开公开 Issue。
