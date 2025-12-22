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
    'daily_limit': int(os.getenv('DAILY_LIMIT', '2')),  # 1日あたりの取得上限
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
                server_settings['daily_limit'] = int(settings_row.get('daily_limit', 2))
                settings_version = int(settings_row.get('version', 0))
                print(f"設定をDBから読み込みました (version: {settings_version})")
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
                        daily_limit = ?,
                        version = ?,
                        updated_at = ?
                    WHERE id = 1
                """, (
                    1 if server_settings['auto_register_mode'] else 0,
                    server_settings['auto_register_stock'],
                    server_settings['daily_limit'],
                    settings_version,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            else:
                db.execute(conn, """
                    INSERT INTO settings (id, auto_register_mode, auto_register_stock, daily_limit, version, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?)
                """, (
                    1 if server_settings['auto_register_mode'] else 0,
                    server_settings['auto_register_stock'],
                    server_settings['daily_limit'],
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
                        daily_limit INT DEFAULT 2,
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
                        daily_limit INTEGER DEFAULT 2,
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
    if db.db_type == 'mysql':
        return
    # SQLite用のマイグレーション処理があれば追加


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
        return redirect(url_for("register"))
    
    return render_template("register.html", reader_connected=False)


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
    
    return render_template("usage.html", reader_connected=False)


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
    
    with get_connection() as conn:
        users = db.fetchall(conn, "SELECT * FROM users")
        units = db.fetchall(conn, "SELECT * FROM units")
        history = db.fetchall(conn, "SELECT * FROM history ORDER BY id DESC")
        usage_count_row = db.fetchone(conn, "SELECT COUNT(id) as count FROM history WHERE txt LIKE ?", ('%] 利用%',))
        usage_count = usage_count_row['count'] if usage_count_row else 0

    server_info = {
        'name': SERVER_NAME,
        'location': SERVER_LOCATION,
        'id': SERVER_ID,
        'db_type': db.db_type.upper(),
        'auto_register': server_settings['auto_register_mode'],
        'auto_register_stock': server_settings['auto_register_stock'],
        'daily_limit': server_settings['daily_limit']
    }

    return render_template("admin_dashboard.html", 
                         users=users, 
                         units=units, 
                         history=history, 
                         usage_count=usage_count,
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
            
            name = request.form.get("name")
            stock = request.form.get("stock")
            available = request.form.get("available")
            db.execute(conn,
                "UPDATE units SET name = ?, stock = ?, available = ? WHERE id = ?",
                (name, stock, available, uid)
            )
        add_history(f"子機情報を更新 (ID:{uid})", 'system')
        flash(f"子機(ID:{uid})の情報を更新しました。", "success")
        return redirect(url_for("admin_unit_detail", uid=uid))
    
    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE id = ?", (uid,))
    if not unit:
        flash("指定された子機は見つかりません。", "error")
        return redirect(url_for("admin_units"))
    return render_template("admin_unit_detail.html", unit=unit)


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
                    "INSERT INTO units (name, password, stock) VALUES (?, ?, ?)",
                    (name, password, stock))
            add_history(f"新しい子機を登録 ({name})", 'system')
            flash(f"子機({name})を登録しました。", "success")
            return redirect(url_for("admin_units"))
        except DatabaseError:
            flash("この子機名は既に登録されています。", "warning")
    
    return render_template("admin_new_unit.html")


@app.route("/admin/history")
def admin_history():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    with get_connection() as conn:
        history = db.fetchall(conn, "SELECT * FROM history WHERE type = 'usage' ORDER BY created_at DESC LIMIT 100")
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
    """利用状況を可視化"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    with get_connection() as conn:
        logs = db.fetchall(conn, "SELECT txt, created_at FROM history WHERE type = ? ORDER BY created_at DESC", ('usage',))

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

    hourly_counts = {}
    for dt in timestamps:
        hour = dt.hour
        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

    daily_counts = {}
    for dt in timestamps:
        day = dt.strftime("%Y-%m-%d")
        daily_counts[day] = daily_counts.get(day, 0) + 1

    return render_template("admin_visuals.html", hourly_counts=hourly_counts, daily_counts=daily_counts)


# ========================================
# API エンドポイント
# ========================================
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
                # 自動登録モードの場合は新規登録
                if server_settings['auto_register_mode']:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    initial_stock = server_settings['auto_register_stock']
                    db.execute(conn, 
                        "INSERT INTO users (card_id, entry, stock, allow) VALUES (?, ?, ?, 1)", 
                        (card_id, now, initial_stock))
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
            
            # 残数チェック
            if user['stock'] <= 0:
                message = f"[{unit_name}] 残数不足 (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({'error': 'User has no stock remaining'}), 400

            # --- 3. 両方の残数/在庫を更新 ---
            new_user_stock = user['stock'] - 1
            new_total = user['total'] + 1
            db.execute(conn, "UPDATE users SET stock = ?, total = ? WHERE card_id = ?", 
                       (new_user_stock, new_total, card_id))
            
            new_unit_stock = unit['stock'] - 1
            db.execute(conn, "UPDATE units SET stock = ? WHERE name = ?", 
                       (new_unit_stock, unit_name))

            message = f"[{unit_name}] 利用成功 (カードID: {card_id}, 残数: {new_user_stock})"
            add_history(message, 'usage')

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
    unit_name = data.get('unit_name')
    unit_password = data.get('password')
    ip_address = request.remote_addr
    
    if not all([unit_name, unit_password]):
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
            
            return jsonify({
                'success': True,
                'stock': unit['stock'],
                'available': unit['available'],
                'auto_register_mode': server_settings['auto_register_mode'],
                'auto_register_stock': server_settings['auto_register_stock'],
                'daily_limit': server_settings['daily_limit'],
                'settings_version': settings_version
            })
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


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """現在の設定を取得（子機からの同期用）"""
    return jsonify({
        'auto_register_mode': server_settings['auto_register_mode'],
        'auto_register_stock': server_settings['auto_register_stock'],
        'daily_limit': server_settings['daily_limit'],
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
    if 'daily_limit' in data:
        server_settings['daily_limit'] = int(data['daily_limit'])
    
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
        server_settings['daily_limit'] = int(request.form.get('daily_limit', 2))
        
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
