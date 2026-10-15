#!/usr/bin/env python3
"""
app.pyの残りの関数をdb_adapter対応に修正するヘルパースクリプト
手動で適用する修正パターンをリストアップ
"""

# 修正が必要な関数のリスト
functions_to_update = [
    # 管理画面系
    "admin_dashboard",  # Line ~638-645
    "admin_users",  # Line ~653-654
    "admin_user_detail",  # Line ~661-682
    "admin_units",  # Line ~692-719
    "admin_unit_detail",  # Line ~726-770
    "admin_new_unit",  # Line ~782-792
    "admin_unit_logs",  # Line ~822-823
    "unit_heartbeat",  # Line ~856-865
    "upload_users",  # Line ~327-377
    "restore_db",  # Line ~993-999, 1033-1034
    "download_history_csv",  # Line ~399-401, 438-439, 469-471, 499-500
    "get_all_users",  # Line ~1143-1144
    "get_user",  # Line ~1149-1150
]

# 修正パターンのマッピング
patterns = """
基本パターン:
1. db = get_db() → with get_connection() as conn:
2. db.execute(...).fetchone() → db.fetchone(conn, ...)
3. db.execute(...).fetchall() → db.fetchall(conn, ...)
4. db.execute(...) (単独) → db.execute(conn, ...)
5. db.commit() → 削除（with文で自動コミット）
6. sqlite3.IntegrityError → DatabaseError
7. cursor = db.cursor() → 削除
8. cursor.execute(...) → db.execute(conn, ...)

注意点:
- with文のインデントを正しく調整する
- トランザクションの範囲を確認する
- エラーハンドリングを適切に配置する
"""

print("=" * 60)
print("app.py DB Adapter修正ガイド")
print("=" * 60)
print("\n【修正が必要な関数】")
for func in functions_to_update:
    print(f"  - {func}()")

print("\n" + patterns)
print("\n【推奨される修正手順】")
print("1. 各関数を個別に修正")
print("2. get_errors()で構文エラーをチェック")
print("3. テスト実行して動作確認")
print("4. 次の関数に進む")
