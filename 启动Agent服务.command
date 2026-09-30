#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$PROJECT_DIR/services/agent"
cd "$AGENT_DIR"

echo "=== Mago Agent 服务启动中 ==="
echo "目录: $(pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "❌ 找不到 uv。请先安装：https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

# Pass the command as an AppleScript argument rather than interpolating it into
# source code. `printf %q` makes paths with spaces, quotes, or other shell
# characters safe for the Terminal shell.
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

AGENT_DIR_Q="$(printf '%q' "$AGENT_DIR")"
if ! run_terminal "cd $AGENT_DIR_Q && exec uv run arq src.worker.WorkerSettings"; then
  echo "⚠️ 无法打开 Agent Worker 终端；热点抓取和视频分析任务将不可用。" >&2
fi

exec uv run python -m src.main
