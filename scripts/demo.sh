#!/usr/bin/env bash
# 无 Docker / 无数据库的「演示模式」启动脚本：只拉起 Agent(8000) + 前端(3000)。
# 数据存在浏览器 localStorage，可完整体验 脚本 → 分镜 → 提示词包 → 导出。
# 用法：make demo  或  bash scripts/demo.sh          （前台，Ctrl+C 一起停）
#      DEMO_BG=1 bash scripts/demo.sh                 （后台，日志在 /tmp/mago-demo-*.log）
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

step() { printf '\n\033[36m▸ %s\033[0m\n' "$1"; }
die()  { printf '\n\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

command -v node >/dev/null 2>&1 || die "需要 Node.js 20+（前端）：https://nodejs.org/"
[ -d apps/web/node_modules ] || die "前端依赖未安装，请先执行：make install-web"

AGENT_READY=0
if [ -x services/agent/.venv/bin/python ]; then
    AGENT_READY=1
elif command -v uv >/dev/null 2>&1; then
    AGENT_READY=1
else
    step "未找到 uv / Agent venv：跳过 Agent，仅启动前端（AI 生成会降级为浏览器内置模板）"
    step "想要真正的服务端生成，请安装 uv 后执行：cd services/agent && uv sync"
fi

[ -f .env ] || { cp .env.example .env && step "已从 .env.example 创建 .env"; }

pids=()
cleanup() {
    step "正在停止演示模式进程…"
    for pid in "${pids[@]:-}"; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

if [ "$AGENT_READY" = "1" ]; then
    if port_busy 8000; then
        step "Agent 已在 :8000 运行，复用现有进程"
    else
        step "启动 Python Agent → http://localhost:8000/docs"
        if [ -x services/agent/.venv/bin/python ]; then
            ( cd services/agent && exec .venv/bin/python -m src.main ) > /tmp/mago-demo-agent.log 2>&1 &
        else
            ( cd services/agent && exec env UV_CACHE_DIR=/tmp/mago-uv-cache uv run python -m src.main ) > /tmp/mago-demo-agent.log 2>&1 &
        fi
        pids+=("$!")
    fi
fi

step "启动前端 → http://localhost:3000"
if port_busy 3000; then
    step "前端已在 :3000 运行，直接打开即可"
else
    ( cd apps/web && exec ../../scripts/pnpm.sh dev ) > /tmp/mago-demo-web.log 2>&1 &
    pids+=("$!")
fi

# 等服务端端口就绪后再打印入口，避免用户打开空白页。
for _ in $(seq 1 45); do
    if port_busy 3000 && { [ "$AGENT_READY" != "1" ] || port_busy 8000; }; then
        break
    fi
    sleep 1
done

cat <<EOT

========================================================
🚀 Mago 演示模式已启动
  前端      http://localhost:3000
  Agent API http://localhost:8000/docs$( [ "$AGENT_READY" = "1" ] || echo "（未启动）" )
  日志      /tmp/mago-demo-web.log /tmp/mago-demo-agent.log

第一次使用建议这样跑：
  1. 首页点「进入演示工作区」（无需注册，数据只存在你的浏览器）
  2. 新建项目 → 输入选题 → 生成脚本
  3. 脚本卡片里点「生成分镜」→ 得到镜头表
  4. 分镜卡片底部选模型 → 「生成提示词包」→ 复制 / 导出 Markdown·CSV·JSON
  5. 「成果库」里能看到全部已生成内容并可导出

要接真实数据库和团队账号，请改用 Docker：make docker-up && bash scripts/setup.sh
Ctrl+C 停止本脚本（复用的已有进程不会被停掉）。
========================================================
EOT

if [ "${DEMO_BG:-0}" = "1" ]; then
    trap - EXIT
    for pid in "${pids[@]:-}"; do [ -n "$pid" ] && disown "$pid" 2>/dev/null || true; done
    exit 0
fi

wait
