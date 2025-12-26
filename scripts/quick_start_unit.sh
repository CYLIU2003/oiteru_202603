#!/bin/bash
# OITERUシステム 子機クイック起動スクリプト (Raspberry Pi用)
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
OITERUシステム 子機クイック起動スクリプト

使い方:
  sudo ./quick_start_unit.sh 192.168.1.100
  sudo ./quick_start_unit.sh 100.114.99.67  # Tailscale IP

パラメータ:
  第1引数    親機のIPアドレス（必須）

注意: sudoで実行してください（NFCリーダー/GPIOアクセスに必要）
EOF
    exit 0
}

# パラメータチェック
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
fi

if [ -z "$1" ]; then
    echo -e "${YELLOW}エラー: 親機のIPアドレスを指定してください${NC}"
    echo "使い方: sudo $0 <親機のIPアドレス>"
    exit 1
fi

# root権限チェック
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}エラー: sudoで実行してください${NC}"
    echo "使い方: sudo $0 $1"
    exit 1
fi

PARENT_HOST="$1"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${CYAN}🐍 子機を起動します...${NC}"
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
    "$VENV_PATH/bin/pip" install nfcpy requests -q
    echo -e "${GREEN}✓ パッケージをインストールしました${NC}"
fi

# config.json更新
CONFIG_FILE="$PROJECT_ROOT/config.json"
if [ -f "$CONFIG_FILE" ]; then
    # SERVER_URLを更新
    sed -i "s|\"SERVER_URL\": \".*\"|\"SERVER_URL\": \"http://$PARENT_HOST:5000\"|" "$CONFIG_FILE"
    echo -e "${GREEN}✓ config.jsonを更新しました${NC}"
fi

echo ""
echo -e "${CYAN}🚀 子機を起動します...${NC}"
echo ""
echo -e "${GRAY}🛑 停止: Ctrl+C を押してください${NC}"
echo ""

# 子機起動
cd "$PROJECT_ROOT"
"$VENV_PATH/bin/python" unit.py
