"""Shared fixtures.

DB を使うテストは本物の MySQL 8 で実行する（SQLite は廃止）。
OITERU_TEST_MYSQL=1 のときだけ動き、毎回 *_test という名前の使い捨て DB を
作り直す。本番 DB を消さないよう、名前が _test で終わらなければ拒否する。
"""

from __future__ import annotations

import os

import pymysql
import pytest
from pymysql.cursors import DictCursor


def _mysql_settings() -> dict:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.environ.get("OITERU_TEST_MYSQL_USER", os.getenv("MYSQL_USER", "root")),
        # 空文字のパスワードも明示的な指定として尊重する（.env の値で上書きしない）
        "password": os.environ.get(
            "OITERU_TEST_MYSQL_PASSWORD", os.getenv("MYSQL_PASSWORD", "")
        ),
        "charset": "utf8mb4",
    }


@pytest.fixture
def mysql_conn():
    """Yield a connection to a freshly created, empty test database."""
    if os.getenv("OITERU_TEST_MYSQL") != "1":
        pytest.skip("MySQL が必要なテストです（OITERU_TEST_MYSQL=1 で実行）")

    database = os.getenv("OITERU_TEST_MYSQL_DATABASE", "oiteru_test")
    if not database.endswith("_test"):
        raise RuntimeError(
            f"テスト用 DB 名は _test で終わる必要があります（指定値: {database}）"
        )

    settings = _mysql_settings()
    admin = pymysql.connect(**settings, autocommit=True)
    try:
        with admin.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
            cursor.execute(
                f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn = pymysql.connect(
            **settings, database=database, cursorclass=DictCursor, autocommit=False
        )
        try:
            yield conn
        finally:
            conn.close()
    finally:
        with admin.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
        admin.close()


def run_sql(conn, query: str, params: tuple = ()) -> list:
    """Run one statement on a test connection and return all rows."""
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        return list(cursor.fetchall())
