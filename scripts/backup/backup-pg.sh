#!/bin/bash
# PostgreSQL backup script - runs daily via cron
set -euo pipefail
umask 077

: "${PG_PASSWORD:?Set PG_PASSWORD to the database password before running backups}"

BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-mago}"
PG_DB="${PG_DB:-mago}"
S3_PATH="${S3_PATH:-}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${PG_DB}_${TIMESTAMP}.sql.gz"
TEMP_FILE="${BACKUP_FILE}.tmp.$$"
trap 'rm -f "$TEMP_FILE"' EXIT

mkdir -p "$BACKUP_DIR"
export PGPASSWORD="$PG_PASSWORD"

echo "Starting backup of $PG_DB to $BACKUP_FILE"
pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$PG_DB" | gzip > "$TEMP_FILE"
gzip -t "$TEMP_FILE"
test -s "$TEMP_FILE"
mv "$TEMP_FILE" "$BACKUP_FILE"
echo "Backup completed: $(du -h "$BACKUP_FILE" | cut -f1)"

# Upload to S3/MinIO if configured
if [ -n "$S3_PATH" ] && command -v aws &> /dev/null; then
    echo "Uploading to $S3_PATH"
    aws s3 cp "$BACKUP_FILE" "$S3_PATH/"
    echo "Upload completed"
fi

# Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +"$RETENTION_DAYS" -delete
echo "Backup process finished successfully"
