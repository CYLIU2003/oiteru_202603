#!/bin/bash
# カードリーダー認識確認・初期化スクリプト

echo "=========================================="
echo "NFCカードリーダー初期化スクリプト"
echo "=========================================="
echo ""

run_as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

ensure_blacklist() {
    local blacklist_file="/etc/modprobe.d/99-oiteru-nfc-blacklist.conf"
    local blacklist_content=$'blacklist port100\nblacklist nfc_digital\ninstall port100 /bin/false\ninstall nfc_digital /bin/false\n'

    if [ ! -f "$blacklist_file" ]; then
        printf '%s' "$blacklist_content" | run_as_root tee "$blacklist_file" >/dev/null
        echo "   ✓ NFCドライバのブラックリストを作成しました"
    fi
}

# PC/SCデーモンの起動
echo "1. PC/SCデーモンを起動..."
if command -v modprobe &> /dev/null; then
    ensure_blacklist
    run_as_root modprobe -r port100 nfc_digital 2>/dev/null || true
fi
if command -v pcscd &> /dev/null; then
    if command -v systemctl &> /dev/null && systemctl list-unit-files pcscd.socket &> /dev/null; then
        run_as_root systemctl enable --now pcscd.socket >/dev/null 2>&1 || true
        sleep 1
        if pgrep -x pcscd &> /dev/null || systemctl is-active --quiet pcscd.socket; then
            echo "   ✓ PC/SCデーモンを systemd 経由で起動しました"
        else
            echo "   ⚠ PC/SCデーモンの起動確認ができませんでした"
        fi
    else
        # 既存のプロセスを停止
        run_as_root pkill -9 pcscd 2>/dev/null || true
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
