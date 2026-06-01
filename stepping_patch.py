# -*- coding: utf-8 -*-
"""Runtime patch for main_stepping_branch.

This branch is dedicated to Raspberry Pi GPIO direct control of
ULN2003AN + 28BYJ-48.  Branch-specific behavior is kept here so the archived
common unit_client.py and the servo branch are not polluted.
"""


HARDWARE_IMPORT_OLD = '''# --- ハードウェアライブラリのインポート (エラーを許容) ---
PLATFORM = "RASPI"
try:
    import RPi.GPIO as GPIO
    import Adafruit_PCA9685
    GPIO.setmode(GPIO.BCM)
except (ImportError, RuntimeError):
    PLATFORM = "PC"
    print("!! 警告: Raspberry Piライブラリが見つかりません。PCモードで起動します。")'''

HARDWARE_IMPORT_NEW = '''# --- ハードウェアライブラリのインポート (エラーを許容) ---
# main_stepping_branch は ULN2003AN + 28BYJ-48 をGPIO直結で使うため、
# PCA9685 が無いだけで PCモードに落としてはいけない。
PLATFORM = "RASPI"
Adafruit_PCA9685 = None
try:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
except (ImportError, RuntimeError) as exc:
    PLATFORM = "PC"
    print(f"!! 警告: RPi.GPIO が利用できません。PCモードで起動します: {exc}")

try:
    import Adafruit_PCA9685
except Exception:
    Adafruit_PCA9685 = None'''


