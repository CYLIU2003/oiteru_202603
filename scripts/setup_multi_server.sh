#!/bin/bash

# ========================================
# OITERU 複数親機セットアップスクリプト
# ========================================

set -e

echo "========================================="
echo "  OITERU 複数親機構成セットアップ"
echo "========================================="
echo ""

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 構成タイプの選択
echo "セットアップする構成を選択してください:"
echo ""
echo "  1. 同一マシン上で複数親機 (テスト・負荷分散用)"
echo "  2. 外部MySQLに接続する親機 (別マシン用)"
echo "  3. 既存のMySQLサーバーを利用"
echo ""
read -p "選択 [1-3]: " SETUP_TYPE

case $SETUP_TYPE in
  1)
    echo ""
    echo -e "${BLUE}同一マシン上で複数親機を起動します${NC}"
    echo ""
    
    # 既存のコンテナを確認
    if docker ps -a | grep -q "oiteru_mysql_shared"; then
      echo -e "${YELLOW}既存のMySQLコンテナが見つかりました。${NC}"
      read -p "既存のコンテナを削除して再起動しますか? [y/N]: " RECREATE
      if [ "$RECREATE" = "y" ] || [ "$RECREATE" = "Y" ]; then
        echo "既存のコンテナを停止・削除します..."
        docker-compose -f docker-compose.multi-server.yml down
      else
        echo "既存のコンテナをそのまま利用します"
      fi
    fi
    
    echo ""
    echo "親機の情報を入力してください:"
    echo ""
    read -p "親機1号機の名前 [親機1号機(メイン)]: " SERVER1_NAME
    SERVER1_NAME=${SERVER1_NAME:-親機1号機(メイン)}
    read -p "親機1号機の設置場所 [1階受付]: " SERVER1_LOCATION
    SERVER1_LOCATION=${SERVER1_LOCATION:-1階受付}
    
    read -p "親機2号機の名前 [親機2号機(サブ)]: " SERVER2_NAME
    SERVER2_NAME=${SERVER2_NAME:-親機2号機(サブ)}
    read -p "親機2号機の設置場所 [2階ロビー]: " SERVER2_LOCATION
    SERVER2_LOCATION=${SERVER2_LOCATION:-2階ロビー}
    
    # docker-compose.ymlを一時的に編集
    cp docker-compose.multi-server.yml docker-compose.multi-server.yml.tmp
    
    # 環境変数を更新
    sed -i "s/SERVER_NAME=親機1号機(メイン)/SERVER_NAME=$SERVER1_NAME/" docker-compose.multi-server.yml.tmp
    sed -i "s/SERVER_LOCATION=1階受付/SERVER_LOCATION=$SERVER1_LOCATION/" docker-compose.multi-server.yml.tmp
    sed -i "s/SERVER_NAME=親機2号機(サブ)/SERVER_NAME=$SERVER2_NAME/" docker-compose.multi-server.yml.tmp
    sed -i "s/SERVER_LOCATION=2階ロビー/SERVER_LOCATION=$SERVER2_LOCATION/" docker-compose.multi-server.yml.tmp
    
    echo ""
    echo -e "${GREEN}設定完了。Dockerコンテナを起動します...${NC}"
    docker-compose -f docker-compose.multi-server.yml.tmp up -d
    
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  セットアップ完了!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "アクセス先:"
    echo "  親機1号機: http://localhost:5000"
    echo "  親機2号機: http://localhost:5001"
    echo "  phpMyAdmin: http://localhost:8080"
    echo ""
    echo "ログ確認:"
    echo "  docker-compose -f docker-compose.multi-server.yml logs -f"
    ;;
    
  2)
    echo ""
    echo -e "${BLUE}外部MySQLに接続する親機をセットアップします${NC}"
    echo ""
    
    read -p "メインサーバーのIPアドレス (例: 192.168.1.100): " MYSQL_HOST
    if [ -z "$MYSQL_HOST" ]; then
      echo -e "${RED}エラー: IPアドレスが入力されていません${NC}"
      exit 1
    fi
    
    read -p "MySQLポート番号 [3306]: " MYSQL_PORT
    MYSQL_PORT=${MYSQL_PORT:-3306}
    
    read -p "MySQLユーザー名 [oiteru_user]: " MYSQL_USER
    MYSQL_USER=${MYSQL_USER:-oiteru_user}
    
    read -sp "MySQLパスワード [oiteru_password_2025]: " MYSQL_PASSWORD
    echo ""
    MYSQL_PASSWORD=${MYSQL_PASSWORD:-oiteru_password_2025}
    
    read -p "この親機の名前 [親機3号機(外部)]: " SERVER_NAME
    SERVER_NAME=${SERVER_NAME:-親機3号機(外部)}
    
    read -p "この親機の設置場所 [3階会議室]: " SERVER_LOCATION
    SERVER_LOCATION=${SERVER_LOCATION:-3階会議室}
    
    # 接続テスト
    echo ""
    echo "MySQLへの接続をテストしています..."
    if command -v mysql &> /dev/null; then
      if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SHOW DATABASES;" &> /dev/null; then
        echo -e "${GREEN}✓ MySQL接続成功${NC}"
      else
        echo -e "${YELLOW}⚠ MySQL接続テストに失敗しました。設定を確認してください。${NC}"
        read -p "それでも続行しますか? [y/N]: " CONTINUE
        if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
          exit 1
        fi
      fi
    else
      echo -e "${YELLOW}⚠ mysqlコマンドが見つかりません。接続テストをスキップします。${NC}"
    fi
    
    # docker-compose.ymlを一時的に編集
    cp docker-compose.external-db.yml docker-compose.external-db.yml.tmp
    
    sed -i "s/MYSQL_HOST=192.168.1.100/MYSQL_HOST=$MYSQL_HOST/" docker-compose.external-db.yml.tmp
    sed -i "s/MYSQL_PORT=3306/MYSQL_PORT=$MYSQL_PORT/" docker-compose.external-db.yml.tmp
    sed -i "s/MYSQL_USER=oiteru_user/MYSQL_USER=$MYSQL_USER/" docker-compose.external-db.yml.tmp
    sed -i "s/MYSQL_PASSWORD=oiteru_password_2025/MYSQL_PASSWORD=$MYSQL_PASSWORD/" docker-compose.external-db.yml.tmp
    sed -i "s/SERVER_NAME=親機3号機(外部)/SERVER_NAME=$SERVER_NAME/" docker-compose.external-db.yml.tmp
    sed -i "s/SERVER_LOCATION=3階会議室/SERVER_LOCATION=$SERVER_LOCATION/" docker-compose.external-db.yml.tmp
    
    echo ""
    echo -e "${GREEN}設定完了。Dockerコンテナを起動します...${NC}"
    docker-compose -f docker-compose.external-db.yml.tmp up -d
    
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  セットアップ完了!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "アクセス先:"
    echo "  この親機: http://localhost:5000"
    echo ""
    echo "接続先MySQL:"
    echo "  ホスト: $MYSQL_HOST:$MYSQL_PORT"
    ;;
    
  3)
    echo ""
    echo -e "${BLUE}既存のMySQLサーバーに接続する設定を行います${NC}"
    echo ""
    
    read -p "MySQLサーバーのIPアドレス: " MYSQL_HOST
    if [ -z "$MYSQL_HOST" ]; then
      echo -e "${RED}エラー: IPアドレスが入力されていません${NC}"
      exit 1
    fi
    
    read -p "MySQLポート番号 [3306]: " MYSQL_PORT
    MYSQL_PORT=${MYSQL_PORT:-3306}
    
    read -p "MySQLユーザー名: " MYSQL_USER
    read -sp "MySQLパスワード: " MYSQL_PASSWORD
    echo ""
    
    read -p "データベース名を作成しますか? [y/N]: " CREATE_DB
    if [ "$CREATE_DB" = "y" ] || [ "$CREATE_DB" = "Y" ]; then
      echo ""
      echo "MySQLにデータベースとテーブルを作成します..."
      
      # データベース作成SQLを生成
      cat > /tmp/create_oiteru_db.sql <<EOF
