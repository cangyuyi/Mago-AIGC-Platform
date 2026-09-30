#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
PNPM="$PROJECT_DIR/scripts/pnpm.sh"
if command -v go >/dev/null 2>&1; then
    GO_BIN="$(command -v go)"
elif [ -x "$PROJECT_DIR/.tools/go/bin/go" ]; then
    GO_BIN="$PROJECT_DIR/.tools/go/bin/go"
else
    GO_BIN="go"
fi

echo "🧙 Mago Agent Platform - Development Environment Setup"
echo "======================================================"

# Check required tools
echo ""
echo "📋 Checking dependencies..."

MISSING=0

check_cmd() {
    if command -v $1 &> /dev/null; then
        echo "  ✅ $1: $($1 --version 2>&1 | head -1)"
    else
        echo "  ❌ $1: NOT FOUND"
        MISSING=$((MISSING+1))
    fi
}

check_cmd node
check_cmd python3
check_cmd uv
check_cmd docker
check_cmd curl
check_cmd ffmpeg
if [ "$GO_BIN" = "go" ] && ! command -v go >/dev/null 2>&1; then
    echo "  ❌ go: NOT FOUND"
    MISSING=$((MISSING+1))
else
    echo "  ✅ go: $("$GO_BIN" version 2>&1 | head -1)"
fi

if ! "$PNPM" --version >/dev/null 2>&1; then
    echo "  ❌ pnpm ${PNPM_VERSION:-9.15.0}: NOT FOUND (use Node.js 20+ with Corepack)"
    MISSING=$((MISSING+1))
else
    echo "  ✅ pnpm: $($PNPM --version)"
fi

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "⚠️  Missing $MISSING required tool(s). Please install them first."
    echo "   - node: https://nodejs.org/"
    echo "   - pnpm: npm install -g pnpm"
    echo "   - go: https://go.dev/dl/"
    echo "   - python3: https://www.python.org/"
    echo "   - uv: pip install uv"
    echo "   - docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo ""
    echo "❌ Docker is installed but the Docker daemon is not reachable." >&2
    echo "   Start Docker Desktop (or the Docker daemon) and run this script again." >&2
    exit 1
fi

# Copy env file
echo ""
echo "📝 Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✅ Created .env from .env.example"
else
    echo "  ⏭️  .env already exists, skipping"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."

echo "  [1/3] Workspace dependencies..."
"$PNPM" install --frozen-lockfile

echo "  [2/3] Go dependencies..."
cd services/api-gateway && "$GO_BIN" mod download && cd ../..

echo "  [3/3] Python agent dependencies..."
cd services/agent && uv sync && cd ../..

# Start infrastructure
echo ""
echo "🐳 Starting infrastructure (postgres/redis/minio/milvus)..."
docker compose up -d postgres redis minio etcd milvus

echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
db_ready=0
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-mago}" -d "${POSTGRES_DB:-mago}" > /dev/null 2>&1; then
        echo "  ✅ PostgreSQL is ready"
        db_ready=1
        break
    fi
    echo "  waiting... ($i/30)"
    sleep 2
done
if [ "$db_ready" -ne 1 ]; then
    echo "❌ PostgreSQL did not become ready within 60 seconds" >&2
    exit 1
fi

# Run migrations
echo ""
echo "🗄️ Running database migrations..."
# Use the pinned Goose container so setup does not depend on a host-installed
# goose binary or an incompatible local version.
docker compose run --rm migrate

# Seed database only when the API is already running. The setup script does
# not start local application processes; use `make dev-api` or Docker first.
echo ""
echo "🌱 Seeding database..."
if curl -fsS "${API_URL:-http://localhost:8080/api/v1}/health" > /dev/null 2>&1; then
    bash scripts/seed-db.sh
else
    echo "  ⏭️  API is not running; skipping demo-user seed (run 'make seed' after starting the API)"
fi

echo ""
echo "======================================================"
echo "✅ Setup complete!"
echo ""
echo "Start development servers:"
echo "  make dev-web    - Frontend (http://localhost:3000)"
echo "  make dev-api    - API Gateway (http://localhost:8080)"
echo "  make dev-agent  - Agent Service (http://localhost:8000)"
echo ""
echo "Or run everything in Docker:"
echo "  make docker-up"
echo ""
echo "Default test account:"
echo "  Email: test@example.com"
echo "  Password: test123456"
