#!/usr/bin/env bash
#
# Back up the Phoenix database from the phoenix-db container.
#
#   scripts/backup-db.sh [DIR] [KEEP]     default: ./backups, keep the newest 14
#
# Writes a compressed custom-format dump (pg_dump -Fc). Example cron line,
# daily at 03:20:
#   20 3 * * * cd /srv/phoenix && scripts/backup-db.sh >> backups/backup.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="${1:-$ROOT/backups}"
KEEP="${2:-14}"
CONTAINER="${PHOENIX_DB_CONTAINER:-phoenix-db}"

env_get() { grep -E "^$1=" "$ROOT/.env" 2>/dev/null | tail -n1 | cut -d= -f2- || true; }
USER_NAME="$(env_get POSTGRES_USER)"; USER_NAME="${USER_NAME:-phoenix}"
DB_NAME="$(env_get POSTGRES_DB)"; DB_NAME="${DB_NAME:-phoenix_db}"

docker inspect "$CONTAINER" >/dev/null 2>&1 || { echo "Container $CONTAINER is not running" >&2; exit 1; }
mkdir -p "$DIR"
chmod 700 "$DIR"

file="$DIR/phoenix-$(date -u +%Y%m%dT%H%M%SZ).dump"
tmp="$file.partial"
docker exec "$CONTAINER" pg_dump -U "$USER_NAME" -d "$DB_NAME" -Fc >"$tmp"
# A dump that pg_restore cannot list is not a backup
docker exec -i "$CONTAINER" pg_restore --list >/dev/null <"$tmp"
mv "$tmp" "$file"
chmod 600 "$file"
echo "Backup written: $file ($(du -h "$file" | cut -f1))"

# Keep only the newest KEEP dumps
ls -1t "$DIR"/phoenix-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  rm -f "$old" && echo "Removed old backup: $old"
done
