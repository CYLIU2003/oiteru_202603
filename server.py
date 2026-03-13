#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU 親機 / 従親機 (Webサーバー)
=========================================

このファイルは親機（従親機）として動作します。
- データベースを持たない場合は「従親機」として外部MySQLに接続
- データベースを持つ場合は「親機」として動作（db_server.pyの使用を推奨）

起動方法:
    python server.py  # legacy互換経路

環境変数:
    DB_TYPE=mysql の場合、外部MySQLに接続
    DB_TYPE=sqlite の場合、ローカルSQLiteを使用
"""

import os
import hashlib
import hmac
import io
import json
import random
import re
import secrets
import socket
import subprocess
import threading
import time
import traceback

import pandas as pd
import requests
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, session, flash, g, send_file
)
from db_adapter import db, get_connection, DatabaseError


def load_env_file(env_path: str):
    """.env を読み込み、未設定の環境変数だけを補完する。"""
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ.setdefault(key, value)


load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# --- Flaskアプリケーションの初期化 ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    minutes=int(os.getenv('ADMIN_SESSION_MINUTES', '30'))
)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oiteru.sqlite3')

if 'FLASK_SECRET_KEY' not in os.environ:
    print("警告: FLASK_SECRET_KEY が未設定です。再起動ごとに一時キーを生成します。")

# ========================================
# サーバー設定
# ========================================
SERVER_NAME = os.getenv('SERVER_NAME', 'OITERU親機')
SERVER_LOCATION = os.getenv('SERVER_LOCATION', '未設定')
SERVER_ID = os.getenv('HOSTNAME', socket.gethostname())

# ========================================
# グローバル設定（DBから読み込み・同期される）
# ========================================
# 初期値は環境変数から取得、その後DBから上書き
server_settings = {
    'auto_register_mode': os.getenv('AUTO_REGISTER_MODE', 'false').lower() == 'true',
    'auto_register_stock': int(os.getenv('AUTO_REGISTER_STOCK', '2')),
    'usage_limit': int(os.getenv('USAGE_LIMIT', '2')),  # 期間あたりの取得上限
    'limit_period': os.getenv('LIMIT_PERIOD', 'day'),   # 上限期間: day, week, month
    'server_name': SERVER_NAME,
    'server_location': SERVER_LOCATION,
}

# 設定バージョン（変更時にインクリメント）
settings_version = 0

# 未登録子機の一時保存用（メモリ内）
unregistered_units = {}

# 子機からの診断情報保存用（メモリ内）
unit_diagnostics = {}

# 子機からのログ保存用（メモリ内）
unit_logs = {}

# 子機設定の保存用（メモリ内、ハートビートで同期）
unit_configs = {}

# 子機への保留中の設定変更（unit_name -> config dict）
pending_unit_config_updates = {}
unit_session_tokens = {}

ADMIN_LOGIN_ATTEMPTS = {}
MAX_LOGIN_ATTEMPTS = int(os.getenv('ADMIN_LOGIN_MAX_ATTEMPTS', '5'))
LOGIN_BLOCK_WINDOW_SECONDS = int(os.getenv('ADMIN_LOGIN_BLOCK_WINDOW_SECONDS', '900'))
UNIT_API_AUTH_HEADER = 'X-Oiteru-Unit-Auth'
DEFAULT_ADMIN_HASHES = {
    hashlib.sha256('admin'.encode()).hexdigest(),
    hashlib.sha256('change-this-admin-password'.encode()).hexdigest(),
    '1b2169971e65007dea2905a92b3f93cceea332f35baf0d1acc74c0dbb3426368',
}
INSECURE_ADMIN_PASSWORDS = {
    'admin',
    'password',
    'change-this-admin-password',
    '12345678',
    '123456789',
}
INSECURE_FLASK_SECRET_KEYS = {
    'change-this-secret-key',
    'secret',
    'flask-secret',
}
INSECURE_MYSQL_PASSWORDS = {
    'change-this-mysql-password',
    'rootpassword',
    'password',
    'oiteru_password_2025',
}


def parse_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def validate_runtime_security():
    """起動前に最低限のセキュリティ設定を検証する。"""
    strict_security = parse_env_bool(
        'OITERU_STRICT_SECURITY',
        default=(db.db_type == 'mysql'),
    )
    errors = []
    warnings = []

    secret_key = (os.getenv('FLASK_SECRET_KEY') or '').strip()
    if not secret_key:
        message = "FLASK_SECRET_KEY が未設定です。"
        (errors if strict_security else warnings).append(message)
    elif secret_key in INSECURE_FLASK_SECRET_KEYS or len(secret_key) < 32:
        message = "FLASK_SECRET_KEY が既定値または短すぎる値です（32文字以上推奨）。"
        (errors if strict_security else warnings).append(message)

    admin_password = (os.getenv('OITERU_ADMIN_PASSWORD') or '').strip()
    if not admin_password:
        message = "OITERU_ADMIN_PASSWORD が未設定です。"
        (errors if strict_security else warnings).append(message)
    elif admin_password.lower() in INSECURE_ADMIN_PASSWORDS:
        errors.append("OITERU_ADMIN_PASSWORD に既定値/弱い値は使用できません。")
    elif len(admin_password) < 12:
        message = "OITERU_ADMIN_PASSWORD は12文字以上を推奨します。"
        (errors if strict_security else warnings).append(message)

    if db.db_type == 'mysql':
        mysql_password = (os.getenv('MYSQL_PASSWORD') or '').strip()
        if not mysql_password:
            errors.append("MYSQL_PASSWORD が未設定です。")
        elif mysql_password in INSECURE_MYSQL_PASSWORDS:
            errors.append("MYSQL_PASSWORD に既定値/弱い値は使用できません。")

    for warning in warnings:
        print(f"警告: {warning}")

    if errors:
        raise RuntimeError(
            "セキュリティ設定エラーにより起動を停止しました:\n- "
            + "\n- ".join(errors)
        )


def hash_secret(secret_value: str) -> str:
    """パスワードや共有秘密を安全な形式で保存する。"""
    return generate_password_hash(secret_value)


def verify_secret(stored_secret: str, provided_secret: str) -> bool:
    """ハッシュ化済みと旧形式の両方を互換的に検証する。"""
    if not stored_secret or not provided_secret:
        return False
    if hmac.compare_digest(stored_secret, provided_secret):
        return True
    try:
        if stored_secret.startswith(('pbkdf2:', 'scrypt:')):
            return check_password_hash(stored_secret, provided_secret)
    except ValueError:
        pass
    legacy_hash = hashlib.sha256(provided_secret.encode()).hexdigest()
    return hmac.compare_digest(stored_secret, legacy_hash)


def is_default_admin_secret(stored_secret: str) -> bool:
    return stored_secret in DEFAULT_ADMIN_HASHES or stored_secret == 'admin'


def get_request_ip() -> str:
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def prune_login_attempts():
    cutoff = time.time() - LOGIN_BLOCK_WINDOW_SECONDS
    expired = [
        ip for ip, attempts in ADMIN_LOGIN_ATTEMPTS.items()
        if attempts and attempts[-1] < cutoff
    ]
    for ip in expired:
        del ADMIN_LOGIN_ATTEMPTS[ip]


def is_login_blocked(ip_address: str) -> bool:
    prune_login_attempts()
    attempts = [
        attempt_time for attempt_time in ADMIN_LOGIN_ATTEMPTS.get(ip_address, [])
        if attempt_time >= time.time() - LOGIN_BLOCK_WINDOW_SECONDS
    ]
    ADMIN_LOGIN_ATTEMPTS[ip_address] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def record_login_failure(ip_address: str):
    prune_login_attempts()
    ADMIN_LOGIN_ATTEMPTS.setdefault(ip_address, []).append(time.time())


def clear_login_failures(ip_address: str):
    ADMIN_LOGIN_ATTEMPTS.pop(ip_address, None)


def require_admin_api():
    if not session.get("admin_logged_in"):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    session.permanent = True
    return None


def validate_unit_credentials(conn, unit_name: str, unit_password: str):
    if not unit_name or not unit_password:
        return None
    unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
    if not unit:
        return None
    if not verify_secret(unit['password'], unit_password):
        return None
    return unit


def issue_unit_session_token(unit_name: str) -> str:
    token = secrets.token_urlsafe(24)
    unit_session_tokens[unit_name] = token
    return token


def validate_unit_token(unit_name: str, provided_token: str) -> bool:
    expected_token = unit_session_tokens.get(unit_name)
    return bool(expected_token and provided_token) and hmac.compare_digest(
        expected_token,
        provided_token,
    )


def get_authenticated_unit(conn, unit_name: str, unit_password: str = None, unit_token: str = None):
    unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
    if not unit:
        return None
    if unit_token and validate_unit_token(unit_name, unit_token):
        return unit
    if unit_password and verify_secret(unit['password'], unit_password):
        return unit
    return None


def get_push_headers(unit_name: str) -> dict:
    unit_token = unit_session_tokens.get(unit_name)
    if not unit_token:
        return {}
    return {UNIT_API_AUTH_HEADER: unit_token}


def ensure_admin_password():
    """管理者パスワードを初期化し、固定値運用を防ぐ。"""
    configured_password = os.getenv('OITERU_ADMIN_PASSWORD', '').strip()
    if configured_password and configured_password.lower() in INSECURE_ADMIN_PASSWORDS:
        raise RuntimeError("既定値または弱い管理者パスワードは使用できません。")
    generated_password = None
    warning_message = None

    with get_connection() as conn:
        info = db.fetchone(conn, "SELECT pass FROM info WHERE id = 1")
        if not info:
            generated_password = configured_password or secrets.token_urlsafe(16)
            db.execute(
                conn,
                "INSERT INTO info (id, pass) VALUES (?, ?)",
                (1, hash_secret(generated_password)),
            )
        elif configured_password and is_default_admin_secret(info['pass']):
            db.execute(
                conn,
                "UPDATE info SET pass = ? WHERE id = 1",
                (hash_secret(configured_password),),
            )
        elif is_default_admin_secret(info['pass']):
            warning_message = (
                "管理者パスワードが既定値のままです。"
                " OITERU_ADMIN_PASSWORD を設定して更新してください。"
            )

    if generated_password:
        print("管理者アカウントを初期化しました。")
        print(f"管理者パスワード: {generated_password}")
        if not configured_password:
            print("OITERU_ADMIN_PASSWORD を設定して恒久値へ更新してください。")
    if warning_message:
        print(f"警告: {warning_message}")


# ========================================
# 設定管理関数
# ========================================
def load_settings_from_db():
    """データベースから設定を読み込む"""
    global server_settings, settings_version
    try:
        with get_connection() as conn:
            # settingsテーブルが存在するか確認
            settings_row = db.fetchone(conn, "SELECT * FROM settings WHERE id = 1")
            if settings_row:
                server_settings['auto_register_mode'] = bool(settings_row.get('auto_register_mode', 0))
                server_settings['auto_register_stock'] = int(settings_row.get('auto_register_stock', 2))
                # daily_limit を usage_limit に移行（後方互換）
                server_settings['usage_limit'] = int(settings_row.get('usage_limit') or settings_row.get('daily_limit', 2))
                server_settings['limit_period'] = settings_row.get('limit_period', 'day') or 'day'
                settings_version = int(settings_row.get('version', 0))
                print(f"[DEBUG] 設定をDBから読み込み: auto_register_mode={server_settings['auto_register_mode']}, version={settings_version}")
            else:
                print(f"[DEBUG] settingsテーブルにデータがありません。デフォルト設定を使用します。")
    except Exception as e:
        print(f"設定読み込みエラー（テーブルが未作成の可能性）: {e}")


def save_settings_to_db():
    """設定をデータベースに保存する"""
    global settings_version
    settings_version += 1
    try:
        with get_connection() as conn:
            # UPSERT (存在すれば更新、なければ挿入)
            existing = db.fetchone(conn, "SELECT id FROM settings WHERE id = 1")
            if existing:
                db.execute(conn, """
                    UPDATE settings SET 
                        auto_register_mode = ?,
                        auto_register_stock = ?,
                        usage_limit = ?,
                        limit_period = ?,
                        version = ?,
                        updated_at = ?
                    WHERE id = 1
                """, (
                    1 if server_settings['auto_register_mode'] else 0,
                    server_settings['auto_register_stock'],
                    server_settings['usage_limit'],
                    server_settings['limit_period'],
                    settings_version,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            else:
                db.execute(conn, """
                    INSERT INTO settings (id, auto_register_mode, auto_register_stock, usage_limit, limit_period, version, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?, ?)
                """, (
                    1 if server_settings['auto_register_mode'] else 0,
                    server_settings['auto_register_stock'],
                    server_settings['usage_limit'],
                    server_settings['limit_period'],
                    settings_version,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        print(f"設定をDBに保存しました (version: {settings_version})")
        return True
    except Exception as e:
        print(f"設定保存エラー: {e}")
        return False


# --- データベース接続ヘルパー ---
def get_db_connection():
    """データベース接続を取得（db_adapter経由）"""
    return get_connection()


@app.teardown_appcontext
def close_connection(exception):
    pass


# --- 期間内利用回数チェック ---
def get_period_start_date(period: str) -> str:
    """期間の開始日を取得する（YYYY-MM-DD形式）"""
    now = datetime.now()
    if period == 'day':
        return now.strftime("%Y-%m-%d")
    elif period == 'week':
        # 週の開始日（月曜日）を取得
        start = now - timedelta(days=now.weekday())
        return start.strftime("%Y-%m-%d")
    elif period == 'month':
        # 月の開始日
        return now.strftime("%Y-%m-01")
    else:
        return now.strftime("%Y-%m-%d")


def get_usage_count_in_period(conn, card_id: str, period: str) -> int:
    """指定期間内のユーザーの利用回数を取得する"""
    period_start = get_period_start_date(period)

    # 先にイベントテーブルを参照し、なければ旧history集計にフォールバック
    try:
        result = db.fetchone(conn, """
            SELECT COUNT(*) as count FROM dispense_events
            WHERE card_id = ?
              AND status = 'recorded'
              AND created_at >= ?
        """, (card_id, period_start + " 00:00:00"))
        return result['count'] if result else 0
    except Exception:
        result = db.fetchone(conn, """
            SELECT COUNT(*) as count FROM history 
            WHERE type = 'success' 
              AND txt LIKE ?
              AND created_at >= ?
        """, (f"%{card_id}%", period_start + " 00:00:00"))
        return result['count'] if result else 0


def get_period_display_name(period: str) -> str:
    """期間の表示名を取得"""
    period_names = {
        'day': '1日',
        'week': '1週間',
        'month': '1ヶ月'
    }
    return period_names.get(period, '1日')


def check_and_reset_user_stock(conn, user, period: str) -> dict:
    """期間が変わった場合、ユーザーのstockをリセットする
    
    Args:
        conn: データベース接続
        user: ユーザー情報の辞書
        period: 期間 ('day', 'week', 'month')
    
    Returns:
        更新されたユーザー情報（リセットされた場合）、またはそのまま（リセット不要の場合）
    """
    card_id = user['card_id']
    last_reset = user.get('last_reset_date')
    
    # last_reset_dateがNullの場合は今日の日付を設定
    if not last_reset:
        today = datetime.now().strftime("%Y-%m-%d")
        db.execute(conn, "UPDATE users SET last_reset_date = ? WHERE card_id = ?", (today, card_id))
        user['last_reset_date'] = today
        return user
    
    # last_reset_dateを文字列に統一（MySQLはdatetime.dateを返す場合がある）
    if hasattr(last_reset, 'strftime'):
        last_reset = last_reset.strftime("%Y-%m-%d")
    
    # 期間の開始日を取得
    period_start = get_period_start_date(period)
    
    # last_reset_dateが期間の開始日より前なら、stockをリセット
    if last_reset < period_start:
        # stockを自動登録時の初期値にリセット
        reset_stock = server_settings['auto_register_stock']
        today = datetime.now().strftime("%Y-%m-%d")
        
        db.execute(conn, 
            "UPDATE users SET stock = ?, last_reset_date = ? WHERE card_id = ?",
            (reset_stock, today, card_id))
        
        # ユーザー情報を更新
        user['stock'] = reset_stock
        user['last_reset_date'] = today
        
        period_name = get_period_display_name(period)
        add_history(f"[自動リセット] {period_name}が変わったため、カードID {card_id} の残数を {reset_stock} にリセットしました", 'system')
        print(f"[自動リセット] カードID {card_id} の残数を {reset_stock} にリセット（{period_name}変更）")
    
    return user


# --- 履歴追加 ---
def add_history(message: str, hist_type: str = 'usage'):
    """履歴を追加する"""
    with get_connection() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(conn, 
            "INSERT INTO history (txt, type, created_at) VALUES (?, ?, ?)",
            (message, hist_type, now))


def create_dispense_event(conn, event_id: str, unit_name: str, card_id: str, status: str, error_code: str = None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(conn, """
        INSERT INTO dispense_events (event_id, unit_name, card_id, status, error_code, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (event_id, unit_name, card_id, status, error_code, now, now))


