#!/bin/bash
# OITERU 仮想環境(venv)用 起動スクリプト (Linux/Mac)
# Dockerを使わずに、ローカルのPython仮想環境(.venv)を使用して起動します。

cd "$(dirname "$0")"

PYTHON_PATH="./.venv/bin/python"
ENV_FILE="./.env"
ENV_EXAMPLE_FILE="./.env.example"

if [ ! -f "$PYTHON_PATH" ]; then
    echo "エラー: 仮想環境が見つかりません: $PYTHON_PATH"
    echo "先に 'python3 -m venv .venv' と 'pip install -r requirements.txt' を実行してください。"
    exit 1
fi

MODE="${1:-parent-mysql}"

case "$MODE" in
    parent-mysql)
        echo "親機 (MySQL) を起動します..."
        echo "※ 事前にMySQLが localhost:3306 で起動している必要があります。"

        if [ ! -f "$ENV_FILE" ]; then
            echo "エラー: .env が見つかりません: $ENV_FILE"
            echo "$ENV_EXAMPLE_FILE をコピーし、必須値を設定してください。"
            exit 1
        fi

        $PYTHON_PATH db_server.py
        ;;
    parent-sqlite)
        echo "親機 (SQLite) を起動します..."
        export DB_TYPE="sqlite"
        $PYTHON_PATH server.py
        ;;
    sub-parent)
        echo "従親機 (MySQL接続) を起動します..."

        if [ ! -f "$ENV_FILE" ]; then
            echo "エラー: .env が見つかりません: $ENV_FILE"
            echo "$ENV_EXAMPLE_FILE をコピーし、必須値を設定してください。"
            exit 1
        fi

        export DB_TYPE="mysql"
        export MYSQL_HOST="${MYSQL_HOST:-localhost}"
        export SERVER_NAME="${SERVER_NAME:-OITERU従親機}"
        $PYTHON_PATH server.py
        ;;
    unit)
        echo "子機クライアントを起動します..."
        echo ""
        echo "========================================="
        echo "  子機: 親機・従親機からの設定同期対応"
        echo "  - GUIモード: --gui オプション"
        echo "  - CUIモード: デフォルト"
        echo "  - リモート設定変更が自動反映されます"
        echo "========================================="
        echo ""
        if ! "$PYTHON_PATH" - <<'PY' >/dev/null 2>&1
import importlib
for module_name in ("RPi.GPIO", "Adafruit_PCA9685", "serial"):
    importlib.import_module(module_name)
PY
        then
            if [ -f "./requirements-client.txt" ]; then
                echo "子機用依存関係をインストール中..."
                $PYTHON_PATH -m pip install -r ./requirements-client.txt
            elif [ -f "./docker/requirements-client.txt" ]; then
                echo "子機用依存関係をインストール中..."
                $PYTHON_PATH -m pip install -r ./docker/requirements-client.txt
            fi
        fi
        shift
        $PYTHON_PATH unit.py "$@"
        ;;
    *)
        echo "使い方: $0 {parent-mysql|parent-sqlite|sub-parent|unit}"
        echo ""
        echo "  parent-mysql  - 親機 (MySQL版, 既定) を起動"
        echo "  parent-sqlite - 親機 (SQLite版, legacy) を起動"
        echo "  sub-parent    - 従親機 (MySQL版) を起動"
        echo "  unit          - 子機を起動"
        exit 1
        ;;
esac
