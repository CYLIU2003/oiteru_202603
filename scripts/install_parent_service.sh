#!/usr/bin/env bash
# OITERU 親機を systemd サービスとして導入・更新するスクリプト（本番 Linux 機用）
#
# 使い方:
#   sudo scripts/install_parent_service.sh             # 導入して起動（再実行すると更新）
#   sudo scripts/install_parent_service.sh --no-start  # 導入と自動起動の有効化だけ行う
#   scripts/install_parent_service.sh --dry-run        # 書き込まずに生成内容を表示する
#
# systemd/ 配下のテンプレートの @OITERU_USER@ と @OITERU_ROOT@ を、
# 実行した利用者とこのリポジトリのパスに置き換えて /etc/systemd/system へ配置します。
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
UNITS=(oiteru-card-reader.service oiteru-parent.service)
HEALTH_URL="http://localhost:5000/api/health"

service_user="${SUDO_USER:-$(id -un)}"
service_root="$PROJECT_ROOT"
dry_run=false
start_service=true

usage() {
    cat <<'USAGE'
Usage:
  sudo scripts/install_parent_service.sh [--user NAME] [--root PATH] [--no-start]
  scripts/install_parent_service.sh --dry-run [--user NAME] [--root PATH]

Options:
  --user NAME   サービスを実行する利用者（既定: sudo を実行した利用者）
  --root PATH   リポジトリの絶対パス（既定: このスクリプトのあるリポジトリ）
  --no-start    導入と自動起動の有効化だけ行い、今は起動しない
  --dry-run     何も書き込まず、生成される unit ファイルを表示する
USAGE
}

while [ $# -gt 0 ]; do
    case "$1" in
        --user) service_user="${2:?--user には利用者名が必要です}"; shift 2 ;;
        --root) service_root="${2:?--root にはパスが必要です}"; shift 2 ;;
        --no-start) start_service=false; shift ;;
        --dry-run) dry_run=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: 不明なオプション: $1" >&2; usage; exit 1 ;;
    esac
done

errors=0
fail() {
    echo "ERROR: $1" >&2
    errors=$((errors + 1))
}

# --- 入力チェック -----------------------------------------------------------
case "$service_root" in
    /*) ;;
    *) fail "--root は絶対パスで指定してください: $service_root" ;;
esac
if [[ "$service_root" =~ [[:space:]] ]]; then
    fail "リポジトリのパスに空白を含めないでください（systemd の ExecStart が壊れます）: $service_root"
fi
if [[ ! "$service_user" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
    fail "利用者名が不正です: $service_user"
fi
if [ "$service_user" = "root" ]; then
    fail "親機を root で動かさないでください。--user で一般利用者を指定してください"
fi

# --- 実行環境チェック（--dry-run では警告だけ） ------------------------------
check() {
    # check <条件コマンド...> -- <メッセージ>
    local message="${*: -1}"
    local condition=("${@:1:$#-2}")
    if ! "${condition[@]}"; then
        if $dry_run; then
            echo "WARNING: $message" >&2
        else
            fail "$message"
        fi
    fi
}

user_exists() { id "$1" >/dev/null 2>&1; }

check user_exists "$service_user" -- "利用者が存在しません: $service_user"
check test -x "$service_root/.venv/bin/gunicorn" -- \
    "$service_root/.venv/bin/gunicorn がありません。.venv を作り requirements.txt を入れてください"
check test -f "$service_root/.env" -- \
    "$service_root/.env がありません。.env.example をコピーして必須値を設定してください"
check test -f "$service_root/gunicorn.conf.py" -- "$service_root/gunicorn.conf.py がありません"

if [ "$errors" -gt 0 ]; then
    exit 1
fi

render() {
    sed -e "s|@OITERU_USER@|${service_user}|g" -e "s|@OITERU_ROOT@|${service_root}|g" \
        "$PROJECT_ROOT/systemd/$1"
}

if $dry_run; then
    for unit in "${UNITS[@]}"; do
        echo "### $SYSTEMD_DIR/$unit"
        render "$unit"
        echo
    done
    exit 0
fi

# --- 導入 --------------------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: sudo を付けて実行してください: sudo $0" >&2
    exit 1
fi

if command -v tmux >/dev/null 2>&1 \
    && sudo -u "$service_user" tmux has-session -t "${OITERU_TMUX_PREFIX:-oiteru}-parent" 2>/dev/null; then
    echo "ERROR: tmux で親機が動いています。ポート 5000 が衝突するため先に止めてください:" >&2
    echo "  scripts/tmux_oiteru.sh stop parent" >&2
    exit 1
fi

if ! systemctl cat mysql.service >/dev/null 2>&1; then
    echo "ERROR: mysql.service が見つかりません。先に scripts/setup_local_mysql.sh を実行してください" >&2
    exit 1
fi

timestamp="$(date +%Y%m%d%H%M%S)"
for unit in "${UNITS[@]}"; do
    target="$SYSTEMD_DIR/$unit"
    rendered="$(render "$unit")"
    if [ -f "$target" ] && [ "$(cat "$target")" != "$rendered" ]; then
        cp -p "$target" "$target.bak.$timestamp"
        echo "既存の $target を $target.bak.$timestamp に退避しました"
    fi
    printf '%s\n' "$rendered" > "$target"
    chmod 644 "$target"
    echo "配置しました: $target"
done

systemctl daemon-reload
systemctl enable mysql.service "${UNITS[@]}"
echo "自動起動を有効にしました: mysql ${UNITS[*]}"

if ! $start_service; then
    echo "起動はしていません。起動するには: sudo systemctl start oiteru-parent"
    exit 0
fi

systemctl restart oiteru-parent.service
echo "親機を起動しました。応答を待っています（最大 60 秒）..."
for _ in $(seq 1 20); do
    if curl -fsS --max-time 3 "$HEALTH_URL" >/dev/null 2>&1; then
        echo "OK: $HEALTH_URL が応答しました"
        systemctl --no-pager --lines=0 status oiteru-parent.service || true
        exit 0
    fi
    sleep 3
done

echo "ERROR: 60 秒以内に応答がありませんでした。ログを確認してください:" >&2
echo "  sudo journalctl -u oiteru-parent -n 100 --no-pager" >&2
exit 1
