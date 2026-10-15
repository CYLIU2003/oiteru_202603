#!/usr/bin/env python3
"""
app.pyをdb_adapter対応に自動変換するスクリプト
"""
import re

def migrate_app_py():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 変換パターン
    patterns = [
        # db = get_db() → with get_connection() as conn:
        (r'(\s+)db = get_db\(\)\n', r'\1with get_connection() as conn:\n'),
        
        # db.execute(...).fetchone() → db.fetchone(conn, ...)
        (r'db\.execute\(([^)]+)\)\.fetchone\(\)', r'db.fetchone(conn, \1)'),
        
        # db.execute(...).fetchall() → db.fetchall(conn, ...)
        (r'db\.execute\(([^)]+)\)\.fetchall\(\)', r'db.fetchall(conn, \1)'),
        
        # db.execute(...) (単独) → db.execute(conn, ...)
        (r'db\.execute\(', r'db.execute(conn, '),
        
        # db.commit() → 削除（with文で自動コミット）
        (r'\s+db\.commit\(\)\s*\n', '\n'),
        
        # cursor = db.cursor() → 不要（削除）
        (r'\s+cursor = db\.cursor\(\)\s*\n', ''),
        
        # cursor.execute(...) → db.execute(conn, ...)
        (r'cursor\.execute\(', r'db.execute(conn, '),
        
        # cursor.fetchall() → 前のdb.execute()の結果を使う（手動修正必要）
        # cursor.fetchone() → 前のdb.execute()の結果を使う（手動修正必要）
        
        # sqlite3.IntegrityError → DatabaseError
        (r'sqlite3\.IntegrityError', r'DatabaseError'),
    ]
    
    original = content
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        # バックアップ
        with open('app.py.backup', 'w', encoding='utf-8') as f:
            f.write(original)
        print("元のファイルを app.py.backup に保存しました")
        
        # 新しい内容を保存
        with open('app.py.migrated', 'w', encoding='utf-8') as f:
            f.write(content)
        print("変換後のファイルを app.py.migrated に保存しました")
        print("\n【注意】以下の項目は手動で確認・修正してください:")
        print("1. インデントの調整（with文のネスト）")
        print("2. cursor.fetchall() / cursor.fetchone() の処理")
        print("3. トランザクションの範囲")
        print("4. エラーハンドリング")
        print("\n確認後、app.py.migratedをapp.pyにリネームしてください。")
    else:
        print("変更の必要なパターンが見つかりませんでした")

if __name__ == '__main__':
    migrate_app_py()
