#!/usr/bin/env bash
set -euo pipefail

CONTAINER="postgres"
DATABASE="barq_tasks"
USER="barq_app"
BACKUP_DIR="backups"

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="$BACKUP_DIR/barq_tasks_${TIMESTAMP}.dump"

echo "=== BARQ POSTGRESQL BACKUP ==="
echo "Database: $DATABASE"
echo "Output: $BACKUP_FILE"

docker exec "$CONTAINER" pg_dump \
    -U "$USER" \
    -d "$DATABASE" \
    -Fc \
    > "$BACKUP_FILE"

if [[ ! -s "$BACKUP_FILE" ]]; then
    echo "FAIL: backup file was not created or is empty" >&2
    exit 1
fi

echo "PASS: PostgreSQL backup created"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