def update_dispense_event(conn, event_id: str, status: str, error_code: str = None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(conn, """
        UPDATE dispense_events
           SET status = ?, error_code = ?, updated_at = ?
         WHERE event_id = ?
    """, (status, error_code, now, event_id))


def generate_event_id() -> str:
    return secrets.token_hex(16)


# --- パスワード確認 ---
def check_password(entered_password: str) -> bool:
    """管理者パスワードを確認する"""
    with get_connection() as conn:
        info = db.fetchone(conn, "SELECT pass FROM info WHERE id = 1")
    return bool(info and verify_secret(info['pass'], entered_password))


# --- データベース初期化 ---
def init_db():
    """データベースのテーブルを初期化する"""
    if db.db_type == 'mysql':
        print("MySQLモード: 必要テーブルを確認します")
        try:
            with get_connection() as conn:
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        card_id VARCHAR(255) UNIQUE NOT NULL,
                        allow TINYINT DEFAULT 1,
                        entry VARCHAR(50),
                        stock INT DEFAULT 2,
                        today INT DEFAULT 0,
                        total INT DEFAULT 0,
                        last_reset_date DATE,
                        last1 VARCHAR(50), last2 VARCHAR(50), last3 VARCHAR(50), last4 VARCHAR(50), last5 VARCHAR(50),
                        last6 VARCHAR(50), last7 VARCHAR(50), last8 VARCHAR(50), last9 VARCHAR(50), last10 VARCHAR(50)
                    )
                """)
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS units (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        stock INT DEFAULT 0,
                        initial_stock INT DEFAULT 100,
                        connect TINYINT DEFAULT 0,
                        available TINYINT DEFAULT 1,
                        last_seen DATETIME,
                        ip_address VARCHAR(50)
                    )
                """)
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        txt TEXT NOT NULL,
                        type VARCHAR(20) DEFAULT 'usage',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS dispense_events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        event_id VARCHAR(64) UNIQUE NOT NULL,
                        unit_name VARCHAR(255) NOT NULL,
                        card_id VARCHAR(255) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        error_code VARCHAR(64),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS settings (
                        id INT PRIMARY KEY,
                        auto_register_mode TINYINT DEFAULT 0,
                        auto_register_stock INT DEFAULT 2,
                        usage_limit INT DEFAULT 2,
                        limit_period VARCHAR(10) DEFAULT 'day',
                        version INT DEFAULT 0,
                        updated_at DATETIME
                    )
                """)
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS info (
                        id INT PRIMARY KEY,
                        pass VARCHAR(255) NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except Exception as e:
            print(f"MySQL初期化エラー: {e}")
        return
        
    if os.path.exists(DB_PATH):
        print("データベースは既に存在します。")
        # settingsテーブルの追加を試みる
        try:
            with get_connection() as conn:
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY,
                        auto_register_mode INTEGER DEFAULT 0,
                        auto_register_stock INTEGER DEFAULT 2,
                        usage_limit INTEGER DEFAULT 2,
                        limit_period TEXT DEFAULT 'day',
                        version INTEGER DEFAULT 0,
                        updated_at TEXT
                    )
                """)
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS dispense_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE NOT NULL,
                        unit_name TEXT NOT NULL,
                        card_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        error_code TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)
        except Exception as e:
            print(f"settingsテーブル作成エラー: {e}")
        return

    print("新しいデータベースを作成・初期化します...")
    with app.app_context():
        with get_connection() as conn:
            # usersテーブル
            db.execute(conn, '''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id TEXT UNIQUE NOT NULL,
                    allow INTEGER DEFAULT 1,
                    entry TEXT,
                    stock INTEGER DEFAULT 2,
                    today INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    last1 TEXT, last2 TEXT, last3 TEXT, last4 TEXT, last5 TEXT,
                    last6 TEXT, last7 TEXT, last8 TEXT, last9 TEXT, last10 TEXT
                )
            ''')
            
            # unitsテーブル
            db.execute(conn, '''
                CREATE TABLE units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    stock INTEGER DEFAULT 0,
                    initial_stock INTEGER DEFAULT 100,
                    connect INTEGER DEFAULT 0,
                    available INTEGER DEFAULT 1,
                    last_seen TEXT,
                    ip_address TEXT
                )
            ''')
            
            # historyテーブル
            db.execute(conn, '''
                CREATE TABLE history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    txt TEXT NOT NULL,
                    type TEXT DEFAULT 'usage',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # dispense_eventsテーブル
            db.execute(conn, '''
                CREATE TABLE dispense_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    unit_name TEXT NOT NULL,
                    card_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # infoテーブル
            db.execute(conn, '''
                CREATE TABLE info (
                    id INTEGER PRIMARY KEY,
                    pass TEXT NOT NULL
                )
            ''')

            print("データベースの初期化が完了しました。")


# --- DBマイグレーション ---
def migrate_db():
    """データベーススキーマのマイグレーション"""
    try:
        with get_connection() as conn:
            # settingsテーブルに新しいカラムを追加（存在しない場合）
            if db.db_type == 'mysql':
                # MySQLの場合
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS dispense_events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        event_id VARCHAR(64) UNIQUE NOT NULL,
                        unit_name VARCHAR(255) NOT NULL,
                        card_id VARCHAR(255) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        error_code VARCHAR(64),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)

                try:
                    db.execute(conn, "ALTER TABLE settings ADD COLUMN usage_limit INT DEFAULT 2")
                    print("  - settingsテーブルに usage_limit カラムを追加しました")
                except Exception:
                    pass  # 既に存在する場合はスキップ
                
                try:
                    db.execute(conn, "ALTER TABLE settings ADD COLUMN limit_period VARCHAR(10) DEFAULT 'day'")
                    print("  - settingsテーブルに limit_period カラムを追加しました")
                except Exception:
                    pass  # 既に存在する場合はスキップ
                
                # usersテーブルにlast_reset_dateカラムを追加
                try:
                    db.execute(conn, "ALTER TABLE users ADD COLUMN last_reset_date DATE")
                    print("  - usersテーブルに last_reset_date カラムを追加しました")
                    # 既存ユーザーには今日の日付を設定
                    today = datetime.now().strftime("%Y-%m-%d")
                    db.execute(conn, "UPDATE users SET last_reset_date = ? WHERE last_reset_date IS NULL", (today,))
                except Exception:
                    pass
                
                # daily_limitの値をusage_limitに移行
                try:
                    db.execute(conn, "UPDATE settings SET usage_limit = daily_limit WHERE usage_limit IS NULL OR usage_limit = 0")
                except Exception:
                    pass
            else:
                # SQLiteの場合
                db.execute(conn, """
                    CREATE TABLE IF NOT EXISTS dispense_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE NOT NULL,
                        unit_name TEXT NOT NULL,
                        card_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        error_code TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                """)

                try:
                    db.execute(conn, "ALTER TABLE settings ADD COLUMN usage_limit INTEGER DEFAULT 2")
                    print("  - settingsテーブルに usage_limit カラムを追加しました")
                except Exception:
                    pass
                
                try:
                    db.execute(conn, "ALTER TABLE settings ADD COLUMN limit_period TEXT DEFAULT 'day'")
                    print("  - settingsテーブルに limit_period カラムを追加しました")
                except Exception:
                    pass
                
                # usersテーブルにlast_reset_dateカラムを追加
                try:
                    db.execute(conn, "ALTER TABLE users ADD COLUMN last_reset_date TEXT")
                    print("  - usersテーブルに last_reset_date カラムを追加しました")
                    # 既存ユーザーには今日の日付を設定
                    today = datetime.now().strftime("%Y-%m-%d")
                    db.execute(conn, "UPDATE users SET last_reset_date = ? WHERE last_reset_date IS NULL", (today,))
                except Exception:
                    pass
                
                try:
                    db.execute(conn, "UPDATE settings SET usage_limit = daily_limit WHERE usage_limit IS NULL OR usage_limit = 0")
                except Exception:
                    pass
    except Exception as e:
        print(f"マイグレーションエラー: {e}")


