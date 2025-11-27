import os
import hashlib
import random
import io
import pandas as pd
import traceback
import re
import json
import socket
import subprocess # Tailscale対応のため追加
import threading
import time
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, session, flash, g, send_file
)
from db_adapter import db, get_connection, DatabaseError

# 注意: 親機（サーバー）ではNFCリーダーを直接使用しません
# NFCリーダーは子機（Raspberry Pi）にのみ接続されています
# nfcpyのインポートは互換性のためのみ残していますが、使用しません
try:
    import nfc
except ImportError:
    nfc = None

 # --- Flaskアプリケーションの初期化 ---
# templates と static フォルダをデフォルトに変更
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'oiteru_secret_key_2025_final'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oiteru.sqlite3')

# 未登録子機の一時保存用（メモリ内）
# {unit_name: {password, ip_address, first_seen, last_seen, heartbeat_count}}
unregistered_units = {}

# 子機からの診断情報保存用（メモリ内）
# {unit_name: {timestamp, diagnostics: [(component, status, detail), ...], ip_address}}
unit_diagnostics = {}

# 子機からのログ保存用（メモリ内）
# {unit_name: [{timestamp, level, message, ip_address}, ...]}
unit_logs = {}


# --- DB Helpers ---

# --- データベース接続ヘルパー ---
# db_adapterを使用するため、get_db()は不要になりましたが、
# 互換性のため残しています。新しいコードではget_connection()を使用してください。
def get_db_connection():
    """データベース接続を取得（db_adapter経由）"""
    return get_connection()

@app.teardown_appcontext
def close_connection(exception):
    # db_adapterが接続管理を行うため、特別な処理は不要
    pass

# --- データベース初期化 ---
def init_db():
    """データベースのテーブルを初期化する"""
    # MySQLの場合はinit_mysql.sqlで初期化されるため、SQLiteの場合のみ実行
    if db.db_type == 'mysql':
        print("MySQLモード: init_mysql.sqlでデータベースを初期化してください")
        return
        
    if os.path.exists(DB_PATH):
        print("データベースは既に存在します。")
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
                    last1 TEXT,
                    last2 TEXT,
                    last3 TEXT,
                    last4 TEXT,
                    last5 TEXT,
                    last6 TEXT,
                    last7 TEXT,
                    last8 TEXT,
                    last9 TEXT,
                    last10 TEXT
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
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # infoテーブル（管理者情報など）
            db.execute(conn, '''
                CREATE TABLE info (
                    id INTEGER PRIMARY KEY,
                    pass TEXT NOT NULL
                )
            ''')
            
            # デフォルトの管理者パスワードを設定（admin）
            default_password = hashlib.sha256('admin'.encode()).hexdigest()
            db.execute(conn, "INSERT INTO info (id, pass) VALUES (?, ?)", (1, default_password))
            
            print("データベースの初期化が完了しました。")
            print("デフォルト管理者パスワード: admin")
