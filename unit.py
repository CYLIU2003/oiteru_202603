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
        - STEPPER_PINS: ULN2003AN の IN1-IN4 に接続する Raspberry Pi BCM GPIO 番号

    ========================================

    `config.example.json` を `config.json` にコピーしてから編集してください。

    詳細な実装は archive/unit_client.py を参照してください。
"""

import os
import sys


STEPPER_DIRECT_BRANCH = r'''
        elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':
            # ULN2003AN + 28BYJ-48 を Raspberry Pi GPIO から直接駆動する。
            # config.json 例:
            #   "STEPPER_PINS": [5, 6, 13, 19]  # IN1, IN2, IN3, IN4 の順。BCM番号。
            #   "STEPPER_STEP_DELAY": 0.0025    # 任意。小さいほど高速。ただし小さすぎると脱調。
            #   "STEPPER_STEPS": 0              # 任意。0/未設定なら MOTOR_DURATION 秒で駆動。
            try:
                raw_pins = config.get('STEPPER_PINS', [5, 6, 13, 19])
                if isinstance(raw_pins, str):
                    raw_pins = [int(pin.strip()) for pin in raw_pins.split(',') if pin.strip()]
                stepper_pins = [int(pin) for pin in raw_pins]
                if len(stepper_pins) != 4:
                    raise ValueError(f"STEPPER_PINS は IN1-IN4 の4本で指定してください: {raw_pins}")

                # 28BYJ-48 + ULN2003AN の標準的な8相ハーフステップ。
                # 回転方向が逆の場合は MOTOR_REVERSE を切り替えるか、STEPPER_PINS の順番を反転する。
                half_step_sequence = [
                    (1, 0, 0, 0),
                    (1, 1, 0, 0),
                    (0, 1, 0, 0),
                    (0, 1, 1, 0),
                    (0, 0, 1, 0),
                    (0, 0, 1, 1),
                    (0, 0, 0, 1),
                    (1, 0, 0, 1),
                ]

                for pin in stepper_pins:
                    GPIO_runtime.setup(pin, GPIO_runtime.OUT, initial=GPIO_runtime.LOW)

                def _coils_off():
                    for pin in stepper_pins:
                        GPIO_runtime.output(pin, GPIO_runtime.LOW)

                def _resolve_step_delay():
                    configured_delay = config.get('STEPPER_STEP_DELAY')
                    if configured_delay not in (None, ''):
                        delay = float(configured_delay)
                    else:
                        # 28BYJ-48は高速にしすぎるとトルク不足で脱調するため、下限を2.5msにする。
                        speed = max(1, min(100, int(current_motor_speed)))
                        delay = 0.012 - (speed - 1) * (0.0095 / 99.0)
                    return max(0.0025, delay)

                def _rotate_stepper(duration_sec, reverse=False, fixed_steps=None):
                    step_delay = _resolve_step_delay()
                    if fixed_steps is None:
                        fixed_steps = int(float(duration_sec) / step_delay)
                    fixed_steps = max(1, int(fixed_steps))
                    sequence = list(reversed(half_step_sequence)) if reverse else half_step_sequence

                    print(
                        f"INFO: ステッピングモーター駆動開始 "
                        f"pins={stepper_pins}, steps={fixed_steps}, delay={step_delay:.4f}s, reverse={reverse}"
                    )
                    try:
                        for step_index in range(fixed_steps):
                            if stop_event.is_set():
                                print("INFO: 停止要求を検知したためステッピングモーターを停止します")
                                break
                            phase = sequence[step_index % len(sequence)]
                            for pin, value in zip(stepper_pins, phase):
                                GPIO_runtime.output(pin, GPIO_runtime.HIGH if value else GPIO_runtime.LOW)
                            time.sleep(step_delay)
                    finally:
                        _coils_off()
                    print("✓ ステッピングモーター駆動完了")

                configured_steps = config.get('STEPPER_STEPS', 0)
                try:
                    configured_steps = int(configured_steps)
                except (TypeError, ValueError):
                    configured_steps = 0
                main_steps = configured_steps if configured_steps > 0 else None

                if current_use_sensor:
                    print("INFO: センサー付きでステッピング排出を開始します。")

                    if SENSOR_CHECK_PRE:
                        print("\n--- ステップ1: 回転前のセンサーチェック ---")
                        if not check_sensor("(回転前)"):
                            print("⚠ 警告: 回転前に物体を検知。詰まり解消を試みます")
                            send_log_to_server("警告: 排出前に残留物検知")
                            for attempt in range(JAM_CLEAR_ATTEMPTS):
                                print(f"詰まり解消試行 {attempt + 1}/{JAM_CLEAR_ATTEMPTS}")
                                _rotate_stepper(min(0.5, float(current_motor_duration)), reverse=not current_motor_reverse)
                                time.sleep(0.3)
                                if check_sensor("(解消確認)"):
                                    print("✓ 詰まり解消成功")
                                    break
                            else:
                                print("✗ 詰まり解消失敗。強制的に排出を試みます。")
                                send_log_to_server("エラー: 初期詰まり解消失敗")
                        else:
                            print("✓ 回転前チェック: 排出口クリア")

                    print(f"\n--- ステップ2: ステッピングモーター回転 ({current_motor_duration}秒) ---")
                    _rotate_stepper(current_motor_duration, reverse=current_motor_reverse, fixed_steps=main_steps)

                    if SENSOR_CHECK_POST:
                        print("\n--- ステップ3: 回転後のセンサーチェック ---")
                        time.sleep(SENSOR_STABILIZE_TIME)
                        if check_sensor("(回転後)"):
                            print("✓ 回転後チェック: 正常に排出されました")
                            send_log_to_server("排出完了 (STEPPER/RASPI_DIRECT 正常)")
                        else:
                            print("⚠ 警告: 回転後も物体検知。追加排出を試みます")
                            send_log_to_server("警告: 排出後に物体残留")
                            for attempt in range(JAM_CLEAR_ATTEMPTS):
                                print(f"追加排出 {attempt + 1}/{JAM_CLEAR_ATTEMPTS}")
                                _rotate_stepper(min(0.7, float(current_motor_duration)), reverse=current_motor_reverse)
                                time.sleep(0.3)
                                if check_sensor("(追加確認)"):
                                    print("✓ 追加排出成功")
                                    send_log_to_server("排出完了 (STEPPER/RASPI_DIRECT 追加試行後)")
                                    break
                            else:
                                print("✗ 排出失敗: 物体が詰まっています")
                                send_log_to_server("エラー: 排出失敗 (STEPPER/RASPI_DIRECT 詰まり)")
                                return False
                    else:
                        print("✓ 排出完了 (回転後チェック無効)")
                        send_log_to_server("排出完了 (STEPPER/RASPI_DIRECT チェックなし)")
                else:
                    print(
                        f"INFO: センサーなしでステッピング排出 "
                        f"(速度:{current_motor_speed}, 時間:{current_motor_duration}秒)"
                    )
                    _rotate_stepper(current_motor_duration, reverse=current_motor_reverse, fixed_steps=main_steps)
                    send_log_to_server("排出完了 (STEPPER/RASPI_DIRECT センサーなし)")

                return True

            except Exception as e:
                msg = f"ステッピングモーター制御エラー: {e}"
                print(f"!! {msg}")
                send_log_to_server(msg)
                try:
                    for pin in config.get('STEPPER_PINS', [5, 6, 13, 19]):
                        GPIO_runtime.output(int(pin), GPIO_runtime.LOW)
                except Exception:
                    pass
                return False
'''


def patch_unit_client_source(source: str) -> str:
    """archive/unit_client.py に STEPPER + RASPI_DIRECT 分岐を実行時注入する。

    本来は archive/unit_client.py 側に直接統合するのが理想だが、unit.py から実行する
    既存構成を壊さず、ULN2003AN + 28BYJ-48 をすぐ動かすための互換パッチ。
    """
    if "STEPPER/RASPI_DIRECT" in source:
        return source

    source = source.replace(
        '"CONTROL_METHOD": "ARDUINO_SERIAL", "USE_SENSOR": True,',
        '"CONTROL_METHOD": "RASPI_DIRECT", "USE_SENSOR": True,\n'
        '    "STEPPER_PINS": [5, 6, 13, 19], "STEPPER_STEP_DELAY": 0.0025, "STEPPER_STEPS": 0,'
    )
    source = source.replace(
        "        'JAM_CLEAR_ATTEMPTS': 'JAM_CLEAR_ATTEMPTS',\n    }",
        "        'JAM_CLEAR_ATTEMPTS': 'JAM_CLEAR_ATTEMPTS',\n"
        "        'STEPPER_PINS': 'STEPPER_PINS',\n"
        "        'STEPPER_STEP_DELAY': 'STEPPER_STEP_DELAY',\n"
        "        'STEPPER_STEPS': 'STEPPER_STEPS',\n"
        "    }"
    )
    source = source.replace(
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15)\n                }',
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15),\n'
        '                    "STEPPER_PINS": config.get("STEPPER_PINS", [5, 6, 13, 19]),\n'
        '                    "STEPPER_STEP_DELAY": config.get("STEPPER_STEP_DELAY", 0.0025),\n'
        '                    "STEPPER_STEPS": config.get("STEPPER_STEPS", 0)\n'
        '                }'
    )

    target = "        elif current_control_method == 'ARDUINO_SERIAL':"
    if target not in source:
        raise RuntimeError("unit_client.py の Arduino 分岐が見つからず、STEPPER/RASPI_DIRECT パッチを適用できません")
    return source.replace(target, STEPPER_DIRECT_BRANCH + "\n" + target, 1)


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    unit_client_path = os.path.join(script_dir, 'archive', 'unit_client.py')
    if not os.path.exists(unit_client_path):
        print(f"エラー: {unit_client_path} が見つかりません")
        sys.exit(1)

    with open(unit_client_path, 'r', encoding='utf-8') as f:
        source = f.read()

    patched_source = patch_unit_client_source(source)
    exec_globals = {
        '__name__': '__main__',
        '__file__': unit_client_path,
        '__package__': None,
    }
    exec(compile(patched_source, unit_client_path, 'exec'), exec_globals)


if __name__ == '__main__':
    main()
