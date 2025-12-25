#!/bin/bash
# OITERU 仮想環境(venv)用 起動スクリプト (Linux/Mac)
# Dockerを使わずに、ローカルのPython仮想環境(.venv)を使用して起動します。

cd "$(dirname "$0")"

PYTHON_PATH="./.venv/bin/python"

if [ ! -f "$PYTHON_PATH" ]; then
    echo "エラー: 仮想環境が見つかりません: $PYTHON_PATH"
    echo "先に 'python3 -m venv .venv' と 'pip install -r requirements.txt' を実行してください。"
    exit 1
fi

case "$1" in
    parent-sqlite)
        echo "親機 (SQLite) を起動します..."
        export DB_TYPE="sqlite"
        $PYTHON_PATH server.py
        ;;
    parent-mysql)
        echo "親機 (MySQL) を起動します..."
        echo "※ 事前にMySQLが localhost:3306 で起動している必要があります。"
        export DB_TYPE="mysql"
        export MYSQL_HOST="localhost"
        export MYSQL_PORT="3306"
        export MYSQL_DATABASE="oiteru"
        export MYSQL_USER="oiteru_user"
        export MYSQL_PASSWORD="oiteru_password_2025"
        $PYTHON_PATH server.py
        ;;
    sub-parent)
        echo "従親機 (MySQL接続) を起動します..."
        export DB_TYPE="mysql"
        export MYSQL_HOST="localhost"
        export MYSQL_PORT="3306"
        export MYSQL_DATABASE="oiteru"
        export MYSQL_USER="oiteru_user"
        export MYSQL_PASSWORD="oiteru_password_2025"
        export SERVER_NAME="OITERU従親機"
        $PYTHON_PATH server.py
        ;;
    unit)
        echo "子機クライアントを起動します..."
        $PYTHON_PATH unit.py
        ;;
    *)
        echo "使い方: $0 {parent-sqlite|parent-mysql|sub-parent|unit}"
        echo ""
        echo "  parent-sqlite - 親機 (SQLite版) を起動"
        echo "  parent-mysql  - 親機 (MySQL版) を起動"
        echo "  sub-parent    - 従親機 (MySQL版) を起動"
        echo "  unit          - 子機を起動"
        exit 1
        ;;
esac
