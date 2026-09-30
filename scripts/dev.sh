#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if command -v go >/dev/null 2>&1; then
    GO_BIN="$(command -v go)"
elif [ -x "$PROJECT_DIR/.tools/go/bin/go" ]; then
    GO_BIN="$PROJECT_DIR/.tools/go/bin/go"
else
    GO_BIN="go"
fi

echo "🧙 Mago Agent Platform - Development Mode"
echo "Starting infrastructure and preparing native service commands..."

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker CLI is required by scripts/dev.sh. Install Docker Desktop and retry." >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is installed but the Docker daemon is not reachable." >&2
    echo "   Start Docker Desktop (or the Docker daemon) and retry." >&2
    exit 1
fi

# Start infrastructure when any required dependency is not already running.
# Checking only PostgreSQL is insufficient: a stale Postgres container can make
# the old script skip Redis, MinIO, etcd, or Milvus and leave the app half-up.
infra_services=(postgres redis minio etcd milvus)
missing_infra=()
for service in "${infra_services[@]}"; do
    if ! docker compose ps --status running -q "$service" 2>/dev/null | grep -q .; then
        missing_infra+=("$service")
    fi
done
if ((${#missing_infra[@]} > 0)); then
    echo "Starting infrastructure containers: ${missing_infra[*]}"
    docker compose up -d "${infra_services[@]}"
fi

# Ensure the schema exists before local API/Agent processes start. The migrate
# service waits for PostgreSQL health and is safe to run repeatedly.
echo "Running database migrations..."
docker compose run --rm migrate

# Do not terminate processes here. This script can be run from a shared machine
# and a broad `pkill -f` pattern could stop unrelated projects. The commands
# below intentionally leave already-running application services untouched;
# start only the services you need in separate terminals.

echo ""
echo "Infrastructure is ready. Start each service in a separate terminal:"
echo ""
echo "  Terminal 1: cd apps/web && ../../scripts/pnpm.sh dev"
echo "  Terminal 2: cd services/api-gateway && \"$GO_BIN\" run ./cmd/server"
echo "  Terminal 3: cd services/agent && uv run python -m src.main"
echo "  Terminal 4: cd services/agent && uv run arq src.worker.WorkerSettings"
echo ""
echo "Frontend:  http://localhost:3000"
echo "API:       http://localhost:8080/api/v1/health"
echo "Agent:     http://localhost:8000/health"
