#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITERU NFCカードリーダー動作確認ツール
=========================================

親機(Windows/Linux)に接続されたNFCカードリーダーの検出と、
カード読み取りの動作確認を行います。

使い方:
    python tools/check_nfc_reader.py          # リーダー検出のみ
    python tools/check_nfc_reader.py --read   # カードを1枚読み取る(10秒待機)

WindowsでPaSoRi RC-S380が認識されない場合:
    1. USBポートに挿し直す
    2. デバイスマネージャーで"その他のデバイス"に表示される場合、
       Zadig (https://zadig.akeo.ie) で WinUSB ドライバを割り当てる
    3. このスクリプトを再実行する
"""

import argparse
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="OITERU NFCリーダー確認ツール")
    parser.add_argument("--read", action="store_true", help="カードを1枚読み取る")
    args = parser.parse_args()

    try:
        import nfc
    except ImportError:
        print("[FAIL] nfcpy がインストールされていません。")
        print("       pip install -r requirements.txt を実行してください。")
        return 1

    # server.py と同じ接続パスを試行
    usb_paths = ["usb:054c:06c3", "usb:054c:06c1", "usb:054c:02e1", "usb"]
    clf = None
    last_error = None
    for path in usb_paths:
        try:
            clf = nfc.ContactlessFrontend(path)
            if clf:
                print(f"[OK] NFCリーダーを検出しました: {clf}")
                print(f"     device: {getattr(clf, 'device', '?')}")
                break
        except Exception as e:
            last_error = e

    if clf is None:
        print("[FAIL] NFCリーダーが見つかりません。")
        print("       - USB接続を確認してください")
        print("       - Windowsで未認識の場合、Zadig で WinUSB ドライバを割り当ててください")
        if last_error:
            print(f"       最終エラー: {last_error}")
        return 1

    if not args.read:
        clf.close()
        print("[INFO] カード読み取りテストをスキップ (--read で実行)")
        return 0

    print("[INFO] カードをリーダーに置いてください (最大10秒待機)...")
    start = time.time()
    card_id = None
    while time.time() - start < 10:
        try:
            target = clf.sense(
                nfc.clf.RemoteTarget("106A"),
                nfc.clf.RemoteTarget("106B"),
                nfc.clf.RemoteTarget("212F"),
                iterations=5,
                interval=0.1,
            )
            if target:
                tag = nfc.tag.activate(clf, target)
                if tag:
                    card_id = tag.identifier.hex().upper()
                    print(f"[OK] カードを読み取りました: {card_id}")
                    print(f"     型: {tag.type}, 製品: {getattr(tag, 'product', '?')}")
                    break
        except Exception as e:
            print(f"[WARN] 読み取りエラー: {e}")
            break

    clf.close()
    if card_id is None:
        print("[FAIL] カードを読み取れませんでした。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
