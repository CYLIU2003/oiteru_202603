"""
OITELUシステム診断モジュール
親機起動時にBIOSチェックのように各種システム診断を実行
"""

import os
import sys
import sqlite3
import socket
import subprocess
import time
from datetime import datetime
from typing import List, Dict, Tuple

# カラー出力用のANSIエスケープコード
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """ヘッダーを表示"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_check(component: str, status: str, detail: str = ""):
    """診断結果を表示"""
    if status == "OK":
        status_str = f"{Colors.OKGREEN}[  OK  ]{Colors.ENDC}"
    elif status == "WARNING":
        status_str = f"{Colors.WARNING}[WARNING]{Colors.ENDC}"
    elif status == "FAIL":
        status_str = f"{Colors.FAIL}[ FAIL ]{Colors.ENDC}"
    else:
        status_str = f"[{status}]"
    
    print(f"{status_str} {component:30s} {detail}")

def check_python_version() -> Tuple[str, str]:
    """Pythonバージョンチェック"""
    version = sys.version.split()[0]
    major, minor = sys.version_info[:2]
    
    if major >= 3 and minor >= 7:
        return ("OK", f"Python {version}")
    else:
        return ("WARNING", f"Python {version} (推奨: 3.7以上)")

def check_required_packages() -> Tuple[str, str]:
    """必須パッケージのチェック"""
    required = ['flask', 'pandas', 'werkzeug']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if not missing:
        return ("OK", f"{len(required)}個のパッケージがインストール済み")
    else:
        return ("FAIL", f"未インストール: {', '.join(missing)}")

def check_database(db_path: str) -> Tuple[str, str]:
    """データベースの存在と整合性チェック"""
    if not os.path.exists(db_path):
        return ("FAIL", "データベースファイルが存在しません")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 必須テーブルの存在確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['users', 'units', 'history', 'info']
        
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            conn.close()
            return ("FAIL", f"不足テーブル: {', '.join(missing_tables)}")
        
        # レコード数取得
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM units")
        unit_count = cursor.fetchone()[0]
        
        conn.close()
        return ("OK", f"ユーザー: {user_count}, 子機: {unit_count}")
        
    except sqlite3.Error as e:
        return ("FAIL", f"DB接続エラー: {str(e)}")

def check_disk_space(path: str = ".") -> Tuple[str, str]:
    """ディスク容量チェック"""
    try:
        stat = os.statvfs(path)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
        used_percent = ((total_gb - free_gb) / total_gb) * 100
        
        if free_gb < 0.5:  # 500MB未満
            return ("FAIL", f"空き容量: {free_gb:.2f}GB (不足)")
        elif free_gb < 1.0:  # 1GB未満
            return ("WARNING", f"空き容量: {free_gb:.2f}GB (使用率: {used_percent:.1f}%)")
        else:
            return ("OK", f"空き容量: {free_gb:.2f}GB (使用率: {used_percent:.1f}%)")
    except Exception as e:
        return ("WARNING", f"チェック失敗: {str(e)}")

def check_network_connectivity() -> Tuple[str, str]:
    """ネットワーク接続チェック"""
    try:
        # ローカルホストでのポート5000の利用可能性チェック
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        
        if result == 0:
            return ("WARNING", "ポート5000が既に使用中")
        else:
            return ("OK", "ポート5000が利用可能")
    except Exception as e:
        return ("WARNING", f"チェック失敗: {str(e)}")

def check_nfc_reader() -> Tuple[str, str]:
    """NFCリーダーチェック（親機では不要だが情報として）"""
    # 親機ではNFCリーダーを使用しないため、これは情報提供のみ
    return ("OK", "親機ではNFCリーダー不要（子機で使用）")

def check_static_files() -> Tuple[str, str]:
    """静的ファイルの存在チェック"""
    required_dirs = ['static', 'templates']
    missing = [d for d in required_dirs if not os.path.exists(d)]
    
    if missing:
        return ("WARNING", f"不足ディレクトリ: {', '.join(missing)}")
    
    # 重要なファイルチェック
    important_files = [
        'static/css/style20250506.css',
        'templates/base.html',
        'templates/index.html'
    ]
    missing_files = [f for f in important_files if not os.path.exists(f)]
    
    if missing_files:
        return ("WARNING", f"{len(missing_files)}個のファイルが不足")
    else:
        return ("OK", "全ての静的ファイルが存在")

def check_permissions() -> Tuple[str, str]:
    """ファイルパーミッションチェック"""
    db_path = 'oiteru.sqlite3'
    
    if not os.path.exists(db_path):
        return ("WARNING", "データベースファイルが存在しません")
    
    try:
        # 読み書き可能かテスト
        readable = os.access(db_path, os.R_OK)
        writable = os.access(db_path, os.W_OK)
        
        if readable and writable:
            return ("OK", "データベースファイルのアクセス権限正常")
        elif readable:
            return ("WARNING", "データベースファイルが書き込み不可")
        else:
            return ("FAIL", "データベースファイルへのアクセス権限なし")
    except Exception as e:
        return ("WARNING", f"チェック失敗: {str(e)}")

def check_backup_system() -> Tuple[str, str]:
    """バックアップシステムのチェック"""
    # バックアップファイルの存在確認
    backup_files = [f for f in os.listdir('.') if f.startswith('oiteru.sqlite3.backup_')]
    
    if not backup_files:
        return ("WARNING", "バックアップファイルが見つかりません")
    
    # 最新のバックアップの日付を確認
    if backup_files:
        latest_backup = max(backup_files)
        return ("OK", f"最新バックアップ: {latest_backup}")
    else:
        return ("WARNING", "バックアップなし")

def check_config_file() -> Tuple[str, str]:
    """設定ファイルのチェック"""
    config_file = 'config.json'
    
    if not os.path.exists(config_file):
        return ("WARNING", "config.jsonが存在しません（オプション）")
    
    try:
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return ("OK", f"{len(config)}個の設定項目を読み込み")
    except Exception as e:
        return ("WARNING", f"config.json読み込みエラー: {str(e)}")

def check_docker_environment() -> Tuple[str, str]:
    """Docker環境チェック"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            return ("OK", f"Docker利用可能: {version}")
        else:
            return ("WARNING", "Dockerコマンド実行エラー")
    except FileNotFoundError:
        return ("WARNING", "Dockerがインストールされていません（オプション）")
    except Exception as e:
        return ("WARNING", f"Dockerチェック失敗: {str(e)}")

