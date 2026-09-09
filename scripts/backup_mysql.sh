#!/usr/bin/env bash
# Create an encrypted, transaction-consistent full OITERU MySQL backup.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="${OITERU_ENV_FILE:-$PROJECT_DIR/.env}"
BACKUP_DIR="${OITERU_BACKUP_DIR:-$PROJECT_DIR/backups}"

if [[ ! -f "$ENV_PATH" ]]; then
    echo "Missing environment file: $ENV_PATH" >&2
    exit 1
fi
if [[ -z "${OITERU_BACKUP_KEY:-}" ]]; then
    echo "OITERU_BACKUP_KEY must be supplied via a protected environment variable." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_PATH"
set +a

mkdir -p "$BACKUP_DIR"
chmod 0700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT="$BACKUP_DIR/oiteru-${STAMP}.sql.gz.enc"

MYSQL_PWD="$MYSQL_PASSWORD" mysqldump \
    --host="${MYSQL_HOST:-localhost}" \
    --port="${MYSQL_PORT:-3306}" \
    --user="$MYSQL_USER" \
    --single-transaction --routines --events --triggers \
    --databases "$MYSQL_DATABASE" \
    | gzip -c \
    | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -md sha256 -salt -pass env:OITERU_BACKUP_KEY \
    > "$OUTPUT"

chmod 0600 "$OUTPUT"
echo "Encrypted backup created: $OUTPUT"
