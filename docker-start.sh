#!/bin/bash
# OITELU Docker起動スクリプト
# docker/フォルダ内のdocker-composeを実行します

cd "$(dirname "$0")/docker"

case "$1" in
    mysql)
        echo "親機DB版（MySQL）を起動します..."
        docker-compose -f docker-compose.mysql.yml up -d
        ;;
    external)
        echo "従親機（外部DB接続）を起動します..."
        docker-compose -f docker-compose.external-db.yml up -d
        ;;
    unit)
        echo "子機をDocker経由で起動します..."
        docker-compose -f docker-compose.unit.yml up -d
        ;;
    stop)
        echo "全てのコンテナを停止します..."
        docker-compose -f docker-compose.mysql.yml down
        docker-compose -f docker-compose.external-db.yml down
        docker-compose -f docker-compose.unit.yml down
        ;;
    *)
        echo "使い方: $0 {mysql|external|unit|stop}"
        echo ""
        echo "  mysql    - 親機DB版（MySQL + Webサーバー）を起動"
        echo "  external - 従親機（外部MySQLに接続）を起動"
        echo "  unit     - 子機をDockerで起動"
        echo "  stop     - 全てのコンテナを停止"
        exit 1
        ;;
esac
