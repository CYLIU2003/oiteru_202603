#!/bin/bash
# NFCカードリーダー監視スクリプト
# unit_client.pyが異常終了した場合に自動的に再起動します

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/unit_client.py"
LOG_FILE="$SCRIPT_DIR/watchdog.log"
MAX_RESTARTS=10
RESTART_INTERVAL=30  # 秒

restart_count=0
last_restart_time=0

echo "[$(date)] Watchdog started" >> "$LOG_FILE"

while true; do
    current_time=$(date +%s)
    
    # 短時間に連続再起動している場合はカウントをリセット
    if [ $((current_time - last_restart_time)) -gt 300 ]; then
        restart_count=0
    fi
    
    # 最大再起動回数チェック
    if [ $restart_count -ge $MAX_RESTARTS ]; then
        echo "[$(date)] ERROR: 最大再起動回数($MAX_RESTARTS)に到達しました。手動での介入が必要です。" >> "$LOG_FILE"
        exit 1
    fi
    
    echo "[$(date)] Starting unit_client.py (再起動回数: $restart_count)" >> "$LOG_FILE"
    sudo python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1
    
    exit_code=$?
    restart_count=$((restart_count + 1))
    last_restart_time=$(date +%s)
    
    echo "[$(date)] unit_client.py が終了しました (終了コード: $exit_code)" >> "$LOG_FILE"
    echo "[$(date)] ${RESTART_INTERVAL}秒後に再起動します..." >> "$LOG_FILE"
    
    sleep $RESTART_INTERVAL
done
