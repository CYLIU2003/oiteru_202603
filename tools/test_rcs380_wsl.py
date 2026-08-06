#!/usr/bin/env python3
"""RC-S380 (WSL2) 動作確認スクリプト"""
import nfc


def main():
    try:
        clf = nfc.ContactlessFrontend("usb")
        if clf:
            print("OPEN OK:", clf)
            clf.close()
        else:
            print("OPEN FAILED: no device")
    except Exception as e:
        print("OPEN ERROR:", type(e).__name__, e)


if __name__ == "__main__":
    main()
