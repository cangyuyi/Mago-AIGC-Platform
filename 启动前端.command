#!/bin/bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PNPM="$PROJECT_DIR/scripts/pnpm.sh"
cd "$PROJECT_DIR/apps/web"
echo "=== Mago Agent 前端启动中 ==="
echo "目录: $(pwd)"
echo ""
if [ ! -x "$PNPM" ]; then
    echo "❌ 找不到项目启动器: $PNPM" >&2
    exit 1
fi
echo "✅ pnpm $($PNPM --version)"
echo "🚀 启动 Next.js 开发服务器..."
echo "启动后请打开 http://localhost:3000（若端口被占用，Next.js 会提示实际端口）"
echo ""
exec "$PNPM" dev
