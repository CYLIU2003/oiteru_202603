#!/bin/bash
# OITERUシステム 従親機クイック起動スクリプト (Mac/Linux用)
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
OITERUシステム 従親機クイック起動スクリプト

使い方:
  ./quick_start_sub.sh 192.168.1.100
  ./quick_start_sub.sh 100.114.99.67  # Tailscale IP

パラメータ:
  第1引数    親機のIPアドレス（必須）
EOF
    exit 0
}

# パラメータチェック
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
fi

if [ -z "$1" ]; then
    echo -e "${YELLOW}エラー: 親機のIPアドレスを指定してください${NC}"
    echo "使い方: $0 <親機のIPアドレス>"
    exit 1
fi

PARENT_HOST="$1"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${CYAN}🐍 従親機を起動します...${NC}"
echo -e "${YELLOW}📡 接続先親機: $PARENT_HOST${NC}"

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

# 環境変数設定
export DB_TYPE='mysql'
export MYSQL_HOST="$PARENT_HOST"
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
