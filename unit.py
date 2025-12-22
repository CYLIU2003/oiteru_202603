#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU 子機 (NFC読み取り + モーター制御)
=========================================

このファイルは子機として動作します。
Raspberry PiにNFCリーダーとモーターを接続して使用します。

起動方法:
    python unit.py

設定:
    config.json で以下を設定してください:
    - SERVER_URL: 親機のURL (例: http://100.114.99.67:5000)
    - UNIT_NAME: 子機の名前
    - UNIT_PASSWORD: 子機のパスワード
    - MOTOR_TYPE: SERVO または STEPPER
    - CONTROL_METHOD: RASPI_DIRECT または ARDUINO_SERIAL
    - USE_SENSOR: true/false

========================================

詳細な実装は archive/unit_client.py を参照してください。
"""

import sys
import os

# 実行パスを調整
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# archive/unit_client.pyをインポート
if __name__ == '__main__':
    unit_client_path = os.path.join(script_dir, 'archive', 'unit_client.py')
    if os.path.exists(unit_client_path):
        exec(open(unit_client_path).read())
    else:
        print(f"エラー: {unit_client_path} が見つかりません")
        sys.exit(1)
