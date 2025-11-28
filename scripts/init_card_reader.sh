#!/bin/bash
# カードリーダー認識確認・初期化スクリプト

echo "=========================================="
echo "NFCカードリーダー初期化スクリプト"
echo "=========================================="
echo ""

# PC/SCデーモンの起動
echo "1. PC/SCデーモンを起動..."
if command -v pcscd &> /dev/null; then
    # 既存のプロセスを停止
    pkill -9 pcscd 2>/dev/null
    sleep 1
    
    # デーモンを起動
    pcscd --debug --apdu --foreground &
    PCSCD_PID=$!
    sleep 2
    
    echo "   ✓ PC/SCデーモンを起動しました (PID: $PCSCD_PID)"
else
    echo "   ⚠ pcscdが見つかりません"
fi

echo ""
echo "2. USBデバイスを確認..."
if command -v lsusb &> /dev/null; then
    lsusb | grep -i "reader\|nfc\|card" || echo "   ⚠ カードリーダーが検出されませんでした"
else
    echo "   ⚠ lsusbコマンドが利用できません"
fi

echo ""
echo "3. PC/SC接続リーダーを確認..."
if command -v pcsc_scan &> /dev/null; then
    timeout 3 pcsc_scan 2>&1 | head -n 20
else
    echo "   ⚠ pcsc_scanが利用できません"
fi

echo ""
echo "=========================================="
echo "初期化完了"
echo "=========================================="
