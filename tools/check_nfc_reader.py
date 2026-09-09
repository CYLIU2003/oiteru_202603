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
import logging
import sys
import time

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="OITERU NFCリーダー確認ツール")
    parser.add_argument("--read", action="store_true", help="カードを1枚読み取る")
    args = parser.parse_args()

    try:
        import nfc
    except ImportError:
        logger.error("nfcpy が未インストールです。pip install -r requirements.txt を実行してください。")
        return 1

    # server.py と同じ接続パスを試行
    usb_paths = ["usb:054c:06c3", "usb:054c:06c1", "usb:054c:02e1", "usb"]
    clf = None
    last_error = None
    for path in usb_paths:
        try:
            candidate = nfc.ContactlessFrontend(path)
            if candidate:
                clf = candidate
                logger.info("NFCリーダーを検出しました")
                break
            candidate.close()
        except Exception as e:
            last_error = e

    if clf is None:
        logger.error("NFCリーダーが見つかりません。USB接続とドライバを確認してください。")
        if last_error:
            logger.error("最終エラー種別: %s", type(last_error).__name__)
        return 1

    if not args.read:
        clf.close()
        logger.info("カード読み取りテストをスキップ (--read で実行)")
        return 0

    logger.info("カードをリーダーに置いてください (最大10秒待機)...")
    start = time.monotonic()
    card_read = False
    try:
        while time.monotonic() - start < 10:
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
                    card_read = True
                    logger.info("カードを読み取りました (UID非表示)")
                    break
    except Exception as e:
        logger.warning("読み取りエラー種別: %s", type(e).__name__)
    finally:
        clf.close()

    if not card_read:
        logger.error("カードを読み取れませんでした。")
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
