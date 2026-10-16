#!/usr/bin/env bash
# 親機（本番）を見る・直すためのコマンドはこれ 1 本です。
# 親機は systemd サービス oiteru-parent として動き、PC を再起動しても自動で起動します。
#
#   scripts/parent.sh status    動いているか確認する（まずはこれ）
#   scripts/parent.sh restart   止まっていたら戻す
#   scripts/parent.sh logs      ログを見る（Ctrl-c で終了。親機は止まりません）
#   scripts/parent.sh install   初回と更新時だけ使う（先輩・開発担当向け）
#
# sudo を付けずに実行してください。必要なところでパスワードを聞かれます。
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="oiteru-parent"
UNITS=(oiteru-card-reader.service oiteru-parent.service)
SYSTEMD_DIR="/etc/systemd/system"
HEALTH_URL="http://127.0.0.1:5000/api/health"
TMUX_SESSION="${OITERU_TMUX_PREFIX:-oiteru}-parent"

usage() {
    cat <<'USAGE'
使い方: scripts/parent.sh <コマンド>

  status    親機が動いているか確認する（まずはこれ）
  restart   親機を再起動する（パスワードを聞かれます）
  logs      親機のログを見る（Ctrl-c で終了。親機は止まりません）
  install   親機を systemd サービスとして登録・更新する（初回と更新時だけ）
            --dry-run          何も書き込まず、登録する内容だけ表示する
            --user NAME        親機を動かす利用者（既定: 実行した人）
            --root PATH        リポジトリの場所（既定: このリポジトリ）
USAGE
}

ok()   { printf '  [OK]   %s\n' "$1"; }
ng()   { printf '  [NG]   %s\n' "$1"; }
warn() { printf '  [注意] %s\n' "$1"; }

health_ok() {
    curl --silent --fail --max-time 5 "$HEALTH_URL" 2>/dev/null | grep -Eq '"status": ?"ok"'
}

tmux_parent_running() {
    command -v tmux >/dev/null 2>&1 && tmux has-session -t "$TMUX_SESSION" 2>/dev/null
}

wait_for_health() {
    local _
    for _ in $(seq 1 30); do
        if health_ok; then
            return 0
        fi
        sleep 2
    done
    return 1
}

cmd_status() {
    local problems=0
    echo "親機の状態"

    if systemctl is-active --quiet "$SERVICE"; then
        ok "親機 ($SERVICE) は動いています"
    else
        ng "親機 ($SERVICE) は止まっています"
        problems=$((problems + 1))
    fi

    if systemctl is-active --quiet mysql; then
        ok "データベース (mysql) は動いています"
    else
        ng "データベース (mysql) は止まっています"
        problems=$((problems + 1))
    fi

    if health_ok; then
        ok "親機は応答しています"
    else
        ng "親機が応答しません ($HEALTH_URL)"
        problems=$((problems + 1))
    fi

    if tmux_parent_running; then
        warn "tmux でも親機が動いています。先輩に scripts/parent.sh install を頼んでください"
        problems=$((problems + 1))
    fi

    echo
    if [ "$problems" -eq 0 ]; then
        echo "問題ありません。"
    else
        echo "問題があります。scripts/parent.sh restart を試してください。"
        echo "それでも直らなければ、さわる前に先輩へ連絡してください（docs/runbook.md）。"
        return 1
    fi
}

cmd_restart() {
    sudo systemctl restart "$SERVICE"
    echo "再起動しました。応答を待っています（最大 60 秒）..."
    if wait_for_health; then
        echo "親機は応答しています。"
        return 0
    fi
    echo "60 秒待っても応答しません。scripts/parent.sh logs の画面を先輩に送ってください。" >&2
    return 1
}

cmd_logs() {
    sudo journalctl -u "$SERVICE" -n 100 -f --no-pager
}

