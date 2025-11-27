#!/bin/bash

# OITELU 親機起動スクリプト（診断機能付き）

echo "========================================"
echo "  OITELU 親機起動スクリプト"
echo "========================================"
echo ""

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 1. USBデバイス確認
echo -e "${YELLOW}[1/4] USBデバイスを確認中...${NC}"
if command -v lsusb &> /dev/null; then
    lsusb | grep -i "sony\|feliCa\|pasori" && echo -e "${GREEN}  ✓ カードリーダーを検出${NC}" || echo -e "${YELLOW}  ⚠ カードリーダーが見つかりません${NC}"
else
    echo -e "${YELLOW}  ⚠ lsusb コマンドが見つかりません${NC}"
fi
echo ""

# 2. Docker確認
echo -e "${YELLOW}[2/4] Docker の確認中...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}  ✗ Docker がインストールされていません${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}  ✗ Docker デーモンが起動していません${NC}"
    echo -e "${YELLOW}  以下のコマンドで起動してください:${NC}"
    echo -e "    sudo service docker start"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker が利用可能です${NC}"
echo ""

# 3. Dockerコンテナ起動
echo -e "${YELLOW}[3/4] Docker コンテナを起動中...${NC}"
docker-compose up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ コンテナを起動しました${NC}"
else
    echo -e "${RED}  ✗ コンテナの起動に失敗しました${NC}"
    exit 1
fi
echo ""

# 4. 診断実行
echo -e "${YELLOW}[4/4] システム診断を実行中...${NC}"
sleep 3

# ホスト環境で診断実行
if [ -f "diagnostics.py" ]; then
    python3 diagnostics.py summary
else
    echo -e "${YELLOW}  ⚠ diagnostics.py が見つかりません${NC}"
fi

# 5. 完了メッセージ
echo ""
echo -e "${GREEN}========================================"
echo -e "  起動完了！"
echo -e "========================================${NC}"
echo ""
echo -e "${CYAN}管理画面: http://localhost:5000/admin${NC}"
echo ""
echo -e "${YELLOW}コンテナを停止する場合:${NC}"
echo -e "  docker-compose down"
echo ""
echo -e "${YELLOW}ログを確認する場合:${NC}"
echo -e "  docker-compose logs -f"
echo ""
