#!/usr/bin/env bash
# Provision one OITERU child device without storing its secret in config.json.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
    echo "Run this script with sudo: sudo scripts/provision_unit.sh" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_PATH="$PROJECT_DIR/config.json"
OWNER="${SUDO_USER:-root}"
OWNER_GROUP="$(id -gn "$OWNER")"
SECRET_DIR="/etc/oiteru"
SECRET_PATH="$SECRET_DIR/unit-secret"

read -r -p "Child device name: " UNIT_NAME
read -r -p "Parent URL (https://...): " SERVER_URL
read -r -s -p "Child device secret (16+ characters): " UNIT_SECRET
printf '\n'

if [[ -z "$UNIT_NAME" || -z "$SERVER_URL" ]]; then
    echo "Child device name and parent URL are required." >&2
    exit 1
fi
if [[ ${#UNIT_SECRET} -lt 16 ]]; then
    echo "Child device secret must contain at least 16 characters." >&2
    exit 1
fi
if [[ ! "$SERVER_URL" =~ ^https?://[^/]+(/.*)?$ ]]; then
    echo "Parent URL must start with http:// or https://." >&2
    exit 1
fi

install -d -m 0700 -o "$OWNER" -g "$OWNER_GROUP" "$SECRET_DIR"
umask 077
printf '%s\n' "$UNIT_SECRET" > "$SECRET_PATH"
chown "$OWNER:$OWNER_GROUP" "$SECRET_PATH"
chmod 0600 "$SECRET_PATH"

if [[ ! -f "$CONFIG_PATH" ]]; then
    cp "$PROJECT_DIR/config.example.json" "$CONFIG_PATH"
fi

python3 - "$CONFIG_PATH" "$SERVER_URL" "$UNIT_NAME" "$SECRET_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    config = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Cannot read {path}: {exc}")
if not isinstance(config, dict):
    raise SystemExit(f"{path} must contain one JSON object")
config.pop("UNIT_PASSWORD", None)
config.update({
    "SERVER_URL": sys.argv[2].rstrip("/"),
    "UNIT_NAME": sys.argv[3],
    "UNIT_SECRET_FILE": sys.argv[4],
})
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
chown "$OWNER:$OWNER_GROUP" "$CONFIG_PATH"
chmod 0600 "$CONFIG_PATH"

# A 404 means the parent is reachable and correctly keeps this unapproved
# device pending; any other connection failure must be resolved before start.
PAYLOAD_PATH="$(mktemp)"
trap 'rm -f "$PAYLOAD_PATH"' EXIT
UNIT_SECRET="$UNIT_SECRET" python3 - "$PAYLOAD_PATH" "$UNIT_NAME" <<'PY'
import json
import os
import sys

with open(sys.argv[1], "w", encoding="utf-8") as payload:
    json.dump({"unit_name": sys.argv[2], "unit_password": os.environ["UNIT_SECRET"]}, payload)
PY
HTTP_STATUS="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 5 --max-time 10 --header 'Content-Type: application/json' \
    --data-binary "@$PAYLOAD_PATH" "$SERVER_URL/api/unit/heartbeat" || true)"

if [[ "$HTTP_STATUS" != "200" && "$HTTP_STATUS" != "404" ]]; then
    echo "Parent authentication check failed (HTTP ${HTTP_STATUS:-connection error})." >&2
    exit 1
fi

echo "Provisioning completed."
echo "  public config: $CONFIG_PATH"
echo "  secret file:   $SECRET_PATH (mode $(stat -c '%a' "$SECRET_PATH"))"
echo "Ask an administrator to approve '$UNIT_NAME' before normal operation."