cmd_install() {
    local service_user service_root dry_run=false errors=0
    service_user="$(id -un)"
    service_root="$PROJECT_ROOT"

    while [ $# -gt 0 ]; do
        case "$1" in
            --user) service_user="${2:?--user には利用者名が必要です}"; shift 2 ;;
            --root) service_root="${2:?--root にはパスが必要です}"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            *) echo "エラー: 不明なオプション: $1" >&2; usage; exit 1 ;;
        esac
    done

    fail() { echo "エラー: $1" >&2; errors=$((errors + 1)); }
    # 実行環境の不足は、--dry-run では注意だけにする
    need() {
        if $dry_run; then echo "注意: $1" >&2; else fail "$1"; fi
    }

    case "$service_root" in
        /*) ;;
        *) fail "--root は絶対パスで指定してください: $service_root" ;;
    esac
    if [[ "$service_root" =~ [[:space:]] ]]; then
        fail "リポジトリの場所に空白を含めないでください: $service_root"
    fi
    if [[ ! "$service_user" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
        fail "利用者名が正しくありません: $service_user"
    fi
    if [ "$service_user" = "root" ]; then
        fail "sudo を付けずに、親機を動かす一般ユーザーで実行してください"
    fi
    id "$service_user" >/dev/null 2>&1 || need "利用者が存在しません: $service_user"
    [ -x "$service_root/.venv/bin/gunicorn" ] \
        || need "$service_root/.venv/bin/gunicorn がありません。docs/setup.md の 1-3 を先に実行してください"
    [ -f "$service_root/.env" ] \
        || need "$service_root/.env がありません。docs/setup.md の 1-2 を先に実行してください"
    if [ "$errors" -gt 0 ]; then
        exit 1
    fi

    render() {
        sed -e "s|@OITERU_USER@|${service_user}|g" -e "s|@OITERU_ROOT@|${service_root}|g" \
            "$PROJECT_ROOT/systemd/$1"
    }

    local unit
    if $dry_run; then
        for unit in "${UNITS[@]}"; do
            echo "### $SYSTEMD_DIR/$unit"
            render "$unit"
            echo
        done
        return 0
    fi

    if ! systemctl cat mysql.service >/dev/null 2>&1; then
        echo "エラー: mysql.service がありません。先に scripts/setup_local_mysql.sh を実行してください" >&2
        exit 1
    fi

    local tmp timestamp
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    timestamp="$(date +%Y%m%d%H%M%S)"
    for unit in "${UNITS[@]}"; do
        render "$unit" > "$tmp/$unit"
        if [ -f "$SYSTEMD_DIR/$unit" ] && ! cmp -s "$tmp/$unit" "$SYSTEMD_DIR/$unit"; then
            sudo cp -p "$SYSTEMD_DIR/$unit" "$SYSTEMD_DIR/$unit.bak.$timestamp"
            echo "前の $unit を $unit.bak.$timestamp として残しました"
        fi
        sudo install -m 0644 "$tmp/$unit" "$SYSTEMD_DIR/$unit"
    done
    sudo systemctl daemon-reload

    # tmux で動いている親機があれば止める（ポート 5000 の取り合いを防ぐ）
    if tmux_parent_running; then
        echo "tmux で動いている親機を止めます。"
        "$PROJECT_ROOT/scripts/tmux_oiteru.sh" stop parent
    fi

    sudo systemctl enable mysql.service "${UNITS[@]}"
    sudo systemctl restart "$SERVICE"
    echo "登録しました。PC を再起動しても親機は自動で起動します。応答を待っています..."
    if ! wait_for_health; then
        echo "60 秒待っても応答しません。scripts/parent.sh logs で原因を確認してください。" >&2
        exit 1
    fi
    cmd_status
}

command="${1:-}"
[ $# -gt 0 ] && shift
case "$command" in
    status) cmd_status ;;
    restart) cmd_restart ;;
    logs) cmd_logs ;;
    install) cmd_install "$@" ;;
    -h|--help|help|"") usage ;;
    *)
        echo "エラー: 不明なコマンド: $command" >&2
        usage
        exit 1
        ;;
esac
