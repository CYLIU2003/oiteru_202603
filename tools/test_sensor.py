#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フォトリフレクタ(LBR-127HLD)センサー単体テストスクリプト

【使い方】
    python3 test_sensor.py

【終了方法】
    Ctrl+C を押す

【配線】
    LBR-127HLD → Raspberry Pi
    VCC → 3.3V or 5V
    GND → GND
    OUT → GPIO 22 (BCM)

【動作】
    - センサーの状態を0.1秒ごとにポーリング
    - LOW(0) = 物体検知(詰まり)
    - HIGH(1) = クリア(正常)
"""

import time
import sys

# GPIOライブラリの初期化
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIOライブラリがインストールされていません")
    print("インストール方法: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

# ========================================
# 設定
# ========================================
SENSOR_PIN = 22  # BCMモード(GPIO 22)
POLL_INTERVAL = 0.1  # ポーリング間隔(秒)

# ========================================
# 初期化
# ========================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# プルアップ抵抗を有効化(センサーがオープンコレクタ出力の場合に必要)
GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("=" * 60)
print("フォトリフレクタセンサーテスト開始")
print("=" * 60)
print(f"センサーピン: GPIO {SENSOR_PIN} (BCM)")
print(f"ポーリング間隔: {POLL_INTERVAL}秒")
print("終了: Ctrl+C")
print("=" * 60)
print("")
print("状態 | RAW値 | 判定")
print("-" * 60)

try:
    prev_state = None
    while True:
        # センサーの状態を読み取る
        raw_value = GPIO.input(SENSOR_PIN)
        
        # LBR-127HLDの出力特性
        # LOW (0) = 物体検知(光が反射している = 詰まり)
        # HIGH (1) = 物体なし(光が反射していない = クリア)
        if raw_value == GPIO.LOW:
            status = "詰まり"
            symbol = "🔴"
        else:
            status = "クリア"
            symbol = "🟢"
        
        # 状態が変化したときのみ表示(オプション: 常に表示する場合は if を削除)
        if raw_value != prev_state:
            timestamp = time.strftime("%H:%M:%S")
            print(f"{symbol}  |  {raw_value}    | {status} ({timestamp})")
            prev_state = raw_value
        
        # コメントアウトを解除すると、すべての値を連続表示
        # timestamp = time.strftime("%H:%M:%S")
        # print(f"{symbol}  |  {raw_value}    | {status} ({timestamp})")
        
        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\n" + "=" * 60)
    print("テスト終了")
    print("=" * 60)

finally:
    # GPIO のクリーンアップ
    GPIO.cleanup()
