#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${OITERU_ENV_FILE:-$PROJECT_ROOT/.env}"

usage() {
    cat <<'USAGE'
Usage:
  scripts/setup_local_mysql.sh [--install]

This script prepares a local MySQL database and user for OITERU.
It reads MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, and MYSQL_PORT
from .env without using Docker.

Options:
  --install   Install mysql-server with apt before setup.
USAGE
}

read_env() {
    local key="$1"
    local default="${2:-}"
    local value
    value="$(
        awk -F= -v key="$key" '
            $0 !~ /^[[:space:]]*#/ && $1 == key {
                sub(/^[^=]*=/, "")
                gsub(/^[[:space:]]+|[[:space:]]+$/, "")
                gsub(/^"|"$/, "")
                gsub(/^'\''|'\''$/, "")
                print
                exit
            }
        ' "$ENV_FILE"
    )"
    if [ -n "$value" ]; then
        printf '%s' "$value"
    else
        printf '%s' "$default"
    fi
}

sql_quote() {
    printf "%s" "$1" | sed "s/'/''/g"
}

sql_ident() {
    printf "%s" "$1" | sed 's/`/``/g'
}

install_mysql=false
case "${1:-}" in
    --install) install_mysql=true ;;
    -h|--help) usage; exit 0 ;;
    "") ;;
    *) echo "ERROR: unknown option: $1" >&2; usage; exit 1 ;;
esac

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env is missing: $ENV_FILE" >&2
    echo "Run: cp .env.example .env" >&2
    exit 1
fi

if [ "$install_mysql" = true ]; then
    sudo apt update
    sudo apt install -y mysql-server
fi

if ! command -v mysql >/dev/null 2>&1; then
    echo "ERROR: mysql command is not installed." >&2
    echo "Run: sudo apt install -y mysql-server" >&2
    exit 1
fi

MYSQL_HOST_VALUE="$(read_env MYSQL_HOST localhost)"
MYSQL_PORT_VALUE="$(read_env MYSQL_PORT 3306)"
MYSQL_DATABASE_VALUE="$(read_env MYSQL_DATABASE oiteru)"
MYSQL_USER_VALUE="$(read_env MYSQL_USER oiteru_user)"
MYSQL_PASSWORD_VALUE="$(read_env MYSQL_PASSWORD)"

if [ -z "$MYSQL_PASSWORD_VALUE" ] || [ "$MYSQL_PASSWORD_VALUE" = "change-this-mysql-password" ]; then
    echo "ERROR: MYSQL_PASSWORD in .env must be changed before setup." >&2
    exit 1
fi

if [ "$MYSQL_HOST_VALUE" != "localhost" ] && [ "$MYSQL_HOST_VALUE" != "127.0.0.1" ]; then
    echo "ERROR: setup_local_mysql.sh is for local MySQL only. MYSQL_HOST=$MYSQL_HOST_VALUE" >&2
    exit 1
fi

sudo systemctl enable mysql >/dev/null 2>&1 || true
sudo systemctl start mysql

db_ident="$(sql_ident "$MYSQL_DATABASE_VALUE")"
user_sql="$(sql_quote "$MYSQL_USER_VALUE")"
pass_sql="$(sql_quote "$MYSQL_PASSWORD_VALUE")"

sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`$db_ident\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$user_sql'@'localhost' IDENTIFIED BY '$pass_sql';
ALTER USER '$user_sql'@'localhost' IDENTIFIED BY '$pass_sql';
CREATE USER IF NOT EXISTS '$user_sql'@'127.0.0.1' IDENTIFIED BY '$pass_sql';
ALTER USER '$user_sql'@'127.0.0.1' IDENTIFIED BY '$pass_sql';
GRANT ALL PRIVILEGES ON \`$db_ident\`.* TO '$user_sql'@'localhost';
GRANT ALL PRIVILEGES ON \`$db_ident\`.* TO '$user_sql'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

mysql \
    -h "$MYSQL_HOST_VALUE" \
    -P "$MYSQL_PORT_VALUE" \
    -u "$MYSQL_USER_VALUE" \
    -p"$MYSQL_PASSWORD_VALUE" \
    "$MYSQL_DATABASE_VALUE" \
    -e "SELECT 'OITERU local MySQL is ready' AS status;"

echo "Local MySQL setup completed."
echo "Next: scripts/tmux_oiteru.sh start parent"
