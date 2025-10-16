#!/bin/bash
# NFCリーダーがDockerコンテナ内で認識されるかテストするスクリプト

echo "=== USB devices check ==="
lsusb

echo ""
echo "=== /dev/bus/usb directory ==="
ls -la /dev/bus/usb/

echo ""
echo "=== Python nfcpy test ==="
python3 << 'EOF'
import nfc

try:
    clf = nfc.ContactlessFrontend()
    print(f"✅ NFC reader initialized successfully: {clf}")
    clf.close()
except Exception as e:
    print(f"❌ NFC reader initialization failed: {e}")
EOF
