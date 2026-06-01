# -*- coding: utf-8 -*-
"""Runtime patch for main_stepping_branch.

This branch is dedicated to Raspberry Pi GPIO direct control of
ULN2003AN + 28BYJ-48.  The archived common implementation remains untouched.
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

STEPPER_BRANCH_MARKER = "elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':"

STEPPER_DIRECT_BRANCH = r'''
        elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':
            # ULN2003AN + 28BYJ-48 を Raspberry Pi GPIO から直接駆動する。
            # 28BYJ-48はIN1,IN3,IN2,IN4の位相順が安定しやすい。
            try:
                def _parse_int_list(raw, default):
                    if raw in (None, ''):
                        raw = default
                    if isinstance(raw, str):
                        return [int(x.strip()) for x in raw.split(',') if x.strip()]
                    return [int(x) for x in raw]

                actual_pins = _parse_int_list(config.get('STEPPER_PINS'), [5, 6, 13, 19])
                if len(actual_pins) != 4:
                    raise ValueError(f"STEPPER_PINS は IN1,IN2,IN3,IN4 の4本で指定してください: {actual_pins}")

                phase_order = _parse_int_list(config.get('STEPPER_PHASE_ORDER'), [0, 2, 1, 3])
                if sorted(phase_order) != [0, 1, 2, 3]:
                    raise ValueError(f"STEPPER_PHASE_ORDER は 0,1,2,3 の並べ替えで指定してください: {phase_order}")
                drive_pins = [actual_pins[i] for i in phase_order]

                drive_mode = str(config.get('STEPPER_DRIVE_MODE', 'full')).strip().lower()
                if drive_mode == 'half':
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
                    default_steps_per_rev = 4096
                else:
                    # 2相励磁フルステップ。1相励磁よりトルクが出やすく、まず回す用途に向く。
                    sequence = [
                        (1, 1, 0, 0),
                        (0, 1, 1, 0),
                        (0, 0, 1, 1),
                        (1, 0, 0, 1),
                    ]
                    default_steps_per_rev = 2048

                steps_per_rev = int(config.get('STEPPER_STEPS_PER_REV', default_steps_per_rev))

                for pin in actual_pins:
                    GPIO_runtime.setup(pin, GPIO_runtime.OUT, initial=GPIO_runtime.LOW)

                def _coils_off():
                    for pin in actual_pins:
                        GPIO_runtime.output(pin, GPIO_runtime.LOW)

                def _resolve_step_delay():
                    configured_delay = config.get('STEPPER_STEP_DELAY')
                    if configured_delay not in (None, ''):
                        delay = float(configured_delay)
                    else:
                        speed = max(1, min(100, int(current_motor_speed)))
                        # 28BYJ-48は速すぎると脱調する。100でも約10msを標準にする。
                        delay = 0.030 - (speed - 1) * (0.020 / 99.0)
                    return max(0.006, delay)

                def _rotate_stepper(duration_sec=None, reverse=False, fixed_steps=None):
                    step_delay = _resolve_step_delay()
                    if fixed_steps is None:
                        fixed_steps = int(float(duration_sec) / step_delay)
                    fixed_steps = max(1, int(fixed_steps))
                    seq = list(reversed(sequence)) if reverse else sequence

                    print(
                        f"INFO: STEPPER/RASPI_DIRECT start actual_pins(IN1-4)={actual_pins}, "
                        f"phase_order={phase_order}, drive_pins={drive_pins}, mode={drive_mode}, "
                        f"steps={fixed_steps}, delay={step_delay:.4f}s, reverse={reverse}"
                    )
                    try:
                        for step_index in range(fixed_steps):
                            if stop_event.is_set():
                                print("INFO: 停止要求を検知したためステッピングモーターを停止します")
                                break
                            phase = seq[step_index % len(seq)]
                            for pin, value in zip(drive_pins, phase):
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
                        send_log_to_server("排出完了 (STEPPER/RASPI_DIRECT チェックなし)")
                else:
                    print(f"INFO: センサーなしでステッピング排出 (時間:{current_motor_duration}秒)")
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
        config.setdefault('STEPPER_PHASE_ORDER', [0, 2, 1, 3])
        config.setdefault('STEPPER_STEP_DELAY', 0.01)
        config.setdefault('STEPPER_DRIVE_MODE', 'full')
        config.setdefault('STEPPER_STEPS', 0)
        config.setdefault('STEPPER_STEPS_PER_REV', 2048)
        config.setdefault('STEPPER_TEST_STEPS', 256)

    def _parse_int_list(value):
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(',') if x.strip()]
        return [int(x) for x in value]

    def _format_list(key, default):
        value = config.get(key, default)
        if isinstance(value, str):
            return value
        return ','.join(str(x) for x in value)

    def _actual_pins():
        pins = _parse_int_list(config.get('STEPPER_PINS', [5, 6, 13, 19]))
        if len(pins) != 4:
            raise ValueError(f"STEPPER_PINS は IN1,IN2,IN3,IN4 の4本です: {pins}")
        return pins

    def _phase_order():
        order = _parse_int_list(config.get('STEPPER_PHASE_ORDER', [0, 2, 1, 3]))
        if sorted(order) != [0, 1, 2, 3]:
            raise ValueError(f"STEPPER_PHASE_ORDER は 0,1,2,3 の並べ替えです: {order}")
        return order

    def _sequences():
        mode = str(config.get('STEPPER_DRIVE_MODE', 'full')).lower()
        if mode == 'half':
            return [
                (1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
                (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1),
            ]
        return [(1, 1, 0, 0), (0, 1, 1, 0), (0, 0, 1, 1), (1, 0, 0, 1)]

    def _coils_off(pins):
        for pin in pins:
            GPIO.output(pin, GPIO.LOW)

    def _run_stepper_now(steps=None, seconds=None, reverse=None, label='manual', phase_order_override=None, confirm=True):
        if PLATFORM == 'PC':
            print("\n✗ PCモードのためGPIOテストは実行できません。Raspberry Pi上で実行してください。")
            return False
        try:
            actual = _actual_pins()
            order = phase_order_override if phase_order_override is not None else _phase_order()
            drive_pins = [actual[i] for i in order]
            delay = max(0.006, float(config.get('STEPPER_STEP_DELAY', 0.01)))
            if reverse is None:
                reverse = bool(config.get('MOTOR_REVERSE', False))
            if steps is None:
                steps = int(float(seconds) / delay) if seconds is not None else int(config.get('STEPPER_TEST_STEPS', 256))
            steps = max(1, int(steps))
        except Exception as e:
            print(f"\n✗ ステッピング設定エラー: {e}")
            return False

        seq = _sequences()
        if reverse:
            seq = list(reversed(seq))

        print("\n" + "=" * 76)
        print(f"  ステッピングモーター実行: {label}")
        print("=" * 76)
        print(f"  actual pins IN1-4 : {actual}")
        print(f"  phase order       : {order}  -> drive pins {drive_pins}")
        print(f"  drive mode        : {config.get('STEPPER_DRIVE_MODE', 'full')}")
        print(f"  steps             : {steps}")
        print(f"  delay             : {delay:.4f} sec")
        print(f"  approx time       : {steps * delay:.2f} sec")
        print(f"  reverse           : {reverse}")
        print("=" * 76)
        if confirm and input("この設定で今すぐ回しますか？ [y/N]: ").strip().lower() != 'y':
            print("キャンセルしました")
            return False
        try:
            for pin in actual:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            print("[STEPPER] 回転開始")
            for idx in range(steps):
                phase = seq[idx % len(seq)]
                for pin, value in zip(drive_pins, phase):
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
                _coils_off(actual)
                print("[STEPPER] コイルOFF")
            except Exception:
                pass

    def _scan_phase_orders():
        candidates = [
            [0, 2, 1, 3],  # 28BYJ-48推奨: IN1,IN3,IN2,IN4
            [0, 1, 2, 3],
            [3, 1, 2, 0],
            [3, 2, 1, 0],
            [0, 2, 3, 1],
            [1, 3, 0, 2],
        ]
        print("\n各候補を短く回します。最も滑らかに回った番号を選んでください。")
        for idx, order in enumerate(candidates, 1):
            input(f"\n候補 {idx}: order={order} を回します。Enterで開始...")
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS', 256)), reverse=False,
                             label=f'配線順候補 {idx}', phase_order_override=order, confirm=False)
        choice = input(f"\n採用する候補番号 [1-{len(candidates)}] または Enterでキャンセル: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            config['STEPPER_PHASE_ORDER'] = candidates[int(choice) - 1]
            print(f"✓ STEPPER_PHASE_ORDER を {config['STEPPER_PHASE_ORDER']} に設定しました")
        else:
            print("キャンセルしました")

    _force_stepper_mode()
    while True:
        _force_stepper_mode()
        print("\n" + "=" * 82)
        print("  OITERU子機 設定メニュー - STEPPER / ULN2003AN / 28BYJ-48 専用")
        print("=" * 82)
        print(f"  1. サーバーURL             : {config['SERVER_URL']}")
        print(f"  2. 子機名                  : {config['UNIT_NAME']}")
        print(f"  3. パスワード              : {'*' * len(config.get('UNIT_PASSWORD', ''))}")
        print(f"  4. センサー使用            : {config['USE_SENSOR']}")
        print(f"  5. 緑LED PIN (BCM)         : {config['GREEN_LED_PIN']}")
        print(f"  6. 赤LED PIN (BCM)         : {config['RED_LED_PIN']}")
        print(f"  7. センサーPIN (BCM)       : {config['SENSOR_PIN']}")
        print(f"  8. STEPPER_PINS IN1-4      : {_format_list('STEPPER_PINS', [5,6,13,19])}")
        print(f"  9. PHASE_ORDER             : {_format_list('STEPPER_PHASE_ORDER', [0,2,1,3])}  (標準=0,2,1,3)")
        print(f" 10. STEP_DELAY 秒           : {config.get('STEPPER_STEP_DELAY', 0.01)}")
        print(f" 11. DRIVE_MODE              : {config.get('STEPPER_DRIVE_MODE', 'full')}  (full/half)")
        print(f" 12. 排出動作時間            : {config['MOTOR_DURATION']}秒")
        print(f" 13. 正方向テスト            : {config.get('STEPPER_TEST_STEPS', 256)} steps")
        print(f" 14. 逆方向テスト            : {config.get('STEPPER_TEST_STEPS', 256)} steps")
        print(f" 15. 配線順スキャン          : 複数phase_orderを順番に試す")
        print(f" 16. 任意ステップ数で回す    : 手入力")
        print(f" 17. 任意秒数で回す          : 手入力")
        print(f" 18. テスト用ステップ数      : {config.get('STEPPER_TEST_STEPS', 256)}")
        print(f" 19. 固定排出ステップ数      : {config.get('STEPPER_STEPS', 0)}  (0=秒数指定)")
        print(f" 20. 回転方向反転            : {config['MOTOR_REVERSE']}")
        print("=" * 82)
        print("  a. 親機自動探知   d. 診断   off. コイルOFF   s. 保存して起動   q. 起動")
        print("=" * 82)
        choice = input("\n選択 [1-20/a/d/off/s/q]: ").strip().lower()

        if choice == '1':
            v = input(f"サーバーURL [{config['SERVER_URL']}]: ").strip()
            if v: config['SERVER_URL'] = v
        elif choice == '2':
            v = input(f"子機名 [{config['UNIT_NAME']}]: ").strip()
            if v: config['UNIT_NAME'] = v
        elif choice == '3':
            v = input("パスワード: ").strip()
            if v: config['UNIT_PASSWORD'] = v
        elif choice == '4':
            config['USE_SENSOR'] = input("センサーを使用しますか？ [Y/n]: ").strip().lower() != 'n'
        elif choice == '5':
            v = input(f"緑LED PIN [{config['GREEN_LED_PIN']}]: ").strip()
            if v.isdigit(): config['GREEN_LED_PIN'] = int(v)
        elif choice == '6':
            v = input(f"赤LED PIN [{config['RED_LED_PIN']}]: ").strip()
            if v.isdigit(): config['RED_LED_PIN'] = int(v)
        elif choice == '7':
            v = input(f"センサーPIN [{config['SENSOR_PIN']}]: ").strip()
            if v.isdigit(): config['SENSOR_PIN'] = int(v)
        elif choice == '8':
            v = input(f"STEPPER_PINS IN1,IN2,IN3,IN4 (BCM) [{_format_list('STEPPER_PINS',[5,6,13,19])}]: ").strip()
            if v:
                pins = _parse_int_list(v)
                if len(pins) == 4: config['STEPPER_PINS'] = pins
                else: print("✗ 4本指定してください")
        elif choice == '9':
            v = input(f"PHASE_ORDER [{_format_list('STEPPER_PHASE_ORDER',[0,2,1,3])}]: ").strip()
            if v:
                order = _parse_int_list(v)
                if sorted(order) == [0,1,2,3]: config['STEPPER_PHASE_ORDER'] = order
                else: print("✗ 0,1,2,3の並べ替えで指定してください")
        elif choice == '10':
            v = input(f"STEP_DELAY秒 [{config.get('STEPPER_STEP_DELAY',0.01)}]: ").strip()
            if v: config['STEPPER_STEP_DELAY'] = max(0.006, float(v))
        elif choice == '11':
            v = input("DRIVE_MODE [full/half]: ").strip().lower()
            if v in ('full','half'):
                config['STEPPER_DRIVE_MODE'] = v
                config['STEPPER_STEPS_PER_REV'] = 2048 if v == 'full' else 4096
        elif choice == '12':
            v = input(f"排出動作時間秒 [{config['MOTOR_DURATION']}]: ").strip()
            if v: config['MOTOR_DURATION'] = float(v)
        elif choice == '13':
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS',256)), reverse=False, label='正方向テスト')
            input("\nEnterキーで戻る...")
        elif choice == '14':
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS',256)), reverse=True, label='逆方向テスト')
            input("\nEnterキーで戻る...")
        elif choice == '15':
            _scan_phase_orders()
            input("\nEnterキーで戻る...")
        elif choice == '16':
            steps = int(input("回すstep数: ").strip())
            rev = input("逆方向? [y/N]: ").strip().lower() == 'y'
            _run_stepper_now(steps=steps, reverse=rev, label=f'任意steps={steps}')
            input("\nEnterキーで戻る...")
        elif choice == '17':
            sec = float(input("回す秒数: ").strip())
            rev = input("逆方向? [y/N]: ").strip().lower() == 'y'
            _run_stepper_now(seconds=sec, reverse=rev, label=f'任意seconds={sec}')
            input("\nEnterキーで戻る...")
        elif choice == '18':
            v = input(f"テスト用ステップ数 [{config.get('STEPPER_TEST_STEPS',256)}]: ").strip()
            if v: config['STEPPER_TEST_STEPS'] = max(1, int(v))
        elif choice == '19':
            v = input(f"固定排出ステップ数 [{config.get('STEPPER_STEPS',0)}] (0=秒数指定): ").strip()
            if v: config['STEPPER_STEPS'] = max(0, int(v))
        elif choice == '20':
            config['MOTOR_REVERSE'] = input("排出時に逆方向にしますか？ [y/N]: ").strip().lower() == 'y'
        elif choice == 'off':
            try:
                actual = _actual_pins()
                for pin in actual: GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                _coils_off(actual)
                print("✓ コイルOFF")
            except Exception as e:
                print(f"✗ コイルOFF失敗: {e}")
            input("\nEnterキーで戻る...")
        elif choice == 'a':
            servers = scan_for_servers(timeout=5)
            if servers:
                for i, u in enumerate(servers, 1): print(f"  {i}. {u}")
                v = input(f"使用する親機 [1-{len(servers)}]: ").strip()
                if v.isdigit() and 1 <= int(v) <= len(servers): config['SERVER_URL'] = servers[int(v)-1]
            else:
                print("親機が見つかりませんでした")
            input("\nEnterキーで戻る...")
        elif choice == 'd':
            run_cui_diagnostics(config)
        elif choice == 's':
            _force_stepper_mode()
            if save_config(config): print("✓ 設定を保存しました")
            return config
        elif choice == 'q':
            _force_stepper_mode()
            return config
        else:
            print("✗ 無効な選択です")
'''

STEPPER_CUI_DIAGNOSTICS = r'''
def run_cui_diagnostics(config):
    """CUIモードでステッピング構成のハードウェア診断を実行する。"""
    config['MOTOR_TYPE'] = 'STEPPER'
    config['CONTROL_METHOD'] = 'RASPI_DIRECT'
    config.setdefault('STEPPER_PHASE_ORDER', [0, 2, 1, 3])
    config.setdefault('STEPPER_STEP_DELAY', 0.01)
    config.setdefault('STEPPER_DRIVE_MODE', 'full')

    if PLATFORM == "PC":
        print("\n[GPIO] PCモードのため診断不可。RPi.GPIOが使えるRaspberry Pi上で実行してください。")
        return

    def _parse(raw, default):
        if raw in (None, ''): raw = default
        if isinstance(raw, str): return [int(x.strip()) for x in raw.split(',') if x.strip()]
        return [int(x) for x in raw]

    pins = _parse(config.get('STEPPER_PINS'), [5,6,13,19])
    order = _parse(config.get('STEPPER_PHASE_ORDER'), [0,2,1,3])
    print(f"\n[STEPPER] actual pins IN1-4: {pins}")
    print(f"[STEPPER] phase order: {order} -> drive pins {[pins[i] for i in order]}")
    print(f"[STEPPER] drive mode: {config.get('STEPPER_DRIVE_MODE')}")
    print(f"[STEPPER] step delay: {config.get('STEPPER_STEP_DELAY')}")
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    print("[STEPPER] GPIO出力初期化: OK")

    if config.get('USE_SENSOR'):
        try:
            GPIO.setup(config['SENSOR_PIN'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            val = GPIO.input(config['SENSOR_PIN'])
            print(f"[センサー] GPIO {config['SENSOR_PIN']}: {'クリア' if val else '物体検知'} (値:{val})")
        except Exception as e:
            print(f"[センサー] エラー: {e}")

    print("[PCA9685] 不要: このブランチはULN2003ANをGPIO直結で駆動します。")
    input("\nEnterキーで戻る...")
'''


def replace_top_level_function(source: str, function_name: str, replacement: str) -> str:
    marker = f"def {function_name}("
    start = source.find(marker)
    if start == -1:
        raise RuntimeError(f"{function_name} が見つかりません")
    next_def = source.find("\ndef ", start + len(marker))
    next_class = source.find("\nclass ", start + len(marker))
    candidates = [i for i in (next_def, next_class) if i != -1]
    end = min(candidates) + 1 if candidates else len(source)
    return source[:start] + replacement.strip() + "\n\n" + source[end:]


def inject_stepper_branch(source: str) -> str:
    if STEPPER_BRANCH_MARKER in source:
        return source
    target = "        elif current_control_method == 'ARDUINO_SERIAL':"
    if target not in source:
        raise RuntimeError("Arduino分岐が見つからず、STEPPER/RASPI_DIRECT分岐を挿入できません")
    return source.replace(target, STEPPER_DIRECT_BRANCH + "\n" + target, 1)


def patch_unit_client_source(source: str) -> str:
    """Convert archive/unit_client.py into the stepping-branch variant at runtime."""
    source = source.replace(HARDWARE_IMPORT_OLD, HARDWARE_IMPORT_NEW)

    source = source.replace(
        '"CONTROL_METHOD": "ARDUINO_SERIAL", "USE_SENSOR": True,',
        '"CONTROL_METHOD": "RASPI_DIRECT", "USE_SENSOR": True,\n'
        '    "STEPPER_PINS": [5, 6, 13, 19], "STEPPER_PHASE_ORDER": [0, 2, 1, 3], '
        '"STEPPER_STEP_DELAY": 0.01, "STEPPER_DRIVE_MODE": "full", '
        '"STEPPER_STEPS": 0, "STEPPER_STEPS_PER_REV": 2048, "STEPPER_TEST_STEPS": 256,'
    )
    source = source.replace(
        "        'JAM_CLEAR_ATTEMPTS': 'JAM_CLEAR_ATTEMPTS',\n    }",
        "        'JAM_CLEAR_ATTEMPTS': 'JAM_CLEAR_ATTEMPTS',\n"
        "        'STEPPER_PINS': 'STEPPER_PINS',\n"
        "        'STEPPER_PHASE_ORDER': 'STEPPER_PHASE_ORDER',\n"
        "        'STEPPER_STEP_DELAY': 'STEPPER_STEP_DELAY',\n"
        "        'STEPPER_DRIVE_MODE': 'STEPPER_DRIVE_MODE',\n"
        "        'STEPPER_STEPS': 'STEPPER_STEPS',\n"
        "        'STEPPER_STEPS_PER_REV': 'STEPPER_STEPS_PER_REV',\n"
        "        'STEPPER_TEST_STEPS': 'STEPPER_TEST_STEPS',\n"
        "    }"
    )
    source = source.replace(
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15)\n                }',
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15),\n'
        '                    "STEPPER_PINS": config.get("STEPPER_PINS", [5, 6, 13, 19]),\n'
        '                    "STEPPER_PHASE_ORDER": config.get("STEPPER_PHASE_ORDER", [0, 2, 1, 3]),\n'
        '                    "STEPPER_STEP_DELAY": config.get("STEPPER_STEP_DELAY", 0.01),\n'
        '                    "STEPPER_DRIVE_MODE": config.get("STEPPER_DRIVE_MODE", "full"),\n'
        '                    "STEPPER_STEPS": config.get("STEPPER_STEPS", 0),\n'
        '                    "STEPPER_STEPS_PER_REV": config.get("STEPPER_STEPS_PER_REV", 2048),\n'
        '                    "STEPPER_TEST_STEPS": config.get("STEPPER_TEST_STEPS", 256)\n'
        '                }'
    )

    source = source.replace(
        "            if CONTROL_METHOD == 'RASPI_DIRECT':\n                import Adafruit_PCA9685 as Adafruit_PCA9685_runtime\n            elif CONTROL_METHOD == 'ARDUINO_SERIAL':",
        "            if CONTROL_METHOD == 'RASPI_DIRECT' and MOTOR_TYPE == 'SERVO':\n"
        "                import Adafruit_PCA9685 as Adafruit_PCA9685_runtime\n"
        "            elif CONTROL_METHOD == 'RASPI_DIRECT' and MOTOR_TYPE == 'STEPPER':\n"
        "                Adafruit_PCA9685_runtime = None\n"
        "            elif CONTROL_METHOD == 'ARDUINO_SERIAL':"
    )

    source = source.replace(
        "        # I2Cチェック\n        if config.get('CONTROL_METHOD') == 'RASPI_DIRECT':",
        "        # I2Cチェック\n        if config.get('CONTROL_METHOD') == 'RASPI_DIRECT' and config.get('MOTOR_TYPE') == 'STEPPER':\n"
        "            print(\"  - I2C/PCA9685: スキップ (STEPPER/RASPI_DIRECT GPIO直結)\")\n"
        "            diagnostics.append((\"GPIO Stepper\", \"OK\", \"ULN2003AN/28BYJ-48\"))\n"
        "        elif config.get('CONTROL_METHOD') == 'RASPI_DIRECT':"
    )

    source = inject_stepper_branch(source)
    source = replace_top_level_function(source, "show_cui_menu", STEPPER_CUI_MENU)
    source = replace_top_level_function(source, "run_cui_diagnostics", STEPPER_CUI_DIAGNOSTICS)
    return source
