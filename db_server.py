#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU 親機DB版 (MySQL + Webサーバー一体型)
=========================================

このファイルは親機（データベース持ち）として動作します。
MySQLデータベースを含めた環境をDockerで起動することを前提としています。

起動方法 (Docker推奨):
    docker-compose -f docker-compose.mysql.yml up -d

環境変数:
    DB_TYPE=mysql (必須)
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    AUTO_REGISTER_MODE=true/false  (自動登録モード)
    AUTO_REGISTER_STOCK=2          (自動登録時の初期残数)
"""

# db_server.pyはserver.pyを継承して使用
# Docker環境でMySQLを使う場合のエントリーポイント

import os

# MySQLモードを強制
os.environ['DB_TYPE'] = 'mysql'

# 自動登録モードをデフォルトで有効化（運用開始時は便利）
if 'AUTO_REGISTER_MODE' not in os.environ:
    os.environ['AUTO_REGISTER_MODE'] = 'true'

if 'AUTO_REGISTER_STOCK' not in os.environ:
    os.environ['AUTO_REGISTER_STOCK'] = '2'

# server.pyをインポートして実行
from server import (
    app,
    init_db,
    migrate_db,
    load_settings_from_db,
    ensure_admin_password,
    broadcast_server_info,
)
import threading

if __name__ == '__main__':
    print("\n" + "="*60)
    print("OITELU 親機DB版 (MySQL) を起動しています...")
    print("="*60)
    
    print(f"\nMySQL設定:")
    print(f"  ホスト: {os.getenv('MYSQL_HOST', 'localhost')}")
    print(f"  ポート: {os.getenv('MYSQL_PORT', '3306')}")
    print(f"  データベース: {os.getenv('MYSQL_DATABASE', 'oiteru')}")
    print(f"\n自動登録モード: {'有効' if os.getenv('AUTO_REGISTER_MODE', 'true').lower() == 'true' else '無効'}")
    print(f"自動登録時の初期残数: {os.getenv('AUTO_REGISTER_STOCK', '2')}")
    
    print("\n子機向けブロードキャストスレッドを起動中...")
    heartbeat_thread = threading.Thread(target=broadcast_server_info, daemon=True)
    heartbeat_thread.start()

    print("\nデータベースを初期化中...")
    init_db()
    migrate_db()
    ensure_admin_password()
    load_settings_from_db()
    
    print("\n" + "="*60)
    print("OITELU 親機DB版の起動が完了しました！")
    print("Webブラウザで http://localhost:5000 にアクセスしてください")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
