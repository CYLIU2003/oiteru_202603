import time
import sys
import threading
import json
import os
import hmac
import hashlib
import socket
import subprocess # Tailscale対応のため追加
import queue
import getpass  # 安全なパスワード入力
from pathlib import Path

# --------------------------------------------------------------------------
# --- 仮想環境の自動セットアップ ---
# --------------------------------------------------------------------------
def setup_virtualenv():
    """~/.hirameki仮想環境を自動作成・適用"""
    venv_path = Path.home() / ".hirameki"
    python_bin = venv_path / "bin" / "python"
    pip_bin = venv_path / "bin" / "pip"
    
    # 既に仮想環境内で実行されているかチェック
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # 仮想環境内で実行中
        return
    
    # .hirameki仮想環境が存在するかチェック
    if not venv_path.exists() or not python_bin.exists():
        print("=" * 60)
        print("  仮想環境 ~/.hirameki が見つかりません")
        print("  自動作成を開始します...")
        print("=" * 60)
        try:
            # 仮想環境を作成
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            print("✓ 仮想環境を作成しました")
            
            # pipをアップグレード
            subprocess.run([str(pip_bin), "install", "--upgrade", "pip"], check=True)
            print("✓ pipをアップグレードしました")
            
            # 必要なパッケージをインストール
            packages = [
                "nfcpy", "requests", "flask", "pandas", "openpyxl", "numpy",
                "RPi.GPIO", "Adafruit-PCA9685", "pyserial",
                "RpiMotorLib", "pigpio", "gpiozero"
            ]
            print(f"✓ 必要なパッケージをインストール中... ({', '.join(packages)})")
            subprocess.run([str(pip_bin), "install"] + packages, check=True)
            print("✓ パッケージのインストールが完了しました")
            
        except subprocess.CalledProcessError as e:
            print(f"✗ 仮想環境のセットアップに失敗しました: {e}")
            print("  手動でセットアップしてください:")
            print(f"    python3 -m venv {venv_path}")
            print(f"    source {venv_path}/bin/activate")
            print("    pip install nfcpy requests flask pandas openpyxl numpy RPi.GPIO Adafruit-PCA9685 pyserial RpiMotorLib pigpio gpiozero")
            sys.exit(1)
    
    # 仮想環境のPythonで再実行
    print(f"INFO: 仮想環境 {venv_path} を使用します")
    os.execv(str(python_bin), [str(python_bin)] + sys.argv)

# スクリプト起動時に仮想環境をセットアップ
if '--no-venv' not in sys.argv:
    setup_virtualenv()

# 仮想環境内でのインポート
import requests
import nfc

# --- GUIライブラリのインポート ---
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    import queue
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# --- ハードウェアライブラリのインポート (エラーを許容) ---
PLATFORM = "RASPI"
Adafruit_PCA9685 = None
try:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
except (ImportError, RuntimeError) as exc:
    PLATFORM = "PC"
    GPIO = None
    print(f"!! 警告: RPi.GPIO が利用できません。PCモードで起動します: {exc}")

try:
    import Adafruit_PCA9685
except Exception as exc:
    Adafruit_PCA9685 = None
    print(f"INFO: PCA9685 ライブラリは未使用または未導入です: {exc}")

try:
    import stepper_driver
except Exception as exc:
    stepper_driver = None
    print(f"INFO: stepper_driver を読み込めませんでした: {exc}")

# --------------------------------------------------------------------------
# --- 実行権限の確認 ---
# --------------------------------------------------------------------------
def ensure_root_privileges():
    """必要に応じてsudo経由で再実行し、ハードウェア制御に必要な権限を確保する"""
    if os.name == "nt":
        return  # Windowsではsudoは不要

    geteuid = getattr(os, "geteuid", None)
    if not callable(geteuid):
        return  # getuidが使えない環境では何もしない

    if geteuid() == 0:
        return  # 既にroot権限

    print("INFO: ハードウェア制御にはroot権限が必要です。sudo経由で再起動します...")
    
    # 仮想環境のPythonパスを取得
    venv_python = Path.home() / ".hirameki" / "bin" / "python"
    if venv_python.exists():
        python_exec = str(venv_python)
    else:
        python_exec = sys.executable
    
    try:
        # 環境変数を引き継いでsudoを実行
        env_vars = os.environ.copy()
        os.execvpe("sudo", ["sudo", "-E", python_exec] + sys.argv, env_vars)
    except FileNotFoundError:
        print("ERROR: sudoコマンドが見つかりません。sudoをインストールするか、手動でroot権限を付与して実行してください。")
        print(f"  実行コマンド例: sudo {python_exec} {' '.join(sys.argv)}")
    except Exception as exc:
        print(f"ERROR: sudoによる再実行に失敗しました: {exc}")

    sys.exit(1)


# --------------------------------------------------------------------------
# --- 設定ファイル関連 ---
# --------------------------------------------------------------------------
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    "SERVER_URL": "http://127.0.0.1:5000", "UNIT_NAME": "test-01",
    "UNIT_PASSWORD": "",  # 初回起動時は空、対話的に設定
    "MOTOR_TYPE": "STEPPER",
    "USE_SENSOR": True,
    "GREEN_LED_PIN": 17, "RED_LED_PIN": 27, "SENSOR_PIN": 22,
    "MOTOR_SPEED": 100, "MOTOR_DURATION": 2.0, "MOTOR_REVERSE": False,
    "SENSOR_CHECK_PRE": True,
    "SENSOR_CHECK_POST": True,
    "JAM_CLEAR_ATTEMPTS": 3,
    "SENSOR_STABILIZE_TIME": 0.3,
    "STEPPER_PINS": [21, 17, 27, 22],
    "STEPPER_PHASE_ORDER": [0, 1, 2, 3],
    "STEPPER_STEP_DELAY": 0.01,
    "STEPPER_DRIVE_MODE": "half",
    "STEPPER_STEPS": 0,
    "STEPPER_STEPS_PER_REV": 2048,
    "STEPPER_TEST_STEPS": 2048,
    "STEPPER_BACKEND": "auto"
}


def _hash_password_for_storage(password: str) -> str:
    """SHA-256 hash password before storing to config file.
    
    Production deployments should use systemd credentials or a hardware
    security module instead of config-file-based passwords.
    """
    if not password:
        return ""
    salt = hashlib.sha256(b"oiteru-unit-config-salt").digest()
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 100000, dklen=32
    ).hex()


def _masked_config_for_persistence(config: dict) -> dict:
    """Return a copy of config safe for writing to disk.
    
    The UNIT_PASSWORD is replaced with a one-way hash for at-rest protection.
    The live config dict retains the plaintext for API calls.
    """
    result = {}
    for key, value in config.items():
        if key.startswith("_"):
            continue
        if key == "UNIT_PASSWORD" and value:
            result[key] = _hash_password_for_storage(str(value))
        else:
            result[key] = value
    return result


