#!/usr/bin/env bash
#
# Restore a backup made by scripts/backup-db.sh into the phoenix-db container.
# This REPLACES the current data.
#
#   scripts/restore-db.sh backups/phoenix-20261102T032000Z.dump --yes
#
# Stop the API first so nothing writes during the restore:
#   docker stop phoenix-api   (start it again afterwards)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILE="${1:-}"
CONFIRM="${2:-}"
CONTAINER="${PHOENIX_DB_CONTAINER:-phoenix-db}"

[[ -f "$FILE" ]] || { echo "Usage: $0 <backup.dump> --yes" >&2; exit 1; }
if [[ "$CONFIRM" != "--yes" ]]; then
  echo "This replaces all data in the database with $FILE." >&2
  echo "Run again with --yes to continue." >&2
  exit 1
fi

env_get() { grep -E "^$1=" "$ROOT/.env" 2>/dev/null | tail -n1 | cut -d= -f2- || true; }
USER_NAME="$(env_get POSTGRES_USER)"; USER_NAME="${USER_NAME:-phoenix}"
DB_NAME="$(env_get POSTGRES_DB)"; DB_NAME="${DB_NAME:-phoenix_db}"

docker exec -i "$CONTAINER" pg_restore -U "$USER_NAME" -d "$DB_NAME" --clean --if-exists --no-owner <"$FILE"
echo "Restored $FILE into $DB_NAME. Start the API again if you stopped it."
