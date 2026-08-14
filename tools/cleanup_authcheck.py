#!/usr/bin/env python3
"""認証チェック用に作成したテストデータを削除する"""
import sqlite3

DB = "/mnt/c/oiteru_202603/oiteru.sqlite3"

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute(
    "DELETE FROM users WHERE card_id IN (?, ?)",
    ("__AUTHCHECK_REGISTER__", "__AUTHCHECK_USAGE__"),
)
conn.commit()
print("deleted rows:", cur.rowcount)
conn.close()
