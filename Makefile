# Mago Agent Platform - Unified Makefile
# Usage: make <target>

.PHONY: help install dev build lint test clean wait-db migrate-up migrate-down migrate-status migrate-create seed \
docker-up docker-down docker-logs docker-restart docker-rebuild docker-min docker-min-down logs \
test-web test-api test-api-race test-agent install-web install-api install-agent \
build-web build-api build-agent lint-web lint-api lint-agent \
dev-web dev-api dev-agent dev-agent-worker setup-env doctor demo smoke

# ===== Configuration =====
WEB_DIR := apps/web
API_DIR := services/api-gateway
AGENT_DIR := services/agent
DOCKER_COMPOSE := docker compose -f docker-compose.yml
PNPM ?= "$(CURDIR)/scripts/pnpm.sh"
# Prefer a host Go toolchain, then fall back to the repository-pinned binary.
# The quotes on each invocation are intentional: this repository commonly lives
# under an iCloud path containing spaces.
GO ?= $(shell if command -v go >/dev/null 2>&1; then command -v go; elif [ -x "$(CURDIR)/.tools/go/bin/go" ]; then printf '%s/.tools/go/bin/go' "$(CURDIR)"; else printf 'go'; fi)
# Keep generated coverage outside iCloud/synced workspaces, which may reject writes.
COVERAGE_FILE ?= /tmp/mago-api-coverage.out
# Keep uv cache outside protected home directories when the repo is synced.
UV_CACHE_DIR ?= /tmp/mago-uv-cache

# ===== Help =====
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ===== Install =====
install: install-web install-api install-agent ## Install all dependencies

install-web: ## Install frontend dependencies
	$(PNPM) install --filter mago-agent-web...

install-api: ## Install Go dependencies
	cd $(API_DIR) && "$(GO)" mod download

install-agent: ## Install Python agent dependencies
	cd $(AGENT_DIR) && UV_CACHE_DIR="$(UV_CACHE_DIR)" uv sync

# ===== First run =====
setup-env: ## Create .env from .env.example when missing
	@if [ -f .env ]; then echo ".env already exists - leaving it untouched"; \
	else cp .env.example .env && echo "Created .env - fill in your LLM API keys before using AI features"; fi

doctor: ## Check local toolchain and service ports, report what is missing
	@bash scripts/doctor.sh

