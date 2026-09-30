#!/bin/bash
set -euo pipefail

# 加载 nvm 环境（如果用户安装了 nvm）。
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

echo "=============================="
echo "  🧙 Mago AIGC Platform 启动器"
echo "=============================="
echo ""

if ! command -v node >/dev/null 2>&1; then
    echo "❌ 找不到 node，请先安装 Node.js 20+（推荐使用 nvm）" >&2
    exit 1
fi
echo "✅ Node $(node --version)"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PNPM="$PROJECT_DIR/scripts/pnpm.sh"
if [ ! -x "$PNPM" ]; then
    echo "❌ 找不到项目 pnpm 启动器: $PNPM" >&2
    exit 1
fi
echo "✅ pnpm $($PNPM --version)"

# Pass commands to Terminal as arguments so project paths containing spaces,
# quotes, or Unicode characters remain valid shell commands.
run_terminal() {
  local command_text="$1"
  osascript - "$command_text" <<'APPLESCRIPT'
on run argv
  tell application "Terminal"
    activate
    do script (item 1 of argv)
  end tell
end run
APPLESCRIPT
}

# The application needs PostgreSQL and Redis. Start the minimum local stack
# when Docker is available; otherwise keep launching the UI and explain what
# is missing. Demo mode remains available without the infrastructure.
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "🐳 启动本地基础设施 (PostgreSQL / Redis / MinIO)..."
  if ! (cd "$PROJECT_DIR" && docker compose up -d postgres redis minio); then
    echo "⚠️ 基础设施启动失败，API 登录和项目数据可能不可用" >&2
  elif ! (cd "$PROJECT_DIR" && docker compose run --rm migrate); then
    echo "⚠️ 数据库迁移失败，API 登录和项目数据可能不可用" >&2
  else
    echo "✅ 数据库迁移完成"
  fi
else
  echo "⚠️ 未检测到可用的 Docker daemon；真实 API 需要 PostgreSQL 和 Redis。"
  echo "   没有后端依赖时，可在 apps/web/.env.local 设置 NEXT_PUBLIC_DEMO_MODE=true。"
fi

PROJECT_DIR_Q="$(printf '%q' "$PROJECT_DIR")"

if [ -x "$PROJECT_DIR/.tools/go/bin/go" ]; then
  GO_BIN="$PROJECT_DIR/.tools/go/bin/go"
elif command -v go >/dev/null 2>&1; then
  GO_BIN="$(command -v go)"
else
  GO_BIN=""
fi

if [ -n "$GO_BIN" ]; then
  GO_BIN_Q="$(printf '%q' "$GO_BIN")"
  echo "🚀 启动 Go API 网关 (端口 8080)..."
  if ! run_terminal "cd $PROJECT_DIR_Q/services/api-gateway && exec $GO_BIN_Q run ./cmd/server"; then
    echo "⚠️ 无法打开 Go API 终端；项目/登录 API 将不可用。" >&2
  fi
else
  echo "⚠️ 未找到 Go；项目/登录 API 将不可用。"
fi

if command -v uv >/dev/null 2>&1; then
  echo "🚀 启动 Python Agent 服务 (端口 8000)..."
  if ! run_terminal "cd $PROJECT_DIR_Q/services/agent && exec uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"; then
    echo "⚠️ 无法打开 Python Agent 终端；Agent 功能将不可用。" >&2
  fi

  echo "🚀 启动 Agent Worker (ARQ/Redis)..."
  if ! run_terminal "cd $PROJECT_DIR_Q/services/agent && exec uv run arq src.worker.WorkerSettings"; then
    echo "⚠️ 无法打开 Agent Worker 终端；热点抓取和视频分析任务将不可用。" >&2
  fi
else
  echo "⚠️ 未找到 uv；Agent 和 Worker 将不可用。"
fi

echo "🚀 启动 Next.js 前端 (端口 3000)..."
cd "$PROJECT_DIR/apps/web"
echo ""
echo "等待编译完成后浏览器自动打开 http://localhost:3000"
echo ""

(
    for i in {1..30}; do
        sleep 2
        if curl -fsS http://localhost:3000 >/dev/null 2>&1; then
            open http://localhost:3000
            echo "✅ 浏览器已打开 http://localhost:3000"
            break
        fi
    done
) &

exec "$PNPM" dev