STEPPER_DIRECT_BRANCH = r'''
        elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':
            # ULN2003AN + 28BYJ-48 を Raspberry Pi GPIO から直接駆動する。
            try:
                raw_pins = config.get('STEPPER_PINS', [5, 6, 13, 19])
                if isinstance(raw_pins, str):
                    raw_pins = [int(pin.strip()) for pin in raw_pins.split(',') if pin.strip()]
                stepper_pins = [int(pin) for pin in raw_pins]
                if len(stepper_pins) != 4:
                    raise ValueError(f"STEPPER_PINS は IN1-IN4 の4本で指定してください: {raw_pins}")

                steps_per_rev = int(config.get('STEPPER_STEPS_PER_REV', 4096))
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
                        speed = max(1, min(100, int(current_motor_speed)))
                        # 28BYJ-48は高速にしすぎると脱調しやすい。
                        # speed=100 でも約5msを下限にする。
                        delay = 0.015 - (speed - 1) * (0.010 / 99.0)
                    return max(0.005, delay)

                def _rotate_stepper(duration_sec=None, reverse=False, fixed_steps=None):
                    step_delay = _resolve_step_delay()
                    if fixed_steps is None:
                        fixed_steps = int(float(duration_sec) / step_delay)
                    fixed_steps = max(1, int(fixed_steps))
                    sequence = list(reversed(half_step_sequence)) if reverse else half_step_sequence

                    print(
                        f"INFO: ステッピングモーター駆動開始 "
                        f"pins={stepper_pins}, steps={fixed_steps}, delay={step_delay:.4f}s, reverse={reverse}, "
                        f"steps_per_rev={steps_per_rev}"
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
                                _rotate_stepper(fixed_steps=max(64, steps_per_rev // 16), reverse=not current_motor_reverse)
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
                    _rotate_stepper(duration_sec=current_motor_duration, reverse=current_motor_reverse, fixed_steps=main_steps)

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
                                _rotate_stepper(fixed_steps=max(128, steps_per_rev // 8), reverse=current_motor_reverse)
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
                    _rotate_stepper(duration_sec=current_motor_duration, reverse=current_motor_reverse, fixed_steps=main_steps)
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


STEPPER_CUI_MENU = r'''
def show_cui_menu(config):
    """CUIモードの設定メニューを表示する。main_stepping_branch はステッピング専用。"""

    def _force_stepper_mode():
        config['MOTOR_TYPE'] = 'STEPPER'
        config['CONTROL_METHOD'] = 'RASPI_DIRECT'
        config.setdefault('STEPPER_PINS', [5, 6, 13, 19])
        config.setdefault('STEPPER_STEP_DELAY', 0.005)
        config.setdefault('STEPPER_STEPS', 0)
        config.setdefault('STEPPER_STEPS_PER_REV', 4096)
        config.setdefault('STEPPER_TEST_STEPS', 512)

    def _format_pins():
        pins = config.get('STEPPER_PINS', [5, 6, 13, 19])
        if isinstance(pins, str):
            return pins
        return ','.join(str(pin) for pin in pins)

    def _parse_pins(value):
        pins = [int(pin.strip()) for pin in value.split(',') if pin.strip()]
        if len(pins) != 4:
            raise ValueError('IN1,IN2,IN3,IN4 の4本をカンマ区切りで指定してください')
        return pins

    def _get_pins():
        raw_pins = config.get('STEPPER_PINS', [5, 6, 13, 19])
        if isinstance(raw_pins, str):
            return _parse_pins(raw_pins)
        pins = [int(pin) for pin in raw_pins]
        if len(pins) != 4:
            raise ValueError(f"STEPPER_PINS は4本必要です: {raw_pins}")
        return pins

    def _coils_off(pins):
        for pin in pins:
            GPIO.output(pin, GPIO.LOW)

    def _run_stepper_now(steps=None, seconds=None, reverse=None, label='manual'):
        """CUIメニューから即時にモーターを回す。"""
        if PLATFORM == 'PC':
            print("\n✗ PCモードのためGPIOテストは実行できません。Raspberry Pi上で実行してください。")
            print("  RPi.GPIO が使えない状態です。PCA9685 の有無はこのブランチでは不要です。")
            return False

        try:
            pins = _get_pins()
            delay = float(config.get('STEPPER_STEP_DELAY', 0.005))
            delay = max(0.005, delay)
            if reverse is None:
                reverse = bool(config.get('MOTOR_REVERSE', False))
            if steps is None:
                if seconds is None:
                    steps = int(config.get('STEPPER_TEST_STEPS', 512))
                else:
                    steps = int(float(seconds) / delay)
            steps = max(1, int(steps))
            steps_per_rev = max(1, int(config.get('STEPPER_STEPS_PER_REV', 4096)))
        except Exception as e:
            print(f"\n✗ ステッピング設定エラー: {e}")
            return False

        sequence = [
            (1, 0, 0, 0),
            (1, 1, 0, 0),
            (0, 1, 0, 0),
            (0, 1, 1, 0),
            (0, 0, 1, 0),
            (0, 0, 1, 1),
            (0, 0, 0, 1),
            (1, 0, 0, 1),
        ]
        if reverse:
            sequence = list(reversed(sequence))

        print("\n" + "=" * 68)
        print(f"  ステッピングモーター実行: {label}")
        print("=" * 68)
        print(f"  pins          : {pins}  (ULN2003AN IN1,IN2,IN3,IN4 / BCM)")
        print(f"  steps         : {steps} half-steps")
        print(f"  step_delay    : {delay:.4f} sec")
        print(f"  approx time   : {steps * delay:.2f} sec")
        print(f"  reverse       : {reverse}")
        print(f"  steps_per_rev : {steps_per_rev}")
        print("=" * 68)
        confirm = input("この設定で今すぐ回しますか？ [y/N]: ").strip().lower()
        if confirm != 'y':
            print("キャンセルしました")
            return False

        try:
            for pin in pins:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

            print("[STEPPER] 回転開始")
            for idx in range(steps):
                phase = sequence[idx % len(sequence)]
                for pin, value in zip(pins, phase):
                    GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
                time.sleep(delay)
            print("[STEPPER] 回転完了")
            return True
        except KeyboardInterrupt:
            print("\n[STEPPER] キーボード割り込みで停止")
            return False
        except Exception as e:
            print(f"[STEPPER] 回転エラー: {e}")
            return False
        finally:
            try:
                _coils_off(pins)
                print("[STEPPER] コイルOFF")
            except Exception:
                pass

    _force_stepper_mode()

    while True:
        _force_stepper_mode()
        print("\n" + "=" * 76)
        print("  OITERU子機 設定メニュー - STEPPER / ULN2003AN / 28BYJ-48 専用")
        print("=" * 76)
        print(f"  1. サーバーURL             : {config['SERVER_URL']}")
        print(f"  2. 子機名                  : {config['UNIT_NAME']}")
        print(f"  3. パスワード              : {'*' * len(config.get('UNIT_PASSWORD', ''))}")
        print(f"  4. センサー使用            : {config['USE_SENSOR']}")
        print(f"  5. 緑LED PIN (BCM)         : {config['GREEN_LED_PIN']}")
        print(f"  6. 赤LED PIN (BCM)         : {config['RED_LED_PIN']}")
        print(f"  7. センサーPIN (BCM)       : {config['SENSOR_PIN']}")
        print(f"  8. STEPPER_PINS (IN1-IN4)  : {_format_pins()}")
        print(f"  9. STEP_DELAY 秒           : {config.get('STEPPER_STEP_DELAY', 0.005)}")
        print(f" 10. 固定ステップ数          : {config.get('STEPPER_STEPS', 0)}  (0=時間指定)")
        print(f" 11. 排出動作時間            : {config['MOTOR_DURATION']}秒")
        print(f" 12. 回転方向反転            : {config['MOTOR_REVERSE']}")
        print(f" 13. 正方向に1回転テスト     : {config.get('STEPPER_STEPS_PER_REV', 4096)} half-steps")
        print(f" 14. 逆方向に1回転テスト     : {config.get('STEPPER_STEPS_PER_REV', 4096)} half-steps")
        print(f" 15. 任意ステップ数で回す    : 手入力")
        print(f" 16. 任意秒数で回す          : 手入力")
        print(f" 17. テスト用ステップ数      : {config.get('STEPPER_TEST_STEPS', 512)}")
        print(f" 18. 1回転ステップ数         : {config.get('STEPPER_STEPS_PER_REV', 4096)}")
        print(f" 19. 速度補助値              : {config['MOTOR_SPEED']}  (STEP_DELAY未指定時のみ使用)")
        print(f" 20. 回転前センサーチェック  : {config.get('SENSOR_CHECK_PRE', True)}")
        print(f" 21. 回転後センサーチェック  : {config.get('SENSOR_CHECK_POST', True)}")
        print(f" 22. 詰まり解消試行回数      : {config.get('JAM_CLEAR_ATTEMPTS', 3)}")
        print("=" * 76)
        print("  a. 親機自動探知")
        print("  d. ハードウェア診断 / GPIO短時間テスト")
        print("  off. コイルOFF")
        print("  s. 設定を保存して起動")
        print("  q. 保存せずに起動")
        print("=" * 76)

        choice = input("\n選択 [1-22/a/d/off/s/q]: ").strip().lower()

        if choice == '1':
            new_val = input(f"サーバーURL [{config['SERVER_URL']}]: ").strip()
            if new_val:
                config['SERVER_URL'] = new_val
        elif choice == '2':
            new_val = input(f"子機名 [{config['UNIT_NAME']}]: ").strip()
            if new_val:
                config['UNIT_NAME'] = new_val
        elif choice == '3':
            new_val = input("パスワード: ").strip()
            if new_val:
                config['UNIT_PASSWORD'] = new_val
        elif choice == '4':
            print("\nセンサー使用:")
            print("  1. 使用する")
            print("  2. 使用しない")
            sensor_choice = input("選択 [1-2]: ").strip()
            if sensor_choice == '1':
                config['USE_SENSOR'] = True
            elif sensor_choice == '2':
                config['USE_SENSOR'] = False
        elif choice == '5':
            new_val = input(f"緑LED PIN (BCM) [{config['GREEN_LED_PIN']}]: ").strip()
            if new_val.isdigit():
                config['GREEN_LED_PIN'] = int(new_val)
        elif choice == '6':
            new_val = input(f"赤LED PIN (BCM) [{config['RED_LED_PIN']}]: ").strip()
            if new_val.isdigit():
                config['RED_LED_PIN'] = int(new_val)
        elif choice == '7':
            new_val = input(f"センサーPIN (BCM) [{config['SENSOR_PIN']}]: ").strip()
            if new_val.isdigit():
                config['SENSOR_PIN'] = int(new_val)
        elif choice == '8':
            new_val = input(f"STEPPER_PINS IN1,IN2,IN3,IN4 (BCM) [{_format_pins()}]: ").strip()
            if new_val:
                try:
                    config['STEPPER_PINS'] = _parse_pins(new_val)
                except ValueError as e:
                    print(f"\n✗ {e}")
        elif choice == '9':
            new_val = input(f"STEP_DELAY 秒 [{config.get('STEPPER_STEP_DELAY', 0.005)}]: ").strip()
            if new_val:
                try:
                    delay = float(new_val)
                    if delay < 0.005:
                        print("\n⚠ 28BYJ-48 は速すぎると脱調しやすいため 0.005 秒に丸めます")
                        delay = 0.005
                    config['STEPPER_STEP_DELAY'] = delay
                except ValueError:
                    print("\n✗ 数値を入力してください")
        elif choice == '10':
            new_val = input(f"固定ステップ数 [{config.get('STEPPER_STEPS', 0)}] (0=時間指定): ").strip()
            if new_val:
                try:
                    config['STEPPER_STEPS'] = max(0, int(new_val))
                except ValueError:
                    print("\n✗ 整数を入力してください")
        elif choice == '11':
            new_val = input(f"排出動作時間 (秒) [{config['MOTOR_DURATION']}]: ").strip()
            if new_val:
                try:
                    config['MOTOR_DURATION'] = float(new_val)
                except ValueError:
                    print("\n✗ 数値を入力してください")
        elif choice == '12':
            print("\n回転方向:")
            print("  1. 通常方向")
            print("  2. 反転方向")
            reverse_choice = input("選択 [1-2]: ").strip()
            if reverse_choice == '1':
                config['MOTOR_REVERSE'] = False
            elif reverse_choice == '2':
                config['MOTOR_REVERSE'] = True
        elif choice == '13':
            _run_stepper_now(
                steps=int(config.get('STEPPER_STEPS_PER_REV', 4096)),
                reverse=False,
                label='正方向 1回転テスト'
            )
            input("\nEnterキーで戻る...")
        elif choice == '14':
            _run_stepper_now(
                steps=int(config.get('STEPPER_STEPS_PER_REV', 4096)),
                reverse=True,
                label='逆方向 1回転テスト'
            )
            input("\nEnterキーで戻る...")
        elif choice == '15':
            try:
                steps = int(input("回す half-step 数: ").strip())
                rev = input("逆方向に回しますか？ [y/N]: ").strip().lower() == 'y'
                _run_stepper_now(steps=steps, reverse=rev, label=f'任意ステップ {steps}')
            except ValueError:
                print("\n✗ 整数を入力してください")
            input("\nEnterキーで戻る...")
        elif choice == '16':
            try:
                seconds = float(input("回す秒数: ").strip())
                rev = input("逆方向に回しますか？ [y/N]: ").strip().lower() == 'y'
                _run_stepper_now(seconds=seconds, reverse=rev, label=f'任意秒数 {seconds}秒')
            except ValueError:
                print("\n✗ 数値を入力してください")
            input("\nEnterキーで戻る...")
        elif choice == '17':
            new_val = input(f"テスト用ステップ数 [{config.get('STEPPER_TEST_STEPS', 512)}]: ").strip()
            if new_val:
                try:
                    config['STEPPER_TEST_STEPS'] = max(1, int(new_val))
                except ValueError:
                    print("\n✗ 整数を入力してください")
        elif choice == '18':
            new_val = input(f"1回転ステップ数 [{config.get('STEPPER_STEPS_PER_REV', 4096)}]: ").strip()
            if new_val:
                try:
                    config['STEPPER_STEPS_PER_REV'] = max(1, int(new_val))
                except ValueError:
                    print("\n✗ 整数を入力してください")
        elif choice == '19':
            new_val = input(f"速度補助値 (1-100) [{config['MOTOR_SPEED']}]: ").strip()
            if new_val.isdigit():
                config['MOTOR_SPEED'] = max(1, min(100, int(new_val)))
        elif choice == '20':
            print("\n回転前センサーチェック:")
            print("  1. 有効")
            print("  2. 無効")
            pre_choice = input("選択 [1-2]: ").strip()
            if pre_choice == '1':
                config['SENSOR_CHECK_PRE'] = True
            elif pre_choice == '2':
                config['SENSOR_CHECK_PRE'] = False
        elif choice == '21':
            print("\n回転後センサーチェック:")
            print("  1. 有効")
            print("  2. 無効")
            post_choice = input("選択 [1-2]: ").strip()
            if post_choice == '1':
                config['SENSOR_CHECK_POST'] = True
            elif post_choice == '2':
                config['SENSOR_CHECK_POST'] = False
        elif choice == '22':
            new_val = input(f"詰まり解消試行回数 [{config.get('JAM_CLEAR_ATTEMPTS', 3)}]: ").strip()
            if new_val.isdigit():
                config['JAM_CLEAR_ATTEMPTS'] = max(0, int(new_val))
        elif choice == 'off':
            try:
                pins = _get_pins()
                for pin in pins:
                    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                _coils_off(pins)
                print("\n✓ コイルをOFFにしました")
            except Exception as e:
                print(f"\n✗ コイルOFF失敗: {e}")
            input("\nEnterキーで戻る...")
        elif choice == 'a':
            print("\n" + "=" * 60)
            print("  親機自動探知を開始します...")
            print("=" * 60)
            servers = scan_for_servers(timeout=5)
            if servers:
                print(f"\n{len(servers)}台の親機を発見しました:")
                for idx, server_url in enumerate(servers, 1):
                    print(f"  {idx}. {server_url}")

                server_choice = input(f"\n使用する親機を選択 [1-{len(servers)}] または Enter でキャンセル: ").strip()
                try:
                    server_idx = int(server_choice) - 1
                    if 0 <= server_idx < len(servers):
                        config['SERVER_URL'] = servers[server_idx]
                        print(f"\n✓ サーバーURLを {servers[server_idx]} に設定しました")
                    else:
                        print("\n✗ 無効な選択です")
                except ValueError:
                    print("\n✗ キャンセルしました")
            else:
                print("\n✗ 親機が見つかりませんでした")
                print("  - 親機サーバー(app.py)が起動していることを確認してください")
                print("  - 同一ネットワークまたはTailscaleで接続されていることを確認してください")
            input("\nEnterキーで戻る...")
        elif choice == 'd':
            print("\n" + "=" * 60)
            print("  ステッピング用ハードウェア診断中...")
            print("=" * 60)
            run_cui_diagnostics(config)
        elif choice == 's':
            _force_stepper_mode()
            if save_config(config):
                print("\n✓ 設定を保存しました")
            else:
                print("\n✗ 設定の保存に失敗しました")
            return config
        elif choice == 'q':
            _force_stepper_mode()
            return config
        else:
            print("\n✗ 無効な選択です")
