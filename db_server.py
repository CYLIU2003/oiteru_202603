#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU 親機DB版 (MySQL + Webサーバー一体型)
=========================================

このファイルは親機（データベース持ち）として動作します。
標準DBは MySQL 8 です。起動前に共通ブートストラップがすべての
migration と設定読込を完了させます。

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
SERVER_PORT = int(os.getenv("SERVER_PORT", "5000"))

# MySQLモードを強制
os.environ['DB_TYPE'] = 'mysql'

# 自動登録は明示的に有効化した場合だけ使う
if 'AUTO_REGISTER_MODE' not in os.environ:
    os.environ['AUTO_REGISTER_MODE'] = 'false'

if 'AUTO_REGISTER_STOCK' not in os.environ:
    os.environ['AUTO_REGISTER_STOCK'] = '2'

# server.pyをインポートして実行
from server import (
    app,
    bootstrap_parent,
)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("OITELU 親機DB版 (MySQL) を起動しています...")
    print("="*60)
    
    print(f"\nMySQL設定:")
    print(f"  ホスト: {os.getenv('MYSQL_HOST', 'localhost')}")
    print(f"  ポート: {os.getenv('MYSQL_PORT', '3306')}")
    print(f"  データベース: {os.getenv('MYSQL_DATABASE', 'oiteru')}")
    print(f"\n自動登録モード: {'有効' if os.getenv('AUTO_REGISTER_MODE', 'false').lower() == 'true' else '無効'}")
    print(f"自動登録時の初期残数: {os.getenv('AUTO_REGISTER_STOCK', '2')}")
    
    print("\nデータベースを初期化し、migrationを適用中...")
    bootstrap_parent(start_background=True)
    
    print("\n" + "="*60)
    print("OITELU 親機DB版の起動が完了しました！")
    print(f"Webブラウザで http://localhost:{SERVER_PORT} にアクセスしてください")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False)