# --- DBマイグレーション ---
def migrate_db():
    """
    データベーススキーマをチェックし、不足しているテーブルやカラムがあれば追加する。
    MySQLの場合はinit_mysql.sqlで初期化されるため、SQLiteの場合のみ実行。
    """
    if db.db_type == 'mysql':
        print("MySQLモード: マイグレーションはスキップします")
        return
        
    print("データベースの構造をチェック・更新します...")
    with app.app_context():
        with get_connection() as conn:
            # 既存のテーブルを確認
            existing_tables_result = db.fetchall(conn, "SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row['name'] for row in existing_tables_result]
            
            updated = False
            
            # historyテーブルが存在しない場合は作成
            if 'history' not in existing_tables:
                print("  -> 更新: historyテーブルを作成します。")
                try:
                    db.execute(conn, '''
                        CREATE TABLE history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            txt TEXT NOT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    updated = True
                    print("  -> historyテーブルを作成しました。")
                except Exception as e:
                    print(f"  -> エラー: historyテーブルの作成に失敗しました: {e}")
            
            # infoテーブルが存在しない場合は作成
            if 'info' not in existing_tables:
                print("  -> 更新: infoテーブルを作成します。")
                try:
                    db.execute(conn, '''
                        CREATE TABLE info (
                            id INTEGER PRIMARY KEY,
                            pass TEXT NOT NULL
                        )
                    ''')
                    # デフォルトの管理者パスワードを設定（admin）
                    default_password = hashlib.sha256('admin'.encode()).hexdigest()
                    db.execute(conn, "INSERT INTO info (id, pass) VALUES (?, ?)", (1, default_password))
                    updated = True
                    print("  -> infoテーブルを作成しました。(デフォルトパスワード: admin)")
                except Exception as e:
                    print(f"  -> エラー: infoテーブルの作成に失敗しました: {e}")
            
            # unitsテーブルのカラムを確認
            if 'units' in existing_tables:
                columns_result = db.fetchall(conn, "PRAGMA table_info(units)")
                columns = [row['name'] for row in columns_result]
                
                if 'last_seen' not in columns:
                    print("  -> 更新: unitsテーブルに 'last_seen' カラムを追加します。")
                    try:
                        db.execute(conn, "ALTER TABLE units ADD COLUMN last_seen TEXT")
                        updated = True
                        print("  -> last_seenカラムを追加しました。")
                    except Exception as e:
                        print(f"  -> エラー: カラムの追加に失敗しました: {e}")
                
                if 'ip_address' not in columns:
                    print("  -> 更新: unitsテーブルに 'ip_address' カラムを追加します。")
                    try:
                        db.execute(conn, "ALTER TABLE units ADD COLUMN ip_address TEXT")
                        updated = True
                        print("  -> ip_addressカラムを追加しました。")
                    except Exception as e:
                        print(f"  -> エラー: カラムの追加に失敗しました: {e}")
            
            if not updated:
                print("  -> データベースは最新です。")

# --- ユーティリティ関数 ---
def add_history(text, log_type='usage'):
    """
    履歴を追加
    log_type: 'usage'=利用履歴, 'system'=システムログ, 'heartbeat'=ハートビート
    """
    with get_connection() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        db.execute(conn, "INSERT INTO history (txt, type) VALUES (?, ?)", (f"{now}: {text}", log_type))

def check_password(password):
    with get_connection() as conn:
        info = db.fetchone(conn, "SELECT pass FROM info WHERE id = ?", (1,))
        return info and info['pass'] == hashlib.sha256(password.encode()).hexdigest()


# --- ▼▼▼ Tailscale対応 ▼▼▼ ---
def get_tailscale_ip():
    """TailscaleのIPアドレスを取得する"""
    try:
        # `tailscale ip -4` コマンドを実行してIPv4アドレスを取得
        result = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, check=True)
        # 出力の末尾にある改行などを除去して返す
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, Exception) as e:
        # Tailscaleがインストールされていない、または実行中でない場合
        print(f"INFO: Tailscale IPが取得できませんでした: {e}")
        return None

def broadcast_server_info():
    """サーバー情報をローカルネットワークにUDPブロードキャストする"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # まずTailscale IPの取得を試みる
    server_ip = get_tailscale_ip()
    
    # Tailscale IPがなければ、ローカルIPにフォールバック
    if not server_ip:
        try:
            hostname = socket.gethostname()
            server_ip = socket.gethostbyname(hostname)
        except Exception:
            server_ip = "127.0.0.1" # それも失敗したらループバック

    print(f"◎ 親機の情報発信を開始します (通知IP: {server_ip}, ポート: 12345)")

    while True:
        message = json.dumps({
            "type": "oiteru_server_heartbeat",
            "server_ip": server_ip,
            "port": 5000
        }).encode('utf-8')
        
        try:
            sock.sendto(message, ('<broadcast>', 12345))
            with app.app_context():
                add_history(f"親機ハートビート送信 (IP: {server_ip})")
        except Exception as e:
            print(f"!! ハートビート送信エラー: {e}")
        
        time.sleep(3)
# --- ▲▲▲ Tailscale対応 ▲▲▲ ---


# ICカードリーダーからカードIDを同期的に読み取る
def read_card_id():
    """
    ICカードリーダーからカードIDを同期的に読み取る。
    タイムアウト付きでカードを待ち受け、成功すればカードID(str)、失敗すればNoneを返す。
    """
    try:
        # nfcpyがインストールされていない場合はエラー
        if nfc is None:
            flash("サーバー側でNFCライブラリ(nfcpy)が不足しています。", "error")
            return None

        # USB接続のリーダーに接続
        with nfc.ContactlessFrontend('usb') as clf:
            # 1.5秒間、3回の試行でカードを待つ (ブロッキング処理)
            target = clf.sense(nfc.clf.RemoteTarget('106A'), nfc.clf.RemoteTarget('106B'), nfc.clf.RemoteTarget('212F'), iterations=3, interval=0.5)

            if target is None:
                flash("ICカードを読み取れませんでした。リーダーにカードを置いてから、もう一度お試しください。", "error")
                return None

            # ターゲットを有効化してタグ情報を取得
            tag = nfc.tag.activate(clf, target)
            if hasattr(tag, 'idm'):
                return tag.idm.hex()
            else:
                flash("カード情報を正しく取得できませんでした。", "error")
                return None

    except IOError:
        flash("ICカードリーダーが見つかりません。USB接続を確認してください。", "error")
        return None
    except Exception as e:
        # その他の予期せぬエラー
        error_message = f"NFCリーダーで予期せぬエラーが発生しました: {e}"
        print(error_message)
        traceback.print_exc()
        flash(error_message, "error")
        return None

# --- UIルート ---

# ↓↓↓↓ ここから貼り付け ↓↓↓↓

@app.route("/admin/backup/download")
def admin_backup_download():
    """管理者向けにユーザーデータをExcel形式でダウンロードさせる"""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    try:
        # データベースから全ユーザー情報を取得
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
        add_history("データバックアップ作成")
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f"バックアップファイルの作成中にエラーが発生しました: {e}", "error")
        add_history(f"バックアップ作成失敗: {e}")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/restore', methods=['GET', 'POST'])
def admin_restore():
    """バックアップファイルからユーザーデータを復元する"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        if 'backup_file' not in request.files:
            flash('ファイルが選択されていません。', 'error')
            return redirect(request.url)
        file = request.files['backup_file']
        if file.filename == '':
            flash('ファイルが選択されていません。', 'error')
            return redirect(request.url)
        if file and file.filename.endswith('.xlsx'):
            try:
                df = pd.read_excel(file)
                required_columns = ['card_id', 'allow', 'entry', 'stock', 'today', 'total']
                if not all(col in df.columns for col in required_columns):
                    flash('Excelファイルの形式が正しくありません。必須カラムが不足しています。', 'error')
                    return redirect(request.url)
                with get_connection() as conn:
                    db.execute(conn, "DELETE FROM users")
                    df.to_sql('users', conn, if_exists='append', index=False)
                add_history("データ復元完了")
                flash('データベースの復元が正常に完了しました。', 'success')
                return redirect(url_for('admin_users'))
            except Exception as e:
                add_history(f"データ復元エラー: {e}")
                flash(f'ファイルの処理中にエラーが発生しました: {e}', 'error')
                return redirect(request.url)
        else:
            flash('許可されていないファイル形式です。.xlsxファイルをアップロードしてください。', 'warning')
            return redirect(request.url)

    # GETリクエストの場合はアップロードフォームを表示
    return render_template('admin_restore.html')

@app.route('/admin/visuals')
def admin_visuals():
    """利用状況を可視化するページ (履歴ベース)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    with get_connection() as conn:
        # 履歴から「利用を記録しました」というログのみを抽出
        logs = db.fetchall(conn, "SELECT txt FROM history WHERE txt LIKE ?", ('%] 利用を記録しました%',))

    timestamps = []
    for log in logs:
        timestamp_str = log['txt'][:16]
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
            timestamps.append(dt)
        except (ValueError, TypeError):
            continue

    hourly_counts = [0] * 24
    daily_counts = {}
    weekly_counts = [0] * 7
    for ts in timestamps:
        hourly_counts[ts.hour] += 1
        day_str = ts.strftime("%Y-%m-%d")
        daily_counts[day_str] = daily_counts.get(day_str, 0) + 1
        weekly_counts[ts.weekday()] += 1
    sorted_daily = sorted(daily_counts.items())
    daily_labels = [item[0] for item in sorted_daily]
    daily_values = [item[1] for item in sorted_daily]
    chart_data = {
        'hourly_labels': [f"{h:02d}:00" for h in range(24)],
        'hourly_data': hourly_counts,
        'daily_labels': daily_labels,
        'daily_data': daily_values,
        'weekly_labels': ['月', '火', '水', '木', '金', '土', '日'],
        'weekly_data': weekly_counts
    }
    return render_template('admin_visuals.html', chart_data=chart_data)

@app.route('/admin/csv_export')
def admin_csv_export():
    """利用履歴をCSV形式でダウンロードする"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    with get_connection() as conn:
        logs = db.fetchall(conn,
            "SELECT txt FROM history WHERE txt LIKE ? ORDER BY id ASC",
            ('%] 利用を記録しました%',)
        )
    if not logs:
        flash("ダウンロード対象の利用履歴がありません。", "warning")
        return redirect(url_for('admin_dashboard'))
    usage_data = []
    for log in logs:
        log_text = log['txt']
        timestamp_str = log_text[:16]
        match = re.search(r'\((\w+)\)', log_text)
        card_id = match.group(1) if match else '不明'
        usage_data.append({'timestamp': timestamp_str, 'card_id': card_id})
    df = pd.DataFrame(usage_data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(
        io.BytesIO(output.read().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='usage_history.csv'
    )

@app.route('/admin/log_export')
def admin_log_export():
    """全ての履歴ログをCSV形式でダウンロードする"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    with get_connection() as conn:
        # 履歴テーブルから全てのログをIDの昇順（古い順）で取得
        logs = db.fetchall(conn, "SELECT txt FROM history ORDER BY id ASC")

    if not logs:
        flash("ダウンロード対象のログがありません。", "warning")
        return redirect(url_for('admin_dashboard'))

    # DataFrameに変換しやすいようにリストに格納
    log_data = [{'log_entry': log['txt']} for log in logs]
    df = pd.DataFrame(log_data)

    # CSVをメモリ上で作成
    output = io.StringIO()
    df.to_csv(output, index=False, header=['log']) # ヘッダーを'log'に指定
    output.seek(0)

    # ファイルとして送信
    return send_file(
        io.BytesIO(output.read().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='all_history_logs.csv'
    )

@app.route("/admin/history")
def admin_history():
    """利用履歴を表示するページ（usageのみ）"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    with get_connection() as conn:
        # usageタイプのログのみを取得
        history = db.fetchall(conn, "SELECT * FROM history WHERE type = 'usage' ORDER BY created_at DESC LIMIT 100")
    return render_template("admin_history.html", history=history)

@app.route("/admin/diagnostics")
def admin_diagnostics():
    """子機の起動診断情報を表示するページ"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # 診断情報とログをテンプレートに渡す
    return render_template("admin_diagnostics.html", 
                         diagnostics=unit_diagnostics,
                         logs=unit_logs)

@app.route("/api/run_diagnostics", methods=['POST'])
def run_diagnostics_api():
    """管理画面から親機の診断を実行するAPIエンドポイント"""
    try:
        from diagnostics import run_full_diagnostics
        
        # 診断を実行（コンソール出力なし）
        diagnostics_results = run_full_diagnostics(db_path=DB_PATH, verbose=False)
        
        return jsonify({
            'success': True,
            'diagnostics': diagnostics_results,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'diagnostics.pyが見つかりません'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ↑↑↑↑ ここまで貼り付け ↑↑↑↑
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # POSTリクエスト（登録ボタンが押された時）
    if request.method == "POST":
        # 課題1で作成した関数で、実際のカードIDを読み取る
        card_id = read_card_id()

        # カードIDが正常に読み取れた場合のみ処理を続行
        if card_id:
            try:
                with get_connection() as conn:
                    # DBに新しいユーザーを登録
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    db.execute(conn, "INSERT INTO users (card_id, entry) VALUES (?, ?)", (card_id, now))
                add_history(f"新規登録({card_id})", 'system')
                flash(f"登録が完了しました。(カードID: {card_id})", "success")
            except DatabaseError:
                # "UNIQUE"制約違反エラーを捕捉し、登録済みであることをユーザーに通知
                flash("この学生証は既に登録済みです。", "warning")
            except Exception as e:
                flash(f"データベース登録中にエラーが発生しました: {e}", "error")

        # read_card_id関数がNoneを返した場合、エラーメッセージは既に出ているのでここでは何もしない
        return redirect(url_for("register"))

    # GETリクエスト（ページ表示時）
    # ページ表示時にリーダーの接続状態を確認し、結果をテンプレートに渡す
    reader_connected = False
    try:
        if nfc:
            with nfc.ContactlessFrontend('usb'):
                reader_connected = True
    except Exception:
        reader_connected = False
        
    return render_template("register.html", reader_connected=reader_connected)



@app.route("/usage", methods=["GET", "POST"])
def usage():
    # POSTリクエスト（確認ボタンが押された時）
    if request.method == "POST":
        if 'retry' in request.form:
            return redirect(url_for('usage'))

        # 課題1で作成した関数で、実際のカードIDを読み取る
        card_id = read_card_id()
        if card_id:
            with get_connection() as conn:
                user = db.fetchone(conn, "SELECT * FROM users WHERE card_id = ?", (card_id,))
                if user:
                    # ユーザーが見つかった場合、結果ページを表示
                    return render_template("usage_result.html", **dict(user))
                else:
                    flash("この学生証は登録されていません。", "warning")
                    return redirect(url_for("usage"))
        else:
            # カードが読み取れなかった場合（エラーはread_card_id内でflash済み）
            return redirect(url_for("usage"))

    # GETリクエスト（ページ表示時）
    reader_connected = False
    try:
        if nfc is not None:
            with nfc.ContactlessFrontend('usb'):
                reader_connected = True
    except Exception:
        reader_connected = False
    
    return render_template("usage.html", reader_connected=reader_connected)

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

        # ダッシュボードのサマリー表示用に、排出回数のみをカウント
        usage_count_row = db.fetchone(conn, "SELECT COUNT(id) as count FROM history WHERE txt LIKE ?", ('%] 利用を記録しました%',))
        usage_count = usage_count_row['count'] if usage_count_row else 0

    return render_template("admin_dashboard.html", users=users, units=units, history=history, usage_count=usage_count)

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
            # --- 削除処理 ---
            if request.form.get("action") == "delete":
                db.execute(conn, "DELETE FROM users WHERE id = ?", (uid,))
                add_history(f"利用者を手動削除しました (ID:{uid})", 'system')
                flash(f"利用者(ID:{uid})を削除しました。", "success")
                return redirect(url_for("admin_users"))
            # --- 更新処理 ---
            card_id = request.form.get("cardid")
            allow = request.form.get("allow")
            stock = request.form.get("stock")
            db.execute(conn,
                "UPDATE users SET card_id = ?, allow = ?, stock = ? WHERE id = ?",
                (card_id, allow, stock, uid)
            )
        add_history(f"利用者情報を更新しました (ID:{uid})", 'system')
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
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    with get_connection() as conn:
        # --- ハートビートのタイムアウト処理 ---
        # 子機クライアント(unit_client.py)は30秒ごとにハートビートを送信するため、
        # 65秒以上信号がなければオフラインと判断する。
        HEARTBEAT_TIMEOUT = timedelta(seconds=65) 
        now = datetime.now()
        
        # 現在オンライン(connect=1)になっている子機を取得
        active_units = db.fetchall(conn, "SELECT * FROM units WHERE connect = ?", (1,))
        
        for unit in active_units:
            if unit['last_seen']:
                try:
                    last_seen_dt = datetime.strptime(unit['last_seen'], "%Y-%m-%d %H:%M:%S")
                    # 最終接続時刻からタイムアウト時間を経過しているか確認
                    if now - last_seen_dt > HEARTBEAT_TIMEOUT:
                        # タイムアウトした場合、接続状態をオフライン(0)に更新
                        db.execute(conn, "UPDATE units SET connect = ? WHERE id = ?", (0, unit['id']))
                        add_history(f"子機がタイムアウトしました: {unit['name']}", 'system')
                except ValueError:
                    # 日付の形式が不正な場合はスキップ
                    continue
        
        # --- タイムアウト処理ここまで ---

        # 最新の状態をDBから再度取得して表示
        all_units = db.fetchall(conn, "SELECT * FROM units ORDER BY id")
    return render_template("admin_units.html", units=all_units)

@app.route("/admin/unit_detail/<int:uid>", methods=["GET", "POST"])
def admin_unit_detail(uid):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == "POST":
        with get_connection() as conn:
            # --- 削除処理 ---
            if request.form.get("action") == "delete":
                unit_to_delete = db.fetchone(conn, "SELECT name FROM units WHERE id = ?", (uid,))
                db.execute(conn, "DELETE FROM units WHERE id = ?", (uid,))
                add_history(f"子機を手動削除しました (ID:{uid}, 名前:{unit_to_delete['name']})")
                flash(f"子機(ID:{uid})を削除しました。", "success")
                return redirect(url_for("admin_units"))

            # --- 更新処理 ---
            name = request.form.get("name")

            # ▼▼▼ 修正点 ▼▼▼
            # フォームから受け取った値を整数(int)に変換する
            try:
                stock = int(request.form.get("stock", 0))
                available = int(request.form.get("available", 0))
            except (ValueError, TypeError):
                # もし数値に変換できない値が入力された場合は、0として扱う
                stock = 0
                available = 0

            db.execute(conn,
                "UPDATE units SET name = ?, stock = ?, available = ? WHERE id = ?",
                (name, stock, available, uid)
            )
        add_history(f"子機情報を更新しました (ID:{uid}, 名前:{name})")
        flash(f"子機(ID:{uid})の情報を更新しました。", "success")
        return redirect(url_for("admin_unit_detail", uid=uid))

    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE id = ?", (uid,))
        if not unit:
            flash("指定された子機が見つかりません。", "error")
            return redirect(url_for('admin_units'))

        unit_name = unit['name']
        search_pattern = f"%[{unit_name}]%"
        logs = db.fetchall(conn,
            "SELECT txt FROM history WHERE txt LIKE ? ORDER BY id DESC", 
            (search_pattern,)
        )
    return render_template("admin_unit_detail.html", unit=unit, logs=logs)

@app.route("/admin/new_unit", methods=["GET", "POST"])
def admin_new_unit():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        stock = request.form.get('stock', 0)
        available = request.form.get('available', 1)
        try:
            with get_connection() as conn:
                db.execute(conn,
                    "INSERT INTO units (name, password, stock, available, connect) VALUES (?, ?, ?, ?, ?)",
                    (name, password, stock, available, 0)
                )
            add_history(f"新しい子機を手動登録しました: {name}")
            flash(f"子機「{name}」を登録しました。", "success")
            return redirect(url_for('admin_units'))
        except DatabaseError:
            flash("エラー: 同じ名前の子機が既に存在します。", "error")
            return redirect(request.url)
        except Exception as e:
            flash(f"登録中にエラーが発生しました: {e}", "error")
            return redirect(request.url)
    return render_template("admin_new_unit.html")
# ...existing code...

# --- REST API ---


@app.route('/api/unit/heartbeat', methods=['POST'])
def unit_heartbeat():
    """子機からの生存確認を受け取り、在庫情報を返す"""
    data = request.json
    unit_name = data.get('name')
    unit_pass = data.get('password')
    unit_ip = data.get('ip_address') # 子機のIPアドレスを受け取る
    client_reported_stock = data.get('stock') # 子機が認識している在庫数

    if not all([unit_name, unit_pass]):
        return jsonify({'error': 'Name and password are required'}), 400
    
    # 特定のTailscale IPからのアクセスをログに記録
    TARGET_IPS = ['100.111.98.81', '100.100.238.109', '100.95.107.112']
    if unit_ip in TARGET_IPS:
        # 必要であればここで特別な処理を行う
        pass

    with get_connection() as conn:
        unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. もし子機が未登録だったら、一時保存する（自動登録はしない）
        if unit is None:
            # 未登録子機の情報を保存/更新
            if unit_name not in unregistered_units:
                unregistered_units[unit_name] = {
                    'password': unit_pass,
                    'ip_address': unit_ip,
                    'first_seen': now_str,
                    'last_seen': now_str,
                    'heartbeat_count': 1
                }
                print(f"[新規発見] 未登録子機: {unit_name} (IP: {unit_ip})")
            else:
                unregistered_units[unit_name]['last_seen'] = now_str
                unregistered_units[unit_name]['heartbeat_count'] += 1
                unregistered_units[unit_name]['ip_address'] = unit_ip  # IPが変わった場合に更新
            
            # 未登録なので拒否応答（stock=0で応答）
            return jsonify({
                'success': False,
                'error': 'Unit not registered. Please contact administrator.',
                'message': '未登録の子機です。管理者に登録を依頼してください。',
                'stock': 0
            }), 403

        # 2. 登録済みの子機の場合、パスワードを検証
        if unit['password'] != unit_pass:
            return jsonify({'error': 'Invalid credentials'}), 401

        # 3. 接続状態と最終接続時刻、IPアドレスを更新
        db.execute(conn,
            "UPDATE units SET connect = ?, last_seen = ?, ip_address = ? WHERE id = ?",
            (1, now_str, unit_ip, unit['id'])
        )
        
        # 子機からの在庫報告があり、かつサーバー側と食い違っている場合
        # 基本はサーバー正だが、ログに残すなどの処理が可能
        # ここではサーバーの値を正として返すので、DB更新は行わない（サーバー主導）
        
        # with文を抜けると自動コミット
        
        # 4. 最新の在庫情報を付けて応答する
        return jsonify({
            'success': True,
            'message': 'Heartbeat received',
            'stock': unit['stock']
        }), 200

@app.route('/api/diagnostics', methods=['POST'])
def receive_diagnostics():
    """子機からの起動時診断結果を受け取り保存"""
    data = request.json
    unit_name = data.get('unit_name')
    diagnostics = data.get('diagnostics')  # [(component, status, detail), ...]
    timestamp = data.get('timestamp')
    
    if not all([unit_name, diagnostics]):
        return jsonify({'error': 'unit_name and diagnostics are required'}), 400
    
    # 診断情報をメモリに保存（グローバル変数を使用）
    if 'unit_diagnostics' not in globals():
        global unit_diagnostics
        unit_diagnostics = {}
    
    unit_diagnostics[unit_name] = {
        'timestamp': timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'diagnostics': diagnostics,
        'ip_address': request.remote_addr
    }
    
    # ログに記録
    print(f"[診断情報] {unit_name} から受信:")
    for component, status, detail in diagnostics:
        status_icon = "✅" if status == "OK" else "❌"
        print(f"  {status_icon} {component}: {detail}")
    
    return jsonify({
        'success': True,
        'message': 'Diagnostics received'
    }), 200

@app.route('/api/log', methods=['POST'])
def receive_log():
    """子機からのリアルタイムログを受け取り保存"""
    data = request.json
    unit_name = data.get('unit_name')
    log_level = data.get('level', 'INFO')  # DEBUG, INFO, WARNING, ERROR
    message = data.get('message')
    timestamp = data.get('timestamp')
    
    if not all([unit_name, message]):
        return jsonify({'error': 'unit_name and message are required'}), 400
    
    # ログをメモリに保存（グローバル変数を使用）
    if 'unit_logs' not in globals():
        global unit_logs
        unit_logs = {}
    
    if unit_name not in unit_logs:
        unit_logs[unit_name] = []
    
    log_entry = {
        'timestamp': timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'level': log_level,
        'message': message,
        'ip_address': request.remote_addr
    }
    
    unit_logs[unit_name].append(log_entry)
    
    # 最新1000件のみ保持
    if len(unit_logs[unit_name]) > 1000:
        unit_logs[unit_name] = unit_logs[unit_name][-1000:]
    
    # サーバーコンソールにも出力
    level_prefix = f"[{log_level}]"
    print(f"{level_prefix} [{unit_name}] {message}")
    
    return jsonify({
        'success': True,
        'message': 'Log received'
    }), 200

@app.route('/api/unregistered_units', methods=['GET'])
def get_unregistered_units():
    """未登録の子機一覧を取得（自動探知用）"""
    # 過去5分以内にハートビートを送ってきた未登録子機のみ表示
    current_time = datetime.now()
    active_units = []
    
    for unit_name, info in list(unregistered_units.items()):
        last_seen = datetime.strptime(info['last_seen'], "%Y-%m-%d %H:%M:%S")
        time_diff = (current_time - last_seen).total_seconds()
        
        if time_diff < 300:  # 5分以内
            active_units.append({
                'name': unit_name,
                'ip_address': info['ip_address'],
                'first_seen': info['first_seen'],
                'last_seen': info['last_seen'],
                'heartbeat_count': info['heartbeat_count'],
                'seconds_ago': int(time_diff)
            })
        else:
            # 古いエントリは削除
            del unregistered_units[unit_name]
    
    return jsonify({
        'success': True,
        'units': active_units,
        'count': len(active_units)
    })

@app.route('/api/register_unit', methods=['POST'])
def register_unit_from_discovery():
    """自動探知した子機を登録"""
    data = request.json
    unit_name = data.get('name')
    
    if not unit_name or unit_name not in unregistered_units:
        return jsonify({'error': '指定された子機が見つかりません'}), 404
    
    # 未登録リストから情報を取得
    unit_info = unregistered_units[unit_name]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with get_connection() as conn:
            # データベースに登録
            db.execute(conn,
                "INSERT INTO units (name, password, stock, connect, available, last_seen, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (unit_name, unit_info['password'], 0, 1, 1, now_str, unit_info['ip_address'])
            )
        
        # 履歴に記録
        add_history(f"子機を登録しました: {unit_name} (IP: {unit_info['ip_address']})")
        
        # 未登録リストから削除
        del unregistered_units[unit_name]
        
        return jsonify({
            'success': True,
            'message': f'子機 {unit_name} を登録しました'
        })
    except Exception as e:
        return jsonify({
            'error': f'登録に失敗しました: {str(e)}'
        }), 500

@app.route("/api/health")
def health_check():
    """サーバーの生存確認用エンドポイント"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route("/api/reader_status")
def reader_status():
    """
    NFCリーダーの状態を確認するエンドポイント
    
    注意: 親機（サーバー）にはNFCリーダーは接続されていません。
    NFCリーダーは子機（Raspberry Pi）に接続されており、
    子機からのハートビートで状態が報告されます。
    
    このエンドポイントは、接続中の子機のNFC状態を返します。
    """
    try:
        with get_connection() as conn:
            # 最近アクティブな子機（過去1分以内に接続確認）を取得
            # unitsテーブルのカラム: id, name, password, stock, connect, available, last_seen
            if db.db_type == 'mysql':
                # MySQL版: TIMESTAMPDIFF関数を使用
                query = '''
                    SELECT name, last_seen, stock, connect,
                           TIMESTAMPDIFF(SECOND, last_seen, NOW()) as seconds_ago
                    FROM units
                    WHERE last_seen IS NOT NULL 
                      AND TIMESTAMPDIFF(SECOND, last_seen, NOW()) < 60
                    ORDER BY last_seen DESC
                '''
            else:
                # SQLite版: julianday関数を使用
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
                "message": f"{len(active_units)}台の子機がオンライン",
                "note": "親機にはNFCリーダーは接続されていません。子機のステータスを表示しています。"
            })
        else:
            return jsonify({
                "connected": False,
                "active_units": [],
                "error": "オンラインの子機が見つかりません（過去60秒以内にハートビートなし）",
                "note": "親機にはNFCリーダーは接続されていません。子機が接続されると状態が表示されます。"
            }), 503  # Service Unavailable
            
    except Exception as e:
        error_message = str(e)
        print(f"リーダーステータス取得エラー: {error_message}")
        print(traceback.format_exc())
        return jsonify({
            "connected": False,
            "error": f"ステータス取得失敗: {error_message}"
        }), 500

@app.route("/api/local_nfc_reader")
def local_nfc_reader():
    """
    親機PC（ホストマシン）に接続されたNFCリーダー（RC-S380など）を検出
    
    注意: これは子機のNFCリーダーとは別で、親機PCに直接接続された
    カードリーダーの状態を確認します。
    """
    try:
        if nfc is None:
            return jsonify({
                "connected": False,
                "error": "nfcpyがインストールされていません",
                "note": "親機でNFCリーダーを使用する場合は 'pip install nfcpy' を実行してください"
            }), 503
        
        # 複数のUSBパスを試行
        usb_paths = [
            'usb',           # 自動検出
            'usb:054c:06c3',  # Sony PaSoRi RC-S380
            'usb:054c:06c1',  # Sony PaSoRi RC-S370
            'usb:054c:02e1',  # Sony PaSoRi RC-S330
        ]
        
        for path in usb_paths:
            try:
                clf = nfc.ContactlessFrontend(path)
                if clf:
                    # リーダー情報を取得
                    device_info = str(clf.device) if hasattr(clf, 'device') else "不明なデバイス"
                    clf.close()
                    
                    return jsonify({
                        "connected": True,
                        "device_path": path,
                        "device_info": device_info,
                        "message": "親機PCのNFCリーダーが検出されました",
                        "note": "これは親機PCに接続されたリーダーです（子機とは別）"
                    })
            except Exception:
                continue
        
        # すべて失敗
        return jsonify({
            "connected": False,
            "error": "親機PCにNFCリーダーが接続されていません",
            "tried_paths": usb_paths,
            "note": "RC-S380などのNFCリーダーをPCに接続してください"
        }), 404
        
    except Exception as e:
        error_message = str(e)
        print(f"ローカルNFCリーダー検出エラー: {error_message}")
        print(traceback.format_exc())
        return jsonify({
            "connected": False,
            "error": f"検出失敗: {error_message}"
        }), 500

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
    """子機からのログを受け取り、子機名を付けて保存する"""
    data = request.json
    message = data.get('message')
    unit_name = data.get('unit_name', '不明な子機') # 子機名を取得、なければ'不明な子機'

    if message:
        # ログメッセージに子機名を付ける
        log_entry = f"[{unit_name}] {message}"
        add_history(log_entry)  # add_historyは自動でタイムスタンプを付ける
        return jsonify({'success': True, 'message': 'Log added.'}), 200
    return jsonify({'success': False, 'error': 'Message not provided'}), 400

@app.route('/api/record_usage', methods=['POST'])
def api_record_usage():
    data = request.json
    card_id = data.get('card_id')
    unit_name = data.get('unit_name') # 子機名を受け取る

    if not all([card_id, unit_name]):
        return jsonify({'error': 'Card ID and Unit Name are required'}), 400

    try:
        with get_connection() as conn:
            # --- 1. 子機の在庫と利用可能状態を確認 ---
            unit = db.fetchone(conn, "SELECT * FROM units WHERE name = ?", (unit_name,))
            if not unit:
                return jsonify({'error': 'Unit not found'}), 404
            
            if unit['stock'] <= 0 or unit['available'] == 0:
                # 在庫がない場合、ログを記録してエラーを返す
                message = f"[{unit_name}] 在庫不足のため利用不可 (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({'error': 'Unit has no stock remaining'}), 400

            # --- 2. 利用者の利用資格を確認 ---
            user = db.fetchone(conn, "SELECT * FROM users WHERE card_id = ?", (card_id,))
            if not user:
                message = f"[{unit_name}] 未登録カード (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({'error': 'User not found'}), 404
            if user['stock'] <= 0:
                message = f"[{unit_name}] 残数不足 (カードID: {card_id})"
                add_history(message, 'usage')
                return jsonify({'error': 'User has no stock remaining'}), 400

            # --- 3. 両方の残数/在庫を更新 ---
            # 利用者の残数を減らす
            new_user_stock = user['stock'] - 1
            new_total = user['total'] + 1
            db.execute(conn, "UPDATE users SET stock = ?, total = ? WHERE card_id = ?", 
                       (new_user_stock, new_total, card_id))
            
            # 子機の在庫を減らす
            new_unit_stock = unit['stock'] - 1
            db.execute(conn, "UPDATE units SET stock = ? WHERE name = ?", 
                       (new_unit_stock, unit_name))

            # 利用記録を追加
            message = f"[{unit_name}] 利用成功 (カードID: {card_id}, 残数: {new_user_stock})"
            add_history(message, 'usage')

            # もし子機の在庫が0になったら、利用不可(available=0)にする
            if new_unit_stock <= 0:
                db.execute(conn, "UPDATE units SET available = 0 WHERE name = ?", (unit_name,))
                add_history(f"[{unit_name}] 在庫が0になったため、自動的に排出を停止しました。", 'system')

            # with文を抜けると自動コミット
            return jsonify({'success': True, 'message': 'Usage recorded and unit stock updated.'})

    except Exception as e:
        # エラーが発生した場合は自動ロールバック
        print(f"!! 在庫更新エラー: {e}")
        return jsonify({'error': f'Database error: {e}'}), 500

if __name__ == '__main__':
    # システム診断を実行
    print("\n" + "="*60)
    print("OITELU親機を起動しています...")
    print("="*60)
    
    try:
        from diagnostics import run_full_diagnostics, should_continue_startup
        
        # 診断実行
        diagnostics = run_full_diagnostics(db_path=DB_PATH, verbose=True)
        
        # 診断結果に基づいて起動判定
        if not should_continue_startup(diagnostics):
            print("起動を中止しました。")
            exit(1)
    except ImportError:
        print("警告: diagnostics.pyが見つかりません。診断をスキップします。")
    except Exception as e:
        print(f"警告: 診断中にエラーが発生しました: {e}")
        print("診断をスキップして起動を続行します。")
    
    print("\nデータベースを初期化中...")
    init_db()    # データベースの初期化（テーブル作成）
    
    print("データベースマイグレーションを実行中...")
    migrate_db() # データベースのマイグレーションを実行
    
    print("子機向けブロードキャストスレッドを起動中...")
    heartbeat_thread = threading.Thread(target=broadcast_server_info, daemon=True)
    heartbeat_thread.start()
    
    print("\n" + "="*60)
    print("OITELU親機の起動が完了しました！")
    print("Webブラウザで http://localhost:5000 にアクセスしてください")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
