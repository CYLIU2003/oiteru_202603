"""RC-S380 を nfcpy で開けるか確認するスクリプト (WSL 内で実行)"""
import nfc

try:
    clf = nfc.ContactlessFrontend("usb")
    print("OPEN OK:", clf)
    clf.close()
except Exception as exc:  # noqa: BLE001
    print("OPEN FAIL:", type(exc).__name__, exc)
