#!/bin/bash

# WSL環境でカードリーダーをWindows側から自動アタッチするスクリプト

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}[カードリーダー自動アタッチ]${NC}"

# WSL環境かどうかを判定
if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
    echo -e "${YELLOW}  WSL環境を検出しました${NC}"
    
    # カードリーダーが既にWSL側で認識されているか確認
    if lsusb 2>/dev/null | grep -qi "054c:06c1\|sony.*rc-s"; then
        echo -e "${GREEN}  ✓ カードリーダーは既にWSL側で認識されています${NC}"
        return 0 2>/dev/null || exit 0
    fi
    
    echo -e "${YELLOW}  カードリーダーがWSL側で見つかりません${NC}"
    echo -e "${YELLOW}  Windows側からアタッチを試みます...${NC}"
    
    # PowerShellスクリプトのパスを取得
    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    WINDOWS_PATH=$(wslpath -w "$SCRIPT_DIR")
    
    # Windows側でusbipdコマンドを実行してアタッチ
    echo -e "${CYAN}  Windows側でusbipd操作を実行中...${NC}"
    
    # カードリーダーのBUSIDを取得
    BUSID=$(powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
        \$output = usbipd list | Select-String -Pattern '054c:06c1|RC-S380'
        if (\$output) {
            \$busid = (\$output[0] -split '\s+')[0]
            Write-Output \$busid
        }
    " 2>/dev/null | tr -d '\r\n')
    
    if [ -z "$BUSID" ]; then
        echo -e "${RED}  ✗ Windows側でカードリーダーが見つかりませんでした${NC}"
        echo -e "${YELLOW}  以下を確認してください:${NC}"
        echo -e "    1. USBケーブルが正しく接続されているか"
        echo -e "    2. デバイスマネージャーでドライバーが正常か"
        echo -e "    3. 別のUSBポートに接続してみる"
        return 1 2>/dev/null || exit 1
    fi
    
    echo -e "${CYAN}  カードリーダーを検出: BUSID=$BUSID${NC}"
    
    # 既存の接続を解除してから再アタッチ
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
        # 既存の接続を解除
        usbipd detach --busid $BUSID 2>\$null
        Start-Sleep -Seconds 1
        
        # WSL2にアタッチ
        usbipd attach --wsl --busid $BUSID --auto-attach
        
        if (\$LASTEXITCODE -eq 0) {
            Write-Host '✓ カードリーダーをWSL2にアタッチしました' -ForegroundColor Green
            exit 0
        } else {
            Write-Host '✗ アタッチに失敗しました' -ForegroundColor Red
            exit 1
        }
    " 2>&1 | sed 's/\r$//'
    
    ATTACH_RESULT=$?
    
    if [ $ATTACH_RESULT -eq 0 ]; then
        # アタッチ成功後、デバイスが認識されるまで待機
        echo -e "${CYAN}  デバイス認識を待機中...${NC}"
        sleep 2
        
        # 確認
        if lsusb 2>/dev/null | grep -qi "054c:06c1\|sony.*rc-s"; then
            echo -e "${GREEN}  ✓ カードリーダーが正常にWSL側で認識されました${NC}"
            return 0 2>/dev/null || exit 0
        else
            echo -e "${YELLOW}  ⚠ アタッチは成功しましたが、認識に時間がかかっています${NC}"
            echo -e "${YELLOW}    数秒後に再確認してください: lsusb | grep Sony${NC}"
            return 0 2>/dev/null || exit 0
        fi
    else
        echo -e "${RED}  ✗ カードリーダーのアタッチに失敗しました${NC}"
        echo -e "${YELLOW}  手動でアタッチしてください:${NC}"
        echo -e "    1. PowerShellを管理者権限で開く"
        echo -e "    2. 実行: usbipd attach --wsl --busid $BUSID"
        echo -e "  または fix_card_reader.bat を実行してください"
        return 1 2>/dev/null || exit 1
    fi
    
else
    echo -e "${CYAN}  ネイティブLinux環境です（WSLではありません）${NC}"
    
    # ネイティブLinuxの場合、カードリーダーが接続されているか確認
    if lsusb 2>/dev/null | grep -qi "054c:06c1\|sony.*rc-s"; then
        echo -e "${GREEN}  ✓ カードリーダーが認識されています${NC}"
        return 0 2>/dev/null || exit 0
    else
        echo -e "${YELLOW}  ⚠ カードリーダーが見つかりません${NC}"
        echo -e "${YELLOW}  USBケーブルの接続を確認してください${NC}"
        return 1 2>/dev/null || exit 1
    fi
fi
