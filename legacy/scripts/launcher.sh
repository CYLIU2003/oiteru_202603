#!/bin/bash
# =========================================
# OITELU ランチャー起動スクリプト (Linux/Mac)
# =========================================

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  OITELU System Launcher${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}どちらのランチャーを起動しますか？${NC}"
echo ""
echo -e "${WHITE}  1. GUI版 (グラフィカルインターフェース)${NC}"
echo -e "${WHITE}  2. CUI版 (BIOS風テキストインターフェース)${NC}"
echo ""

read -p "選択してください [1-2]: " choice

if [ "$choice" = "1" ]; then
    echo ""
    echo -e "${GREEN}GUI版ランチャーを起動しています...${NC}"
    python3 launcher_gui.py
elif [ "$choice" = "2" ]; then
    echo ""
    echo -e "${GREEN}CUI版ランチャーを起動しています...${NC}"
    python3 launcher_cui.py
else
    echo ""
    echo -e "${YELLOW}無効な選択です。デフォルトでCUI版を起動します。${NC}"
    sleep 2
    python3 launcher_cui.py
fi

echo ""
read -p "Press Enter to exit..."