CREATE DATABASE IF NOT EXISTS oiteru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'oiteru_user'@'%' IDENTIFIED BY 'oiteru_password_2025';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'%';
FLUSH PRIVILEGES;
EOF
      
      mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" < /tmp/create_oiteru_db.sql
      
      if [ -f "init_mysql.sql" ]; then
        echo "テーブルを初期化しています..."
        mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u oiteru_user -poiteru_password_2025 oiteru < init_mysql.sql
        echo -e "${GREEN}✓ データベース初期化完了${NC}"
      else
        echo -e "${YELLOW}⚠ init_mysql.sql が見つかりません。手動でテーブルを作成してください。${NC}"
      fi
      
      rm /tmp/create_oiteru_db.sql
    fi
    
    read -p "この親機の名前: " SERVER_NAME
    read -p "この親機の設置場所: " SERVER_LOCATION
    
    # .envファイルを作成
    cat > .env.external <<EOF
# 外部MySQL接続設定
DB_TYPE=mysql
MYSQL_HOST=$MYSQL_HOST
MYSQL_PORT=$MYSQL_PORT
MYSQL_DATABASE=oiteru
MYSQL_USER=oiteru_user
MYSQL_PASSWORD=oiteru_password_2025

# サーバー識別情報
SERVER_NAME=$SERVER_NAME
SERVER_LOCATION=$SERVER_LOCATION
EOF
    
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  設定ファイル作成完了!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "設定ファイル: .env.external"
    echo ""
    echo "起動方法:"
    echo "  source .env.external && python app.py"
    echo ""
    echo "またはDocker Composeで起動:"
    echo "  docker-compose --env-file .env.external up -d"
    ;;
    
  *)
    echo -e "${RED}エラー: 無効な選択です${NC}"
    exit 1
    ;;
esac

echo ""
echo -e "${BLUE}詳細は取説書/MULTI_SERVER.md をご覧ください${NC}"