def save_config(config):
    try:
        persisted_config = _masked_config_for_persistence(config)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(persisted_config, f, indent=4, ensure_ascii=False)
        return True
    except IOError:
        return False


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = DEFAULT_CONFIG.copy()
                loaded = json.load(f)
                config.update(loaded)
                return config
        except (IOError, json.JSONDecodeError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def parse_int_list(value, default=None):
    if value in (None, ""):
        value = default or []
    if isinstance(value, str):
        return [int(x.strip()) for x in value.split(',') if x.strip()]
    return [int(x) for x in value]


def format_int_list(value, default=None):
    try:
        return ','.join(str(x) for x in parse_int_list(value, default or []))
    except (TypeError, ValueError):
        return ','.join(str(x) for x in (default or []))


def parse_bool_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    return False


def normalize_motor_config(config):
    """モーター設定を保存・送信用に正規化する。"""
    normalized = dict(DEFAULT_CONFIG)
    normalized.update(config or {})
    if 'SENSOR_GPIO_PIN' in normalized and 'SENSOR_PIN' not in (config or {}):
        normalized['SENSOR_PIN'] = normalized['SENSOR_GPIO_PIN']

    normalized['MOTOR_TYPE'] = str(normalized.get('MOTOR_TYPE', 'STEPPER')).upper()
    if normalized['MOTOR_TYPE'] not in ('SERVO', 'STEPPER'):
        normalized['MOTOR_TYPE'] = DEFAULT_CONFIG['MOTOR_TYPE']
    normalized['USE_SENSOR'] = parse_bool_value(normalized.get('USE_SENSOR'))
    normalized['MOTOR_REVERSE'] = parse_bool_value(normalized.get('MOTOR_REVERSE'))

    for key in ('GREEN_LED_PIN', 'RED_LED_PIN', 'SENSOR_PIN', 'PCA9685_CHANNEL',
                'STEPPER_STEPS', 'STEPPER_STEPS_PER_REV', 'STEPPER_TEST_STEPS',
                'HEARTBEAT_INTERVAL', 'JAM_CLEAR_ATTEMPTS'):
        try:
            normalized[key] = int(normalized.get(key, DEFAULT_CONFIG.get(key, 0)))
        except (TypeError, ValueError):
            normalized[key] = DEFAULT_CONFIG.get(key, 0)

    for key in ('MOTOR_SPEED',):
        try:
            normalized[key] = max(1, min(100, int(normalized.get(key, DEFAULT_CONFIG[key]))))
        except (TypeError, ValueError):
            normalized[key] = DEFAULT_CONFIG[key]

    for key in ('MOTOR_DURATION', 'STEPPER_STEP_DELAY', 'SENSOR_STABILIZE_TIME'):
        try:
            normalized[key] = float(normalized.get(key, DEFAULT_CONFIG[key]))
        except (TypeError, ValueError):
            normalized[key] = DEFAULT_CONFIG[key]

    try:
        normalized['STEPPER_PINS'] = parse_int_list(
            normalized.get('STEPPER_PINS'),
            DEFAULT_CONFIG['STEPPER_PINS'],
        )
    except (TypeError, ValueError):
        normalized['STEPPER_PINS'] = list(DEFAULT_CONFIG['STEPPER_PINS'])
    if len(normalized['STEPPER_PINS']) != 4:
        normalized['STEPPER_PINS'] = list(DEFAULT_CONFIG['STEPPER_PINS'])
    try:
        normalized['STEPPER_PHASE_ORDER'] = parse_int_list(
            normalized.get('STEPPER_PHASE_ORDER'),
            DEFAULT_CONFIG['STEPPER_PHASE_ORDER'],
        )
    except (TypeError, ValueError):
        normalized['STEPPER_PHASE_ORDER'] = list(DEFAULT_CONFIG['STEPPER_PHASE_ORDER'])
    if sorted(normalized['STEPPER_PHASE_ORDER']) != [0, 1, 2, 3]:
        normalized['STEPPER_PHASE_ORDER'] = list(DEFAULT_CONFIG['STEPPER_PHASE_ORDER'])
    normalized['STEPPER_DRIVE_MODE'] = str(
        normalized.get('STEPPER_DRIVE_MODE', 'half')
    ).strip().lower()
    if normalized['STEPPER_DRIVE_MODE'] not in ('full', 'half', 'wave'):
        normalized['STEPPER_DRIVE_MODE'] = 'half'
    normalized['STEPPER_BACKEND'] = str(
        normalized.get('STEPPER_BACKEND', 'auto')
    ).strip().lower()
    if normalized['STEPPER_BACKEND'] not in ('auto', 'pigpio', 'library', 'gpio'):
        normalized['STEPPER_BACKEND'] = 'auto'

    normalized['SERVER_URL'] = str(normalized.get('SERVER_URL', DEFAULT_CONFIG['SERVER_URL']))
    normalized['UNIT_NAME'] = str(normalized.get('UNIT_NAME', DEFAULT_CONFIG['UNIT_NAME']))
    normalized['UNIT_PASSWORD'] = str(normalized.get('UNIT_PASSWORD', DEFAULT_CONFIG['UNIT_PASSWORD']))
    normalized['SENSOR_GPIO_PIN'] = normalized['SENSOR_PIN']
    return normalized


def apply_remote_config(remote_config, current_config):
    """親機から受信した設定を適用してconfig.jsonに保存する
    
    Args:
        remote_config: 親機から受信した設定辞書
        current_config: 現在の設定辞書（更新される）
    """
    # 設定キーのマッピング（親機キー → 子機キー）
    key_mapping = {
        'MOTOR_TYPE': 'MOTOR_TYPE',
        'USE_SENSOR': 'USE_SENSOR',
        'MOTOR_SPEED': 'MOTOR_SPEED',
        'MOTOR_DURATION': 'MOTOR_DURATION',
        'MOTOR_REVERSE': 'MOTOR_REVERSE',
        'SENSOR_GPIO_PIN': 'SENSOR_PIN',
        'SENSOR_PIN': 'SENSOR_PIN',
        'PCA9685_CHANNEL': 'PCA9685_CHANNEL',
        'HEARTBEAT_INTERVAL': 'HEARTBEAT_INTERVAL',
        'SENSOR_TIMEOUT': 'SENSOR_TIMEOUT',
        'SENSOR_CHECK_PRE': 'SENSOR_CHECK_PRE',
        'SENSOR_CHECK_POST': 'SENSOR_CHECK_POST',
        'JAM_CLEAR_ATTEMPTS': 'JAM_CLEAR_ATTEMPTS',
        'STEPPER_PINS': 'STEPPER_PINS',
        'STEPPER_PHASE_ORDER': 'STEPPER_PHASE_ORDER',
        'STEPPER_STEP_DELAY': 'STEPPER_STEP_DELAY',
        'STEPPER_DRIVE_MODE': 'STEPPER_DRIVE_MODE',
        'STEPPER_STEPS': 'STEPPER_STEPS',
        'STEPPER_STEPS_PER_REV': 'STEPPER_STEPS_PER_REV',
        'STEPPER_TEST_STEPS': 'STEPPER_TEST_STEPS',
        'STEPPER_BACKEND': 'STEPPER_BACKEND',
    }
    
    remote_config = normalize_motor_config(remote_config)
    updated_keys = []
    for remote_key, local_key in key_mapping.items():
        if remote_key in remote_config:
            old_value = current_config.get(local_key)
            new_value = remote_config[remote_key]
            
            # 値が変更された場合のみ更新
            if old_value != new_value:
                current_config[local_key] = new_value
                updated_keys.append(f"{local_key}: {old_value} → {new_value}")
    
    if updated_keys:
        print(f"[設定更新] 以下の設定が変更されました:")
        for key in updated_keys:
            print(f"  - {key}")
        
        # 設定をファイルに保存
        if save_config(current_config):
            print("[設定更新] config.json に保存し、即座に反映されます ✓")
        else:
            print("[設定更新] config.json の保存に失敗しました")
    else:
        print("[設定更新] 変更なし")


# --------------------------------------------------------------------------
# --- Flask API サーバー（親機からの即時設定変更を受信） ---
# --------------------------------------------------------------------------
def start_flask_api_server(config, port=5001):
    """子機側でFlask APIサーバーを起動し、親機からの設定変更を受信する
    
    Args:
        config: 設定辞書（参照）
        port: APIサーバーのポート番号
    """
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    app.config['config_ref'] = config  # 設定への参照を保持

    def is_authorized_request():
        expected_secret = str(app.config['config_ref'].get('_unit_api_token') or '')
        provided_secret = request.headers.get('X-Oiteru-Unit-Auth', '')
        return bool(expected_secret and provided_secret) and hmac.compare_digest(
            expected_secret,
            provided_secret,
        )

    def run_motor_test_from_api():
        test_config = normalize_motor_config(app.config['config_ref'])

        if PLATFORM != "RASPI":
            return {'ok': True, 'message': 'PCモードのためモーターは動作しません'}

        from unit.hardware_controller import HardwareController
        controller = HardwareController(gpio_module=GPIO, platform=PLATFORM)
        result = controller.test_motor(
            test_config,
            reverse=test_config.get('MOTOR_REVERSE', False),
            label='api-test',
        )
        return {'ok': result.success, 'message': result.message}
    
    @app.route('/api/config/update', methods=['POST'])
    def update_config():
        """親機から設定変更を受信"""
        if not is_authorized_request():
            return jsonify({'error': 'Unauthorized'}), 401
        try:
            data = request.json
            if not data or 'config' not in data:
                return jsonify({'error': 'Invalid request'}), 400
            
            new_config = data['config']
            current_config = app.config['config_ref']
            
            # 設定を適用
            apply_remote_config(new_config, current_config)
            
            return jsonify({
                'success': True,
                'message': '設定を更新しました'
            })
        except Exception as e:
            print(f"[Flask API] 設定更新エラー: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """ヘルスチェック"""
        return jsonify({'status': 'ok', 'unit_name': config.get('UNIT_NAME')})
    
    @app.route('/api/command', methods=['POST'])
    def execute_command():
        """親機からのデバッグコマンドを実行"""
        if not is_authorized_request():
            return jsonify({'error': 'Unauthorized'}), 401
        try:
            data = request.json
            command = data.get('command')
            
            if not command:
                return jsonify({'error': 'Command required'}), 400
            
            result = {
                'command': command,
                'executed': False,
                'output': None,
                'error': None
            }
            
            # サポートするコマンド
            if command == 'restart_nfc':
                result['output'] = 'NFCリーダーの再起動をリクエストしました'
                result['executed'] = True
                # NFCリーダー再起動フラグを設定（メインループで処理）
                config['_restart_nfc'] = True
                
            elif command == 'test_motor':
                motor_result = run_motor_test_from_api()
                result['output'] = motor_result['message']
                result['executed'] = bool(motor_result['ok'])
                if not motor_result['ok']:
                    result['error'] = motor_result['message']
                
            elif command == 'test_sensor':
                result['output'] = 'センサーテストをリクエストしました'
                result['executed'] = True
                config['_test_sensor'] = True
                
            elif command == 'get_status':
                # 現在の状態を返す
                status_info = {
                    'unit_name': config.get('UNIT_NAME'),
                    'motor_type': config.get('MOTOR_TYPE'),
                    'use_sensor': config.get('USE_SENSOR'),
                    'motor_speed': config.get('MOTOR_SPEED'),
                    'motor_duration': config.get('MOTOR_DURATION'),
                    'motor_reverse': config.get('MOTOR_REVERSE'),
                    'heartbeat_interval': config.get('HEARTBEAT_INTERVAL', 30),
                }
                
                # psutilを使ってシステム情報を取得
                try:
                    import psutil
                    status_info['cpu_percent'] = round(psutil.cpu_percent(interval=0.1), 1)
                    status_info['memory_percent'] = round(psutil.virtual_memory().percent, 1)
                    status_info['disk_percent'] = round(psutil.disk_usage('/').percent, 1)
                    
                    # 起動時間
                    import datetime
                    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
                    status_info['boot_time'] = boot_time.strftime('%Y-%m-%d %H:%M:%S')
                    
                except ImportError:
                    status_info['system_info'] = 'psutil未インストール (pip install psutil)'
                except Exception as e:
                    status_info['system_info_error'] = str(e)
                
                result['output'] = status_info
                result['executed'] = True
                
            elif command == 'ping':
                result['output'] = 'pong'
                result['executed'] = True
                
            else:
                result['error'] = f'不明なコマンド: {command}'
            
            return jsonify(result)
            
        except Exception as e:
            print(f"[Flask API] コマンド実行エラー: {e}")
            return jsonify({'error': str(e)}), 500
    
    # バックグラウンドで起動（ログ出力を抑制）
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    print(f"[Flask API] ポート {port} で設定受信サーバーを起動しました")
    app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)


# (ネットワークスキャン機能は変更なし)
def scan_for_servers(timeout=5):
    """UDPブロードキャストとTailscaleネットワークをスキャンして親機サーバーを見つける"""
    found_servers = {}
    
    # スキャン中であることをユーザーに通知 (GUIがある場合)
    # (ここではprint文で代替)
    print("INFO: 親機サーバーのスキャンを開始... (最大5秒)")

    # --- 方法1: Tailscaleネットワーク上のピアをスキャン ---
    try:
        # `tailscale status --json` でTailnet上の全デバイス情報を取得
        result = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # 自分以外のピアのIPアドレスをリストアップ
        peer_ips = [
            ip
            for peer in data.get('Peer', {}).values()
            if peer.get('Online', False) and 'TailscaleIPs' in peer
            for ip in peer.get('TailscaleIPs', [])
        ]
        
        print(f"INFO: Tailscale上で {len(peer_ips)} 台のオンラインデバイスを発見。")

        # 各IPの health エンドポイントに接続を試みる
        for ip in peer_ips:
            url = f"http://{ip}:5001"
            try:
                response = requests.get(f"{url}/api/health", timeout=0.5)
                if response.status_code == 200 and response.json().get('status') == 'ok':
                    print(f"  -> Tailscale経由で親機を発見: {url}")
                    found_servers[ip] = url
            except requests.RequestException:
                continue # 接続失敗は無視

    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"INFO: Tailscaleスキャンに失敗しました: {e}")

    # --- 方法2: 従来のUDPブロードキャストをリッスン ---
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)
    try:
        sock.bind(('', 12345))
    except OSError:
        # bindに失敗してもTailscaleの結果は返せるようにする
        return list(found_servers.values())

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            data, addr = sock.recvfrom(1024)
            message = json.loads(data.decode('utf-8'))
            if message.get("type") == "oiteru_server_heartbeat":
                ip = message.get('server_ip')
                url = f"http://{ip}:{message.get('port', 5001)}"
                if ip not in found_servers:
                    print(f"  -> UDP経由で親機を発見: {url}")
                    found_servers[ip] = url
        except socket.timeout:
            break
        except Exception:
            continue
            
    sock.close()
    print("INFO: スキャン完了。")
    return list(found_servers.values())

# --------------------------------------------------------------------------
# --- Tkinterによる設定GUI ---
# --------------------------------------------------------------------------
class SettingsGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("子機クライアント")
        self.config = load_config()
        self.client_thread = None
        self.stop_client_event = threading.Event()
        self.advanced_settings_visible = False
        self.hardware_status_visible = False
        self.is_checking_hardware = False
        self.hardware_thread = None
        self.gui_queue = queue.Queue()
        self.is_auto_scanning = False
        self.auto_detection_started = False

        self.MOTOR_TYPE_MAP = {"サーボモーター": "SERVO", "ステッピングモーター": "STEPPER"}
        self.USE_SENSOR_MAP = {"使用する": True, "使用しない": False}
        self.MOTOR_REVERSE_MAP = {"正回転": False, "逆回転": True}
        self.STEPPER_DRIVE_MODE_MAP = {"半ステップ": "half", "フルステップ": "full", "ウェーブ": "wave"}
        self.STEPPER_BACKEND_MAP = {"自動選択": "auto", "pigpio優先": "pigpio", "RpiMotorLib": "library", "GPIO直接": "gpio"}
        self.MOTOR_TYPE_MAP_REV = {v: k for k, v in self.MOTOR_TYPE_MAP.items()}
        self.USE_SENSOR_MAP_REV = {v: k for k, v in self.USE_SENSOR_MAP.items()}
        self.MOTOR_REVERSE_MAP_REV = {v: k for k, v in self.MOTOR_REVERSE_MAP.items()}
        self.STEPPER_DRIVE_MODE_MAP_REV = {v: k for k, v in self.STEPPER_DRIVE_MODE_MAP.items()}
        self.STEPPER_BACKEND_MAP_REV = {v: k for k, v in self.STEPPER_BACKEND_MAP.items()}
        
        self.create_widgets()
        self.load_settings()
        self.start_auto_server_detection()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.entries = {}
        self.comboboxes = {}
        self.buttons = {}
        
        # リモート設定同期の案内
        info_frame = ttk.Frame(main_frame, padding="5")
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        info_label = ttk.Label(info_frame, text="🔄 親機・従親機からの設定変更が自動的に反映されます", 
                              foreground="#006400", font=("", 9, "bold"))
        info_label.pack()
        
        status_frame = ttk.LabelFrame(main_frame, text="子機状態", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.stock_status = tk.StringVar(value="WAIT")
        self.nfc_status = tk.StringVar(value="停止中")
        ttk.Label(status_frame, text="NFCリーダー:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.nfc_status).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(status_frame, text="現在の在庫数:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.stock_status).grid(row=1, column=1, sticky=tk.W, padx=5)

        self.settings_frame = ttk.LabelFrame(main_frame, text="初期設定", padding="10")
        self.settings_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        ttk.Label(self.settings_frame, text="サーバーURL").grid(row=0, column=0, sticky=tk.W, pady=4)
        server_frame = ttk.Frame(self.settings_frame)
        server_frame.grid(row=0, column=1, sticky="ew")
        self.entries["SERVER_URL"] = ttk.Entry(server_frame, width=35)
        self.entries["SERVER_URL"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.buttons["scan"] = ttk.Button(server_frame, text="親機スキャン", command=self.run_scan)
        self.buttons["scan"].pack(side=tk.LEFT, padx=(5, 0))
        self.server_scan_status = tk.StringVar(value="")
        ttk.Label(server_frame, textvariable=self.server_scan_status, foreground="#006400").pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(self.settings_frame, text="子機名").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.entries["UNIT_NAME"] = ttk.Entry(self.settings_frame)
        self.entries["UNIT_NAME"].grid(row=1, column=1, sticky=(tk.W, tk.E))
        ttk.Label(self.settings_frame, text="パスワード").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.entries["UNIT_PASSWORD"] = ttk.Entry(self.settings_frame, show="*")
        self.entries["UNIT_PASSWORD"].grid(row=2, column=1, sticky=(tk.W, tk.E))
        ttk.Label(self.settings_frame, text="モーターの種類").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.comboboxes["MOTOR_TYPE"] = ttk.Combobox(self.settings_frame, values=list(self.MOTOR_TYPE_MAP.keys()), state="readonly")
        self.comboboxes["MOTOR_TYPE"].grid(row=3, column=1, sticky=(tk.W, tk.E))
        self.comboboxes["MOTOR_TYPE"].bind("<<ComboboxSelected>>", lambda _event: self.update_motor_option_visibility())
        ttk.Label(self.settings_frame, text="排出検知センサー").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.comboboxes["USE_SENSOR"] = ttk.Combobox(self.settings_frame, values=list(self.USE_SENSOR_MAP.keys()), state="readonly")
        self.comboboxes["USE_SENSOR"].grid(row=4, column=1, sticky=(tk.W, tk.E))

        self.hardware_status_frame = ttk.LabelFrame(self.settings_frame, text="ハードウェア状態", padding="10")
        self.hardware_status_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10, padx=5)
        self.pca_status = tk.StringVar(value="未診断")
        self.sensor_status = tk.StringVar(value="未診断")
        ttk.Label(self.hardware_status_frame, text="モータードライバー:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(self.hardware_status_frame, textvariable=self.pca_status).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(self.hardware_status_frame, text="排出検知センサー:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(self.hardware_status_frame, textvariable=self.sensor_status).grid(row=1, column=1, sticky=tk.W, padx=5)
        self.hardware_status_frame.grid_remove()

        self.advanced_settings_frame = ttk.Frame(self.settings_frame, padding="10 10 10 0")
        self.advanced_settings_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
        
        # ▼▼▼ 高度な設定にモーター方向を追加 ▼▼▼
        ttk.Label(self.advanced_settings_frame, text="モーター回転方向").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.comboboxes["MOTOR_REVERSE"] = ttk.Combobox(self.advanced_settings_frame, values=list(self.MOTOR_REVERSE_MAP.keys()), state="readonly")
        self.comboboxes["MOTOR_REVERSE"].grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

        ttk.Label(self.advanced_settings_frame, text="モーター速度 (1-100)").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.entries["MOTOR_SPEED"] = ttk.Entry(self.advanced_settings_frame)
        self.entries["MOTOR_SPEED"].grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(self.advanced_settings_frame, text="モーター動作時間 (秒)").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.entries["MOTOR_DURATION"] = ttk.Entry(self.advanced_settings_frame)
        self.entries["MOTOR_DURATION"].grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(self.advanced_settings_frame, text="---").grid(row=3, column=0, columnspan=2, pady=5)
        
        # (ピン設定などのラベルのrowを更新)
        ttk.Label(self.advanced_settings_frame, text="緑色LEDピン (BCM)").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.entries["GREEN_LED_PIN"] = ttk.Entry(self.advanced_settings_frame)
        self.entries["GREEN_LED_PIN"].grid(row=4, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.advanced_settings_frame, text="赤色LEDピン (BCM)").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.entries["RED_LED_PIN"] = ttk.Entry(self.advanced_settings_frame)
        self.entries["RED_LED_PIN"].grid(row=5, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.advanced_settings_frame, text="センサーピン (BCM)").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.entries["SENSOR_PIN"] = ttk.Entry(self.advanced_settings_frame)
        self.entries["SENSOR_PIN"].grid(row=6, column=1, sticky=(tk.W, tk.E), pady=2)

        self.servo_frame = ttk.LabelFrame(self.advanced_settings_frame, text="サーボ設定", padding="8")
        self.servo_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        ttk.Label(self.servo_frame, text="PCA9685チャンネル").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entries["PCA9685_CHANNEL"] = ttk.Entry(self.servo_frame)
        self.entries["PCA9685_CHANNEL"].grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

        self.stepper_frame = ttk.LabelFrame(self.advanced_settings_frame, text="ステッピングモーター設定", padding="8")
        self.stepper_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        ttk.Label(self.stepper_frame, text="IN1-4 GPIO (BCM)").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entries["STEPPER_PINS"] = ttk.Entry(self.stepper_frame)
        self.entries["STEPPER_PINS"].grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.stepper_frame, text="位相順序").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.entries["STEPPER_PHASE_ORDER"] = ttk.Entry(self.stepper_frame)
        self.entries["STEPPER_PHASE_ORDER"].grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.stepper_frame, text="1ステップ待機秒").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.entries["STEPPER_STEP_DELAY"] = ttk.Entry(self.stepper_frame)
        self.entries["STEPPER_STEP_DELAY"].grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.stepper_frame, text="駆動方式").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.comboboxes["STEPPER_DRIVE_MODE"] = ttk.Combobox(self.stepper_frame, values=list(self.STEPPER_DRIVE_MODE_MAP.keys()), state="readonly")
        self.comboboxes["STEPPER_DRIVE_MODE"].grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.stepper_frame, text="排出ステップ数").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.entries["STEPPER_STEPS"] = ttk.Entry(self.stepper_frame)
        self.entries["STEPPER_STEPS"].grid(row=4, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.stepper_frame, text="テストステップ数").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.entries["STEPPER_TEST_STEPS"] = ttk.Entry(self.stepper_frame)
        self.entries["STEPPER_TEST_STEPS"].grid(row=5, column=1, sticky=(tk.W, tk.E), pady=2)
        ttk.Label(self.stepper_frame, text="バックエンド").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.comboboxes["STEPPER_BACKEND"] = ttk.Combobox(self.stepper_frame, values=list(self.STEPPER_BACKEND_MAP.keys()), state="readonly")
        self.comboboxes["STEPPER_BACKEND"].grid(row=6, column=1, sticky=(tk.W, tk.E), pady=2)
        stepper_button_frame = ttk.Frame(self.stepper_frame)
        stepper_button_frame.grid(row=7, column=0, columnspan=2, sticky=tk.E, pady=(6, 0))
        self.buttons["stepper_forward"] = ttk.Button(stepper_button_frame, text="正方向テスト", command=lambda: self.run_stepper_test(False))
        self.buttons["stepper_forward"].pack(side=tk.LEFT, padx=4)
        self.buttons["stepper_reverse"] = ttk.Button(stepper_button_frame, text="逆方向テスト", command=lambda: self.run_stepper_test(True))
        self.buttons["stepper_reverse"].pack(side=tk.LEFT, padx=4)
        self.buttons["stepper_off"] = ttk.Button(stepper_button_frame, text="コイルOFF", command=self.coils_off_from_gui)
        self.buttons["stepper_off"].pack(side=tk.LEFT, padx=4)
        self.advanced_settings_frame.grid_remove()

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=tk.E, pady=15)
        self.buttons["hw_status"] = ttk.Button(button_frame, text="ハードウェア状態 🔽", command=self.toggle_hardware_status)
        self.buttons["hw_status"].pack(side=tk.LEFT, padx=10)
        self.buttons["advanced"] = ttk.Button(button_frame, text="高度な設定 🔽", command=self.toggle_advanced_settings)
        self.buttons["advanced"].pack(side=tk.LEFT, padx=10)
        self.buttons["save"] = ttk.Button(button_frame, text="設定を保存", command=self.save_settings)
        self.buttons["save"].pack(side=tk.LEFT, padx=5)
        self.buttons["start_stop"] = ttk.Button(button_frame, text="起動", command=self.toggle_client_run)
        self.buttons["start_stop"].pack(side=tk.LEFT)

    def toggle_client_run(self):
        if self.client_thread and self.client_thread.is_alive():
            self.stop_client_event.set()
            self.buttons["start_stop"].config(text="起動")
            self.set_widgets_state("normal")
            self.nfc_status.set("停止中")
            self.stock_status.set("---")
            print("INFO: 子機クライアントを中止しました。")
        else:
            self.save_settings(show_success_message=False)
            self.stop_client_event.clear()
            self.client_thread = threading.Thread(
                target=run_client,
                args=(load_config(), self.stop_client_event, self.gui_queue),
                daemon=True
            )
            self.client_thread.start()
            self.buttons["start_stop"].config(text="中止")
            self.set_widgets_state("disabled")
            self.nfc_status.set("待機中...")
            self.process_gui_queue()
            print("INFO: 子機クライアントを起動しました。")

    def set_widgets_state(self, state):
        self.settings_frame.config(text="初期設定 (実行中は変更不可)" if state == "disabled" else "初期設定")
        for widget in self.entries.values():
            widget.config(state=state)
        combo_state = "disabled" if state == "disabled" else "readonly"
        for widget in self.comboboxes.values():
            widget.config(state=combo_state)
        for name, button in self.buttons.items():
            if name not in ["start_stop", "hw_status"]:
                button.config(state=state)

    def process_gui_queue(self):
        try:
            while True:
                message = self.gui_queue.get_nowait()
                if 'stock' in message:
                    self.stock_status.set(str(message['stock']))
                if 'nfc' in message:
                    self.nfc_status.set(message['nfc'])
                if 'pca' in message:
                    self.pca_status.set(message['pca'])
                if 'sensor' in message:
                    self.sensor_status.set(message['sensor'])
                if 'auto_scan_message' in message:
                    self.server_scan_status.set(message['auto_scan_message'])
                if 'auto_server' in message:
                    server_url = message['auto_server']
                    if server_url:
                        self.entries["SERVER_URL"].delete(0, tk.END)
                        self.entries["SERVER_URL"].insert(0, server_url)
                        self.config["SERVER_URL"] = server_url
                        save_config(self.config)
                    self.is_auto_scanning = False
        except queue.Empty:
            pass
        finally:
            if (
                (self.client_thread and self.client_thread.is_alive())
                or self.is_checking_hardware
                or self.is_auto_scanning
            ):
                self.master.after(100, self.process_gui_queue)

    def toggle_hardware_status(self):
        if self.hardware_status_visible:
            self.hardware_status_frame.grid_remove()
            self.buttons["hw_status"].config(text="ハードウェア状態 🔽")
            self.is_checking_hardware = False
        else:
            self.hardware_status_frame.grid()
            self.buttons["hw_status"].config(text="ハードウェア状態 🔼")
            self.is_checking_hardware = True
            if self.hardware_thread is None or not self.hardware_thread.is_alive():
                self.hardware_thread = threading.Thread(target=self.update_hardware_status_thread, daemon=True)
                self.hardware_thread.start()
            self.process_gui_queue()
        self.hardware_status_visible = not self.hardware_status_visible

    def update_hardware_status_thread(self):
        if PLATFORM != "RASPI":
            self.gui_queue.put({'pca': "PCモードのため診断不可", 'sensor': "PCモードのため診断不可"})
            return
        current_config = self.get_current_config()
        if current_config.get("USE_SENSOR"):
            try:
                GPIO.setup(current_config["SENSOR_PIN"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            except Exception:
                self.gui_queue.put({'sensor': "ピン初期化エラー"})

        while self.is_checking_hardware:
            pca_msg, sensor_msg = "未診断", "未診断"
            if current_config.get("MOTOR_TYPE") == "STEPPER":
                if stepper_driver is None:
                    pca_msg = "❌ stepper_driverなし"
                else:
                    try:
                        summary = stepper_driver.summarise(current_config)
                        backends = summary.get("available_backends", {})
                        ok_backends = [name for name, ok in backends.items() if ok]
                        pca_msg = "✅ " + ",".join(ok_backends)
                    except Exception as exc:
                        pca_msg = f"❌ 設定エラー: {exc}"
            elif current_config.get("MOTOR_TYPE") == "SERVO":
                try:
                    if Adafruit_PCA9685 is None:
                        raise RuntimeError("Adafruit_PCA9685なし")
                    Adafruit_PCA9685.PCA9685(address=0x40, busnum=1)
                    pca_msg = "✅ PCA9685接続"
                except Exception:
                    pca_msg = "❌ PCA9685接続エラー"
            else:
                pca_msg = "不明"
            if current_config.get("USE_SENSOR"):
                try:
                    sensor_msg = "検知なし (クリア)" if GPIO.input(current_config["SENSOR_PIN"]) else "検知あり (物品あり)"
                except Exception:
                    sensor_msg = "ピン読み取りエラー"
            else:
                sensor_msg = "設定で無効"
            self.gui_queue.put({'pca': pca_msg, 'sensor': sensor_msg})
            time.sleep(1)

    def on_closing(self):
        self.is_checking_hardware = False
        self.stop_client_event.set()
        self.master.destroy()

    def get_current_config(self):
        config = {key: entry.get() for key, entry in self.entries.items()}
        config.update({
            "MOTOR_TYPE": self.MOTOR_TYPE_MAP.get(self.comboboxes["MOTOR_TYPE"].get()),
            "USE_SENSOR": self.USE_SENSOR_MAP.get(self.comboboxes["USE_SENSOR"].get()),
            "MOTOR_REVERSE": self.MOTOR_REVERSE_MAP.get(self.comboboxes["MOTOR_REVERSE"].get()),
            "STEPPER_DRIVE_MODE": self.STEPPER_DRIVE_MODE_MAP.get(self.comboboxes["STEPPER_DRIVE_MODE"].get()),
            "STEPPER_BACKEND": self.STEPPER_BACKEND_MAP.get(self.comboboxes["STEPPER_BACKEND"].get()),
        })
        return normalize_motor_config(config)

    def toggle_advanced_settings(self):
        if self.advanced_settings_visible:
            self.advanced_settings_frame.grid_remove()
            self.buttons["advanced"].config(text="高度な設定 🔽")
        else:
            self.advanced_settings_frame.grid()
            self.buttons["advanced"].config(text="高度な設定 🔼")
            self.update_motor_option_visibility()
        self.advanced_settings_visible = not self.advanced_settings_visible

    def update_motor_option_visibility(self):
        config = self.get_current_config()
        if config.get("MOTOR_TYPE") == "STEPPER":
            self.stepper_frame.grid()
            self.servo_frame.grid_remove()
        elif config.get("MOTOR_TYPE") == "SERVO":
            self.servo_frame.grid()
            self.stepper_frame.grid_remove()
        else:
            self.servo_frame.grid_remove()
            self.stepper_frame.grid_remove()

    def run_stepper_test(self, reverse=False):
        config = self.get_current_config()
        if config.get("MOTOR_TYPE") != "STEPPER":
            messagebox.showinfo("ステッパーテスト", "STEPPER のときだけ実行できます。")
            return
        if PLATFORM != "RASPI" or GPIO is None:
            messagebox.showwarning("ステッパーテスト", "Raspberry Pi上で実行してください。")
            return
        if stepper_driver is None:
            messagebox.showerror("ステッパーテスト", "stepper_driver が利用できません。")
            return
        if not messagebox.askyesno("ステッパーテスト", "現在の設定でモーターを回しますか？"):
            return
        try:
            from unit.hardware_controller import HardwareController
            controller = HardwareController(gpio_module=GPIO, platform=PLATFORM)
            result = controller.test_motor(
                config,
                reverse=reverse,
                label='gui-stepper-test',
            )
            if result.success:
                messagebox.showinfo("ステッパーテスト", f"完了しました: {result.message}")
            else:
                messagebox.showerror("ステッパーテスト", f"失敗しました: {result.message}")
        except Exception as exc:
            messagebox.showerror("ステッパーテスト", str(exc))

    def coils_off_from_gui(self):
        if stepper_driver is None:
            messagebox.showerror("コイルOFF", "stepper_driver が利用できません。")
            return
        stepper_driver.coils_off(GPIO, self.get_current_config())
        messagebox.showinfo("コイルOFF", "コイルOFFを実行しました。")

    def run_scan(self):
        servers = scan_for_servers()
        if not servers:
            messagebox.showinfo("スキャン結果", "親機サーバーが見つかりませんでした。")
            self.server_scan_status.set("親機が見つかりませんでした")
            return
        found_server = servers[0]
        self.entries["SERVER_URL"].delete(0, tk.END)
        self.entries["SERVER_URL"].insert(0, found_server)
        self.config["SERVER_URL"] = found_server
        save_config(self.config)
        self.server_scan_status.set(f"親機: {found_server}")
        messagebox.showinfo("スキャン完了", f"親機サーバーを自動設定しました:\n{found_server}")

    def load_settings(self):
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            value = self.config.get(key, DEFAULT_CONFIG.get(key, ''))
            if key in ("STEPPER_PINS", "STEPPER_PHASE_ORDER"):
                value = format_int_list(value, DEFAULT_CONFIG.get(key, []))
            entry.insert(0, str(value))
        self.comboboxes["MOTOR_TYPE"].set(self.MOTOR_TYPE_MAP_REV.get(self.config.get("MOTOR_TYPE")))
        self.comboboxes["USE_SENSOR"].set(self.USE_SENSOR_MAP_REV.get(self.config.get("USE_SENSOR")))
        self.comboboxes["MOTOR_REVERSE"].set(self.MOTOR_REVERSE_MAP_REV.get(self.config.get("MOTOR_REVERSE")))
        self.comboboxes["STEPPER_DRIVE_MODE"].set(
            self.STEPPER_DRIVE_MODE_MAP_REV.get(self.config.get("STEPPER_DRIVE_MODE"), "半ステップ")
        )
        self.comboboxes["STEPPER_BACKEND"].set(
            self.STEPPER_BACKEND_MAP_REV.get(self.config.get("STEPPER_BACKEND"), "自動選択")
        )
        self.update_motor_option_visibility()
        server_url = (self.config.get("SERVER_URL") or "").strip()
        if server_url:
            self.server_scan_status.set(f"現在: {server_url}")
        else:
            self.server_scan_status.set("")
    
    def save_settings(self, show_success_message=True):
        self.config = self.get_current_config()
        
        if save_config(self.config):
            if show_success_message:
                messagebox.showinfo("成功", "設定を保存しました。")
        else:
            messagebox.showerror("エラー", "設定の保存に失敗しました。")

    def start_auto_server_detection(self):
        if self.auto_detection_started:
            return

        current_url = (self.config.get("SERVER_URL") or "").strip()
        normalized_url = current_url.rstrip('/')
        if normalized_url and normalized_url not in (
            "http://127.0.0.1:5001",
            "http://localhost:5001",
            "127.0.0.1",
            "localhost",
        ):
            self.server_scan_status.set("既存設定を使用します")
            return

        self.auto_detection_started = True
        self.is_auto_scanning = True
        self.server_scan_status.set("親機を検索中...")

        def worker():
            # 親機が見つかるまでループする（ユーザーが停止するまで）
            while self.is_auto_scanning:
                servers = scan_for_servers(timeout=3)
                if servers:
                    self.gui_queue.put({
                        'auto_server': servers[0],
                        'auto_scan_message': f"自動検出: {servers[0]}"
                    })
                    break # 見つかったらループ終了
                else:
                    self.gui_queue.put({
                        'auto_scan_message': "親機を探しています..."
                    })
                    time.sleep(2) # 少し待って再試行

        threading.Thread(target=worker, daemon=True).start()
        self.master.after(100, self.process_gui_queue)

# --------------------------------------------------------------------------
# --- メインクライアント処理 ---
# --------------------------------------------------------------------------
def startup_diagnostics(config):
    """起動時診断 - BIOS風チェック"""
    print("\n" + "=" * 70)
    print("  OITERU子機クライアント - 起動診断")
    print("=" * 70)
    
    diagnostics = []
    
    # 1. Tailscale接続チェック
    print("\n[1/6] Tailscale接続チェック...")
    try:
        result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'online' in result.stdout.lower():
            tailscale_ip = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True).stdout.strip()
            print(f"  ✓ Tailscale接続: OK (IP: {tailscale_ip})")
            diagnostics.append(("Tailscale", "OK", tailscale_ip))
        else:
            print("  ⚠ Tailscale接続: オフライン")
            diagnostics.append(("Tailscale", "オフライン", "N/A"))
    except Exception as e:
        print(f"  ✗ Tailscale接続: 未インストールまたはエラー")
        diagnostics.append(("Tailscale", "エラー", str(e)[:30]))
    
    # 2. NFCリーダーチェック
    print("\n[2/6] NFCリーダーチェック...")
    try:
        import nfc
        clf = nfc.ContactlessFrontend('usb')
        if clf:
            device_path = str(clf.device)
            print(f"  ✓ NFCリーダー: 検出 ({device_path})")
            diagnostics.append(("NFCリーダー", "OK", device_path))
            clf.close()
        else:
            print("  ✗ NFCリーダー: 未接続")
            diagnostics.append(("NFCリーダー", "未接続", "N/A"))
    except Exception as e:
        print(f"  ✗ NFCリーダー: エラー ({str(e)[:40]})")
        diagnostics.append(("NFCリーダー", "エラー", str(e)[:30]))
    
    # 3. GPIO/I2Cチェック
    print("\n[3/6] GPIO/I2Cチェック...")
    if PLATFORM == "RASPI":
        # GPIOチェック
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            print("  ✓ GPIO: 利用可能")
            diagnostics.append(("GPIO", "OK", "BCMモード"))
        except Exception as e:
            print(f"  ⚠ GPIO: エラー ({str(e)[:40]})")
            diagnostics.append(("GPIO", "エラー", str(e)[:30]))
        
        # モーター制御チェック
        if config.get('MOTOR_TYPE') == 'STEPPER':
            if stepper_driver is None:
                print("  ⚠ Stepper: stepper_driver が利用できません")
                diagnostics.append(("Stepper", "エラー", "stepper_driver unavailable"))
            else:
                try:
                    summary = stepper_driver.summarise(config)
                    backends = summary.get("available_backends", {})
                    backend_text = ",".join(
                        f"{name}={'OK' if ok else 'NG'}"
                        for name, ok in backends.items()
                    )
                    print(
                        "  ✓ Stepper GPIO: "
                        f"pins={summary['pins']} mode={summary['drive_mode']} backend={summary['backend']}"
                    )
                    print(f"    backends: {backend_text}")
                    diagnostics.append(("Stepper GPIO", "OK", backend_text))
                except Exception as e:
                    print(f"  ⚠ Stepper設定: エラー ({str(e)[:40]})")
                    diagnostics.append(("Stepper設定", "エラー", str(e)[:30]))
        elif config.get('MOTOR_TYPE') == 'SERVO':
            try:
                if Adafruit_PCA9685 is None:
                    raise RuntimeError("Adafruit_PCA9685 is not installed")
                import Adafruit_PCA9685
                # I2Cバスを明示的に指定 (通常はbus=1)
                pwm = Adafruit_PCA9685.PCA9685(busnum=1)
                pwm.set_pwm_freq(50)
                print("  ✓ I2C/PCA9685: 利用可能")
                diagnostics.append(("I2C/PCA9685", "OK", "0x40"))
            except Exception as e:
                print(f"  ⚠ I2C/PCA9685: エラー ({str(e)[:40]})")
                diagnostics.append(("I2C/PCA9685", "エラー", str(e)[:30]))
        else:
            print("  - I2C: スキップ (Arduino制御モード)")
            diagnostics.append(("I2C", "スキップ", "Arduino制御"))
    else:
        print("  - GPIO/I2C: PCモード (スキップ)")
        diagnostics.append(("GPIO/I2C", "スキップ", "PCモード"))
    
    # 4. 親機サーバー接続チェック
    print("\n[4/6] 親機サーバー接続チェック...")
    server_url = config.get('SERVER_URL')
    try:
        response = requests.get(f"{server_url}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✓ 親機サーバー: 接続OK ({server_url})")
            diagnostics.append(("親機サーバー", "OK", server_url))
        else:
            print(f"  ✗ 親機サーバー: エラー (status={response.status_code})")
            diagnostics.append(("親機サーバー", "エラー", f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"  ✗ 親機サーバー: 接続失敗 ({str(e)[:40]})")
        diagnostics.append(("親機サーバー", "接続失敗", server_url))
    
    # 5. ネットワークチェック
    print("\n[5/6] ネットワークチェック...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"  ✓ ローカルネットワーク: OK (IP: {local_ip})")
        diagnostics.append(("ローカルIP", "OK", local_ip))
    except Exception:
        print("  ✗ ローカルネットワーク: 接続不可")
        diagnostics.append(("ローカルIP", "エラー", "N/A"))
    
    # 6. 設定ファイルチェック
    print("\n[6/6] 設定ファイルチェック...")
    required_keys = ['SERVER_URL', 'UNIT_NAME', 'MOTOR_TYPE']
    missing = [k for k in required_keys if not config.get(k)]
    if not missing:
        print("  ✓ 設定ファイル: 完全")
        diagnostics.append(("設定ファイル", "OK", "すべて設定済み"))
    else:
        print(f"  ⚠ 設定ファイル: 不完全 (不足: {', '.join(missing)})")
        diagnostics.append(("設定ファイル", "不完全", ', '.join(missing)))
    
    print("\n" + "=" * 70)
    print("  診断完了")
    print("=" * 70)
    
    return diagnostics

def send_diagnostics_to_server(server_url, unit_name, diagnostics):
    """診断結果を親機に送信"""
    try:
        payload = {
            "unit_name": unit_name,
            "diagnostics": [
                {"component": d[0], "status": d[1], "detail": d[2]}
                for d in diagnostics
            ],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        requests.post(f"{server_url}/api/diagnostics", json=payload, timeout=5)
    except Exception as e:
        print(f"  ⚠ 診断結果の送信に失敗: {e}")

def run_client(config, stop_event, gui_queue):
    SERVER_URL = config.get('SERVER_URL')
    UNIT_NAME = config.get('UNIT_NAME')
    UNIT_PASSWORD = config.get('UNIT_PASSWORD')
    MOTOR_TYPE = config.get('MOTOR_TYPE')
    USE_SENSOR = config.get('USE_SENSOR')
    GREEN_LED_PIN = config.get('GREEN_LED_PIN')
    RED_LED_PIN = config.get('RED_LED_PIN')
    SENSOR_PIN = config.get('SENSOR_PIN')
    MOTOR_SPEED = config.get('MOTOR_SPEED', 100)
    MOTOR_DURATION = config.get('MOTOR_DURATION', 2.0)
    MOTOR_REVERSE = config.get('MOTOR_REVERSE', False)
    SENSOR_CHECK_PRE = config.get('SENSOR_CHECK_PRE', True)
    SENSOR_CHECK_POST = config.get('SENSOR_CHECK_POST', True)
    JAM_CLEAR_ATTEMPTS = config.get('JAM_CLEAR_ATTEMPTS', 3)
    SENSOR_STABILIZE_TIME = config.get('SENSOR_STABILIZE_TIME', 0.3)
    HEARTBEAT_INTERVAL = config.get('HEARTBEAT_INTERVAL', 30)

    # 起動時診断を実行
    diagnostics = startup_diagnostics(config)
    send_diagnostics_to_server(SERVER_URL, UNIT_NAME, diagnostics)

    PLATFORM_RUNTIME = PLATFORM
    GPIO_runtime = None

    if PLATFORM_RUNTIME == 'RASPI':
        try:
            import RPi.GPIO as GPIO_runtime
            GPIO_runtime.setmode(GPIO_runtime.BCM)
            GPIO_runtime.setup(GREEN_LED_PIN, GPIO_runtime.OUT)
            GPIO_runtime.setup(RED_LED_PIN, GPIO_runtime.OUT)

            if USE_SENSOR:
                # LBR-127HLDはオープンコレクタ出力のため、プルアップ抵抗を有効化
                GPIO_runtime.setup(SENSOR_PIN, GPIO_runtime.IN, pull_up_down=GPIO_runtime.PUD_UP)
                print(f"INFO: センサーピン GPIO {SENSOR_PIN} をプルアップ抵抗付きで初期化しました")

        except Exception as e:
            print(f"警告: GPIO初期化失敗: {e}。")
            PLATFORM_RUNTIME = 'PC'

    def get_my_ip():
        """自身のIPアドレスを取得（Tailscale優先）"""
        try:
            # Tailscale IPの取得を試みる
            result = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception as e:
            print(f"Tailscale IP取得エラー: {e}")
        
        try:
            # Tailscaleがない場合はローカルIPを取得
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            print(f"ローカルIP取得エラー: {e}")
        
        return "unknown"

    def refresh_runtime_settings():
        nonlocal MOTOR_TYPE, USE_SENSOR, MOTOR_SPEED, MOTOR_DURATION, MOTOR_REVERSE
        nonlocal SENSOR_PIN, SENSOR_CHECK_PRE, SENSOR_CHECK_POST, JAM_CLEAR_ATTEMPTS
        nonlocal SENSOR_STABILIZE_TIME, HEARTBEAT_INTERVAL

        MOTOR_TYPE = config.get('MOTOR_TYPE', MOTOR_TYPE)
        USE_SENSOR = config.get('USE_SENSOR', USE_SENSOR)
        MOTOR_SPEED = config.get('MOTOR_SPEED', MOTOR_SPEED)
        MOTOR_DURATION = config.get('MOTOR_DURATION', MOTOR_DURATION)
        MOTOR_REVERSE = config.get('MOTOR_REVERSE', MOTOR_REVERSE)
        SENSOR_PIN = config.get('SENSOR_PIN', SENSOR_PIN)
        SENSOR_CHECK_PRE = config.get('SENSOR_CHECK_PRE', SENSOR_CHECK_PRE)
        SENSOR_CHECK_POST = config.get('SENSOR_CHECK_POST', SENSOR_CHECK_POST)
        JAM_CLEAR_ATTEMPTS = config.get('JAM_CLEAR_ATTEMPTS', JAM_CLEAR_ATTEMPTS)
        SENSOR_STABILIZE_TIME = config.get('SENSOR_STABILIZE_TIME', SENSOR_STABILIZE_TIME)
        HEARTBEAT_INTERVAL = max(5, int(config.get('HEARTBEAT_INTERVAL', HEARTBEAT_INTERVAL)))

    def send_heartbeat():
        nonlocal HEARTBEAT_INTERVAL
        
        while not stop_event.is_set():
            try:
                refresh_runtime_settings()
                # IPアドレスを毎回取得（ネットワーク変更に対応）
                my_ip = get_my_ip()
                
                # 現在の設定を構築
                current_config = {
                    "MOTOR_TYPE": MOTOR_TYPE,
                    "USE_SENSOR": USE_SENSOR,
                    "MOTOR_SPEED": MOTOR_SPEED,
                    "MOTOR_DURATION": MOTOR_DURATION,
                    "MOTOR_REVERSE": MOTOR_REVERSE,
                    "SENSOR_GPIO_PIN": SENSOR_PIN,
                    "SENSOR_CHECK_PRE": SENSOR_CHECK_PRE,
                    "SENSOR_CHECK_POST": SENSOR_CHECK_POST,
                    "JAM_CLEAR_ATTEMPTS": JAM_CLEAR_ATTEMPTS,
                    "HEARTBEAT_INTERVAL": HEARTBEAT_INTERVAL,
                    "PCA9685_CHANNEL": config.get("PCA9685_CHANNEL", 15),
                    "STEPPER_PINS": config.get("STEPPER_PINS", [21, 17, 27, 22]),
                    "STEPPER_PHASE_ORDER": config.get("STEPPER_PHASE_ORDER", [0, 1, 2, 3]),
                    "STEPPER_STEP_DELAY": config.get("STEPPER_STEP_DELAY", 0.01),
                    "STEPPER_DRIVE_MODE": config.get("STEPPER_DRIVE_MODE", "half"),
                    "STEPPER_STEPS": config.get("STEPPER_STEPS", 0),
                    "STEPPER_STEPS_PER_REV": config.get("STEPPER_STEPS_PER_REV", 2048),
                    "STEPPER_TEST_STEPS": config.get("STEPPER_TEST_STEPS", 2048),
                    "STEPPER_BACKEND": config.get("STEPPER_BACKEND", "auto")
                }
                
                # サーバーにハートビートを送信（設定情報付き）
                payload = {
                    "name": UNIT_NAME, 
                    "password": UNIT_PASSWORD,
                    "ip_address": my_ip,
                    "config": current_config
                }
                response = requests.post(f"{SERVER_URL}/api/unit/heartbeat", json=payload, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('unit_api_token'):
                        config['_unit_api_token'] = data['unit_api_token']
                    if 'stock' in data:
                        # サーバーからの在庫数で同期（GUI更新）
                        gui_queue.put({'stock': data['stock']})
                    
                    # 親機からの設定変更をチェック（即時送信 or heartbeat経由）
                    if 'config_update' in data and data['config_update']:
                        print("[設定変更] 親機から設定変更を受信しました（即時反映）")
                        new_config = data['config_update']
                        apply_remote_config(new_config, config)
                        refresh_runtime_settings()
                    elif 'pending_config' in data and data['pending_config']:
                        print("[設定変更] 親機から設定変更を受信しました")
                        new_config = data['pending_config']
                        apply_remote_config(new_config, config)
                        refresh_runtime_settings()
                        
                else:
                    gui_queue.put({'stock': '--- (サーバーエラー)'})
            except requests.exceptions.RequestException:
                gui_queue.put({'stock': '--- (通信エラー)'})
            
            for _ in range(max(5, int(HEARTBEAT_INTERVAL))):
                if stop_event.is_set(): break
                time.sleep(1)

    def send_log_to_server(message):
        try:
            payload = {"unit_name": UNIT_NAME, "message": message}
            payload["unit_password"] = UNIT_PASSWORD
            if config.get('_unit_api_token'):
                payload["unit_token"] = config['_unit_api_token']
            requests.post(f"{SERVER_URL}/api/log", json=payload, timeout=3)
        except requests.exceptions.RequestException: pass

    def indicate(status):
        if PLATFORM_RUNTIME != 'RASPI': return
        pin = GREEN_LED_PIN if status == 'success' else RED_LED_PIN
        try:
            GPIO_runtime.output(pin, GPIO_runtime.HIGH)
            time.sleep(2)
            GPIO_runtime.output(pin, GPIO_runtime.LOW)
        except Exception: pass

    def check_sensor(description="", stabilize=True):
        """フォトリフレクタの状態をチェック
        Returns: True=物体検知なし（クリア）, False=物体検知（詰まり）
        
        Args:
            description: ログ出力用の説明文
            stabilize: 読み取り前に安定化待機を行うか(デフォルト: True)
        """
        if not USE_SENSOR or PLATFORM_RUNTIME != 'RASPI':
            return True
        
        # センサー安定化待機(ノイズ除去)
        if stabilize:
            time.sleep(0.05)  # 50msec待機
        
        # 複数回読み取って安定した値を取得(デバウンス)
        readings = []
        for _ in range(3):
            readings.append(GPIO_runtime.input(SENSOR_PIN))
            time.sleep(0.01)  # 10msec間隔
        
        # 多数決で値を決定(ノイズ対策)
        sensor_val = max(set(readings), key=readings.count)
        
        # LBR-127HLD: LOW=物体検知, HIGH=クリア
        is_clear = (sensor_val == 1)
        status = "クリア" if is_clear else "物体検知"
        print(f"[センサーチェック{description}] 値={sensor_val} ({status}) [読み取り: {readings}]")
        return is_clear

    def dispense_item():
        from unit.hardware_controller import HardwareController, DispenseRequest

        controller = HardwareController(
            gpio_module=GPIO_runtime,
            platform=PLATFORM_RUNTIME,
        )
        request = DispenseRequest(
            config=config,
            stop_event=stop_event,
            on_log=send_log_to_server,
        )
        result = controller.dispense(request)

        if result.success:
            indicate("success")
        else:
            indicate("failure")

        send_log_to_server(
            f"排出{'成功' if result.success else '失敗'}"
            f" ({result.motor_type}, attempts={result.attempts}"
            + (f", error={result.error}" if result.error else "") + ")"
        )
        return result.success

    def handle_card_touch(tag):
        """NFCカードタッチ時の処理（改良版）"""
        # Type3Tag (FeliCa) のチェック - Type2Tag等もサポート
        card_id = None
        try:
            if hasattr(tag, 'idm'):
                # FeliCa (Type3Tag)
                card_id = tag.idm.hex()
            elif hasattr(tag, 'identifier'):
                # NFC-A/B (Type2Tag, Type4Tag等)
                card_id = tag.identifier.hex()
            else:
                send_log_to_server(f"未対応のカードタイプ: {type(tag)}")
                return False
        except Exception as e:
            send_log_to_server(f"カードID取得エラー: {e}")
            return False
        
        if not card_id:
            return False
            
        gui_queue.put({'nfc': f'読取中: {card_id}'})
        send_log_to_server(f"カード検出: {card_id}")
        
        try:
            payload = {"card_id": card_id, "unit_name": UNIT_NAME}
            payload["unit_password"] = UNIT_PASSWORD
            if config.get('_unit_api_token'):
                payload["unit_token"] = config['_unit_api_token']
            response = requests.post(f"{SERVER_URL}/api/record_usage", json=payload, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                event_id = response_data.get('event_id')
                if not event_id:
                    send_log_to_server(f"利用認可レスポンス不正 (event_idなし) ({card_id})")
                    indicate("failure")
                    return True

                send_log_to_server(f"利用認可 ({card_id}) event={event_id[:8]}")
                dispense_ok = dispense_item()
                result_payload = {
                    "event_id": event_id,
                    "unit_name": UNIT_NAME,
                    "success": dispense_ok,
                    "error_code": None if dispense_ok else "DISPENSE_FAILED_CLIENT",
                    "unit_password": UNIT_PASSWORD,
                }
                if config.get('_unit_api_token'):
                    result_payload["unit_token"] = config['_unit_api_token']

                result_response = None
                last_result_error = None
                for _ in range(3):
                    try:
                        result_response = requests.post(
                            f"{SERVER_URL}/api/dispense_result",
                            json=result_payload,
                            timeout=10
                        )
                        break
                    except requests.exceptions.RequestException as req_error:
                        last_result_error = req_error
                        time.sleep(1)

                if result_response is None:
                    send_log_to_server(
                        f"排出結果確定APIへの送信失敗 ({card_id}) event={event_id[:8]} err={last_result_error}"
                    )
                    indicate("failure")
                    return True

                if result_response.status_code == 200:
                    result_data = result_response.json()
                    if result_data.get('success'):
                        send_log_to_server(f"排出結果を確定 ({card_id}) event={event_id[:8]}")
                        indicate("success")
                    else:
                        fail_code = result_data.get('error_code', 'UNKNOWN')
                        send_log_to_server(
                            f"排出結果は失敗として確定 ({card_id}) event={event_id[:8]} code={fail_code}"
                        )
                        indicate("failure")
                else:
                    try:
                        result_error = result_response.json().get('error', '不明なエラー')
                    except Exception:
                        result_error = f"HTTP {result_response.status_code}"
                    send_log_to_server(
                        f"排出結果確定APIエラー ({result_error}) ({card_id}) event={event_id[:8]}"
                    )
                    indicate("failure")
            else:
                # JSONパースエラーを安全に処理
                try:
                    error_msg = response.json().get('error', '不明なエラー')
                except:
                    error_msg = f"HTTP {response.status_code}"
                send_log_to_server(f"利用不可 ({error_msg}) ({card_id})")
                indicate("failure")
                
        except requests.exceptions.Timeout:
            send_log_to_server(f"サーバー接続タイムアウト ({card_id})")
            indicate("failure")
        except requests.exceptions.ConnectionError:
            send_log_to_server(f"サーバー接続エラー ({card_id})")
            indicate("failure")
        except Exception as e:
            send_log_to_server(f"予期しないエラー: {e} ({card_id})")
            indicate("failure")
        finally:
            time.sleep(2)
            if not stop_event.is_set():
                gui_queue.put({'nfc': '待機中...'})
        
        return True

    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()

    # Flask APIサーバーを別スレッドで起動
    flask_thread = threading.Thread(target=start_flask_api_server, args=(config, 5001), daemon=True)
    flask_thread.start()

    clf = None
    retry_count = 0
    max_retries = 5
    retry_delay = 3  # 秒
    
    def init_nfc_reader():
        """NFCリーダーを初期化（リトライ機能付き）"""
        attempts = 0
        last_error = None
        
        while attempts < max_retries:
            try:
                attempts += 1
                gui_queue.put({'nfc': f'リーダー接続中... ({attempts}/{max_retries})'})
                send_log_to_server(f"NFCリーダー初期化試行 {attempts}/{max_retries}")
                
                # 複数のUSBパスを試行
                usb_paths = [
                    'usb',           # 自動検出
                    'usb:054c:06c3',  # Sony PaSoRi RC-S380
                    'usb:054c:06c1',  # Sony PaSoRi RC-S370
                ]
                
                for path in usb_paths:
                    try:
                        clf = nfc.ContactlessFrontend(path)
                        if clf:
                            gui_queue.put({'nfc': f'✅ リーダー接続完了 ({path})'})
                            send_log_to_server(f"NFCリーダー初期化成功: {path}")
                            return clf
                    except Exception as path_error:
                        last_error = path_error
                        continue
                
                # すべてのパスで失敗した場合
                raise last_error if last_error else Exception("すべてのUSBパスで接続失敗")
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                send_log_to_server(f"NFCリーダー初期化失敗 ({attempts}): {error_msg}")
                
                if attempts < max_retries:
                    gui_queue.put({'nfc': f'⚠️ 再試行まで{retry_delay}秒... ({error_msg[:30]})'})
                    time.sleep(retry_delay)
                else:
                    gui_queue.put({'nfc': f'❌ リーダー接続失敗: {error_msg[:50]}'})
                    raise
        
        return None
    
    try:
        if PLATFORM_RUNTIME == "RASPI":
            # NFCリーダーの初期化（リトライ付き）
            clf = init_nfc_reader()
            
            if not clf:
                gui_queue.put({'nfc': '❌ NFCリーダーが利用できません'})
                stop_event.wait()
                return
            
            # メインループ: カード読み取り
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            while not stop_event.is_set():
                try:
                    # カード読み取り試行
                    connected = clf.connect(
                        rdwr={'on-connect': handle_card_touch},
                        terminate=lambda: stop_event.is_set()
                    )
                    
                    if connected:
                        consecutive_errors = 0  # 成功したらエラーカウントリセット
                        time.sleep(0.1)
                    else:
                        time.sleep(0.5)
                        
                except Exception as e:
                    consecutive_errors += 1
                    error_msg = str(e)
                    
                    # デバイス切断エラーの検知
                    if "No such device" in error_msg or "Errno 19" in error_msg:
                        send_log_to_server(f"NFCリーダー切断を検知: {error_msg}")
                        gui_queue.put({'nfc': '⚠️ リーダー切断検知、再接続中...'})
                        
                        # 古いclfをクローズ
                        try:
                            if clf:
                                clf.close()
                        except:
                            pass
                        
                        # 短い待機後に再初期化
                        time.sleep(2)
                        try:
                            clf = init_nfc_reader()
                            consecutive_errors = 0
                            continue
                        except Exception as reinit_error:
                            gui_queue.put({'nfc': f'❌ 再接続失敗: {str(reinit_error)[:30]}'})
                            break
                    
                    # その他のエラー
                    if consecutive_errors >= max_consecutive_errors:
                        send_log_to_server(f"連続エラー上限到達: {error_msg}")
                        gui_queue.put({'nfc': f'❌ エラー多発のため停止: {error_msg[:30]}'})
                        break
                    
                    gui_queue.put({'nfc': f'⚠️ エラー({consecutive_errors}): {error_msg[:30]}'})
                    time.sleep(1)
        else:
            gui_queue.put({'nfc': 'PCモードのためNFC利用不可'})
            stop_event.wait()
            
    except Exception as e:
        error_msg = str(e)
        gui_queue.put({'nfc': f'❌ 致命的エラー: {error_msg[:50]}'})
        send_log_to_server(f"NFCスレッド致命的エラー: {error_msg}")
        
    finally:
        # クリーンアップ
        if clf:
            try:
                clf.close()
                send_log_to_server("NFCリーダーをクローズしました")
            except:
                pass
        
        if PLATFORM_RUNTIME == 'RASPI' and GPIO_runtime:
            try:
                GPIO_runtime.cleanup()
            except:
                pass
        
        print("--- スクリプトを終了します ---")

# --------------------------------------------------------------------------
# --- CUIモード実装 ---
# --------------------------------------------------------------------------
def show_cui_menu(config):
    """CUIモードの設定メニューを表示"""

    def parse_int_list(value):
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(',') if x.strip()]
        return [int(x) for x in value]

    def format_list(key, default):
        value = config.get(key, default)
        if isinstance(value, str):
            return value
        return ','.join(str(x) for x in value)

    def run_stepper_test(reverse=False):
        if PLATFORM != 'RASPI' or GPIO is None:
            print("\n✗ PCモードのためGPIOテストは実行できません。Raspberry Pi上で実行してください。")
            return
        if stepper_driver is None:
            print("\n✗ stepper_driver が利用できません。requirements-client.txt を確認してください。")
            return

        try:
            steps = int(config.get('STEPPER_TEST_STEPS', 2048))
            print("\n" + "=" * 60)
            print(f"  STEPPER テスト: {'逆方向' if reverse else '正方向'}")
            print("=" * 60)
            summary = stepper_driver.summarise(config)
            print(f"  pins        : {summary['pins']}")
            print(f"  phase_order : {summary['phase_order']}")
            print(f"  drive_mode  : {summary['drive_mode']}")
            print(f"  backend     : {summary['backend']}")
            print(f"  steps       : {steps}")
            if input("この設定で回しますか？ [y/N]: ").strip().lower() != 'y':
                print("キャンセルしました")
                return
            result = stepper_driver.run_stepper(
                GPIO,
                config,
                steps=steps,
                reverse=reverse,
                motor_speed=int(config.get('MOTOR_SPEED', 100)),
                label='cui-stepper-test',
            )
            print("✓ テスト完了" if result.get('ok') else f"✗ テスト失敗: {result}")
        except Exception as e:
            print(f"✗ STEPPER テストエラー: {e}")

    while True:
        print("\n" + "=" * 60)
        print("  設定メニュー")
        print("=" * 60)
        print(f"  1. サーバーURL     : {config['SERVER_URL']}")
        print(f"  2. 子機名          : {config['UNIT_NAME']}")
        print(f"  3. パスワード      : {'*' * len(config.get('UNIT_PASSWORD', ''))}")
        print(f"  4. モーター種類    : {config['MOTOR_TYPE']}")
        print(f"  5. センサー使用    : {config['USE_SENSOR']}")
        print(f"  6. 緑LED PIN       : {config['GREEN_LED_PIN']}")
        print(f"  7. 赤LED PIN       : {config['RED_LED_PIN']}")
        print(f"  8. センサーPIN     : {config['SENSOR_PIN']}")
        print(f"  9. モーター速度    : {config['MOTOR_SPEED']}")
        print(f" 10. モーター時間    : {config['MOTOR_DURATION']}秒")
        print(f" 11. モーター反転    : {config['MOTOR_REVERSE']}")
        if config.get('MOTOR_TYPE') == 'STEPPER':
            print(f" 12. STEPPER_PINS    : {format_list('STEPPER_PINS', [21, 17, 27, 22])}")
            print(f" 13. PHASE_ORDER     : {format_list('STEPPER_PHASE_ORDER', [0, 1, 2, 3])}")
            print(f" 14. STEP_DELAY      : {config.get('STEPPER_STEP_DELAY', 0.01)}秒")
            print(f" 15. DRIVE_MODE      : {config.get('STEPPER_DRIVE_MODE', 'half')}")
            print(f" 16. 排出ステップ数  : {config.get('STEPPER_STEPS', 0)} (0=秒数から計算)")
            print(f" 17. テストステップ  : {config.get('STEPPER_TEST_STEPS', 2048)}")
            print(f" 18. STEPPER_BACKEND : {config.get('STEPPER_BACKEND', 'auto')}")
        print("=" * 60)
        print("  a. 親機自動探知")
        print("  d. ハードウェア診断")
        print("  t. ステッパー正方向テスト")
        print("  r. ステッパー逆方向テスト")
        print("  off. ステッパーコイルOFF")
        print("  s. 設定を保存して起動")
        print("  q. 保存せずに起動")
        print("=" * 60)
        
        choice = input("\n選択 [1-18/a/d/t/r/off/s/q]: ").strip().lower()
        
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
            print("\nモーター種類:")
            print("  1. SERVO (サーボモーター)")
            print("  2. STEPPER (ステッピングモーター)")
            motor_choice = input("選択 [1-2]: ").strip()
            if motor_choice == '1':
                config['MOTOR_TYPE'] = 'SERVO'
            elif motor_choice == '2':
                config['MOTOR_TYPE'] = 'STEPPER'
        elif choice == '5':
            print("\nセンサー使用:")
            print("  1. 使用する")
            print("  2. 使用しない")
            sensor_choice = input("選択 [1-2]: ").strip()
            if sensor_choice == '1':
                config['USE_SENSOR'] = True
            elif sensor_choice == '2':
                config['USE_SENSOR'] = False
        elif choice == '6':
            new_val = input(f"緑LED PIN (BCM) [{config['GREEN_LED_PIN']}]: ").strip()
            if new_val.isdigit():
                config['GREEN_LED_PIN'] = int(new_val)
        elif choice == '7':
            new_val = input(f"赤LED PIN (BCM) [{config['RED_LED_PIN']}]: ").strip()
            if new_val.isdigit():
                config['RED_LED_PIN'] = int(new_val)
        elif choice == '8':
            new_val = input(f"センサーPIN (BCM) [{config['SENSOR_PIN']}]: ").strip()
            if new_val.isdigit():
                config['SENSOR_PIN'] = int(new_val)
        elif choice == '9':
            new_val = input(f"モーター速度 (0-100) [{config['MOTOR_SPEED']}]: ").strip()
            if new_val.isdigit():
                config['MOTOR_SPEED'] = int(new_val)
        elif choice == '10':
            new_val = input(f"モーター時間 (秒) [{config['MOTOR_DURATION']}]: ").strip()
            try:
                config['MOTOR_DURATION'] = float(new_val)
            except ValueError:
                pass
        elif choice == '11':
            print("\nモーター反転:")
            print("  1. 正転")
            print("  2. 逆転")
            reverse_choice = input("選択 [1-2]: ").strip()
            if reverse_choice == '1':
                config['MOTOR_REVERSE'] = False
            elif reverse_choice == '2':
                config['MOTOR_REVERSE'] = True
        elif choice == '12':
            new_val = input(
                f"STEPPER_PINS IN1,IN2,IN3,IN4 (BCM) [{format_list('STEPPER_PINS', [21, 17, 27, 22])}]: "
            ).strip()
            if new_val:
                pins = parse_int_list(new_val)
                if len(pins) == 4:
                    config['STEPPER_PINS'] = pins
                else:
                    print("✗ 4本指定してください")
        elif choice == '13':
            new_val = input(
                f"STEPPER_PHASE_ORDER [{format_list('STEPPER_PHASE_ORDER', [0, 1, 2, 3])}]: "
            ).strip()
            if new_val:
                order = parse_int_list(new_val)
                if sorted(order) == [0, 1, 2, 3]:
                    config['STEPPER_PHASE_ORDER'] = order
                else:
                    print("✗ 0,1,2,3 の並べ替えで指定してください")
        elif choice == '14':
            new_val = input(f"STEP_DELAY秒 [{config.get('STEPPER_STEP_DELAY', 0.01)}]: ").strip()
            if new_val:
                config['STEPPER_STEP_DELAY'] = max(0.01, float(new_val))
        elif choice == '15':
            new_val = input("DRIVE_MODE [full/half/wave]: ").strip().lower()
            if new_val in ('full', 'half', 'wave'):
                config['STEPPER_DRIVE_MODE'] = new_val
            else:
                print("✗ full / half / wave のいずれかを指定してください")
        elif choice == '16':
            new_val = input(f"排出ステップ数 [{config.get('STEPPER_STEPS', 0)}] (0=秒数から計算): ").strip()
            if new_val:
                config['STEPPER_STEPS'] = max(0, int(new_val))
        elif choice == '17':
            new_val = input(f"テストステップ数 [{config.get('STEPPER_TEST_STEPS', 2048)}]: ").strip()
            if new_val:
                config['STEPPER_TEST_STEPS'] = max(1, int(new_val))
        elif choice == '18':
            new_val = input(f"STEPPER_BACKEND [{config.get('STEPPER_BACKEND', 'auto')}] (auto/pigpio/library/gpio): ").strip().lower()
            if new_val in ('auto', 'pigpio', 'library', 'gpio'):
                config['STEPPER_BACKEND'] = new_val
            else:
                print("✗ auto / pigpio / library / gpio のいずれかを指定してください")
        elif choice == 'a':
            print("\n" + "=" * 60)
            print("  親機自動探知を開始します...")
            print("=" * 60)
            servers = scan_for_servers(timeout=5)
            if servers:
                print(f"\n{len(servers)}台の親機を発見しました:")
                for idx, server_url in enumerate(servers, 1):
                    print(f"  {idx}. {server_url}")
                
                print("\n使用する親機を選択してください:")
                server_choice = input(f"選択 [1-{len(servers)}] または Enter でキャンセル: ").strip()
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
                print("  ヒント:")
                print("  - 親機サーバー(app.py)が起動していることを確認してください")
                print("  - 同一ネットワークまたはTailscaleで接続されていることを確認してください")
            input("\nEnterキーで戻る...")
        elif choice == 'd':
            print("\n" + "=" * 60)
            print("  ハードウェア診断中...")
            print("=" * 60)
            run_cui_diagnostics(config)
        elif choice == 't':
            run_stepper_test(reverse=False)
            input("\nEnterキーで戻る...")
        elif choice == 'r':
            run_stepper_test(reverse=True)
            input("\nEnterキーで戻る...")
        elif choice == 'off':
            if stepper_driver is not None:
                stepper_driver.coils_off(GPIO, config)
                print("✓ コイルOFF")
            else:
                print("✗ stepper_driver が利用できません")
            input("\nEnterキーで戻る...")
        elif choice == 's':
            if save_config(config):
                print("\n✓ 設定を保存しました")
            else:
                print("\n✗ 設定の保存に失敗しました")
            return config
        elif choice == 'q':
            return config
        else:
            print("\n✗ 無効な選択です")

def run_cui_diagnostics(config):
    """CUIモードでハードウェア診断を実行"""
    if PLATFORM == "PC":
        print("\n[PCA9685] PCモードのため診断不可")
        print("[センサー] PCモードのため診断不可")
        return
    
    # センサー診断
    try:
        if config['USE_SENSOR']:
            GPIO.setup(config['SENSOR_PIN'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            sensor_state = GPIO.input(config['SENSOR_PIN'])
            sensor_msg = "正常" if sensor_state in [0, 1] else "異常"
            print(f"\n[センサー] PIN {config['SENSOR_PIN']}: {sensor_msg} (値: {sensor_state})")
        else:
            print("\n[センサー] 使用しない設定")
    except Exception as e:
        print(f"\n[センサー] エラー: {e}")
    
    # モーター制御診断
    if config['MOTOR_TYPE'] == 'STEPPER':
        if stepper_driver is None:
            print("[STEPPER] エラー: stepper_driver が利用できません")
        else:
            try:
                summary = stepper_driver.summarise(config)
                print(f"[STEPPER] pins: {summary['pins']}")
                print(f"[STEPPER] phase_order: {summary['phase_order']} -> drive_pins {summary['drive_pins']}")
                print(f"[STEPPER] drive_mode: {summary['drive_mode']}")
                print(f"[STEPPER] step_delay: {summary['step_delay']}")
                print(f"[STEPPER] backend: {summary['backend']}")
                for name, ok in summary['available_backends'].items():
                    print(f"[STEPPER] backend {name}: {'OK' if ok else 'NG'}")
            except Exception as e:
                print(f"[STEPPER] 設定エラー: {e}")
    elif config['MOTOR_TYPE'] == 'SERVO':
        try:
            if Adafruit_PCA9685 is None:
                raise RuntimeError("Adafruit_PCA9685 is not installed")
            test_pwm = Adafruit_PCA9685.PCA9685()
            test_pwm.set_pwm_freq(50)
            print("[PCA9685] 正常に初期化されました")
        except Exception as e:
            print(f"[PCA9685] エラー: {e}")
    else:
        print("[PCA9685] Arduino制御のため診断スキップ")
    
    input("\nEnterキーで戻る...")

def run_cui_mode():
    """CUIモードで子機を起動（GUIなし）"""
    global SERVER_URL, UNIT_NAME, UNIT_PASSWORD
    global MOTOR_TYPE, USE_SENSOR
    global GREEN_LED_PIN, RED_LED_PIN, SENSOR_PIN
    global MOTOR_SPEED, MOTOR_DURATION, MOTOR_REVERSE
    
    # 停止イベントを作成
    stop_event = threading.Event()
    
    print("=" * 60)
    print("  OITERU子機クライアント - CUIモード")
    print("=" * 60)
    print("")
    print("🔄 親機・従親機からの設定変更が自動的に反映されます")
    print("   - Heartbeat経由: 30秒ごとに設定を同期")
    print("   - 即時反映: Flask API (ポート5001) で受信")
    print("")
    
    # 設定ファイルを読み込み
    config = load_config()
    
    # 自動探知モードのチェック
    if '--find-server' in sys.argv:
        print("\n親機自動探知モードで起動します...")
        servers = scan_for_servers(timeout=5)
        if servers:
            config['SERVER_URL'] = servers[0]
            print(f"✓ 親機を自動検出しました: {servers[0]}")
            if save_config(config):
                print("✓ 設定を保存しました")
        else:
            print("✗ 親機が見つかりませんでした。現在の設定で続行します。")
    
    # ヘッドレス起動や --no-gui 起動では対話メニューを出さず、そのまま起動する
    interactive_menu_requested = (
        '--auto' not in sys.argv
        and '--find-server' not in sys.argv
        and '--no-gui' not in sys.argv
        and sys.stdin.isatty()
    )

    # 設定メニューの表示
    if interactive_menu_requested:
        print("\nオプションを選択してください:")
        print("  1. そのまま起動")
        print("  2. 設定メニューを開く")
        print("  3. 親機を自動探知して起動")
        try:
            response = input("選択 [1-3]: ").strip()
            if response == '2':
                config = show_cui_menu(config)
            elif response == '3':
                print("\n親機自動探知を開始します...")
                servers = scan_for_servers(timeout=5)
                if servers:
                    print(f"\n{len(servers)}台の親機を発見しました:")
                    for idx, server_url in enumerate(servers, 1):
                        print(f"  {idx}. {server_url}")
                    
                    if len(servers) == 1:
                        config['SERVER_URL'] = servers[0]
                        print(f"\n✓ サーバーURLを {servers[0]} に設定しました")
                        if save_config(config):
                            print("✓ 設定を保存しました")
                    else:
                        server_choice = input(f"\n使用する親機を選択 [1-{len(servers)}]: ").strip()
                        try:
                            server_idx = int(server_choice) - 1
                            if 0 <= server_idx < len(servers):
                                config['SERVER_URL'] = servers[server_idx]
                                print(f"\n✓ サーバーURLを {servers[server_idx]} に設定しました")
                                if save_config(config):
                                    print("✓ 設定を保存しました")
                        except ValueError:
                            print("\n✗ 無効な選択です。現在の設定で続行します。")
                else:
                    print("\n✗ 親機が見つかりませんでした。現在の設定で続行します。")
        except (EOFError, KeyboardInterrupt):
            print("\n")
    else:
        print("\n自動起動モードで続行します（対話メニューは省略）")
    
    # グローバル変数に設定を適用
    SERVER_URL = config['SERVER_URL']
    UNIT_NAME = config['UNIT_NAME']
    UNIT_PASSWORD = config['UNIT_PASSWORD']
    MOTOR_TYPE = config['MOTOR_TYPE']
    USE_SENSOR = config['USE_SENSOR']
    GREEN_LED_PIN = config['GREEN_LED_PIN']
    RED_LED_PIN = config['RED_LED_PIN']
    SENSOR_PIN = config['SENSOR_PIN']
    MOTOR_SPEED = config['MOTOR_SPEED']
    MOTOR_DURATION = config['MOTOR_DURATION']
    MOTOR_REVERSE = config['MOTOR_REVERSE']
    
    print("\n" + "=" * 60)
    print("  子機を起動しています...")
    print("=" * 60)
    print(f"  サーバー: {SERVER_URL}")
    print(f"  子機名: {UNIT_NAME}")
    print("=" * 60)
    print("\n[Ctrl+C] で終了します\n")
    
    # CUIモード用のキューを作成
    cui_queue = queue.Queue()
    
    # CUI用の簡易キュー処理
    def cui_queue_handler(q):
        """キューからメッセージを受け取ってコンソールに表示"""
        while not stop_event.is_set():
            try:
                msg = q.get(timeout=0.5)
                timestamp = time.strftime("%H:%M:%S")
                if 'nfc' in msg:
                    print(f"[{timestamp}] NFC: {msg['nfc']}")
                elif 'stock' in msg:
                    print(f"[{timestamp}] 在庫: {msg['stock']}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ERROR] キュー処理エラー: {e}")
    
    # キュー処理スレッドを起動
    queue_thread = threading.Thread(target=cui_queue_handler, args=(cui_queue,), daemon=True)
    queue_thread.start()
    
    # メインスレッドを起動
    try:
        run_client(config, stop_event, cui_queue)
    except KeyboardInterrupt:
        print("\n\n[!] 終了シグナルを受信しました")
        stop_event.set()
        print("[!] クリーンアップ中...")
        time.sleep(1)
        print("[✓] 終了しました")

# --------------------------------------------------------------------------
# --- センサーテストモード ---
# --------------------------------------------------------------------------
def run_sensor_test_mode():
    """センサー単体テストモード"""
    print("=" * 70)
    print("  フォトリフレクタセンサーテストモード")
    print("=" * 70)
    
    if PLATFORM != "RASPI":
        print("エラー: センサーテストはRaspberry Piでのみ実行できます")
        print("現在のプラットフォーム:", PLATFORM)
        sys.exit(1)
    
    # 設定読み込み
    config = load_config()
    sensor_pin = config.get('SENSOR_PIN', 22)
    use_sensor = config.get('USE_SENSOR', True)
    
    if not use_sensor:
        print("警告: 設定でセンサーが無効になっています")
        print(f"設定ファイル: {CONFIG_FILE}")
        response = input("\nそれでもテストを続けますか? [y/N]: ").strip().lower()
        if response != 'y':
            print("テストを中止しました")
            sys.exit(0)
    
    print(f"\nセンサーピン: GPIO {sensor_pin} (BCM)")
    print("センサー種類: LBR-127HLD フォトリフレクタ")
    print("出力特性: LOW(0)=物体検知, HIGH(1)=クリア")
    print("\n[Ctrl+C] で終了\n")
    print("=" * 70)
    print("")
    print("状態 | RAW値 | 判定       | タイムスタンプ")
    print("-" * 70)
    
    try:
        # GPIOセットアップ
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        prev_state = None
        poll_interval = 0.1  # 秒
        
        while True:
            # センサー読み取り
            raw_value = GPIO.input(sensor_pin)
            
            # LBR-127HLD: LOW=物体検知, HIGH=クリア
            if raw_value == GPIO.LOW:
                status = "詰まり"
                symbol = "🔴"
            else:
                status = "クリア"
                symbol = "🟢"
            
            # 状態変化時のみ表示
            if raw_value != prev_state:
                timestamp = time.strftime("%H:%M:%S")
                print(f"{symbol}  |  {raw_value}    | {status:10} | {timestamp}")
                prev_state = raw_value
            
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("  テスト終了")
        print("=" * 70)
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # GPIO クリーンアップ
        try:
            GPIO.cleanup()
        except:
            pass

# --------------------------------------------------------------------------
# --- 起動処理 ---
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # センサーテストモードのチェック
    if '--test-sensor' in sys.argv:
        run_sensor_test_mode()
        sys.exit(0)
    
    if PLATFORM == "RASPI":
        ensure_root_privileges()

    # デフォルトはCUIモード（--guiオプションがある場合のみGUIモード）
    if '--gui' in sys.argv and HAS_TKINTER:
        # GUIモードで起動
        root = tk.Tk()
        app = SettingsGUI(root)
        root.mainloop()
    else:
        # CUIモードで起動（デフォルト）
        run_cui_mode()
