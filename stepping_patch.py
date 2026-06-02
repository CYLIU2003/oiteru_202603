# -*- coding: utf-8 -*-
"""Runtime patch for main_stepping_branch.

This branch is dedicated to Raspberry Pi GPIO direct control of
ULN2003AN + 28BYJ-48.  The archived common implementation remains untouched.

The stepper motor is driven by ``stepper_driver`` which prefers
``gpiozero`` + ``pigpio`` (the proven ``stepping_movement.py`` path), then
``RpiMotorLib.BYJMotor``, then direct GPIO fallback.  See
``stepper_driver.py`` for the dispatch logic.
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
    Adafruit_PCA9685 = None

# ステッピングモーター制御は stepper_driver 側で PigpioZero > RpiMotorLib > GPIO の順に選ぶ。
# インポートできなくても PC モードにせず、stepper_driver 側でフォールバックする。
try:
    import stepper_driver as _stepper_driver_import
except Exception as _stepper_driver_exc:
    _stepper_driver_import = None
    print(f"!! 警告: stepper_driver のインポートに失敗: {_stepper_driver_exc}")'''

STEPPER_BRANCH_MARKER = "elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':"

STEPPER_DIRECT_BRANCH = r'''
        elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':
            # ULN2003AN + 28BYJ-48 を stepper_driver 経由で駆動する。
            # 標準は RpiMotorLib (BYJMotor)、利用不可なら GPIO フォールバック。
            try:
                try:
                    import stepper_driver as _stepper_driver_runtime
                except Exception as _imp_exc:
                    _stepper_driver_runtime = None
                    print(f"!! STEPPER: stepper_driver インポート失敗: {_imp_exc}")

                if _stepper_driver_runtime is None:
                    print("!! STEPPER: 制御ライブラリが利用できないため失敗")
                    send_log_to_server("STEPPER: stepper_driver not available")
                    return False

                actual_pins = _stepper_driver_runtime.resolve_pins(config)
                phase_order = _stepper_driver_runtime.resolve_phase_order(config)
                drive_mode = _stepper_driver_runtime.resolve_drive_mode(config)
                step_delay = _stepper_driver_runtime.resolve_step_delay(config, motor_speed=current_motor_speed)
                wait = _stepper_driver_runtime.step_delay_for_drive_mode(drive_mode, step_delay)
                steps_per_rev = _stepper_driver_runtime.resolve_steps_per_rev(drive_mode)

                configured_steps = config.get('STEPPER_STEPS', 0)
                try:
                    configured_steps = int(configured_steps)
                except (TypeError, ValueError):
                    configured_steps = 0
                if configured_steps > 0:
                    main_steps = configured_steps
                else:
                    main_steps = max(1, int(float(current_motor_duration) / wait))

                print(
                    f"INFO: STEPPER/RASPI_DIRECT config actual_pins(IN1-4)={actual_pins}, "
                    f"phase_order={phase_order}, drive_mode={drive_mode}, "
                    f"main_steps={main_steps}, wait={wait:.4f}s, reverse={current_motor_reverse}"
                )

                def _rotate(duration_sec=None, fixed_steps=None, reverse=False, label='dispense'):
                    return _stepper_driver_runtime.run_stepper(
                        GPIO_runtime,
                        config,
                        steps=fixed_steps,
                        seconds=duration_sec,
                        reverse=reverse,
                        motor_speed=current_motor_speed,
                        stop_check=lambda: stop_event.is_set(),
                        label=label,
                    )

                if current_use_sensor:
                    print("INFO: センサー付きでステッピング排出を開始します。")
                    if SENSOR_CHECK_PRE:
                        print("\n--- ステップ1: 回転前のセンサーチェック ---")
                        if not check_sensor("(回転前)"):
                            print("⚠ 警告: 回転前に物体を検知。詰まり解消を試みます")
                            send_log_to_server("警告: 排出前に残留物検知")
                            for attempt in range(JAM_CLEAR_ATTEMPTS):
                                print(f"詰まり解消試行 {attempt + 1}/{JAM_CLEAR_ATTEMPTS}")
                                _rotate(fixed_steps=max(64, steps_per_rev // 16), reverse=not current_motor_reverse, label='jam-clear')
                                time.sleep(0.3)
                                if check_sensor("(解消確認)"):
                                    print("✓ 詰まり解消成功")
                                    break

                    print(f"\n--- ステップ2: ステッピングモーター回転 ({current_motor_duration}秒) ---")
                    _rotate(duration_sec=current_motor_duration, fixed_steps=main_steps, reverse=current_motor_reverse, label='nfc-dispense')

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
                                _rotate(fixed_steps=max(128, steps_per_rev // 8), reverse=current_motor_reverse, label='retry')
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
                    _rotate(duration_sec=current_motor_duration, fixed_steps=main_steps, reverse=current_motor_reverse, label='nfc-dispense-nosensor')
                    send_log_to_server("排出完了 (STEPPER/RASPI_DIRECT センサーなし)")

                return True

            except Exception as e:
                msg = f"ステッピングモーター制御エラー: {e}"
                print(f"!! {msg}")
                send_log_to_server(msg)
                try:
                    for pin in config.get('STEPPER_PINS', [21, 17, 27, 22]):
                        GPIO_runtime.output(int(pin), GPIO_runtime.LOW)
                except Exception:
                    pass
                return False
'''

STEPPER_CUI_MENU = r'''
def show_cui_menu(config):
    """CUIモードの設定メニューを表示する。main_stepping_branch はステッピング専用。"""

    try:
        import stepper_driver as _stepper_driver
    except Exception as _cui_imp_exc:
        _stepper_driver = None
        print(f"!! CUI: stepper_driver インポート失敗: {_cui_imp_exc}")

    def _force_stepper_mode():
        config['MOTOR_TYPE'] = 'STEPPER'
        config['CONTROL_METHOD'] = 'RASPI_DIRECT'
        config.setdefault('STEPPER_PINS', [21, 17, 27, 22])
        config.setdefault('STEPPER_PHASE_ORDER', [0, 1, 2, 3])
        config.setdefault('STEPPER_STEP_DELAY', 0.01)
        config.setdefault('STEPPER_DRIVE_MODE', 'half')
        config.setdefault('STEPPER_STEPS', 0)
        config.setdefault('STEPPER_STEPS_PER_REV', 2048)
        config.setdefault('STEPPER_TEST_STEPS', 2048)
        config.setdefault('STEPPER_BACKEND', 'auto')

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
        pins = _parse_int_list(config.get('STEPPER_PINS', [21, 17, 27, 22]))
        if len(pins) != 4:
            raise ValueError(f"STEPPER_PINS は IN1,IN2,IN3,IN4 の4本です: {pins}")
        return pins

    def _phase_order():
        order = _parse_int_list(config.get('STEPPER_PHASE_ORDER', [0, 1, 2, 3]))
        if sorted(order) != [0, 1, 2, 3]:
            raise ValueError(f"STEPPER_PHASE_ORDER は 0,1,2,3 の並べ替えです: {order}")
        return order

    def _sequences():
        mode = str(config.get('STEPPER_DRIVE_MODE', 'half')).lower()
        if mode == 'half':
            return [
                (1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
                (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1),
            ]
        return [(1, 1, 0, 0), (0, 1, 1, 0), (0, 0, 1, 1), (1, 0, 0, 1)]

    def _coils_off(pins):
        for pin in pins:
            GPIO.output(pin, GPIO.LOW)

    def _run_stepper_now(steps=None, seconds=None, reverse=None, label='manual', phase_order_override=None, confirm=True, force_backend=None):
        if PLATFORM == 'PC':
            print("\n✗ PCモードのためGPIOテストは実行できません。Raspberry Pi上で実行してください。")
            return False
        try:
            actual = _actual_pins()
            order = phase_order_override if phase_order_override is not None else _phase_order()
            drive_pins = [actual[i] for i in order]
            base_delay = max(0.01, float(config.get('STEPPER_STEP_DELAY', 0.01)))
            if reverse is None:
                reverse = bool(config.get('MOTOR_REVERSE', False))
            if steps is None:
                steps = int(float(seconds) / base_delay) if seconds is not None else int(config.get('STEPPER_TEST_STEPS', 2048))
            steps = max(1, int(steps))
            drive_mode = str(config.get('STEPPER_DRIVE_MODE', 'half')).lower()
            if drive_mode == 'half':
                wait = max(0.0015, base_delay)
            elif drive_mode == 'wave':
                wait = max(0.005, base_delay)
            else:
                wait = max(0.005, base_delay)
        except Exception as e:
            print(f"\n✗ ステッピング設定エラー: {e}")
            return False

        backend_setting = (force_backend if force_backend is not None
                           else str(config.get('STEPPER_BACKEND', 'auto')).lower())
        pigpio_ok = _stepper_driver is not None and _stepper_driver.gpiozero_available()
        library_ok = _stepper_driver is not None and _stepper_driver.library_available()
        if backend_setting == 'pigpio':
            effective_backend = 'PigpioZero' if pigpio_ok else 'PigpioZero (NG)'
        elif backend_setting == 'library':
            effective_backend = 'RpiMotorLib' if library_ok else 'RpiMotorLib (NG)'
        elif backend_setting == 'gpio':
            effective_backend = 'GPIO'
        else:
            effective_backend = 'PigpioZero' if pigpio_ok else ('RpiMotorLib' if library_ok else 'GPIO')

        print("\n" + "=" * 76)
        print(f"  ステッピングモーター実行: {label}")
        print("=" * 76)
        print(f"  backend           : {effective_backend}   (config STEPPER_BACKEND={backend_setting}, PigpioZero={pigpio_ok}, RpiMotorLib={library_ok})")
        print(f"  actual pins IN1-4 : {actual}")
        print(f"  phase order       : {order}  -> drive pins {drive_pins}")
        print(f"  drive mode        : {drive_mode}")
        print(f"  steps             : {steps}")
        print(f"  seconds           : {steps * wait:.2f} (=steps*delay)")
        print(f"  delay             : {wait:.4f} sec")
        print(f"  reverse           : {reverse}")
        print("=" * 76)
        if confirm and input("この設定で今すぐ回しますか？ [y/N]: ").strip().lower() != 'y':
            print("キャンセルしました")
            return False
        try:
            if _stepper_driver is not None:
                run_config = dict(config)
                run_config['STEPPER_PHASE_ORDER'] = order
                run_backend = force_backend if force_backend is not None else ('gpio' if phase_order_override is not None else None)
                result = _stepper_driver.run_stepper(
                    GPIO,
                    run_config,
                    steps=steps,
                    seconds=None,
                    reverse=reverse,
                    motor_speed=int(config.get('MOTOR_SPEED', 100)),
                    backend=run_backend,
                    label=label,
                )
                return bool(result.get('ok', False))
            # GPIO フォールバック
            for pin in actual:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            seq = _sequences()
            if reverse:
                seq = list(reversed(seq))
            print("[STEPPER] 回転開始 (GPIO fallback)")
            for idx in range(steps):
                phase = seq[idx % len(seq)]
                for pin, value in zip(drive_pins, phase):
                    GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
                time.sleep(wait)
            print("[STEPPER] 回転完了 (GPIO fallback)")
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
            [0, 1, 2, 3],  # stepping_movement.py と同じ IN1,IN2,IN3,IN4
            [0, 2, 1, 3],
            [3, 1, 2, 0],
            [3, 2, 1, 0],
            [0, 2, 3, 1],
            [1, 3, 0, 2],
        ]
        print("\n各候補を短く回します。最も滑らかに回った番号を選んでください。")
        for idx, order in enumerate(candidates, 1):
            input(f"\n候補 {idx}: order={order} を回します。Enterで開始...")
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS', 2048)), reverse=False,
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
        print(f"  8. STEPPER_PINS IN1-4      : {_format_list('STEPPER_PINS', [21,17,27,22])}  (標準=21,17,27,22)")
        print(f"  9. PHASE_ORDER             : {_format_list('STEPPER_PHASE_ORDER', [0,1,2,3])}  (標準=0,1,2,3)")
        print(f" 10. STEP_DELAY 秒           : {config.get('STEPPER_STEP_DELAY', 0.01)}")
        print(f" 11. DRIVE_MODE              : {config.get('STEPPER_DRIVE_MODE', 'half')}  (full/half/wave)")
        print(f" 12. 排出動作時間            : {config['MOTOR_DURATION']}秒")
        print(f" 13. 正方向テスト            : {config.get('STEPPER_TEST_STEPS', 2048)} steps")
        print(f" 14. 逆方向テスト            : {config.get('STEPPER_TEST_STEPS', 2048)} steps")
        print(f" 15. 配線順スキャン          : 複数phase_orderを順番に試す")
        print(f" 16. 任意ステップ数で回す    : 手入力")
        print(f" 17. 任意秒数で回す          : 手入力")
        print(f" 18. テスト用ステップ数      : {config.get('STEPPER_TEST_STEPS', 2048)}")
        print(f" 19. 固定排出ステップ数      : {config.get('STEPPER_STEPS', 0)}  (0=秒数指定)")
        print(f" 20. 回転方向反転            : {config['MOTOR_REVERSE']}")
        _pg_ok = (_stepper_driver is not None and _stepper_driver.gpiozero_available())
        _rml_ok = (_stepper_driver is not None and _stepper_driver.library_available())
        _avail = f"PigpioZero={'OK' if _pg_ok else 'NG'} RpiMotorLib={'OK' if _rml_ok else 'NG'}"
        print(f" 21. STEPPER_BACKEND         : {config.get('STEPPER_BACKEND', 'auto')}  (auto/pigpio/library/gpio)  {_avail}")
        print(f" 22. 自動選択正方向テスト    : {config.get('STEPPER_TEST_STEPS', 2048)} steps (auto 経由)")
        print(f" 23. 自動選択逆方向テスト    : {config.get('STEPPER_TEST_STEPS', 2048)} steps (auto 経由)")
        print(f" 24. 任意ステップ数          : 手入力 (現在のSTEPPER_BACKEND設定に従う)")
        print(f" 25. 任意秒数               : 手入力 (現在のSTEPPER_BACKEND設定に従う)")
        print(f" 26. GPIOフォールバック強制  : STEPPER_BACKEND=gpio でテスト")
        print("=" * 82)
        try:
            _used = {int(config.get('GREEN_LED_PIN')), int(config.get('RED_LED_PIN')), int(config.get('SENSOR_PIN'))}
            _conflicts = sorted(set(_actual_pins()) & _used)
            if _conflicts:
                print(f"  警告: ステッパーとLED/センサーで同じGPIOを使用しています: {_conflicts}")
        except Exception:
            pass
        print("  a. 親機自動探知   d. 診断   off. コイルOFF   s. 保存して起動   q. 起動")
        print("=" * 82)
        choice = input("\n選択 [1-26/a/d/off/s/q]: ").strip().lower()

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
            v = input(f"STEPPER_PINS IN1,IN2,IN3,IN4 (BCM) [{_format_list('STEPPER_PINS',[21,17,27,22])}]: ").strip()
            if v:
                pins = _parse_int_list(v)
                if len(pins) == 4: config['STEPPER_PINS'] = pins
                else: print("✗ 4本指定してください")
        elif choice == '9':
            v = input(f"PHASE_ORDER [{_format_list('STEPPER_PHASE_ORDER',[0,1,2,3])}]: ").strip()
            if v:
                order = _parse_int_list(v)
                if sorted(order) == [0,1,2,3]: config['STEPPER_PHASE_ORDER'] = order
                else: print("✗ 0,1,2,3の並べ替えで指定してください")
        elif choice == '10':
            v = input(f"STEP_DELAY秒 [{config.get('STEPPER_STEP_DELAY',0.01)}]: ").strip()
            if v: config['STEPPER_STEP_DELAY'] = max(0.01, float(v))
        elif choice == '11':
            v = input("DRIVE_MODE [full/half/wave]: ").strip().lower()
            if v in ('full','half','wave'):
                config['STEPPER_DRIVE_MODE'] = v
                config['STEPPER_STEPS_PER_REV'] = 2048
        elif choice == '12':
            v = input(f"排出動作時間秒 [{config['MOTOR_DURATION']}]: ").strip()
            if v: config['MOTOR_DURATION'] = float(v)
        elif choice == '13':
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS',2048)), reverse=False, label='正方向テスト')
            input("\nEnterキーで戻る...")
        elif choice == '14':
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS',2048)), reverse=True, label='逆方向テスト')
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
            v = input(f"テスト用ステップ数 [{config.get('STEPPER_TEST_STEPS',2048)}]: ").strip()
            if v: config['STEPPER_TEST_STEPS'] = max(1, int(v))
        elif choice == '19':
            v = input(f"固定排出ステップ数 [{config.get('STEPPER_STEPS',0)}] (0=秒数指定): ").strip()
            if v: config['STEPPER_STEPS'] = max(0, int(v))
        elif choice == '20':
            config['MOTOR_REVERSE'] = input("排出時に逆方向にしますか？ [y/N]: ").strip().lower() == 'y'
        elif choice == '21':
            cur = config.get('STEPPER_BACKEND', 'auto')
            v = input(f"STEPPER_BACKEND [{cur}] (auto/pigpio/library/gpio): ").strip().lower()
            if v in ('auto', 'pigpio', 'library', 'gpio'):
                config['STEPPER_BACKEND'] = v
                print(f"✓ STEPPER_BACKEND を {v} に設定しました")
            else:
                print("✗ auto / pigpio / library / gpio のいずれかを指定してください")
        elif choice == '22':
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS',2048)), reverse=False,
                             label='自動選択正方向テスト', force_backend=None)
            input("\nEnterキーで戻る...")
        elif choice == '23':
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS',2048)), reverse=True,
                             label='自動選択逆方向テスト', force_backend=None)
            input("\nEnterキーで戻る...")
        elif choice == '24':
            try:
                steps = int(input("回すstep数: ").strip())
                rev = input("逆方向? [y/N]: ").strip().lower() == 'y'
            except ValueError:
                print("✗ 数値を入力してください")
            else:
                _run_stepper_now(steps=steps, reverse=rev, label=f'任意steps={steps}')
            input("\nEnterキーで戻る...")
        elif choice == '25':
            try:
                sec = float(input("回す秒数: ").strip())
                rev = input("逆方向? [y/N]: ").strip().lower() == 'y'
            except ValueError:
                print("✗ 数値を入力してください")
            else:
                _run_stepper_now(seconds=sec, reverse=rev, label=f'任意seconds={sec}')
            input("\nEnterキーで戻る...")
        elif choice == '26':
            _run_stepper_now(steps=int(config.get('STEPPER_TEST_STEPS',2048)), reverse=False,
                             label='GPIOフォールバック強制テスト', force_backend='gpio')
            input("\nEnterキーで戻る...")
        elif choice == 'off':
            try:
                if _stepper_driver is not None:
                    _stepper_driver.coils_off(GPIO, config)
                else:
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
    config.setdefault('STEPPER_PHASE_ORDER', [0, 1, 2, 3])
    config.setdefault('STEPPER_STEP_DELAY', 0.01)
    config.setdefault('STEPPER_DRIVE_MODE', 'half')
    config.setdefault('STEPPER_BACKEND', 'auto')

    try:
        import stepper_driver as _stepper_driver_diag
    except Exception as _diag_imp_exc:
        _stepper_driver_diag = None
        print(f"!! DIAG: stepper_driver インポート失敗: {_diag_imp_exc}")

    if PLATFORM == "PC":
        print("\n[GPIO] PCモードのため診断不可。RPi.GPIOが使えるRaspberry Pi上で実行してください。")
        if _stepper_driver_diag is not None:
            print(f"[STEPPER] library_available={_stepper_driver_diag.library_available()}, "
                  f"import_error={_stepper_driver_diag.library_import_error()}")
        return

    def _parse(raw, default):
        if raw in (None, ''): raw = default
        if isinstance(raw, str): return [int(x.strip()) for x in raw.split(',') if x.strip()]
        return [int(x) for x in raw]

    pins = _parse(config.get('STEPPER_PINS'), [21,17,27,22])
    order = _parse(config.get('STEPPER_PHASE_ORDER'), [0,1,2,3])
    backend = str(config.get('STEPPER_BACKEND', 'auto')).lower()
    lib_ok = (_stepper_driver_diag is not None and _stepper_driver_diag.library_available())
    print(f"\n[STEPPER] actual pins IN1-4: {pins}")
    print(f"[STEPPER] phase order: {order} -> drive pins {[pins[i] for i in order]}")
    print(f"[STEPPER] drive mode: {config.get('STEPPER_DRIVE_MODE')}")
    print(f"[STEPPER] step delay: {config.get('STEPPER_STEP_DELAY')}")
    print(f"[STEPPER] backend config: STEPPER_BACKEND={backend}")
    try:
        used = {int(config.get('GREEN_LED_PIN')), int(config.get('RED_LED_PIN')), int(config.get('SENSOR_PIN'))}
        conflicts = sorted(set(pins) & used)
        if conflicts:
            print(f"[STEPPER] 警告: LED/センサーとGPIOが衝突しています: {conflicts}")
    except Exception:
        pass
    if _stepper_driver_diag is not None:
        print(f"[STEPPER] library_available={lib_ok}, import_error={_stepper_driver_diag.library_import_error()}")
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
        '    "STEPPER_PINS": [21, 17, 27, 22], "STEPPER_PHASE_ORDER": [0, 1, 2, 3], '
        '"STEPPER_STEP_DELAY": 0.01, "STEPPER_DRIVE_MODE": "half", '
        '"STEPPER_STEPS": 0, "STEPPER_STEPS_PER_REV": 2048, "STEPPER_TEST_STEPS": 2048, '
        '"STEPPER_BACKEND": "auto",'
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
        "        'STEPPER_BACKEND': 'STEPPER_BACKEND',\n"
        "    }"
    )
    source = source.replace(
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15)\n                }',
        '"PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15),\n'
        '                    "STEPPER_PINS": config.get("STEPPER_PINS", [21, 17, 27, 22]),\n'
        '                    "STEPPER_PHASE_ORDER": config.get("STEPPER_PHASE_ORDER", [0, 1, 2, 3]),\n'
        '                    "STEPPER_STEP_DELAY": config.get("STEPPER_STEP_DELAY", 0.01),\n'
        '                    "STEPPER_DRIVE_MODE": config.get("STEPPER_DRIVE_MODE", "half"),\n'
        '                    "STEPPER_STEPS": config.get("STEPPER_STEPS", 0),\n'
        '                    "STEPPER_STEPS_PER_REV": config.get("STEPPER_STEPS_PER_REV", 2048),\n'
        '                    "STEPPER_TEST_STEPS": config.get("STEPPER_TEST_STEPS", 2048),\n'
        '                    "STEPPER_BACKEND": config.get("STEPPER_BACKEND", "auto")\n'
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

    # Auto-install packages list: add RpiMotorLib for the stepper backend.
    source = source.replace(
        '            packages = [\n'
        '                "nfcpy", "requests", "flask", "pandas", "openpyxl", "numpy",\n'
        '                "RPi.GPIO", "Adafruit-PCA9685", "pyserial"\n'
        '            ]',
        '            packages = [\n'
        '                "nfcpy", "requests", "flask", "pandas", "openpyxl", "numpy",\n'
        '                "RPi.GPIO", "Adafruit-PCA9685", "pyserial",\n'
        '                "RpiMotorLib", "pigpio", "gpiozero"\n'
        '            ]'
    )
    source = source.replace(
        '            print(f"    pip install nfcpy requests flask pandas openpyxl numpy RPi.GPIO Adafruit-PCA9685 pyserial")',
        '            print(f"    pip install nfcpy requests flask pandas openpyxl numpy RPi.GPIO Adafruit-PCA9685 pyserial RpiMotorLib pigpio gpiozero")'
    )

    source = inject_stepper_branch(source)
    source = replace_top_level_function(source, "show_cui_menu", STEPPER_CUI_MENU)
    source = replace_top_level_function(source, "run_cui_diagnostics", STEPPER_CUI_DIAGNOSTICS)
    return source
