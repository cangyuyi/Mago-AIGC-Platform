#!/bin/bash
# PostgreSQL restore script
set -euo pipefail

: "${PG_PASSWORD:?Set PG_PASSWORD to the database password before restoring}"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.sql.gz> [target_db]"
    echo "Example: $0 /backups/postgres/mago_20260101_000000.sql.gz mago_restore"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-mago}"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-mago}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

gzip -t "$BACKUP_FILE"
export PGPASSWORD="$PG_PASSWORD"

echo "⚠️  This will overwrite database $TARGET_DB on $PG_HOST"
read -p "Are you sure? Type YES to continue: " confirm
if [ "$confirm" != "YES" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo "Restoring $BACKUP_FILE to $TARGET_DB..."
gunzip -c "$BACKUP_FILE" | psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$TARGET_DB"
echo "Restore completed successfully"
