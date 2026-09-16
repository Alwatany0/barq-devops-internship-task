#!/usr/bin/env bash
set -euo pipefail

CONTAINER="postgres"
DATABASE="barq_tasks"
USER="barq_app"

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <backup.dump>" >&2
    exit 2
fi

BACKUP_FILE="$1"

if [[ ! -s "$BACKUP_FILE" ]]; then
    echo "FAIL: backup file does not exist or is empty: $BACKUP_FILE" >&2
    exit 1
fi

echo "=== BARQ POSTGRESQL RESTORE ==="
echo "Database: $DATABASE"
echo "Backup: $BACKUP_FILE"

docker cp "$BACKUP_FILE" "$CONTAINER:/tmp/restore.dump"

docker exec "$CONTAINER" pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --dbname="$DATABASE" \
    --username="$USER" \
    /tmp/restore.dump

docker exec "$CONTAINER" rm -f /tmp/restore.dump

echo "PASS: PostgreSQL restore completed"
