#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU ランチャー共通ユーティリティ
=========================================

GUI版とCUI版のランチャーで共通して使用するユーティリティ関数
"""

import os
import sys
import json
import subprocess
import platform
import socket
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ========================================
# 定数定義
# ========================================

# モード定義
MODE_NORMAL = "normal"          # 通常モード（直接Python実行）
MODE_VENV = "venv"              # 仮想環境モード
MODE_DOCKER = "docker"          # Dockerモード

# ロール定義
ROLE_PARENT = "parent"          # 親機
ROLE_SUB_PARENT = "sub_parent"  # 従親機
ROLE_UNIT = "unit"              # 子機

# デフォルト設定
DEFAULT_CONFIG = {
    "server_name": "OITERU親機",
    "server_location": "未設定",
    "parent_url": "http://localhost:5000",
    "unit_name": socket.gethostname(),
    "unit_password": "password123",
    "db_type": "sqlite",
    "mysql_host": "localhost",
    "mysql_port": 3306,
    "mysql_database": "oiteru",
    "mysql_user": "oiteru_user",
    "mysql_password": "oiteru_password_2025",
    "venv_path": ".venv",
    "python_command": "python",
    "docker_compose_file": "docker-compose.yml",
    "server_port": 5000,
    "auto_install_packages": True,
    "last_mode": MODE_NORMAL,
    "last_role": ROLE_PARENT
}

# ========================================
# 設定ファイル管理
# ========================================

def get_project_root() -> Path:
    """プロジェクトルートディレクトリを取得"""
    # このスクリプトがscriptsフォルダにある場合、親ディレクトリがプロジェクトルート
    script_dir = Path(__file__).parent
    
    # scriptsフォルダ内かチェック
    if script_dir.name == "scripts":
        return script_dir.parent
    else:
        return script_dir

def get_config_path() -> Path:
    """ランチャー設定ファイルのパスを取得"""
    # scriptsフォルダ内で実行されている場合を考慮
    script_dir = Path(__file__).parent
    config_path = script_dir / "launcher_config.json"
    
    # scriptsフォルダにない場合は親ディレクトリを確認
    if not config_path.exists():
        parent_dir = script_dir.parent
        config_path = parent_dir / "launcher_config.json"
    
    return config_path

def load_config() -> Dict:
    """設定ファイルを読み込む"""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # デフォルト値とマージ
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception as e:
            print(f"警告: 設定ファイルの読み込みに失敗しました: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config: Dict) -> bool:
    """設定ファイルを保存する"""
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"エラー: 設定ファイルの保存に失敗しました: {e}")
        return False

# ========================================
# 仮想環境管理
# ========================================

def detect_venv() -> Optional[Path]:
    """仮想環境を検出する"""
    project_root = get_project_root()
    
    # 一般的な仮想環境のパス候補
    venv_candidates = [
        project_root / ".venv",
        project_root / "venv",
        project_root / "env",
    ]
    
    for venv_path in venv_candidates:
        if venv_path.exists():
            # Pythonバイナリが存在するか確認
            if platform.system() == "Windows":
                python_exe = venv_path / "Scripts" / "python.exe"
            else:
                python_exe = venv_path / "bin" / "python"
            
            if python_exe.exists():
                return venv_path
    
    return None

def create_venv(venv_path: Optional[Path] = None) -> Tuple[bool, str]:
    """仮想環境を作成する"""
    if venv_path is None:
        venv_path = get_project_root() / ".venv"
    
    try:
        # venvモジュールを使用して仮想環境を作成
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        return True, f"仮想環境を作成しました: {venv_path}"
    except subprocess.CalledProcessError as e:
        return False, f"仮想環境の作成に失敗しました: {e}"
    except Exception as e:
        return False, f"エラー: {e}"

def get_venv_python(venv_path: Path) -> Path:
    """仮想環境のPythonパスを取得"""
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"

def install_requirements(venv_path: Optional[Path] = None) -> Tuple[bool, str]:
    """requirements.txtから依存パッケージをインストール"""
    project_root = get_project_root()
    requirements_file = project_root / "requirements.txt"
    
    if not requirements_file.exists():
        return False, "requirements.txt が見つかりません"
    
    try:
        if venv_path:
            python_exe = get_venv_python(venv_path)
        else:
            python_exe = sys.executable
        
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True
        )
        return True, "依存パッケージをインストールしました"
    except subprocess.CalledProcessError as e:
        return False, f"パッケージのインストールに失敗しました: {e.stderr.decode()}"
    except Exception as e:
        return False, f"エラー: {e}"

# ========================================
# Docker管理
# ========================================

def check_docker() -> Tuple[bool, str]:
    """Dockerが利用可能か確認"""
    try:
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["docker", "ps"],
            check=True,
            capture_output=True
        )
        return True, "Docker は利用可能です"
    except subprocess.CalledProcessError:
        return False, "Docker デーモンが起動していません"
    except FileNotFoundError:
        return False, "Docker がインストールされていません"
    except Exception as e:
        return False, f"Docker の確認中にエラー: {e}"

def check_docker_compose() -> Tuple[bool, str]:
    """Docker Composeが利用可能か確認"""
    try:
        # docker compose (v2)を試す
        result = subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            capture_output=True
        )
        return True, "Docker Compose は利用可能です"
    except subprocess.CalledProcessError:
        # docker-compose (v1)を試す
        try:
            subprocess.run(
                ["docker-compose", "--version"],
                check=True,
                capture_output=True
            )
            return True, "Docker Compose (v1) は利用可能です"
        except:
            return False, "Docker Compose がインストールされていません"
    except Exception as e:
        return False, f"Docker Compose の確認中にエラー: {e}"

def get_docker_compose_command() -> List[str]:
    """適切なDocker Composeコマンドを取得"""
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            capture_output=True
        )
        return ["docker", "compose"]
    except:
        return ["docker-compose"]

# ========================================
# システム情報
# ========================================

def get_system_info() -> Dict:
    """システム情報を取得"""
    return {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "hostname": socket.gethostname(),
        "cwd": str(Path.cwd()),
    }

def check_port_available(port: int) -> bool:
    """指定ポートが利用可能か確認"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", port))
        return True
    except OSError:
        return False