'''


STEPPER_CUI_DIAGNOSTICS = r'''
def run_cui_diagnostics(config):
    """CUIモードでステッピング構成のハードウェア診断を実行する。"""
    config['MOTOR_TYPE'] = 'STEPPER'
    config['CONTROL_METHOD'] = 'RASPI_DIRECT'
    config.setdefault('STEPPER_STEP_DELAY', 0.005)
    config.setdefault('STEPPER_STEPS_PER_REV', 4096)

    if PLATFORM == "PC":
        print("\n[GPIO] PCモードのため診断不可")
        print("[STEPPER] RPi.GPIO が使える Raspberry Pi 上で実行してください")
        return

    def _parse_pins(raw_pins):
        if isinstance(raw_pins, str):
            raw_pins = [int(pin.strip()) for pin in raw_pins.split(',') if pin.strip()]
        pins = [int(pin) for pin in raw_pins]
        if len(pins) != 4:
            raise ValueError(f"STEPPER_PINS は IN1-IN4 の4本で指定してください: {raw_pins}")
        return pins

    try:
        pins = _parse_pins(config.get('STEPPER_PINS', [5, 6, 13, 19]))
        print(f"\n[STEPPER] ULN2003AN IN1-IN4 GPIO(BCM): {pins}")
        for pin in pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        print("[STEPPER] GPIO出力初期化: OK")
    except Exception as e:
        print(f"\n[STEPPER] GPIO初期化エラー: {e}")
        input("\nEnterキーで戻る...")
        return

    try:
        if config.get('USE_SENSOR'):
            GPIO.setup(config['SENSOR_PIN'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            sensor_state = GPIO.input(config['SENSOR_PIN'])
            sensor_status = "クリア" if sensor_state == 1 else "物体検知"
            print(f"[センサー] GPIO {config['SENSOR_PIN']}: {sensor_status} (値: {sensor_state})")
        else:
            print("[センサー] 使用しない設定")
    except Exception as e:
        print(f"[センサー] エラー: {e}")

    print("[PCA9685] このブランチでは使用しません。STEPPER/RASPI_DIRECT はGPIO直結です。")
    print("[Arduino] このブランチでは使用しません。")

    test_choice = input("\n512 half-stepsだけ短くテスト回転しますか？ [y/N]: ").strip().lower()
    if test_choice == 'y':
        sequence = [
            (1, 0, 0, 0),
            (1, 1, 0, 0),
            (0, 1, 0, 0),
            (0, 1, 1, 0),
            (0, 0, 1, 0),
            (0, 0, 1, 1),
            (0, 0, 0, 1),
            (1, 0, 0, 1),
        ]
        if config.get('MOTOR_REVERSE', False):
            sequence = list(reversed(sequence))
        try:
            delay = float(config.get('STEPPER_STEP_DELAY', 0.005))
        except (TypeError, ValueError):
            delay = 0.005
        delay = max(0.005, delay)

        try:
            print(f"[STEPPER] テスト開始: steps=512, delay={delay:.4f}s")
            for idx in range(512):
                phase = sequence[idx % len(sequence)]
                for pin, value in zip(pins, phase):
                    GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
                time.sleep(delay)
            print("[STEPPER] テスト完了")
        except Exception as e:
            print(f"[STEPPER] テスト回転エラー: {e}")
        finally:
            for pin in pins:
                GPIO.output(pin, GPIO.LOW)
            print("[STEPPER] コイルOFF")

    input("\nEnterキーで戻る...")
'''


def replace_top_level_function(source: str, function_name: str, replacement: str) -> str:
    """Replace a top-level function in source."""
    marker = f"def {function_name}("
    start = source.find(marker)
    if start == -1:
        raise RuntimeError(f"{function_name} が見つかりません")

    next_def = source.find("\ndef ", start + len(marker))
    next_class = source.find("\nclass ", start + len(marker))
    candidates = [idx for idx in (next_def, next_class) if idx != -1]
    end = min(candidates) + 1 if candidates else len(source)
    return source[:start] + replacement.strip() + "\n\n" + source[end:]


def patch_unit_client_source(source: str) -> str:
    """Convert archive/unit_client.py into the stepping-branch variant at runtime."""
    source = source.replace(HARDWARE_IMPORT_OLD, HARDWARE_IMPORT_NEW)

    source = source.replace(
        '"CONTROL_METHOD": "ARDUINO_SERIAL", "USE_SENSOR": True,',
        '"CONTROL_METHOD": "RASPI_DIRECT", "USE_SENSOR": True,\n'
        '    "STEPPER_PINS": [5, 6, 13, 19], "STEPPER_STEP_DELAY": 0.005, '
        '"STEPPER_STEPS": 0, "STEPPER_STEPS_PER_REV": 4096, "STEPPER_TEST_STEPS": 512,'
    )
    source = source.replace(
        "        'JAM_CLEAR_ATTEMPTS': 'JAM_CLEAR_ATTEMPTS',\n    }",
        "        'JAM_CLEAR_ATTEMPTS': 'JAM_CLEAR_ATTEMPTS',\n"
        "        'STEPPER_PINS': 'STEPPER_PINS',\n"
        "        'STEPPER_STEP_DELAY': 'STEPPER_STEP_DELAY',\n"
        "        'STEPPER_STEPS': 'STEPPER_STEPS',\n"
        "        'STEPPER_STEPS_PER_REV': 'STEPPER_STEPS_PER_REV',\n"
        "        'STEPPER_TEST_STEPS': 'STEPPER_TEST_STEPS',\n"
        "    }"
    )
    source = source.replace(
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15)\n                }',
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15),\n'
        '                    "STEPPER_PINS": config.get("STEPPER_PINS", [5, 6, 13, 19]),\n'
        '                    "STEPPER_STEP_DELAY": config.get("STEPPER_STEP_DELAY", 0.005),\n'
        '                    "STEPPER_STEPS": config.get("STEPPER_STEPS", 0),\n'
        '                    "STEPPER_STEPS_PER_REV": config.get("STEPPER_STEPS_PER_REV", 4096),\n'
        '                    "STEPPER_TEST_STEPS": config.get("STEPPER_TEST_STEPS", 512)\n'
        '                }'
    )

    # Do not import PCA9685 for stepper GPIO direct mode.
    source = source.replace(
        "            if CONTROL_METHOD == 'RASPI_DIRECT':\n                import Adafruit_PCA9685 as Adafruit_PCA9685_runtime\n            elif CONTROL_METHOD == 'ARDUINO_SERIAL':",
        "            if CONTROL_METHOD == 'RASPI_DIRECT' and MOTOR_TYPE == 'SERVO':\n"
        "                import Adafruit_PCA9685 as Adafruit_PCA9685_runtime\n"
        "            elif CONTROL_METHOD == 'RASPI_DIRECT' and MOTOR_TYPE == 'STEPPER':\n"
        "                Adafruit_PCA9685_runtime = None\n"
        "            elif CONTROL_METHOD == 'ARDUINO_SERIAL':"
    )

    # Startup diagnostics should not require PCA9685 in stepper mode.
    source = source.replace(
        "        # I2Cチェック\n        if config.get('CONTROL_METHOD') == 'RASPI_DIRECT':\n            try:\n                import Adafruit_PCA9685\n                # I2Cバスを明示的に指定 (通常はbus=1)\n                pwm = Adafruit_PCA9685.PCA9685(busnum=1)\n                pwm.set_pwm_freq(50)\n                print(\"  ✓ I2C/PCA9685: 利用可能\")\n                diagnostics.append((\"I2C/PCA9685\", \"OK\", \"0x40\"))\n            except Exception as e:\n                print(f\"  ⚠ I2C/PCA9685: エラー ({str(e)[:40]})\")\n                diagnostics.append((\"I2C/PCA9685\", \"エラー\", str(e)[:30]))\n        else:\n            print(\"  - I2C: スキップ (Arduino制御モード)\")\n            diagnostics.append((\"I2C\", \"スキップ\", \"Arduino制御\"))",
        "        # ステッピング直結ではI2C/PCA9685は不要\n"
        "        if config.get('CONTROL_METHOD') == 'RASPI_DIRECT' and config.get('MOTOR_TYPE') == 'STEPPER':\n"
        "            print(\"  - I2C/PCA9685: スキップ (STEPPER/RASPI_DIRECT GPIO直結)\")\n"
        "            diagnostics.append((\"GPIO Stepper\", \"OK\", \"ULN2003AN/28BYJ-48\"))\n"
        "        elif config.get('CONTROL_METHOD') == 'RASPI_DIRECT':\n"
        "            try:\n"
        "                import Adafruit_PCA9685\n"
        "                pwm = Adafruit_PCA9685.PCA9685(busnum=1)\n"
        "                pwm.set_pwm_freq(50)\n"
        "                print(\"  ✓ I2C/PCA9685: 利用可能\")\n"
        "                diagnostics.append((\"I2C/PCA9685\", \"OK\", \"0x40\"))\n"
        "            except Exception as e:\n"
        "                print(f\"  ⚠ I2C/PCA9685: エラー ({str(e)[:40]})\")\n"
        "                diagnostics.append((\"I2C/PCA9685\", \"エラー\", str(e)[:30]))\n"
        "        else:\n"
        "            print(\"  - I2C: スキップ (Arduino制御モード)\")\n"
        "            diagnostics.append((\"I2C\", \"スキップ\", \"Arduino制御\"))"
    )

    if "STEPPER/RASPI_DIRECT" not in source:
        target = "        elif current_control_method == 'ARDUINO_SERIAL':"
        if target not in source:
            raise RuntimeError("unit_client.py の Arduino 分岐が見つからず、STEPPER/RASPI_DIRECT パッチを適用できません")
        source = source.replace(target, STEPPER_DIRECT_BRANCH + "\n" + target, 1)

    source = replace_top_level_function(source, "show_cui_menu", STEPPER_CUI_MENU)
    source = replace_top_level_function(source, "run_cui_diagnostics", STEPPER_CUI_DIAGNOSTICS)
    return source
