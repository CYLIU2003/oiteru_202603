#!/usr/bin/env python3
"""データベース内のユーザーを確認するスクリプト"""
import sys
import sqlite3

DB_PATH = 'oiteru.sqlite3'

print("=" * 60)
print("ユーザーデータベース確認")
print("=" * 60)

# 接続確認
try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 全ユーザー数を確認
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']
    print(f"\n総ユーザー数: {total_users}")
    
    # 最初の10ユーザーを表示
    print("\n登録されているユーザー (最初の10件):")
    print("-" * 60)
    cursor.execute("SELECT card_id, name, stock, total FROM users LIMIT 10")
    users = cursor.fetchall()
    
    if users:
        for user in users:
            print(f"カードID: {user['card_id']}")
            print(f"  名前: {user['name']}")
            print(f"  残数: {user['stock']}")
            print(f"  累計: {user['total']}")
            print()
    else:
        print("ユーザーが登録されていません")
    
    # 特定のカードIDを確認（コマンドライン引数から）
    if len(sys.argv) > 1:
        search_card_id = sys.argv[1]
        print("=" * 60)
        print(f"カードID '{search_card_id}' の検索結果:")
        print("-" * 60)
        
        cursor.execute("SELECT * FROM users WHERE card_id = ?", (search_card_id,))
        user = cursor.fetchone()
        if user:
            print(f"✅ ユーザーが見つかりました:")
            print(f"  カードID: {user['card_id']}")
            print(f"  名前: {user['name']}")
            print(f"  残数: {user['stock']}")
            print(f"  累計: {user['total']}")
        else:
            print(f"❌ カードID '{search_card_id}' は登録されていません")
    
    print("\n" + "=" * 60)
    
    conn.close()
    
except Exception as e:
    print(f"エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
