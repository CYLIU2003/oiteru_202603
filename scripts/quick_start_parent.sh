#!/bin/bash
# OITERUシステム 親機クイック起動スクリプト (Mac/Linux用)
# 軽量版 - 最小限の設定で素早く起動

set -e

# カラー定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

# ヘルプ表示
show_help() {
    cat << EOF
OITERUシステム 親機クイック起動スクリプト

使い方:
  ./quick_start_parent.sh          # 仮想環境モードで起動
  ./quick_start_parent.sh --docker # Dockerモードで起動

オプション:
  --docker    Dockerコンテナ内でサーバーを起動
  --help      このヘルプを表示
EOF
    exit 0
}

# パラメータ解析
DOCKER_MODE=false
if [ "$1" = "--docker" ]; then
    DOCKER_MODE=true
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$DOCKER_MODE" = true ]; then
    echo -e "${CYAN}🐳 Dockerモードで起動します...${NC}"
    
    # Docker起動
    cd "$PROJECT_ROOT"
    echo -e "${YELLOW}Docker Composeを起動中...${NC}"
    docker-compose -f docker-compose.mysql.yml up -d
    
    echo ""
    echo -e "${GREEN}✅ 親機起動完了！${NC}"
    echo -e "${CYAN}📡 アクセス: http://localhost:5000${NC}"
    echo -e "${CYAN}🔧 管理画面: http://localhost:5000/admin${NC}"
    echo ""
    echo -e "${GRAY}📋 ログ表示: docker-compose -f docker-compose.mysql.yml logs -f${NC}"
    echo -e "${GRAY}🛑 停止: docker-compose -f docker-compose.mysql.yml down${NC}"
    
else
    echo -e "${CYAN}🐍 仮想環境モードで起動します...${NC}"
    
    # 仮想環境パス検出
    VENV_PATH=""
    VENV_CANDIDATES=(
        "$HOME/.venv_oiteru"
        "$PROJECT_ROOT/.venv"
        "$PROJECT_ROOT/venv"
    )
    
    for path in "${VENV_CANDIDATES[@]}"; do
        if [ -f "$path/bin/activate" ]; then
            VENV_PATH="$path"
            echo -e "${GREEN}✓ 仮想環境を検出: $VENV_PATH${NC}"
            break
        fi
    done
    
    if [ -z "$VENV_PATH" ]; then
        echo -e "${YELLOW}⚠ 仮想環境が見つかりません。作成します...${NC}"
        VENV_PATH="$HOME/.venv_oiteru"
        python3 -m venv "$VENV_PATH"
        echo -e "${GREEN}✓ 仮想環境を作成: $VENV_PATH${NC}"
        
        # パッケージインストール
        "$VENV_PATH/bin/pip" install -r "$PROJECT_ROOT/requirements.txt" -q
        "$VENV_PATH/bin/pip" install pymysql -q
        echo -e "${GREEN}✓ パッケージをインストールしました${NC}"
    fi
    
    # MySQLコンテナ起動確認
    echo -e "${YELLOW}MySQL Dockerコンテナを確認中...${NC}"
    if ! docker ps --filter "name=oiteru_mysql" --format "{{.Names}}" 2>/dev/null | grep -q oiteru_mysql; then
        echo -e "${YELLOW}MySQLコンテナを起動します...${NC}"
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.mysql.yml up -d oiteru_mysql
        sleep 3
        echo -e "${GREEN}✓ MySQLコンテナ起動完了${NC}"
    else
        echo -e "${GREEN}✓ MySQLコンテナは既に起動中${NC}"
    fi
    
    # 環境変数設定
    export DB_TYPE='mysql'
    export MYSQL_HOST='localhost'
    export MYSQL_PORT='3306'
    export MYSQL_DATABASE='oiteru'
    export MYSQL_USER='oiteru_user'
    export MYSQL_PASSWORD='oiteru_password_2025'
    
    echo ""
    echo -e "${CYAN}🚀 サーバーを起動します...${NC}"
    echo ""
    echo -e "${CYAN}📡 アクセス: http://localhost:5000${NC}"
    echo -e "${CYAN}🔧 管理画面: http://localhost:5000/admin (パスワード: admin)${NC}"
    echo ""
    echo -e "${GRAY}🛑 停止: Ctrl+C を押してください${NC}"
    echo ""
    
    # サーバー起動
    cd "$PROJECT_ROOT"
    "$VENV_PATH/bin/python" server.py
fi
