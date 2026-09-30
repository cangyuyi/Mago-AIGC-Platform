#!/usr/bin/env bash
# 只读体检脚本：不安装、不启动、不修改任何东西。
# 用法：make doctor  或  bash scripts/doctor.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }
h2()   { printf '\n%s\n' "$1"; }

BLOCKERS=0

if command -v go >/dev/null 2>&1; then
    GO_BIN="$(command -v go)"
elif [ -x "$PROJECT_DIR/.tools/go/bin/go" ]; then
    GO_BIN="$PROJECT_DIR/.tools/go/bin/go"
else
    GO_BIN=""
fi

h2 "工具链"
if command -v node >/dev/null 2>&1; then
    NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
    if [ "$NODE_MAJOR" -ge 20 ] 2>/dev/null; then
        ok "Node.js $(node --version)（前端需要 20+）"
    else
        bad "Node.js $(node --version) 过低，前端需要 20+（建议 nvm install 20）"
        BLOCKERS=$((BLOCKERS + 1))
    fi
else
    bad "未安装 Node.js → https://nodejs.org/"
    BLOCKERS=$((BLOCKERS + 1))
fi

if ./scripts/pnpm.sh --version >/dev/null 2>&1; then
    ok "pnpm $(./scripts/pnpm.sh --version 2>/dev/null)（经 scripts/pnpm.sh）"
else
    bad "pnpm 不可用：装好 Node 20+ 后执行 corepack enable"
    BLOCKERS=$((BLOCKERS + 1))
fi

# Agent 需要 Python 3.11+。有 uv 时它会自动准备解释器，系统版本低也不算阻塞。
if command -v python3 >/dev/null 2>&1; then
    PY_VER="$(python3 -c 'import sys;print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo 0.0)"
    PY_MAJOR="${PY_VER%%.*}"
    PY_MINOR="${PY_VER##*.}"
    if { [ "$PY_MAJOR" -gt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 11 ]; }; } 2>/dev/null; then
        ok "Python $PY_VER"
    elif command -v uv >/dev/null 2>&1; then
        warn "系统 Python $PY_VER 偏低，但 uv 会为 Agent 自动准备 3.11+ 解释器（无需手动升级）"
    elif [ -x services/agent/.venv/bin/python ]; then
        warn "系统 Python $PY_VER 偏低，Agent 使用自带 venv：$(services/agent/.venv/bin/python -V 2>&1 | awk '{print $2}')"
    else
        bad "Python $PY_VER 低于 Agent 要求的 3.11，且没有 uv/venv → 先装 uv：pip install uv"
        BLOCKERS=$((BLOCKERS + 1))
    fi
else
    bad "未安装 Python（Agent 服务需要 3.11+，或用 uv 自动管理）"
    BLOCKERS=$((BLOCKERS + 1))
fi

if command -v uv >/dev/null 2>&1; then
    ok "uv（Agent 依赖管理）"
elif [ -x "$PROJECT_DIR/services/agent/.venv/bin/python" ]; then
    warn "没有 uv，但 services/agent/.venv 已存在：可直接用 .venv/bin/python -m src.main"
else
    bad "未安装 uv 且没有现成 venv → pip install uv（或 brew install uv）"
    BLOCKERS=$((BLOCKERS + 1))
fi

if [ -n "$GO_BIN" ]; then
    ok "Go $("$GO_BIN" version 2>&1 | awk '{print $3}')（仅 Go API 网关需要）"
else
    warn "未找到 Go（含 .tools/go）：可以只用 Agent + 前端，Go API 与登录入库功能不可用"
fi

h2 "配置与依赖"
if [ -f .env ]; then
    ok ".env 存在"
    HAS_KEY=0
    for key in OPENAI_API_KEY ANTHROPIC_API_KEY GOOGLE_API_KEY DEEPSEEK_API_KEY; do
        val="$(grep -E "^${key}=..*" .env | head -1 || true)"
        [ -n "$val" ] && HAS_KEY=1
    done
    if [ "$HAS_KEY" -eq 1 ]; then
        ok "已配置至少一个 LLM API Key"
    else
        warn ".env 里没有任何 LLM API Key：脚本/分镜会走内置模板，仍可用，但文案较模板化"
    fi
    if grep -qE "^JWT_SECRET=change_this" .env; then
        warn "JWT_SECRET 仍是示例值：本地无妨，上线前必须换成 >=32 位随机串"
    fi
else
    warn "缺少 .env → make setup-env（会从 .env.example 复制）"
fi

[ -d apps/web/node_modules ] && ok "apps/web 依赖已安装" || bad "apps/web 依赖未安装 → make install-web"
if [ -x services/agent/.venv/bin/python ] || command -v uv >/dev/null 2>&1; then
    ok "Agent 依赖可就绪（.venv 或 uv）"
fi

h2 "服务端口"
check_port() { # $1=port $2=name $3=expected(up|down)
    if lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; then
        ok "$2 正在监听 :$1"
    else
        printf '  · %s 未运行（:%s）\n' "$2" "$1"
    fi
}
check_port 3000 "前端 Next.js"
check_port 8000 "Python Agent"
check_port 8080 "Go API 网关"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 9000 "MinIO"

h2 "Docker（可选：完整栈才需要）"
if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        ok "Docker 可用：make docker-up（完整栈）或 make docker-min（只要 PG+Redis+MinIO）"
    else
        warn "Docker 已安装但守护进程未启动（打开 Docker Desktop 即可）"
    fi
else
    warn "未安装 Docker：可用演示模式跑通主链路 → bash scripts/demo.sh"
fi

h2 "结论"
if [ "$BLOCKERS" -eq 0 ]; then
    ok "关键工具链齐备。日常开发：make dev-agent + make dev-web"
else
    bad "有 $BLOCKERS 项阻塞，先按上面的提示补齐"
fi
exit 0