# ========================================
# プロセス起動
# ========================================

def start_server_normal(role: str, config: Dict) -> Tuple[subprocess.Popen, str]:
    """通常モードでサーバーを起動"""
    project_root = get_project_root()
    
    # 環境変数の設定
    env = os.environ.copy()
    
    if role == ROLE_PARENT:
        script = "server.py"
        env["SERVER_NAME"] = config.get("server_name", "OITERU親機")
        env["SERVER_LOCATION"] = config.get("server_location", "未設定")
        env["DB_TYPE"] = config.get("db_type", "sqlite")
        
        if config.get("db_type") == "mysql":
            env["MYSQL_HOST"] = config.get("mysql_host", "localhost")
            env["MYSQL_PORT"] = str(config.get("mysql_port", 3306))
            env["MYSQL_DATABASE"] = config.get("mysql_database", "oiteru")
            env["MYSQL_USER"] = config.get("mysql_user", "oiteru_user")
            env["MYSQL_PASSWORD"] = config.get("mysql_password", "")
    
    elif role == ROLE_SUB_PARENT:
        script = "server.py"
        env["SERVER_NAME"] = config.get("server_name", "OITERU従親機")
        env["SERVER_LOCATION"] = config.get("server_location", "未設定")
        env["DB_TYPE"] = "mysql"  # 従親機は必ずMySQL
        env["MYSQL_HOST"] = config.get("mysql_host", "localhost")
        env["MYSQL_PORT"] = str(config.get("mysql_port", 3306))
        env["MYSQL_DATABASE"] = config.get("mysql_database", "oiteru")
        env["MYSQL_USER"] = config.get("mysql_user", "oiteru_user")
        env["MYSQL_PASSWORD"] = config.get("mysql_password", "")
    
    elif role == ROLE_UNIT:
        script = "unit.py"
        # config.jsonを更新
        update_unit_config(config)
    
    else:
        raise ValueError(f"不明なロール: {role}")
    
    # Pythonスクリプトを実行
    python_cmd = config.get("python_command", "python")
    process = subprocess.Popen(
        [python_cmd, str(project_root / script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    return process, f"{script} を起動しました (PID: {process.pid})"

def start_server_venv(role: str, config: Dict, venv_path: Path) -> Tuple[subprocess.Popen, str]:
    """仮想環境モードでサーバーを起動"""
    project_root = get_project_root()
    python_exe = get_venv_python(venv_path)
    
    # 環境変数の設定
    env = os.environ.copy()
    
    if role == ROLE_PARENT:
        script = "server.py"
        env["SERVER_NAME"] = config.get("server_name", "OITERU親機")
        env["SERVER_LOCATION"] = config.get("server_location", "未設定")
        env["DB_TYPE"] = config.get("db_type", "sqlite")
        
        if config.get("db_type") == "mysql":
            env["MYSQL_HOST"] = config.get("mysql_host", "localhost")
            env["MYSQL_PORT"] = str(config.get("mysql_port", 3306))
            env["MYSQL_DATABASE"] = config.get("mysql_database", "oiteru")
            env["MYSQL_USER"] = config.get("mysql_user", "oiteru_user")
            env["MYSQL_PASSWORD"] = config.get("mysql_password", "")
    
    elif role == ROLE_SUB_PARENT:
        script = "server.py"
        env["SERVER_NAME"] = config.get("server_name", "OITERU従親機")
        env["SERVER_LOCATION"] = config.get("server_location", "未設定")
        env["DB_TYPE"] = "mysql"
        env["MYSQL_HOST"] = config.get("mysql_host", "localhost")
        env["MYSQL_PORT"] = str(config.get("mysql_port", 3306))
        env["MYSQL_DATABASE"] = config.get("mysql_database", "oiteru")
        env["MYSQL_USER"] = config.get("mysql_user", "oiteru_user")
        env["MYSQL_PASSWORD"] = config.get("mysql_password", "")
    
    elif role == ROLE_UNIT:
        script = "unit.py"
        update_unit_config(config)
    
    else:
        raise ValueError(f"不明なロール: {role}")
    
    # 仮想環境のPythonで実行
    process = subprocess.Popen(
        [str(python_exe), str(project_root / script)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    return process, f"{script} を起動しました (venv, PID: {process.pid})"

def start_server_docker(role: str, config: Dict) -> Tuple[Optional[subprocess.Popen], str]:
    """Dockerモードでサーバーを起動"""
    project_root = get_project_root()
    
    # Docker Composeコマンドを取得
    docker_cmd = get_docker_compose_command()
    
    # 環境変数ファイルを作成
    env_file = project_root / ".env"
    env_content = []
    
    if role == ROLE_PARENT:
        compose_file = config.get("docker_compose_file", "docker-compose.yml")
        env_content.append(f"SERVER_NAME={config.get('server_name', 'OITERU親機')}")
        env_content.append(f"SERVER_LOCATION={config.get('server_location', '未設定')}")
        env_content.append(f"DB_TYPE={config.get('db_type', 'sqlite')}")
        
        if config.get("db_type") == "mysql":
            env_content.append(f"MYSQL_HOST={config.get('mysql_host', 'localhost')}")
            env_content.append(f"MYSQL_PORT={config.get('mysql_port', 3306)}")
            env_content.append(f"MYSQL_DATABASE={config.get('mysql_database', 'oiteru')}")
            env_content.append(f"MYSQL_USER={config.get('mysql_user', 'oiteru_user')}")
            env_content.append(f"MYSQL_PASSWORD={config.get('mysql_password', '')}")
    
    elif role == ROLE_SUB_PARENT:
        compose_file = "docker-compose.external-db.yml"
        env_content.append(f"SERVER_NAME={config.get('server_name', 'OITERU従親機')}")
        env_content.append(f"SERVER_LOCATION={config.get('server_location', '未設定')}")
        env_content.append(f"DB_TYPE=mysql")
        env_content.append(f"MYSQL_HOST={config.get('mysql_host', 'localhost')}")
        env_content.append(f"MYSQL_PORT={config.get('mysql_port', 3306)}")
        env_content.append(f"MYSQL_DATABASE={config.get('mysql_database', 'oiteru')}")
        env_content.append(f"MYSQL_USER={config.get('mysql_user', 'oiteru_user')}")
        env_content.append(f"MYSQL_PASSWORD={config.get('mysql_password', '')}")
    
    elif role == ROLE_UNIT:
        compose_file = "docker/docker-compose.unit.yml"
        update_unit_config(config)
    
    else:
        raise ValueError(f"不明なロール: {role}")
    
    # .envファイルを書き込み
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_content))
    except Exception as e:
        return None, f".envファイルの作成に失敗: {e}"
    
    # Docker Composeを起動
    try:
        compose_path = project_root / compose_file
        if not compose_path.exists():
            return None, f"Docker Composeファイルが見つかりません: {compose_file}"
        
        subprocess.run(
            docker_cmd + ["-f", str(compose_path), "up", "-d"],
            check=True,
            cwd=str(project_root)
        )
        return None, f"Dockerコンテナを起動しました ({compose_file})"
    except subprocess.CalledProcessError as e:
        return None, f"Docker起動に失敗: {e}"
    except Exception as e:
        return None, f"エラー: {e}"

def update_unit_config(config: Dict):
    """子機用のconfig.jsonを更新"""
    project_root = get_project_root()
    config_file = project_root / "config.json"
    
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                unit_config = json.load(f)
        else:
            unit_config = {}
        
        # ランチャー設定から必要な項目を更新
        unit_config["SERVER_URL"] = config.get("parent_url", "http://localhost:5000")
        unit_config["UNIT_NAME"] = config.get("unit_name", socket.gethostname())
        unit_config["UNIT_PASSWORD"] = config.get("unit_password", "password123")
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(unit_config, f, indent=4, ensure_ascii=False)
    
    except Exception as e:
        print(f"警告: config.jsonの更新に失敗: {e}")

# ========================================
# ヘルパー関数
# ========================================

def get_role_display_name(role: str) -> str:
    """ロールの表示名を取得"""
    role_names = {
        ROLE_PARENT: "親機",
        ROLE_SUB_PARENT: "従親機",
        ROLE_UNIT: "子機"
    }
    return role_names.get(role, "不明")

def get_mode_display_name(mode: str) -> str:
    """モードの表示名を取得"""
    mode_names = {
        MODE_NORMAL: "通常モード",
        MODE_VENV: "仮想環境モード",
        MODE_DOCKER: "Dockerモード"
    }
    return mode_names.get(mode, "不明")

# ========================================
# カードリーダー管理
# ========================================

def detect_card_reader() -> Tuple[bool, str]:
    """カードリーダーを検出"""
    try:
        # lsusbコマンドでカードリーダーを検出
        result = subprocess.run(
            ["lsusb"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout.lower()
        
        # Sony FeliCa (PaSoRi) やその他のカードリーダーを検出
        reader_keywords = ["sony", "felica", "pasori", "nfc", "card reader"]
        
        for keyword in reader_keywords:
            if keyword in output:
                return True, f"カードリーダーを検出: {keyword}"
        
        return False, "カードリーダーが見つかりません"
    
    except FileNotFoundError:
        return False, "lsusbコマンドが見つかりません (WSL/Linux環境が必要)"
    except subprocess.TimeoutExpired:
        return False, "lsusbコマンドがタイムアウトしました"
    except Exception as e:
        return False, f"カードリーダー検出エラー: {e}"

def check_pcscd() -> Tuple[bool, str]:
    """pcscd (PC/SC デーモン) が起動しているか確認"""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "pcscd"],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return True, "pcscd は起動しています"
        else:
            return False, "pcscd は起動していません"
    
    except FileNotFoundError:
        return False, "pgrepコマンドが見つかりません"
    except Exception as e:
        return False, f"pcscd確認エラー: {e}"

def start_pcscd() -> Tuple[bool, str]:
    """pcscdを起動"""
    try:
        # 既存のpcscdを停止
        subprocess.run(
            ["pkill", "-9", "pcscd"],
            capture_output=True,
            timeout=5
        )
        
        # pcscdを起動
        subprocess.run(
            ["pcscd"],
            capture_output=True,
            timeout=5
        )
        
        # 起動確認
        time.sleep(1)
        is_running, msg = check_pcscd()
        
        if is_running:
            return True, "pcscd を起動しました"
        else:
            return False, "pcscd の起動に失敗しました"
    
    except FileNotFoundError:
        return False, "pcscdコマンドが見つかりません (pcscdパッケージをインストールしてください)"
    except Exception as e:
        return False, f"pcscd起動エラー: {e}"

def attach_usb_to_wsl(bus_id: str = None) -> Tuple[bool, str]:
    """WSL環境でUSBデバイスをアタッチ（Windows専用）"""
    if platform.system() != "Windows":
        return False, "この機能はWindows専用です"
    
    try:
        # usbipdコマンドの存在確認
        result = subprocess.run(
            ["usbipd", "--version"],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False, "usbipdがインストールされていません (winget install usbipd)"
        
        # BUSIDが指定されていない場合、カードリーダーを自動検出
        if not bus_id:
            list_result = subprocess.run(
                ["usbipd", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Sony FeliCa やカードリーダーを探す
            for line in list_result.stdout.split('\n'):
                if any(keyword in line.lower() for keyword in ["sony", "felica", "pasori"]):
                    # BUSIDを抽出 (例: "1-4")
                    parts = line.split()
                    if parts:
                        bus_id = parts[0]
                        break
            
            if not bus_id:
                return False, "カードリーダーのBUSIDを自動検出できませんでした"
        
        # bindする
        subprocess.run(
            ["usbipd", "bind", "--busid", bus_id],
            capture_output=True,
            timeout=10
        )
        
        # WSLにアタッチ
        result = subprocess.run(
            ["usbipd", "attach", "--wsl", "--busid", bus_id],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            return True, f"USBデバイス (BUSID: {bus_id}) をWSLにアタッチしました"
        else:
            error_msg = result.stderr if result.stderr else "不明なエラー"
            return False, f"USBアタッチ失敗: {error_msg}"
    
    except FileNotFoundError:
        return False, "usbipdコマンドが見つかりません (winget install usbipd)"
    except subprocess.TimeoutExpired:
        return False, "USBアタッチがタイムアウトしました"
    except Exception as e:
        return False, f"USBアタッチエラー: {e}"

def initialize_card_reader(auto_attach_wsl: bool = True) -> Tuple[bool, str]:
    """カードリーダーを初期化（検出、アタッチ、pcscd起動）"""
    messages = []
    
    # Windows環境でWSLを使用している場合、USBアタッチを試行
    if platform.system() == "Windows" and auto_attach_wsl:
        messages.append("Windows環境を検出。WSL USB アタッチを試行中...")
        success, msg = attach_usb_to_wsl()
        messages.append(msg)
        
        if not success:
            messages.append("注意: WSLへのUSBアタッチに失敗しました。手動でアタッチしてください。")
    
    # カードリーダーを検出
    messages.append("カードリーダーを検出中...")
    reader_ok, reader_msg = detect_card_reader()
    messages.append(reader_msg)
    
    if not reader_ok:
        return False, "\n".join(messages)
    
    # pcscdを起動
    messages.append("pcscd を起動中...")
    pcscd_ok, pcscd_msg = start_pcscd()
    messages.append(pcscd_msg)
    
    if pcscd_ok:
        return True, "\n".join(messages)
    else:
        return False, "\n".join(messages)