def run_full_diagnostics(db_path: str = 'oiteru.sqlite3', verbose: bool = True) -> List[Dict]:
    """全ての診断を実行"""
    start_time = time.time()
    
    if verbose:
        print_header("OITELU システム診断")
        print(f"{Colors.OKCYAN}診断開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}\n")
    
    diagnostics = []
    
    # 各種チェック実行
    checks = [
        ("Pythonバージョン", check_python_version),
        ("必須パッケージ", check_required_packages),
        ("データベース", lambda: check_database(db_path)),
        ("ディスク容量", check_disk_space),
        ("ネットワーク", check_network_connectivity),
        ("NFCリーダー", check_nfc_reader),
        ("静的ファイル", check_static_files),
        ("ファイル権限", check_permissions),
        ("バックアップシステム", check_backup_system),
        ("設定ファイル", check_config_file),
        ("Docker環境", check_docker_environment),
    ]
    
    for component, check_func in checks:
        status, detail = check_func()
        diagnostics.append({
            'component': component,
            'status': status,
            'detail': detail,
            'timestamp': datetime.now().isoformat()
        })
        
        if verbose:
            print_check(component, status, detail)
    
    elapsed = time.time() - start_time
    
    if verbose:
        print(f"\n{Colors.OKCYAN}診断完了: {elapsed:.2f}秒{Colors.ENDC}")
        
        # サマリー表示
        ok_count = sum(1 for d in diagnostics if d['status'] == 'OK')
        warning_count = sum(1 for d in diagnostics if d['status'] == 'WARNING')
        fail_count = sum(1 for d in diagnostics if d['status'] == 'FAIL')
        
        print(f"\n{Colors.BOLD}診断サマリー:{Colors.ENDC}")
        print(f"  {Colors.OKGREEN}OK:      {ok_count}{Colors.ENDC}")
        print(f"  {Colors.WARNING}WARNING: {warning_count}{Colors.ENDC}")
        print(f"  {Colors.FAIL}FAIL:    {fail_count}{Colors.ENDC}")
        
        if fail_count > 0:
            print(f"\n{Colors.FAIL}{Colors.BOLD}重大な問題が検出されました。起動前に修正してください。{Colors.ENDC}")
            return diagnostics
        elif warning_count > 0:
            print(f"\n{Colors.WARNING}警告があります。必要に応じて確認してください。{Colors.ENDC}")
        else:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}全てのチェックが正常に完了しました！{Colors.ENDC}")
        
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    return diagnostics

def should_continue_startup(diagnostics: List[Dict]) -> bool:
    """診断結果に基づいて起動を続行すべきか判定"""
    fail_count = sum(1 for d in diagnostics if d['status'] == 'FAIL')
    
    if fail_count > 0:
        print(f"\n{Colors.FAIL}{Colors.BOLD}致命的なエラーが{fail_count}件検出されました。{Colors.ENDC}")
        response = input(f"{Colors.WARNING}それでも起動を続行しますか? (yes/no): {Colors.ENDC}")
        return response.lower() in ['yes', 'y']
    
    return True

if __name__ == '__main__':
    # スタンドアロンで実行された場合
    diagnostics = run_full_diagnostics()
    
    if not should_continue_startup(diagnostics):
        print(f"{Colors.FAIL}起動を中止しました。{Colors.ENDC}")
        sys.exit(1)
    else:
        print(f"{Colors.OKGREEN}起動準備完了！{Colors.ENDC}")