# ========================================
# 子機向けブロードキャスト (Tailscale対応)
# ========================================
def get_tailscale_ip():
    """Tailscale IPを取得"""
    try:
        result = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_local_ip():
    """ローカルIPを取得"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def broadcast_server_info():
    """子機向けにサーバー情報をブロードキャスト"""
    tailscale_ip = get_tailscale_ip()
    server_ip = tailscale_ip if tailscale_ip else get_local_ip()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while True:
        message = json.dumps({
            "type": "oiteru_server_heartbeat",
            "server_ip": server_ip,
            "port": 5000
        }).encode('utf-8')
        
        try:
            sock.sendto(message, ('<broadcast>', 12345))
        except Exception as e:
            print(f"!! ハートビート送信エラー: {e}")
        
        time.sleep(3)


# ========================================
# UIルート
# ========================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """手動登録ページ（自動登録モードでは使用頻度低）"""
    if request.method == "POST":
        card_id = request.form.get('card_id', '').strip()
        
        # カードIDが空の場合、NFCリーダーから読み取る
        if not card_id:
            try:
                import nfc
                import time
                
                clf = nfc.ContactlessFrontend('usb')
                if clf:
                    # カードを検出（最大3秒待機）
                    start_time = time.time()
                    while time.time() - start_time < 3:
                        target = clf.sense(nfc.clf.RemoteTarget('106A'), 
                                          nfc.clf.RemoteTarget('106B'),
                                          nfc.clf.RemoteTarget('212F'),
                                          iterations=5, interval=0.1)
                        if target:
                            tag = nfc.tag.activate(clf, target)
                            if tag:
                                card_id = tag.identifier.hex().upper()
                                break
                    clf.close()
            except Exception as e:
                flash(f"カード読み取りエラー: {e}", "error")
                return redirect(url_for("register"))
        
        if card_id:
            try:
                with get_connection() as conn:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    db.execute(conn, "INSERT INTO users (card_id, entry, stock) VALUES (?, ?, ?)", 
                              (card_id, now, server_settings['auto_register_stock']))
                add_history(f"新規登録({card_id})", 'system')
                flash(f"登録が完了しました。(カードID: {card_id})", "success")
            except DatabaseError:
                flash("この学生証は既に登録済みです。", "warning")
            except Exception as e:
                flash(f"データベース登録中にエラーが発生しました: {e}", "error")
        else:
            flash("カードを読み取れませんでした。カードをリーダーに置いてください。", "warning")
        return redirect(url_for("register"))
    
    # NFCリーダー接続確認
    reader_connected = False
    try:
        import nfc
        clf = nfc.ContactlessFrontend('usb')
        if clf:
            reader_connected = True
            clf.close()
    except:
        pass
    
    return render_template("register.html", reader_connected=reader_connected)


@app.route("/usage", methods=["GET", "POST"])
def usage():
    """利用確認ページ"""
    if request.method == "POST":
        card_id = request.form.get('card_id', '').strip()
        if card_id:
            with get_connection() as conn:
                user = db.fetchone(conn, "SELECT * FROM users WHERE card_id = ?", (card_id,))
                if user:
                    return render_template("usage_result.html", **dict(user))
                else:
                    flash("この学生証は登録されていません。", "warning")
        return redirect(url_for("usage"))
    
    # NFCリーダー接続確認
    reader_connected = False
    try:
        import nfc
        clf = nfc.ContactlessFrontend('usb')
        if clf:
            reader_connected = True
            clf.close()
    except:
        pass
    
    return render_template("usage.html", reader_connected=reader_connected)


# ========================================
# 管理者ルート
# ========================================
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if 'logout' in request.args:
        session.pop('admin_logged_in', None)
        flash("ログアウトしました。", "success")
        return redirect(url_for('admin_login'))
    if request.method == "POST":
        request_ip = get_request_ip()
        if is_login_blocked(request_ip):
            flash("ログイン試行回数が上限に達しました。しばらく待ってから再試行してください。", "error")
            return render_template("admin_login.html")

        entered_pass = request.form.get("password", "")
        if check_password(entered_pass):
            session["admin_logged_in"] = True
            session.permanent = True
            clear_login_failures(request_ip)
            return redirect(url_for("admin_dashboard"))
        else:
            record_login_failure(request_ip)
            flash("パスワードが違います。", "error")
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    # 有効データ開始日時（テストデータを除外）
    valid_start_datetime = datetime(2026, 1, 22, 19, 20, 0)
    
    with get_connection() as conn:
        users = db.fetchall(conn, "SELECT * FROM users")
        units = db.fetchall(conn, "SELECT * FROM units")
        history = db.fetchall(conn, "SELECT * FROM history ORDER BY id DESC")
        # 実際の排出数を履歴テーブルのsuccessレコード数でカウント（valid_start_datetime以降）
        dispensed_row = db.fetchone(conn, 
            "SELECT COUNT(*) as total FROM history WHERE type = 'success' AND created_at >= ?",
            (valid_start_datetime.strftime("%Y-%m-%d %H:%M:%S"),))
        total_dispensed = int(dispensed_row['total']) if dispensed_row and dispensed_row['total'] else 0

    server_info = {
        'name': SERVER_NAME,
        'location': SERVER_LOCATION,
        'id': SERVER_ID,
        'db_type': db.db_type.upper(),
        'auto_register': server_settings['auto_register_mode'],
        'auto_register_stock': server_settings['auto_register_stock'],
        'usage_limit': server_settings['usage_limit'],
        'limit_period': server_settings['limit_period']
    }

    return render_template("admin_dashboard.html", 
                         users=users, 
                         units=units, 
                         history=history, 
                         total_dispensed=total_dispensed,
                         server_info=server_info)


@app.route("/admin/users")
def admin_users():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    with get_connection() as conn:
        users = db.fetchall(conn, "SELECT * FROM users")
    return render_template("admin_users.html", users=users)


@app.route("/admin/user_detail/<int:uid>", methods=["GET", "POST"])
def admin_user_detail(uid):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    if request.method == "POST":
        with get_connection() as conn:
            if request.form.get("action") == "delete":
                db.execute(conn, "DELETE FROM users WHERE id = ?", (uid,))
                add_history(f"利用者を削除 (ID:{uid})", 'system')
                flash(f"利用者(ID:{uid})を削除しました。", "success")
                return redirect(url_for("admin_users"))
            
            card_id = request.form.get("cardid")
            allow = request.form.get("allow")
            stock = request.form.get("stock")
            db.execute(conn,
                "UPDATE users SET card_id = ?, allow = ?, stock = ? WHERE id = ?",
                (card_id, allow, stock, uid)
            )
        add_history(f"利用者情報を更新 (ID:{uid})", 'system')
        flash(f"利用者(ID:{uid})の情報を更新しました。", "success")
        return redirect(url_for("admin_user_detail", uid=uid))
    
    with get_connection() as conn:
        user = db.fetchone(conn, "SELECT * FROM users WHERE id = ?", (uid,))
    if not user:
        flash("指定された利用者は見つかりません。", "error")
        return redirect(url_for("admin_users"))
    return render_template("admin_user_detail.html", user=user)


@app.route("/admin/units")
def admin_units():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    with get_connection() as conn:
        units = db.fetchall(conn, "SELECT * FROM units")
    return render_template("admin_units.html", units=units, unregistered_units=unregistered_units)


@app.route("/admin/unit_detail/<int:uid>", methods=["GET", "POST"])
def admin_unit_detail(uid):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    if request.method == "POST":
        with get_connection() as conn:
            if request.form.get("action") == "delete":
                db.execute(conn, "DELETE FROM units WHERE id = ?", (uid,))
                add_history(f"子機を削除 (ID:{uid})", 'system')
                flash(f"子機(ID:{uid})を削除しました。", "success")
                return redirect(url_for("admin_units"))
            
            # 名前はDBに反映しない（表示名のみ）
            # name = request.form.get("name")
            stock = request.form.get("stock")
            initial_stock = request.form.get("initial_stock")
            available = request.form.get("available")
            db.execute(conn,
                "UPDATE units SET stock = ?, initial_stock = ?, available = ? WHERE id = ?",
                (stock, initial_stock, available, uid)
            )
        add_history(f"子機情報を更新 (ID:{uid})", 'system')
        flash(f"子機(ID:{uid})の情報を更新しました。", "success")
        return redirect(url_for("admin_unit_detail", uid=uid))
    
    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE id = ?", (uid,))
    if not unit:
        flash("指定された子機は見つかりません。", "error")
        return redirect(url_for("admin_units"))
    
    # 子機の設定情報を取得
    unit_name = unit['name']
    unit_config = unit_configs.get(unit_name, {}).get('config', None)
    config_last_updated = unit_configs.get(unit_name, {}).get('last_updated', None)
    has_pending_config = unit_name in pending_unit_config_updates
    
    return render_template("admin_unit_detail.html", unit=unit, 
                           unit_config=unit_config, 
                           config_last_updated=config_last_updated,
                           has_pending_config=has_pending_config)


@app.route("/admin/new_unit", methods=["GET", "POST"])
def admin_new_unit():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        stock = request.form.get("stock", 0)
        
        try:
            with get_connection() as conn:
                db.execute(conn, 
                    "INSERT INTO units (name, password, stock, initial_stock) VALUES (?, ?, ?, ?)",
                    (name, hash_secret(password), stock, stock))
            add_history(f"新しい子機を登録 ({name})", 'system')
            flash(f"子機({name})を登録しました。", "success")
            return redirect(url_for("admin_units"))
        except DatabaseError:
            flash("この子機名は既に登録されています。", "warning")
    
    return render_template("admin_new_unit.html")


@app.route("/admin/history")
def admin_history():
    """排出成功の利用履歴を表示（カードタッチ＋排出成功のみカウント）"""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    with get_connection() as conn:
        history = db.fetchall(conn, "SELECT * FROM history WHERE type = 'success' ORDER BY created_at DESC LIMIT 100")
    return render_template("admin_history.html", history=history)


@app.route("/admin/backup/download")
def admin_backup_download():
    """Excel形式でバックアップダウンロード"""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    try:
        with get_connection() as conn:
            users = db.fetchall(conn, "SELECT * FROM users ORDER BY id")
        users_list = [dict(row) for row in users]
        if not users_list:
            flash("バックアップ対象のユーザーデータがありません。", "warning")
            return redirect(url_for('admin_dashboard'))
        df = pd.DataFrame(users_list)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='users')
        output.seek(0)
        filename = f"backup_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        add_history("データバックアップ作成", 'system')
        return send_file(
            output, as_attachment=True, download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f"バックアップファイルの作成中にエラーが発生しました: {e}", "error")
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/restore', methods=['GET', 'POST'])
def admin_restore():
    """バックアップファイルから復元"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        if 'backup_file' not in request.files:
            flash('ファイルが選択されていません。', 'error')
            return redirect(request.url)
        file = request.files['backup_file']
        if file.filename == '' or not file.filename.endswith('.xlsx'):
            flash('.xlsxファイルをアップロードしてください。', 'warning')
            return redirect(request.url)
        try:
            df = pd.read_excel(file)
            required_columns = ['card_id', 'allow', 'entry', 'stock', 'today', 'total']
            if not all(col in df.columns for col in required_columns):
                flash('Excelファイルの形式が正しくありません。', 'error')
                return redirect(request.url)
            with get_connection() as conn:
                db.execute(conn, "DELETE FROM users")
                for _, row in df.iterrows():
                    db.execute(conn, '''
                        INSERT INTO users (card_id, allow, entry, stock, today, total) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (row['card_id'], row['allow'], row['entry'], 
                          row['stock'], row['today'], row['total']))
            add_history("データ復元完了", 'system')
            flash('データベースの復元が完了しました。', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'ファイル処理中にエラーが発生: {e}', 'error')
            return redirect(request.url)

    return render_template('admin_restore.html')


@app.route('/admin/visuals')
def admin_visuals():
    """利用状況を可視化（排出成功のみカウント）"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # 有効データ開始日時（テストデータを除外）: 2026/1/22 19:20以降のみカウント
    valid_start_date = datetime(2026, 1, 22, 19, 20, 0)

    with get_connection() as conn:
        # 'success' タイプのみ取得（カードタッチ＋排出成功）、1/21以降のみ
        logs = db.fetchall(conn, "SELECT txt, created_at FROM history WHERE type = ? AND created_at >= ? ORDER BY created_at DESC", ('success', valid_start_date.strftime("%Y-%m-%d %H:%M:%S")))

    timestamps = []
    for log in logs:
        ts = log['created_at']
        if isinstance(ts, str):
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                timestamps.append(dt)
            except (ValueError, TypeError):
                continue
        elif isinstance(ts, datetime):
            timestamps.append(ts)

    # 日付リストを取得（プルダウン用）
    available_dates = sorted(set(dt.strftime("%Y-%m-%d") for dt in timestamps))
    
    # 日付ごとの時間別カウント
    hourly_by_date = {}
    for date in available_dates:
        hourly_by_date[date] = {h: 0 for h in range(24)}
    for dt in timestamps:
        date = dt.strftime("%Y-%m-%d")
        hourly_by_date[date][dt.hour] += 1
    
    # 全期間の時間別カウント（0-23時）
    hourly_counts_all = {h: 0 for h in range(24)}
    for dt in timestamps:
        hourly_counts_all[dt.hour] += 1

    # 日別カウント
    daily_counts = {}
    for dt in timestamps:
        day = dt.strftime("%Y-%m-%d")
        daily_counts[day] = daily_counts.get(day, 0) + 1

    # 曜日別カウント（月=0, 日=6）
    weekly_counts = {i: 0 for i in range(7)}
    for dt in timestamps:
        weekly_counts[dt.weekday()] += 1

    # 曜日ラベル
    weekday_names = ['月', '火', '水', '木', '金', '土', '日']

    # chart_dataオブジェクトを構築
    chart_data = {
        'hourly_labels': [f"{h}時" for h in range(24)],
        'hourly_data': [hourly_counts_all[h] for h in range(24)],
        'hourly_by_date': {date: [hourly_by_date[date][h] for h in range(24)] for date in available_dates},
        'available_dates': available_dates,
        'daily_labels': sorted(daily_counts.keys())[-14:] if daily_counts else [],  # 直近14日
        'daily_data': [daily_counts.get(d, 0) for d in (sorted(daily_counts.keys())[-14:] if daily_counts else [])],
        'weekly_labels': weekday_names,
        'weekly_data': [weekly_counts[i] for i in range(7)]
    }

    return render_template("admin_visuals.html", chart_data=chart_data, total_count=len(timestamps))


# ========================================
# API エンドポイント
# ========================================
@app.route('/api/health', methods=['GET'])
def api_health():
    """子機からの親機探知用ヘルスチェックエンドポイント"""
    return jsonify({'status': 'ok', 'server': 'oiteru'})


@app.route('/api/reader_status', methods=['GET'])
def api_reader_status():
    """
    NFCリーダーの状態を確認するエンドポイント
    子機からのハートビートで状態が報告されます。
    """
    try:
        with get_connection() as conn:
            # 最近アクティブな子機（過去60秒以内）を取得
            if db.db_type == 'mysql':
                query = '''
                    SELECT name, last_seen, stock, connect,
                           TIMESTAMPDIFF(SECOND, last_seen, NOW()) as seconds_ago
                    FROM units
                    WHERE last_seen IS NOT NULL 
                      AND TIMESTAMPDIFF(SECOND, last_seen, NOW()) < 60
                    ORDER BY last_seen DESC
                '''
            else:
                query = '''
                    SELECT name, last_seen, stock, connect,
                           (julianday('now') - julianday(last_seen)) * 86400.0 as seconds_ago
                    FROM units
                    WHERE last_seen IS NOT NULL 
                      AND (julianday('now') - julianday(last_seen)) * 86400.0 < 60
                    ORDER BY last_seen DESC
                '''
            
            rows = db.fetchall(conn, query)
        
        active_units = []
        for row in rows:
            active_units.append({
                "unit_name": row['name'],
                "last_seen": row['last_seen'],
                "stock": row['stock'],
                "connected": bool(row['connect']),
                "seconds_ago": round(row['seconds_ago'], 1),
                "status": "online"
            })
        
        if active_units:
            return jsonify({
                "connected": True,
                "active_units": active_units,
                "message": f"{len(active_units)}台の子機がオンライン"
            })
        else:
            return jsonify({
                "connected": False,
                "active_units": [],
                "error": "オンラインの子機が見つかりません"
            }), 503
            
    except Exception as e:
        print(f"リーダーステータス取得エラー: {e}")
        return jsonify({
            "connected": False,
            "error": f"ステータス取得失敗: {str(e)}"
        }), 500


@app.route('/api/local_nfc_reader', methods=['GET'])
def api_local_nfc_reader():
    """
    親機PCに接続されたNFCリーダーを検出
    """
    try:
        import nfc
        clf = nfc.ContactlessFrontend('usb')
        if clf:
            device_info = str(clf)
            clf.close()
            return jsonify({
                "connected": True,
                "device": device_info,
                "message": "NFCリーダーが接続されています"
            })
        else:
            return jsonify({
                "connected": False,
                "error": "NFCリーダーが見つかりません"
            }), 404
    except Exception as e:
        return jsonify({
            "connected": False,
            "error": str(e)
        }), 404


@app.route('/api/read_card', methods=['GET'])
def api_read_card():
    """
    NFCカードを読み取ってカードIDを返す
    タイムアウト: 10秒
    """
    try:
        import nfc
        clf = nfc.ContactlessFrontend('usb')
        if not clf:
            return jsonify({
                "success": False,
                "error": "NFCリーダーが見つかりません"
            }), 404
        
        card_id = None
        
        def on_connect(tag):
            nonlocal card_id
            try:
                # FeliCa (学生証など)
                if hasattr(tag, 'idm'):
                    card_id = tag.idm.hex().upper()
                    return True
                # NFC-A/B (MIFARE等)
                if hasattr(tag, 'identifier'):
                    card_id = tag.identifier.hex().upper()
                    return True
            except Exception as e:
                app.logger.error(f"カード読み取りエラー: {e}")
            return True
        
        # 10秒間待機してカードを読み取り
        clf.connect(rdwr={'on-connect': on_connect}, terminate=lambda: card_id is not None)
        clf.close()
        
        if card_id:
            return jsonify({
                "success": True,
                "card_id": card_id
            })
        else:
            return jsonify({
                "success": False,
                "error": "カードが読み取れませんでした"
            }), 408
            
    except Exception as e:
        app.logger.error(f"NFCカード読み取りエラー: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/unregistered_units', methods=['GET'])
def api_unregistered_units():
    """未登録子機の一覧を取得"""
    auth_error = require_admin_api()
    if auth_error:
        return auth_error

    now = datetime.now()
    units = []
    for name, info in unregistered_units.items():
        # 最終通信からの秒数を計算
        try:
            last_seen_dt = datetime.strptime(info['last_seen'], "%Y-%m-%d %H:%M:%S")
            seconds_ago = (now - last_seen_dt).total_seconds()
        except:
            seconds_ago = 9999
        
        units.append({
            'name': name,
            'ip_address': info.get('ip_address', '不明'),
            'first_seen': info.get('first_seen', ''),
            'last_seen': info.get('last_seen', ''),
            'seconds_ago': round(seconds_ago, 1),
            'heartbeat_count': info.get('heartbeat_count', 0),
        })
    
    return jsonify({
        'success': len(units) > 0,
        'count': len(units),
        'units': units
    })


@app.route('/api/register_unit', methods=['POST'])
def api_register_unit():
    """未登録子機を正式登録"""
    auth_error = require_admin_api()
    if auth_error:
        return auth_error

    data = request.json
    unit_name = data.get('name')
    
    if not unit_name:
        return jsonify({'success': False, 'error': '子機名が指定されていません'}), 400
    
    if unit_name not in unregistered_units:
        return jsonify({'success': False, 'error': '未登録子機が見つかりません'}), 404
    
    pending_unit = unregistered_units[unit_name]
    
    try:
        with get_connection() as conn:
            db.execute(conn,
                "INSERT INTO units (name, password, stock, connect, available, ip_address) VALUES (?, ?, ?, 1, 1, ?)",
                (unit_name, pending_unit['password_hash'], server_settings.get('auto_register_stock', 5), pending_unit.get('ip_address', ''))
            )
        del unregistered_units[unit_name]
        add_history(f"子機登録: {unit_name}", 'system')
        return jsonify({'success': True, 'message': f'子機「{unit_name}」を登録しました'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/unit/<int:uid>/toggle_available', methods=['POST'])
def api_toggle_unit_available(uid):
    """子機の利用可能状態をトグルする（名前は更新しない）"""
    if not session.get("admin_logged_in"):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        with get_connection() as conn:
            unit = db.fetchone(conn, "SELECT available FROM units WHERE id = ?", (uid,))
            if not unit:
                return jsonify({'success': False, 'error': 'Unit not found'}), 404
            
            new_available = 0 if unit['available'] == 1 else 1
            db.execute(conn, "UPDATE units SET available = ? WHERE id = ?", (new_available, uid))
        
        add_history(f"子機(ID:{uid})の利用可能状態を{'有効' if new_available else '無効'}に変更", 'system')
        return jsonify({'success': True, 'available': new_available})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/<int:uid>/toggle_allow', methods=['POST'])
def api_toggle_user_allow(uid):
    """利用者の許可状態をトグルする"""
    if not session.get("admin_logged_in"):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        with get_connection() as conn:
            user = db.fetchone(conn, "SELECT allow FROM users WHERE id = ?", (uid,))
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            new_allow = 0 if user['allow'] == 1 else 1
            db.execute(conn, "UPDATE users SET allow = ? WHERE id = ?", (new_allow, uid))
        
        add_history(f"利用者(ID:{uid})の許可状態を{'許可' if new_allow else '不許可'}に変更", 'system')
        return jsonify({'success': True, 'allow': new_allow})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users', methods=['GET'])
def api_get_users():
    auth_error = require_admin_api()
    if auth_error:
        return auth_error

    with get_connection() as conn:
        users = db.fetchall(conn, 'SELECT * FROM users')
    return jsonify([dict(row) for row in users])


@app.route('/api/users/<string:card_id>', methods=['GET'])
def api_get_user_by_card(card_id):
    auth_error = require_admin_api()
    if auth_error:
        return auth_error

    with get_connection() as conn:
        user = db.fetchone(conn, 'SELECT * FROM users WHERE card_id = ?', (card_id,))
    if user:
        return jsonify(dict(user))
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/log', methods=['POST'])
def api_add_log():
    """子機からのログを受け取る"""
    data = request.json or {}
    message = data.get('message')
    unit_name = data.get('unit_name', '不明な子機')
    unit_password = data.get('unit_password')
    unit_token = data.get('unit_token')

    with get_connection() as conn:
        unit = get_authenticated_unit(conn, unit_name, unit_password, unit_token)
    if not unit:
        return jsonify({'success': False, 'error': 'Invalid unit credentials'}), 401

    if message:
        log_entry = f"[{unit_name}] {message}"
        add_history(log_entry)
        
        # unit_logsにも保存（最新100件まで）
        if unit_name not in unit_logs:
            unit_logs[unit_name] = []
        unit_logs[unit_name].append({
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message': message
        })
        # 最新100件に制限
        if len(unit_logs[unit_name]) > 100:
            unit_logs[unit_name] = unit_logs[unit_name][-100:]
        
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'error': 'Message not provided'}), 400


@app.route('/api/unit/<unit_name>/logs', methods=['GET'])
def api_get_unit_logs(unit_name):
    """子機のログを取得"""
    auth_error = require_admin_api()
    if auth_error:
        return auth_error

    logs = unit_logs.get(unit_name, [])
    return jsonify({'logs': logs, 'count': len(logs)})


@app.route('/api/record_usage', methods=['POST'])
def api_record_usage():
    """
    子機からの利用認可API（在庫減算はまだ行わない）
    認可成功後、子機は /api/dispense_result で物理排出結果を通知する
    """
    data = request.json or {}
    card_id = data.get('card_id')
    unit_name = data.get('unit_name')
    unit_password = data.get('unit_password')
    unit_token = data.get('unit_token')

    if not all([card_id, unit_name]) or not (unit_password or unit_token):
        return jsonify({'error': 'Card ID, Unit Name and unit credentials are required'}), 400

    event_id = generate_event_id()

    try:
        with get_connection() as conn:
            create_dispense_event(conn, event_id, unit_name, card_id, 'requested')

            # --- 1. 子機の在庫と利用可能状態を確認 ---
            unit = get_authenticated_unit(conn, unit_name, unit_password, unit_token)
            if not unit:
                update_dispense_event(conn, event_id, 'failed', 'INVALID_UNIT_CREDENTIALS')
                return jsonify({'error': 'Invalid unit credentials', 'event_id': event_id}), 401
            
            if unit['stock'] <= 0 or unit['available'] == 0:
                message = f"[{unit_name}] 在庫不足のため利用不可 (カードID: {card_id})"
                add_history(message, 'usage')
                update_dispense_event(conn, event_id, 'failed', 'UNIT_STOCK_EMPTY')
                return jsonify({'error': 'Unit has no stock remaining', 'event_id': event_id}), 400

            # --- 2. 利用者の確認（自動登録モード対応） ---
            user = db.fetchone(conn, "SELECT * FROM users WHERE card_id = ?", (card_id,))
            
            if not user:
                # デバッグログ
                print(f"[DEBUG] 未登録カード: {card_id}, auto_register_mode={server_settings['auto_register_mode']}")
                
                # 自動登録モードの場合は新規登録
                if server_settings['auto_register_mode']:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    today = datetime.now().strftime("%Y-%m-%d")
                    initial_stock = server_settings['auto_register_stock']
                    print(f"[DEBUG] 自動登録実行: card_id={card_id}, initial_stock={initial_stock}")
                    db.execute(conn, 
                        "INSERT INTO users (card_id, entry, stock, allow, last_reset_date) VALUES (?, ?, ?, 1, ?)", 
                        (card_id, now, initial_stock, today))
                    message = f"[{unit_name}] 自動登録 (カードID: {card_id}, 初期残数: {initial_stock})"
                    add_history(message, 'system')
                    # 新しく登録したユーザーを取得
                    user = db.fetchone(conn, "SELECT * FROM users WHERE card_id = ?", (card_id,))
                else:
                    message = f"[{unit_name}] 未登録カード (カードID: {card_id})"
                    add_history(message, 'usage')
                    update_dispense_event(conn, event_id, 'failed', 'USER_NOT_FOUND')
                    return jsonify({'error': 'User not found', 'auto_register': False, 'event_id': event_id}), 404
            
            # 利用不許可のユーザー
            if user.get('allow', 1) == 0:
                message = f"[{unit_name}] 利用不許可 (カードID: {card_id})"
                add_history(message, 'usage')
                update_dispense_event(conn, event_id, 'failed', 'USER_DENIED')
                return jsonify({'error': 'User is not allowed', 'event_id': event_id}), 403
            
            # --- 期間が変わった場合、stockを自動リセット ---
            period = server_settings['limit_period']
            user = check_and_reset_user_stock(conn, user, period)
            
            # 残数チェック
            if user['stock'] <= 0:
                message = f"[{unit_name}] 残数不足 (カードID: {card_id})"
                add_history(message, 'usage')
                update_dispense_event(conn, event_id, 'failed', 'USER_STOCK_EMPTY')
                return jsonify({'error': 'User has no stock remaining', 'event_id': event_id}), 400

            # --- 期間内の利用上限チェック ---
            period = server_settings['limit_period']
            usage_limit = server_settings['usage_limit']
            usage_count = get_usage_count_in_period(conn, card_id, period)
            
            if usage_count >= usage_limit:
                period_name = get_period_display_name(period)
                message = f"[{unit_name}] {period_name}の上限({usage_limit}個)に達しています (カードID: {card_id})"
                add_history(message, 'usage')
                update_dispense_event(conn, event_id, 'failed', 'PERIOD_LIMIT_EXCEEDED')
                return jsonify({
                    'error': 'Period limit exceeded',
                    'message': f'{period_name}あたりの取得上限（{usage_limit}個）に達しました',
                    'usage_count': usage_count,
                    'usage_limit': usage_limit,
                    'period': period,
                    'event_id': event_id,
                }), 429

            update_dispense_event(conn, event_id, 'authorized')
            add_history(f"[{unit_name}] 排出認可 (event_id: {event_id}, カードID: {card_id})", 'usage')

            return jsonify({
                'success': True, 
                'authorized': True,
                'message': 'Dispense authorized',
                'event_id': event_id,
            })

    except Exception as e:
        print(f"!! 利用認可エラー: {e}")
        return jsonify({'error': f'Database error: {e}'}), 500


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    return False


@app.route('/api/dispense_result', methods=['POST'])
def api_dispense_result():
    """子機からの物理排出結果を受け取り、在庫を確定更新する"""
    data = request.json or {}
    event_id = data.get('event_id')
    unit_name = data.get('unit_name')
    unit_password = data.get('unit_password')
    unit_token = data.get('unit_token')
    dispense_success = parse_bool(data.get('success'))
    error_code = data.get('error_code')

    if not all([event_id, unit_name]) or not (unit_password or unit_token):
        return jsonify({'error': 'Event ID, Unit Name and unit credentials are required'}), 400

    try:
        with get_connection() as conn:
            unit = get_authenticated_unit(conn, unit_name, unit_password, unit_token)
            if not unit:
                return jsonify({'error': 'Invalid unit credentials'}), 401

            event = db.fetchone(conn, "SELECT * FROM dispense_events WHERE event_id = ?", (event_id,))
            if not event:
                return jsonify({'error': 'Event not found'}), 404
            if event['unit_name'] != unit_name:
                return jsonify({'error': 'Event does not belong to unit'}), 403

            current_status = event['status']
            if current_status == 'recorded':
                return jsonify({'success': True, 'recorded': True, 'idempotent': True, 'event_id': event_id})
            if current_status == 'failed':
                return jsonify({
                    'success': False,
                    'recorded': False,
                    'idempotent': True,
                    'event_id': event_id,
                    'error_code': event.get('error_code'),
                })

            if not dispense_success:
                fail_code = error_code or 'DISPENSE_FAILED'
                update_dispense_event(conn, event_id, 'failed', fail_code)
                add_history(
                    f"[{unit_name}] 排出失敗 (event_id: {event_id}, カードID: {event['card_id']}, code: {fail_code})",
                    'usage',
                )
                return jsonify({
                    'success': False,
                    'recorded': False,
                    'event_id': event_id,
                    'error_code': fail_code,
                })

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            transitioned = db.update(
                conn,
                "UPDATE dispense_events SET status = ?, updated_at = ? WHERE event_id = ? AND status IN ('authorized', 'requested')",
                ('dispensing', now, event_id),
            )
            if transitioned == 0:
                latest = db.fetchone(conn, "SELECT status, error_code FROM dispense_events WHERE event_id = ?", (event_id,))
                if latest and latest['status'] == 'recorded':
                    return jsonify({'success': True, 'recorded': True, 'idempotent': True, 'event_id': event_id})
                if latest and latest['status'] == 'failed':
                    return jsonify({
                        'success': False,
                        'recorded': False,
                        'idempotent': True,
                        'event_id': event_id,
                        'error_code': latest.get('error_code'),
                    })
                return jsonify({'error': f"Event is not processable (status: {latest['status'] if latest else 'unknown'})"}), 409

            latest_unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
            user = db.fetchone(conn, "SELECT * FROM users WHERE card_id = ?", (event['card_id'],))

            if not user:
                update_dispense_event(conn, event_id, 'failed', 'USER_NOT_FOUND')
                return jsonify({'error': 'User not found'}), 404

            if latest_unit['stock'] <= 0 or latest_unit['available'] == 0:
                update_dispense_event(conn, event_id, 'failed', 'UNIT_STOCK_EMPTY')
                return jsonify({'error': 'Unit has no stock remaining'}), 400

            if user.get('allow', 1) == 0:
                update_dispense_event(conn, event_id, 'failed', 'USER_DENIED')
                return jsonify({'error': 'User is not allowed'}), 403

            period = server_settings['limit_period']
            user = check_and_reset_user_stock(conn, user, period)

            if user['stock'] <= 0:
                update_dispense_event(conn, event_id, 'failed', 'USER_STOCK_EMPTY')
                return jsonify({'error': 'User has no stock remaining'}), 400

            usage_limit = server_settings['usage_limit']
            usage_count = get_usage_count_in_period(conn, event['card_id'], period)
            if usage_count >= usage_limit:
                update_dispense_event(conn, event_id, 'failed', 'PERIOD_LIMIT_EXCEEDED')
                period_name = get_period_display_name(period)
                return jsonify({
                    'error': 'Period limit exceeded',
                    'message': f'{period_name}あたりの取得上限（{usage_limit}個）に達しました',
                    'usage_count': usage_count,
                    'usage_limit': usage_limit,
                    'period': period,
                }), 429

            new_user_stock = user['stock'] - 1
            new_total = user['total'] + 1
            db.execute(conn, "UPDATE users SET stock = ?, total = ? WHERE card_id = ?", (new_user_stock, new_total, event['card_id']))

            new_unit_stock = latest_unit['stock'] - 1
            db.execute(conn, "UPDATE units SET stock = ? WHERE name = ?", (new_unit_stock, unit_name))

            if new_unit_stock <= 0:
                db.execute(conn, "UPDATE units SET available = 0 WHERE name = ?", (unit_name,))
                add_history(f"[{unit_name}] 在庫0のため排出停止", 'system')

            update_dispense_event(conn, event_id, 'recorded')
            add_history(
                f"[{unit_name}] 利用成功 (event_id: {event_id}, カードID: {event['card_id']}, 残数: {new_user_stock})",
                'success',
            )

            return jsonify({
                'success': True,
                'recorded': True,
                'event_id': event_id,
                'user_stock': new_user_stock,
                'unit_stock': new_unit_stock,
            })
    except Exception as e:
        print(f"!! 排出結果更新エラー: {e}")
        return jsonify({'error': f'Database error: {e}'}), 500


@app.route('/api/unit/heartbeat', methods=['POST'])
def api_unit_heartbeat():
    """子機からの生存確認を受け取る"""
    data = request.json
    
    # デバッグ: 受信データをログ出力
    print(f"[DEBUG] Heartbeat received: {data}")
    
    if data is None:
        print("[DEBUG] No JSON data received")
        return jsonify({'error': 'No JSON data received'}), 400
    
    unit_name = data.get('unit_name') or data.get('name')  # 両方のキーに対応
    unit_password = data.get('unit_password') or data.get('password')
    ip_address = request.remote_addr
    
    # 子機から送られた設定情報を保存
    unit_config = data.get('config', {})
    if unit_config and unit_name:
        unit_configs[unit_name] = {
            'config': unit_config,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip_address': ip_address
        }
    
    if not all([unit_name, unit_password]):
        print(f"[DEBUG] Missing fields - unit_name: {unit_name}, password: {'***' if unit_password else None}")
        return jsonify({'error': 'Unit name and password required'}), 400
    
    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
        
        if unit:
            if not verify_secret(unit['password'], unit_password):
                return jsonify({'error': 'Invalid password'}), 401
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute(conn, 
                "UPDATE units SET connect = 1, last_seen = ?, ip_address = ? WHERE name = ?",
                (now, ip_address, unit_name))
            
            # レスポンスを構築
            response_data = {
                'success': True,
                'stock': unit['stock'],
                'available': unit['available'],
                'auto_register_mode': server_settings['auto_register_mode'],
                'auto_register_stock': server_settings['auto_register_stock'],
                'usage_limit': server_settings['usage_limit'],
                'limit_period': server_settings['limit_period'],
                'settings_version': settings_version,
                'unit_api_token': unit_session_tokens.get(unit_name) or issue_unit_session_token(unit_name),
            }
            
            # 保留中の設定変更があれば送信
            if unit_name in pending_unit_config_updates:
                response_data['config_update'] = pending_unit_config_updates[unit_name]
                del pending_unit_config_updates[unit_name]  # 送信したら削除
                print(f"[DEBUG] Sending config update to {unit_name}")
            
            return jsonify(response_data)
        else:
            # 未登録子機として一時保存
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if unit_name not in unregistered_units:
                unregistered_units[unit_name] = {
                    'password_hash': hash_secret(unit_password),
                    'ip_address': ip_address,
                    'first_seen': now,
                    'last_seen': now,
                    'heartbeat_count': 1
                }
            else:
                unregistered_units[unit_name]['last_seen'] = now
                unregistered_units[unit_name]['heartbeat_count'] += 1
                unregistered_units[unit_name]['ip_address'] = ip_address
            
            return jsonify({'error': 'Unit not registered', 'pending': True}), 404


@app.route('/api/unit/register_pending/<string:unit_name>', methods=['POST'])
def api_register_pending_unit(unit_name):
    """未登録子機を正式登録"""
    if not session.get("admin_logged_in"):
        return jsonify({'error': 'Unauthorized'}), 401
    
    if unit_name not in unregistered_units:
        return jsonify({'error': 'Pending unit not found'}), 404
    
    pending_unit = unregistered_units[unit_name]
    
    try:
        with get_connection() as conn:
            db.execute(conn,
                "INSERT INTO units (name, password, stock, connect, ip_address) VALUES (?, ?, 0, 1, ?)",
                (unit_name, pending_unit['password_hash'], pending_unit['ip_address']))
        
        del unregistered_units[unit_name]
        add_history(f"子機を登録 ({unit_name})", 'system')
        
        return jsonify({'success': True, 'message': f'{unit_name} registered'})
    except DatabaseError:
        return jsonify({'error': 'Unit name already exists'}), 400


@app.route('/api/unit/<string:unit_name>/config', methods=['GET'])
def api_get_unit_config(unit_name):
    """子機の設定情報を取得"""
    if not session.get("admin_logged_in"):
        return jsonify({'error': 'Unauthorized'}), 401
    
    if unit_name in unit_configs:
        return jsonify({
            'success': True,
            'unit_name': unit_name,
            **unit_configs[unit_name]
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Unit config not found (子機がまだハートビートを送信していません)'
        }), 404


@app.route('/api/unit/<string:unit_name>/config', methods=['POST'])
def api_update_unit_config(unit_name):
    """子機の設定を更新し、即座に子機に送信"""
    if not session.get("admin_logged_in"):
        return jsonify({'error': 'Unauthorized'}), 401
    
    new_config = request.json
    if not new_config:
        return jsonify({'error': 'No config provided'}), 400
    
    # 保留中の設定変更として保存（heartbeatのバックアップとして）
    pending_unit_config_updates[unit_name] = new_config
    
    # 親機側のunit_configsも即座に更新（画面表示用）
    if unit_name in unit_configs:
        unit_configs[unit_name]['config'] = new_config
        unit_configs[unit_name]['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        unit_configs[unit_name] = {
            'config': new_config,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip_address': None
        }
    
    # 子機のIPアドレスを取得
    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
    
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    
    unit_ip = unit.get('ip_address')
    push_headers = get_push_headers(unit_name)
    
    # 子機に即座に設定を送信
    push_success = False
    push_error = None
    
    if unit_ip and unit['connect'] == 1 and push_headers:
        try:
            # 子機のポート番号を推測（デフォルト5001）
            unit_port = 5001
            unit_url = f"http://{unit_ip}:{unit_port}/api/config/update"
            
            # タイムアウトを短く設定（子機が応答しない場合に備えて）
            response = requests.post(
                unit_url,
                json={'config': new_config},
                headers=push_headers,
                timeout=5
            )
            
            if response.status_code == 200:
                push_success = True
                add_history(f"子機({unit_name})に設定を即座に送信しました", 'system')
                # 成功したら保留中の設定から削除
                if unit_name in pending_unit_config_updates:
                    del pending_unit_config_updates[unit_name]
            else:
                push_error = f"子機が設定を受け付けませんでした (status: {response.status_code})"
                
        except requests.exceptions.Timeout:
            push_error = "子機への接続がタイムアウトしました"
        except requests.exceptions.ConnectionError:
            push_error = "子機に接続できませんでした"
        except Exception as e:
            push_error = f"エラー: {str(e)}"
    else:
        push_error = "子機がオフライン、または認証トークン未取得です"
    
    if not push_success:
        add_history(f"子機({unit_name})の設定変更を予約（次回heartbeatで同期）", 'system')
    
    return jsonify({
        'success': True,
        'push_success': push_success,
        'push_error': push_error,
        'message': '設定を即座に送信しました' if push_success else f'設定変更を予約しました（{push_error}）。次回ハートビートで子機に同期されます。',
        'pending_config': new_config
    })


@app.route('/api/unit/<unit_name>/command', methods=['POST'])
def api_send_unit_command(unit_name):
    """子機にコマンドを送信（デバッグ用）"""
    if not session.get("admin_logged_in"):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'Command required'}), 400
    
    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
    
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404
    
    unit_ip = unit.get('ip_address')
    push_headers = get_push_headers(unit_name)
    
    if not unit_ip or unit['connect'] == 0 or not push_headers:
        return jsonify({'error': 'Unit is offline or session token unavailable'}), 503
    
    try:
        unit_port = 5001
        unit_url = f"http://{unit_ip}:{unit_port}/api/command"
        
        response = requests.post(
            unit_url,
            json={'command': command},
            headers=push_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            add_history(f"子機({unit_name})にコマンド送信: {command}", 'system')
            return jsonify({
                'success': True,
                'result': result,
                'message': 'コマンドを送信しました'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'子機がエラーを返しました (status: {response.status_code})'
            })
            
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'タイムアウト'}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': '接続エラー'}), 503
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """現在の設定を取得（子機からの同期用）"""
    return jsonify({
        'auto_register_mode': server_settings['auto_register_mode'],
        'auto_register_stock': server_settings['auto_register_stock'],
        'usage_limit': server_settings['usage_limit'],
        'limit_period': server_settings['limit_period'],
        'server_name': SERVER_NAME,
        'server_location': SERVER_LOCATION,
        'db_type': db.db_type,
        'settings_version': settings_version
    })


@app.route('/api/settings', methods=['POST'])
def api_update_settings():
    """設定を更新（管理画面から）"""
    if not session.get("admin_logged_in"):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    
    if 'auto_register_mode' in data:
        server_settings['auto_register_mode'] = bool(data['auto_register_mode'])
    if 'auto_register_stock' in data:
        server_settings['auto_register_stock'] = int(data['auto_register_stock'])
    if 'usage_limit' in data:
        server_settings['usage_limit'] = int(data['usage_limit'])
    if 'limit_period' in data:
        server_settings['limit_period'] = data['limit_period']
    
    if save_settings_to_db():
        add_history(f"設定を変更 (自動登録: {'有効' if server_settings['auto_register_mode'] else '無効'}, 初期残数: {server_settings['auto_register_stock']})", 'system')
        return jsonify({
            'success': True,
            'settings': server_settings,
            'settings_version': settings_version
        })
    else:
        return jsonify({'error': 'Failed to save settings'}), 500


# ========================================
# 管理画面: 設定ページ
# ========================================
@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """システム設定ページ"""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    
    if request.method == 'POST':
        # フォームから設定を更新
        server_settings['auto_register_mode'] = request.form.get('auto_register_mode') == 'on'
        server_settings['auto_register_stock'] = int(request.form.get('auto_register_stock', 2))
        server_settings['usage_limit'] = int(request.form.get('usage_limit', 2))
        server_settings['limit_period'] = request.form.get('limit_period', 'day')
        
        print(f"[DEBUG] 設定を更新: auto_register_mode={server_settings['auto_register_mode']}")
        
        if save_settings_to_db():
            add_history(f"設定を変更 (自動登録: {'有効' if server_settings['auto_register_mode'] else '無効'})", 'system')
            flash('設定を保存しました。', 'success')
        else:
            flash('設定の保存に失敗しました。', 'error')
        
        return redirect(url_for('admin_settings'))
    
    return render_template('admin_settings.html', 
                          settings=server_settings,
                          settings_version=settings_version)


# ========================================
# メイン
# ========================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("OITELU 親機/従親機 を起動しています...")
    print("="*60)

    if db.db_type == 'sqlite':
        print("警告: server.py + SQLite は legacy 互換経路です。")
        print("標準構成は db_server.py + MySQL を使用してください。")
    try:
        validate_runtime_security()
    except RuntimeError as error:
        print(str(error))
        raise

    print("\nデータベースを初期化中...")
    init_db()
    migrate_db()
    ensure_admin_password()
    
    print("設定をDBから読み込み中...")
    load_settings_from_db()
    
    print(f"\n設定:")
    print(f"  データベース: {db.db_type.upper()}")
    print(f"  自動登録モード: {'有効' if server_settings['auto_register_mode'] else '無効'}")
    if server_settings['auto_register_mode']:
        print(f"  自動登録時の初期残数: {server_settings['auto_register_stock']}")
    
    print("\n子機向けブロードキャストスレッドを起動中...")
    heartbeat_thread = threading.Thread(target=broadcast_server_info, daemon=True)
    heartbeat_thread.start()
    
    print("\n" + "="*60)
    print("OITELU 親機/従親機の起動が完了しました！")
    print("Webブラウザで http://localhost:5000 にアクセスしてください")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
