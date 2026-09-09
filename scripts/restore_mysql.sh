#!/usr/bin/env bash
# Restore an encrypted full OITERU MySQL backup. Run only in a maintenance window.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: OITERU_BACKUP_KEY=... $0 /path/to/oiteru-*.sql.gz.enc" >&2
    exit 1
fi
if [[ -z "${OITERU_BACKUP_KEY:-}" ]]; then
    echo "OITERU_BACKUP_KEY must be supplied via a protected environment variable." >&2
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="${OITERU_ENV_FILE:-$PROJECT_DIR/.env}"
BACKUP_PATH="$1"
[[ -f "$ENV_PATH" && -f "$BACKUP_PATH" ]] || { echo "Missing .env or backup file" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_PATH"
set +a

read -r -p "Restore $BACKUP_PATH into $MYSQL_DATABASE? Type RESTORE to continue: " CONFIRM
[[ "$CONFIRM" == "RESTORE" ]] || { echo "Cancelled."; exit 1; }

openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -md sha256 -pass env:OITERU_BACKUP_KEY -in "$BACKUP_PATH" \
    | gzip -dc \
    | MYSQL_PWD="$MYSQL_PASSWORD" mysql --host="${MYSQL_HOST:-localhost}" --port="${MYSQL_PORT:-3306}" --user="$MYSQL_USER"

echo "Restore completed. Run the smoke tests before resuming service."