smoke: ## End-to-end smoke test against a running Agent (no DB, no LLM key needed)
	@python3 scripts/smoke_journey.py --agent $${AGENT_URL:-http://localhost:8000} $${SMOKE_WEB:+--web $$SMOKE_WEB}

demo: ## Start Agent + Web with no Docker/DB (browser-only persistence)
	@bash scripts/demo.sh

# ===== Development =====
wait-db: ## Wait until PostgreSQL accepts connections
	@until docker compose exec -T postgres pg_isready -U $${POSTGRES_USER:-mago} -d $${POSTGRES_DB:-mago} >/dev/null 2>&1; do echo "Waiting for PostgreSQL..."; sleep 2; done

dev: ## Start all services in development mode (requires docker for infrastructure, local for apps)
	@echo "Starting infrastructure..."
	$(DOCKER_COMPOSE) up -d postgres redis minio milvus etcd
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5
	@echo "Running migrations..."
	$(MAKE) migrate-up
	@echo "Starting all services (run in separate terminals for hot reload):"
	@echo "  make dev-web    - Start Next.js frontend"
	@echo "  make dev-api    - Start Go API gateway"
	@echo "  make dev-agent  - Start Python agent API service"
	@echo "  make dev-agent-worker - Start ARQ worker for long-running tasks"

dev-web: ## Start Next.js dev server
	cd $(WEB_DIR) && $(PNPM) dev

dev-api: ## Start Go API (uses air for hot reload when installed)
	cd $(API_DIR) && if command -v air >/dev/null 2>&1; then air -c .air.toml; else echo "air not found; starting with go run (no hot reload)"; "$(GO)" run ./cmd/server; fi

dev-agent: ## Start Python agent with hot reload
	cd $(AGENT_DIR) && UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run python -m src.main

dev-agent-worker: ## Start ARQ worker for long-running tasks
	cd $(AGENT_DIR) && UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run arq src.worker.WorkerSettings

# ===== Build =====
build: build-web build-api build-agent ## Build all services

build-web: ## Build frontend
	cd $(WEB_DIR) && $(PNPM) build

build-api: ## Build Go API
	cd $(API_DIR) && CGO_ENABLED=0 "$(GO)" build -o bin/server ./cmd/server/

build-agent: ## Build Python agent (check syntax only)
	cd $(AGENT_DIR) && UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run python -c "import src.main; print('OK')"

# ===== Lint =====
lint: lint-web lint-api lint-agent ## Lint all services

lint-web: ## Lint frontend
	cd $(WEB_DIR) && $(PNPM) lint

lint-api: ## Lint Go API (uses the standard Go toolchain)
	cd $(API_DIR) && "$(GO)" vet ./...

lint-agent: ## Lint Python agent
	cd $(AGENT_DIR) && UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run ruff check src/ tests/
	cd $(AGENT_DIR) && UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run mypy src/ --check-untyped-defs

# ===== Test =====
test: check-web test-api test-agent ## Test all services

test-web: ## Test frontend (vitest unit + component tests)
	cd $(WEB_DIR) && $(PNPM) test

check-web: ## Validate frontend (typecheck + lint + tests)
	cd $(WEB_DIR) && $(PNPM) typecheck
	cd $(WEB_DIR) && $(PNPM) lint
	$(MAKE) test-web


# CGO_ENABLED=0 is required on machines without a C toolchain, but the race
# detector needs cgo - keep the default path race-free and use test-api-race
# (CGO_ENABLED=1) locally or in CI where gcc exists.
test-api: ## Test Go API
	cd $(API_DIR) && GOCACHE=$${GOCACHE:-/tmp/mago-go-cache} CGO_ENABLED=0 "$(GO)" test -count=1 -coverprofile="$(COVERAGE_FILE)" ./...

test-api-race: ## Test Go API with the race detector (requires a C toolchain)
	cd $(API_DIR) && GOCACHE=$${GOCACHE:-/tmp/mago-go-cache} CGO_ENABLED=1 "$(GO)" test -count=1 -race ./...

test-agent: ## Test Python agent
	cd $(AGENT_DIR) && if [ -x .venv/bin/pytest ]; then PYTHONPYCACHEPREFIX=/tmp/mago-agent-pycache .venv/bin/pytest tests/ -v --tb=short -o cache_dir=/tmp/mago-agent-pytest-cache; else UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run pytest tests/ -v --tb=short -o cache_dir=/tmp/mago-agent-pytest-cache; fi

# ===== Database =====
# Use the pinned Goose service so developers do not need a host-installed
# binary, and use the Compose service name `postgres` from inside the network.
GOOSE_DB_URL := postgresql://$${POSTGRES_USER:-mago}:$${POSTGRES_PASSWORD_URLENCODED:-$${POSTGRES_PASSWORD:-mago_secret}}@postgres:5432/$${POSTGRES_DB:-mago}?sslmode=disable

migrate-up: ## Run database migrations
	$(DOCKER_COMPOSE) run --rm migrate

migrate-down: ## Rollback last migration
	$(DOCKER_COMPOSE) run --rm --entrypoint goose migrate -dir /migrations postgres "$(GOOSE_DB_URL)" down

migrate-status: ## Show migration status
	$(DOCKER_COMPOSE) run --rm --entrypoint goose migrate -dir /migrations postgres "$(GOOSE_DB_URL)" status

migrate-create: ## Create new migration: make migrate-create name=add_table
	cd $(API_DIR) && goose -dir migrations create $(name) sql

seed: ## Run database seed script
	bash scripts/seed-db.sh

# ===== Docker =====
docker-up: ## Start all services with docker compose
	$(DOCKER_COMPOSE) up -d --build

# Milvus + etcd need ~4GB of RAM and are only required for the trend/RAG
# features, so this overlay starts just Postgres, Redis and MinIO.
DOCKER_COMPOSE_MIN := docker compose -f docker-compose.min.yml

docker-min: ## Start only Postgres + Redis + MinIO (no Milvus, lighter laptop)
	$(DOCKER_COMPOSE_MIN) up -d
	@echo "Next: make migrate-up (needs the full compose file) or point DATABASE_URL at localhost:5432"

docker-min-down: ## Stop the lightweight infrastructure stack
	$(DOCKER_COMPOSE_MIN) down

docker-down: ## Stop all services
	$(DOCKER_COMPOSE) down

docker-logs: ## Show docker logs
	$(DOCKER_COMPOSE) logs -f

docker-restart: docker-down docker-up ## Restart all services

docker-rebuild: ## Rebuild all images
	$(DOCKER_COMPOSE) build --no-cache

# ===== Clean =====
clean: ## Clean build artifacts
	rm -rf $(WEB_DIR)/.next
	rm -rf $(WEB_DIR)/node_modules
	rm -rf $(API_DIR)/bin
	rm -rf $(AGENT_DIR)/.venv
	rm -rf $(AGENT_DIR)/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
