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
    python server.py

環境変数:
    DB_TYPE=mysql の場合、外部MySQLに接続
    DB_TYPE=sqlite の場合、ローカルSQLiteを使用
"""

import os
import hashlib
import random
import io
import pandas as pd
import traceback
import re
import json
import socket
import subprocess
import threading
import time
import requests
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, session, flash, g, send_file
)
from db_adapter import db, get_connection, DatabaseError

# --- Flaskアプリケーションの初期化 ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'oiteru_secret_key_2025_final'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oiteru.sqlite3')

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
    
    # historyテーブルから成功した利用回数をカウント
    # カードIDを含む成功ログを検索
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


# --- パスワード確認 ---
def check_password(entered_password: str) -> bool:
    """管理者パスワードを確認する"""
    hashed = hashlib.sha256(entered_password.encode()).hexdigest()
    with get_connection() as conn:
        info = db.fetchone(conn, "SELECT pass FROM info WHERE id = 1")
    return info and info['pass'] == hashed


# --- データベース初期化 ---
def init_db():
    """データベースのテーブルを初期化する"""
    if db.db_type == 'mysql':
        print("MySQLモード: docker/init_mysql.sqlで初期化してください")
        # settingsテーブルの作成を試みる
        try:
            with get_connection() as conn:
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
        except Exception as e:
            print(f"settingsテーブル作成エラー: {e}")
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
            
            # infoテーブル
            db.execute(conn, '''
                CREATE TABLE info (
                    id INTEGER PRIMARY KEY,
                    pass TEXT NOT NULL
                )
            ''')
            
            # デフォルトの管理者パスワード
            default_password = hashlib.sha256('admin'.encode()).hexdigest()
            db.execute(conn, "INSERT INTO info (id, pass) VALUES (?, ?)", (1, default_password))
            
            print("データベースの初期化が完了しました。")
            print("デフォルト管理者パスワード: admin")


# --- DBマイグレーション ---
def migrate_db():
    """データベーススキーマのマイグレーション"""
    try:
        with get_connection() as conn:
            # settingsテーブルに新しいカラムを追加（存在しない場合）
            if db.db_type == 'mysql':
                # MySQLの場合
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
        entered_pass = request.form.get("password", "")
        if check_password(entered_pass):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
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
                    (name, password, stock, stock))
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
            'password': info.get('password', '')
        })
    
    return jsonify({
        'success': len(units) > 0,
        'count': len(units),
        'units': units
    })


@app.route('/api/register_unit', methods=['POST'])
def api_register_unit():
    """未登録子機を正式登録"""
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
                (unit_name, pending_unit['password'], server_settings.get('auto_register_stock', 5), pending_unit.get('ip_address', ''))
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
    with get_connection() as conn:
        users = db.fetchall(conn, 'SELECT * FROM users')
    return jsonify([dict(row) for row in users])


@app.route('/api/users/<string:card_id>', methods=['GET'])
def api_get_user_by_card(card_id):
    with get_connection() as conn:
        user = db.fetchone(conn, 'SELECT * FROM users WHERE card_id = ?', (card_id,))
    if user:
        return jsonify(dict(user))
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/log', methods=['POST'])
def api_add_log():
    """子機からのログを受け取る"""
    data = request.json
    message = data.get('message')
    unit_name = data.get('unit_name', '不明な子機')
    if message:
        log_entry = f"[{unit_name}] {message}"
        add_history(log_entry)
        return jsonify({'success': True}), 200
    return jsonify({'success': False, 'error': 'Message not provided'}), 400


@app.route('/api/record_usage', methods=['POST'])
def api_record_usage():
    """
    子機からの利用記録API
    自動登録モードが有効な場合、未登録カードも自動登録してから利用記録を行う
    """
    data = request.json
    card_id = data.get('card_id')
    unit_name = data.get('unit_name')

    if not all([card_id, unit_name]):
        return jsonify({'error': 'Card ID and Unit Name are required'}), 400

    try:
        with get_connection() as conn:
            # --- 1. 子機の在庫と利用可能状態を確認 ---
            unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
            if not unit:
                return jsonify({'error': 'Unit not found'}), 404
            
            if unit['stock'] <= 0 or unit['available'] == 0:
                message = f"[{unit_name}] 在庫不足のため利用不可 (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({'error': 'Unit has no stock remaining'}), 400

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
                    return jsonify({'error': 'User not found', 'auto_register': False}), 404
            
            # 利用不許可のユーザー
            if user.get('allow', 1) == 0:
                message = f"[{unit_name}] 利用不許可 (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({'error': 'User is not allowed'}), 403
            
            # --- 期間が変わった場合、stockを自動リセット ---
            period = server_settings['limit_period']
            user = check_and_reset_user_stock(conn, user, period)
            
            # 残数チェック
            if user['stock'] <= 0:
                message = f"[{unit_name}] 残数不足 (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({'error': 'User has no stock remaining'}), 400

            # --- 期間内の利用上限チェック ---
            period = server_settings['limit_period']
            usage_limit = server_settings['usage_limit']
            usage_count = get_usage_count_in_period(conn, card_id, period)
            
            if usage_count >= usage_limit:
                period_name = get_period_display_name(period)
                message = f"[{unit_name}] {period_name}の上限({usage_limit}個)に達しています (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({
                    'error': 'Period limit exceeded',
                    'message': f'{period_name}あたりの取得上限（{usage_limit}個）に達しました',
                    'usage_count': usage_count,
                    'usage_limit': usage_limit,
                    'period': period
                }), 429

            # --- 3. 両方の残数/在庫を更新 ---
            new_user_stock = user['stock'] - 1
            new_total = user['total'] + 1
            db.execute(conn, "UPDATE users SET stock = ?, total = ? WHERE card_id = ?", 
                       (new_user_stock, new_total, card_id))
            
            new_unit_stock = unit['stock'] - 1
            db.execute(conn, "UPDATE units SET stock = ? WHERE name = ?", 
                       (new_unit_stock, unit_name))

            message = f"[{unit_name}] 利用成功 (カードID: {card_id}, 残数: {new_user_stock})"
            add_history(message, 'success')  # 排出成功のみ 'success' タイプで記録

            # 子機の在庫が0になったら利用不可に
            if new_unit_stock <= 0:
                db.execute(conn, "UPDATE units SET available = 0 WHERE name = ?", (unit_name,))
                add_history(f"[{unit_name}] 在庫0のため排出停止", 'system')

            return jsonify({
                'success': True, 
                'message': 'Usage recorded',
                'user_stock': new_user_stock,
                'unit_stock': new_unit_stock
            })

    except Exception as e:
        print(f"!! 在庫更新エラー: {e}")
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
    unit_password = data.get('password')
    ip_address = request.remote_addr
    
    # 子機から送られた設定情報を保存
    unit_config = data.get('config', {})
    if unit_config and unit_name:
        unit_configs[unit_name] = {
            'config': unit_config,
            'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip_address': ip_address
        }
    
    if not all([unit_name, unit_password]):
        print(f"[DEBUG] Missing fields - unit_name: {unit_name}, password: {'***' if unit_password else None}")
        return jsonify({'error': 'Unit name and password required'}), 400
    
    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
        
        if unit:
            if unit['password'] != unit_password:
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
                'settings_version': settings_version
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
                    'password': unit_password,
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
                (unit_name, pending_unit['password'], pending_unit['ip_address']))
        
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
    
    # 子機に即座に設定を送信
    push_success = False
    push_error = None
    
    if unit_ip and unit['connect'] == 1:
        try:
            # 子機のポート番号を推測（デフォルト5001）
            unit_port = 5001
            unit_url = f"http://{unit_ip}:{unit_port}/api/config/update"
            
            # タイムアウトを短く設定（子機が応答しない場合に備えて）
            response = requests.post(
                unit_url,
                json={'config': new_config},
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
        push_error = "子機がオフラインです"
    
    if not push_success:
        add_history(f"子機({unit_name})の設定変更を予約（次回heartbeatで同期）", 'system')
    
    return jsonify({
        'success': True,
        'push_success': push_success,
        'push_error': push_error,
        'message': '設定を即座に送信しました' if push_success else f'設定変更を予約しました（{push_error}）。次回ハートビートで子機に同期されます。',
        'pending_config': new_config
    })


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
    
    print("\nデータベースを初期化中...")
    init_db()
    migrate_db()
    
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
    
    app.run(host='0.0.0.0', port=5000, debug=True)
