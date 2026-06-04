#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_PREFIX="${OITERU_TMUX_PREFIX:-oiteru}"

usage() {
    cat <<'USAGE'
Usage:
  scripts/tmux_oiteru.sh start parent|unit|sub-parent
  scripts/tmux_oiteru.sh stop parent|unit|sub-parent
  scripts/tmux_oiteru.sh restart parent|unit|sub-parent
  scripts/tmux_oiteru.sh attach parent|unit|sub-parent
  scripts/tmux_oiteru.sh status [parent|unit|sub-parent]
  scripts/tmux_oiteru.sh logs parent|unit|sub-parent

Environment:
  OITERU_TMUX_PREFIX  tmux session prefix (default: oiteru)

Examples:
  scripts/tmux_oiteru.sh start parent
  scripts/tmux_oiteru.sh attach parent
  scripts/tmux_oiteru.sh status
USAGE
}

require_tmux() {
    if ! command -v tmux >/dev/null 2>&1; then
        echo "ERROR: tmux is not installed. Run: sudo apt install -y tmux" >&2
        exit 1
    fi
}

role_to_mode() {
    case "${1:-}" in
        parent) echo "parent-mysql" ;;
        unit) echo "unit" ;;
        sub-parent) echo "sub-parent" ;;
        *) return 1 ;;
    esac
}

session_name() {
    case "${1:-}" in
        parent) echo "${SESSION_PREFIX}-parent" ;;
        unit) echo "${SESSION_PREFIX}-unit" ;;
        sub-parent) echo "${SESSION_PREFIX}-sub-parent" ;;
        *) return 1 ;;
    esac
}

session_exists() {
    tmux has-session -t "$1" 2>/dev/null
}

ensure_files_for_role() {
    local role="$1"
    if [ ! -x "$PROJECT_ROOT/venv-start.sh" ]; then
        echo "ERROR: venv-start.sh is missing or not executable." >&2
        echo "Run: chmod +x venv-start.sh" >&2
        exit 1
    fi

    if [ "$role" = "parent" ] || [ "$role" = "sub-parent" ]; then
        if [ ! -f "$PROJECT_ROOT/.env" ]; then
            echo "ERROR: .env is missing. Run: cp .env.example .env" >&2
            exit 1
        fi
    fi

    if [ "$role" = "unit" ] && [ ! -f "$PROJECT_ROOT/config.json" ]; then
        echo "ERROR: config.json is missing. Run: cp config.example.json config.json" >&2
        exit 1
    fi
}

start_role() {
    local role="$1"
    local mode session log_file
    mode="$(role_to_mode "$role")" || {
        echo "ERROR: unknown role: $role" >&2
        usage
        exit 1
    }
    session="$(session_name "$role")"
    log_file="$PROJECT_ROOT/logs/${session}.log"

    ensure_files_for_role "$role"
    mkdir -p "$PROJECT_ROOT/logs"

    if session_exists "$session"; then
        echo "tmux session already exists: $session"
        echo "Attach: scripts/tmux_oiteru.sh attach $role"
        return 0
    fi

    tmux new-session -d -s "$session" -c "$PROJECT_ROOT" \
        "bash -lc './venv-start.sh $mode 2>&1 | tee -a \"$log_file\"'"

    echo "Started: $session"
    echo "Attach: scripts/tmux_oiteru.sh attach $role"
    echo "Logs:   scripts/tmux_oiteru.sh logs $role"
}

stop_role() {
    local role="$1"
    local session
    session="$(session_name "$role")" || {
        echo "ERROR: unknown role: $role" >&2
        usage
        exit 1
    }

    if session_exists "$session"; then
        tmux send-keys -t "$session" C-c
        sleep 1
        tmux kill-session -t "$session" 2>/dev/null || true
        echo "Stopped: $session"
    else
        echo "Not running: $session"
    fi
}

attach_role() {
    local role="$1"
    local session
    session="$(session_name "$role")" || {
        echo "ERROR: unknown role: $role" >&2
        usage
        exit 1
    }

    if ! session_exists "$session"; then
        echo "ERROR: tmux session is not running: $session" >&2
        exit 1
    fi

    tmux attach -t "$session"
}

status_role() {
    local role="${1:-}"
    if [ -n "$role" ]; then
        local session
        session="$(session_name "$role")" || {
            echo "ERROR: unknown role: $role" >&2
            usage
            exit 1
        }
        if session_exists "$session"; then
            echo "running: $session"
        else
            echo "stopped: $session"
        fi
        return 0
    fi

    for role in parent unit sub-parent; do
        status_role "$role"
    done
}

logs_role() {
    local role="$1"
    local session log_file
    session="$(session_name "$role")" || {
        echo "ERROR: unknown role: $role" >&2
        usage
        exit 1
    }
    log_file="$PROJECT_ROOT/logs/${session}.log"
    if [ ! -f "$log_file" ]; then
        echo "No log file yet: $log_file"
        return 0
    fi
    tail -f "$log_file"
}

main() {
    require_tmux

    local command="${1:-}"
    local role="${2:-}"

    case "$command" in
        start)
            [ -n "$role" ] || { usage; exit 1; }
            start_role "$role"
            ;;
        stop)
            [ -n "$role" ] || { usage; exit 1; }
            stop_role "$role"
            ;;
        restart)
            [ -n "$role" ] || { usage; exit 1; }
            stop_role "$role"
            start_role "$role"
            ;;
        attach)
            [ -n "$role" ] || { usage; exit 1; }
            attach_role "$role"
            ;;
        status)
            status_role "$role"
            ;;
        logs)
            [ -n "$role" ] || { usage; exit 1; }
            logs_role "$role"
            ;;
        -h|--help|help|"")
            usage
            ;;
        *)
            echo "ERROR: unknown command: $command" >&2
            usage
            exit 1
            ;;
    esac
}

main "$@"
