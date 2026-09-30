#!/bin/bash
# Seed demo data for Mago Agent Platform (development only).
set -euo pipefail

API_URL="${API_URL:-http://localhost:8080/api/v1}"
SEED_EMAIL="${SEED_EMAIL:-test@example.com}"
SEED_NAME="${SEED_NAME:-测试用户}"
SEED_PASSWORD="${SEED_PASSWORD:-test123456}"

echo "🌱 Seeding Mago Agent Platform demo data..."

# Wait for API to be ready and fail clearly instead of reporting a false success.
echo "Waiting for API to be ready..."
ready=0
for i in {1..30}; do
    if curl -fsS "$API_URL/health" > /dev/null; then
        echo "✅ API is ready"
        ready=1
        break
    fi
    sleep 2
done
if [ "$ready" -ne 1 ]; then
    echo "❌ API did not become ready within 60 seconds" >&2
    exit 1
fi

# This script is intentionally for local/demo environments. Never run it against
# a production API with the default password; override all SEED_* variables.
echo "Creating development demo user..."
payload="$(SEED_EMAIL="$SEED_EMAIL" SEED_NAME="$SEED_NAME" SEED_PASSWORD="$SEED_PASSWORD" python3 - <<'PY'
import json
import os

print(json.dumps({
    "email": os.environ["SEED_EMAIL"],
    "name": os.environ["SEED_NAME"],
    "password": os.environ["SEED_PASSWORD"],
}, ensure_ascii=False))
PY
)"
response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT
http_code="$(curl -sS -o "$response_file" -w '%{http_code}' -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "$payload")" || {
    echo "❌ Demo user registration request failed" >&2
    cat "$response_file" >&2 || true
    exit 1
}
case "$http_code" in
    2*)
        ;;
    409)
        echo "Demo user already exists; continuing"
        ;;
    *)
        echo "❌ Demo user registration failed with HTTP $http_code" >&2
        cat "$response_file" >&2 || true
        exit 1
        ;;
esac

echo ""
echo "✅ Demo data seed completed!"
echo "You can login with: $SEED_EMAIL / (the value of SEED_PASSWORD)"
echo ""
echo "Demo projects will be created automatically on first login"
