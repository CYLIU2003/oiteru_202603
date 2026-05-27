#!/bin/bash
# カードリーダー認識確認・初期化スクリプト

echo "=========================================="
echo "NFCカードリーダー初期化スクリプト"
echo "=========================================="
echo ""

# PC/SCデーモンの起動
echo "1. PC/SCデーモンを起動..."
if command -v modprobe &> /dev/null; then
    sudo modprobe -r port100 nfc_digital 2>/dev/null || true
fi
if command -v pcscd &> /dev/null; then
    if command -v systemctl &> /dev/null && systemctl list-unit-files pcscd.socket &> /dev/null; then
        sudo systemctl enable --now pcscd.socket >/dev/null 2>&1 || true
        sudo systemctl restart pcscd >/dev/null 2>&1 || true
        sleep 1
        if pgrep -x pcscd &> /dev/null || systemctl is-active --quiet pcscd.socket; then
            echo "   ✓ PC/SCデーモンを systemd 経由で起動しました"
        else
            echo "   ⚠ PC/SCデーモンの起動確認ができませんでした"
        fi
    else
        # 既存のプロセスを停止
        pkill -9 pcscd 2>/dev/null
        sleep 1
        
        # デーモンを起動
        pcscd --debug --apdu --foreground &
        PCSCD_PID=$!
        sleep 2
        
        echo "   ✓ PC/SCデーモンを起動しました (PID: $PCSCD_PID)"
    fi
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
